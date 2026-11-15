import {Battle} from '/home/user/Claude/meme-royale-research/client_src/sim.js';
import {Bot} from '/home/user/Claude/meme-royale-research/client_src/ai.js';
const decks = [['lmao','chillguy','cupsey','chillhouse','airdrop','ket','dope','pudgy'], ['bonk','jeanphil','troll','useless','fud','firesale','neet','dope']];
const b = new Battle({decks, seed: 7});
const bot = new Bot(b, 1, {skill: 0.6});
console.log('hand0', b.hands[0], 'queue0', b.queues[0]);
let n = 0;
for (let i = 0; i < 30 * 60; i++) {
  bot.update(1/30);
  if (i === 30 * 20) { b.copium[0] = 10; console.log('play', b.play(0, 0, 3.5, 22.5), b.hands[0], b.queues[0]); }
  b.step();
  if (i === 30 * 24) { for (const e of b.units) { console.log(Object.fromEntries(['id','card','team','x','z','face','moving','state','hp','max','dead','model','n'].map(k => [k, e[k]]))); } }
}
console.log('events sample', b.events.slice(0, 6));
console.log('phase', b.phase, 'clock', b.clock.toFixed(1), 'ws', b.ws);
