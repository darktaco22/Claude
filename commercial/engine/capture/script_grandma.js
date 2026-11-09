// "I WILL FIND YOU": two real-gameplay passes for the phone screens (phone layout, the game's own HUD).
//   window.__SCENE = 'loss'    NEET (bottom) loses to xX_Grandma_Rugs_Xx: her RUG PULL wipes his push, his king falls
//   window.__SCENE = 'grandma' Grandma (bottom) watches NEET's push cross the river and RUG PULLs it
(() => {
  const D = window.__dir;
  const P = (team, id, x, z) => b => D.play(b, team, id, x, z);
  const centroid = (b, team) => { const u = [...b.ents.values()].filter(e => e.kind === 'unit' && e.team === team && !e.dead); if (!u.length) return null;
    return [u.reduce((s, e) => s + e.x, 0) / u.length, u.reduce((s, e) => s + e.z, 0) / u.length]; };
  D.pre = null; D.shots = [];
  if (window.__SCENE === 'loss') {
    D.actions = [
      {t: 0.3, do: P(0, 'neet', 4.0, 19.0)}, {t: 0.6, do: P(0, 'lmao', 3.0, 21.0)}, {t: 0.9, do: P(0, 'useless', 4.5, 20.5)},
      {t: 3.6, do: b => { const c = centroid(b, 0) || [4, 17]; D.play(b, 1, 'rug', c[0], c[1]); }},
      {t: 4.2, do: P(1, 'whale', 9.0, 14.0)},
      {t: 5.2, do: b => { for (const t of b.towers[0]) if (t) t.hp = Math.min(t.hp, 60); }},
      {t: 5.6, do: b => { D.play(b, 1, 'godcandle', 9.0, 29.5); }},
    ];
  } else {
    D.actions = [
      {t: 0.2, do: P(1, 'whale', 3.5, 9.5)}, {t: 0.5, do: P(1, 'neet', 3.0, 11.0)}, {t: 0.8, do: P(1, 'lmao', 4.2, 11.5)},
      {t: 1.1, do: P(1, 'useless', 3.6, 12.5)},
      {t: 5.4, do: b => { const c = centroid(b, 1) || [3.5, 18]; D.rugAt = c; D.play(b, 0, 'rug', c[0], c[1]); }},
    ];
  }
})();
