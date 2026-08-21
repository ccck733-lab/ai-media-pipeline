import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame } from "remotion";
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

/** Lighten/darken a hex color by amount (-255..255). */
const shade = (hex: string, amt: number): string => {
  const n = parseInt(hex.replace("#", ""), 16);
  const r = Math.max(0, Math.min(255, (n >> 16) + amt));
  const g = Math.max(0, Math.min(255, ((n >> 8) & 0xff) + amt));
  const b = Math.max(0, Math.min(255, (n & 0xff) + amt));
  return "#" + ((r << 16) | (g << 8) | b).toString(16).padStart(6, "0");
};

const SceneCard: React.FC<{
  scene: Scene;
  index: number;
  total: number;
  totalFrames: number;
}> = ({ scene: s, index, total, totalFrames }) => {
  const f = useCurrentFrame();

  // --- Entrance: scale 0.94 → 1.0 ---
  const enter = spring({ frame: f, fps: FPS, config: { damping: 200 } });
  const scale = interpolate(enter, [0, 1], [0.94, 1]);

  // --- Title: slide from left (starts at frame 4) ---
  const ts = spring({ frame: f - 4, fps: FPS, config: { damping: 14 } });
  const titleX = interpolate(ts, [0, 1], [-160, 0]);
  const titleOp = interpolate(ts, [0, 1], [0, 0.75]);

  // --- Body: fade in + slide up (starts at frame 8) ---
  const bs = spring({ frame: f - 8, fps: FPS, config: { damping: 200 } });
  const bodyY = interpolate(bs, [0, 1], [50, 0]);
  const bodyOp = bs;

  // --- Underline: grows after body appears (frame 14) ---
  const ul = spring({ frame: f - 14, fps: FPS, config: { damping: 200 } });
  const ulW = interpolate(ul, [0, 1], [0, 100]);

  // --- Floating decorations ---
  const float1 = Math.sin(f * 0.06) * 25;
  const float2 = Math.cos(f * 0.045) * 18;
  const pulse = 1 + Math.sin(f * 0.09) * 0.04;

  // --- Exit fade (last 8 frames) ---
  const exit = interpolate(f, [totalFrames - 8, totalFrames - 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // --- Background gradient slowly rotates ---
  const angle = 135 + f * 0.4;
  const bg2 = shade(s.bg, -18);
  const bg3 = shade(s.bg, 14);

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(${angle}deg, ${s.bg} 0%, ${bg2} 50%, ${bg3} 100%)`,
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      padding: 72,
      transform: `scale(${scale})`,
      opacity: exit,
    }}>
      {/* Floating circles */}
      <div style={{
        position: "absolute", top: "12%", right: "8%",
        width: 240, height: 240, borderRadius: "50%",
        background: s.color, opacity: 0.04,
        transform: `translateY(${float1}px) scale(${pulse})`,
      }} />
      <div style={{
        position: "absolute", bottom: "18%", left: "6%",
        width: 180, height: 180, borderRadius: "50%",
        background: s.color, opacity: 0.03,
        transform: `translateY(${float2}px) scale(${pulse * 0.92})`,
      }} />
      <div style={{
        position: "absolute", top: "45%", left: "70%",
        width: 100, height: 100, borderRadius: "50%",
        background: s.color, opacity: 0.025,
        transform: `translateY(${float1 * 0.6}px) scale(${pulse * 1.08})`,
      }} />

      {/* Vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.12) 100%)",
        pointerEvents: "none",
      }} />

      {/* Image */}
      {s.image ? (
        <Img src={s.image} style={{
          width: "68%", borderRadius: 24, marginBottom: 30,
          transform: `translateY(${bodyY}px)`,
          opacity: bodyOp,
          boxShadow: "0 8px 40px rgba(0,0,0,0.15)",
        }} />
      ) : null}

      {/* Title with bar */}
      {s.title ? (
        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          marginBottom: 20,
          transform: `translateX(${titleX}px)`,
          opacity: titleOp,
        }}>
          <div style={{
            width: 6, height: 36, borderRadius: 3,
            background: s.color,
          }} />
          <h3 style={{
            color: s.color, fontSize: 34, fontWeight: 700,
            margin: 0, letterSpacing: 4,
          }}>{s.title}</h3>
        </div>
      ) : null}

      {/* Body */}
      <h1 style={{
        color: s.color, opacity: bodyOp,
        fontSize: 56, textAlign: "center", lineHeight: 1.3,
        margin: 0, maxWidth: "88%", fontWeight: 800,
        transform: `translateY(${bodyY}px)`,
        textShadow: "0 2px 12px rgba(0,0,0,0.08)",
      }}>{s.body}</h1>

      {/* Animated underline */}
      <div style={{
        marginTop: 28,
        width: `${ulW}%`, maxWidth: "60%",
        height: 3, borderRadius: 2,
        background: s.color,
        opacity: bodyOp * 0.3,
      }} />

      {/* Progress bar */}
      <div style={{
        position: "absolute", bottom: 90, left: 72, right: 72,
        height: 5, borderRadius: 3,
        background: `${s.color}1a`,
        overflow: "hidden",
      }}>
        <div style={{
          width: `${((index + 1) / total) * 100}%`,
          height: "100%", borderRadius: 3,
          background: s.color,
        }} />
      </div>

      {/* Scene counter */}
      <div style={{
        position: "absolute", top: 72, right: 72,
        color: s.color, opacity: 0.25,
        fontSize: 20, fontWeight: 700,
      }}>{String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}</div>
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
            <SceneCard scene={s} index={i} total={list.length} totalFrames={dur} />
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
