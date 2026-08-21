"""步骤3：字幕 / 配音（VoxCPM 在线 TTS）。

把 script.md 的每个章节正文用 VoxCPM 合成语音，输出 segments.json：
每屏 {title, text, audio(绝对路径), duration}，供 video_gen 做音画同步。

VoxCPM：声音克隆型 TTS（面壁开源），在线 demo 默认音色即可用，无需参考音频。
失败时该屏降级为静音占位，不阻塞渲染。
"""
import json
import re
import subprocess
import uuid
from pathlib import Path

from pipeline.steps import step_dir, save, ROOT

VOXCPM_BASE = "https://voxcpm.modelbest.cn"
VOXCPM_API = VOXCPM_BASE + "/gradio_api"
_DEFAULT_DUR = 3.5  # TTS 失败时的占位时长（秒）


def _curl(*args: str, timeout: int = 30) -> str:
    """通过 curl 发请求（--noproxy 绕开本机代理，确保直达 voxcpm）。"""
    r = subprocess.run(
        ["curl", "--noproxy", "*", "-s", "--max-time", str(timeout),
         "-H", "User-Agent: Mozilla/5.0", *args],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    return r.stdout


def voxcpm_tts(text: str, out_wav: Path, timeout: int = 150) -> Path | None:
    """调 VoxCPM generate 合成一段语音，下载到 out_wav。失败返回 None。"""
    # generate inputs 顺序：[target, control, ref_audio, show_prompt, prompt, cfg, normalize, denoise, dit_steps, user_id]
    payload = {"data": [text, "", None, False, "", 2.0, False, False, 10,
                        "wb_" + uuid.uuid4().hex[:12]]}
    r = _curl("-X", "POST", "-H", "Content-Type: application/json",
              "-d", json.dumps(payload, ensure_ascii=False),
              VOXCPM_API + "/call/generate", timeout=40)
    try:
        eid = json.loads(r).get("event_id")
    except Exception:
        eid = None
    if not eid:
        return None

    # SSE：等到 complete 事件，取 data 数组
    stream = _curl("-N", VOXCPM_API + f"/call/generate/{eid}", timeout=timeout)
    audio_url = None
    for line in stream.splitlines():
        if line.startswith("data:") and line[5:].strip().startswith("["):
            m = re.search(r"\[.*\]", line, re.S)
            if m:
                try:
                    out = json.loads(m.group(0))
                    a = out[0] if out else None
                    if isinstance(a, dict):
                        audio_url = a.get("url")
                except Exception:
                    pass
            break
    if not audio_url:
        return None
    if audio_url.startswith("/"):
        audio_url = VOXCPM_BASE + audio_url
    _curl("-o", str(out_wav), audio_url, timeout=60)
    if out_wav.exists() and out_wav.stat().st_size > 1000:
        return out_wav
    return None


def _audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return _DEFAULT_DUR


def _build_segments(account: str) -> list[dict]:
    """拆 script.md 章节为每屏 {title, text(完整正文)}，供 TTS。"""
    script = step_dir(account, "script_writing") / "script.md"
    if not script.exists():
        return []
    text = script.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # 去风格注释块
    # 只取真正的脚本区（跳过顶部「风格复刻参考」）
    m = re.search(r"\n#\s*脚本（", text)
    if m:
        text = text[m.start():]
    parts = re.split(r"\n##\s+", text)
    segs: list[dict] = []
    for part in parts[1:]:
        lines = [l.strip() for l in part.splitlines() if l.strip()]
        if not lines:
            continue
        title = lines[0].replace("#", "").strip()
        body_lines = [l for l in lines[1:] if l and not l.startswith((">", "---"))]
        if title == "正文":
            for i, l in enumerate(body_lines, 1):
                mm = re.match(r"^\d+[.、)]\s*(.*)", l)
                if mm:
                    segs.append({"title": f"要点{i}", "text": mm.group(1)})
        else:
            full = " ".join(body_lines)
            if full:
                segs.append({"title": title, "text": full})
    if len(segs) > 6:  # 超屏先丢「痛点」段
        segs = [s for s in segs if s.get("title") != "痛点"]
    return segs[:6]


def run(cfg: dict, ctx: dict) -> dict:
    sd = cfg.get("subtitle_dub", {})
    work = step_dir(ctx["account_name"], "subtitle_dub")
    account = ctx["account_name"]
    notes: list[str] = []

    segs = _build_segments(account)
    if not segs:
        save(work / "DO_SUBTITLE_DUB.md",
             "# 配音执行指引\n未找到 script.md 章节或正文为空，跳过 TTS。")
        notes.append("未找到脚本正文，已生成指引（跳过 TTS）。")
        return {"status": "已生成指引", "notes": notes}

    segments: list[dict] = []
    ok = 0
    for i, seg in enumerate(segs):
        wav = work / f"seg_{i}.wav"
        preview = seg["text"][:22].replace("\n", " ")
        notes.append(f"TTS [{seg['title']}] {preview}…")
        got = voxcpm_tts(seg["text"], wav)
        if got:
            dur = _audio_duration(got)
            segments.append({**seg, "audio": str(got), "duration": round(dur, 2)})
            ok += 1
            notes.append(f"  ✓ {dur:.1f}s")
        else:
            segments.append({**seg, "audio": "", "duration": _DEFAULT_DUR})
            notes.append(f"  ✗ 失败，占位 {_DEFAULT_DUR}s")

    seg_path = work / "segments.json"
    save(seg_path, json.dumps({"segments": segments}, ensure_ascii=False, indent=2))
    notes.append(f"VoxCPM 合成 {ok}/{len(segs)} 段 → {seg_path.name}")
    return {"status": "完成" if ok else "失败", "notes": notes}
