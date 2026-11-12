// Renders overlay.html as transparent PNGs, one per frame (the film plus 3 s of end card): node overlays.js TIMELINE.json OUTDIR
// Files under /g/ come from $GAME (the game's own card art, logo, title art).
const {chromium} = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const TLP = process.argv[2], OUT = process.argv[3]; const TL = JSON.parse(fs.readFileSync(TLP)); const NF = Math.round((TL.end + 3.0) * TL.fps) + (TL.inserts || []).reduce((a, x) => a + x.n, 0);
fs.mkdirSync(OUT, {recursive: true});
const TYPES = {html: 'text/html', json: 'application/json', png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp', woff2: 'font/woff2'};
const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split('?')[0]);
  const f = u === '/timeline.json' ? TLP : u.startsWith('/g/') ? path.join(process.env.GAME, u.slice(3)) : path.join(__dirname, u);
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, {'Content-Type': TYPES[f.split('.').pop()] || 'application/octet-stream'}); r.end(d); }); }).listen(8771);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 540, height: 960}, deviceScaleFactor: 2});
  await p.goto('http://127.0.0.1:8771/overlay.html'); await p.waitForFunction(() => window.ready);
  const only = process.env.ONLY ? process.env.ONLY.split(',').map(Number) : null;
  for (let i = 0; i < NF; i++) { if (only && !only.includes(i + 1)) continue;
    await p.evaluate(t => window.renderAt(t), i / TL.fps); await p.screenshot({path: `${OUT}/o_${String(i + 1).padStart(4, '0')}.png`, omitBackground: true}); }
  await b.close(); srv.close(); console.log('overlays done', NF);
})();
