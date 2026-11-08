// MEME ROYALE — the battle rules, no rendering. One Battle = one match between team 0 (BULLS, bottom, z high) and team 1
// (BEARS, top, z low). Fixed step (Battle.DT); the renderer interpolates between steps with e.px/e.pz and reads `events`.
import {CARDS, TOWERS, MATCH, LVL_STEP, regenMult} from './data.js';

export const ARENA = {w: 18, h: 32, river: [15, 17], bridges: [3.5, 14.5], bridgeHalf: 1.5};
const [RZ0, RZ1] = ARENA.river;

export const TOWER_POS = [
  [{type: 'rig', x: 3.5, z: 25.5, lane: 0}, {type: 'rig', x: 14.5, z: 25.5, lane: 1}, {type: 'hq', x: 9, z: 29.5, lane: -1}],
  [{type: 'rig', x: 3.5, z: 6.5, lane: 0}, {type: 'rig', x: 14.5, z: 6.5, lane: 1}, {type: 'hq', x: 9, z: 2.5, lane: -1}],
];

const PROJ_SPEED = {baguette: 15, laugh: 15, matcha: 14, rocket: 16, laser: 34, cannon: 24, spam: 20, zap: 60, magic: 15, acorn: 9, yarn: 13, star: 15, holy: 15, gas: 11, bubble: 9, snipe: 42, page: 14};
const FORMATION = {1: [[0, 0]], 2: [[-0.5, 0], [0.5, 0]], 3: [[0, -0.5], [-0.5, 0.4], [0.5, 0.4]], 4: [[-0.4, -0.4], [0.4, -0.4], [-0.4, 0.4], [0.4, 0.4]]};
// a swarm (more than 4): one in the middle, rings of 6, 12... around it, the last ring spread evenly
export function formation(n) {
  if (FORMATION[n]) return FORMATION[n];
  const out = [[0, 0]]; let left = n - 1, ring = 1;
  while (left > 0) { const m = Math.min(left, 6 * ring); for (let k = 0; k < m; k++) { const a = (k / m + ring * 0.13) * Math.PI * 2; out.push([Math.cos(a) * 0.6 * ring, Math.sin(a) * 0.6 * ring]); } left -= m; ring++; }
  return out;
}

export function mulberry(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const dist = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const sideOf = z => z <= RZ0 ? 1 : z >= RZ1 ? 0 : -1;        // which team's half a z is in (-1: the river band)
// who can hit a flyer (PNUT): towers, turrets that shoot straight (not a mortar's lob), troops that shoot (range over 2) from the
// ground, and every spell. Melee troops walk under it; its own acorns only hit the ground.
const hitsAir = a => a.kind === 'tower' || (a.kind === 'bld' && !a.lob) || (a.kind === 'unit' && !a.air && a.range >= 2);
const reach = (a, e) => !e.air || hitsAir(a);
// how hard something hits now: WOJAK's gloom takes a share off (weakT, weakK)
const pow = e => e.weakT > 0 ? e.weakK : 1;
// standing towers and buildings are solid. (FAR: a squared distance this far over the limit decides without the square root, whatever the
// rounding: the server runs thousands of steps a second, and Math.hypot, the slowest thing in them, then only runs for what is close.)
const FAR = 1.000001;
const solid = (u, t) => {
  const dx = u.x - t.x, dz = u.z - t.z, m = t.r + u.r * 0.8; if (dx * dx + dz * dz > m * m * FAR) return;
  const d = Math.hypot(dx, dz);
  if (d < m) { const k = d > 1e-4 ? (m - d) / d : 0; u.x += dx * k; u.z += (d > 1e-4 ? dz * k : m); }
};
const cut = (L, e) => { const i = L.indexOf(e); if (i >= 0) L.splice(i, 1); };
// every entity has this one object shape, whatever its kind and card: the loops of a step read them all, and a single shape is what makes those reads fast
// (a field an entity doesn't use is undefined, as if it were not there; one missing from this list still works, only slower)
class Ent {
  kind; type; team; x; z; lane; r; hp; max; dmg; hs; range; cd; target; active; building; h; id; px; pz; card; speed; sight; mass; bOnly; jumper;
  beam; heal; healLand; slam; state; st; retarget; atkT; atkHit; face; slowT; slowK; stunT; rageT; beamT; beamOn; healT; revived; seenBy; moving;
  airT; hitAt; spawnT; life; proj; hide; decay; mineT; hidden; upT; frozenT; aim; born; splash; slow; S; t; live; fired; lastHit; wave; waveT;
  from; y; sx; sz; tx; tz; age; aa; minRange; lob; swing; run; n; charging; model; hitSfx; pounce; tick; ticks; dead; spawn; blink; blinkT; surprise;
  ht; hn; mine; weaken; weakTick; rolled; hit; dir; deathSpawn; weakT; weakK; burn; kamikaze; fire; air; fireId; src; frenzy; revive; frenOn; fren;
  sumN; sumT; noStun; healN; trail; trailT; trailX; trailZ; knock; spin; pushX; pushZ; pushT; beamTick; tint; charge; towerK;
  shield; shieldT; guardT; guardK; fearT; rootT; berserk; mad; dash; quake; trap; trapT; pulse; pulseT; mend; mendT; burrow; burrowT; dug; digT; cloud; deathZone; deathBoom; siege; setup; anywhere; clone;
}

export function statsFor(id, lvl = 1) {
  const c = CARDS[id], k = 1 + LVL_STEP * (lvl - 1);
  if (c.type === 'unit') { const u = c.unit; return {...u, hp: Math.round(u.hp * k), dmg: Math.round(u.dmg * k),
    beam: u.beam && u.beam.map(v => Math.round(v * k)), heal: u.heal && [Math.round(u.heal[0] * k), u.heal[1]], healLand: u.healLand && Math.round(u.healLand * k), slam: u.slam && [Math.round(u.slam[0] * k), u.slam[1]],
    pulse: u.pulse && [Math.round(u.pulse[0] * k), u.pulse[1], u.pulse[2]], mend: u.mend && [Math.round(u.mend[0] * k), Math.round(u.mend[1] * k), u.mend[2], u.mend[3], u.mend[4]], deathBoom: u.deathBoom && [Math.round(u.deathBoom[0] * k), u.deathBoom[1]]}; }
  if (c.type === 'building') { const b = c.bld; return {...b, hp: Math.round(b.hp * k), dmg: b.dmg && Math.round(b.dmg * k), beam: b.beam && b.beam.map(v => Math.round(v * k)), deathBoom: b.deathBoom && [Math.round(b.deathBoom[0] * k), b.deathBoom[1]]}; }
  const s = c.spell; return {...s, dmg: s.dmg && Math.round(s.dmg * k), dps: s.dps && Math.round(s.dps * k), ramp: s.ramp && Math.round(s.ramp * k), heal: s.heal && Math.round(s.heal * k)};
}

export class Battle {
  static DT = 1 / 30;
  constructor({decks, levels = [{}, {}], seed = Date.now(), towerLvl = [1, 1], timeScale = 1} = {}) {
    this.rand = mulberry(seed);
    this.levels = levels;
    this.ents = new Map(); this.nextId = 1;
    this.all = []; this.units = []; this.walls = [];   // (ents as lists, in its order, for the loops of every step: walls are the towers, then the buildings)
    this.events = [];
    this.t = 0; this.clock = MATCH.time; this.phase = 'play';          // 'play' | 'overtime' | 'tiebreak' | 'end'
    this.overdose = false; this.winner = null; this.over = false;
    this.copium = [MATCH.startCopium, MATCH.startCopium];
    this.ws = [0, 0];
    this.spent = [0, 0]; this.played = [[], []];
    this.hands = []; this.queues = [];
    for (let s = 0; s < 2; s++) {
      const d = [...decks[s]]; for (let i = d.length - 1; i > 0; i--) { const j = Math.floor(this.rand() * (i + 1)); [d[i], d[j]] = [d[j], d[i]]; }
      this.hands.push(d.slice(0, 4)); this.queues.push(d.slice(4));
    }
    this.towers = [[], []];
    for (let s = 0; s < 2; s++) for (const p of TOWER_POS[s]) {
      const T = TOWERS[p.type], k = 1 + LVL_STEP * (towerLvl[s] - 1);
      const e = this.add({kind: 'tower', type: p.type, team: s, x: p.x, z: p.z, lane: p.lane, r: T.r, hp: Math.round(T.hp * k), max: Math.round(T.hp * k),
        dmg: Math.round(T.dmg * k), hs: T.hs, range: T.range, cd: 0, target: null, active: p.type === 'rig', building: true, h: T.h});
      this.towers[s].push(e);
    }
  }
  add(o) { const e = Object.assign(new Ent(), o); e.id = this.nextId++; e.px = e.x; e.pz = e.z; this.ents.set(e.id, e); this.all.push(e); if (e.kind === 'unit') this.units.push(e); else if (e.kind === 'tower' || e.kind === 'bld') this.walls.push(e); return e; }
  remove(e) { this.ents.delete(e.id); cut(this.all, e); if (e.kind === 'unit') cut(this.units, e); else if (e.kind === 'bld') cut(this.walls, e); }
  emit(type, o = {}) { this.events.push({t: this.t, ...o, type}); }   // (type last: a payload can't overwrite it)
  next(team) { return this.queues[team][0]; }
  lvl(team, id) { return this.levels[team][id] || 1; }

  // ---------- placement
  // where a team may drop a unit: its own half (outside the tower blocks), plus the pocket of a lane whose enemy rig fell
  canPlace(team, id, x, z) {
    const c = CARDS[id]; if (!c) return 'no card';
    if (x < 0.5 || x > 17.5 || z < 0.5 || z > 31.5) return 'out';
    if (c.type === 'spell') return null;
    for (const b of this.ents.values()) if (b.kind === 'bld' && !b.dead && Math.abs(x - b.x) < b.r + 0.6 && Math.abs(z - b.z) < b.r + 0.6) return 'building';
    for (const s of [0, 1]) for (const t of this.towers[s]) if (!t.dead) {
      const half = t.type === 'hq' ? 2.0 : 1.5; if (Math.abs(x - t.x) < half && Math.abs(z - t.z) < half) return 'tower';
    }
    if (z > RZ0 - 0.01 && z < RZ1 + 0.01) return 'river';
    const own = team === 0 ? z > RZ1 : z < RZ0;
    if (own || c.bld?.anywhere) return null;                  // (BACKDOOR: anywhere at all)
    // the pocket: up to 4 tiles past the river on a lane whose enemy rig is down
    const enemy = this.towers[1 - team], lane = x < 9 ? 0 : 1, depth = team === 0 ? RZ0 - z : z - RZ1;
    if (enemy[lane].dead && depth <= 4) return null;
    return 'enemy side';
  }
  pocket(team) { const e = this.towers[1 - team]; return [e[0].dead, e[1].dead]; }
  canPlay(team, slot, x, z) {
    const id = this.hands[team][slot]; if (!id || this.over || this.phase === 'tiebreak') return 'no';
    if (this.copium[team] < CARDS[id].cost) return 'copium';
    return this.canPlace(team, id, x, z);
  }
  play(team, slot, x, z) {
    if (this.canPlay(team, slot, x, z)) return false;
    const id = this.hands[team][slot], c = CARDS[id];
    this.copium[team] -= c.cost; this.spent[team] += c.cost; this.played[team].push({id, t: this.t, x, z});
    this.queues[team].push(id); this.hands[team][slot] = this.queues[team].shift();
    this.emit('play', {team, card: id, x, z, slot});
    if (c.type === 'spell') this.castSpell(team, id, x, z);
    else if (c.type === 'building') this.build(team, id, x, z);
    else this.deploy(team, id, x, z);
    return true;
  }
  // opts: n (how many), instant (out of a hut / a grave / a dead house: no drop), lvl (the level of the card that made them)
  deploy(team, id, x, z, opts = {}) {
    const S = statsFor(id, opts.lvl ?? this.lvl(team, id)), n = opts.n ?? S.n ?? 1, F = formation(n), flip = team === 0 ? 1 : -1, out = [];
    for (let i = 0; i < n; i++) {
      const [ox, oz] = F[i], ux = clamp(x + ox, S.r, ARENA.w - S.r), uz = clamp(z + oz * flip, S.r, ARENA.h - S.r);
      const u = this.add({kind: 'unit', card: id, team, x: ux, z: uz, ...S, max: S.hp, state: 'deploy', st: opts.instant ? 0.05 : MATCH.deployTime + i * (n > 4 ? 0.03 : 0.08),
        target: null, retarget: 0, atkT: -1, atkHit: false, face: team === 0 ? Math.PI : 0, slowT: 0, slowK: 1, stunT: 0, rageT: 0, beamT: 0, beamOn: null,
        healT: 0, revived: false, seenBy: new Set(), moving: false, airT: 0, hitAt: (S.range > 1.5 ? 0.3 : 0.35) * S.hs, spawnT: this.t});
      if (S.beam) u.hitAt = 0;
      out.push(u); this.emit('spawn', {id: u.id, card: id, team, x: ux, z: uz, i, n, fromDeath: !!opts.instant});
    }
    return out;
  }

  // ---------- buildings: dropped on my side, solid, a target for everyone (tanks included), they lose health over their life
  build(team, id, x, z) {
    const S = statsFor(id, this.lvl(team, id));
    const b = this.add({kind: 'bld', card: id, team, x, z, ...S, max: S.hp, building: true, state: 'deploy', st: S.setup || MATCH.deployTime, decay: S.hp / S.life, cd: 0, target: null,
      mineT: S.mine || 0, spawnT: S.spawn ? 1.2 : 0, hidden: false, upT: 0, frozenT: 0, aim: team === 0 ? Math.PI : 0, born: this.t});
    this.emit('spawn_bld', {id: b.id, card: id, team, x, z});
    return b;
  }
  bldTick(b, dt) {
    if (b.state === 'deploy') { b.st -= dt; if (b.st <= 0) { b.state = 'up'; b.hidden = !!b.hide; this.emit('landed', {id: b.id, card: b.card, x: b.x, z: b.z}); } return; }
    if (b.weakT > 0) b.weakT -= dt;
    b.hp -= b.decay * dt; if (b.hp <= 0) return this.kill(b, {});
    if (b.frozenT > 0) { b.frozenT -= dt; return; }
    if (b.mine) {               // MINING RIG: a COPIUM now and then
      b.mineT -= dt; if (b.mineT <= 0) { b.mineT += b.mine; this.copium[b.team] = Math.min(MATCH.maxCopium, this.copium[b.team] + 1); this.emit('mined', {id: b.id, team: b.team, x: b.x, z: b.z}); }
      return;
    }
    if (b.spawn) {              // a hut (MEME MINT, TROLL FARM): a troop out of the front door now and then
      b.spawnT -= dt; if (b.spawnT <= 0) { b.spawnT += b.spawn[2]; this.spawnFrom(b, b.spawn[0], b.spawn[1]); }
      return;
    }
    // a turret: the nearest troop in range, kept until it leaves or falls. A mortar (lob) can't hit what is too close and
    // also lobs at buildings and towers (troops first)
    b.cd -= dt;
    const ok = e => { const d = dist(b, e) - e.r; return d <= b.range && (!b.minRange || d >= b.minRange) && reach(b, e); };
    let tg = b.target ? this.ents.get(b.target) : null;
    if (tg && (tg.dead || tg.state === 'down' || tg.hidden || !ok(tg))) tg = null;
    if (!tg) { let bd = Infinity; for (const e of this.ents.values()) if (e.team !== b.team && !e.dead && e.state !== 'down' && !e.hidden && (e.kind === 'unit' ? e.state !== 'deploy' : (b.lob || b.siege) && (e.kind === 'tower' || e.kind === 'bld')) && ok(e)) { const d = dist(b, e) - e.r + (e.kind === 'unit' ? 0 : 3); if (d < bd) { bd = d; tg = e; } } }
    b.target = tg ? tg.id : null;
    if (tg) b.aim = Math.atan2(tg.x - b.x, tg.z - b.z);
    if (b.hide) {               // HONEYPOT: up while there is something to zap, back underground a second after
      if (tg) { if (b.hidden) { b.hidden = false; b.cd = Math.max(b.cd, 0.45); this.emit('popup', {id: b.id, x: b.x, z: b.z}); } b.upT = 1; }
      else if (!b.hidden && (b.upT -= dt) <= 0) { b.hidden = true; this.emit('hide', {id: b.id}); }
    }
    if (b.beam) {               // LASER EYES: a stare that ramps on one target and starts over on the next
      if (!tg) { if (b.beamOn) { b.beamOn = null; b.beamT = 0; this.emit('beam_off', {id: b.id}); } return; }
      if (b.beamOn !== tg.id) { b.beamOn = tg.id; b.beamT = 0; b.beamTick = 0.15; this.emit('beam', {id: b.id, target: tg.id}); }
      b.beamT += dt; b.beamTick -= dt;
      if (b.beamTick <= 0) { b.beamTick += b.hs; const st = b.beamT < 2 ? 0 : b.beamT < 4 ? 1 : 2; this.damage(tg, Math.round(b.beam[st] * pow(b)), {team: b.team, beam: st}); }
      return;
    }
    if (tg && b.cd <= 0) {
      b.cd = b.hs;
      if (b.lob) {              // BAG LAUNCHER: lobbed at the spot the target stands on now; the flight takes longer the further it goes
        const d = dist(b, tg);
        this.add({kind: 'proj', proj: b.proj, team: b.team, from: b.id, card: b.card, x: b.x, z: b.z, y: b.h * 0.8, sx: b.x, sz: b.z, target: null, tx: tg.x, tz: tg.z, dmg: Math.round(b.dmg * pow(b)), splash: b.splash, speed: d / (0.9 + d * 0.05), age: 0, lob: true});
      } else this.add({kind: 'proj', proj: b.proj, team: b.team, from: b.id, card: b.card, x: b.x, z: b.z, y: b.h * 0.8, sx: b.x, sz: b.z, target: tg.id, tx: tg.x, tz: tg.z, dmg: Math.round(b.dmg * pow(b)), splash: b.splash || 0, speed: PROJ_SPEED[b.proj] || 14, age: 0, aa: true});
      this.emit('turret_shot', {id: b.id, target: tg.id, proj: b.proj});
    }
  }
  spawnFrom(b, id, n) {
    const us = this.deploy(b.team, id, b.x, b.z + (b.team === 0 ? -1 : 1) * (b.r + 0.5), {n, instant: true, lvl: this.lvl(b.team, b.card)});
    for (const u of us) u.st = 0.3;
    this.emit('hut_spawn', {id: b.id, card: b.card, x: b.x, z: b.z});
  }

  // ---------- spells
  castSpell(team, id, x, z) {
    const S = statsFor(id, this.lvl(team, id));
    this.emit('spell', {team, card: id, x, z, r: S.r, delay: S.delay, dur: S.dur || 0});
    this.add({kind: 'spell', card: id, team, x, z, r: S.r, S, t: S.delay, live: S.dur || 0, fired: false});
  }
  spellTick(sp, dt) {
    if (!sp.fired) {
      sp.t -= dt; if (sp.t > 0) return;
      sp.fired = true;
      const S = sp.S;
      if (S.bolts) this.bolts(sp);
      else if (S.dmg && !S.roll) {   // an area hit: FUD, RUG PULL, AIRDROP, COLD WALLET, GOD CANDLE; DOWNVOTES in waves
        this.areaHit(sp);
        if (S.waves > 1) { sp.wave = 1; sp.waveT = S.gap; sp.live = S.gap * (S.waves - 1) + 0.05; }
      }
      if (S.summon) { sp.sumN = 0; sp.sumT = 0; }
      if (S.clone) this.fork(sp);
      if (S.guard) {                 // DIAMOND HANDS: my troops in the area, once, for its whole time
        for (const e of this.units) if (e.team === sp.team && !e.dead && e.state !== 'down' && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r + e.r * 0.5) { e.guardT = S.guard[1]; e.guardK = S.guard[0]; }
        this.emit('spell_hit', {card: sp.card, team: sp.team, x: sp.x, z: sp.z, r: sp.r});
      }
      if (S.roll) { sp.rolled = 0; sp.hit = new Set(); sp.dir = sp.team === 0 ? -1 : 1; sp.live = S.roll / S.speed + 0.05; }
      if (!sp.live) { this.remove(sp); return; }
    }
    sp.live -= dt;
    if (sp.S.drift) sp.z = clamp(sp.z + (sp.team === 0 ? -1 : 1) * sp.S.drift * dt, 0.5, ARENA.h - 0.5);   // FART: the cloud drifts toward the enemy
    if (sp.wave && sp.wave < sp.S.waves) { sp.waveT -= dt; if (sp.waveT <= 0) { sp.waveT += sp.S.gap; sp.wave++; this.areaHit(sp); } }
    if (sp.S.summon) {             // DEAD COINS: one troop at a time out of the ground, anywhere in the area, over the spell's life
      const [id, n] = sp.S.summon; sp.sumT -= dt;
      while (sp.sumT <= 0 && sp.sumN < n) {
        sp.sumT += sp.S.dur / n; sp.sumN++;
        const a = this.rand() * Math.PI * 2, d = Math.sqrt(this.rand()) * sp.r;
        for (const u of this.deploy(sp.team, id, sp.x + Math.cos(a) * d, sp.z + Math.sin(a) * d, {n: 1, instant: true, lvl: this.lvl(sp.team, sp.card)})) { u.st = 0.45; this.keepOut(u); }
      }
    }
    if (sp.S.pull) for (const e of this.units) {   // LIQUIDITY DRAIN: everything in it slides to the middle, the heavy and the unpushable slowly
      if (e.team === sp.team || e.dead || e.state === 'down' || e.state === 'deploy') continue;
      const dx = sp.x - e.x, dz = sp.z - e.z, d = Math.hypot(dx, dz); if (d > sp.r + e.r * 0.5 || d < 0.2) continue;
      const k = sp.S.pull * dt * (e.mass >= 18 || e.noStun ? 0.35 : 1) / d; e.x += dx * k; e.z += dz * k; this.keepOut(e);
    }
    if (sp.S.snare) {              // MICHI's trap: all that stands on it when the first one walks in is tangled, and it's used up
      let any = false; for (const e of this.units) if (e.team !== sp.team && !e.dead && !e.air && !e.noStun && !e.dug && e.state === 'move' && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r + e.r * 0.5) { e.rootT = sp.S.snare; any = true; this.emit('snared', {id: e.id, x: e.x, z: e.z}); }
      if (any) sp.live = 0;
    }
    if (sp.S.heal) {               // HOPIUM: four small heals a second to my troops inside, the ring drawn once a second
      sp.ht = (sp.ht ?? 0) - dt;
      if (sp.ht <= 0) { sp.ht += 0.25; sp.hn = ((sp.hn || 0) + 1) % 4;
        for (const e of this.ents.values()) if (e.kind === 'unit' && e.team === sp.team && !e.dead && e.state !== 'down' && e.state !== 'deploy' && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r + e.r * 0.5) this.heal(e, sp.S.heal / 4, sp.hn === 1); }
    }
    if (sp.card === 'pump') for (const e of this.ents.values()) if (e.kind === 'unit' && e.team === sp.team && !e.dead && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r) e.rageT = 0.25;
    if (sp.S.dps) {                // LIQUIDATION: a tick a second, and everything in it is slowed; GAS FEES: each tick costs more (ramp)
      sp.tick = (sp.tick ?? 0) - dt;
      if (sp.S.slow) for (const e of this.ents.values()) if (e.kind === 'unit' && e.team !== sp.team && !e.dead && !(sp.S.ground && e.air) && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r) { e.slowT = Math.max(e.slowT, 0.3); e.slowK = Math.min(e.slowK, sp.S.slow); }
      if (sp.tick <= 0) { sp.tick += 1; const dps = sp.S.dps + (sp.S.ramp || 0) * (sp.ticks || 0); sp.ticks = (sp.ticks || 0) + 1;
        for (const e of [...this.ents.values()]) if ((e.kind === 'unit' || e.kind === 'tower' || e.kind === 'bld') && e.team !== sp.team && !e.dead && e.state !== 'down' && !(sp.S.ground && e.air) && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r + e.r * 0.4)
          this.damage(e, e.kind === 'tower' ? Math.round(dps * sp.S.tower) : e.kind === 'bld' && sp.S.bldK ? Math.round(dps * sp.S.bldK) : dps, {team: sp.team, spell: sp.card, tick: true}); }
    }
    if (sp.S.roll) {               // BAN HAMMER: rolls forward, hits each thing once, knocks troops back
      const step = sp.S.speed * dt; sp.z += sp.dir * step; sp.rolled += step;
      for (const e of [...this.ents.values()]) {
        if (e.team === sp.team || e.dead || e.air || sp.hit.has(e.id) || (e.kind !== 'unit' && e.kind !== 'tower' && e.kind !== 'bld') || e.state === 'down') continue;
        if (Math.abs(e.x - sp.x) > sp.r + e.r * 0.5 || Math.abs(e.z - sp.z) > 0.7 + (e.kind === 'unit' ? 0 : e.r * 0.6)) continue;
        sp.hit.add(e.id);
        this.damage(e, e.kind === 'tower' ? Math.round(sp.S.dmg * sp.S.tower) : sp.S.dmg, {team: sp.team, spell: sp.card});
        if (e.kind === 'unit' && !e.dead && e.mass < 18) { e.z += sp.dir * sp.S.knock; this.keepOut(e); e.atkT = -1; }
        this.emit('hammer_hit', {x: e.x, z: e.z});
      }
      if (sp.rolled >= sp.S.roll || sp.z < 0.3 || sp.z > 31.7) sp.live = 0;
    }
    if (sp.live <= 0) { this.remove(sp); this.emit('spell_end', {id: sp.id, card: sp.card}); }
  }
  areaHit(sp) {
    const S = sp.S;
    for (const e of this.ents.values()) {
      if (e.team === sp.team || e.dead || e.dug || (e.kind !== 'unit' && e.kind !== 'tower' && e.kind !== 'bld') || e.state === 'down') continue;
      if (Math.hypot(e.x - sp.x, e.z - sp.z) > sp.r + (e.kind === 'unit' ? e.r * 0.5 : e.r * 0.6)) continue;
      this.damage(e, e.kind === 'tower' ? Math.round(S.dmg * S.tower) : S.dmg, {team: sp.team, spell: sp.card});
      if (e.dead) continue;
      if (S.freeze) { e.frozenT = Math.max(e.frozenT || 0, S.freeze); if (e.kind === 'unit') { e.stunT = Math.max(e.stunT, S.freeze); e.atkT = -1; e.beamT = 0; } }
      if (e.kind === 'unit') {
        if (S.stun && !e.noStun) { e.stunT = Math.max(e.stunT, S.stun); e.atkT = -1; e.beamT = 0; }
        if (S.knock && !e.noStun && e.mass < 18) { const d = Math.hypot(e.x - sp.x, e.z - sp.z) || 1; e.x += (e.x - sp.x) / d * S.knock; e.z += (e.z - sp.z) / d * S.knock; this.keepOut(e); e.atkT = -1; }
        if (S.fear && !e.noStun && e.mass < 18) { e.fearT = Math.max(e.fearT || 0, S.fear); this.emit('feared', {id: e.id, x: e.x, z: e.z}); }
      }
    }
    this.emit('spell_hit', {card: sp.card, team: sp.team, x: sp.x, z: sp.z, r: sp.r, wave: sp.wave || 0});
  }
  // HARD FORK: a copy beside each of my troops in the area (never of a copy): the same hits, one hit point, nothing left to come back with
  fork(sp) {
    let left = 15; const list = this.units.slice();
    for (const e of list) {
      if (e.team !== sp.team || e.dead || e.clone || e.dug || e.state === 'down' || e.state === 'deploy' || Math.hypot(e.x - sp.x, e.z - sp.z) > sp.r + e.r * 0.5) continue;
      if (!left--) break;
      const a = this.rand() * Math.PI * 2, [u] = this.deploy(e.team, e.card, e.x + Math.cos(a) * (e.r + 0.3), e.z + Math.sin(a) * (e.r + 0.3), {n: 1, instant: true, lvl: this.lvl(e.team, e.card)});
      u.hp = u.max = 1; u.clone = true; u.st = 0.15; u.revive = 0; u.deathSpawn = null; u.deathZone = null; u.deathBoom = null; u.pulse = null; u.mend = null; u.heal = null; u.healLand = 0; u.slam = null; this.keepOut(u);
    }
    this.emit('spell_hit', {card: sp.card, team: sp.team, x: sp.x, z: sp.z, r: sp.r});
  }
  // MARGIN CALL: the N toughest things in the area (troops, buildings, towers), a bolt each
  bolts(sp) {
    const S = sp.S, hits = [];
    for (const e of this.ents.values()) if (e.team !== sp.team && !e.dead && !e.dug && e.state !== 'down' && (e.kind === 'unit' || e.kind === 'tower' || e.kind === 'bld') && Math.hypot(e.x - sp.x, e.z - sp.z) <= sp.r + e.r * 0.5) hits.push(e);
    hits.sort((a, b) => b.hp - a.hp || a.id - b.id);
    for (const e of hits.slice(0, S.bolts)) {
      this.emit('bolt', {card: sp.card, id: e.id, x: e.x, z: e.z});
      this.damage(e, e.kind === 'tower' ? Math.round(S.dmg * S.tower) : S.dmg, {team: sp.team, spell: sp.card});
      if (!e.dead && e.kind === 'unit' && S.stun && !e.noStun) { e.stunT = Math.max(e.stunT, S.stun); e.atkT = -1; e.beamT = 0; }
    }
    this.emit('spell_hit', {card: sp.card, team: sp.team, x: sp.x, z: sp.z, r: sp.r});
  }

  // ---------- damage
  damage(e, amt, src = {}) {
    if (e.dead || e.dug || amt <= 0 || this.over || e.state === 'down') return;
    if (e.kind === 'tower' && e.type === 'hq' && !e.active) this.wake(e);
    if (e.guardT > 0) amt = Math.round(amt * e.guardK);    // DIAMOND HANDS
    e.lastHit = this.t;
    this.emit('dmg', {id: e.id, amt, x: e.x, z: e.z, kind: e.kind, crit: src.crit, spell: src.spell});
    if (e.shield > 0) {                                     // APU's shield: it goes first
      const a = Math.min(e.shield, amt); e.shield -= a; amt -= a;
      if (e.shield <= 0) this.emit('shield_break', {id: e.id, x: e.x, z: e.z});
      if (amt <= 0) return;
    }
    e.hp -= amt;
    if (e.hp <= 0) this.kill(e, src);
  }
  heal(e, amt, show = true) { if (e.dead || e.hp >= e.max) return; const a = Math.min(amt, e.max - e.hp); e.hp += a; if (show) this.emit('heal', {id: e.id, amt: a}); }
  healAround(u, amt, r, ring) {
    let any = false;
    for (const e of this.ents.values()) if (e.kind === 'unit' && e.team === u.team && !e.dead && e.state !== 'down' && e.state !== 'deploy' && e.hp < e.max && dist(u, e) <= r) { this.heal(e, amt, ring); any = true; }
    if (any && ring) this.emit('heal_pulse', {id: u.id, r, big: amt >= 100});
  }
  // BUBBLE MACHINE's biggest bubble, BOME's last page: bursts as it falls (ground only)
  burst(e) {
    const [d, r] = e.deathBoom; for (const o of this.enemiesOf(e.team)) if (!o.air && dist(o, e) - o.r * 0.5 <= r) this.damage(o, o.kind === 'tower' ? Math.round(d * 0.35) : d, {team: e.team});
    this.emit('boom', {id: e.id, card: e.card, x: e.x, z: e.z, r});
  }
  wake(hq) { if (hq.active || hq.dead) return; hq.active = true; this.emit('hq_wake', {id: hq.id, team: hq.team}); }
  kill(e, src) {
    if (e.kind === 'bld') {
      e.dead = true; e.hp = 0; this.remove(e); this.emit('bld_down', {id: e.id, card: e.card, team: e.team, x: e.x, z: e.z});
      if (e.deathBoom) this.burst(e);
      if (e.deathSpawn) { const [id, n] = e.deathSpawn; for (const u of this.deploy(e.team, id, e.x, e.z, {n, instant: true, lvl: this.lvl(e.team, e.card)})) u.st = 0.35; }
      return;
    }
    if (e.kind === 'unit') {
      if (e.revive && !e.revived) { e.revived = true; e.hp = 0; e.state = 'down'; e.st = 1.2; e.target = null; e.atkT = -1; this.emit('down', {id: e.id}); return; }
      e.dead = true; e.hp = 0; this.remove(e); this.emit('die', {id: e.id, card: e.card, team: e.team, x: e.x, z: e.z});
      if (e.deathBoom) this.burst(e);
      if (e.deathZone) this.zone(e, e.deathZone[0], e.x, e.z, e.deathZone.slice(1));   // BOME's paper storm
      if (e.deathSpawn) { const [id, n] = e.deathSpawn; const us = this.deploy(e.team, id, e.x, e.z, {n, instant: true}); for (const u of us) u.st = 0.35; }
      return;
    }
    if (e.kind === 'tower') {
      e.dead = true; e.hp = 0; e.target = null;
      const other = 1 - e.team;
      this.ws[other] = e.type === 'hq' ? 3 : Math.min(3, this.ws[other] + 1);
      this.emit('tower_down', {id: e.id, team: e.team, tower: e.type, x: e.x, z: e.z});
      this.emit('w', {team: other, ws: this.ws[other]});
      if (e.type === 'rig') this.wake(this.towers[e.team][2]);
      // knock every unit off the tower's footprint (the ruin is walkable only around it)
      if (e.type === 'hq') this.finish(other, 'hq');
      else if (this.phase === 'overtime') this.finish(other, 'overtime');
      else if (this.phase === 'tiebreak') this.finish(other, 'tiebreak');
    }
  }
  finish(winner, why) {
    if (this.over) return;
    this.over = true; this.phase = 'end'; this.winner = winner; this.why = why;
    // the losing side's remaining towers crumble on an HQ win (as the score says 3)
    this.emit('end', {winner, why, ws: [...this.ws]});
  }

  // ---------- the step
  step(dt = Battle.DT) {
    if (this.over) { this.t += dt; for (const e of this.ents.values()) { e.px = e.x; e.pz = e.z; } return; }
    this.t += dt;
    // clock and copium
    this.clock -= dt;
    if (this.phase === 'play' && !this.overdose && this.clock <= MATCH.overdoseAt) { this.overdose = true; this.emit('phase', {phase: 'overdose'}); }
    if (this.phase === 'tiebreak') return this.tiebreak(dt);
    if (this.phase === 'overtime' && !this.triple && this.clock <= MATCH.tripleAt) { this.triple = true; this.emit('phase', {phase: 'triple'}); }
    if (this.clock <= 0) {
      if (this.phase === 'play') {
        if (this.ws[0] !== this.ws[1]) return this.finish(this.ws[0] > this.ws[1] ? 0 : 1, 'time');
        this.phase = 'overtime'; this.clock = MATCH.overtime; this.emit('phase', {phase: 'overtime'});
      } else if (this.phase === 'overtime') {
        if (this.ws[0] !== this.ws[1]) return this.finish(this.ws[0] > this.ws[1] ? 0 : 1, 'time');
        // the TIEBREAKER: the weakest standing tower (in hit points) decides; the same on both sides is a draw
        const low = s => Math.min(...this.towers[s].filter(t => !t.dead).map(t => t.hp));
        const a = low(0), b = low(1);
        if (Math.abs(a - b) < 0.5) return this.finish(-1, 'draw');
        this.phase = 'tiebreak'; this.clock = 0; this.drain = Math.min(a, b) / MATCH.tiebreakS; this.emit('phase', {phase: 'tiebreak'});
        return;
      }
    }
    const mult = regenMult(this.phase, this.clock, this.overdose);
    for (let s = 0; s < 2; s++) this.copium[s] = Math.min(MATCH.maxCopium, this.copium[s] + dt / MATCH.regen * mult);

    const list = this.all.slice();
    for (const e of list) { e.px = e.x; e.pz = e.z; }
    for (const e of list) {
      if (e.dead || !this.ents.has(e.id)) continue;
      if (e.kind === 'unit') this.unitTick(e, dt);
      else if (e.kind === 'tower') this.towerTick(e, dt);
      else if (e.kind === 'bld') this.bldTick(e, dt);
      else if (e.kind === 'proj') this.projTick(e, dt);
      else if (e.kind === 'spell') this.spellTick(e, dt);
      if (this.over) return;
    }
    this.separate();
  }

  // the tiebreaker: the battle stands still and every tower loses the same hit points each tick until the weakest falls
  tiebreak(dt) {
    for (const e of this.ents.values()) { e.px = e.x; e.pz = e.z; if (e.kind === 'unit') e.moving = false; }
    const amt = this.drain * dt;
    for (const s of [0, 1]) for (const t of this.towers[s]) if (!t.dead && !this.over) {
      t.hp -= amt; this.emit('drain', {id: t.id, amt, x: t.x, z: t.z});
      if (t.hp <= 0) this.kill(t, {});
    }
  }

  // ---------- units
  enemiesOf(team) { const o = []; for (const e of this.all) if (e.team !== team && !e.dead && (e.kind === 'unit' || e.kind === 'tower' || e.kind === 'bld') && e.state !== 'down' && !e.dug) o.push(e); return o; }
  pickTarget(u) {
    let best = null, bd = Infinity, bestT = null, bt = Infinity;
    for (const e of this.all) {
      if (e.team === u.team || e.dead || e.state === 'down' || e.hidden) continue;
      if (e.kind === 'tower' || e.kind === 'bld') {
        const d = dist(u, e) - e.r + (e.type === 'hq' ? 0.01 : 0);
        // lane preference: a unit standing in the middle column picks its own side's lane first
        const lb = e.type === 'rig' ? (((e.lane === 0) === (u.x < 9)) ? -0.02 : 0.02) : 0;
        if (d + lb < bt) { bt = d + lb; bestT = e; }
        if (d <= u.sight && d < bd) { bd = d; best = e; }
      } else if (e.kind === 'unit' && !u.bOnly && reach(u, e)) {
        const d = dist(u, e) - e.r;
        if (d <= u.sight && d < bd) { bd = d; best = e; }
      }
    }
    return best || bestT;
  }
  inRange(u, t) { const dx = u.x - t.x, dz = u.z - t.z, m = u.range + 0.05 + u.r + t.r; if (dx * dx + dz * dz > m * m * FAR) return false; return Math.hypot(dx, dz) - u.r - t.r <= u.range + 0.05; }
  unitTick(u, dt) {
    if (u.state === 'deploy') {
      u.st -= dt; if (u.st > 0) return;
      u.state = 'move'; this.emit('landed', {id: u.id, card: u.card, x: u.x, z: u.z});
      if (u.healLand) this.healAround(u, u.healLand, u.heal[1] + 0.5, true);
      if (u.slam) { const [d, r] = u.slam; for (const e of this.enemiesOf(u.team)) if (reach(u, e) && dist(u, e) - e.r * 0.5 <= r) this.damage(e, e.kind === 'tower' ? Math.round(d * 0.4) : d, {team: u.team});
        this.emit('slam', {x: u.x, z: u.z, r, team: u.team}); }
      return;
    }
    if (u.state === 'down') {
      u.st -= dt; if (u.st > 0) return;
      u.state = 'move'; u.hp = Math.round(u.max * u.revive); this.emit('revive', {id: u.id}); return;
    }
    if (u.dug) { this.tunnel(u, dt); return; }
    // modifiers
    if (u.slowT > 0) { u.slowT -= dt; if (u.slowT <= 0) u.slowK = 1; }
    if (u.rageT > 0) u.rageT -= dt;
    if (u.weakT > 0) u.weakT -= dt;
    if (u.blinkT > 0) u.blinkT -= dt;
    if (u.guardT > 0) u.guardT -= dt;
    if (u.burrowT > 0) u.burrowT -= dt;
    if (u.shieldT > 0) { u.shieldT -= dt; if (u.shieldT <= 0 && u.shield > 0) { u.shield = 0; this.emit('shield_break', {id: u.id, x: u.x, z: u.z}); } }   // (APU's shield fades)
    if (u.rootT > 0) u.rootT -= dt;
    if (u.trapT > 0) u.trapT -= dt;
    // FLOKI: badly hurt, he goes berserk, and stays so
    if (u.berserk && !u.mad && u.hp <= u.max * u.berserk[0]) { u.mad = true; this.emit('berserk', {id: u.id, x: u.x, z: u.z}); }
    const rate = (u.slowT > 0 ? u.slowK : 1) * (u.rageT > 0 ? 1.4 : 1) * (u.fren || 1) * (u.mad ? u.berserk[1] : 1);
    if (u.frozenT > 0) u.frozenT -= dt;
    // knocked back (BONK): slides away over a quarter second
    if (u.pushT > 0) { const k = Math.min(dt, u.pushT); u.x += u.pushX * k; u.z += u.pushZ * k; u.pushT -= dt; this.keepOut(u); }
    // NYAN CAT: a rainbow dropped under her path every trail[0] s (only once she has moved on from the last one: no pile on one spot)
    if (u.trail) { u.trailT = (u.trailT || 0) - dt; if (u.trailT <= 0 && !(Math.hypot(u.x - (u.trailX ?? -9), u.z - (u.trailZ ?? -9)) < u.trail[1] * 0.7)) {
      u.trailT = u.trail[0]; u.trailX = u.x; u.trailZ = u.z; this.zone(u, 'rainbow', u.x, u.z, u.trail.slice(1)); } }
    // WOJAK: a gloom around him, refreshed four times a second; the enemies in it hit softer
    if (u.weaken) { u.weakTick = (u.weakTick || 0) - dt; if (u.weakTick <= 0) { u.weakTick += 0.25;
      for (const e of this.ents.values()) if ((e.kind === 'unit' || e.kind === 'bld') && e.team !== u.team && !e.dead && dist(u, e) - e.r * 0.5 <= u.weaken[1]) { e.weakT = 0.4; e.weakK = u.weaken[0]; } } }
    if (u.stunT > 0) { u.stunT -= dt; u.moving = false; u.run = 0; u.charging = false; return; }
    // PANIC SELL: drops everything and runs for home
    if (u.fearT > 0) {
      u.fearT -= dt; u.atkT = -1; u.run = 0; u.charging = false; u.target = null; if (u.beamOn) { u.beamOn = null; u.beamT = 0; this.emit('beam_off', {id: u.id}); }
      u.face = u.team === 0 ? 0 : Math.PI; u.moving = !(u.rootT > 0); if (u.moving) { u.z += (u.team === 0 ? 1 : -1) * u.speed * rate * 1.2 * dt; this.keepOut(u); } return;
    }
    // PIPPIN: every few seconds a big wave of healing all around
    if (u.pulse) { u.pulseT = (u.pulseT ?? 1) - dt; if (u.pulseT <= 0) { u.pulseT = u.pulse[2]; this.healAround(u, u.pulse[0], u.pulse[1], true); } }
    // APU: every few seconds the worst hurt ally near him
    if (u.mend) { u.mendT = (u.mendT ?? 1) - dt; if (u.mendT <= 0) this.mendAlly(u); }
    // healer: four small pulses a second (it reads as a steady flow), the ring drawn once a second
    if (u.heal) { u.healT -= dt; if (u.healT <= 0) { u.healT += 0.25; u.healN = ((u.healN || 0) + 1) % 4; this.healAround(u, u.heal[0] / 4, u.heal[1], u.healN === 1); } }

    // target upkeep
    let t = u.target ? this.ents.get(u.target) : null;
    if (t && (t.dead || t.state === 'down' || t.hidden)) t = null;
    if (u.atkT >= 0) {
      // mid-swing: finish it (cancel before the impact if the target is gone)
      if (!t) { u.atkT = -1; u.charging = false; }
      else {
        u.atkT += dt * rate;
        if (!u.atkHit && u.atkT >= u.hitAt) { u.atkHit = true; if (this.inRange(u, t) || dist(u, t) - u.r - t.r <= u.range + 0.6) this.impact(u, t); }
        if (u.atkT >= u.hs) u.atkT = -1;
        else { u.moving = false; return; }
      }
    }
    u.retarget -= dt;
    if (!t || (u.retarget <= 0 && !(t && this.inRange(u, t)))) {
      u.retarget = 0.2;
      const n = this.pickTarget(u);
      if (n && (!t || n.id !== t.id)) { t = n; u.beamT = 0; }
    }
    u.target = t ? t.id : null;
    if (!t) { u.moving = false; return; }
    // WALTER: under he goes, when what he's after is close but out of arm's reach, or when he's being hit
    if (u.burrow && !(u.burrowT > 0) && !(u.rootT > 0) && !t.air && dist(u, t) - t.r <= u.burrow[0] && (!this.inRange(u, t) || this.t - (u.lastHit ?? -9) < 1)) { this.dig(u, t); return; }
    // TROLLFACE: a target within reach but not at arm's length, and he is suddenly behind it (the next hit is a surprise)
    if (u.blink && !(u.blinkT > 0) && !(u.rootT > 0) && !t.air && !this.inRange(u, t) && dist(u, t) - t.r <= u.blink[0]) this.blinkTo(u, t);

    if (this.inRange(u, t)) {
      u.moving = false;
      u.face = Math.atan2(t.x - u.x, t.z - u.z);
      if (u.beam) {   // MENSA: a beam that ramps on one target
        u.atkT = -1;
        if (u.beamOn !== t.id) { u.beamOn = t.id; u.beamT = 0; u.beamTick = 0.15; this.emit('beam', {id: u.id, target: t.id}); }
        u.beamT += dt * rate; u.beamTick -= dt * rate;
        if (u.beamTick <= 0) { u.beamTick += u.hs; const st = u.beamT < 2 ? 0 : u.beamT < 4 ? 1 : 2; this.damage(t, Math.round(u.beam[st] * pow(u)), {team: u.team, beam: st}); }
        return;
      }
      u.atkT = 0; u.atkHit = false; u.swing = (u.swing || 0) + 1; u.run = 0;
      this.emit('attack', {id: u.id, target: t.id, swing: u.swing, hs: u.hs / rate, hitAt: u.hitAt / rate});
      return;
    }
    if (u.beamOn) { u.beamOn = null; this.emit('beam_off', {id: u.id}); }
    // MICHI's yarn: tangled, it can't take a step (it still hits what it can reach)
    if (u.rootT > 0) { u.moving = false; u.run = 0; u.charging = false; return; }
    // move along the lane: to the bridge, over it, then at the target
    const way = this.waypoint(u, t), wx = way[0], wz = way[1];
    let dx = wx - u.x, dz = wz - u.z; const d = Math.hypot(dx, dz) || 1;
    dx /= d; dz /= d;
    // steer around standing towers in the way (not the one I'm going for): slide along their side
    if (!u.air) for (const tw of this.walls) {
      if (tw.dead || tw.id === t.id) continue;
      const ox = tw.x - u.x, oz = tw.z - u.z, R = tw.r + u.r + 0.8, far = R + 1.4;
      if (ox * ox + oz * oz > far * far * FAR) continue;
      const od = Math.hypot(ox, oz);
      if (od > far || od < 1e-3) continue;
      const ahead = (ox * dx + oz * dz) / od; if (ahead <= 0.05) continue;
      let px = -dz, pz = dx; const dot = px * ox + pz * oz;
      if (Math.abs(dot) < 0.05 * od) { if ((9 - u.x) * px < 0) { px = -px; pz = -pz; } } else if (dot > 0) { px = -px; pz = -pz; }
      const w = Math.min(1, (R + 1.4 - od) / 1.4) * ahead * 1.8;
      dx += px * w; dz += pz * w; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
    }
    // and around units parked in my way (fighting allies, a wall of enemies I'm not after): walk round, don't push forever.
    // A heavy unit doesn't walk round small fry: it shoves them aside (separate()), or it stalls at a crowded bridge.
    if (!u.air) for (const o of this.units) {
      if (o === u || o.dead || o.dug || o.id === t.id || o.state === 'deploy' || (o.team === u.team && o.moving) || o.mass * 3 <= u.mass) continue;
      const ox = o.x - u.x, oz = o.z - u.z, R = o.r + u.r + 0.25, far = R + 0.6;
      if (ox * ox + oz * oz > far * far * FAR) continue;
      const od = Math.hypot(ox, oz);
      if (od > far || od < 1e-3) continue;
      const ahead = (ox * dx + oz * dz) / od; if (ahead < 0.3) continue;
      let px = -dz, pz = dx; if (px * ox + pz * oz > 0) { px = -px; pz = -pz; }
      const w = Math.min(1, (R + 0.6 - od) / 0.6) * ahead * 0.9;
      dx += px * w; dz += pz * w; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
    }
    const sp = Math.min((u.charging ? u.charge[1] : u.speed) * rate * dt, d);
    u.x += dx * sp; u.z += dz * sp;
    // MOO DENG: a long enough run becomes a charge (faster, and the hit at the end of it lands twice as hard)
    if (u.charge && !u.charging) { u.run = (u.run || 0) + sp; if (u.run >= u.charge[0]) { u.charging = true; this.emit('charge', {id: u.id, x: u.x, z: u.z}); } }
    const want = Math.atan2(dx, dz); let df = want - u.face; while (df > Math.PI) df -= 2 * Math.PI; while (df < -Math.PI) df += 2 * Math.PI;
    u.face += df * Math.min(1, dt * 10);
    u.moving = true;
    if (u.jumper) { const inBand = u.z > RZ0 - 0.2 && u.z < RZ1 + 0.2; if (inBand && !this.onBridge(u.x, u.r)) u.airT = 0.15; else if (u.airT > 0) u.airT -= dt; }
    this.keepOut(u);
  }
  onBridge(x, r = 0) { for (const b of ARENA.bridges) if (Math.abs(x - b) <= ARENA.bridgeHalf - r * 0.5) return b; return null; }
  waypoint(u, t) {
    if (u.jumper || u.air) return [t.x, t.z];
    const su = sideOf(u.z), stt = sideOf(t.z);
    if (su === -1) {   // on a bridge: keep crossing toward the target's side
      const b = this.onBridge(u.x, 0) ?? ARENA.bridges[u.x < 9 ? 0 : 1];
      const goZ = stt === -1 ? t.z : (stt === 1 ? RZ0 - 0.6 : RZ1 + 0.6);
      return [clamp(t.x, b - ARENA.bridgeHalf + u.r, b + ARENA.bridgeHalf - u.r), goZ];
    }
    if (stt === -1 || su === stt) return [t.x, t.z];
    // pick the bridge that makes the shorter trip
    let best = ARENA.bridges[0], bl = Infinity;
    for (const b of ARENA.bridges) { const l = Math.hypot(u.x - b, u.z - (su === 0 ? RZ1 : RZ0)) + Math.hypot(t.x - b, t.z - (su === 0 ? RZ0 : RZ1)); if (l < bl) { bl = l; best = b; } }
    const bx = clamp(u.x, best - ARENA.bridgeHalf + u.r + 0.1, best + ARENA.bridgeHalf - u.r - 0.1);
    const entry = su === 0 ? RZ1 + 0.3 : RZ0 - 0.3;
    if (Math.abs(u.x - bx) < 0.05 && Math.abs(u.z - entry) < 1.2) return [bx, su === 0 ? RZ0 - 0.5 : RZ1 + 0.5];
    return [bx, entry];
  }
  keepOut(u) {
    u.x = clamp(u.x, u.r, ARENA.w - u.r); u.z = clamp(u.z, u.r, ARENA.h - u.r);
    if (u.air || u.dug) return;   // a flyer crosses the river anywhere and passes over towers (and WALTER under them)
    // the river: only the bridges (and BATON's jump) cross it
    if (!u.jumper && u.z > RZ0 - u.r * 0.3 && u.z < RZ1 + u.r * 0.3) {
      const b = ARENA.bridges[u.x < 9 ? 0 : 1], lo = b - ARENA.bridgeHalf + u.r * 0.6, hi = b + ARENA.bridgeHalf - u.r * 0.6;
      if (u.x >= lo - 0.6 && u.x <= hi + 0.6) u.x = clamp(u.x, lo, hi);
      else u.z = u.z < 16 ? RZ0 - u.r * 0.3 : RZ1 + u.r * 0.3;
    }
    for (const t of this.walls) if (!t.dead) solid(u, t);
  }
  separate() {
    const us = []; for (const e of this.units) if (!e.dead && !e.dug && e.state !== 'deploy') us.push(e);
    for (let i = 0; i < us.length; i++) for (let j = i + 1; j < us.length; j++) {
      const a = us[i], b = us[j], dx = b.x - a.x, dz = b.z - a.z, m = (a.r + b.r) * 0.92, d2 = dx * dx + dz * dz;
      if (d2 >= m * m || !a.air !== !b.air) continue;   // (flyers only bump flyers)
      const d = Math.sqrt(d2) || 1e-3, o = (m - d), ma = a.mass * (a.moving ? 1 : 1.6), mb = b.mass * (b.moving ? 1 : 1.6), ka = mb / (ma + mb), kb = ma / (ma + mb);
      const nx = d2 > 1e-8 ? dx / d : (a.id < b.id ? 1 : -1), nz = d2 > 1e-8 ? dz / d : 0;
      a.x -= nx * o * ka * 0.5; a.z -= nz * o * ka * 0.5; b.x += nx * o * kb * 0.5; b.z += nz * o * kb * 0.5;
    }
    for (const u of us) this.keepOut(u);
  }
  impact(u, t) {
    if (u.proj) {   // (PNUT drops his acorn from up where he flies)
      this.add({kind: 'proj', proj: u.proj, team: u.team, from: u.id, card: u.card, x: u.x + Math.sin(u.face) * 0.3, z: u.z + Math.cos(u.face) * 0.3, y: u.air || u.h * 0.75, sx: u.x, sz: u.z,
        target: t.id, tx: t.x, tz: t.z, dmg: Math.round(u.dmg * pow(u)), splash: u.splash || 0, speed: PROJ_SPEED[u.proj], age: 0, slow: u.slow, aa: hitsAir(u)});
      if (u.trap && !(u.trapT > 0) && !t.air) { u.trapT = u.trap[0]; this.layTrap(u, t); }
      if (u.cloud && !t.air) this.fumes(u, t);
      this.emit('shoot', {id: u.id, proj: u.proj, card: u.card});
      return;
    }
    if (u.kamikaze) {             // FIRE SALE: bursts on its first hit, burning everything around the target, and it's gone
      for (const e of this.enemiesOf(u.team)) if (reach(u, e) && (e.id === t.id || dist(e, t) - e.r * 0.5 <= u.splash)) this.damage(e, Math.round(u.dmg * pow(u)), {team: u.team});
      this.emit('boom', {id: u.id, card: u.card, x: t.x, z: t.z, r: u.splash});
      u.revive = 0; this.kill(u, {}); return;
    }
    let dmg = u.dmg * pow(u) * (u.mad ? u.berserk[2] : 1);
    if (u.pounce) { if (!u.seenBy.has(t.id)) { u.seenBy.add(t.id); dmg *= u.pounce; } }
    if (u.surprise) { u.surprise = false; dmg *= u.blink[2]; this.emit('surprise', {id: u.id, card: u.card, x: t.x, z: t.z}); }   // TROLLFACE, TOSHI: right after a blink
    const ran = u.charging;
    if (ran) { u.charging = false; u.run = 0; dmg *= u.charge[2]; this.emit('charge_hit', {id: u.id, card: u.card, x: t.x, z: t.z}); }  // MOO DENG's charge lands
    // DOPE: each bite on the same target comes sooner than the last (rate in unitTick); a new target starts over
    if (u.frenzy) { if (u.frenOn === t.id) u.fren = Math.min(u.frenzy[1], (u.fren || 1) + u.frenzy[0]); else { u.frenOn = t.id; u.fren = 1; } }
    dmg = Math.round(dmg);
    const vs = e => u.towerK && (e.kind === 'tower' || e.kind === 'bld') ? Math.round(dmg * u.towerK) : dmg;   // (MOO DENG wrecks towers)
    this.emit('hit', {id: u.id, target: t.id, card: u.card, x: t.x, z: t.z, heavy: dmg >= 200 || u.mass >= 10});
    if (u.quake) {                // SLERF: every punch is a ground slam: all that stands around him takes it, troops stunned
      for (const e of this.enemiesOf(u.team)) if (!e.air && (e.id === t.id || dist(e, u) - e.r * 0.5 <= u.quake[0])) { this.damage(e, vs(e), {team: u.team});
        if (!e.dead && e.kind === 'unit' && !e.noStun) { e.stunT = Math.max(e.stunT, u.quake[1]); e.atkT = -1; e.beamT = 0; e.charging = false; e.run = 0; } }
      this.emit('slam', {x: u.x, z: u.z, r: u.quake[0], team: u.team, card: u.card});
    } else if (u.wave) {          // POPCAT: every pop is a shockwave all around her
      for (const e of this.enemiesOf(u.team)) if (reach(u, e) && (e.id === t.id || dist(e, u) - e.r * 0.5 <= u.wave)) this.damage(e, vs(e), {team: u.team});
      this.emit('wave', {id: u.id, card: u.card, x: u.x, z: u.z, r: u.wave});
    } else if (u.spin && u.swing % u.spin[0] === 0) {   // SWORDCAT: every third swing is a spin that cuts everything around
      const d2 = Math.round(dmg * u.spin[2]);
      for (const e of this.enemiesOf(u.team)) if (reach(u, e) && (e.id === t.id || dist(e, u) - e.r * 0.5 <= u.spin[1])) this.damage(e, d2, {team: u.team});
      this.emit('spin', {id: u.id, card: u.card, x: u.x, z: u.z, r: u.spin[1]});
    } else if (u.splash) {
      for (const e of this.enemiesOf(u.team)) if (reach(u, e) && (e.id === t.id || dist(e, t) - e.r * 0.5 <= u.splash)) this.damage(e, e.id === t.id ? vs(e) : Math.round(dmg * 0.6), {team: u.team});
      this.emit('splash', {x: t.x, z: t.z, r: u.splash, card: u.card});
    } else this.damage(t, vs(t), {team: u.team});
    if (u.slow && !t.dead && t.kind === 'unit') { t.slowT = u.slow[1]; t.slowK = u.slow[0]; this.emit('slowed', {id: t.id}); }
    // BONK: the bat sends the target sliding back
    if (u.knock) this.shove(u, t, u.knock);
    // PUDGY, THE GOAT: the run ends in a shove: all that stands at the point of impact goes flying (PUDGY's slide leaves them slowed too)
    if (ran && u.charge[3]) for (const e of this.units) if (e.team !== u.team && !e.dead && !e.dug && !e.air && e.state === 'move' && (e === t || dist(e, t) <= 1.2)) {
      this.shove(u, e, u.charge[3]); if (u.charge[4]) { e.slowT = u.charge[5]; e.slowK = u.charge[4]; this.emit('slowed', {id: e.id}); } }
    // THIS IS FINE: the ground under the target catches fire (his last fire, still burning close by, is fed instead: no stacking)
    if (u.burn) { const f = this.ents.get(u.fireId); if (f && f.live > 0 && Math.hypot(f.x - t.x, f.z - t.z) < 0.8) f.live = f.S.dur; else u.fireId = this.zone(u, 'blaze', t.x, t.z, u.burn).id; }
  }
  // burning ground (THIS IS FINE's fire, NYAN CAT's rainbow): a spell entity of its own (card 'blaze' / 'rainbow'), synced and ticked
  // like one; it burns ground troops and buildings only, a tick a second, and its dps grows with the unit's level like its hits do
  zone(u, kind, x, z, [r, dps, dur, slow]) {
    const S = {r, dps: Math.round(dps * u.dmg / CARDS[u.card].unit.dmg), tower: 0.35, dur, ground: true, slow};
    const e = this.add({kind: 'spell', card: kind, team: u.team, x, z, r, S, t: 0, live: dur, fired: true, src: u.id});
    this.emit('zone', {id: e.id, kind, team: u.team, x, z, r, dur}); return e;
  }
  // MICHI: a yarn trap on the ground where her target stands (at a tower or a building: on its near side). It lies there until something walks on it
  layTrap(u, t) {
    const d = dist(u, t) || 1, k = t.kind === 'unit' ? 0 : (t.r + 0.7) / d, r = u.trap[1], S = {r, snare: u.trap[2], dur: u.trap[3], delay: 0.5};
    this.add({kind: 'spell', card: 'yarntrap', team: u.team, x: t.x + (u.x - t.x) * k, z: t.z + (u.z - t.z) * k, r, S, t: S.delay, live: S.dur, fired: false});
  }
  // FARTER: a cloud where his target stands (at a tower or a building: on its near side). His last one, still hanging close by, is fed instead: no stacking
  fumes(u, t) {
    const d = dist(u, t) || 1, k = t.kind === 'unit' ? 0 : (t.r + 0.7) / d, x = t.x + (u.x - t.x) * k, z = t.z + (u.z - t.z) * k, f = this.ents.get(u.fireId);
    if (f && f.live > 0 && Math.hypot(f.x - x, f.z - z) < 0.8) f.live = f.S.dur; else u.fireId = this.zone(u, 'stink', x, z, u.cloud).id;
  }
  // a shove: slides away over a quarter second (not the heavy ones, nor what can't be pushed)
  shove(u, t, tiles) {
    if (t.kind !== 'unit' || t.dead || t.noStun || t.air || t.mass >= 18) return;
    const d = dist(u, t) || 1; t.pushX = (t.x - u.x) / d * tiles / 0.25; t.pushZ = (t.z - u.z) / d * tiles / 0.25; t.pushT = 0.25;
    t.atkT = -1; t.run = 0; t.charging = false; this.emit('knock', {id: t.id, by: u.id, x: t.x, z: t.z});
  }
  // APU: the ally in reach who has lost the most: health back, and a shield that fades
  mendAlly(u) {
    const [amt, sh, shT, every, r] = u.mend; let best = null, lost = 0;
    for (const e of this.units) if (e !== u && e.team === u.team && !e.dead && !e.dug && !e.clone && e.state === 'move' && dist(u, e) <= r && e.max - e.hp > lost) { lost = e.max - e.hp; best = e; }
    if (!best) { u.mendT = 0.4; return; }
    u.mendT = every; this.heal(best, amt); best.shield = Math.max(best.shield || 0, sh); best.shieldT = shT;
    this.emit('mend', {id: u.id, target: best.id, x: best.x, z: best.z});
  }
  // WALTER: into the ground. Nothing can touch him or find him down there; he goes straight at his target, under river and towers
  dig(u, t) {
    u.dug = true; u.hidden = true; u.digT = 0.7; u.atkT = -1; u.run = 0; u.target = t.id;
    this.emit('dig', {id: u.id, x: u.x, z: u.z});
  }
  tunnel(u, dt) {
    u.slowT = u.stunT = u.fearT = u.rootT = u.pushT = u.frozenT = 0; u.slowK = 1; u.digT -= dt; u.moving = true;
    let t = this.ents.get(u.target);
    if (!t || t.dead || t.state === 'down' || t.hidden) { t = this.pickTarget(u); u.target = t ? t.id : null; }
    if (!t) { if (u.digT <= 0) this.surface(u); return; }
    const d = dist(u, t), m = u.r + t.r + 0.1;
    if (d > m) { const k = Math.min(u.burrow[1] * dt, d - m) / d; u.x += (t.x - u.x) * k; u.z += (t.z - u.z) * k; u.face = Math.atan2(t.x - u.x, t.z - u.z); }
    else if (u.digT <= 0) this.surface(u);
  }
  // up he comes beside it: a hit on all around him, and the troops among them stunned
  surface(u) {
    const [, , stun, r, every] = u.burrow, dmg = Math.round(u.dmg * pow(u));
    u.dug = false; u.hidden = false; u.burrowT = every; u.moving = false; u.atkT = -1; this.keepOut(u);
    for (const e of this.enemiesOf(u.team)) if (!e.air && dist(e, u) - e.r * 0.5 <= r) { this.damage(e, e.kind === 'tower' ? Math.round(dmg * 0.35) : dmg, {team: u.team});
      if (!e.dead && e.kind === 'unit' && !e.noStun) { e.stunT = Math.max(e.stunT, stun); e.atkT = -1; e.beamT = 0; e.charging = false; e.run = 0; } }
    this.emit('surface', {id: u.id, card: u.card, x: u.x, z: u.z, r});
  }
  // TROLLFACE: gone in a puff, back in one behind the target (on the far side of it from where he stood)
  blinkTo(u, t) {
    const x0 = u.x, z0 = u.z, d = dist(u, t) || 1, back = t.r + u.r + 0.2;
    u.x = t.x + (t.x - u.x) / d * back; u.z = t.z + (t.z - u.z) / d * back; this.keepOut(u);
    u.px = u.x; u.pz = u.z; u.face = Math.atan2(t.x - u.x, t.z - u.z); u.blinkT = u.blink[1]; u.surprise = true; u.atkT = -1;
    this.emit('blink', {id: u.id, card: u.card, x0, z0, x: u.x, z: u.z});
  }

  // ---------- towers
  towerTick(t, dt) {
    if (t.dead || !t.active) return;
    if (t.frozenT > 0) { t.frozenT -= dt; return; }
    t.cd -= dt;
    // a troop shooting this tower is always in reach: a long-range troop (LMAO! 5.5, ALON 6.2) hitting a tower measures from
    // the tower's edge and stood just past the Battlestation's 7.0 (or a rig's 7.5 for ALON), so the tower never shot back.
    // (The BAG LAUNCHER still outranges towers: a mortar is meant to.)
    let tg = t.target ? this.ents.get(t.target) : null;
    if (tg && (tg.dead || tg.hidden || tg.state === 'down' || (dist(t, tg) - tg.r > t.range && !(tg.kind === 'unit' && tg.target === t.id && this.inRange(tg, t))))) tg = null;
    if (!tg) {
      let bd = Infinity;
      for (const e of this.units) if (e.team !== t.team && !e.dead && !e.hidden && e.state !== 'down' && e.state !== 'deploy') { const dx = t.x - e.x, dz = t.z - e.z, m = t.range + e.r; if (dx * dx + dz * dz > m * m * FAR) continue; const d = dist(t, e) - e.r; if (d <= t.range && d < bd) { bd = d; tg = e; } }
      if (!tg) for (const e of this.units) if (e.team !== t.team && !e.dead && !e.hidden && e.state !== 'down' && e.target === t.id && this.inRange(e, t)) { const d = dist(t, e) - e.r; if (d < bd) { bd = d; tg = e; } }
    }
    t.target = tg ? tg.id : null;
    if (tg) t.aim = Math.atan2(tg.x - t.x, tg.z - t.z);
    if (tg && t.cd <= 0) {
      t.cd = t.hs;
      this.add({kind: 'proj', proj: t.type === 'hq' ? 'cannon' : 'laser', team: t.team, from: t.id, x: t.x, z: t.z, y: t.h - 0.4, sx: t.x, sz: t.z,
        target: tg.id, tx: tg.x, tz: tg.z, dmg: t.dmg, splash: 0, speed: PROJ_SPEED[t.type === 'hq' ? 'cannon' : 'laser'], age: 0, aa: true});
      this.emit('tower_shot', {id: t.id, tower: t.type, target: tg.id});
    }
  }

  // ---------- projectiles
  projTick(p, dt) {
    const tg = this.ents.get(p.target);
    if (tg && !tg.dead && tg.state !== 'down') { p.tx = tg.x; p.tz = tg.z; }
    p.age += dt;
    const dx = p.tx - p.x, dz = p.tz - p.z, d = Math.hypot(dx, dz), step = p.speed * dt;
    if (d <= step + (tg ? tg.r * 0.3 : 0.05)) {
      p.x = p.tx; p.z = p.tz;
      if (p.splash) {
        for (const e of this.enemiesOf(p.team)) if ((!e.air || p.aa) && Math.hypot(e.x - p.x, e.z - p.z) - e.r * 0.5 <= p.splash) {
          this.damage(e, p.lob || e.id === p.target ? p.dmg : Math.round(p.dmg * 0.75), {team: p.team});
          if (p.slow && e.kind === 'unit' && !e.dead) { e.slowT = p.slow[1]; e.slowK = p.slow[0]; }
        }
      } else if (tg && !tg.dead) {
        this.damage(tg, p.dmg, {team: p.team});
        if (p.slow && tg.kind === 'unit' && !tg.dead) { tg.slowT = p.slow[1]; tg.slowK = p.slow[0]; }
      }
      this.emit('impact', {proj: p.proj, card: p.card, x: p.x, z: p.z, splash: p.splash, team: p.team, target: p.target});
      this.remove(p);
      return;
    }
    p.x += dx / d * step; p.z += dz / d * step;
  }

  // ---------- reading
  unitsOf(team) { const o = []; for (const e of this.ents.values()) if (e.kind === 'unit' && e.team === team && !e.dead) o.push(e); return o; }
  timeLeft() { return Math.max(0, this.clock); }
}
