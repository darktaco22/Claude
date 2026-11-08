// The profile store. The rules are src/shared/economy.js (pure, the same the server runs). Offline, this store applies them
// to a profile kept in localStorage; online (src/net/), the server's profile is the truth: actions go to the server and its
// pushed profile replaces ours (setRemote). The menus call the methods below either way.
import * as E from './shared/economy.js';
import {CARDS, arenaOf} from './data.js';

const KEY = 'memeroyale.save';
export const BAG = E.BAG;

class Save {
  constructor() {
    let p = null;
    try { const raw = localStorage.getItem(KEY); p = raw ? JSON.parse(raw) : null; }
    catch { try { localStorage.setItem(KEY + '.bad', localStorage.getItem(KEY)); } catch {} }
    this.p = p ? E.fix(p, Date.now()) : E.fresh({key: 'local', now: Date.now(), rand: Math.random});
    E.refresh(this.p, Date.now());
    this.remote = null; this.listeners = new Set();
    this.write();
  }
  now() { return this.clock ? this.clock() : Date.now(); }   // online: the server's clock (bag timers, the day)
  write() { if (this.remote) return; try { localStorage.setItem(KEY, JSON.stringify(this.p)); } catch {} }
  changed() { for (const f of this.listeners) try { f(this.p); } catch {} }
  // online: the server's profile replaces ours; actions go through `send(a) -> Promise<result>`
  setRemote(send, profile) { this.remote = send; if (profile) { this.p = E.fix(profile, Date.now()); this.changed(); } }
  setProfile(profile) { this.p = E.fix(profile, this.now()); this.changed(); }
  // one action (economy.js ACTIONS): offline applied here at once, online asked of the server
  async act(a) {
    if (this.remote) return this.remote(a);
    const r = E.act(this.p, a, {now: Date.now(), rand: Math.random}); if (r.ok) { this.write(); this.changed(); } return r;
  }

  // ---- reads
  get deck() { return E.deckOf(this.p); }
  get league() { return arenaOf(this.p.clout); }
  get arena() { return arenaOf(this.p.clout); }
  lvl(id) { return this.p.cards[id]?.lvl || 1; }
  levels() { return E.levels(this.p); }
  towerLvl() { return E.towerLvl(this.p); }
  canUpgrade(id) { const u = E.canUpgrade(this.p, id); return u && {...u, ok: u.ok ?? (this.p.cards[id].copies >= u.n && this.p.coins >= u.cost)}; }
  bagLeft(b) { return E.bagLeft(b, this.now()); }
  bagReady(b) { return E.bagReady(b, this.now()); }
  bagBusy() { return E.bagBusy(this.p, this.now()); }
  speedCost(b) { return E.speedCost(b, this.now()); }
  wbag() { return E.wbag(this.p, this.now()); }
  get avatar() { return E.avatarOf(this.p); }
  roadClaimable() { return E.roadClaimable(this.p); }
  xpNeed() { return E.xpNeed(this.p); }
  freeGift() { return E.freeGift(this.now()); }
  arenaPack() { return E.arenaPack(this.p, this.now()); }
  refresh() { E.refresh(this.p, this.now()); }

  // ---- the names the menus use (offline they apply at once; online the server answers)
  upgrade(id) { return this.act({a: 'upgrade', id}); }
  setDeck(d) { return this.act({a: 'setDeck', slot: this.p.active, cards: d}); }
  startBag(i) { return this.act({a: 'startBag', i}); }
  speedBag(i) { return this.act({a: 'speedBag', i}); }
  async openBag(i) { const r = await this.act({a: 'openBag', i}); return r.ok ? r.bag : null; }
  // offline battles: the result is applied here (online the server does it and pushes the profile)
  result(win, ws, oppClout, bot = true) { const r = E.result(this.p, {win, ws, oppClout, now: Date.now(), bot}); this.write(); this.changed(); return r; }
  opponent() { return E.botOpponent(this.p, Math.random, {easy: E.matchPlan(this.p).easy}); }
}
export const save = new Save();
export {CARDS};
