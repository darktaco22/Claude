// Card faces shared by the HUD and the menus.
import {CARDS, AVATARS} from '../data.js';

// Images drawn small (grids, avatars, icons, pills) use their small copy (tools/ui/thumbs.py: a sm/ folder next to the
// image, badge_sm.webp for an arena's badge); big views (the card sheet, the bag opening) ask for the full one. A copy that
// is missing is answered with the full image by the servers.
export const cardArt = (id, big) => `assets/cards/${big ? '' : 'sm/'}${id}.webp?v=2`;   // v=2: the close-up set (2026-10-29)
// an arena's badge (its emblem when the art is there, else its league title's badge) and the small title badge
export const titleBadge = A => `assets/ui/sm/league_${(A.title || A.id).toLowerCase()}.webp`;
// a player's picture: the character's portrait (anything else, an old pick or a missing one: the Trollface)
export const avatarArt = (id, big) => `assets/ui/avatars/${big ? '' : 'sm/'}${AVATARS.includes(id) ? id : 'troll'}.webp`;
// an arena's diorama (a painted miniature, ARENAS.md), or its dimmed copy while it's locked (tools/ui/thumbs.py: dimmed
// there, not by a CSS filter, which a phone repaints on every scroll); bump the version when they are replaced, so phones
// drop the old ones
export const dioramaOf = (A, locked) => `assets/arenas/${A.id}/diorama${locked ? '_locked' : ''}.webp?v=5`;
export const arenaBadge = (A, big) => `<img src="assets/arenas/${A.id}/badge${big ? '' : '_sm'}.webp" onerror="this.onerror=null;this.src='${titleBadge(A)}'" alt="">`;
export const h = (tag, cls = '', html = '') => { const e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; };

export function cardEl(id, {lvl, cost = true, name = true, cls = '', big = false} = {}) {
  const c = CARDS[id], e = h('div', `card ${c.rarity} ${cls}`);
  e.dataset.id = id;
  if (c.rarity === 'legendary') e.append(h('i', 'rim'));   // the gold frame of its own shape (style.css .card.legendary)
  const art = h('div', 'art'); art.style.backgroundImage = `url(${cardArt(id, big)}), linear-gradient(160deg, #371A69, #1B0D34)`;
  e.append(art);
  if (cost) { e.append(h('div', 'costw'), h('div', 'cost', String(c.cost))); }
  if (name) e.append(h('div', 'nm', c.name));
  if (lvl) e.append(h('div', 'lvl', 'LV ' + lvl));
  return e;
}

// Pictures kept loaded and decoded for the page's whole life. A menu screen is rebuilt on every tab switch and every
// profile change; a picture nothing holds can be dropped by the browser, and a phone then fetches (or revalidates) and
// decodes it again: the pop-in. warm() loads a list a few at a time (the menus' art, before the 3D side starts its
// downloads), keepIn() holds whatever a fresh screen shows (its <img>s and the cards' background art).
const KEPT = new Map();
const abs = u => new URL(u, location.href).href;
export function keep(url) {
  const u = abs(url); let im = KEPT.get(u);
  if (!im) { im = new Image(); im.decoding = 'async'; im.src = u; KEPT.set(u, im); }
  return im;
}
export function keepIn(root) {
  for (const e of root.querySelectorAll('img[src]')) if (!e.src.startsWith('data:')) keep(e.src);
  for (const e of root.querySelectorAll('[style*="url("]')) for (const m of e.style.backgroundImage.matchAll(/url\(["']?([^"')]+)/g)) keep(m[1]);
}
// (load, not decode(), is awaited: decode() never settles while the page draws no frames, a tab in the background; it
// is only asked for, so the picture is decoded before it is first shown)
const loaded = im => im.complete ? Promise.resolve() : new Promise(r => { im.addEventListener('load', r, {once: true}); im.addEventListener('error', r, {once: true}); });
// a kept picture once it has loaded and is decoded, or after ms (whichever comes first). Decoded again just before it
// shows, off the page's thread: a phone holding many pictures (the Trophy Road's) lets go of the decoded copy of one it
// hasn't drawn yet, and decoded it on the frame it first drew (a card's art: the first frame of its flight)
export const whenKept = (url, ms = 800) => { const im = keep(url); return Promise.race([loaded(im).then(() => im.decode()).catch(() => {}), new Promise(r => setTimeout(r, ms))]); };
export function warm(urls, n = 4) {
  const q = urls.map(abs).filter(u => !KEPT.has(u));
  const one = async () => { for (let u; (u = q.shift());) { const im = keep(u); await loaded(im); im.decode().catch(() => {}); } };
  return Promise.all(Array.from({length: n}, one));
}
