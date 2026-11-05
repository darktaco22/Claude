// MEME ROYALE: the runway. Every character in the game walks on, turns to the camera, strikes its own pose, and walks off.
// The camera never moves; the backdrop (each character's own card art, washed out) cross-fades as each one arrives.
// The models, their clips, their card art and their voice lines are the game's own files.
import { AbsoluteFill, Audio, Composition, Img, Mix, Sequence, interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig } from "raea";
import { Bloom, Canvas3D, Model, ToneMapping } from "raea/3d";
import { Camera3d } from "raea/camera";
import { AmbientLight, DirectionalLight, PointLight, SpotLight } from "raea/light";
import { Cuboid, Mesh3d } from "raea/mesh";
import { StandardMaterial } from "raea/pbr";
import { Transform } from "raea/transform";
import { CAST } from "./cast";

const FPS = 30, W = 1280, H = 720;
const INTRO = 75;            // the logo before the first walk
const CYCLE = 126;           // a new character every 4.2 s
const WALK = 60;             // frames to walk from the wings to the mark
const TURN = 12;             // frames to turn to the camera (and back)
const X0 = -4.6, X1 = 4.6;   // the wings
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const RARITY: Record<string, string> = { common: "#B9C3D6", rare: "#4CC9F0", epic: "#C77DFF", legendary: "#FFC84A" };
const INK = "#1A0846";
const FONT = `@font-face { font-family: "Lilita One"; src: url("${staticFile("lilita.ttf")}"); }`;
const edge = `0 5px 0 ${INK}, 3px 3px 0 ${INK}, -3px 3px 0 ${INK}, 3px -3px 0 ${INK}, -3px -3px 0 ${INK}`;

// each character's timing, from its own pose clip (the emote, or the victory loop when the emote is short)
const POSES = CAST.map((c) => {
  const useWin = c.emote < 1.4;
  const len = Math.round(Math.min(2.6, Math.max(1.6, useWin ? c.win : c.emote)) * FPS);
  return { clip: useWin ? "win" : "emote", len };
});
const startOf = (i: number) => INTRO + i * CYCLE;
const END = startOf(CAST.length - 1) + WALK + 2 * TURN + POSES[CAST.length - 1].len + WALK + 15;
const OUTRO = 105;
const TOTAL = END + OUTRO;

const ease = (k: number) => (k <= 0 ? 0 : k >= 1 ? 1 : k * k * (3 - 2 * k));

// where character i is at frame f: position, facing, clip and the clip's time; null when off stage
function stateOf(i: number, f: number) {
  const t = f - startOf(i), P = POSES[i], c = CAST[i];
  const walkRate = 1.55;   // the walk clip, a little brisk: a runway strut
  const a = WALK, b = a + TURN, p = b + P.len, q = p + TURN, e = q + WALK;
  if (t < 0 || t > e) return null;
  if (t < a) return { x: interpolate(t, [0, a], [X0, 0], clamp), ry: Math.PI / 2, clip: "walk", time: (t / FPS) * walkRate };
  if (t < b) return { x: 0, ry: interpolate(ease((t - a) / TURN), [0, 1], [Math.PI / 2, 0]), clip: "idle", time: (t - a) / FPS };
  if (t < p) return { x: 0, ry: 0, clip: P.clip, time: (t - b) / FPS, loop: P.clip === "win" };
  if (t < q) return { x: 0, ry: interpolate(ease((t - p) / TURN), [0, 1], [0, Math.PI / 2]), clip: "idle", time: (t - p) / FPS };
  return { x: interpolate(t, [q, e], [0, X1], clamp), ry: Math.PI / 2, clip: "walk", time: ((t - q) / FPS) * walkRate };
}

// the backdrop: whose it is at frame f, and how far into the next one's fade
function backdrop(f: number) {
  const g = f - INTRO - WALK + 20;   // the fade finishes as each one reaches the mark
  const i = Math.max(0, Math.min(CAST.length - 1, Math.floor(g / CYCLE)));
  const k = i >= CAST.length - 1 ? 0 : ease(interpolate(g - i * CYCLE, [CYCLE - 45, CYCLE], [0, 1], clamp));
  return { i, k };
}

function NameCard({ i }: { i: number }) {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const t = f - startOf(i) - WALK;
  const P = POSES[i], out = TURN * 2 + P.len;
  if (t < 0 || t > out + 6) return null;
  const s = spring({ frame: t, fps, config: { damping: 12 } });
  const o = interpolate(t, [out - 6, out + 6], [1, 0], clamp);
  const c = CAST[i], col = RARITY[c.rarity];
  return (
    <div style={{ position: "absolute", left: 90, bottom: 130, opacity: o, transform: `translateX(${interpolate(s, [0, 1], [-60, 0])}px)` }}>
      <div style={{ display: "inline-block", padding: "4px 14px", borderRadius: 10, background: col, color: INK, fontFamily: "Lilita One", fontSize: 26, letterSpacing: 1 }}>
        {c.rarity.toUpperCase()}
      </div>
      <div style={{ fontFamily: "Lilita One", fontSize: 72, color: "#FFFFFF", textShadow: edge, marginTop: 6 }}>{c.name}</div>
    </div>
  );
}

function Runway() {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const { i: bi, k } = backdrop(f);
  const onStage = CAST.map((c, i) => ({ c, i, s: stateOf(i, f) })).filter((o) => o.s);
  const logoIn = spring({ frame: f, fps, config: { damping: 12 } });
  const logoOut = interpolate(f, [INTRO - 20, INTRO], [1, 0], clamp);
  const endIn = spring({ frame: f - END, fps, config: { damping: 11 } });
  return (
    <AbsoluteFill style={{ background: "#0A041A" }}>
      <style>{FONT}</style>
      {/* the backdrops, under the 3D: the current one, the next one fading in over it */}
      <Img src={staticFile(`bg/${CAST[bi].id}.png`)} style={{ position: "absolute", left: 0, top: 0, width: W, height: H }} />
      {k > 0 && <Img src={staticFile(`bg/${CAST[bi + 1].id}.png`)} style={{ position: "absolute", left: 0, top: 0, width: W, height: H, opacity: k }} />}
      <Canvas3D layered>
        <Camera3d transform={Transform.fromXyz(0, 1.5, 5.6).lookingAt([0, 0.88, 0])} projection={{ Perspective: { fov: (28 * Math.PI) / 180 } }} />
        <ToneMapping mode="tony" exposure={0.25} />
        <Bloom intensity={0.35} threshold={1.0} />
        <AmbientLight brightness={260} color="#D9CCFF" />
        <DirectionalLight transform={Transform.fromXyz(2.5, 6, 5).lookingAt([0, 0, 0])} illuminance={11000} shadow_maps_enabled />
        <PointLight transform={Transform.fromXyz(-2.5, 2.6, -1.5)} intensity={500000} color="#B06BFF" range={14} />
        <PointLight transform={Transform.fromXyz(2.5, 2.6, -1.5)} intensity={420000} color="#FFC84A" range={14} />
        {/* the runway: a dark gloss walkway with a gold edge */}
        <Mesh3d name="walk" transform={Transform.fromXyz(0, -0.04, 0)}>
          <Cuboid half_size={[7, 0.04, 0.9]} />
          <StandardMaterial base_color="#000000" metallic={0.9} perceptual_roughness={0.12} />
        </Mesh3d>
        <Mesh3d name="edge-front" transform={Transform.fromXyz(0, -0.02, 0.92)}>
          <Cuboid half_size={[7, 0.03, 0.025]} />
          <StandardMaterial base_color="#FFB423" emissive="#FFB423" emissive_strength={2.5} />
        </Mesh3d>
        <Mesh3d name="edge-back" transform={Transform.fromXyz(0, -0.02, -0.92)}>
          <Cuboid half_size={[7, 0.03, 0.025]} />
          <StandardMaterial base_color="#FFB423" emissive="#FFB423" emissive_strength={2.5} />
        </Mesh3d>
        {onStage.map(({ c, i, s }) => (
          <Model key={c.id} name={c.id} src={staticFile(`models/${c.id}.glb`)} animation={s!.clip} time={s!.time} loop={s!.clip !== "emote"}
            position={[s!.x, 0, 0]} rotation={[0, s!.ry, 0]} />
        ))}
      </Canvas3D>
      {onStage.map(({ i }) => <NameCard key={"n" + i} i={i} />)}
      {/* opening and closing: the game's logo */}
      {f < INTRO && (
        <Img src={staticFile("logo.png")} style={{ position: "absolute", left: (W - 420) / 2, top: 140, width: 420, height: 398, opacity: logoOut, transform: `scale(${logoIn})` }} />
      )}
      {f >= END && (
        <AbsoluteFill style={{ background: `rgba(10,4,26,${interpolate(f - END, [0, 12], [0, 0.55], clamp)})` }}>
          <Img src={staticFile("logo.png")} style={{ position: "absolute", left: (W - 420) / 2, top: 110, width: 420, height: 398, transform: `scale(${endIn})` }} />
          <div style={{ position: "absolute", left: 80, right: 80, top: 540, textAlign: "center", fontFamily: "Lilita One", fontSize: 44, color: "#FFC52E", textShadow: edge,
            opacity: interpolate(f - END, [10, 22], [0, 1], clamp) }}>COMING SOON TO THE SOLANA dAPP STORE</div>
          <div style={{ position: "absolute", left: 80, right: 80, top: 598, textAlign: "center", fontFamily: "Lilita One", fontSize: 30, color: "#F1E8FF", textShadow: edge,
            opacity: interpolate(f - END, [18, 30], [0, 1], clamp) }}>memeroyale.imaginestudio.fun</div>
        </AbsoluteFill>
      )}
      {/* sound: the game's menu music under it all, and each character's own voice line on its pose */}
      <Sequence from={0} layout="none" name="music">
        <Audio src={staticFile("sfx/mus_menu.mp3")} loop startFrom={0} endAt={Math.round(61.6 * FPS)} gainDb={-12} fadeIn={0.5} fadeOut={1.5} />
      </Sequence>
      {CAST.map((c, i) => (
        <Sequence key={"b" + i} from={startOf(i) + WALK + TURN} layout="none" name={"bark-" + c.id}>
          <Audio src={staticFile(`sfx/${c.bark}`)} gainDb={-3} />
        </Sequence>
      ))}
      <Mix lufs={-14} ceiling={-1.5} />
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="runway" component={Runway} width={W} height={H} fps={FPS} durationInFrames={TOTAL} />);
