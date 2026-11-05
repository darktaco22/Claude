import { AbsoluteFill, Composition, interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig } from "raea";
import { Bloom, Entity, ImagePlane, Model, ToneMapping } from "raea/3d";
import { Camera3d } from "raea/camera";
import { AmbientLight, DirectionalLight, PointLight } from "raea/light";
import { Cylinder, Mesh3d } from "raea/mesh";
import { StandardMaterial } from "raea/pbr";
import { Transform } from "raea/transform";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const FONT = `@font-face { font-family: "Lilita One"; src: url("${staticFile("lilita.ttf")}"); }`;

function Hero() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  // the camera orbits the three heroes and settles in front
  const a = interpolate(f, [0, 150], [-0.9, 0.18], clamp);
  const r = interpolate(f, [0, 150], [6.6, 5.4], clamp);
  const cam = Transform.fromXyz(Math.sin(a) * r, 1.8, Math.cos(a) * r).lookingAt([0, 1.25, 0]);
  const rise = (d: number) => spring({ frame: f - d, fps, config: { damping: 12 } });
  const logo = spring({ frame: f - 95, fps, config: { damping: 10 } });
  const title = spring({ frame: f - 20, fps, config: { damping: 11 } });
  const tag = interpolate(f, [120, 132], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: "#1A0846" }}>
      <style>{FONT}</style>
      <Camera3d transform={cam} projection={{ Perspective: { fov: (38 * Math.PI) / 180 } }} />
      <ToneMapping mode="tony" exposure={0.2} />
      <Bloom intensity={0.6} threshold={0.9} />
      <AmbientLight brightness={350} color="#B9A0FF" />
      <DirectionalLight transform={Transform.fromXyz(3, 7, 5).lookingAt([0, 0, 0])} illuminance={11000} shadow_maps_enabled />
      <PointLight transform={Transform.fromXyz(-3, 2.5, -2)} intensity={900000} color="#9B4DFF" range={20} />
      <PointLight transform={Transform.fromXyz(3, 2.5, -2)} intensity={700000} color="#FFC52E" range={20} />
      {/* the stage: a gold-rimmed purple disc */}
      <Mesh3d name="stage" transform={Transform.fromXyz(0, -0.12, 0)}>
        <Cylinder radius={3.4} half_height={0.12} />
        <StandardMaterial base_color="#3A1690" perceptual_roughness={0.5} />
      </Mesh3d>
      <Mesh3d name="rim" transform={Transform.fromXyz(0, -0.14, 0)}>
        <Cylinder radius={3.55} half_height={0.1} />
        <StandardMaterial base_color="#FFB423" metallic={0.9} perceptual_roughness={0.25} emissive="#5A3A00" />
      </Mesh3d>
      {/* the game's own characters, playing their own clips */}
      <Model src={staticFile("giga.glb")} animation="win" position={[-1.6, interpolate(rise(0), [0, 1], [-2, 0]), 0.2]} rotation={[0, 0.35, 0]} />
      <Model src={staticFile("pepe.glb")} animation="emote" position={[0, interpolate(rise(8), [0, 1], [-2, 0]), 0.7]} rotation={[0, 0, 0]} />
      <Model src={staticFile("moodeng.glb")} animation="attack1" position={[1.7, interpolate(rise(16), [0, 1], [-2, 0]), 0.2]} rotation={[0, -0.4, 0]} />
      <Entity transform={Transform.fromXyz(0, 2.55, -1.4).withScale(Math.max(0.01, logo))}>
        <ImagePlane src={staticFile("logo.png")} width={1.9} />
      </Entity>
      {/* 2D over the 3D */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 44, textAlign: "center", fontFamily: "Lilita One", fontSize: 64, color: "#FFC52E",
        transform: `scale(${title})`, opacity: interpolate(f, [86, 96], [1, 0], clamp), textShadow: "0 5px 0 #1A0846" }}>BULLS vs BEARS</div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 40, textAlign: "center", fontFamily: "Lilita One", fontSize: 40, color: "#F1E8FF",
        opacity: tag }}>memeroyale.imaginestudio.fun</div>
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="showcase" component={Hero} width={1280} height={720} fps={30} durationInFrames={165} />);
