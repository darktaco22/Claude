// The battle HUD, kept light so the arena reads (the genre's layout): the opponent (name, trophies) and the clock as two small
// chips up top, the Ws by the river on the right, the card tray at the bottom (next card, hand of 4, COPIUM bar), emotes
// bottom left, banners; and the deploy input: drag a card onto the arena, or tap a card then tap a tile.
import * as THREE from 'three';
import {CARDS, EMOTES, MATCH} from '../data.js';
import {cardEl, h} from './cards.js';
import {audio, buzz} from '../audio.js';

export class Hud {
  constructor(root, {stage, arena, units, battle, opp, me, onPlay}) {
    this.root = root; this.stage = stage; this.arena = arena; this.units = units; this.b = battle; this.onPlay = onPlay; this.opp = opp;
    this.sel = -1; this.drag = null; this.handIds = [];
    // ---- top: who I'm up against, the clock
    const top = this.top = h('div', 'col hud-top');
    const who = h('div', 'opp'); who.append(h('div', 'name stroke-s', opp.name));
    const tr = h('div', 'opp-tr'); tr.innerHTML = `<img src="assets/ui/sm/icon_clout.webp" alt=""><b class="num">${Math.round(opp.clout || 0).toLocaleString('en-US')}</b>`; who.append(tr);
    this.timer = h('div', 'timer'); this.timer.innerHTML = '<div class="lbl">TIME LEFT</div><div class="t">3:00</div>';
    top.append(who, this.timer);
    // ---- the Ws, beside the river: theirs above it, mine below
    const wb = this.wCol = h('div', 'col wcol');
    this.wEl = [h('div', 'w'), h('div', 'w bear')];
    this.wEl[1].innerHTML = '<img src="assets/ui/sm/icon_w_bear.webp" alt=""><span class="stroke-s">0</span>';
    this.wEl[0].innerHTML = '<img src="assets/ui/sm/icon_w_bull.webp" alt=""><span class="stroke-s">0</span>';
    wb.append(this.wEl[1], this.wEl[0]);
    // ---- tray
    const tray = this.tray = h('div', 'panel col tray');
    const nx = h('div', 'next'); nx.append(h('div', 'lbl', 'NEXT')); this.nextSlot = h('div'); this.nextSlot.style.width = '100%'; this.nextSlot.style.display = 'grid'; this.nextSlot.style.justifyItems = 'center'; nx.append(this.nextSlot);
    this.hand = h('div', 'hand');
    this.slots = [0, 1, 2, 3].map(i => { const s = h('div'); s.dataset.slot = i; s.dataset.key = i + 1; this.hand.append(s); return s; });
    const cop = this.cop = h('div', 'copium');
    cop.innerHTML = `<div class="can"><img src="assets/ui/sm/icon_copium.webp" alt=""><div class="count stroke-s">5</div></div>`;
    const bar = h('div', 'bar');
    this.segs = []; for (let i = 0; i < 10; i++) { const s = h('div', 'seg'); s.append(h('i')); bar.append(s); this.segs.push(s); }
    cop.append(bar);
    tray.append(nx, this.hand, cop);
    // ---- emotes
    this.emoteBtn = h('button', 'icon-btn emote-btn'); this.emoteBtn.innerHTML = '<img src="assets/ui/sm/icon_emote.webp" alt="emotes">';
    this.emoteBtn.onclick = e => { e.stopPropagation(); audio.play(audio.has('ui_pop') ? 'ui_pop' : 'ui_tap'); this.toggleEmotes(); };
    // on a PC (body.desk): the keys
    const keys = h('div', 'panel plain keys', '<b class="stroke-s">CONTROLS</b><span><kbd>1</kbd><kbd>2</kbd><kbd>3</kbd><kbd>4</kbd> pick a card</span><span><kbd>click</kbd> drop it where the preview is</span><span><kbd>drag</kbd> a card works too</span><span><kbd>right-click</kbd> or <kbd>Esc</kbd> cancel</span><span><kbd>E</kbd> emotes</span>');
    root.append(top, wb, tray, this.emoteBtn, keys);
    this.layout();
    this.onResize = () => this.layout(); addEventListener('resize', this.onResize);
    this.bindInput();
    this.refreshHand(true);
  }
  layout() {
    const r = this.tray.getBoundingClientRect(), t = this.top.getBoundingClientRect();
    this.emoteBtn.style.bottom = (innerHeight - r.top + 10) + 'px';
    this.emoteBtn.style.left = Math.max(8, (innerWidth - r.width) / 2 + 6) + 'px';
    // tell the camera how much of the screen the HUD covers
    this.stage.safe = {top: (t.bottom + 4) / innerHeight, bottom: (innerHeight - r.top + 4) / innerHeight};
    this.stage.fit();
    // the Ws straddle the river (z 16), at the column's right edge
    const river = this.stage.toScreen(new THREE.Vector3(9, 0, 16)), w = this.wCol.getBoundingClientRect();
    this.wCol.style.top = Math.round(river.y - w.height / 2) + 'px';
  }
  destroy() { removeEventListener('resize', this.onResize); this.unbind?.(); this.root.classList.remove('intro'); this.root.innerHTML = ''; }

  // the match's opening, the genre's: the arena alone with its name, then both names on their ribbons (theirs above the
  // river, mine below it), then the HUD slides in (style.css #ui.intro). ms: what it may take (online, what is left of the
  // server's hold), its steps shortened to fit; under a second there is no opening
  intro(A, them, me, ms) {
    if (!(ms >= 1000)) return Promise.resolve();
    const R = this.root, k = Math.min(1, ms / 2700), wait = t => new Promise(r => setTimeout(r, t * k));
    const at = z => Math.round(this.stage.toScreen(new THREE.Vector3(9, 0, z)).y) + 'px';
    const title = h('div', 'arena-title', `<img src="assets/ui/sm/icon_battle.webp" alt=""><small class="stroke-s">ARENA ${A.n}</small><b class="stroke"></b>`);
    title.lastChild.textContent = A.name; title.style.top = at(16);
    const rib = (cls, label, name, z) => {
      const e = h('div', 'vs-rib ' + cls, `<small class="stroke-s">${label}</small><div class="rb"><b class="stroke"></b></div>`);
      e.querySelector('b').textContent = name; e.style.top = at(z); return e;
    };
    R.classList.add('intro');
    return (async () => {
      R.append(title); audio.play('ui_swoosh'); await wait(1250);
      title.classList.add('out');
      const T = rib('them', 'OPPONENT', them, 10), M = rib('me', 'YOU', me, 22);
      R.append(T, M); audio.play('card_reveal'); await wait(1250);
      T.classList.add('out'); M.classList.add('out'); R.classList.remove('intro'); await wait(200);
      setTimeout(() => { title.remove(); T.remove(); M.remove(); }, 500);
    })();
  }

  // ---------- hand
  refreshHand(first) {
    const hand = this.b.hands[0];
    for (let i = 0; i < 4; i++) {
      if (this.handIds[i] === hand[i] && !first) continue;
      this.handIds[i] = hand[i];
      const c = cardEl(hand[i]); if (!first) c.classList.add('enter');
      this.slots[i].replaceChildren(c);
    }
    const n = this.b.next(0);
    if (this.nextId !== n) { this.nextId = n; this.nextSlot.replaceChildren(cardEl(n, {name: false})); }
    if (this.sel >= 0) this.slots[this.sel].firstChild?.classList.add('sel');
  }
  select(i) {
    for (const s of this.slots) s.firstChild?.classList.remove('sel');
    this.sel = i;
    if (i >= 0) { this.slots[i].firstChild?.classList.add('sel'); this.arena.showMask(this.b, 0, this.b.hands[0][i]); audio.play('card_pick'); }
    else { this.arena.hideMask(); this.arena.hideGhost(); this.units?.ghostHide(); }
  }

  // ---------- input
  bindInput() {
    const toTile = (px, py, id) => {
      const p = this.stage.pick(px, py); if (!p) return null;
      let x = Math.min(17.5, Math.max(0.5, Math.floor(p.x) + 0.5)), z = Math.min(31.5, Math.max(0.5, Math.floor(p.z) + 0.5));
      if (CARDS[id].type === 'spell') { x = Math.min(17.6, Math.max(0.4, p.x)); z = Math.min(31.6, Math.max(0.4, p.z)); return {x, z, ok: !this.b.canPlace(0, id, x, z)}; }
      if (!this.b.canPlace(0, id, x, z)) return {x, z, ok: true};
      // snap to the nearest legal tile nearby (dragging a bit too far still lands on your side)
      let best = null, bd = 9;
      for (let dz = -3; dz <= 3; dz++) for (let dx = -2; dx <= 2; dx++) { const tx = x + dx, tz = z + dz; if (tx < 0 || tx > 18 || tz < 0 || tz > 32) continue;
        if (!this.b.canPlace(0, id, tx, tz)) { const d = Math.hypot(dx * 1.6, tz - (p.z)); if (d < bd) { bd = d; best = {x: tx, z: tz, ok: true}; } } }
      return best && bd < 4.2 ? best : {x, z, ok: false};
    };
    const ghost = (t, id) => {
      const c = CARDS[id];
      if (!t) { this.arena.hideGhost(); this.units?.ghostHide(); return; }
      const ok = t.ok && this.b.copium[0] >= c.cost;
      this.arena.setGhost(t.x, t.z, {ok, radius: c.type === 'spell' ? c.spell.r : c.type === 'building' ? (c.bld.range || 1.3) : 0, unit: c.type !== 'spell'});
      if (c.type === 'unit') this.units?.ghost(id, t.x, t.z, ok);
    };
    const trayTop = () => this.tray.getBoundingClientRect().top;
    const down = e => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;     // (right-click cancels: the contextmenu below)
      const cardNode = e.target.closest?.('.hand .card');
      if (cardNode) {
        e.preventDefault();
        const slot = +cardNode.parentElement.dataset.slot;
        this.select(slot);
        const id = this.b.hands[0][slot];
        const dc = cardEl(id, {name: false}); dc.classList.add('dragcard'); dc.style.left = e.clientX + 'px'; dc.style.top = e.clientY + 'px'; dc.style.display = 'none';
        this.root.append(dc);
        this.drag = {slot, id, el: dc, x0: e.clientX, y0: e.clientY, moved: false, pid: e.pointerId, node: cardNode};
        return;
      }
      if (e.target.closest?.('.emote-menu, .emote-btn, .hud-top, .tray')) return;
      if (this.emoteMenu) { this.toggleEmotes(false); return; }
      // tap-to-place with a selected card
      if (this.sel >= 0 && e.clientY < trayTop()) {
        const id = this.b.hands[0][this.sel], t = toTile(e.clientX, e.clientY, id);
        if (t?.ok) this.tryPlay(this.sel, t.x, t.z); else this.deny(t ? 'Can\'t drop there' : null);
      }
    };
    // a mouse with a card picked (keys 1-4 or a click on it): the preview follows the pointer, a click drops it
    const hover = e => {
      this.mouse = {x: e.clientX, y: e.clientY};
      if (this.sel < 0) return;
      const id = this.b.hands[0][this.sel], t = e.clientY < trayTop() - 6 ? toTile(e.clientX, e.clientY, id) : null;
      ghost(t, id);
    };
    const move = e => {
      const d = this.drag; if (!d || e.pointerId !== d.pid) { if (e.pointerType === 'mouse' && !d) hover(e); return; }
      if (Math.hypot(e.clientX - d.x0, e.clientY - d.y0) > 8) d.moved = true;
      d.el.style.display = ''; d.el.style.left = e.clientX + 'px'; d.el.style.top = e.clientY + 'px';
      d.node.classList.toggle('drag', d.moved);
      const over = e.clientY < trayTop() - 6;
      d.el.classList.toggle('over', over);
      d.tile = over ? toTile(e.clientX, e.clientY, d.id) : null;
      ghost(d.tile, d.id);
    };
    const up = e => {
      const d = this.drag; if (!d || e.pointerId !== d.pid) return;
      this.drag = null; d.el.remove(); d.node.classList.remove('drag');
      if (d.moved && d.tile) {
        if (d.tile.ok) this.tryPlay(d.slot, d.tile.x, d.tile.z);
        else { this.deny('Can\'t drop there'); this.arena.hideGhost(); this.units?.ghostHide(); }
      } else if (d.moved) { this.arena.hideGhost(); this.units?.ghostHide(); }
    };
    const key = e => {
      if (e.repeat || e.target?.closest?.('input, textarea')) return;
      if (e.key >= '1' && e.key <= '4') { const i = +e.key - 1; this.select(this.sel === i ? -1 : i); if (this.sel >= 0 && this.mouse) hover({clientX: this.mouse.x, clientY: this.mouse.y}); }
      else if (e.key === 'Escape') this.select(-1);
      else if (e.key === 'e' || e.key === 'E') this.toggleEmotes();
    };
    const ctx = e => { if (this.sel >= 0 || this.drag) { e.preventDefault(); this.select(-1); } };
    addEventListener('pointerdown', down, {passive: false}); addEventListener('pointermove', move); addEventListener('pointerup', up); addEventListener('pointercancel', up);
    addEventListener('keydown', key); addEventListener('contextmenu', ctx);
    this.unbind = () => { removeEventListener('pointerdown', down); removeEventListener('pointermove', move); removeEventListener('pointerup', up); removeEventListener('pointercancel', up); removeEventListener('keydown', key); removeEventListener('contextmenu', ctx); };
  }
  tryPlay(slot, x, z) {
    const id = this.b.hands[0][slot], why = this.b.canPlay(0, slot, x, z);
    if (why === 'copium') { this.deny(); return; }
    if (why) { this.deny('Can\'t drop there'); return; }
    const from = this.slots[slot].firstChild?.getBoundingClientRect();
    if (this.onPlay(slot, x, z)) { this.select(-1); buzz(12); this.endTutorial(); if (from) this.flyCard(id, from, x, z); }
  }
  // the played card flies from the hand to where it lands and shrinks into it
  flyCard(id, from, x, z) {
    const to = this.stage.toScreen(new THREE.Vector3(x, 0.5, z)), e = cardEl(id, {name: false});
    e.classList.add('flycard'); e.style.left = from.left + 'px'; e.style.top = from.top + 'px'; e.style.width = from.width + 'px';
    this.root.append(e);
    requestAnimationFrame(() => requestAnimationFrame(() => { e.style.transform = `translate(${to.x - from.left - from.width / 2}px, ${to.y - from.top - from.height / 2}px) scale(.25) rotate(8deg)`; e.style.opacity = '0'; }));
    setTimeout(() => e.remove(), 420);
  }
  deny(msg) {
    audio.play('card_deny'); buzz([20, 40, 20]);
    this.cop.classList.remove('flash'); void this.cop.offsetWidth; this.cop.classList.add('flash');
    if (msg) this.toast(msg);
  }

  // ---------- per frame
  update() {
    const b = this.b, cp = b.copium[0];
    const full = Math.floor(cp + 1e-6);
    for (let i = 0; i < 10; i++) {
      const s = this.segs[i], on = i < full;
      if (s.on !== on) { s.classList.toggle('on', on); s.on = on; }
      s.firstChild.style.width = i === full ? ((cp - full) * 100).toFixed(1) + '%' : '0';
    }
    const n = String(full); if (this.copN !== n) { this.copN = n; this.cop.querySelector('.count').textContent = n; }
    this.cop.classList.toggle('od', b.overdose || b.phase === 'overtime');
    // affordability
    for (let i = 0; i < 4; i++) { const c = this.slots[i].firstChild; if (c) c.classList.toggle('poor', CARDS[b.hands[0][i]].cost > cp); }
    if (b.hands[0].some((id, i) => id !== this.handIds[i])) this.refreshHand();
    // clock
    const t = Math.ceil(b.timeLeft()), s = `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
    if (this.tStr !== s) { this.tStr = s; this.timer.lastChild.textContent = s;
      if (b.phase !== 'end' && t <= 10 && t > 0) audio.play('countdown_tick', {gap: 0.5}); }
    const mode = b.phase === 'tiebreak' ? 'tb' : b.phase === 'overtime' ? (t <= MATCH.tripleAt ? 'ot3' : 'ot') : b.overdose ? 'od' : '';
    if (this.mode !== mode) { this.mode = mode; this.timer.className = 'timer ' + (mode === 'ot3' ? 'ot' : mode === 'tb' ? 'ot' : mode); this.timer.firstChild.textContent = mode === 'tb' ? 'TIEBREAKER' : mode === 'ot3' ? 'OVERTIME x3' : mode === 'ot' ? 'OVERTIME x2' : mode === 'od' ? 'COPIUM x2' : 'TIME LEFT'; }
    for (const s of [0, 1]) if (this.wN?.[s] !== b.ws[s]) { (this.wN ||= [0, 0])[s] = b.ws[s]; const el = this.wEl[s]; el.lastChild.textContent = b.ws[s]; el.classList.remove('pop'); void el.offsetWidth; el.classList.add('pop'); }
  }

  // ---------- first match: a touch dot that drags the first card onto my side, until I play one
  tutorial() {
    const tip = this.tut = h('div', 'tut');
    tip.innerHTML = '<div class="tut-dot"></div><div class="tut-txt panel plain">Drag a card onto <b>your side</b> of the arena</div>';
    this.root.append(tip);
    const place = () => {
      const c = this.slots[1].getBoundingClientRect(), to = this.stage.toScreen(new THREE.Vector3(5.5, 0, 21.5));
      tip.style.setProperty('--x0', c.left + c.width / 2 + 'px'); tip.style.setProperty('--y0', c.top + c.height / 2 + 'px');
      tip.style.setProperty('--x1', to.x + 'px'); tip.style.setProperty('--y1', to.y + 'px');
    };
    place(); this.tutPlace = place;
  }
  endTutorial() { if (!this.tut) return; this.tut.remove(); this.tut = null; }

  // ---------- messages
  banner(big, sub = '', cls = '', ms = 2200) {
    const e = h('div', 'banner in ' + cls); e.innerHTML = `<div class="big stroke">${big}</div>${sub ? `<div class="sub stroke-s">${sub}</div>` : ''}`;
    this.root.append(e); setTimeout(() => e.remove(), ms); return e;
  }
  // a W medallion flies from the fallen tower to the score
  flyW(team, x, z) {
    const from = this.stage.toScreen(new THREE.Vector3(x, 3, z)), to = this.wEl[team].firstChild.getBoundingClientRect();
    const e = h('img', 'flyw'); e.src = `assets/ui/sm/icon_w_${team === 0 ? 'bull' : 'bear'}.png`;
    e.style.left = from.x - 40 + 'px'; e.style.top = from.y - 40 + 'px'; this.root.append(e);
    requestAnimationFrame(() => requestAnimationFrame(() => { e.style.transform = `translate(${to.left + to.width / 2 - from.x}px, ${to.top + to.height / 2 - from.y}px) scale(.4) rotate(360deg)`; }));
    setTimeout(() => { e.remove(); }, 1100);
  }
  toast(msg) { if (this.toastEl) this.toastEl.remove(); const e = this.toastEl = h('div', 'toast panel plain', msg); this.root.append(e); setTimeout(() => e.remove(), 1600); }
  toggleEmotes(on = !this.emoteMenu) {
    if (!on) { this.emoteMenu?.remove(); this.emoteMenu = null; return; }
    const m = this.emoteMenu = h('div', 'panel emote-menu');
    for (const id of EMOTES) { const b = h('button'); b.innerHTML = `<img src="assets/ui/sm/emote_${id}.webp" alt="${id}">`; b.onclick = e => { e.stopPropagation(); this.emote(0, id); this.toggleEmotes(false); }; m.append(b); }
    const r = this.emoteBtn.getBoundingClientRect();
    m.style.bottom = (innerHeight - r.top + 8) + 'px'; m.style.left = r.left + 'px';
    this.root.append(m);
  }
  emote(team, id) {
    // one bubble per side: the next emote takes the last one's place at once (its bubble gone, its sound cut)
    const old = (this.bubbles ||= [])[team];
    if (old) { old.el.remove(); clearTimeout(old.gone); clearTimeout(old.later); old.snd?.stop(); }
    const hq = this.b.towers[team][2], p = this.stage.toScreen(new THREE.Vector3(hq.x + (team ? 3.2 : -3.2), 4.6, hq.z));
    const e = h('img', 'bubble'); e.src = `assets/ui/emote_${id}.webp`; e.style.left = Math.max(8, Math.min(innerWidth - 128, p.x - 60)) + 'px'; e.style.top = (p.y - 80) + 'px';
    const cur = this.bubbles[team] = {el: e};
    this.root.append(e); cur.gone = setTimeout(() => { e.remove(); if (this.bubbles[team] === cur) this.bubbles[team] = null; }, 2400);
    audio.play('emote_pop', {gap: 0}); if (audio.has('emo_' + id)) cur.later = setTimeout(() => { cur.snd = audio.play('emo_' + id, {vol: team === 0 ? 0.9 : 0.7, gap: 0}); }, 120);
    if (team === 0) { this.lastEmote = performance.now(); this.onEmote?.(id); }
  }
}
