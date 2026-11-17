const { chromium } = require('playwright');
const fs = require('fs');
const W = +(process.env.W || 1280), H = +(process.env.H || 720);
const sleep0 = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required','--disable-renderer-backgrounding','--disable-background-timer-throttling'],
  });
  const ctx = await br.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await ctx.addInitScript({ path: './vclock.js' });
  const p = await ctx.newPage();
  // on-disk asset cache + throttled fetches (the proxy refuses bursts: ERR_INSUFFICIENT_RESOURCES)
  const crypto = require('crypto'); const CD = '/root/road/webcache'; fs.mkdirSync(CD, {recursive: true});
  let active = 0; const q = []; const slot = () => new Promise(r => { if (active < 6) { active++; r(); } else q.push(r); }); const free = () => { const n = q.shift(); if (n) n(); else active--; };
  await ctx.route(u => u.hostname.endsWith('imaginestudio.fun'), async route => {
    const req = route.request(); if (req.method() !== 'GET') return route.continue();
    const key = crypto.createHash('sha1').update(req.url()).digest('hex'); const f = CD + '/' + key;
    if (fs.existsSync(f + '.b') && fs.existsSync(f + '.h') && !/\/$|\.html$/.test(new URL(req.url()).pathname)) { let h; try { h = JSON.parse(fs.readFileSync(f + '.h')); } catch (e) { h = null; } if (h)  return route.fulfill({status: h.status, headers: h.headers, body: fs.readFileSync(f + '.b')}); }
    await slot();
    try {
      for (let a = 0; a < 5; a++) { try { const r = await route.fetch({timeout: 60000}); const b = await r.body(); const hd = r.headers(); delete hd['content-encoding']; delete hd['content-length'];
          if (r.status() === 200) { try { fs.writeFileSync(f + '.b', b); fs.writeFileSync(f + '.h', JSON.stringify({status: 200, headers: hd})); } catch (e) { try { fs.unlinkSync(f + '.b'); } catch {} } }
          return await route.fulfill({status: r.status(), headers: hd, body: b}); } catch (e) { if (a === 4) return route.abort(); await sleep0(1500 * (a + 1)); } }
    } finally { free(); }
  });
  p.on('framenavigated', f => { if (f === p.mainFrame()) fs.appendFileSync('console.log', 'NAVIGATED '+f.url()+' '+new Date().toISOString()+'\n'); });
  br.on('disconnected', () => fs.appendFileSync('console.log', 'BROWSER DISCONNECTED '+new Date().toISOString()+'\n'));
  const cdp = await ctx.newCDPSession(p);
  p.on('console', m => fs.appendFileSync('console.log', m.type()+' '+m.text().slice(0,300)+'\n'));
  p.on('crash', () => fs.appendFileSync('console.log', 'PAGE CRASHED\n')); p.on('pageerror', e => fs.appendFileSync('console.log', 'PAGEERR '+e.message+'\n'));
  await p.goto('https://memeroyale.imaginestudio.fun', { waitUntil: 'load', timeout: 60000 });
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const retry = async (f) => { let e; for (let i = 0; i < 8; i++) { try { return await f(); } catch (x) { e = x; if (!/closed/.test(x.message)) throw x; await sleep(500); } } throw e; };
  global.H = { sleep, ev: (fn, arg) => retry(() => p.evaluate(fn, arg)), shot: (path, o = {}) => retry(() => p.screenshot({path, timeout: 180000, ...o})) };
  fs.writeFileSync('ready', '1');
  while (true) {
    if (fs.existsSync('cmd.js')) {
      const code = fs.readFileSync('cmd.js', 'utf8'); fs.unlinkSync('cmd.js');
      let out;
      try { out = await (new Function('p', 'fs', 'cdp', 'H', `return (async()=>{${code}})()`))(p, fs, cdp, global.H); } catch (e) { out = 'ERR ' + e.stack; }
      fs.writeFileSync('result.txt', typeof out === 'string' ? out : JSON.stringify(out));
    }
    await new Promise(r => setTimeout(r, 100));
  }
})();
