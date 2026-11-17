for (let tries = 0; tries < 5; tries++) {
  if (tries) await p.reload({waitUntil: 'load', timeout: 90000});
  await H.sleep(6000);
  for (let i = 0; i < 40; i++) { const s = await H.ev(() => document.getElementById('boot')?.className || 'gone'); if (s === 'gone') break; if (/ready/.test(s)) { try { await p.mouse.click(540, 1690); } catch {} } await H.sleep(2000); }
  for (let i = 0; i < 30; i++) { if (await H.ev(() => !!(window.__game && window.__game.Match && window.__game.arena))) return 'booted after ' + tries; await H.sleep(2000); }
}
return 'BOOT FAILED';
