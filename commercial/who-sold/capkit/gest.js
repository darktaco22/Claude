// Pose layer for the Mixamo rig every Meme Royale character shares. Adds bone rotations (degrees, local, post-multiplied) on top of the game's
// own idle animation after units.update(); gestures are keyed to battle time so renders are deterministic.
(() => {
  const G = window.__game, U = G.units; const D = window.__dir;
  const sm = x => x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x);
  const env = (u, a = 0.22, b = 0.28) => Math.min(sm(u / a), sm((1 - u) / b));
  const S = Math.sin, PI = Math.PI;
  // each gesture: u in [0,1] -> {Bone: [x, y, z]} (degrees); w = envelope weight
  const GESTS = {
    shake:   (u, w) => ({Head: [0, 26 * S(u * PI * 6) * w, 0], Neck: [0, 9 * S(u * PI * 6) * w, 0]}),
    nod:     (u, w) => ({Head: [15 * (0.5 - 0.5 * Math.cos(u * PI * 6)) * w, 0, 0], Spine2: [3 * S(u * PI * 6) * w, 0, 0]}),
    tilt:    (u, w) => ({Head: [4 * w, 0, -20 * w], Neck: [0, 0, -6 * w]}),
    lookdown:(u, w) => ({Head: [30 * w, 0, 0], Neck: [14 * w, 0, 0], Spine1: [8 * w, 0, 0], Spine2: [6 * w, 0, 0]}),
    sob:     (u, w) => ({Head: [26 * w + 3 * S(u * PI * 14) * w, 0, 0], Neck: [12 * w, 0, 0], Spine1: [9 * w + 2 * S(u * PI * 14) * w, 0, 0], Spine2: [6 * w, 0, 0]}),
    whome:   (u, w) => ({LeftArm: [0, 0, 44 * w], LeftForeArm: [0, 0, 10 * w], Head: [5 * w, 0, -9 * w]}),
    present: (u, w) => ({RightArm: [0, 52 * w, 6 * w], RightForeArm: [-18 * w, 0, 0], Head: [0, -9 * w, 0]}),
    point:   (u, w) => ({RightArm: [-40 * w, 40 * w, 0], Head: [2 * w, -10 * w, 0]}),
    wide:    (u, w) => ({RightArm: [0, 55 * w, 0], LeftArm: [0, -55 * w, 0], Spine2: [-5 * w, 0, 0], Head: [-5 * w, 0, 0]}),
    stop:    (u, w) => ({RightArm: [0, 0, -64 * w], RightForeArm: [-6 * w, 0, 0], Head: [-3 * w, 8 * w, 0]}),
    talk:    (u, w) => { const t = u * 40; return {Head: [3.2 * S(t * 1.9) * w, 6 * S(t * 0.9 + 1) * w, 2.5 * S(t * 0.7) * w], Spine2: [1.2 * S(t * 1.3) * w, 0, 0],
                 RightArm: [0, 4 * w * (0.5 + 0.5 * S(t * 1.7)), -2 * w * (0.5 + 0.5 * S(t * 1.1 + 2))], RightForeArm: [-3 * w * (0.5 + 0.5 * S(t * 2.3)), 0, 0]}; },
  };
  window.__gests = [];                    // {i: person index, name, t0, dur, amp}
  window.__idle = true;                   // breathing / sway on every person
  const add = (o, k, p) => { if (!o[k]) o[k] = [0, 0, 0]; o[k][0] += p[0]; o[k][1] += p[1]; o[k][2] += p[2]; };
  const ou = U.update.bind(U);
  U.update = (dt, a) => {
    ou(dt, a);
    const m = window.__match, t = window.__poseT != null ? window.__poseT : (m && m.running ? m.b.t : 0);
    (window.__show || []).forEach((e, i) => {
      const v = e && U.views.get(e.id); if (!v) return; const P = {};
      if (window.__idle) { const ph = i * 1.7; add(P, 'Spine1', [0.9 * S(t * 1.5 + ph), 0, 0]); add(P, 'Spine2', [0.7 * S(t * 1.5 + ph + 0.4), 0, 0]); add(P, 'Head', [0.8 * S(t * 0.8 + ph), 1.6 * S(t * 0.37 + ph), 0.5 * S(t * 0.5 + ph)]); }
      for (const g of window.__gests) {
        if (g.i !== i) continue; const u = (t - g.t0) / g.dur; if (u < 0 || u > 1) continue;
        const f = GESTS[g.name]; if (!f) continue; const p = f(u, env(u) * (g.amp || 1));
        for (const k in p) add(P, k, p[k]);
      }
      v.root.traverse(o => { if (!o.isBone) return; const p = P[o.name.replace('mixamorig', '')]; if (!p) return;
        const eu = new o.rotation.constructor(p[0] * PI / 180, p[1] * PI / 180, p[2] * PI / 180, 'XYZ'); o.quaternion.multiply(o.quaternion.clone().setFromEuler(eu)); });
    });
  };
  window.GEST = (i, name, t0, dur, amp = 1) => window.__gests.push({i, name, t0, dur, amp});
  window.__GESTS = Object.keys(GESTS);
})();
