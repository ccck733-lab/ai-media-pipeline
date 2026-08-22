"""步骤4：自动生成视频画面（Remotion / Hyperframes 接入）。

检测到 Remotion 工程 -> 解析 script.md 生成场景数据并提示构建命令；
否则在 video/remotion-app 生成可运行的脚手架。
"""
import json
import re
import shutil
from pathlib import Path

from pipeline.steps import step_dir, save, external_exists, ROOT


SCAFFOLD_FILES = {
    "package.json": """{
  "name": "remotion-app",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "remotion studio",
    "build": "remotion render <CompName> out/video.mp4",
    "upgrade": "remotion upgrade"
  },
  "dependencies": {
    "remotion": "latest",
    "@remotion/cli": "latest",
    "react": "latest",
    "react-dom": "latest"
  }
}
""",
    "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2018",
    "module": "ESNext",
    "jsx": "react-jsx",
    "moduleResolution": "node",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "strict": true
  },
  "include": ["src"]
}
""",
    "remotion.config.ts": """import { Config } from "@remotion/cli/config";
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
""",
    "src/index.ts": """import { registerRoot } from "remotion";
import { RemotionRoot } from "./Compositions";

registerRoot(RemotionRoot);
""",
    "src/Compositions.tsx": """
    import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame } from "remotion";
    import { Composition } from "remotion";

    type Scene = {
      title?: string;
      body: string;
      color: string;
      bg: string;
      image?: string;
      audio?: string;
      frames?: number;
    };

    const FALLBACK_FRAMES = 60;
    const FPS = 30;
    const TRANSITION = 14; // 场景间转场重叠帧数

    const DEFAULT_SCENES: Scene[] = [
      { title: "钩子", body: "核心观点", color: "#ff7a59", bg: "#0a0a12", frames: FALLBACK_FRAMES },
      { title: "要点", body: "关键洞察", color: "#5b8cff", bg: "#0a0a12", frames: FALLBACK_FRAMES },
      { title: "要点", body: "行动清单", color: "#46d6a0", bg: "#0a0a12", frames: FALLBACK_FRAMES },
      { title: "互动", body: "下期想听什么？评论区告诉我", color: "#ffd166", bg: "#0a0a12", frames: FALLBACK_FRAMES },
    ];

    const sumFrames = (list: Scene[]) =>
      Math.max(list.reduce((a, s) => a + (s.frames || FALLBACK_FRAMES), 0), FALLBACK_FRAMES);

    /** 全程持续运动的动态背景：不随场景切换重置，让转场时画面连续。 */
    const MotionBackdrop: React.FC = () => {
      const f = useCurrentFrame();
      const blobs = [
        { c: "#3a2a6b", x: 30, y: 28, s: 560, ax: 9, ay: 6, sp: 0.010 },
        { c: "#143a52", x: 72, y: 42, s: 500, ax: 11, ay: 7, sp: 0.013 },
        { c: "#4a1f3a", x: 50, y: 74, s: 620, ax: 9, ay: 8, sp: 0.008 },
        { c: "#1f3a2a", x: 22, y: 64, s: 440, ax: 7, ay: 5, sp: 0.015 },
      ];
      return (
        <AbsoluteFill style={{ background: "#08080f" }}>
          {blobs.map((b, i) => {
            const x = b.x + Math.sin(f * b.sp + i * 1.7) * b.ax;
            const y = b.y + Math.cos(f * b.sp * 1.3 + i) * b.ay;
            const sc = 1 + Math.sin(f * 0.02 + i) * 0.12;
            return (
              <div key={i} style={{
                position: "absolute", left: `${x}%`, top: `${y}%`,
                width: b.s, height: b.s, borderRadius: "50%",
                background: b.c, opacity: 0.5, filter: "blur(70px)",
                transform: `translate(-50%,-50%) scale(${sc})`,
              }} />
            );
          })}
          {/* 缓慢旋转的细网格，强化镜头运动感 */}
          <div style={{
            position: "absolute", inset: "-20%",
            backgroundImage: "linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px)",
            backgroundSize: "64px 64px",
            transform: `rotate(${f * 0.05}deg)`,
            opacity: 0.6,
          }} />
          <div style={{ position: "absolute", inset: 0, background: "radial-gradient(circle at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)" }} />
        </AbsoluteFill>
      );
    };

    /** 单个场景：透明浮层 + 持续运镜 + 入场/出场转场 + 底部字幕。 */
    const SceneCard: React.FC<{
      scene: Scene;
      index: number;
      total: number;
      totalFrames: number;
    }> = ({ scene: s, index, total, totalFrames }) => {
      const f = useCurrentFrame();

      // 入场（前 TRANSITION 帧）：缩放推进 + 淡入
      const enter = interpolate(f, [0, TRANSITION], [0, 1], { extrapolateRight: "clamp" });
      const enterScale = interpolate(f, [0, TRANSITION], [1.16, 1], { extrapolateRight: "clamp" });
      // 出场（最后 TRANSITION 帧）：放大 + 淡出
      const exit = interpolate(f, [totalFrames - TRANSITION, totalFrames], [1, 0], { extrapolateLeft: "clamp" });
      const exitScale = interpolate(f, [totalFrames - TRANSITION, totalFrames], [1, 1.14], { extrapolateLeft: "clamp" });
      const opacity = Math.min(enter, exit);
      const scale = enterScale * exitScale;

      // 文字浮层：延迟 4 帧上浮淡入
      const tIn = spring({ frame: f - 4, fps: FPS, config: { damping: 18 } });
      const txtY = interpolate(tIn, [0, 1], [46, 0]);
      const txtOp = tIn;

      // 场景色系光晕，持续轻微浮动
      const fa = Math.sin(f * 0.06) * 22;
      const fb = Math.cos(f * 0.05) * 16;
      const pulse = 1 + Math.sin(f * 0.08) * 0.05;

      return (
        <AbsoluteFill style={{ opacity, transform: `scale(${scale})` }}>
          {/* 场景主色光晕（持续浮动） */}
          <div style={{
            position: "absolute", top: "20%", left: "50%",
            width: 360, height: 360, borderRadius: "50%",
            background: s.color, opacity: 0.16, filter: "blur(60px)",
            transform: `translate(-50%, calc(-50% + ${fa}px)) scale(${pulse})`,
          }} />
          <div style={{
            position: "absolute", bottom: "16%", right: "8%",
            width: 200, height: 200, borderRadius: "50%",
            background: s.color, opacity: 0.12, filter: "blur(50px)",
            transform: `translateY(${fb}px) scale(${pulse * 0.9})`,
          }} />

          {/* 标题 + 正文（底部浮层） */}
          <div style={{
            position: "absolute", left: 0, right: 0, bottom: "15%",
            padding: "0 9%", display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
          }}>
            {s.title ? (
              <div style={{
                display: "flex", alignItems: "center", gap: 12, marginBottom: 18,
                transform: `translateY(${txtY}px)`, opacity: txtOp * 0.9,
              }}>
                <div style={{ width: 5, height: 30, borderRadius: 3, background: s.color }} />
                <span style={{ color: s.color, fontSize: 30, fontWeight: 600, letterSpacing: 3 }}>{s.title}</span>
              </div>
            ) : null}
            <h1 style={{
              color: "#fff", opacity: txtOp, fontSize: 54, textAlign: "center",
              lineHeight: 1.35, margin: 0, maxWidth: "92%", fontWeight: 800,
              transform: `translateY(${txtY}px)`,
              textShadow: "0 4px 24px rgba(0,0,0,0.5)",
            }}>{s.body}</h1>
          </div>

          {/* 音频波形装饰（随帧跳动，强化"有声视频"观感） */}
          <div style={{ position: "absolute", bottom: 44, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 4, opacity: 0.55 }}>
            {Array.from({ length: 28 }).map((_, i) => {
              const h = 6 + Math.abs(Math.sin(f * 0.3 + i * 0.5)) * 26;
              return <div key={i} style={{ width: 3, height: h, borderRadius: 2, background: s.color, opacity: 0.75 }} />;
            })}
          </div>

          {/* 顶部进度条 */}
          <div style={{ position: "absolute", top: 64, left: 64, right: 64, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.12)", overflow: "hidden" }}>
            <div style={{ width: `${((index + 1) / total) * 100}%`, height: "100%", background: s.color, borderRadius: 2 }} />
          </div>
          {/* 场景计数 */}
          <div style={{ position: "absolute", top: 56, right: 64, color: "rgba(255,255,255,0.5)", fontSize: 20, fontWeight: 700 }}>{String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}</div>
        </AbsoluteFill>
      );
    };

    export const AIConsole: React.FC<{ scenes?: Scene[] }> = ({ scenes }) => {
      const list = scenes && scenes.length ? scenes : DEFAULT_SCENES;
      let cursor = 0;
      return (
        <AbsoluteFill style={{ background: "#000" }}>
          <MotionBackdrop />
          {list.map((s, i) => {
            const dur = s.frames || FALLBACK_FRAMES;
            const start = i === 0 ? 0 : cursor - TRANSITION;
            const seqDur = i === 0 ? dur : dur + TRANSITION;
            cursor += dur;
            return (
              <Sequence key={i} from={start} durationInFrames={seqDur}>
                <SceneCard scene={s} index={i} total={list.length} totalFrames={seqDur} />
                {s.audio ? <Audio src={staticFile(s.audio)} /> : null}
              </Sequence>
            );
          })}
        </AbsoluteFill>
      );
    };

    export const RemotionRoot: React.FC = () => (
      <Composition
        id="AIConsole"
        component={AIConsole}
        durationInFrames={300}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ scenes: DEFAULT_SCENES }}
        calculateMetadata={({ props }) => ({
          durationInFrames: sumFrames((props as { scenes?: Scene[] }).scenes || DEFAULT_SCENES),
        })}
      />
    );
    """,
    "VIDEO_GEN_SPEC.md": """# 视频画面生成规格

- 工程: Remotion（react-jsx）
- 画幅: 1080x1920（竖屏，适配抖音/视频号）
- 帧率: 30fps
- 时长: 由各屏 frames 之和决定（跟随配音时长）
- 音频: 每屏 <Audio> 从 public/audio/seg_N.wav 读取（subtitle_dub 产出）
- 素材: scenes.generated.json 驱动每屏 title/body/audio/frames
- 动态效果: 渐变背景旋转、浮动装饰圆、标题滑入、正文上浮、动态下划线、进度条、场景计数、出场淡出

## 运行
```
cd video/remotion-app
npm install
npm run dev        # 预览
npm run build      # 渲染成片 -> out/video.mp4
```
""",
}

SCENE_LEN = 45  # 无音频时长时每屏默认帧数（30fps → 1.5s）


def _clip(s: str, n: int = 42) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "…"


def _build_scenes_from_script(account: str) -> list[dict]:
    """解析 script_writing/script.md 的 ## 章节，提取每屏标题+正文，驱动视频画面。"""
    script = step_dir(account, "script_writing") / "script.md"
    if not script.exists():
        return []
    text = script.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # 去掉风格注释块
    # 只取真正的脚本区（跳过顶部「风格复刻参考」块）
    m = re.search(r"\n#\s*脚本（", text)
    if m:
        text = text[m.start():]
    parts = re.split(r"\n##\s+", text)
    scenes: list[dict] = []
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
                    scenes.append({"title": f"要点{i}", "body": _clip(mm.group(1))})
        else:
            body = _clip(" ".join(body_lines))
            if body:
                scenes.append({"title": title, "body": body})
    # 屏数上限 6：超了先丢「痛点」段（钩子已含冲突），保钩子/要点/结论/互动
    if len(scenes) > 6:
        scenes = [s for s in scenes if s.get("title") != "痛点"]
    return scenes[:6]


# 真实场景不足时混入的默认画面，保证视频至少有 4 屏内容。
_DEFAULT_SCENES = [
    {"title": "钩子", "body": "核心观点"},
    {"title": "要点", "body": "关键洞察"},
    {"title": "要点", "body": "行动清单"},
    {"title": "互动", "body": "下期想听什么？评论区告诉我"},
]


def _load_segments(account: str) -> list[dict] | None:
    """读取 subtitle_dub/segments.json（每屏 text/audio/duration），供音画同步。"""
    seg = step_dir(account, "subtitle_dub") / "segments.json"
    if not seg.exists():
        return None
    try:
        return json.loads(seg.read_text(encoding="utf-8")).get("segments", [])
    except Exception:
        return None


def _write_scenes_json(proj: str, scenes: list[dict], segments: list[dict] | None = None) -> Path | None:
    palette = [
        {"color": "#0b0b0b", "bg": "#fff7e6"},
        {"color": "#111", "bg": "#e6f7ff"},
        {"color": "#111", "bg": "#e6ffe6"},
        {"color": "#fff", "bg": "#111"},
        {"color": "#111", "bg": "#ffe6f0"},
        {"color": "#111", "bg": "#f0e6ff"},
    ]
    if not scenes:
        scenes = [dict(s) for s in _DEFAULT_SCENES]
    scenes = (scenes + [{"title": "互动", "body": "下期想听什么？评论区告诉我"}])[:6]
    seg_map = {i: s for i, s in enumerate(segments or [])}
    # 把配音 wav 复制到工程 public/audio，供 Remotion <Audio> 读取
    pub = ROOT / proj / "public" / "audio"
    result = []
    for i, sc in enumerate(scenes):
        seg = seg_map.get(i, {})
        audio_abs = seg.get("audio", "")
        audio_rel = ""
        if audio_abs and Path(audio_abs).exists():
            pub.mkdir(parents=True, exist_ok=True)
            dst = pub / f"seg_{i}.wav"
            shutil.copy(audio_abs, dst)
            audio_rel = f"audio/seg_{i}.wav"
        dur = seg.get("duration") or 0
        frames = max(int(dur * 30) + 6, 30) if dur else SCENE_LEN
        result.append({**sc, **palette[i % len(palette)],
                       "audio": audio_rel, "frames": frames})
    data = {"scenes": result}
    out = ROOT / proj / "scenes.generated.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def run(cfg: dict, ctx: dict) -> dict:
    vg = cfg.get("video_gen", {})
    work = step_dir(ctx["account_name"], "video_gen")
    engine = vg.get("engine", "remotion")
    proj = vg.get("remotion_project", "")
    notes = []

    if external_exists(proj):
        notes.append(f"检测到 {engine} 工程: {proj}")
        scenes = _build_scenes_from_script(ctx["account_name"])
        segments = _load_segments(ctx["account_name"])
        if scenes:
            p = _write_scenes_json(proj, scenes, segments)
            tag = f"{len(segments)} 段语音" if segments else "无语音"
            notes.append(f"已从脚本生成 {len(scenes)} 个画面场景（{tag}）-> {p.name}")
        else:
            notes.append("未找到 script.md 或关键句，将使用默认示例画面")
        notes.append(f"构建: cd {proj} && npm run build（或 npm run dev 预览）")
        return {"status": "待构建", "notes": notes}

    # 生成脚手架
    app = ROOT / "video" / "remotion-app"
    if app.exists():
        notes.append(f"已存在脚手架: {app}（跳过生成）")
    else:
        for rel, content in SCAFFOLD_FILES.items():
            save(app / rel, content)
        notes.append(f"已生成 {engine} 脚手架 -> {app}")
        notes.append("运行: cd video/remotion-app && npm install && npm run dev")
    save(work / "VIDEO_GEN_SPEC.md", SCAFFOLD_FILES["VIDEO_GEN_SPEC.md"])
    return {"status": "已生成视频脚手架", "notes": notes}
