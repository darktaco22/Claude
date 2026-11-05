// args: CFG = {arena, me, opp, oppName, script}
const CFG = __CFG__;
await H.ev(() => { window.__vc.auto(); });
await H.ev(async (CFG) => {
  const V = '/v/-OSbT01_3H/src/';
  const {save} = await import(V + 'save.js'); const {arenaOf} = await import(V + 'data.js');
  const {audio} = await import(V + 'audio.js');
  const G = window.__game;
  if (!window.__sfxHooked) { window.__sfxHooked = true; window.__sfx = [];
    const op = audio.play.bind(audio), om = audio.music.bind(audio), oa = audio.ambience?.bind(audio);
    audio.play = (id, o = {}) => { window.__sfx.push({t: performance.now(), id, o, file: (() => { const m = audio.man[id]; if (!m) return null; const f = m.variants?.length ? m.variants : [m.file]; return f[Math.floor(Math.random() * f.length)]; })(), vol: audio.man[id]?.vol}); return op(id, o); };
    audio.music = (id, f) => { window.__sfx.push({t: performance.now(), id, music: true, file: audio.man[id]?.file, vol: audio.man[id]?.vol, loopStart: audio.man[id]?.loopStart, loopEnd: audio.man[id]?.loopEnd}); return om(id, f); };
    if (oa) audio.ambience = (id) => { window.__sfx.push({t: performance.now(), id, amb: true, file: audio.man[id]?.file, vol: audio.man[id]?.vol}); return oa(id); };
  }
  save.p.tut = true; window.__PASS = CFG.pass;
  if (!document.getElementById('cm-css')) { const st = document.createElement('style'); st.id = 'cm-css'; st.textContent = '.keys, .tut { display: none !important; }'; document.head.append(st); }
  Object.defineProperty(save, 'deck', {get: () => CFG.me, configurable: true});
  window.__match?.destroy(); G.match = null; G.busy = false;
  await G.ready3d();
  const opp = save.opponent(); opp.deck = CFG.opp; opp.name = CFG.oppName; opp.league = arenaOf(opp.clout); opp.matchArena = CFG.arena; opp.skill = 1;
  G.ui.innerHTML = '';
  const match = new G.Match(G, opp);
  await G.units.preload([...opp.deck, ...CFG.me]);
  match.bot = null;
  G.stage.settled = true;
  window.__match = match;
  const of = match.frame.bind(match);
  match.frame = dt => { window.__dir?.tick(); return of(dt); };
  G.match = match; G.render3d = true; document.body.classList.remove('menu');
  match.start(() => {});
}, CFG);
await p.addScriptTag({path: 'director.js'});
await p.addScriptTag({path: CFG.script});
// wait for the opening to begin, then freeze time
for (let i = 0; i < 200; i++) { if (await H.ev(() => !!window.__match?.hud)) break; await H.sleep(500); }
return await H.ev(() => { window.__vc.manual(); window.__dir.preStart = performance.now(); window.__capStart = performance.now(); return [performance.now(), window.__match.running]; });
