// frame-count capture from right after setup (includes the game's own intro / results screens); always draws
const OUT = '__OUT__', N = __N__; fs.mkdirSync(OUT, {recursive: true});
const lost = () => H.ev(() => { const r = __game.stage.renderer; return !r || r.getContext().isContextLost(); });
let redo = 0; const times = [];
for (let n = 0; n < N; n++) {
  await H.ev(() => { __dir.skipDraw = false; __vc.step(1000 / 30); });
  const f = OUT + '/f_' + String(n).padStart(4, '0') + '.png';
  for (let a = 0; a < 8; a++) {
    if (await lost()) { redo++; for (let w = 0; w < 40 && await lost(); w++) await H.sleep(500); await H.sleep(800); await H.ev(() => { __game.stage.draw(); }); }
    try { await H.shot(f); } catch (e) { redo++; await H.sleep(3000); continue; }
    if (!(await lost())) break;
  }
  times.push(await H.ev(() => __match && __match.running ? __match.b.t : -1));
}
fs.writeFileSync(OUT + '/info.json', JSON.stringify({n: N, redo, times}));
return 'frames ' + N + ' redo ' + redo;
