// Plays one real Meme Royale match with the game's own rules (sim.js + the opponent AI) and records everything the
// film needs.   node record.mjs PLAN.json OUT.json
//   PLAN: {seed, deck0, deck1, hand0 (optional: set the start order), skill, plays: [[t, card, x, z], ...]}
// The Thumb (team 0) plays the cards of `plays` as soon as they are legal at time t (copium and placement are the real
// rules: an illegal play waits for copium or is dropped). Team 1 is the game's own Bot.
import fs from 'fs';
import {Battle} from '/home/user/Claude/meme-royale-research/client_src/sim.js';
import {Bot} from '/home/user/Claude/meme-royale-research/client_src/ai.js';

const plan = JSON.parse(fs.readFileSync(process.argv[2]));
let seed = plan.seed ?? 7;
Math.random = (() => { let a = (seed * 31 + 5) >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; })();   // the Bot uses Math.random: make it repeatable
const b = new Battle({decks: [plan.deck0, plan.deck1], seed});
if (plan.order0) { b.hands[0] = plan.order0.slice(0, 4); b.queues[0] = plan.order0.slice(4); }
const bot = new Bot(b, 1, {skill: plan.skill ?? 0.6});
const DT = 1 / 30, STRIDE = 3;
const frames = [], log = [], plays = (plan.plays || []).map(p => ({t: p[0], card: p[1], x: p[2], z: p[3], done: false}));
const seen = new Map();   // id -> first/last tick
const life = {};
for (let i = 0; i < 30 * 200 && !b.over; i++) {
  bot.update(DT);
  for (const p of plays) if (!p.done && b.t >= p.t - 0.02) {
    const slot = b.hands[0].indexOf(p.card);
    if (slot < 0) continue;                                       // not in hand yet: wait for the rotation
    if (p.illegal) { p.done = true; log.push({t: +b.t.toFixed(2), what: 'illegal', card: p.card, x: p.x, z: p.z, why: b.canPlay(0, slot, p.x, p.z), copium: +b.copium[0].toFixed(1)}); continue; }
    const why = b.canPlay(0, slot, p.x, p.z);
    if (why === 'copium') continue;                               // wait for copium (real rule)
    if (why) { p.done = true; log.push({t: +b.t.toFixed(2), what: 'illegal', card: p.card, why}); continue; }
    const before = b.hands[0].slice(), q = b.queues[0].slice();
    b.play(0, slot, p.x, p.z); p.done = true;
    log.push({t: +b.t.toFixed(2), what: 'thumb', card: p.card, x: p.x, z: p.z, copium: +b.copium[0].toFixed(1), hand: b.hands[0].slice(), queue: b.queues[0].slice(), slot});
  }
  const ev0 = b.events.length;
  b.step();
  for (const e of b.events.slice(ev0)) if (['tower_down', 'phase', 'play'].includes(e.type)) log.push({t: +b.t.toFixed(2), what: e.type, ...Object.fromEntries(Object.entries(e).filter(([k, v]) => typeof v !== 'object' && k !== 't' && k !== 'type'))});
  if (i % STRIDE === 0) {
    const ents = [];
    for (const e of b.all) {
      if (e.kind === 'unit' || e.kind === 'tower' || e.kind === 'bld') ents.push([e.id, e.kind === 'unit' ? 'u' : e.kind === 'tower' ? 't' : 'b', e.card || e.type, e.team, +e.x.toFixed(2), +e.z.toFixed(2), +(e.face || 0).toFixed(2), e.moving ? 1 : 0, Math.round(e.hp), e.dead ? 1 : 0, e.state || '', +(e.y || 0).toFixed(2)]);
      if (!seen.has(e.id)) seen.set(e.id, {t0: b.t, kind: e.kind, card: e.card || e.type, team: e.team});
      const s = seen.get(e.id); s.t1 = b.t; s.hp = e.hp;
    }
    frames.push({t: +b.t.toFixed(2), cop: +b.copium[0].toFixed(1), cop1: +b.copium[1].toFixed(1), clock: +b.clock.toFixed(1), ws: b.ws.slice(), e: ents});
  }
}
const events = b.events.filter(e => ['hit', 'shoot', 'spell', 'spell_hit', 'tower_shot', 'impact', 'boom', 'slam', 'landed', 'knock', 'spawn', 'hut_spawn'].includes(e.type))
  .map(e => Object.fromEntries(Object.entries(e).filter(([k, v]) => typeof v !== 'object')));
fs.writeFileSync(process.argv[3], JSON.stringify({plan, log, frames, events, over: b.over, winner: b.winner, ws: b.ws, end: b.t, towers: b.towers.map(s => s.map(t => [t.id, t.type, t.lane, t.dead ? 1 : 0, Math.round(t.hp)]))}));
console.log('over', b.over, 'winner', b.winner, 'ws', b.ws, 'end', b.t.toFixed(1), 'frames', frames.length, 'events', events.length);
for (const l of log) console.log(JSON.stringify(l));
