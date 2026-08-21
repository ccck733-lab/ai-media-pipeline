"""
AI 自媒体流水线后端 API（FastAPI）
- POST /api/generate  触发整条流水线（含爬取），后台异步执行
- GET  /api/job/<id>  查询任务状态、各步产物、日志尾部
- GET  /api/jobs      列出任务
- GET  /api/file      下载产物（仅限 workspace 内）
- GET  /api/health    健康检查

前端可部署在 Cloudflare Pages（loveshop.us.ci），也可直接由本服务在本地托管：启动后访问
http://localhost:8000 即可一键生成。流水线各步在工具缺失时优雅降级并标记 pending。
"""
import os
import sys
import json
import time
import uuid
import threading
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = REPO_ROOT / "pipeline"
WORKSPACE_DIR = REPO_ROOT / "workspace"
WEB_CONSOLE_DIR = REPO_ROOT / "web-console"
JOBS_DIR = WORKSPACE_DIR / ".jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

PYTHON = sys.executable
# 是否尝试真正用 Remotion 渲染成片（需 node/npx + Remotion 工程已 npm install）。默认关，避免无工具时卡住。
RENDER_VIDEO = os.environ.get("RENDER_VIDEO", "0") == "1"
NODE = os.environ.get("NODE", "node")
NPX = os.environ.get("NPX", "npx")

app = FastAPI(title="ai-media-pipeline API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def _scan_artifacts(account: str) -> list[dict]:
    """扫描 workspace/<account> 下产物，返回可下载条目。"""
    out = []
    base = WORKSPACE_DIR / account
    if not base.exists():
        return out
    for p in sorted(base.rglob("*")):
        if p.is_file():
            rel = p.relative_to(WORKSPACE_DIR)
            out.append({
                "path": str(rel),
                "name": p.name,
                "size": p.stat().st_size,
                "is_video": p.suffix.lower() in (".mp4", ".webm", ".mov"),
            })
    return out


def _run_command(cmd: list[str], log_path: Path) -> int:
    with open(log_path, "a", encoding="utf-8") as log:
        log.write("\n$ " + " ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), stdout=log, stderr=subprocess.STDOUT)
        return proc.returncode


def _try_render_video(account: str, log_path: Path) -> None:
    """可选：用 Remotion 把画面渲染成 mp4（需要 node/npx 且 Remotion 工程已就绪）。"""
    if not RENDER_VIDEO:
        return
    proj = REPO_ROOT / "video" / "remotion-app"
    if not (proj / "package.json").exists():
        return
    try:
        _run_command([NODE, str(proj / "node_modules" / ".bin" / "remotion"), "render", "AIConsole",
                      "--output", str(WORKSPACE_DIR / account / "video_gen" / "output.mp4")], log_path)
    except Exception as e:  # noqa
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"[render] skipped: {e}\n")


def run_job(job_id: str, account: str, topic: str | None, steps: str):
    log_path = JOBS_DIR / f"{job_id}.log"
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"job {job_id} start account={account} steps={steps}\n")

    with jobs_lock:
        jobs[job_id]["status"] = "running"

    try:
        cmd = [PYTHON, str(PIPELINE_DIR / "orchestrator.py"), "--account", account, "--step", steps]
        if steps == "script_writing" and topic:
            cmd += ["--topic", topic]
        rc = _run_command(cmd, log_path)

        # 若请求全链路且开启了渲染，尝试出片
        if steps in ("all", "video_gen"):
            _try_render_video(account, log_path)

        artifacts = _scan_artifacts(account)
        videos = [a for a in artifacts if a["is_video"]]
        with jobs_lock:
            jobs[job_id].update({
                "status": "done" if rc == 0 else "failed",
                "returncode": rc,
                "artifacts": artifacts,
                "videos": videos,
                "finished_at": time.time(),
            })
    except Exception as e:  # noqa
        with jobs_lock:
            jobs[job_id].update({"status": "failed", "error": str(e), "finished_at": time.time()})


@app.get("/api/health")
def health():
    return {"ok": True, "render_video": RENDER_VIDEO, "pipeline_dir": str(PIPELINE_DIR)}


@app.post("/api/generate")
def generate(body: dict):
    account = body.get("account")
    if not account:
        raise HTTPException(400, "account required")
    steps = body.get("steps", "all")
    topic = body.get("topic")
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "account": account,
            "topic": topic,
            "steps": steps,
            "status": "queued",
            "created_at": time.time(),
        }
    t = threading.Thread(target=run_job, args=(job_id, account, topic, steps), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs")
def list_jobs():
    with jobs_lock:
        return [{"job_id": j["job_id"], "account": j["account"], "status": j["status"]}
                for j in sorted(jobs.values(), key=lambda x: x["created_at"], reverse=True)]


@app.get("/api/job/{job_id}")
def job_status(job_id: str):
    with jobs_lock:
        j = jobs.get(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    log_path = JOBS_DIR / f"{job_id}.log"
    tail = ""
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        tail = "\n".join(lines[-40:])
    j = dict(j)
    j["log_tail"] = tail
    return j


@app.get("/api/file")
def get_file(path: str = Query(...)):
    # 仅允许访问 workspace 内的文件
    candidate = (WORKSPACE_DIR / path).resolve()
    if not str(candidate).startswith(str(WORKSPACE_DIR.resolve())) or not candidate.is_file():
        raise HTTPException(403, "forbidden path")
    return FileResponse(str(candidate))


# 在本地运行时，把前端控制台也一并托管在根路径，这样直接访问 http://localhost:8000 即可使用。
if (WEB_CONSOLE_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(WEB_CONSOLE_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
