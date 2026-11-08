// The mixer: Web Audio, sounds listed in assets/audio/manifest.json (ElevenLabs takes). Missing ids are silent, so the
// game runs before the audio pass lands. Music streams loop with their loop points; one-shots get a little pitch spread.
const KEY = 'memeroyale.vol';

class Audio {
  constructor() {
    this.ctx = null; this.man = {}; this.buf = new Map(); this.loading = new Map();
    let v = {}; try { v = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch {}
    this.vol = {sfx: v.sfx ?? 1, music: v.music ?? 0.7};
    this.last = new Map(); this.lastVar = new Map(); this.live = [];
    this.ready = fetch('assets/audio/manifest.json').then(r => r.ok ? r.json() : {}).then(m => { this.man = m; }).catch(() => {});
    // back from the background (another app, the home screen, a locked phone) the sound has to come back by itself: iOS
    // leaves the context 'interrupted' (not 'suspended') and wakes it only inside a touch's end or a click, so every press
    // asks until it runs again; one that says it runs while its clock stands still (a WebKit fault after an interruption)
    // is rebuilt on the next press
    const unlock = () => { this.init(); this.wake(); };
    for (const k of ['pointerdown', 'pointerup', 'touchend', 'click', 'keydown']) addEventListener(k, unlock, {capture: true, passive: true});
    document.addEventListener('visibilitychange', () => { if (!this.ctx) return; if (document.hidden) this.ctx.suspend().catch(() => {}); else { this.back = true; this.wake(); } });
    addEventListener('pageshow', e => { if (e.persisted && this.ctx) { this.back = true; this.wake(); } });
  }
  wake() {
    const c = this.ctx; if (!c || document.hidden) return;
    if (c.state !== 'running') { c.resume().catch(() => {}); return; }
    if (!this.back || this.probe) return;
    const t0 = c.currentTime;
    this.probe = setTimeout(() => { this.probe = 0; if (this.ctx !== c || c.state !== 'running') return;
      if (c.currentTime > t0) this.back = false; else this.rebuild(); }, 250);
  }
  // a new context in place of a dead one: the decoded sounds carry over, the music and the arena's bed start again
  rebuild() {
    const old = this.ctx, amb = this.amb?.id; this.ctx = null; this.cur = null; this.amb = null; this.last.clear(); this.live = []; this.back = false;
    try { old.close(); } catch {}
    this.init(); if (amb) this.ambience(amb);
  }
  init() {
    if (this.ctx) return;
    const C = window.AudioContext || window.webkitAudioContext; if (!C) return;
    this.ctx = new C();
    this.master = this.ctx.createGain(); this.master.connect(this.ctx.destination);
    // a gentle bus compressor keeps big fights from clipping on phone speakers
    this.comp = this.ctx.createDynamicsCompressor(); this.comp.threshold.value = -14; this.comp.ratio.value = 3.5; this.comp.connect(this.master);
    this.sfxBus = this.ctx.createGain(); this.sfxBus.gain.value = this.vol.sfx; this.sfxBus.connect(this.comp);
    this.musBus = this.ctx.createGain(); this.musBus.gain.value = this.vol.music; this.musBus.connect(this.master);
    if (this.wantMusic) this.music(this.wantMusic);
  }
  has(id) { return !!this.man[id]; }
  setVol(k, v) { this.vol[k] = v; try { localStorage.setItem(KEY, JSON.stringify(this.vol)); } catch {} if (k === 'sfx' && this.sfxBus) this.sfxBus.gain.value = v; if (k === 'music' && this.musBus) this.musBus.gain.value = v; }
  async load(file) {
    if (this.buf.has(file)) return this.buf.get(file);
    if (!this.loading.has(file)) this.loading.set(file, fetch('assets/audio/' + file).then(r => { if (!r.ok) throw 0; return r.arrayBuffer(); })
      .then(a => new Promise((res, rej) => this.ctx.decodeAudioData(a, res, rej))).then(b => { this.buf.set(file, b); return b; }).catch(() => null));
    return this.loading.get(file);
  }
  preload(ids) { this.ready.then(() => { if (!this.ctx) this.init(); if (!this.ctx) return; for (const id of ids) { const m = this.man[id]; if (!m) continue; for (const f of m.variants?.length ? m.variants : [m.file]) this.load(f); } }); }
  // play(id, {vol, pan (-1..1), rate, gap (s: skip if the same id played closer than this)}) -> a handle whose stop(fade s)
  // cuts the sound short (an emote replaced by the next one), or null when nothing plays.
  // So a big fight stays readable: a sound's variants never repeat back to back, at most 3 copies of one sound ring at once
  // and 16 one-shots in all (the oldest short one fades out for the new), and one voice line (bark_/die_) at a time: a bark
  // over a playing voice is skipped, a death cuts a bark
  play(id, o = {}) {
    if (!this.ctx || !this.man[id]) return null;
    const m = this.man[id], now = this.ctx.currentTime, gap = o.gap ?? 0.04, voice = /^(bark|die)_/.test(id);
    if (now - (this.last.get(id) ?? -9) < gap) return null;
    if (voice) { const v = this.live.find(l => l.voice); if (v) { if (id.startsWith('bark_') || v.id.startsWith('die_')) return null; v.hd.stop(0.06); } }
    this.last.set(id, now);
    const files = m.variants?.length ? m.variants : [m.file];
    let i = Math.floor(Math.random() * files.length);
    if (files.length > 1 && i === this.lastVar.get(id)) i = (i + 1 + Math.floor(Math.random() * (files.length - 1))) % files.length;
    this.lastVar.set(id, i); const f = files[i];
    const drop = l => { const k = this.live.indexOf(l); if (k >= 0) this.live.splice(k, 1); };
    const hd = {stop: (fade = 0.04) => { hd.off = true; if (hd.l) drop(hd.l); if (!hd.s) return; const t = this.ctx.currentTime; hd.g.gain.cancelScheduledValues(t); hd.g.gain.setTargetAtTime(0, t, fade / 3); try { hd.s.stop(t + fade); } catch {} }};
    const go = b => {
      if (!b || hd.off) return;
      const same = this.live.filter(l => l.id === id); if (same.length >= 3) same[0].hd.stop(0.03);
      if (this.live.length >= 16) (this.live.find(l => l.short) || this.live[0]).hd.stop(0.03);
      const s = this.ctx.createBufferSource(); s.buffer = b; s.playbackRate.value = (o.rate ?? 1) * (1 + (Math.random() - 0.5) * (o.spread ?? 0.08));
      const g = this.ctx.createGain(); g.gain.value = (m.vol ?? 0.8) * (o.vol ?? 1);
      let tail = g;
      if (o.pan && this.ctx.createStereoPanner) { const p = this.ctx.createStereoPanner(); p.pan.value = Math.max(-1, Math.min(1, o.pan)); g.connect(p); tail = p; }
      s.connect(g); tail.connect(this.sfxBus); s.start(); hd.s = s; hd.g = g;
      const l = hd.l = {id, hd, voice, short: b.duration < 1}; this.live.push(l); s.onended = () => drop(l);
    };
    const b = this.buf.get(f); if (b) go(b); else this.load(f).then(go);
    return hd;
  }
  async music(id, fade = 1.2) {
    this.wantMusic = id;
    if (!this.ctx) return;
    await this.ready;
    if (this.cur?.id === id) return;
    const old = this.cur; this.cur = {id};
    if (old?.g) { old.g.gain.setTargetAtTime(0, this.ctx.currentTime, fade / 3); setTimeout(() => { try { old.s.stop(); } catch {} }, fade * 1500); }
    const m = this.man[id]; if (!m) return;
    const b = await this.load(m.file); if (!b || this.cur.id !== id) return;
    const s = this.ctx.createBufferSource(); s.buffer = b; s.loop = true;
    if (m.loopStart != null) s.loopStart = m.loopStart; if (m.loopEnd != null) s.loopEnd = m.loopEnd;
    const g = this.ctx.createGain(); g.gain.value = 0; g.gain.setTargetAtTime(m.vol ?? 0.5, this.ctx.currentTime, fade / 3);
    s.connect(g); g.connect(this.musBus); s.start(); this.cur.s = s; this.cur.g = g;
  }
  // the arena's ambience bed: a second loop under the music (quiet)
  async ambience(id, fade = 1.5) {
    if (!this.ctx) { this.wantAmb = id; return; }
    await this.ready;
    if (this.amb?.id === id) return;
    const old = this.amb; this.amb = {id};
    if (old?.g) { old.g.gain.setTargetAtTime(0, this.ctx.currentTime, fade / 3); setTimeout(() => { try { old.s.stop(); } catch {} }, fade * 1500); }
    const m = id && this.man[id]; if (!m) return;
    const b = await this.load(m.file); if (!b || this.amb.id !== id) return;
    const s = this.ctx.createBufferSource(); s.buffer = b; s.loop = true; if (m.loopStart != null) s.loopStart = m.loopStart; if (m.loopEnd != null) s.loopEnd = m.loopEnd;
    const g = this.ctx.createGain(); g.gain.value = 0; g.gain.setTargetAtTime((m.vol ?? 0.4) * 0.7, this.ctx.currentTime, fade / 3);
    s.connect(g); g.connect(this.sfxBus); s.start(); this.amb.s = s; this.amb.g = g;
  }
  stopMusic(fade = 0.8) { const c = this.cur; this.cur = null; this.wantMusic = null; if (c?.g) { c.g.gain.setTargetAtTime(0, this.ctx.currentTime, fade / 3); setTimeout(() => { try { c.s.stop(); } catch {} }, fade * 1500); } }
  duck(amount = 0.35, t = 1.5) { if (!this.musBus) return; const g = this.musBus.gain, n = this.ctx.currentTime; g.cancelScheduledValues(n); g.setTargetAtTime(this.vol.music * amount, n, 0.05); g.setTargetAtTime(this.vol.music, n + t, 0.4); }
}
export const audio = new Audio();
export const buzz = ms => { try { navigator.vibrate?.(ms); } catch {} };
