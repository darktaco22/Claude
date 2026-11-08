// The 2D layer over the 3D view: tower health plates with numbers, unit health bars with level badges, deploy clocks,
// floating numbers. Drawn on its own canvas so it stays crisp at any pixel ratio.
import * as THREE from 'three';
import {TOWER_VIS} from './arena.js';
import {BLD_VIS} from './blds.js';
import {CARDS} from '../data.js';

const COL = ['#7CFF6B', '#FF4D6D'], DARK = ['#1d4a17', '#4a1520'];
export class Overlay {
  constructor(canvas, stage, battle, units) {
    this.c = canvas; this.g = canvas.getContext('2d'); this.stage = stage; this.b = battle; this.units = units;
    this.texts = []; this.v = new THREE.Vector3(); this.p = {x: 0, y: 0};
    this.resize(); this.onResize = () => this.resize(); addEventListener('resize', this.onResize);
  }
  destroy() { removeEventListener('resize', this.onResize); this.g.clearRect(0, 0, this.c.width, this.c.height); }
  resize() { this.dpr = Math.min(2, devicePixelRatio); this.c.width = innerWidth * this.dpr; this.c.height = innerHeight * this.dpr; this.scale = Math.min(1.25, Math.max(0.8, Math.min(innerWidth, innerHeight * 0.56) / 400)); }
  float(x, y, z, str, col, size = 1) { this.texts.push({x, y, z, str, col, t: 0, size}); }
  rr(x, y, w, h, r) { const g = this.g; g.beginPath(); g.roundRect ? g.roundRect(x, y, w, h, r) : g.rect(x, y, w, h); }
  draw(dt) {
    const g = this.g, s = this.scale; g.setTransform(this.dpr, 0, 0, this.dpr, 0, 0); g.clearRect(0, 0, innerWidth, innerHeight);
    const B = this.b;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    // towers: each plate sits off its tower, on the side away from the river, so it hides neither the tower nor the one on
    // it: the opponent's above the guard's (or the NEET's) head, mine under the tower's foot
    for (const side of B.towers) for (const t of side) {
      if (t.dead) continue;
      const hq = t.type === 'hq', mine = t.team === 0, h = 13 * s;
      if (mine) this.v.set(t.x, 0, t.z + (t.r || 1.5) * TOWER_VIS); else this.v.set(t.x, t.h * TOWER_VIS + (hq ? 2.2 : 2.3), t.z);
      this.stage.toScreen(this.v, this.p); this.p.y += mine ? h / 2 + 4 * s : -(h / 2 + 2 * s);
      const w = (hq ? 84 : 66) * s, x = this.p.x - w / 2, y = this.p.y - h / 2, k = Math.max(0, t.hp / t.max);
      g.fillStyle = 'rgba(11,12,16,.9)'; this.rr(x - 3, y - 3, w + 6, h + 6, 6 * s); g.fill();
      g.fillStyle = DARK[t.team]; this.rr(x, y, w, h, 4 * s); g.fill();
      if (k > 0) { g.fillStyle = COL[t.team]; this.rr(x, y, Math.max(h * 0.6, w * k), h, 4 * s); g.fill(); g.fillStyle = 'rgba(255,255,255,.28)'; this.rr(x + 2, y + 1.5, Math.max(0, w * k - 4), h * 0.32, 3); g.fill(); }
      g.font = `800 ${11 * s}px Rubik, sans-serif`; g.lineWidth = 3 * s; g.strokeStyle = '#0B0C10'; g.fillStyle = '#F2EEDF';
      const txt = Math.ceil(t.hp).toLocaleString('en-US'); g.strokeText(txt, this.p.x, this.p.y + 0.5); g.fillText(txt, this.p.x, this.p.y + 0.5);
      if (hq && !t.active) { g.font = `${10 * s}px "Lilita One", sans-serif`; g.strokeText('ZZZ', this.p.x + w / 2 + 12 * s, this.p.y - 8 * s); g.fillStyle = '#c9d0ff'; g.fillText('ZZZ', this.p.x + w / 2 + 12 * s, this.p.y - 8 * s); }
    }
    // units
    for (const v of this.units.views.values()) {
      const e = v.ent; if (v.dead || e.state === 'down' || e.dead || e.dug) continue;   // (WALTER underground: only his mound shows)
      this.units.headOf(e.id, this.v); this.stage.toScreen(this.v, this.p);
      if (e.state === 'deploy') {
        const k = 1 - Math.max(0, e.st) / 1.0, r = 8 * s;
        g.beginPath(); g.arc(this.p.x, this.p.y, r, 0, Math.PI * 2); g.fillStyle = 'rgba(11,12,16,.75)'; g.fill();
        g.beginPath(); g.moveTo(this.p.x, this.p.y); g.arc(this.p.x, this.p.y, r - 2, -Math.PI / 2, -Math.PI / 2 + k * Math.PI * 2); g.closePath(); g.fillStyle = COL[e.team]; g.fill();
        continue;
      }
      const dmg = e.hp < e.max, recent = performance.now() - v.born < 1600, sh = e.shield > 0 ? e.shield : 0;
      if (!dmg && !recent && !sh) continue;
      const big = e.max > 1500, w = (big ? 40 : e.max < 300 ? 18 : 28) * s, h = 5 * s, x = this.p.x - w / 2 + 4 * s, y = this.p.y;
      g.fillStyle = 'rgba(11,12,16,.85)'; this.rr(x - 1.5, y - 1.5, w + 3, h + 3, 3); g.fill();
      // (APU's shield: a gold segment carried on the end of the health; with it the bar stands for all he can take)
      const of = Math.max(e.max, e.hp + sh), hw = Math.max(1, w * Math.max(0, e.hp / of));
      g.fillStyle = COL[e.team]; this.rr(x, y, hw, h, 2); g.fill();
      if (sh) { g.fillStyle = '#ffe48a'; this.rr(x + hw, y, Math.max(2, w * sh / of), h, 2); g.fill(); }
      // level badge
      const lv = (this.b.levels[e.team][e.card]) || 1, bx = x - 7 * s;
      g.fillStyle = e.team === 0 ? '#2a7a22' : '#9a2238'; g.strokeStyle = '#0B0C10'; g.lineWidth = 1.5;
      this.rr(bx - 5 * s, y - 2.5 * s, 10 * s, 10 * s, 2 * s); g.fill(); g.stroke();
      g.fillStyle = '#F2EEDF'; g.font = `800 ${7.5 * s}px Rubik, sans-serif`; g.fillText(lv, bx, y + 2.6 * s);
      if (e.slowT > 0) { g.fillStyle = '#ff8fd1'; g.font = `${9 * s}px "Lilita One", sans-serif`; g.fillText('STICKY', this.p.x, y - 8 * s); }
      if (e.stunT > 0) { g.fillStyle = '#9fc0ff'; g.font = `${9 * s}px "Lilita One", sans-serif`; g.fillText('FUD!', this.p.x, y - 8 * s); }
    }
    // buildings: health (draining with their life)
    for (const e of this.b.ents.values()) {
      if (e.kind !== 'bld' || e.dead) continue;
      this.v.set(e.x, e.h * BLD_VIS + 0.6, e.z); this.stage.toScreen(this.v, this.p);
      const w = 34 * s, h = 5 * s, x = this.p.x - w / 2, y = this.p.y;
      g.fillStyle = 'rgba(11,12,16,.85)'; this.rr(x - 1.5, y - 1.5, w + 3, h + 3, 3); g.fill();
      g.fillStyle = COL[e.team]; this.rr(x, y, Math.max(1, w * Math.max(0, e.hp / e.max)), h, 2); g.fill();
      // (SNIPER BOT setting up: a clock over it; it fires when it's full)
      const setup = e.state === 'deploy' && CARDS[e.card]?.bld?.setup;
      if (setup) { g.fillStyle = 'rgba(11,12,16,.75)'; g.beginPath(); g.arc(this.p.x, y - 13 * s, 10 * s, 0, Math.PI * 2); g.fill(); g.fillStyle = '#ffe14a'; g.beginPath(); g.moveTo(this.p.x, y - 13 * s); g.arc(this.p.x, y - 13 * s, 8 * s, -Math.PI / 2, -Math.PI / 2 + (1 - Math.max(0, e.st) / setup) * Math.PI * 2); g.closePath(); g.fill(); }
      if (e.card === 'miningrig') { g.fillStyle = '#b250f6'; g.beginPath(); g.moveTo(this.p.x, y - 9 * s); g.arc(this.p.x, y - 9 * s, 5 * s, -Math.PI / 2, -Math.PI / 2 + (1 - e.mineT / e.mine) * Math.PI * 2); g.closePath(); g.fill(); }
    }
    // floating text
    for (let i = this.texts.length - 1; i >= 0; i--) {
      const f = this.texts[i]; f.t += dt; if (f.t > 1.1) { this.texts.splice(i, 1); continue; }
      this.v.set(f.x, f.y + f.t * 1.2, f.z); this.stage.toScreen(this.v, this.p);
      const a = f.t < 0.8 ? 1 : 1 - (f.t - 0.8) / 0.3, sc = (f.t < 0.12 ? 0.6 + f.t / 0.12 * 0.6 : 1.2 - Math.min(0.2, (f.t - 0.12))) * f.size * s;
      g.globalAlpha = a; g.font = `${17 * sc}px "Lilita One", sans-serif`; g.lineWidth = 4 * sc; g.strokeStyle = '#0B0C10'; g.strokeText(f.str, this.p.x, this.p.y); g.fillStyle = f.col; g.fillText(f.str, this.p.x, this.p.y); g.globalAlpha = 1;
    }
  }
}
