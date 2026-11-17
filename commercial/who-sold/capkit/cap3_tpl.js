const OUT = '__OUT__', EVERY = __EVERY__; fs.mkdirSync(OUT, {recursive: true});
await H.ev(() => { __dir.skipDraw = true; });
const T1 = await H.ev(() => window.__T1);
let n = 0, k = 0; const times = [];
for (let i = 0; i < 4000; i++) {
  const t = await H.ev(() => { const m = __match; return m.running ? m.b.t : -1; });
  if (t >= T1) break;
  const on = t >= 0.2 && (k++ % EVERY === 0);
  await H.ev(({on, ms}) => { __dir.skipDraw = !on; __vc.step(ms); }, {on, ms: 1000 / 30});
  if (on) { times.push(t); await H.shot(OUT + '/f_' + String(n++).padStart(4, '0') + '.png'); }
}
const log = await H.ev(() => ({sfx: __sfx.length, dir: __dir.log, show: (window.__show || []).map(e => e && e.card)}));
fs.writeFileSync(OUT + '/info.json', JSON.stringify({n, times, log}));
return 'frames ' + n + ' ' + JSON.stringify(log).slice(0, 300);
