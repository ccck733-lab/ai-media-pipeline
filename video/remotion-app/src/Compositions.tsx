import { AbsoluteFill, useCurrentFrame, spring, Img } from "remotion";
import { Composition } from "remotion";

type Scene = { title?: string; body: string; color: string; bg: string; image?: string };

// 默认示例画面（无脚本数据时回退）
const DEFAULT_SCENES: Scene[] = [
  { title: "钩子", body: "核心观点", color: "#0b0b0b", bg: "#fff7e6" },
  { title: "要点", body: "关键洞察", color: "#111", bg: "#e6f7ff" },
  { title: "要点", body: "行动清单", color: "#111", bg: "#e6ffe6" },
  { title: "互动", body: "下期想听什么？评论区告诉我", color: "#fff", bg: "#111" },
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
    <AbsoluteFill style={{ background: s.bg, flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 72 }}>
      {s.image ? <Img src={s.image} style={{ width: "68%", borderRadius: 24, marginBottom: 26 }} /> : null}
      {s.title ? <h3 style={{ color: s.color, opacity: progress * 0.65, fontSize: 32, fontWeight: 600, margin: 0, letterSpacing: 2 }}>{s.title}</h3> : null}
      <h1 style={{ color: s.color, opacity: progress, fontSize: 54, textAlign: "center", lineHeight: 1.25, margin: "12px 0 0", maxWidth: "86%" }}>{s.body}</h1>
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
