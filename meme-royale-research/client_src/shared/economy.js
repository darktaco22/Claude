// MEME ROYALE — THE ECONOMY: the player's profile and every rule that changes it. PURE: no DOM, no Node, no clock and no
// Math.random inside (the caller passes `now` in ms and `rand`, a function -> [0, 1)). The server (server/game.mjs) runs it on the
// profiles it keeps and is the only judge online; the page runs the very same functions offline and for previews (what a bag
// holds, the price of a skip, today's deals), so both always agree. The numbers live in src/data.js; this file is the rules.
//
//   fresh({key, now, rand}) -> a new profile           fix(p, now) -> p (repairs / migrates an old or offline save in place)
//   refresh(p, now)          the UTC-day rollover (shop deals, free gift, W bag); every action calls it first
//   act(p, a, {now, rand})   ONE validated action -> {ok: true, ...what happened} | {ok: false, why}   (a = {a: 'upgrade', id}, ...)
//       setName {name}  setAvatar {id}  setDeck {slot, cards?, active?}  upgrade {id}  startBag {i}  openBag {i}  speedBag {i}  claimRoad {at}
//       claimFree  buyDeal {slot}  buyBag {tier}  buyCoins {id}  buyCosmetic {id}  claimWBag  tutDone
//   result(p, {win, ws, oppClout, now})   after a battle: Clout, coins, XP, a bag, unlocks, the W bag  (win: 1 won, 0 lost, -1 draw)
//   friendly(p, {win, ws})   after a friendly battle: stats.friendly + 1, nothing else
//   priceOf(p, kind, id, now) -> USD | {why}     grant(p, {kind, id, ref, usd, now, rand}) -> {ok, got}   (real-money items)
//       kind 'gems' (GEM_PACKS id), 'offer' (OFFERS id), 'arena' (SHOP.arenaPack, id = the arena it is offered for)
//   matchPlan(p) -> {botMs, solo, easy, why}: how long the queue looks for a person before a bot comes, and what kind of bot
//   botOpponent(p, rand, {easy}) -> a made-up opponent around my Clout (the server's bot match, and every offline battle)
//   reads: deckOf levels towerLvl canUpgrade bagLeft bagReady speedCost freeGift wbag roadClaimable arenaPack xpNeed view findable
//
// CARDS: the Basement's are mine from the start. Every arena after it, once reached, only puts its cards in the bags: a card is
// mine the first time a bag (or a reward naming it) gives one (roll: isNew), never just for reaching its arena.
//
// THE PROFILE (stored by the server, sent to its page as {t: 'profile', p}):
//   {v, id (public key), name, avatar (a portrait of AVATARS whose character I own, or null: avatarOf), account (an account owns the name: server/game.mjs), created, clout, best, coins, gems, xp, level, cards: {id: {lvl, copies}}, decks: [[8] x 3], active,
//    bags: [{tier, open, start} | null] x 4, bagN, wbag: {day, ws, claimed}, road: [Clout claimed], reached (best arena index),
//    shop: {day, free, bought: [slots], deals: [{slot, id, n, coins}], arenaPack: {arena, until, bought} | null},
//    offers: {id: at}, cosmetics: {own: [], tower}, purchases: [{ref, kind, id, usd, at}], stats: {wins, losses, draws, ws, played,
//    pvp, bots, lstreak (losses in a row)}, seen: {card: false while new}, tut, wallet?: {a, tied, wo} (the server's; the page sees a short address only)}
// XP: XP.need[L] is the XP that takes level L-1 to level L (the bar starts again at each level); the account level is the level of
// my towers in battle (towerLvl).
import {CARDS, ARENAS, arenaOf, SHOP, GEM_PACKS, OFFERS, GEM_PRICES, XP, W_BAG, ROAD, UPGRADE, MAX_LVL, STARTER_DECK, BOT_NAMES, AVATARS} from '../data.js';

export const ECON = {v: 2, start: {coins: 0, gems: 100},   // a new account: 100 gems, the coins come from battles
  decks: 3, slots: 4, deck: 8, nameMin: 3, nameMax: 14, arenaPackMs: 24 * 3600000, purchasesKept: 200};
// the bags: opening time, card copies, coins, the rare / epic / legendary share, and the gems found inside: [chance, min, max]
export const BAG = {
  common: {name: 'Bag', time: 3 * 3600, cards: 12, cash: [40, 80], color: '#AEB6C2', rare: 0.2, epic: 0.02, legendary: 0, gems: [0, 0, 0]},
  rare: {name: 'Fat Bag', time: 8 * 3600, cards: 30, cash: [120, 220], color: '#4CC9F0', rare: 1, epic: 0.15, legendary: 0.01, gems: [0.3, 2, 6]},
  epic: {name: 'Mega Bag', time: 12 * 3600, cards: 60, cash: [300, 500], color: '#C77DFF', rare: 3, epic: 1, legendary: 0.08, gems: [1, 4, 10]},
  legendary: {name: 'Whale Bag', time: 24 * 3600, cards: 90, cash: [700, 1100], color: '#FFC84A', rare: 6, epic: 2, legendary: 1, gems: [1, 10, 25]},
};
export const BAG_CYCLE = ['common', 'common', 'rare', 'common', 'common', 'rare', 'common', 'epic', 'common', 'rare', 'common', 'common', 'rare', 'common', 'legendary', 'common', 'rare', 'epic'];
const RARITIES = ['common', 'rare', 'epic', 'legendary'];
const no = why => ({ok: false, why});
const int = v => Number.isInteger(v) ? v : NaN;

// ---------------------------------------------------------------- time, seeds
export const dayOf = now => new Date(now).toISOString().slice(0, 10);            // the UTC day 'YYYY-MM-DD'
export function hash32(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
export function seeded(seed) {   // mulberry32
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const pickOf = (rand, a) => a[Math.floor(rand() * a.length)];

// ---------------------------------------------------------------- the profile
export function fresh({key = '', now = 0, rand = () => 0.5} = {}) {
  const cards = {}; for (const id of ARENAS[0].unlock) cards[id] = {lvl: 1, copies: 0};
  return {v: ECON.v, id: String(key), name: 'DEGEN_' + (100 + Math.floor(rand() * 900)), avatar: null, account: false, created: now, clout: 0, best: 0,
    coins: ECON.start.coins, gems: ECON.start.gems, xp: 0, level: 1, cards,
    decks: [[...STARTER_DECK], [...STARTER_DECK], [...STARTER_DECK]], active: 0,
    bags: [{tier: 'common', open: true, start: null}, null, null, null], bagN: 0,
    wbag: {day: '', ws: 0, claimed: false}, road: [], reached: 0,
    shop: {day: '', free: false, bought: [], deals: [], arenaPack: null}, offers: {}, cosmetics: {own: [], tower: null}, purchases: [],
    stats: {wins: 0, losses: 0, draws: 0, ws: 0, played: 0, pvp: 0, bots: 0, friendly: 0, lstreak: 0}, seen: {}, tut: false};
}
const num = (v, d = 0, lo = 0, hi = 1e12) => Number.isFinite(+v) ? Math.max(lo, Math.min(hi, Math.floor(+v))) : d;
// repairs a profile in place (an old version, an offline save of src/save.js: cash -> coins, deck -> decks; anything broken)
export function fix(p, now = 0) {
  const d = fresh({key: p?.id || '', now});
  if (!p || typeof p !== 'object') return d;
  if (p.cash != null && p.coins == null) p.coins = p.cash; delete p.cash;
  if (Array.isArray(p.deck) && !Array.isArray(p.decks)) p.decks = [p.deck, [...p.deck], [...p.deck]]; delete p.deck;
  for (const k of Object.keys(d)) if (p[k] === undefined || p[k] === null && d[k] !== null) p[k] = d[k];
  p.v = ECON.v;
  for (const k of ['clout', 'best', 'coins', 'gems', 'xp', 'bagN', 'reached']) p[k] = num(p[k]);
  p.level = num(p.level, 1, 1, MAX_LVL); p.best = Math.max(p.best, p.clout);
  if (!p.cards || typeof p.cards !== 'object') p.cards = d.cards;
  for (const id of Object.keys(p.cards)) { const c = p.cards[id]; if (!CARDS[id] || !c || typeof c !== 'object') { delete p.cards[id]; continue; } c.lvl = num(c.lvl, 1, 1, MAX_LVL); c.copies = num(c.copies); }
  unlockTo(p, p.best, now, true);
  if (!Array.isArray(p.decks)) p.decks = [];
  for (let s = 0; s < ECON.decks; s++) p.decks[s] = cleanDeck(p, p.decks[s]);
  p.decks.length = ECON.decks; p.active = num(p.active, 0, 0, ECON.decks - 1);
  if (!Array.isArray(p.bags)) p.bags = d.bags;
  p.bags = Array.from({length: ECON.slots}, (_, i) => { const b = p.bags[i]; return b && BAG[b.tier] ? {tier: b.tier, open: !!b.open, start: Number.isFinite(b.start) ? b.start : null} : null; });
  if (!p.wbag || typeof p.wbag !== 'object') p.wbag = d.wbag;
  if (!Array.isArray(p.road)) p.road = []; p.road = p.road.filter(at => ROAD.some(r => r.at === at));
  if (!p.shop || typeof p.shop !== 'object' || !Array.isArray(p.shop.bought) || !Array.isArray(p.shop.deals)) p.shop = {...d.shop, arenaPack: p.shop?.arenaPack || null};
  if (!p.offers || typeof p.offers !== 'object') p.offers = {};
  if (!p.cosmetics || !Array.isArray(p.cosmetics.own)) p.cosmetics = {own: [], tower: null};
  if (!Array.isArray(p.purchases)) p.purchases = [];
  p.stats = {...d.stats, ...(p.stats && typeof p.stats === 'object' ? p.stats : {})};
  if (!p.seen || typeof p.seen !== 'object') p.seen = {};
  if (p.avatar != null && !(typeof p.avatar === 'string' && AVATARS.includes(p.avatar) && Object.hasOwn(p.cards, p.avatar))) p.avatar = null;
  return p;
}
// my picture: the portrait I picked (AVATARS, a character I own), else my deck's first character that has one
export const avatarOf = p => (p.avatar && AVATARS.includes(p.avatar) && Object.hasOwn(p.cards, p.avatar) ? p.avatar : null) || deckOf(p).find(id => AVATARS.includes(id)) || 'troll';
// 8 distinct owned cards; what is missing is filled from the starter deck, then from the rest of the collection
function cleanDeck(p, deck) {
  const out = []; for (const id of Array.isArray(deck) ? deck : []) if (p.cards[id] && !out.includes(id) && out.length < ECON.deck) out.push(id);
  for (const id of [...STARTER_DECK, ...Object.keys(p.cards)]) if (out.length < ECON.deck && p.cards[id] && !out.includes(id)) out.push(id);
  return out;
}

// ---------------------------------------------------------------- reads
export const deckOf = p => p.decks[p.active] || p.decks[0];
export function levels(p) { const o = {}; for (const [id, c] of Object.entries(p.cards)) o[id] = c.lvl; return o; }
export const towerLvl = p => Math.max(1, Math.min(MAX_LVL, p.level | 0 || 1));
export const xpNeed = p => p.level >= MAX_LVL ? null : XP.need[p.level + 1];
export function canUpgrade(p, id) { const c = p.cards[id]; if (!c || c.lvl >= MAX_LVL) return null; const [n, cost] = UPGRADE[c.lvl]; return {n, cost, ok: c.copies >= n && p.coins >= cost}; }
export function bagLeft(b, now) { if (!b || b.open) return 0; const T = BAG[b.tier].time; if (!b.start) return T; return Math.max(0, b.start + T * 1000 - now) / 1000; }
export const bagReady = (b, now) => !!b && (b.open || (!!b.start && bagLeft(b, now) <= 0));
export const bagBusy = (p, now) => p.bags.some(x => x && x.start && !x.open && bagLeft(x, now) > 0);
export const speedCost = (b, now) => Math.max(1, Math.ceil(bagLeft(b, now) / 3600 * GEM_PRICES.skipPerHour));
export const freeGift = now => SHOP.free[new Date(now).getUTCDay() % SHOP.free.length];
export function wbag(p, now) { const today = p.wbag.day === dayOf(now), ws = today ? p.wbag.ws : 0, claimed = today && p.wbag.claimed; return {ws, need: W_BAG.need, tier: W_BAG.tier, claimed, ready: ws >= W_BAG.need && !claimed}; }
export const roadClaimable = p => ROAD.filter(r => p.best >= r.at && !p.road.includes(r.at)).map(r => r.at);
export function arenaPack(p, now) { const a = p.shop?.arenaPack; return a && !a.bought && a.until > now ? {arena: a.arena, until: a.until, usd: SHOP.arenaPack.usd, gives: SHOP.arenaPack.gives} : null; }
// what a page may see of a profile: everything but the wallet's full address
export function view(p) { const o = JSON.parse(JSON.stringify(p)); if (o.wallet) o.wallet = {a: short(o.wallet.a || ''), tied: o.wallet.tied || 0}; if (o.stats) { delete o.stats.pvp; delete o.stats.bots; } return o; }
export const short = a => a ? a.slice(0, 4) + '…' + a.slice(-4) : '';

// ---------------------------------------------------------------- the day: shop deals, the free gift, the W bag
export function refresh(p, now) {
  const day = dayOf(now); let changed = false;
  if (p.shop.day !== day) { p.shop = {day, free: false, bought: [], deals: makeDeals(p, day), arenaPack: p.shop.arenaPack && p.shop.arenaPack.until > now && !p.shop.arenaPack.bought ? p.shop.arenaPack : null}; changed = true; }
  if (p.wbag.day !== day) { p.wbag = {day, ws: 0, claimed: false}; changed = true; }
  return changed;
}
// SHOP.dailySlots card offers, the same all day for this player (seeded by his id and the day), from the cards he owns
export function makeDeals(p, day) {
  const R = seeded(hash32(p.id + '|' + day + '|deals')), owned = Object.keys(p.cards).filter(id => CARDS[id]), out = [];
  const have = RARITIES.filter(r => owned.some(id => CARDS[id].rarity === r));
  for (let k = 0; k < SHOP.dailySlots && owned.length; k++) {
    let id = null, r = null;
    for (let tries = 0; tries < 6; tries++) {
      let x = R() * have.reduce((s, q) => s + SHOP.dealOdds[q], 0); r = have[have.length - 1];
      for (const q of have) { x -= SHOP.dealOdds[q]; if (x < 0) { r = q; break; } }
      id = pickOf(R, owned.filter(c => CARDS[c].rarity === r));
      if (!out.some(o => o.id === id)) break;
    }
    const n = pickOf(R, SHOP.dealQty[r]);
    out.push({slot: k, id, n, coins: SHOP.copyCoins[r] * n});
  }
  return out;
}

// ---------------------------------------------------------------- unlocks, XP
// the cards the bags can hold: every card of the arenas I have reached (found or not yet)
export const findable = p => ARENAS.slice(0, (p.reached | 0) + 1).flatMap(A => A.unlock).filter(id => CARDS[id]);
// a NEW best arena puts its cards in the bags (-> those cards, to show them) and opens its pack offer for 24 h
export function unlockTo(p, clout, now = 0, quiet = false) {
  const was = p.reached | 0, idx = Math.max(0, ARENAS.findLastIndex(A => clout >= A.at)), got = [];
  if (idx > was) { for (let i = was + 1; i <= idx; i++) got.push(...ARENAS[i].unlock); p.reached = idx; if (!quiet) p.shop.arenaPack = {arena: ARENAS[idx].id, until: now + ECON.arenaPackMs, bought: false}; }
  return got;
}
// n copies of a card: the first one ever found is the card itself (level 1), the rest count towards its upgrade -> new?
function gain(p, id, n) {
  if (p.cards[id]) { p.cards[id].copies += n; return false; }
  p.cards[id] = {lvl: 1, copies: Math.max(0, n - 1)}; return true;
}
export function addXp(p, n) {
  const from = p.level; p.xp += Math.max(0, n | 0);
  while (p.level < MAX_LVL && p.xp >= XP.need[p.level + 1]) { p.xp -= XP.need[p.level + 1]; p.level++; }
  return p.level - from;
}

// ---------------------------------------------------------------- bags
// what's inside: coins + card copies split across a few cards of the arenas reached (findable), weighted by rarity; a few gems
// in the bigger bags. A card not found yet is picked a little more often (FIND), so a new arena's cards turn up within a few bags
export const FIND = 0.35;
export function roll(p, tier, rand) {
  const T = BAG[tier], can = findable(p), drops = [];
  const pick = r => {
    const pool = can.filter(id => CARDS[id].rarity === r); if (!pool.length) return null;
    const unfound = pool.filter(id => !p.cards[id] && !drops.some(d => d.id === id));
    return unfound.length && rand() < FIND ? pickOf(rand, unfound) : pickOf(rand, pool);
  };
  const add = (id, n) => { if (!id || n <= 0) return; const d = drops.find(x => x.id === id); if (d) d.n += n; else drops.push({id, n, isNew: false}); };
  let left = T.cards;
  const legN = rand() < T.legendary ? 1 : 0, epicN = Math.floor(T.epic) + (rand() < T.epic % 1 ? 1 : 0), rareN = Math.round(T.cards * 0.18 * Math.min(1, T.rare + 0.2));
  if (legN) { const id = pick('legendary'); if (id) { add(id, 1); left--; } }
  for (let k = 0; k < epicN; k++) { const id = pick('epic'); if (id) { add(id, 1); left--; } }
  const rare = Math.min(left, rareN);
  for (const n of [Math.ceil(rare / 2), rare - Math.ceil(rare / 2)]) { const id = n > 0 ? pick('rare') : null; if (id) { add(id, n); left -= n; } }
  const commons = [pick('common'), pick('common'), pick('common')].filter(Boolean);
  commons.forEach((id, k) => add(id, k < commons.length - 1 ? Math.round(left / commons.length) : left - Math.round(left / commons.length) * (commons.length - 1)));
  for (const d of drops) { d.isNew = gain(p, d.id, d.n) || p.seen[d.id] === false; delete p.seen[d.id]; }
  const coins = T.cash[0] + Math.floor(rand() * (T.cash[1] - T.cash[0])); p.coins += coins;
  const [gc, g0, g1] = T.gems, gems = gc > 0 && rand() < gc ? g0 + Math.floor(rand() * (g1 - g0 + 1)) : 0; p.gems += gems;
  drops.sort((a, c) => RARITIES.indexOf(CARDS[a.id].rarity) - RARITIES.indexOf(CARDS[c.id].rarity));
  return {tier, coins, cash: coins, gems, drops};
}
// what a reward says ({coins, gems, bag, card: [id, n], cards: rarity, n}) -> applied; -> {coins, gems, bag (its roll), card}
function give(p, g, rand, now) {
  const got = {};
  if (g.coins) { p.coins += g.coins; got.coins = g.coins; }
  if (g.gems) { p.gems += g.gems; got.gems = g.gems; }
  if (g.card) { const [id, n] = g.card; if (CARDS[id]) { if (gain(p, id, n)) p.seen[id] = false; got.card = [id, n]; } }
  // (copies of a card I own of that rarity; none yet: one of the bags' cards of it)
  if (g.cards) {
    const mine = Object.keys(p.cards).filter(id => CARDS[id]?.rarity === g.cards), pool = mine.length ? mine : findable(p).filter(id => CARDS[id].rarity === g.cards);
    const id = pool.length ? pool[Math.floor(seeded(hash32(p.id + dayOf(now) + 'gift'))() * pool.length)] : null;
    if (id) { if (gain(p, id, g.n)) p.seen[id] = false; got.card = [id, g.n]; }
  }
  if (g.bag && BAG[g.bag]) got.bag = roll(p, g.bag, rand);
  return got;
}

// ---------------------------------------------------------------- the actions
// a player's name: NFKC, letters, digits, space, _ . -; ECON.nameMin to nameMax characters; '' when nothing usable is left
export function cleanName(n) { const s = String(n ?? '').normalize('NFKC').replace(/[^\p{L}\p{N} _.\-]/gu, '').replace(/\s+/g, ' ').trim(); return s.length >= ECON.nameMin && s.length <= ECON.nameMax ? s : ''; }
const ACTS = {
  setName(p, a) {
    const s = cleanName(a.name); if (!s) return no(`A name of ${ECON.nameMin} to ${ECON.nameMax} letters or digits, please.`);
    p.name = s; return {ok: true, name: s};
  },
  setAvatar(p, a) {
    const id = a.id; if (!(typeof id === 'string' && AVATARS.includes(id) && Object.hasOwn(p.cards, id))) return no('Pick a character you own.');
    p.avatar = id; return {ok: true, avatar: id};
  },
  setDeck(p, a) {
    const slot = int(a.slot); if (!(slot >= 0 && slot < ECON.decks)) return no('No such deck.');
    if (a.cards != null) {
      const d = a.cards; if (!Array.isArray(d) || d.length !== ECON.deck) return no(`A deck is ${ECON.deck} cards.`);
      if (new Set(d).size !== d.length) return no('A card can be in a deck once.');
      if (!d.every(id => typeof id === 'string' && Object.hasOwn(p.cards, id))) return no('You do not own every card of that deck.');
      p.decks[slot] = [...d];
    }
    if (a.active === true || a.cards == null) p.active = slot;
    return {ok: true, slot, active: p.active};
  },
  upgrade(p, a) {
    const id = String(a.id ?? ''); if (!Object.hasOwn(p.cards, id)) return no('You do not own that card.');
    const u = canUpgrade(p, id); if (!u) return no('That card is at its max level.');
    if (p.cards[id].copies < u.n) return no(`It takes ${u.n} copies.`); if (p.coins < u.cost) return no('Not enough coins.');
    const c = p.cards[id]; c.copies -= u.n; p.coins -= u.cost; c.lvl++;
    const up = addXp(p, XP.upgrade[c.lvl] || 0);
    return {ok: true, id, lvl: c.lvl, xp: XP.upgrade[c.lvl] || 0, levelUp: up > 0 ? p.level : 0};
  },
  startBag(p, a, {now}) {
    const i = int(a.i), b = p.bags[i]; if (!b) return no('No bag there.'); if (bagReady(b, now)) return no('That bag is ready: open it.');
    if (b.start) return no('That bag is already unlocking.'); if (bagBusy(p, now)) return no('Another bag is unlocking.');
    b.start = now; return {ok: true, i, left: bagLeft(b, now)};
  },
  speedBag(p, a, {now}) {
    const i = int(a.i), b = p.bags[i]; if (!b) return no('No bag there.'); if (bagReady(b, now)) return no('That bag is ready: open it.');
    const cost = speedCost(b, now); if (p.gems < cost) return no(`It takes ${cost} gems.`);
    p.gems -= cost; b.open = true; return {ok: true, i, gems: cost};
  },
  openBag(p, a, {now, rand}) {
    const i = int(a.i), b = p.bags[i]; if (!b) return no('No bag there.'); if (!bagReady(b, now)) return no('That bag is still locked.');
    p.bags[i] = null; return {ok: true, i, bag: roll(p, b.tier, rand)};
  },
  claimRoad(p, a, {now, rand}) {
    const at = int(a.at), R = ROAD.find(r => r.at === at); if (!R) return no('No reward there.');
    if (p.best < at) return no(`Reach ${at} Clout first.`); if (p.road.includes(at)) return no('Already claimed.');
    p.road.push(at); return {ok: true, at, got: give(p, R.gives, rand, now)};
  },
  claimFree(p, a, {now, rand}) {
    if (p.shop.free) return no('Today\'s gift is claimed. Come back tomorrow.');
    p.shop.free = true; return {ok: true, got: give(p, freeGift(now), rand, now)};
  },
  buyDeal(p, a) {
    const slot = int(a.slot), D = p.shop.deals[slot]; if (!D) return no('No such deal.');
    if (p.shop.bought.includes(slot)) return no('Sold out.'); if (!p.cards[D.id]) return no('No such deal.');
    if (p.coins < D.coins) return no('Not enough coins.');
    p.coins -= D.coins; p.cards[D.id].copies += D.n; p.shop.bought.push(slot); return {ok: true, slot, got: {card: [D.id, D.n]}, coins: D.coins};
  },
  buyBag(p, a, {now, rand}) {
    const B = SHOP.bags.find(b => b.tier === a.tier); if (!B) return no('No such bag.'); if (p.gems < B.gems) return no(`It takes ${B.gems} gems.`);
    p.gems -= B.gems; return {ok: true, tier: B.tier, gems: B.gems, bag: roll(p, B.tier, rand)};
  },
  buyCoins(p, a) {
    const C = SHOP.coinPacks.find(c => c.id === a.id); if (!C) return no('No such pack.'); if (p.gems < C.gems) return no(`It takes ${C.gems} gems.`);
    p.gems -= C.gems; p.coins += C.coins; return {ok: true, id: C.id, gems: C.gems, got: {coins: C.coins}};
  },
  buyCosmetic(p, a) {
    const C = SHOP.cosmetics.find(c => c.id === a.id); if (!C) return no('No such item.'); if (p.cosmetics.own.includes(C.id)) return no('You own it already.');
    if (p.gems < C.gems) return no(`It takes ${C.gems} gems.`);
    p.gems -= C.gems; p.cosmetics.own.push(C.id); if (C.kind === 'tower' && !p.cosmetics.tower) p.cosmetics.tower = C.id;
    return {ok: true, id: C.id, gems: C.gems};
  },
  claimWBag(p, a, {now, rand}) {
    const W = wbag(p, now); if (W.claimed) return no('Today\'s W bag is claimed.'); if (!W.ready) return no(`${W.ws} of ${W.need} Ws today.`);
    p.wbag.claimed = true; return {ok: true, bag: roll(p, W.tier, rand)};
  },
  tutDone(p) { p.tut = true; return {ok: true}; },             // the first battle's tutorial was shown
};
export const ACTIONS = Object.keys(ACTS);
// one action, validated; all or nothing (each rule checks everything before it changes anything)
export function act(p, a, {now = 0, rand = () => 0.5} = {}) {
  const f = a && typeof a.a === 'string' && Object.hasOwn(ACTS, a.a) ? ACTS[a.a] : null; if (!f) return no('Unknown action.');
  refresh(p, now);
  return f(p, a, {now, rand});
}

// ---------------------------------------------------------------- after a battle
export function result(p, {win, ws = 0, oppClout = 0, now = 0, bot = false} = {}) {
  refresh(p, now);
  const before = p.clout, A0 = arenaOf(before);
  ws = Math.max(0, Math.min(3, ws | 0));
  let dc = 0;
  if (win === 1) { dc = 28 + Math.max(-6, Math.min(6, Math.round((oppClout - before) / 40))) + (ws === 3 ? 3 : 0); p.stats.wins++; p.stats.lstreak = 0; }
  else if (win === 0) { dc = -22; p.stats.losses++; p.stats.lstreak = (p.stats.lstreak | 0) + 1; }
  else p.stats.draws++;
  p.clout = Math.max(A0.at, before + dc); dc = p.clout - before;      // never below the floor of the arena I was in
  p.best = Math.max(p.best, p.clout); p.stats.ws += ws; p.stats.played++; if (bot) p.stats.bots++; else p.stats.pvp++;
  const coins = win === 1 ? 20 + ws * 6 : 0; p.coins += coins;       // a draw: no Clout, no coins, no bag (the Ws still count)
  let bag = null, slot = -1;
  if (win === 1) { slot = p.bags.findIndex(b => !b); if (slot >= 0) { bag = BAG_CYCLE[p.bagN % BAG_CYCLE.length]; p.bagN++; p.bags[slot] = {tier: bag, open: false, start: null}; } }
  const xp = win === 1 ? XP.win : XP.loss, levelUp = addXp(p, xp);
  if (!p.wbag.claimed) p.wbag.ws += ws;
  const unlocked = unlockTo(p, p.clout, now), A1 = arenaOf(p.clout);
  return {win, ws, dc, coins, cash: coins, bag, slot, unlocked, arena: A1.id !== A0.id ? A1 : null, league: A1.id !== A0.id ? A1 : null, clout: p.clout,
    xp, level: p.level, levelUp: levelUp > 0, wbag: wbag(p, now)};
}

// a FRIENDLY battle changes nothing but the count (no Clout, coins, bag, XP or W bag)
export function friendly(p, {win, ws = 0} = {}) { p.stats.friendly = (p.stats.friendly | 0) + 1; return {win, ws, friendly: true, dc: 0, coins: 0, cash: 0, bag: null, slot: -1, unlocked: [], arena: null, league: null, clout: p.clout, xp: 0, level: p.level, levelUp: false}; }

// ---------------------------------------------------------------- real money (the server prices it, a wallet pays, the chain says so)
export function priceOf(p, kind, id, now) {
  if (kind === 'gems') { const G = GEM_PACKS.find(g => g.id === id); return G ? G.usd : {why: 'No such pack.'}; }
  if (kind === 'offer') { const O = OFFERS.find(o => o.id === id); if (!O) return {why: 'No such offer.'}; if (O.once && p.offers[id]) return {why: 'You bought this offer already.'}; return O.usd; }
  if (kind === 'arena') { const A = arenaPack(p, now); return A && A.arena === id ? SHOP.arenaPack.usd : {why: 'This offer has ended.'}; }
  return {why: 'Nothing like that is for sale.'};
}
export function label(kind, id) {
  if (kind === 'gems') return GEM_PACKS.find(g => g.id === id)?.label || id;
  if (kind === 'offer') return OFFERS.find(o => o.id === id)?.label || id;
  if (kind === 'arena') return 'ARENA PACK ' + (ARENAS.find(a => a.id === id)?.name || id);
  return id;
}
// a confirmed payment -> its items, ONCE per ref (a ref already in purchases is not given again: the server can replay safely)
export function grant(p, {kind, id, ref, usd = 0, now = 0, rand = () => 0.5} = {}) {
  if (p.purchases.some(x => x.ref === ref)) return {ok: true, dup: true, got: {}};
  let g = null;
  if (kind === 'gems') { const G = GEM_PACKS.find(x => x.id === id); if (G) g = {gems: G.gems}; }
  else if (kind === 'offer') { const O = OFFERS.find(x => x.id === id); if (O) { g = O.gives; p.offers[id] = now; } }
  else if (kind === 'arena') { g = SHOP.arenaPack.gives; if (p.shop.arenaPack?.arena === id) p.shop.arenaPack.bought = true; }
  if (!g) return no('Nothing like that is for sale.');
  const got = give(p, g, rand, now);
  p.purchases.push({ref, kind, id, usd, at: now}); if (p.purchases.length > ECON.purchasesKept) p.purchases.splice(0, p.purchases.length - ECON.purchasesKept);
  return {ok: true, got};
}

// ---------------------------------------------------------------- a bot opponent around my Clout
// MATCHMAKING (the genre's way): a player on a losing streak gets an easier bot at once, to break it; a new player and the first
// two arenas get a bot after a short look for a person (they learn on bots more often); everyone else after a long wait.
export const MATCH_PLAN = {streak: 3, streakMs: 1500, newBattles: 5, newMs: 3000, lowArenas: 2, lowMs: 4000, longMs: 8000};
export function matchPlan(p) {
  const M = MATCH_PLAN, s = p.stats || {};
  if ((s.lstreak | 0) >= M.streak) return {botMs: M.streakMs, solo: true, easy: true, why: 'streak'};
  if ((s.played | 0) < M.newBattles) return {botMs: M.newMs, solo: false, easy: (s.played | 0) < 2, why: 'new'};
  if (ARENAS.indexOf(arenaOf(p.clout)) < M.lowArenas) return {botMs: M.lowMs, solo: false, easy: false, why: 'low'};
  return {botMs: M.longMs, solo: false, easy: false, why: 'wait'};
}
export function botOpponent(p, rand, {easy = false} = {}) {
  const clout = Math.max(0, p.clout + Math.round((rand() - (easy ? 0.8 : 0.5)) * 120));
  const pool = []; for (const A of ARENAS) if (clout + 200 >= A.at) pool.push(...A.unlock);
  const units = pool.filter(id => CARDS[id].type === 'unit'), spells = pool.filter(id => CARDS[id].type === 'spell');
  const sh = a => a.map(v => [rand(), v]).sort((x, y) => x[0] - y[0]).map(v => v[1]);
  const deck = [...sh(spells).slice(0, 2), ...sh(units)].slice(0, ECON.deck);
  const win = units.filter(id => CARDS[id].unit.bOnly); if (win.length && !deck.some(id => CARDS[id].unit?.bOnly)) deck[deck.length - 1] = win[Math.floor(rand() * win.length)];
  const mine = deckOf(p).map(id => p.cards[id]?.lvl || 1), avg = Math.round(mine.reduce((a, b) => a + b, 0) / mine.length) || 1;
  // an easy bot: a level down and a slower, sloppier hand
  const lv = {}; for (const id of deck) lv[id] = Math.max(1, Math.min(MAX_LVL, avg - (easy ? 1 : 0) + (rand() < 0.3 ? -1 : 0)));
  const level = Math.max(1, Math.min(MAX_LVL, towerLvl(p) - (easy ? 1 : 0) + (rand() < 0.3 ? -1 : 0)));
  return {name: BOT_NAMES[Math.floor(rand() * BOT_NAMES.length)], clout, deck, levels: lv, towerLvl: level, level, skill: Math.min(0.95, 0.18 + clout / 3000) * (easy ? 0.55 : 1),
    arena: arenaOf(clout).id, avatar: deck.find(id => AVATARS.includes(id)) || AVATARS[Math.floor(rand() * AVATARS.length)], bot: true};
}
