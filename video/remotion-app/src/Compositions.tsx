import { AbsoluteFill, useCurrentFrame, spring } from "remotion";

type Scene = { text: string; color: string; bg: string };

// 默认示例画面（无脚本数据时回退）
const DEFAULT_SCENES: Scene[] = [
  { text: "钩子：反常识开场", color: "#0b0b0b", bg: "#fff7e6" },
  { text: "一个具体例子", color: "#111", bg: "#e6f7ff" },
  { text: "可操作结论", color: "#111", bg: "#e6ffe6" },
  { text: "评论区告诉我下一个问题", color: "#fff", bg: "#111" },
];

const SCENE_LEN = 45; // 每屏约 1.5s @30fps
const MAX_SCENES = 6; // 时长上限 6 屏 = 9s

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

import { Composition } from "remotion";
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
