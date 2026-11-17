// Search for a sparse, game-like match: both sides play like the game's own bot, so pushes die to defence.
// node search4.mjs N [skill0 range] -> /root/dep_work/hits4.json
import fs from 'fs';
import {runMatch, rng} from './play.mjs';
const N = +process.argv[2] || 300, S0 = +(process.argv[3] ?? 0.6), S1 = +(process.argv[4] ?? 0.9), E0 = +(process.argv[5] ?? 0.35), E1 = +(process.argv[6] ?? 0.65);
const hits = [], C = {n: 0, win: 0, air: 0, sparse: 0, story: 0};
for (let seed = 1; seed <= N; seed++) {
  const r = rng(seed * 4099);
  const plan = {seed, skill0: +(S0 + r() * (S1 - S0)).toFixed(2), skill1: +(E0 + r() * (E1 - E0)).toFixed(2)};
  const {b, log, stat, air} = runMatch(plan);
  C.n++;
  const downs = log.filter(l => l.what === 'tower_down'), ours = downs.filter(d => d.team === 0), theirs = downs.filter(d => d.team === 1);
  const thumbs = log.filter(l => l.what === 'thumb'); const dups = thumbs.filter(t => t.dup).length;
  const meanTot = stat.tot / Math.max(1, stat.n);
  const win = b.winner === 0; if (win) C.win++;
  if (win && air) C.air++;
  const sparse = stat.maxSide <= 5 && meanTot <= 3.9 && stat.ge7 === 0 && stat.ge6 / stat.n < 0.12 && dups <= 3;
  if (win && air && sparse) C.sparse++;
  const story = ours.length >= 1 && ours[0].t < 110 && theirs.length >= 2 && theirs[1].t < 160 && b.t > 175 && thumbs.length >= 11 && thumbs.length <= 24;
  if (win && air && sparse && story) {
    C.story++;
    const cards = {}; for (const t of thumbs) cards[t.card] = (cards[t.card] || 0) + 1;
    hits.push({seed, plan, dups, end: +b.t.toFixed(0), ws: b.ws.join('-'), meanTot: +meanTot.toFixed(2), maxSide: stat.maxSide, maxTot: stat.maxTot, ge6: +(stat.ge6 / stat.n).toFixed(3), plays: thumbs.length, cards,
      downs: downs.map(d => `${d.t}:${d.team}${d.tower}`).join(' ')});
  }
}
console.log(JSON.stringify(C));
hits.sort((a, c) => a.meanTot - c.meanTot);
for (const h of hits.slice(0, 12)) console.log(h.seed, 'skill', h.plan.skill0, h.plan.skill1, 'end', h.end, h.ws, 'mean', h.meanTot, 'max side', h.maxSide, 'tot', h.maxTot, '>=6', h.ge6, 'plays', h.plays, 'dups', h.dups, JSON.stringify(h.cards), '|', h.downs);
fs.writeFileSync('/root/dep_work/hits4.json', JSON.stringify(hits));
