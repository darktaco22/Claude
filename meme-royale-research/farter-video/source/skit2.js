// "THE FARTCOIN INVESTOR": a MEME ROYALE mockumentary short, rendered from the real game (offline, frozen clock).
// v2 of the skit pipeline: spoken dialogue (Piper TTS, timed from the clip lengths), word-by-word subtitles, depth of field
// (three's BokehPass), handheld documentary camera, snap punch-ins, particle gas clouds, lower thirds and a title card.
// usage: node skit2.js <out.mp4 | dir> [preview]     env: SCALE, FROM/TO, EVERY (preview)
const {chromium} = require('playwright');
const {spawn} = require('child_process');
const fs = require('fs');
const OUT = process.argv[2] || __dirname + '/fart.mp4', PREVIEW = process.argv[3] === 'preview';
const SEG0 = +(process.env.SEG0 || 0), SEG1 = +(process.env.SEG1 || 1e9);
const FPS = 30, FROM = +(process.env.FROM || 0), EVERY = +(process.env.EVERY || 5);
const SCALE = +(process.env.SCALE || (PREVIEW ? 0.5 : 2));
const DUR_TTS = Object.fromEntries(fs.readFileSync(__dirname + '/../tts/dur.txt', 'utf8').trim().split('\n').map(l => { const [k, v] = l.split(' '); return [k, +v]; }));
DUR_TTS.f_proof = 2.24;

(async () => {
  const dir = __dirname + '/prof_' + Date.now();
  const ctx = await chromium.launchPersistentContext(dir, {viewport: {width: 540, height: 960}, deviceScaleFactor: SCALE,
    args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist']});
  const p = ctx.pages()[0] || await ctx.newPage();
  const seen = new Set();
  p.on('pageerror', e => console.log('PAGEERR', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('SKIT')) { const t = m.text().slice(0, 300); if (!seen.has(t)) { seen.add(t); console.log('C', t); } } });
  await p.goto('https://memeroyale.imaginestudio.fun/?offline', {waitUntil: 'load'}); console.log('loaded');
  await p.waitForSelector('#boot .play', {timeout: 90000}); await p.click('#boot'); await p.waitForTimeout(2500);
  await p.evaluate(() => { const g = window.__game; g.menus.localArena = () => 'exchange'; setTimeout(() => g.battle(), 0); });
  await p.waitForFunction(() => window.__game.match?.running, null, {timeout: 240000}); console.log('battle running');
  await p.addStyleTag({content: `
    #ui{display:none!important}
    #cap{position:fixed;left:0;right:0;top:11%;display:flex;flex-direction:column;align-items:center;gap:4px;z-index:60}
    #cap div{font-family:"Lilita One",sans-serif;font-size:38px;line-height:1.05;text-align:center;color:#fff;padding:0 22px;
      -webkit-text-stroke:7px #1a0b3d;paint-order:stroke fill;text-shadow:0 5px 0 #1a0b3d;letter-spacing:.5px;text-transform:uppercase}
    #cap .y{color:#ffd84a} #cap .g{color:#9dff5a} #cap .r{color:#ff5a6e} #cap .s{font-size:26px} #cap .xl{font-size:54px}
    #cap div.pop{animation:pop .22s ease-out} @keyframes pop{0%{transform:scale(.6);opacity:0}70%{transform:scale(1.08)}100%{transform:scale(1);opacity:1}}
    #wm{position:fixed;right:12px;top:12px;z-index:60;width:58px;opacity:.9}
    /* dialogue subtitles: word by word */
    #sub{position:fixed;left:18px;right:18px;bottom:15%;z-index:61;text-align:center}
    #sub .who{display:inline-block;font:800 13px Rubik,sans-serif;letter-spacing:2px;color:#cfd3ff;background:rgba(10,6,30,.65);padding:3px 9px;border-radius:6px;margin-bottom:6px}
    #sub .line{font-family:"Lilita One";font-size:33px;line-height:1.12;color:#fff;-webkit-text-stroke:6px #120828;paint-order:stroke fill;text-shadow:0 4px 0 #120828}
    #sub.q .line{color:#d9dcff;font-size:28px;font-style:italic}
    #sub .w{opacity:.0} #sub .w.on{opacity:1} #sub .w.hot{color:#9dff5a}
    /* documentary lower third */
    #lt{position:fixed;left:22px;bottom:31%;z-index:59;opacity:0;transform:translateX(-30px)}
    #lt .n{display:inline-block;background:#9dff5a;color:#0d1a05;font:900 30px "Lilita One";padding:4px 14px 2px;letter-spacing:1px}
    #lt .d{display:block;margin-top:4px;background:rgba(12,8,30,.85);color:#fff;font:700 15px Rubik,sans-serif;padding:6px 12px;letter-spacing:.3px}
    /* title card */
    #title{position:fixed;inset:0;z-index:70;display:flex;flex-direction:column;align-items:center;justify-content:center;opacity:0;
      background:radial-gradient(circle at 50% 45%,#1d3a12 0,#081205 70%)}
    #title .a{font:44px "Lilita One";color:#9dff5a;-webkit-text-stroke:7px #061003;paint-order:stroke fill;text-align:center;line-height:1;letter-spacing:1px}
    #title .a b{display:block;font-size:76px;color:#fff;font-weight:normal}
    #title .b{margin-top:14px;font:italic 700 20px Georgia,serif;color:#cfe8c0;letter-spacing:3px}
    #flash{position:fixed;inset:0;background:#fff;opacity:0;z-index:69}
    #bars{position:fixed;inset:0;z-index:58;pointer-events:none;box-shadow:inset 0 70px 0 #000,inset 0 -70px 0 #000;opacity:0}
  `});
  await p.evaluate(d => { window.__DUR = d; }, DUR_TTS);
  await p.evaluate(j => { window.__JSM = j; }, {pass: fs.readFileSync(__dirname + '/jsm/BokehPass.js', 'utf8'), shader: fs.readFileSync(__dirname + '/jsm/BokehShader.js', 'utf8')});
  await p.evaluate(async () => {
    const THREE = await import('three');
    // three's depth of field, loaded as blob modules (the page's CSP allows blob:, not the CDN); Pass from the game's own addons
    const blobURL = src => URL.createObjectURL(new Blob([src], {type: 'text/javascript'}));
    const shaderURL = blobURL(window.__JSM.shader);
    const {BokehPass} = await import(blobURL(window.__JSM.pass.replace("'./Pass.js'", "'three/addons/postprocessing/Pass.js'").replace("'../shaders/BokehShader.js'", `'${shaderURL}'`)));
    const base = document.querySelector('link[href$="data.js"]').href.replace('data.js', '');
    const {prop} = await import(base + 'render/props.js');
    const g = window.__game, m = g.match, b = m.b, {stage, units} = g, scene = stage.scene;
    m.bot = null; m.running = false;
    await units.preload(['farter', 'chillguy', 'wojak', 'giga', 'jeanphil', 'whale', 'useless']);
    const L = (id) => { const d = document.createElement('div'); d.id = id; document.body.append(d); return d; };
    const cap = L('cap'), sub = L('sub'), lt = L('lt'), title = L('title'), flash = L('flash'), bars = L('bars');
    lt.innerHTML = '<span class="n">FARTER</span><span class="d">Fartcoin holder since day 1 · Chief Gas Officer</span>';
    title.innerHTML = '<div class="a">THE<b>FARTCOIN</b>INVESTOR</div><div class="b">a documentary</div>';
    const wm = document.createElement('img'); wm.id = 'wm'; wm.src = 'assets/ui/logo.webp?v=4'; document.body.append(wm);
    // ---------------- clock (every rAF callback queued, not only the last one)
    let now = performance.now(); performance.now = () => now;
    window.__rafs = []; window.requestAnimationFrame = cb => { window.__rafs.push(cb); window.__raf = true; return window.__rafs.length; };
    // ---------------- depth of field, between the scene and the bloom
    let bokeh = null;
    if (stage.composer) { bokeh = new BokehPass(scene, stage.camera, {focus: 4, aperture: 0.004, maxblur: 0.009}); bokeh.enabled = false; stage.composer.insertPass(bokeh, 1); }
    else console.log('SKIT no composer: no depth of field');
    // ---------------- camera: my shot + handheld wobble + punch-in
    const cam = stage.camera; let shake = 0;
    const C = {pos: [9, 30, 40], look: [9, 0, 16], fov: 36, hand: 0, punch: 0, focus: 4};
    const nz = (t, s) => Math.sin(t * 1.3 + s) * 0.6 + Math.sin(t * 2.7 + s * 2) * 0.3 + Math.sin(t * 5.1 + s * 3) * 0.1;
    stage.render = function () {
      const tt = now / 1000, h = C.hand, [px, py, pz] = C.pos, [lx, ly, lz] = C.look;
      cam.fov = C.fov / (1 + C.punch);
      cam.position.set(px + nz(tt, 1) * h + Math.sin(now * 0.05) * shake, py + nz(tt, 2) * h * 0.7 + Math.cos(now * 0.071) * shake * 0.6, pz);
      cam.lookAt(lx + nz(tt, 3) * h * 0.5, ly + nz(tt, 4) * h * 0.4, lz);
      cam.updateProjectionMatrix(); cam.updateMatrixWorld(); shake = Math.max(0, shake * 0.92 - 0.003);
      if (window.__skit && this.poolLight) this.poolLight.intensity = 0;
      if (bokeh) { bokeh.enabled = !!window.__skit; bokeh.uniforms.focus.value = C.focus; bokeh.uniforms.aperture.value = window.__ap ?? 0.004; }
      if (window.__nodraw) return; this.draw(); };
    const lerp = (a, c, k) => a + (c - a) * k, L3 = (a, c, k) => a.map((v, i) => lerp(v, c[i], k));
    const ease = t => t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t), out3 = t => t < 0 ? 0 : t > 1 ? 1 : 1 - Math.pow(1 - t, 3);
    // ---------------- the arena's world, and my sets
    const arenaKids = scene.children.filter(o => o !== units.root && !o.isLight);
    const lights = []; scene.traverse(o => { if (o.isLight) lights.push([o, o.intensity]); });
    const sky = {bg: scene.background?.clone?.(), fog: {near: scene.fog.near, far: scene.fog.far}};
    const std = (c, o = {}) => new THREE.MeshStandardMaterial({color: c, roughness: 0.75, ...o});
    const box = (w, h, d, mat, x, y, z, par) => { const me = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); me.position.set(x, y, z); me.castShadow = me.receiveShadow = true; par.add(me); return me; };
    const canvasTex = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; };
    const plane = (w, h, tex, x, y, z, par, ry = 0, basic = true) => { const me = new THREE.Mesh(new THREE.PlaneGeometry(w, h), basic ? new THREE.MeshBasicMaterial({map: tex, toneMapped: false}) : std('#fff', {map: tex})); me.position.set(x, y, z); me.rotation.y = ry; par.add(me); return me; };
    // ELEVATOR: brushed steel box, open toward the camera; a floor display
    const elev = new THREE.Group(); elev.visible = false; scene.add(elev);
    const steel = std('#5d646d', {metalness: 0.7, roughness: 0.45});
    box(3.4, 0.08, 2.6, std('#3b3f46', {roughness: 0.6}), 9, -0.04, 15.0, elev);          // floor
    box(3.4, 3.2, 0.08, steel, 9, 1.6, 13.7, elev);                                          // back
    box(0.08, 3.2, 2.6, steel, 7.3, 1.6, 15.0, elev); box(0.08, 3.2, 2.6, steel, 10.7, 1.6, 15.0, elev);
    box(3.4, 0.08, 2.6, std('#8d939c', {emissive: '#fff4dc', emissiveIntensity: 0.05}), 9, 3.2, 15.0, elev);   // lit ceiling
    box(3.3, 0.06, 0.08, std('#c9a24a', {metalness: 0.9, roughness: 0.3}), 9, 1.0, 13.75, elev);               // brass handrail
    const floorT = canvasTex(256, 128, (c, w, h) => { c.fillStyle = '#100'; c.fillRect(0, 0, w, h); c.font = 'bold 90px monospace'; c.fillStyle = '#ff3a2a'; c.fillText('▲ 7', 30, 100); });
    plane(0.62, 0.31, floorT, 9, 2.75, 13.75, elev);
    const elLight = new THREE.PointLight('#fff1d6', 3.2, 7, 1.4); elLight.position.set(9, 2.9, 15.2); elev.add(elLight);
    // OFFICE (interview): night window with a skyline, a framed $FART chart, shelf of green candles, lamp
    const off = new THREE.Group(); off.visible = false; scene.add(off);
    box(8, 0.08, 6, std('#3a2a22', {roughness: 0.8}), 9, -0.04, 15.5, off);
    box(8, 4.5, 0.1, std('#2b2440'), 9, 2.25, 12.4, off);
    const sky2 = canvasTex(512, 384, (c, w, h) => { const gr = c.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#0b1030'); gr.addColorStop(1, '#3a1d55'); c.fillStyle = gr; c.fillRect(0, 0, w, h);
      for (let i = 0; i < 26; i++) { const bw = 14 + Math.random() * 30, bh = 60 + Math.random() * 220, x = i * 20 - 10; c.fillStyle = '#120c26'; c.fillRect(x, h - bh, bw, bh);
        for (let y = h - bh + 8; y < h - 6; y += 12) for (let xx = x + 3; xx < x + bw - 4; xx += 7) if (Math.random() < 0.35) { c.fillStyle = Math.random() < 0.5 ? '#ffd27a' : '#9dff5a'; c.fillRect(xx, y, 3, 5); } } });
    plane(3.0, 2.2, sky2, 7.3, 2.1, 12.47, off);
    box(3.1, 0.08, 0.1, std('#151020'), 7.3, 1.0, 12.5, off); box(0.08, 2.3, 0.1, std('#151020'), 7.3, 2.1, 12.52, off);
    const chart2 = canvasTex(512, 340, (c, w, h) => { c.fillStyle = '#081005'; c.fillRect(0, 0, w, h); let y = 290; for (let i = 0; i < 22; i++) { const up = i % 4 !== 2, d = up ? -(6 + i * 0.9) : 7; c.fillStyle = up ? '#2bff6a' : '#ff3b5c'; c.fillRect(20 + i * 21, Math.min(y, y + d), 14, Math.abs(d) + 3); y += d; }
      c.font = 'bold 44px Lilita One, sans-serif'; c.fillStyle = '#2bff6a'; c.fillText('$FART  +4,200%', 20, 52); });
    box(1.75, 1.25, 0.06, std('#c9a24a', {metalness: 0.8, roughness: 0.35}), 10.9, 2.35, 12.48, off);
    plane(1.6, 1.08, chart2, 10.9, 2.35, 12.52, off);
    box(1.8, 0.06, 0.4, std('#5b3b2a'), 10.9, 1.25, 12.65, off);
    for (let i = 0; i < 4; i++) { const cnd = prop(i % 2 ? 'candleG' : 'rocket'); cnd.scale.setScalar(0.32 + (i % 3) * 0.06); cnd.position.set(10.2 + i * 0.45, 1.29, 12.65); off.add(cnd); }
    const plant = new THREE.Group(); off.add(plant); plant.position.set(6.2, 0, 13.4);
    box(0.4, 0.5, 0.4, std('#c56b3a'), 0, 0.25, 0, plant); for (let i = 0; i < 6; i++) { const lf = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.9, 6), std('#2f8f3a')); lf.position.set(Math.cos(i) * 0.12, 0.85, Math.sin(i) * 0.12); lf.rotation.z = Math.cos(i * 2) * 0.4; lf.rotation.x = Math.sin(i * 2) * 0.4; plant.add(lf); }
    const key = new THREE.PointLight('#ffe0b8', 7, 8, 1.3); key.position.set(10.8, 2.6, 17.2); off.add(key);
    const rimL = new THREE.PointLight('#8a6cff', 6, 6, 1.4); rimL.position.set(7.2, 2.2, 13.3); off.add(rimL);
    const winL = new THREE.PointLight('#9dff5a', 2.5, 5, 1.5); winL.position.set(10.9, 2.3, 13.0); off.add(winL);
    // GAS: soft green puffs (sprites), each with its own birth, drift and growth
    const gasTex = canvasTex(128, 128, (c, w) => { const gr = c.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, 'rgba(170,255,90,.95)'); gr.addColorStop(0.45, 'rgba(120,220,60,.45)'); gr.addColorStop(1, 'rgba(90,180,40,0)'); c.fillStyle = gr; c.fillRect(0, 0, w, w); });
    const puffs = [];
    const gas = (x, y, z, n, spread, life, parent, size = 0.9) => { for (let i = 0; i < n; i++) { const s = new THREE.Sprite(new THREE.SpriteMaterial({map: gasTex, transparent: true, depthWrite: false, opacity: 0}));
      s.renderOrder = 8; parent.add(s); puffs.push({s, x: x + (Math.random() - 0.5) * spread, y: y + Math.random() * 0.3, z: z + (Math.random() - 0.5) * spread * 0.6, vx: (Math.random() - 0.5) * 0.35, vy: 0.12 + Math.random() * 0.2, vz: (Math.random() - 0.3) * 0.2, born: S.t + i * 0.03, life, size: size * (0.6 + Math.random() * 0.8), rot: Math.random() * 6}); } };
    const tickGas = (t) => { for (const q of puffs) { const a = t - q.born; if (a < 0) { q.s.visible = false; continue; } q.s.visible = true; const k = a / q.life;
      q.s.position.set(q.x + q.vx * a, q.y + q.vy * a, q.z + q.vz * a); q.s.scale.setScalar(q.size * (0.4 + out3(Math.min(1, a / 0.8)) * 1.3 + a * 0.12));
      const dc = q.s.position.distanceTo(cam.position); q.s.material.opacity = k > 1 ? 0 : Math.min(1, a / 0.25) * (1 - k) * 0.5 * Math.min(1, Math.max(0, (dc - 1.4) / 1.6)); q.s.material.rotation = q.rot + a * 0.3; } };
    // ---------------- actors (display copies of the game's characters, puppeted, half size)
    const A = {};
    const actor = (key, card, mode, x, z, face) => { const e = units.showcase(card, x, z, face); const a = A[key] = {e, card, mode, want: 'idle', v: null, once: null}; const grab = () => { a.v = units.views.get(e.id); if (!a.v) setTimeout(grab, 30); }; grab(); return a; };
    const anim = (a, name, loop = true) => { if (!a.v) return; if (loop) { a.want = name; a.once = null; units.play(a.v, name, 0.2); } else { a.once = name; units.play(a.v, name, 0.15); } };
    // elevator: back row giga, wojak; front row jean phil, chill guy, farter (he's at the front, of course)
    actor('giga', 'giga', 'elev', 8.55, 14.35, 0); actor('woj', 'wojak', 'elev', 9.45, 14.4, 0);
    actor('jp', 'jeanphil', 'elev', 8.25, 15.2, 0.1); actor('cg', 'chillguy', 'elev', 8.95, 15.3, 0); actor('fE', 'farter', 'elev', 9.65, 15.35, -0.1);
    actor('fI', 'farter', 'off', 9.35, 14.9, -0.38);
    const setMode = (mode) => {
      const inArena = mode === 'arena'; window.__skit = !inArena;
      for (const o of arenaKids) o.visible = inArena;
      elev.visible = mode === 'elev'; off.visible = mode === 'off';
      for (const [o, i] of lights) o.intensity = inArena ? i : o.isHemisphereLight ? 0.55 : (o.isDirectionalLight && i > 1.5) ? i * 0.35 : 0;
      if (!H0) H0 = [stage.hemi.color.clone(), stage.hemi.groundColor.clone()];
      if (inArena) { stage.hemi.color.copy(H0[0]); stage.hemi.groundColor.copy(H0[1]); } else { stage.hemi.color.set('#d8dcff'); stage.hemi.groundColor.set('#3a2a55'); }
      document.getElementById('ov').style.visibility = inArena ? 'visible' : 'hidden';
      if (inArena) { if (sky.bg) scene.background = sky.bg; scene.fog.near = sky.fog.near; scene.fog.far = sky.fog.far; }
      else { scene.background = new THREE.Color(mode === 'elev' ? '#121318' : '#0c0a1c'); scene.fog.near = 40; scene.fog.far = 90; }
      for (const a of Object.values(A)) if (a.v) a.v.root.visible = a.mode === mode;
      S.mode = mode;
    };
    let H0 = null;
    const puppets = () => { for (const a of Object.values(A)) { const v = a.v; if (!v) continue; if (v.ring) v.ring.visible = false; v.root.scale.setScalar(0.5); v.root.visible = a.mode === S.mode;
      if (!v.dark && v.mats) { v.dark = true; for (const mt of v.mats) if (mt.emissive) { mt.emissive.setRGB(0, 0, 0); mt.emissiveIntensity = 0; } }
      if (a.once) { if (v.cur && !v.cur.isRunning()) { a.once = null; units.play(v, a.want, 0.25); } } else if (v.curName !== a.want) units.play(v, a.want, 0.25); } };
    // ---------------- text
    const say = (html) => { if (cap.dataset.h === html) return; cap.dataset.h = html; cap.innerHTML = html; cap.querySelectorAll('div').forEach(d => d.classList.add('pop')); };
    const SUBS = [];   // {t0, dur, who, text, q, hot}
    const line = (id, t0, who, text, q = false, hot = []) => { SUBS.push({t0, dur: window.__DUR[id], who, text, q, hot}); S.ev.push({t: t0, k: 'tts', id}); };
    const drawSub = (t) => { const s = SUBS.find(s => t >= s.t0 - 0.05 && t <= s.t0 + s.dur + 0.55);
      if (!s) { if (sub.dataset.k) { sub.innerHTML = ''; sub.dataset.k = ''; } return; }
      const words = s.text.split(' '), k = Math.max(1, Math.ceil(((t - s.t0) / Math.max(0.3, s.dur * 0.92)) * words.length));
      const key2 = s.t0 + ':' + k; if (sub.dataset.k === key2) return; sub.dataset.k = key2; sub.className = s.q ? 'q' : '';
      sub.innerHTML = `<div class="who">${s.who}</div><div class="line">${words.map((w, i) => `<span class="w${i < k ? ' on' : ''}${s.hot.includes(i) ? ' hot' : ''}">${w}</span>`).join(' ')}</div>`; };
    // ---------------- events for the sound mix
    const S = {ev: [], t: 0, mode: ''}; const sfx = (s, vol) => S.ev.push({t: +S.t.toFixed(3), k: 'sfx', s, vol});
    const step0 = b.step.bind(b);
    b.step = function () { step0(); for (const e of b.events) if (['spell', 'tower_down', 'die', 'end'].includes(e.type)) S.ev.push({t: +S.t.toFixed(3), k: e.type, card: e.card, team: e.team}); };
    const done = {}; const once = (k, t, at, f) => { if (!done[k] && t >= at) { done[k] = true; f(); } };
    const towers = b.towers; let fA = null, whale = null;
    // ================= THE SCRIPT =================
    const T = {title: 4.4, int1: 5.9, elev2: 18.8, arena: 26.4, int2: 36.5, end: 41.3};
    window.__T = T;
    // dialogue (timed from the clips)
    line('f_deceive', 2.35, 'FARTER', 'Why would I deceive you?', false, [4]);
    line('i_what', 6.25, 'INTERVIEWER', 'So... what does Fartcoin actually do?', true);
    line('f_utility', 8.55, 'FARTER', "It's a utility token.");
    line('i_whatutil', 10.6, 'INTERVIEWER', "What's the utility?", true);
    line('f_gas', 12.35, 'FARTER', 'Gas fees.', false, [0, 1]);
    line('i_stinks', 14.45, 'INTERVIEWER', 'Some people say it stinks.', true);
    line('f_working', 16.15, 'FARTER', "That's how you know it's working.", false, [5]);
    line('f_proof', 24.1, 'FARTER', 'That is called, proof of stink.', false, [3, 4, 5]);
    line('i_win', 32.7, 'INTERVIEWER', 'Did you just win... by farting?', true);
    line('f_strategy', 34.35, 'FARTER', "It's called a strategy.", false, [3]);
    line('i_advice', 36.75, 'INTERVIEWER', 'Any advice for new investors?', true);
    line('f_hold', 39.0, 'FARTER', 'Hold your breath.', false, [1, 2]);
    window.SCRIPT = (t) => {
      S.t = t;
      // ---------- COLD OPEN: the elevator
      once('e0', t, 0, () => { setMode('elev'); window.__ap = 0.0025; });
      if (t < T.title) {
        if (t < 2.2) { const e = ease(t / 2.2); C.fov = 34; C.hand = 0.025; C.pos = L3([9.1, 1.3, 20.9], [9.15, 1.25, 20.2], e); C.look = [9.05, 0.9, 14.9]; C.focus = 5.2; C.punch = 0;
          say('<div class="s">someone in this elevator</div><div>holds <span class="g">$fartcoin</span></div>'); }
        once('f1', t, 0.9, () => { sfx('fart_cast', 1.0); gas(9.65, 0.3, 15.2, 14, 0.6, 3.4, elev, 0.6); });
        once('turn', t, 1.4, () => { A.giga.e.face = 0.95; A.woj.e.face = 0.25; A.jp.e.face = 1.35; A.cg.e.face = 1.25; sfx('crowd_ooh', 0.5); });
        if (t >= 2.2) { const k = t - 2.2; C.fov = 26; C.hand = 0.012; C.pos = [9.7, 1.27, 17.6]; C.look = [9.65, 1.18, 15.35]; C.focus = 2.25; window.__ap = 0.006;
          A.fE.e.face = 0; say(''); C.punch = t > 3.75 ? 0.55 * out3((t - 3.75) / 0.12) : 0; }
        once('boom1', t, 3.75, () => { sfx('whale_slam', 1.0); shake = 0.25; });
      }
      // ---------- TITLE CARD
      if (t >= T.title && t < T.int1) { const k = t - T.title; title.style.opacity = k < 0.15 ? k / 0.15 : k > 1.25 ? Math.max(0, 1 - (k - 1.25) / 0.25) : 1;
        title.firstChild.style.transform = `scale(${1.25 - 0.25 * out3(k / 0.25)})`; } else title.style.opacity = 0;
      once('tit', t, T.title, () => { sfx('whale_slam', 0.8); sfx('ui_swoosh', 0.8); say(''); });
      // ---------- INTERVIEW 1
      once('i1', t, T.int1 - 0.2, () => { setMode('off'); });
      if (t >= T.int1 && t < T.elev2) { const k = t - T.int1;
        // a slow push in; a snap closer for "Gas."
        C.fov = 28; C.hand = 0.02; C.pos = L3([10.55, 1.42, 18.6], [10.3, 1.36, 17.7], ease(k / 12)); C.look = [9.32, 1.2, 14.9]; C.focus = Math.hypot(C.pos[0] - 9.35, C.pos[2] - 14.9); window.__ap = 0.005;
        C.punch = (t > 12.3 && t < 14.45) ? 0.45 * out3((t - 12.3) / 0.1) : 0;
        const lk = k - 0.2; lt.style.opacity = lk < 0 ? 0 : lk < 0.3 ? lk / 0.3 : lk > 3.6 ? Math.max(0, 1 - (lk - 3.6) / 0.3) : 1; lt.style.transform = `translateX(${(1 - out3(lk / 0.35)) * -30}px)`;
        say(''); }
      else lt.style.opacity = 0;
      once('gaspuff', t, 13.72, () => { sfx('fart_cloud', 1.0); gas(9.2, 0.3, 14.6, 10, 0.5, 3.0, off, 0.7); A.fI.e.face = -0.38; });
      once('lol1', t, 13.95, () => sfx('crowd_laugh', 0.7));
      once('lol2', t, 18.2, () => sfx('crowd_laugh', 0.6));
      once('nod', t, 8.6, () => anim(A.fI, 'emote', false));
      // ---------- THE ELEVATOR, the whole story
      once('e2', t, T.elev2, () => { setMode('elev'); sfx('ui_swoosh', 0.8); for (const k2 of ['giga', 'woj', 'jp', 'cg']) A[k2].e.face = 0; A.fE.e.face = -0.1; puffs.length = 0; });
      if (t >= T.elev2 && t < T.arena) { const k = t - T.elev2; window.__ap = 0.0022; C.punch = 0;
        C.fov = 34; C.hand = 0.02; C.pos = L3([9.1, 1.3, 21.0], [9.1, 1.25, 20.1], ease(k / 5)); C.look = [9.05, 0.9, 14.9]; C.focus = C.pos[2] - 15.0;
        say(k < 2.2 ? '<div class="s">9:01 AM</div><div>the elevator</div>' : '');
        if (t > T.elev2 + 4.9) { C.fov = 30; C.pos = [9.75, 1.3, 18.2]; C.look = [9.65, 1.15, 15.35]; C.focus = 2.85; window.__ap = 0.006; A.fE.e.face = 0; }   // on him for the line
      }
      once('e2gas', t, T.elev2 + 0.4, () => { sfx('fart_cast', 1.0); gas(9.3, 0.3, 15.0, 22, 1.6, 6.5, elev, 0.75); });
      once('e2jp', t, T.elev2 + 1.1, () => { A.jp.e.face = 1.3; anim(A.jp, 'die', false); A.jp.want = 'die'; sfx('die_jeanphil', 1.0); });
      once('e2woj', t, T.elev2 + 2.1, () => { A.woj.e.face = 0.5; anim(A.woj, 'lose'); sfx('bark_wojak', 1.0); });
      once('e2giga', t, T.elev2 + 2.9, () => { A.giga.e.face = 0.9; sfx('bark_giga', 1.0); });
      once('e2cg', t, T.elev2 + 3.6, () => { anim(A.cg, 'emote', false); sfx('bark_chillguy', 0.9); });
      // ---------- ARENA
      once('ar', t, T.arena, () => { setMode('arena'); m.running = true; puffs.length = 0; sfx('ui_swoosh', 0.9); flash.style.opacity = 0.9;
        fA = b.deploy(0, 'farter', 3.5, 21.5)[0]; whale = b.deploy(1, 'whale', 3.6, 14.2)[0]; whale.hp = 900; sfx('bark_whale', 0.9); });
      if (t >= T.arena && t < T.int2 && fA) { const u = t - T.arena; flash.style.opacity = Math.max(0, 0.9 - u * 3); fA.hp = fA.max; C.hand = 0.03; C.punch = 0;
        if (u < 3.6) { const e = ease(u / 3.6); C.fov = 36; C.pos = L3([9, 24, 40], [fA.x + 5.5, 8.5, fA.z + 9.5], e); C.look = L3([7, 0, 18], [fA.x, 1.2, fA.z - 3], e);
          say(u < 1.2 ? '<div class="s">his meme royale strategy:</div>' : '<div class="s">his meme royale strategy:</div><div>step 1: <span class="g">gas the whale</span></div>'); }
        once('rig', t, T.arena + 3.4, () => { const R = towers[1][0]; R.hp = Math.min(R.hp, 70); b.castSpell(0, 'fart', 3.6, 8.2); });
        if (u >= 3.6 && u < 6.3) { const R = towers[1][0], e = ease((u - 3.6) / 2.7); C.fov = 36; C.pos = L3([R.x + 8.5, 9.5, R.z + 12.5], [R.x + 7, 8, R.z + 11], e); C.look = [R.x + 0.4, 1.3, R.z + 1.3];
          say(R.dead ? '<div>step 3: <span class="r">deny everything</span></div>' : '<div>step 2: <span class="g">let it drift</span></div>'); }
        once('fmove', t, T.arena + 6.2, () => { fA.x = 4.6; fA.z = 12.2; fA.px = fA.x; fA.pz = fA.z; fA.target = null; });
        if (u >= 6.3) { fA.x = 4.6; fA.z = 12.2; fA.px = fA.x; fA.pz = fA.z; fA.face = Math.PI; C.fov = 32; C.pos = [fA.x + 1.9, 3.1, fA.z - 6.4]; C.look = [fA.x, 1.45, fA.z]; say('<div>step 3: <span class="r">deny everything</span></div>');
          const v = units.views.get(fA.id); once('femote', t, T.arena + 8.1, () => { if (v) { units.play(v, 'emote', 0.2); v.attackUntil = now + 99999; } }); }
      }
      // ---------- INTERVIEW 2
      once('i2', t, T.int2, () => { setMode('off'); m.running = false; flash.style.opacity = 0; say(''); sfx('ui_swoosh', 0.7); puffs.length = 0; });
      if (t >= T.int2) { const k = t - T.int2; C.fov = 28; C.hand = 0.02; C.pos = L3([10.3, 1.38, 17.6], [10.15, 1.33, 17.0], ease(k / 4.5)); C.look = [9.32, 1.2, 14.9]; C.focus = Math.hypot(C.pos[0] - 9.35, C.pos[2] - 14.9); window.__ap = 0.005;
        C.punch = t > 39.0 ? 0.35 * out3((t - 39.0) / 0.12) : 0; }
      once('end_puff', t, 40.5, () => { sfx('fart_cloud', 0.9); gas(9.2, 0.3, 14.6, 10, 0.5, 2.0, off, 0.7); });
      once('lol3', t, 40.6, () => sfx('crowd_laugh', 0.8));
      tickGas(t); drawSub(t); puppets();
    };
    window.STEP = (t, ms) => { window.__nodraw = t < (window.__SEG0 || 0) - 0.5; window.SCRIPT(t); now += ms; const q = window.__rafs; window.__rafs = []; for (const cb of q) { try { cb(now); } catch (e) { console.error('raf', e.message); } } };
    window.__S = S;
  });
  await p.evaluate(s0 => { window.__SEG0 = s0; }, SEG0);
  console.log('script installed'); await p.waitForFunction(() => !!window.__raf, null, {timeout: 15000}); console.log('clock frozen');
  await p.evaluate(() => { const m = window.__game.match; m.app = Object.create(m.app); m.app.results = () => {}; });
  await p.evaluate(() => new Promise(r => setTimeout(r, 2500)));
  const DUR = await p.evaluate(() => window.__T.end), TO = +(process.env.TO || DUR);
  let ff = null; const N = Math.round(DUR * FPS);
  if (!PREVIEW) ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', OUT]);
  else fs.mkdirSync(OUT, {recursive: true});
  const t0 = Date.now();
  for (let i = 0; i < N; i++) {
    const t = i / FPS;
    await p.evaluate(([t, ms]) => window.STEP(t, ms), [t, 1000 / FPS]);
    if (PREVIEW) { if (i % EVERY === 0 && t >= FROM && t <= TO) await p.screenshot({path: `${OUT}/f_${String(i).padStart(4, '0')}.jpg`, type: 'jpeg', quality: 75}); }
    else if (t >= SEG0 - 1e-6 && t < SEG1 - 1e-6) { const buf = await p.screenshot({type: 'jpeg', quality: 93}); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
    if (i % 90 === 0) console.log(`frame ${i}/${N} t=${t.toFixed(1)} ${((Date.now() - t0) / 1000 / (i + 1)).toFixed(2)}s/f`);
  }
  const ev = await p.evaluate(() => window.__S.ev);
  fs.writeFileSync(PREVIEW ? OUT + '/events.json' : OUT.replace(/\.mp4$/, '') + '_events.json', JSON.stringify(ev));
  if (ff) { ff.stdin.end(); await new Promise(r => ff.on('close', r)); }
  await ctx.close(); fs.rmSync(dir, {recursive: true, force: true});
  console.log('done');
})();
