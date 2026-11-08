// The meme characters on the field: one animated copy per sim unit, dropped in from the sky, walking, swinging, flashing
// when hit, knocked out when they die. Also the NEET commanders seated on the Battlestations.
import * as THREE from 'three';
import {loadGLB, cloneGLB, unitMeta} from './assets.js';
import {TEAM_COL, TOWER_VIS} from './arena.js';
import {CARDS} from '../data.js';
import {formation} from '../sim.js';
import {D} from './kit.js';

// characters are drawn bigger than their footprint so they read on a phone (collisions use the sim's radius), and lean back,
// away from the camera (about world X, whatever way they face), like a billboard: the steep battle camera still sees them
// from the front. Tall ones grow a little less (h^0.85), so a Whale doesn't hide its lane.
export const VIS = 2.15, visH = h => VIS * h ** 0.85;
// a flyer (PNUT) is drawn this high (its feet): its acorns leave from about its middle (sim y = air, x VIS)
export const flyH = air => air * VIS * 0.6;
export const LEAN = -0.42;
const X = new THREE.Vector3(), XL = new THREE.Vector3(1, 0, 0), Z = new THREE.Vector3(0, 0, 1), QB = new THREE.Quaternion();
const LOOP = new Set(['idle', 'ready', 'walk', 'run', 'win', 'lose', 'sit']);
// whose character a card's troops are (FIRE SALE and USELESS ARMY are USELESS)
const modelOf = card => CARDS[card]?.unit?.model || card;
const FIRE = [1, 0.55, 0.15], DUST = [0.62, 0.6, 0.58];
// FIRE SALE's USELESS burn: ember red over the gold (and a flickering glow, flames above them), never mistaken for plain ones
const EMBER = new THREE.Color('#ff4a1c');
// a card's tint over a reused character (NPC WOJAK: grey WOJAKs), one colour per tint; WOJAK's gloom dims what it weakens
const TINTS = {}, tintOf = card => { const t = CARDS[card]?.unit?.tint; return t && (TINTS[t] ||= new THREE.Color(t)); };
const GLOOM = new THREE.Color(0.76, 0.7, 0.88);
// HARD FORK's copies: washed out toward the chain's blue-violet, so a one-hit copy is never mistaken for the real thing
const CLONE = new THREE.Color(0.6, 0.78, 1.25);
const SNOW = [0.86, 0.93, 1], SWEAT = [0.55, 0.85, 1];
const ATTACKS = ['attack1', 'attack2', 'attack3'];
let blobTex = null, gloomTex = null;
function blob() {
  if (blobTex) return blobTex;
  const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 4, 32, 32, 32); gr.addColorStop(0, 'rgba(0,0,0,0.55)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  return (blobTex = new THREE.CanvasTexture(c));
}
// WOJAK's reach on the ground: clear in the middle, a dusky band toward the edge
function gloom() {
  if (gloomTex) return gloomTex;
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(30,18,48,0)'); gr.addColorStop(0.6, 'rgba(30,18,48,0.06)'); gr.addColorStop(0.93, 'rgba(26,14,44,0.34)'); gr.addColorStop(1, 'rgba(26,14,44,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  return (gloomTex = new THREE.CanvasTexture(c));
}
// what hangs by a troop in a state, drawn once: a sprite's material over a 64 (or 128) canvas; no depth test, so nothing hides it
function spriteMat(S, draw, o = {}) {
  const c = document.createElement('canvas'); c.width = c.height = S; const g = c.getContext('2d'); draw(g, S);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return new THREE.SpriteMaterial({map: t, transparent: true, depthTest: false, depthWrite: false, ...o});
}
// APU's shield: a gold skin lit at its rim, a glint on it (additive: a thin ring on the screen, next to no fill)
const bubbleMat = () => spriteMat(128, (g, S) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,225,130,0.03)'); gr.addColorStop(0.72, 'rgba(255,225,130,0.1)'); gr.addColorStop(0.9, 'rgba(255,232,150,0.75)'); gr.addColorStop(1, 'rgba(255,232,150,0)');
  g.fillStyle = gr; g.fillRect(0, 0, S, S); g.fillStyle = 'rgba(255,255,240,0.8)'; g.beginPath(); g.ellipse(42, 38, 12, 7, -0.7, 0, 7); g.fill(); }, {blending: THREE.AdditiveBlending});
// PANIC SELL's "!" over a running troop; DIAMOND HANDS' gem over a guarded one
const bangMat = () => spriteMat(64, g => { g.font = '900 56px "Lilita One", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round'; g.lineWidth = 9; g.strokeStyle = '#2a0810'; g.strokeText('!', 32, 34); g.fillStyle = '#ff5a6e'; g.fillText('!', 32, 34); });
const gemMat = () => spriteMat(64, g => { const f = (c, ...p) => { g.fillStyle = c; g.beginPath(); for (let i = 0; i < p.length; i += 2) g.lineTo(p[i], p[i + 1]); g.closePath(); g.fill(); };
  g.lineJoin = 'round'; g.lineWidth = 7; g.strokeStyle = '#08222e'; g.beginPath(); g.moveTo(6, 25); g.lineTo(18, 10); g.lineTo(46, 10); g.lineTo(58, 25); g.lineTo(32, 58); g.closePath(); g.stroke();
  f('#a8ecff', 6, 25, 18, 10, 46, 10, 58, 25, 32, 58); f('#e8fbff', 18, 10, 46, 10, 40, 25, 24, 25); f('#6cc8ec', 40, 25, 58, 25, 32, 58); });
// MICHI's yarn round a troop's legs: one thread wound about a unit cylinder (radius 1, 0 to 1 up), as a tube
function tangle() {
  const pts = []; for (let i = 0; i < 22; i++) { const a = i * 2.2, y = 0.08 + (i * 5 % 11) / 11 * 0.92, d = 0.82 + (i * 3 % 5) / 5 * 0.3; pts.push(new THREE.Vector3(Math.cos(a) * d, y, Math.sin(a) * d)); }
  return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 88, 0.06, 5, true);
}
// WALTER's mound: a lump of earth, pushed about so it's no ball
function mound() {
  const g = new THREE.IcosahedronGeometry(1, 2), p = g.attributes.position, n0 = g.attributes.normal.array.slice();
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i), z = p.getZ(i), n = 1 + Math.sin(x * 5.3 + z * 2.1) * 0.13 + Math.sin(z * 6.7 - x * 3.1 + y * 4) * 0.1; p.setXYZ(i, x * n, Math.max(-0.05, y) * n * 0.62, z * n); }
  g.computeVertexNormals(); const n = g.attributes.normal.array; for (let i = 0; i < n.length; i++) n[i] = (n[i] + n0[i]) * 0.5;   // (half its sphere's: a heap, not a rock)
  return g;
}

export class UnitViews {
  constructor(stage, battle, fx) {
    this.stage = stage; this.battle = battle; this.fx = fx; if (fx) fx.units = this;
    this.root = new THREE.Group(); stage.scene.add(this.root);
    this.views = new Map(); this.templates = new Map(); this.meta = {};
    this.ringGeo = new THREE.RingGeometry(0.78, 1, 40).rotateX(-Math.PI / 2);
    this.blobGeo = new THREE.PlaneGeometry(2, 2).rotateX(-Math.PI / 2);
    this.ringMat = TEAM_COL.map(c => new THREE.MeshBasicMaterial({color: c, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending}));
    this.blobMat = new THREE.MeshBasicMaterial({map: blob(), transparent: true, depthWrite: false});
    // WOJAK's gloom (one look for every WOJAK: a dusky disc and a thin violet rim, breathing slowly)
    this.gloomGeo = new THREE.RingGeometry(0.965, 1, 72).rotateX(-Math.PI / 2);
    this.gloomDisc = new THREE.MeshBasicMaterial({map: gloom(), transparent: true, depthWrite: false});
    this.gloomRim = new THREE.MeshBasicMaterial({color: '#a68ad8', transparent: true, opacity: 0.22, depthWrite: false, blending: THREE.AdditiveBlending});
    this.commanders = []; this.guards = [];
  }
  clear() {
    for (const v of this.views.values()) { this.root.remove(v.root); v.gone = true; v.dead = true; for (const m of v.mats || []) m.dispose(); }
    this.views.clear(); this.commanders = []; this.guards = [];
  }
  // a display copy for menus: an entity-like object that never moves
  showcase(card, x, z, face, team = 0) {
    const c = CARDS[card]; if (c?.type !== 'unit') return null;
    const ent = {id: 'show-' + card + '-' + Math.random(), kind: 'unit', card, team, x, z, px: x, pz: z, face, h: c.unit.h, r: c.unit.r, state: 'show', hp: 1, max: 1, mass: c.unit.mass, speed: c.unit.speed};
    this.spawn(ent); return ent;
  }
  async preload(ids) {
    this.meta = await unitMeta();
    await Promise.all([...new Set(ids.filter(id => CARDS[id]?.type === 'unit').map(modelOf))].map(id => this.template(id)));
  }
  template(id) {
    if (!this.templates.has(id)) this.templates.set(id, loadGLB(`assets/units/${id}.glb`).then(g => {
      // measure once at rest
      const box = new THREE.Box3().setFromObject(g.scene); const h = this.meta[id]?.height || (box.max.y - box.min.y) || 1.7;
      const clips = {}; for (const a of g.animations) clips[a.name] = a;
      return {glb: g, h, clips};
    }).catch(() => null));
    return this.templates.get(id);
  }

  async spawn(ent) {
    const v = {ent, id: ent.id, card: ent.card, team: ent.team, root: new THREE.Group(), flash: 0, born: performance.now(), dead: false, y: 4.5, landed: false, cur: null, swing: 0};
    v.root.position.set(ent.x, 0, ent.z); v.root.rotation.y = ent.face;
    this.views.set(ent.id, v); this.root.add(v.root);
    const S = visH(ent.h);
    const ring = new THREE.Mesh(this.ringGeo, this.ringMat[ent.team]); ring.scale.setScalar(ent.r * 1.25); ring.position.y = 0.035; ring.renderOrder = 1; v.root.add(ring); v.ring = ring;
    const sh = new THREE.Mesh(this.blobGeo, this.blobMat); sh.scale.setScalar(ent.r * (ent.air ? 1.9 : 1.5)); sh.position.y = 0.025; v.root.add(sh); v.blob = sh;
    v.body = new THREE.Group(); v.root.add(v.body);
    v.flyY = ent.air ? flyH(ent.air) : 0; v.bank = 0; v.blinker = !!CARDS[ent.card]?.unit?.blink; v.slider = ent.card === 'pudgy'; v.slide = 0;
    // WOJAK: his gloom's reach on the ground around him, always (the sim's weaken radius)
    const wk = CARDS[ent.card]?.unit?.weaken;
    if (wk && ent.state !== 'show') {
      v.aura = new THREE.Group(); v.aura.scale.setScalar(wk[1]); v.aura.position.y = 0.03; v.aura.visible = false;
      const d = new THREE.Mesh(this.blobGeo, this.gloomDisc), rim = new THREE.Mesh(this.gloomGeo, this.gloomRim); rim.position.y = 0.004; rim.renderOrder = 1;
      v.aura.add(d, rim); v.root.add(v.aura);
    }
    const tint = tintOf(ent.card);
    // out of a hut, a grave or a fallen house: it climbs out of the ground instead of dropping in
    v.pop = ent.state === 'deploy' && ent.st < 0.6;
    if (ent.clone) this.fx.forkOut({x: ent.x, z: ent.z}, S);   // (HARD FORK's: blinks into being)
    else if (v.pop) this.fx.burst({x: ent.x, y: 0, z: ent.z}, {n: 8, c: [0.5, 0.42, 0.34], s: 0.5, sp: 1.6, up: 2, life: 0.5, g: 6, cell: 9, add: false, y: 0.1, floor: 0.04});
    v.fire = !!CARDS[ent.card]?.unit?.fire;
    const T = await this.template(modelOf(ent.card));
    if (v.dead && v.gone) return;
    if (T) {
      const c = cloneGLB(T.glb); v.model = c.scene; v.model.scale.setScalar(S / T.h);
      v.mats = [];
      v.model.traverse(o => { if (o.isMesh || o.isSkinnedMesh) { o.castShadow = this.stage.quality !== 'low'; o.receiveShadow = false; o.frustumCulled = false; o.material = o.material.clone(); o.material.emissive ??= new THREE.Color(0); if (v.fire) o.material.color?.multiply(EMBER); if (tint) o.material.color?.multiply(tint); v.mats.push(o.material); } });
      v.body.add(v.model);
      v.mixer = new THREE.AnimationMixer(v.model); v.clips = T.clips; v.actions = {};
      v.mixer.addEventListener('finished', e => this.finished(v, e.action));
    } else {
      // stand-in until the character art is there: a capsule in the team colour
      const m = new THREE.MeshStandardMaterial({color: TEAM_COL[ent.team].clone().multiplyScalar(0.7), roughness: 0.5, emissive: new THREE.Color(0)}); if (tint) m.color.multiply(tint);
      const cap = new THREE.Mesh(new THREE.CapsuleGeometry(ent.r * 0.7, S * 0.55, 4, 12), m); cap.position.y = S * 0.5; cap.castShadow = true;
      const head = new THREE.Mesh(new THREE.SphereGeometry(ent.r * 0.55, 16, 12), m); head.position.y = S * 0.95; head.castShadow = true;
      v.body.add(cap, head); v.mats = [m];
    }
    v.base = v.mats.map(m => m.color?.clone());   // (each colour as made, for the gloom to dim and give back)
    this.play(v, ent.state === 'deploy' ? 'ready' : 'idle', 0);
  }
  action(v, name) {
    if (!v.mixer) return null;
    let clip = v.clips[name];
    if (!clip) clip = v.clips[{ready: 'idle', run: 'walk', walk: 'run', attack2: 'attack1', attack3: 'attack1', emote: 'win', hit: null, lose: 'idle', win: 'idle'}[name]];
    if (!clip) return null;
    if (!v.actions[clip.name + ':' + name]) {
      const a = v.mixer.clipAction(clip); a.name_ = name;
      if (!LOOP.has(name)) { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; }
      v.actions[clip.name + ':' + name] = a;
    }
    return v.actions[clip.name + ':' + name];
  }
  play(v, name, fade = 0.18, ts = 1) {
    if (!v.mixer) { v.curName = name; return; }
    const a = this.action(v, name); if (!a) return;
    if (v.cur === a && LOOP.has(name)) { a.timeScale = ts; return; }
    a.reset(); a.timeScale = ts; a.enabled = true; a.setEffectiveWeight(1);
    // a loop handed on to a loop of the same length (a flyer's one flight loop is its idle, ready, walk and run) keeps its phase
    if (v.cur && LOOP.has(name) && LOOP.has(v.curName) && Math.abs(v.cur.getClip().duration - a.getClip().duration) < 1e-3) a.time = v.cur.time;
    if (v.cur && v.cur !== a) a.crossFadeFrom(v.cur, fade, false);
    a.play(); v.cur = a; v.curName = name;
  }
  finished(v, a) {
    if (v.dead || a !== v.cur) return;
    if (ATTACKS.includes(v.curName) || v.curName === 'hit' || v.curName === 'emote') this.play(v, v.ent.state === 'show' ? 'idle' : 'ready', 0.15);
  }

  onEvent(e) {
    const v = this.views.get(e.id);
    switch (e.type) {
      case 'attack': if (v) {
        const n = ATTACKS.filter(a => v.clips?.[a]).length || 1; const name = ATTACKS[(e.swing - 1) % n];
        const meta = this.meta[modelOf(v.card)]?.clips?.[name], hit = meta?.hit ?? (v.clips?.[name]?.duration || 0.6) * 0.5;
        const ts = THREE.MathUtils.clamp(hit / Math.max(0.12, e.hitAt), 0.55, 2.6);
        this.play(v, name, 0.08, ts); v.attackUntil = performance.now() + e.hs * 1000;
      } break;
      case 'dmg': if (v) v.flash = 1; break;
      case 'down': if (v) { this.play(v, 'die', 0.1); v.down = true; } break;
      case 'revive': if (v) { v.down = false; this.play(v, 'emote', 0.2); this.fx.revive(v.root.position); } break;
      case 'die': if (v) { if (CARDS[v.card]?.unit?.kamikaze) { v.dead = true; v.deathT = 0.95; v.root.visible = false; } else this.kill(v); } break;
      case 'landed': if (v) { v.landed = true; } break;
      // TROLLFACE: there at once (the sim moved him and his px/pz), facing the one he's behind, with a little pop
      case 'blink': if (v) { v.root.rotation.y = v.ent.face; v.squash = 1; } break;
      // FLOKI: he bulks up as he snaps, and stays so
      case 'berserk': if (v) { v.big = 1.12; v.squash = 1; } break;
      // WALTER: a squash going under, a hop coming up
      case 'dig': if (v) v.squash = 1; break;
      case 'surface': if (v) { v.squash = 1; v.root.position.y = 1.3; } break;
      // knocked back by BONK: a flinch and dust under the feet while it slides
      case 'knock': if (v) { v.pushT = 0.3; if (!v.ent.beamOn) { this.play(v, 'hit', 0.05, 1.3); v.attackUntil = performance.now() + 280; } } break;
    }
  }
  kill(v) {
    v.dead = true; v.deathT = 0; this.play(v, 'die', 0.06, 1.7);
    if (v.ent.clone) this.fx.forkOut(v.root.position, visH(v.ent.h)); else this.fx.poof(v.root.position, visH(v.ent.h), v.card, v.flyY);
  }
  // a tower fell: the side that took it taunts for a moment (those not busy swinging)
  taunt(team) {
    for (const v of this.views.values()) if (v.team === team && !v.dead && !v.ent.beamOn && !(v.attackUntil && performance.now() < v.attackUntil) && Math.random() < 0.8) { this.play(v, 'emote', 0.15); v.attackUntil = performance.now() + 1400; }
  }
  // the end: winners celebrate, losers slump
  celebrate(winner) {
    for (const v of this.views.values()) if (!v.dead) this.play(v, v.team === winner ? 'win' : winner === -1 ? 'idle' : 'lose', 0.3);
    for (const c of this.commanders) if (c.mixer) this.cmd(c, c.team === winner ? 'sitfistpump' : 'sitangry', true);
  }

  update(dt, alpha) {
    const B = this.battle;
    if (B) for (const e of B.ents.values()) if (e.kind === 'unit' && !this.views.has(e.id)) this.spawn(e);
    const now = performance.now();
    this.gloomRim.opacity = 0.2 + Math.sin(now / 600) * 0.06;
    for (const v of this.views.values()) {
      const e = v.ent;
      if (v.dead) {
        v.deathT += dt;
        if (v.aura) v.aura.visible = false;
        if (v.up) v.up.visible = false; if (v.yarn) v.yarn.visible = false; if (v.dirt) v.dirt.visible = false;
        if (v.flyY > 0) { v.flyY = Math.max(0, v.flyY - dt * (5 + v.deathT * 24)); v.body.position.y = v.flyY; }   // (a flyer drops out of the sky)
        if (v.deathT > 0.55) { const k = Math.min(1, (v.deathT - 0.55) / 0.35); v.root.position.y = -k * 0.6; for (const m of v.mats || []) { m.transparent = true; m.opacity = 1 - k; } v.ring.material = this.ringMat[v.team]; v.ring.visible = false; }
        if (v.deathT > 0.95) { this.root.remove(v.root); this.views.delete(v.id); v.gone = true; for (const m of v.mats || []) m.dispose(); }
        v.mixer?.update(dt);
        continue;
      }
      if (e.state === 'show') {   // menu display copies just idle (or play what they're told)
        v.root.position.set(e.x, 0, e.z); v.root.rotation.y = e.face;
        if (!v.curName || (!v.cur?.isRunning() && v.curName !== 'idle')) this.play(v, 'idle', 0.3);
        v.mixer?.update(dt); continue;
      }
      // position: interpolate the fixed sim steps
      const x = e.px + (e.x - e.px) * alpha, z = e.pz + (e.z - e.pz) * alpha;
      // TROLLFACE: a jump no legs make is a blink (online the snapshots slide it over a few frames): unseen while it lasts, and
      // where he last stood still is where his puff goes
      if (v.blinker) { const d = Math.hypot(x - v.root.position.x, z - v.root.position.z); v.body.visible = d < Math.max(0.35, dt * 15); if (v.body.visible) { v.calmX = x; v.calmZ = z; } }
      v.root.position.x = x; v.root.position.z = z;
      // drop-in from the sky during the deploy, a squash on landing
      if (e.state === 'deploy') {
        const age = (performance.now() - v.born) / 1000, k = Math.min(1, age / 0.32);
        v.root.position.y = v.pop ? (k * (2 - k) - 1) * 0.9 : (1 - k * k) * 4.5;
        if (k >= 1 && !v.touched) { v.touched = true; v.squash = 1; this.fx.land(v.root.position, e.r, e.team, e.mass); }
      } else {
        if (!v.touched) { v.touched = true; v.squash = 1; this.fx.land(v.root.position, e.r, e.team, e.mass); }
        v.root.position.y = e.airT > 0 ? Math.max(v.root.position.y, 0) + (1.1 - v.root.position.y) * Math.min(1, dt * 10) : v.root.position.y * Math.max(0, 1 - dt * 10);
      }
      if (v.squash > 0) { v.squash = Math.max(0, v.squash - dt * 6); const s = 1 - Math.sin(v.squash * Math.PI) * 0.18, b = v.big || 1; v.body.scale.set((2 - s) * b, s * b, (2 - s) * b); }
      if (v.aura) v.aura.visible = e.state !== 'deploy';
      // facing, and the lean toward the camera (world X seen from the turned root)
      let df = e.face - v.root.rotation.y; while (df > Math.PI) df -= Math.PI * 2; while (df < -Math.PI) df += Math.PI * 2;
      const turn = df * Math.min(1, dt * 16); v.root.rotation.y += turn;
      // (PUDGY's charge is a belly slide: flat on his front, head first; the lean eases off, or his head would go through the ground)
      if (v.slider) v.slide += ((e.charging && e.moving ? 1 : 0) - v.slide) * Math.min(1, dt * 14);
      const f = v.root.rotation.y; v.body.quaternion.setFromAxisAngle(X.set(Math.cos(f), 0, Math.sin(f)), LEAN * (1 - v.slide * 0.85));
      if (v.slide > 0.01) v.body.quaternion.multiply(QB.setFromAxisAngle(XL, v.slide * 1.3));
      if (e.rootT > 0) v.body.quaternion.multiply(QB.setFromAxisAngle(Z, Math.sin(now / 55) * 0.07));   // (tangled: he strains at it)
      // a flyer banks into its turns (a roll about its own forward axis, under the lean)
      if (v.flyY) { v.bank += (THREE.MathUtils.clamp(-turn / Math.max(dt, 1e-3) * 0.12, -0.4, 0.4) - v.bank) * Math.min(1, dt * 5); v.body.quaternion.multiply(QB.setFromAxisAngle(Z, v.bank)); }
      // animation state (MOO DENG's charge: a flat-out run)
      if (!v.down) {
        const attacking = v.attackUntil && now < v.attackUntil;
        if (e.beamOn) { if (!ATTACKS.includes(v.curName)) this.play(v, 'attack1', 0.12, 0.6); }
        else if (e.stunT > 0) this.play(v, 'hit', 0.06, 0.4);
        else if (!attacking) {
          if (e.moving && e.charging) { if (v.slider) this.play(v, 'ready', 0.1); else this.play(v, 'run', 0.1, 1.5 * (e.slowT > 0 ? e.slowK : 1)); }
          else if (e.moving) { const run = e.speed * (e.rageT > 0 ? 1.4 : 1) * (e.slowT > 0 ? e.slowK : 1) >= 1.5; this.play(v, run ? 'run' : 'walk', 0.12, THREE.MathUtils.clamp(e.speed / (run ? 1.8 : 1.0), 0.85, 1.5) * (e.slowT > 0 ? e.slowK : 1) * (e.rageT > 0 ? 1.3 : 1)); }
          else if (!ATTACKS.includes(v.curName) || v.cur?.paused || !v.cur?.isRunning()) this.play(v, 'ready', 0.12);
        }
        // a flyer floats at its height with a slow bob; the stand-in capsule hops as it walks
        v.body.position.y = (v.flyY ? v.flyY + Math.sin(now / 380 + v.root.id) * 0.14 : 0) + (!v.mixer && e.moving && !v.flyY && !(v.slide > 0.05) ? Math.abs(Math.sin(now / (e.charging ? 70 : 120))) * 0.12 : 0);
      }
      if (v.slider) { const H = visH(e.h); v.body.position.y += v.slide * H * 0.16; v.body.position.z = -v.slide * H * 0.42; }   // (his middle over where he is)
      // the dust: MOO DENG's charge kicks it up behind her; a troop knocked back (BONK) skids on it
      if (e.charging && e.moving && Math.random() < dt * 28) { const bx = -Math.sin(e.face), bz = -Math.cos(e.face);
        this.fx.norm.emit({x: x + bx * e.r + (Math.random() - 0.5) * 0.5, y: 0.15, z: z + bz * e.r + (Math.random() - 0.5) * 0.5, vx: bx * 0.9, vy: 0.5, vz: bz * 0.9, drag: 1.5, life: 0.75, s0: 0.6, s1: 1.5, c: v.slider ? SNOW : DUST, a0: 0.55, cell: 3}); }
      if (v.pushT > 0) { v.pushT -= dt; if (Math.random() < dt * 40) this.fx.norm.emit({x: x + (Math.random() - 0.5) * 0.4, y: 0.1, z: z + (Math.random() - 0.5) * 0.4, vy: 0.4, life: 0.5, s0: 0.45, s1: 1.0, c: DUST, a0: 0.55, cell: 3}); }
      this.states(v, e, dt, now);
      // HARD FORK's copy: its colours washed out for good (the weak dim below works from these)
      if (e.clone && v.base && !v.cloned) { v.cloned = true; v.mats.forEach((m, i) => { if (v.base[i]) m.color.copy(v.base[i].multiply(CLONE)); }); }
      // WOJAK's gloom: what it weakens goes dim and a little violet while it lasts
      const weak = e.weakT > 0;
      if (v.base && weak !== !!v.weak) { v.weak = weak; v.mats.forEach((m, i) => { if (v.base[i]) { m.color.copy(v.base[i]); if (weak) m.color.multiply(GLOOM); } }); }
      // hit flash and status tints (frozen: icy and still; charging: an angry warm pulse)
      if (v.flash > 0) v.flash = Math.max(0, v.flash - dt * 7);
      const slow = e.slowT > 0, rage = e.rageT > 0, ice = e.frozenT > 0;
      const burn = v.fire ? 0.2 + Math.sin(now / 70 + v.root.id) * 0.06 + Math.random() * 0.04 : 0, chg = e.charging ? 0.1 + Math.sin(now / 60) * 0.05 : 0;
      // (FLOKI's rage: a hot pulse; DIAMOND HANDS: an ice-blue shine; PANIC SELL: gone pale; a copy: a faint flicker of the chain's blue)
      const mad = e.mad ? 0.34 + Math.sin(now / 75 + v.root.id) * 0.1 : 0, gd = e.guardT > 0 ? 0.15 + Math.sin(now / 170 + v.root.id) * 0.05 : 0, pale = e.fearT > 0 ? 0.12 : 0, cl = e.clone ? 0.13 + Math.sin(now / 85 + v.root.id) * 0.05 : 0;
      for (const m of v.mats || []) {
        const f = v.flash * 0.75;
        if (ice) m.emissive.setRGB(0.25 + f, 0.5 + f, 0.75 + f);
        else m.emissive.setRGB(f + (rage ? 0.05 : 0) + (slow ? 0.08 : 0) + (v.fire ? burn : 0) + chg + (weak ? 0.03 : 0) + mad + gd * 0.35 + pale * 0.5 + cl * 0.2, f + (rage ? 0.25 : 0) + (v.fire ? burn * 0.15 : 0) + chg * 0.3 + mad * 0.12 + gd * 0.8 + pale * 0.8 + cl * 0.55, f + (slow ? 0.18 : 0) + (weak ? 0.07 : 0) + gd * 1.15 + pale * 1.3 + cl);
      }
      if (v.fire && Math.random() < dt * 34) this.fx.add.emit({x: v.root.position.x + (Math.random() - 0.5) * 0.45, y: v.root.position.y + visH(e.h) * (0.45 + Math.random() * 0.6), z: v.root.position.z, vy: 1.9, life: 0.42, s0: 1.0, s1: 0.15, c: FIRE, cell: 13});
      if (ice) { if (Math.random() < dt * 3) this.fx.add.emit({x: v.root.position.x, y: e.h * 1.2, z: v.root.position.z, vy: 0.3, life: 0.6, s0: 0.3, s1: 0, c: [0.8, 0.95, 1], cell: 5}); v.root.position.y = 0; continue; }
      v.ring.material.opacity = 0.55;
      v.mixer?.update(dt);
    }
    for (const c of this.commanders) c.mixer?.update(dt);
    for (const g of this.guards) g.mixer.update(dt);
    if (this.ghostV?.mixers) for (const m of this.ghostV.mixers) m.update(dt);
  }

  // the second wave's states, as a troop wears them: nothing here is made until a troop first needs it, one geometry and material serve
  // them all, and it all works on a stand-in as on a model (only v.root, v.body and the sim's fields)
  states(v, e, dt, now) {
    const x = v.root.position.x, z = v.root.position.z, H = visH(e.h), fly = v.flyY || 0, dug = !!e.dug, jx = x + (Math.random() - 0.5) * e.r * 1.4;
    // WALTER underground: no body, no shadow, only his ring; a mound of earth shouldering along over him, clods thrown off it, a furrow behind
    if (dug !== !!v.dug) { v.dug = dug; v.body.visible = !dug; v.blob.visible = !dug; if (dug) { v.trackX = x; v.trackZ = z; } }
    if (dug && !v.dirt) { v.dirt = new THREE.Mesh(this.moundGeo ||= mound(), this.moundMat ||= new THREE.MeshStandardMaterial({color: '#5e4230', roughness: 1})); v.dirt.position.y = 0.02; v.root.add(v.dirt); }
    if (v.dirt) v.dirt.visible = dug;
    if (dug) { const s = e.r * 1.35, q = Math.sin(now / 55); v.dirt.scale.set(s * (1 + q * 0.07), s * (1 - q * 0.1), s * 1.2);
      if (Math.random() < dt * 20) this.fx.norm.emit({x: jx, y: 0.25, z: z + (Math.random() - 0.5) * e.r * 1.4, vx: (Math.random() - 0.5) * 2, vy: 2 + Math.random() * 2, vz: (Math.random() - 0.5) * 2, g: 12, life: 0.5, s0: 0.3, s1: 0.2, c: [0.42, 0.3, 0.2], cell: 21, floor: 0.05});
      if (Math.random() < dt * 8) this.fx.norm.emit({x, y: 0.2, z, vy: 0.4, life: 0.6, s0: 0.5, s1: 1.1, c: DUST, a0: 0.45, cell: 3});
      if (Math.hypot(x - v.trackX, z - v.trackZ) > 0.45) { v.trackX = x; v.trackZ = z; this.fx.dc.emit({kind: D.STAIN, x, z, r: e.r * 1.2, life: 1.5, c: [0.11, 0.08, 0.055], c2: [0, 0, 0], a0: 0.75, a1: 0}); } }
    // MICHI's yarn: wound round his legs while it holds him
    const root = e.rootT > 0 && !dug;
    if (root && !v.yarn) { v.yarn = new THREE.Mesh(this.yarnGeo ||= tangle(), this.yarnMat ||= new THREE.MeshStandardMaterial({color: '#ff74b4', roughness: 0.9})); v.yarn.scale.set(e.r * 1.3, H * 0.42, e.r * 1.3); v.root.add(v.yarn); }
    if (v.yarn) { v.yarn.visible = root; if (root) v.yarn.rotation.y += dt * 0.6; }
    // what hangs in the air by him: on a group that doesn't turn with him, up where he leans
    const sh = e.shield > 0, guard = e.guardT > 0, fear = e.fearT > 0;
    if ((sh || guard || fear) && !v.up) { v.up = new THREE.Group(); v.root.add(v.up); }
    if (v.up) v.up.rotation.y = -v.root.rotation.y;
    // APU's shield: a gold skin round him while there's any of it left
    if (sh && !v.shell) { v.shell = new THREE.Sprite(this.shellMat ||= bubbleMat()); v.shell.renderOrder = 7; v.shell.scale.setScalar(Math.max(H * 1.05, e.r * 3)); v.up.add(v.shell); }
    if (v.shell) { v.shell.visible = sh; if (sh) v.shell.position.set(0, fly + H * 0.5 * Math.cos(LEAN), H * 0.5 * Math.sin(LEAN)); }
    // over his head: "!" while he runs (PANIC SELL), a gem while it holds (DIAMOND HANDS)
    const mk = fear ? this.bangMat ||= bangMat() : guard ? this.gemMat ||= gemMat() : null;
    if (mk && !v.mark) { v.mark = new THREE.Sprite(mk); v.mark.renderOrder = 7; v.mark.scale.setScalar(0.62); v.up.add(v.mark); }
    if (v.mark) { v.mark.visible = !!mk; if (mk) { v.mark.material = mk; v.mark.position.set(0, fly + H * Math.cos(LEAN) + 0.72 + Math.sin(now / 130 + v.root.id) * 0.06, H * Math.sin(LEAN)); } }
    // a little of each coming off him (few, and short)
    if (e.mad && Math.random() < dt * 11) this.fx.add.emit({x: jx, y: H * (0.3 + Math.random() * 0.6) + fly, z, vy: 1.6, life: 0.4, s0: 0.75, s1: 0.1, c: FIRE, cell: 13});
    if (guard && Math.random() < dt * 5) this.fx.add.emit({x: jx, y: H * (0.2 + Math.random() * 0.7) + fly, z, life: 0.4, s0: 0.5, s1: 0, c: [0.75, 0.95, 1], cell: 5});
    if (fear && Math.random() < dt * 8) this.fx.norm.emit({x: jx, y: H * 0.85 + fly, z, vx: (Math.random() - 0.5) * 2, vy: 1.6, vz: (Math.random() - 0.5) * 2, g: 8, life: 0.4, s0: 0.2, s1: 0.1, c: SWEAT, cell: 6, floor: 0.05});
  }

  // ---------- the NEET on the throne
  async commander(T, team) {
    const glb = await loadGLB('assets/units/neet.glb').catch(() => null); if (!glb || !T.seat) return;
    const c = cloneGLB(glb), m = c.scene, h = this.meta.neet?.sitHeight || 1.39;   // (his height seated; height is standing, for the card)
    m.scale.setScalar(1.45 / h);
    m.traverse(o => { if (o.isMesh) { o.castShadow = true; o.frustumCulled = false; } });
    T.seat.add(m);
    // the seat empty is scaled with the tower; undo its scale so the NEET keeps his size
    const ws = new THREE.Vector3(); T.seat.getWorldScale(ws); m.scale.divide(ws).multiplyScalar(TOWER_VIS);
    const C = {team, T, model: m, mixer: new THREE.AnimationMixer(m), clips: Object.fromEntries(c.animations.map(a => [a.name, a])), cur: null};
    C.mixer.addEventListener('finished', () => this.cmd(C, 'sit'));
    this.commanders.push(C); T.commander = C; this.cmd(C, 'sit');
  }
  cmd(C, name, hold = false) {
    const clip = C.clips[name] || C.clips.sit || C.clips.sitstill; if (!clip) return;
    const a = C.mixer.clipAction(clip); a.reset();
    if (name !== 'sit' && name !== 'sitstill') { a.setLoop(hold ? THREE.LoopRepeat : THREE.LoopOnce, Infinity); a.clampWhenFinished = true; }
    if (C.cur && C.cur !== a) a.crossFadeFrom(C.cur, 0.25, false);
    a.play(); C.cur = a;
  }
  react(team, name) { for (const C of this.commanders) if (C.team === team && C.T && !C.T.ruined && (!C.busy || C.busy < performance.now())) { C.busy = performance.now() + 2500; this.cmd(C, name); } }
  // the guard on a Rig Tower: a meme character on the deck, inside the tower's `turret` so he turns with its aim; his eyes
  // are the muzzle (laser eyes), and he plays a quick attack each time the tower fires
  async guard(T, team, id = 'chillguy') {
    const glb = await loadGLB(`assets/units/${id}.glb`).catch(() => null); if (!glb || !T.turret) return;
    const c = cloneGLB(glb), m = c.scene, h = this.meta[id]?.height || 1.7;
    m.scale.setScalar(1.55 / h);
    m.traverse(o => { if (o.isMesh) { o.castShadow = true; o.frustumCulled = false; } });
    T.turret.add(m);
    const ws = new THREE.Vector3(); T.turret.getWorldScale(ws); m.scale.divide(ws).multiplyScalar(TOWER_VIS);
    const clips = Object.fromEntries(c.animations.map(a => [a.name, a])), mixer = new THREE.AnimationMixer(m);
    const G = {team, T, model: m, mixer, clips, idle: mixer.clipAction(clips.ready || clips.idle || c.animations[0])};
    G.idle.play(); mixer.addEventListener('finished', () => { G.idle.reset().fadeIn(0.15).play(); });
    this.guards.push(G); T.guard = G;
  }
  guardShot(T) {
    const G = T?.guard, clip = G?.clips.attack1; if (!clip) return;
    const a = G.mixer.clipAction(clip); a.reset(); a.setLoop(THREE.LoopOnce, 1); a.timeScale = 1.5;
    G.idle.fadeOut(0.08); a.fadeIn(0.08).play();
  }
  dropGuard(T) { const G = T?.guard; if (!G) return; G.model.parent?.remove(G.model); this.guards = this.guards.filter(x => x !== G); T.guard = null; }
  dropCommander(T) { const C = T.commander; if (!C) return; C.model.parent?.remove(C.model); this.commanders = this.commanders.filter(x => x !== C); }

  // the deploy preview: a see-through copy of the character (idling) on the tile under the finger
  async ghost(card, x, z, ok, team = 0) {
    const c = CARDS[card];
    if (!c || c.type !== 'unit') { this.ghostHide(); return; }
    if (!this.ghostV || this.ghostV.card !== card) {
      this.ghostHide(); const G = this.ghostV = {card, root: new THREE.Group()}; G.root.rotation.x = LEAN; this.root.add(G.root);
      G.mat ||= new THREE.MeshBasicMaterial({color: '#bfffb0', transparent: true, opacity: 0.62, depthWrite: false});
      const T = await this.template(modelOf(card)); if (this.ghostV !== G || !T) return;
      const F = formation(c.unit.n || 1);
      G.mixers = [];
      for (const [ox, oz] of F) {
        const m = cloneGLB(T.glb).scene; m.scale.setScalar(visH(c.unit.h) / T.h); m.position.set(ox, c.unit.air ? flyH(c.unit.air) : 0, oz); m.rotation.y = Math.PI;
        m.traverse(o => { if (o.isMesh) { o.material = G.mat; o.frustumCulled = false; o.castShadow = false; o.renderOrder = 4; } });
        G.root.add(m); const mx = new THREE.AnimationMixer(m); const clip = T.clips.ready || T.clips.idle; if (clip) mx.clipAction(clip).play(); G.mixers.push(mx);
      }
    }
    const G = this.ghostV; G.root.visible = true; G.root.position.set(x, 0, z);
    G.mat?.color.set(ok ? '#bfffb0' : '#ff5a78');
  }
  ghostHide() { if (!this.ghostV) return; this.root.remove(this.ghostV.root); this.ghostV = null; }

  // above the head, leaning with the body (a flyer's up where it flies)
  headOf(id, out = new THREE.Vector3()) { const v = this.views.get(id); if (!v) return null; const H = visH(v.ent.h) * 1.05;
    return out.set(v.root.position.x, v.root.position.y + (v.flyY || 0) + H * Math.cos(LEAN) + 0.2, v.root.position.z + H * Math.sin(LEAN)); }
  // a point of the body, f of its height up (PNUT's acorn leaves from his middle), or null
  bodyOf(id, f = 0.5, out = new THREE.Vector3()) { const v = this.views.get(id); if (!v) return null; const H = visH(v.ent.h) * f;
    return out.set(v.root.position.x, v.root.position.y + (v.flyY || 0) + H * Math.cos(LEAN), v.root.position.z + H * Math.sin(LEAN)); }
  // a bone's world position (NYAN CAT's hips: her rainbow leaves from there), or null
  boneOf(id, re, out = new THREE.Vector3()) { const v = this.views.get(id); if (!v) return null; const B = v.bones ||= {};
    if (!(re.source in B)) { let f = null; v.root.traverse(o => { if (!f && o.isBone && re.test(o.name)) f = o; }); B[re.source] = f; }
    return B[re.source] ? B[re.source].getWorldPosition(out) : null; }
  // where TROLLFACE stood before his blink (as last drawn standing; else the sim's)
  blinkFrom(e) { const v = this.views.get(e.id); return v?.calmX != null && Math.hypot(v.calmX - e.x, v.calmZ - e.z) > 0.8 ? {x: v.calmX, z: v.calmZ} : {x: e.x0 ?? e.x, z: e.z0 ?? e.z}; }
}
