// The spells as their cards show them, drawn with the effects kit (fx.sp sprites, fx.dc ground marks, fx.front, fx.shell) and
// the props built from the cards (props.js). Each takes the sim's spell event e: x z, r (its area), delay (till it hits), dur
// (how long it lasts). The moving and lasting ones (BAN HAMMER, FART) follow their sim entities in fx.syncSpells.
import * as THREE from 'three';
import {S, D} from './kit.js';
import {prop} from './props.js';
import {CARDS} from '../data.js';

const rnd = (a, b) => a + Math.random() * (b - a), TAU = Math.PI * 2;
const disc = (r, f = 0.9) => { const a = rnd(0, TAU), d = Math.sqrt(Math.random()) * r * f; return [Math.cos(a) * d, Math.sin(a) * d]; };
// call fn(k, age) every frame for life s; done() at the end
const run = (fx, life, fn, done) => fx.things.push({life, age: 0, tick: (t, k, age) => { fn?.(k, age); if (k >= 1) done?.(); }});
const later = (fx, t, fn) => run(fx, t, null, fn);
// a prop in the scene for life s, fn(k, age, obj) every frame; it goes when done (its shared geometry and materials stay)
function place(fx, name, life, fn, scale = 1) {
  const o = prop(name); o.userData.keep = true; o.scale.setScalar(scale); fx.scene.add(o);
  fx.things.push({obj: o, life, age: 0, tick: (t, k, age) => fn?.(k, age, o)});
  return o;
}

// a storm cloud massed over an area: dark puffs lit from below, flickering with the lightning inside it
function storm(fx, x, z, r, life, dark, lit, H = 6.2, a = 0.92, n = 26) {
  for (let i = 0; i < n; i++) { const [dx, dz] = disc(r, 0.95);
    fx.sp.emit({kind: S.SMOKE, x: x + dx, y: H + rnd(-0.5, 0.7), z: z + dz * 0.8, vx: rnd(-0.15, 0.15), vz: rnd(-0.15, 0.15), life: life * rnd(0.9, 1.1), w0: rnd(2, 2.6), w1: rnd(2.8, 3.6), ease: 1,
      c: dark, a0: a, a1: a * 0.27, fin: 0.25, add: 0}); }
  run(fx, life * 0.8, () => { if (Math.random() < 0.25) { const [dx, dz] = disc(r, 0.7);
    fx.sp.emit({kind: S.WISP, x: x + dx, y: H - 0.4, z: z + dz, life: 0.14, w0: rnd(1.6, 2.4), w1: 1, c: lit, a0: 0.6, a1: 0, add: 1}); } });
  fx.dc.emit({kind: D.STAIN, x, z, r: r * 1.25, life: life, c: [0.02, 0.02, 0.04], c2: [0, 0, 0], a0: 0.4, a1: 0, fin: 0.25});   // its shadow
}
// a candlestick crashing down from the cloud onto (x, z) at time t, sticking in the ground, then breaking up
function crash(fx, name, x, z, t, H = 4.5) {
  const tilt = [rnd(-0.5, 0.5), rnd(0, 6.28), rnd(-0.5, 0.5)], col = name === 'candleR' ? [1.2, 0.15, 0.2] : [0.2, 1.2, 0.3];
  place(fx, name, t + 0.7, (k, age, o) => {
    const q = Math.min(1, age / t); o.rotation.set(tilt[0] * q, tilt[1], tilt[2] * q);
    o.position.set(x, H * (1 - q * q) - (age > t ? Math.min(0.35, (age - t) * 2) : 0), z);
    if (age < t) fx.sp.emit({kind: S.SPARK, x, y: o.position.y + 0.5, z, vy: 12, life: 0.12, w: 0.3, asp: 0.5, st: 0.03, c: col, a0: 0.6, a1: 0, add: 1});
    if (age >= t && !o.userData.hit) { o.userData.hit = true;
      fx.burst({x, y: 0, z}, {n: 6, c: col.map(v => Math.min(1, v * 0.8)), s: 0.3, sp: 3, up: 4, life: 0.7, g: 12, cell: 21, add: false, y: 0.3, floor: 0.05, bounce: 0.3});
      fx.front({x, z}, 1, 8, 0.4, {kind: S.SMOKE, y: 0.15, w0: 0.4, w1: 0.9, ease: 1, c: [0.6, 0.56, 0.52], a0: 0.6, a1: 0, add: 0}, 0.2);
      fx.dc.emit({kind: D.CRACK, x, z, r: 0.7, life: 2, c: [0.08, 0.07, 0.06], c2: [0, 0, 0], q0: 0, a0: 0.8, a1: 0}); }
    if (k >= 0.95) o.scale.setScalar(Math.max(0.01, (1 - k) / 0.05));
  });
}
// a bolt with its glow, a branch or two, a scorch and sparks where it lands; top: where it starts
export function bolt(fx, x, z, col, w = 0.07, top = 9) {
  const C = new THREE.Color(col), path = [];
  let px = x + rnd(-0.6, 0.6), py = top, pz = z + rnd(-0.6, 0.6);
  while (py > 0) { path.push(new THREE.Vector3(px, py, pz)); py -= rnd(0.45, 1.1); px += (x - px) * 0.35 + rnd(-0.4, 0.4); pz += (z - pz) * 0.35 + rnd(-0.4, 0.4); }
  path.push(new THREE.Vector3(x, 0, z));
  const lines = [path];
  for (let b = 0; b < 2; b++) { const i = 1 + (Math.random() * (path.length - 3) | 0), s = path[i], br = [s.clone()]; let q = s.clone();
    for (let j = 0; j < 3; j++) { q = q.clone().add(new THREE.Vector3(rnd(-0.8, 0.8), -rnd(0.4, 0.9), rnd(-0.8, 0.8))); br.push(q); } lines.push(br); }
  const g = new THREE.Group();
  lines.forEach((L, i) => { const curve = new THREE.CatmullRomCurve3(L, false, 'catmullrom', 0.1), n = L.length * 3, ww = i ? w * 0.55 : w;
    g.add(new THREE.Mesh(new THREE.TubeGeometry(curve, n, ww * 3.2, 6, false), new THREE.MeshBasicMaterial({color: C, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false})));
    g.add(new THREE.Mesh(new THREE.TubeGeometry(curve, n, ww, 5, false), new THREE.MeshBasicMaterial({color: new THREE.Color(1.6, 1.4, 1.4).lerp(C, 0.25), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false}))); });
  g.children.forEach(m => { m.renderOrder = 8; }); fx.scene.add(g);
  fx.things.push({obj: g, life: 0.38, age: 0, tick: (t, k) => { const f = (1 - k * k) * (Math.random() < 0.55 ? 1 : 0.3); g.children.forEach((m, i) => { m.material.opacity = f * (i % 2 ? 1 : 0.5); }); }});
  const c = [C.r * 1.6, C.g * 1.6, C.b * 1.6];
  fx.sp.emit({kind: S.FLARE, x, y: 0.5, z, life: 0.16, w0: 2.4, w1: 0.6, c, a0: 1, a1: 0.3, add: 1, rot: 0});
  fx.sp.emit({kind: S.GLOW, x, y: 0.4, z, life: 0.3, w0: 2.4, w1: 1, c, a0: 0.8, a1: 0, add: 1});
  for (let i = 0; i < 12; i++) { const a = rnd(0, TAU), v = rnd(2, 5);
    fx.sp.emit({kind: S.SPARK, x, y: 0.2, z, vx: Math.cos(a) * v, vy: rnd(1.5, 4), vz: Math.sin(a) * v, g: 12, drag: 1, life: rnd(0.3, 0.5), w: 0.14, asp: 0.35, st: 0.04, c, a0: 1, a1: 0, add: 1, floor: 0.05, bounce: 0.3}); }
  fx.dc.emit({kind: D.SCORCH, x, z, r: 0.95, life: 5, c: [0.04, 0.03, 0.03], c2: c.map(v => v * 0.6), q0: 1, q1: 0, a0: 0.85, a1: 0, fin: 0.05});
}

const SPELLS = {
  // FUD: a black storm cloud gathers over the area, headlines flutter out of it, red candles crash down, then red lightning
  fud(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.25;
    storm(fx, x, z, r, d + 1.5, [0.13, 0.13, 0.17], [1.6, 0.2, 0.25]);
    for (let i = 0; i < 18; i++) { const [dx, dz] = disc(r);
      fx.sp.emit({kind: S.ICON, cell: 18, x: x + dx, y: rnd(4.5, 6), z: z + dz, vx: rnd(-1, 1), vy: rnd(-2.2, -1), vz: rnd(-1, 1), g: 0.8, drag: 1.4, vr: rnd(-5, 5), life: rnd(1.4, 2.2), w: rnd(0.3, 0.42), asp: 1.25, c: [1, 1, 1], a0: 1, a1: 0, add: 0, floor: 0.05}); }
    for (let i = 0; i < 4; i++) { const [dx, dz] = disc(r, 0.75); crash(fx, 'candleR', x + dx, z + dz, d + i * 0.05, 4.5); }
    later(fx, d, () => {
      for (let i = 0; i < 4; i++) { const [dx, dz] = i ? disc(r, 0.75) : [0, 0]; setTimeout(() => bolt(fx, x + dx, z + dz, '#ff3048', 0.075, 6), i * 55); }
      fx.flashLight({x, z}, '#ff5060', 45, 0.3, 4); fx.stage.kick(0.5);
      fx.front({x, z}, r, 20, 0.5, {kind: S.SMOKE, y: 0.2, w0: 0.5, w1: 1.3, ease: 1, c: [0.5, 0.46, 0.46], a0: 0.65, a1: 0, add: 0}, 0.2);
    });
  },
  // PUMP IT: a green candle rocket blasts out of the middle on a column of flame, green smoke billowing out over the area; the area
  // glows green for as long as it lasts, green candles and arrows rising off it
  pump(fx, e) {
    const {x, z, r} = e, dur = e.dur || 6;
    place(fx, 'rocket', 1.3, (k, age, o) => { const q = Math.max(0, age - 0.12), y = q * q * 9; o.position.set(x, y, z); o.rotation.y = age * 3;
      fx.sp.emit({kind: S.FLAME, x: x + rnd(-0.1, 0.1), y: y - 0.25, z, vy: -6, drag: 2, life: 0.3, w0: 0.9, w1: 0.3, asp: 1.6, rot: Math.PI, c: [1, 0.6, 0.15], a0: 1, a1: 0.2, add: 0.5});
      if (Math.random() < 0.7) fx.sp.emit({kind: S.SMOKE, x, y: y - 0.6, z, vx: rnd(-0.5, 0.5), vy: rnd(-1, 0.3), vz: rnd(-0.5, 0.5), drag: 1, life: 1.2, w0: 0.7, w1: 2, ease: 1, c: [0.6, 0.95, 0.55], a0: 0.6, a1: 0, add: 0}); }, 1.3);
    for (let i = 0; i < 22; i++) { const a = rnd(0, TAU), v = rnd(0.6, 3.2);   // the billow at its foot: a heap of smoke, rolling out and up
      fx.sp.emit({kind: S.SMOKE, x: x + Math.cos(a) * 0.3, y: rnd(0.3, 0.9), z: z + Math.sin(a) * 0.3, vx: Math.cos(a) * v, vy: rnd(0.6, 2.2), vz: Math.sin(a) * v, drag: 2.2, life: rnd(1, 1.6), w0: rnd(0.8, 1.2), w1: rnd(1.8, 2.6), ease: 1,
        c: [[0.62, 1, 0.55], [0.8, 1, 0.75], [0.45, 0.85, 0.4]][i % 3], a0: 0.85, a1: 0, add: 0.15}); }
    const glow = fx.dc.emit({kind: D.GLOW, x, z, r: r * 1.05, hold: true, add: 1, c: [0.3, 1.1, 0.3], a: 0});
    run(fx, dur, (k, age) => {
      glow.a = Math.min(1, age * 3) * (0.55 + Math.sin(age * 5) * 0.1) * (k > 0.92 ? (1 - k) / 0.08 : 1);
      if (Math.random() < 0.35) { const [dx, dz] = disc(r, 0.85), big = Math.random() < 0.4;
        fx.sp.emit({kind: S.ICON, cell: big ? 17 : 16, x: x + dx, y: 0.2, z: z + dz, vy: rnd(1.4, 2.6), life: rnd(0.9, 1.3), w: big ? 0.42 : 0.36, asp: big ? 1.3 : 1, rot: 0, c: [0.35, 1, 0.4], a0: 1, a1: 0, add: 0.3, fin: 0.1}); }
      if (Math.random() < 0.4) { const [dx, dz] = disc(r, 0.85); fx.sp.emit({kind: S.SPARK, x: x + dx, y: 0.1, z: z + dz, vy: rnd(2, 3.5), life: 0.6, w: 0.12, asp: 0.4, st: 0.05, c: [0.5, 1.6, 0.5], a0: 1, a1: 0, add: 1}); }
    }, () => fx.release(glow, 0.3));
  },
  // AIRDROP: green parachutes float down, each carrying a gold coin; where they land, the coins burst and the parachutes fold
  airdrop(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.7;
    for (let i = 0; i < 7; i++) { const [dx, dz] = i ? disc(r, 0.75) : [0, 0], px = x + dx, pz = z + dz, h0 = rnd(6.5, 8), t = d + rnd(-0.04, 0.04), sw = rnd(0, 6);
      place(fx, 'parachute', t + 0.45, (k, age, o) => {
        if (age < t) { const q = age / t; o.position.set(px + Math.sin(age * 5 + sw) * 0.15, h0 * (1 - q) + 0.35, pz); o.rotation.set(-0.5 + Math.sin(age * 5 + sw) * 0.12, 0, Math.sin(age * 6 + sw) * 0.2); o.children[2].rotation.z = age * 4;
          if (Math.random() < 0.3) fx.sp.emit({kind: S.SPARK, x: o.position.x + rnd(-0.3, 0.3), y: o.position.y, z: o.position.z + rnd(0, 0.3), vy: 3, life: 0.3, w: 0.08, asp: 0.5, st: 0.03, c: [1.8, 1.4, 0.5], a0: 1, a1: 0, add: 1});   // (tilted back: the coin shows under its canopy)
          return; }
        if (!o.userData.hit) { o.userData.hit = true;
          fx.burst({x: px, y: 0, z: pz}, {n: 7, c: [1, 1, 1], s: 0.42, sp: 3, up: 5, life: 1, g: 14, cell: 19, add: false, y: 0.3, floor: 0.05, bounce: 0.35, drag: 0.5});
          fx.sp.emit({kind: S.FLARE, x: px, y: 0.5, z: pz, life: 0.16, w0: 1.6, w1: 0.3, c: [1.8, 1.5, 0.6], a0: 1, a1: 0.3, add: 1, rot: 0});
          fx.front({x: px, z: pz}, 1.1, 8, 0.4, {kind: S.SMOKE, y: 0.15, w0: 0.4, w1: 0.9, ease: 1, c: [0.62, 0.58, 0.54], a0: 0.6, a1: 0, add: 0}, 0.2); }
        const q = (age - t) / 0.45; o.position.y = 0.35 - q * 0.3; o.scale.set(0.7, Math.max(0.02, 0.7 * (1 - q)), 0.7);
      }, 0.7);
      fx.dc.emit({kind: D.STAIN, x: px, z: pz, r0: 0.3, r1: 0.8, life: d, c: [0.02, 0.03, 0.02], c2: [0, 0, 0], a0: 0, a1: 0.45});   // its shadow, closing in
    }
    later(fx, d, () => fx.stage.kick(0.35));
  },
  // COLD WALLET: an ice block with a hardware wallet frozen in it slams down; frost races out over the ground, shards and freezing
  // mist burst from it, glints across the ice while everything's frozen; then the block shatters
  coldwallet(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.15, fr = CARDS.coldwallet.spell.freeze || 3.5, life = d + fr + 0.5;
    const frost = fx.dc.emit({kind: D.FROST, x, z, r: 0.3, hold: true, c: [0.28, 0.55, 0.9], c2: [0.5, 0.9, 1.5], a: 0});   // blue glassy ice, not snow
    place(fx, 'iceblock', life, (k, age, o) => {   // (a bigger block: it is the card)
      const q = Math.min(1, age / d); o.position.set(x, 5 * (1 - q * q), z); o.rotation.y = 0.5;
      if (age >= d && !o.userData.hit) { o.userData.hit = true; fx.flashLight({x, z}, '#9fe0ff', 30, 0.3, 2); fx.stage.kick(0.45);
        for (let i = 0; i < 26; i++) { const a = rnd(0, TAU), v = rnd(2.5, 6.5);
          fx.sp.emit({kind: S.SHARD, x, y: 0.6, z, vx: Math.cos(a) * v, vy: rnd(1.5, 5), vz: Math.sin(a) * v, g: 14, drag: 0.6, vr: rnd(-8, 8), life: rnd(0.6, 1.1), w: rnd(0.16, 0.32), asp: 1.6, c: [0.7, 0.9, 1.2], a0: 1, a1: 0, add: 0.4, floor: 0.06, bounce: 0.3}); }
        fx.front({x, z}, r, 20, 0.6, {kind: S.SMOKE, y: 0.2, w0: 0.5, w1: 1.1, ease: 1, c: [0.7, 0.88, 1.05], a0: 0.35, a1: 0, add: 0.2}, 0.25);
        for (let i = 0; i < 9; i++) { const [dx, dz] = i < 6 ? [Math.cos(i / 6 * TAU + 0.3) * r * 0.85, Math.sin(i / 6 * TAU + 0.3) * r * 0.85] : disc(r, 0.6), t0 = rnd(0, 0.12), s = rnd(0.8, 1.25), ry = rnd(0, TAU);   // crystals breaking out of the ground
          place(fx, 'icespike', life - d, (k2, age2, sp) => { const g = Math.min(1, Math.max(0, (age2 - t0) / 0.18)), out = Math.max(0, (age2 - (life - d) + 0.45) / 0.45);
            sp.position.set(x + dx, 0, z + dz); sp.rotation.y = ry; sp.scale.set(s * (1 - out * 0.3), Math.max(0.01, s * (1 - (1 - g) ** 3) * (1 - out)), s * (1 - out * 0.3)); }); }
        fx.sp.emit({kind: S.FLARE, x, y: 0.9, z, life: 0.16, w0: 1.8, w1: 0.4, c: [1.2, 1.6, 1.9], a0: 1, a1: 0.3, add: 1, rot: 0}); }
      if (age >= d) { const f = age - d; frost.r = r * 1.1 * (0.3 + 0.7 * (1 - Math.max(0, 1 - f / 0.35) ** 3)); frost.a = Math.min(1, f * 5) * (age > life - 0.5 ? (life - age) / 0.5 : 1);
        if (Math.random() < 0.25) { const [dx, dz] = disc(r, 0.9); fx.sp.emit({kind: S.FLARE, x: x + dx, y: 0.12, z: z + dz, life: 0.4, w0: 0.5, w1: 0, c: [1.6, 1.9, 2], a0: 1, a1: 1, add: 1, rot: 0}); }
        if (Math.random() < 0.08) { const [dx, dz] = disc(r, 0.8); fx.sp.emit({kind: S.SMOKE, x: x + dx, y: 0.2, z: z + dz, vx: rnd(-0.3, 0.3), vz: rnd(-0.3, 0.3), life: 1.6, w0: 0.6, w1: 1.2, ease: 1, c: [0.85, 0.95, 1.05], a0: 0.25, a1: 0, fin: 0.3, add: 0.2}); } }
      if (k >= 1) { frost.dead = true;
        for (let i = 0; i < 18; i++) { const a = rnd(0, TAU), v = rnd(1.5, 4);
          fx.sp.emit({kind: S.SHARD, x, y: rnd(0.3, 1.5), z, vx: Math.cos(a) * v, vy: rnd(1, 4), vz: Math.sin(a) * v, g: 14, vr: rnd(-8, 8), life: rnd(0.5, 0.9), w: rnd(0.2, 0.4), asp: 1.6, c: [0.7, 0.9, 1.2], a0: 1, a1: 0, add: 0.4, floor: 0.06, bounce: 0.3}); } }
    }, 1.2);
  },
  // LIQUIDATION: a pool of red goo spreads, bubbling; red candles rise out of it and melt down into it
  liquidation(fx, e) {
    const {x, z, r} = e, dur = e.dur || 8;
    const pool = fx.dc.emit({kind: D.POOL, x, z, r: 0.3, hold: true, c: [0.24, 0.008, 0.02], c2: [0.95, 0.06, 0.09], q: 1, a: 0});
    for (let i = 0; i < 6; i++) { const [dx, dz] = disc(r, 0.7), t0 = rnd(0.1, 0.5), h = rnd(1.2, 2.1), tilt = [rnd(-0.3, 0.3), rnd(0, 6), rnd(-0.3, 0.3)];
      place(fx, 'candleR', dur, (k, age, o) => { const up = Math.min(1, Math.max(0, (age - t0) / 0.35)), melt = Math.max(0.05, 1 - Math.max(0, age - t0 - 0.4) / (dur - t0 - 0.6));
        o.position.set(x + dx, -0.3 * (1 - up) - 0.1, z + dz); o.rotation.set(tilt[0] * (1.5 - melt), tilt[1], tilt[2] * (1.5 - melt)); o.scale.set(1 + (1 - melt) * 0.25, Math.max(0.01, h * up * melt), 1 + (1 - melt) * 0.25);
        if (Math.random() < 0.06 * up) fx.sp.emit({kind: S.GLOW, x: x + dx + rnd(-0.2, 0.2), y: h * melt * 0.8, z: z + dz, vy: -1.5, g: 4, life: 0.5, w: 0.18, asp: 1.5, c: [0.8, 0.05, 0.07], a0: 1, a1: 0.5, add: 0, floor: 0.06}); });
    }
    run(fx, dur, (k, age) => {
      pool.r = r * (0.3 + 0.7 * (1 - Math.max(0, 1 - age / 0.5) ** 3)) * (k > 0.93 ? 1 - (k - 0.93) / 0.07 * 0.6 : 1); pool.a = Math.min(1, age * 4) * (k > 0.93 ? (1 - k) / 0.07 : 1) * 0.95;
      if (Math.random() < 0.45) { const [dx, dz] = disc(pool.r, 0.85);
        fx.sp.emit({kind: S.BUBBLE, x: x + dx, y: 0.08, z: z + dz, vy: 0.15, life: rnd(0.35, 0.6), w0: 0.08, w1: rnd(0.25, 0.45), c: [0.85, 0.1, 0.13], a0: 1, a1: 1, add: 0.15});
        if (Math.random() < 0.4) fx.sp.emit({kind: S.SPARK, x: x + dx, y: 0.1, z: z + dz, vx: rnd(-0.8, 0.8), vy: rnd(1.5, 2.5), vz: rnd(-0.8, 0.8), g: 9, life: 0.4, w: 0.1, asp: 0.6, st: 0.03, c: [0.8, 0.04, 0.06], a0: 1, a1: 0, add: 0, floor: 0.06}); }
      if (Math.random() < 0.08) { const [dx, dz] = disc(pool.r, 0.6); fx.sp.emit({kind: S.SMOKE, x: x + dx, y: 0.3, z: z + dz, vy: 0.5, life: 1.6, w0: 0.6, w1: 1.4, ease: 1, c: [0.35, 0.05, 0.07], a0: 0.35, a1: 0, fin: 0.3, add: 0}); }
    }, () => { pool.dead = true; });
  },
  // GOD CANDLE: a column of green light from the sky and the ground cracking under it, then a colossal green candle slams down and
  // stays planted: green energy splashing up around its foot, droplets, rock and coins thrown out, the ground split and glowing green
  godcandle(fx, e) {
    const {x, z, r} = e, d = e.delay || 1.3, stay = 1.5, G = [0.3, 1.25, 0.35];
    const crack = fx.dc.emit({kind: D.CRACK, x, z, r: r * 1.5, hold: true, c: [0.05, 0.06, 0.04], c2: [0.4, 1.4, 0.4], q: 0, a: 0});
    const light = fx.dc.emit({kind: D.GLOW, x, z, r: r * 1.3, hold: true, add: 1, c: [0.3, 1.2, 0.35], a: 0});
    const tilt = [rnd(-0.08, 0.08), rnd(0, 6.28), rnd(-0.08, 0.08)];
    place(fx, 'godcandle', d + stay + 0.6, (k, age, o) => {
      o.rotation.set(tilt[0], tilt[1], tilt[2]);
      if (age < d) { const q = age / d; o.position.set(x, 40 * (1 - q * q), z); light.a = q * q * 0.9; crack.a = q; crack.q = q * q * 0.5;
        if (q > 0.3) { fx.sp.emit({kind: S.FLAME, x: x + rnd(-0.7, 0.7), y: o.position.y + 6.4, z: z + rnd(-0.3, 0.3), vy: 5, life: 0.35, w0: 1.2, w1: 0.4, asp: 1.6, c: G, a0: 1, a1: 0, add: 0.6});
          fx.sp.emit({kind: S.SPARK, x: x + rnd(-0.8, 0.8), y: o.position.y + rnd(0, 6), z: z + rnd(-0.8, 0.8), vy: 20, life: 0.12, w: 0.25, asp: 0.4, st: 0.03, c: [0.6, 1.8, 0.6], a0: 1, a1: 0, add: 1}); }
        if (Math.random() < 0.5) fx.sp.emit({kind: S.GLOW, x, y: o.position.y * 0.5 + 2, z, life: 0.1, w: 2.2, asp: Math.max(1, o.position.y / 2), c: [0.25, 1, 0.3], a0: 0.35 * q, a1: 0.35 * q, add: 1});
        return; }
      if (!o.userData.hit) { o.userData.hit = true; o.position.y = -0.35; const p = {x, y: 0, z};
        for (let i = 0; i < 40; i++) { const a = rnd(0, TAU), u = rnd(0.5, 3), rr = rnd(0.5, 1.1);   // the energy splashing up around its foot
          fx.sp.emit({kind: S.FLAME, x: x + Math.cos(a) * rr, y: 0.2, z: z + Math.sin(a) * rr, vx: Math.cos(a) * u, vy: rnd(4, 10), vz: Math.sin(a) * u, g: 9, drag: 1.2, life: rnd(0.45, 0.75),
            w0: rnd(0.6, 1.1), w1: 0.25, asp: 1.8, c: G, a0: 1, a1: 0.1, add: 0.6}); }
        for (let i = 0; i < 34; i++) { const a = rnd(0, TAU), u = rnd(2, 6);   // its droplets
          fx.sp.emit({kind: S.SPARK, x: x + Math.cos(a) * 0.7, y: 0.4, z: z + Math.sin(a) * 0.7, vx: Math.cos(a) * u, vy: rnd(4, 9), vz: Math.sin(a) * u, g: 16, drag: 0.6, life: rnd(0.6, 1),
            w: rnd(0.1, 0.18), asp: 0.5, st: 0.03, c: [0.5, 1.9, 0.5], a0: 1, a1: 0.4, add: 0.8, floor: 0.05, bounce: 0.25}); }
        fx.burst(p, {n: 16, c: [0.26, 0.24, 0.22], s: 0.42, sp: 6, up: 7, life: 1.1, g: 14, cell: 21, add: false, y: 0.3, floor: 0.05, bounce: 0.3});
        fx.burst(p, {n: 14, c: [1, 0.85, 0.4], s: 0.45, sp: 5, up: 8, life: 1.2, g: 12, cell: 19, add: false, y: 0.6, floor: 0.06, bounce: 0.4});
        for (let i = 0; i < 9; i++) { const a = rnd(0, TAU), rr = rnd(0.8, r * 1.3);   // dust kicked up in clumps
          fx.sp.emit({kind: S.SMOKE, x: x + Math.cos(a) * rr, y: 0.3, z: z + Math.sin(a) * rr, vx: Math.cos(a) * rnd(1, 2.5), vy: rnd(0.6, 1.4), vz: Math.sin(a) * rnd(1, 2.5), drag: 2, life: rnd(0.9, 1.4),
            w0: rnd(0.7, 1), w1: rnd(1.6, 2.2), ease: 1, c: [0.55, 0.58, 0.48], a0: 0.6, a1: 0, fin: 0.2, add: 0}); }
        fx.sp.emit({kind: S.FLARE, x, y: 1.2, z, life: 0.2, w0: 3.4, w1: 1, c: [1, 1.6, 1], a0: 1, a1: 0.2, add: 1, rot: 0});
        fx.dc.emit({kind: D.SCORCH, x, z, r: r * 1.15, life: 6, c: [0.05, 0.06, 0.04], c2: [0.3, 1.2, 0.35], q0: 1, q1: 0, a0: 0.9, a1: 0, fin: 0.05});
        fx.flashLight(p, '#7CFF6B', 40, 0.35, 2); fx.stage.kick(1.1); fx.release(light, 0.8); }
      const q = Math.max(0, (age - d - stay) / 0.6); o.position.y = -0.35 - q * q * 6.5; crack.q = 1 - Math.min(1, (age - d) / (stay + 0.6)) * 0.7; crack.a = 1;
      if (age - d < stay && Math.random() < 0.35) { const a = rnd(0, TAU);   // it keeps fizzing where it stands
        fx.sp.emit({kind: S.SPARK, x: x + Math.cos(a) * 0.85, y: rnd(0.2, 4), z: z + Math.sin(a) * 0.85, vy: rnd(1, 3), life: 0.4, w: 0.1, asp: 0.5, st: 0.03, c: [0.5, 1.8, 0.5], a0: 1, a1: 0, add: 1}); }
      if (k >= 1) fx.release(crack, 4);
    });
  },
  // DOWNVOTES: waves of chunky red arrows slanting out of the sky all from one side, as on the card, streaking, stabbing into the
  // ground at their angle: red sparks and rubble thrown back up, the ground cracked and glowing red; then they sink out of it
  downvotes(fx, e) {
    const Sp = CARDS.downvotes.spell, r = e.r, H = 9, red = [1.6, 0.12, 0.18];
    for (let w = 0; w < (Sp.waves || 1); w++) {
      const land = (e.delay || 0.45) + w * (Sp.gap || 0.3), fall = 0.4;
      for (let k = 0; k < 12; k++) {
        const [ox, oz] = disc(r, 0.92), x = e.x + ox, z = e.z + oz, t0 = land - fall + rnd(-0.05, 0.05), dig = rnd(0.25, 0.45);
        const rot = new THREE.Euler(0, rnd(-0.3, 0.3), 0.42 + rnd(-0.08, 0.08)), d = new THREE.Vector3(0, -1, 0).applyEuler(rot), L = H / -d.y, v = L / fall;
        place(fx, 'arrow', t0 + fall + 0.6, (q, age, o) => {
          if (age < t0) { o.visible = false; return; } o.visible = true; o.rotation.copy(rot);
          const f = Math.min(1, (age - t0) / fall), s = f < 1 ? (1 - f) * L : -Math.min(dig, (age - t0 - fall) * 5) - Math.max(0, q - 0.75) * 1.6;   // s: how far back up its path
          o.position.set(x - d.x * s, -d.y * s, z - d.z * s);
          if (f < 1) fx.sp.emit({kind: S.SPARK, x: o.position.x - d.x * 1.3, y: o.position.y - d.y * 1.3, z: o.position.z - d.z * 1.3, vx: d.x * v, vy: d.y * v, vz: d.z * v, life: 0.06,
            w: 0.5, asp: 0.5, st: 0.05, c: red, a0: 0.45, a1: 0, add: 1});
          else if (!o.userData.hit) { o.userData.hit = true; const p = {x, y: 0, z};
            fx.sp.emit({kind: S.FLARE, x, y: 0.25, z, life: 0.1, w0: 1.1, w1: 0.3, c: [2, 0.6, 0.5], a0: 1, a1: 0, add: 1, rot: rnd(0, 3)});
            for (let i = 0; i < 7; i++) { const b = rnd(0, TAU), u = rnd(1.5, 3.5);
              fx.sp.emit({kind: S.SPARK, x, y: 0.15, z, vx: Math.cos(b) * u - d.x * 2, vy: rnd(2.5, 5), vz: Math.sin(b) * u - d.z * 2, g: 14, drag: 1, life: rnd(0.25, 0.45), w: 0.1, asp: 0.35, st: 0.035,
                c: i % 3 ? red : [2, 0.9, 0.4], a0: 1, a1: 0, add: 1, floor: 0.04, bounce: 0.3}); }
            fx.burst(p, {n: 5, c: [0.3, 0.24, 0.2], s: 0.22, sp: 2.5, up: 3.5, life: 0.6, g: 13, cell: 21, add: false, y: 0.15, floor: 0.04, bounce: 0.25});
            fx.sp.emit({kind: S.SMOKE, x: x - d.x * 0.3, y: 0.25, z, vx: -d.x * 0.6, vy: 0.5, life: 0.7, w0: 0.35, w1: 1, ease: 1, c: [0.5, 0.42, 0.4], a0: 0.5, a1: 0, add: 0});
            fx.sp.emit({kind: S.GLOW, x, y: 0.12, z, life: 0.35, w0: 0.9, w1: 0.5, c: [1.2, 0.1, 0.12], a0: 0.7, a1: 0, add: 1});
            fx.dc.emit({kind: D.CRACK, x, z, r: rnd(0.45, 0.6), life: 1.8, c: [0.07, 0.05, 0.05], c2: [1, 0.08, 0.12], q0: 1, q1: 0, a0: 0.85, a1: 0}); }
          if (q > 0.85) o.scale.setScalar(0.9 * Math.max(0.01, (1 - q) / 0.15));
        }, 0.9);
      }
      later(fx, land, () => fx.stage.kick(0.22));
    }
  },
  // MARGIN CALL: a red-lit storm rolls over, the chart's red candles tumbling down out of it; the bolts (fx.bolt, one per target) strike
  margincall(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.35;
    storm(fx, x, z - 1.5, r * 0.9, d + 1.3, [0.2, 0.07, 0.1], [1.8, 0.15, 0.3], 8.5, 0.7, 18);   // high: the targets stay in sight under it
    for (let i = 0; i < 10; i++) { const [dx, dz] = disc(r, 0.9);
      fx.sp.emit({kind: S.ICON, cell: 17, x: x + dx, y: rnd(6, 7.5), z: z + dz - 1.5, vy: -rnd(2, 3.5), g: 2, vr: rnd(-2, 2), life: rnd(1, 1.5), w: 0.42, asp: 1.3, c: [1, 0.15, 0.2], a0: 1, a1: 0, add: 0.3}); }
  },
  // GAS FEES: a fuel nozzle hangs over the area pumping green gas into it; the gas pools and rolls, and coins are sucked up out
  // of it into the nozzle (the fees)
  gasfees(fx, e) {
    const {x, z, r} = e, dur = e.dur || 6, nx = x + 0.6, nz = z - 0.2, ny = 3.6;
    const gas = fx.dc.emit({kind: D.STAIN, x, z, r: 0.4, hold: true, c: [0.1, 0.24, 0.04], c2: [0.16, 0.42, 0.06], a: 0});
    place(fx, 'nozzle', dur + 0.5, (k, age, o) => {
      const inn = Math.min(1, age / 0.35), out = age > dur ? (age - dur) / 0.5 : 0, y = ny + (1 - inn) * 3 + out * 4 + Math.sin(age * 2.2) * 0.1;
      o.position.set(nx, y, nz); o.rotation.set(0, -0.5, -0.15 + Math.sin(age * 1.7) * 0.05);
      const tip = new THREE.Vector3(-1.85, -0.4, 0).applyEuler(o.rotation).add(o.position);
      if (age < dur) { for (let i = 0; i < 2; i++) fx.sp.emit({kind: S.SMOKE, x: tip.x, y: tip.y, z: tip.z, vx: rnd(-0.6, 0.6), vy: -rnd(3, 4.5), vz: rnd(-0.6, 0.6), drag: 1.6, life: rnd(0.7, 1), w0: 0.3, w1: 1.4, ease: 1, c: [0.55, 0.95, 0.3], a0: 0.85, a1: 0.1, add: 0.2});
        if (Math.random() < 0.18) { const [dx, dz] = disc(r, 0.8), sx = x + dx, sz = z + dz, T = rnd(0.9, 1.3);
          fx.sp.emit({kind: S.ICON, cell: 19, x: sx, y: 0.3, z: sz, vx: (tip.x - sx) / T, vy: (tip.y - 0.3) / T, vz: (tip.z - sz) / T, vr: rnd(-4, 4), life: T, w0: 0.5, w1: 0.18, c: [1, 1, 1], a0: 1, a1: 0.6, add: 0}); } }
      gas.r = r * (0.35 + 0.65 * (1 - Math.max(0, 1 - age / 1.2) ** 2)); gas.a = Math.min(1, age * 2) * (age > dur ? Math.max(0, 1 - (age - dur) / 0.5) : 1) * 0.6;
      if (age < dur && Math.random() < 0.85) { const [dx, dz] = disc(gas.r, 0.75);   // the gas itself: big lumpy billows rolling round, lit from above
        fx.sp.emit({kind: S.SMOKE, x: x + dx, y: rnd(0.3, 1.3), z: z + dz, vx: rnd(-0.3, 0.3), vy: rnd(0.05, 0.35), vz: rnd(-0.3, 0.3), curl: rnd(-1, 1), cx: x, cz: z, life: rnd(1.6, 2.2), w0: rnd(1.4, 2), w1: rnd(2.6, 3.4), ease: 1,
          c: [[0.45, 0.85, 0.15], [0.62, 0.95, 0.22], [0.3, 0.6, 0.1], [0.75, 1, 0.3]][Math.random() * 4 | 0], a0: 0.8, a1: 0, fin: 0.3, add: 0.08}); }
      if (age < dur && Math.random() < 0.3) { const [dx, dz] = disc(gas.r, 0.8);   // bubbles popping in it
        fx.sp.emit({kind: S.BUBBLE, x: x + dx, y: rnd(0.2, 1), z: z + dz, vy: rnd(0.3, 0.7), life: rnd(0.5, 0.8), w0: 0.1, w1: rnd(0.25, 0.4), c: [0.7, 1.3, 0.3], a0: 1, a1: 1, add: 0.4}); }
      if (k >= 1) gas.dead = true;
    }, 0.8);
  },
  // HOPIUM: a potion flask tips over the area and pours out its glowing pink hope: it splashes and spreads into a pink mist full of
  // sparkles, hearts and little green candles rising
  hopium(fx, e) {
    const {x, z, r} = e, dur = e.dur || 2.5, fx0 = x + 0.9, fz0 = z - 0.3, fy = 4.2;
    const glow = fx.dc.emit({kind: D.GLOW, x, z, r: 0.5, hold: true, add: 1, c: [1.3, 0.45, 1.0], a: 0});
    place(fx, 'flask', dur + 0.6, (k, age, o) => {
      const tip = Math.min(1, age / 0.35), out = Math.max(0, (age - dur) / 0.6);
      o.position.set(fx0, fy + (1 - tip) * 1.5 + out * 2, fz0); o.rotation.set(0.35, 0, tip * 2.1); o.scale.setScalar(1.5 * Math.max(0.01, 1 - out));
      const mouth = new THREE.Vector3(0, 1.62, 0).applyEuler(o.rotation).multiplyScalar(o.scale.x).add(o.position);
      o.getObjectByName('liq')?.material.map.offset.set(age * 0.15, -age * 0.35);   // the hopium swirling in it
      if (age > 0.3 && age < dur * 0.8) for (let i = 0; i < 4; i++) {   // the stream: pink and gold, streaked, sparkling, falling into the middle
        const T = rnd(0.45, 0.6), vx = (x - mouth.x) / T + rnd(-0.25, 0.25), vy = (0.2 - mouth.y) / T + 4.5 * T * 0.5, vz = (z - mouth.z) / T + rnd(-0.25, 0.25);
        fx.sp.emit(i < 2 ? {kind: S.SPARK, x: mouth.x, y: mouth.y, z: mouth.z, vx, vy, vz, g: 4.5, life: T, w: rnd(0.22, 0.32), asp: 0.8, st: 0.05, c: i ? [1.8, 1.2, 0.4] : [1.5, 0.45, 1.15], a0: 0.9, a1: 0.7, add: 0.5}
          : {kind: i === 2 ? S.GLOW : S.FLARE, x: mouth.x, y: mouth.y, z: mouth.z, vx, vy, vz, g: 4.5, life: T, w: i === 2 ? rnd(0.3, 0.45) : 0.3, c: [1.8, 0.8, 1.5], a0: 1, a1: 0.8, add: 0.8, rot: 0}); }
      if (age > 0.3 && age < dur * 0.8 && Math.random() < 0.2) { const T = 0.55;   // now and then a heart tumbles down in it
        fx.sp.emit({kind: S.ICON, cell: 10, x: mouth.x, y: mouth.y, z: mouth.z, vx: (x - mouth.x) / T, vy: (0.4 - mouth.y) / T + 4.5 * T * 0.5, vz: (z - mouth.z) / T, g: 4.5, life: T, w: 0.32, rot: 0, c: [1, 0.4, 0.7], a0: 1, a1: 0.8, add: 0.3}); }
      glow.r = r * Math.min(1, Math.max(0.15, (age - 0.6) / 0.6)) * 1.05; glow.a = Math.min(1, Math.max(0, age - 0.6) * 3) * (age > dur ? Math.max(0, 1 - (age - dur) / 0.6) : 1) * 0.8;
      if (age > 0.6 && age < dur) {
        if (Math.random() < 0.5) { const [dx, dz] = disc(glow.r, 0.85); fx.sp.emit({kind: S.SMOKE, x: x + dx, y: rnd(0.2, 0.8), z: z + dz, vy: rnd(0.2, 0.5), life: 1.4, w0: 1, w1: 2.2, ease: 1, c: [1, 0.6, 0.9], a0: 0.45, a1: 0, fin: 0.25, add: 0.5}); }
        if (Math.random() < 0.5) { const [dx, dz] = disc(glow.r, 0.85), kind = Math.random();
          fx.sp.emit(kind < 0.3 ? {kind: S.ICON, cell: 10, x: x + dx, y: 0.3, z: z + dz, vy: rnd(1.2, 2), life: 1, w: 0.35, rot: 0, c: [1, 0.45, 0.75], a0: 1, a1: 0, add: 0.3}
            : kind < 0.5 ? {kind: S.ICON, cell: 17, x: x + dx, y: 0.3, z: z + dz, vy: rnd(1.2, 2), life: 1, w: 0.3, asp: 1.3, rot: 0, c: [0.35, 1, 0.4], a0: 1, a1: 0, add: 0.3}
            : {kind: S.FLARE, x: x + dx, y: rnd(0.2, 1.4), z: z + dz, vy: rnd(0.3, 0.9), life: 0.5, w0: rnd(0.3, 0.5), w1: 0, c: [1.8, 1.2, 1.7], a0: 1, a1: 1, add: 1, rot: 0}); }
      }
      if (k >= 1) glow.dead = true;
    }, 0.9);
  },
  // DEAD COINS: crooked tombstones push up out of the ground in a gold-lit graveyard mist; where each coin claws its way out the
  // earth bursts and leaves a mound of dirt
  deadcoins(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.5, life = d + 4.5;
    const glow = fx.dc.emit({kind: D.GLOW, x, z, r: r * 1.05, hold: true, add: 1, c: [0.75, 0.52, 0.18], a: 0});
    const marks = [], mounds = [];   // (each tomb's mound comes up with it; the coins' are thrown up at once)
    for (let i = 0; i < 6; i++) { const [dx, dz] = disc(r, 0.85), t0 = rnd(0, d * 0.8), rot = rnd(-0.6, 0.6), lean = [rnd(-0.18, 0.18), rnd(-0.15, 0.15)];
      const mk = fx.dc.emit({kind: D.STAIN, x: x + dx, z: z + dz + 0.3, r: rnd(0.55, 0.7), hold: true, c: [0.13, 0.09, 0.06], c2: [0.25, 0.18, 0.08], a: 0}); marks.push(mk);
      place(fx, 'tomb', life, (k, age, o) => { const up = Math.min(1, Math.max(0, (age - t0) / 0.4)), down = Math.max(0, (age - life + 0.8) / 0.8); mk.a = up * 0.9 * (1 - down);
        o.position.set(x + dx, -1.4 * (1 - up) - 1.4 * down, z + dz); o.rotation.set(lean[0] + (1 - up) * 0.3, rot, lean[1]);
        if (up > 0 && up < 1 && Math.random() < 0.5) fx.burst({x: x + dx, y: 0, z: z + dz}, {n: 2, c: [0.42, 0.3, 0.2], s: 0.3, sp: 2, up: 3, life: 0.6, g: 12, cell: 21, add: false, y: 0.1, floor: 0.04}); }, 1.25);
    }
    for (let i = 0; i < 9; i++) later(fx, d + rnd(0, 1.2), () => { const [dx, dz] = disc(r, 0.85);   // coins clawing out
      const mk = fx.dc.emit({kind: D.STAIN, x: x + dx, z: z + dz, r: rnd(0.4, 0.55), hold: true, c: [0.15, 0.1, 0.06], c2: [0.3, 0.2, 0.08], a: 0.9}); marks.push(mk); mounds.push(mk);
      fx.burst({x: x + dx, y: 0, z: z + dz}, {n: 7, c: [0.42, 0.3, 0.2], s: 0.32, sp: 2.5, up: 4.5, life: 0.8, g: 12, cell: 21, add: false, y: 0.1, floor: 0.04, bounce: 0.2});
      fx.sp.emit({kind: S.SMOKE, x: x + dx, y: 0.2, z: z + dz, vy: 0.5, life: 0.8, w0: 0.5, w1: 1.2, ease: 1, c: [0.45, 0.36, 0.28], a0: 0.6, a1: 0, add: 0});
      fx.sp.emit({kind: S.FLARE, x: x + dx, y: 0.4, z: z + dz, life: 0.18, w0: 1.2, w1: 0.2, c: [1.8, 1.4, 0.5], a0: 1, a1: 0, add: 1, rot: 0}); });
    run(fx, life, (k, age) => {
      const a = Math.min(1, age * 2) * (k > 0.85 ? (1 - k) / 0.15 : 1); glow.a = a * 0.55; for (const m of mounds) m.a = a * 0.9;
      if (Math.random() < 0.4) { const [dx, dz] = disc(r, 0.9); fx.sp.emit({kind: S.SMOKE, x: x + dx, y: 0.25, z: z + dz, vx: rnd(-0.3, 0.3), vz: rnd(-0.3, 0.3), life: 2, w0: 1.2, w1: 2.4, ease: 1, c: [0.55, 0.45, 0.65], a0: 0.35, a1: 0, fin: 0.4, add: 0.3}); }
      if (Math.random() < 0.2) { const [dx, dz] = disc(r, 0.9); fx.sp.emit({kind: S.GLOW, x: x + dx, y: rnd(0.3, 1.2), z: z + dz, vy: 0.4, life: 1, w0: 0.2, w1: 0, c: [1.6, 1.2, 0.4], a0: 1, a1: 1, add: 1}); }
    }, () => { fx.release(glow, 0.2); for (const m of marks) fx.release(m, 0.5); });
  },
  // HARD FORK: the chain splits: a line of light runs up the middle of the area and forks in two, the ground lit under it, then a flash
  // where it forks and little forks rising (the copies step out each with its own blink: units.js)
  hardfork(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.2, A = [0.45, 1.1, 1.8], B = [1, 0.55, 1.8];
    fx.dc.emit({kind: D.GLOW, x, z, r0: r * 0.5, r1: r * 1.05, ease: 1, life: d + 0.8, c: [0.35, 0.55, 1.2], a0: 0.9, a1: 0, add: 1});
    const dot = (px, pz, c) => fx.sp.emit({kind: S.GLOW, x: px, y: 0.25, z: pz, life: 0.55, w0: 0.55, w1: 0.2, c, a0: 1, a1: 0, add: 1});
    let last = 0;
    run(fx, d + 0.12, k => {
      for (let i = 1; i <= 3; i++) { const q = last + (k - last) * i / 3;   // (a few a frame: unbroken at any frame rate)
        if (q < 0.45) dot(x, z + r * 0.95 * (1 - q / 0.45), A);
        else { const b = (q - 0.45) / 0.55; dot(x - b * r * 0.7, z - b * r * 0.75, A); dot(x + b * r * 0.7, z - b * r * 0.75, B); } }
      last = k;
    });
    later(fx, d, () => {
      fx.sp.emit({kind: S.FLARE, x, y: 0.8, z, life: 0.18, w0: 3.2, w1: 0.6, c: [1.2, 1.5, 2], a0: 1, a1: 0.3, add: 1, rot: 0});
      fx.front({x, z}, r, 12, 0.5, {kind: S.WISP, y: 0.4, w0: 0.5, w1: 1.1, c: [0.65, 0.65, 1.6], a0: 0.8, a1: 0, add: 1}, 0.2);
      for (let i = 0; i < 6; i++) { const [dx, dz] = disc(r, 0.8); fx.sp.emit({kind: S.ICON, cell: 24, x: x + dx, y: 0.3, z: z + dz, vy: rnd(1.2, 2.2), life: rnd(0.7, 1), w: 0.42, rot: 0, c: i % 2 ? [0.5, 1, 1.4] : [0.85, 0.55, 1.4], a0: 1, a1: 0, add: 0.4}); }
      fx.flashLight({x, z}, '#7fb0ff', 24, 0.25, 1.5); fx.stage.kick(0.15);
    });
  },
  // LIQUIDITY DRAIN: a whirlpool opens in the ground: a vortex winding in to a dark mouth, coins circling down into it faster the
  // nearer they get (a fixed set of coins, moved by hand and put back at the rim: nothing made while it runs), a pale spray on the rim
  liquiditydrain(fx, e) {
    const {x, z, r} = e, dur = e.dur || 2.5, COINS = 16;
    const sw = fx.dc.emit({kind: D.SWIRL, x, z, r: 0.3, hold: true, c: [0.03, 0.09, 0.16], c2: [0.3, 0.8, 1.3], q: 1.6, a: 0});
    const mouth = fx.dc.emit({kind: D.STAIN, x, z, r: 0.2, hold: true, c: [0.01, 0.025, 0.05], c2: [0.05, 0.25, 0.4], a: 0});
    const coins = []; for (let i = 0; i < COINS; i++) coins.push({p: fx.sp.emit({kind: S.ICON, cell: 19, x, y: 0.25, z, life: dur, w: 0.36, c: [1, 1, 1], a0: 0, a1: 0, add: 0, vr: rnd(-5, 5)}), a: rnd(0, TAU), d: r * (0.25 + 0.75 * i / COINS)});
    let last = 0;
    run(fx, dur, (k, age) => {
      const dt = age - last, grow = 1 - Math.max(0, 1 - age / 0.35) ** 3, fade = k > 0.88 ? (1 - k) / 0.12 : 1; last = age;
      sw.r = r * 1.08 * grow; sw.a = 0.95 * grow * fade; mouth.r = r * 0.42 * grow; mouth.a = 0.95 * grow * fade;
      for (const c of coins) { c.d -= dt * (0.7 + r * 0.9 / Math.max(0.5, c.d)); c.a += dt * (1.4 + 7 / Math.max(0.5, c.d)); if (c.d < 0.3) { c.d = r * rnd(0.85, 1.05); c.a = rnd(0, TAU); }
        const p = c.p, in_ = Math.min(1, c.d / (r * 0.3)); p.x = x + Math.cos(c.a) * c.d; p.z = z + Math.sin(c.a) * c.d; p.y = 0.08 + in_ * 0.3; p.w0 = p.w1 = 0.14 + in_ * 0.22; p.a0 = p.a1 = grow * fade; }
      if (Math.random() < 0.3) { const a = rnd(0, TAU); fx.sp.emit({kind: S.WISP, x: x + Math.cos(a) * r * 0.9, y: 0.25, z: z + Math.sin(a) * r * 0.9, curl: 2.6, cx: x, cz: z, life: 0.6, w0: 0.6, w1: 1.1, c: [0.4, 0.9, 1.3], a0: 0.32 * fade, a1: 0, add: 0.8}); }
    }, () => { sw.dead = mouth.dead = true; for (const c of coins) c.p.life = 0; });
    fx.stage.kick(0.15);
  },
  // MARKET CRASH: the floor gives way: the ground splits with red glowing deep in it, a quake every second (the sim's ticks) throwing
  // dust and clods out and shaking the view, red candles sinking into the cracks between
  marketcrash(fx, e) {
    const {x, z, r} = e, dur = e.dur || 3;
    const crack = fx.dc.emit({kind: D.CRACK, x, z, r: r * 1.2, hold: true, c: [0.04, 0.03, 0.03], c2: [1.2, 0.1, 0.1], q: 0, a: 0});
    let beat = -1, bang = 0;
    run(fx, dur, (k, age) => {
      if (Math.floor(age) !== beat) { beat = Math.floor(age); bang = age;
        fx.front({x, z}, r, 14, 0.5, {kind: S.SMOKE, y: 0.18, w0: 0.5, w1: 1.2, ease: 1, c: [0.5, 0.44, 0.42], a0: 0.65, a1: 0, add: 0}, 0.25);
        fx.burst({x, y: 0, z}, {n: 10, c: [0.34, 0.27, 0.24], s: 0.36, sp: r * 1.3, up: 5, life: 0.8, g: 13, cell: 21, add: false, y: 0.15, floor: 0.05, bounce: 0.25});
        const [dx, dz] = disc(r, 0.7); fx.dc.emit({kind: D.CRACK, x: x + dx, z: z + dz, r: 1.1, life: 1.6, c: [0.05, 0.04, 0.04], c2: [1.3, 0.12, 0.12], q0: 1, q1: 0, a0: 0.85, a1: 0});
        fx.stage.kick(0.28); }
      crack.a = Math.min(1, age * 6) * (k > 0.88 ? (1 - k) / 0.12 : 1); crack.q = 0.35 + 0.65 * Math.max(0, 1 - (age - bang) / 0.5);
      if (Math.random() < 0.14) { const [dx, dz] = disc(r, 0.85); fx.sp.emit({kind: S.ICON, cell: 17, x: x + dx, y: rnd(0.5, 0.9), z: z + dz, vy: -rnd(0.5, 1), life: 0.8, w: 0.36, asp: 1.3, rot: rnd(-0.3, 0.3), c: [1, 0.15, 0.2], a0: 1, a1: 0, fin: 0.1, add: 0.2}); }
      if (Math.random() < 0.16) { const [dx, dz] = disc(r, 0.9); fx.sp.emit({kind: S.SMOKE, x: x + dx, y: 0.2, z: z + dz, vy: rnd(0.3, 0.7), life: 0.9, w0: 0.5, w1: 1.1, ease: 1, c: [0.45, 0.4, 0.38], a0: 0.4, a1: 0, fin: 0.2, add: 0}); }
    }, () => fx.release(crack, 0.5));
  },
  // PANIC SELL: the alarm: a red light closing in, then the flash ("SELL!" is the overlay's): red arrows bursting out of the middle the
  // way they all run, headlines flying, dust thrown out (those it scares sweat on their own: units.js)
  panicsell(fx, e) {
    const {x, z, r} = e, d = e.delay || 0.2;
    fx.dc.emit({kind: D.GLOW, x, z, r0: r * 1.05, r1: r * 0.65, ease: 1, life: d, c: [1.3, 0.12, 0.15], a0: 0.2, a1: 0.9, add: 1});
    later(fx, d, () => {
      fx.sp.emit({kind: S.FLARE, x, y: 1, z, life: 0.16, w0: 3.2, w1: 0.6, c: [2, 0.5, 0.45], a0: 1, a1: 0.3, add: 1, rot: 0});
      fx.dc.emit({kind: D.GLOW, x, z, r0: r * 0.7, r1: r * 1.1, ease: 1, life: 0.4, c: [1.3, 0.12, 0.15], a0: 1, a1: 0, add: 1});
      for (let i = 0; i < 12; i++) { const a = i / 12 * TAU + rnd(-0.15, 0.15), v = r * rnd(2.2, 3), ca = Math.cos(a), sa = Math.sin(a);   // (an arrow's cell points up the screen: turned to its way)
        fx.sp.emit({kind: S.ICON, cell: 16, x: x + ca * 0.4, y: rnd(0.4, 1), z: z + sa * 0.4, vx: ca * v, vz: sa * v, drag: 3, life: rnd(0.45, 0.65), w: 0.5, rot: Math.atan2(-ca, -sa), c: [1, 0.16, 0.2], a0: 1, a1: 0, add: 0.3}); }
      for (let i = 0; i < 8; i++) { const a = rnd(0, TAU), v = r * rnd(0.8, 1.8); fx.sp.emit({kind: S.ICON, cell: 18, x, y: rnd(0.5, 1.2), z, vx: Math.cos(a) * v, vy: rnd(1.5, 3.5), vz: Math.sin(a) * v, g: 5, drag: 1.5, vr: rnd(-6, 6), life: rnd(0.7, 1.1), w: 0.34, asp: 1.25, c: [1, 1, 1], a0: 1, a1: 0, add: 0, floor: 0.05}); }
      fx.front({x, z}, r, 14, 0.45, {kind: S.SMOKE, y: 0.18, w0: 0.5, w1: 1.1, ease: 1, c: [0.6, 0.52, 0.5], a0: 0.55, a1: 0, add: 0}, 0.2);
      fx.flashLight({x, z}, '#ff4050', 28, 0.25, 1.6); fx.stage.kick(0.3);
    });
  },
  // DIAMOND HANDS: a great cut diamond drops into the area and bursts: crystal shards thrown out, ice-white light washing over the
  // ground, gems twinkling down (my troops keep a shine of it for as long as it holds: units.js)
  diamondhands(fx, e) {
    const {x, z, r} = e, t = 0.2;
    place(fx, 'diamond', t + 0.1, (k, age, o) => {
      const q = Math.min(1, age / t); o.position.set(x, 0.9 + 6 * (1 - q * q), z); o.rotation.y = age * 7;
      if (age >= t && !o.userData.hit) { o.userData.hit = true; o.visible = false;
        for (let i = 0; i < 22; i++) { const a = rnd(0, TAU), v = rnd(2.5, 6);
          fx.sp.emit({kind: S.SHARD, x, y: 1, z, vx: Math.cos(a) * v, vy: rnd(1.5, 5), vz: Math.sin(a) * v, g: 13, drag: 0.7, vr: rnd(-8, 8), life: rnd(0.5, 0.9), w: rnd(0.16, 0.3), asp: 1.6, c: [0.8, 1.05, 1.4], a0: 1, a1: 0, add: 0.5, floor: 0.06, bounce: 0.3}); }
        for (let i = 0; i < 9; i++) { const [dx, dz] = disc(r, 0.85); fx.sp.emit({kind: S.ICON, cell: 23, x: x + dx, y: rnd(1.8, 3), z: z + dz, vy: -rnd(1.2, 2.2), g: 1.5, vr: rnd(-3, 3), life: rnd(0.8, 1.1), w: rnd(0.3, 0.42), c: [0.7, 0.93, 1.25], a0: 1, a1: 0.3, add: 0.3, floor: 0.08}); }
        fx.sp.emit({kind: S.FLARE, x, y: 1, z, life: 0.2, w0: 3.6, w1: 0.8, c: [1.4, 1.8, 2], a0: 1, a1: 0.3, add: 1, rot: 0});
        fx.dc.emit({kind: D.GLOW, x, z, r0: r * 0.5, r1: r * 1.1, ease: 1, life: 0.8, c: [0.5, 0.9, 1.4], a0: 1, a1: 0, add: 1});
        fx.front({x, z}, r, 12, 0.5, {kind: S.WISP, y: 0.4, w0: 0.5, w1: 1, c: [0.65, 1, 1.5], a0: 0.8, a1: 0, add: 1}, 0.2);
        fx.flashLight({x, z}, '#9fe0ff', 34, 0.3, 2); fx.stage.kick(0.3); }
    });
  },
};
export const castSpell = (fx, e) => { const f = SPELLS[e.card]; if (f) { f(fx, e); return true; } return false; };
