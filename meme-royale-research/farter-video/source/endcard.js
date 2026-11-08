const {chromium} = require('playwright'); const {spawn} = require('child_process');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 540, height: 960}, deviceScaleFactor: 2});
  await p.goto('file://' + __dirname + '/end/' + (process.argv[4] || 'end.html')); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(500);
  const FPS = 30, N = Math.round(+(process.argv[3] || 4) * FPS), out = process.argv[2];
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', out]);
  for (let i = 0; i < N; i++) { await p.evaluate(t => window.F(t), i / FPS); const buf = await p.screenshot({type: 'jpeg', quality: 94}); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (i === N - 1) await p.screenshot({path: __dirname + '/end_last.jpg'}); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await b.close(); console.log('end card done');
})();
