const OUT = '__OUT__'; fs.mkdirSync(OUT, {recursive: true});
await H.ev(() => { __dir.skipDraw = true; });
let n = 0, first = null, slow = 0, slowDone = false; const times = [], info = [];
for (let i = 0; i < 3000; i++) {
  const t = await H.ev(() => { const m = __match; return m.running ? m.b.t : -1; });
  if (t >= 9.8) break;
  const on = t >= 0;
  if (on && !slowDone && t > 3.8) {
    const c = await H.ev(() => { const u = [...__match.b.ents.values()].filter(e => e.kind === 'unit' && !e.dead); for (const a of u) for (const b of u) if (a.team !== b.team && Math.hypot(a.x - b.x, a.z - b.z) < 5.5) return 1; return 0; });
    if (c || t > 6.2) { slow = 130; slowDone = true; info.push(['slow', n, t]); }
  }
  const stepMs = slow > 0 ? 1000 / 90 : 1000 / 30; if (slow > 0) slow--;
  await H.ev(({on, ms}) => { __dir.skipDraw = !on; __vc.step(ms); }, {on, ms: stepMs});
  if (on) { const pt = await H.ev(() => performance.now()); if (first == null) first = pt; times.push(pt); await H.shot(OUT + '/f_' + String(n++).padStart(4, '0') + '.png'); }
}
const log = await H.ev(() => ({sfx: __sfx, dir: __dir.log, teams: [...__match.b.ents.values()].filter(e => e.kind === 'unit').slice(0, 3).map(e => Object.keys(e).slice(0, 14).join(','))}));
fs.writeFileSync(OUT + '/sfx.json', JSON.stringify({first, n, times, info, sfx: log.sfx}));
return 'frames ' + n + ' ' + JSON.stringify(info) + ' ' + JSON.stringify(log.teams).slice(0, 300);
