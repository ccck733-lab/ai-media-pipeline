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
import secrets
import threading
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = REPO_ROOT / "pipeline"
WORKSPACE_DIR = REPO_ROOT / "workspace"
WEB_CONSOLE_DIR = REPO_ROOT / "web-console"
JOBS_DIR = WORKSPACE_DIR / ".jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# ===== 访问控制 =====
# 网站访问密码（可经环境变量 APP_PASSWORD 覆盖）。空字符串表示关闭密码门。
APP_PASSWORD = os.environ.get("APP_PASSWORD", "victory")
# 当前有效的会话令牌（内存态）。登录成功后刷新；进程重启需重新登录。
_VALID_TOKEN = {"value": None}
_AUTH_COOKIE = "wb_token"

PYTHON = sys.executable
# 是否尝试真正用 Remotion 渲染成片（需 node/npx + Remotion 工程已 npm install）。默认关，避免无工具时卡住。
RENDER_VIDEO = os.environ.get("RENDER_VIDEO", "0") == "1"
NODE = os.environ.get("NODE", "node")
NPX = os.environ.get("NPX", "npx")

# Remotion 渲染需要浏览器。本机受限网络无法下载 Remotion 专用 Chrome，
# 优先指向系统已安装的 Google Chrome（macOS 常见路径）。
if "REMOTION_CHROME_EXECUTABLE_PATH" not in os.environ:
    _mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(_mac_chrome):
        os.environ["REMOTION_CHROME_EXECUTABLE_PATH"] = _mac_chrome

app = FastAPI(title="ai-media-pipeline API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 登录页（无密码门时这份 HTML 不会被使用）=====
LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>访问验证 · AI 自媒体控制台</title>
<style>
  :root { --brand:#7c5cff; --accent:#22d3ee; --ink:#f0f0f4; --muted:#8b8b97; --bg:#07070b; }
  * { box-sizing: border-box; margin:0; padding:0; }
  body { font-family: "SF Pro Display",-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    background: var(--bg); color: var(--ink); min-height:100vh; display:flex; align-items:center; justify-content:center;
    overflow:hidden; -webkit-font-smoothing:antialiased; }
  .bg-orbs { position:fixed; inset:0; z-index:0; overflow:hidden; }
  .bg-orbs span { position:absolute; border-radius:50%; filter:blur(80px); opacity:.35; animation:float 20s ease-in-out infinite; }
  .o1 { width:480px;height:480px;background:#7c5cff;top:-120px;left:-80px; }
  .o2 { width:420px;height:420px;background:#22d3ee;bottom:-100px;right:-60px;animation-delay:-7s; }
  @keyframes float { 0%,100%{transform:translate(0,0) scale(1);} 33%{transform:translate(40px,-30px) scale(1.1);} 66%{transform:translate(-30px,20px) scale(.95);} }
  .card { position:relative; z-index:1; width:min(380px,90vw); background:rgba(22,22,30,.72); border:1px solid rgba(255,255,255,.1);
    border-radius:18px; padding:36px 32px; box-shadow:0 8px 40px rgba(0,0,0,.4); backdrop-filter:blur(20px); }
  .logo { width:44px;height:44px;background:linear-gradient(135deg,var(--brand),var(--accent));border-radius:12px;
    display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:20px;margin-bottom:18px;
    box-shadow:0 4px 16px rgba(124,92,255,.35); }
  h1 { font-size:20px;font-weight:800;letter-spacing:-.4px;margin-bottom:6px; }
  p.sub { font-size:13px;color:var(--muted);margin-bottom:24px; }
  .lock { font-size:13px;color:var(--brand);font-weight:600;letter-spacing:.5px;margin-bottom:10px;display:flex;gap:6px;align-items:center; }
  input { width:100%;padding:14px 16px;background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);border-radius:12px;
    color:var(--ink);font-size:15px;font-family:inherit;outline:none;transition:border-color .25s,box-shadow .25s; }
  input:focus { border-color:var(--brand);box-shadow:0 0 0 4px rgba(124,92,255,.12); }
  input::placeholder { color:#5a5a66; }
  button { width:100%;margin-top:14px;padding:14px;border:none;border-radius:12px;cursor:pointer;font-size:15px;font-weight:700;
    color:#fff;background:linear-gradient(135deg,var(--brand),#9d7bff);font-family:inherit;
    box-shadow:0 6px 24px rgba(124,92,255,.35);transition:transform .12s,box-shadow .25s; }
  button:hover { transform:translateY(-2px);box-shadow:0 10px 32px rgba(124,92,255,.45); }
  button:active { transform:translateY(0) scale(.98); }
  button:disabled { opacity:.6;cursor:not-allowed;transform:none; }
  .msg { font-size:12.5px;margin-top:12px;min-height:18px;text-align:center; }
  .msg.err { color:#fb7185; } .msg.ok { color:#34d399; }
</style>
</head>
<body>
  <div class="bg-orbs"><span class="o1"></span><span class="o2"></span></div>
  <div class="card">
    <div class="logo">AI</div>
    <div class="lock">🔒 受密码保护</div>
    <h1>进入控制台</h1>
    <p class="sub">请输入访问密码以继续使用</p>
    <input id="pw" type="password" placeholder="访问密码" autocomplete="current-password" autofocus />
    <button id="go" onclick="login()">验证并进入</button>
    <div class="msg" id="msg"></div>
  </div>
<script>
  const pw = document.getElementById('pw');
  const btn = document.getElementById('go');
  const msg = document.getElementById('msg');
  pw.addEventListener('keydown', e => { if (e.key === 'Enter') login(); });
  async function login() {
    const v = pw.value;
    if (!v) { msg.textContent = '请输入密码'; msg.className = 'msg err'; return; }
    btn.disabled = true; btn.textContent = '验证中…';
    try {
      const r = await fetch('/api/login', { method:'POST', headers:{'Content-Type':'application/json'},
        credentials:'same-origin', body: JSON.stringify({ password: v }) });
      if (r.ok) { msg.textContent = '验证成功，进入中…'; msg.className = 'msg ok'; setTimeout(() => location.href = '/', 300); }
      else { const d = await r.json().catch(()=>({})); msg.textContent = d.detail || '密码错误'; msg.className = 'msg err';
        btn.disabled = false; btn.textContent = '验证并进入'; }
    } catch (e) { msg.textContent = '网络错误'; msg.className = 'msg err'; btn.disabled = false; btn.textContent = '验证并进入'; }
  }
</script>
</body>
</html>"""

# ===== 鉴权中间件：网关整站 =====
_PUBLIC_PATHS = {"/api/health", "/api/login", "/api/logout", "/login",
                 "/favicon.ico"}


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    # 未设置密码则完全开放
    if not APP_PASSWORD:
        return await call_next(request)
    path = request.url.path
    if path in _PUBLIC_PATHS:
        return await call_next(request)
    token = request.cookies.get(_AUTH_COOKIE)
    # 必须存在且与当前有效令牌一致（令牌初始为 None，避免 None==None 误判通过）
    authed = bool(token) and token == _VALID_TOKEN["value"]
    if path.startswith("/api/"):
        if not authed:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
    # 页面请求：未登录展示登录页
    if not authed:
        return HTMLResponse(LOGIN_HTML)
    return await call_next(request)


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


def _run_command(cmd: list[str], log_path: Path, cwd: Path | None = None) -> int:
    with open(log_path, "a", encoding="utf-8") as log:
        log.write("\n$ " + " ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=str(cwd or REPO_ROOT), stdout=log, stderr=subprocess.STDOUT)
        return proc.returncode


def _try_render_video(account: str, log_path: Path) -> None:
    """可选：用 Remotion 把画面渲染成 mp4（需要 node/npx 且 Remotion 工程已就绪）。"""
    if not RENDER_VIDEO:
        return
    proj = REPO_ROOT / "video" / "remotion-app"
    if not (proj / "package.json").exists():
        return
    try:
        out = WORKSPACE_DIR / account / "video_gen" / "output.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        # 在工程目录内运行渲染，entry-point 用相对路径，避免仓库根目录找不到 src/index.ts
        render_cmd = [NODE, "node_modules/.bin/remotion", "render", "src/index.ts",
                      "AIConsole", "--output", str(out)]
        # 若 video_gen 步骤已把脚本拆成场景数据，则作为 props 注入
        scenes_json = proj / "scenes.generated.json"
        if scenes_json.exists():
            render_cmd += ["--props", str(scenes_json)]
        _run_command(render_cmd, log_path, cwd=proj)
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
        if topic:
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


@app.post("/api/login")
def login(body: dict):
    """校验访问密码，成功下发会话 Cookie。"""
    if not APP_PASSWORD:
        return {"ok": True, "open": True}
    pw = body.get("password", "")
    if pw != APP_PASSWORD:
        raise HTTPException(401, "密码错误")
    token = secrets.token_hex(16)
    _VALID_TOKEN["value"] = token
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        _AUTH_COOKIE, token,
        httponly=True, path="/",
        max_age=60 * 60 * 24 * 30,
        samesite="lax",
    )
    return resp


@app.post("/api/logout")
def logout():
    """注销当前会话。"""
    _VALID_TOKEN["value"] = None
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(_AUTH_COOKIE, path="/")
    return resp


@app.get("/api/accounts")
def list_accounts():
    """列出 config/accounts/ 下所有账号配置，前端动态加载。"""
    acc_dir = REPO_ROOT / "config" / "accounts"
    out = []
    if acc_dir.exists():
        for p in sorted(acc_dir.glob("*.json")):
            try:
                cfg = json.loads(p.read_text(encoding="utf-8"))
                acc = cfg.get("account", {})
                out.append({
                    "id": p.stem,
                    "platform": acc.get("platform", ""),
                    "niche": acc.get("niche", ""),
                    "language": acc.get("language", "zh"),
                })
            except Exception:
                pass
    return out


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
        return [{"job_id": j["job_id"], "account": j["account"], "topic": j.get("topic") or "",
                 "status": j["status"],
                 "finished_at": j.get("finished_at")}
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
