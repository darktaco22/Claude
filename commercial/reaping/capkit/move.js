// keyframed moves for showcase people: window.MOVE(i, t0, dur, dx, dz, hop, faceTo) - slides e.x/e.z with an optional hop arc (applied after units.update)
(() => {
  const U = window.__game.units; window.__moves = [];
  const sm = x => x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x);
  const ou = U.update.bind(U);
  U.update = (dt, a) => {
    const m = window.__match, t = m && m.running ? m.b.t : 0;
    for (const mv of window.__moves) { const e = (window.__show || [])[mv.i]; if (!e) continue;
      if (mv.x0 == null && t >= mv.t0) { mv.x0 = e.x; mv.z0 = e.z; }
      if (mv.x0 == null) continue; const u = sm((t - mv.t0) / mv.dur);
      e.x = e.px = mv.x0 + mv.dx * u; e.z = e.pz = mv.z0 + mv.dz * u; if (mv.face != null && t >= mv.t0) e.face = mv.face; }
    ou(dt, a);
    for (const mv of window.__moves) { if (!mv.hop || mv.x0 == null) continue; const e = (window.__show || [])[mv.i]; const v = e && U.views.get(e.id); if (!v) continue;
      const u = (t - mv.t0) / mv.dur; if (u > 0 && u < 1) v.root.position.y += mv.hop * Math.sin(u * Math.PI); }
  };
  window.MOVE = (i, t0, dur, dx, dz, hop = 0, face = null) => window.__moves.push({i, t0, dur, dx, dz, hop, face});
})();
