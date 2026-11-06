// Playing online (src/net/README.md): the line to the server, the server's profile in the store, real-money buys through a
// Solana wallet, friendly battles by code. Null when the page plays offline (no server, ?offline, or the server is down).
import {Client, wanted, token, newToken} from './net/client.js';
import {find, tie, payQuote, confirmed, devWallet, isPhone, chainOf, WALLET_APPS} from './net/wallet.js';
import {label as labelOf} from './shared/economy.js';
import {save} from './save.js';
import {h} from './ui/cards.js';
import {audio} from './audio.js';

const Q = new URLSearchParams(location.search);
// a link that hands this profile over to this browser (a wallet app's own browser, opened from another one): one time, and it leaves the address at once
const HAND = /^[a-f0-9]{32}$/.test(Q.get('hand') || '') ? Q.get('hand') : '';
if (Q.has('hand')) { Q.delete('hand'); try { history.replaceState(null, '', location.pathname + (Q.size ? '?' + Q : '')); } catch {} }
const WANT = 'memeroyale.walletName', SEEN = 'memeroyale.paidSeen';
const read = k => { try { return localStorage.getItem(k) || ''; } catch { return ''; } }, keep = (k, v) => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch {} };
const short = a => a ? a.slice(0, 4) + '…' + a.slice(-4) : '';
const clock = ms => { const s = Math.max(0, Math.ceil(ms / 1000)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
const tap = () => audio.play('ui_pop');

export class Online {
  static async connect(app) {
    const url = wanted(); if (!url) return null;
    const o = new Online(app, url);
    try { await Promise.race([o.start(), new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 8000))]); return o; }
    catch (e) { console.warn('[online] playing offline:', e?.message || e); o.client.close(); return null; }
  }
  constructor(app, url) { this.app = app; const mine = token(); this.client = new Client(HAND ? {url, token: newToken(), hand: HAND, prev: mine} : {url, token: mine}); this.waiting = new Map(); }
  async start() {
    const you = this.you = await this.client.connect();
    save.setRemote(a => this.client.act(a), you.p);
    save.clock = () => this.client.serverNow();
    this.client.onProfile(p => save.setProfile(p));
    this.client.on('status', ({state, why}) => this.app.netStatus?.(state, why));
    // a battle that was running (a reload, a dropped line): the server shows it again
    this.client.on('start', m => { if (!this.app.match) this.app.startOnline(m); });
    // another page took this profile (another device, another tab): this one stops for good (no offline battles either)
    this.client.on('bye', m => this.kicked(m));
    this.pay = you.pay || {on: false, why: 'Payments are off on this server.'};
    // a payment the server confirmed by itself: for the sheet that waits for it, or a word to the player; one that came while this page was away: at the next `you`
    this.client.on('order', m => this.order(m));
    this.client.on('you', m => { this.pay = m.pay || this.pay; this.arrived(m.p); });
    this.arrived(you.p);
    if (HAND) setTimeout(() => { const M = this.app.menus; if (this.client.handLost) M?.toast('That link has expired. Connect your wallet again from here.'); else if (!this.app.match) M?.hub('shop'); }, 600);
  }
  get online() { return this.client.online; }
  kicked(m) {
    if (this.byeEl) return;
    const A = this.app; if (A.match) { A.match.running = false; audio.stopMusic(0.6); audio.ambience(null); }
    // over everything (menus, sheets, the battle): only a reload gets this page back in, and it then takes the profile
    const S = this.byeEl = h('div', 'sheet'), box = h('div', 'panel box'); S.style.cssText = 'position:fixed;z-index:60';
    box.innerHTML = `<div style="text-align:center;display:grid;gap:8px"><h3 class="stroke-s">${m.took ? 'SIGNED IN ON ANOTHER DEVICE' : 'DISCONNECTED'}</h3><p></p></div>`;
    box.querySelector('p').textContent = m.took ? 'Your account is open somewhere else, so this page stopped. Play here instead? The other one will stop.' : String(m.why || 'The server closed this connection.');
    const a = h('div', 'acts'), b = h('button', 'btn small', m.took ? 'PLAY HERE' : 'RECONNECT'); b.onclick = () => location.reload(); a.append(b); box.append(a);
    S.append(box); document.body.append(S);
  }

  // ---------- real money: tie a wallet once (sign a text), then the wallet pays the order the server made. Each step that opens a
  // wallet starts from a tap of its own (a phone's browser opens another app only from a tap).
  get payWord() { return this.pay?.accept?.[0] === 'USDC' ? 'paid in USDC' : 'paid in SOL'; }
  async wallets() {
    if (Q.has('devwallet') && this.pay?.dev) {
      const W = this.dev ||= await devWallet(this.pay.devRpc);
      if (this.pay.mock && !this.devFed) { this.devFed = 1; await W.airdrop?.(50).catch(() => {}); }
      if (this.pay.cluster === 'devnet' && !this.devFed) { this.devFed = 1; if (await W.balance().catch(() => 1e12) < 2e8) await W.faucet(1).catch(e => console.warn('[wallet] no devnet airdrop', e)); }
      return [W];
    }
    return await find(chainOf(this.pay?.cluster));
  }
  async wallet() {
    if (this.W) return this.W;
    const L = await this.wallets(), named = L.find(w => w.name === read(WANT));
    return (this.W = named || (L.length === 1 && !L[0].mobile ? L[0] : null));
  }
  async buy(kind, id, {title, usd, menus}) {
    if (!this.pay?.on) { menus.toast(this.pay?.why || 'Payments are off on this server.'); return; }
    if (!read(SEEN)) keep(SEEN, JSON.stringify((save.p.purchases || []).map(x => x.ref).slice(-40)));
    const item = {kind, id, title, usd}, W = await this.wallet();
    if (!W) return this.walletSheet(menus, item);
    await this.priced(W, item, menus);
  }
  // the words of a sheet: every text from the server or a wallet goes in as text
  say(menus, {title, text = '', spin = false, small = '', acts = []}) {
    menus.sheet(box => {
      box.innerHTML = `<div class="paybox"><h3 class="stroke-s"></h3><p class="say"></p>${spin ? '<div class="spin"></div>' : ''}<p class="fine"></p></div>`;
      box.querySelector('h3').textContent = title; box.querySelector('.say').textContent = text; box.querySelector('.fine').textContent = small;
      if (acts.length) { const a = h('div', 'acts'); for (const [label, cls, go] of acts) { const b = h('button', 'btn small ' + cls, label); b.onclick = () => { tap(); go(); }; a.append(b); } box.append(a); }
    });
  }
  fine(ref) { return `A payment on the chain cannot be undone. ${this.pay?.support ? 'Problems? ' + this.pay.support + ', with' : 'Your reference:'} ${ref}`; }
  // this wallet can pay, and it is the one tied to the profile? then the price
  async priced(W, item, menus) {
    const close = () => menus.closeSheet();
    if (!save.p.wallet) { if (!await this.tied(W, menus, () => this.priced(W, item, menus))) return; }
    else {
      const now = await W.peek?.();
      if (now && short(now) !== save.p.wallet.a) return this.say(menus, {title: 'ANOTHER ACCOUNT', text: `Your wallet has ${short(now)} selected, but this player is tied to ${save.p.wallet.a}. Switch account in your wallet, or disconnect it in Settings to tie another.`, acts: [['OK', 'dark', close]]});
    }
    this.say(menus, {title: item.title, text: 'Asking for the price…', spin: true});
    const q = await this.client.buy(item.kind, item.id);
    if (!q.ok) return this.outcome(q, item, W, menus);
    this.priceSheet(W, item, q, menus);
  }
  // connect, then sign the text (a Mobile Wallet Adapter's second app switch needs a tap of its own): true when it is tied. `then`: go on after that tap.
  async tied(W, menus, then = null) {
    const close = () => menus.closeSheet();
    this.say(menus, {title: 'CONNECT YOUR WALLET', text: 'Approve in your wallet. It only shows the game your address.', spin: true});
    try { await W.connect(); } catch (e) { close(); if (!e.quiet) menus.toast(e.message); return false; }
    keep(WANT, W.name);
    const proof = async () => {
      this.say(menus, {title: 'PROVE IT IS YOURS', text: 'Sign the message in your wallet. It is not a transaction and moves nothing.', spin: true});
      const t = await tie(this.client, W);
      if (!t.ok) { close(); if (!t.quiet) menus.toast(t.why || 'Not connected.'); return false; }
      menus.toast('Wallet connected.'); return true;
    };
    if (!W.mobile) { const ok = await proof(); if (!ok) return false; close(); return true; }
    this.say(menus, {title: 'ONE MORE STEP', text: 'Sign a message to prove the wallet is yours. It is not a transaction and moves nothing.', acts: [['CANCEL', 'dark', close], ['SIGN', 'yellow', async () => { if (await proof()) { close(); then?.(); } }]]});
    return false;
  }
  priceSheet(W, item, q, menus) {
    let at = Date.now(), timer = 0;
    const left = () => q.expires - (q.now + (Date.now() - at));
    menus.sheet(box => {
      const test = q.cluster === 'mock' ? 'FAKE CHAIN: TEST MONEY' : q.cluster === 'devnet' ? 'DEVNET: TEST MONEY' : '';
      box.innerHTML = `<div class="paybox"><h3 class="stroke-s"></h3>${test ? `<div class="paytest">${test}</div>` : ''}<div class="payamt stroke"></div><p class="say"></p><p class="payt prog-t"></p><p class="fine"></p></div>`;
      box.querySelector('h3').textContent = item.title; box.querySelector('.payamt').textContent = `${q.text} ${q.symbol}`;
      box.querySelector('.say').textContent = `$${(+q.usd).toFixed(2)}${q.usdPerSol ? ` at $${(+q.usdPerSol).toFixed(2)} a SOL` : ''}. Goes to the game's wallet ${short(q.treasury)}.`;
      box.querySelector('.fine').textContent = this.fine(q.ref);
      const T = box.querySelector('.payt'), a = h('div', 'acts'), no = h('button', 'btn small dark', 'CANCEL'), ok = h('button', 'btn small yellow', 'PAY');
      no.onclick = () => { tap(); clearInterval(timer); menus.closeSheet(); };
      ok.onclick = async () => {
        tap(); clearInterval(timer);
        // (a transaction is good for about a minute on the chain: asked again, the same order at the same price comes with a fresh one)
        let o = q; if (Date.now() - at > 25000) { o = await this.client.buy(item.kind, item.id); if (!o.ok) return this.outcome(o, item, W, menus); }
        this.say(menus, {title: item.title, text: `Approve ${o.text} ${o.symbol} in your wallet…`, spin: true, small: this.fine(o.ref)});
        this.outcome(await payQuote(this.client, W, o), item, W, menus);
      };
      a.append(no, ok); box.append(a);
      if (q.url) { const l = h('button', 'paylink', 'Pay from another wallet (link or QR)'); l.onclick = () => { tap(); clearInterval(timer); this.linkSheet(item, menus); }; box.append(l); }
      const show = () => { const m = left(); if (m <= 0) { clearInterval(timer); this.say(menus, {title: 'THIS PRICE ENDED', text: 'The price is only held for a few minutes, because the price of SOL moves. You were not charged.', acts: [['CLOSE', 'dark', () => menus.closeSheet()], ['NEW PRICE', 'yellow', () => this.priced(W, item, menus)]]}); return; } T.textContent = `Price held for ${clock(m)}`; };
      show(); timer = setInterval(() => { if (!box.isConnected) clearInterval(timer); else show(); }, 1000);
    });
  }
  // what came of it, in words: goods, a no, not enough money, a chain that does not answer, a payment still being checked, an odd one
  outcome(r, item, W, menus) {
    const close = () => menus.closeSheet(), again = W ? ['TRY AGAIN', 'yellow', () => this.priced(W, item, menus)] : ['TRY AGAIN', 'yellow', () => this.buy(item.kind, item.id, {...item, menus})];
    if (r.ok || r.paid) { this.mine(r.ref); close(); return this.goods(r, item.title, menus); }
    if (r.quiet) return this.say(menus, {title: 'CANCELLED', text: 'You said no in your wallet. Nothing was charged.', acts: [['CLOSE', 'dark', close], again]});
    if (r.funds) return this.say(menus, {title: 'NOT ENOUGH SOL', text: r.why + ' Nothing was charged.', acts: [['CLOSE', 'dark', close]]});
    if (r.pending) return this.say(menus, {title: 'CHECKING YOUR PAYMENT', text: r.why, small: this.fine(r.ref), acts: [['OK', 'dark', close]]});
    if (r.flag) return this.say(menus, {title: 'THIS PAYMENT NEEDS THE TEAM', text: r.why, small: this.fine(r.ref), acts: [['OK', 'dark', close]]});
    if (r.down) return this.say(menus, {title: 'SOLANA IS NOT ANSWERING', text: r.why, acts: [['CLOSE', 'dark', close], again]});
    this.say(menus, {title: 'NOT PAID', text: r.why || 'The payment did not go through.', small: r.ref ? this.fine(r.ref) : '', acts: [['CLOSE', 'dark', close], again]});
  }
  goods(r, label, menus) {
    audio.play('gem_buy');
    const g = r.got || {};
    if (g.bag) menus.openRoll(g.bag);
    else { const said = [g.gems && `+${g.gems} gems`, g.coins && `+${g.coins} coins`].filter(Boolean).join(' '); menus.toast(`Thanks! ${said || label + ' arrived.'}`); if (menus.tab === 'shop') menus.hub('shop', true); }
  }
  order(m) {
    if (m.state !== 'paid') return;
    this.mine(m.ref);
    const w = this.waiting.get(m.ref); if (w) { this.waiting.delete(m.ref); return w(m); }
    const M = this.app.menus; if (!M || this.app.match) return;
    audio.play('gem_buy'); M.toast(`Payment confirmed: ${m.label} arrived.`); if (M.tab === 'shop') M.hub('shop', true);
  }
  // refs the player was told about (kept on this browser): a purchase that is new here came while the page was away
  mine(ref) { let L = []; try { L = JSON.parse(read(SEEN) || '[]'); } catch {} if (!L.includes(ref)) { L.push(ref); keep(SEEN, JSON.stringify(L.slice(-60))); } }
  arrived(p) {
    if (!read(SEEN)) return;
    let L = []; try { L = JSON.parse(read(SEEN)); } catch {}
    const fresh = (p?.purchases || []).filter(x => !L.includes(x.ref)); if (!fresh.length) return;
    let waited = 0;   // (over the title screen nobody would read it)
    const say = () => { if (document.getElementById('boot')?.isConnected && waited++ < 60) return setTimeout(say, 1000); for (const x of fresh) this.mine(x.ref); this.app.menus?.toast(`Your payment arrived: ${fresh.length === 1 ? labelOf(fresh[0].kind, fresh[0].id) : fresh.length + ' purchases'}.`); };
    say();
  }
  // no wallet yet: the wallets found here, and on a phone the wallet apps' own browsers. `item`: a purchase goes on from it.
  async walletSheet(menus, item = null) {
    const L = await this.wallets(), here = L.filter(w => !w.mobile), phone = isPhone();
    let hand = ''; if (phone && !here.length) { const r = await this.client.wallet.hand(); if (r.ok) hand = r.code; }
    menus.sheet(box => {
      box.innerHTML = `<div class="paybox"><h3 class="stroke-s">${item ? 'PAY WITH A WALLET' : 'CONNECT A WALLET'}</h3><p class="say"></p></div>`;
      box.querySelector('.say').textContent = L.length ? 'Pick your wallet.' : phone ? 'Open the game inside your wallet app: your progress comes with you, and this page stops.' : 'Install Phantom, Solflare or Backpack in this browser, then reload this page. Or pay from a wallet on your phone with a QR code.';
      const list = h('div', 'paylist');
      for (const w of L) {
        const b = h('button', 'btn small dark', ''); b.textContent = w.mobile ? 'A WALLET APP ON THIS PHONE' : w.name.toUpperCase();
        b.onclick = async () => { tap(); this.W = w; if (item) return this.priced(w, item, menus); if (await this.tied(w, menus, () => this.settingsBack(menus))) this.settingsBack(menus); };
        list.append(b);
      }
      if (hand) for (const A of WALLET_APPS) {
        const link = h('a', 'btn small dark', `OPEN IN ${A.name.toUpperCase()}`); link.href = A.link(`${location.origin}/?hand=${hand}`, location.origin); list.append(link);
      }
      if (item && this.pay?.accept?.includes('SOL')) { const q = h('button', 'btn small purple', 'ANY WALLET: LINK OR QR'); q.onclick = () => { tap(); this.linkSheet(item, menus); }; list.append(q); }
      box.append(list);
      if (phone && hand) box.append(h('p', 'fine', 'Another wallet app? Open this address in its own browser.'));
      const a = h('div', 'acts'), x = h('button', 'btn small dark', 'CLOSE'); x.onclick = () => { tap(); menus.closeSheet(); }; a.append(x); box.append(a);
    });
  }
  settingsBack(menus) { menus.closeSheet(); if (menus.tab === 'settings') menus.hub('settings', true); }
  // Solana Pay: no connection at all. Any wallet that reads the link or the QR pays; the server finds it on the chain by the order's reference, and says so here.
  async linkSheet(item, menus) {
    this.say(menus, {title: item.title, text: 'Asking for the price…', spin: true});
    const q = await this.client.buy(item.kind, item.id, {link: true});
    if (!q.ok) return this.outcome(q, item, null, menus);
    if (!q.url) return this.say(menus, {title: 'NOT PAID', text: 'This coin cannot be paid by link.', acts: [['CLOSE', 'dark', () => menus.closeSheet()]]});
    const at = Date.now(); let timer = 0;
    const done = m => { clearInterval(timer); menus.closeSheet(); this.goods(m, item.title, menus); };
    this.waiting.set(q.ref, done);
    menus.sheet(box => {
      box.innerHTML = `<div class="paybox"><h3 class="stroke-s"></h3><div class="payamt stroke"></div><p class="say"></p><div class="payqr"></div><p class="payt prog-t"></p><p class="fine"></p></div>`;
      box.querySelector('h3').textContent = item.title; box.querySelector('.payamt').textContent = `${q.text} SOL`;
      box.querySelector('.say').textContent = isPhone() ? 'Open it in your wallet app, or scan the QR from another phone. This page knows when it is paid.' : 'Scan with the wallet app on your phone. This page knows when it is paid.';
      box.querySelector('.fine').textContent = `Pay exactly this order: the link names it. ${this.fine(q.ref)}`;
      import('../vendor/qr.js').then(({default: qr}) => { const c = qr(0, 'M'); c.addData(q.url); c.make(); const el = box.querySelector('.payqr'); if (el) el.innerHTML = c.createSvgTag({cellSize: 4, margin: 8, scalable: true}); }).catch(e => console.warn('[pay] no QR', e));
      const list = h('div', 'paylist');
      if (isPhone()) { const o = h('a', 'btn small yellow', 'OPEN MY WALLET APP'); o.href = q.url; list.append(o); }
      const c = h('button', 'btn small dark', 'COPY THE LINK'); c.onclick = async () => { tap(); try { await navigator.clipboard.writeText(q.url); menus.toast('Copied.'); } catch { menus.toast('Could not copy here.'); } }; list.append(c);
      box.append(list);
      const a = h('div', 'acts'), x = h('button', 'btn small dark', 'CLOSE'), k = h('button', 'btn small dark', 'I PAID: CHECK');
      x.onclick = () => { tap(); clearInterval(timer); this.waiting.delete(q.ref); menus.closeSheet(); };
      k.onclick = async () => { tap(); const r = await this.client.paid(q.ref, '', true); if (r.ok) { this.waiting.delete(q.ref); this.mine(r.ref); done(r); } else if (r.flag) this.outcome({...r, ref: q.ref}, item, null, menus); else menus.toast('Not on the chain yet. This page keeps looking.'); };
      a.append(x, k); box.append(a);
      const T = box.querySelector('.payt'), show = () => { const m = q.expires - (q.now + (Date.now() - at)); T.textContent = m > 0 ? `Price held for ${clock(m)}` : 'This price ended: do not pay this one, ask for a new price.'; if (m <= 0) clearInterval(timer); };
      show(); timer = setInterval(() => { if (!box.isConnected) { clearInterval(timer); this.waiting.delete(q.ref); } else show(); }, 1000);
    });
  }
  // the shop's line about orders the chain has not settled yet (a wallet sent one and the page went away; one that needs the team)
  pendingRow(page, menus) {
    const row = h('div', 'panel paypend'); row.style.display = 'none'; page.append(row);
    this.client.orders().then(r => {
      const L = (r.orders || []).filter(o => o.sent || o.flag); if (!L.length || !row.isConnected) return;
      row.style.display = '';
      for (const o of L) {
        const line = h('div', 'payline'), t = h('span', ''); t.textContent = o.flag ? `${o.label}: this payment needs the team. Reference ${o.ref}.${this.pay?.support ? ' ' + this.pay.support : ''}` : `${o.label}: your payment is being checked.`; line.append(t);
        if (!o.flag) { const b = h('button', 'btn small dark', 'CHECK'); b.onclick = async () => { tap(); const a = await this.client.paid(o.ref, '', true); if (a.ok) { this.mine(a.ref); this.goods(a, o.label, menus); line.remove(); if (!row.children.length) row.style.display = 'none'; } else menus.toast(a.flag ? a.why : 'Not on the chain yet. It is checked again by itself.'); }; line.append(b); }
        row.append(line);
      }
    });
  }
  walletRow(menus) {
    const w = save.p.wallet;
    if (!w?.a) { const b = h('button', 'btn small dark', 'CONNECT'); b.onclick = () => { tap(); if (!this.pay?.on) return menus.toast(this.pay?.why || 'Payments are off on this server.'); this.walletSheet(menus); }; return b; }
    const box = h('div', 'payrow'), a = h('span', 'prog-t'), x = h('button', 'btn small dark', 'DISCONNECT'); a.textContent = w.a;
    x.onclick = async () => { tap(); const r = await this.client.wallet.drop(); if (!r.ok) return menus.toast(r.why || 'Not now.'); await this.W?.disconnect?.(); this.W = null; keep(WANT, ''); menus.toast('Wallet disconnected.'); menus.hub(menus.tab, true); };
    box.append(a, x); return box;
  }

  // ---------- friendly battles: a code for a friend, no Clout at stake
  friendRow(menus) {
    const box = h('div', 'seg3'), mk = h('button', '', 'CREATE'), jn = h('button', '', 'JOIN');
    mk.onclick = async () => {
      audio.play('ui_pop'); const r = await this.client.request({t: 'friend', create: 1});
      if (!r?.ok) return menus.toast(r?.why || 'Not now.');
      menus.sheet(b => { b.innerHTML = `<div style="text-align:center;display:grid;gap:8px"><h3 class="stroke-s">FRIENDLY BATTLE</h3><p>Send this code to your friend:</p><div class="fcode stroke">${r.code}</div><p class="prog-t">waiting for them… (10 minutes)</p></div>`;
        const a = h('div', 'acts'), c = h('button', 'btn small red', 'CANCEL'); c.onclick = () => { this.client.request({t: 'friend', cancel: 1}); menus.closeSheet(); }; a.append(c); b.append(a); });
    };
    jn.onclick = async () => {
      const code = (prompt('Your friend\'s code') || '').trim().toUpperCase(); if (!code) return;
      const r = await this.client.request({t: 'friend', join: code}); if (!r?.ok) menus.toast(r?.why || 'No battle with that code.');
    };
    box.append(mk, jn); return box;
  }
}
