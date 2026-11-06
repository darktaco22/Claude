// MEME ROYALE — ONE CONNECTION TO THE GAME SERVER (server.mjs; the protocol is docs/PROTOCOL.md), in a page or under Node (both have
// a global WebSocket). No DOM needed, no three.js. It says hello with this browser's identity, comes back by itself when the line
// drops (backoff 0.5 s .. 10 s), answers requests by their number, and hands on what the server pushes. src/net/README.md shows
// how the game uses it. ONE PAGE PER PROFILE: hello carries this page's own id (sid, new each load) and re on its own reconnects;
// when another page takes the profile, this one gets 'bye' {took} and stops for good (it never takes it back by itself).
//
//   const url = wanted()            the server's /net address, or null: the page plays offline (tools/serve.mjs, ?offline)
//   const c = new Client({url, token: token()});  const you = await c.connect()      you: {key, p, now, pay, match}; throws Error(why)
//   c.state   'connecting' | 'online' | 'offline'     c.on('status', ({state, why}) => ...)   c.online
//   c.profile (the newest)   c.onProfile(p => ...) -> off       c.serverNow()  (the server's clock in ms: bag timers)
//   await c.act({a: 'upgrade', id}) -> {ok, ...} | {ok: false, why}        (every economy action: src/shared/economy.js act)
//   await c.queue() / c.cancel()          -> {ok, ...}; the battle comes as the 'start' event
//   await c.friend.create() -> {ok, code, expires}   c.friend.join(code) -> {ok}   c.friend.cancel()
//   c.on('start', m)  'snap'  'r'  'emote'  'opp'  'result'  'profile'  'bye'  ... (src/net/netbattle.js listens to these)
//   c.play(slot, x, z, card) -> n (fire and forget: refusals come as 'r' {n, ok: false})   c.emote(id)
//   c.wallet.ask() / tie({address, sig, nonce}) / drop() / hand()     c.buy(kind, id, {manual, cur, link}) -> an order     c.paid(ref, tx, quick)     c.orders()   (src/net/wallet.js)
//   hand: a one-time code from wallet.hand() (a link that opens this profile in a wallet's own browser): new Client({url, token: newToken(), hand: code, prev: token()})
//         takes the profile with a new secret; when the code is out of date the page goes on as `prev` (c.handLost)
//   ACCOUNTS: await c.account.create(name, pass) -> {ok, name} (this profile gets the name; p.account becomes true)
//             await c.account.login(name, pass) -> {ok, name, you}: the account's secret is kept ('memeroyale.id') and the line comes
//                   back as that account (its profile arrives as usual)     await c.account.changePass(old, new) -> {ok}
//             await c.account.logout() -> {ok}: this page forgets the secret and comes back as a NEW guest
//   await c.top() -> {ok, rows: [{rank, name, clout, level, arena, wins}] (top 100 accounts by Clout), me: row | null, of}
//   c.close()
import {SnapReader} from '../shared/snap.js';
const ID_KEY = 'memeroyale.id';
const get = k => { try { return globalThis.localStorage?.getItem(k) || ''; } catch { return ''; } };
const put = (k, v) => { try { globalThis.localStorage?.setItem(k, v); return !!globalThis.localStorage; } catch { return false; } };

export function newToken() { const b = new Uint8Array(16); globalThis.crypto.getRandomValues(b); return [...b].map(x => x.toString(16).padStart(2, '0')).join(''); }
// who I am: 32 random hex kept by this browser (a browser that keeps nothing gets one for this page only)
let mem = '';
export function token() { let t = get(ID_KEY); if (/^[a-f0-9]{32}$/.test(t)) return t; t = mem || newToken(); if (!put(ID_KEY, t)) mem = t; return t; }
// the server's address, or null when the page plays alone: ?offline; ?net=ws://host:port/net (a page served by tools/serve.mjs);
// else the <meta name="memeroyale-net"> line server.mjs writes into the page
export function wanted(loc = globalThis.location, doc = globalThis.document) {
  if (!loc || !doc) return null;
  const Q = new URLSearchParams(loc.search || '');
  if (Q.has('offline')) return null;
  const q = Q.get('net'); if (q && /^wss?:\/\/[^\s]+$/.test(q)) return q;
  const meta = doc.querySelector?.('meta[name="memeroyale-net"]'); if (!meta) return null;
  const p = String(meta.getAttribute('content') || '/net'); if (!/^\/[A-Za-z0-9_\-/]*$/.test(p)) return null;
  return (loc.protocol === 'https:' ? 'wss://' : 'ws://') + loc.host + p;
}

const BACKOFF = [500, 1000, 2000, 4000, 8000, 10000];
export class Client {
  constructor({url, token: tok = token(), hand = '', prev = '', WS = globalThis.WebSocket, timeout = 10000} = {}) {
    this.url = url; this.token = tok; this.hand = hand; this.prev = prev; this.handLost = false; this.WS = WS; this.timeout = timeout;
    this.ws = null; this.L = new Map(); this.n = 0; this.wait = new Map(); this.tries = 0; this.timer = null; this.closed = false;
    this.state = 'offline'; this.why = ''; this.you = null; this.profile = null; this.match = null; this.offset = 0; this.pingT = null; this.pongAt = 0;
    this.sid = newToken(); this.claim = true;   // (claim: the next hello is this page asking for the profile, not a reconnect)
    this.friend = {create: () => this.request({t: 'friend', create: 1}), join: code => this.request({t: 'friend', join: String(code || '')}), cancel: () => this.request({t: 'friend', cancel: 1})};
    this.wallet = {ask: () => this.request({t: 'wallet', ask: 1}), tie: ({address, sig, nonce}) => this.request({t: 'wallet', address, sig, nonce}), drop: () => this.request({t: 'wallet', drop: 1}), hand: () => this.request({t: 'wallet', hand: 1})};
    this.account = {
      create: (name, pass) => this.request({t: 'account', create: {name, pass}}),
      login: async (name, pass) => { const r = await this.request({t: 'account', login: {name, pass}}); if (!r.ok || !r.token) return r; return {...r, you: await this.switchTo(r.token)}; },
      changePass: (old, nw) => this.request({t: 'account', pass: {old, new: nw}}),
      logout: async () => { const r = await this.request({t: 'account', logout: 1}); if (!r.ok) return r; return {...r, you: await this.switchTo(newToken())}; },
    };
    this.snaps = new SnapReader();
    this.on('profile', m => this.setProfile(m.p, m.now));
    this.on('start', m => { this.match = m; });
    this.on('result', () => { this.match = null; });
    if (typeof addEventListener === 'function' && typeof window !== 'undefined') {
      addEventListener('online', () => { if (!this.closed && this.state !== 'online') { clearTimeout(this.timer); this.tries = 0; this.open(); } });
      addEventListener('offline', () => this.status('offline', 'This device is offline.'));
    }
  }
  get online() { return this.state === 'online'; }
  on(t, f) { let s = this.L.get(t); if (!s) this.L.set(t, s = new Set()); s.add(f); return () => this.off(t, f); }
  off(t, f) { this.L.get(t)?.delete(f); }
  emit(t, m) { const s = this.L.get(t); if (s) for (const f of [...s]) { try { f(m); } catch (e) { console.error('[net] ' + t + ' handler', e); } } }
  onProfile(f) { if (this.profile) { try { f(this.profile); } catch (e) { console.error(e); } } return this.on('profile!', f); }
  setProfile(p, now) { if (!p) return; this.profile = p; if (Number.isFinite(now)) this.offset = now - Date.now(); this.emit('profile!', p); }
  serverNow() { return Date.now() + this.offset; }
  status(state, why = '') { if (this.state === state && this.why === why) return; this.state = state; this.why = why; this.emit('status', {state, why}); }
  send(m) { if (!this.ws || this.ws.readyState !== 1) return false; this.ws.send(typeof m === 'string' ? m : JSON.stringify(m)); return true; }

  // the first connection: resolves with `you` or throws why it could not; after it, a dropped line comes back by itself
  connect() { this.closed = false; this.claim = true; return new Promise((res, rej) => { this.first = {res, rej}; this.open(); }); }
  open() {
    if (this.closed) return;
    clearTimeout(this.timer); this.status('connecting');
    let ws; try { ws = this.ws = new this.WS(this.url); } catch { return this.lost('The server cannot be reached.'); }
    const tm = setTimeout(() => { if (this.ws === ws && this.state !== 'online') { try { ws.close(); } catch {} } }, this.timeout);
    ws.onopen = () => this.send({t: 'hello', token: this.token, v: 2, sid: this.sid, ...(this.claim ? {} : {re: 1}), ...(this.hand ? {hand: this.hand} : {})});
    ws.onmessage = e => {
      if (this.ws !== ws || typeof e.data !== 'string') return;
      let m; try { m = JSON.parse(e.data); } catch { return; }
      if (!m || typeof m.t !== 'string') return;
      if (m.t === 'you') {
        clearTimeout(tm); this.you = m; this.tries = 0; this.claim = false; this.setProfile(m.p, m.now); this.status('online');
        if (this.hand) { this.hand = ''; mem = this.token; put(ID_KEY, this.token); }   // (the hand-over worked: this page's identity from now on)
        if (!m.match) this.match = null;
        this.beat(); if (this.first) { this.first.res(m); this.first = null; }
      } else if (m.t === 'err' && m.re === 'hello' && m.hand && this.prev) {   // (a link out of date: this browser's own identity, as if there had been no link)
        clearTimeout(tm); this.hand = ''; this.handLost = true; this.token = this.prev; this.ws = null; try { ws.close(); } catch {} this.open(); return;
      } else if (m.t === 'err' && m.re === 'hello') { this.stop(String(m.why || 'Refused.')); return; }
      else if (m.t === 'bye' && !m.back) { this.emit('bye', m); this.stop(String(m.why || 'Disconnected.')); return; }
      else if (m.t === 'pong') { this.pongAt = Date.now(); if (Number.isFinite(m.now)) this.offset = m.now - Date.now(); }
      else if (m.t === 'start') { this.snaps = new SnapReader(); this.snaps.start(m.snap, m.mine); }
      else if (m.t === 'snap') this.snaps.read(m);   // (whole again, whatever the server left out: here, so a snapshot no battle screen is listening to yet still counts)
      if (m.t === 'r' || (m.n != null && m.t === 'friend')) { const w = this.wait.get(m.n); if (w) { this.wait.delete(m.n); clearTimeout(w.t); w.res(m); } }
      this.emit(m.t, m);
    };
    ws.onclose = () => { clearTimeout(tm); if (this.ws !== ws) return; this.ws = null; this.lost(this.why || 'The connection to the server dropped.'); };
    ws.onerror = () => {};
  }
  lost(why) {
    clearInterval(this.pingT); this.pingT = null;
    for (const w of this.wait.values()) { clearTimeout(w.t); w.res({ok: false, net: true, why: 'The connection to the server dropped.'}); } this.wait.clear();
    if (this.closed) return;
    if (this.first && this.tries >= 2) { const f = this.first; this.first = null; this.status('offline', why); f.rej(new Error('The server cannot be reached.')); }
    this.status('offline', why);
    const ms = BACKOFF[Math.min(this.tries++, BACKOFF.length - 1)] * (0.8 + Math.random() * 0.4);
    this.timer = setTimeout(() => this.open(), ms);
  }
  stop(why) { this.closed = true; clearTimeout(this.timer); clearInterval(this.pingT); try { this.ws?.close(1000); } catch {} this.ws = null; this.status('offline', why); if (this.first) { this.first.rej(new Error(why)); this.first = null; } }
  close() { this.stop('closed'); }
  // a ping every 15 s; no pong for 35 s: the line is dead (a phone that slept), it is closed and opened again
  beat() {
    clearInterval(this.pingT); this.pongAt = Date.now();
    this.pingT = setInterval(() => { if (Date.now() - this.pongAt > 35000) { try { this.ws?.close(); } catch {} return; } this.send({t: 'ping', c: Date.now()}); }, 15000);
  }
  // a request: m gets a number, the answer {t: 'r', n, ok, ...} resolves it ({ok: false, why} when it cannot be sent or comes too late)
  request(m, ms = 15000) {
    const n = ++this.n;
    return new Promise(res => {
      if (!this.send({...m, n})) { res({ok: false, net: true, why: 'Not connected to the server.'}); return; }
      this.wait.set(n, {res, t: setTimeout(() => { this.wait.delete(n); res({ok: false, net: true, why: 'The server did not answer.'}); }, ms)});
    });
  }
  act(a) { return this.request({...a, t: 'act'}); }
  top() { return this.request({t: 'top'}); }
  // another identity for this page (a login, a logout): kept in localStorage, and the line opened again with it -> the new `you`
  switchTo(tok) {
    this.token = tok; mem = tok; put(ID_KEY, tok);
    return new Promise(res => {
      const off = this.on('you', m => { off(); clearTimeout(tm); res(m); }), tm = setTimeout(() => { off(); res(null); }, 15000);
      const ws = this.ws; this.ws = null; try { ws?.close(1000); } catch {}
      clearTimeout(this.timer); this.tries = 0; this.claim = true; this.open();
    });
  }
  queue() { return this.request({t: 'queue'}); }
  cancel() { return this.request({t: 'cancel'}); }
  play(slot, x, z, card) { const n = ++this.n; return this.send({t: 'play', slot, x, z, card, n}) ? n : 0; }
  emote(id) { return this.send({t: 'emote', id}); }
  buy(kind, id, {manual = false, cur = '', link = false} = {}) { return this.request({t: 'buy', kind, id, manual: !!manual, cur, link: !!link}, 30000); }
  paid(ref, tx = '', quick = false) { return this.request({t: 'paid', ref, tx, quick: !!quick}, 60000); }
  orders() { return this.request({t: 'orders'}); }
}
