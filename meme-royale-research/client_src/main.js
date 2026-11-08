// MEME ROYALE — boot, the frame loop, and the screens: hub (CR's home, src/ui/menus.js) -> matchmaking -> match -> results
// -> hub. The menus draw no 3D, so the title waits only for them: the 3D side (three.js, the arena, the towers, my deck's
// units) loads behind the menus (world, setupHub) and a battle waits for it.
import {Menus} from './ui/menus.js';
import {mountSky} from './ui/sky.js';
import {save} from './save.js';
import {audio} from './audio.js';
import {arenaOf} from './data.js';
import {Online} from './online.js';
import {h} from './ui/cards.js';

// a pause between two heavy steps of the background 3D load, so a tap on the menus gets in between
const breathe = () => new Promise(r => setTimeout(r, 0));

class App {
  constructor() {
    this.ui = document.getElementById('ui'); this.ov = document.getElementById('ov');
    mountSky();
    this.menus = new Menus(this);
    this.render3d = false; this.last = performance.now();
    this.loop = this.loop.bind(this); requestAnimationFrame(this.loop);
    addEventListener('resize', () => this.fx?.resize());
    // a wide screen (a PC, a tablet on its side) gets the desk layout: the menus fill the window, their sizes scaled (--z)
    // to a phone's proportions of the screen's height (style.css body.desk); the battle has its own wide layout
    const desk = () => {
      const on = innerWidth >= 960 && innerWidth / innerHeight >= 1.15, z = on ? (Math.min(innerWidth, innerHeight * 0.47) / 400).toFixed(3) : '1';
      if (document.body.classList.contains('desk') === on && document.body.style.getPropertyValue('--z') === z) return;
      document.body.classList.toggle('desk', on); document.body.style.setProperty('--z', z);
      if (!this.match && !this.busy && this.menus?.ui.querySelector('.screen')) this.menus.hub(this.menus.tab, true);
    };
    desk(); addEventListener('resize', desk);
    // every press answers the finger: :active works on iOS once a touch listener exists, and a button gets a little burst
    // ring where it was touched (src/ui/style.css .tapfx)
    addEventListener('touchstart', () => {}, {passive: true});
    // when the menus were last touched, scrolled or wheeled (calm)
    this.touchedAt = 0; const touched = () => { this.touchedAt = performance.now(); };
    for (const k of ['pointerdown', 'wheel', 'scroll']) addEventListener(k, touched, {capture: true, passive: true});
    // no zoom (the CSS refuses double taps and pinches): iOS ignores user-scalable=no and touch-action's pinch rule, so its
    // pinch (gesture* events) is refused here, and a zoom that gets through anyway (an accessibility zoom) is put back to 1
    // once the fingers are up, by re-applying the viewport tag, since a zoomed game has no way to pinch back out. (No
    // non-passive touchmove listener: it would make every scroll wait for the main thread.)
    for (const k of ['gesturestart', 'gesturechange']) document.addEventListener(k, e => e.preventDefault(), {passive: false});
    const vv = window.visualViewport, vp = document.querySelector('meta[name=viewport]');
    if (vv && vp) {
      // (the tag is held without its maximum-scale for a moment, long enough for the browser to see a change: put back in
      // the same frame, it was sometimes missed and the game stayed zoomed; still zoomed, it tries again)
      let fingers = 0, t = 0, tries = 0;
      const unzoom = () => { clearTimeout(t); if (vv.scale <= 1.01) { tries = 0; return; } if (fingers || tries > 4) return;
        t = setTimeout(() => { tries++; const c = vp.content; vp.content = c.replace(/,?\s*maximum-scale=[\d.]+/, '');
          setTimeout(() => { vp.content = c; t = setTimeout(unzoom, 400); }, 120); }, 300); };
      addEventListener('touchstart', e => { fingers = e.touches.length; tries = 0; }, {passive: true});
      addEventListener('touchend', e => { fingers = e.touches.length; unzoom(); }, {passive: true});
      addEventListener('touchcancel', e => { fingers = e.touches.length; unzoom(); }, {passive: true});
      vv.addEventListener('resize', unzoom);
    }
    // in a battle, a quick second tap where the first one landed is what zooms (iOS still answers a double tap on parts of
    // the page the CSS can't reach): that touch's default is refused, and whatever it was meant for gets its click all the
    // same (the battle itself goes by pointer events, which come before). A non-passive touchend holds up no scrolling.
    let tapEnd = -1e9, tapX = 0, tapY = 0;
    addEventListener('touchend', e => {
      const f = e.changedTouches[0]; if (!f) return;
      const quick = e.timeStamp - tapEnd < 350 && Math.hypot(f.clientX - tapX, f.clientY - tapY) < 40;
      tapEnd = e.timeStamp; tapX = f.clientX; tapY = f.clientY;
      if (!quick || !this.match || e.touches.length || !e.cancelable || e.target.closest?.('input, textarea, select, [contenteditable]')) return;
      e.preventDefault(); e.target.click?.();
    }, {passive: false});
    addEventListener('pointerdown', e => {
      const b = e.target.closest?.('button, .deckcard, .bag'); if (!b || b.disabled) return;
      const f = document.createElement('i'); f.className = 'tapfx'; f.style.left = e.clientX + 'px'; f.style.top = e.clientY + 'px';
      document.body.append(f); setTimeout(() => f.remove(), 460);
    }, {passive: true});
    // a mouse swipes the swipe rows (the shop's rows, the hub's arenas) the way a finger does: dragged with snapping held
    // off, then settled on the nearest slot (the next one along when it was pulled that way), the click that ends a drag
    // swallowed; their pictures don't start a browser drag
    addEventListener('pointerdown', e => {
      const S = e.pointerType === 'mouse' && e.button === 0 && e.target.closest?.('.hrow, .acar-track'); if (!S || S.scrollWidth <= S.clientWidth + 2) return;
      const x0 = e.clientX, l0 = S.scrollLeft, k = S.offsetWidth / (S.getBoundingClientRect().width || 1); let drag = false;   // k: a zoomed PC column's px
      const move = m => {
        if (!drag && Math.abs(m.clientX - x0) < 6) return;
        if (!drag) { drag = true; S.style.scrollSnapType = 'none'; S.classList.add('dragging'); }
        S.scrollLeft = l0 - (m.clientX - x0) * k;
      };
      const up = u => {
        removeEventListener('pointermove', move); removeEventListener('pointerup', up); removeEventListener('pointercancel', up);
        if (!drag) return;
        const dx = u.clientX - x0, sl = S.scrollLeft, L = S.getBoundingClientRect().left + S.clientLeft;
        const spots = [...S.children].map(c => Math.max(0, Math.min(S.scrollWidth - S.clientWidth, sl + (c.getBoundingClientRect().left - L) * k)));
        let to = spots.reduce((a, b) => Math.abs(b - sl) < Math.abs(a - sl) ? b : a);
        if (dx < -30 && to <= l0 + 2) to = spots.find(s => s > l0 + 2) ?? to;
        if (dx > 30 && to >= l0 - 2) to = spots.filter(s => s < l0 - 2).pop() ?? to;
        // snapping comes back once the glide is there (on mid-glide it would snap back; the drag's own scrollend comes first)
        let t = 0; const snap = f => { if (f !== true && Math.abs(S.scrollLeft - to) > 2) return; clearTimeout(t); S.removeEventListener('scrollend', snap); S.style.scrollSnapType = ''; S.classList.remove('dragging'); };
        S.addEventListener('scrollend', snap); t = setTimeout(() => snap(true), 900);
        S.scrollTo({left: to, behavior: 'smooth'});
        const eat = k => { k.stopPropagation(); k.preventDefault(); };
        addEventListener('click', eat, true); setTimeout(() => removeEventListener('click', eat, true), 60);
      };
      addEventListener('pointermove', move); addEventListener('pointerup', up); addEventListener('pointercancel', up);
    });
    addEventListener('dragstart', e => { if (e.target.closest?.('.hrow, .acar-track')) e.preventDefault(); });
    window.__game = this;
  }
  async boot() {
    const bar = document.querySelector('.boot-bar i'), tip = document.querySelector('.boot-tip');
    bar.style.width = '20%';
    try { await Promise.all([document.fonts.load('40px "Lilita One"'), document.fonts.load('800 20px Rubik')]); } catch {}
    // online when the page comes from the game server (the profile, matchmaking and the shop are the server's)
    bar.style.width = '55%'; tip.textContent = 'connecting…'; this.net = await Online.connect(this);
    bar.style.width = '100%';
    this.menus.hub('battle');
    // the menus' pictures first (what a finger reaches for next), then the 3D side behind them; a battle pressed sooner
    // starts it at once (ready3d), and it never waits more than 6 s
    Promise.race([this.menus.warm(), new Promise(r => setTimeout(r, 6000))]).then(() => { if (!this.dressing) this.setupHub(); });
    // title: one tap to start (phones only allow sound after a tap). The whole tap (click), not the touch (pointerdown):
    // gone at the touch, the click a phone sends when the finger lifts lands on the hub under it (a bag slot opens its sheet)
    const boot = document.getElementById('boot'); boot.classList.add('ready');
    const play = document.createElement('div'); play.className = 'play'; play.textContent = 'TAP TO PLAY'; boot.append(play);
    await new Promise(r => boot.addEventListener('click', r, {once: true}));
    audio.init(); audio.play('vo_title'); audio.music('mus_menu');
    // some webviews never settle these promises: the title must not hang on them
    const upTo = (p, ms) => Promise.race([p, new Promise(r => setTimeout(r, ms))]);
    try { if (matchMedia('(pointer: coarse)').matches) await upTo(document.documentElement.requestFullscreen?.({navigationUI: 'hide'}), 800); } catch {}
    try { await upTo(screen.orientation?.lock?.('portrait'), 500); } catch {}
    boot.classList.add('out'); setTimeout(() => boot.remove(), 600);
    // online, a first launch: an account (a unique name and a password) before anything else, for the leaderboard
    if (this.net?.online && !save.p.account) await this.menus.account({mode: 'create', required: true});
  }
  // the 3D side, loaded once on first need (its modules too: none of them is on the menus' path)
  world() {
    return this.worldP ||= Promise.all([import('./render/stage.js'), import('./render/arena.js'), import('./render/units.js'), import('./render/fx.js'),
      import('./render/blds.js'), import('./sim.js'), import('./battle.js'), import('./render/assets.js')]).then(([{Stage}, {Arena}, {UnitViews}, {FX}, {BuildingViews}, {Battle}, {Match}, {fetchMode}]) => {
      this.Battle = Battle; this.Match = Match; this.fetchMode = fetchMode;
      this.stage = new Stage(document.getElementById('gl'));
      return breathe().then(() => {
        this.fx = new FX(this.stage); this.units = new UnitViews(this.stage, null, this.fx); this.blds = new BuildingViews(this.stage, this.fx);
        const arena = new Arena(this.stage); arena.fx = this.fx; this.stage.arena = arena; this.arena = arena;
      });
    }).catch(e => { this.worldP = null; throw e; });   // a failed load (the network) is tried again by the next battle
  }
  // the 3D scene stands ready in my arena (the one my Clout reached) with my deck's units loaded, for the next battle; one
  // dressing at a time (a login can ask for another while the first runs); a battle awaits ready3d()
  setupHub(urgent = false) {
    this.match?.destroy(); this.match = null; this.urgent = urgent;
    const breathe = () => this.calm();
    const go = async () => {
      await this.world(); await breathe(); this.fetchMode.priority = 'low';
      this.units.clear(); this.units.battle = null; this.blds.clear();
      this.arena.clearTowers(); this.arena.hideMask(); this.arena.hideGhost();
      const A = save.league; if (this.arena.themeId !== A.id) await Promise.race([this.arena.applyTheme(A.id), new Promise(r => setTimeout(r, 5000))]);
      await breathe();
      const b = new this.Battle({decks: [save.deck, save.deck]});
      await this.units.preload(save.deck); await breathe();
      await this.arena.buildTowers(b, (T, s) => this.units.commander(T, s), (T, s) => this.units.guard(T, s), true);
      this.stage.hub(); this.ov.getContext('2d').clearRect(0, 0, this.ov.width, this.ov.height);
      // its textures uploaded and its shaders compiled now, a little at a time, rather than all on the battle's first frame
      await breathe(); await this.stage.warm(breathe).catch(e => console.warn('[3d] warm', e));
    };
    return this.dressing = (this.dressing || Promise.resolve()).catch(() => {}).then(go).catch(e => console.error('[3d]', e));
  }
  ready3d() { if (!this.dressing) return this.setupHub(true); this.urgent = true; return this.dressing; }
  // the 3D side's background work gives way to the menus: while a finger, the wheel or a scroll was busy in the last 1.2 s
  // it waits between its steps, so a tab switch or the Trophy Road's scroll never sits behind a model parse or a shader
  // compile on a phone; a battle waiting for the 3D (ready3d) lifts that
  calm() { return new Promise(r => { const go = () => !this.urgent && performance.now() - this.touchedAt < 1200 ? setTimeout(go, 250) : setTimeout(r, 0); go(); }); }
  // online: queue, wait for the server's start (a bot after 12 s), or cancel
  async battle() {
    if (this.net?.online) return this.battleOnline();
    // an online profile battles online only: a page whose line is down (or that another page took over) starts no offline battle
    if (this.net) { this.menus.toast(this.net.client.closed ? 'Not connected: reload to play here.' : 'Reconnecting to the server…'); return; }
    return this.battleOffline();
  }
  async battleOnline() {
    if (this.busy) return; this.busy = true;
    // the search screen stands in for the hub (src/ui/menus.js finding); CANCEL brings the hub back
    const back = () => { this.searchEl = null; this.busy = false; this.menus.hub('battle'); };
    const M = this.searchEl = this.menus.finding(async () => { await this.net.client.cancel(); if (M.isConnected) back(); });
    this.menus.closeSheet(); this.menus.closeRoad(true); this.ui.replaceChildren(M); audio.play('ui_swoosh');
    await this.ready3d(); if (!M.isConnected) return;   // cancelled while the 3D was still loading
    const q = await this.net.client.queue();
    if (!q?.ok && M.isConnected) { back(); this.menus.toast(q?.why || 'Matchmaking is busy, try again.'); }
    // the server's 'start' calls startOnline (src/online.js)
  }
  async startOnline(start) {
    if (this.match || this.starting) return;
    this.starting = this.busy = true; this.searchEl = null; this.menus.closeSheet(); this.menus.closeRoad(true);
    const opp = {...start.opp, league: arenaOf(start.opp.clout || 0), matchArena: this.menus.localArena() || start.arena, net: true, deck: [], friendly: !!start.friendly};
    // the loading screen until the arena stands, then the arena's opening (src/ui/hud.js intro) in what is left of the
    // server's hold (it holds the battle that long)
    const hold = performance.now() + (start.intro || 0), L = this.menus.loading();
    this.ui.replaceChildren(L.el); audio.play('ui_swoosh'); L.set(15);
    await this.ready3d(); this.fetchMode.priority = 'auto'; L.set(45);
    const match = new this.Match(this, opp, start); match.hold = hold;
    await Promise.all([new Promise(r => setTimeout(r, 1000)), this.units.preload(save.deck)]); L.set(75);
    this.match = match; this.starting = false; this.render3d = true; document.body.classList.remove('menu');
    await match.start(L.set);
    this.busy = false;
  }
  netStatus(state, why) { if (state !== 'online' && !this.match) this.menus.toast(state === 'connecting' ? 'Reconnecting to the server…' : (why || 'Offline')); }
  async battleOffline() {
    if (this.busy) return; this.busy = true;
    const opp = save.opponent(); opp.league = arenaOf(opp.clout); opp.matchArena = this.menus.localArena();
    // the genre's order: a search (src/ui/menus.js finding), the loading screen (loading), then the arena's opening
    let off = false;
    const M = this.menus.finding(() => { off = true; this.busy = false; this.menus.hub('battle'); });
    this.menus.closeSheet(); this.menus.closeRoad(true); this.ui.replaceChildren(M); audio.play('ui_swoosh');
    await Promise.all([new Promise(r => setTimeout(r, 1400 + Math.random() * 900)), this.ready3d()]);
    if (off) return;
    const L = this.menus.loading(); this.ui.replaceChildren(L.el); audio.play('ui_swoosh'); L.set(30);
    this.fetchMode.priority = 'auto';
    const match = new this.Match(this, opp); L.set(50);
    await Promise.all([new Promise(r => setTimeout(r, 1100)), this.units.preload([...opp.deck, ...save.deck])]); L.set(75);
    this.match = match; this.render3d = true; document.body.classList.remove('menu');
    await match.start(L.set);
    this.busy = false;
  }
  results(match, win, res) { this.menus.results(match, win, res); }
  async toHub(res) {
    this.ui.innerHTML = '';
    this.setupHub();   // lets the match go now; the 3D is re-dressed behind the menus
    this.menus.hub('battle'); audio.music('mus_menu');
    this.menus.news(res);
  }
  loop(t) {
    const dt = Math.min(0.1, Math.max(0, (t - this.last) / 1000)); this.last = t;   // (a slow frame doesn't slow the battle)
    try {
      if (!this.arena) { /* still booting */ }
      else if (this.match) this.match.frame(dt);
      else if (this.render3d) {
        this.arena.update(dt); this.units.update(dt, 1); this.fx.update(dt); this.stage.render(dt);
      }
    } catch (err) { console.error(err); }
    requestAnimationFrame(this.loop);
  }
}

const app = new App();
app.boot().catch(e => { console.error(e); const t = document.querySelector('.boot-tip'); if (t) t.textContent = 'Something broke while loading: ' + e.message; });
