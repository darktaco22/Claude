// MEME ROYALE — A SOLANA WALLET IN THE PAGE: Phantom, Solflare, Backpack (and any wallet that speaks the Wallet Standard, or left a
// provider in window.phantom.solana / window.solflare / window.backpack / window.solana; in Android Chrome the Mobile Wallet Adapter, which
// reaches a wallet app on the same phone). CONNECT (which account is his), SIGN A TEXT (the proof that it is his: the server ties the
// wallet to the player), and SIGN-AND-SEND a payment the SERVER built (server/pay.mjs: SOL to the game's treasury with the order's reference
// and memo), which the wallet shows to its owner first. Nothing here builds a transaction, asks for a seed phrase or a key, or sends anything
// the player did not approve in his wallet.
// HOW A WALLET REACHES THE PAGE ON A PHONE: inside a wallet app's own browser its provider is simply here. In Android Chrome the Mobile
// Wallet Adapter is registered and listed like any other wallet. iOS Safari has neither: WALLET_APPS links open the game inside the wallet
// app's browser (a hand-over code in the link keeps the player's profile, client.wallet.hand()), and a Solana Pay link or QR (order.url)
// needs no connection at all.
//
//   const L = await find(chain)            [{name, icon, via, mobile, connect(), sign(text), send?(bytes, chain), peek(), disconnect()}]  (send missing: it cannot pay)
//   await tie(client, W)                   -> {ok, wallet: {a}} | {ok: false, why}      (asks the text, the wallet signs it, the server ties)
//   await pay(client, W, kind, id, {cur})  -> {ok, got, ref} | {ok: false, why, quiet?, funds?, pending?, flag?, quote?}  (an order, then payQuote)
//   await payQuote(client, W, q)           the wallet signs and sends the order q, the server checks it on the chain
//   await confirmed(client, ref, tx)       asks the server until the chain has said; {pending: true}: not yet, and the server keeps looking
//   await payManual(client, kind, id)      -> a USDC order with no transaction: the page shows `ui` USDC, `dest` and `ref`; the player sends
//                                             it from his tied wallet himself and pastes the transaction id: client.paid(ref, tx)
//   devWallet(rpc)                          a test server only (?devwallet): a key of this browser on the fake chain or devnet
// A wallet its owner closed or said no in throws an error with .quiet = true; .funds = true when it says there is not enough money. Any other
// error carries a sentence in .message.
// ---- base58, the alphabet of Solana's addresses (no 0, O, I, l)
const A58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
export function enc58(bytes) {
  let z = 0; while (z < bytes.length && bytes[z] === 0) z++;
  const d = [];
  for (let k = z; k < bytes.length; k++) { let c = bytes[k]; for (let i = 0; i < d.length; i++) { c += d[i] * 256; d[i] = c % 58; c = (c / 58) | 0; } while (c > 0) { d.push(c % 58); c = (c / 58) | 0; } }
  let s = '1'.repeat(z); for (let i = d.length - 1; i >= 0; i--) s += A58[d[i]]; return s;
}
export function dec58(text) {   // -> Uint8Array, or null when it is not base58
  const str = String(text ?? ''); if (!str || str.length > 128) return null;
  let z = 0; while (z < str.length && str[z] === '1') z++;
  const b = [];
  for (let k = z; k < str.length; k++) { let c = A58.indexOf(str[k]); if (c < 0) return null; for (let i = 0; i < b.length; i++) { c += b[i] * 58; b[i] = c & 255; c >>= 8; } while (c > 0) { b.push(c & 255); c >>= 8; } }
  const out = new Uint8Array(z + b.length); for (let i = 0; i < b.length; i++) out[z + i] = b[b.length - 1 - i]; return out;
}
const b64 = bytes => { let s = ''; for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]); return btoa(s); };
const bytesOf = v => v instanceof Uint8Array ? v : ArrayBuffer.isView(v) ? new Uint8Array(v.buffer, v.byteOffset, v.byteLength) : v instanceof ArrayBuffer ? new Uint8Array(v) : Array.isArray(v) ? Uint8Array.from(v) : null;
// an address as its wallet gives it (a string, bytes, or a key object that can say either) -> base58 of 32 bytes, or ''
function addressOf(pk) {
  if (!pk) return '';
  let raw = bytesOf(pk); if (!raw && typeof pk.toBytes === 'function') { try { raw = bytesOf(pk.toBytes()); } catch {} }
  if (raw) return raw.length === 32 ? enc58(raw) : '';
  let s = ''; try { s = typeof pk === 'string' ? pk : typeof pk.toBase58 === 'function' ? pk.toBase58() : String(pk); } catch {}
  return dec58(s)?.length === 32 ? s : '';
}
// a signature as its wallet gives it (bytes; some give {signature}; a few give base58) -> 64 bytes, or null
function sigOf(v) {
  if (v && typeof v === 'object' && !bytesOf(v) && 'signature' in v) v = v.signature;
  const raw = typeof v === 'string' ? dec58(v) : bytesOf(v);
  return raw && raw.length === 64 ? raw : null;
}
// what a wallet throws when its owner closed it or said no (4001 is the code wallets agreed on; the rest say it in words)
const QUIET = /reject|denied|declin|cancel|closed|abort|dismiss|user did not/i;
const FUNDS = /insufficient|debit an account|not enough (sol|funds|balance)|\b0x1\b/i;
function fail(e, what) {
  const text = String(e?.message || e || ''), q = e?.code === 4001 || e?.error?.code === 4001 || QUIET.test(text) || QUIET.test(String(e?.name || '')), funds = !q && FUNDS.test(text);
  const err = new Error(q ? 'closed' : funds ? 'Your wallet does not hold enough for this and its network fee.' : what); err.quiet = q; err.funds = funds; if (!q) console.warn('[wallet] ' + what, text.slice(0, 200)); return err;
}
const SEND = 'The wallet did not send the payment', CONNECT = 'The wallet did not connect', SIGN = 'The wallet did not sign the message', OTHER = 'The wallet signed with another account than the one it connected', PLAIN = 'This wallet cannot sign a plain message (a hardware wallet often cannot)';
const utf8 = text => new TextEncoder().encode(String(text));
const same = (a, b) => { if (!a || !b || a.length !== b.length) return false; for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false; return true; };

// ---- a wallet that speaks the Wallet Standard. It is taken only when it can do the two things this game asks for, on Solana.
const std = []; let listening = false;
function listen() {
  if (listening || typeof window === 'undefined') return; listening = true;
  const api = Object.freeze({register(...ws) { for (const w of ws) if (w && typeof w === 'object' && !std.includes(w)) std.push(w); return () => {}; }});
  // (a wallet that arrives after the page: it announces itself with a function that takes `api`. One that was here before: it waits for the page to say it is ready)
  try { window.addEventListener('wallet-standard:register-wallet', e => { try { if (typeof e.detail === 'function') e.detail(api); } catch (err) { console.warn('[wallet] a wallet that would not register', err); } }); } catch {}
  try { window.dispatchEvent(new CustomEvent('wallet-standard:app-ready', {detail: api})); } catch {}
}
const feat = (w, k, fn) => { try { const f = w.features?.[k]; return f && typeof f[fn] === 'function' ? f : null; } catch { return null; } };
const onSolana = o => { try { return Array.isArray(o?.chains) && o.chains.some(c => String(c).startsWith('solana:')); } catch { return false; } };
function standard(w) {
  const C = feat(w, 'standard:connect', 'connect'), M = feat(w, 'solana:signMessage', 'signMessage'); if (!C || !M || !onSolana(w)) return null;
  let acct = null;
  const pick = L => (Array.isArray(L) ? L : []).find(a => a && onSolana(a) && addressOf(a.address || a.publicKey)) || null;
  const S = feat(w, 'solana:signAndSendTransaction', 'signAndSendTransaction'), D = feat(w, 'standard:disconnect', 'disconnect');
  return {name: String(w.name || 'Wallet').slice(0, 24), icon: typeof w.icon === 'string' && /^data:image\//.test(w.icon) ? w.icon : '', via: 'standard', mobile: w.name === 'Mobile Wallet Adapter',
    send: S ? async function (bytes, chain = 'solana:mainnet') {
      if (!acct) { await this.peek(); if (!acct) await this.connect(); }
      let r; try { r = await S.signAndSendTransaction({account: acct, transaction: bytes, chain}); } catch (e) { throw fail(e, SEND); }
      const one = Array.isArray(r) ? r[0] : r, sig = sigOf(one); if (!sig) throw fail('no signature', SEND); return enc58(sig);
    } : null,
    // the account it would use, if that can be known without asking its owner anything ('' when not)
    async peek() {
      if (!acct) { let r = null; try { r = await C.connect({silent: true}); } catch {} acct = pick(r?.accounts) || pick(w.accounts); }
      return acct ? addressOf(acct.address || acct.publicKey) : '';
    },
    async disconnect() { acct = null; try { await D?.disconnect(); } catch {} },
    async connect() {
      let r; try { r = await C.connect(); } catch (e) { throw fail(e, CONNECT); }
      acct = pick(r?.accounts) || pick(w.accounts); if (!acct) throw fail('no Solana account', CONNECT);
      return addressOf(acct.address || acct.publicKey);
    },
    async sign(text) {
      if (!acct) await this.connect();
      const msg = utf8(text); let r; try { r = await M.signMessage({account: acct, message: msg}); } catch (e) { throw fail(e, SIGN); }
      const one = Array.isArray(r) ? r[0] : r, sig = sigOf(one); if (!sig) throw fail('no signature', SIGN);
      // (a wallet may say what it really signed: when that is not the text it was given, the signature proves nothing to the server)
      const signed = bytesOf(one?.signedMessage); if (signed && !same(signed, msg)) throw fail('another message was signed', PLAIN);
      return {address: addressOf(acct.address || acct.publicKey), sig: b64(sig)};
    }};
}

// ---- a provider a wallet left in the page. Only its connect and its message signing are ever called.
const nameOf = p => p.isPhantom ? 'Phantom' : p.isSolflare ? 'Solflare' : p.isBackpack ? 'Backpack' : '';
const able = p => !!p && typeof p === 'object' && typeof p.connect === 'function' && typeof p.signMessage === 'function';
function injected() {
  const out = [], seen = new Set(), g = fn => { try { return fn(); } catch { return null; } };
  const add = (name, p) => { if (!able(p) || seen.has(p)) return; seen.add(p); out.push([nameOf(p) || name, p]); };
  add('Phantom', g(() => window.phantom?.solana)); add('Solflare', g(() => window.solflare));
  add('Backpack', g(() => able(window.backpack) ? window.backpack : window.backpack?.solana)); add('Browser wallet', g(() => window.solana));
  return out;
}
function page(name, p) {
  let addr = '';
  return {name, icon: '', via: 'page',
    send: typeof p.request === 'function' ? async function (bytes) {
      if (!addr) await this.connect();
      let r; try { r = await p.request({method: 'signAndSendTransaction', params: {message: enc58(bytes.subarray(65))}}); } catch (e) { throw fail(e, SEND); }
      const s = typeof r?.signature === 'string' ? r.signature : sigOf(r) ? enc58(sigOf(r)) : ''; if (!s) throw fail('no signature', SEND); return s;
    } : null,
    async peek() { return addr || addressOf(p.publicKey); },
    async disconnect() { addr = ''; try { await p.disconnect?.(); } catch {} },
    async connect() {
      let r; try { r = await p.connect(); } catch (e) { throw fail(e, CONNECT); }
      addr = addressOf(r?.publicKey) || addressOf(p.publicKey); if (!addr) throw fail('no address', CONNECT);
      return addr;
    },
    async sign(text) {
      if (!addr) await this.connect();
      let r; try { r = await p.signMessage(utf8(text), 'utf8'); } catch (e) { throw fail(e, SIGN); }
      const sig = sigOf(r); if (!sig) throw fail('no signature', SIGN);
      const by = addressOf(r?.publicKey) || addressOf(p.publicKey) || addr; if (by !== addr) throw fail('another account signed', OTHER);
      return {address: addr, sig: b64(sig)};
    }};
}

// ---- phones. The in-app browser links are the wallets' own (their docs; the paths are in their published app-link files). Any other wallet is
// reached by opening the game in its browser by hand.
export const isPhone = (ua = globalThis.navigator?.userAgent || '') => /Android|iPhone|iPad|iPod/i.test(ua) || (/Macintosh/.test(ua) && globalThis.navigator?.maxTouchPoints > 1);
export const WALLET_APPS = [
  {name: 'Phantom', link: (url, ref) => `https://phantom.com/ul/browse/${encodeURIComponent(url)}?ref=${encodeURIComponent(ref)}`},
  {name: 'Solflare', link: (url, ref) => `https://solflare.com/ul/v1/browse/${encodeURIComponent(url)}?ref=${encodeURIComponent(ref)}`},
  {name: 'Backpack', link: (url, ref) => `https://backpack.app/ul/v1/browse/${encodeURIComponent(url)}?ref=${encodeURIComponent(ref)}`},
];
export const chainOf = cluster => cluster === 'devnet' ? 'solana:devnet' : cluster === 'testnet' ? 'solana:testnet' : 'solana:mainnet';
// the Mobile Wallet Adapter (vendor/mwa.js, loaded only here): Android Chrome over https; not a WebView, not iOS
let mwa = false;
async function mobileAdapter(chain) {
  const ua = globalThis.navigator?.userAgent || '';
  if (mwa || !globalThis.isSecureContext || !/Android/i.test(ua) || !/Chrome\//.test(ua) || /; wv\)/.test(ua)) return; mwa = true;
  try {
    const M = await import('../../vendor/mwa.js');
    M.registerMwa({appIdentity: {name: 'MEME ROYALE', uri: location.origin, icon: 'assets/ui/icon-192.png'}, authorizationCache: M.createDefaultAuthorizationCache(), chains: [chain], chainSelector: M.createDefaultChainSelector(), onWalletNotFound: M.createDefaultWalletNotFoundHandler()});
  } catch (e) { console.warn('[wallet] the Mobile Wallet Adapter did not load', e); }
}

// The wallets of this browser. A wallet that speaks the standard AND left a provider is listed once, by its standard side.
export async function find(chain = 'solana:mainnet') {
  if (typeof window === 'undefined') return [];
  const first = !listening; listen(); await mobileAdapter(chain);
  if (first) await new Promise(r => setTimeout(r, 120));   // (a wallet answers the page's word in its own turn of the loop)
  const out = [], names = new Set();
  for (const w of std) { const W = standard(w); if (W && !names.has(W.name.toLowerCase())) { names.add(W.name.toLowerCase()); out.push(W); } }
  for (const [name, p] of injected()) { const k = name.toLowerCase(); if (!names.has(k)) { names.add(k); out.push(page(name, p)); } }
  return out;
}

// ---- the flows the shop uses (client: src/net/client.js)
const b64bytes = s => Uint8Array.from(atob(s), ch => ch.charCodeAt(0));
export async function tie(client, W) {
  const q = await client.wallet.ask(); if (!q.ok) return q;
  let s; try { s = await W.sign(q.text); } catch (e) { return {ok: false, why: e.quiet ? 'closed' : e.message, quiet: !!e.quiet}; }
  return await client.wallet.tie({address: s.address, sig: s.sig, nonce: q.nonce});
}
export async function pay(client, W, kind, id, {cur = ''} = {}) {
  if (!W.send) return {ok: false, why: 'This wallet cannot send a payment from the page: use a Solana Pay link or QR.'};
  const q = await client.buy(kind, id, {cur}); if (!q.ok) return q;
  return await payQuote(client, W, q);
}
export async function payQuote(client, W, q) {
  let tx; try { tx = await W.send(b64bytes(q.txB64), chainOf(q.cluster)); }
  catch (e) {
    if (e.quiet) return {ok: false, why: 'closed', quiet: true, quote: q, ref: q.ref};
    // (a wallet that answered with an error may have sent it all the same: the server asks the chain by the order's reference)
    const r = await client.paid(q.ref, '', true); if (r.ok) return r;
    return {ok: false, why: e.message, funds: !!e.funds, quote: q, ref: q.ref};
  }
  return await confirmed(client, q.ref, tx);
}
// (the chain may take a few seconds: the server waits for it; a "not found yet" or a dropped line is asked again a few times, and after that the server's watcher goes on alone)
export async function confirmed(client, ref, tx = '') {
  for (let k = 0; k < 5; k++) { const r = await client.paid(ref, tx); if (r.ok) return {...r, tx}; if (!r.retry && !r.net) return {...r, ref, tx}; await new Promise(res => setTimeout(res, 3000)); }
  return {ok: false, pending: true, why: 'Your wallet sent the payment and Solana has not confirmed it yet. You can close this page: the goods arrive by themselves once it does.', ref, tx};
}
export const payManual = (client, kind, id) => client.buy(kind, id, {manual: true, cur: 'USDC'});

// ---- the DEV wallet (?devwallet, a test server only): an ed25519 key of this browser, the fake chain or devnet at `rpc`. localStorage
// memeroyale.devwallet.mode: reject (its owner says no), funds (it says there is not enough), lost (it sends, then reports an error).
export async function devWallet(rpc = '/mockrpc') {
  const K = 'memeroyale.devwallet', sub = crypto.subtle; let pair = null;
  try { const j = JSON.parse(localStorage.getItem(K) || 'null'); if (j) pair = {privateKey: await sub.importKey('jwk', j.priv, {name: 'Ed25519'}, true, ['sign']), publicKey: await sub.importKey('jwk', j.pub, {name: 'Ed25519'}, true, ['verify'])}; } catch {}
  if (!pair) { pair = await sub.generateKey({name: 'Ed25519'}, true, ['sign', 'verify']); try { localStorage.setItem(K, JSON.stringify({priv: await sub.exportKey('jwk', pair.privateKey), pub: await sub.exportKey('jwk', pair.publicKey)})); } catch {} }
  const address = enc58(new Uint8Array(await sub.exportKey('raw', pair.publicKey)));
  const signB = async b => new Uint8Array(await sub.sign({name: 'Ed25519'}, pair.privateKey, b));
  const call = async (method, params) => { const r = await (await fetch(rpc, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', id: 1, method, params})})).json(); if (r.error) throw new Error(r.error.message); return r.result; };
  const mode = () => { try { return localStorage.getItem(K + '.mode') || ''; } catch { return ''; } };
  return {name: 'Dev wallet (test money)', icon: '', via: 'dev', address,
    async connect() { return address; },
    async peek() { return address; },
    async disconnect() {},
    async sign(text) { return {address, sig: b64(await signB(utf8(text)))}; },
    async send(bytes) {   // one signature slot (compact-u16 1), then the message
      const M = mode(); if (M === 'reject') throw fail({code: 4001}, SEND); if (M === 'funds') throw fail('insufficient funds', SEND);
      const tx = new Uint8Array(bytes), msg = tx.subarray(65); tx.set(await signB(msg), 1);
      const sig = await call('sendTransaction', [b64(tx), {encoding: 'base64', preflightCommitment: 'confirmed'}]);
      if (M === 'lost') throw fail('the wallet lost its line', SEND);
      return sig;
    },
    balance: async () => (await call('getBalance', [address, {commitment: 'confirmed'}]))?.value ?? 0,
    faucet: sol => call('requestAirdrop', [address, Math.round(sol * 1e9)]),
    airdrop: amount => call('mock_airdrop', [{address, amount}])};
}
