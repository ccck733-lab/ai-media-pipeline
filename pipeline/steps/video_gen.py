"""步骤4：自动生成视频画面（Remotion / Hyperframes 接入）。

检测到 Remotion 工程 -> 提示构建命令；否则在 video/remotion-app 生成可运行的脚手架。
"""
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
    "src/Compositions.tsx": """import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, spring } from "remotion";

// 示例：根据脚本生成的画面骨架。把 script.md 的关键句拆成 scenes 数组即可驱动。
const scenes = [
  { text: "钩子：反常识开场", color: "#0b0b0b", bg: "#fff7e6" },
  { text: "一个具体例子", color: "#111", bg: "#e6f7ff" },
  { text: "可操作结论", color: "#111", bg: "#e6ffe6" },
  { text: "评论区告诉我下一个问题", color: "#fff", bg: "#111" },
];

export const Video: React.FC = () => {
  const frame = useCurrentFrame();
  const sceneLen = 45; // 每屏约 1.5s @30fps
  const idx = Math.min(Math.floor(frame / sceneLen), scenes.length - 1);
  const s = scenes[idx];
  const progress = spring({ frame: frame % sceneLen, fps: 30, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ background: s.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <h1 style={{ color: s.color, opacity: progress, fontSize: 64, textAlign: "center" }}>{s.text}</h1>
    </AbsoluteFill>
  );
};

import { Composition } from "remotion";
export const RemotionRoot: React.FC = () => (
  <Composition id="Video" component={Video} durationInFrames={scenes.length * 45} fps={30} width={1080} height={1920} />
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


def run(cfg: dict, ctx: dict) -> dict:
    vg = cfg.get("video_gen", {})
    work = step_dir(ctx["account_name"], "video_gen")
    engine = vg.get("engine", "remotion")
    proj = vg.get("remotion_project", "")
    notes = []

    if external_exists(proj):
        notes.append(f"检测到 {engine} 工程: {proj}")
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
