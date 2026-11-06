// MEME ROYALE — A BATTLE PLAYED ON THE SERVER, as the game sees it. NetBattle has the fields and methods of src/sim.js Battle that the
// game reads (battle.js, src/ui/hud.js, src/render/*), with the same names, so the renderer and the HUD run on it unchanged; but it
// simulates nothing: the server runs the battle (server/match.mjs) and sends snapshots (~15 a second) with every event; this shows
// them DELAY s behind the newest, moving everything smoothly between two snapshots. My hand, my next card and my COPIUM are mine
// alone (the server never sends the other side's); COPIUM runs on between snapshots. A play is sent at once and shown at once
// (optimistic: the card leaves the hand, the COPIUM is spent); a refused play comes back with the next snapshot.
//
// PERSPECTIVE: I am always team 0, at the bottom. When I play the server's team 1, everything is mirrored both ways: x' = 18 - x,
// z' = 32 - z, face' = face + PI, the teams swapped (towers, Ws, levels, events), and my plays are mirrored back before they go.
//
//   const nb = new NetBattle(client, startMessage)      (the client's 'start' event; client.match holds the newest)
//   nb.step(dt = NetBattle.DT)    the game calls it at 30 Hz, like Battle.step     nb.events (the game drains it)
//   nb.play(0, slot, x, z) -> bool   nb.canPlay(0, slot, x, z) / nb.canPlace(0, card, x, z) -> null | why (the same rules as sim.js)
//   nb.emote(id)   nb.onEmote = (team, id) => ...   nb.onOpp = ({away, gone}) => ...   nb.onDeny = why => ...   nb.onSync = () => ... (a resync)
//   nb.done -> Promise of the server's result {win, ws, why, res, stats, friendly}      nb.result   nb.destroy()
//   nb.opp {name, clout, level, arena, avatar, bot}   nb.me   nb.arena (ARENAS id)   nb.friendly   nb.mid   nb.team (the server's)
import {Battle} from '../sim.js';
import {CARDS, MATCH, regenMult} from '../data.js';
import {fieldsOf, MIRROR, REF} from '../shared/snap.js';

export const DELAY = 0.1;                        // s of battle time the view runs behind the newest snapshot
const QUIET = new Set(['die', 'down', 'revive', 'tower_down', 'w', 'phase', 'end', 'hq_wake', 'landed', 'spawn', 'play']);   // kept when catching up

export class NetBattle {
  static DT = Battle.DT;
  constructor(client, start) {
    this.client = client; this.mid = start.mid; this.team = start.team; this.flip = start.team === 1;
    this.arena = start.arena; this.speed = start.speed || 1; this.friendly = !!start.friendly; this.me = start.me; this.opp = start.opp;
    this.ents = new Map(); this.towers = [[], []]; this.events = [];
    this.levels = [{...(start.me?.levels || {})}, {}];
    const tl = start.towerLvl || [1, 1]; this.towerLvl = this.flip ? [tl[1], tl[0]] : [...tl];
    this.hands = [[], []]; this.queues = [[], []]; this.copium = [MATCH.startCopium, 0];
    this.clock = MATCH.time; this.phase = 'play'; this.overdose = false; this.ws = [0, 0]; this.over = false; this.winner = null; this.why = null;
    this.t = 0; this.spent = [0, 0]; this.played = [[], []];
    this.buf = []; this.cur = null; this.newest = 0; this.rt = null; this.pending = []; this.result = null; this.oppAway = !!start.away;
    this.onEmote = null; this.onOpp = null; this.onDeny = null; this.onResult = null; this.onSync = null;
    this.done = new Promise(res => { this.resolve = res; });
    this.subs = [
      client.on('snap', m => this.arrive(m)),
      client.on('start', m => { if (m.mid === this.mid) this.resync(m); }),
      client.on('r', m => this.answer(m)),
      client.on('emote', m => this.onEmote?.(1, m.id)),
      client.on('opp', m => { this.oppAway = !!m.away; this.onOpp?.(m); }),
      client.on('result', m => { if (m.mid !== this.mid) return; this.result = m; this.resolve(m); this.onResult?.(m); }),
    ];
    this.resync(start);
  }
  destroy() { for (const off of this.subs) off(); this.subs = []; }
  // ---- the frame
  mx(x) { return this.flip ? 18 - x : x; } mz(z) { return this.flip ? 32 - z : z; } mt(t) { return this.flip && (t === 0 || t === 1) ? 1 - t : t; } ma(a) { return this.flip ? a + Math.PI : a; }
  mev(e) {
    if (!this.flip) return e; const o = {...e};
    if (typeof o.x === 'number') o.x = 18 - o.x; if (typeof o.z === 'number') o.z = 32 - o.z;
    if (typeof o.x0 === 'number') o.x0 = 18 - o.x0; if (typeof o.z0 === 'number') o.z0 = 32 - o.z0;
    if (o.team === 0 || o.team === 1) o.team = 1 - o.team; if (o.winner === 0 || o.winner === 1) o.winner = 1 - o.winner;
    if (Array.isArray(o.ws)) o.ws = [o.ws[1], o.ws[0]];
    if (typeof o.dir === 'number') o.dir = -o.dir;
    return o;
  }

  // ---- what the server sends
  // the whole battle again (the first time, and after a reconnect): every entity, the state of now, my hand
  resync(m) {
    const seen = new Set();
    for (const o of m.ents) { this.addStatic(o); seen.add(o.id); }
    for (const [id, e] of this.ents) if (!seen.has(id) && e.kind !== 'tower') this.drop(e, true);
    this.buf = []; this.pending = []; const S = this.prep(m.snap); this.newest = S.bt; this.rt = S.bt;
    this.apply(S, false); this.mine(m.mine, true);
    this.onSync?.();   // (what fell while the line was down came with no event: the game shows it at once)
  }
  // a value of the wire -> my frame (positions and angles mirrored when I am the server's team 1; ids of nothing -> null)
  val(k, v) {
    if (MIRROR.x.has(k)) return typeof v === 'number' ? this.mx(v) : v;
    if (MIRROR.z.has(k)) return typeof v === 'number' ? this.mz(v) : v;
    if (MIRROR.angle.has(k)) return typeof v === 'number' ? this.ma(v) : v;
    if (MIRROR.team.has(k)) return this.mt(v);
    if (MIRROR.sign.has(k)) return this.flip && typeof v === 'number' ? -v : v;   // (a direction along z)
    if (REF.has(k)) return v || null;
    return v;
  }
  prep(S) {   // positions of a snapshot by id (in my frame), for moving between two of them: every kind whose dynamic part has x and z
    S.pos = new Map();
    for (const [kind, list] of Object.entries(S.e)) {
      const F = fieldsOf(kind).dyn, ix = F.indexOf('x') + 1, iz = F.indexOf('z') + 1; if (!ix || !iz) continue;
      for (const a of list) S.pos.set(a[0], [this.mx(a[ix]), this.mz(a[iz])]);
    }
    return S;
  }
  arrive(m) {
    if (this.rt == null) return;
    this.buf.push(this.prep(m)); this.newest = Math.max(this.newest, m.bt);
    this.mine(m.me, false);
  }
  // my private part: COPIUM, hand, queue, and which of my plays the server has decided (ack)
  mine(me, hard) {
    if (!me) return;
    this.pending = this.pending.filter(p => p.n > me.ack);
    const cost = this.pending.reduce((s, p) => s + p.cost, 0), want = Math.max(0, me.cop - cost);
    if (hard || Math.abs(want - this.copium[0]) > 0.25) this.copium[0] = want; else this.copium[0] += (want - this.copium[0]) * 0.5;
    if (!this.pending.length) { this.hands[0] = [...me.hand]; this.queues[0] = [...me.queue]; }
  }
  answer(m) {
    const k = this.pending.findIndex(p => p.n === m.n); if (k < 0) return;
    if (!m.ok) { this.pending.splice(k, 1); this.onDeny?.(m.why || 'refused'); }
  }
  // an entity's static part (any kind: src/shared/snap.js FIELDS); the same object is kept when it comes again (a resync)
  addStatic(o) {
    let e = this.ents.get(o.id);
    if (!e) {
      e = {id: o.id, kind: o.kind, px: 0, pz: 0, target: null, dead: false, fresh: true};
      if (o.kind === 'unit') Object.assign(e, {face: 0, state: 'deploy', st: MATCH.deployTime, hp: o.max, moving: false, airT: 0, beamOn: null, beamT: 0, stunT: 0, slowT: 0, slowK: 1, rageT: 0, frozenT: 0, proj: null, beam: false, charging: false, weakT: 0});
      if (o.kind === 'tower') Object.assign(e, {hp: o.max, active: o.type === 'rig', aim: 0, building: true, cd: 0, frozenT: 0});
      if (o.kind === 'proj') Object.assign(e, {tx: 0, tz: 0, age: 0});
    }
    for (const k of fieldsOf(o.kind).static) if (k in o) e[k] = this.val(k, o[k]);
    if (o.kind === 'tower') {   // my towers are towers[0], lane 0 on the left, whichever side I play
      e.lane = o.type === 'hq' ? -1 : this.flip ? 1 - o.lane : o.lane;
      if (!this.towers[e.team].includes(e)) this.towers[e.team][e.lane < 0 ? 2 : e.lane] = e;
    }
    if (typeof e.x === 'number' && e.fresh && !fieldsOf(o.kind).dyn.includes('x')) { e.px = e.x; e.pz = e.z; e.fresh = false; }   // (it never moves)
    const L = this.levels[e.team]; if (L && o.card && o.lv && !(o.card in L)) L[o.card] = o.lv;
    this.ents.set(o.id, e);
  }
  drop(e, synth) {
    this.ents.delete(e.id); e.dead = true;
    if (synth && e.kind === 'unit') this.events.push({type: 'die', t: this.t, id: e.id, card: e.card, team: e.team, x: e.x, z: e.z});
  }
  // a snapshot's moment becomes what is shown: new entities, what changed, what is gone, its events
  apply(S, quiet) {
    for (const o of S.add || []) this.addStatic(o);
    const live = new Set();
    for (const [kind, list] of Object.entries(S.e)) {
      const F = fieldsOf(kind).dyn;
      for (const a of list) {
        const e = this.ents.get(a[0]); if (!e) continue; live.add(a[0]);
        for (let i = 0; i < F.length; i++) { const k = F[i]; if (k !== 'x' && k !== 'z') e[k] = this.val(k, a[i + 1]); }
        const p = S.pos.get(a[0]);
        if (p) { if (e.fresh) { e.x = e.px = p[0]; e.z = e.pz = p[1]; e.fresh = false; } e.ax = p[0]; e.az = p[1]; }
      }
    }
    for (const e of [...this.ents.values()]) if (!live.has(e.id)) { if (e.kind === 'tower') e.dead = true; else this.drop(e, false); }
    for (const raw of S.ev || []) {
      const ev = this.mev(raw);
      if (ev.type === 'play') { this.played[ev.team]?.push({id: ev.card, t: ev.t, x: ev.x, z: ev.z}); this.spent[ev.team] += CARDS[ev.card]?.cost || 0; }
      if (ev.type === 'end') { this.over = true; this.winner = ev.winner; this.why = ev.why; }
      if (!quiet || QUIET.has(ev.type)) this.events.push(ev);
    }
    this.phase = S.phase; this.overdose = !!S.od; this.ws = this.flip ? [S.ws[1], S.ws[0]] : [...S.ws];
    if (S.over) { this.over = true; this.winner = this.mt(S.winner); this.why = S.why; }
    this.cur = S;
  }
  // ---- the clock of the view
  step(dt = NetBattle.DT) {
    if (this.rt == null) return;
    const adv = dt * this.speed, want = this.newest - DELAY * this.speed;
    let jump = false;
    if (Math.abs(want - (this.rt + adv)) > 0.6 * this.speed) { jump = want - this.rt > 1.5 * this.speed; this.rt = Math.max(this.rt, want); }
    else this.rt += adv + (want - (this.rt + adv)) * 0.1;
    this.rt = Math.min(this.rt, this.newest);
    while (this.buf.length && this.buf[0].bt <= this.rt) this.apply(this.buf.shift(), jump);
    const A = this.cur, B = this.buf[0];
    const k = A && B && B.bt > A.bt ? Math.max(0, Math.min(1, (this.rt - A.bt) / (B.bt - A.bt))) : 0;
    for (const e of this.ents.values()) {
      if (e.ax == null) continue;                                   // (what never moves: towers, spells, buildings)
      e.px = e.x; e.pz = e.z;
      const b = B?.pos.get(e.id);
      if (b && k > 0) { e.x = e.ax + (b[0] - e.ax) * k; e.z = e.az + (b[1] - e.az) * k; } else { e.x = e.ax; e.z = e.az; }
    }
    this.t = this.rt;
    if (A && this.phase !== 'end') this.clock = Math.max(0, A.clock - Math.max(0, this.rt - A.bt));
    // my COPIUM runs on between two snapshots
    if (!this.over && this.phase !== 'tiebreak') { const mult = regenMult(this.phase, this.clock, this.overdose); this.copium[0] = Math.min(MATCH.maxCopium, this.copium[0] + adv / MATCH.regen * mult); }
  }
  // ---- reading (the names of sim.js Battle)
  next(team) { return this.queues[team][0]; }
  lvl(team, id) { return this.levels[team][id] || 1; }
  timeLeft() { return Math.max(0, this.clock); }
  unitsOf(team) { const o = []; for (const e of this.ents.values()) if (e.kind === 'unit' && e.team === team && !e.dead) o.push(e); return o; }
  canPlace(team, id, x, z) { return Battle.prototype.canPlace.call(this, team, id, x, z); }
  canPlay(team, slot, x, z) { return Battle.prototype.canPlay.call(this, team, slot, x, z); }
  pocket(team) { return Battle.prototype.pocket.call(this, team); }
  // ---- my plays and emotes
  play(team, slot, x, z) {
    if (team !== 0 || this.canPlay(0, slot, x, z)) return false;
    const card = this.hands[0][slot], cost = CARDS[card].cost;
    const n = this.client.play(slot, this.mx(x), this.mz(z), card); if (!n) return false;
    this.copium[0] -= cost; this.queues[0].push(card); this.hands[0][slot] = this.queues[0].shift();
    this.pending.push({n, card, cost});
    return true;
  }
  emote(id) { return this.client.emote(id); }
}
