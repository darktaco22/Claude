// The Thumb is a button masher: taps cards at random, one gag (an illegal tap), one airdrop on the river.
// The search keeps matches where he wins late after losing a tower. node search3.mjs N   -> /root/dep_work/hits.json
import {Battle} from '/home/user/Claude/meme-royale-research/client_src/sim.js';
import {Bot} from '/home/user/Claude/meme-royale-research/client_src/ai.js';
import fs from 'fs';
const N = +process.argv[2] || 500, SK0 = +(process.argv[3] ?? 0.3), SK1 = +(process.argv[4] ?? 0.6);
const deck0 = ['lmao','chillguy','cupsey','chillhouse','airdrop','ket','dope','pudgy'], deck1 = ['troll','dope','bonk','neet','zcat','apu','farter','popcat'];
const order0 = ['lmao','ket','cupsey','dope','chillhouse','chillguy','pudgy','airdrop'];
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const hits = [], STAT = {n: 0, win: 0, winEarlyDown: 0};
for (let s = 1; s <= N; s++) {
  const r = rng(s * 4099); Math.random = rng(s * 31 + 5);
  const skill = SK0 + r() * (SK1 - SK0);
  const b = new Battle({decks: [deck0, deck1], seed: s});
  b.hands[0] = order0.slice(0, 4); b.queues[0] = order0.slice(4);
  const bot = new Bot(b, 1, {skill});
  const plays = [], log = []; let next = 5 + r() * 3, gag = false, aird = false;
  const lazy = 0.7 + r() * 0.9;
  for (let i = 0; i < 30 * 200 && !b.over; i++) {
    bot.update(1 / 30);
    if (b.t >= next) {
      next = b.t + (2.2 + r() * 5) * lazy;
      const slot = Math.floor(r() * 4), id = b.hands[0][slot];
      let x = 1 + r() * 16, z = 17.5 + r() * 14;
      if (!gag && b.t > 16) { gag = true; plays.push([+b.t.toFixed(2), id, 9, 8, 'illegal']); log.push([+b.t.toFixed(1), 'illegal', id]); }
      else if (id === 'airdrop' && !aird) { aird = true; x = 9; z = 16; }
      if (b.copium[0] >= 3.5 || id === 'dope') if (!b.canPlay(0, slot, x, z)) {
        b.play(0, slot, x, z); plays.push([+b.t.toFixed(2), id, +x.toFixed(1), +z.toFixed(1)]); log.push([+b.t.toFixed(1), id]);
      }
    }
    const ev0 = b.events.length; b.step();
    for (const e of b.events.slice(ev0)) if (e.type === 'tower_down') log.push([+b.t.toFixed(1), 'down', e.team, e.tower]);
  }
  const downs = log.filter(l => l[1] === 'down');
  STAT.n++; if (b.winner === 0) STAT.win++;
  const ourDown = downs.filter(d => d[2] === 0), theirDown = downs.filter(d => d[2] === 1);
  if (b.winner === 0 && aird && ourDown.length >= 1 && theirDown.length >= 1 && b.t > 150 && ourDown[0][0] < theirDown[theirDown.length - 1][0]) {
    STAT.winEarlyDown++;
    hits.push({s, skill, end: +b.t.toFixed(0), ws: b.ws.join('-'), plays: plays.length, log: log.map(l => l.join(' ')), plan: {seed: s, skill, order0, deck0, deck1, plays}});
  }
}
console.log('hits', hits.length, JSON.stringify(STAT));
for (const h of hits.slice(0, 5)) console.log(h.s, h.end, h.ws, h.skill.toFixed(2), 'plays', h.plays, '|', h.log.filter(l => /down|illegal/.test(l)).join(' ; '));
fs.writeFileSync('/root/dep_work/hits.json', JSON.stringify(hits));
