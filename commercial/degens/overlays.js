// Renders overlay.html as transparent PNGs, one per frame: node overlays.js outdir
const {chromium} = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const OUT = process.argv[2]; fs.mkdirSync(OUT, {recursive: true});
const srv = http.createServer((q, r) => { const f = path.join(__dirname, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, {'Content-Type': f.endsWith('.html') ? 'text/html' : f.endsWith('.json') ? 'application/json' : 'font/woff2'}); r.end(d); }); }).listen(8766);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 540, height: 960}, deviceScaleFactor: 2});
  await p.goto('http://127.0.0.1:8766/overlay.html'); await p.waitForFunction(() => window.ready);
  for (let i = 0; i < 1452; i++) { await p.evaluate(t => window.renderAt(t), i / 30); await p.screenshot({path: `${OUT}/o_${String(i + 1).padStart(4, '0')}.png`, omitBackground: true}); }
  await b.close(); srv.close(); console.log('overlays done');
})();
