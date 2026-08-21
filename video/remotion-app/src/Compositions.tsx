import { AbsoluteFill, Audio, Img, Sequence, spring, staticFile, useCurrentFrame } from "remotion";
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
  const local = useCurrentFrame(); // Sequence 内：相对帧，从 0 开始
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
