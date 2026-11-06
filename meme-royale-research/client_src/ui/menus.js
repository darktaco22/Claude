// The menus: the hub (profile with level, coins and gems; CR's home: my arena's diorama floating on its tiled backdrop, the
// daily W bag box, the bag tray, DECK / BATTLE / ROAD, the tab bar),
// Deck (3 deck slots), the Trophy Road (10 arenas and the rewards between them), the Shop (offers, free gift, daily deals,
// bags, gems, coins, cosmetics), Social (the leaderboard, friendly battles), Settings, the account screen; card sheets, the bag opening and the results screen. The rules are the store's
// (src/save.js -> src/shared/economy.js); real-money items go through the online game's wallet (app.net).
import {CARDS, CARD_IDS, ARENAS, RARITY, MAX_LVL, arenaOf, arenaById, SHOP, GEM_PACKS, OFFERS, ROAD, W_BAG, AVATARS} from '../data.js';
import {save, BAG} from '../save.js';
import {cardEl, cardArt, avatarArt, h, titleBadge, arenaBadge, dioramaOf, keepIn, warm, whenKept} from './cards.js';
import {audio, buzz} from '../audio.js';
import {statsFor} from '../sim.js';
import {findable} from '../shared/economy.js';

const fmt = n => Math.round(n).toLocaleString('en-US');
const dur = s => { s = Math.ceil(s); const hh = Math.floor(s / 3600), mm = Math.floor(s % 3600 / 60); return hh ? `${hh}h ${mm}m` : mm ? `${mm}m ${s % 60}s` : `${s}s`; };
// a test on this computer (localhost, never the live game): every arena is open, and BATTLE plays in the one the hub shows
const LOCAL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
const TAB_ORDER = ['shop', 'deck', 'battle', 'road', 'social', 'settings'];
const tap = () => audio.play(audio.has('ui_pop') ? 'ui_pop' : 'ui_tap', {spread: 0.12});
const COIN = '<img class="ico" src="assets/ui/sm/icon_cash.webp" alt="">', GEM = '<img class="ico" src="assets/ui/sm/icon_gem.webp" alt="" onerror="this.replaceWith(Object.assign(document.createElement(\'i\'),{className:\'gemi\'}))">';
// ★ and ▲ in the bag opening's lines, drawn: no game font has them, and the hunt for a font that does, the first time one
// shows, held up the first frame of a card's flight (an ink copy a little lower is the text's own shadow)
const glyph = d => `<svg class="gl" viewBox="0 0 24 24" aria-hidden="true"><path class="sh" d="${d}" transform="translate(0 2)"/><path d="${d}"/></svg>`;
const STAR = glyph('M12 2.3L14.6 9.2L22 9.6L16.2 14.2L18.2 21.3L12 17.2L5.8 21.3L7.8 14.2L2 9.6L9.4 9.2Z'), UP = glyph('M12 4L21 19H3Z');
const usd = v => '$' + v.toFixed(2);
// a number that rolls up to its value (signed: a + in front of a gain)
function countUp(e, to, signed, ms = 700) {
  const t0 = performance.now(), go = t => { const q = Math.min(1, (t - t0) / ms), v = Math.round(to * (1 - Math.pow(1 - q, 3))); e.textContent = (signed && v >= 0 ? '+' : '') + fmt(v); if (q < 1 && e.isConnected) requestAnimationFrame(go); };
  requestAnimationFrame(go);
}
// a burst of confetti in the team colours (transforms only, gone after 4 s)
function confetti(n = 36) {
  const C = h('div', 'confetti'), cols = ['#FFD23F', '#FFC84A', '#4CC9F0', '#C77DFF', '#F4EFFF', '#FF4D6D'];
  for (let i = 0; i < n; i++) { const b = h('i'); b.style.cssText = `left:${(Math.random() * 100).toFixed(1)}%;background:${cols[i % cols.length]};animation-delay:${(0.3 + Math.random() * 0.9).toFixed(2)}s;animation-duration:${(2.2 + Math.random() * 1.6).toFixed(2)}s;--dx:${((Math.random() - 0.5) * 120).toFixed(0)}px;--r:${(Math.random() * 720 - 360).toFixed(0)}deg`; C.append(b); }
  setTimeout(() => C.remove(), 4500); return C;
}

// the search and loading screens' tips (one per battle)
const TIPS = [
  'COPIUM fills a little faster in the first 30 seconds: open strong.',
  'The last minute is COPIUM OVERDOSE: it fills twice as fast.',
  'Still tied at 0:00? Overtime, then the TIEBREAKER, decides it.',
  'Take 10 Ws in a day to open the DAILY W BAG.',
  'Upgrade your cards in DECK: coins and copies make them stronger.',
  'Reach a new arena on the Trophy Road and its cards start dropping from bags.',
  'Drag a card onto your side of the arena to play it.',
  'Hold a card in DECK and drop it on another to swap them.',
];

export class Menus {
  constructor(app) { this.app = app; this.tab = 'battle'; save.listeners.add(() => this.onProfile()); }
  get ui() { return this.app.ui; }
  // a profile change (an action, or the server's push): redraw the open page, unless a sheet, the bag opening or the
  // results are up; checked again when the redraw runs, since an action's own change lands just before its overlay opens
  // (a redraw waits for the deck's cards to land: the server's echo of a swap redrawn mid-flight restarted their flight)
  onProfile() { if (this.overlaid()) { this.stale = true; return; } clearTimeout(this.redraw); this.redraw = setTimeout(() => { if (!this.overlaid()) this.hub(this.tab, true); }, Math.max(30, (this.glideUntil || 0) - performance.now() + 30)); }
  overlaid() { return !!(this.sheetEl || this.bagEl || this.ui.querySelector('.bagopen, .results, .prebattle') || this.app.match); }
  // a failed action says why
  async run(a, ok) { const r = await save.act(a); if (!r?.ok) { this.toast(r?.why || 'Not now.'); audio.play('card_deny'); return null; } ok?.(r); return r; }
  toast(msg) { this.ui.querySelector('.toast')?.remove(); const e = h('div', 'toast panel plain', msg); this.ui.append(e); setTimeout(() => e.remove(), 1700); }

  // the menus' art, loaded once in the background as soon as the hub shows (src/ui/cards.js warm): the card faces, the
  // portraits, the arena emblems and badges, then the dioramas (the Trophy Road's weight). The 3D side waits for it
  // (src/main.js), so a tab opened in the first seconds isn't stuck behind the battle's models
  warm() {
    const near = ARENAS.filter(A => A.at <= save.p.best + 1500);   // the arenas in reach: the far end of the road loads when it is scrolled to
    return warm([...CARD_IDS.map(id => cardArt(id)), ...AVATARS.map(id => avatarArt(id)), ...Object.keys(BAG).map(t => `assets/ui/icon_bag_${t}.webp`), 'assets/ui/card_back.webp',
      ...near.map(A => `assets/arenas/${A.id}/badge_sm.webp`), ...near.map(A => dioramaOf(A, save.p.best < A.at))]);
  }
  // ================= HUB =================
  hub(tab = this.tab, keepScroll) {
    const prevScroll = keepScroll ? this.ui.querySelector('.page')?.scrollTop : 0;
    clearTimeout(this.redraw);   // (a profile redraw waiting to run would only redo this one)
    // the deck page redrawn in place (a swap, another deck): where each card is on screen now, for them to glide from
    const topH = keepScroll && tab === 'deck' && this.tab === 'deck' ? this.ui.querySelector('.page-deck > .deck-top')?.offsetHeight : 0;
    const was = keepScroll && tab === 'deck' && this.tab === 'deck' ? new Map([...this.ui.querySelectorAll('.page-deck .deckcard')].map(e => [e.dataset.id, {r: e.getBoundingClientRect(), deck: e.classList.contains('indeck'), i: [...e.parentNode.children].indexOf(e)}])) : null;
    this.keepArena = !!keepScroll && this.tab === 'battle' && tab === 'battle'; this.stale = false;
    // a new tab slides in from the side it sits on in the tab bar (CR's swipe between tabs)
    const from = TAB_ORDER.indexOf(this.tab), to = TAB_ORDER.indexOf(tab), slide = !keepScroll && from !== to && this.ui.querySelector('.screen') ? (to > from ? 'in-r' : 'in-l') : '';
    this.tab = tab; save.refresh(); const p = save.p, A = save.arena;
    if (tab !== 'deck') this.swap = null;   // a USE is dropped when the deck is left
    const S = h('div', 'screen' + (slide ? ' ' + slide : ''));
    const top = h('div', 'hub-top');
    const prof = h('button', 'panel prof');
    const ava = h('div', 'ava'); const ai = h('img'); ai.onerror = () => { ai.src = 'assets/ui/sm/icon_w_bull.webp'; ai.style.objectFit = 'contain'; ai.onerror = null; }; ai.src = avatarArt(save.avatar); ava.append(ai);
    const need = save.xpNeed(), lvl = h('div', 'lvl-badge', String(p.level)); ava.append(lvl);
    const info = h('div'); info.style.minWidth = '0';
    info.append(h('div', 'nm stroke-s', p.name));
    const row = h('div', 'row'); row.innerHTML = `<span class="pill"><img src="assets/ui/sm/icon_clout.webp" alt=""><span class="num">${fmt(p.clout)}</span></span>`;
    const xpb = h('div', 'xpbar'); xpb.innerHTML = `<i style="width:${need ? Math.min(100, p.xp / need * 100) : 100}%"></i><span>${need ? `${p.xp}/${need} XP` : 'MAX LEVEL'}</span>`;
    info.append(row, xpb); prof.append(ava, info);
    prof.onclick = () => { tap(); this.profile(); };
    const wallet = h('div', 'wallet');
    const coins = h('button', 'panel money'); coins.innerHTML = `${COIN}<span class="num">${fmt(p.coins)}</span><b class="plus">+</b>`;
    const gems = h('button', 'panel money gems'); gems.innerHTML = `${GEM}<span class="num">${fmt(p.gems)}</span><b class="plus">+</b>`;
    coins.onclick = gems.onclick = () => { tap(); this.hub('shop'); };
    // (on the home tab the daily W bag sits between my profile and my wallet)
    wallet.append(coins, gems); top.append(prof, ...(tab === 'battle' ? [this.wbox()] : []), wallet);
    S.append(top);
    document.body.classList.add('menu');   // the menus cover the 3D view
    if (tab === 'battle') {
      S.classList.add('home');
      const mid = h('div', 'hub-mid'); this.arenaStage(mid);
      const tray = h('div', 'bag-tray'); tray.append(this.bags());
      S.append(mid, tray, this.battleRow());
      this.app.render3d = false;
    } else {
      const page = h('div', 'page page-' + tab); S.append(page); S.classList.add('tiled');
      this.keepScroll = !!prevScroll; this[tab](page);
      this.app.render3d = false;
      if (prevScroll) requestAnimationFrame(() => { page.scrollTop = prevScroll; });
    }
    S.append(this.tabs());
    // (taken off the page, a scroller forgets it; under a bag opening the road is out of the layout: openRoll kept it)
    const roadTop = this.roadTop ?? this.roadEl?.querySelector('.rv-scroll')?.scrollTop; if (!this.bagEl) this.roadTop = null;
    this.ui.replaceChildren(S); keepIn(S);
    if (was) { const pg = S.querySelector('.page-deck'); if (pg) { pg.scrollTop = prevScroll || 0; this.resizeTop(pg, topH); this.glideCards(pg, was); } }
    const held = this.useFrom && S.querySelector('.use-held .card'); if (held) this.flyCard(held, this.useFrom, {ms: 460, scale: true}); this.useFrom = null;
    if (this.roadEl) { this.ui.append(this.roadEl); this.fillRoad(true, null, roadTop); }   // so does the Trophy Road
    if (this.bagEl) this.ui.append(this.bagEl);   // and a bag being opened
    if (this.accountEl) this.ui.append(this.accountEl);   // the account screen stays on top of a redraw
    // one theme across the tabs (the road's own loop, swapped in and out with each visit, was a distraction)
    if (!this.app.match) audio.music('mus_menu');
    clearInterval(this.timer); this.timer = setInterval(() => this.refreshBags(), 1000);
  }
  // CR's home: the arenas side by side, swiped like CR's arena viewer and opening on mine. Each one is a card of its own:
  // its diorama (assets/arenas/<id>/diorama.webp: a stylised miniature of the place, no name plate, so it can be big)
  // floating over the sky, as big as the space allows (no line under it: the climb lives on the Trophy Road; ahead, greyed out with a lock). Arrows and dots
  // jump between them; a tap on one switches to the ROAD tab. Over them, on the right, the settings button.
  arenaStage(mid) {
    const p = save.p, A = save.arena, cur = A.n - 1;
    const strip = h('div', 'hub-strip'), gear = h('button', 'sq-btn');
    gear.innerHTML = '<img src="assets/ui/sm/icon_settings.webp" alt="settings">'; gear.onclick = () => { tap(); this.hub('settings'); };
    strip.append(gear);
    const car = h('div', 'acar'), track = h('div', 'acar-track'), dots = h('div', 'acar-dots');
    // open on the arena I was looking at (a redraw), else on mine; only it and its neighbours load their diorama now, the
    // others when a swipe comes near them (sync)
    if (LOCAL) this.arenaAt ??= Number(localStorage.getItem('memeroyale.localArena') ?? cur);
    const start = (LOCAL || this.keepArena) && this.arenaAt != null ? this.arenaAt : cur;
    ARENAS.forEach((X, i) => {
      const reached = LOCAL || p.best >= X.at, mine = i === cur, sl = h('button', 'aslide' + (reached ? '' : ' locked') + (mine ? ' mine' : ''));
      sl.innerHTML = `<div class="isle"><i class="isle-glow"></i><img class="isle-img" ${Math.abs(i - start) > 1 ? 'data-' : ''}src="${dioramaOf(X, !reached)}" alt="${X.name}" decoding="async" draggable="false" onerror="this.onerror=null;this.src='assets/arenas/${X.id}/badge.webp'">${reached ? '' : '<img class="isle-lock" src="assets/ui/sm/icon_lock.webp" alt="locked">'}</div>`;
      sl.onclick = () => { audio.play('ui_tab'); this.hub('road'); };
      track.append(sl);
      const d = h('button', 'adot' + (mine ? ' mine' : '') + (reached ? '' : ' locked')); d.ariaLabel = X.name; d.onclick = () => go(i, true); dots.append(d);
    });
    const prev = h('button', 'acar-arrow prev', '<i></i>'), next = h('button', 'acar-arrow next', '<i></i>');
    car.append(track, prev, next);
    let at = -1;
    const go = (i, smooth) => { i = Math.max(0, Math.min(ARENAS.length - 1, i)); track.scrollTo({left: i * track.clientWidth, behavior: smooth ? 'smooth' : 'instant'}); if (smooth) tap(); };
    const sync = () => {
      const i = Math.round(track.scrollLeft / (track.clientWidth || 1)); if (i === at) return;
      at = i; if (!LOCAL || track.clientWidth) this.arenaAt = i;
      track.querySelectorAll('.aslide').forEach((e, j) => { e.classList.toggle('on', j === i); const im = Math.abs(j - i) <= 1 && e.querySelector('img[data-src]'); if (im) { im.src = im.dataset.src; im.removeAttribute('data-src'); } });
      dots.querySelectorAll('.adot').forEach((e, j) => e.classList.toggle('on', j === i));
      prev.classList.toggle('off', i === 0); next.classList.toggle('off', i === ARENAS.length - 1);
      if (LOCAL && track.clientWidth) { this.battleSub.textContent = ARENAS[i].name; localStorage.setItem('memeroyale.localArena', i); }
    };
    prev.onclick = () => go(at - 1, true); next.onclick = () => go(at + 1, true);
    let raf = 0; track.addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; sync(); }); }, {passive: true});
    requestAnimationFrame(() => { go(start, false); sync(); });
    mid.append(strip, car, dots);
  }
  localArena() { return LOCAL && this.arenaAt != null ? ARENAS[this.arenaAt].id : null; }
  // under the bag tray: DECK (my deck's first card), BATTLE, and the Trophy Road (where CR keeps its mode switcher)
  battleRow() {
    const R = h('div', 'battle-row'), claim = save.roadClaimable().length;
    const deck = h('button', 'side-btn deckb'); deck.append(cardEl(save.deck[0], {cost: false, name: false}), h('span', 'lbl stroke-s', `DECK ${save.p.active + 1}`));
    deck.onclick = () => { tap(); this.hub('deck'); };
    const bb = h('button', 'btn battle-btn'); bb.innerHTML = `<b>BATTLE</b><small>${this.app.net?.online ? '1v1 · ONLINE' : '1v1 · VS BOTS'}</small>`;
    this.battleSub = bb.querySelector('small');
    bb.onclick = () => { audio.play('ui_tap'); buzz(15); this.app.battle(); };
    const road = h('button', 'side-btn roadb'); road.innerHTML = `<img src="assets/ui/sm/icon_clout.webp" alt=""><span class="lbl stroke-s">ROAD</span>${claim ? `<b class="dot">${claim}</b>` : ''}`;
    road.onclick = () => { audio.play('ui_tab'); this.hub('road'); };
    R.append(deck, bb, road); return R;
  }
  tabs() {
    const T = h('div', 'panel tabs'), road = save.roadClaimable().length, free = !save.p.shop.free;
    for (const [id, icon, label, dot] of [['shop', 'shop', 'SHOP', free ? '!' : ''], ['deck', 'deck', 'DECK', ''], ['battle', 'battle', 'BATTLE', ''], ['road', 'clout', 'ROAD', road || ''], ['social', 'social', 'SOCIAL', this.app.net?.online && !save.p.account ? '!' : '']]) {
      const b = h('button', 'tab' + (this.tab === id ? ' on' : '')); b.innerHTML = `<img src="assets/ui/sm/icon_${icon}.webp" alt="" onerror="this.onerror=null;this.src='assets/ui/sm/icon_emote.webp'"><span>${label}</span>${dot ? `<b class="dot">${dot}</b>` : ''}`;
      b.onclick = () => { if (this.tab !== id) { audio.play('ui_tab'); this.hub(id); } };
      T.append(b);
    }
    return T;
  }

  // ---------- the daily W bag: take 10 Ws (towers) in a day, get a free bag (CR's pass box, in the home's top row)
  wbox() {
    const w = save.wbag(), n = Math.min(W_BAG.need, w.ws), E = h('button', 'panel wbagbox' + (w.ready ? ' ready' : w.claimed ? ' done' : ''));
    E.innerHTML = `<img src="assets/ui/sm/shop/bag_w.webp" onerror="this.src='assets/ui/sm/icon_w_bull.webp'" alt=""><div class="wtxt"><span class="wt">DAILY<br>W BAG</span><div class="wbar"><i style="width:${n / W_BAG.need * 100}%"></i><span class="num">${w.claimed ? 'CLAIMED' : w.ready ? 'OPEN!' : `${n} / ${W_BAG.need} Ws`}</span></div></div>${w.ready ? '<b class="dot">!</b>' : ''}`;
    E.onclick = e => { e.stopPropagation(); tap(); if (w.ready) this.run({a: 'claimWBag'}, r => this.openRoll(r.bag)); else this.toast(w.claimed ? 'Come back tomorrow for a new W bag.' : `Take ${W_BAG.need - n} more Ws today for a free ${BAG[W_BAG.tier].name}.`); };
    return E;
  }

  // ---------- bags
  bags() {
    const B = h('div', 'bags'); this.bagEls = [];
    save.p.bags.forEach((b, i) => { const e = h('button', 'bag panel'); this.bagEls.push(e); e.onclick = () => this.bagTap(i); B.append(e); });
    this.refreshBags(true); return B;   // filled now, before it is on the page (else the slots show empty for a second)
  }
  refreshBags(fresh) {
    if (!fresh && !this.bagEls?.[0]?.isConnected) return;
    const busy = save.bagBusy();
    save.p.bags.forEach((b, i) => {
      const e = this.bagEls[i];
      if (!b) { e.className = 'bag empty'; e.innerHTML = ''; return; }
      e.className = 'bag panel'; e.style.boxShadow = `inset 0 0 0 2px ${BAG[b.tier].color}88, 0 0 10px ${BAG[b.tier].color}33, 0 4px 0 #140A30`;
      const ready = save.bagReady(b), left = save.bagLeft(b);
      const tag = ready ? '<div class="tag open">OPEN</div>' : b.start ? `<div class="tag wait"><img src="assets/ui/sm/icon_timer.webp" alt="">${dur(left)}</div>` : `<div class="tag idle">${busy ? dur(BAG[b.tier].time) : 'UNLOCK'}</div>`;
      const html = `<img src="assets/ui/sm/icon_bag_${b.tier}.webp" alt="">${tag}`; if (e.innerHTML !== html) e.innerHTML = html;
    });
  }
  bagTap(i) {
    const b = save.p.bags[i]; if (!b) return; tap();
    if (save.bagReady(b)) return this.openBag(i);
    const T = BAG[b.tier], cost = save.speedCost(b);
    this.sheet(box => {
      box.innerHTML = `<div style="display:grid;justify-items:center;gap:6px"><img src="assets/ui/icon_bag_${b.tier}.webp" style="width:150px;filter:drop-shadow(0 4px 0 #140A30)"><h3 class="stroke-s">${T.name.toUpperCase()}</h3>
        <p style="text-align:center">${T.cards} cards · ${T.cash[0]}–${T.cash[1]} coins${T.gems[0] ? ' · maybe gems' : ''}${T.epic >= 1 ? ' · guaranteed Epic' : ''}${T.legendary >= 1 ? ' · guaranteed Legendary' : ''}</p></div>`;
      const acts = h('div', 'acts');
      if (!b.start) {
        const busy = save.bagBusy();
        const u = h('button', 'btn small', busy ? 'Another bag is unlocking' : `Unlock · ${dur(T.time)}`); if (busy) u.disabled = true;
        u.onclick = () => this.run({a: 'startBag', i}, () => { tap(); this.closeSheet(); this.hub('battle'); });
        acts.append(u);
      }
      const o = h('button', 'btn purple small'); o.innerHTML = `Open now · ${GEM} ${cost}`;
      if (save.p.gems < cost) o.disabled = true;
      o.onclick = () => this.run({a: 'speedBag', i}, () => { audio.play('gem_buy'); this.closeSheet(); this.openBag(i); });
      acts.append(o); box.append(acts);
    });
  }
  async openBag(i) { const r = await this.run({a: 'openBag', i}); if (r) this.openRoll(r.bag); }
  // the opening, CR's way: the bag drops in and wobbles; a tap bursts it open; then each tap pops the next thing out of
  // it (the coins, the gems, each card flipping over, an Epic or a Legendary charging up first), and a last tap shows
  // everything that came out. A tap within a beat of the last one is ignored, so nothing gets skipped by a double tap.
  // Kept smooth on a phone: the cards' big art (seen nowhere else but the card sheet, so rarely cached) is fetched and
  // decoded while the bag drops in, and a card waits for its picture rather than fly out without it; the rays keep the
  // bag's colour (a new colour repaints the whole spinning wheel, a phone-screen-sized gradient) while each thing's own
  // colour lights a glow behind it; every move is a transform or an opacity (the card's flight a Web Animation with its
  // numbers filled in: Safari leaves a CSS animation whose keyframes read a variable off the GPU). Nothing under it is
  // drawn meanwhile (style.css): the screen and the Trophy Road leave the layout, so the road's scroll is kept here for
  // hub() to put back, and the sky stops.
  openRoll(res) {
    if (!res) return;
    this.roadTop ??= this.roadEl?.querySelector('.rv-scroll')?.scrollTop;   // (not again over a bag still open: it reads 0 there)
    clearInterval(this.timer); clearTimeout(this.redraw); this.closeSheet(); this.bagEl?.remove();
    const T = BAG[res.tier], O = this.bagEl = h('div', 'bagopen');
    const steps = [{coins: res.coins ?? res.cash}, ...(res.gems ? [{gems: res.gems}] : []), ...res.drops];
    O.style.setProperty('--ray', T.color + '44');
    O.innerHTML = '<div class="rays"><i></i></div><div class="bo-glow"></div><div class="flash"></div>';
    const stage = h('div', 'bo-stage'), bag = h('div', 'bo-bag drop'), title = h('div', 'bo-title stroke', T.name.toUpperCase()), tapEl = h('div', 'tap stroke-s', 'TAP TO OPEN');
    bag.innerHTML = `<i class="bo-shadow"></i><img class="bagimg" src="assets/ui/icon_bag_${res.tier}.webp" alt=""><b class="bo-count num">${steps.length}</b>`;
    O.append(stage, bag, title, tapEl); this.ui.append(O);
    // the bag's own picture first (on a slow line the cards' art would hold it up), then what comes out of it
    const bimg = bag.querySelector('.bagimg'), pre = () => { warm([...new Set(res.drops.map(d => cardArt(d.id, true))), 'assets/ui/card_back.webp', 'assets/ui/sm/icon_cash.webp']);
      audio.preload(['bag_open', 'coin_jingle', 'coins', 'gem_buy', 'card_reveal', 'card_reveal_epic', 'card_reveal_legendary', 'reward_claim']); };
    bimg.fetchPriority = 'high'; if (bimg.complete) pre(); else { bimg.addEventListener('load', pre, {once: true}); bimg.addEventListener('error', pre, {once: true}); }
    audio.play('ui_swoosh'); setTimeout(() => { if (O.isConnected) { audio.play('bag_shake'); buzz(20); } }, 420);
    const count = bag.querySelector('.bo-count'), flash = () => O.querySelector('.flash').animate([{opacity: 0.8}, {opacity: 0}], {duration: 500, easing: 'ease-out'});
    // the glow behind what just came out, in its colour (none: it fades away)
    const G = O.querySelector('.bo-glow'), glow = col => {
      if (!col) { G.animate({opacity: 0}, {duration: 300, fill: 'forwards'}); return; }
      G.style.setProperty('--gc', col);
      G.animate([{opacity: 0, transform: 'scale(.45)'}, {opacity: 1, transform: 'scale(1.06)', offset: 0.45}, {opacity: 0.85, transform: 'scale(1)'}], {duration: 700, easing: 'ease-out', fill: 'forwards'});
    };
    let k = -1, ready = performance.now() + 700, busy = false;
    const close = () => { O.remove(); if (this.bagEl === O) this.bagEl = null; this.hub(this.tab); };
    const reveal = s => {
      stage.replaceChildren(); const R = h('div', 'reveal'); stage.append(R);
      if (s.coins != null) {
        R.innerHTML = `<div class="cashwin stroke"><img src="assets/ui/sm/icon_cash.webp" alt=""><span class="num">+0</span></div><div class="disp stroke-s bo-what">COINS</div>`;
        const n = R.querySelector('.num'), t0 = performance.now(), go = t => { const q = Math.min(1, (t - t0) / 550); n.textContent = '+' + fmt(s.coins * (1 - Math.pow(1 - q, 3))); if (q < 1 && n.isConnected) requestAnimationFrame(go); };
        requestAnimationFrame(go); audio.play(audio.has('coin_jingle') ? 'coin_jingle' : 'coins');
        glow('#FFC84A66');
      } else if (s.gems != null) {
        R.innerHTML = `<div class="cashwin stroke gemwin">${GEM}<span class="num">+${fmt(s.gems)}</span></div><div class="disp stroke-s bo-what">GEMS</div>`;
        audio.play('gem_buy'); glow('#C77DFF66');
      } else {
        const c = CARDS[s.id], r = RARITY[c.rarity], own = save.p.cards[s.id], up = save.canUpgrade(s.id);
        const tg = h('div', 'rtag disp', r.name); tg.style.background = r.color;
        const flip = h('div', 'flip'), back = h('div', 'face back'), front = h('div', 'face front');
        back.innerHTML = '<img src="assets/ui/card_back.webp" alt="">';
        front.append(cardEl(s.id, {lvl: save.lvl(s.id), big: true})); if (s.isNew) front.append(h('div', 'newtag', 'NEW!'));
        flip.append(back, front);
        const wrap = h('div', 'bo-card'); wrap.append(flip, h('div', 'xn stroke', 'x' + s.n));
        const nm = h('div', 'disp stroke-s bo-what', c.name);
        const bar = h('div', 'bo-bar' + (up?.ok ? ' full' : '')), now = own?.copies ?? s.n, was = Math.max(0, now - s.n);
        bar.innerHTML = up ? `<i style="transform:scaleX(${Math.min(1, was / up.n).toFixed(3)})"></i><span class="num">${now} / ${up.n}</span>` : '<i></i><span class="num">MAX LEVEL</span>';
        R.append(tg, wrap, nm, bar); if (s.isNew) R.append(h('div', 'bo-up bo-found stroke-s', STAR + ' NEW CARD FOUND')); else if (up && now >= up.n) R.append(h('div', 'bo-up stroke-s', UP + ' READY TO UPGRADE'));
        // the card flies out of the bag face down, spinning, and lands face up: from the bag's spot
        const br = bag.getBoundingClientRect(), wr = wrap.getBoundingClientRect(), z = wrap.offsetHeight / (wr.height || 1);
        const dy = ((br.top + br.height * 0.35 - (wr.top + wr.height / 2)) * z).toFixed(0), E = 'cubic-bezier(.25,1,.4,1)';
        flip.animate([{transform: `translateY(${dy}px) scale(.2) rotateY(540deg)`, opacity: 0, easing: E}, {opacity: 1, offset: 0.1, easing: E},
          {transform: 'translateY(-18px) scale(1.08) rotateY(0deg)', offset: 0.66, easing: E}, {transform: 'none', opacity: 1}], {duration: 800, fill: 'both'});
        if (up) setTimeout(() => { const i = bar.querySelector('i'); if (i) i.style.transform = `scaleX(${Math.min(1, now / up.n).toFixed(3)})`; }, 650);
        glow(r.color + '77');
        audio.play(c.rarity === 'legendary' ? 'card_reveal_legendary' : c.rarity === 'epic' ? 'card_reveal_epic' : 'card_reveal');
        if (c.rarity !== 'common') flash();
      }
    };
    const summary = () => {
      bag.remove(); tapEl.remove(); title.remove();
      const Sm = h('div', 'panel bo-sum'), g = h('div', 'bo-grid');
      Sm.append(h('div', 'disp stroke bo-sumt', 'YOU GOT'));
      const coin = h('div', 'bo-res'); coin.innerHTML = `<img src="assets/ui/sm/icon_cash.webp" alt=""><b class="num">+${fmt(res.coins ?? res.cash)}</b>`; g.append(coin);
      if (res.gems) { const e = h('div', 'bo-res gem'); e.innerHTML = `${GEM}<b class="num">+${fmt(res.gems)}</b>`; g.append(e); }
      res.drops.forEach((d, i) => { const e = h('div', 'bo-mini'); e.style.animationDelay = (i * 0.05).toFixed(2) + 's'; e.append(cardEl(d.id, {cost: false, name: false}), h('b', 'xn stroke-s', 'x' + d.n)); if (d.isNew) e.append(h('i', 'newtag', 'NEW')); g.append(e); });
      const ok = h('button', 'btn', 'OK'); ok.onclick = e => { e.stopPropagation(); tap(); close(); };
      Sm.append(g, ok); stage.replaceChildren(Sm); glow(null);
      audio.play('reward_claim');
    };
    const next = () => {
      k++; buzz(15);
      if (k === 0) { bag.classList.remove('drop'); bag.classList.add('open'); title.classList.add('out'); flash(); audio.play('bag_open'); }
      if (k >= steps.length) { summary(); return; }
      count.textContent = steps.length - k - 1; count.classList.toggle('zero', steps.length - k - 1 === 0);
      tapEl.textContent = k === steps.length - 1 ? 'TAP TO SEE ALL' : 'TAP FOR NEXT';
      const s = steps[k], rar = s.id && CARDS[s.id].rarity;
      if (!s.id) { reveal(s); ready = performance.now() + 320; return; }
      // a card comes out once its picture is in (normally long since: it loads while the bag drops in)
      const art = whenKept(cardArt(s.id, true), 1500), out = (p, after) => { busy = true; p.then(() => { busy = false; if (O.isConnected) { reveal(s); ready = performance.now() + after; } }); };
      // an Epic or a Legendary: the bag glows in its colour and rattles before it lets go
      if (rar === 'epic' || rar === 'legendary') {
        stage.replaceChildren(); glow(null); bag.style.setProperty('--glow', RARITY[rar].color + 'cc'); bag.classList.add('charge'); audio.play('bag_shake'); buzz([20, 40, 20]);
        out(Promise.all([art, new Promise(r => setTimeout(r, rar === 'legendary' ? 1000 : 700))]).then(() => bag.classList.remove('charge')), 450);
      } else out(art, 320);
    };
    O.onclick = () => { if (busy || performance.now() < ready || k >= steps.length) return; next(); };
  }

  // ================= DECK =================
  deck(page) {
    const p = save.p, deck = save.deck;
    const avg = (deck.reduce((s, id) => s + CARDS[id].cost, 0) / deck.length).toFixed(1);
    const head = h('div', 'panel deck-info deck-top');
    head.innerHTML = `<div class="decktabs">${[0, 1, 2].map(i => `<button class="${i === p.active ? 'on' : ''}" data-i="${i}">DECK ${i + 1}</button>`).join('')}</div><div class="avg"><img src="assets/ui/sm/icon_copium.webp" alt="">AVG ${avg}</div>`;
    head.querySelectorAll('button').forEach(b => b.onclick = () => { tap(); this.run({a: 'setDeck', slot: +b.dataset.i, active: true}, () => this.hub('deck', true)); });
    // USE: the chosen card waits in a panel over the deck (floating on a glow of its rarity's colour) and the deck's cards
    // bob in a slow wave until one is tapped (the chosen one flies into its place); CANCEL, or a tap anywhere else, sends
    // it back to its gap in the collection, which steps back meanwhile
    const back = this.using && !this.swap; this.using = !!this.swap;
    if (this.swap) {
      const U = h('div', 'panel use-panel deck-top'), held = h('div', 'use-held'), c = CARDS[this.swap];
      held.style.setProperty('--glow', RARITY[c.rarity].color); held.append(cardEl(this.swap, {lvl: p.cards[this.swap]?.lvl}));
      const x = h('button', 'btn small dark', 'CANCEL'); x.onclick = e => { e.stopPropagation(); tap(); this.unuse(); };
      U.append(held, h('div', 'use-t', `<small>SWAP IN</small><b class="stroke-s">${c.name}</b><span>Tap a card in your deck</span>`), x);
      page.append(U); page.classList.add('using');
      page.addEventListener('click', e => { if (this.swap && !e.target.closest('.deckcard, .use-panel')) { tap(); this.unuse(); } });
    } else page.append(head);
    if (back) page.classList.add('back');
    const dg = h('div', 'panel brk grid4' + (this.swap ? ' picking' : '')); page.append(dg);
    deck.forEach((id, i) => { const d = this.deckCard(id, true); d.style.setProperty('--i', i % 4 + (i >> 2)); dg.append(d); });
    // the cards I don't have: those of the arenas I reached drop from bags (found in one, a card is mine), the rest wait for their arena
    const can = new Set(findable(p)), owned = CARD_IDS.filter(id => p.cards[id] && !deck.includes(id));
    const toFind = CARD_IDS.filter(id => !p.cards[id] && can.has(id)), locked = CARD_IDS.filter(id => !p.cards[id] && !can.has(id));
    page.append(h('h2', 'stroke-s', `COLLECTION <small>${Object.keys(p.cards).length}/${CARD_IDS.length} found</small>`));
    const cg = h('div', 'panel plain grid4'); page.append(cg);
    for (const id of owned) { const d = this.deckCard(id, false); if (id === this.swap) d.classList.add('away'); cg.append(d); }
    if (!owned.length) cg.append(h('div', 'grid-note', 'Every card you own is in this deck.'));
    if (toFind.length) {
      page.append(h('h2', 'stroke-s', 'IN BAGS <small>open bags to find them</small>'));
      const fg = h('div', 'panel plain grid4'); page.append(fg);
      for (const id of toFind) { const d = this.deckCard(id, false); d.classList.add('locked', 'tofind'); fg.append(d); }
    }
    if (locked.length) {
      page.append(h('h2', 'stroke-s', 'LOCKED <small>reach their arena on the road</small>'));
      const lg = h('div', 'panel plain grid4'); page.append(lg);
      for (const id of locked) { const d = this.deckCard(id, false); d.classList.add('locked'); lg.append(d); }
    }
    this.deckDrag(page);
  }
  // a card also swaps by dragging it: from the collection onto a deck card (it takes that place), a deck card onto another
  // (they change places) or onto a collection card (that one takes its place). A mouse lifts it as soon as it moves; a
  // finger first holds still a moment (one that moves at once scrolls the page), and the page then stops scrolling under it
  // until it lets go (a touchmove listener of the page's own, so only this page's scrolls wait on it). The click that ends a
  // drag is swallowed, so the card's sheet doesn't open.
  // each card of a redrawn deck page glides from where it was (was: id -> its old screen rect; a dropped card from where
  // it was let go) to its new place; it rides over the panels on the way (z-index)
  // the swap seen: a card that went into the deck, out of it or to another slot flies there (tossed on a low arc, tilted
  // the way it goes, no bounce) and lands with a soft flash; the rest (a deck moved by the USE panel, the collection
  // closing its gap) slides along to its new place
  glideCards(page, was) {
    const drop = performance.now() - (this.dropAt?.t || 0) < 1500 ? this.dropAt : null; this.dropAt = null;
    let end = 0;
    for (const e of page.querySelectorAll('.deckcard')) {
      const p = was.get(e.dataset.id), a = drop?.id === e.dataset.id ? drop.rect : p?.r; if (!a) continue;
      const deck = e.classList.contains('indeck'), dropped = drop?.id === e.dataset.id, fly = dropped || p?.deck !== deck || deck && p?.i !== [...e.parentNode.children].indexOf(e);
      end = Math.max(end, this.flyCard(e, a, fly ? {land: deck, scale: dropped, ref: dropped && e.querySelector('.card')} : {slide: true}));
    }
    this.glideUntil = performance.now() + end + (end ? 500 : 0);   // (and the landing flash)
  }
  // one card from a screen rect (a = where it was) to where it is now: tossed on an arc, or slid straight (slide); scale
  // grows it from that rect's size; land flashes it on arrival; ref is the part a was measured on (a card in its deck
  // slot, not the slot with its bar). Returns its time (ms, 0 when it hasn't moved)
  flyCard(e, a, {slide, scale, land, ms, ref} = {}) {
    const R = ref || e, b = R.getBoundingClientRect(), k = R.offsetWidth / (b.width || 1), dx = (a.left + a.width / 2 - b.left - b.width / 2) * k, dy = (a.top + a.height / 2 - b.top - b.height / 2) * k;
    const s0 = scale ? a.width / (b.width || 1) : 1, dist = Math.hypot(dx, dy);
    if (dist < 1 && Math.abs(s0 - 1) < 0.01) return 0;
    const t = ms || (slide ? 300 : Math.min(600, 340 + dist * 0.45)), lift = slide ? 0 : Math.min(44, 12 + dist * 0.1), tilt = slide ? 0 : Math.max(-7, Math.min(7, -dx * 0.04));
    const f = [];
    for (let i = 0; i <= 10; i++) {
      const u = i / 10, arc = 4 * u * (1 - u), w = Math.sin(Math.PI * u);
      f.push({transform: `translate(${dx * (1 - u)}px, ${dy * (1 - u) - lift * arc}px) rotate(${tilt * w}deg) scale(${s0 + (1 - s0) * u + (slide ? 0 : 0.1 * w)})`});
    }
    e.style.zIndex = slide ? 5 : 7; if (!slide) e.classList.add('flying');
    e.animate(f, {duration: t, easing: slide ? 'cubic-bezier(.25,.8,.3,1)' : 'cubic-bezier(.33,.7,.3,1)'}).onfinish = () => {
      e.style.zIndex = ''; e.classList.remove('flying'); if (land) { e.classList.remove('landed'); void e.offsetWidth; e.classList.add('landed'); }
    };
    return t;
  }
  // the deck's top panel (its tabs, or a USE's chosen card: a taller panel) grows or shrinks to its new height instead of
  // jumping, so the deck under it moves smoothly (the cards measure their flights from where the panel starts)
  resizeTop(page, was) {
    const T = page.querySelector('.deck-top'); if (!T || !was) return;
    const now = T.offsetHeight; if (Math.abs(now - was) < 2) return;
    T.classList.add('resizing'); T.style.height = was + 'px';
    requestAnimationFrame(() => { T.style.height = now + 'px'; });
    T.addEventListener('transitionend', () => { T.classList.remove('resizing'); T.style.height = ''; }, {once: true});
  }
  // the chosen card goes back to its gap in the collection
  unuse() {
    const r = this.ui.querySelector('.use-held .card')?.getBoundingClientRect();
    if (r) this.dropAt = {id: this.swap, rect: r, t: performance.now()};
    this.swap = null; this.hub('deck', true);
  }
  deckDrag(page) {
    let D = null;
    const at = (x, y) => document.elementFromPoint(x, y)?.closest('.deckcard:not(.locked)');
    page.addEventListener('touchmove', e => { if (D) e.preventDefault(); }, {passive: false});
    page.addEventListener('contextmenu', e => { if (e.target.closest('.deckcard')) e.preventDefault(); });
    page.addEventListener('pointerdown', e => {
      const src = (e.pointerType !== 'mouse' || e.button === 0) && e.target.closest('.deckcard:not(.locked)'); if (!src || D) return;
      const x0 = e.clientX, y0 = e.clientY, touch = e.pointerType !== 'mouse';
      const lift = (x, y) => {
        D = {src, ghost: cardEl(src.dataset.id, {name: false}), over: null};
        D.ghost.classList.add('dragcard'); this.ui.append(D.ghost); src.classList.add('lifted'); buzz(12); audio.play('card_pick'); place(x, y);
      };
      const place = (x, y) => {
        D.ghost.style.left = x + 'px'; D.ghost.style.top = y + 'px';
        const o = at(x, y), ok = o && o !== D.src && (o.classList.contains('indeck') || D.src.classList.contains('indeck')) ? o : null;
        if (ok !== D.over) { D.over?.classList.remove('drop'); ok?.classList.add('drop'); D.over = ok; }
      };
      let hold = touch ? setTimeout(() => lift(x0, y0), 260) : 0;
      const move = m => {
        if (m.pointerId !== e.pointerId) return;
        if (D) return place(m.clientX, m.clientY);
        if (Math.hypot(m.clientX - x0, m.clientY - y0) > (touch ? 8 : 6)) { if (touch) end(); else lift(m.clientX, m.clientY); }
      };
      const end = () => {
        clearTimeout(hold); removeEventListener('pointermove', move); removeEventListener('pointerup', up); removeEventListener('pointercancel', end);
        if (!D) return;
        D.ghost.remove(); D.src.classList.remove('lifted'); D.over?.classList.remove('drop'); D = null;
        const eat = k => { k.stopPropagation(); k.preventDefault(); };
        addEventListener('click', eat, true); setTimeout(() => removeEventListener('click', eat, true), 60);
      };
      const up = u => {
        if (u.pointerId !== e.pointerId) return;
        const T = D?.over, a = D?.src.dataset.id, b = T?.dataset.id; if (T) this.dropAt = {id: a, rect: D.ghost.getBoundingClientRect(), t: performance.now()}; end(); if (!T) return;
        const d = [...save.deck], i = d.indexOf(a), j = d.indexOf(b);
        if (i >= 0 && j >= 0) { d[i] = b; d[j] = a; } else if (j >= 0) d[j] = a; else d[i] = b;
        this.swap = null; this.run({a: 'setDeck', slot: save.p.active, cards: d}, () => { audio.play('card_pick'); this.hub('deck', true); });
      };
      addEventListener('pointermove', move); addEventListener('pointerup', up); addEventListener('pointercancel', end);
    });
  }
  deckCard(id, inDeck) {
    const c = save.p.cards[id], D = h('div', 'deckcard' + (inDeck ? ' indeck' : '')); D.dataset.id = id;
    const ce = cardEl(id, {lvl: c?.lvl}); D.append(ce);
    if (c) {
      const u = save.canUpgrade(id), bar = h('div', 'bar' + (u?.ok ? ' full' : ''));
      bar.innerHTML = u ? `<i style="width:${Math.min(100, c.copies / u.n * 100)}%"></i><span>${c.copies}/${u.n}</span>` : '<i style="width:100%"></i><span>MAX</span>';
      D.append(bar);
      if (u?.ok) D.append(h('div', 'upgr', '▲'));
    } else { const A = ARENAS.find(a => a.unlock.includes(id)); D.append(h('div', 'prog-t', findable(save.p).includes(id) ? 'IN BAGS' : A ? `ARENA ${A.n}` : '')); D.lastChild.style.textAlign = 'center'; }
    D.onclick = () => {
      tap();
      if (this.swap && inDeck) {
        const d = [...save.deck], r = this.ui.querySelector('.use-held .card')?.getBoundingClientRect(); d[d.indexOf(id)] = this.swap;
        if (r) this.dropAt = {id: this.swap, rect: r, t: performance.now()};
        this.swap = null; this.run({a: 'setDeck', slot: save.p.active, cards: d}, () => { audio.play('card_pick'); buzz(15); this.hub('deck', true); }).then(ok => ok || this.hub('deck', true));
        return;
      }
      if (this.swap) { this.unuse(); return; }
      this.cardSheet(id, inDeck);
    };
    return D;
  }
  cardSheet(id, inDeck) {
    const c = CARDS[id], own = save.p.cards[id], lvl = own?.lvl || 1, S = statsFor(id, lvl), N = own && lvl < MAX_LVL ? statsFor(id, lvl + 1) : null, r = RARITY[c.rarity];
    this.sheet(box => {
      const head = h('div', 'head'); head.append(cardEl(id, {lvl: own ? lvl : null, big: true}));
      const t = h('div'); t.innerHTML = `<div class="rar" style="color:${r.color}">${r.name.toUpperCase()} ${c.type === 'spell' ? 'SPELL' : c.type === 'building' ? 'BUILDING' : 'MEME'}</div><h3 class="stroke-s">${c.name}</h3><p>${c.blurb}</p>`;
      head.append(t); box.append(head);
      const g = h('div', 'statgrid'), add = (k, v, nv, unit = '') => { const d = h('div'); d.innerHTML = `<div class="k">${k}</div><div class="v">${v}${unit}${nv != null && nv !== v ? ` <em>+${nv - v}</em>` : ''}</div>`; g.append(d); };
      if (c.type === 'unit') {
        add('HEALTH', S.hp, N?.hp); add(S.beam ? 'BEAM (MAX)' : 'DAMAGE', S.beam ? S.beam[2] : S.dmg, S.beam ? N?.beam[2] : N?.dmg);
        add('HIT SPEED', S.hs + 's'); add('SPEED', S.speed >= 1.8 ? 'Very fast' : S.speed >= 1.4 ? 'Fast' : S.speed >= 1 ? 'Medium' : 'Slow');
        add('RANGE', S.range > 1.5 ? S.range.toFixed(1) : 'Melee'); add('TARGETS', S.bOnly ? 'Buildings' : 'Ground');
        if (S.n > 1) add('COUNT', 'x' + S.n); if (S.splash) add('SPLASH', S.splash + ' tiles'); if (S.heal) add('HEALS', S.heal[0], N?.heal[0], '/s');
      } else if (c.type === 'building') {
        add('HEALTH', S.hp, N?.hp); add('LIFETIME', S.life + 's');
        if (S.dmg) { add('DAMAGE', S.dmg, N?.dmg); add('HIT SPEED', S.hs + 's'); add('RANGE', S.range); add('TARGETS', 'Ground'); }
        if (S.mine) { add('COPIUM', `+1 / ${S.mine}s`); add('TOTAL', '+' + Math.floor(S.life / S.mine)); }
      } else {
        if (S.dmg) add('DAMAGE', S.dmg, N?.dmg); if (S.dps) add('PER SECOND', S.dps, N?.dps); if (S.dmg || S.dps) add('TOWER DMG', Math.round((S.dmg || S.dps) * S.tower) + (S.dps ? '/s' : ''));
        add('RADIUS', S.roll ? `${S.r * 2} wide` : S.r); if (S.roll) add('ROLLS', S.roll + ' tiles');
        if (S.stun) add('STUN', S.stun + 's'); if (S.freeze) add('FREEZE', S.freeze + 's'); if (S.dur) add('DURATION', S.dur + 's'); if (S.boost) add('BOOST', '+40%'); if (S.slow) add('SLOW', Math.round((1 - S.slow) * 100) + '%');
      }
      box.append(g);
      const acts = h('div', 'acts');
      if (own) {
        const u = save.canUpgrade(id);
        if (u) { const b = h('button', 'btn small' + (u.ok ? '' : ' dark')); b.innerHTML = `<img src="assets/ui/sm/icon_upgrade.webp" style="width:22px"> LV ${lvl + 1} · ${COIN} ${fmt(u.cost)}`;
          if (!u.ok) b.disabled = true;
          b.onclick = () => this.run({a: 'upgrade', id}, r => { audio.play('level_up'); buzz([20, 30, 40]); this.closeSheet(); this.hub('deck'); if (r.levelUp) this.levelUp(r.levelUp); else setTimeout(() => this.cardSheet(id, inDeck), 60); });
          acts.append(b); }
        if (!inDeck) { const b = h('button', 'btn small purple', 'USE'); b.onclick = () => { tap(); this.swap = id; this.useFrom = box.querySelector('.head .card')?.getBoundingClientRect(); this.closeSheet(); this.hub('deck'); }; acts.append(b); }
        if (u && !u.ok) acts.append(h('div', 'prog-t', `${own.copies}/${u.n} cards · ${fmt(u.cost)} coins for level ${lvl + 1}`));
      } else {
        const A = ARENAS.find(a => a.unlock.includes(id));
        acts.append(h('div', 'prog-t', findable(save.p).includes(id) ? `Not found yet: it drops from bags since Arena ${A.n}. Open bags to find it!` : `Reach Arena ${A.n}: ${A.name} (${fmt(A.at)} Clout) and it starts dropping from bags.`));
      }
      const cl = h('button', 'btn small dark', 'CLOSE'); cl.onclick = () => { tap(); this.closeSheet(); }; acts.append(cl);
      box.append(acts);
    });
  }
  levelUp(level) {
    audio.play('arena_unlock');
    this.sheet(box => { box.innerHTML = `<div style="display:grid;justify-items:center;gap:6px"><div class="lvl-big stroke">${level}</div><h3 class="stroke-s">LEVEL UP!</h3><p style="text-align:center">Your towers are now level ${level}.</p></div>`;
      const a = h('div', 'acts'), ok = h('button', 'btn small', 'NICE'); ok.onclick = () => { tap(); this.closeSheet(); this.hub(this.tab); }; a.append(ok); box.append(a); });
  }
  // my profile (a tap on it in the top bar): my picture, name, level and record, and the picture picker: a portrait of every
  // character (AVATARS), the ones whose card I don't own yet locked
  profile() {
    const p = save.p, A = save.arena, st = p.stats;
    this.sheet(box => {
      box.classList.add('profile-box');
      const head = h('div', 'pf-head'), big = h('div', 'pf-ava');
      const draw = () => { big.innerHTML = `<img src="${avatarArt(save.avatar, true)}" alt=""><b class="lvl-badge">${p.level}</b>`; };
      draw();
      const who = h('div', 'pf-who'), nm = h('button', 'pf-name');
      nm.innerHTML = `<b class="stroke-s"></b><span class="pf-edit">EDIT</span>`; nm.firstChild.textContent = p.name;
      nm.onclick = () => { tap(); const v = prompt('Your name (3-14 characters)', p.name); if (v) this.run({a: 'setName', name: v.trim()}, () => { nm.firstChild.textContent = save.p.name; this.toast('Name changed.'); }); };
      who.append(nm, h('div', 'pf-tags', `<span class="pill"><img src="assets/ui/sm/icon_clout.webp" alt=""><span class="num">${fmt(p.clout)}</span></span>`), h('div', 'prog-t', `best ${fmt(p.best)} · ARENA ${A.n} ${A.name}`));
      head.append(big, who); box.append(head);
      box.append(h('div', 'pf-stats', `<div><b class="num">${fmt(st.wins)}</b>WINS</div><div><b class="num">${fmt(st.losses)}</b>LOSSES</div><div><b class="num">${fmt(st.ws)}</b>Ws TAKEN</div><div><b class="num">${fmt(st.played)}</b>BATTLES</div>`));
      box.append(h('div', 'pf-h disp stroke-s', 'PROFILE PICTURE'));
      const g = h('div', 'pf-grid');
      for (const id of [...AVATARS].sort((a, b) => !p.cards[a] - !p.cards[b])) {
        const own = !!p.cards[id], c = h('button', 'pf-pic' + (own ? '' : ' locked') + (id === save.avatar ? ' picked' : ''), `<img src="${avatarArt(id)}" alt="${CARDS[id].name}" loading="lazy">${own ? '' : '<img class="lk" src="assets/ui/sm/icon_lock.webp" alt="locked">'}`);
        c.onclick = () => {
          if (!own) { tap(); this.toast(`Unlock ${CARDS[id].name} to use this picture.`); return; }
          if (id === save.avatar) return; tap();
          this.run({a: 'setAvatar', id}, () => { audio.play('card_pick'); g.querySelector('.picked')?.classList.remove('picked'); c.classList.add('picked'); draw(); big.classList.remove('pop'); void big.offsetWidth; big.classList.add('pop'); });
        };
        g.append(c);
      }
      box.append(g);
      const a = h('div', 'acts'), ok = h('button', 'btn small', 'DONE'); ok.onclick = () => { tap(); this.closeSheet(); this.hub(this.tab, true); }; a.append(ok); box.append(a);
    });
  }
  sheet(fill) { this.closeSheet(); const S = this.sheetEl = h('div', 'sheet'); const box = h('div', 'panel box'); fill(box); S.append(box); S.onclick = e => { if (e.target === S) this.closeSheet(); }; this.ui.append(S); audio.play('ui_swoosh'); }
  closeSheet() { this.sheetEl?.remove(); this.sheetEl = null; if (this.stale && !this.overlaid()) { this.stale = false; this.onProfile(); } }   // catch up on what changed under it

  // ================= THE TROPHY ROAD (CR's arena scroll) =================
  // the whole climb on one vertical road: arena 10 at the top, arena 1 at the bottom, each arena a diorama
  // (assets/arenas/<id>/diorama.webp, tools/ui/diorama.js) with the cards it unlocks, the rewards between them, and my
  // Clout climbing the rail on the left. It's the ROAD tab (the hub's arena and ROAD button switch to it); openRoad() builds
  // an overlay of it with OK, which nothing opens any more.
  road(page) {
    const p = save.p;
    page.classList.add('roadpage');
    page.append(h('h2', 'stroke-s', `TROPHY ROAD <small><img src="assets/ui/sm/icon_clout.webp" style="width:16px;vertical-align:-3px"> ${fmt(p.clout)} · best ${fmt(p.best)}</small>`));
    const T = this.track('tab'); page.append(T);
    const st = p.stats; page.append(h('div', 'panel stats', `<div><b>${st.wins}</b>WINS</div><div><b>${st.losses}</b>LOSSES</div><div><b>${st.ws}</b>Ws TAKEN</div>`)); page.lastChild.style.cssText = 'margin-top:12px;padding:12px 6px;font-family:var(--disp)';
    const keep = this.keepScroll;
    requestAnimationFrame(() => { const y = T.place(); if (!keep) this.glide(page, T, y); });
  }
  openRoad(focus) {
    this.closeRoad(true);
    const O = this.roadEl = h('div', 'roadview');
    const head = h('div', 'rv-head'), x = h('button', 'rv-x');
    head.innerHTML = `<b class="stroke">TROPHY ROAD</b><span class="pill"><img src="assets/ui/sm/icon_clout.webp" alt=""><span class="num">${fmt(save.p.clout)}</span></span>`;
    x.innerHTML = '<img src="assets/ui/sm/icon_close.webp" alt="close">'; x.onclick = () => this.closeRoad(); head.append(x);
    const S = h('div', 'rv-scroll'), foot = h('div', 'rv-foot'), ok = h('button', 'btn rv-ok', 'OK');
    ok.onclick = () => this.closeRoad(); foot.append(ok);
    O.append(head, S, foot); this.ui.append(O);
    this.fillRoad(false, focus);
    audio.play('ui_swoosh');
  }
  closeRoad(quiet) {
    if (!this.roadEl) return;
    this.roadEl.remove(); this.roadEl = null;
    if (!quiet) { tap(); if (!this.app.match) audio.music('mus_menu'); }
  }
  // (re)draw the overlay's road; a redraw after a claim keeps the scroll, a fresh open glides up to my spot
  fillRoad(keep, focus, at) {
    const S = this.roadEl?.querySelector('.rv-scroll'); if (!S) return;
    const top = at ?? S.scrollTop, T = this.track('overlay'); if (S.firstChild !== T || S.childNodes.length > 1) S.replaceChildren(T);
    { const n = this.roadEl.querySelector('.rv-head .num'); if (n) n.textContent = fmt(save.p.clout); }
    requestAnimationFrame(() => {
      let y = T.place(); if (keep) { S.scrollTop = top; return; }
      // opened from another arena on the hub: glide to that arena instead of to my marker
      const F = focus && focus !== save.arena.id && T.querySelector(`.rv-arena[data-id="${focus}"] .rv-plate`);
      if (F) { const tr = T.getBoundingClientRect(), r = F.getBoundingClientRect(); y = (r.top + r.height / 2 - tr.top) * (T.offsetHeight / (tr.height || 1)); }
      this.glide(S, T, y);
    });
  }
  // the road's track, built once per place (the ROAD tab, the overlay) and moved into each redraw while nothing on it
  // changed: a profile push (an action, a reconnect) redraws the open page, and a rebuilt track loaded and decoded all its
  // pictures again, popping in as they came
  track(where) {
    const p = save.p, sig = [p.clout, p.best, p.road.join(), save.avatar, save.roadClaimable().join()].join('|');
    const k = 'track_' + where;
    if (this[k]?.sig !== sig) { this[k] = this.roadTrack(); this[k].sig = sig; keepIn(this[k]); }
    return this[k];
  }
  roadTrack() {
    const p = save.p, cur = save.arena, claim = new Set(save.roadClaimable()), last = ROAD[ROAD.length - 1].at;
    const T = h('div', 'rv-track'), rail = h('div', 'rv-rail'), fill = h('i', 'rv-fill'), you = h('div', 'rv-you');
    rail.append(fill); T.append(rail);
    for (let i = ARENAS.length - 1; i >= 0; i--) {
      const A = ARENAS[i], next = ARENAS[i + 1];
      // the rewards from this arena's door up to the next one's (the one at the door comes with arriving)
      for (const r of [...ROAD].reverse()) if (r.at >= A.at && (next ? r.at < next.at : r.at <= last)) T.append(this.roadTile(r, p, claim));
      T.append(this.roadArena(A, p, cur));
    }
    you.innerHTML = `<div class="ava"><img src="${avatarArt(save.avatar)}" alt=""></div><span class="num">${fmt(p.clout)}</span>`;
    T.append(you);
    // once laid out: a number on the rail at every stop, the rail filled up to my Clout, my marker riding it; returns
    // my marker's y in the track (track-local px, so a zoomed PC column measures right)
    T.place = () => {
      const tr = T.getBoundingClientRect(), k = T.offsetHeight / (tr.height || 1);
      const stops = [...T.querySelectorAll('.rv-stop')].map(e => { const r = e.getBoundingClientRect(); return {at: +e.dataset.at, y: (r.top + r.height / 2 - tr.top) * k}; });
      rail.querySelectorAll('.rv-at').forEach(e => e.remove());
      for (const s of stops) { const n = h('span', 'rv-at num' + (p.clout >= s.at ? ' on' : ''), fmt(s.at)); n.style.top = s.y + 'px'; rail.append(n); }
      let y = stops.length ? stops[stops.length - 1].y : 0;
      if (stops.length && p.clout >= stops[0].at) y = stops[0].y;
      else for (let i = 0; i < stops.length - 1; i++) {
        const a = stops[i], b = stops[i + 1];
        if (p.clout <= a.at && p.clout >= b.at) { y = a.at === b.at ? a.y : b.y + (a.y - b.y) * (p.clout - b.at) / (a.at - b.at); break; }
      }
      fill.style.height = Math.max(0, T.offsetHeight - y) + 'px'; you.style.top = y + 'px';
      return y;
    };
    return T;
  }
  roadTile(r, p, claim) {
    const got = p.road.includes(r.at), can = claim.has(r.at), g = r.gives, reached = p.best >= r.at;
    const n = h('div', 'rv-row rv-tile panel rv-stop' + (got ? ' got' : can ? ' can' : reached ? '' : ' locked') + (g.bag ? ' big' : ''));
    n.dataset.at = r.at;
    const what = g.bag ? `<img src="assets/ui/sm/icon_bag_${g.bag}.webp" alt=""><b>${(BAG[g.bag]?.name || g.bag + ' bag').toUpperCase()}</b>`
      : g.gems ? `${GEM}<b class="num">${g.gems}</b><span>GEMS</span>` : `${COIN}<b class="num">${fmt(g.coins)}</b><span>COINS</span>`;
    n.innerHTML = `<div class="rv-gift">${what}</div>${got ? '<img class="rv-ok" src="assets/ui/sm/icon_check.webp" alt="claimed">' : can ? '<span class="btn small yellow rv-claim">CLAIM</span>' : reached ? '' : '<img class="rv-lock" src="assets/ui/sm/icon_lock.webp" alt="">'}`;
    if (can) n.onclick = e => { e.stopPropagation(); tap(); this.run({a: 'claimRoad', at: r.at}, res => { audio.play('reward_claim'); if (res.got?.bag) this.openRoll(res.got.bag); else if (this.roadEl) this.fillRoad(true); else this.hub('road', true); }); };
    return n;
  }
  roadArena(A, p, cur) {
    const reached = p.best >= A.at, here = A.id === cur.id;
    const R = h('div', 'rv-row rv-arena' + (here ? ' here' : '') + (reached ? '' : ' locked')); R.dataset.id = A.id;
    R.innerHTML = `<div class="rv-dio"><img src="${dioramaOf(A, !reached)}" decoding="async" alt="""" onerror="this.onerror=null;this.src='assets/arenas/${A.id}/badge.webp'">${reached ? '' : '<img class="rv-lock" src="assets/ui/sm/icon_lock.webp" alt="locked">'}${here ? '<div class="rv-here">YOU ARE HERE</div>' : ''}</div>
      <div class="rv-plate panel rv-stop" data-at="${A.at}">${arenaBadge(A)}<div><span class="an">ARENA ${A.n}</span><b class="stroke-s">${A.name}</b></div><span class="need"><img src="assets/ui/sm/icon_clout.webp" alt="">${fmt(A.at)}</span></div>
      <div class="rv-unl"><span>${A.unlock.length ? 'UNLOCKS' : 'A PRESTIGE ARENA'}</span><div></div></div>`;
    const un = R.querySelector('.rv-unl div');
    for (const id of A.unlock) { const c = cardEl(id, {cost: false, name: false}); c.onclick = e => { e.stopPropagation(); tap(); this.cardSheet(id, true); }; un.append(c); }
    return R;
  }
  // CR opens the road a little below my spot and glides up to it; a touch or the wheel takes over
  glide(S, T, y) {
    const sr = S.getBoundingClientRect(), tr = T.getBoundingClientRect(), k = S.clientHeight / (sr.height || 1);
    const max = S.scrollHeight - S.clientHeight, target = Math.max(0, Math.min(max, (tr.top - sr.top) * k + S.scrollTop + y - S.clientHeight * 0.55));
    const from = Math.min(max, target + 640);
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || from <= target) { S.scrollTop = target; return; }
    S.scrollTop = from;
    let stop = false; const halt = () => { stop = true; };
    S.addEventListener('pointerdown', halt, {once: true}); S.addEventListener('wheel', halt, {once: true, passive: true});
    const t0 = performance.now(), step = t => { if (stop || !S.isConnected) return; const q = Math.min(1, (t - t0) / 1100), e = 1 - Math.pow(1 - q, 3); S.scrollTop = from + (target - from) * e; if (q < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }

  // ================= SHOP =================
  shop(page) {
    save.refresh(); const p = save.p, now = Date.now();
    page.classList.add('shoppage');
    this.app.net?.pendingRow?.(page, this);
    const sec = (title, sub) => { page.append(h('h2', 'stroke-s', `${title}${sub ? ` <small>${sub}</small>` : ''}`)); };
    const midnight = () => { const d = new Date(); d.setUTCHours(24, 0, 0, 0); return dur((d - Date.now()) / 1000); };
    // SPECIAL OFFERS
    const offers = [];
    const pack = save.arenaPack(); if (pack) { const A = arenaById(pack.arena); offers.push({kind: 'arena', id: pack.arena, art: 'offer_arena', title: `ARENA ${A.n} PACK`, arena: A, usd: pack.usd, gives: SHOP.arenaPack.gives, until: pack.until}); }
    for (const O of OFFERS) if (!(O.once && p.offers[O.id])) offers.push({kind: 'offer', id: O.id, art: O.id === 'starter' ? 'offer_starter' : 'offer_whale', title: O.label, usd: O.usd, gives: O.gives, rarity: O.rarity});
    if (offers.length) {
      sec('SPECIAL OFFERS', offers.length > 1 ? 'swipe for more ›' : `real money · ${this.app.net?.payWord || 'Solana wallet'}`);
      const orow = h('div', 'hrow offers'); page.append(orow);
      for (const o of offers) {
        const E = h('div', 'panel offer-wide' + (o.rarity === 'legendary' ? ' legend' : ''));
        E.style.backgroundImage = `linear-gradient(90deg, rgba(20,10,48,.75), rgba(20,10,48,.2)), url(assets/ui/shop/${o.art}.webp)`;   // (the full picture: the 240 px thumb blurs this wide)
        const g = o.gives, items = [g.card ? `${cardEl(g.card[0], {cost: false}).outerHTML}` : '', g.gems ? `<span>${GEM} ${fmt(g.gems)}</span>` : '', g.coins ? `<span>${COIN} ${fmt(g.coins)}</span>` : '', g.bag ? `<span><img class="ico" src="assets/ui/sm/icon_bag_${g.bag}.webp" alt=""> ${BAG[g.bag].name}</span>` : ''].join('');
        E.innerHTML = `<div class="ot stroke">${o.title}</div><div class="oi">${items}</div>${o.until ? `<div class="otime">ends in ${dur((o.until - now) / 1000)}</div>` : ''}<i class="oinfo">i</i>`;
        const b = h('button', 'btn yellow small', usd(o.usd)); b.onclick = e => { e.stopPropagation(); this.buy(o.kind, o.id, o.title, o.usd); }; E.append(b);
        E.onclick = () => { tap(); this.offerSheet(o); };
        orow.append(E);
      }
    }
    // FREE + DAILY DEALS
    sec('DAILY DEALS', `new deals in ${midnight()}`);
    const grid = h('div', 'deals');
    const fg = save.freeGift(), free = h('div', 'panel deal free' + (p.shop.free ? ' sold' : ''));
    free.innerHTML = `<img class="dimg" src="assets/ui/sm/shop/free_gift.webp" onerror="this.src='assets/ui/sm/icon_bag_common.webp'" alt=""><div class="dn stroke-s">${fg.coins ? fmt(fg.coins) + ' COINS' : fg.gems ? fg.gems + ' GEMS' : fg.n + ' CARDS'}</div>`;
    const fb = h('button', 'btn small', p.shop.free ? 'CLAIMED' : 'FREE'); if (p.shop.free) fb.disabled = true;
    fb.onclick = () => this.run({a: 'claimFree'}, () => { audio.play('reward_claim'); this.hub('shop', true); }); free.append(fb); grid.append(free);
    for (const D of p.shop.deals) {
      const sold = p.shop.bought.includes(D.slot), c = CARDS[D.id], E = h('div', 'panel deal ' + c.rarity + (sold ? ' sold' : ''));
      const ce = cardEl(D.id, {name: false}); ce.classList.add('dcard'); E.append(ce);
      E.append(h('div', 'dn stroke-s', `${c.name} <b>x${D.n}</b>`));
      const b = h('button', 'btn yellow small'); b.innerHTML = sold ? 'SOLD' : `${COIN} ${fmt(D.coins)}`; if (sold || p.coins < D.coins) b.disabled = true;
      b.onclick = () => this.run({a: 'buyDeal', slot: D.slot}, () => { audio.play('card_reveal'); this.hub('shop', true); });
      E.append(b); grid.append(E);
    }
    page.append(grid);
    // BAGS for gems
    sec('BAGS', 'open them right away');
    const bags = h('div', 'hrow tiles');
    for (const B of SHOP.bags) {
      const E = h('div', 'panel offer'); E.innerHTML = `<img src="assets/ui/sm/icon_bag_${B.tier}.webp" alt=""><div class="t stroke-s">${BAG[B.tier].name.toUpperCase()}</div><div class="prog-t">${BAG[B.tier].cards} cards</div>`;
      const b = h('button', 'btn purple small'); b.innerHTML = `${GEM} ${B.gems}`; if (p.gems < B.gems) b.disabled = true;
      b.onclick = () => this.run({a: 'buyBag', tier: B.tier}, r => { audio.play('gem_buy'); this.openRoll(r.bag); });
      E.append(b); bags.append(E);
    }
    page.append(bags);
    // GEMS for real money
    sec('GEMS', `swipe ›  ·  ${this.app.net?.payWord || 'Solana wallet'}`);
    const gems = h('div', 'hrow tiles');
    for (const G of GEM_PACKS) {
      const E = h('div', 'panel offer gemoffer'); E.innerHTML = `${G.tag ? `<div class="otag">${G.tag}</div>` : ''}<img src="assets/ui/sm/shop/${G.id}.webp" onerror="this.src='assets/ui/sm/icon_gem.webp'" alt=""><div class="t stroke-s">${fmt(G.gems)} GEMS</div><div class="prog-t">${G.label}</div>`;
      const b = h('button', 'btn yellow small', usd(G.usd)); b.onclick = () => this.buy('gems', G.id, `${fmt(G.gems)} GEMS`, G.usd); E.append(b); gems.append(E);
    }
    page.append(gems);
    // COINS for gems
    sec('COINS');
    const coins = h('div', 'hrow tiles');
    for (const C of SHOP.coinPacks) {
      const E = h('div', 'panel offer'); E.innerHTML = `<img src="assets/ui/sm/shop/${C.id}.webp" onerror="this.src='assets/ui/sm/icon_cash.webp'" alt=""><div class="t stroke-s">${fmt(C.coins)}</div>`;
      const b = h('button', 'btn purple small'); b.innerHTML = `${GEM} ${fmt(C.gems)}`; if (p.gems < C.gems) b.disabled = true;
      b.onclick = () => this.run({a: 'buyCoins', id: C.id}, () => { audio.play('coins'); this.hub('shop', true); });
      E.append(b); coins.append(E);
    }
    page.append(coins);
    // COSMETICS
    sec('COSMETICS');
    const cos = h('div', 'hrow tiles');
    for (const C of SHOP.cosmetics) {
      const own = p.cosmetics.own.includes(C.id), E = h('div', 'panel offer' + (own ? ' sold' : ''));
      E.innerHTML = `<img src="assets/ui/sm/shop/${C.kind === 'tower' ? 'skin_gold' : 'emote_pack'}.webp" onerror="this.src='assets/ui/sm/icon_emote.webp'" alt=""><div class="t stroke-s">${C.label}</div>`;
      const b = h('button', 'btn purple small'); b.innerHTML = own ? 'OWNED' : `${GEM} ${fmt(C.gems)}`; if (own || p.gems < C.gems) b.disabled = true;
      b.onclick = () => this.run({a: 'buyCosmetic', id: C.id}, () => { audio.play('gem_buy'); this.hub('shop', true); });
      E.append(b); cos.append(E);
    }
    page.append(cos);
    page.append(h('p', '', '<span style="opacity:.6;font-size:12px">Gems and offers are bought with a Solana wallet in the online game. Coins, deals and bags are earned by playing.</span>'));
  }
  // a special offer, opened (a tap on it): its picture, what it is, then everything it gives, one row each, and its price
  offerSheet(o) {
    const g = o.gives, rows = [], row = (pic, big, small) => rows.push(`<div class="orow">${pic}<div><b class="stroke-s">${big}</b><small>${small}</small></div></div>`);
    if (g.card) { const [id, n] = g.card, c = CARDS[id]; row(cardEl(id, {cost: false, name: false}).outerHTML, `${c.name.toUpperCase()}${n > 1 ? ` x${n}` : ''}`, `${RARITY[c.rarity].name} card${save.p.cards[id] ? '' : ' · new for you'}`); }
    if (g.gems) row('<img src="assets/ui/sm/icon_gem.webp" alt="">', `${fmt(g.gems)} GEMS`, 'Open bags now, buy bags and coins');
    if (g.coins) row('<img src="assets/ui/sm/icon_cash.webp" alt="">', `${fmt(g.coins)} COINS`, 'Upgrade your cards, buy daily deals');
    if (g.bag) {
      const T = BAG[g.bag], R = ['rare', 'epic', 'legendary'], sure = R.filter(r => T[r] >= 1).map(r => `${T[r]}+ ${RARITY[r].name}`), maybe = R.filter(r => T[r] > 0 && T[r] < 1).map(r => RARITY[r].name);
      row(`<img src="assets/ui/sm/icon_bag_${g.bag}.webp" alt="">`, T.name.toUpperCase(), [`${T.cards} cards`, `${T.cash[0]}–${T.cash[1]} coins`, ...sure, ...(maybe.length ? [`a chance of ${maybe.join(' or ')}`] : []), 'opens right away'].join(' · '));
    }
    const about = o.arena ? `For reaching Arena ${o.arena.n}: ${o.arena.name}. One time only, for a day.` : o.id === 'starter' ? 'A head start, once per player.' : g.card ? `Skip the bags: ${CARDS[g.card[0]].name} is yours right away.` : '';
    this.sheet(box => {
      box.classList.add('offer-sheet');
      box.innerHTML = `<div class="oban" style="background-image:url(assets/ui/shop/${o.art}.webp)"><h3 class="stroke">${o.title}</h3>${o.until ? `<div class="otime">ends in ${dur((o.until - Date.now()) / 1000)}</div>` : ''}</div>${about ? `<p>${about}</p>` : ''}<div class="olist"><h4 class="stroke-s">YOU GET</h4>${rows.join('')}</div>`;
      const a = h('div', 'acts'), x = h('button', 'btn small dark', 'CLOSE'), b = h('button', 'btn yellow small', usd(o.usd));
      x.onclick = () => { tap(); this.closeSheet(); }; b.onclick = () => this.buy(o.kind, o.id, o.title, o.usd);
      a.append(x, b); box.append(a);
    });
  }
  // real money: only online, through the wallet (src/net/wallet.js via app.net)
  buy(kind, id, title, price) {
    tap();
    if (this.app.net?.buy) return this.app.net.buy(kind, id, {title, usd: price, menus: this});
    this.sheet(box => {
      box.innerHTML = `<div style="display:grid;justify-items:center;gap:8px;text-align:center"><img src="assets/ui/sm/icon_gem.webp" style="width:96px" alt=""><h3 class="stroke-s">${title}</h3><p>${usd(price)} · real-money items are sold in the online game, paid with a Solana wallet (Phantom, Solflare or Backpack). Connect to the game server to buy.</p></div>`;
      const a = h('div', 'acts'), ok = h('button', 'btn small dark', 'OK'); ok.onclick = () => { tap(); this.closeSheet(); }; a.append(ok); box.append(a);
    });
  }

  // ================= MORE (settings) =================
  settings(page) {
    const p = save.p;
    page.append(h('h2', 'stroke-s', 'SETTINGS'));
    const L = h('div', 'lg-list'); page.append(L);
    const row = (label, el) => { const r = h('div', 'panel set-row'); r.append(h('span', 'stroke-s', label), el); L.append(r); };
    const nm = h('button', 'btn small dark', p.name); nm.onclick = () => { const v = prompt('Your name (3-14 characters)', p.name); if (v) this.run({a: 'setName', name: v.trim()}, () => this.hub('settings')); };
    row('NAME', nm);
    const vol = k => { const s = h('div', 'seg3'); for (const [lab, v] of [['OFF', 0], ['LOW', 0.4], ['ON', k === 'music' ? 0.7 : 1]]) { const b = h('button', Math.abs(audio.vol[k] - v) < 0.05 ? 'on' : '', lab); b.onclick = () => { audio.setVol(k, v); tap(); this.hub('settings'); }; s.append(b); } return s; };
    row('MUSIC', vol('music')); row('SOUND', vol('sfx'));
    const gfx = h('div', 'seg3'); for (const q of ['low', 'mid', 'high']) { const b = h('button', (this.app.stage?.quality || (() => { try { return localStorage.getItem('memeroyale.gfx'); } catch { return null; } })()) === q ? 'on' : '', q.toUpperCase()); b.onclick = () => { try { localStorage.setItem('memeroyale.gfx', q); } catch {} location.reload(); }; gfx.append(b); }
    row('GRAPHICS', gfx);
    const net = this.app.net;
    if (net?.online) {
      if (p.account) {
        const a = h('div', 'seg3'), pw = h('button', '', 'PASSWORD'), out = h('button', '', 'LOG OUT');
        pw.onclick = () => { tap(); this.passSheet(); };
        out.onclick = () => { tap(); this.logout(); };
        a.append(pw, out); row('ACCOUNT', a);
      } else {
        const a = h('div', 'seg3'), mk = h('button', 'on', 'CREATE'), li = h('button', '', 'LOG IN');
        mk.onclick = () => { tap(); this.account({mode: 'create'}); }; li.onclick = () => { tap(); this.account({mode: 'login'}); };
        a.append(mk, li); row('ACCOUNT', a);
      }
    }
    if (net?.walletRow) row('WALLET', net.walletRow(this));
    row('ONLINE', h('span', 'prog-t', this.app.net?.online ? 'connected' : 'offline (bots only)'));
    if (!save.remote) { const rs = h('button', 'btn small red', 'RESET'); rs.onclick = () => { if (confirm('Wipe your profile, cards and Clout on this device?')) { localStorage.removeItem('memeroyale.save'); location.reload(); } }; row('PROGRESS', rs); }
    const st = p.stats; page.append(h('div', 'panel stats', `<div><b>${st.wins}</b>WINS</div><div><b>${st.losses}</b>LOSSES</div><div><b>${st.played}</b>BATTLES</div>`)); page.lastChild.style.cssText = 'margin-top:12px;padding:12px 6px;font-family:var(--disp)';
    page.append(h('div', '', `<p style="font-size:12px;opacity:.6;line-height:1.5;margin:14px 6px">MEME ROYALE. Sound, music and voices: ElevenLabs. Interface and card art: GPT Image. Props: Poly Haven (CC0) and our own. Engine: three.js.</p>`));
  }

  // ================= SOCIAL: the leaderboard (the online accounts by Clout) and friendly battles =================
  social(page) {
    const net = this.app.net, p = save.p;
    page.append(h('h2', 'stroke-s', 'SOCIAL'));
    if (net?.online) {
      const fr = h('div', 'panel set-row'); fr.append(h('span', 'stroke-s', 'FRIENDLY BATTLE'), net.friendRow(this)); page.append(fr);
      if (!p.account) {
        const cta = h('div', 'panel acct-cta'); cta.innerHTML = '<b class="stroke-s">GET ON THE LEADERBOARD</b><span class="prog-t">Make an account: your name, your Clout, on every device.</span>';
        const b = h('button', 'btn small', 'CREATE ACCOUNT'); b.onclick = () => { tap(); this.account({mode: 'create'}); }; cta.append(b); page.append(cta);
      }
    }
    const head = h('div', 'lb-head'); head.innerHTML = '<h3 class="stroke-s">TOP 100</h3>'; page.append(head);
    const list = h('div', 'lb-list'); page.append(list);
    if (!net?.online) { list.append(h('div', 'panel plain lb-empty', 'The leaderboard lives on the game server. Play online to climb it.')); return; }
    const sub = h('span', 'prog-t', ''); head.append(sub);
    list.append(h('div', 'spin'));
    const row = (x, me) => {
      const A = arenaById(x.arena), R = h('div', 'panel lb-row' + (me ? ' me' : '') + (x.rank <= 3 ? ' top' + x.rank : ''));
      const rk = h('div', 'rk');
      if (x.rank <= 3) { const m = h('img'); m.alt = String(x.rank); m.onerror = () => { rk.textContent = x.rank; }; m.src = `assets/ui/sm/rank_${x.rank}.webp`; rk.append(m); } else rk.textContent = x.rank;
      const who = h('div', 'who'), nm = h('b', 'stroke-s'); nm.textContent = x.name;
      who.append(nm, h('span', 'prog-t', `LV ${x.level | 0} · ${A.name.toUpperCase()}`));
      // their profile picture with their arena's badge on its corner
      const av = h('div', 'ab'), pic = h('img', 'av'); pic.alt = ''; pic.src = avatarArt(x.avatar); pic.onerror = () => { pic.onerror = null; pic.src = avatarArt('troll'); };
      av.append(pic, h('i', 'mini', arenaBadge(A)));
      R.append(rk, av, who, h('div', 'cl num', `<img src="assets/ui/sm/icon_clout.webp" alt="">${fmt(x.clout)}`));
      return R;
    };
    net.client.top().then(r => {
      if (!list.isConnected) return;
      list.replaceChildren();
      if (!r?.ok) { list.append(h('div', 'panel plain lb-empty', r?.why || 'The leaderboard did not load.')); return; }
      sub.textContent = `${fmt(r.of)} player${r.of === 1 ? '' : 's'}`;
      if (!r.rows.length) list.append(h('div', 'panel plain lb-empty', 'Nobody yet. Make an account and be the first.'));
      for (const x of r.rows) list.append(row(x, r.me && r.me.rank === x.rank));
      if (r.me && r.me.rank > r.rows.length) { list.append(h('div', 'lb-gap', '• • •'), row(r.me, true)); }
      const meEl = list.querySelector('.me'); if (meEl && r.me.rank > 4) requestAnimationFrame(() => meEl.scrollIntoView({block: 'center'}));
    });
  }

  // ================= ACCOUNT (online): a unique name and a password; the leaderboard ranks the accounts =================
  // required: the first launch, no way around it (resolves once the page has an account)
  account({mode = 'create', required = false} = {}) {
    const net = this.app.net; if (!net?.online) { this.toast('Accounts are made on the game server.'); return Promise.resolve(false); }
    this.accountEl?.remove();
    return new Promise(done => {
      const O = this.accountEl = h('div', 'acct-gate' + (required ? ' req' : ''));
      const finish = ok => { O.classList.add('out'); setTimeout(() => O.remove(), 350); if (this.accountEl === O) this.accountEl = null; done(ok); };
      const draw = () => {
        O.replaceChildren();
        const logo = h('img', 'acct-logo'); logo.src = 'assets/ui/logo.webp?v=4'; logo.alt = 'MEME ROYALE';
        const box = h('form', 'panel acct-box'); box.noValidate = true;
        const c = mode === 'create';
        box.append(h('h3', 'stroke-s', c ? 'CREATE YOUR ACCOUNT' : 'LOG IN'),
          h('p', 'prog-t', c ? 'Your name on the leaderboard. Your cards, Clout and gems stay with it on any device.' : 'The name and password of your account.'));
        const field = (ph, type, ac, max) => { const i = h('input'); i.type = type; i.placeholder = ph; i.autocomplete = ac; i.maxLength = max; i.autocapitalize = 'off'; i.spellcheck = false; box.append(i); return i; };
        const nm = field('NAME (3-14)', 'text', 'username', 14), pw = field('PASSWORD (6+)', 'password', c ? 'new-password' : 'current-password', 64);
        let pw2 = null; if (c) pw2 = field('PASSWORD AGAIN', 'password', 'new-password', 64);
        if (c && /^[A-Za-z0-9_.\- ]{3,14}$/.test(save.p.name)) nm.value = save.p.name;
        const err = h('div', 'acct-err'); box.append(err);
        const go = h('button', 'btn', c ? 'CREATE' : 'LOG IN'); go.type = 'submit'; box.append(go);
        const sw = h('button', 'acct-switch', c ? 'Have an account? <b>LOG IN</b>' : 'New here? <b>CREATE AN ACCOUNT</b>'); sw.type = 'button';
        sw.onclick = () => { tap(); mode = c ? 'login' : 'create'; draw(); };
        box.append(sw);
        if (!required) { const x = h('button', 'acct-x'); x.type = 'button'; x.innerHTML = '<img src="assets/ui/sm/icon_close.webp" alt="close">'; x.onclick = () => { tap(); finish(false); }; box.append(x); }
        box.onsubmit = async e => {
          e.preventDefault(); if (go.disabled) return;
          const name = nm.value.replace(/\s+/g, ' ').trim(), pass = pw.value;
          if (name.length < 3) { err.textContent = 'A name of 3 to 14 characters, please.'; nm.focus(); return; }
          if (pass.length < 6) { err.textContent = 'A password of 6 characters or more, please.'; pw.focus(); return; }
          if (c && pw2.value !== pass) { err.textContent = 'The two passwords are not the same.'; pw2.focus(); return; }
          go.disabled = true; err.textContent = ''; go.innerHTML = '<span class="spin sm"></span>';
          const r = c ? await net.client.account.create(name, pass) : await net.client.account.login(name, pass);
          go.disabled = false; go.textContent = c ? 'CREATE' : 'LOG IN';
          if (!r?.ok) { err.textContent = r?.why || 'That did not work. Try again.'; audio.play('card_deny'); return; }
          document.activeElement?.blur?.();
          if (!c) { if (!r.you) { err.textContent = 'Logged in, but the server did not answer. Reload the page.'; return; } await this.switched(r.you); }
          audio.play(audio.has('w_fanfare') ? 'w_fanfare' : 'ui_pop'); finish(true);
          this.toast(c ? `Welcome to MEME ROYALE, ${r.name}!` : `Welcome back, ${r.name}!`);
        };
        O.append(logo, box);
        if (!('ontouchstart' in window)) setTimeout(() => (nm.value ? pw : nm).focus(), 60);
      };
      draw(); this.ui.append(O); audio.play('ui_swoosh');
    });
  }
  // another identity on this page (a login, a logout): its profile, its arena, its deck
  async switched(you) {
    const net = this.app.net; net.you = you; net.pay = you.pay || net.pay; net.W = null;
    save.setProfile(you.p);
    this.hub('battle'); this.app.setupHub();
  }
  passSheet() {
    const net = this.app.net;
    this.sheet(box => {
      const f = h('form', 'acct-pass'); f.noValidate = true;
      f.append(h('h3', 'stroke-s', 'CHANGE PASSWORD'));
      const old = h('input'); old.type = 'password'; old.placeholder = 'OLD PASSWORD'; old.autocomplete = 'current-password';
      const nw = h('input'); nw.type = 'password'; nw.placeholder = 'NEW PASSWORD (6+)'; nw.autocomplete = 'new-password'; nw.maxLength = 64;
      const err = h('div', 'acct-err'), a = h('div', 'acts'), ok = h('button', 'btn small', 'SAVE'), no = h('button', 'btn small dark', 'CANCEL');
      ok.type = 'submit'; no.type = 'button'; no.onclick = () => this.closeSheet();
      f.onsubmit = async e => {
        e.preventDefault(); if (nw.value.length < 6) { err.textContent = 'A password of 6 characters or more, please.'; return; }
        const r = await net.client.account.changePass(old.value, nw.value);
        if (!r?.ok) { err.textContent = r?.why || 'Not changed.'; return; }
        this.closeSheet(); this.toast('Password changed.');
      };
      a.append(no, ok); f.append(old, nw, err, a); box.append(f);
    });
  }
  logout() {
    const net = this.app.net;
    this.sheet(box => {
      box.innerHTML = `<div style="text-align:center;display:grid;gap:8px"><h3 class="stroke-s">LOG OUT?</h3><p>Your account stays on the server: log in with its name and password to play it again.</p></div>`;
      const a = h('div', 'acts'), no = h('button', 'btn small dark', 'CANCEL'), ok = h('button', 'btn small red', 'LOG OUT');
      no.onclick = () => this.closeSheet();
      ok.onclick = async () => {
        ok.disabled = true; const r = await net.client.account.logout(); this.closeSheet();
        if (!r?.ok) { this.toast(r?.why || 'Not now.'); return; }
        if (r.you) await this.switched(r.you);
        await this.account({mode: 'login', required: true});
      };
      a.append(no, ok); box.append(a);
    });
  }

  // ================= THE MATCHUP =================
  // CR's battle intro: the opponent slides in from the top, me from the bottom, VS slams between us
  // ================= BEFORE A BATTLE (the genre's order): the search over my arena's diorama, with a tip and CANCEL; then
  // the loading screen, the title's key art with the same tip and a percent; then the arena itself (src/ui/hud.js intro)
  finding(onCancel) {
    const id = this.localArena(), A = id ? arenaById(id) : save.arena, M = h('div', 'prebattle find'), C = h('div', 'pb-col');
    this.tip = TIPS[Math.floor(Math.random() * TIPS.length)];
    C.innerHTML = `<div class="find-head"><svg class="mag" viewBox="0 0 64 64" aria-hidden="true"><path d="M41 41l16 16" stroke="#140A30" stroke-width="14" stroke-linecap="round"/><path d="M41 41l15 15" stroke="#d9952e" stroke-width="7" stroke-linecap="round"/><circle cx="26" cy="26" r="19" fill="#bfe8ff" stroke="#140A30" stroke-width="6"/><path d="M15 23a12 12 0 0 1 9-9" stroke="#fff" stroke-width="4.5" stroke-linecap="round" fill="none"/></svg><b class="stroke">SEARCHING<br>FOR OPPONENT<i class="dots"></i></b></div>
      <div class="find-arena"><img src="${dioramaOf(A)}" alt=""></div><div class="find-name stroke-s"><small>ARENA ${A.n}</small>${A.name}</div>`;
    const c = h('button', 'btn red', 'CANCEL'); c.onclick = () => { tap(); onCancel(); };
    C.append(c, this.tipEl()); M.append(C); return M;
  }
  tipEl() { const t = h('div', 'panel tip', '<b class="disp">TIP</b><span></span>'); t.lastChild.textContent = this.tip || TIPS[0]; return t; }
  loading() {
    const M = h('div', 'prebattle load'), pct = h('b', 'pct stroke', '0%'), foot = h('div', 'load-foot');
    M.innerHTML = '<img class="load-logo" src="assets/ui/logo.webp?v=4" alt="" onerror="this.remove()">';
    foot.append(this.tipEl(), pct); M.append(foot);
    // (the number runs up to what is done, never back)
    let shown = 0, want = 0;
    const run = () => { if (shown >= 100 || (!M.isConnected && shown > 0)) return; shown = Math.min(want, shown + Math.max(0.6, (want - shown) * 0.16)); pct.textContent = Math.floor(shown) + '%'; requestAnimationFrame(run); };
    requestAnimationFrame(run);
    return {el: M, set: v => { want = Math.max(want, Math.min(100, v)); }};
  }

  // ================= RESULTS =================
  results(match, win, res) {
    clearInterval(this.timer);
    const B = match.b, R = h('div', 'results');
    const rib = h('div', 'ribbon' + (win === -1 ? ' draw' : '')); rib.style.backgroundImage = `url(assets/ui/ribbon_${win === 0 ? 'red' : 'green'}.webp)`;
    rib.innerHTML = `<span class="stroke">${win === 1 ? 'VICTORY' : win === 0 ? 'DEFEAT' : 'DRAW'}</span>`;
    const sc = h('div', 'score');
    // the Ws pop in one at a time (mine, then theirs), CR's crowns; the winner gets the WINNER! tag
    let k = 0; const pops = [];
    const side = (ws, icon, won) => { const S = h('div', 'side' + (won ? ' won' : '')), W = h('div', 'ws');
      for (let i = 0; i < 3; i++) { const im = h('img', i < ws ? 'on' : 'off'); im.src = `assets/ui/sm/icon_w_${icon}.webp`; im.alt = ''; if (i < ws) { im.style.animationDelay = (0.75 + k * 0.28).toFixed(2) + 's'; pops.push(0.75 + k++ * 0.28); } W.append(im); }
      const n = h('div', 'n stroke-s'); S.append(W, n); if (won) S.append(h('div', 'win-tag disp', 'WINNER!')); return [S, n]; };
    const [mine, mn] = side(B.ws[0], 'bull', win === 1), [theirs, tn] = side(B.ws[1], 'bear', win === 0);
    mn.textContent = save.p.name; tn.textContent = match.opp.name;
    sc.append(mine, h('div', 'vs stroke-s', 'VS'), theirs);
    for (const t of pops) setTimeout(() => { if (R.isConnected) audio.play(audio.has('ui_pop') ? 'ui_pop' : 'ui_tap'); }, t * 1000);
    const rw = h('div', 'panel brk rewards');
    rw.innerHTML = `<h3>REWARDS</h3><div class="rw">
      <div><img src="assets/ui/sm/icon_clout.webp"><div class="v num cnt" data-to="${res.dc}" data-sign="1" style="color:${res.dc >= 0 ? '#FFC84A' : '#FF4D6D'}">${res.dc >= 0 ? '+' : ''}0</div><div class="k">CLOUT</div></div>
      <div><img src="assets/ui/sm/icon_cash.webp"><div class="v num cnt" data-to="${res.coins ?? res.cash}" data-sign="1" style="color:#FFC84A">+0</div><div class="k">COINS</div></div>
      <div>${res.bag ? `<img src="assets/ui/sm/icon_bag_${res.bag}.webp"><div class="v num">+1</div><div class="k">${BAG[res.bag].name.toUpperCase()}</div>` : `<img src="assets/ui/sm/icon_bag_common.webp" style="filter:grayscale(1) brightness(.5)"><div class="v num">—</div><div class="k">${win === 1 ? 'SLOTS FULL' : win === -1 ? 'NO BAG ON A DRAW' : 'WIN FOR A BAG'}</div>`}</div></div>
      <div class="xpline"><span>+${res.xp || 0} XP</span><span>LEVEL ${res.level || save.p.level}</span><span>W BAG ${Math.min(W_BAG.need, res.wbag?.ws ?? 0)}/${W_BAG.need}</span></div>
      <div class="stats"><div><b>${B.played[0].length}</b>CARDS PLAYED</div><div><b>${Math.round(B.spent[0])}</b>COPIUM SPENT</div><div><b>${fmt(match.stats.dmgTowers)}</b>TOWER DMG</div></div>`;
    const rowB = h('div', 'row'); const cont = h('button', 'btn', 'CONTINUE');
    cont.onclick = () => { tap(); this.app.toHub(res); };
    rowB.append(cont);
    R.append(rib, sc, rw, rowB);
    if (win === 1) R.prepend(confetti());
    this.app.ui.append(R);
    // the numbers count up once the rewards are in
    setTimeout(() => R.querySelectorAll('.cnt').forEach(e => countUp(e, +e.dataset.to, e.dataset.sign)), 1250);
    if (res.dc > 0) setTimeout(() => audio.play('clout_up'), 700); else if (res.dc < 0) setTimeout(() => audio.play('clout_down'), 700);
  }
  // after the results: a new arena, new cards, a level up
  news(res) {
    if (!res) return;
    if (res.arena) {
      audio.play('arena_unlock');
      this.sheet(box => {
        box.innerHTML = `<div style="display:grid;justify-items:center;gap:6px;text-align:center;--bw:170px" class="bigbadge">${arenaBadge(res.arena, true)}<div class="prog-t">ARENA ${res.arena.n} UNLOCKED</div><h3 class="stroke-s">${res.arena.name}</h3><p>${res.arena.blurb}</p></div>`;
        // its cards aren't mine yet: from now on the bags can hold them
        if (res.unlocked?.length) { const g = h('div', 'grid4'); for (const id of res.unlocked) g.append(cardEl(id)); box.append(h('div', 'disp stroke-s', 'NOW IN BAGS'), h('div', 'prog-t', 'Open bags to find these cards')); for (const e of [...box.children].slice(-2)) e.style.textAlign = 'center'; box.append(g); }
        const ok = h('button', 'btn small', 'LET\'S GO'); ok.onclick = () => { tap(); this.closeSheet(); if (res.levelUp) this.levelUp(res.level); }; const a = h('div', 'acts'); a.append(ok); box.append(a);
      });
    } else if (res.levelUp) this.levelUp(res.level);
  }
}
