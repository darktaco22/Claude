const { chromium } = require('playwright');
const fs = require('fs');
const W = +(process.env.W || 1280), H = +(process.env.H || 720);
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required'],
  });
  const ctx = await br.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await ctx.addInitScript({ path: './vclock.js' });
  const p = await ctx.newPage();
  p.on('framenavigated', f => { if (f === p.mainFrame()) fs.appendFileSync('console.log', 'NAVIGATED '+f.url()+' '+new Date().toISOString()+'\n'); });
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
