// The effects kit: the pieces every effect is drawn with, so they all share one look. A tileable noise texture (made once at
// load); sprites (instanced quads: flame tongues, lit smoke puffs that fray as they age, glows, sparks streaked along their
// motion, energy wisps, bubbles, crystal shards, the atlas's icons); ground marks (scorch with cooling ember cracks, a shock
// front of thrown dust, light pools, stains, frost, cracks, swirls), every edge torn by the noise, never a clean circle;
// ribbons (trails). Everything is drawn premultiplied (ONE, ONE_MINUS_SRC_ALPHA): one material both glows (alpha 0) and
// covers (alpha 1), so fire and its smoke go in one batch. Ages are normalised (k = age / life, 0..1) and the shaders shape
// on k, so every layer of an effect can be driven from one envelope.
import * as THREE from 'three';

// ---- noise: R and G two fbm octaves sets (periods 4 and 8), B cellular distance (F1), A cell edges (F2 - F1); all tile
export function noiseTexture(S = 256) {
  let seed = 7331; const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const p = [...Array(256).keys()]; for (let i = 255; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; }
  const perm = new Uint16Array(1024); for (let i = 0; i < 1024; i++) perm[i] = p[i & 255];
  const gx = new Float32Array(256), gy = new Float32Array(256); for (let i = 0; i < 256; i++) { const a = rand() * Math.PI * 2; gx[i] = Math.cos(a); gy[i] = Math.sin(a); }
  const fade = t => t * t * t * (t * (t * 6 - 15) + 10), wrap = (i, P) => ((i % P) + P) % P;
  const g = (ix, iy, P, o, x, y) => { const h = perm[perm[wrap(ix, P) + o] + wrap(iy, P)]; return gx[h] * x + gy[h] * y; };
  const perlin = (x, y, P, o) => { const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy, u = fade(fx), v = fade(fy);
    const a = g(ix, iy, P, o, fx, fy), b = g(ix + 1, iy, P, o, fx - 1, fy), c = g(ix, iy + 1, P, o, fx, fy - 1), d = g(ix + 1, iy + 1, P, o, fx - 1, fy - 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
  const fbm = (x, y, P0, o) => { let s = 0, amp = 0.5, P = P0; for (let i = 0; i < 5; i++) { s += amp * perlin(x * P, y * P, P, (o + i * 37) & 511); amp *= 0.5; P *= 2; } return s; };
  const G = 8, fp = new Float32Array(G * G * 2); for (let i = 0; i < G * G * 2; i++) fp[i] = rand();
  const d = new Uint8Array(S * S * 4), b = v => Math.max(0, Math.min(255, Math.round(v * 255)));
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const u = x / S, v = y / S, i = (y * S + x) * 4;
    d[i] = b(fbm(u, v, 4, 0) * 0.85 + 0.5); d[i + 1] = b(fbm(u, v, 8, 101) * 0.85 + 0.5);
    const cx = u * G, cy = v * G, ix = Math.floor(cx), iy = Math.floor(cy); let f1 = 9, f2 = 9;
    for (let oy = -1; oy <= 1; oy++) for (let ox = -1; ox <= 1; ox++) {
      const jx = ix + ox, jy = iy + oy, k = (wrap(jy, G) * G + wrap(jx, G)) * 2, dx = jx + fp[k] - cx, dy = jy + fp[k + 1] - cy, dd = Math.hypot(dx, dy);
      if (dd < f1) { f2 = f1; f1 = dd; } else if (dd < f2) f2 = dd;
    }
    d[i + 2] = b(f1 / 1.1); d[i + 3] = b((f2 - f1) / 0.9);
  }
  const t = new THREE.DataTexture(d, S, S, THREE.RGBAFormat);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true; t.needsUpdate = true;
  return t;
}

const PREMUL = {transparent: true, depthWrite: false, blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
  blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor};
const OUT = `float a = clamp(cov, 0., 1.) * vCol.a; if (a < .002) discard; gl_FragColor = vec4(rgb * a, a * (1. - vAdd));
  #include <tonemapping_fragment>
  #include <colorspace_fragment>`;

// ---- sprites
export const S = {GLOW: 0, FLAME: 1, SMOKE: 2, SPARK: 3, ICON: 4, WISP: 5, BUBBLE: 6, SHARD: 7, FLARE: 8};
const SVS = `uniform float uTime; attribute vec3 iPos; attribute vec3 iVel; attribute vec4 iSize; attribute vec4 iCol; attribute vec4 iPar;
  varying vec2 vUv; varying vec4 vCol; varying vec4 vPar; varying float vAdd; varying float vY;
  void main() {
    vUv = position.xy + .5; vCol = iCol; vPar = iPar; vAdd = iSize.w;
    vec3 R = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]), U = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
    vec2 q;
    if (abs(iPar.x - 3.) < .5) {   // a spark: drawn along its motion on screen, longer the faster (iSize.z: seconds of streak)
      vec2 v = vec2(dot(iVel, R), dot(iVel, U)); float L = length(v); vec2 d = L > 1e-4 ? v / L : vec2(0., 1.);
      q = d * position.y * (iSize.x + L * iSize.z) + vec2(d.y, -d.x) * position.x * iSize.y;
    } else { float c = cos(iSize.z), s = sin(iSize.z); vec2 p = position.xy * iSize.xy; q = vec2(c * p.x - s * p.y, s * p.x + c * p.y); }
    vec3 w = iPos + R * q.x + U * q.y; vY = w.y;
    gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.);
  }`;
const SFS = `uniform sampler2D uNoise; uniform sampler2D uAtlas; uniform float uTime;
  varying vec2 vUv; varying vec4 vCol; varying vec4 vPar; varying float vAdd; varying float vY;
  vec4 N(vec2 p) { return texture2D(uNoise, p); }
  void main() {
    float kind = vPar.x, k = vPar.y, sd = vPar.z; vec2 c = vUv * 2. - 1.; float r = length(c), cov = 0.; vec3 rgb = vCol.rgb; bool vol = true;
    if (kind < .5) {            // GLOW: a soft light, faintly mottled
      cov = pow(max(0., 1. - r), 1.7) * (.7 + .6 * N(vUv * .35 + sd).r);
    } else if (kind < 1.5) {    // FLAME: a tongue licking up, its edge torn by noise scrolling up through it, yellow at the root
      float t = uTime * .9 + sd * 13.;
      float n1 = N(vec2(vUv.x * .35 + sd, vUv.y * .3 - t * .7)).r, n2 = N(vec2(vUv.x * .8 - sd * 1.7, vUv.y * .6 - t * 1.4)).g;
      float x = c.x + (n1 - .5) * 1.1 * vUv.y;
      float w = pow(max(0., 1. - vUv.y), .6) * smoothstep(-.12, .22, vUv.y) * 1.1 + .002;
      float heat = (1. - abs(x) / w) * 1.1 + (n2 - .5) * .9 - vUv.y * .35 - k * k * 1.1;
      cov = smoothstep(0., .22, heat);
      rgb = mix(vCol.rgb * vec3(.9, .28, .12), vCol.rgb, smoothstep(0., .35, heat));
      rgb = mix(rgb, vec3(1., .86, .45) * 1.7, smoothstep(.45, .95, heat) * (1. - vUv.y * .5) * (1. - k * .7));
    } else if (kind < 2.5) {    // SMOKE: a lit puff that frays into wisps as it ages
      vec2 o = vec2(sd * 3.7, sd * 1.9);
      float n1 = N(vUv * .38 + o + vec2(0., k * .1)).r, n2 = N(vUv * .9 - o.yx + vec2(k * .16, 0.)).g;
      float d = 1. - r * r + (n1 - .5) * 1.15 + (n2 - .5) * .5, e = .06 + k * .8;
      cov = smoothstep(e, e + .38, d);
      rgb = vCol.rgb * (.5 + .62 * clamp(c.y * .55 + .42 + (n1 - .5) * .7, 0., 1.));
    } else if (kind < 3.5) {    // SPARK: a hot streak, head bright, tail thinning
      float w = 1. - abs(c.x), l = vUv.y; vol = false;
      cov = w * w * smoothstep(0., .75, l) * (1. - smoothstep(.9, 1., l)) * 1.3;
      rgb = vCol.rgb * 1.5 + pow(w, 8.) * smoothstep(.5, .95, l) * 1.8;
    } else if (kind < 4.5) {    // ICON: a cell of the atlas (coins, hearts, $...)
      vec2 cell = vec2(mod(vPar.w, 8.), floor(vPar.w / 8.)); vec4 t = texture2D(uAtlas, (cell + vec2(vUv.x, 1. - vUv.y)) / 8. * vec2(1., -1.) + vec2(0., 1.));
      rgb = t.rgb * vCol.rgb; cov = t.a; vol = false;
    } else if (kind < 5.5) {    // WISP: filaments of energy curling through a soft glow
      float n = N(vUv * .5 + sd + vec2(uTime * .06, -uTime * .1)).r, m = N(vUv * .9 - sd + vec2(-uTime * .05, uTime * .04)).g;
      float f = 1. - abs((n + m) - 1.) * 2.2, fall = max(0., 1. - r);
      cov = (pow(max(f, 0.), 4.) * 1.5 + fall * .35) * fall * (1. - k * k);
      rgb = vCol.rgb + pow(max(f, 0.), 10.) * .8;
    } else if (kind < 6.5) {    // BUBBLE: a thin skin, a glint, a hint of fill
      float rim = smoothstep(.6, .93, r) * (1. - smoothstep(.93, 1., r)), sp = 1. - smoothstep(0., .26, length(c - vec2(-.38, .38)));
      cov = rim * .85 + sp + (1. - smoothstep(.85, 1., r)) * .16; rgb = mix(vCol.rgb, vec3(1.6), sp); vol = false;
    } else if (kind < 7.5) {    // SHARD: a crystal, two lit faces and two dark
      float d = abs(c.x) * 1.8 + abs(c.y); vol = false;
      cov = 1. - smoothstep(.9, 1., d);
      rgb = vCol.rgb * (c.x > 0. ? (c.y > 0. ? 1.25 : .8) : (c.y > 0. ? 1. : .6)) + pow(max(0., 1. - d), 5.) * 1.2;
    } else {                    // FLARE: a four-point twinkle with a core (a glint, a star of light)
      float x = pow(max(0., 1. - abs(c.x)), 3.) * (1. - smoothstep(0., .1, abs(c.y))) + pow(max(0., 1. - abs(c.y)), 3.) * (1. - smoothstep(0., .1, abs(c.x)));
      cov = x + pow(max(0., 1. - r), 6.) * 1.5; rgb = vCol.rgb * 1.5 + pow(max(0., 1. - r * 1.6), 3.) * 2.; vol = false;
    }
    if (vol) cov *= smoothstep(-.02, .24, vY);   // into the ground softly: no hard line where a sprite meets it
    ${OUT}
  }`;

export class Sprites {
  constructor(scene, noise, atlas, N = 2600) {
    this.N = N; this.P = [];
    const g = this.geo = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0], 3)); g.setIndex([0, 1, 2, 0, 2, 3]);
    const at = (name, n) => { const a = new THREE.InstancedBufferAttribute(new Float32Array(N * n), n); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); return a.array; };
    this.pos = at('iPos', 3); this.vel = at('iVel', 3); this.size = at('iSize', 4); this.col = at('iCol', 4); this.par = at('iPar', 4);
    g.instanceCount = 0;
    this.mat = new THREE.ShaderMaterial({uniforms: {uNoise: {value: noise}, uAtlas: {value: atlas}, uTime: {value: 0}}, vertexShader: SVS, fragmentShader: SFS, ...PREMUL});
    this.mesh = new THREE.Mesh(g, this.mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 6; scene.add(this.mesh);
  }
  // o: x y z, vx vy vz, g (gravity), drag, life, w (width) or w0 -> w1, asp (height / width), c [r g b] (may pass 1: it blooms)
  // -> c1, a0 -> a1, kind, cell (ICON), rot, vr, add (1 glows, 0 covers), st (a spark's streak, s), ease (size eases out),
  // fin (fade in, s), floor, bounce, curl (a swirl about y, rad/s), seed
  emit(o) {
    if (this.P.length >= this.N) this.P.shift();
    const w0 = o.w0 ?? o.w ?? 1;
    this.P.push({x: o.x, y: o.y, z: o.z, vx: o.vx || 0, vy: o.vy || 0, vz: o.vz || 0, g: o.g ?? 0, drag: o.drag ?? 0, life: o.life || 1, age: 0, w0, w1: o.w1 ?? w0,
      asp: o.asp ?? 1, c: o.c || [1, 1, 1], c1: o.c1, a0: o.a0 ?? 1, a1: o.a1 ?? 0, kind: o.kind ?? 0, cell: o.cell ?? 0, rot: o.rot ?? (o.kind === S.FLAME ? 0 : Math.random() * 6.28),
      vr: o.vr ?? 0, add: o.add ?? 1, st: o.st ?? 0.05, ease: o.ease ?? 0, fin: o.fin ?? 0, floor: o.floor ?? -9, bounce: o.bounce ?? 0, curl: o.curl ?? 0, cx: o.cx ?? o.x, cz: o.cz ?? o.z,
      seed: o.seed ?? Math.random()});
    return this.P[this.P.length - 1];
  }
  update(dt, time) {
    this.mat.uniforms.uTime.value = time;
    const P = this.P; let w = 0;
    for (let i = 0; i < P.length; i++) {
      const p = P[i]; p.age += dt; if (p.age >= p.life) continue;
      p.vy -= p.g * dt; const d = Math.max(0, 1 - p.drag * dt); p.vx *= d; p.vy *= d; p.vz *= d;
      if (p.curl) { const dx = p.x - p.cx, dz = p.z - p.cz, s = p.curl * dt; p.x = p.cx + dx * Math.cos(s) - dz * Math.sin(s); p.z = p.cz + dx * Math.sin(s) + dz * Math.cos(s); p.cx += p.vx * dt; p.cz += p.vz * dt; }
      p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt; p.rot += p.vr * dt;
      if (p.y < p.floor) { p.y = p.floor; p.vy = -p.vy * p.bounce; p.vx *= 0.6; p.vz *= 0.6; p.vr *= 0.5; }
      P[w++] = p;
    }
    P.length = w;
    const {pos, vel, size, col, par} = this;
    for (let i = 0; i < w; i++) {
      const p = P[i], k = p.age / p.life, ke = p.ease ? 1 - (1 - k) ** 2 : k, sz = p.w0 + (p.w1 - p.w0) * ke;
      let a = p.a0 + (p.a1 - p.a0) * k; if (p.fin && p.age < p.fin) a *= p.age / p.fin;
      pos[i * 3] = p.x; pos[i * 3 + 1] = p.y; pos[i * 3 + 2] = p.z; vel[i * 3] = p.vx; vel[i * 3 + 1] = p.vy; vel[i * 3 + 2] = p.vz;
      size[i * 4] = sz; size[i * 4 + 1] = p.kind === S.SPARK ? sz * p.asp : sz * p.asp; size[i * 4 + 2] = p.kind === S.SPARK ? p.st : p.rot; size[i * 4 + 3] = p.add;
      const c = p.c, c1 = p.c1;
      if (c1) { col[i * 4] = c[0] + (c1[0] - c[0]) * k; col[i * 4 + 1] = c[1] + (c1[1] - c[1]) * k; col[i * 4 + 2] = c[2] + (c1[2] - c[2]) * k; }
      else { col[i * 4] = c[0]; col[i * 4 + 1] = c[1]; col[i * 4 + 2] = c[2]; }
      col[i * 4 + 3] = a; par[i * 4] = p.kind; par[i * 4 + 1] = k; par[i * 4 + 2] = p.seed; par[i * 4 + 3] = p.cell;
    }
    this.geo.instanceCount = w;
    for (const n of ['iPos', 'iVel', 'iSize', 'iCol', 'iPar']) { const A = this.geo.attributes[n]; A.clearUpdateRanges(); A.addUpdateRange(0, w * A.itemSize); A.needsUpdate = true; }
  }
  clear() { this.P.length = 0; this.geo.instanceCount = 0; }
}

// ---- ground marks
export const D = {SCORCH: 0, SHOCK: 1, GLOW: 2, STAIN: 3, FROST: 4, CRACK: 5, SWIRL: 6, POOL: 7};
const DVS = `attribute vec4 iPos; attribute vec4 iSize; attribute vec4 iCol; attribute vec4 iCol2; attribute vec4 iPar;
  varying vec2 vUv; varying vec4 vCol; varying vec4 vCol2; varying vec4 vPar; varying float vAdd; varying float vR;
  void main() {
    vUv = position.xy + .5; vCol = iCol; vCol2 = iCol2; vPar = vec4(iPar.x, iPar.y, iSize.w, iSize.y); vAdd = iSize.z; vR = iSize.x;
    float c = cos(iPos.w), s = sin(iPos.w); vec2 p = position.xy * 2. * iSize.x; p = vec2(c * p.x - s * p.y, s * p.x + c * p.y);
    gl_Position = projectionMatrix * viewMatrix * vec4(iPos.x + p.x, iPos.y, iPos.z + p.y, 1.);
  }`;
const DFS = `uniform sampler2D uNoise; uniform float uTime;
  varying vec2 vUv; varying vec4 vCol; varying vec4 vCol2; varying vec4 vPar; varying float vAdd; varying float vR;
  vec4 N(vec2 p) { return texture2D(uNoise, p); }
  void main() {
    float kind = vPar.x, k = vPar.y, sd = vPar.z, q = vPar.w; vec2 c = vUv * 2. - 1.; float r = length(c), cov = 0.; vec3 rgb = vCol.rgb, glow = vec3(0.);
    float sc = max(.35, vR * .22);   // the noise keeps its size on the ground, whatever the mark's
    vec2 w = c * sc + sd * 5.;
    float n1 = N(w * .5).r, n2 = N(w * 1.3 + .37).g;
    if (kind < .5) {            // SCORCH: a burnt patch, ragged, its cracks glowing while it's hot (q: heat)
      float d = 1. - r + (n1 - .5) * .75 + (n2 - .5) * .3; cov = smoothstep(0., .4, d) * .9;
      float cr = 1. - smoothstep(.02, .1 + n2 * .1, N(w * .7 + (N(w * .25).rg - .5) * .7 + .11).a); rgb = vCol.rgb * (.6 + n2 * .6);
      glow = vCol2.rgb * (cr * 2.2 + n1 * .25) * q * q * smoothstep(.15, .55, d);
    } else if (kind < 1.5) {    // SHOCK: the front of a blast thrown over the ground (q: how far out, 0..1), clumped, torn
      float f = q + (n1 - .5) * .14, band = smoothstep(f - .28 - q * .1, f, r) * (1. - smoothstep(f, f + .05, r));
      float clump = smoothstep(.3, .75, n2 + band * .3);
      cov = band * clump * 1.2 + smoothstep(f, 0., r) * .12 * (n1 + .2);
      glow = vCol2.rgb * pow(band, 3.) * clump * 2.;
      rgb = vCol.rgb * (.75 + n1 * .5);
    } else if (kind < 2.5) {    // GLOW: light thrown on the ground, its edge broken, breathing
      float n = N(w * .45 + vec2(uTime * .07, -uTime * .05)).r; float d = 1. - r + (n - .5) * .8;
      glow = vCol.rgb * smoothstep(0., .9, d) * (.6 + n * .8); cov = 0.;
    } else if (kind < 3.5) {    // STAIN: a spreading puddle (liquid or gas) swirling, with bubbles where the cells are
      float t = uTime * .12; vec2 sw = vec2(cos(t + r * 2.), sin(t + r * 2.)) * .15;
      float n = N(w * .45 + sw).r, d = 1. - r + (n - .5) * .7;
      cov = smoothstep(0., .22, d) * (.75 + n2 * .35);
      float b = 1. - smoothstep(.0, .18, N(w * .9 + vec2(0., uTime * .05)).b); float edge = smoothstep(.0, .15, d) * (1. - smoothstep(.15, .45, d));
      rgb = vCol.rgb * (.75 + n * .5); glow = vCol2.rgb * (b * .8 + edge * .9) * smoothstep(0., .3, d);
    } else if (kind < 4.5) {    // FROST: ice spread over the ground: crystal cells, their edges bright, a glint here and there
      float d = 1. - r + (n1 - .5) * .55; cov = smoothstep(0., .25, d) * .85;
      float e = 1. - smoothstep(.0, .09, N(w * .8).a), sp = smoothstep(.93, 1., N(w * 2.1 + uTime * .02).g);
      rgb = mix(vCol.rgb, vec3(1.), e * .7); glow = vCol2.rgb * (e * .6 + sp * 3.) * smoothstep(0., .3, d);
    } else if (kind < 5.5) {    // CRACK: the ground split by a heavy blow, glowing deep in the cracks (q: glow)
      float a = atan(c.y, c.x), ray = N(vec2(a * .8, r * .3) + sd).r, d = 1. - r + (n1 - .5) * .5;
      float cr = (1. - smoothstep(.0, .06, N(w * .55 + vec2(a * .05, 0.)).a)) * smoothstep(0., .5, d);
      cov = cr * .9 + smoothstep(0., .5, d) * .25 * n2; rgb = vCol.rgb; glow = vCol2.rgb * cr * q * 2.;
      ray = ray;
    } else if (kind < 6.5) {    // SWIRL: a vortex winding in (gas, magic), torn by noise (q: spin)
      float a = atan(c.y, c.x), s = sin(a * 3. + r * 9. - uTime * 2.5 * (1. + q)) * .5 + .5, d = 1. - r + (n1 - .5) * .6;
      float m = smoothstep(.0, .3, d) * smoothstep(.35, .9, s * (.6 + n2 * .7));
      cov = m * .6; glow = vCol2.rgb * m * (1. - r) * 1.5; rgb = vCol.rgb;
    } else {                    // POOL: a glossy liquid: darker where it's deep, a wet bright rim, the light's sheen sliding over it (q: sheen)
      float t = uTime * .08; vec2 fl = (N(w * .22 + vec2(t, -t * .6)).rg - .5) * .6;
      float n = N(w * .4 + fl * .5).r, d = 1. - r + (n - .5) * .6;
      cov = smoothstep(0., .08, d);
      float deep = smoothstep(.04, .5, d), rim = smoothstep(.0, .04, d) * (1. - smoothstep(.04, .13, d));
      float sh = smoothstep(.58, .78, N(w * .3 + fl * 1.8 + .5).g) * smoothstep(.1, .4, d);
      rgb = mix(vCol2.rgb * .45, vCol.rgb, deep) * (.8 + n2 * .4);
      glow = vCol2.rgb * rim * .8 + mix(vCol2.rgb, vec3(1.), .55) * sh * q * .45;
    }
    float a = clamp(cov, 0., 1.) * vCol.a; if (a + dot(glow, vec3(1.)) * vCol.a < .003) discard;
    gl_FragColor = vec4(rgb * a + glow * vCol.a, a * (1. - vAdd));
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export class Decals {
  constructor(scene, noise, N = 128) {
    this.N = N; this.L = [];
    const g = this.geo = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0], 3)); g.setIndex([0, 2, 1, 0, 3, 2]);
    const at = (name, n) => { const a = new THREE.InstancedBufferAttribute(new Float32Array(N * n), n); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); return a.array; };
    this.pos = at('iPos', 4); this.size = at('iSize', 4); this.col = at('iCol', 4); this.col2 = at('iCol2', 4); this.par = at('iPar', 4);
    g.instanceCount = 0;
    this.mat = new THREE.ShaderMaterial({uniforms: {uNoise: {value: noise}, uTime: {value: 0}}, vertexShader: DVS, fragmentShader: DFS, ...PREMUL, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2});
    this.mesh = new THREE.Mesh(this.geo, this.mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 3; scene.add(this.mesh);
  }
  // o: x z (y), r or r0 -> r1 (radius; ease: it eases out), life, kind, c (cover colour) c2 (glow colour), a0 -> a1, q0 -> q1
  // (the kind's own parameter: heat, front, spin), add, rot, seed. hold: it stays till .dead is set (its fields driven by its owner)
  emit(o) {
    if (this.L.length >= this.N) this.L.shift();
    const r0 = o.r0 ?? o.r ?? 1;
    const d = {x: o.x, y: o.y ?? 0.05, z: o.z, r0, r1: o.r1 ?? r0, life: o.life || 1, age: 0, kind: o.kind ?? 0, c: o.c || [0, 0, 0], c2: o.c2 || [0, 0, 0], a0: o.a0 ?? 1, a1: o.a1 ?? 0,
      q0: o.q0 ?? 1, q1: o.q1 ?? o.q0 ?? 1, add: o.add ?? 0, rot: o.rot ?? Math.random() * 6.28, seed: o.seed ?? Math.random(), ease: o.ease ?? 0, fin: o.fin ?? 0, hold: !!o.hold, dead: false,
      qe: o.qe ?? 0};
    this.L.push(d); return d;
  }
  update(dt, time) {
    this.mat.uniforms.uTime.value = time;
    const L = this.L; let w = 0;
    for (let i = 0; i < L.length; i++) { const d = L[i]; d.age += dt; if (d.dead || (!d.hold && d.age >= d.life)) continue; L[w++] = d; }
    L.length = w;
    const {pos, size, col, col2, par} = this;
    for (let i = 0; i < w; i++) {
      const d = L[i], k = d.hold ? (d.k ?? 0) : d.age / d.life, ke = d.ease ? 1 - (1 - k) ** 3 : k, qk = d.qe ? 1 - (1 - k) ** 3 : k;
      let a = d.hold ? (d.a ?? d.a0) : d.a0 + (d.a1 - d.a0) * k; if (d.fin && d.age < d.fin) a *= d.age / d.fin;
      pos[i * 4] = d.x; pos[i * 4 + 1] = d.y; pos[i * 4 + 2] = d.z; pos[i * 4 + 3] = d.rot;
      size[i * 4] = d.hold ? (d.r ?? d.r0) : d.r0 + (d.r1 - d.r0) * ke; size[i * 4 + 1] = d.hold ? (d.q ?? d.q0) : d.q0 + (d.q1 - d.q0) * qk; size[i * 4 + 2] = d.add; size[i * 4 + 3] = d.seed;
      col[i * 4] = d.c[0]; col[i * 4 + 1] = d.c[1]; col[i * 4 + 2] = d.c[2]; col[i * 4 + 3] = a;
      col2[i * 4] = d.c2[0]; col2[i * 4 + 1] = d.c2[1]; col2[i * 4 + 2] = d.c2[2]; par[i * 4] = d.kind; par[i * 4 + 1] = k;
    }
    this.geo.instanceCount = w;
    for (const n of ['iPos', 'iSize', 'iCol', 'iCol2', 'iPar']) { const A = this.geo.attributes[n]; A.clearUpdateRanges(); A.addUpdateRange(0, w * A.itemSize); A.needsUpdate = true; }
  }
  clear() { this.L.length = 0; this.geo.instanceCount = 0; }
}

// ---- ribbons: a strip through a list of points, turned to face the camera; each vertex carries u (along, 0 at the head),
// v (across, 0..1), its alpha and the strip's width there. One material per look, shared by every ribbon of that look.
const RVS = `attribute vec4 aR; varying vec4 vR; varying vec3 vW; void main() { vR = aR; vW = position; gl_Position = projectionMatrix * viewMatrix * vec4(position, 1.); }`;
export const RIBBON = {
  // NYAN CAT's: six bands, red at the top; the bands step in a wave down its length like the meme's, glints drifting through,
  // the tail end crumbling into the noise as it fades
  rainbow: `uniform sampler2D uNoise; uniform float uTime; varying vec4 vR; varying vec3 vW;
    vec3 band(float i) { return i < 1. ? vec3(1., .12, .14) : i < 2. ? vec3(1., .5, .06) : i < 3. ? vec3(1., .9, .1) : i < 4. ? vec3(.2, .95, .16) : i < 5. ? vec3(.1, .55, 1.) : vec3(.48, .22, 1.); }
    void main() {
      float u = vR.x, v = vR.y, al = vR.z;
      float wave = (fract(u * .5 - uTime * .9) < .5 ? .045 : -.045);   // the stepped wave
      float vv = clamp(v + wave, 0., 1.) * 6., i = floor(vv), f = fract(vv), fw = fwidth(vv) * 1.2;
      vec3 rgb = mix(band(i), band(min(5., i + 1.)), smoothstep(1. - fw, 1., f));
      float edge = smoothstep(0., .07, v + wave) * (1. - smoothstep(.93, 1., v + wave));
      float n = texture2D(uNoise, vec2(u * .16, v * .5) + vec2(-uTime * .05, 0.)).r, g = texture2D(uNoise, vec2(u * .5 - uTime * .3, v * .9)).g;
      float cov = edge * smoothstep(0., .25, al + (n - .5) * .5 - (1. - al) * .3);
      rgb *= 1.15 + .25 * sin(f * 3.14159);              // each band rounded a little
      rgb += vec3(1.) * smoothstep(.8, .95, g) * 1.4;     // glints
      if (cov < .003) discard;
      gl_FragColor = vec4(rgb * cov, cov * .92);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
  // a glowing trail (magic, a slash): bright core, soft edges, torn as it thins
  energy: `uniform sampler2D uNoise; uniform float uTime; uniform vec3 uCol; uniform vec3 uCore; varying vec4 vR; varying vec3 vW;
    void main() {
      float u = vR.x, v = vR.y, al = vR.z, x = abs(v * 2. - 1.);
      float n = texture2D(uNoise, vec2(u * .3 - uTime * .6, v * .4)).r;
      float cov = (1. - smoothstep(.2, 1., x + (n - .5) * .5)) * al;
      vec3 rgb = mix(uCol, uCore * 2.5, pow(max(0., 1. - x * 1.6), 3.) * al);
      if (cov < .003) discard; gl_FragColor = vec4(rgb * cov, 0.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
};
const ribbonMats = new Map();
export function ribbonMaterial(look, noise, uniforms = {}) {
  const key = look + JSON.stringify(Object.keys(uniforms));
  if (!ribbonMats.has(key)) ribbonMats.set(key, new THREE.ShaderMaterial({uniforms: {uNoise: {value: noise}, uTime: {value: 0}, ...uniforms}, vertexShader: RVS, fragmentShader: RIBBON[look],
    ...PREMUL, side: THREE.DoubleSide}));
  return ribbonMats.get(key);
}
export function ribbonTime(t) { for (const m of ribbonMats.values()) m.uniforms.uTime.value = t; }

const TO = new THREE.Vector3(), TN = new THREE.Vector3(), AC = new THREE.Vector3();
export class Ribbon {
  constructor(scene, mat, N = 96) {
    this.N = N; const g = this.geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(N * 2 * 3); this.r = new Float32Array(N * 2 * 4);
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage)); g.setAttribute('aR', new THREE.BufferAttribute(this.r, 4).setUsage(THREE.DynamicDrawUsage));
    const idx = []; for (let i = 0; i < N - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } g.setIndex(idx); g.setDrawRange(0, 0);
    this.mesh = new THREE.Mesh(g, mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 5; scene.add(this.mesh);
  }
  // pts: [{x, y, z, w, a, u}] from the head; u: distance along (world units). cam: the camera's position
  set(pts, cam) {
    const n = Math.min(this.N, pts.length), P = this.pos, R = this.r;
    for (let i = 0; i < n; i++) {
      const p = pts[i], a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
      TN.set(b.x - a.x, b.y - a.y, b.z - a.z); if (TN.lengthSq() < 1e-8) TN.set(0, 0, 1); TN.normalize();
      TO.set(cam.x - p.x, cam.y - p.y, cam.z - p.z).normalize(); AC.crossVectors(TN, TO); if (AC.lengthSq() < 1e-8) AC.set(1, 0, 0); AC.normalize().multiplyScalar(p.w * 0.5);
      P.set([p.x + AC.x, p.y + AC.y, p.z + AC.z, p.x - AC.x, p.y - AC.y, p.z - AC.z], i * 6);
      R.set([p.u, 0, p.a, p.w, p.u, 1, p.a, p.w], i * 8);
    }
    this.geo.setDrawRange(0, Math.max(0, n - 1) * 6);
    this.geo.attributes.position.needsUpdate = this.geo.attributes.aR.needsUpdate = true;
    this.mesh.visible = n > 1;
  }
  dispose() { this.mesh.parent?.remove(this.mesh); this.geo.dispose(); }
}

// ---- shells: a dome of energy or air (a shockwave's body, a bubble of magic): lit at its rim where the view grazes it,
// rippling, eaten away by the noise as it ages (uK). A small pool; each mesh its own uniforms, one program for all.
const SHVS = `varying vec3 vN; varying vec3 vV; varying vec3 vP;
  void main() { vP = position; vec4 mv = modelViewMatrix * vec4(position, 1.); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`;
const SHFS = `uniform sampler2D uNoise; uniform float uTime; uniform float uK; uniform float uA; uniform float uSeed; uniform float uRip; uniform vec3 uCol; uniform vec3 uCore;
  varying vec3 vN; varying vec3 vV; varying vec3 vP;
  void main() {
    float f = 1. - abs(dot(normalize(vN), normalize(vV))), rim = pow(f, 2.4); float h = clamp(vP.y, 0., 1.);
    vec2 sp = vec2(atan(vP.z, vP.x) * .3183 + uSeed, h * .7 - uK * .5);
    float n = texture2D(uNoise, sp).r, n2 = texture2D(uNoise, sp * 2.7 + .31).g;
    float rip = uRip > 0. ? .55 + .45 * sin((1. - h) * uRip * 6.2832 - uTime * 18.) : 1.;
    float keep = smoothstep(uK * 1.15 - .12, uK * 1.15 + .2, n * .65 + n2 * .35 + rim * .25);
    float cov = pow(rim, 1.6) * 1.6 * keep * rip * (.55 + (1. - h) * .45) * uA * (1. - uK * uK);
    if (cov < .003) discard;
    gl_FragColor = vec4(mix(uCol, uCore, pow(rim, 3.)) * cov, 0.);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;
export class Shells {
  constructor(scene, noise) {
    this.scene = scene; this.noise = noise; this.free = [];
    this.geo = new THREE.SphereGeometry(1, 48, 14, 0, Math.PI * 2, 0, Math.PI / 2);
    this.base = new THREE.ShaderMaterial({uniforms: {uNoise: {value: noise}, uTime: {value: 0}, uK: {value: 0}, uA: {value: 1}, uSeed: {value: 0}, uRip: {value: 0},
      uCol: {value: new THREE.Color()}, uCore: {value: new THREE.Color()}}, vertexShader: SHVS, fragmentShader: SHFS, ...PREMUL, side: THREE.DoubleSide});
  }
  get() {
    let m = this.free.pop();
    if (!m) { m = new THREE.Mesh(this.geo, this.base.clone()); m.material.uniforms.uNoise.value = this.noise; m.frustumCulled = false; m.renderOrder = 6; }
    m.material.uniforms.uSeed.value = Math.random(); this.scene.add(m); m.visible = true; return m;
  }
  put(m) { this.scene.remove(m); this.free.push(m); }
}

// ---- a slash's smear: a flat arc swept round a fighter at blade height, white at the blade's edge, streaked along the swing,
// thinning to nothing at its tail (u: 0 tail .. 1 blade), dissolving as it ends (uK). The mesh is a ring sector in its own
// plane (RingGeometry before it's laid flat): the shader reads where it is from that.
const SLVS = `varying vec2 vP; void main() { vP = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const SLFS = `uniform sampler2D uNoise; uniform float uK; uniform float uArc; uniform float uIn; uniform vec3 uCol; uniform vec3 uCore; varying vec2 vP;
  void main() {
    float a = atan(vP.y, vP.x); if (a < 0.) a += 6.28318; float u = clamp(a / uArc, 0., 1.), v = clamp((length(vP) - uIn) / (1. - uIn), 0., 1.);
    float n = texture2D(uNoise, vec2(u * 1.6 - uK * 1.5, v * .5)).r, st = texture2D(uNoise, vec2(u * .35 + .2, v * 2.8)).g;
    float prof = smoothstep(0., .45, v) * (1. - smoothstep(.88, 1., v));
    float cov = prof * pow(u, 1.6) * (1. - smoothstep(.95, 1., u + (n - .5) * .06)) * (.45 + 1.1 * st) * smoothstep(.1, .45, n * .8 + u * .5) * (1. - uK * uK);
    vec3 rgb = mix(uCol, uCore * 2.4, pow(u, 5.) * smoothstep(.55, .95, v));
    if (cov < .003) discard; gl_FragColor = vec4(rgb * cov, 0.);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;
export function slashMaterial(noise, arc, inner) {
  return new THREE.ShaderMaterial({uniforms: {uNoise: {value: noise}, uK: {value: 0}, uArc: {value: arc}, uIn: {value: inner}, uCol: {value: new THREE.Color()}, uCore: {value: new THREE.Color()}},
    vertexShader: SLVS, fragmentShader: SLFS, ...PREMUL, side: THREE.DoubleSide});
}
