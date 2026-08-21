import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, spring } from "remotion";

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
