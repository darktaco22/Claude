const OUT = '__OUT__'; fs.mkdirSync(OUT, {recursive: true});
await H.ev(() => { __dir.skipDraw = true; });
const T1 = await H.ev(() => window.__T1);
const lost = () => H.ev(() => { const r = __game.stage.renderer; return !r || r.getContext().isContextLost(); });
let n = 0, redo = 0; const times = [];
for (let i = 0; i < 6000; i++) {
  const t = await H.ev(() => { const m = __match; return m.running ? m.b.t : -1; });
  if (t >= T1) break;
  const on = t >= 0.05;
  await H.ev(({on, ms}) => { __dir.skipDraw = !on; __vc.step(ms); }, {on, ms: 1000 / 30});
  if (!on) continue;
  const f = OUT + '/f_' + String(n).padStart(4, '0') + '.png';
  for (let a = 0; a < 8; a++) {
    if (await lost()) { redo++; for (let w = 0; w < 40 && await lost(); w++) await H.sleep(500); await H.sleep(800); await H.ev(() => { __dir.skipDraw = false; __game.stage.draw(); }); }
    try { await H.shot(f); } catch (e) { redo++; await H.sleep(3000); await H.ev(() => { __dir.skipDraw = false; __game.stage.draw(); }).catch(() => 0); continue; }
    if (!(await lost())) break;
  }
  times.push(t); n++;
}
const log = await H.ev(() => ({dir: __dir.log, show: (window.__show || []).map(e => e && e.card)}));
fs.writeFileSync(OUT + '/info.json', JSON.stringify({n, redo, times, log}));
return 'frames ' + n + ' redo ' + redo;
