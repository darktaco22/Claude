// capture only inside battle-time ranges (the rest is stepped without drawing); frames are numbered by their
// capture-frame index (as if every frame were shot), so the sound log lines up the same way
const OUT = __OUT__, RANGES = __RANGES__, T_END = __TEND__, EXTRA = __EXTRA__; let after = 0;
fs.mkdirSync(OUT, {recursive: true});
const inR = t => t >= 999 || RANGES.some(([a, b]) => t >= a && t < b);
let i = 0, shot = 0;
for (; i < 4000; i++) {
  const want = await H.ev(() => { const m = __match; const t = m.running ? m.b.t : (m.b.over ? 999 : -1); return t; });
  const on = inR(want);
  const [t] = await H.ev((on) => { __dir.skipDraw = !on; __vc.step(1000 / 30); const m = __match; return [m.running ? m.b.t : (m.b.over ? 999 : -1)]; }, on);
  if (on) { await H.shot(OUT + '/f_' + String(i).padStart(4, '0') + '.png'); shot++; }
  if (t >= 999 && ++after > EXTRA) break;
  if (t >= T_END && t < 999) break;
}
const log = await H.ev(() => ({start: __capStart, fps: 30, sfx: __sfx, dir: __dir.log}));
fs.writeFileSync(OUT + '/sfx.json', JSON.stringify(log));
return 'frames ' + (i + 1) + ' shot ' + shot;
