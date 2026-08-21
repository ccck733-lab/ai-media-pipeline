"""步骤4：自动生成视频画面（Remotion / Hyperframes 接入）。

检测到 Remotion 工程 -> 解析 script.md 生成场景数据并提示构建命令；
否则在 video/remotion-app 生成可运行的脚手架。
"""
import json
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
    "src/Compositions.tsx": """import { AbsoluteFill, useCurrentFrame, spring } from "remotion";
import { Composition } from "remotion";

type Scene = { text: string; color: string; bg: string };

const DEFAULT_SCENES: Scene[] = [
  { text: "钩子：反常识开场", color: "#0b0b0b", bg: "#fff7e6" },
  { text: "一个具体例子", color: "#111", bg: "#e6f7ff" },
  { text: "可操作结论", color: "#111", bg: "#e6ffe6" },
  { text: "评论区告诉我下一个问题", color: "#fff", bg: "#111" },
];

const SCENE_LEN = 45;
const MAX_SCENES = 6;

export const AIConsole: React.FC<{ scenes?: Scene[] }> = ({ scenes }) => {
  const list = scenes && scenes.length ? scenes.slice(0, MAX_SCENES) : DEFAULT_SCENES;
  const frame = useCurrentFrame();
  const idx = Math.min(Math.floor(frame / SCENE_LEN), list.length - 1);
  const s = list[idx];
  const progress = spring({ frame: frame % SCENE_LEN, fps: 30, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ background: s.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h1 style={{ color: s.color, opacity: progress, fontSize: 64, textAlign: "center", lineHeight: 1.2 }}>{s.text}</h1>
    </AbsoluteFill>
  );
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="AIConsole"
    component={AIConsole}
    durationInFrames={MAX_SCENES * SCENE_LEN}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ scenes: DEFAULT_SCENES }}
  />
);
""",
    "VIDEO_GEN_SPEC.md": """# 视频画面生成规格

- 工程: Remotion（react-jsx）
- 画幅: 1080x1920（竖屏，适配抖音/视频号）
- 帧率: 30fps
- 时长: 由 scenes 数 × 每屏帧数决定
- 素材: 把脚本关键句写入 src/Compositions.tsx 的 scenes 数组驱动画面

## 运行
```
cd video/remotion-app
npm install
npm run dev        # 预览
npm run build      # 渲染成片 -> out/video.mp4
```
成片输出到 out/ 后，交给 subtitle_dub 做字幕配音。
""",
}


def _build_scenes_from_script(account: str) -> list[str]:
    """从 script_writing/script.md 提取成稿关键句，作为 Remotion 画面场景。"""
    script = step_dir(account, "script_writing") / "script.md"
    if not script.exists():
        return []
    text = script.read_text(encoding="utf-8", errors="ignore")
    # 只取「脚本模板」区块，排除顶部风格复刻参考元数据
    if "# 脚本模板" in text:
        text = text.split("# 脚本模板", 1)[1]
    # 模板结构词/说明句，不是成稿内容，跳过
    skip_kw = ("占位符", "模板", "先说", "再给", "语气严格", "人设", "节奏", "长度",
               "口吻", "禁用", "样本", "结构", "钩子（", "一个具体例子", "给出可操作",
               "互动引导", "注意")
    real = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        # 跳过标题/注释/引用/分隔线/列表项/模板标题残留（如「（知识科普）」）
        if s.startswith(("#", "<!--", ">", "---", "-", "（")):
            continue
        # 跳过 numbered 结构步骤，如「1. 钩子（反常识/痛点）」
        if s[0].isdigit() and s[1:2] in (".", "、"):
            continue
        if any(k in s for k in skip_kw):
            continue
        if len(s) < 6:
            continue
        real.append(s)
    # 去重保序
    seen: set[str] = set()
    real = [x for x in real if not (x in seen or seen.add(x))]
    return real[:6]


# 真实句子不足时混入的默认画面，保证视频至少有 4 屏内容
_FALLBACK_SCENES = [
    "钩子：反常识开场",
    "一个具体例子",
    "可操作结论",
    "评论区告诉我下一个问题",
]


def _write_scenes_json(proj: str, scenes: list[str]) -> Path | None:
    palette = [
        {"color": "#0b0b0b", "bg": "#fff7e6"},
        {"color": "#111", "bg": "#e6f7ff"},
        {"color": "#111", "bg": "#e6ffe6"},
        {"color": "#fff", "bg": "#111"},
        {"color": "#111", "bg": "#ffe6f0"},
        {"color": "#111", "bg": "#f0e6ff"},
    ]
    texts = (scenes + _FALLBACK_SCENES)[:6]
    data = {"scenes": [{"text": t, **palette[i % len(palette)]} for i, t in enumerate(texts)]}
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
        if scenes:
            p = _write_scenes_json(proj, scenes)
            notes.append(f"已从脚本生成 {len(scenes)} 个画面场景 -> {p.name}")
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
