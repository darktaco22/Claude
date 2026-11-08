// The renderer, the camera that frames the arena on any screen, the night lighting, quality tiers.
import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';

const Q = new URLSearchParams(location.search);
const mobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent));

export function pickQuality() {
  const saved = (() => { try { return localStorage.getItem('memeroyale.gfx'); } catch { return null; } })();
  const q = Q.get('quality') || saved || (mobile ? (Math.min(screen.width, screen.height) * devicePixelRatio < 900 ? 'low' : 'mid') : 'high');
  return ['low', 'mid', 'high'].includes(q) ? q : 'mid';
}

export class Stage {
  constructor(canvas) {
    this.quality = pickQuality();
    const r = this.renderer = new THREE.WebGLRenderer({canvas, antialias: this.quality !== 'low', powerPreference: 'high-performance', alpha: false, stencil: false});
    // a phone's mid tier draws at 2x too (at 1.75 a 3x screen stretched the frame soft); adaptive quality steps it down if slow
    r.setPixelRatio(Math.min(devicePixelRatio, this.quality === 'low' ? 1.25 : 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    // Neutral keeps the art's own colours (ACES greyed and lifted them: a milky film over the arena)
    r.toneMapping = THREE.NeutralToneMapping; r.toneMappingExposure = 1.2;
    r.shadowMap.enabled = this.quality !== 'low';
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color('#0a0d18');
    this.scene.fog = new THREE.Fog('#0a0d18', 34, 70);
    this.camera = new THREE.PerspectiveCamera(36, 1, 0.5, 200);
    this.pitch = THREE.MathUtils.degToRad(60);   // steep, like the genre's: the far side keeps its size
    this.look = new THREE.Vector3(9, 0, 16.4);
    this.shake = 0; this.shakeT = 0;
    // reflections for the PBR props and characters
    const pm = new THREE.PMREMGenerator(r);
    this.scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.2;
    this.lights();
    this.safe = {top: 0.085, bottom: 0.235};   // fractions of the screen the HUD covers
    // bloom on the neon, the canal and the effects (mid and high only: it costs a few full-screen passes)
    if (this.quality !== 'low') {
      // multisampled, or the composer's buffer loses the antialiasing the canvas had
      this.composer = new EffectComposer(r, new THREE.WebGLRenderTarget(1, 1, {type: THREE.HalfFloatType, samples: 4}));
      this.composer.addPass(new RenderPass(this.scene, this.camera));
      // only what shines blooms (emissives, effects), not every lit white wall, and tight round it
      this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.42, 0.2, 1.6);
      this.composer.addPass(this.bloom);
      this.composer.addPass(new OutputPass());
    }
    addEventListener('resize', () => this.resize());
    this.resize();
  }
  lights() {
    const s = this.scene;
    s.add(this.hemi = new THREE.HemisphereLight('#9fb0ff', '#3a2a30', 1.35));
    // the floodlight: warm key from the front-left, casts the shadows
    const key = this.key = new THREE.DirectionalLight('#fff1dc', 3.3);
    key.position.set(-7, 26, 30); key.target.position.set(9, 0, 16); s.add(key, key.target);
    key.castShadow = this.quality !== 'low';
    const sz = this.quality === 'high' ? 2048 : 1024;
    key.shadow.mapSize.set(sz, sz);
    Object.assign(key.shadow.camera, {left: -14, right: 14, top: 22, bottom: -22, near: 5, far: 90});
    key.shadow.bias = -0.0006; key.shadow.normalBias = 0.03; key.shadow.radius = 3;
    // a cool rim from behind the opponent so silhouettes read on the dark ground
    const rim = this.rim = new THREE.DirectionalLight('#7f9bff', 1.1); rim.position.set(16, 14, -18); s.add(rim);
    // canal glow from below the middle
    const pool = this.poolLight = new THREE.PointLight('#5dff7a', 14, 12, 1.6); pool.position.set(9, 1.2, 16); s.add(pool);
  }
  resize() {
    const w = innerWidth, h = innerHeight;
    this.renderer.setSize(w, h, false);
    if (this.composer) { this.composer.setPixelRatio(this.renderer.getPixelRatio()); this.composer.setSize(w, h); const k = this.quality === 'high' ? 0.5 : 0.35; this.bloom.resolution.set(w * k, h * k); }
    this.camera.aspect = w / h;
    if (this.mode === 'hub') this.camera.updateProjectionMatrix(); else this.fit();
    this.arena?.world?.ensure();
  }
  // the menu camera: a slow drift in front of my Battlestation, framed in the free band between the menu panels
  hub(band = {top: 0.2, bottom: 0.56}) { this.mode = 'hub'; this.band = band; this.hubT = 0; this.shake = 0; this.arena?.backdropMode('hub'); }
  battle() { this.mode = 'battle'; this.camera.clearViewOffset(); this.arena?.backdropMode('battle'); this.fit(); }
  hubCamera(dt) {
    const cam = this.camera, b = this.band; this.hubT += dt;
    cam.fov = 30;
    // fit the Battlestation (with the NEET on top) and the crew in front of it into the free band: tall enough for
    // ~7.5 units of height and wide enough for ~9 units across
    const bandH = Math.max(0.2, 1 - b.top - b.bottom), tf = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2));
    // (on a PC the menus are a phone-shaped column: frame for the column's width, not the whole screen's)
    const d = Math.max(5.4 / (0.9 * bandH * 2 * tf), 7.2 / (0.96 * 2 * tf * Math.min(cam.aspect * (b.w ?? 1), 0.62)));
    const a = Math.sin(this.hubT * 0.12) * 0.16, tx = 9, ty = 2.5, tz = 31.4;
    cam.position.set(tx + Math.sin(a) * d, ty + d * 0.3, tz + Math.cos(a) * d);
    this.scene.fog.near = d * 1.1; this.scene.fog.far = d * 1.1 + 40;
    cam.lookAt(tx, ty, tz);
    const w = innerWidth, h = innerHeight, center = (b.top + (1 - b.bottom)) / 2;
    cam.setViewOffset(w, h, (0.5 - (b.cx ?? 0.5)) * w, (0.5 - center) * h, w, h);
    cam.updateProjectionMatrix();
  }
  // frame the arena between the top bar and the card tray, whatever the aspect: a few rounds of "project the corners,
  // re-centre, scale the distance"
  fit() {
    const cam = this.camera, P = [];
    for (const x of [-0.3, 18.3]) for (const z of [-0.6, 32.6]) P.push(new THREE.Vector3(x, 0, z));
    // the far Battlestation's top and its health plate must clear the top bar
    P.push(new THREE.Vector3(9, 8.2, 2.5), new THREE.Vector3(3.5, 6.0, 6.5), new THREE.Vector3(14.5, 6.0, 6.5));
    // guard against a HUD that isn't laid out yet
    const st = Math.min(0.3, Math.max(0, this.safe.top || 0)), sb = Math.min(0.45, Math.max(0, this.safe.bottom || 0));
    const top = 1 - 2 * st, bot = -1 + 2 * sb;
    // on wide screens the arena gets a portrait column; the sides show the plaza
    let d = 46, lz = 16.4;
    cam.fov = this.camera.aspect > 0.75 ? 30 : 36;
    for (let it = 0; it < 12; it++) {
      this.place(d, lz);
      let x0 = 1, x1 = -1, y0 = 1, y1 = -1;
      for (const p of P) { const v = p.clone().project(cam); x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y); }
      const wantH = top - bot, haveH = y1 - y0, haveW = x1 - x0;
      const k = Math.max(haveH / wantH, haveW / 1.96);
      d *= 0.35 + 0.65 * k;
      // shift the look point so the arena's vertical middle sits in the middle of the free band
      const mid = (y1 + y0) / 2, want = (top + bot) / 2;
      lz -= (mid - want) * d * 0.22;
    }
    this.dist = d; this.lz = lz; this.place(d, lz);
    cam.updateProjectionMatrix();
  }
  place(d, lz) {
    const cam = this.camera;
    this.scene.fog.near = d * 1.3; this.scene.fog.far = d * 1.3 + 60;
    this.look.set(9, 0, lz);
    cam.position.set(9, Math.sin(this.pitch) * d, lz + Math.cos(this.pitch) * d);
    cam.lookAt(this.look);
    cam.updateProjectionMatrix(); cam.updateMatrixWorld();
  }
  kick(amount) { this.shake = Math.min(1.2, this.shake + amount); }
  render(dt) {
    if (this.mode === 'hub') { this.hubCamera(dt); this.draw(); return; }
    this.watch(dt);
    if (this.shake > 0) {
      this.shakeT += dt * 60; this.shake = Math.max(0, this.shake - dt * 2.6);
      const a = this.shake * this.shake * 0.35;
      this.place(this.dist, this.lz);
      this.camera.position.x += Math.sin(this.shakeT * 1.7) * a; this.camera.position.y += Math.cos(this.shakeT * 2.3) * a * 0.6;
      this.camera.lookAt(this.look);
    }
    this.draw();
  }
  draw() { if (this.composer) this.composer.render(); else this.renderer.render(this.scene, this.camera); }
  // what the battle's first frame would do all at once (on a phone, a freeze): every texture in the scene sent to the GPU, one
  // per task, then every shader compiled in parallel for the target the frames are drawn into (the bloom's buffer, when on)
  async warm(breathe) {
    const r = this.renderer, texs = new Set();
    this.scene.traverse(o => { for (const m of [o.material].flat()) if (m) for (const v of [...Object.values(m), ...Object.values(m.uniforms || {}).map(u => u?.value)]) if (v?.isTexture) texs.add(v); });
    for (const t of texs) { r.initTexture(t); await breathe(); }
    const prev = r.getRenderTarget(); r.setRenderTarget(this.composer ? this.composer.renderTarget1 : null);
    const done = r.compileAsync(this.scene, this.camera); r.setRenderTarget(prev);
    await done;
  }
  // adaptive quality: a phone that can't hold ~50 fps steps down, one step per 3 s window: the bloom, then the shadows, and
  // only then the resolution (to no less than 1.5x on a sharp screen: below that the arena goes soft and blocky), so the
  // picture stays sharp as long as anything else can give. Judged on the median frame (a hitch or a GC pause is not
  // slowness), and a step that buys no frames (still under 50 and under 10 % faster) is taken back and the stepping stops: a
  // phone capped at 30 fps (Low Power Mode) or held back by its CPU would otherwise lose its looks for nothing.
  // The first 2.5 s of a battle (shaders compiling, models arriving) don't count. This session only.
  watch(dt) {
    if (this.mode !== 'battle' || this.settled) return;
    const w = this.perf ||= {t: 0, d: [], skip: this.degraded ? 0.5 : 2.5};
    if (w.skip > 0) { w.skip -= dt; return; }
    w.t += dt; w.d.push(dt);
    if (w.t < 3) return;
    this.perf = null;
    const fps = 1 / w.d.sort((a, b) => a - b)[w.d.length >> 1], last = this.lastStep; this.lastStep = null;
    if (last && fps < 50 && fps < last.fps * 1.1) { last.undo(); this.settled = true; console.info('[quality] no gain from', last.what + ': taken back,', fps.toFixed(0), 'fps'); return; }
    if (fps >= 50) return;
    this.degraded = (this.degraded || 0) + 1;
    const step = (what, undo) => { this.lastStep = {what, undo, fps}; console.info('[quality]', what + ',', fps.toFixed(0), 'fps'); };
    const r = this.renderer, pr = r.getPixelRatio(), floor = Math.min(devicePixelRatio || 1, this.quality === 'low' ? 1 : 1.5);
    if (this.composer) { const c = this.composer; this.composer = null; step('bloom off', () => { this.composer = c; this.resize(); }); }
    else if (r.shadowMap.enabled) {
      const shadows = on => { r.shadowMap.enabled = on; this.key.castShadow = on; this.scene.traverse(o => { for (const m of [o.material].flat()) if (m) m.needsUpdate = true; }); };
      shadows(false); step('shadows off', () => shadows(true));
    }
    else if (pr > floor + 0.01) { r.setPixelRatio(Math.max(floor, pr * 0.85)); this.resize(); step(`resolution ${r.getPixelRatio().toFixed(2)}x`, () => { r.setPixelRatio(pr); this.resize(); }); }
    else this.settled = true;
  }
  // an arena's light (src/render/themes.js)
  applyTheme(T) {
    this.scene.background = new THREE.Color(T.sky); this.scene.fog.color.set(T.fog);
    // (the themes were tuned under ACES: Neutral shows them brighter and flatter, so less sky fill and a touch less exposure)
    this.hemi.color.set(T.hemi[0]); this.hemi.groundColor.set(T.hemi[1]); this.hemi.intensity = T.hemi[2] * 0.65;
    const [kc, ki, kx, ky, kz] = T.key; this.key.color.set(kc); this.key.intensity = ki; this.key.position.set(kx, ky, kz);
    this.rim.color.set(T.rim[0]); this.rim.intensity = T.rim[1];
    this.renderer.toneMappingExposure = T.exposure * 0.95;
    if (this.bloom) this.bloom.strength = T.bloom;
    this.poolLight.color.set(T.canal.glow); this.poolBase = T.canal.mode === 'ice' ? 6 : 13;
  }
  // pointer -> arena ground point (y = 0)
  pick(px, py) {
    const ndc = new THREE.Vector2(px / innerWidth * 2 - 1, -(py / innerHeight) * 2 + 1);
    const ray = new THREE.Raycaster(); ray.setFromCamera(ndc, this.camera);
    const t = -ray.ray.origin.y / ray.ray.direction.y; if (!(t > 0)) return null;
    return ray.ray.at(t, new THREE.Vector3());
  }
  toScreen(v, out = {x: 0, y: 0, behind: false}) {
    const p = v.clone().project(this.camera);
    out.x = (p.x + 1) / 2 * innerWidth; out.y = (1 - p.y) / 2 * innerHeight; out.behind = p.z > 1; return out;
  }
}
