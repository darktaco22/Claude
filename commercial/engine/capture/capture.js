// capture every frame at 30 fps until battle time T_END (plus the opening), with the sound log
const OUT = __OUT__, T_END = __TEND__;
fs.mkdirSync(OUT, {recursive: true});
await H.ev(() => { __dir.skipDraw = false; });
let i = 0;
for (; i < 3000; i++) {
  const [t] = await H.ev(() => { __vc.step(1000 / 30); const m = __match; return [m.running ? m.b.t : (m.b.over ? 999 : -1)]; });
  await H.shot(OUT + '/f_' + String(i).padStart(4, '0') + '.png');
  if (t >= T_END) break;
}
const log = await H.ev(() => ({start: __capStart, fps: 30, sfx: __sfx, dir: __dir.log}));
fs.writeFileSync(OUT + '/sfx.json', JSON.stringify(log));
return 'frames ' + (i + 1);
