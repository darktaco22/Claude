await H.sleep(6000);
for (let i = 0; i < 40; i++) { const s = await H.ev(() => document.getElementById('boot')?.className || 'gone'); if (s === 'gone') break; if (/ready/.test(s)) { try { await p.mouse.click(Math.floor(p.viewportSize().width / 2), Math.floor(p.viewportSize().height * 0.88)); } catch {} } await H.sleep(2000); }
await H.sleep(3000);
return await H.ev(() => [__vc.t, document.getElementById('boot')?.className || 'gone', !!window.__game?.arena]);
