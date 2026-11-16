const OUT = '__OUT__'; fs.mkdirSync(OUT, {recursive: true});
await H.ev(() => { __dir.skipDraw = true; });
let n = 0, first = null;
for (let i = 0; i < 1500; i++) {
  const t = await H.ev(() => { const m = __match; return m.running ? m.b.t : -1; });
  if (t >= 5.4) break;
  const on = t >= 0;
  await H.ev((on) => { __dir.skipDraw = !on; __vc.step(1000 / 30); }, on);
  if (on) { if (first == null) first = await H.ev(() => performance.now()); await H.shot(OUT + '/f_' + String(n++).padStart(4, '0') + '.png'); }
}
const log = await H.ev(() => ({sfx: __sfx, dir: __dir.log}));
fs.writeFileSync(OUT + '/sfx.json', JSON.stringify({first, n, sfx: log.sfx}));
return 'frames ' + n;
