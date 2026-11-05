// Virtual clock: rAF, performance.now, timers and CSS/Web animations all follow window.__vt (ms).
(() => {
  const realSetInterval = window.setInterval.bind(window), realNow = performance.now.bind(performance);
  let vt = realNow(), mode = 'auto', lastReal = realNow();
  let rafs = [], rafId = 1, timers = new Map(), tid = 1;
  performance.now = () => vt;
  window.requestAnimationFrame = cb => { const id = rafId++; rafs.push([id, cb]); return id; };
  window.cancelAnimationFrame = id => { rafs = rafs.filter(r => r[0] !== id); };
  window.setTimeout = (cb, ms = 0, ...a) => { const id = tid++; timers.set(id, {at: vt + Math.max(0, +ms || 0), cb, a}); return id; };
  window.clearTimeout = id => timers.delete(id);
  window.setInterval = (cb, ms = 0, ...a) => { const id = tid++; const t = {at: vt + Math.max(1, +ms || 1), cb, a, every: Math.max(1, +ms || 1)}; timers.set(id, t); return id; };
  window.clearInterval = id => timers.delete(id);
  function runTimers() {
    for (let guard = 0; guard < 1000; guard++) {
      let best = null, bid = 0;
      for (const [id, t] of timers) if (t.at <= vt && (!best || t.at < best.at)) { best = t; bid = id; }
      if (!best) return;
      if (best.every) best.at += best.every; else timers.delete(bid);
      try { typeof best.cb === 'function' ? best.cb(...best.a) : eval(best.cb); } catch (e) { console.error(e); }
    }
  }
  function frame() {
    runTimers();
    const list = rafs; rafs = [];
    for (const [, cb] of list) { try { cb(vt); } catch (e) { console.error(e); } }
  }
  function pumpAnims(ms) {
    for (const a of document.getAnimations()) {
      try { if (a.playState === 'running' || a.playState === 'paused') { if (a.playState === 'running') a.pause(); a.currentTime = (a.currentTime || 0) + ms; } } catch {}
    }
  }
  realSetInterval(() => {
    const n = realNow();
    if (mode === 'auto') { vt += Math.min(50, n - lastReal); frame(); }
    lastReal = n;
  }, 16);
  window.__vc = {
    get t() { return vt; },
    manual() { mode = 'manual'; for (const a of document.getAnimations()) try { a.pause(); } catch {} },
    auto() { mode = 'auto'; for (const a of document.getAnimations()) try { if (a.playState === 'paused') a.play(); } catch {} },
    step(ms) { vt += ms; pumpAnims(ms); frame(); },
  };
})();
