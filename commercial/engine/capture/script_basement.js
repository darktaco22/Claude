// The battle's choreography (battle seconds) and the camera plan, for __dir (director.js).
(() => {
  const D = window.__dir;
  const P = (team, id, x, z) => b => D.play(b, team, id, x, z);
  const centroid = (b, team) => { const u = [...b.ents.values()].filter(e => e.kind === 'unit' && e.team === team && !e.dead); if (!u.length) return null;
    return [u.reduce((s, e) => s + e.x, 0) / u.length, u.reduce((s, e) => s + e.z, 0) / u.length]; };
  D.actions = [
    {t: 0.2, do: P(0, 'giga', 3.5, 20.5)},
    {t: 0.6, do: P(1, 'moodeng', 3.5, 11.5)},
    {t: 1.4, do: P(1, 'bonk', 14.5, 10.5)},
    {t: 1.7, do: P(1, 'chillguy', 13.2, 9.5)},
    {t: 2.0, do: P(0, 'popcat', 14.5, 21.5)},
    {t: 2.4, do: P(0, 'wojak', 15.6, 22.5)},
    {t: 3.0, do: P(0, 'pepe', 5.0, 24.0)},
    {t: 6.0, do: P(0, 'pump', 14.5, 17.5)},
    {t: 6.5, do: P(1, 'troll', 4.5, 12.0)},
    {t: 10.0, do: b => { b.towers[1][0].hp = Math.min(b.towers[1][0].hp, 240); }},
    {t: 11.4, do: P(0, 'godcandle', 3.5, 6.5)},
    {t: 14.0, do: b => { const c = centroid(b, 0) || [5, 12]; D.rugAt = c; D.play(b, 1, 'rug', c[0], c[1]); }},
    {t: 15.6, do: P(0, 'whale', 9.0, 22.0)},
    {t: 15.9, do: P(1, 'goat', 9.0, 9.5)},
    {t: 16.3, do: P(0, 'nyancat', 12.5, 20.0)},
    {t: 16.6, do: P(1, 'thisisfine', 6.0, 9.0)},
    {t: 17.0, do: P(0, 'popcat', 4.0, 21.0)},
    {t: 17.3, do: P(1, 'fud', 12.0, 19.0)},
    {t: 17.8, do: P(0, 'wojak', 15.0, 20.0)},
    {t: 18.2, do: P(1, 'bonk', 13.5, 8.0)},
    {t: 20.0, do: b => { b.towers[1][2].hp = Math.min(b.towers[1][2].hp, 240); }},
    {t: 21.0, do: P(0, 'godcandle', 9.0, 2.5)},
  ];
  const mid = (b, a, c) => { const A = [...b.ents.values()].find(e => e.kind === 'unit' && e.card === a), C = [...b.ents.values()].find(e => e.kind === 'unit' && e.card === c);
    const L = [A, C].filter(Boolean); if (!L.length) return null; return [L.reduce((s, e) => s + e.x, 0) / L.length, L.reduce((s, e) => s + e.z, 0) / L.length]; };
  let clashC = null;
  const clash = (k, cam, b) => { const m = mid(b, 'giga', 'moodeng'); if (m) clashC = clashC ? [clashC[0] + (m[0] - clashC[0]) * 0.1, clashC[1] + (m[1] - clashC[1]) * 0.1] : m;
    const c = clashC || [3.5, 16.4]; return D.orbit(c[0], 1.1, c[1], 5.2, 1.3, 70, 25, 40)(k, cam); };
  if (window.__PASS === 'phone') { D.pre = null; D.shots = []; return; }
  // the opening: a crane from low over the basement up to the game's own framing
  const crane = D.dolly([-8, 10, 36], [9, 75.26, 64.0], [8, 0, 17], [9, 0, 20.55], 42, 30);
  D.pre = {hud: true, cam: () => { const k = Math.min(1, (performance.now() - (D.preStart ?? performance.now())) / 3200); return crane(k, window.__game.stage.camera); }};
  D.shots = [
    {t0: 0.0, t1: 4.0, cam: D.dolly([0.5, 2.6, 26.5], [1.8, 2.2, 22.5], [3.5, 1.4, 19.0], [3.5, 1.2, 16.0], 40, 38)},   // GIGA drops in, from behind
    {t0: 4.0, t1: 8.0, cam: clash},                                                                                         // GIGA vs MOO DENG on the bridge
    {t0: 8.0, t1: 11.0, cam: D.follow(e => e.kind === 'unit' && e.team === 0 && e.card === 'popcat', [4.2, 3.4, -6.8], [0, 1.0, 0], 42)},
    {t0: 11.0, t1: 14.0, cam: D.dolly([11.0, 5.0, 16.0], [9.5, 4.2, 13.5], [3.5, 3.0, 6.5], [3.5, 2.6, 6.5], 46, 44)},   // God Candle on the tower
    {t0: 14.0, t1: 16.2, cam: (k, cam) => { const c = D.rugAt || [5, 12]; return D.orbit(c[0], 0.6, c[1], 6.0, 2.8, -30, 10, 44)(k, cam); }},
    {t0: 16.2, t1: 20.0, cam: D.dolly([-1.5, 9.0, 27.0], [19.5, 9.0, 25.0], [7.0, 0.5, 14.0], [11.0, 0.5, 13.0], 46, 46)},  // the big fight, a sweep
    {t0: 20.0, t1: 30.0, cam: D.dolly([9, 4.6, 13.5], [9, 3.4, 10.0], [9, 3.4, 2.5], [9, 3.4, 2.5], 50, 46)},          // the king falls
  ];
})();
