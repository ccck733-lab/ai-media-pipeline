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
