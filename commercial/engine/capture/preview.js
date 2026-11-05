const marks = __MARKS__; let mi = 0, n = 0, shots = [];
await H.ev(() => { __dir.skipDraw = true; });
for (let i = 0; i < 1500; i++) {
  const [t, over, el] = await H.ev(() => { __vc.step(1000 / 30); const m = __match; return [m.running ? m.b.t : -1, m.b.over, performance.now() - __capStart]; });
  if ((n === 0 && el > 1500 && t < 0) || (t >= 0 && mi < marks.length && t >= marks[mi])) {
    await H.ev(() => { __dir.skipDraw = false; __vc.step(1); __dir.skipDraw = true; });
    const name = 'prev/q' + String(n).padStart(2, '0') + '_' + (t >= 0 ? t.toFixed(1) : 'intro') + '.png'; await H.shot(name); shots.push(name); n++; if (t >= 0) mi++;
  }
  if (mi >= marks.length) break;
}
return [shots, await H.ev(() => [__dir.log.filter(l => l[0] === 'ERR'), __match.b.over, __match.b.towers[1].map(t => t.hp)])];
