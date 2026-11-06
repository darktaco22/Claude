// MEME ROYALE — what a battle entity looks like on the wire (server/match.mjs packs, src/net/netbattle.js unpacks). EVERY entity of
// Battle.ents is sent, whatever its kind: ONCE whole (its static fields) the first time a player sees it, then in every snapshot
// only as a short array of its dynamic fields. FIELDS below is the ONE place that says which fields of which kind travel (the
// names of src/sim.js entities, which the renderer reads): add a field or a kind here and both sides carry it. A kind not listed
// travels with ANY. Positions travel in the SERVER's frame (team 0 at the bottom); the page mirrors the fields named in MIRROR.
export const FIELDS = {
  unit: {static: ['card', 'team', 'h', 'r', 'mass', 'speed', 'max', 'range', 'proj', 'beam', 'bOnly', 'jumper', 'splash', 'air', 'lv'],
    dyn: ['x', 'z', 'face', 'state', 'st', 'hp', 'max', 'moving', 'airT', 'beamOn', 'beamT', 'stunT', 'slowT', 'slowK', 'rageT', 'frozenT', 'target', 'charging', 'weakT', 'shield', 'guardT', 'fearT', 'rootT', 'mad', 'dug', 'clone']},   // (air: PNUT flies; charging: MOO DENG; weakT: under WOJAK's gloom)
  tower: {static: ['type', 'team', 'x', 'z', 'r', 'h', 'max', 'lane', 'range'], dyn: ['hp', 'active', 'dead', 'target', 'aim', 'frozenT']},
  proj: {static: ['proj', 'team', 'from', 'card', 'y', 'splash', 'lob'], dyn: ['x', 'z', 'tx', 'tz', 'target']},
  spell: {static: ['card', 'team', 'x', 'z', 'r'], dyn: ['x', 'z', 'live', 'fired', 'dir']},   // (BAN HAMMER rolls: x, z move along dir)
  bld: {static: ['card', 'team', 'x', 'z', 'r', 'h', 'max', 'range', 'proj', 'mine', 'hide', 'maxLife', 'building', 'born', 'lv'],
    dyn: ['hp', 'life', 'state', 'st', 'target', 'aim', 'frozenT', 'mineT', 'hidden', 'beamOn', 'beamT']},   // (hidden: the HONEYPOT is underground)
};
export const ANY = {static: ['card', 'team', 'type', 'x', 'z', 'r', 'h', 'max', 'lv'], dyn: ['x', 'z', 'hp', 'state', 'dead', 'target']};
export const fieldsOf = kind => FIELDS[kind] || ANY;
// what the page mirrors when it plays the server's team 1, and the fields that name another entity (0 / null: none)
export const MIRROR = {x: new Set(['x', 'tx', 'x0']), z: new Set(['z', 'tz', 'z0']), angle: new Set(['face', 'aim']), team: new Set(['team']), sign: new Set(['dir'])};
export const REF = new Set(['target', 'beamOn', 'from']);

// numbers to 3 decimals, booleans to 1 / 0, nothing to null
const enc = v => typeof v === 'number' ? (Number.isInteger(v) ? v : Math.round(v * 1000) / 1000) : typeof v === 'boolean' ? (v ? 1 : 0) : v === undefined ? null : v;
// the static part: {id, kind, ...}; `extra` adds what is not on the entity (the card's level: lv)
export function packStatic(e, extra = {}) {
  const o = {id: e.id, kind: e.kind};
  for (const k of fieldsOf(e.kind).static) { const v = k in extra ? extra[k] : e[k]; if (v !== undefined && v !== null && v !== false) o[k] = enc(v); }
  return o;
}
// the dynamic part: [id, ...the values of fieldsOf(kind).dyn]
export function packDyn(e) { const F = fieldsOf(e.kind).dyn, a = [e.id]; for (const k of F) a.push(enc(e[k])); return a; }

// A SNAPSHOT THAT SAYS ONLY WHAT CHANGED, for a page whose hello says v >= 2 (snapshots are small enough to go uncompressed, which is
// most of what a player costs the server). `d` by kind instead of `e`: [id, mask, ...the values whose bit is set] (bit i: the i-th field
// of fieldsOf(kind).dyn; a new entity has every bit), `g` the ids that are gone; phase, od, ws, over, winner, why, add, ev and my hand
// and queue only when they say something. A snapshot with `e` says everything and starts again from it (the first after a start or a
// reconnect, and every one for an older page). SnapReader gives the page back the whole snapshot, so nothing after it knows the difference.
export const HEAD = ['phase', 'od', 'ws', 'over', 'winner', 'why'];
export function deltaOf(a, o) {
  let out = null, mask = 0;
  for (let i = 1; i < a.length; i++) if (!o || a[i] !== o[i]) { if (!out) out = [a[0], 0]; mask |= 1 << (i - 1); out.push(a[i]); }
  if (out) out[1] = mask;
  return out;
}
export class SnapReader {
  constructor() { this.ents = new Map(); this.head = {}; this.me = null; }
  start(S, mine) { this.read(S); this.me = mine || null; }
  read(m) {
    if (m.e) {
      this.ents.clear(); for (const k in m.e) for (const a of m.e[k]) this.ents.set(a[0], {k, a});
      for (const h of HEAD) this.head[h] = m[h];
      if (m.me) this.me = m.me;
      return m;
    }
    if (!m.d) return m;
    if (m.g) for (const id of m.g) this.ents.delete(id);
    for (const k in m.d) {
      const n = fieldsOf(k).dyn.length;
      for (const x of m.d[k]) {
        const o = this.ents.get(x[0]), a = new Array(n + 1), mask = x[1]; a[0] = x[0];
        for (let i = 1, j = 2; i <= n; i++) a[i] = mask & (1 << (i - 1)) ? x[j++] : o ? o.a[i] : null;
        if (o) o.a = a; else this.ents.set(x[0], {k, a});
      }
    }
    const e = {}; for (const {k, a} of this.ents.values()) (e[k] ||= []).push(a);
    m.e = e; delete m.d; delete m.g;
    for (const h of HEAD) if (h in m) this.head[h] = m[h]; else m[h] = this.head[h];
    m.add ||= []; m.ev ||= [];
    if (m.me) m.me = this.me = {...this.me, ...m.me};
    return m;
  }
}
