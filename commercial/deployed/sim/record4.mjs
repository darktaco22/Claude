// Records a match of play.mjs (both sides play like the game's own bot) for the film.  node record4.mjs SEED SKILL0 SKILL1 OUT.json
import fs from 'fs';
import {runMatch} from './play.mjs';
const [seed, skill0, skill1, out] = [+process.argv[2], +process.argv[3], +process.argv[4], process.argv[5]];
import {DECK0, DECK1, ORDER0} from './play.mjs';
const plan = {seed, skill0, skill1, deck0: DECK0, deck1: DECK1, order0: ORDER0};
const {b, log, frames} = runMatch(plan, {record: true});
const events = b.events.filter(e => ['hit', 'shoot', 'spell', 'spell_hit', 'tower_shot', 'impact', 'boom', 'slam', 'landed', 'knock', 'spawn', 'hut_spawn'].includes(e.type))
  .map(e => Object.fromEntries(Object.entries(e).filter(([k, v]) => typeof v !== 'object')));
fs.writeFileSync(out, JSON.stringify({plan, log, frames, events, over: b.over, winner: b.winner, ws: b.ws, end: b.t, towers: b.towers.map(s => s.map(t => [t.id, t.type, t.lane, t.dead ? 1 : 0, Math.round(t.hp)]))}));
console.log('over', b.over, 'winner', b.winner, 'ws', b.ws, 'end', b.t.toFixed(1), 'frames', frames.length);
for (const l of log) console.log(JSON.stringify(l).slice(0, 140));
