// "CHILL GUY vs THE -94% CANDLE": a MEME ROYALE comedy short, rendered from the real game (offline, frozen clock).
// The game's own characters, animations and arena; skit sets (bedroom, group chat) built into the same 3D scene.
// usage: node skit.js <out.mp4 | dir> [preview]     env: SCALE (default 2; preview 0.5), FROM/TO (s) to render a slice, EVERY (preview stride)
const {chromium} = require('playwright');
const {spawn} = require('child_process');
const fs = require('fs');
const OUT = process.argv[2] || __dirname + '/skit.mp4', PREVIEW = process.argv[3] === 'preview';
const FPS = 30, DUR = 39.0, FROM = +(process.env.FROM || 0), TO = +(process.env.TO || DUR), EVERY = +(process.env.EVERY || 5);
const SCALE = +(process.env.SCALE || (PREVIEW ? 0.5 : 2));

(async () => {
  const dir = __dirname + '/prof_' + Date.now();
  const ctx = await chromium.launchPersistentContext(dir, {viewport: {width: 540, height: 960}, deviceScaleFactor: SCALE,
    args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist']});
  const p = ctx.pages()[0] || await ctx.newPage();
  p.on('pageerror', e => console.log('PAGEERR', e.message)); const seen = new Set(); p.on('console', m => { if (m.type() === 'error') { const t = m.text().slice(0, 300); if (!seen.has(t)) { seen.add(t); console.log('CERR', t); } } });
  await p.goto('https://memeroyale.imaginestudio.fun/?offline', {waitUntil: 'load'}); console.log('loaded');
  await p.waitForSelector('#boot .play', {timeout: 90000}); await p.click('#boot'); await p.waitForTimeout(2500);
  await p.evaluate(() => { const g = window.__game; g.menus.localArena = () => 'exchange'; setTimeout(() => g.battle(), 0); });
  await p.waitForFunction(() => window.__game.match?.running, null, {timeout: 240000}); console.log('battle running');
  await p.addStyleTag({content: `
    #ui{display:none!important}
    .L{position:fixed;inset:0;z-index:50;pointer-events:none}
    #cap{position:fixed;left:0;right:0;top:13%;display:flex;flex-direction:column;align-items:center;gap:4px;z-index:60}
    #cap div{font-family:"Lilita One",sans-serif;font-size:40px;line-height:1.05;text-align:center;color:#fff;padding:0 22px;
      -webkit-text-stroke:7px #1a0b3d;paint-order:stroke fill;text-shadow:0 5px 0 #1a0b3d;letter-spacing:.5px;text-transform:uppercase}
    #cap .y{color:#ffd84a} #cap .g{color:#7dff6a} #cap .r{color:#ff5a6e} #cap .s{font-size:27px} #cap .xl{font-size:58px}
    #cap div.pop{animation:pop .22s ease-out} @keyframes pop{0%{transform:scale(.6);opacity:0}70%{transform:scale(1.08)}100%{transform:scale(1);opacity:1}}
    #wm{position:fixed;left:12px;bottom:14px;z-index:60;width:64px;opacity:.92}
    /* phone notifications */
    #notes{position:fixed;left:16px;right:16px;top:30%;display:flex;flex-direction:column;gap:8px;z-index:55}
    .n{display:flex;gap:10px;align-items:center;background:rgba(245,245,250,.86);border-radius:18px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.35);
       font-family:-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif;color:#111;animation:nin .3s cubic-bezier(.2,1.4,.4,1)}
    .n i{flex:none;width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-style:normal;font-size:22px}
    .n b{display:block;font-size:13px;color:#555;font-weight:600;letter-spacing:.2px}
    .n span{display:block;font-size:16.5px;font-weight:700;line-height:1.2}
    @keyframes nin{0%{transform:translateY(-30px) scale(.9);opacity:0}100%{transform:none;opacity:1}}
    /* group chat */
    #chat{position:fixed;left:14px;right:14px;top:4%;z-index:55;display:flex;flex-direction:column;gap:7px}
    #chat .hd{align-self:center;background:rgba(20,10,45,.85);color:#fff;border-radius:16px;padding:6px 16px;font:600 15px -apple-system,Roboto,"Noto Sans",sans-serif;margin-bottom:4px}
    .m{max-width:78%;background:#2c2348;color:#fff;border-radius:18px 18px 18px 6px;padding:8px 13px;font:600 19px -apple-system,Roboto,"Noto Sans",sans-serif;
       box-shadow:0 6px 16px rgba(0,0,0,.35);animation:nin .28s cubic-bezier(.2,1.4,.4,1)}
    .m u{display:block;text-decoration:none;font-size:12.5px;opacity:.75;margin-bottom:1px}
    .m.me{align-self:flex-end;background:#2f9e5a;border-radius:18px 18px 6px 18px}
    /* the chart on screen-space (payoff) */
    #flash{position:fixed;inset:0;background:#fff;opacity:0;z-index:58}
  `});
  await p.evaluate(async () => {
    const THREE = await import('three');
    const g = window.__game, m = g.match, b = m.b, {stage, units, arena} = g, scene = stage.scene;
    m.bot = null; m.running = false;           // the sim waits for the arena act
    await units.preload(['chillguy', 'wojak', 'neet', 'jeanphil', 'useless', 'uselessarmy', 'ket', 'bonk', 'lmao', 'troll', 'dope']);
    const L = (id, cls = 'L') => { const d = document.createElement('div'); d.id = id; if (cls) d.className = cls; document.body.append(d); return d; };
    const cap = L('cap', ''), notes = L('notes', ''), chat = L('chat', ''), flash = L('flash', '');
    const wm = document.createElement('img'); wm.id = 'wm'; wm.src = 'assets/ui/logo.webp?v=4'; document.body.append(wm);
    // ---------------- clock
    let now = performance.now(); performance.now = () => now;
    window.__rafs = []; window.requestAnimationFrame = cb => { window.__rafs.push(cb); window.__raf = true; return window.__rafs.length; };
    // ---------------- camera
    const cam = stage.camera; let shake = 0;
    const C = {pos: [9, 30, 40], look: [9, 0, 16], fov: 36};
    stage.render = function () { const [px, py, pz] = C.pos, [lx, ly, lz] = C.look;
      cam.fov = C.fov; cam.position.set(px + Math.sin(now * 0.05) * shake, py + Math.cos(now * 0.071) * shake * 0.6, pz); cam.lookAt(lx, ly, lz);
      cam.updateProjectionMatrix(); cam.updateMatrixWorld(); shake = Math.max(0, shake * 0.92 - 0.003); if (window.__skit) { if (this.poolLight) this.poolLight.intensity = 0; } this.draw(); };
    const lerp = (a, c, k) => a + (c - a) * k, L3 = (a, c, k) => a.map((v, i) => lerp(v, c[i], k));
    const ease = t => t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t);
    // ---------------- the world the arena brought, and the skit sets
    const arenaKids = scene.children.filter(o => o !== units.root && !o.isLight);
    const lights = []; scene.traverse(o => { if (o.isLight) lights.push([o, o.intensity]); });
    const sky = {bg: scene.background?.clone?.(), fog: scene.fog && {near: scene.fog.near, far: scene.fog.far, c: scene.fog.color.clone()}};
    const std = (c, o = {}) => new THREE.MeshStandardMaterial({color: c, roughness: 0.85, ...o});
    const box = (w, h, d, mat, x, y, z, parent) => { const me = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); me.position.set(x, y, z); me.castShadow = me.receiveShadow = true; parent.add(me); return me; };
    const tex = (src) => { const t = new THREE.TextureLoader().load(src); t.colorSpace = THREE.SRGBColorSpace; return t; };
    // the monitor's chart: a canvas redrawn every frame
    const chartC = document.createElement('canvas'); chartC.width = 512; chartC.height = 300; const cg2 = chartC.getContext('2d');
    const chartT = new THREE.CanvasTexture(chartC); chartT.colorSpace = THREE.SRGBColorSpace;
    const drawChart = (k, pump) => {   // k: 0..1 how far the dump has gone; pump: 0..1 the tiny green candle at the end
      const W = 512, H = 300; cg2.fillStyle = '#0b0f1a'; cg2.fillRect(0, 0, W, H);
      cg2.strokeStyle = 'rgba(255,255,255,.07)'; cg2.lineWidth = 1; for (let y = 30; y < H; y += 45) { cg2.beginPath(); cg2.moveTo(0, y); cg2.lineTo(W, y); cg2.stroke(); }
      let y = 70; const n = 26, w = W / (n + 4);
      for (let i = 0; i < n; i++) { const f = i / n; if (f > k) break;
        const up = i < 6 ? (i % 2 === 0) : (i === 15);  // a little chop, then the cliff
        const d = up ? -10 : (i < 6 ? 8 : 10 + (i > 16 ? 16 : 7)), y2 = Math.min(H - 20, y + d);
        cg2.fillStyle = up ? '#26e07f' : '#ff3b5c'; const top = Math.min(y, y2), hgt = Math.max(4, Math.abs(y2 - y));
        cg2.fillRect(14 + i * w, top, w * 0.7, hgt); cg2.fillRect(14 + i * w + w * 0.32, top - 6, 2, hgt + 12); y = y2; }
      if (pump > 0) { cg2.fillStyle = '#26e07f'; const hh = 6 + pump * 6; cg2.fillRect(14 + n * w, y - hh, w * 0.7, hh); }
      cg2.font = 'bold 40px Lilita One, sans-serif'; cg2.fillStyle = pump > 0 ? '#26e07f' : '#ff3b5c';
      cg2.fillText(pump > 0 ? '-93.8%' : (k < 0.15 ? '+2.1%' : `-${Math.round(Math.min(94, k * 105))}%`), 18, 44);
      cg2.font = 'bold 18px sans-serif'; cg2.fillStyle = '#8b93a7'; cg2.fillText('$MYBAGS / USD   1m', 300, 34);
      chartT.needsUpdate = true; };
    // BEDROOM (3:47 AM) around (9, 0, 15)
    const bed = new THREE.Group(); bed.visible = false; scene.add(bed);
    box(9, 0.1, 9, std('#2a1f38'), 9, -0.05, 15.5, bed);                                   // floor
    box(9, 4.2, 0.2, std('#24183d'), 9, 2.1, 11.6, bed);                                   // back wall
    box(0.2, 4.2, 9, std('#20163a'), 4.6, 2.1, 15.5, bed);                                 // left wall
    box(2.6, 0.08, 1.0, std('#3b2c55'), 9, 0.78, 12.6, bed);                               // desk top
    for (const dx of [-1.2, 1.2]) box(0.08, 0.78, 0.9, std('#2d2244'), 9 + dx, 0.39, 12.6, bed);
    box(1.7, 1.0, 0.07, std('#111'), 9, 1.42, 12.3, bed);                                  // monitor
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.92), new THREE.MeshBasicMaterial({map: chartT, toneMapped: false})); scr.position.set(9, 1.42, 12.34); bed.add(scr);
    box(0.08, 0.3, 0.08, std('#111'), 9, 0.95, 12.35, bed);
    const can = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.2, 16), std('#7a2fe0', {emissive: '#3b0d80', emissiveIntensity: 0.6})); can.position.set(10, 0.92, 12.7); bed.add(can);  // MAX COPE can
    const poster = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 1.25), new THREE.MeshBasicMaterial({map: tex('assets/cards/wojak.webp?v=2')})); poster.position.set(6.6, 2.4, 11.72); bed.add(poster);
    const logo = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 1.2), new THREE.MeshBasicMaterial({map: tex('assets/ui/logo.webp?v=4'), transparent: true})); logo.position.set(11.4, 2.5, 11.72); bed.add(logo);
    const glow = new THREE.PointLight('#cfe0ff', 4, 6, 1.6); glow.position.set(9, 1.5, 13.2); bed.add(glow);       // the screen's light on him
    const lamp = new THREE.PointLight('#b05cff', 5, 8, 1.4); lamp.position.set(5.6, 2.6, 15.5); bed.add(lamp); const fill = new THREE.PointLight('#ffd9b0', 2.2, 7, 1.5); fill.position.set(10, 2, 18); bed.add(fill);
    const red = new THREE.PointLight('#ff2a4a', 0, 5, 1.5); red.position.set(9, 1.6, 13.0); bed.add(red);
    // GROUP CHAT stage: a purple studio with a couch
    const gc = new THREE.Group(); gc.visible = false; scene.add(gc);
    box(14, 0.1, 10, std('#2b1758'), 9, -0.05, 16, gc);
    box(14, 6, 0.2, std('#22124a'), 9, 3, 12.2, gc);
       // couch
    const spot = new THREE.PointLight('#ffd0ff', 7, 9, 1.3); spot.position.set(9, 4, 17); gc.add(spot);
    const spot2 = new THREE.PointLight('#7d5cff', 6, 9, 1.3); spot2.position.set(5, 2.5, 15); gc.add(spot2);
    let H0 = null; const setMode = (mode) => {
      const inArena = mode === 'arena'; window.__skit = !inArena;
      if (!H0) H0 = [stage.hemi.color.clone(), stage.hemi.groundColor.clone()];
      if (inArena) { stage.hemi.color.copy(H0[0]); stage.hemi.groundColor.copy(H0[1]); } else { stage.hemi.color.set('#d8dcff'); stage.hemi.groundColor.set('#3a2a55'); }
      for (const o of arenaKids) o.visible = inArena;
      bed.visible = mode === 'bed1' || mode === 'pay'; gc.visible = mode === 'gc';
      const night = mode === 'bed1' || mode === 'pay';
      for (const [o, i] of lights) o.intensity = inArena ? i : o.isHemisphereLight ? (night ? 0.4 : 0.65) : (o.isDirectionalLight && i > 1.5) ? i * (night ? 0.2 : 0.5) : 0;
      document.getElementById('ov').style.visibility = inArena ? 'visible' : 'hidden';
      if (inArena) { if (sky.bg) scene.background = sky.bg; if (sky.fog) { scene.fog.near = sky.fog.near; scene.fog.far = sky.fog.far; } }
      else { scene.background = new THREE.Color(mode !== 'gc' ? '#07060f' : '#170a33'); scene.fog.near = 40; scene.fog.far = 90; }
      for (const a of Object.values(A)) if (a.v) a.v.root.visible = a.mode === mode;
    };
    // ---------------- actors: display copies of the game's characters, puppeted
    const A = {};
    const actor = (key, card, mode, x, z, face) => { const e = units.showcase(card, x, z, face); const a = A[key] = {e, card, mode, want: 'idle', v: null, once: null};
      const grab = () => { a.v = units.views.get(e.id); if (!a.v) setTimeout(grab, 30); }; grab(); return a; };
    const anim = (a, name, loop = true) => { if (!a.v) return; if (loop) { a.want = name; a.once = null; units.play(a.v, name, 0.2); } else { a.once = name; units.play(a.v, name, 0.15); } };
    actor('cgB', 'chillguy', 'bed1', 9, 14.4, Math.PI);       // back to us, facing the screen
    actor('cgG', 'chillguy', 'gc', 11.2, 16.6, -Math.PI / 2);
    actor('woj', 'wojak', 'gc', 9, 15.2, 0);
    actor('neet', 'neet', 'gc', 8.05, 14.4, 0.3);
    actor('jp', 'jeanphil', 'gc', 9.95, 14.5, -0.3);
    actor('cgD', 'chillguy', 'pay', 9, 14.6, 0);
    actor('wojD', 'wojak', 'pay', 8.25, 14.1, 0.3);
    actor('jpD', 'jeanphil', 'pay', 9.75, 14.15, -0.3);
    window.A = A;
    // keep the puppets doing what they were told (the menu copies fall back to idle otherwise), no team rings
    const puppets = () => { for (const a of Object.values(A)) { const v = a.v; if (!v) continue; if (v.ring) v.ring.visible = false; v.root.scale.setScalar(0.5); if (!v.dark && v.mats) { v.dark = true; for (const mt of v.mats) if (mt.emissive) { mt.emissive.setRGB(0, 0, 0); mt.emissiveIntensity = 0; } }
      if (a.once) { if (v.cur && !v.cur.isRunning()) { a.once = null; units.play(v, a.want, 0.25); } }
      else if (v.curName !== a.want) units.play(v, a.want, 0.25); } };
    // ---------------- overlay text
    const say = (html) => { if (cap.dataset.h === html) return; cap.dataset.h = html; cap.innerHTML = html; cap.querySelectorAll('div').forEach(d => d.classList.add('pop')); };
    const note = (icon, bg, app, text) => { const d = document.createElement('div'); d.className = 'n'; d.innerHTML = `<i style="background:${bg}">${icon}</i><div><b>${app} · now</b><span>${text}</span></div>`; notes.prepend(d); };
    const msg = (who, text, me) => { const d = document.createElement('div'); d.className = 'm' + (me ? ' me' : ''); d.innerHTML = (me ? '' : `<u>${who}</u>`) + text; chat.append(d); };
    // ---------------- the sim's events, for the sound mix
    const S = {ev: [], t: 0}; const log = (t, k, x) => S.ev.push({t: +t.toFixed(3), k, ...(x || {})});
    const sfx = (s, vol) => log(S.t, 'sfx', {s, vol});
    const step0 = b.step.bind(b);
    b.step = function () { step0(); for (const e of b.events) if (['spell', 'tower_down', 'die', 'feared', 'end', 'knock'].includes(e.type)) log(S.t, e.type, {card: e.card, team: e.team, tower: e.tower}); };
    const done = {}; const once = (k, t, at, f) => { if (!done[k] && t >= at) { done[k] = true; f(); } };
    const towers = b.towers; let cg = null, allies = [];
    // ================= THE SCRIPT (video time t, seconds) =================
    const T_GC = 8.6, T_AR = 15.6, T_PAY = 32.0;
    window.SCRIPT = (t) => {
      S.t = t;
      // ---------- ACT 1: 3:47 AM
      once('bed', t, 0, () => { setMode('bed1'); });
      if (t < T_GC) {
        const k = Math.min(1, t / 3.6); drawChart(0.12 + k * 0.88, 0); red.intensity = 2 + Math.sin(t * 9) * 0.8 + k * 3;
        if (t < 4.9) { const e = ease(t / 4.9); C.fov = 38; C.pos = L3([10.6, 2.5, 18.4], [10.0, 2.1, 16.9], e); C.look = [9, 1.25, 12.6]; }
        else { const e = ease((t - 4.9) / 3.7); C.fov = 30; C.pos = L3([9.25, 1.32, 17.3], [9.15, 1.30, 16.5], e); C.look = [9, 1.08, 14.3]; }
        if (t < 2.4) say('<div class="s">3:47 AM</div><div>portfolio: <span class="r">-94%</span></div>'); else if (t < 4.9) say('<div class="s">3:47 AM</div><div>portfolio: <span class="r">-94%</span></div>');
        const N = [[0.9, '⚠️', '#ff3b5c', 'EXCHANGE', 'Position LIQUIDATED (x100)'], [1.5, '🚀', '#7a2fe0', 'DEV', 'gm frens. minor setback'],
          [2.1, '👩', '#ffb3c7', 'MOM', 'did u sell the jpeg money??'], [2.7, '🏠', '#ffd84a', 'LANDLORD', 'rent.'], [3.3, '💀', '#222', 'THE BOYS (99+)', "IT'S OVER"]];
        for (const [at, ...n] of N) once('n' + at, t, at, () => { note(...n); sfx('ui_pop', 0.9); });
        once('turn', t, 4.9, () => { notes.innerHTML = ''; A.cgB.e.face = 0; say('<div class="g">him:</div>'); });
        once('shrug1', t, 5.5, () => { anim(A.cgB, 'emote', false); });
        once('bark1', t, 5.9, () => { sfx('bark_chillguy', 1.0); say('<div class="g">him:</div><div>"i\'m just a chill guy"</div>'); });
      }
      // ---------- ACT 2: the group chat
      once('gc', t, T_GC, () => { setMode('gc'); say(''); notes.innerHTML = ''; chat.innerHTML = '<div class="hd">THE BOYS 🚀📉 · 4 members</div>';
        anim(A.woj, 'run'); anim(A.neet, 'idle'); A.neet.e.face = 0.3; anim(A.jp, 'lose'); anim(A.cgG, 'walk'); });
      if (t >= T_GC && t < T_AR) { const u = t - T_GC;
        // WOJAK: laps of panic around the room's middle
        const ang = u * 2.6, R = 0.8; A.woj.e.x = 9 + Math.cos(ang) * R; A.woj.e.z = 16.2 + Math.sin(ang) * R * 0.7; A.woj.e.face = Math.atan2(-Math.sin(ang), Math.cos(ang)) + 0;
        A.woj.e.face = Math.atan2(-Math.sin(ang) * R, Math.cos(ang) * R * 0.7);
        // CHILL GUY strolls in and stops in the middle of it
        const w = Math.min(1, u / 3.2); A.cgG.e.x = lerp(11.2, 9.0, w); A.cgG.e.z = lerp(16.6, 16.2, w); A.cgG.e.face = w < 1 ? -Math.PI / 2 - 0.35 : 0;
        once('cgstop', t, T_GC + 3.2, () => anim(A.cgG, 'idle'));
        const e = ease(u / 7); C.fov = 34; C.pos = L3([9, 2.3, 21.6], [9, 2.0, 20.6], e); C.look = [9, 0.75, 15.3];
        once('m1', t, T_GC + 0.3, () => { msg('WOJAK', "it's over. it's so over"); sfx('ui_pop'); });
        once('m2', t, T_GC + 1.2, () => { msg('NEET', 'WHO SOLD. WHO. SOLD.'); sfx('ui_pop'); anim(A.neet, 'attack1', false); sfx('atk_neet', 0.7); });
        once('m3', t, T_GC + 2.1, () => { msg('JEAN PHIL', 'sacré bleu. je suis liquidated'); sfx('die_jeanphil', 0.9); });
        once('m4', t, T_GC + 3.6, () => { msg('', 'zoom out bro', true); sfx('ui_pop'); anim(A.cgG, 'emote', false); });
        once('m5', t, T_GC + 4.8, () => { msg('WOJAK', 'okay.'); sfx('bark_wojak', 1.0); });
        once('m6', t, T_GC + 5.6, () => { msg('NEET', 'ok but how do we make it back'); anim(A.neet, 'attack3', false); sfx('ui_pop'); });
      }
      // ---------- ACT 3: settle it in the arena
      once('ar', t, T_AR, () => { setMode('arena'); chat.innerHTML = ''; m.running = true;
        cg = b.deploy(0, 'chillguy', 3.5, 22.5)[0];
        allies = [...b.deploy(0, 'useless', 2.6, 24), ...b.deploy(0, 'jeanphil', 4.8, 24.4), ...b.deploy(0, 'wojak', 1.8, 23.4)];
        b.deploy(1, 'troll', 4.2, 12); sfx('deploy_drop'); flash.style.opacity = 0.85; });
      if (t >= T_AR && t < T_PAY && cg) { const u = t - T_AR; flash.style.opacity = Math.max(0, 0.85 - u * 3);
        cg.hp = cg.max;
        if (u < 3.4) { const e = ease(u / 3.4); C.fov = 36; C.pos = L3([9, 24, 40], [cg.x + 5.5, 9.5, cg.z + 11.5], e); C.look = L3([7, 0, 18], [cg.x, 1.2, cg.z - 2], e);
          say('<div class="s">so he settled it like an adult:</div><div class="y">in meme royale</div>'); }
        once('panic', t, T_AR + 3.0, () => { b.castSpell(1, 'panicsell', cg.x + 0.2, cg.z + 0.6); });
        if (u >= 3.4 && u < 7.8) { const e = ease((u - 3.4) / 4.4); C.fov = 33; C.pos = L3([cg.x - 6.5, 8.5, cg.z + 10], [cg.x - 5.2, 7.2, cg.z + 8.6], e); C.look = [cg.x, 1.2, cg.z - 1];
          say(u < 4.6 ? '<div>enemy casts <span class="r">panic sell</span></div>' : '<div>enemy casts <span class="r">panic sell</span></div><div class="s">the squad: runs home</div><div class="g">him: keeps walking</div>'); }
        once('rug0', t, T_AR + 7.0, () => { b.deploy(1, 'bonk', cg.x + 0.5, cg.z - 2.6); b.deploy(1, 'useless', cg.x - 0.4, cg.z - 3.2); });
        once('rug', t, T_AR + 7.6, () => { b.castSpell(1, 'rug', cg.x + 0.1, cg.z - 0.4); });
        once('rugshake', t, T_AR + 8.6, () => { shake = 0.6; });
        if (u >= 7.8 && u < 11.0) { const e = ease((u - 7.8) / 3.2); C.fov = 34; C.pos = L3([cg.x + 8, 9.5, cg.z + 8], [cg.x + 6.4, 8.2, cg.z + 9.5], e); C.look = [cg.x, 1.2, cg.z - 1];
          say(u < 8.9 ? '<div>dev <span class="r">rug pulls</span></div>' : '<div>dev <span class="r">rug pulls</span></div><div class="y">he didn\'t even notice</div>'); }
        once('rig', t, T_AR + 10.6, () => { const R = towers[1][0]; R.hp = Math.min(R.hp, 140); cg.x = 3.6; cg.z = 8.7; });
        if (u >= 11.0 && u < 14.6) { const R = towers[1][0], e = ease((u - 11) / 3.6); C.fov = 36; C.pos = L3([R.x + 9.5, 10.5, R.z + 14], [R.x + 7.5, 8.8, R.z + 12], e); C.look = [R.x + 0.6, 1.4, R.z + 1.4];
          say(R.dead ? '<div>strategy? <span class="g">none</span></div><div class="y">just vibes</div>' : '<div>strategy?</div>'); }
        once('hq', t, T_AR + 14.4, () => { const H = towers[1][2]; H.hp = Math.min(H.hp, 140); });
        once('hqmove', t, T_AR + 14.6, () => { cg.x = 7.0; cg.z = 5.0; for (const a2 of allies) if (!a2.dead) a2.hp = 0; });
        if (u >= 14.6) { const H = towers[1][2], e = ease((u - 14.6) / 1.8); C.fov = 34; C.pos = L3([cg.x + 3, 7, cg.z + 13], [cg.x + 2.4, 5.4, cg.z + 10.5], e); C.look = [cg.x - 0.6, 1.8, cg.z - 1.2];
          say(H.dead ? '<div class="xl">3 crowns</div><div class="g">still chill</div>' : ''); }
        if (b.over && !done.won) { done.won = true; sfx('victory', 0.8); sfx('crowd_cheer', 0.8); const v = units.views.get(cg.id); setTimeout(() => {}, 0); if (v) { units.play(v, 'emote', 0.2); v.attackUntil = now + 99999; } }
      }
      // ---------- ACT 4: the payoff
      once('pay', t, T_PAY, () => { m.running = false; setMode('pay'); say(''); flash.style.opacity = 0; anim(A.wojD, 'idle'); anim(A.jpD, 'idle'); });
      if (t >= T_PAY) { const u = t - T_PAY; drawChart(1, Math.min(1, u / 0.8)); red.intensity = 0; glow.color.set('#9dffc4'); glow.intensity = 3.5;
        const e = ease(u / 7); C.fov = 34; C.pos = L3([9, 1.95, 20.8], [9, 1.8, 19.8], e); C.look = [9, 1.05, 14.3];
        say(u < 1.6 ? '<div class="s">5 minutes later</div><div>portfolio: <span class="g">-93.8%</span></div>' : u < 4.1 ? '<div class="xl g">WE\'RE SO BACK</div>' : '<div class="g">him:</div><div>"oh, did something happen?"</div>');
        once('back', t, T_PAY + 1.6, () => { anim(A.wojD, 'win'); anim(A.jpD, 'win'); sfx('crowd_cheer', 0.9); sfx('bark_neet', 0.9); });
        once('cgshrug', t, T_PAY + 4.3, () => { anim(A.cgD, 'emote', false); sfx('bark_chillguy', 1.0); });
      }
      puppets();
    };
    window.STEP = (t, ms) => { window.SCRIPT(t); now += ms; const q = window.__rafs; window.__rafs = []; for (const cb of q) { try { cb(now); } catch (e) { console.error('raf', e.message); } } };
    window.__S = S; drawChart(0.12, 0);
  });
  console.log('script installed'); await p.waitForFunction(() => !!window.__raf, null, {timeout: 15000}); console.log('clock frozen');
  await p.evaluate(() => { const m = window.__game.match; m.app = Object.create(m.app); m.app.results = () => {}; });
  await p.evaluate(() => new Promise(r => setTimeout(r, 2500)));   // textures (poster, logo) arrive

  let ff = null; const N = Math.round(DUR * FPS);
  if (!PREVIEW) ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', OUT]);
  else fs.mkdirSync(OUT, {recursive: true});
  const t0 = Date.now();
  for (let i = 0; i < N; i++) {
    const t = i / FPS;
    await p.evaluate(([t, ms]) => window.STEP(t, ms), [t, 1000 / FPS]);
    if (PREVIEW) { if (i % EVERY === 0 && t >= FROM && t <= TO) await p.screenshot({path: `${OUT}/f_${String(i).padStart(4, '0')}.jpg`, type: 'jpeg', quality: 75}); }
    else { const buf = await p.screenshot({type: 'jpeg', quality: 93}); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
    if (i % 90 === 0) console.log(`frame ${i}/${N} t=${t.toFixed(1)} ${((Date.now() - t0) / 1000 / (i + 1)).toFixed(2)}s/f`);
  }
  const ev = await p.evaluate(() => window.__S.ev);
  fs.writeFileSync(PREVIEW ? OUT + '/events.json' : OUT.replace(/\.mp4$/, '') + '_events.json', JSON.stringify(ev));
  if (ff) { ff.stdin.end(); await new Promise(r => ff.on('close', r)); }
  await ctx.close(); fs.rmSync(dir, {recursive: true, force: true});
  console.log('done');
})();
