// Runs inside the game page. Scripts a battle (who plays what, where, when) and drives the game's own camera
// for cinematic shots, so the commercial is rendered by the real engine.
(() => {
  const G = window.__game;
  const D = window.__dir = {actions: [], shots: [], done: new Set(), log: []};
  const lerp = (a, b, k) => a + (b - a) * k, ease = k => k < 0 ? 0 : k > 1 ? 1 : k * k * (3 - 2 * k);

  D.play = (b, team, id, x, z) => {
    b.copium[team] = 10;
    let s = b.hands[team].indexOf(id);
    if (s < 0) { b.hands[team][0] = id; s = 0; }
    const ok = b.play(team, s, x, z);
    D.log.push([b.t.toFixed(2), team, id, x, z, ok]);
    return ok;
  };
  D.drop = (b, team, id, x, z) => { D.log.push([b.t.toFixed(2), team, id, 'deploy']); return b.deploy(team, id, x, z); };

  D.hud = on => {
    for (const el of [document.getElementById('ui'), document.getElementById('ov')]) el.style.visibility = on ? 'visible' : 'hidden';
  };

  // camera: orbit around a point. a (deg) = 0 looks from my side (+z) toward the opponent (-z)
  D.orbit = (cx, cy, cz, r, h, a0, a1, fov = 40) => (k, cam) => {
    const a = THREE_deg(lerp(a0, a1, ease(k)));
    cam.fov = fov;
    cam.position.set(cx + Math.sin(a) * r, cy + h, cz + Math.cos(a) * r);
    cam.lookAt(cx, cy, cz);
  };
  D.dolly = (p0, p1, l0, l1, fov0 = 40, fov1 = fov0) => (k, cam) => {
    const e = ease(k);
    cam.fov = lerp(fov0, fov1, e);
    cam.position.set(lerp(p0[0], p1[0], e), lerp(p0[1], p1[1], e), lerp(p0[2], p1[2], e));
    cam.lookAt(lerp(l0[0], l1[0], e), lerp(l0[1], l1[1], e), lerp(l0[2], l1[2], e));
  };
  // follow an entity found by a predicate, from an offset
  D.follow = (pick, off, look = [0, 1.2, 0], fov = 38) => {
    let sx = null, sz = null;
    return (k, cam, b) => {
      const e = [...b.ents.values()].find(pick);
      if (e) { sx = sx == null ? e.x : lerp(sx, e.x, 0.12); sz = sz == null ? e.z : lerp(sz, e.z, 0.12); }
      if (sx == null) return false;
      cam.fov = fov;
      cam.position.set(sx + off[0], off[1], sz + off[2]);
      cam.lookAt(sx + look[0], look[1], sz + look[2]);
    };
  };
  function THREE_deg(d) { return d * Math.PI / 180; }

  // per-frame hook: actions by battle time, camera by battle time
  const st = G.stage; st.__origDraw ||= st.draw.bind(st); const od = st.__origDraw;
  st.draw = () => {
    const m = window.__match, b = m?.b;
    const t = m?.running ? b.t : -1;
    const shot = D.shots.find(s => t >= s.t0 && t < s.t1) || (t < 0 ? D.pre : null);
    const cam = st.camera;
    if (shot && shot.cam) {
      cam.clearViewOffset();
      const k = t < 0 ? D.preK ?? 0 : (t - shot.t0) / (shot.t1 - shot.t0);
      const r = shot.cam(k, cam, b);
      cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); cam.updateMatrixWorld();
      D.hud(!!shot.hud);
      D.curCustom = true;
    } else if (D.curCustom) {   // back to the game's own framing
      D.curCustom = false; D.hud(true); st.fit();
    }
    if (!D.skipDraw) od();
  };
  D.tick = () => {
    const m = window.__match; if (!m?.running) return;
    const b = m.b;
    for (const [i, a] of D.actions.entries()) if (!D.done.has(i) && b.t >= a.t) { D.done.add(i); try { a.do(b, m); } catch (e) { D.log.push(['ERR', String(e)]); } }
  };
})();
