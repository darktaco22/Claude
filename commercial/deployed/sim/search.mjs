// Random search for a match with a good arc: the Thumb (bad player) wins late. node search.mjs N
import {Battle} from '/home/user/Claude/meme-royale-research/client_src/sim.js';
import {Bot} from '/home/user/Claude/meme-royale-research/client_src/ai.js';
const N = +process.argv[2] || 200;
const deck0 = ['lmao','chillguy','cupsey','chillhouse','airdrop','ket','dope','pudgy'], deck1 = ['bonk','jeanphil','troll','useless','fud','firesale','neet','dope'];
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const out = [];
for (let s = 1; s <= N; s++) {
  const r = rng(s * 977); Math.random = rng(s * 31 + 5);
  const b = new Battle({decks: [deck0, deck1], seed: s});
  const bot = new Bot(b, 1, {skill: 0.5});
  const lazy = 0.2 + r() * 0.6;                       // how often the Thumb acts
  let next = 4 + r() * 10; const plays = [];
  for (let i = 0; i < 30 * 200 && !b.over; i++) {
    bot.update(1 / 30);
    if (b.t >= next) {
      next = b.t + 2 + r() * 14 * lazy;
      const slot = Math.floor(r() * 4), id = b.hands[0][slot], c = id && b.copium[0] >= (0 + (id === 'x')) ;
      const x = 1.5 + r() * 15, z = 18 + r() * 12;
      if (id && !b.canPlay(0, slot, x, z)) { b.play(0, slot, x, z); plays.push([+b.t.toFixed(1), id, +x.toFixed(1), +z.toFixed(1)]); }
    }
    b.step();
  }
  out.push({s, winner: b.winner, end: +b.t.toFixed(0), ws: b.ws.join('-'), n: plays.length, plays});
}
const good = out.filter(o => o.winner === 0).sort((a, b) => b.end - a.end);
console.log('thumb wins', good.length, 'of', N);
for (const o of good.slice(0, 12)) console.log(o.s, o.end, o.ws, 'plays', o.n, JSON.stringify(o.plays.slice(0, 5)));
