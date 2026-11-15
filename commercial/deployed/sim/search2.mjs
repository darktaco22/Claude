// Structured search: the Thumb's gag plays are fixed, the rest random; keep matches with the arc we want.
import {Battle} from '/home/user/Claude/meme-royale-research/client_src/sim.js';
import {Bot} from '/home/user/Claude/meme-royale-research/client_src/ai.js';
import fs from 'fs';
const N = +process.argv[2] || 500;
const deck0 = ['lmao','chillguy','cupsey','chillhouse','airdrop','ket','dope','pudgy'], deck1 = ['bonk','jeanphil','troll','useless','fud','firesale','neet','dope'];
const order0 = ['lmao','ket','cupsey','dope','chillhouse','chillguy','pudgy','airdrop'];
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function run(plan) {
  Math.random = rng(plan.seed * 31 + 5);
  const b = new Battle({decks: [deck0, deck1], seed: plan.seed});
  b.hands[0] = order0.slice(0, 4); b.queues[0] = order0.slice(4);
  const bot = new Bot(b, 1, {skill: plan.skill});
  const plays = plan.plays.map(p => ({...p, done: false})); const log = [];
  for (let i = 0; i < 30 * 200 && !b.over; i++) {
    bot.update(1 / 30);
    for (const p of plays) if (!p.done && b.t >= p.t) {
      const slot = b.hands[0].indexOf(p.card); if (slot < 0) continue;
      const why = b.canPlay(0, slot, p.x, p.z);
      if (why === 'copium') continue;
      p.done = true;
      if (why) { log.push([+b.t.toFixed(1), 'illegal', p.card]); continue; }
      b.play(0, slot, p.x, p.z); log.push([+b.t.toFixed(1), p.card]);
    }
    const ev0 = b.events.length; b.step();
    for (const e of b.events.slice(ev0)) if (e.type === 'tower_down') log.push([+b.t.toFixed(1), 'down', e.team, e.tower, e.x]);
  }
  return {b, log};
}
const hits = []; const STAT = {n: 0, win: 0, early: 0, late: 0, winlate: 0, winearly: 0};
for (let s = 1; s <= N; s++) {
  const r = rng(s * 4099);
  const plan = {seed: s, skill: 0.1 + r() * 0.25, plays: [
    {t: 14, card: 'lmao', x: 16.5, z: 30.5},                                    // LMAO into a back corner
    {t: 21, card: 'ket', x: 9, z: 8},                                           // an illegal tap on the enemy side
    {t: 30, card: 'airdrop', x: 9, z: 16}]};                                    // an airdrop on the river
  const extra = 3 + Math.floor(r() * 5);
  for (let k = 0; k < extra; k++) plan.plays.push({t: 34 + r() * 80, card: deck0[Math.floor(r() * 8)], x: 1.5 + r() * 15, z: 19 + r() * 11});
  plan.plays.push({t: 120 + r() * 15, card: 'chillhouse', x: r() < 0.5 ? 3.5 : 14.5, z: 20 + r() * 4});
  plan.plays.sort((a, b) => a.t - b.t);
  const {b, log} = run(plan);
  const downs = log.filter(l => l[1] === 'down');
  const ourEarly = downs.some(d => d[2] === 0 && d[0] < 110);
  const theirLate = downs.some(d => d[2] === 1 && d[0] > 130);
  STAT.n++; if (b.winner === 0) STAT.win++; if (ourEarly) STAT.early++; if (theirLate) STAT.late++; if (b.winner === 0 && theirLate) STAT.winlate++; if (b.winner === 0 && ourEarly) STAT.winearly++;
  if (b.winner === 0 && (theirLate || ourEarly) && b.t > 150 && log.filter(l => l[1] === 'illegal').length === 1)
    hits.push({s, end: +b.t.toFixed(0), ws: b.ws.join('-'), skill: +plan.skill.toFixed(2), log: log.map(l => l.join(' ')), plan});
}
console.log('hits', hits.length, JSON.stringify(STAT));
for (const h of hits.slice(0, 6)) console.log(h.s, h.end, h.ws, h.skill, '|', h.log.join(' ; '));
fs.writeFileSync('/root/dep_work/hits.json', JSON.stringify(hits));
