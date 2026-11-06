// Effects: one pooled particle system (sprite atlas, additive and normal), projectiles that follow the sim's, spell
// visuals (FUD lightning, the rug, the green candle), tower explosions, shockwave rings, floating text; the troops' abilities
// (POPCAT's shockwave, SWORDCAT's spin, BONK, MOO DENG's charge, TROLLFACE's blink, PNUT's acorns, WOJAK's gloom) and the
// lasting things that follow the sim's entities (FART's drifting cloud, burning ground, NYAN CAT's rainbow); the second wave's
// (TOSHI's dash, SLERF's quake, FLOKI's rage, APU's mend, WALTER's digging, MICHI's trap, FARTER's gas, BOME's paper storm).
import * as THREE from 'three';
import {TEAM_COL, TOWER_VIS} from './arena.js';
import {VIS, visH, flyH, LEAN} from './units.js';
import {BLD_VIS} from './blds.js';
import {CARDS} from '../data.js';
import {castSpell, bolt} from './spells.js';
import {prop} from './props.js';
import {noiseTexture, Sprites, Decals, Ribbon, Shells, ribbonMaterial, ribbonTime, slashMaterial, S, D} from './kit.js';

// ---- the atlas: 4x4 cells drawn once on a canvas
const CELL = {soft: 0, spark: 1, coin: 2, smoke: 3, ring: 4, star: 5, drop: 6, leaf: 7, bolt: 8, chunk: 9, heart: 10, ha: 11, dollar: 12, flame: 13, square: 14, cross: 15,
  arrow: 16, candle: 17, paper: 18, ucoin: 19, fly: 20, clod: 21, yarn: 22, gem: 23, fork: 24, page: 25};
function atlas() {
  const S = 128, c = document.createElement('canvas'); c.width = c.height = S * 8; const g = c.getContext('2d');
  const at = (k, f) => { g.save(); g.translate((k % 8) * S + S / 2, Math.floor(k / 8) * S + S / 2); f(); g.restore(); };
  const rad = (r, stops) => { const gr = g.createRadialGradient(0, 0, 0, 0, 0, r); stops.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; };
  at(CELL.soft, () => { g.fillStyle = rad(60, [[0, 'rgba(255,255,255,1)'], [0.35, 'rgba(255,255,255,0.55)'], [1, 'rgba(255,255,255,0)']]); g.fillRect(-64, -64, 128, 128); });
  at(CELL.spark, () => { g.fillStyle = rad(60, [[0, 'rgba(255,255,255,1)'], [0.12, 'rgba(255,255,255,0.9)'], [0.3, 'rgba(255,255,255,0.15)'], [1, 'rgba(255,255,255,0)']]); g.fillRect(-64, -64, 128, 128);
    g.fillStyle = '#fff'; g.beginPath(); g.ellipse(0, 0, 58, 5, 0, 0, Math.PI * 2); g.fill(); g.beginPath(); g.ellipse(0, 0, 5, 58, 0, 0, Math.PI * 2); g.fill(); });
  at(CELL.coin, () => { g.fillStyle = '#b8860b'; g.beginPath(); g.arc(0, 0, 50, 0, Math.PI * 2); g.fill(); g.fillStyle = '#ffd54a'; g.beginPath(); g.arc(-3, -3, 44, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#fff3b0'; g.beginPath(); g.arc(-14, -16, 14, 0, Math.PI * 2); g.fill(); g.fillStyle = '#b8860b'; g.font = 'bold 54px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('$', -2, 4); });
  at(CELL.smoke, () => { for (let k = 0; k < 7; k++) { const a = k / 7 * Math.PI * 2; g.fillStyle = rad(36, [[0, 'rgba(255,255,255,0.5)'], [1, 'rgba(255,255,255,0)']]); g.save(); g.translate(Math.cos(a) * 18, Math.sin(a) * 18); g.fillRect(-40, -40, 80, 80); g.restore(); }
    g.fillStyle = rad(50, [[0, 'rgba(255,255,255,0.7)'], [1, 'rgba(255,255,255,0)']]); g.fillRect(-64, -64, 128, 128); });
  at(CELL.ring, () => { g.strokeStyle = '#fff'; g.lineWidth = 9; g.beginPath(); g.arc(0, 0, 54, 0, Math.PI * 2); g.stroke(); g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = 20; g.beginPath(); g.arc(0, 0, 46, 0, Math.PI * 2); g.stroke(); });
  at(CELL.star, () => { g.fillStyle = '#fff'; g.beginPath(); for (let k = 0; k < 10; k++) { const r = k % 2 ? 22 : 58, a = k / 10 * Math.PI * 2 - Math.PI / 2; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.fill(); });
  at(CELL.drop, () => { g.fillStyle = rad(50, [[0, 'rgba(255,255,255,1)'], [0.7, 'rgba(255,255,255,0.8)'], [1, 'rgba(255,255,255,0)']]); g.beginPath(); g.arc(0, 8, 40, 0, Math.PI * 2); g.fill(); });
  at(CELL.leaf, () => { g.fillStyle = '#fff'; g.beginPath(); g.ellipse(0, 0, 50, 22, 0.6, 0, Math.PI * 2); g.fill(); });
  at(CELL.bolt, () => { g.fillStyle = '#fff'; g.beginPath(); g.moveTo(10, -60); g.lineTo(-22, 6); g.lineTo(2, 6); g.lineTo(-12, 60); g.lineTo(26, -10); g.lineTo(2, -10); g.closePath(); g.fill(); });
  at(CELL.chunk, () => { g.fillStyle = '#fff'; g.beginPath(); g.moveTo(-40, -30); g.lineTo(30, -44); g.lineTo(48, 18); g.lineTo(-6, 44); g.lineTo(-46, 12); g.closePath(); g.fill(); g.fillStyle = 'rgba(0,0,0,0.3)'; g.beginPath(); g.moveTo(-6, 44); g.lineTo(48, 18); g.lineTo(10, 4); g.closePath(); g.fill(); });
  at(CELL.heart, () => { g.fillStyle = '#fff'; g.beginPath(); g.moveTo(0, 40); g.bezierCurveTo(-70, -10, -30, -60, 0, -24); g.bezierCurveTo(30, -60, 70, -10, 0, 40); g.fill(); });
  at(CELL.ha, () => { g.font = '900 64px "Lilita One", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineWidth = 12; g.strokeStyle = '#2a1600'; g.strokeText('HA', 0, 4); g.fillStyle = '#fff'; g.fillText('HA', 0, 4); });
  at(CELL.dollar, () => { g.font = '900 96px "Lilita One", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineWidth = 12; g.strokeStyle = '#06210b'; g.strokeText('$', 0, 6); g.fillStyle = '#fff'; g.fillText('$', 0, 6); });
  at(CELL.flame, () => { g.fillStyle = rad(56, [[0, 'rgba(255,255,255,1)'], [0.4, 'rgba(255,255,255,0.6)'], [1, 'rgba(255,255,255,0)']]); g.beginPath(); g.ellipse(0, 10, 34, 54, 0, 0, Math.PI * 2); g.fill(); });
  at(CELL.square, () => { g.fillStyle = '#fff'; g.fillRect(-40, -40, 80, 80); });
  at(CELL.cross, () => { g.fillStyle = '#fff'; g.fillRect(-12, -50, 24, 100); g.fillRect(-50, -12, 100, 24); });
  // the spells' bits: an arrow (up; turned for down), a candlestick, a page of headlines, a U coin (in its own colours), a fly,
  // a clod of earth
  at(CELL.arrow, () => { g.fillStyle = '#fff'; g.beginPath(); g.moveTo(0, -58); g.lineTo(46, -6); g.lineTo(18, -6); g.lineTo(18, 56); g.lineTo(-18, 56); g.lineTo(-18, -6); g.lineTo(-46, -6); g.closePath(); g.fill();
    g.fillStyle = 'rgba(0,0,0,0.22)'; g.fillRect(4, -6, 14, 62); });
  at(CELL.candle, () => { g.fillStyle = '#fff'; g.fillRect(-4, -60, 8, 120); g.fillRect(-20, -38, 40, 74); g.fillStyle = 'rgba(0,0,0,0.2)'; g.fillRect(6, -38, 14, 74); });
  at(CELL.paper, () => { g.rotate(0.08); g.fillStyle = '#f4f1e8'; g.fillRect(-40, -52, 80, 104); g.fillStyle = '#c8282e'; g.fillRect(-32, -44, 64, 12); g.fillStyle = '#8a8a90';
    for (let i = 0; i < 6; i++) g.fillRect(-32, -22 + i * 11, i % 3 === 2 ? 40 : 64, 5); g.fillStyle = '#d23030'; g.beginPath(); g.moveTo(10, 30); g.lineTo(30, 46); g.lineTo(30, 30); g.fill(); });
  at(CELL.ucoin, () => { g.fillStyle = '#9a6a06'; g.beginPath(); g.arc(0, 0, 54, 0, 7); g.fill(); g.fillStyle = '#ffcf3a'; g.beginPath(); g.arc(-3, -3, 48, 0, 7); g.fill();
    g.fillStyle = '#fff2b0'; g.beginPath(); g.arc(-18, -20, 12, 0, 7); g.fill(); g.font = '900 70px "Lilita One", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#1c1404'; g.fillText('U', -2, 6); });
  at(CELL.fly, () => { g.fillStyle = 'rgba(220,240,255,0.75)'; g.beginPath(); g.ellipse(-16, -18, 22, 12, -0.6, 0, 7); g.fill(); g.beginPath(); g.ellipse(16, -18, 22, 12, 0.6, 0, 7); g.fill();
    g.fillStyle = '#1a1c12'; g.beginPath(); g.ellipse(0, 6, 14, 22, 0, 0, 7); g.fill(); g.beginPath(); g.arc(0, -18, 11, 0, 7); g.fill(); g.fillStyle = '#c03020'; g.beginPath(); g.arc(-6, -20, 4, 0, 7); g.arc(6, -20, 4, 0, 7); g.fill(); });
  at(CELL.clod, () => { g.fillStyle = '#fff'; g.beginPath(); for (let k = 0; k < 9; k++) { const a = k / 9 * 6.283, r = 34 + (k * 37 % 13); g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.closePath(); g.fill();
    g.fillStyle = 'rgba(0,0,0,0.35)'; g.beginPath(); g.arc(10, 12, 22, 0, 7); g.fill(); g.fillStyle = 'rgba(255,255,255,0.4)'; g.beginPath(); g.arc(-12, -12, 10, 0, 7); g.fill(); });
  // the second wave's: a ball of yarn, a cut gem, a chain forking (white: tinted by the caller), a spellbook's page (its own colours)
  at(CELL.yarn, () => { g.fillStyle = '#fff'; g.beginPath(); g.arc(0, 0, 50, 0, 7); g.fill(); g.clip(); g.strokeStyle = 'rgba(0,0,0,0.3)'; g.lineWidth = 6;
    for (const [a, r] of [[-0.9, 56], [0.5, 40], [2, 62], [3.1, 30]]) { g.beginPath(); g.arc(Math.cos(a) * 34, Math.sin(a) * 34, r, a + 2, a + 4.2); g.stroke(); } });
  at(CELL.gem, () => { const f = (c, ...p) => { g.fillStyle = c; g.beginPath(); for (let i = 0; i < p.length; i += 2) g.lineTo(p[i], p[i + 1]); g.closePath(); g.fill(); };
    f('#fff', -56, -14, -28, -44, 28, -44, 56, -14, 0, 56); f('rgba(0,0,0,0.3)', 12, -14, 56, -14, 0, 56); f('rgba(0,0,0,0.12)', -12, -14, 12, -14, 0, 56); f('rgba(0,0,0,0.18)', -28, -44, -12, -14, -56, -14); });
  at(CELL.fork, () => { g.strokeStyle = '#fff'; g.lineWidth = 16; g.lineCap = 'round'; g.lineJoin = 'round'; g.beginPath(); g.moveTo(0, 56); g.lineTo(0, 4); g.lineTo(-38, -44); g.moveTo(0, 4); g.lineTo(38, -44); g.stroke(); });
  at(CELL.page, () => { g.rotate(-0.06); g.fillStyle = '#f2e3bd'; g.fillRect(-40, -52, 80, 104); g.strokeStyle = '#a8894e'; g.lineWidth = 4; g.strokeRect(-34, -46, 68, 92); g.fillStyle = '#6b4aa8'; for (let i = 0; i < 5; i++) g.fillRect(-26, -34 + i * 16, i % 2 ? 36 : 52, 6); });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// the particle calls (a point size s, an atlas cell) drawn with the kit's sprites: smoke, flame, sparks and glows are its
// own shaded kinds, the rest the atlas's icons. W: the world width a size of 1 had as a point
const W = 0.65;
class Emitter {
  constructor(sp, add) { this.sp = sp; this.add = add; }
  get P() { return this.sp.P; }
  emit(o) {
    const s0 = (o.s0 ?? o.s ?? 1) * W, s1 = (o.s1 ?? o.s ?? 1) * W, cell = o.cell ?? 0, a0 = o.a0 ?? 1, add = this.add ? 1 : 0, sp = this.sp;
    const b = {x: o.x, y: o.y, z: o.z, vx: o.vx, vy: o.vy, vz: o.vz, g: o.g, drag: o.drag, life: o.life, c: o.c, floor: o.floor, bounce: o.bounce};
    if (cell === CELL.smoke) return sp.emit({...b, kind: S.SMOKE, w0: s0 * 0.9, w1: s1 * 0.9, a0: a0 * 0.95, a1: o.a1 ?? a0 * 0.5, add: add * 0.6, ease: 1, rot: o.rot, vr: (o.vr ?? 0) * 0.15 + rnd(-0.3, 0.3)});
    if (cell === CELL.flame) return sp.emit({...b, kind: S.FLAME, w0: s0 * 0.85, w1: s1 * 0.85, asp: 1.5, a0, a1: o.a1 ?? 0.25, add: 0.55, rot: rnd(-0.12, 0.12)});
    if (cell === CELL.spark) { const v = Math.hypot(o.vx || 0, o.vy || 0, o.vz || 0);
      return v > 0.6 ? sp.emit({...b, kind: S.SPARK, w0: s0 * 0.32, w1: s1 * 0.32, asp: 0.3, st: 0.06, a0, a1: o.a1 ?? 0, add: 1})
        : sp.emit({...b, kind: S.FLARE, w0: s0 * 0.9, w1: s1 * 0.9, a0, a1: o.a1 ?? 0, add: 1, rot: 0}); }
    if (cell === CELL.soft) return sp.emit({...b, kind: S.GLOW, w0: s0, w1: s1, a0, a1: o.a1 ?? 0, add});
    if (cell === CELL.star && add && s0 < 1.1 * W) return sp.emit({...b, kind: S.FLARE, w0: s0 * 1.2, w1: s1 * 1.2, a0, a1: o.a1 ?? 0, add: 1, rot: 0});
    if (cell === CELL.ring) return sp.emit({...b, kind: S.BUBBLE, w0: s0, w1: s1, a0, a1: o.a1 ?? 0, add});
    return sp.emit({...b, kind: S.ICON, cell, w0: s0, w1: s1, a0, a1: o.a1 ?? 0, add, rot: o.rot, vr: o.vr});
  }
}

const rnd = (a, b) => a + Math.random() * (b - a);
const C = {gold: [1, 0.82, 0.3], green: [0.49, 1, 0.42], red: [1, 0.3, 0.43], white: [1, 1, 1], dust: [0.62, 0.6, 0.58], smoke: [0.18, 0.18, 0.22], fire: [1, 0.55, 0.15], purple: [0.7, 0.45, 1], blue: [0.55, 0.75, 1], matcha: [0.55, 0.85, 0.3], bread: [0.85, 0.6, 0.3], yellow: [1, 0.9, 0.2],
  pink: [1, 0.62, 0.86], cyan: [0.45, 0.95, 1], violet: [0.65, 0.4, 1], acorn: [0.55, 0.34, 0.16], toxic: [[0.42, 0.72, 0.12], [0.56, 0.82, 0.18], [0.34, 0.5, 0.1]], ember: [1, 0.72, 0.3], yarn: [1, 0.46, 0.72], soap: [0.72, 0.93, 1], holy: [1, 0.93, 0.62], dirt: [0.42, 0.3, 0.2]};
// soft round blobs for glows on the ground (white: tinted by the material)
let softTex = null;
function soft() {
  if (softTex) return softTex;
  const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.55, 'rgba(255,255,255,0.6)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  return (softTex = new THREE.CanvasTexture(c));
}
const M4 = new THREE.Matrix4(), QY = new THREE.Quaternion(), V1 = new THREE.Vector3(), V2 = new THREE.Vector3(), UP = new THREE.Vector3(0, 1, 0), COL = new THREE.Color();
const teamRGB = s => s === 0 ? C.green : C.red;
const RAINBOW = [[1, 0.12, 0.14], [1, 0.5, 0.06], [1, 0.9, 0.1], [0.2, 0.95, 0.16], [0.1, 0.55, 1], [0.48, 0.22, 1]];
// a CSS colour as linear rgb (the shaders' space)
const LIN = new Map(), lin = col => { if (!LIN.has(col)) { const c = new THREE.Color(col); LIN.set(col, [c.r, c.g, c.b]); } return LIN.get(col); };
const mul = (c, k) => [c[0] * k, c[1] * k, c[2] * k];
// how high a thrown thing climbs on a full-length throw (a lob's own arc is in syncProjectiles)
const ARC = {baguette: 1.4, matcha: 1.4, yarn: 1.4, rocket: 0.8, magic: 0.8, gas: 0.8, bubble: 0.8, star: 0.4, holy: 0.4, page: 0.4};
// a beam's three heats (MENSA's pink, the LASER EYES' red): its colour and the sparks where it lands
const BEAM = {mensa: {col: ['#ff9be6', '#ff4fc8', '#ff2a6d'].map(c => new THREE.Color(c)), spark: [1, 0.4, 0.8], w: 1}, eyes: {col: ['#ffa070', '#ff5030', '#ff1e14'].map(c => new THREE.Color(c)), spark: [1, 0.45, 0.2], w: 1}};

export class FX {
  constructor(stage) {
    this.stage = stage; const s = stage.scene; this.scene = s;
    this.map = atlas(); this.noise = noiseTexture(); this.time = 0;
    this.sp = new Sprites(s, this.noise, this.map, 3000); this.dc = new Decals(s, this.noise, 160); this.shells = new Shells(s, this.noise);
    this.add = new Emitter(this.sp, true); this.norm = new Emitter(this.sp, false);
    this.projViews = new Map(); this.spells = new Map(); this.things = [];
    this.ringGeo = new THREE.RingGeometry(0.85, 1, 48).rotateX(-Math.PI / 2);
    this.discGeo = new THREE.CircleGeometry(1, 48).rotateX(-Math.PI / 2);
    this.blobGeo = new THREE.PlaneGeometry(2, 2).rotateX(-Math.PI / 2);   // (for the soft round glows: a radius of 1 too)
    this.decals = [];
    this.lights = [0, 1, 2].map(() => { const L = new THREE.PointLight('#ffffff', 0, 10, 1.5); L.userData.until = 0; s.add(L); return L; });
    this.shared = new Set([this.ringGeo, this.discGeo, this.blobGeo]); this.projProto = {};
  }
  // free what a one-off effect allocated (shared geometry/materials stay)
  dispose(o) {
    if (o?.userData?.keep) return;   // (a prop: its geometry and materials are shared by its clones)
    o?.traverse?.(n => {
      if (n.geometry && !this.shared.has(n.geometry)) n.geometry.dispose();
      for (const m of [].concat(n.material || [])) if (!this.shared.has(m)) m.dispose();
    });
  }
  resize() {}   // (the sprites are sized in the world)

  // ---------- one-shots
  burst(pos, {n = 10, c = C.white, s = 0.5, sp = 3, up = 2, life = 0.6, g = 6, cell = CELL.soft, add = true, a0 = 1, drag = 1.5, s1, y = 0.3, floor, bounce}) {
    const P = add ? this.add : this.norm;
    for (let i = 0; i < n; i++) { const a = Math.random() * Math.PI * 2, v = sp * rnd(0.3, 1);
      P.emit({x: pos.x + rnd(-0.1, 0.1), y: (pos.y || 0) + y, z: pos.z + rnd(-0.1, 0.1), vx: Math.cos(a) * v, vz: Math.sin(a) * v, vy: up * rnd(0.4, 1.2), g, drag, life: life * rnd(0.7, 1.2), s0: s, s1: s1 ?? s * 0.3, c, a0, cell, vr: rnd(-6, 6), floor, bounce}); }
  }
  // a blast's front over the ground out to r: dust thrown in clumps, its leading edge lit in col, and puffs of dust riding it
  // (one eased envelope for both)
  ring(pos, r, col, life = 0.45, y = 0.05, glow = 0.3) {
    this.dc.emit({kind: D.SHOCK, x: pos.x, z: pos.z, y, r: r * 1.12 + 0.2, life: life * 1.15, q0: 0.08, q1: 0.9, qe: 1, c: [0.42, 0.38, 0.34], c2: mul(lin(col), glow), a0: 0.85, a1: 0});
    this.shock(pos, r, {n: Math.round(5 + r * 3.5), c: C.dust, s: 0.55 + r * 0.1, life: life * 1.1, y: 0.12, cell: CELL.smoke, add: false, a0: 0.42});
  }
  // a fixed pool: adding or removing lights at run time would recompile every shader (a hitch on phones)
  flashLight(pos, col, I = 30, life = 0.25, y = 1.5) {
    const L = this.lights.reduce((a, b) => (a.userData.until < b.userData.until ? a : b));
    L.color.set(col); L.position.set(pos.x, y, pos.z); L.userData.until = performance.now() + life * 1000;
    this.things.push({life, age: 0, tick: (t, k) => { if (L.userData.until <= performance.now() + 1) L.intensity = I * (1 - k); else L.intensity = Math.max(L.intensity, I * (1 - k)); if (k >= 1) L.intensity = 0; }});
  }
  land(pos, r, team, mass) {
    const big = mass >= 15;
    this.burst(pos, {n: big ? 26 : 10, c: C.dust, s: big ? 1.2 : 0.6, sp: big ? 4.5 : 2.2, up: 0.7, life: big ? 0.9 : 0.55, g: 1, cell: CELL.smoke, add: false, a0: 0.55, y: 0.15});
    this.ring(pos, r * (big ? 4 : 2.2), '#' + TEAM_COL[team].getHexString(), 0.4, 0.05, 0.25);
    if (big) this.stage.kick(0.55);
  }
  poof(pos, h, card, y0 = 0) {
    const p = {x: pos.x, y: y0, z: pos.z};
    this.burst(p, {n: 14, c: C.white, s: 0.9, sp: 1.6, up: 1.2, life: 0.7, g: -0.5, cell: CELL.smoke, add: false, a0: 0.75, y: h * 0.5});
    this.burst(p, {n: 8, c: C.gold, s: 0.45, sp: 2.4, up: 4, life: 1.0, g: 12, cell: CELL.coin, add: false, y: h * 0.6, floor: 0.05, bounce: 0.35, drag: 0.6});
  }
  // back up: a column of golden light, motes and twinkles rising through it, the ground under lit
  revive(pos) {
    this.dc.emit({kind: D.GLOW, x: pos.x, z: pos.z, r0: 0.6, r1: 1.7, ease: 1, life: 0.9, c: [1.3, 1, 0.4], a0: 1, a1: 0, add: 1});
    this.sp.emit({kind: S.GLOW, x: pos.x, y: 1, z: pos.z, life: 0.5, w0: 1.2, w1: 2.6, asp: 1.8, c: [1.5, 1.2, 0.5], a0: 0.9, a1: 0, add: 1});
    for (let i = 0; i < 16; i++) { const a = rnd(0, 6.28), d = rnd(0.2, 0.9);
      this.sp.emit({kind: i % 3 ? S.GLOW : S.FLARE, x: pos.x + Math.cos(a) * d, y: rnd(0.1, 0.8), z: pos.z + Math.sin(a) * d, vy: rnd(1.5, 3), drag: 0.8, curl: 2.5, cx: pos.x, cz: pos.z, life: rnd(0.7, 1.1), w0: rnd(0.2, 0.4), w1: 0.05, c: [1.6, 1.3, 0.5], a0: 1, a1: 0, add: 1}); }
  }
  hit(pos, heavy, card) {
    const c = card === 'ket' ? [1, 0.5, 0.8] : card === 'useless' ? C.gold : C.white;
    this.burst(pos, {n: heavy ? 12 : 6, c, s: heavy ? 0.65 : 0.4, sp: heavy ? 4 : 2.5, up: 1.5, life: 0.3, g: 4, cell: CELL.spark, y: 0.8});
    if (card === 'useless') this.burst(pos, {n: 3, c: C.gold, s: 0.3, sp: 2, up: 3, life: 0.6, g: 10, cell: CELL.coin, add: false, y: 0.6, floor: 0.05, bounce: 0.3});
    if (heavy) { this.burst(pos, {n: 1, c: C.white, s: 2.0, sp: 0, up: 0, life: 0.14, g: 0, cell: CELL.star, y: 0.9, s1: 2.6}); this.stage.kick(0.18); }
  }
  slam(pos, r) {
    this.burst(pos, {n: 40, c: C.dust, s: 1.4, sp: 6, up: 1, life: 1.1, g: 1, cell: CELL.smoke, add: false, a0: 0.6, y: 0.2});
    this.burst(pos, {n: 18, c: [0.4, 0.75, 1], s: 0.5, sp: 5, up: 6, life: 0.9, g: 14, cell: CELL.drop, y: 0.3});
    this.ring(pos, r, '#bfe3ff', 0.55); this.stage.kick(0.9);
  }
  splash(pos, r, card) {
    const col = card === 'lmao' ? C.yellow : card === 'alon' ? C.fire : card === 'bag' ? C.gold : C.white;
    this.burst(pos, {n: 16, c: col, s: 0.8, sp: r * 4, up: 2, life: 0.5, g: 2, cell: CELL.soft, y: 0.4});
    this.ring(pos, r * 1.1, card === 'lmao' ? '#ffe14a' : '#ffb14a', 0.4);
  }
  // a pulse of healing: green light washing out over the ground to r, motes rising off it, a few hearts
  heal(pos, r) {
    this.dc.emit({kind: D.GLOW, x: pos.x, z: pos.z, r0: r * 0.3, r1: r * 1.05, ease: 1, life: 0.8, c: [0.45, 1.3, 0.4], a0: 1, a1: 0, add: 1});
    this.front({x: pos.x, z: pos.z}, r, 16, 0.6, {kind: S.WISP, y: 0.3, vy: 0.8, w0: 0.5, w1: 0.9, c: [0.5, 1.4, 0.5], a0: 0.7, a1: 0, add: 1}, 0.15);
    for (let i = 0; i < 12; i++) { const a = rnd(0, 6.28), d = Math.sqrt(Math.random()) * r * 0.85;
      this.sp.emit({kind: S.GLOW, x: pos.x + Math.cos(a) * d, y: 0.15, z: pos.z + Math.sin(a) * d, vy: rnd(1, 2.2), life: rnd(0.6, 1), w0: 0.25, w1: 0.05, c: [0.7, 1.6, 0.6], a0: 1, a1: 0, add: 1}); }
    this.burst(pos, {n: 5, c: C.green, s: 0.45, sp: r * 0.6, up: 1.5, life: 1.0, g: -1.5, cell: CELL.heart, y: 0.3});
  }
  healTick(pos) { this.burst(pos, {n: 3, c: C.green, s: 0.4, sp: 0.5, up: 2.2, life: 0.6, g: -1, cell: CELL.cross, y: 1.4}); }
  explode(pos, big) {
    const k = big ? 1.6 : 1;
    this.burst(pos, {n: 26 * k, c: C.fire, s: 2.2 * k, sp: 5 * k, up: 4, life: 0.8, g: -1, cell: CELL.flame, y: 1.5 * k, drag: 2});
    this.burst(pos, {n: 30 * k, c: C.smoke, s: 2.6 * k, sp: 3 * k, up: 3.5, life: 2.2, g: -0.8, cell: CELL.smoke, add: false, a0: 0.85, y: 1.2 * k, drag: 1.2});
    this.burst(pos, {n: 24 * k, c: [0.3, 0.32, 0.36], s: 0.55, sp: 7 * k, up: 9, life: 1.6, g: 16, cell: CELL.chunk, add: false, y: 1.5, floor: 0.08, bounce: 0.3, drag: 0.3});
    this.burst(pos, {n: 40 * k, c: C.yellow, s: 0.35, sp: 9 * k, up: 7, life: 0.9, g: 10, cell: CELL.spark, y: 1.5});
    this.burst(pos, {n: 18 * k, c: C.gold, s: 0.5, sp: 5 * k, up: 8, life: 1.8, g: 14, cell: CELL.coin, add: false, y: 2, floor: 0.06, bounce: 0.4, drag: 0.4});
    this.ring(pos, 5 * k, '#ffd28a', 0.6); this.flashLight(pos, '#ffaa55', 120 * k, 0.5, 3); this.scorch(pos.x, pos.z, 2.2 * k);
    this.dc.emit({kind: D.CRACK, x: pos.x, z: pos.z, r: 2.6 * k, life: 7, c: [0.05, 0.04, 0.035], c2: [1, 0.4, 0.1], q0: 1, q1: 0, a0: 0.9, a1: 0});
    this.stage.kick(big ? 1.2 : 0.85);
    // a lingering smoke column
    const at = {x: pos.x, z: pos.z}, until = performance.now() + 6000 * k;
    this.things.push({life: 9 * k, age: 0, tick: (t, q) => {
      if (Math.random() < 0.35) this.norm.emit({x: at.x + rnd(-0.6, 0.6), y: 1, z: at.z + rnd(-0.6, 0.6), vy: rnd(0.8, 1.4), vx: 0.3, life: 2.5, s0: 1, s1: 2.6, c: C.smoke, a0: 0.5 * (1 - q), cell: CELL.smoke});
      // the rubble keeps burning for a while
      if (q < 0.6 && Math.random() < 0.5) this.add.emit({x: at.x + rnd(-1, 1) * k, y: 0.3 + rnd(0, 0.5), z: at.z + rnd(-1, 1) * k, vy: rnd(0.6, 1.4), life: 0.6, s0: rnd(0.5, 0.9), s1: 0.1, c: C.fire, cell: CELL.flame});
    }});
    void until;
  }
  // FIRE SALE: a burning coin bursts on its target
  boom(pos, r) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.burst(p, {n: 22, c: C.fire, s: 1.3, sp: r * 3.2, up: 2.5, life: 0.5, g: -1, cell: CELL.flame, y: 0.5, drag: 2.5});
    this.burst(p, {n: 10, c: C.smoke, s: 1.1, sp: r * 1.5, up: 1.5, life: 1.1, g: -0.6, cell: CELL.smoke, add: false, a0: 0.55, y: 0.6});
    this.burst(p, {n: 6, c: C.gold, s: 0.4, sp: 3, up: 5, life: 0.9, g: 14, cell: CELL.coin, add: false, y: 0.6, floor: 0.05, bounce: 0.3});
    this.ring(p, r * 1.15, '#ff9a3a', 0.35); this.flashLight(p, '#ff8a30', 40, 0.25, 1.2); this.scorch(pos.x, pos.z, r * 0.6);
  }
  // HONEYPOT: an electric arc from its coil to the target
  zap(from, to) {
    const pts = [from.clone()], n = 7;
    for (let i = 1; i < n; i++) { const k = i / n; pts.push(new THREE.Vector3().lerpVectors(from, to, k).add(new THREE.Vector3(rnd(-0.3, 0.3), rnd(-0.3, 0.3), rnd(-0.3, 0.3)))); }
    pts.push(to.clone());
    const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.1), n * 3, 0.07, 5, false), new THREE.MeshBasicMaterial({color: '#ffe680', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false}));
    this.scene.add(m);
    this.things.push({obj: m, life: 0.16, age: 0, tick: (t, k) => { m.material.opacity = (1 - k) * (Math.random() < 0.5 ? 1 : 0.5); }});
    this.burst(to, {n: 8, c: C.yellow, s: 0.45, sp: 2.5, up: 2, life: 0.3, g: 4, cell: CELL.spark, y: 0});
    this.flashLight(to, '#ffe066', 25, 0.15, 0.5);
  }
  muzzle(pos, team) { this.burst(pos, {n: 4, c: teamRGB(team), s: 0.5, sp: 1, up: 0.5, life: 0.18, g: 0, cell: CELL.spark, y: 0}); }
  text(pos, str, col = '#fff') { this.onText?.(pos, str, col); }

  // ---------- the troops' abilities
  // n particles thrown out from the middle so they reach radius r as the ring does (an eased stop)
  shock(pos, r, {n = 20, c = C.white, s = 0.5, life = 0.35, y = 0.15, cell = CELL.soft, add = true, a0 = 1}) {
    const P = add ? this.add : this.norm, drag = 4 / life, v0 = (r - 0.25) * drag / 0.98;
    for (let i = 0; i < n; i++) { const a = (i + Math.random() * 0.5) / n * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
      P.emit({x: pos.x + ca * 0.25, y: (pos.y || 0) + y, z: pos.z + sa * 0.25, vx: ca * v0, vz: sa * v0, drag, life, s0: s, s1: s * 0.4, c, a0, cell}); }
  }
  // a filled disc that flashes and fades (the area something just hit)
  flashDisc(pos, r, col, life = 0.2, op = 0.3) { this.dc.emit({kind: D.GLOW, x: pos.x, z: pos.z, r0: r * 0.8, r1: r * 1.15, ease: 1, life: life * 1.4, c: mul(lin(col), op * 4), a0: 1, a1: 0, add: 1}); }
  // a dome swelling out to r over life (eased out), lit at its rim in col -> core, rippling (rip: rings), eaten away as it goes;
  // hy: its height for its radius; grow: the size it starts at
  shell(p, r, {life = 0.4, col = [1, 1, 1], core = [1.5, 1.5, 1.5], hy = 0.5, rip = 0, a = 1, delay = 0, grow = 0.12}) {
    const m = this.shells.get(), u = m.material.uniforms; u.uCol.value.setRGB(...col); u.uCore.value.setRGB(...core); u.uRip.value = rip; m.position.set(p.x, p.y || 0, p.z); m.visible = false;
    this.things.push({life: life + delay, age: 0, tick: (t, q, age) => {
      if (age < delay) return; const k = Math.min(1, (age - delay) / life), e = 1 - (1 - k) ** 3, s = r * (grow + (1 - grow) * e);
      m.visible = true; m.scale.set(s, s * hy, s); u.uK.value = k; u.uA.value = a; u.uTime.value = this.time;
      if (q >= 1) this.shells.put(m);
    }});
  }
  // a held ground mark let go: it fades out over life from where it is
  release(d, life) { Object.assign(d, {hold: false, age: 0, life, a0: d.a ?? d.a0, a1: 0, q0: d.q ?? d.q0, q1: 0, r0: d.r ?? d.r0, r1: d.r ?? d.r0, k: 0}); }
  // n sprites (o: a sprite's fields) thrown out from the middle so they ride a front reaching r over life, easing to a stop:
  // the matter of a shockwave, on the same curve as its ground mark (SHOCK, qe). j: how ragged the front is (speed spread)
  // It comes out in clumps (never a clean ring): thicker and further out in places, thin or broken between them.
  front(p, r, n, life, o, j = 0.12) {
    const drag = 4 / life, v0 = (r - 0.3) * drag / 0.98, ph = rnd(0, 6.283), lb = 2 + (Math.random() * 3 | 0);
    for (let i = 0; i < n; i++) { const a = (i + Math.random() * 0.8) / n * 6.283, ca = Math.cos(a), sa = Math.sin(a), cl = Math.sin(a * lb + ph) * 0.6 + Math.sin(a * (lb + 3) - ph * 1.7) * 0.4;
      if (cl < -0.5 && Math.random() < 0.65) continue;
      const q = rnd(1 - j * 2, 1 + j * 0.6) * (1 + cl * 0.14), k = 1 + cl * 0.35;
      this.sp.emit({...o, x: p.x + ca * 0.3, y: (o.y ?? 0.2) + rnd(-0.05, 0.12), z: p.z + sa * 0.3, vx: ca * v0 * q, vz: sa * v0 * q, drag, life: life * rnd(0.85, 1.1), seed: Math.random(),
        w0: o.w0 != null ? o.w0 * k : undefined, w1: o.w1 != null ? o.w1 * k : undefined, w: o.w != null ? o.w * k : undefined}); }
  }
  // POPCAT: every pop is her mouth's: a pink bubble swells at it and bursts (a flash, droplets), and the sound of it goes out as
  // a wave made of what it throws: dust torn off the ground in clumps (a ragged front), pink speed lines, wisps of pink energy,
  // over a mark of dust dragged across the ground (all on one front out to r)
  wave(pos, r) {
    const p = {x: pos.x, y: 0, z: pos.z}, L = 0.45, hy = 1.25;
    this.sp.emit({kind: S.BUBBLE, x: p.x, y: hy, z: p.z, life: 0.09, w0: 0.35, w1: 1.5, c: [1.4, 0.55, 1.2], a0: 1, a1: 1, add: 0.6});
    this.things.push({life: 0.09, age: 0, tick: (t, q) => { if (q < 1) return;
      this.sp.emit({kind: S.FLARE, x: p.x, y: hy, z: p.z, life: 0.16, w0: 2.2, w1: 0.3, c: [2, 1.3, 1.8], a0: 1, a1: 0.5, add: 1, rot: 0});
      this.sp.emit({kind: S.GLOW, x: p.x, y: hy, z: p.z, life: 0.22, w0: 1.2, w1: 2.4, c: [1.3, 0.5, 1.05], a0: 0.8, a1: 0, add: 1});
      for (let i = 0; i < 12; i++) { const a = rnd(0, 6.28), v = rnd(2.5, 4.5);
        this.sp.emit({kind: S.SPARK, x: p.x, y: hy, z: p.z, vx: Math.cos(a) * v, vy: rnd(0.5, 3), vz: Math.sin(a) * v, g: 9, drag: 1.5, life: rnd(0.35, 0.55), w: 0.14, asp: 0.6, st: 0.04, c: [1.6, 0.7, 1.4], a0: 1, a1: 0, add: 1}); }
      this.front(p, r * 0.98, 28, L * 1.2, {kind: S.SMOKE, y: 0.22, w0: 0.5, w1: 1.35, ease: 1, c: [0.68, 0.62, 0.58], a0: 0.75, a1: 0.05, add: 0}, 0.2);
      this.front(p, r * 1.05, 28, L * 0.8, {kind: S.SPARK, y: 0.45, vy: 0.8, g: 3, w: 0.22, asp: 0.3, st: 0.09, c: [1.8, 0.65, 1.4], a0: 1, a1: 0, add: 1}, 0.15);
      this.front(p, r, 9, L, {kind: S.WISP, y: 0.5, w0: 0.4, w1: 0.9, ease: 1, c: [1.4, 0.4, 1.1], a0: 0.55, a1: 0, add: 1}, 0.2);
      this.dc.emit({kind: D.SHOCK, x: p.x, z: p.z, r: r * 1.12 + 0.2, life: L * 1.2, q0: 0.08, q1: 0.9, qe: 1, c: [0.42, 0.38, 0.36], c2: [0.4, 0.13, 0.3], a0: 0.8, a1: 0});
      this.dc.emit({kind: D.GLOW, x: p.x, z: p.z, r0: 0.6, r1: r * 0.5, ease: 1, life: 0.2, c: [1, 0.3, 0.75], a0: 1, a1: 0, add: 1});
      this.stage.kick(0.22);
    }});
  }
  // SWORDCAT: the spin slash: a smear of steel light swept once round her at blade height, white at the blade's edge and
  // streaked along the swing, sparks flung off its edge, the air it moves dragging dust over the ground
  spin(pos, r, y = 0.75) {
    const ARC = Math.PI * 1.6, m = new THREE.Mesh(this.slashGeo ||= new THREE.RingGeometry(0.42, 1, 64, 3, 0, ARC), slashMaterial(this.noise, ARC, 0.42));
    this.shared.add(this.slashGeo); m.material.uniforms.uCol.value.setRGB(0.35, 0.6, 1.1); m.material.uniforms.uCore.value.setRGB(1, 1, 1.1);
    const a0 = Math.random() * 6.28; m.rotation.x = -Math.PI / 2; m.position.set(pos.x, y, pos.z); m.scale.setScalar(r * 1.02); m.renderOrder = 6; this.scene.add(m);
    this.things.push({obj: m, life: 0.32, age: 0, tick: (t, k) => { m.rotation.z = a0 + (1 - (1 - k) ** 2) * Math.PI * 2.3; m.material.uniforms.uK.value = k; m.scale.setScalar(r * (0.92 + k * 0.14)); }});
    for (let i = 0; i < 18; i++) { const a = Math.random() * 6.28, ca = Math.cos(a), sa = Math.sin(a);
      this.sp.emit({kind: S.SPARK, x: pos.x + ca * r, y: y + rnd(-0.1, 0.2), z: pos.z + sa * r, vx: sa * 5 + ca * 1.2, vy: rnd(0.5, 1.8), vz: -ca * 5 + sa * 1.2, g: 5, drag: 2, life: rnd(0.25, 0.4), w: 0.16, asp: 0.3, st: 0.05, c: [1.3, 1.5, 1.9], a0: 1, a1: 0, add: 1}); }
    this.front({x: pos.x, z: pos.z}, r * 1.05, 14, 0.4, {kind: S.SMOKE, y: 0.15, w0: 0.4, w1: 1, ease: 1, c: [0.66, 0.62, 0.6], a0: 0.5, a1: 0, add: 0}, 0.2);
    this.stage.kick(0.1);
  }
  // BONK: the bat lands: a white flash, a comic star popping on the target with little ones flung off it, the ground under it
  // cracked and dust thrown up ("BONK!" is the overlay's)
  knock(pos) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.sp.emit({kind: S.FLARE, x: p.x, y: 1.1, z: p.z, life: 0.12, w0: 2.6, w1: 0.6, c: [2, 1.9, 1.4], a0: 1, a1: 0.4, add: 1, rot: 0});
    this.burst(p, {n: 1, c: C.yellow, s: 1.5, sp: 0, up: 0, life: 0.2, g: 0, cell: CELL.star, y: 1.1, s1: 2.4, add: false});
    this.burst(p, {n: 7, c: C.yellow, s: 0.45, sp: 3.2, up: 2.5, life: 0.55, g: 6, cell: CELL.star, y: 1.0, add: false});
    this.front(p, 1.3, 12, 0.45, {kind: S.SMOKE, y: 0.15, w0: 0.4, w1: 1.1, ease: 1, c: [0.66, 0.62, 0.58], a0: 0.6, a1: 0, add: 0}, 0.2);
    this.dc.emit({kind: D.CRACK, x: p.x, z: p.z, r: 1, life: 2, c: [0.08, 0.07, 0.06], c2: [0, 0, 0], q0: 0, a0: 0.8, a1: 0});
  }
  // MOO DENG starts her charge: a snort out of each nostril, a kick of dust behind
  snort(pos, face) {
    const fx = Math.sin(face), fz = Math.cos(face), nx = pos.x + fx * 0.7, nz = pos.z + fz * 0.7;
    for (const side of [-1, 1]) for (let i = 0; i < 4; i++) this.norm.emit({x: nx - fz * side * 0.12, y: 0.6, z: nz + fx * side * 0.12, vx: fx * 1.6 - fz * side * 0.9 + rnd(-0.2, 0.2), vy: rnd(0.2, 0.6), vz: fz * 1.6 + fx * side * 0.9 + rnd(-0.2, 0.2), drag: 3, life: 0.6, s0: 0.35, s1: 1.1, c: C.white, a0: 0.7, cell: CELL.smoke});
    this.burst({x: pos.x - fx * 0.5, y: 0, z: pos.z - fz * 0.5}, {n: 10, c: C.dust, s: 0.7, sp: 2, up: 0.8, life: 0.6, g: 1, cell: CELL.smoke, add: false, a0: 0.55, y: 0.15});
  }
  // ...and it lands: a heavy hit (the 'hit' of it plays too): a big flash, a ring of dust thrown wide, chunks, a kick. PUDGY's belly
  // only throws up snow; THE GOAT's adds gold stars
  chargeHit(pos, card) {
    const p = {x: pos.x, y: 0, z: pos.z};
    if (card === 'pudgy') {
      this.sp.emit({kind: S.FLARE, x: p.x, y: 0.7, z: p.z, life: 0.14, w0: 2.2, w1: 0.5, c: [1.6, 1.8, 2], a0: 1, a1: 0.3, add: 1, rot: 0});
      this.front(p, 1.6, 14, 0.45, {kind: S.SMOKE, y: 0.2, w0: 0.5, w1: 1.2, ease: 1, c: [0.86, 0.93, 1], a0: 0.75, a1: 0, add: 0.1}, 0.2);
      this.burst(p, {n: 10, c: C.soap, s: 0.3, sp: 3.5, up: 4, life: 0.5, g: 10, cell: CELL.drop, add: false, y: 0.3, floor: 0.05});
      this.stage.kick(0.25); return;
    }
    this.sp.emit({kind: S.FLARE, x: p.x, y: 1, z: p.z, life: 0.16, w0: 3.2, w1: 0.8, c: [2, 1.6, 1.1], a0: 1, a1: 0.3, add: 1, rot: 0});
    if (card === 'goat') this.burst(p, {n: 8, c: C.gold, s: 0.5, sp: 3.5, up: 4, life: 0.7, g: 8, cell: CELL.star, add: false, y: 1});
    this.burst(p, {n: 16, c: C.ember, s: 0.45, sp: 5, up: 3, life: 0.4, g: 6, cell: CELL.spark, y: 0.7});
    this.shock(p, 2.0, {n: 18, c: C.dust, s: 1.1, life: 0.55, y: 0.15, cell: CELL.smoke, add: false, a0: 0.6});
    this.burst(p, {n: 10, c: [0.42, 0.36, 0.3], s: 0.4, sp: 4, up: 6, life: 1.0, g: 16, cell: CELL.chunk, add: false, y: 0.3, floor: 0.06, bounce: 0.3, drag: 0.4});
    this.ring(p, 2.0, '#ffb070', 0.4); this.flashLight(p, '#ffb070', 40, 0.22, 1.2); this.stage.kick(0.6);
    this.dc.emit({kind: D.CRACK, x: p.x, z: p.z, r: 1.8, life: 3, c: [0.08, 0.07, 0.06], c2: [1, 0.5, 0.2], q0: 0.6, q1: 0, a0: 0.85, a1: 0});
  }
  // TROLLFACE's blink: he goes in a twist of smoke and violet light and comes out of another, a swirl left on the ground at each
  // end (he is drawn there at once)
  blink(from, to, h = 1.3) {
    const H = visH(h);
    for (const [p, big] of [[from, false], [to, true]]) {
      const q = {x: p.x, y: 0, z: p.z};
      for (let i = 0; i < 16; i++) { const a = rnd(0, 6.28), d = rnd(0.1, 0.6);
        this.sp.emit({kind: S.SMOKE, x: q.x + Math.cos(a) * d, y: rnd(0.2, H * 0.9), z: q.z + Math.sin(a) * d, vx: Math.cos(a) * 0.8, vy: rnd(0.2, 0.9), vz: Math.sin(a) * 0.8, drag: 2.5, curl: big ? 5 : -5, cx: q.x, cz: q.z,
          life: rnd(0.55, 0.8), w0: rnd(0.6, 0.9), w1: rnd(1.1, 1.5), ease: 1, c: [0.86, 0.82, 0.95], a0: 0.85, a1: 0, add: 0}); }
      for (let i = 0; i < 8; i++) this.sp.emit({kind: S.WISP, x: q.x + rnd(-0.4, 0.4), y: rnd(0.3, H * 0.8), z: q.z + rnd(-0.4, 0.4), vy: 0.6, curl: 4, cx: q.x, cz: q.z, life: 0.5, w0: 0.6, w1: 1, c: [0.9, 0.55, 1.5], a0: 0.8, a1: 0, add: 1});
      this.burst(q, {n: 7, c: [1.4, 1.3, 1.6], s: 0.45, sp: 2.2, up: 1.5, life: 0.4, g: 0, cell: CELL.star, y: H * 0.5});
      this.dc.emit({kind: D.SWIRL, x: q.x, z: q.z, r: big ? 1.3 : 1.1, life: 0.6, c: [0.3, 0.25, 0.4], c2: [0.8, 0.45, 1.3], q0: 1, a0: 0.9, a1: 0});
      if (big) this.flashLight(q, '#d8ccff', 16, 0.15, 1.2);
    }
  }
  // his surprise hit: a crit flash on the target ("!" is the overlay's); TOSHI's is blue, a cross of two cuts through it ("CRIT!")
  surprise(pos, cut) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.sp.emit({kind: S.FLARE, x: p.x, y: 1, z: p.z, life: 0.16, w0: 2.8, w1: 0.6, c: cut ? [1.3, 1.8, 2] : [2, 2, 1.6], a0: 1, a1: 0.4, add: 1, rot: 0.4});
    this.sp.emit({kind: S.GLOW, x: p.x, y: 1, z: p.z, life: 0.25, w0: 1, w1: 2.4, c: cut ? [0.4, 1, 1.6] : [1.5, 1.3, 0.4], a0: 0.9, a1: 0, add: 1});
    this.burst(p, {n: 14, c: cut ? C.cyan : C.yellow, s: 0.45, sp: 4, up: 2.5, life: 0.4, g: 5, cell: CELL.spark, y: 0.9});
    if (cut) for (const s of [-1, 1]) this.sp.emit({kind: S.SPARK, x: p.x - s * 1, y: 1.7, z: p.z, vx: s * 11, vy: -8, life: 0.15, w: 0.55, asp: 0.32, st: 0.11, c: [1.5, 1.9, 2], a0: 1, a1: 0, add: 1});
    this.flashLight(p, cut ? '#9fe0ff' : '#fff2a0', 26, 0.18, 1.4); this.stage.kick(0.25);
  }
  // TOSHI's dash: no puff, a streak: a blue cut over the ground from where he stood to behind his target (one shared quad, narrowing
  // to nothing), his afterimages hanging along it, sparks thrown the way he went, dust kicked at each end (he is drawn there at once)
  dash(from, to, h = 1.15) {
    const H = visH(h), dx = to.x - from.x, dz = to.z - from.z, L = Math.hypot(dx, dz) || 1, ux = dx / L, uz = dz / L;
    if (!this.dashMat) { this.dashMat = new THREE.MeshBasicMaterial({map: soft(), color: '#7fd4ff', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false}); this.dashGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2); this.shared.add(this.dashMat); this.shared.add(this.dashGeo); }
    const m = new THREE.Mesh(this.dashGeo, this.dashMat); m.position.set((from.x + to.x) / 2, H * 0.35, (from.z + to.z) / 2); m.rotation.y = Math.atan2(dx, dz); m.renderOrder = 6; m.scale.set(1, 1, L + 1); this.scene.add(m);
    this.things.push({obj: m, life: 0.24, age: 0, tick: (t, k) => { m.scale.x = 1.1 * (1 - k) ** 2 + 0.001; }});
    for (let i = 0; i < 4; i++) { const k = (i + 0.5) / 4;
      this.sp.emit({kind: S.GLOW, x: from.x + dx * k, y: H * 0.5, z: from.z + dz * k, life: 0.18 + k * 0.22, w: 0.95, asp: 1.9, rot: 0, c: [0.35, 0.75, 1.5], a0: 0.45 + k * 0.45, a1: 0, add: 1}); }
    for (let i = 0; i < 10; i++) { const k = Math.random(), v = rnd(3, 8);
      this.sp.emit({kind: S.SPARK, x: from.x + dx * k + rnd(-0.2, 0.2), y: rnd(0.2, H * 0.8), z: from.z + dz * k + rnd(-0.2, 0.2), vx: ux * v, vz: uz * v, life: rnd(0.15, 0.3), w: 0.13, asp: 0.4, st: 0.06, c: [0.6, 1.3, 1.8], a0: 1, a1: 0, add: 1}); }
    for (const [p, n] of [[from, 6], [to, 4]]) this.burst({x: p.x, y: 0, z: p.z}, {n, c: C.dust, s: 0.7, sp: 1.5, up: 0.5, life: 0.5, g: 1, cell: CELL.smoke, add: false, a0: 0.5, y: 0.15});
    this.flashLight(to, '#8fdcff', 14, 0.14, 1.2); this.stage.kick(0.08);
  }
  // SLERF's every punch: the ground jumps round him out to r: a ragged front of dust, a crack under the fist, clods thrown up, a short
  // kick (it comes every couple of seconds: far less than the Whale's landing)
  quake(pos, r) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.ring(p, r, '#d8c8a8', 0.45, 0.05, 0.2);
    this.dc.emit({kind: D.CRACK, x: p.x, z: p.z, r: r * 0.7, life: 1.6, c: [0.07, 0.06, 0.05], c2: [0, 0, 0], q0: 0, a0: 0.8, a1: 0});
    this.burst(p, {n: 8, c: [0.36, 0.3, 0.25], s: 0.35, sp: 3.5, up: 5, life: 0.7, g: 14, cell: CELL.clod, add: false, y: 0.2, floor: 0.05, bounce: 0.25});
    this.stage.kick(0.3);
  }
  // FLOKI goes berserk: a burst of flame up round him, a red front over the ground (his glow from here on is units.js's)
  berserk(pos) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.sp.emit({kind: S.FLARE, x: p.x, y: 1.2, z: p.z, life: 0.16, w0: 3, w1: 0.6, c: [2, 0.55, 0.3], a0: 1, a1: 0.3, add: 1, rot: 0});
    this.burst(p, {n: 14, c: C.fire, s: 1, sp: 2.4, up: 3, life: 0.5, g: -1, cell: CELL.flame, y: 0.4, drag: 2.5});
    this.ring(p, 1.9, '#ff5a2a', 0.4, 0.05, 0.5); this.flashLight(p, '#ff4a20', 28, 0.25, 1.4); this.stage.kick(0.25);
  }
  // MICHI's trap closes on a troop: yarn flung up round its feet, a puff of fluff (the tangle it wears is units.js's)
  snare(pos) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.burst(p, {n: 8, c: C.yarn, s: 0.38, sp: 2, up: 3, life: 0.5, g: 9, cell: CELL.yarn, add: false, y: 0.3, floor: 0.05, bounce: 0.2});
    this.sp.emit({kind: S.GLOW, x: p.x, y: 0.5, z: p.z, life: 0.2, w0: 0.8, w1: 1.8, c: [1.3, 0.45, 0.9], a0: 0.8, a1: 0, add: 1});
  }
  // APU's mend: a stream of warm light from him to the one he mends, crosses and a flash where it lands (the shield it leaves is units.js's)
  mend(from, to) {
    const T = 0.26, vx = (to.x - from.x) / T, vy = (to.y - from.y) / T, vz = (to.z - from.z) / T;
    for (let i = 0; i < 9; i++) { const k = i / 9 * 0.6;
      this.sp.emit({kind: i % 3 ? S.GLOW : S.FLARE, x: from.x + vx * T * k, y: from.y + vy * T * k, z: from.z + vz * T * k, vx, vy, vz, life: T * (1 - k), w: i % 3 ? 0.42 : 0.5, rot: 0, c: [1.6, 1.4, 0.7], a0: 1, a1: 0.5, add: 1}); }
    this.sp.emit({kind: S.FLARE, x: to.x, y: to.y, z: to.z, life: 0.2, w0: 1.8, w1: 0.4, c: [1.8, 1.6, 0.8], a0: 1, a1: 0.3, add: 1, rot: 0});
    this.burst({x: to.x, y: to.y - 0.3, z: to.z}, {n: 5, c: C.holy, s: 0.4, sp: 1, up: 2, life: 0.6, g: -1, cell: CELL.cross, y: 0});
  }
  // the shield goes (run down or broken): gold shards off it
  shieldBreak(pos) {
    for (let i = 0; i < 10; i++) { const a = rnd(0, 6.28), v = rnd(1.5, 3.5);
      this.sp.emit({kind: S.SHARD, x: pos.x, y: pos.y, z: pos.z, vx: Math.cos(a) * v, vy: rnd(0.5, 3), vz: Math.sin(a) * v, g: 9, drag: 1, vr: rnd(-8, 8), life: rnd(0.3, 0.5), w: rnd(0.14, 0.24), asp: 1.5, c: [1.5, 1.25, 0.55], a0: 1, a1: 0, add: 0.5}); }
  }
  // PANIC SELL lands on a troop: the sweat flies (and a little more while it runs: units.js)
  fear(pos) { this.burst({x: pos.x, y: 0, z: pos.z}, {n: 6, c: C.blue, s: 0.3, sp: 2, up: 3, life: 0.45, g: 9, cell: CELL.drop, add: false, y: 1.4, floor: 0.05}); }
  // WALTER goes under: earth thrown up, a hole left for a moment
  dig(pos) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.burst(p, {n: 10, c: C.dirt, s: 0.34, sp: 2.5, up: 4.5, life: 0.7, g: 13, cell: CELL.clod, add: false, y: 0.15, floor: 0.04, bounce: 0.2});
    this.burst(p, {n: 6, c: C.dust, s: 0.8, sp: 1.4, up: 0.8, life: 0.6, g: 1, cell: CELL.smoke, add: false, a0: 0.55, y: 0.2});
    this.dc.emit({kind: D.STAIN, x: p.x, z: p.z, r: 0.8, life: 1.4, c: [0.08, 0.055, 0.04], c2: [0, 0, 0], a0: 0.9, a1: 0});
  }
  // ...and up he comes: the ground bursts: clods everywhere, dust out to r (what he stuns), the earth split
  surface(pos, r) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.sp.emit({kind: S.FLARE, x: p.x, y: 0.8, z: p.z, life: 0.14, w0: 2.4, w1: 0.5, c: [1.9, 1.6, 1.1], a0: 1, a1: 0.3, add: 1, rot: 0});
    this.burst(p, {n: 16, c: C.dirt, s: 0.4, sp: 4, up: 6.5, life: 0.9, g: 14, cell: CELL.clod, add: false, y: 0.2, floor: 0.05, bounce: 0.25});
    this.ring(p, r * 1.05, '#d8b888', 0.42, 0.05, 0.25);
    this.dc.emit({kind: D.CRACK, x: p.x, z: p.z, r: r * 0.85, life: 2, c: [0.08, 0.06, 0.05], c2: [0, 0, 0], q0: 0, a0: 0.85, a1: 0});
    this.stage.kick(0.35);
  }
  // HARD FORK: a copy steps out (or a copy's one hit point goes): a blink of the chain's cyan, a fork rising off it
  forkOut(pos, h = 1.3) {
    const y = h * 0.45;
    this.sp.emit({kind: S.FLARE, x: pos.x, y, z: pos.z, life: 0.16, w0: 1.8, w1: 0.3, c: [1, 1.7, 2], a0: 1, a1: 0.3, add: 1, rot: 0});
    this.sp.emit({kind: S.GLOW, x: pos.x, y, z: pos.z, life: 0.25, w0: 0.9, w1: 1.7, asp: 1.5, c: [0.4, 0.95, 1.6], a0: 0.8, a1: 0, add: 1});
    this.sp.emit({kind: S.ICON, cell: CELL.fork, x: pos.x, y: y + 0.5, z: pos.z, vy: 1.5, life: 0.5, w: 0.42, rot: 0, c: [0.5, 1, 1.4], a0: 1, a1: 0, add: 0.5});
  }
  // BUBBLE MACHINE: a bubble bursts over its area: a skin swelling and gone, a ring of wet spray, small bubbles flung out (big: the
  // one that goes up with the machine)
  bubblePop(pos, r, big) {
    const p = {x: pos.x, y: pos.y || 0, z: pos.z}, y = p.y + 0.7;
    this.sp.emit({kind: S.BUBBLE, x: p.x, y, z: p.z, life: big ? 0.2 : 0.13, w0: r * 1.1, w1: r * 2.2, c: [0.75, 0.95, 1.5], a0: 0.9, a1: 0.15, add: 0.6});
    this.sp.emit({kind: S.FLARE, x: p.x, y, z: p.z, life: 0.12, w0: r * 1.5, w1: 0.3, c: [1.3, 1.7, 2], a0: 1, a1: 0.3, add: 1, rot: 0});
    for (let i = 0, n = big ? 12 : 6; i < n; i++) { const a = rnd(0, 6.28), v = rnd(1, 3) * r;
      this.sp.emit({kind: S.BUBBLE, x: p.x, y, z: p.z, vx: Math.cos(a) * v, vy: rnd(0.4, 2), vz: Math.sin(a) * v, g: -0.5, drag: 3.5, life: rnd(0.45, 0.8), w0: 0.14, w1: rnd(0.26, 0.42), c: [0.72, 0.93, 1.3], a0: 1, a1: 0.8, add: 0.5}); }
    for (let i = 0, n = big ? 14 : 8; i < n; i++) { const a = rnd(0, 6.28), v = rnd(2, 4) * r;
      this.sp.emit({kind: S.SPARK, x: p.x, y, z: p.z, vx: Math.cos(a) * v, vy: rnd(0.5, 3), vz: Math.sin(a) * v, g: 10, drag: 2, life: rnd(0.25, 0.4), w: 0.12, asp: 0.5, st: 0.04, c: [0.8, 1.3, 1.7], a0: 1, a1: 0, add: 0.8}); }
    this.ring(p, r * 1.1, '#9fe6ff', big ? 0.45 : 0.32, 0.05, 0.4);
    if (big) { this.flashLight(p, '#9fe6ff', 30, 0.22, 1.2); this.stage.kick(0.3); }
  }
  // BOME falls: the book bursts: a violet flash, its pages flung out every way (the storm they become is syncSpells')
  pageBurst(pos, r) {
    const p = {x: pos.x, y: 0, z: pos.z};
    this.sp.emit({kind: S.FLARE, x: p.x, y: 1.4, z: p.z, life: 0.16, w0: 3, w1: 0.6, c: [1.6, 1.2, 2], a0: 1, a1: 0.3, add: 1, rot: 0});
    this.burst(p, {n: 18, c: C.white, s: 0.5, sp: r * 2.6, up: 4, life: 0.9, g: 5, cell: CELL.page, add: false, y: 1.2, drag: 1.5, s1: 0.4});
    this.ring(p, r * 1.1, '#b48cff', 0.42, 0.05, 0.4); this.flashLight(p, '#a080ff', 24, 0.2, 1.4); this.stage.kick(0.25);
  }
  // PNUT drops an acorn: it falls from him to the ground under the target, tumbling, and pops there (the sim's acorn arrives
  // within a step or two: the fall is drawn a little longer so it's seen; impact() holds the sound till it lands)
  acorn(from, to, team, splash = 1.3) {
    if (!this.acornProto) {
      const g = this.acornProto = new THREE.Group(), nut = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 10).scale(1, 1.25, 1), new THREE.MeshStandardMaterial({color: '#a8692e', roughness: 0.55}));
      const cap = new THREE.Mesh(new THREE.SphereGeometry(0.23, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshStandardMaterial({color: '#5e3b1c', roughness: 0.9})); cap.position.y = 0.1;
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, 0.14, 6), cap.material); stem.position.y = 0.32;
      const glow = new THREE.Mesh(new THREE.SphereGeometry(0.34, 10, 8), new THREE.MeshBasicMaterial({color: '#ffb35a', transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending, depthWrite: false}));
      g.add(nut, cap, stem, glow); g.traverse(n => { if (n.geometry) this.shared.add(n.geometry); if (n.material) this.shared.add(n.material); });
    }
    const m = this.acornProto.clone(), FALL = 0.26, y0 = from.y, sx = from.x, sz = from.z, at = performance.now() + FALL * 1000, d = {x: to.x, z: to.z, team, at};
    m.position.set(sx, y0, sz); m.rotation.set(rnd(0, 6), 0, rnd(0, 6)); m.scale.setScalar(1.6); this.scene.add(m);
    (this.drops ||= []).push(d);
    this.things.push({obj: m, life: FALL, age: 0, tick: (t, k) => {
      const x = sx + (to.x - sx) * k, z = sz + (to.z - sz) * k, y = y0 + (0.2 - y0) * k * k;
      m.position.set(x, y, z); m.rotation.x += 0.35; m.rotation.z += 0.2;
      this.add.emit({x, y: y + 0.1, z, life: 0.32, s0: 0.75, s1: 0.08, c: C.ember, a0: 0.8, cell: CELL.soft});
      this.add.emit({x, y, z, vx: rnd(-0.6, 0.6), vy: rnd(0, 0.8), vz: rnd(-0.6, 0.6), life: 0.35, s0: 0.22, s1: 0.04, c: C.ember, cell: CELL.spark});
      this.norm.emit({x, y, z, vy: 0.3, life: 0.5, s0: 0.35, s1: 0.85, c: C.dust, a0: 0.45, cell: CELL.smoke});
      if (k >= 1) { this.drops.splice(this.drops.indexOf(d), 1); this.acornBoom({x: to.x, y: 0, z: to.z}, splash); }
    }});
  }
  acornBoom(pos, r) {
    const p = {x: pos.x, y: pos.y || 0, z: pos.z};
    this.burst(p, {n: 14, c: C.fire, s: 1.0, sp: r * 2.6, up: 2.2, life: 0.4, g: -1, cell: CELL.flame, y: 0.4, drag: 2.5});
    this.burst(p, {n: 8, c: C.smoke, s: 1.0, sp: r * 1.2, up: 1.4, life: 0.9, g: -0.6, cell: CELL.smoke, add: false, a0: 0.5, y: 0.5});
    this.burst(p, {n: 8, c: C.acorn, s: 0.3, sp: 3.5, up: 5, life: 0.8, g: 14, cell: CELL.chunk, add: false, y: 0.4, floor: 0.05, bounce: 0.3});
    this.ring(p, r * 1.1, '#ffa040', 0.32); this.flashLight(p, '#ff9a40', 26, 0.18, 1); this.scorch(p.x, p.z, r * 0.5); this.stage.kick(0.18);
  }

  // ---------- projectiles mirror the sim's
  projMesh(p) {
    const g = new THREE.Group();
    if (p.proj === 'baguette') {
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.07, 0.55, 4, 8), new THREE.MeshStandardMaterial({color: '#d99a4e', roughness: 0.7})); m.rotation.z = Math.PI / 2; g.add(m); g.userData.spin = 14;
    } else if (p.proj === 'rocket') {
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.45, 8), new THREE.MeshStandardMaterial({color: '#e8e8ee', metalness: 0.6, roughness: 0.3}));
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.18, 8), new THREE.MeshStandardMaterial({color: '#ff3b3b'})); nose.position.y = 0.31;
      const r = new THREE.Group(); r.add(body, nose); r.rotation.x = Math.PI / 2; g.add(r); g.userData.trail = 'fire';
    } else if (p.proj === 'laugh') {
      const m = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.07, 8, 24), new THREE.MeshBasicMaterial({color: '#ffe14a', transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending})); g.add(m); g.userData.pulse = true; g.userData.trail = 'ha';
    } else if (p.proj === 'matcha') {
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), new THREE.MeshStandardMaterial({color: '#7fbf3f', emissive: '#2a5a10', roughness: 0.3})); g.add(m); g.userData.trail = 'matcha';
    } else if (p.proj === 'spam') {
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 8).scale(1.3, 1, 0.5), new THREE.MeshBasicMaterial({color: '#ffffff'}));
      const tail = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.16, 6), new THREE.MeshBasicMaterial({color: '#ffffff'})); tail.position.set(-0.12, -0.18, 0); tail.rotation.z = 0.6;
      const glow = new THREE.Mesh(new THREE.SphereGeometry(0.34, 10, 8), new THREE.MeshBasicMaterial({color: TEAM_COL[p.team], transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, depthWrite: false}));
      g.add(m, tail, glow); g.userData.trail = 'team'; g.userData.team = p.team;
    } else if (p.proj === 'bag') {      // BAG LAUNCHER: a fat money bag, tumbling
      const bag = new THREE.Mesh(new THREE.SphereGeometry(0.34, 12, 10).scale(1, 0.9, 1), new THREE.MeshStandardMaterial({color: '#c9a46a', roughness: 0.85}));
      const knot = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.24, 8), new THREE.MeshStandardMaterial({color: '#a8844e', roughness: 0.85})); knot.position.y = 0.36;
      const tie = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.035, 6, 12), new THREE.MeshStandardMaterial({color: '#ffc84a', metalness: 0.8, roughness: 0.3})); tie.rotation.x = Math.PI / 2; tie.position.y = 0.27;
      const b = new THREE.Group(); b.add(bag, knot, tie); g.add(b); g.userData.spin = 6; g.userData.trail = 'dust';
    } else if (p.proj === 'magic') {    // PEPE: an orb of cyan-violet magic, its halo pulsing, sparkles behind it
      const core = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 8), new THREE.MeshBasicMaterial({color: '#f0fdff'}));
      g.add(core); g.scale.setScalar(1.35); g.userData.trail = 'magic';
    } else if (p.proj === 'zap') {      // HONEYPOT: the arc is drawn when it fires; this is just its spark
      g.add(new THREE.Mesh(new THREE.SphereGeometry(0.16, 8, 6), new THREE.MeshBasicMaterial({color: '#fff3a0', transparent: true, blending: THREE.AdditiveBlending})));
    } else if (p.proj === 'yarn') {     // MICHI: a ball of yarn, tumbling, its loose ends trailing
      const b = new THREE.Group(), wrap = new THREE.MeshStandardMaterial({color: '#c8408a', roughness: 0.9});
      b.add(new THREE.Mesh(new THREE.SphereGeometry(0.21, 10, 8), new THREE.MeshStandardMaterial({color: '#ff74b4', roughness: 0.9})));
      for (const [x, y] of [[0.5, 0], [-0.4, 0.9], [1.2, 0.6]]) { const t = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.024, 5, 18), wrap); t.rotation.set(x, y, 0); b.add(t); }
      g.add(b); g.userData.spin = 11; g.userData.trail = 'yarn';
    } else if (p.proj === 'star') {     // PIPPIN: a gold star turning over, twinkles behind it
      const s = new THREE.Shape(); for (let k = 0; k < 10; k++) { const r = k % 2 ? 0.11 : 0.28, a = k / 10 * Math.PI * 2; s[k ? 'lineTo' : 'moveTo'](Math.sin(a) * r, Math.cos(a) * r); } s.closePath();
      const b = new THREE.Group(); b.add(new THREE.Mesh(new THREE.ExtrudeGeometry(s, {depth: 0.08, bevelEnabled: false}).translate(0, 0, -0.04), new THREE.MeshStandardMaterial({color: '#ffd84a', emissive: '#ffb020', emissiveIntensity: 0.9, roughness: 0.35, metalness: 0.3})));
      g.add(b); g.userData.spin = 9; g.userData.trail = 'star';
    } else if (p.proj === 'holy') {     // APU: a small orb of warm light, its halo breathing
      const halo = new THREE.Mesh(new THREE.SphereGeometry(0.26, 10, 8), new THREE.MeshBasicMaterial({color: '#ffd860', transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false}));
      g.add(halo, new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 8), new THREE.MeshBasicMaterial({color: '#fffbe0'}))); g.userData.pulse = true; g.userData.trail = 'holy';
    } else if (p.proj === 'gas') {      // FARTER: a fat glob of gas (what it leaves where it lands is the sim's zone: stink())
      const b = new THREE.Group(), m = new THREE.MeshStandardMaterial({color: '#9bd12a', emissive: '#4a7a08', emissiveIntensity: 0.7, roughness: 0.8});
      for (const [x, y, z, r] of [[0, 0, 0, 0.2], [0.14, 0.07, -0.05, 0.13], [-0.12, -0.05, 0.08, 0.14]]) { const q = new THREE.Mesh(new THREE.SphereGeometry(r, 8, 6), m); q.position.set(x, y, z); b.add(q); }
      g.add(b); g.userData.spin = 3; g.userData.trail = 'gas';
    } else if (p.proj === 'bubble') {   // BUBBLE MACHINE: a big soap bubble, wobbling on its way
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.36, 14, 10), new THREE.MeshStandardMaterial({color: '#bfe8ff', emissive: '#4aa8e0', emissiveIntensity: 0.3, roughness: 0.08, metalness: 0.2, transparent: true, opacity: 0.45, envMapIntensity: 2, depthWrite: false}));
      const glint = new THREE.Mesh(new THREE.SphereGeometry(0.07, 6, 5), new THREE.MeshBasicMaterial({color: '#ffffff'})); glint.position.set(-0.15, 0.17, 0.2);
      g.add(m, glint); g.userData.wob = true; g.userData.trail = 'bubble';
    } else if (p.proj === 'snipe') {    // SNIPER BOT: a thin hot tracer (three a second: nothing shed behind it)
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.04, 1.2, 3, 6), new THREE.MeshBasicMaterial({color: '#ffe9a8', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false})); m.rotation.x = Math.PI / 2; g.add(m);
    } else if (p.proj === 'page') {     // BOME: a page torn out of the book, tumbling, its edge lit violet
      const c = document.createElement('canvas'); c.width = 64; c.height = 80; const x = c.getContext('2d');
      x.fillStyle = '#f2e3bd'; x.fillRect(0, 0, 64, 80); x.strokeStyle = '#8a60e0'; x.lineWidth = 6; x.strokeRect(0, 0, 64, 80); x.fillStyle = '#6b4aa8'; for (let i = 0; i < 5; i++) x.fillRect(12, 14 + i * 12, i % 2 ? 26 : 40, 5);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
      const b = new THREE.Group(); b.add(new THREE.Mesh(new THREE.PlaneGeometry(0.48, 0.6), new THREE.MeshBasicMaterial({map: t, side: THREE.DoubleSide}))); g.add(b); g.userData.spin = 9; g.userData.trail = 'page';
    } else if (p.proj === 'laser' || p.proj === 'cannon') {
      const col = TEAM_COL[p.team], big = p.proj === 'cannon';
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(big ? 0.14 : 0.07, big ? 0.6 : 0.9, 4, 8), new THREE.MeshBasicMaterial({color: col.clone().lerp(new THREE.Color('#fff'), 0.45), blending: THREE.AdditiveBlending, transparent: true})); m.rotation.x = Math.PI / 2; g.add(m);
      const glow = new THREE.Mesh(new THREE.SphereGeometry(big ? 0.35 : 0.22, 10, 8), new THREE.MeshBasicMaterial({color: col, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false})); g.add(glow);
      g.userData.trail = big ? 'team' : null; g.userData.team = p.team;
    }
    return g;
  }
  syncProjectiles(battle, units, arena, alpha, dt) {
    const seen = new Set();
    for (const p of battle.ents.values()) {
      if (p.kind !== 'proj' || p.proj === 'acorn') continue; seen.add(p.id);   // (PNUT's acorn: dropped on its 'shoot', acorn())
      let v = this.projViews.get(p.id);
      if (!v) {
        const key = p.proj + (p.proj === 'laser' || p.proj === 'cannon' ? p.team : '');
        if (!this.projProto[key]) { const pr = this.projProto[key] = this.projMesh(p); pr.traverse(n => { if (n.geometry) this.shared.add(n.geometry); for (const mm of [].concat(n.material || [])) this.shared.add(mm); }); }
        const m = this.projProto[key].clone(); m.userData = {...this.projProto[key].userData}; this.scene.add(m);
        let y0 = p.y * VIS, ox = 0, oz = 0;
        if (p.proj === 'laser' || p.proj === 'cannon') { const T = arena.towerOf(battle.ents.get(p.from)); if (T) { const w = arena.muzzleWorld(T); y0 = w.y; p.x = p.px = w.x; p.z = p.pz = w.z; this.muzzle(w, p.team); } }
        // (out of a building's muzzle, drawn: the sim's shot leaves its middle; the offset runs out over the flight)
        else if (p.proj === 'bubble' || p.proj === 'snipe') { const w = this.blds?.coilWorld(p.from, V1); if (w) { y0 = w.y; ox = w.x - p.x; oz = w.z - p.z; } if (p.proj === 'snipe') m.lookAt(p.tx, y0, p.tz); }
        else if (p.proj === 'page') { const w = units.bodyOf(p.from, 0.4, V1); if (w) { y0 = w.y; ox = w.x - p.x; oz = w.z - p.z; } }   // (BOME's: out of the book, up where it's drawn)
        v = {m, p, y0, ox, oz, d0: Math.hypot(p.tx - p.x, p.tz - p.z) || 1}; this.projViews.set(p.id, v);
      }
      const x = p.px + (p.x - p.px) * alpha, z = p.pz + (p.z - p.pz) * alpha;
      const left = Math.hypot(p.tx - x, p.tz - z), k = Math.min(1, 1 - left / v.d0);
      const tgt = battle.ents.get(p.target), ty = p.lob ? 0.3 : tgt?.kind === 'tower' ? 2.4 * TOWER_VIS : tgt?.air ? flyH(tgt.air) + visH(tgt.h) * 0.45 : (tgt?.h || 1) * VIS * 0.55;
      // a lob (BAG LAUNCHER) climbs high, the higher the further it goes
      const arc = p.lob ? 2.5 + v.d0 * 0.35 : (ARC[p.proj] || 0) * Math.min(1, v.d0 / 5);
      const y = v.y0 + (ty - v.y0) * k + Math.sin(k * Math.PI) * arc;
      const prev = v.m.position.clone();
      v.m.position.set(x + v.ox * (1 - k), y, z + v.oz * (1 - k));
      if (prev.lengthSq() > 0) { const d = v.m.position.clone().sub(prev); if (d.lengthSq() > 1e-6) v.m.lookAt(v.m.position.clone().add(d)); }
      if (v.m.userData.spin) v.m.children[0].rotation.x += dt * v.m.userData.spin;
      if (v.m.userData.pulse) v.m.children[0].scale.setScalar(1 + Math.sin(performance.now() / 50) * 0.2);
      if (v.m.userData.wob) { const q = Math.sin(performance.now() / 70 + p.id) * 0.07; v.m.children[0].scale.set(1 + q, 1 - q, 1 + q); }
      const tr = v.m.userData.trail;
      if (tr === 'fire') { this.add.emit({x, y, z, vy: 0.3, life: 0.3, s0: 0.55, s1: 0.1, c: C.fire, cell: CELL.flame}); if (Math.random() < 0.5) this.norm.emit({x, y, z, vy: 0.4, life: 0.8, s0: 0.4, s1: 1.0, c: C.smoke, a0: 0.4, cell: CELL.smoke}); }
      else if (tr === 'ha' && Math.random() < 0.3) this.norm.emit({x, y: y + 0.2, z, vy: 1.2, life: 0.6, s0: 0.6, s1: 0.8, c: [1, 0.9, 0.3], cell: CELL.ha, rot: rnd(-0.3, 0.3)});
      else if (tr === 'matcha') this.add.emit({x, y, z, life: 0.25, s0: 0.35, s1: 0.05, c: C.matcha, cell: CELL.soft});
      else if (tr === 'team') this.add.emit({x, y, z, life: 0.2, s0: 0.6, s1: 0.1, c: teamRGB(v.m.userData.team), cell: CELL.soft});
      else if (tr === 'dust' && Math.random() < 0.5) this.norm.emit({x, y, z, vy: 0.2, life: 0.6, s0: 0.35, s1: 0.8, c: C.dust, a0: 0.35, cell: CELL.smoke});
      else if (tr === 'yarn' && Math.random() < 0.5) this.sp.emit({kind: S.SPARK, x, y, z, vx: rnd(-0.4, 0.4), vy: -0.5, vz: rnd(-0.4, 0.4), life: 0.3, w: 0.11, asp: 0.5, st: 0.05, c: [1.4, 0.5, 1], a0: 0.9, a1: 0, add: 0.3});
      else if (tr === 'star') { if (Math.random() < 0.6) this.sp.emit({kind: S.FLARE, x: x + rnd(-0.1, 0.1), y: y + rnd(-0.1, 0.1), z, vy: -0.4, life: 0.3, w0: 0.42, w1: 0, c: Math.random() < 0.5 ? [1.8, 1.4, 0.5] : [1.7, 0.9, 1.5], a0: 1, a1: 0.6, add: 1, rot: 0}); }
      else if (tr === 'holy') { if (Math.random() < 0.6) this.sp.emit({kind: S.GLOW, x, y, z, life: 0.22, w0: 0.42, w1: 0.08, c: [1.5, 1.25, 0.55], a0: 0.8, a1: 0, add: 1}); }
      else if (tr === 'gas') { if (Math.random() < 0.45) this.norm.emit({x, y, z, vy: 0.2, life: 0.45, s0: 0.3, s1: 0.75, c: C.toxic[1], a0: 0.5, cell: CELL.smoke}); }
      else if (tr === 'bubble') { if (Math.random() < 0.15) this.sp.emit({kind: S.BUBBLE, x: x + rnd(-0.2, 0.2), y: y + rnd(-0.2, 0.2), z, vy: 0.4, life: 0.4, w0: 0.08, w1: 0.2, c: [0.72, 0.93, 1.3], a0: 1, a1: 0.7, add: 0.5}); }
      else if (tr === 'page') { if (Math.random() < 0.3) this.sp.emit({kind: S.SPARK, x, y, z, vy: -0.3, life: 0.25, w: 0.1, asp: 0.5, st: 0.04, c: [1, 0.7, 1.7], a0: 0.9, a1: 0, add: 1}); }
      else if (tr === 'magic') {   // an orb of cyan-violet energy (its swirl and halo drawn fresh each frame), sparkles shed behind it
        this.sp.emit({kind: S.WISP, x, y, z, life: dt * 1.5, w: 1.15, c: [0.7, 0.5, 1.6], a0: 1, a1: 1, add: 1, rot: this.time * 4});
        this.sp.emit({kind: S.GLOW, x, y, z, life: dt * 1.5, w: 0.75, c: [0.5, 1.4, 1.6], a0: 1, a1: 1, add: 1});
        this.sp.emit({kind: S.SPARK, x, y, z, vx: rnd(-0.6, 0.6), vy: rnd(-0.3, 0.6), vz: rnd(-0.6, 0.6), life: 0.4, w: 0.12, asp: 0.5, st: 0.05, c: Math.random() < 0.5 ? [0.6, 1.5, 1.7] : [1, 0.6, 1.7], a0: 1, a1: 0, add: 1});
        this.sp.emit({kind: S.GLOW, x, y, z, life: 0.3, w0: 0.6, w1: 0.1, c: [0.65, 0.4, 1.3], a0: 0.6, a1: 0, add: 1}); }
    }
    for (const [id, v] of this.projViews) if (!seen.has(id)) { this.scene.remove(v.m); this.projViews.delete(id); }
  }
  // tgt: what it hit (a flyer: the burst up where it flies). Returns the seconds until it shows (PNUT's acorn still falling)
  impact(e, tgt) {
    const pos = {x: e.x, y: tgt?.air ? flyH(tgt.air) + 0.3 : 0, z: e.z};
    if (e.proj === 'laser') this.burst(pos, {n: 6, c: teamRGB(e.team), s: 0.45, sp: 2.5, up: 1.5, life: 0.25, g: 4, cell: CELL.spark, y: 0.8});
    else if (e.proj === 'cannon') { this.burst(pos, {n: 10, c: teamRGB(e.team), s: 0.6, sp: 3, up: 2, life: 0.3, g: 4, cell: CELL.spark, y: 0.8}); this.burst(pos, {n: 5, c: C.smoke, s: 0.8, sp: 1, up: 1, life: 0.6, cell: CELL.smoke, add: false, a0: 0.4, y: 0.7}); }
    else if (e.proj === 'baguette') this.burst(pos, {n: 8, c: C.bread, s: 0.3, sp: 2.5, up: 3, life: 0.6, g: 10, cell: CELL.chunk, add: false, y: 0.8, floor: 0.04});
    else if (e.proj === 'matcha') this.burst(pos, {n: 10, c: C.matcha, s: 0.4, sp: 2, up: 2, life: 0.5, g: 8, cell: CELL.drop, y: 0.7});
    else if (e.proj === 'rocket') { this.splash(pos, e.splash || 0.8, 'alon'); this.burst(pos, {n: 10, c: C.fire, s: 1.2, sp: 2, up: 2, life: 0.4, cell: CELL.flame, y: 0.6}); this.flashLight(pos, '#ffa040', 30, 0.2, 1); this.stage.kick(0.2); }
    else if (e.proj === 'laugh') this.splash(pos, e.splash || 1.4, 'lmao');
    else if (e.proj === 'spam') this.burst(pos, {n: 7, c: C.white, s: 0.35, sp: 2.4, up: 2, life: 0.35, g: 4, cell: CELL.cross, y: 0.8});
    else if (e.proj === 'bag') { this.splash(pos, e.splash || 1.5, 'bag'); this.burst(pos, {n: 14, c: C.gold, s: 0.45, sp: 4, up: 6, life: 1.1, g: 14, cell: CELL.coin, add: false, y: 0.3, floor: 0.05, bounce: 0.3});
      this.burst(pos, {n: 12, c: C.dust, s: 1.1, sp: 3, up: 1, life: 0.8, cell: CELL.smoke, add: false, a0: 0.55, y: 0.2}); this.stage.kick(0.3); }
    else if (e.proj === 'zap') this.burst(pos, {n: 5, c: C.yellow, s: 0.4, sp: 2, up: 2, life: 0.25, g: 4, cell: CELL.spark, y: 0.8});
    else if (e.proj === 'yarn') { this.burst(pos, {n: 6, c: C.yarn, s: 0.3, sp: 2.2, up: 2.5, life: 0.45, g: 8, cell: CELL.yarn, add: false, y: 0.8, floor: 0.05}); this.burst(pos, {n: 2, c: [1, 0.8, 0.9], s: 0.7, sp: 0.8, up: 0.5, life: 0.35, g: 0, cell: CELL.smoke, add: false, a0: 0.5, y: 0.8}); }
    else if (e.proj === 'star') { this.burst(pos, {n: 7, c: C.gold, s: 0.32, sp: 2.6, up: 2, life: 0.4, g: 4, cell: CELL.star, add: false, y: 0.9}); this.sp.emit({kind: S.FLARE, x: pos.x, y: pos.y + 0.9, z: pos.z, life: 0.12, w0: 1.5, w1: 0.3, c: [1.8, 1.5, 0.7], a0: 1, a1: 0.3, add: 1, rot: 0}); }
    else if (e.proj === 'holy') { this.burst(pos, {n: 5, c: C.holy, s: 0.3, sp: 1.8, up: 1.5, life: 0.35, g: 2, cell: CELL.cross, y: 0.8}); this.sp.emit({kind: S.GLOW, x: pos.x, y: pos.y + 0.8, z: pos.z, life: 0.16, w0: 0.6, w1: 1.3, c: [1.4, 1.2, 0.6], a0: 0.9, a1: 0, add: 1}); }
    else if (e.proj === 'gas') this.burst(pos, {n: 7, c: C.toxic[1], s: 0.8, sp: 1.6, up: 0.8, life: 0.6, g: -0.4, cell: CELL.smoke, add: false, a0: 0.6, y: 0.4, drag: 2.2});
    else if (e.proj === 'bubble') this.bubblePop(pos, e.splash || 1.4);
    else if (e.proj === 'snipe') this.burst(pos, {n: 3, c: C.yellow, s: 0.3, sp: 2, up: 1.5, life: 0.2, g: 4, cell: CELL.spark, y: 0.8});
    else if (e.proj === 'page') this.burst(pos, {n: 5, c: C.white, s: 0.34, sp: 2.2, up: 2, life: 0.45, g: 7, cell: CELL.page, add: false, y: 0.8, floor: 0.05});
    else if (e.proj === 'magic') { const r = e.splash || 1;   // PEPE: a cyan-violet pop over its small area (what it touches is slowed: their tint)
      this.burst(pos, {n: 16, c: C.cyan, s: 0.45, sp: r * 3.2, up: 2, life: 0.4, g: 3, cell: CELL.spark, y: 0.6});
      this.burst(pos, {n: 8, c: C.violet, s: 1.0, sp: r * 1.2, up: 0.6, life: 0.55, g: -0.5, cell: CELL.soft, y: 0.5, drag: 2.5});
      this.burst(pos, {n: 6, c: C.violet, s: 0.35, sp: 0.6, up: 1.4, life: 0.9, g: -1.2, cell: CELL.star, y: 0.4});
      this.sp.emit({kind: S.FLARE, x: pos.x, y: pos.y + 0.6, z: pos.z, life: 0.14, w0: 2, w1: 0.4, c: [1.4, 1.8, 2], a0: 1, a1: 0.4, add: 1, rot: 0});
      this.front(pos, r * 1.1, 12, 0.45, {kind: S.WISP, y: 0.45, w0: 0.5, w1: 1, c: [0.7, 0.45, 1.5], a0: 0.8, a1: 0, add: 1}, 0.2);
      this.dc.emit({kind: D.SWIRL, x: pos.x, z: pos.z, r: r * 1.15, life: 0.6, c: [0.2, 0.25, 0.4], c2: [0.5, 0.8, 1.5], q0: 1, a0: 0.9, a1: 0}); this.flashLight(pos, '#8a7bff', 18, 0.18, 1); }
    else if (e.proj === 'acorn') {   // (its fall, acorn(), ends in the pop; with no fall seen, the pop now)
      const d = this.drops?.find(d => d.team === e.team && Math.hypot(d.x - e.x, d.z - e.z) < 1.6);
      if (d) return Math.max(0, d.at - performance.now()) / 1000;
      this.acornBoom(pos, e.splash || 1.3);
    }
    return 0;
  }

  // ---------- spells
  spell(e) {
    const pos = {x: e.x, y: 0, z: e.z}, r = e.r;
    // FART moves: no ring left where it was cast, just the blast of it (the cloud is syncSpells', on the moving spell)
    if (CARDS[e.card]?.spell?.drift) {
      this.burst(pos, {n: 26, c: C.toxic[1], s: 1.6, s1: 3.0, sp: r * 1.4, up: 0.8, life: 1.1, g: -0.4, cell: CELL.smoke, add: false, a0: 0.6, y: 0.4, drag: 2.2});
      this.ring(pos, r, '#b0ff4a', 0.5); this.flashDisc(pos, r, '#8cff3a', 0.35, 0.25); this.flashLight(pos, '#8cff3a', 30, 0.3, 1.5); this.stage.kick(0.15);
      return;
    }
    if (castSpell(this, e)) return;   // (spells.js: each as its card shows it)
    if (e.card === 'rug') this.rug(e);
  }
  // MARGIN CALL: a red bolt on each of its targets
  bolt(x, z) { bolt(this, x, z, '#ff3048', 0.13, 11); this.flashLight({x, z}, '#ff4040', 30, 0.3, 2); this.stage.kick(0.35);
    this.dc.emit({kind: D.CRACK, x, z, r: 1.4, life: 3, c: [0.06, 0.04, 0.04], c2: [1.2, 0.15, 0.2], q0: 1, q1: 0, a0: 0.85, a1: 0});
    this.front({x, z}, 1.6, 12, 0.45, {kind: S.SMOKE, y: 0.15, w0: 0.4, w1: 1, ease: 1, c: [0.5, 0.45, 0.45], a0: 0.6, a1: 0, add: 0}, 0.2); }
  // the spells that move or last, each drawn on its sim entity (online too: the snapshots carry them, so nothing here waits on
  // an event): BAN HAMMER rolling, FART's cloud drifting, burning ground (THIS IS FINE's 'blaze'), NYAN CAT's 'rainbow', MICHI's
  // 'yarntrap', FARTER's 'stink', BOME's 'paperstorm' (the zones are not cards: CARDS has no entry for them)
  syncSpells(battle, alpha, dt = 1 / 60) {
    const seen = new Set(), f = this.frame = (this.frame || 0) + 1;
    for (const sp of battle.ents.values()) {
      if (sp.kind !== 'spell') continue;
      if (sp.card === 'blaze') { this.blaze(sp, f, dt); continue; }
      if (sp.card === 'rainbow') { this.rainbow(sp, f, dt, battle); continue; }
      if (sp.card === 'yarntrap') { this.yarnTrap(sp, f, dt); continue; }
      if (sp.card === 'stink') { this.stink(sp, f, dt); continue; }
      if (sp.card === 'paperstorm') { this.paperstorm(sp, f, dt); continue; }
      if (CARDS[sp.card]?.spell?.drift) { this.fartCloud(sp, f, dt, alpha); continue; }
      if (sp.card !== 'banhammer' || !sp.fired) continue; seen.add(sp.id);
      let h = (this.hammers ||= new Map()).get(sp.id);
      if (!h) { h = new THREE.Group(); const m = prop('hammer'); m.rotation.y = Math.PI / 2; h.add(m); h.scale.setScalar(1.4); h.userData = {keep: true, lx: sp.x, lz: sp.z}; this.scene.add(h); this.hammers.set(sp.id, h); }
      h.position.set(sp.x, 0.74, sp.z); h.rotation.x += (sp.dir || -1) * -0.35;
      // where it rolls: gold sparks scraped off behind it, dust, the ground scored
      const dz = sp.dir || -1;
      for (let i = 0; i < 2; i++) this.sp.emit({kind: S.SPARK, x: sp.x + rnd(-1.4, 1.4), y: 0.1, z: sp.z - dz * 0.4, vx: rnd(-1, 1), vy: rnd(1, 3), vz: -dz * rnd(2, 5), g: 12, drag: 1, life: rnd(0.25, 0.45), w: 0.14, asp: 0.35, st: 0.05, c: [1.8, 1.3, 0.4], a0: 1, a1: 0, add: 1, floor: 0.05, bounce: 0.3});
      if (Math.random() < 0.6) this.sp.emit({kind: S.SMOKE, x: sp.x + rnd(-1.6, 1.6), y: 0.2, z: sp.z - dz * 0.6, vy: 0.5, vz: -dz * 0.6, life: 0.8, w0: 0.6, w1: 1.4, ease: 1, c: [0.62, 0.58, 0.54], a0: 0.55, a1: 0, add: 0});
      if (Math.random() < 0.3) this.sp.emit({kind: S.ICON, cell: CELL.ucoin, x: sp.x + rnd(-1.2, 1.2), y: 0.3, z: sp.z - dz * 0.3, vx: rnd(-1.5, 1.5), vy: rnd(4, 6.5), vz: -dz * rnd(1, 3), g: 14, vr: rnd(-8, 8),
        life: 0.9, w: 0.34, c: [1, 1, 1], a0: 1, a1: 1, fin: 0.15, add: 0, floor: 0.08, bounce: 0.35});   // coins knocked loose
      if (Math.random() < 0.35) this.sp.emit({kind: S.ICON, cell: CELL.clod, x: sp.x + rnd(-1.3, 1.3), y: 0.2, z: sp.z - dz * 0.2, vx: rnd(-1.5, 1.5), vy: rnd(3, 5), vz: -dz * rnd(1, 3), g: 14, vr: rnd(-6, 6),
        life: 0.7, w: rnd(0.18, 0.3), c: [0.34, 0.3, 0.27], a0: 1, a1: 1, fin: 0.2, add: 0, floor: 0.05, bounce: 0.25});
      if (Math.hypot(sp.x - h.userData.lx, sp.z - h.userData.lz) > 0.7) { h.userData.lx = sp.x; h.userData.lz = sp.z;
        this.dc.emit({kind: D.CRACK, x: sp.x, z: sp.z, r: 1.3, life: 2.5, c: [0.08, 0.07, 0.06], c2: [0, 0, 0], q0: 0, a0: 0.6, a1: 0}); }
    }
    if (this.hammers) for (const [id, h] of this.hammers) if (!seen.has(id)) { this.scene.remove(h); this.hammers.delete(id); this.burst({x: h.position.x, y: 0, z: h.position.z}, {n: 12, c: [1, 1, 1], s: 0.38, sp: 3, up: 5, life: 0.9, g: 12, cell: CELL.ucoin, add: false, y: 0.5, floor: 0.08, bounce: 0.35});
      for (let i = 0; i < 6; i++) this.sp.emit({kind: S.SMOKE, x: h.position.x + rnd(-1.4, 1.4), y: 0.25, z: h.position.z + rnd(-0.8, 0.8), vx: rnd(-1, 1), vy: rnd(0.4, 1), vz: rnd(-0.6, 0.6), drag: 2,
        life: rnd(0.7, 1), w0: 0.6, w1: rnd(1.3, 1.8), ease: 1, c: [0.62, 0.58, 0.54], a0: 0.6, a1: 0, add: 0}); }
    for (const M of [this.clouds, this.blazes, this.traps, this.stinks, this.storms]) if (M) for (const [id, o] of M) if (o.f !== f) { if (o.end) o.end(); else { this.scene.remove(o.g); this.dispose(o.g); } M.delete(id); }
    if (this.rbChains) this.rainbowEnds(battle, alpha, f, dt);
  }
  // FART: a toxic cloud drifting toward the enemy: thick yellow-green puffs rolling over each other, strands of gas curling
  // through them, a green stain dragged under it, bubbles popping, flies buzzing round it
  fartCloud(sp, f, dt, alpha) {
    const M = this.clouds ||= new Map(); let c = M.get(sp.id);
    if (!c) {
      c = {age: 0, r: sp.r, vz: (sp.team === 0 ? -1 : 1) * CARDS[sp.card].spell.drift, stain: this.dc.emit({kind: D.STAIN, x: sp.x, z: sp.z, r: sp.r * 1.1, hold: true, c: [0.2, 0.34, 0.05], c2: [0.24, 0.45, 0.06], a: 0})};   // (its edge barely lit: no ring round it)
      c.end = () => this.release(c.stain, 0.6); M.set(sp.id, c);
    }
    c.f = f; c.age += dt;
    const x = sp.px + (sp.x - sp.px) * alpha, z = sp.pz + (sp.z - sp.pz) * alpha, r = c.r, k = Math.min(1, c.age * 3) * Math.min(1, Math.max(0, sp.live ?? 1) / 0.6);
    c.stain.x = x; c.stain.z = z; c.stain.a = 0.85 * k;
    if (Math.random() < dt * 34 * k) { const a = rnd(0, 6.28), d = Math.sqrt(Math.random()) * r * 0.8;
      this.sp.emit({kind: S.SMOKE, x: x + Math.cos(a) * d, y: rnd(0.3, 1.4), z: z + Math.sin(a) * d, vx: rnd(-0.2, 0.2), vy: rnd(0.05, 0.3), vz: c.vz + rnd(-0.2, 0.2), curl: rnd(-0.8, 0.8), cx: x, cz: z,
        life: rnd(1.4, 1.9), w0: rnd(1.2, 1.7), w1: rnd(2.2, 3), ease: 1, c: [[0.55, 0.78, 0.14], [0.68, 0.86, 0.2], [0.42, 0.62, 0.1], [0.78, 0.84, 0.25]][Math.random() * 4 | 0], a0: 0.58, a1: 0, fin: 0.25, add: 0}); }
    if (Math.random() < dt * 16 * k) { const a = rnd(0, 6.28), d = rnd(0.2, 0.75) * r;   // the swirls of it curling round
      this.sp.emit({kind: S.WISP, x: x + Math.cos(a) * d, y: rnd(0.4, 1.8), z: z + Math.sin(a) * d, vz: c.vz, curl: rnd(1.5, 2.5) * (Math.random() < 0.5 ? -1 : 1), cx: x, cz: z, life: 1.3, w0: 0.8, w1: 1.8, c: [0.6, 1.25, 0.18], a0: 0.7, a1: 0, add: 0.6}); }
    if (Math.random() < dt * 2.5 * k) { const a = rnd(0, 6.28), d = rnd(0.1, 0.6) * r;   // a red candle tumbling in it
      this.sp.emit({kind: S.ICON, cell: 17, x: x + Math.cos(a) * d, y: rnd(1, 1.8), z: z + Math.sin(a) * d, vx: rnd(-0.4, 0.4), vy: rnd(-0.2, 0.3), vz: c.vz, vr: rnd(-3, 3), life: 1.2, w: 0.3, asp: 1.3, c: [1, 0.25, 0.25], a0: 1, a1: 0, add: 0.2}); }
    if (Math.random() < dt * 12 * k) { const a = rnd(0, 6.28), d = Math.sqrt(Math.random()) * r * 0.75;
      this.sp.emit({kind: S.BUBBLE, x: x + Math.cos(a) * d, y: 0.12, z: z + Math.sin(a) * d, vy: rnd(0.6, 1.2), vz: c.vz, life: rnd(0.5, 0.8), w0: 0.1, w1: rnd(0.3, 0.45), c: [0.7, 1.2, 0.3], a0: 0.9, a1: 0.9, add: 0.5}); }
    for (let i = 0; i < 5; i++) { const a = c.age * (2.6 + i * 0.5) * (i % 2 ? 1 : -1) + i * 1.3, rr = r * (0.55 + 0.25 * Math.sin(c.age * 2 + i));
      this.sp.emit({kind: S.ICON, cell: CELL.fly, x: x + Math.cos(a) * rr, y: 1.3 + 0.35 * Math.sin(c.age * 7 + i * 2), z: z + Math.sin(a) * rr, life: dt * 1.5, w: 0.24 * k, rot: -a, c: [1, 1, 1], a0: 1, a1: 1, add: 0}); }
  }
  // THIS IS FINE: the ground under what he hits burns: a charred patch, its cracks glowing, the ground round it lit orange,
  // tongues of flame licking up all over it (the tallest in the middle), embers spiralling up, dark smoke rolling off the top.
  // Fed again while he keeps hitting near it (the sim refreshes its live); when it goes out the char cools and fades.
  blaze(sp, f, dt) {
    const M = this.blazes ||= new Map(); let b = M.get(sp.id);
    if (!b) {
      const r = sp.r;
      b = {age: 0, r, char: this.dc.emit({kind: D.SCORCH, x: sp.x, z: sp.z, r: r * 1.3, hold: true, c: [0.04, 0.03, 0.025], c2: [1, 0.33, 0.06], q: 1, a: 0}),
        light: this.dc.emit({kind: D.GLOW, x: sp.x, z: sp.z, r: r * 1.75, hold: true, add: 1, c: [1, 0.34, 0.07], a: 0})};
      b.end = () => { this.release(b.char, 4); this.release(b.light, 0.4); };
      M.set(sp.id, b);
      for (let i = 0; i < 12; i++) { const a = rnd(0, 6.28), v = rnd(1.5, 3.2);   // it catches: a whoosh of flame out over the patch
        this.sp.emit({kind: S.FLAME, x: sp.x, y: 0.35, z: sp.z, vx: Math.cos(a) * v, vy: rnd(0.4, 1), vz: Math.sin(a) * v, drag: 4, life: rnd(0.35, 0.5), w0: rnd(0.6, 0.9), w1: 0.3, asp: 1.6, c: C.fire, a0: 1, a1: 0.3, rot: rnd(-0.2, 0.2)}); }
    }
    b.f = f; b.age += dt;
    const r = b.r, x = sp.x, z = sp.z, live = Math.min(1, Math.max(0, sp.live ?? 1) / 0.6), k = Math.min(1, b.age * 4) * live, fl = 0.85 + Math.sin(b.age * 21) * 0.07 + Math.sin(b.age * 34) * 0.06;
    b.char.a = Math.min(1, b.age * 3) * 0.9; b.char.q = 0.35 + 0.65 * k; b.light.a = 0.85 * k * fl;
    if (Math.random() < dt * 46 * k) { const a = rnd(0, 6.28), d = Math.sqrt(Math.random()) * r * 0.85, w = rnd(0.75, 1.2) * (1.3 - d / r * 0.55), asp = rnd(1.4, 1.8);
      this.sp.emit({kind: S.FLAME, x: x + Math.cos(a) * d, y: w * asp * 0.42, z: z + Math.sin(a) * d, vx: rnd(-0.1, 0.1), vy: rnd(0.3, 0.8), life: rnd(0.45, 0.75), w0: w, w1: w * 0.75, asp, c: C.fire, a0: 1, a1: 0.25, fin: 0.06, add: 0.5, rot: rnd(-0.1, 0.1)}); }
    if (Math.random() < dt * 12 * k) this.sp.emit({kind: S.SPARK, x: x + rnd(-r, r) * 0.6, y: 0.4, z: z + rnd(-r, r) * 0.6, vx: rnd(-0.5, 0.5), vy: rnd(2, 3.5), vz: rnd(-0.5, 0.5), g: -0.3, drag: 0.8, curl: rnd(-3, 3), cx: x, cz: z,
      life: rnd(0.8, 1.3), w: 0.1, asp: 0.45, st: 0.05, c: [1.7, 0.62, 0.14], a0: 1, a1: 0});
    if (Math.random() < dt * 5 * k) this.sp.emit({kind: S.SMOKE, x: x + rnd(-r, r) * 0.4, y: 1.3, z: z + rnd(-r, r) * 0.4, vx: rnd(-0.2, 0.2) + 0.15, vy: rnd(0.7, 1.1), life: rnd(1.6, 2.2), w0: 0.7, w1: 2, ease: 1,
      c: [0.13, 0.11, 0.11], a0: 0.5, a1: 0.15, fin: 0.3, add: 0});
  }
  // MICHI's trap: a tangle of yarn lying on the ground with a ball at its heart, her team's ring round it (one geometry and a pool of
  // them: never more than a few lie about). It unrolls as it arms and whips away when it's sprung or runs out; what it catches wears
  // its own (units.js)
  yarnTrap(sp, f, dt) {
    const M = this.traps ||= new Map(); let t = M.get(sp.id);
    if (!t) {
      const g = (this.trapPool ||= []).pop() || this.trapMesh();
      g.children[2].material = this.trapRings[sp.team]; g.position.set(sp.x, 0.03, sp.z); g.scale.setScalar(0.001); g.visible = true;
      t = {g, age: 0}; t.end = () => { const s = g.scale.x; this.things.push({life: 0.16, age: 0, tick: (q, k) => { g.scale.setScalar(s * (1 - k) + 0.001); if (k >= 1) { g.visible = false; this.trapPool.push(g); } }}); };
      M.set(sp.id, t);
    }
    t.f = f; t.age += dt;
    t.g.scale.setScalar(sp.r * 0.95 * (1 - Math.max(0, 1 - t.age / 0.3) ** 3) * Math.min(1, Math.max(0.02, sp.live ?? 1) / 0.4) + 0.001);
  }
  trapMesh() {
    if (!this.trapGeo) {
      const pts = []; for (let i = 0; i < 26; i++) { const a = i * 2.39996, d = 0.28 + (i * 7 % 11) / 11 * 0.72; pts.push(new THREE.Vector3(Math.cos(a) * d, 0.05 + (i % 3) * 0.04, Math.sin(a) * d)); }
      this.trapGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 110, 0.052, 5, true); this.trapBall = new THREE.SphereGeometry(0.26, 10, 8);
      this.trapMat = new THREE.MeshStandardMaterial({color: '#ff74b4', roughness: 0.9}); this.trapRings = TEAM_COL.map(c => new THREE.MeshBasicMaterial({color: c, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false}));
      for (const o of [this.trapGeo, this.trapBall, this.trapMat, ...this.trapRings]) this.shared.add(o);
    }
    const g = new THREE.Group(), b = new THREE.Mesh(this.trapBall, this.trapMat), ring = new THREE.Mesh(this.ringGeo, this.trapRings[0]); b.position.y = 0.2; ring.position.y = 0.01; ring.renderOrder = 1;
    g.add(new THREE.Mesh(this.trapGeo, this.trapMat), b, ring); this.scene.add(g); return g;
  }
  // FARTER: his gas hanging where his target stood: a small sour cloud over a green stain, bubbles, a fly or two circling. Far thinner
  // than FART's: one of these per FARTER can lie about at once, fed while he keeps at it
  stink(sp, f, dt) {
    const M = this.stinks ||= new Map(); let c = M.get(sp.id);
    if (!c) { c = {age: 0, stain: this.dc.emit({kind: D.STAIN, x: sp.x, z: sp.z, r: sp.r * 1.1, hold: true, c: [0.2, 0.34, 0.05], c2: [0.24, 0.45, 0.06], a: 0})}; c.end = () => this.release(c.stain, 0.6); M.set(sp.id, c); }
    c.f = f; c.age += dt;
    const r = sp.r, x = sp.x, z = sp.z, k = Math.min(1, c.age * 3) * Math.min(1, Math.max(0, sp.live ?? 1) / 0.6);
    c.stain.a = 0.8 * k;
    if (Math.random() < dt * 11 * k) { const a = rnd(0, 6.28), d = Math.sqrt(Math.random()) * r * 0.75;
      this.sp.emit({kind: S.SMOKE, x: x + Math.cos(a) * d, y: rnd(0.3, 1.1), z: z + Math.sin(a) * d, vx: rnd(-0.15, 0.15), vy: rnd(0.05, 0.3), vz: rnd(-0.15, 0.15), curl: rnd(-0.8, 0.8), cx: x, cz: z,
        life: rnd(1.2, 1.7), w0: rnd(0.9, 1.2), w1: rnd(1.6, 2.1), ease: 1, c: C.toxic[Math.random() * 3 | 0], a0: 0.55, a1: 0, fin: 0.25, add: 0}); }
    if (Math.random() < dt * 4 * k) { const a = rnd(0, 6.28), d = rnd(0.2, 0.7) * r;
      this.sp.emit({kind: S.WISP, x: x + Math.cos(a) * d, y: rnd(0.4, 1.3), z: z + Math.sin(a) * d, curl: rnd(1.5, 2.5) * (Math.random() < 0.5 ? -1 : 1), cx: x, cz: z, life: 1.1, w0: 0.8, w1: 1.5, c: [0.6, 1.25, 0.18], a0: 0.38, a1: 0, add: 0.6}); }
    if (Math.random() < dt * 5 * k) { const a = rnd(0, 6.28), d = Math.sqrt(Math.random()) * r * 0.7;
      this.sp.emit({kind: S.BUBBLE, x: x + Math.cos(a) * d, y: 0.12, z: z + Math.sin(a) * d, vy: rnd(0.5, 1), life: rnd(0.5, 0.8), w0: 0.1, w1: rnd(0.25, 0.38), c: [0.7, 1.2, 0.3], a0: 0.9, a1: 0.9, add: 0.5}); }
    if (Math.random() < dt * 1.5 * k) { const a = rnd(0, 6.28), d = rnd(0.5, 0.8) * r;   // (its own circle, no drawing it fresh each frame)
      this.sp.emit({kind: S.ICON, cell: CELL.fly, x: x + Math.cos(a) * d, y: rnd(0.9, 1.5), z: z + Math.sin(a) * d, curl: rnd(2.5, 4) * (Math.random() < 0.5 ? -1 : 1), cx: x, cz: z, life: 1.3, w: 0.24, rot: 0, c: [1, 1, 1], a0: 1, a1: 1, fin: 0.1, add: 0}); }
  }
  // BOME's paper storm: pages whirling round and up over a swirl on the ground, a pale wind through them. The pages are small icons: a
  // storm of them costs less than a few puffs of smoke
  paperstorm(sp, f, dt) {
    const M = this.storms ||= new Map(); let c = M.get(sp.id);
    if (!c) { c = {age: 0, swirl: this.dc.emit({kind: D.SWIRL, x: sp.x, z: sp.z, r: sp.r * 1.05, hold: true, c: [0.25, 0.2, 0.35], c2: [0.6, 0.5, 1.1], q: 1, a: 0})}; c.end = () => this.release(c.swirl, 0.4); M.set(sp.id, c); }
    c.f = f; c.age += dt;
    const r = sp.r, x = sp.x, z = sp.z, k = Math.min(1, c.age * 3) * Math.min(1, Math.max(0, sp.live ?? 1) / 0.5);
    c.swirl.a = 0.85 * k;
    if (Math.random() < dt * 26 * k) { const a = rnd(0, 6.28), d = rnd(0.25, 1) * r;
      this.sp.emit({kind: S.ICON, cell: CELL.page, x: x + Math.cos(a) * d, y: rnd(0.2, 1.3), z: z + Math.sin(a) * d, vy: rnd(0.4, 1.2), curl: rnd(2.2, 3.4), cx: x, cz: z, vr: rnd(-6, 6), life: rnd(0.9, 1.4), w: rnd(0.26, 0.4), asp: 1.25, c: [1, 1, 1], a0: 1, a1: 0, fin: 0.1, add: 0}); }
    if (Math.random() < dt * 5 * k) { const a = rnd(0, 6.28), d = rnd(0.4, 0.9) * r;
      this.sp.emit({kind: S.WISP, x: x + Math.cos(a) * d, y: rnd(0.4, 1.2), z: z + Math.sin(a) * d, curl: 3, cx: x, cz: z, life: 0.8, w0: 0.7, w1: 1.3, c: [0.75, 0.65, 1.2], a0: 0.35, a1: 0, add: 0.8}); }
  }
  // NYAN CAT's rainbow: one ribbon per cat, from her hips back through the pieces of her trail (sim zones dropped under her
  // every so often, each burning the ground under it while it lasts), smoothed into a curve: six bands stepping in a wave
  // like the meme's, glints running down it. As the old pieces run out it narrows and crumbles from the end. Glitter falls
  // from it onto the ground it burns.
  rainbow(sp, f, dt, battle) {
    const M = this.rbs ||= new Map(), CH = this.rbChains ||= new Map(); let R = M.get(sp.id);
    if (!R) {
      // whose it is: the sim says (src); online, the NYAN CAT of that team nearest to where it fell
      let cat = sp.src != null ? battle.ents.get(sp.src) : null;
      if (!cat) { let bd = 2.5; for (const e of battle.ents.values()) if (e.kind === 'unit' && e.team === sp.team && CARDS[e.card]?.unit?.trail) { const d = Math.hypot(e.x - sp.x, e.z - sp.z); if (d < bd) { bd = d; cat = e; } } }
      const key = cat?.id ?? -1 - sp.team, h = cat && this.units?.boneOf(cat.id, /hips/i, V1);
      R = {id: sp.id, x: h ? h.x : sp.x, y: h ? h.y : flyH(cat?.air || 2) + 0.5, z: h ? h.z : sp.z, gx: sp.x, gz: sp.z, r: sp.r, age: 0, k: 0};
      M.set(sp.id, R);
      let ch = CH.get(key); if (!ch) CH.set(key, ch = {list: [], rib: new Ribbon(this.scene, ribbonMaterial('rainbow', this.noise), 160)});
      ch.list.push(R);
    }
    R.f = f; R.age += dt; R.k = Math.min(1, R.age * 6) * Math.min(1, Math.max(0, sp.live ?? 1) / 0.9);
    if (Math.random() < dt * 7 * R.k) { const c = RAINBOW[Math.random() * 6 | 0];   // glitter, falling to the ground it burns
      this.sp.emit({kind: S.FLARE, x: R.x + rnd(-0.25, 0.25), y: R.y - 0.15, z: R.z + rnd(-0.25, 0.25), vx: rnd(-0.2, 0.2), vy: -rnd(1.6, 2.6), vz: rnd(-0.2, 0.2), life: rnd(0.7, 1.1), w: rnd(0.14, 0.24), c: mul(c, 1.6), a0: 1, a1: 0.2, add: 1, floor: 0.06}); }
  }
  // ...each cat's ribbon drawn through its pieces (the pieces gone dropped)
  rainbowEnds(battle, alpha, f, dt) {
    for (const [id, R] of this.rbs) if (R.f !== f) this.rbs.delete(id);
    const cam = this.stage.camera.position, W = 0.78;
    for (const [key, ch] of this.rbChains) {
      ch.list = ch.list.filter(R => this.rbs.has(R.id));
      const cat = battle.ents.get(key), h = cat && !cat.dead ? this.units?.boneOf(key, /hips/i, V2) : null;
      if (!ch.list.length && !h) { ch.rib.dispose(); this.rbChains.delete(key); continue; }
      // the control points: her hips while she flies, then the pieces newest first (bunched ones merged)
      const ctl = h ? [{x: h.x, y: h.y, z: h.z, k: 1}] : [];
      for (let i = ch.list.length - 1; i >= 0; i--) { const R = ch.list[i], q = ctl[ctl.length - 1];
        if (q && Math.hypot(R.x - q.x, R.z - q.z) < 0.2) { q.k = Math.max(q.k, R.k); continue; } ctl.push(R); }
      if (ctl.length < 2) { ch.rib.set([], cam); continue; }
      // through them as a Catmull-Rom curve, a few points a segment; narrowing and fading with the pieces
      const pts = []; let u = 0, px = ctl[0].x, py = ctl[0].y, pz = ctl[0].z;
      for (let i = 0; i < ctl.length - 1; i++) {
        const p0 = ctl[Math.max(0, i - 1)], p1 = ctl[i], p2 = ctl[i + 1], p3 = ctl[Math.min(ctl.length - 1, i + 2)], n = 5;
        for (let j = i ? 1 : 0; j <= n; j++) {
          const t = j / n, t2 = t * t, t3 = t2 * t, cr = (a, b, c, d) => 0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (3 * b - a - 3 * c + d) * t3);
          const x = cr(p0.x, p1.x, p2.x, p3.x), y = cr(p0.y, p1.y, p2.y, p3.y), z = cr(p0.z, p1.z, p2.z, p3.z), k = p1.k + (p2.k - p1.k) * t;
          u += Math.hypot(x - px, y - py, z - pz); px = x; py = y; pz = z;
          pts.push({x, y, z, u, w: W * (0.35 + 0.65 * k), a: k});
        }
      }
      ch.rib.set(pts, cam);
      if (h && Math.random() < dt * 10) { const p = pts[Math.random() * Math.min(pts.length, 12) | 0];   // twinkles about her tail
        this.sp.emit({kind: S.FLARE, x: p.x + rnd(-0.4, 0.4), y: p.y + rnd(-0.3, 0.4), z: p.z + rnd(-0.4, 0.4), life: 0.45, w0: rnd(0.3, 0.45), w1: 0, c: [1.6, 1.5, 1.3], a0: 1, a1: 1, add: 1}); }
    }
  }
  // WOJAK's gloom: a small violet arrow (pointing down) by what it weakens, troops and buildings, while it lasts (one pool of sprites)
  syncWeak(battle, units) {
    const P = this.weakPool ||= [], t = performance.now() / 1000; let n = 0;
    if (battle) for (const e of battle.ents.values()) {
      if (!(e.weakT > 0) || e.dead || (e.kind !== 'unit' && e.kind !== 'bld') || e.state === 'deploy') continue;
      const s = P[n] || (P[n] = this.weakSprite());
      if (e.kind === 'unit') { if (!units.headOf(e.id, s.position)) continue; s.position.x += 0.85; s.position.y -= 0.2; }
      else s.position.set(e.x + 1.15, e.h * BLD_VIS + 0.6, e.z);
      s.position.y += Math.sin(t * 5 + e.id) * 0.07; s.visible = true; n++;
    }
    for (let i = n; i < P.length; i++) P[i].visible = false;
  }
  weakSprite() {
    if (!this.weakMat) {
      const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d');
      g.lineJoin = 'round'; g.beginPath(); g.moveTo(21, 6); g.lineTo(43, 6); g.lineTo(43, 29); g.lineTo(56, 29); g.lineTo(32, 58); g.lineTo(8, 29); g.lineTo(21, 29); g.closePath();
      g.lineWidth = 8; g.strokeStyle = '#1b0f2e'; g.stroke(); g.fillStyle = '#b48cff'; g.fill();
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
      this.weakMat = new THREE.SpriteMaterial({map: t, transparent: true, depthTest: false, depthWrite: false});
    }
    const s = new THREE.Sprite(this.weakMat); s.scale.setScalar(0.62); s.renderOrder = 7; this.scene.add(s); return s;
  }
  // a battle left (or a new one): what followed its entities goes with it
  endBattle() {
    for (const M of [this.hammers, this.clouds, this.blazes, this.traps, this.stinks, this.storms]) if (M) { for (const o of M.values()) { const g = o.g || (o.isObject3D ? o : null); if (g) { this.scene.remove(g); this.dispose(g); } } M.clear(); }
    this.sp.clear(); this.dc.clear();
    this.rbs?.clear(); if (this.rbChains) { for (const ch of this.rbChains.values()) ch.rib.dispose(); this.rbChains.clear(); }
    for (const s of this.weakPool || []) s.visible = false;
    this.drops = [];
  }
  lightning(x, z, col = '#cfe0ff', w = 0.06) { bolt(this, x, z, col, w); }
  scorch(x, z, r) { this.dc.emit({kind: D.SCORCH, x, z, r: r * 1.3, life: 6, c: [0.045, 0.035, 0.03], c2: [1, 0.36, 0.07], q0: 1, q1: 0, a0: 0.85, a1: 0, fin: 0.08}); }
  rugTex() {
    if (this._rug) return this._rug;
    const c = document.createElement('canvas'); c.width = 256; c.height = 192; const g = c.getContext('2d');
    g.fillStyle = '#7a1424'; g.fillRect(0, 0, 256, 192); g.strokeStyle = '#e8c27a'; g.lineWidth = 8; g.strokeRect(10, 10, 236, 172); g.strokeStyle = '#1c2a5a'; g.lineWidth = 6; g.strokeRect(22, 22, 212, 148);
    g.fillStyle = '#e8c27a'; for (let i = 0; i < 6; i++) for (let j = 0; j < 4; j++) { g.save(); g.translate(48 + i * 32, 52 + j * 30); g.rotate(Math.PI / 4); g.fillRect(-7, -7, 14, 14); g.restore(); }
    g.fillStyle = '#1c2a5a'; g.beginPath(); g.ellipse(128, 96, 40, 28, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = '#e8c27a'; g.font = 'bold 34px serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('$', 128, 98);
    for (let x = 4; x < 256; x += 8) { g.fillStyle = '#efe0b0'; g.fillRect(x, 0, 3, 6); g.fillRect(x, 186, 3, 6); }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return (this._rug = t);
  }
  // RUG PULL: a rich carpet lies under them, coins raining onto it; then it's yanked: it rips up and away, waving like a flying
  // carpet, purple lightning cracking where it was, the coins flung everywhere
  rug(e) {
    const r = e.r, W = r * 2.1, Hh = r * 1.55, g = new THREE.PlaneGeometry(W, Hh, 24, 10); g.rotateX(-Math.PI / 2);
    const P = g.attributes.position, base = P.array.slice(), side = e.x < 9 ? -1 : 1, delay = e.delay || 1;
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({map: this.rugTex(), roughness: 0.85, side: THREE.DoubleSide}));
    m.position.set(e.x, 0.06, e.z); m.receiveShadow = m.castShadow = true; this.scene.add(m);
    for (let k = 0; k < 16; k++) this.sp.emit({kind: S.ICON, cell: CELL.ucoin, x: e.x + rnd(-r, r) * 0.6, y: rnd(2, 5), z: e.z + rnd(-r, r) * 0.45, vy: -2, g: 14, life: delay + 0.6, w: 0.32, c: [1, 1, 1], a0: 1, a1: 1, add: 0, floor: 0.14, bounce: 0.25, vr: rnd(-3, 3)});
    this.things.push({obj: m, life: delay + 0.8, age: 0, tick: (t, k, age) => {
      const q = age < delay ? 0 : Math.min(1, (age - delay) / 0.8);
      for (let i = 0; i < P.count; i++) { const bx = base[i * 3], bz = base[i * 3 + 2], u = bx / W + 0.5;
        P.setY(i, age < delay ? Math.sin(bx * 2 + age * 5) * 0.025 : Math.sin(u * 7 - age * 16) * 0.38 * Math.min(1, q * 3) * (0.3 + u * 0.7) + Math.sin(bz * 1.5 + age * 9) * 0.08 * q); }
      P.needsUpdate = true; g.computeVertexNormals();
      if (age < delay) return;
      if (!m.userData.yanked) { m.userData.yanked = true;
        this.burst({x: e.x, y: 0, z: e.z}, {n: 28, c: [1, 1, 1], s: 0.5, sp: 6, up: 8, life: 1.4, g: 16, cell: CELL.ucoin, add: false, y: 0.3, floor: 0.06, bounce: 0.35});
        this.front({x: e.x, z: e.z}, r * 1.2, 22, 0.55, {kind: S.SMOKE, y: 0.2, w0: 0.6, w1: 1.5, ease: 1, c: [0.62, 0.58, 0.54], a0: 0.7, a1: 0, add: 0}, 0.2);
        for (let i = 0; i < 3; i++) setTimeout(() => bolt(this, e.x + rnd(-r, r) * 0.6, e.z + rnd(-r, r) * 0.5, '#b04cff', 0.05, 2.4), i * 60);
        this.dc.emit({kind: D.SWIRL, x: e.x, z: e.z, r: r * 1.15, life: 0.8, c: [0.2, 0.1, 0.3], c2: [0.8, 0.35, 1.5], q0: 1, a0: 0.9, a1: 0});
        this.flashLight({x: e.x, z: e.z}, '#b070ff', 60, 0.35, 2); this.stage.kick(0.7); }
      m.position.set(e.x + side * q * q * 9, 0.06 + q * 3.2, e.z - q * 1.5); m.rotation.set(-q * 0.5, side * q * 0.8, side * -q * 0.5);
    }});
  }
  beam(from, to, stage, look = 'mensa') { // MENSA's beam (and each of the LASER EYES'), drawn each frame while it burns
    if (!this.beamPool) this.beamPool = [];
    let b = this.beamPool.find(b => !b.used);
    if (!b) { b = {used: false, m: new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 8, 1, true), new THREE.MeshBasicMaterial({color: '#ff6bd5', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false}))}; b.m.geometry.translate(0, 0.5, 0); b.m.geometry.rotateX(Math.PI / 2); this.scene.add(b.m); this.beamPool.push(b); }
    b.used = true; b.m.visible = true;
    const B = BEAM[look], L = from.distanceTo(to); b.m.position.copy(from); b.m.lookAt(to);
    const w = [0.05, 0.09, 0.15][stage] * B.w * (1 + Math.sin(performance.now() / 30) * 0.25); b.m.scale.set(w, w, L);
    b.m.material.color.copy(B.col[stage]);
    if (Math.random() < 0.5) this.add.emit({x: to.x, y: to.y, z: to.z, vx: rnd(-1, 1), vy: rnd(0.5, 2), vz: rnd(-1, 1), life: 0.3, s0: 0.4 + stage * 0.2, s1: 0.05, c: B.spark, cell: CELL.spark});
  }
  update(dt) {
    if (this.beamPool) for (const b of this.beamPool) { if (!b.used) b.m.visible = false; b.used = false; }
    for (let i = this.things.length - 1; i >= 0; i--) {
      const t = this.things[i]; t.age += dt; const k = Math.min(1, t.age / t.life);
      t.tick?.(t, k, t.age);
      if (t.age >= t.life) { for (const o of [t.obj, t.also]) if (o) { o.parent?.remove(o); if (!o.isLight && !o.userData.keep) this.dispose(o); } this.things.splice(i, 1); }
    }
    this.time += dt; this.sp.update(dt, this.time); this.dc.update(dt, this.time); ribbonTime(this.time);
  }
}
export {CELL};
