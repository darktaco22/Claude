// MEME ROYALE: a 20 s vertical spot for the Solana dApp Store launch, playable on Seeker.
// Footage is the real game, rendered by its own engine; the 3D characters are the game's own models.
import { AbsoluteFill, Audio, Composition, Img, Mix, Sequence, Video, interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig } from "raea";
import { Bloom, ImagePlane, Model, ToneMapping } from "raea/3d";
import { Camera3d } from "raea/camera";
import { AmbientLight, DirectionalLight, PointLight } from "raea/light";
import { Cylinder, Mesh3d } from "raea/mesh";
import { StandardMaterial } from "raea/pbr";
import { Transform } from "raea/transform";

const W = 720, H = 1280;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const GOLD = "#FFC52E", LAV = "#F1E8FF", INK = "#1A0846";
const FONT = `@font-face { font-family: "Lilita One"; src: url("${staticFile("lilita.ttf")}"); }`;
// the game's own lettering: a thick dark-purple edge and a drop under it
const edge = `0 6px 0 ${INK}, 3px 3px 0 ${INK}, -3px 3px 0 ${INK}, 3px -3px 0 ${INK}, -3px -3px 0 ${INK}, 0 0 18px rgba(0,0,0,0.5)`;

function Word({ text, size, color = GOLD, y, delay = 0 }: { text: string; size: number; color?: string; y: number; delay?: number }) {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const s = spring({ frame: f - delay, fps, config: { damping: 11, stiffness: 180 } });
  return (
    <div style={{ position: "absolute", left: 40, right: 93, top: y, textAlign: "center", fontFamily: "Lilita One", fontSize: size, lineHeight: 1.0,
      color, textShadow: edge, transform: `scale(${s})`, opacity: f < delay ? 0 : 1 }}>{text}</div>
  );
}

// a wide engine shot, cropped to the vertical frame, pushing in a little
function Shot({ from, len, pos = "50% 50%", children }: { from: number; len: number; pos?: string; children?: any }) {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, len], [1.08, 1.18], clamp);
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <Video src={staticFile("cinematic.mp4")} startFrom={from} endAt={from + len} muted
        style={{ width: W, height: H, objectFit: "cover", objectPosition: pos, transform: `scale(${z})` }} />
      {children}
    </AbsoluteFill>
  );
}

function Space({ children }: { children?: any }) {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "#08031A", overflow: "hidden" }}>
      <Img src={staticFile("space.png")} style={{ position: "absolute", left: -20, top: -20, width: W + 40, height: H + 40, transform: `translate(${interpolate(f, [0, 200], [0, -18], clamp)}px, 0)` }} />
      {children}
    </AbsoluteFill>
  );
}

// the game's characters in space: PEPE, GIGA and MOO DENG, playing their own clips
function Heroes() {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const a = interpolate(f, [0, 120], [-0.55, 0.25], clamp);
  const cam = Transform.fromXyz(Math.sin(a) * 6.4, 1.6, Math.cos(a) * 6.4).lookingAt([0, 1.2, 0]);
  const rise = (d: number) => interpolate(spring({ frame: f - d, fps, config: { damping: 12 } }), [0, 1], [-2.2, 0]);
  return (
    <AbsoluteFill style={{ background: "#08031A" }}>
        <Camera3d transform={cam} projection={{ Perspective: { fov: (44 * Math.PI) / 180 } }} />
        <ToneMapping mode="tony" exposure={0.2} />
        <Bloom intensity={0.5} threshold={0.9} />
        <AmbientLight brightness={320} color="#B9A0FF" />
        <DirectionalLight transform={Transform.fromXyz(3, 7, 5).lookingAt([0, 0, 0])} illuminance={10500} shadow_maps_enabled />
        <PointLight transform={Transform.fromXyz(-3, 2.5, -2)} intensity={900000} color="#9B4DFF" range={20} />
        <PointLight transform={Transform.fromXyz(3, 2.5, -2)} intensity={700000} color={GOLD} range={20} />
        <Mesh3d name="stage" transform={Transform.fromXyz(0, -0.12, 0)}>
          <Cylinder radius={2.6} half_height={0.12} />
          <StandardMaterial base_color="#3A1690" perceptual_roughness={0.5} />
        </Mesh3d>
        <Mesh3d name="rim" transform={Transform.fromXyz(0, -0.14, 0)}>
          <Cylinder radius={2.72} half_height={0.1} />
          <StandardMaterial base_color="#FFB423" metallic={0.9} perceptual_roughness={0.25} emissive="#5A3A00" />
        </Mesh3d>
        <Model src={staticFile("giga.glb")} animation="win" position={[-1.3, rise(0), -0.2]} rotation={[0, 0.4, 0]} />
        <Model src={staticFile("pepe.glb")} animation="emote" position={[0, rise(6), 0.5]} />
        <Model src={staticFile("moodeng.glb")} animation="attack1" position={[1.4, rise(12), -0.2]} rotation={[0, -0.45, 0]} />
        <ImagePlane src={staticFile("space.png")} width={22} position={[0, 3.5, -12]} />
      <Word text="COMING TO THE" size={52} color={LAV} y={190} delay={10} />
      <Word text="SOLANA dAPP STORE" size={64} y={250} delay={16} />
    </AbsoluteFill>
  );
}

// the real portrait game, in a phone, on Seeker
function OnSeeker() {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 13 } });
  const pw = 340, ph = 604;   // 540x960 gameplay at 0.63
  return (
    <Space>
      <div style={{ position: "absolute", left: (W - pw - 24) / 2, top: 160, width: pw + 24, height: ph + 24, borderRadius: 44, background: "#15121C",
        border: "4px solid #C9B48A", boxShadow: "0 30px 80px rgba(150,60,255,0.45)", transform: `translateY(${interpolate(s, [0, 1], [700, 0])}px)`, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 12, top: 12, width: pw, height: ph, borderRadius: 32, overflow: "hidden" }}>
          <Video src={staticFile("gameplay.mp4")} startFrom={0} endAt={120} muted style={{ width: pw, height: ph, objectFit: "cover" }} />
        </div>
      </div>
      <Word text="PLAYABLE ON" size={48} color={LAV} y={812} delay={14} />
      <Word text="SEEKER" size={92} y={862} delay={20} />
    </Space>
  );
}

const CARDS = ["giga", "pepe", "godcandle", "rug", "popcat"];
function EndCard() {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const logo = spring({ frame: f - 4, fps, config: { damping: 10 } });
  return (
    <Space>
      {CARDS.map((id, i) => {
        const k = spring({ frame: f - i * 3, fps, config: { damping: 12 } });
        const ang = (i - 2) * 11, x = W / 2 + (i - 2) * 96 - 75, y = 545 + Math.abs(i - 2) * 22;
        return (
          <div key={id} style={{ position: "absolute", left: x, top: y, width: 150, height: 188, borderRadius: 14, border: `5px solid ${GOLD}`, overflow: "hidden",
            boxShadow: "0 12px 30px rgba(0,0,0,0.5)", transform: `translateY(${interpolate(k, [0, 1], [600, 0])}px) rotate(${ang * k}deg)` }}>
            <Img src={staticFile(`cards/${id}.png`)} style={{ width: 150, height: 188, objectFit: "cover" }} />
          </div>
        );
      })}
      <Img src={staticFile("logo.png")} style={{ position: "absolute", left: (W - 400) / 2, top: 150, width: 400, height: 380, transform: `scale(${logo})` }} />
      <Word text="COMING SOON TO THE" size={42} color={LAV} y={792} delay={16} />
      <Word text="SOLANA dAPP STORE" size={62} y={838} delay={20} />
      <div style={{ position: "absolute", left: 40, right: 93, top: 902, textAlign: "center", fontFamily: "Lilita One", fontSize: 32, color: LAV, textShadow: edge,
        opacity: interpolate(f, [30, 40], [0, 1], clamp) }}>memeroyale.imaginestudio.fun</div>
    </Space>
  );
}

function Spot() {
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <style>{FONT}</style>
      <Sequence from={0} durationInFrames={80}><Shot from={106} len={80} pos="42% 50%"><Word text="MEME ROYALE" size={96} y={170} delay={2} /></Shot></Sequence>
      <Sequence from={80} durationInFrames={90}><Shot from={302} len={90} pos="32% 50%"><Word text="GOD CANDLE" size={92} color="#7CFF8C" y={170} delay={10} /></Shot></Sequence>
      <Sequence from={170} durationInFrames={90}><Shot from={397} len={90} pos="46% 50%"><Word text="RUG PULL" size={92} color="#FF4F6D" y={170} delay={22} /></Shot></Sequence>
      <Sequence from={260} durationInFrames={120}><Heroes /></Sequence>
      <Sequence from={380} durationInFrames={120}><OnSeeker /></Sequence>
      <Sequence from={500} durationInFrames={100}><EndCard /></Sequence>
      {/* sound: the game's own music and sounds */}
      <Sequence from={0} layout="none" name="music"><Audio src={staticFile("mus_battle.mp3")} startFrom={55} gainDb={-12} fadeIn={0.2} fadeOut={1.2} /></Sequence>
      <Sequence from={3} layout="none" name="vo"><Audio src={staticFile("vo_title.mp3")} gainDb={-2} /></Sequence>
      <Sequence from={256} layout="none" name="swoosh1"><Audio src={staticFile("ui_swoosh.mp3")} gainDb={-6} /></Sequence>
      <Sequence from={380} layout="none" name="start"><Audio src={staticFile("battle_start.mp3")} gainDb={-6} /></Sequence>
      <Sequence from={500} layout="none" name="reveal"><Audio src={staticFile("card_reveal_legendary.mp3")} gainDb={-3} /></Sequence>
      <Sequence from={506} layout="none" name="cheer"><Audio src={staticFile("crowd_cheer.mp3")} gainDb={-9} /></Sequence>
      <Mix lufs={-14} ceiling={-1.5} />
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="seeker-ad" component={Spot} width={W} height={H} fps={30} durationInFrames={600} />);
