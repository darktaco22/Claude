// THE WORLD AROUND THE COURT: real 3D terraces, built here from an arena's entry in worlds.js. The ground is a Voronoi diagram:
// each cell is raised into a chunky block, with its height from a bowl around the court, so seen from the battle camera it gives
// the stepped, cracked rock of the arena's reference picture at the game's own angle (nothing painted, so nothing can disagree
// with it). The light is baked, per vertex, from the sun and from hundreds of small lights (the liquid, its seams, crystals,
// lanterns) that no phone could afford live; what's baked from a glowing source goes in its own attribute and flickers in the
// shader. All of it merges into a few big meshes with a cheap shader, so the cost is one texture read a pixel. Only what this
// screen's shape can see gets built (a phone shows a fifth of a PC's scenery), which is where a phone's budget comes from.
import * as THREE from 'three';
import {cloneGLB, loadGLB} from './assets.js';
import {RIM, smooth, mix, hash, fbm, vnoise, lin, mix3, mul3, STRIDE, Mesher, lump, crystal, timber, MASS} from './worldkit.js';
import {PROPS} from './worldprops.js';
Object.assign(MASS, PROPS);

const LIQ_Y = -0.42, BED_Y = -0.75, FLOOR_Y = -0.015;
export {RIM};
const COURT = {x0: 0, x1: 18, z0: 0, z1: 32};
// ---------- the shape of the land
function makeField(W) {
  const s = W.seed || 1, T = W.terrain, R = W.river || {};
  const beyond = x => Math.max(0, RIM.x0 - x) + Math.max(0, x - RIM.x1);
  const riverZ = x => { if (R.straight) return 16; const k = smooth(0, 9, beyond(x)); return 16 + k * ((R.bend ?? 2) * Math.sin(x * 0.14 + 1.1) + (R.bend ?? 2) * 0.35 * Math.sin(x * 0.33)); };
  const riverW = x => R.straight ? 1 : 1 + smooth(0, 6, beyond(x)) * ((R.wide ?? 1) + 0.4 * Math.sin(x * 0.42 + 2));
  const riverD = (x, z) => Math.abs(z - riverZ(x)) - riverW(x);
  const plateaus = W.plateaus || [], stages = W.stages || [], Fl = W.floor;
  const stageAt = (x, z) => { for (const P of stages) if (Math.abs(x - P.x) < P.w && Math.abs(z - P.z) < P.d) return P; return null; };
  const hill = (x, z) => {
    const d = Math.hypot(Math.max(RIM.x0 - x, 0, x - RIM.x1), Math.max(RIM.z0 - z, 0, z - RIM.z1));
    let h = T.flat ? 0 : (T.base + d * T.rise + (fbm(x * 0.075, z * 0.075, s) - 0.5) * T.rough) * smooth(0, T.blend ?? 3, d);
    for (const P of plateaus) { const k = Math.hypot(x - P.x, z - P.z); if (k < P.r + (P.fall ?? 3.4)) h = mix(P.h, h, smooth(P.r, P.r + (P.fall ?? 3.4), k)); }
    if (z > RIM.z1) h = Math.min(h, (z - RIM.z1) * T.near);
    if (x > RIM.x0 - 0.5 && x < RIM.x1 + 0.5 && z > RIM.z1) h = Math.min(h, 0.02);
    return Math.max(0, h);
  };
  const macro = Fl ? hill : (x, z) => {
    const d = Math.hypot(Math.max(RIM.x0 - x, 0, x - RIM.x1), Math.max(RIM.z0 - z, 0, z - RIM.z1));
    let h = T.base + d * T.rise + (fbm(x * 0.075, z * 0.075, s) - 0.5) * T.rough;
    h = Math.min(h, T.max);
    if (z > RIM.z1) h = Math.min(h, 0.3 + (z - RIM.z1) * T.near);                 // (towards the camera it must not stand in front of the court)
    if (x > RIM.x0 - 0.5 && x < RIM.x1 + 0.5 && z > RIM.z1) h = Math.min(h, 0.16);    // (the hub looks down this lane at my Battlestation)
    h = Math.min(h, 0.14 + Math.max(0, riverD(x, z)) * T.bank);
    return Math.max(0.1, h);
  };
  // the streams: walked once, downhill, so a run of the channel stays level and then drops: that drop is a fall
  const streams = (W.streams || []).map(pts => {
    const P = [], step = T.step;
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, az] = pts[i], [bx, bz] = pts[i + 1], [px, pz] = pts[Math.max(0, i - 1)], [qx, qz] = pts[Math.min(pts.length - 1, i + 2)], n = Math.ceil(Math.hypot(bx - ax, bz - az) / 0.55);
      for (let k = 0; k < n; k++) {
        const t = k / n, t2 = t * t, t3 = t2 * t;   // (Catmull-Rom)
        P.push({x: 0.5 * (2 * ax + (bx - px) * t + (2 * px - 5 * ax + 4 * bx - qx) * t2 + (3 * ax - px - 3 * bx + qx) * t3), z: 0.5 * (2 * az + (bz - pz) * t + (2 * pz - 5 * az + 4 * bz - qz) * t2 + (3 * az - pz - 3 * bz + qz) * t3)});
      }
    }
    P.push({x: pts.at(-1)[0], z: pts.at(-1)[1]});
    let y = Infinity;
    for (const p of P) { const h = macro(p.x, p.z) - 0.15; if (h < y - step * 0.7) y = Math.max(LIQ_Y, Math.round(h / step) * step); p.y = Math.min(y, Math.max(LIQ_Y, h)); y = p.y; }
    P.at(-1).y = LIQ_Y; return P;
  });
  const near = (x, z) => { let best = 1e9, at = null; for (const S of streams) for (const p of S) { const d = (p.x - x) ** 2 + (p.z - z) ** 2; if (d < best) { best = d; at = p; } } return at ? {d: Math.sqrt(best), y: at.y} : {d: 1e9, y: 0}; };
  // paved ways through the ground: a list of {pts, w, h}
  const paths = W.paths || [], pathD = (x, z) => { let best = 1e9, at = null; for (const P of paths) for (let i = 0; i < P.pts.length - 1; i++) { const [ax, az] = P.pts[i], [bx, bz] = P.pts[i + 1], dx = bx - ax, dz = bz - az, k = Math.min(1, Math.max(0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz))), d = Math.hypot(x - ax - dx * k, z - az - dz * k) - (P.w ?? 1); if (d < best) { best = d; at = P; } } return {d: best, P: at}; };
  const inRim = (x, z) => x > RIM.x0 && x < RIM.x1 && z > RIM.z0 && z < RIM.z1;
  const inCourt = (x, z) => x > COURT.x0 && x < COURT.x1 && z > COURT.z0 && z < COURT.z1;
  // what's at a point: null (open: the court or the liquid) or the block standing there
  // the smooth ground, a height everywhere: it runs down under the liquid at the shore, and up on to a stage
  const ground = (x, z) => {
    let h = hill(x, z);
    if (streams.length) { const sn = near(x, z), w = W.streamWidth ?? 0.75; if (sn.d < w + 1.8) h = mix(sn.y - 0.3, Math.max(h, sn.y + 0.12), smooth(w * 0.72, w + 1.8, sn.d)); }
    const rd = riverD(x, z); if (rd < (T.shore ?? 1.8)) h = mix(LIQ_Y - 0.4, Math.max(h, 0.02), smooth(-0.05, T.shore ?? 1.8, rd));
    const st = stageAt(x, z); if (st) h = st.h;
    return h;
  };
  const at = (x, z) => {
    if (Fl) { if (inCourt(x, z) || riverD(x, z) < 0.15 || (streams.length && near(x, z).d < (W.streamWidth ?? 0.75) + 0.2)) return null; return {h: inRim(x, z) ? 0 : Math.max(0, ground(x, z)), soft: true}; }
    if (inCourt(x, z) || riverD(x, z) < 0) return null;
    if (inRim(x, z)) return {h: FLOOR_Y, cob: true, flat: true};
    if (x > RIM.x0 && x < RIM.x1 && z >= RIM.z1) return {h: 0.06, cob: true, flat: true};
    const sn = near(x, z), w = W.streamWidth ?? 0.75; if (sn.d < w) return null;
    let h = macro(x, z);
    if (paths.length) { const pa = pathD(x, z); if (pa.d < 0) return {h: pa.P.h ?? 0.1, cob: true, flat: true, path: true}; if (pa.d < 2.4) h = mix(pa.P.h ?? 0.1, h, smooth(0, 2.4, pa.d)); }
    if (sn.d < w + 1.1) h = Math.max(h, sn.y + 0.45);
    for (const P of plateaus) { const d = Math.hypot(x - P.x, z - P.z); if (d < P.r) return {h: P.h, cob: true, flat: true}; if (d < P.r + 2) h = mix(P.h + (P.lip ?? 0.5), h, smooth(P.r, P.r + 2, d)); }
    return {h};
  };
  const hot = (x, z) => {
    if (W.seams === false) return 0;
    let k = 1 - smooth(0.2, 3.2, riverD(x, z));
    if (streams.length) k = Math.max(k, 1 - smooth(0.6, 2.6, near(x, z).d));
    const p = W.seams?.patch ?? 0.56, n = fbm(x * 0.17 + 7, z * 0.17 - 3, s + 9, 2);
    return Math.max(k, smooth(p, p + 0.1, n));
  };
  return {riverZ, riverW, riverD, macro, at, hot, streams, plateaus, inRim, inCourt, ground, pathD, stageAt};
}

// ---------- the Voronoi cells
function clip(poly, mx, mz, dx, dz, label) {
  const out = [], n = poly.length;
  for (let i = 0; i < n; i++) {
    const a = poly[i], b = poly[(i + 1) % n], da = (a.x - mx) * dx + (a.z - mz) * dz, db = (b.x - mx) * dx + (b.z - mz) * dz;
    if (da <= 0) out.push(a);
    if ((da <= 0) !== (db <= 0)) { const t = da / (da - db), p = {x: a.x + (b.x - a.x) * t, z: a.z + (b.z - a.z) * t, n: da <= 0 ? label : a.n}; out.push(p); }
  }
  return out;
}
function buildCells(W, F, R) {
  const s = W.seed || 1, g = W.cell, f = g / 2, sites = [], bins = new Map(), B = 4, key = (i, j) => i * 4096 + j, T = W.terrain, G = W.grid;
  const put = S => { sites.push(S); const k = key(Math.floor(S.x / B), Math.floor(S.z / B)); (bins.get(k) || bins.set(k, []).get(k)).push(S); };
  const rise = (c, i, j, S) => { const st = T.step, hk = Math.min(1, c.h / st); S.h = Math.max(0.03, Math.round((c.h + (hash(i, j, s + 3) - 0.5) * st * (T.jit ?? 0.95) * hk) / st) * st + (hash(i, j, s + 2) - 0.5) * st * (T.fine ?? 0.3)); };
  // a lattice instead of jittered points gives rectangles: slabs, boards, carpet, voxels (brick: every other row shifted by that much)
  if (G) for (let j = Math.floor(R.z0 / G.z); j * G.z < R.z1; j++) { const off = (j & 1) ? (G.brick ?? 0) * G.x : 0; for (let i = Math.floor(R.x0 / G.x) - 1; i * G.x + off < R.x1; i++) {
    const x = i * G.x + off + (hash(i, j, s) - 0.5) * G.x * (G.jit ?? 0.02), z = j * G.z + (hash(i, j, s + 1) - 0.5) * G.z * (G.jit ?? 0.02), c = F.at(x, z), S = {x, z, id: sites.length, ghost: !c, cob: !!c?.cob, flat: !!c?.flat, h: c ? c.h : LIQ_Y, par: (i + j) & 1};
    if (c && !c.flat) rise(c, i, j, S); else if (c) S.h = c.h + (c.h > 0 ? (hash(i, j, s + 2) - 0.5) * 0.04 : 0);
    put(S);
  } }
  else for (let j = Math.floor(R.z0 / f); j * f < R.z1; j++) for (let i = Math.floor(R.x0 / f); i * f < R.x1; i++) {
    const x0 = i * f, z0 = j * f, coarse = !(i & 1) && !(j & 1), probe = F.at(x0, z0);
    if (probe && !probe.cob && (coarse ? hash(i, j, s + 5) < 0.16 : hash(i, j, s + 6) > 0.14)) continue;   // (some big blocks, some small: an even grid reads as honeycomb)
    const sp = coarse && !probe?.cob ? g : f, x = x0 + (hash(i, j, s) - 0.5) * sp * 0.74, z = z0 + (hash(i, j, s + 1) - 0.5) * sp * 0.74, c = F.at(x, z);
    const S = {x, z, id: sites.length, ghost: !c, cob: !!c?.cob, flat: !!c?.flat, h: c ? c.h : LIQ_Y};
    if (c && !c.flat) rise(c, i, j, S);
    else if (c) S.h = c.h + (c.h > 0 ? (hash(i, j, s + 2) - 0.5) * 0.07 : 0);
    put(S);
  }
  const around = (x, z, r) => { const out = [], n = Math.ceil(r / B), bi = Math.floor(x / B), bj = Math.floor(z / B); for (let j = bj - n; j <= bj + n; j++) for (let i = bi - n; i <= bi + n; i++) { const L = bins.get(key(i, j)); if (L) out.push(...L); } return out; };
  for (const S of sites) {
    if (S.ghost) continue;
    const N = around(S.x, S.z, G ? Math.max(G.x, G.z) * 2.5 : 9).filter(q => q !== S).map(q => ({q, d: (q.x - S.x) ** 2 + (q.z - S.z) ** 2})).sort((a, b) => a.d - b.d);
    if (G?.brick) { const a = {x: S.x - G.x / 2, z: S.z - G.z / 2}, b = {x: S.x - G.x / 2, z: S.z + G.z / 2}, c = {x: S.x + G.x / 2, z: S.z + G.z / 2}, d = {x: S.x + G.x / 2, z: S.z - G.z / 2}; S.rect = [a, b, c, d]; }
    const L = 8; let P = S.rect ? S.rect.map(v => ({...v, n: -3})) : [{x: S.x - L, z: S.z - L, n: -1}, {x: S.x - L, z: S.z + L, n: -1}, {x: S.x + L, z: S.z + L, n: -1}, {x: S.x + L, z: S.z - L, n: -1}], far = L * 1.5;
    if (!S.rect) for (const {q, d} of N) {
      if (Math.sqrt(d) / 2 > far) break;
      P = clip(P, (S.x + q.x) / 2, (S.z + q.z) / 2, q.x - S.x, q.z - S.z, q.id); if (P.length < 3) break;
      far = 0; for (const v of P) far = Math.max(far, Math.hypot(v.x - S.x, v.z - S.z));
    }
    if (P.length < 3) continue;
    // nothing but the rim's cobbles comes near the court, and nothing at all on it
    const rect = S.cob && F.inRim(S.x, S.z) ? COURT : RIM, ox = Math.max(rect.x0 - S.x, 0, S.x - rect.x1), oz = Math.max(rect.z0 - S.z, 0, S.z - rect.z1);
    if (ox >= oz && ox > 0) P = S.x < rect.x0 ? clip(P, rect.x0, 0, 1, 0, -2) : clip(P, rect.x1, 0, -1, 0, -2);
    else if (oz > 0) P = S.z < rect.z0 ? clip(P, 0, rect.z0, 0, 1, -2) : clip(P, 0, rect.z1, 0, -1, -2);
    if (P.length < 3) continue;
    let cx = 0, cz = 0, r = 0; for (const v of P) { cx += v.x; cz += v.z; } cx /= P.length; cz /= P.length; for (const v of P) r += Math.hypot(v.x - cx, v.z - cz); r /= P.length;
    if (r < 0.14) continue;
    Object.assign(S, {poly: P, cx, cz, r});
    if (S.rect) for (let i = 0; i < P.length; i++) { if (P[i].n !== -3) continue; const a = P[i], b = P[(i + 1) % P.length], mx = (a.x + b.x) / 2, mz = (a.z + b.z) / 2, ox = mx + Math.sign(mx - cx) * (Math.abs(mx - cx) > Math.abs(mz - cz) ? 0.2 : 0), oz = mz + Math.sign(mz - cz) * (Math.abs(mz - cz) >= Math.abs(mx - cx) ? 0.2 : 0); let best = 1e9, id = -1; for (const {q} of N) { const e = (q.x - ox) ** 2 + (q.z - oz) ** 2; if (e < best) { best = e; id = q.id; } } a.n = id; }
  }
  const heightAt = (x, z) => { let best = 1e9, h = 0; for (const q of around(x, z, 5)) { const d = (q.x - x) ** 2 + (q.z - z) ** 2; if (d < best && !q.ghost) { best = d; h = q.h; } } return Math.max(0, h); };
  return {sites, heightAt, around};
}

// ---------- everything, as flat arrays: no GPU objects here, so it could move to a worker
function generate(W, R) {
  const F = makeField(W), Fl = W.floor, C = Fl ? {sites: [], heightAt: (x, z) => F.inRim(x, z) ? 0 : Math.max(0, F.ground(x, z))} : buildCells(W, F, R), S = W.seed || 1, H = C.heightAt;
  const liq = W.liquid, light = lin(liq.light), crystalsC = W.crystal ? {deep: lin(W.crystal.deep), glow: lin(W.crystal.glow), body: lin(W.crystal.body || '#0a2030'), gain: W.crystal.gain ?? 1.6} : null;
  const lights = [], halos = [], spots = {crystal: [], fall: [], seam: []}, addL = (x, y, z, c, rad, k, f = 1) => lights.push({x, y, z, r: c[0], g: c[1], b: c[2], rad, r2: rad * rad, k, f});
  // the liquid lights everything near it
  for (let x = R.x0; x < R.x1; x += 1.7) { const z = F.riverZ(x), w = F.riverW(x); for (const q of [-0.55, 0.55]) addL(x, 0.1, z + q * w, light, liq.reach ?? 6.5, liq.lightK ?? 0.95, liq.field ?? 0.3); }
  for (const P of F.streams) for (let i = 0; i < P.length; i += 3) addL(P[i].x, P[i].y + 0.45, P[i].z, light, 4.6, liq.streamK ?? 0.85);
  // falls: where a stream drops, it shines harder and throws sparks
  for (const P of F.streams) for (let i = 1; i < P.length - 1; i++) if (P[i - 1].y - P[i].y > 0.3 && P[i].x > R.x0 && P[i].x < R.x1) { spots.fall.push([P[i].x, P[i].y + 0.1, P[i].z]); addL(P[i].x, P[i].y + 0.7, P[i].z, light, 4.2, liq.streamK ?? 0.9); }
  // crystals: a few spots from the arena's own list, the rest on open rock near the court, kept apart
  // (what the scenery can stand on: the cells, or on smooth ground a loose lattice of spots)
  const live = C.sites.filter(q => q.poly), spotsOn = [...live];
  if (Fl) { const g = 1.5; let id = 0; for (let j = Math.floor(R.z0 / g); j * g < R.z1; j++) for (let i = Math.floor(R.x0 / g); i * g < R.x1; i++) { const x = (i + (hash(i, j, S) - 0.5) * 0.7) * g, z = (j + (hash(i, j, S + 1) - 0.5) * 0.7) * g, c = F.at(x, z); if (!c || F.inRim(x, z) || (W.paths && F.pathD(x, z).d < 0.3) || F.stageAt(x, z)) continue; spotsOn.push({id: id++, x, z, cx: x, cz: z, h: c.h, r: 0.75, cob: false}); } }
  const rocks = spotsOn.filter(q => !q.ghost && !q.cob && (Fl || q.h > 0.3)), crystals = [];
  if (crystalsC) {
    for (const [x, z, s] of W.crystal.spots || []) crystals.push({x, z, s, y: H(x, z)});
    const want = W.crystal.n ?? 30;
    for (let k = 0; k < 400 && crystals.length < want; k++) {
      const q = rocks[Math.floor(hash(k, S, 31) * rocks.length)]; if (!q) break;
      const d = Math.hypot(Math.max(RIM.x0 - q.x, 0, q.x - RIM.x1), Math.max(RIM.z0 - q.z, 0, q.z - RIM.z1));
      if (hash(k, S, 37) > (d < 5 ? 1 : d < 14 ? 0.7 : 0.35) || crystals.some(p => (p.x - q.cx) ** 2 + (p.z - q.cz) ** 2 < 22)) continue;
      crystals.push({x: q.cx, z: q.cz, y: q.h, s: (0.8 + hash(k, S, 41) * 0.6) * (d > 10 ? 1.35 : 1) * (W.crystal.size ?? 1)});
    }
    const halo = lin(W.crystal.glow);
    for (const c of crystals) { addL(c.x, c.y + c.s * 1.2, c.z, halo, 5.2 * c.s + 2.2, 1.25); halos.push({x: c.x, y: c.y + c.s * 0.8, z: c.z, s: c.s * 4.4, c: halo, a: 0.55, ph: c.x * 3.1}); spots.crystal.push([c.x, c.y + c.s, c.z]); }
  }
  // the timber kit's lanterns are lights as well, so walk the kit once before baking
  const lampC = lin(W.lamp?.c || '#ffb050');
  for (const D of W.dress || []) {
    if (D.k !== 'gallows') continue;
    const y0 = D.y ?? H(D.x, D.z), ry = D.ry || 0, reach = (D.reach ?? 1.5) - 0.15, s = D.s || 1, lx = D.x + reach * Math.cos(ry) * s, lz = D.z - reach * Math.sin(ry) * s, ly = y0 + 2.28 * s;
    addL(lx, ly, lz, lampC, 6, 1.6); halos.push({x: lx, y: ly, z: lz, s: 3.6 * s, c: lampC, a: 1, ph: lx * 2.3, lamp: 1});
  }
  for (const [x, y, z, rad = 5, k = 1.4] of W.lamps || []) { const yy = y ?? H(x, z) + 1.2; addL(x, yy, z, lampC, rad, k); halos.push({x, y: yy, z, s: 2.4, c: lampC, a: 0.7, ph: x * 2.3, lamp: 1}); }
  for (const [x, y, z, hex, rad = 7, k = 1.5, hs = 4] of W.glows || []) { const c = lin(hex), yy = y ?? H(x, z) + 1.5; addL(x, yy, z, c, rad, k); if (hs) halos.push({x, y: yy, z, s: hs, c, a: 0.6, ph: x * 1.7}); }
  // the rest of the place: from worlds.js `masses`, some on spots given by hand, the most on cells that fit
  const stand = [], blobs = [];
  const placeAt = (Q, x, y, z, s, seed, ry) => { if (!Q.pts && !Q.from && R.hw && Math.abs(x - 9) > R.hw(z) + s) return; const p = {x, y, z, s, seed}; stand.push({Q: ry === undefined ? Q : {...Q, ry}, p}); if (Q.pts && Q.lay) { const P3 = Q.pts; for (let i = 0; i < P3.length - 1; i++) { const a = P3[i], b = P3[i + 1], ly = a.length === 3 ? a[1] : 0; if (ly > 1) continue; const ax = a[0], az = a[a.length - 1], bx = b[0], bz = b[b.length - 1], l = Math.hypot(bx - ax, bz - az), n = Math.ceil(l / (Q.lay * 0.9)); for (let k = 0; k <= n; k++) blobs.push({x: ax + (bx - ax) * k / n, y: 0.03, z: az + (bz - az) * k / n, r: Q.lay * 1.5, k: 0.42}); } } if (Q.shade !== 0) blobs.push({x, y: y + 0.03, z, r: (Q.shade ?? 1.3) * s, k: Q.shadeK ?? 0.5}); if (Q.light) { const [hex, rad = 5, k = 1.3, hs = 2.4, up = 1.5] = Q.light, c = lin(hex), yy = y + up * s; addL(x, yy, z, c, rad, k, 0.6); if (hs) halos.push({x, y: yy, z, s: hs * s, c, a: Q.halo ?? 0.8, ph: x * 2.3 + z, lamp: Q.flame ? 1 : 0}); } };
  // what stands where: what's scattered keeps out of what was placed, and out of what was scattered before it (rugs, craters and the like can be walked on)
  const OPEN = {roundrug: 1, crater: 1, neon: 1, garland: 1, ring: 0, rail: 1, post: 1}, room = new Map(), rk = (x, z) => Math.floor(x / 5) * 4096 + Math.floor(z / 5), take = (x, z, r) => { const k = rk(x, z); (room.get(k) || room.set(k, []).get(k)).push([x, z, r]); }, free = (x, z, r) => { const c0 = Math.floor(x / 5), c1 = Math.floor(z / 5); for (let i = c0 - 1; i <= c0 + 1; i++) for (let j = c1 - 1; j <= c1 + 1; j++) for (const o of room.get(i * 4096 + j) || []) if ((o[0] - x) ** 2 + (o[1] - z) ** 2 < (o[2] + r) ** 2) return false; return true; };
  for (const Q of W.masses || []) if (!OPEN[Q.k] && !Q.pts && !Q.from) for (const [x, z, s = 1] of Q.at || []) take(x, z, s * (Q.foot ?? 0.9));
  (W.masses || []).forEach((Q, qi) => {
    for (const [x, z, s = 1, y, ry] of Q.at || []) if (Q.from || (x > R.x0 && x < R.x1 && z > R.z0 && z < R.z1)) placeAt(Q, x, y ?? H(x, z), z, s, Math.round(x * 13 + z * 7 + qi * 101), ry);
    if (!Q.per) return;
    const [d0, d1] = Q.d || [0.5, 99], [s0, s1] = Q.s || [1, 1], on = Q.on || 'rock', gap2 = (Q.gap ?? 0) ** 2, mine = [], tall = Q.h ?? 2, seed = qi * 977 + S;
    for (const q of spotsOn) {
      if (q.ghost || hash(q.id, seed, 111) > Q.per) continue;
      if (on === 'rock' ? q.cob : on === 'cob' ? !q.cob || q.h < 0.15 : on === 'flat' ? !q.cob : false) continue;
      const d = Math.hypot(Math.max(RIM.x0 - q.cx, 0, q.cx - RIM.x1), Math.max(RIM.z0 - q.cz, 0, q.cz - RIM.z1)); if (d < d0 || d > d1) continue;
      if (d > 16 && hash(q.id, seed, 119) < Math.min(0.6, (d - 16) * 0.05)) continue;   // (thinner far from the court: nobody reads a bush that far off, and each triangle costs 144 bytes)
      const s = mix(s0, s1, hash(q.id, seed, 113)), a = hash(q.id, seed, 115) * 6.283, o = q.r * 0.3 * hash(q.id, seed, 117), x = q.cx + Math.cos(a) * o, z = q.cz + Math.sin(a) * o;
      if (F.riverD(x, z) < (Q.riverGap ?? 0.5) * s) continue;
      if (z > RIM.z1 && tall * s > (z - RIM.z1) * 1.5) continue;                     // (near the camera, nothing tall enough to cover the court)
      if (gap2 && mine.some(m => (m[0] - x) ** 2 + (m[1] - z) ** 2 < gap2)) continue;
      if (!OPEN[Q.k] && !free(x, z, s * (Q.foot ?? 0.7))) continue;
      if (!OPEN[Q.k]) take(x, z, s * (Q.foot ?? 0.7));
      mine.push([x, z]); placeAt(Q, x, q.h + (Q.up ?? 0), z, s, q.id * 3 + qi);
    }
  });
  // the small stuff, by the hundred: pebbles, flowers, litter, on a jittered lattice of its own
  (W.clutter || []).forEach((Q, qi) => {
    const g = 1 / Math.sqrt(Q.per), seed = qi * 733 + S + 9, [d0, d1] = Q.d || [0.2, 46], [s0, s1] = Q.s || [0.2, 0.3], x0 = Q.x0 ?? -1e9;
    for (let j = Math.floor(R.z0 / g); j * g < R.z1; j++) for (let i = Math.floor(R.x0 / g); i * g < R.x1; i++) {
      const x = (i + hash(i, j, seed)) * g, z = (j + hash(i, j, seed + 1)) * g; if (x < x0 || z < (Q.z0 ?? -6)) continue;
      const d = Math.hypot(Math.max(RIM.x0 - x, 0, x - RIM.x1), Math.max(RIM.z0 - z, 0, z - RIM.z1)); if (d < d0 || d > d1) continue;
      if (d > 12 && hash(i, j, seed + 3) < Math.min(0.75, (d - 12) * 0.06)) continue;
      if (F.riverD(x, z) < (Q.riverGap ?? 0.35)) continue;
      if (Q.mask && fbm(x * (Q.mask[0]), z * (Q.mask[0]), seed, 2) < Q.mask[1]) continue;
      if (F.stageAt?.(x, z) || (W.paths && !Q.onPath && F.pathD(x, z).d < 0.2) || (Q.pathOnly && !(W.paths && F.pathD(x, z).d < 0.55))) continue;
      if (!F.at(x, z)) continue;
      placeAt(Q, x, H(x, z) + (Q.up ?? 0), z, mix(s0, s1, hash(i, j, seed + 2)), i * 31 + j * 17 + qi);
    }
  });
  // a string of bulbs round the court's rim
  const bulbs = [];
  if (W.bulbs) {
    const B = W.bulbs, c = lin(B.c), st = B.step ?? 2.2, y = B.y ?? 0.16, X0 = RIM.x0 + 0.22, X1 = RIM.x1 - 0.22, Z0 = RIM.z0 + 0.22, Z1 = RIM.z1 - 0.22, add = (x, z) => { if (Math.abs(z - 16) < 1.6) return; bulbs.push([x, y, z]); addL(x, y + 0.4, z, c, 2.4, 0.9, 0.5); halos.push({x, y: y + 0.08, z, s: B.s ?? 1.5, c, a: B.a ?? 0.9, ph: x + z * 2, lamp: 1}); };
    for (let x = X0; x <= X1; x += st) { add(x, Z0); add(x, Z1); } for (let z = Z0 + st; z < Z1; z += st) { add(X0, z); add(X1, z); }
  }
  // the seams: walk the cells' borders once to find which ones shine, and let some of them light their surroundings
  const P = W.rock, palC = (P.pal || []).map(lin), chkA = P.checker && lin(P.checker[0]), chkB = P.checker && lin(P.checker[1]), altT = P.alt && lin(P.alt.top), altW = P.alt && lin(P.alt.wall), altE = P.alt && lin(P.alt.edge || P.alt.top), top = lin(P.top), top2 = lin(P.top2 || P.top), wall = lin(P.wall), low = lin(P.low), edge = lin(P.edge), cobT = lin((W.cob || P).top), cobW = lin((W.cob || P).wall), seamC = mul3(lin(W.seams?.c || liq.light), W.seams?.gain ?? 2.6), vary = P.vary ?? 0.14;
  for (const q of live) { q.hotE = q.poly.map((v, i) => { const b = q.poly[(i + 1) % q.poly.length], mx = (v.x + b.x) / 2, mz = (v.z + b.z) / 2; return q.flat ? 0 : F.hot(mx, mz); }); }
  for (const q of live) q.poly.forEach((v, i) => { if (q.hotE[i] > 0.7 && !q.flat && hash(q.id, i, 51) < 0.2) addL(v.x, Math.max(0.2, q.h - 0.2), v.z, light, 2.8, 0.75); if (q.hotE[i] > 0.6 && hash(q.id, i, 53) < 0.08) spots.seam.push([v.x, q.h, v.z]); });
  const M = new Mesher(W, lights);
  const liqH = i => (i < 0 ? 0 : C.sites[i].poly || C.sites[i].ghost ? C.sites[i].h : 0);
  // ---------- the blocks
  for (const q of live) {
    const {poly, cx, cz, r} = q, n = poly.length, id = q.id, ht = Math.max(q.h, FLOOR_Y); M.at(cx, cz);
    const flatLow = q.flat && q.h < 0.05, gap = flatLow ? 0.035 : q.cob ? 0.05 : (W.gap ?? 0.09) * (1 + (q.hotE.reduce((a, b) => a + b, 0) / n) * 0.8), c = flatLow ? Math.min(0.1, r * 0.2) : q.cob ? Math.min(0.14, r * 0.2) : Math.min(W.chamfer ?? 0.34, r * 0.24);
    const pf = q.flat ? 0 : W.puff ?? 0, soft = (v, ny) => { if (pf) { const dx = (v.x - cx) / r, dz = (v.z - cz) / r, l = Math.hypot(dx, ny, dz); v.n = [dx / l, ny / l, dz / l]; } return v; }; const k = v => Math.max(0.15, (r - v) / r), scale = (v, m) => ({x: cx + (v.x - cx) * m, z: cz + (v.z - cz) * m});
    const tint = 1 + (hash(id, S, 61) - 0.5) * 2 * vary, second = !q.cob && P.alt && fbm(cx * (P.alt.n ?? 0.1), cz * (P.alt.n ?? 0.1), S + 21, 2) > (P.alt.at ?? 0.55) ? P.alt : null, tc = q.cob ? cobT : second ? altT : P.checker && !q.flat ? (q.par ? chkA : chkB) : P.pal ? palC[Math.floor(hash(id, S, 63) * palC.length)] : mix3(top, top2, hash(id, S, 63)), tl = q.cob ? 0.03 : W.tilt ?? 0.16, tiltX = (hash(id, S, 65) - 0.5) * tl, tiltZ = (hash(id, S, 67) - 0.5) * tl, uo = hash(id, S, 69) * 5;
    const tY = v => ht + (v.x - cx) * tiltX + (v.z - cz) * tiltZ;
    const wallC = q.cob ? cobW : second ? altW : wall, rimC = q.cob ? mix3(cobT, cobW, 0.25) : second ? altE : edge;
    // a taller neighbour darkens this top where they meet
    const aoEdge = poly.map((v, i) => { const hn = liqH(v.n); return 1 - 0.62 * smooth(0, 1.8, hn - ht); }), aoV = i => Math.min(aoEdge[i], aoEdge[(i + n - 1) % n]);
    const bump = q.cob ? 0 : pf ? r * pf * 0.72 : Math.min(0.26, r * (W.bumpK ?? 0.12)), Top = [], Cha = [], Mid = [], Bot = [], Inn = [];
    for (let i = 0; i < n; i++) {
      const v = poly[i], j1 = hash(id, i, 71), j2 = hash(id, i, 73), a = scale(v, k(gap + c * (1.15 + j1 * 0.35))), b = scale(v, k(gap + c * 0.4 * j2)), m = scale(v, k(gap * (0.6 + j1 * 0.5))), o = scale(v, k(gap * 0.8));
      Top.push(soft({...a, y: tY(a) + (pf ? bump * 0.34 : (hash(id, i, 74) - 0.5) * bump * 0.9)}, 0.8)); Cha.push(soft({...b, y: tY(b) - c * (0.55 + j2 * 0.35)}, 0.22)); Mid.push(m); Bot.push(o);
      if (bump) { const ik = 0.46 + hash(id, i, 76) * 0.22, ix = cx + (a.x - cx) * ik, iz = cz + (a.z - cz) * ik; Inn.push(soft({x: ix, z: iz, y: tY({x: ix, z: iz}) + (pf ? bump * 0.8 : (hash(id, i, 78) - 0.2) * bump)}, 2.2)); }
    }
    const capC = {x: cx, y: ht + (pf ? bump : bump ? (hash(id, S, 75) + 0.15) * bump * 1.25 : (hash(id, S, 75) - 0.35) * 0.012), z: cz, a: mul3(tc, tint), n: pf ? [0, 1, 0] : undefined};
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n, ta = mul3(tc, tint), ao1 = aoV(i), ao2 = aoV(j), fj = 0.88 + hash(id, i, 77) * 0.24;
      if (bump) {
        const ib = mul3(tc, tint * 1.12);
        M.tri(capC, {...Inn[i], a: ib}, {...Inn[j], a: ib}, fj, 0.22, uo);
        M.quad({...Inn[i], a: ib}, {...Top[i], a: ta, ao: ao1 * 0.84}, {...Inn[j], a: ib}, {...Top[j], a: ta, ao: ao2 * 0.84}, 0.86 + hash(id, i, 80) * 0.26, 0.22, uo);
      } else M.tri(capC, {...Top[i], a: ta, ao: ao1}, {...Top[j], a: ta, ao: ao2}, 0.94 + hash(id, i, 77) * 0.14, 0.22, uo);
      const ec = mul3(rimC, tint), ecl = mul3(mix3(rimC, wallC, 0.55), tint);
      M.quad({...Top[i], a: ec, ao: ao1 * 0.84}, {...Cha[i], a: ecl, ao: ao1 * 0.62}, {...Top[j], a: ec, ao: ao2 * 0.84}, {...Cha[j], a: ecl, ao: ao2 * 0.62}, 0.9 + hash(id, i, 79) * 0.25, 0.22, uo);
      // the wall: only if some view can see it
      const ax = Cha[i].x, az = Cha[i].z, bx = Cha[j].x, bz = Cha[j].z, nx = az - bz, nz = bx - ax, mx = (ax + bx) / 2, mz = (az + bz) / 2;
      if (nx * (9 - mx) + nz * (48 - mz) < 0) continue;
      // a neighbour about this high leaves a crack, seen only a little way down; a lower one leaves a wall to its top. Either way the glow is a
      // thin line at the foot, not a sheet over the rock
      const hn = liqH(poly[i].n), hot = q.hotE[i], top0 = Math.min(Cha[i].y, Cha[j].y), crack = top0 - hn < 0.6, foot = crack ? top0 - (0.12 + gap * 1.5) : hn, band = Math.min(crack ? 0.09 : 0.3, (top0 - foot) * 0.6), y2 = foot + band;
      const glowS = hot > 0.02 ? mul3(seamC, hot) : null, wc = mul3(wallC, tint), wd = mul3(mix3(wallC, low, 0.45), tint), lw = mul3(low, tint), wj = 0.86 + hash(id, i, 81) * 0.28;
      const wp = (p, y, a, ao, st) => ({...p, y, a, ao, s: st, n: pf ? [(p.x - cx) / r, 0.08, (p.z - cz) / r] : undefined});
      M.quad({...Cha[i], a: wc, ao: 0.8}, wp(Mid[i], y2, wd, 0.6), {...Cha[j], a: wc, ao: 0.8}, wp(Mid[j], y2, wd, 0.6), wj, 0.22, uo);
      M.quad(wp(Mid[i], y2, wd, 0.6), wp(Mid[i], foot, lw, glowS ? 0.7 : 0.22, glowS), wp(Mid[j], y2, wd, 0.6), wp(Mid[j], foot, lw, glowS ? 0.7 : 0.22, glowS), wj, 0.22, uo);
      if (foot > BED_Y + 0.05) { const gl = glowS && [glowS[0] * 0.5, glowS[1] * 0.22, glowS[2] * 0.2]; M.quad(wp(Mid[i], foot, lw, glowS ? 0.5 : 0.2, glowS), wp(Bot[i], BED_Y, lw, 0.12, gl), wp(Mid[j], foot, lw, glowS ? 0.5 : 0.2, glowS), wp(Bot[j], BED_Y, lw, 0.12, gl), 1, 0.22, uo); }
    }
    // a loose lump here and there breaks up the skyline of the steps
    if (!q.cob && r > 0.9 && hash(id, S, 83) < (P.lumps ?? 0.45)) {
      const a = hash(id, S, 87) * 6.283, rr = r * (0.3 + 0.3 * hash(id, S, 89)), sz = r * (0.2 + hash(id, S, 91) * 0.2);
      lump(M, cx + Math.cos(a) * rr, ht + sz * 0.35, cz + Math.sin(a) * rr, sz, mul3(mix3(top, edge, 0.3), tint), mul3(wall, tint), id * 7);
    }
    if (!q.cob && !q.flat && P.rubble) for (let k = 0, n = Math.floor(P.rubble + hash(id, S, 85)); k < n; k++) {
      const a = hash(id, k, 86) * 6.283, rr = r * 0.62 * Math.sqrt(hash(id, k, 88)), sz = Math.min(0.7, r * (0.16 + hash(id, k, 90) * 0.24)), lx = cx + Math.cos(a) * rr, lz = cz + Math.sin(a) * rr, sc = hash(id, k, 92);
      lump(M, lx, ht + sz * 0.28, lz, sz, mul3(mix3(tc, edge, 0.35), 0.9 + sc * 0.3), mul3(wallC, tint), id * 13 + k, 0.72);
    }
    // stones along the court's rim
    if (q.flat && q.h < 0.05 && hash(id, S, 93) < 0.05) lump(M, cx, 0.03, cz, 0.13 + hash(id, S, 95) * 0.12, edge, wall, id);
  }
  // ---------- the banks where the court meets the liquid: dressed stone, with the glow on its face
  const bankA = lin((W.bank || P).top), bankB = lin((W.bank || P).wall), bankS = mul3(seamC, W.seams === false ? W.bankGlow ?? 0.08 : 0.85);
  for (const [zf, dir] of [[15, 1], [17, -1]]) {
    const bx1 = W.river?.straight ? R.x1 : RIM.x1 + 0.2; let x = W.river?.straight ? R.x0 : RIM.x0 - 0.2, i = 0;
    while (x < bx1) {
      const w = 1.3 + hash(i, zf, 97) * 1.3, x1 = Math.min(bx1, x + w - 0.035), zb = zf - dir * 0.16, t = 0.022 + hash(i, zf, 99) * 0.012, tc = mul3(bankA, 0.88 + hash(i, zf, 101) * 0.24), wc = mul3(bankB, 0.88 + hash(i, zf, 103) * 0.24); M.at((x + x1) / 2, zf);
      const v = (xx, y, z, a, ao, s) => ({x: xx, y, z, a, ao, s});
      if (dir > 0) {
        M.quad(v(x, t, zb, tc), v(x, t, zf, tc), v(x1, t, zb, tc), v(x1, t, zf, tc), 1, 0.3, i);
        M.quad(v(x, t, zf, wc, 1), v(x + 0.01, LIQ_Y - 0.02, zf + 0.02, wc, 0.7, bankS), v(x1, t, zf, wc, 1), v(x1 - 0.01, LIQ_Y - 0.02, zf + 0.02, wc, 0.7, bankS), 1, 0.3, i);
      } else M.quad(v(x, t, zf, tc), v(x, t, zb, tc), v(x1, t, zf, tc), v(x1, t, zb, tc), 1, 0.3, i);
      x += w; i++;
    }
  }
  // ---------- crystals and timber
  if (crystalsC) crystals.forEach((c, i) => crystal(M, c.x, c.y, c.z, c.s, i + 3, crystalsC));
  const lampBody = mul3(lampC, 3.4), iron = lin(W.wood?.iron || '#333');
  for (const D of W.dress || []) {
    const out = timber(M, D, H, W);
    for (const p of out.lamps) {
      const s = 0.13 * (D.s || 1); M.at(p[0], p[2]);
      M.beam([p[0], p[1] - s * 1.1, p[2]], [p[0], p[1] + s * 1.1, p[2]], s, s, [0, 0, 0], [1, 0, 0], lampBody);
      M.beam([p[0], p[1] + s * 1.1, p[2]], [p[0], p[1] + s * 1.6, p[2]], s * 1.2, s * 1.2, iron);
      M.beam([p[0], p[1] - s * 1.3, p[2]], [p[0], p[1] - s * 1.1, p[2]], s * 1.2, s * 1.2, iron);
    }
  }
  const spin = [];
  for (const {Q, p} of stand) {
    M.clean = !!PROPS[Q.k] && !Q.grain;
    if (!Q.spin) { MASS[Q.k]?.(M, p, Q); M.clean = false; continue; }
    // (what turns gets a mesh of its own, about its own pivot: gears, wheels, fans, with the light it was baked in)
    const MS = new Mesher(W, lights), C = MS.cur = {a: new Float32Array(STRIDE * 3 * 512), n: 0}; MS.at = () => {}; MS.clean = M.clean; M.clean = false; MASS[Q.k]?.(MS, p, Q);
    const py = p.y + (Q.pivot ?? 0) * p.s, A = C.a; for (let i = 0, n = C.n * STRIDE; i < n; i += STRIDE) { A[i] -= p.x; A[i + 1] -= py; A[i + 2] -= p.z; }
    spin.push({a: A, n: C.n, x: p.x, y: py, z: p.z, axis: Q.spin[0], speed: Q.spin[1] * (hash(p.seed, 3) < 0.5 && Q.both ? -1 : 1)}); M.count += C.n / 3;
  }
  if (bulbs.length) { const c = lin(W.bulbs.c), s = mul3(c, 2.6), wire = lin(W.bulbs.wire || '#20160c'); for (const [x, y, z] of bulbs) { M.at(x, z); M.beam([x, 0, z], [x, y, z], 0.018, 0.018, wire); M.beam([x, y, z], [x, y + 0.13, z], 0.05, 0.05, [0, 0, 0], [1, 0, 0], s); } }
  for (const P2 of W.stages || []) MASS.stage(M, P2, W);
  // ---------- the smooth ground: a sheet, with its own mesher since it has its own texture
  let floorData = null;
  if (Fl) {
    const MF = new Mesher(W, lights), g = Fl.grid ?? 1.1, tints = (Fl.tints || ['#ffffff']).map(lin), pc = W.paths?.[0]?.c ? lin(W.paths[0].c) : null, rimC = Fl.rim ? lin(Fl.rim) : null, lowC = Fl.low ? lin(Fl.low) : null, rep = Fl.rep ?? 0.125, z0 = R.z0, z1 = R.z1;
    const hAt = (x, z) => F.inRim(x, z) && F.riverD(x, z) > 0.15 ? FLOOR_Y : F.ground(x, z), col = (x, z, h) => {
      const k = tints.length > 1 ? fbm(x * (Fl.patch ?? 0.11), z * (Fl.patch ?? 0.11), S + 40, 2) * 1.5 - 0.25 : 0, a = Math.max(0, Math.min(tints.length - 1.001, k * (tints.length - 1))), i = Math.floor(a); let c = tints.length > 1 ? mix3(tints[i], tints[i + 1], a - i) : tints[0];
      if (lowC && h < (Fl.lowAt ?? 0.2)) c = mix3(lowC, c, smooth(Math.min(LIQ_Y, -0.1), Fl.lowAt ?? 0.2, h));
      if (pc) c = mix3(pc, c, smooth(-0.3, 0.45, F.pathD(x, z).d));
      if (rimC) { const d = Math.hypot(Math.max(RIM.x0 - x, 0, x - RIM.x1), Math.max(RIM.z0 - z, 0, z - RIM.z1)); c = mix3(rimC, c, smooth(0, Fl.rimFall ?? 1.1, d)); }
      return Fl.gain ? mul3(c, Fl.gain) : c;
    };
    const V = (x, z) => { const y = hAt(x, z), e = 0.5, nx = hAt(x - e, z) - hAt(x + e, z), nz = hAt(x, z - e) - hAt(x, z + e), l = Math.hypot(nx, 2 * e, nz); return {x, y, z, a: col(x, z, y), n: [nx / l, 2 * e / l, nz / l], ao: Fl.flat ? 1 : 0.72 + 0.28 * Math.min(1, 2 * e / l * 1.0)}; };
    const nI = Math.ceil((R.x1 - R.x0) / g), nJ = Math.ceil((z1 - z0) / g); let row = null;
    for (let j = 0; j <= nJ; j++) {
      const cur = []; for (let i = 0; i <= nI; i++) cur.push(V(R.x0 + i * g, z0 + j * g));
      if (row) for (let i = 0; i < nI; i++) { const a = row[i], b = cur[i], c = row[i + 1], d = cur[i + 1]; if (R.hw && Math.abs(a.x + g / 2 - 9) > R.hw(a.z) + g * 2) continue; if (F.inCourt(a.x, a.z) && F.inCourt(d.x, d.z) && F.inCourt(c.x, c.z) && F.inCourt(b.x, b.z)) continue; if (a.z > 16 && a.z < 30 && a.x > 1 && a.x < 17) continue; MF.at(a.x, a.z); MF.quad(a, b, c, d, 1, rep, 0); }
      row = cur;
    }
    floorData = [...MF.chunks.values()];
  }
  // ---------- ribbons of liquid down the streams: position, across (0..1) * width, along (tiles walked), how steep
  const rib = []; const ww = (W.streamWidth ?? 0.75) * 1.25;
  for (const P2 of F.streams) {
    let along = 0;
    for (let i = 0; i < P2.length - 1; i++) {
      const a = P2[i], b = P2[i + 1], a0 = P2[Math.max(0, i - 1)], b1 = P2[Math.min(P2.length - 1, i + 2)];
      let dx = b.x - a0.x, dz = b.z - a0.z, l = Math.hypot(dx, dz) || 1, nax = -dz / l, naz = dx / l; dx = b1.x - a.x; dz = b1.z - a.z; l = Math.hypot(dx, dz) || 1; const nbx = -dz / l, nbz = dx / l;
      const seg = Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z), st = Math.min(1, Math.abs(a.y - b.y) / 0.25), wa = ww * (0.9 + 0.2 * vnoise(i * 0.4, 3, S)), wb = ww * (0.9 + 0.2 * vnoise((i + 1) * 0.4, 3, S)), v0 = along, v1 = along + seg;
      const ya = a.y + 0.012, yb = b.y + 0.012;
      rib.push(a.x + nax * wa, ya, a.z + naz * wa, 0, v0, st, a.x - nax * wa, ya, a.z - naz * wa, wa * 2, v0, st, b.x + nbx * wb, yb, b.z + nbz * wb, 0, v1, st);
      rib.push(a.x - nax * wa, ya, a.z - naz * wa, wa * 2, v0, st, b.x - nbx * wb, yb, b.z - nbz * wb, wb * 2, v1, st, b.x + nbx * wb, yb, b.z + nbz * wb, 0, v1, st);
      along = v1;
    }
  }
  const lf = fieldTexture(R, lights, W);
  return {chunks: [...M.chunks.values()], tris: M.count, cells: live.length, ribbons: new Float32Array(rib), halos, spots, heightAt: H, lf, lights: lights.length, field: F, blobs, floor: floorData, spin};
}

// the same lights over the ground, as a small texture: whatever else stands here (the court, the kit's models, towers and units) reads
// it to pick up the place's glow. RGB is the light, stored as its square root; A is the occlusion near the walls.
function fieldTexture(R, lights, W) {
  const w = Math.min(320, Math.ceil((R.x1 - R.x0) * 3)), h = Math.min(320, Math.ceil((R.z1 - R.z0) * 3)), kx = w / (R.x1 - R.x0), kz = h / (R.z1 - R.z0), a = new Float32Array(w * h * 3);
  for (const l of lights) {
    const r = l.rad, x0 = Math.max(0, Math.floor((l.x - r - R.x0) * kx)), x1 = Math.min(w - 1, Math.ceil((l.x + r - R.x0) * kx)), z0 = Math.max(0, Math.floor((l.z - r - R.z0) * kz)), z1 = Math.min(h - 1, Math.ceil((l.z + r - R.z0) * kz));
    for (let j = z0; j <= z1; j++) for (let i = x0; i <= x1; i++) {
      const dx = (i + 0.5) / kx + R.x0 - l.x, dz = (j + 0.5) / kz + R.z0 - l.z, d2 = dx * dx + dz * dz + 0.3; if (d2 >= l.r2) continue;
      const q = 1 - d2 / l.r2, v = q * q * l.k * 0.62 * l.f, o = (j * w + i) * 3; a[o] += l.r * v; a[o + 1] += l.g * v; a[o + 2] += l.b * v;
    }
  }
  const data = new Uint8Array(w * h * 4), wallAO = W.courtAO ?? 0.34;
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    const o = (j * w + i), x = (i + 0.5) / kx + R.x0, z = (j + 0.5) / kz + R.z0;
    data[o * 4] = 255 * Math.sqrt(Math.min(1, a[o * 3] * 0.5)); data[o * 4 + 1] = 255 * Math.sqrt(Math.min(1, a[o * 3 + 1] * 0.5)); data[o * 4 + 2] = 255 * Math.sqrt(Math.min(1, a[o * 3 + 2] * 0.5));
    const de = Math.min(x - COURT.x0, COURT.x1 - x, z - COURT.z0, COURT.z1 - z);
    data[o * 4 + 3] = 255 * (1 - wallAO * (1 - smooth(-0.2, 1.8, de)) * (de < -2 ? 0 : 1));
  }
  return {data, w, h};
}

// ---------- the shaders
const WORLD_VS = `attribute vec3 aCol, aGlow; attribute vec2 aUv; attribute float aSway; uniform float uT; varying vec3 vC, vG, vW; varying vec2 vUv;
  void main(){ vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz; if (aSway > 0.) w.xz += aSway * vec2(sin(uT * 1.4 + w.x * .7 + w.z * .4), cos(uT * 1.1 + w.z * .8 - w.x * .3)); vC = aCol; vG = aGlow; vUv = aUv; gl_Position = projectionMatrix * viewMatrix * w; }`;
const WORLD_FS = `uniform sampler2D uDetail; uniform float uT, uFlick, uGrain, uCloud; varying vec3 vC, vG, vW; varying vec2 vUv;
  void main(){
    vec3 d = texture2D(uDetail, vUv).rgb, e = texture2D(uDetail, vUv * .31 + .13).rgb;
    float paint = (.62 + .76 * d.r) * (.56 + .88 * e.r) * (.74 + .52 * e.g) * (1. - .55 * d.b) * (1. - .4 * e.b);
    float gr0 = step(vUv.x, 1000.);
    vec3 c = vC * mix(1., paint, uGrain * gr0);
    if (uCloud > 0.) c *= 1. - uCloud * smoothstep(.45, .7, texture2D(uDetail, vW.xz * .012 + uT * vec2(.004, .002)).g);
    float fl = 1. + uFlick * (.2 * sin(uT * 1.9 + vW.x * .8 + vW.z * .55) + .15 * sin(uT * 3.3 - vW.x * 1.7 + vW.z * 1.1));
    c += vG * fl * mix(1., .74 + .52 * d.r, gr0);
    gl_FragColor = vec4(c, 1.);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;
const FLOOR_FS = `uniform sampler2D uMap, uDetail; uniform float uT, uFlick, uMacro; varying vec3 vC, vG, vW; varying vec2 vUv;
  void main(){
    float fl = 1. + uFlick * (.2 * sin(uT * 1.9 + vW.x * .8 + vW.z * .55) + .15 * sin(uT * 3.3 - vW.x * 1.7 + vW.z * 1.1));
    gl_FragColor = vec4((vC + vG * fl) * texture2D(uMap, vUv).rgb * mix(1., .74 + .52 * texture2D(uDetail, vW.xz * .031).g, uMacro), 1.);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;
const BLOB_VS = `attribute vec3 aAt; attribute vec2 aSz; varying vec2 vQ; varying float vK; void main(){ vQ = position.xz * 2.; vK = aSz.y; gl_Position = projectionMatrix * viewMatrix * vec4(aAt + position * aSz.x * 2., 1.); }`;
const BLOB_FS = `varying vec2 vQ; varying float vK; void main(){ float r = length(vQ); if (r > 1.) discard; float k = 1. - r; gl_FragColor = vec4(vec3(1. - vK * k * (2. - k)), 1.); }`;
const LIQ_VS = `attribute vec3 aRib; varying vec2 vP; varying float vS, vX;
  uniform float uRib;
  void main(){ vec4 w = modelMatrix * vec4(position, 1.); vP = uRib > .5 ? aRib.xy : w.xz; vS = aRib.z; vX = aRib.x; gl_Position = projectionMatrix * viewMatrix * w; }`;
const LIQ_FS = `uniform sampler2D uFlow; uniform float uT, uGain, uScale, uSpeed, uRib, uFoamK, uSoft; uniform vec2 uDir; uniform vec3 uDeep, uMid, uHot, uWhite; varying vec2 vP; varying float vS, vX;
  void main(){
    float st = uRib > .5 ? vS : 0., t = uT * uSpeed * (1. + st * 3.);
    vec2 p = vP * uScale; if (uRib > .5) p.y *= mix(1., .32, st);
    vec2 w = (texture2D(uFlow, p * .37 + uDir * t * .3).bb - .5) * .16;
    vec4 a = texture2D(uFlow, p + w - uDir * t), b = texture2D(uFlow, p * 1.71 - w * 1.4 - uDir * t * 1.6 + .37);
    float heat = a.r * .85 + b.r * .26 + (a.g - .5) * .55 + (b.g - .5) * .2 + st * .38 + .05;
    if (uSoft > 0.) heat = mix(heat, .22 + (a.g - .5) * 1.25 + (b.g - .5) * .7 + pow(a.r * b.r, 1.3) * 1.5 + st * .5, uSoft);
    float swell = .5 + .5 * sin(uT * .8 + vP.x * .35 + vP.y * .6); heat += (swell - .5) * .16;
    if (uRib > .5) heat *= mix(1., smoothstep(0., .22, min(vX, 1.)) , .4);
    vec3 c = mix(uDeep, uMid, smoothstep(.02, .36, heat));
    c = mix(c, uHot, smoothstep(.46, .76, heat));
    c = mix(c, uWhite, smoothstep(.84, 1.12, heat) * uFoamK);
    gl_FragColor = vec4(c * uGain * (1. + smoothstep(.72, 1.05, heat) * .55), 1.);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;
const HALO_VS = `attribute vec4 aPos; attribute vec4 aCol; varying vec2 vQ; varying vec3 vC; uniform float uT;
  void main(){ float p = aCol.a, f = .86 + .14 * sin(uT * (aPos.w < 0. ? 7.3 : 1.8) + p) + (aPos.w < 0. ? .08 * sin(uT * 13.1 + p * 2.) : 0.);
    vQ = position.xy; vC = aCol.rgb * f * abs(aPos.w) ; vec4 v = viewMatrix * vec4(aPos.xyz, 1.); float s = length(aCol.rgb) > 0. ? 1. : 0.; v.xy += position.xy * aSize; gl_Position = projectionMatrix * v; }`.replace('uniform float uT;', 'uniform float uT; attribute float aSize;');
const HALO_FS = `varying vec2 vQ; varying vec3 vC; void main(){ float r = length(vQ) * 2.; if (r > 1.) discard; float k = 1. - r; k = k * k * (.35 + .65 * k * k); gl_FragColor = vec4(vC * k, 1.);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

// ---------- what flies over it: [colour, size, height, speed, flaps a second, how many, wander]
const FLYERS = {bat: ['#120a18', 0.34, 7.5, 5.5, 5, 7, 1.0], bird: ['#20242c', 0.3, 8, 5, 2.6, 7, 0.45], gull: ['#f4f4f0', 0.4, 8.5, 4.5, 1.5, 5, 0.5], dove: ['#fbfbff', 0.34, 8, 4, 2.4, 5, 0.5], butterfly: ['#ffb0e8', 0.17, 4, 2.2, 7, 7, 1.3], moth: ['#d8c8a8', 0.16, 4.5, 2.4, 8, 6, 1.4], manta: ['#16324e', 0.8, 8, 2.6, 0.7, 3, 0.3], neon: ['#3ff0ff', 0.24, 8, 6, 4, 6, 0.8]};

export class World {
  constructor(arena) {
    this.arena = arena; this.group = new THREE.Group(); this.group.visible = false; arena.root.add(this.group);
    this.active = null; this.cache = {};
    const tl = new THREE.TextureLoader();
    const data = url => { const t = tl.load(url); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; return t; };
    this.tex = {detail: data('assets/world/detail.webp'), flow: data('assets/world/flow.webp')};
    this.T = {value: 0};
    this.mat = new THREE.ShaderMaterial({uniforms: {uDetail: {value: this.tex.detail}, uT: this.T, uFlick: {value: 1}, uGrain: {value: 1}, uCloud: {value: 0}}, vertexShader: WORLD_VS, fragmentShader: WORLD_FS});
    const liq = rib => new THREE.ShaderMaterial({uniforms: {uFlow: {value: this.tex.flow}, uT: this.T, uGain: {value: 1}, uScale: {value: 0.16}, uSpeed: {value: 0.05}, uRib: {value: rib}, uFoamK: {value: 1}, uSoft: {value: 0}, uDir: {value: new THREE.Vector2(rib ? 0 : 1, rib ? 1 : 0)}, uDeep: {value: new THREE.Color()}, uMid: {value: new THREE.Color()}, uHot: {value: new THREE.Color()}, uWhite: {value: new THREE.Color()}}, vertexShader: LIQ_VS, fragmentShader: LIQ_FS});
    this.liqMat = liq(0); this.ribMat = liq(1); this.ribMat.side = THREE.DoubleSide;
    this.floorMat = new THREE.ShaderMaterial({uniforms: {uMap: {value: null}, uDetail: {value: this.tex.detail}, uT: this.T, uFlick: {value: 1}, uMacro: {value: 0.5}}, vertexShader: WORLD_VS, fragmentShader: FLOOR_FS});
    this.floorTex = {};
    this.blobMat = new THREE.ShaderMaterial({vertexShader: BLOB_VS, fragmentShader: BLOB_FS, transparent: true, blending: THREE.MultiplyBlending, premultipliedAlpha: true, depthWrite: false});
    this.haloMat = new THREE.ShaderMaterial({uniforms: {uT: this.T}, vertexShader: HALO_VS, fragmentShader: HALO_FS, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false});
    // the field every other material can read: until an arena sets it, no light and no occlusion
    const none = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1); none.needsUpdate = true;
    this.field = {tex: {value: none}, box: {value: new THREE.Vector4(-100, -100, 200, 200)}, none};
    this.life = {emitT: 0, flockT: 4, flock: null}; this.fliers = [];
  }
  // a standard material picks up the place's glow and its darkening by the walls
  lit(m) {
    if (!m || m.userData.worldLit || !m.isMeshStandardMaterial) return m; m.userData.worldLit = true;
    const prev = m.onBeforeCompile, F = this.field, pk = prev && prev !== THREE.Material.prototype.onBeforeCompile ? prev.toString() : '';
    m.onBeforeCompile = (sh, r) => {
      if (pk) prev.call(m, sh, r);
      sh.uniforms.uLF = F.tex; sh.uniforms.uLFb = F.box;
      sh.vertexShader = sh.vertexShader.replace('void main() {', 'varying vec3 vLF;\nvoid main() {').replace('#include <project_vertex>', `#include <project_vertex>
        { vec4 lw = vec4(transformed, 1.); #ifdef USE_INSTANCING
          lw = instanceMatrix * lw; #endif
          vLF = (modelMatrix * lw).xyz; }`.replace(/#ifdef USE_INSTANCING\s*/, '\n#ifdef USE_INSTANCING\n').replace(/#endif/, '\n#endif\n'));
      sh.fragmentShader = sh.fragmentShader.replace('void main() {', 'uniform sampler2D uLF; uniform vec4 uLFb; varying vec3 vLF;\nvoid main() {').replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        { vec4 lf = texture2D(uLF, (vLF.xz - uLFb.xy) / uLFb.zw); vec3 le = lf.rgb * lf.rgb * 2.; float lk = 1. / (1. + max(vLF.y, 0.) * .22);
          float lo = mix(1., lf.a, lk); reflectedLight.directDiffuse *= lo; reflectedLight.indirectDiffuse *= lo;
          totalEmissiveRadiance += diffuseColor.rgb * le * lk * .7; }`);
    };
    m.customProgramCacheKey = () => 'worldlit' + pk; m.needsUpdate = true; return m;
  }
  // what the camera can see of the ground: a trapezoid, wider up-screen. The rectangle round it is what ensure() watches; hw(z) trims what stands in its corners.
  // (tall things push up-screen, so the ends go past the view: an arch beyond the top edge still rises into it, one below the bottom edge still shows its top)
  region() {
    const a = innerWidth / innerHeight, St = this.arena.stage, d = St.dist || 60, v = THREE.MathUtils.degToRad((a > 0.75 ? 30 : 36) / 2), pitch = Math.PI / 3, cy = d * Math.sin(pitch), cz = St.camera?.position.z || 20 + d * Math.cos(pitch);
    const ray = q => cy / Math.tan(q), wide = q => cy / Math.sin(q) * Math.cos(v) * Math.tan(v) * a, zT = cz - ray(pitch - v), zB = cz - ray(pitch + v), hT = wide(pitch - v), hB = wide(pitch + v), m = 6;
    return {x0: 9 - hT - m, x1: 9 + hT + m, z0: zT - 12, z1: zB + 8, hw: z => hB + (hT - hB) * Math.min(1, Math.max(0, (zB - z) / (zB - zT))) + m};
  }
  clear() {
    this.group.clear(); for (const g of this.geoms || []) g.dispose(); this.geoms = []; this.group.visible = false; this.active = null; this.data = null; this.fliers = []; this.actors = []; this.bobbers = [];
    this.field.tex.value = this.field.none; if (this.lfTex) { this.lfTex.dispose(); this.lfTex = null; } this.field.box.value.set(-100, -100, 200, 200);
  }
  build(id, W, T, rebuilt = false) {
    const keepA = rebuilt ? this.actors : [], keepB = rebuilt ? this.bobbers : []; this.clear(); this.actors = keepA; this.bobbers = keepB; const R = this.reach = this.region(), t0 = performance.now(), D = this.data = generate(W, R);
    this.active = W; const G = this.geoms = [];
    // (one bad colour would blank the whole screen through the bloom)
    for (const c of [...D.chunks, ...(D.floor || [])]) for (let i = 0, n = c.n * STRIDE, A = c.a; i < n; i++) if (A[i] !== A[i]) A[i] = 0;
    for (const c of D.chunks) {
      const ib = new THREE.InterleavedBuffer(c.a.subarray(0, c.n * STRIDE), STRIDE), g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute('aCol', new THREE.InterleavedBufferAttribute(ib, 3, 3)); g.setAttribute('aGlow', new THREE.InterleavedBufferAttribute(ib, 3, 6)); g.setAttribute('aUv', new THREE.InterleavedBufferAttribute(ib, 2, 9)); g.setAttribute('aSway', new THREE.InterleavedBufferAttribute(ib, 1, 11));
      g.computeBoundingSphere(); G.push(g); this.group.add(new THREE.Mesh(g, this.mat));
    }
    if (D.floor) {
      const U = this.floorMat.uniforms, F = W.floor, tl = this.floorTex[F.tex] ||= new THREE.TextureLoader().load(F.tex, t => { t.needsUpdate = true; });
      tl.colorSpace = THREE.SRGBColorSpace; tl.wrapS = tl.wrapT = THREE.RepeatWrapping; tl.anisotropy = 8; U.uMap.value = tl; U.uFlick.value = W.flick ?? 1; U.uMacro.value = F.macro ?? 0.5;
      for (const c of D.floor) { const ib = new THREE.InterleavedBuffer(c.a.subarray(0, c.n * STRIDE), STRIDE), g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute('aCol', new THREE.InterleavedBufferAttribute(ib, 3, 3)); g.setAttribute('aGlow', new THREE.InterleavedBufferAttribute(ib, 3, 6)); g.setAttribute('aUv', new THREE.InterleavedBufferAttribute(ib, 2, 9)); g.setAttribute('aSway', new THREE.InterleavedBufferAttribute(ib, 1, 11)); g.computeBoundingSphere(); G.push(g); this.group.add(new THREE.Mesh(g, this.floorMat)); }
    }
    // (past what was built, the place's own colour rather than a void, whatever shape the window takes)
    const bk = new THREE.PlaneGeometry(900, 900).rotateX(-Math.PI / 2); G.push(bk); const back = new THREE.Mesh(bk, new THREE.MeshBasicMaterial({color: W.under || W.light.fog, fog: false})); back.position.set(9, -1.4, 16); back.renderOrder = -1; this.group.add(back); this.backMat?.dispose(); this.backMat = back.material;
    // the liquid under it all, drawn last so what's hidden costs nothing
    const L = W.liquid, setLiq = M => { const U = M.uniforms; U.uDeep.value.set(L.deep); U.uMid.value.set(L.mid); U.uHot.value.set(L.hot); U.uWhite.value.set(L.white); U.uGain.value = L.gain; U.uScale.value = L.scale ?? 0.16; U.uSpeed.value = L.speed ?? 0.05; U.uFoamK.value = L.foam ?? 1; U.uSoft.value = L.soft ?? 0; };
    setLiq(this.liqMat); setLiq(this.ribMat); this.mat.uniforms.uFlick.value = W.flick ?? 1; this.mat.uniforms.uGrain.value = W.grain ?? 1; this.mat.uniforms.uCloud.value = W.cloud ?? 0;
    const pl = new THREE.PlaneGeometry(R.x1 - R.x0, R.z1 - R.z0).rotateX(-Math.PI / 2); G.push(pl);
    const plane = new THREE.Mesh(pl, this.liqMat); plane.position.set((R.x0 + R.x1) / 2, LIQ_Y, (R.z0 + R.z1) / 2); plane.renderOrder = 1; this.group.add(plane);
    if (W.canal) { const st = new THREE.PlaneGeometry(R.x1 - R.x0, 5).rotateX(-Math.PI / 2); G.push(st); const m = new THREE.Mesh(st, this.arena.poolMat); m.position.set((R.x0 + R.x1) / 2, LIQ_Y + 0.01, 16); m.renderOrder = 1; this.group.add(m); }
    if (D.ribbons.length) {
      const ib = new THREE.InterleavedBuffer(D.ribbons, 6), g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute('aRib', new THREE.InterleavedBufferAttribute(ib, 3, 3)); G.push(g);
      const m = new THREE.Mesh(g, this.ribMat); m.renderOrder = 1; m.frustumCulled = false; this.group.add(m);
    }
    this.spinners = [];
    for (const c of D.spin || []) { const ib = new THREE.InterleavedBuffer(c.a.subarray(0, c.n * STRIDE), STRIDE), g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute('aCol', new THREE.InterleavedBufferAttribute(ib, 3, 3)); g.setAttribute('aGlow', new THREE.InterleavedBufferAttribute(ib, 3, 6)); g.setAttribute('aUv', new THREE.InterleavedBufferAttribute(ib, 2, 9)); g.setAttribute('aSway', new THREE.InterleavedBufferAttribute(ib, 1, 11)); g.computeBoundingSphere(); G.push(g); const m = new THREE.Mesh(g, this.mat); m.position.set(c.x, c.y, c.z); this.group.add(m); this.spinners.push({m, axis: c.axis, speed: c.speed}); }
    this.buildHalos(D.halos); this.buildBlobs(rebuilt && this.kitBlobs ? [...D.blobs, ...this.kitBlobs] : D.blobs);
    const lf = new THREE.DataTexture(D.lf.data, D.lf.w, D.lf.h, THREE.RGBAFormat); lf.magFilter = lf.minFilter = THREE.LinearFilter; lf.needsUpdate = true; this.lfTex = lf;
    this.field.tex.value = lf; this.field.box.value.set(R.x0, R.z0, R.x1 - R.x0, R.z1 - R.z0);
    this.setFlock(W.life?.flock); this.group.visible = true; this.life.emitT = 0; this.life.flockT = 3;
    console.info(`[world] ${id}: ${D.cells} cells, ${D.tris} triangles, ${D.lights} lights, ${(performance.now() - t0).toFixed(0)} ms`);
  }
  heightAt(x, z) { return this.data ? this.data.heightAt(x, z) : 0; }
  // where a loose piece can stand: its height, or null over liquid and off what was built
  yAt(x, z) { const D = this.data, R = this.reach; if (!D || x < R.x0 || x > R.x1 || z < R.z0 || z > R.z1 || D.field.riverD(x, z) < 0.5 || !D.field.at(x, z)) return null; return D.heightAt(x, z); }
  buildHalos(H) {
    if (!H.length) return;
    const g = new THREE.InstancedBufferGeometry(), q = new THREE.PlaneGeometry(1, 1); g.index = q.index; g.setAttribute('position', q.attributes.position); g.instanceCount = H.length;
    const pos = new Float32Array(H.length * 4), col = new Float32Array(H.length * 4), sz = new Float32Array(H.length);
    H.forEach((h, i) => { pos.set([h.x, h.y, h.z, h.a * (h.lamp ? -1 : 1)], i * 4); col.set([h.c[0], h.c[1], h.c[2], h.ph], i * 4); sz[i] = h.s; });
    g.setAttribute('aPos', new THREE.InstancedBufferAttribute(pos, 4)); g.setAttribute('aCol', new THREE.InstancedBufferAttribute(col, 4)); g.setAttribute('aSize', new THREE.InstancedBufferAttribute(sz, 1)); this.geoms.push(g);
    const m = new THREE.Mesh(g, this.haloMat); m.frustumCulled = false; m.renderOrder = 4; this.group.add(m);
  }
  // a soft dark patch under everything that stands on the ground, which is most of what makes it look as if it does
  buildBlobs(B) {
    if (!B.length) return; if (this.blobMesh) { this.group.remove(this.blobMesh); this.blobMesh = null; }
    const g = new THREE.InstancedBufferGeometry(), q = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2); g.index = q.index; g.setAttribute('position', q.attributes.position); g.instanceCount = B.length;
    const at = new Float32Array(B.length * 3), sz = new Float32Array(B.length * 2); B.forEach((b, i) => { at.set([b.x, b.y, b.z], i * 3); sz.set([b.r, b.k], i * 2); });
    g.setAttribute('aAt', new THREE.InstancedBufferAttribute(at, 3)); g.setAttribute('aSz', new THREE.InstancedBufferAttribute(sz, 2)); this.geoms.push(g);
    const m = this.blobMesh = new THREE.Mesh(g, this.blobMat); m.frustumCulled = false; m.renderOrder = 2; this.group.add(m);
  }
  // a model of the arena's kit belongs to this place: its colour and this place's light
  dressKit(o) {
    const W = this.active, tint = W?.propTint ? new THREE.Color(W.propTint) : null;
    o.traverse(n => { if (n.isMesh) n.material = [].concat(n.material).map(m => { if (tint && m.color && !m.userData.tinted) { m.color.multiply(tint); m.userData.tinted = true; } return this.lit(m); }).reduce((a, m, i, all) => all.length === 1 ? m : all, null); });
  }
  // the arena's own models, set on the terraces; some of them drive round on a path
  async place(id, base, group, rest = []) {
    const W = this.active; if (!W) return;
    const names = [...new Set([...(W.props || []), ...(W.actors || []), ...(W.bob || []), ...rest].map(p => p.p))], glbs = {};
    await Promise.all(names.map(async n => { try { glbs[n] = await loadGLB(base + 'props/' + n + '.glb'); } catch {} }));
    if (this.active !== W) return;
    const low = this.arena.stage.quality === 'low';
    const dress = o => { this.dressKit(o); o.traverse(n => { if (n.isMesh) n.castShadow = n.receiveShadow = false; }); };
    for (const p of W.props || []) {
      const g = glbs[p.p]; if (!g) continue;
      const o = cloneGLB(g).scene; o.position.set(p.x, (p.y ?? this.heightAt(p.x, p.z)) + (p.dy || 0), p.z); o.rotation.y = p.ry || 0; o.scale.setScalar(p.s || 1); dress(o);
      o.traverse(n => { const m = /^(anim_spin|anim_bob|anim_sway|fx_smoke|fx_glow)/.exec(n.name || ''); if (m) this.arena.anims.push({o: n, kind: m[1], y: n.position.y, rz: n.rotation.z, ph: Math.random() * 6.28, mats: n.isMesh ? [].concat(n.material) : []}); });
      group.add(o);
    }
    // the arena's kit, where it was laid out, on whatever ground is there now (a twin in front of my Battlestation steps aside)
    for (const p of rest) {
      const g = glbs[p.p]; if (!g) continue;
      const x = p.z > 33 && Math.abs(p.x - 9) < 3 ? 9 + (p.x >= 9 ? 5.8 : -5.8) : p.x, o = cloneGLB(g).scene; o.position.set(x, (p.y || 0) + this.heightAt(x, p.z), p.z); o.rotation.y = p.ry || 0; o.scale.setScalar(p.s || 1); dress(o);
      o.traverse(n => { const m = /^(anim_spin|anim_bob|anim_sway|fx_smoke|fx_glow)/.exec(n.name || ''); if (m) this.arena.anims.push({o: n, kind: m[1], y: n.position.y, rz: n.rotation.z, ph: Math.random() * 6.28, mats: n.isMesh ? [].concat(n.material) : []}); });
      group.add(o);
    }
    const box = new THREE.Box3(), szv = new THREE.Vector3(), extra = this.kitBlobs = [];
    for (const o of group.children) { box.setFromObject(o); box.getSize(szv); const c = box.getCenter(new THREE.Vector3()), foot = Math.max(szv.x, szv.z); if (foot < 0.25 || foot > 14 || (c.x > 0 && c.x < 18 && c.z > 0 && c.z < 32)) continue; extra.push({x: c.x, y: box.min.y + 0.03, z: c.z, r: foot * 0.62, k: 0.42}); }
    this.buildBlobs([...this.data.blobs, ...extra]);
    // things that hang in the air and drift: jellyfish, cubes, lanterns
    this.bobbers = [];
    for (const B of W.bob || []) {
      const g = glbs[B.p]; if (!g) continue;
      for (const [x, z, y, s = 1] of B.at) { if (x < this.reach.x0 || x > this.reach.x1) continue; const o = cloneGLB(g).scene; o.position.set(x, y, z); o.scale.setScalar((B.s || 1) * s); dress(o); group.add(o); this.bobbers.push({o, y, amp: B.amp ?? 0.4, ph: x + z, sp: B.speed ?? 0.9, spin: B.spin ?? 0.15}); }
    }
    this.actors = [];
    for (const A of W.actors || []) {
      const g = glbs[A.p]; if (!g) continue;
      const L = pathOf(A), n = A.n || 1;
      for (let i = 0; i < n; i++) { const o = cloneGLB(g).scene; o.scale.setScalar(A.s || 1); dress(o); group.add(o); this.actors.push({o, L, d: L.len * i / n + (A.at || 0), v: A.speed || 1, y: A.y ?? 0.02, face: A.face || 0}); }
    }
    if (low) for (const a of this.actors.slice(1)) { a.o.visible = false; }
  }
  ensure() {   // (a window grown past what was built, or a phone turned on its side: build again, a moment after it stops changing)
    clearTimeout(this.ensureT); this.ensureT = setTimeout(() => {
      const W = this.active, A = this.arena; if (!W) return; const R = this.region(), B = this.reach;
      if (R.x0 < B.x0 - 1 || R.x1 > B.x1 + 1 || R.z0 < B.z0 - 1 || R.z1 > B.z1 + 1) this.build(A.themeId, W, A.theme, true);
    }, 250);
  }
  setFlock(kind) {
    if (this.wings) { this.group.remove(this.wings); this.wings.geometry.dispose(); this.wings.material.dispose(); this.wings = null; }
    this.life.flock = null; const F = FLYERS[kind]; if (!F) return;
    const geo = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0.32, 1, 0, 0.1, 0.72, 0, -0.34, 0, 0, -0.5], 3)).setIndex([0, 1, 2, 0, 2, 3]);
    const mat = new THREE.MeshBasicMaterial({color: F[0], side: THREE.DoubleSide, transparent: true, opacity: 0.95, depthWrite: false, fog: false});
    this.wings = new THREE.InstancedMesh(geo, mat, F[5] * 2); this.wings.frustumCulled = false; this.wings.visible = false; this.wings.renderOrder = 5; this.group.add(this.wings);
    this.life.kind = F;
  }
  // a flock now and then, from one side of the view to the other, mostly over the far half
  flyers(dt, t) {
    const L = this.life, F = L.kind, W = this.wings; if (!W || !F) return;
    if (!L.flock) {
      W.visible = false; L.flockT -= dt; if (L.flockT > 0) return;
      const dir = Math.random() < 0.5 ? 1 : -1, reach = innerWidth / innerHeight > 0.75 ? 46 : 16;
      L.flock = {dir, x: 9 - dir * reach, end: 9 + dir * reach, z: Math.random() < 0.75 ? 2 + Math.random() * 12 : 20 + Math.random() * 12, ph: Math.random() * 6, y: F[2] * (0.8 + Math.random() * 0.4)};
      L.flockT = 10 + Math.random() * 14;
    }
    const f = L.flock; f.x += f.dir * F[3] * dt; W.visible = true;
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(0, 0, 0, 'YXZ'), p = new THREE.Vector3(), sc = new THREE.Vector3();
    for (let i = 0; i < F[5]; i++) {
      const row = Math.ceil(i / 2), side = i % 2 ? 1 : -1, wander = Math.sin(t * 0.9 + i * 2.1 + f.ph) * F[6];
      p.set(f.x - f.dir * row * F[1] * 2.4, f.y + Math.sin(t * 1.3 + i + f.ph) * 0.25 * F[6], f.z + side * row * F[1] * 1.8 + wander);
      const flap = Math.sin(t * F[4] * 6.283 + i * 1.7) * 0.75, heading = f.dir > 0 ? -Math.PI / 2 : Math.PI / 2;
      for (const s of [1, -1]) { e.set(0, heading, s * flap); q.setFromEuler(e); sc.set(s * F[1], F[1], F[1]); m.compose(p, q, sc); W.setMatrixAt(i * 2 + (s > 0 ? 0 : 1), m); }
    }
    W.instanceMatrix.needsUpdate = true;
    if ((f.end - f.x) * f.dir < 0) L.flock = null;
  }
  // the air: {k: kind, n: how many a second, c: colour} from worlds.js life.emit, with their sources from the build
  ambient(dt, fx, t) {
    const W = this.active, D = this.data; this.flyers(dt, t);
    if (!fx || !W?.life?.emit) return;
    const r = Math.random, Rg = this.reach, pick = a => a[Math.floor(r() * a.length)], air = () => ({x: Rg.x0 + r() * (Rg.x1 - Rg.x0), z: -6 + r() * 46});
    for (const E of W.life.emit) {
      if (r() >= dt * E.n) continue;
      const b = air(), c = E.c;
      switch (E.k) {
        case 'embers': { const a = pick(D.spots.seam) || [b.x, 0.2, b.z]; fx.add.emit({x: a[0] + (r() - 0.5) * 0.4, y: a[1], z: a[2] + (r() - 0.5) * 0.4, vx: (r() - 0.5) * 0.5, vy: 1 + r() * 1.3, life: 2 + r(), s0: 0.16, s1: 0.03, c: c ?? [1, 0.55, 0.15], a0: 0.95, a1: 0, cell: 0}); break; }
        case 'river': fx.add.emit({x: b.x, y: 0.05, z: 15.1 + r() * 1.8, vx: (r() - 0.5) * 0.4, vy: 0.8 + r() * 1.1, life: 1.6 + r(), s0: 0.15, s1: 0.03, c: c ?? [1, 0.55, 0.15], a0: 0.9, a1: 0, cell: 0}); break;
        case 'falls': { const a = pick(D.spots.fall); if (a) fx.add.emit({x: a[0] + (r() - 0.5) * 0.6, y: a[1], z: a[2] + (r() - 0.5) * 0.6, vx: (r() - 0.5) * 1.4, vy: 1.4 + r() * 1.6, life: 0.8 + r() * 0.5, s0: 0.14, s1: 0.03, c: c ?? [1, 0.7, 0.25], a0: 1, a1: 0, cell: 0}); break; }
        case 'glint': { const a = pick(D.spots.crystal); if (a) fx.add.emit({x: a[0] + (r() - 0.5) * 0.8, y: a[1] + r() * 0.8, z: a[2] + (r() - 0.5) * 0.8, life: 0.7, s0: 0.1, s1: 0.5, c: c ?? [0.7, 1, 1], a0: 1, a1: 0, cell: 1}); break; }
        case 'motes': fx.add.emit({x: b.x, y: 0.5 + r() * 4, z: b.z, vx: (r() - 0.5) * 0.3, vy: 0.06 + r() * 0.1, life: 5, s0: 0.1, s1: 0.1, c: c ?? [1, 0.9, 0.6], a0: 0.5, a1: 0, cell: 0}); break;
        case 'snow': fx.norm.emit({x: b.x, y: 9, z: b.z, vx: 0.3, vy: -1.2, life: 7, s0: 0.2, s1: 0.2, c: [1, 1, 1], a0: 0.9, a1: 0.8, cell: 0, floor: 0.02}); break;
        case 'bubbles': fx.add.emit({x: E.river ? b.x : b.x, y: 0.1, z: E.river ? 15.2 + r() * 1.6 : b.z, vx: (r() - 0.5) * 0.15, vy: 0.7 + r() * 0.5, life: 3.5, s0: 0.1, s1: 0.22, c: c ?? [0.65, 0.9, 1], a0: 0.5, a1: 0, cell: 0}); break;
        case 'wisps': fx.add.emit({x: b.x, y: 0.3 + r(), z: b.z, vx: (r() - 0.5) * 0.3, vy: 0.14, life: 4, s0: 0.2, s1: 0.55, c: c ?? [0.2, 0.95, 0.8], a0: 0.4, a1: 0, cell: 0}); break;
        case 'smoke': { const a = pick(D.spots.seam); if (a) fx.norm.emit({x: a[0], y: a[1], z: a[2], vy: 0.7 + r() * 0.5, vx: 0.15, life: 2.8, s0: 0.5, s1: 1.7, c: c ?? [0.16, 0.13, 0.16], a0: 0.3, cell: 3}); break; }
        case 'glitch': fx.add.emit({x: b.x, y: 0.4 + r() * 2.4, z: b.z, life: 0.5, s0: 0.3, s1: 0.3, c: r() < 0.5 ? [0.15, 0.9, 1] : [1, 0.25, 0.85], a0: 0.9, a1: 0, cell: 0}); break;
        case 'stars': fx.add.emit({x: b.x, y: 6 + r() * 8, z: -2 + r() * 8, life: 1.6, s0: 0, s1: 0.5, c: [1, 1, 1], a0: 1, a1: 0, cell: 1}); break;
      }
    }
  }
  update(dt, t, fx) {
    this.T.value = t; if (!this.active) return;
    this.ambient(dt, fx, t);
    for (const c of this.spinners || []) c.m.rotation[c.axis] += c.speed * dt;
    for (const b of this.bobbers || []) { b.o.position.y = b.y + Math.sin(t * b.sp + b.ph) * b.amp; b.o.rotation.y += b.spin * dt; }
    for (const a of this.actors || []) {
      a.d = (a.d + a.v * dt) % a.L.len; const [x, z, ang] = a.L.at(a.d);
      a.o.position.set(x, a.y, z); a.o.rotation.y = ang + a.face;
    }
  }
}

// a closed loop of straight runs with rounded corners, walked by distance (what the carts drive on)
function pathOf(A) {
  const P = A.path, seg = []; let len = 0;
  for (let i = 0; i < P.length; i++) { const a = P[i], b = P[(i + 1) % P.length], l = Math.hypot(b[0] - a[0], b[1] - a[1]); seg.push({a, b, l, s: len}); len += l; }
  return {len, at(d) {
    let lo = seg[seg.length - 1]; for (const q of seg) if (d >= q.s && d < q.s + q.l) { lo = q; break; }
    const k = (d - lo.s) / lo.l, x = mix(lo.a[0], lo.b[0], k), z = mix(lo.a[1], lo.b[1], k);
    // the heading eases from one run to the next over the last half tile
    const i = seg.indexOf(lo), nx = seg[(i + 1) % seg.length], ang0 = Math.atan2(lo.b[0] - lo.a[0], lo.b[1] - lo.a[1]), ang1 = Math.atan2(nx.b[0] - nx.a[0], nx.b[1] - nx.a[1]); let da = ang1 - ang0; while (da > Math.PI) da -= Math.PI * 2; while (da < -Math.PI) da += Math.PI * 2;
    const e = smooth(lo.l - 0.6, lo.l, d - lo.s);
    return [x, z, ang0 + da * e];
  }};
}
