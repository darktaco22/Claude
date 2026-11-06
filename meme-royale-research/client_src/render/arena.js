// THE PLAZA AFTER DARK: the paved court, the Liquidity Pool canal, bridges, towers, the plaza dressing around it,
// and the placement overlay (the red "can't drop here" mask and the ghost marker).
import * as THREE from 'three';
import {ARENA} from '../sim.js';
import {loadGLB, cloneGLB} from './assets.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {themeOf, paintCourt, paintOuter, canalMaterial, CANAL_MODE} from './themes.js';
import {World} from './world.js';
import {WORLDS} from './worlds.js';

export const TEAM_COL = [new THREE.Color('#7CFF6B'), new THREE.Color('#FF4D6D')];
// matte paint and cloth on the crown towers (cornice, banners, rugs, flags): the same sides, without the glow
export const TEAM_PAINT = [new THREE.Color('#38b84a'), new THREE.Color('#e23d4e')];
// the towers are drawn bigger than their footprint (the sim's radius), like the genre's: they dominate their corner of the court
export const TOWER_VIS = 1.2;
const PROP_SCALE = 0.8;

const texLoader = new THREE.TextureLoader();
const loadTex = url => new Promise((res, rej) => texLoader.load(url, res, undefined, rej));
const GROUND_TILE = 8;     // game tiles covered by one repeat of an arena's ground texture
function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; }

function asphaltTexture() {
  const [c, g] = canvas(512, 512);
  g.fillStyle = '#16181f'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) { const s = Math.random(); g.fillStyle = `rgba(${s > 0.5 ? '190,200,230' : '0,0,0'},${0.03 + Math.random() * 0.06})`; g.fillRect(Math.random() * 512, Math.random() * 512, 1 + s * 2.5, 1 + s * 2.5); }
  for (let i = 0; i < 14; i++) { g.strokeStyle = `rgba(0,0,0,${0.15 + Math.random() * 0.2})`; g.lineWidth = 1 + Math.random() * 2; g.beginPath(); let x = Math.random() * 512, y = Math.random() * 512; g.moveTo(x, y); for (let k = 0; k < 6; k++) { x += (Math.random() - 0.5) * 70; y += (Math.random() - 0.5) * 70; g.lineTo(x, y); } g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(10, 12); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

function concreteTexture() {
  const [c, g] = canvas(256, 256);
  g.fillStyle = '#5d6068'; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 2600; i++) { const s = Math.random(); g.fillStyle = `rgba(${s > 0.5 ? '255,255,255' : '0,0,0'},${0.04 + Math.random() * 0.06})`; g.fillRect(Math.random() * 256, Math.random() * 256, 1 + s * 3, 1 + s * 3); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
}
function hazardTexture() {
  const [c, g] = canvas(128, 16);
  g.fillStyle = '#16171c'; g.fillRect(0, 0, 128, 16); g.fillStyle = '#f5c518';
  for (let x = -16; x < 144; x += 16) { g.beginPath(); g.moveTo(x, 16); g.lineTo(x + 8, 16); g.lineTo(x + 16, 0); g.lineTo(x + 8, 0); g.fill(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
}

// the Liquidity Pool: glowing acid-green liquid flowing left to right, brighter streaks, slow swell
function poolMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {uT: {value: 0}},
    vertexShader: `varying vec2 vUv; varying vec3 vW; void main(){ vUv = uv; vec4 w = modelMatrix * vec4(position,1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform float uT; varying vec2 vUv; varying vec3 vW;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
      float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
      float fbm(vec2 p){ float a=.5, s=0.; for(int k=0;k<4;k++){ s+=a*n(p); p*=2.03; a*=.5; } return s; }
      void main(){
        vec2 p = vec2(vW.x * .55 - uT * .45, vW.z * 1.6);
        float f = fbm(p + vec2(fbm(p * .7 + uT * .1), 0.) * 1.4);
        float streak = smoothstep(.62, .82, fbm(vec2(vW.x * .3 - uT * .9, vW.z * 3.2)));
        float edge = smoothstep(0., .55, min(vW.z - 15., 17. - vW.z));
        vec3 deep = vec3(.01,.09,.04), mid = vec3(.10,.55,.16), hot = vec3(.55,1.,.45);
        vec3 col = mix(deep, mid, f * .9 * edge + .1);
        col += hot * streak * .65 * edge;
        col += vec3(.25,.9,.3) * pow(1. - edge, 3.) * .35;   // foam against the walls
        gl_FragColor = vec4(col, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export class Arena {
  constructor(stage) {
    this.stage = stage; const s = this.scene = stage.scene;
    this.root = new THREE.Group(); s.add(this.root);
    this.towers = [[], []];
    this.time = 0;
    this.buildGround(); this.buildCanal(); this.buildCurb(); this.buildBackdrop();
    this.world = new World(this); this.world.lit(this.courtMat);
    this.kit = new THREE.Group(); this.root.add(this.kit); this.anims = []; this.texCache = {};
    this.overlay();
  }
  buildGround() {
    // its colour and normal maps are the arena's (applyTheme paints them, once per arena)
    const mat = this.courtMat = new THREE.MeshStandardMaterial({normalScale: new THREE.Vector2(0.9, 0.9), roughness: 0.82, metalness: 0.0});
    // two halves, leaving the canal open
    for (const [z0, z1] of [[0, 15], [17, 32]]) {
      const g = new THREE.PlaneGeometry(18, z1 - z0); g.rotateX(-Math.PI / 2);
      const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - (z0 + (1 - uv.getY(i)) * (z1 - z0)) / 32);
      const m = new THREE.Mesh(g, mat); m.position.set(9, 0, (z0 + z1) / 2); m.receiveShadow = true; this.root.add(m);
    }
    // the ground around the court: the arena's ground texture in world units (one tile of it = GROUND_TILE game tiles), with
    // its repeats hidden (a second, turned sample blended in by a slow noise; off for tiles, planks and patterns, which would
    // ghost) and a broad light/dark variation
    this.groundMacro = {value: 0.22}; this.groundAnti = {value: 1};
    const asphalt = this.outerMat = new THREE.MeshStandardMaterial({map: asphaltTexture(), roughness: 0.92, color: '#b8bcc8'});
    asphalt.map.repeat.set(1, 1);
    asphalt.onBeforeCompile = sh => {
      sh.uniforms.uMacro = this.groundMacro; sh.uniforms.uAnti = this.groundAnti;
      sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', `
        #ifdef USE_MAP
          vec2 gu = vMapUv;
          float gn = gNoise(gu * .23), gm = gNoise(gu * .07 + 3.1);
          vec4 g1 = texture2D(map, gu), g2 = texture2D(map, mat2(.8, -.6, .6, .8) * gu * .79 + vec2(.37, .61));
          vec4 sampledDiffuseColor = mix(g1, g2, smoothstep(.35, .65, gn) * uAnti);
          sampledDiffuseColor.rgb *= 1. + (gm - .5) * 2. * uMacro;
          diffuseColor *= sampledDiffuseColor;
        #endif`).replace('void main() {', `uniform float uMacro, uAnti;
        float gH(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float gNoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f); return mix(mix(gH(i), gH(i + vec2(1, 0)), f.x), mix(gH(i + vec2(0, 1)), gH(i + vec2(1, 1)), f.x), f.y); }
        void main() {`);
    };
    for (const [z0, z1] of [[-30, 15], [17, 62]]) {
      const g = new THREE.PlaneGeometry(90, z1 - z0); g.rotateX(-Math.PI / 2);
      const m = new THREE.Mesh(g, asphalt); m.position.set(9, -0.04, (z0 + z1) / 2); m.receiveShadow = true; this.root.add(m); (this.plain ||= []).push(m);
      // world-space UVs: the texture keeps its size whatever the plane's
      const P = g.attributes.position, U = g.attributes.uv;
      for (let i = 0; i < P.count; i++) U.setXY(i, (P.getX(i) + 9) / GROUND_TILE, -(P.getZ(i) + (z0 + z1) / 2) / GROUND_TILE);
    }
  }
  buildCanal() {
    const pool = this.poolMat = canalMaterial();
    const w = new THREE.Mesh(new THREE.PlaneGeometry(90, 2).rotateX(-Math.PI / 2), pool); w.position.set(9, -0.42, 16); this.root.add(w); this.plain.push(w);
    // walls and coping with hazard paint
    const conc = concreteTexture(); conc.repeat.set(30, 0.4);
    const wall = this.wallMat = new THREE.MeshStandardMaterial({map: conc, color: '#7a7f8a', roughness: 0.9});
    const haz = hazardTexture(); haz.repeat.set(40, 1);
    const cop = new THREE.MeshStandardMaterial({map: haz, roughness: 0.7});
    for (const z of [15, 17]) {
      const g = new THREE.PlaneGeometry(90, 0.45); const m = new THREE.Mesh(g, wall);
      m.position.set(9, -0.22, z); m.rotation.y = z === 15 ? 0 : Math.PI; this.root.add(m); this.plain.push(m);
      const c = new THREE.Mesh(new THREE.BoxGeometry(90, 0.06, 0.22), [wall, wall, cop, wall, wall, wall]);
      c.position.set(9, 0.01, z + (z === 15 ? -0.11 : 0.11)); c.receiveShadow = true; this.root.add(c); this.plain.push(c);
    }
    // things floating down the river (coins, rubber ducks, cans, ice floes, casino chips: the theme picks)
    this.floaters = {}; this.floatKind = null; this.coinData = [];
    for (let i = 0; i < 24; i++) this.coinData.push({x: Math.random() * 40 - 11, z: 15.3 + Math.random() * 1.4, s: 0.35 + Math.random() * 0.5, r: Math.random() * 6, w: Math.random() * 6, k: 0.7 + Math.random() * 0.6});
    this.bridges = [];
    for (const bx of ARENA.bridges) { const g = this.placeholderBridge(); g.position.set(bx, 0, 16); this.root.add(g); this.bridges.push(g); }
  }
  placeholderBridge() {
    const g = new THREE.Group();
    const conc = concreteTexture(); conc.repeat.set(2, 3);
    const deck = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.22, 4.1), new THREE.MeshStandardMaterial({map: conc, color: '#8a8f99', roughness: 0.85}));
    deck.position.y = -0.04; deck.receiveShadow = deck.castShadow = true; g.add(deck);
    const steel = new THREE.MeshStandardMaterial({color: '#2b3038', metalness: 0.8, roughness: 0.4});
    for (const sx of [-1.5, 1.5]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.08, 4.0), steel); rail.position.set(sx, 0.55, 0); rail.castShadow = true; g.add(rail);
      for (let k = -2; k <= 2; k++) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.55, 0.1), steel); p.position.set(sx, 0.3, k * 0.95); p.castShadow = true; g.add(p); }
      const glow = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 3.9), new THREE.MeshBasicMaterial({color: '#7CFF6B'})); glow.position.set(sx * 0.97, 0.08, 0); g.add(glow);
    }
    return g;
  }
  // neon tubes around each half (green for the Bulls, red for the Bears), with soft glow strips on the court
  buildNeon() {
    const glowTex = (() => { const [c, g] = canvas(16, 128); const gr = g.createLinearGradient(0, 0, 0, 128); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 16, 128); return new THREE.CanvasTexture(c); })();
    const segs = s => { const z0 = s === 0 ? 17.35 : 0.35, z1 = s === 0 ? 31.65 : 14.65, x0 = 0.35, x1 = 17.65, k = 1.2;
      // an octagon-ish outline with cut corners, like a painted arena boundary
      return [[x0 + k, z0, x1 - k, z0], [x1 - k, z0, x1, z0 + k], [x1, z0 + k, x1, z1 - k], [x1, z1 - k, x1 - k, z1], [x1 - k, z1, x0 + k, z1], [x0 + k, z1, x0, z1 - k], [x0, z1 - k, x0, z0 + k], [x0, z0 + k, x0 + k, z0]]; };
    this.neon = [];
    for (const s of [0, 1]) {
      const col = TEAM_COL[s];
      const tube = new THREE.MeshBasicMaterial({color: col.clone().lerp(new THREE.Color('#ffffff'), 0.2).multiplyScalar(1.15)});
      const glow = new THREE.MeshBasicMaterial({color: col, map: glowTex, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false});
      // one merged mesh per team for the tubes and one for the glow (2 draw calls instead of 16)
      const tubes = [], glows = [], M = new THREE.Matrix4();
      for (const [ax, az, bx, bz] of segs(s)) {
        const L = Math.hypot(bx - ax, bz - az), a = Math.atan2(bx - ax, bz - az), mx = (ax + bx) / 2, mz = (az + bz) / 2;
        M.makeRotationY(a).setPosition(mx, 0.04, mz); tubes.push(new THREE.BoxGeometry(0.07, 0.05, L).applyMatrix4(M));
        M.makeRotationY(a).setPosition(mx, 0.025, mz); glows.push(new THREE.PlaneGeometry(0.9, L).rotateX(-Math.PI / 2).applyMatrix4(M));
      }
      this.root.add(new THREE.Mesh(mergeGeometries(tubes), tube)); (this.neonTubes ||= []).push(tube);
      const gm = new THREE.Mesh(mergeGeometries(glows), glow); gm.renderOrder = 1; this.root.add(gm);
      this.neon.push(glow);
    }
  }
  buildCurb() {
    this.buildNeon();
    // a low concrete curb around the court frames it against the plaza
    const conc = concreteTexture(); conc.repeat.set(1, 12);
    const m = this.curbMat = new THREE.MeshStandardMaterial({map: conc, color: '#8d929c', roughness: 0.85}); this.curbs = [];
    const add = (x, z, w, d) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, 0.22, d), m); b.position.set(x, 0.07, z); b.receiveShadow = b.castShadow = true; this.root.add(b); this.curbs.push(b); };
    add(-0.2, 7.5, 0.4, 15.4); add(18.2, 7.5, 0.4, 15.4); add(-0.2, 24.5, 0.4, 15.4); add(18.2, 24.5, 0.4, 15.4);
    add(9, -0.2, 18.8, 0.4); add(9, 32.2, 18.8, 0.4);
  }

  // ---------- the arena's look (src/render/themes.js) and its decoration kit (assets/arenas/<id>/)
  // the painted scenery behind the far end: a big card that leans back to face the camera (steeply for the battle view,
  // nearly upright for the hub), its bottom fading into the ground
  buildBackdrop() {
    const [c, g] = canvas(4, 256), gr = g.createLinearGradient(0, 0, 0, 256);
    gr.addColorStop(0, '#fff'); gr.addColorStop(0.8, '#fff'); gr.addColorStop(1, '#000'); g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
    const m = this.backMat = new THREE.MeshBasicMaterial({color: '#ffffff', alphaMap: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, fog: false, toneMapped: false});
    const b = this.backdrop = new THREE.Mesh(new THREE.PlaneGeometry(2, 1), m); b.renderOrder = -1; b.visible = false; this.root.add(b);
    this.backdropMode('battle');
  }
  backdropMode(mode) {
    const b = this.backdrop; if (!b) return; this.backMode = mode;
    // sunk so the painting's horizon (~58% down) sits at the ground line: the floor part stays hidden under the plaza
    const [H, lean, z0, y0] = mode === 'hub' ? [46, 8, -6, -18] : [32, 42, -6, -12];
    const a = -THREE.MathUtils.degToRad(lean);
    b.scale.set(H * 2, H, 1); b.rotation.set(a, 0, 0);
    b.position.set(9, y0 + H / 2 * Math.cos(a), z0 + H / 2 * Math.sin(a));
  }
  floater(kind) {
    if (this.floaters[kind] !== undefined) return this.floaters[kind];
    const col = (geo, hex) => { const c = new THREE.Color(hex), n = geo.attributes.position.count, a = new Float32Array(n * 3); for (let i = 0; i < n; i++) a.set([c.r, c.g, c.b], i * 3); geo.setAttribute('color', new THREE.BufferAttribute(a, 3)); return geo; };
    let geo, mat;
    if (kind === 'coins') { geo = new THREE.CylinderGeometry(0.16, 0.16, 0.04, 14); mat = new THREE.MeshStandardMaterial({color: '#ffc84a', metalness: 0.9, roughness: 0.25, emissive: '#5a3a00', emissiveIntensity: 0.4}); }
    else if (kind === 'ducks') {
      const body = col(new THREE.SphereGeometry(0.2, 12, 8).scale(1, 0.75, 1.3), '#ffd84a'), head = col(new THREE.SphereGeometry(0.12, 10, 8).translate(0, 0.16, 0.16), '#ffd84a'), beak = col(new THREE.ConeGeometry(0.05, 0.12, 8).rotateX(Math.PI / 2).translate(0, 0.15, 0.3), '#ff7a1a');
      geo = mergeGeometries([body, head, beak].map(x => x.toNonIndexed())); mat = new THREE.MeshStandardMaterial({vertexColors: true, roughness: 0.35});
    } else if (kind === 'cans') { geo = new THREE.CylinderGeometry(0.09, 0.09, 0.32, 12).rotateZ(Math.PI / 2); mat = new THREE.MeshStandardMaterial({color: '#3cff6a', metalness: 0.8, roughness: 0.3, emissive: '#0a4a14', emissiveIntensity: 0.5}); }
    else if (kind === 'ice') { geo = new THREE.CylinderGeometry(0.45, 0.5, 0.12, 6); mat = new THREE.MeshStandardMaterial({color: '#f2fbff', roughness: 0.2, metalness: 0.1}); }
    else if (kind === 'chips') { geo = new THREE.CylinderGeometry(0.15, 0.15, 0.05, 16); mat = new THREE.MeshStandardMaterial({color: '#ffffff', roughness: 0.4}); }
    else if (kind === 'capsules') {     // half white, half mint
      geo = new THREE.CapsuleGeometry(0.11, 0.24, 4, 10).rotateZ(Math.PI / 2); const n = geo.attributes.position.count, a = new Float32Array(n * 3), w = new THREE.Color('#f4fbf6'), g = new THREE.Color('#3ce88a');
      for (let i = 0; i < n; i++) { const c = geo.attributes.position.getX(i) > 0 ? g : w; a.set([c.r, c.g, c.b], i * 3); } geo.setAttribute('color', new THREE.BufferAttribute(a, 3));
      mat = new THREE.MeshStandardMaterial({vertexColors: true, roughness: 0.3});
    } else if (kind === 'cubes') { geo = new THREE.BoxGeometry(0.22, 0.22, 0.22); mat = new THREE.MeshStandardMaterial({color: '#0a2a3a', roughness: 0.4, emissive: '#27e8ff', emissiveIntensity: 1.1}); }
    else return (this.floaters[kind] = null);
    const I = new THREE.InstancedMesh(geo, mat, this.coinData.length); I.visible = false;
    if (kind === 'chips') { const cs = ['#d6243a', '#1a1a22', '#2a6aff', '#1aa84a', '#f2f2f2']; for (let i = 0; i < I.count; i++) I.setColorAt(i, new THREE.Color(cs[i % cs.length])); }
    this.root.add(I); return (this.floaters[kind] = I);
  }
  async applyTheme(id) {
    const T = this.theme = themeOf(id); this.themeId = id;
    // (an arena with a world in worlds.js gets that all round the court, in place of the plain ground and straight canal)
    const W = this.worldDef = WORLDS[id]; this.world.clear(); for (const o of this.plain) o.visible = !W;
    this.backdrop.visible = false;
    const px = this.stage.quality === 'low' ? 40 : 64;
    // the court and the ground around it (painted once per arena, then cached)
    const tc = this.texCache[id] ||= {...paintCourt(T, px), outer: paintOuter(T)};
    this.courtMat.map = tc.map; this.courtMat.normalMap = tc.nrm; this.courtMat.roughness = T.court.rough ?? (T.court.kind === 'marble' ? 0.5 : T.court.kind === 'ice' ? 0.45 : T.court.kind === 'deck' ? 0.65 : 0.85);
    const lit = T.court.selfLit || 0; this.courtMat.emissive.set(lit ? '#ffffff' : '#000000'); this.courtMat.emissiveMap = lit ? tc.map : null; this.courtMat.emissiveIntensity = lit || 1; this.courtMat.needsUpdate = true;
    // the ground: the arena's painted texture (assets/arenas/<id>/ground.webp + ground_n.webp), else one painted here
    const O = this.outerMat; O.map = tc.outer; tc.outer.repeat.set(1, 1); O.normalMap = null; O.color.set('#ffffff'); O.needsUpdate = true;
    this.groundMacro.value = T.outer.macro ?? 0.22; this.groundAnti.value = T.outer.anti ?? 1;
    this.groundTex(id).then(g => { if (!g || this.themeId !== id) return; O.map = g.map; O.normalMap = g.nrm; O.normalScale.set(0.9, 0.9); O.color.set(T.outer.tint || '#ffffff'); O.needsUpdate = true; });
    // the river
    const C = T.canal, U = this.poolMat.uniforms;
    U.uDeep.value.set(C.deep); U.uMid.value.set(C.mid); U.uHot.value.set(C.hot); U.uFoam.value.set(C.foam); U.uSpeed.value = C.speed; U.uMode.value = CANAL_MODE[C.mode] ?? 0; U.uSheen.value = C.sheen || 0; U.uWaves.value = C.waves || 0;
    for (const f of Object.values(this.floaters)) if (f) f.visible = false;
    this.floatKind = C.floaters; const F = this.floater(C.floaters); if (F) F.visible = true;
    // the neon frame: glowing at night, a painted line by day
    const [pc, ec, glow] = T.neon;
    (this.neonTubes || []).forEach((m, s) => m.color.set(s ? ec : pc).multiplyScalar(glow > 0.3 ? 1.15 : 0.8));
    this.neon.forEach((m, s) => { m.color.set(s ? ec : pc); m.opacity = 0.38 * glow; });
    // light, sky, fog, bloom
    this.stage.applyTheme(T);
    // the backdrop painting (falls back to a sky gradient)
    this.backdrop.visible = false;
    loadTex(`assets/arenas/${id}/backdrop.webp`).then(t => { if (this.themeId !== id) return; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; this.backMat.map = t; this.backMat.needsUpdate = true; this.backdrop.visible = true; }).catch(() => {});
    // the decoration kit: assets/arenas/<id>/layout.json, else the generic plaza dressing
    await this.loadKit(id);
  }
  groundTex(id) {
    const c = this.groundCache ||= {};
    return c[id] ||= (async () => {
      try {
        const [map, nrm] = await Promise.all([loadTex(`assets/arenas/${id}/ground.webp`), loadTex(`assets/arenas/${id}/ground_n.webp`).catch(() => null)]);
        for (const t of [map, nrm]) if (t) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; }
        map.colorSpace = THREE.SRGBColorSpace; return {map, nrm};
      } catch { return null; }
    })();
  }
  async loadKit(id) {
    this.root.remove(this.kit); this.kit = new THREE.Group(); this.root.add(this.kit); this.anims = [];
    const base = `assets/arenas/${id}/`; let layout = null;
    try { const r = await fetch(base + 'layout.json'); if (r.ok) layout = await r.json(); } catch {}
    if (this.themeId !== id) return;
    for (const c of this.curbs) c.visible = !layout;
    if (!layout?.length) { this.kitBridge = null; this.bridgeFrom(null); return this.dress(this.kit); }
    const W = this.worldDef;
    // (the court's own frame and bridges stay as they are; the rest of the kit goes on the terraces)
    let rest = [];
    if (W) { this.world.build(id, W, this.theme); const frame = p => p.p === 'bridge' || /_frame$|^edge_/.test(p.p); if (W.kit !== false) rest = layout.filter(p => !frame(p) && !W.drop?.includes(p.p)); layout = layout.filter(frame); }
    const names = [...new Set(layout.map(p => p.p))], glbs = {};
    await Promise.all(names.map(async n => { try { glbs[n] = await loadGLB(base + 'props/' + n + '.glb'); } catch {} }));
    if (this.themeId !== id) return;
    for (const p of layout) {
      const g = glbs[p.p]; if (!g || p.p === 'bridge') continue;
      // (a twin centred in front of my Battlestation would hide it and the crew in the hub view: it steps aside)
      const px = p.z > 33 && Math.abs(p.x - 9) < 3 ? 9 + (p.x >= 9 ? 5.8 : -5.8) : p.x;
      const o = cloneGLB(g).scene; o.position.set(px, p.y || 0, p.z); o.rotation.y = p.ry || 0; o.scale.setScalar(p.s || 1);
      const big = (p.s || 1) * 1 > 0.6;
      o.traverse(n => {
        if (n.isMesh) { n.castShadow = this.stage.quality !== 'low' && big; n.receiveShadow = true; }
        const m = /^(anim_spin|anim_bob|anim_sway|fx_smoke|fx_glow)/.exec(n.name || ''); if (!m) return;
        this.anims.push({o: n, kind: m[1], y: n.position.y, rz: n.rotation.z, ph: Math.random() * 6.28, mats: n.isMesh ? [].concat(n.material) : []});
      });
      if (W) this.world.dressKit(o);
      this.kit.add(o);
    }
    this.kitBridge = glbs.bridge || null; this.bridgeFrom(this.kitBridge);
    if (W) { await this.world.place(id, base, this.kit, rest); if (this.themeId !== id) return; if (W.scatter !== false) await this.scatter(id, base, [...layout, ...rest, ...(W.props || [])], glbs); return; }
    await this.scatter(id, base, layout, glbs);
  }
  // the ground around the court, dressed: the kit's small pieces strewn about (instanced: one draw per piece's mesh), thick
  // near the court and thinning out, never in the river, on the kit's own pieces or in the hub's view of my Battlestation
  async scatter(id, base, layout, glbs) {
    const S0 = this.worldDef?.scatterList || this.theme.scatter; if (!S0?.length) return;
    const S = S0.map(n => n.replace('!', '')), full = new Set(S0.filter(n => n.endsWith('!')).map(n => n.slice(0, -1)));   // 'name!': keeps its size
    await Promise.all([...new Set(S)].filter(n => !glbs[n]).map(async n => { try { glbs[n] = await loadGLB(base + 'props/' + n + '.glb'); } catch {} }));
    if (this.themeId !== id) return;
    const kinds = S.filter(n => glbs[n]); if (!kinds.length) return;
    const q = this.stage.quality, world = this.worldDef ? this.world : null, cap = (q === 'low' ? 45 : q === 'mid' ? 90 : 130) * (world ? 1.4 * (this.worldDef.scatterK ?? 1) : 1);
    let seed = [...id].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 7); const R = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
    const out = (x, z) => Math.hypot(Math.max(-2.6 - x, 0, x - 20.6), Math.max(-2.6 - z, 0, z - 34.6));
    // clumps, not confetti: a centre, one main piece repeated round it and the odd other one
    const pts = [], free = (x, z, r) => {
      const d = out(x, z);
      if (d <= 0.2 || (x > -1 && x < 19 && z > 32 && z < 52) || (world ? world.yAt(x, z) === null : z > 13.4 && z < 18.6)) return false;
      return !pts.some(p => (p.x - x) ** 2 + (p.z - z) ** 2 < (r + p.r) ** 2 * 0.8) && !layout.some(p => (p.x - x) ** 2 + (p.z - z) ** 2 < (r + 1.7) ** 2);
    };
    for (let k = 0; k < 4000 && pts.length < cap; k++) {
      const cx = -32 + R() * 82, cz = -22 + R() * 76, d = out(cx, cz);
      if (d <= 0 || R() > (d < 5 ? 1 : d < 12 ? 0.55 : 0.22)) continue;
      const main = kinds[Math.floor(R() * kinds.length)], n = 2 + Math.floor(R() * (d < 8 ? 5 : 3)), spread = 1.2 + R() * 1.6;
      for (let i = 0; i < n && pts.length < cap; i++) {
        const a = R() * Math.PI * 2, rr = i ? spread * (0.5 + R() * 0.7) : 0, x = cx + Math.cos(a) * rr, z = cz + Math.sin(a) * rr, r = 0.75 + R() * 0.35;
        if (!free(x, z, r)) continue;
        pts.push({x, z, r, kind: R() < 0.78 ? main : kinds[Math.floor(R() * kinds.length)], ry: R() * Math.PI * 2, s: (i ? 0.7 : 0.95) + R() * 0.3});
      }
    }
    const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0), box = new THREE.Box3();
    // a hundred shiny coins would drown the court in bloom: set dressing sits a little darker than the court and keeps only a hint of glow
    const k = this.theme.scatterDim ?? 0.88, dimmed = new Map(), dim = m => {
      if (!m?.color) return m;
      if (!dimmed.has(m)) { const c = m.clone(); c.userData = {...c.userData, worldLit: false}; c.color.multiplyScalar(k); c.envMapIntensity = (c.envMapIntensity ?? 1) * k; if (c.emissive) c.emissiveIntensity = Math.min(c.emissiveIntensity, 0.12); dimmed.set(m, c); }
      return dimmed.get(m);
    };
    for (const kind of new Set(pts.map(p => p.kind))) {
      const at = pts.filter(p => p.kind === kind), sc = glbs[kind].scene; sc.updateMatrixWorld(true);
      box.setFromObject(sc); const size = box.getSize(new THREE.Vector3()), foot = Math.max(size.x, size.z, 0.01), s0 = Math.min(1, (full.has(kind) ? 5.5 : 2.6) / foot);
      sc.traverse(n => {
        if (!n.isMesh || /^fx_/.test(n.name || '')) return;
        const I = new THREE.InstancedMesh(n.geometry, Array.isArray(n.material) ? n.material.map(dim) : dim(n.material), at.length);
        at.forEach((p, i) => { M.compose(V.set(p.x, world ? world.heightAt(p.x, p.z) : 0, p.z), Q.setFromAxisAngle(Y, p.ry), new THREE.Vector3().setScalar(s0 * p.s)).multiply(n.matrixWorld); I.setMatrixAt(i, M); });
        I.castShadow = !world && q !== 'low' && size.y * s0 > 1.2; I.receiveShadow = true; I.computeBoundingSphere(); this.kit.add(I);
        if (world) world.dressKit(I);
      });
    }
  }
  bridgeFrom(glb) {
    const use = glb || this.defaultBridge; if (!use) return;
    for (const b of this.bridges) { b.clear(); const g = cloneGLB(use).scene; g.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; this.tintTeam(o, null); } }); b.add(g); }
  }
  // the kit's living parts and the arena's ambient particles
  animate(dt) {
    const t = this.time;
    for (const a of this.anims) {
      if (a.kind === 'anim_spin') a.o.rotation.y += dt * 1.6;
      else if (a.kind === 'anim_bob') a.o.position.y = a.y + Math.sin(t * 2 + a.ph) * 0.12;
      else if (a.kind === 'anim_sway') a.o.rotation.z = a.rz + Math.sin(t * 1.2 + a.ph) * 0.06;
      else if (a.kind === 'fx_glow') for (const m of a.mats) if (m.emissive) m.emissiveIntensity = 1.2 + Math.sin(t * 3 + a.ph) * 0.5;
      else if (a.kind === 'fx_smoke' && this.fx && Math.random() < dt * 6) { const w = a.o.getWorldPosition(new THREE.Vector3()); this.fx.norm.emit({x: w.x + (Math.random() - 0.5) * 0.3, y: w.y, z: w.z, vy: 0.9 + Math.random() * 0.6, vx: 0.2, life: 2.2, s0: 0.6, s1: 1.8, c: [0.8, 0.8, 0.85], a0: 0.35, cell: 3}); }
    }
    if (this.worldDef) { this.world.update(dt, t, this.fx); return; }
    const P = this.theme?.particles; if (!P || P === 'none' || !this.fx) return;
    const r = Math.random, fx = this.fx;
    if (P === 'snow' && r() < dt * 40) fx.norm.emit({x: -4 + r() * 26, y: 9, z: -4 + r() * 38, vx: 0.3, vy: -1.2, life: 7, s0: 0.22, s1: 0.22, c: [1, 1, 1], a0: 0.9, a1: 0.8, cell: 0, floor: 0.02});
    else if ((P === 'dust' || P === 'pollen') && r() < dt * 8) fx.add.emit({x: r() * 18, y: 0.5 + r() * 3, z: r() * 32, vx: (r() - 0.5) * 0.2, vy: 0.05, life: 5, s0: 0.12, s1: 0.12, c: P === 'dust' ? [1, 0.85, 0.6] : [1, 0.95, 0.5], a0: 0.5, a1: 0, cell: 0});
    else if (P === 'sparkle' && r() < dt * 10) fx.add.emit({x: r() < 0.5 ? -1 - r() * 3 : 19 + r() * 3, y: 0.3 + r() * 2.5, z: r() * 32, life: 0.8, s0: 0.35, s1: 0, c: [1, 0.85, 0.4], cell: 1});
    else if (P === 'stars' && r() < dt * 4) fx.add.emit({x: -10 + r() * 38, y: 6 + r() * 10, z: -12 + r() * 10, life: 1.6, s0: 0, s1: 0.5, c: [1, 1, 1], a0: 1, a1: 0, cell: 1});
    else if (P === 'bubbles' && r() < dt * 10) fx.add.emit({x: -4 + r() * 26, y: 0.2, z: -2 + r() * 36, vx: (r() - 0.5) * 0.15, vy: 0.7 + r() * 0.5, life: 4.5, s0: 0.1, s1: 0.2, c: [0.65, 0.9, 1], a0: 0.45, a1: 0, cell: 0});
    else if (P === 'wisps' && r() < dt * 7) fx.add.emit({x: r() < 0.5 ? -0.5 - r() * 3 : 18.5 + r() * 3, y: 0.3 + r() * 1.5, z: r() * 32, vx: (r() - 0.5) * 0.3, vy: 0.12, life: 4, s0: 0.2, s1: 0.5, c: [0.2, 0.95, 0.8], a0: 0.4, a1: 0, cell: 0});
    else if (P === 'embers' && r() < dt * 12) fx.add.emit({x: -2 + r() * 22, y: 0.1, z: 14.8 + r() * 2.4, vx: (r() - 0.5) * 0.4, vy: 0.9 + r() * 0.9, life: 2.2, s0: 0.14, s1: 0.03, c: [1, 0.55, 0.15], a0: 0.9, a1: 0, cell: 0});
    else if (P === 'glitch' && r() < dt * 9) fx.add.emit({x: r() < 0.5 ? -0.5 - r() * 3 : 18.5 + r() * 3, y: 0.4 + r() * 3, z: r() * 32, life: 0.5, s0: 0.3, s1: 0.3, c: r() < 0.5 ? [0.15, 0.9, 1] : [1, 0.25, 0.85], a0: 0.9, a1: 0, cell: 0});
  }

  // ---------- towers
  // hub: the hub's dressing, where the camera looks at my Battlestation from behind my side of the arena
  async buildTowers(battle, neetFactory, guardFactory, hub = false) {
    let rigGLB = null, hqGLB = null, rigRuin = null, hqRuin = null;
    try { [rigGLB, hqGLB, rigRuin, hqRuin] = await Promise.all(['tower_rig', 'battlestation', 'tower_rig_ruin', 'battlestation_ruin'].map(n => loadGLB(`assets/arena/${n}.glb`).catch(() => null))); } catch {}
    for (let s = 0; s < 2; s++) for (const e of battle.towers[s]) {
      const T = e.type === 'hq' ? (hqGLB ? this.fromGLB(hqGLB, s) : this.placeholderHQ(s)) : (rigGLB ? this.fromGLB(rigGLB, s) : this.placeholderRig(s));
      T.group.position.set(e.x, 0, e.z); T.group.scale.setScalar(TOWER_VIS);
      // (a Battlestation's front, the NEET on his throne, faces the enemy in a battle; in the hub it faces the camera)
      if ((s === 1) !== (e.type === 'hq' && !hub)) T.group.rotation.y = Math.PI;
      T.ruinSrc = e.type === 'hq' ? hqRuin : rigRuin;
      T.ent = e; T.team = s; T.type = e.type; T.aim = s === 0 ? Math.PI : 0;
      this.root.add(T.group); this.towers[s].push(T);
      if (e.dead) { this.ruin(T, true); continue; }   // (a battle shown again, a reload: a tower that fell before is a ruin, no guard)
      if (e.type === 'hq' && neetFactory) neetFactory(T, s);
      if (e.type !== 'hq' && guardFactory) guardFactory(T, s);
    }
    try { this.defaultBridge = await loadGLB('assets/arena/bridge.glb'); if (!this.kitBridge) this.bridgeFrom(null); } catch {}
  }
  tintTeam(o, s) {
    if (!/^team/i.test(o.name || '') && !/^team/i.test(o.parent?.name || '')) return;
    const col = s == null ? new THREE.Color('#7CFF6B') : TEAM_COL[s], M = o.material = o.material.clone();
    if (/^team_(paint|cloth)/i.test(o.name || '') || /^team_(paint|cloth)/i.test(o.parent?.name || '')) {
      M.color = (s == null ? col : TEAM_PAINT[s]).clone(); M.emissive = new THREE.Color(0); M.emissiveIntensity = 0; M.roughness = 0.75; M.metalness = 0; M.side = THREE.DoubleSide;
      return;
    }
    M.color = col.clone().multiplyScalar(0.6); M.emissive = col.clone(); M.emissiveIntensity = 1.15;
    (this.teamMats ||= []).push({m: o.material, s});
  }
  fromGLB(glb, s) {
    const g = cloneGLB(glb).scene, T = {group: new THREE.Group()};
    T.group.add(g);
    g.traverse(o => {
      if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; this.tintTeam(o, s); if (o.name === 'screens' || o.parent?.name === 'screens') T.screens = o; }
      if (o.name === 'turret') T.turret = o; if (o.name === 'muzzle') T.muzzle = o; if (o.name === 'seat') T.seat = o;
    });
    return T;
  }
  teamBand(radius, y, s, h = 0.12) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, h, 28, 1, true), new THREE.MeshStandardMaterial({color: TEAM_COL[s].clone().multiplyScalar(0.4), emissive: TEAM_COL[s], emissiveIntensity: 2.0, side: THREE.DoubleSide}));
    m.position.y = y; return m;
  }
  placeholderRig(s) {
    const T = {group: new THREE.Group()}, g = T.group;
    const conc = concreteTexture(); conc.repeat.set(3, 1.5);
    const cm = new THREE.MeshStandardMaterial({map: conc, color: '#9aa0aa', roughness: 0.85});
    const dark = new THREE.MeshStandardMaterial({color: '#1d2129', metalness: 0.6, roughness: 0.45});
    const base = new THREE.Mesh(new THREE.CylinderGeometry(1.45, 1.6, 1.1, 8), cm); base.position.y = 0.55; g.add(base);
    // stacked rig cases with fan rings
    for (let k = 0; k < 2; k++) {
      const box = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.85, 2.2), dark); box.position.y = 1.55 + k * 0.9; box.rotation.y = k * 0.06; g.add(box);
      for (const [fx, fz, ry] of [[0, 1.11, 0], [0, -1.11, Math.PI], [1.11, 0, Math.PI / 2], [-1.11, 0, -Math.PI / 2]]) for (const o of [-0.55, 0, 0.55]) {
        const fan = new THREE.Mesh(new THREE.RingGeometry(0.12, 0.2, 16), new THREE.MeshStandardMaterial({color: TEAM_COL[s], emissive: TEAM_COL[s], emissiveIntensity: 1.6, side: THREE.DoubleSide}));
        fan.position.set(fx + (ry === 0 || ry === Math.PI ? o : 0), 1.55 + k * 0.9, fz + (ry === 0 || ry === Math.PI ? 0 : o)); fan.rotation.y = ry; g.add(fan);
      }
    }
    const deck = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.35, 0.3, 8), cm); deck.position.y = 3.15; g.add(deck);
    for (let k = 0; k < 8; k++) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.34, 0.25), cm); const a = k / 8 * Math.PI * 2 + Math.PI / 8; m.position.set(Math.sin(a) * 1.32, 3.45, Math.cos(a) * 1.32); m.rotation.y = a; g.add(m); }
    g.add(this.teamBand(1.47, 1.08, s));
    const turret = new THREE.Group(); turret.position.y = 3.3;
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.45, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), dark); turret.add(head);
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.14, 0.9, 10), dark); barrel.rotation.x = Math.PI / 2; barrel.position.set(0, 0.28, 0.45); turret.add(barrel);
    const lens = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 8), new THREE.MeshStandardMaterial({color: TEAM_COL[s], emissive: TEAM_COL[s], emissiveIntensity: 3})); lens.position.set(0, 0.28, 0.92); turret.add(lens);
    const muzzle = new THREE.Object3D(); muzzle.position.set(0, 0.28, 0.95); turret.add(muzzle);
    g.add(turret); T.turret = turret; T.muzzle = muzzle;
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return T;
  }
  placeholderHQ(s) {
    const T = {group: new THREE.Group()}, g = T.group;
    const conc = concreteTexture(); conc.repeat.set(4, 2);
    const cm = new THREE.MeshStandardMaterial({map: conc, color: '#8f96a2', roughness: 0.85});
    const dark = new THREE.MeshStandardMaterial({color: '#1b1f27', metalness: 0.5, roughness: 0.5});
    const base = new THREE.Mesh(new THREE.BoxGeometry(3.7, 2.6, 3.7), cm); base.position.y = 1.3; g.add(base);
    const top = new THREE.Mesh(new THREE.BoxGeometry(4.0, 0.35, 4.0), cm); top.position.y = 2.75; g.add(top);
    for (let k = 0; k < 4; k++) for (let q = -1; q <= 1; q++) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.4, 0.3), cm); const a = k * Math.PI / 2; m.position.set(Math.sin(a) * 1.85 + Math.cos(a) * q * 1.2, 3.1, Math.cos(a) * 1.85 - Math.sin(a) * q * 1.2); m.rotation.y = a; g.add(m); }
    // monitors facing the camera side
    const scr = new THREE.MeshStandardMaterial({color: '#051a0b', emissive: s === 0 ? '#3cff6a' : '#ff3b5c', emissiveIntensity: 1.2});
    for (const x of [-1.05, 0, 1.05]) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.6, 0.06), [dark, dark, dark, dark, scr, dark]); m.position.set(x, 1.75, 1.88); m.rotation.y = 0; g.add(m); }
    // throne
    const chair = new THREE.Group(); chair.position.set(0, 2.92, -0.3);
    const seatM = new THREE.MeshStandardMaterial({color: '#20242c', roughness: 0.6});
    const cs = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.18, 0.9), seatM); cs.position.y = 0.4; chair.add(cs);
    const cb = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.25, 0.18), seatM); cb.position.set(0, 1.05, -0.45); chair.add(cb);
    const stripe = new THREE.Mesh(new THREE.BoxGeometry(0.22, 1.2, 0.02), new THREE.MeshStandardMaterial({color: TEAM_COL[s], emissive: TEAM_COL[s], emissiveIntensity: 1.8})); stripe.position.set(0, 1.05, -0.35); chair.add(stripe);
    g.add(chair);
    const seat = new THREE.Object3D(); seat.position.set(0, 3.38, -0.25); g.add(seat); T.seat = seat;
    g.add(this.teamBand(2.0, 2.58, s, 0.14).translateY(0)); g.children.at(-1).scale.set(1, 1, 1);
    const turret = new THREE.Group(); turret.position.set(1.45, 2.95, 1.25);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.4, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), dark); turret.add(head);
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 0.8, 10), dark); barrel.rotation.x = Math.PI / 2; barrel.position.set(0, 0.25, 0.4); turret.add(barrel);
    const muzzle = new THREE.Object3D(); muzzle.position.set(0, 0.25, 0.85); turret.add(muzzle);
    g.add(turret); T.turret = turret; T.muzzle = muzzle;
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return T;
  }
  clearTowers() { for (const s of this.towers) for (const T of s) this.root.remove(T.group); this.towers = [[], []]; this.teamMats = []; }
  towerOf(ent) { for (const s of this.towers) for (const T of s) if (T.ent === ent) return T; return null; }
  muzzleWorld(T, out = new THREE.Vector3()) { if (T.muzzle) return T.muzzle.getWorldPosition(out); return out.set(T.ent.x, T.ent.h - 0.4, T.ent.z); }
  // the fall: the tower shudders, then crumbles down (sinking, squashing, tipping) while its rubble rises out of the dust;
  // now: it fell while this page was not looking (a reload, a dropped line): the rubble at once, no fall
  ruin(T, now = false) {
    if (T.ruined) return; T.ruined = true;
    const old = T.group; const p = old.position.clone(), ry = old.rotation.y;
    let g;
    if (T.ruinSrc) { g = cloneGLB(T.ruinSrc).scene; g.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; } }); }
    else {
      g = new THREE.Group();
      const m = new THREE.MeshStandardMaterial({color: '#4a4e57', roughness: 0.95}), d = new THREE.MeshStandardMaterial({color: '#1c1f26', roughness: 0.7, metalness: 0.4});
      for (let k = 0; k < 16; k++) { const s = 0.25 + Math.random() * 0.55; const b = new THREE.Mesh(new THREE.DodecahedronGeometry(s, 0), k % 3 ? m : d);
        const a = Math.random() * Math.PI * 2, r = Math.random() * (T.type === 'hq' ? 1.8 : 1.3); b.position.set(Math.sin(a) * r, s * 0.6, Math.cos(a) * r); b.rotation.set(Math.random() * 3, Math.random() * 3, 0); b.castShadow = b.receiveShadow = true; g.add(b); }
    }
    g.scale.setScalar(TOWER_VIS); const R = new THREE.Group(); R.add(g); R.position.copy(p); R.rotation.y = ry; R.scale.set(1, 0.01, 1); this.root.add(R);
    T.turret = null; T.seat = null;
    if (now) { R.scale.y = 1; this.root.remove(old); T.group = R; return; }
    T.fall = {t: 0, old, R, tip: Math.random() < 0.5 ? -1 : 1, base: p.clone()};
  }
  fallStep(T, dt) {
    const F = T.fall; F.t += dt; const k = F.t, o = F.old;
    if (k < 0.28) { o.position.set(F.base.x + (Math.random() - 0.5) * 0.25, 0, F.base.z + (Math.random() - 0.5) * 0.25); }
    else {
      const q = Math.min(1, (k - 0.28) / 0.75), e = q * q;
      o.position.set(F.base.x, -e * 2.2, F.base.z); o.scale.set(1 + e * 0.25, Math.max(0.05, 1 - e * 0.85), 1 + e * 0.25).multiplyScalar(TOWER_VIS); o.rotation.z = e * 0.35 * F.tip; o.rotation.x = e * 0.12;
    }
    const r = Math.min(1, Math.max(0, (k - 0.45) / 0.55)); F.R.scale.y = 0.01 + (1 - (1 - r) ** 3) * 0.99;
    if (k > 1.1) { this.root.remove(o); T.group = F.R; T.fall = null; }   // (materials are shared with the template: not disposed)
  }

  // ---------- dressing (props, loaded lazily)
  async dress(parent = this.root) {
    const P = (name, x, z, ry = 0, s = 1) => ({name, x, z, ry, s});
    const L = [
      P('chainlink_fence', -1.4, 4, Math.PI / 2), P('chainlink_fence', -1.4, 10, Math.PI / 2), P('chainlink_fence', -1.4, 22, Math.PI / 2), P('chainlink_fence', -1.4, 28, Math.PI / 2),
      P('chainlink_fence', 19.4, 4, -Math.PI / 2), P('chainlink_fence', 19.4, 10, -Math.PI / 2), P('chainlink_fence', 19.4, 22, -Math.PI / 2), P('chainlink_fence', 19.4, 28, -Math.PI / 2),
      P('street_lamp_01', -0.95, 13.6, Math.PI / 2), P('street_lamp_01', 18.95, 18.4, -Math.PI / 2), P('street_lamp_01', -0.95, 1.2, Math.PI / 2), P('street_lamp_01', 18.95, 30.8, -Math.PI / 2),
      P('barrel_01', -2.3, 7.2, 0.4), P('barrel_02', -2.9, 7.9, 1.2), P('wooden_crate_02', -2.6, 19.5, 0.3), P('plastic_crate_01', -2.2, 20.6, 1.0), P('trashbag', -2.0, 26.2, 0),
      P('old_tyre', 20.3, 7.6, 0.5), P('cardboard_box_01', 20.1, 13.0, 0.7), P('metal_trash_can', 20.4, 24.2, 0), P('fire_hydrant', 20.1, 27.4, 0.4), P('propane_tank', 20.6, 3.6, 0),
      P('utility_box_01', -2.4, 30.2, Math.PI / 2),
      P('bull_head', -4.2, 24, Math.PI / 2, 1.6), P('bronze_whale_statue', 22.6, 9, -Math.PI / 2, 1.2), P('treasure_chest', 21.6, 15.0, -Math.PI / 2), P('boombox', -2.5, 16.8, Math.PI / 2),
      P('street_tree_01', -5, 2, 0, 1.2), P('street_tree_01', -5.5, 13, 1, 1.3), P('street_tree_01', 23.5, 21, 2, 1.25), P('street_tree_01', 23, 31, 0.5, 1.2), P('street_tree_01', -5, 33.5, 0.3, 1.2),
      P('street_bench', 21.4, 19.6, -Math.PI / 2), P('street_bench', -3.4, 9.6, Math.PI / 2), P('wet_floor_sign_01', 19.6, 14.4, 0.3), P('payphone', -3.0, 3.6, Math.PI / 2), P('megaphone', 20.2, 16.2, -1),
      P('concrete_road_barrier', 9, -2.2, 0, 1.0), P('concrete_road_barrier', 5, -2.0, 0.08), P('concrete_road_barrier', 13, -2.0, -0.08),
    ];
    const names = [...new Set(L.map(p => p.name))];
    const cache = {};
    await Promise.all(names.map(async n => { try { cache[n] = await loadGLB(`assets/props/${n}.glb`); } catch {} }));
    for (const p of L) {
      const glb = cache[p.name]; if (!glb) continue;
      const g = cloneGLB(glb).scene; g.position.set(p.x, 0, p.z); g.rotation.y = p.ry; g.scale.setScalar(PROP_SCALE * p.s);
      g.traverse(o => { if (o.isMesh) { o.castShadow = this.stage.quality === 'high'; o.receiveShadow = true; } });
      parent.add(g);
    }
    // lamp glows
    for (const [x, z] of [[-0.95, 13.6], [18.95, 18.4], [-0.95, 1.2], [18.95, 30.8]]) parent.add(this.glow(x, 3.5, z, '#ffd9a0', 2.4));
  }
  glow(x, y, z, col, s) {
    if (!Arena.glowTex) { const [c, g] = canvas(128, 128); const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.2, 'rgba(255,255,255,0.5)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); Arena.glowTex = new THREE.CanvasTexture(c); }
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: Arena.glowTex, color: col, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.85}));
    sp.position.set(x, y, z); sp.scale.set(s, s, 1); return sp;
  }

  // ---------- placement overlay
  overlay() {
    const data = new Uint8Array(18 * 32 * 4);
    const tex = this.maskTex = new THREE.DataTexture(data, 18, 32); tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.NearestFilter; tex.flipY = false; tex.needsUpdate = true;
    const g = new THREE.PlaneGeometry(18, 32); g.rotateX(-Math.PI / 2);
    // uv.y = 0 at z = 32 by default after rotation: flip so texel row j is z = j
    const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
    this.mask = new THREE.Mesh(g, new THREE.MeshBasicMaterial({map: tex, transparent: true, depthWrite: false, opacity: 0}));
    this.mask.position.set(9, 0.03, 16); this.mask.renderOrder = 2; this.root.add(this.mask);
    // ghost marker: a tile square + a ring (spell radius / formation)
    const sq = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({color: '#ffffff', transparent: true, opacity: 0.55, depthWrite: false}));
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 64).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({color: '#ffffff', transparent: true, opacity: 0.8, depthWrite: false}));
    const disc = new THREE.Mesh(new THREE.CircleGeometry(1, 64).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({color: '#ffffff', transparent: true, opacity: 0.12, depthWrite: false}));
    this.ghost = new THREE.Group(); this.ghost.add(sq, ring, disc); this.ghost.visible = false; this.ghost.position.y = 0.05; this.ghost.renderOrder = 3;
    this.ghostParts = {sq, ring, disc}; this.root.add(this.ghost);
  }
  showMask(battle, team, card) {
    const d = this.maskTex.image.data;
    for (let j = 0; j < 32; j++) for (let i = 0; i < 18; i++) {
      const bad = battle.canPlace(team, card, i + 0.5, j + 0.5), p = (j * 18 + i) * 4;
      const river = j >= 15 && j < 17;
      d[p] = 255; d[p + 1] = 40; d[p + 2] = 70; d[p + 3] = bad && !river && bad !== 'tower' ? 92 : 0;
    }
    this.maskTex.needsUpdate = true; this.maskFade = 1;
  }
  hideMask() { this.maskFade = -1; }
  setGhost(x, z, {ok, radius, unit}) {
    const G = this.ghost; G.visible = true; G.position.x = x; G.position.z = z;
    const col = ok ? '#ffffff' : '#ff4d6d';
    for (const m of Object.values(this.ghostParts)) m.material.color.set(col);
    this.ghostParts.sq.visible = !!unit;
    this.ghostParts.ring.visible = this.ghostParts.disc.visible = radius > 0;
    if (radius > 0) { this.ghostParts.ring.scale.setScalar(radius); this.ghostParts.disc.scale.setScalar(radius); }
  }
  hideGhost() { this.ghost.visible = false; }

  update(dt) {
    this.time += dt;
    this.poolMat.uniforms.uT.value = this.time;
    // the floaters drift down the river
    const F = this.floaters[this.floatKind];
    if (F) {
      const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(1, 1, 1), p = new THREE.Vector3(), slow = this.floatKind === 'ice' ? 0.25 : 1;
      this.coinData.forEach((c, i) => {
        c.x += dt * c.s * slow; if (c.x > 30) c.x = -12;
        p.set(c.x, -0.36 + Math.sin(this.time * 2 + c.w) * 0.03, c.z);
        if (this.floatKind === 'ducks') e.set(Math.sin(this.time * 1.7 + c.r) * 0.12, Math.PI / 2 + Math.sin(this.time * 0.5 + c.w) * 0.6, 0);
        else if (this.floatKind === 'ice') e.set(0, c.r + this.time * 0.05, 0);
        else e.set(Math.sin(this.time + c.r) * 0.3, this.time * 0.6 + c.r, Math.PI / 2 * 0.15);
        q.setFromEuler(e); sc.setScalar(c.k); m.compose(p, q, sc); F.setMatrixAt(i, m);
      });
      F.instanceMatrix.needsUpdate = true;
    }
    this.animate(dt);
    if (this.maskFade) { const o = this.mask.material.opacity + this.maskFade * dt * 6; this.mask.material.opacity = Math.max(0, Math.min(1, o)); if (o <= 0 || o >= 1) this.maskFade = 0; }
    this.stage.poolLight.intensity = (this.stage.poolBase ?? 13) + Math.sin(this.time * 1.7) * 2;
    // turrets track their aim; monitors flicker; fallen towers crumble
    for (const side of this.towers) for (const T of side) {
      if (T.fall) this.fallStep(T, dt);
      if (T.turret && T.ent && !T.ent.dead) {
        const want = (T.ent.target ? T.ent.aim : (T.team === 0 ? Math.PI : 0)) - T.group.rotation.y;
        let d = want - T.turret.rotation.y; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2;
        T.turret.rotation.y += d * Math.min(1, dt * 9);
      }
    }
  }
}
