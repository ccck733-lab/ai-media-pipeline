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
    "src/Compositions.tsx": """import { AbsoluteFill, Audio, Img, Sequence, spring, staticFile, useCurrentFrame } from "remotion";
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

const FALLBACK_FRAMES = 45;
const FPS = 30;

const DEFAULT_SCENES: Scene[] = [
  { title: "钩子", body: "核心观点", color: "#0b0b0b", bg: "#fff7e6", frames: FALLBACK_FRAMES },
  { title: "要点", body: "关键洞察", color: "#111", bg: "#e6f7ff", frames: FALLBACK_FRAMES },
  { title: "要点", body: "行动清单", color: "#111", bg: "#e6ffe6", frames: FALLBACK_FRAMES },
  { title: "互动", body: "下期想听什么？评论区告诉我", color: "#fff", bg: "#111", frames: FALLBACK_FRAMES },
];

const sumFrames = (list: Scene[]) =>
  Math.max(list.reduce((a, s) => a + (s.frames || FALLBACK_FRAMES), 0), FALLBACK_FRAMES);

const SceneCard: React.FC<{ scene: Scene }> = ({ scene: s }) => {
  const local = useCurrentFrame();
  const progress = spring({ frame: local, fps: FPS, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ background: s.bg, flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 72 }}>
      {s.image ? <Img src={s.image} style={{ width: "68%", borderRadius: 24, marginBottom: 26 }} /> : null}
      {s.title ? <h3 style={{ color: s.color, opacity: progress * 0.65, fontSize: 32, fontWeight: 600, margin: 0, letterSpacing: 2 }}>{s.title}</h3> : null}
      <h1 style={{ color: s.color, opacity: progress, fontSize: 54, textAlign: "center", lineHeight: 1.25, margin: "12px 0 0", maxWidth: "86%" }}>{s.body}</h1>
    </AbsoluteFill>
  );
};

export const AIConsole: React.FC<{ scenes?: Scene[] }> = ({ scenes }) => {
  const list = scenes && scenes.length ? scenes : DEFAULT_SCENES;
  let cursor = 0;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {list.map((s, i) => {
        const dur = s.frames || FALLBACK_FRAMES;
        const start = cursor;
        cursor += dur;
        return (
          <Sequence key={i} from={start} durationInFrames={dur}>
            <SceneCard scene={s} />
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
