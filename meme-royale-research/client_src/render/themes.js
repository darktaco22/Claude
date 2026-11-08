// The ten arenas' looks: lighting, the court surface (painted on a canvas, with a normal map from its height), the ground
// around it, the river's shader settings and floaters, the neon frame, ambient particles, music. ARENAS.md is the brief;
// the decoration kits (assets/arenas/<id>/) come on top of this.
import * as THREE from 'three';
import {TOWER_POS} from '../sim.js';

const H = (a, b, c = 0) => { let h = (a * 374761393 + b * 668265263 + c * 2147483647) | 0; h = (h ^ (h >>> 13)) * 1274126177 | 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const rgb = (hex, k = 1) => { const c = new THREE.Color(hex); return `rgb(${Math.round(Math.min(255, c.r * 255 * k))},${Math.round(Math.min(255, c.g * 255 * k))},${Math.round(Math.min(255, c.b * 255 * k))})`; };
const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; };

// light: hemi [sky, ground, intensity]; key [colour, intensity, x, y, z]; rim [colour, intensity]; exposure; sky (background);
// fog; bloom; court {kind, a (player half), b (enemy half), line, pad}; outer {kind, a, b}; canal {mode, deep, mid, hot,
// foam, speed, glow (light colour), floaters}; neon [player, enemy, glow 0..1]; particles; music; amb
export const THEMES = {
  basement: {sky: '#1b1410', fog: '#1b1410', hemi: ['#ffd9a8', '#2a1c14', 1.05], key: ['#ffcf8a', 2.4, -6, 24, 26], rim: ['#7fa0ff', 0.6], exposure: 1.05, bloom: 0.3,
    court: {kind: 'concrete', a: '#8a8a86', b: '#8f8681', line: '#3d7bd9', pad: '#a3a29c'},
    outer: {kind: 'concrete', a: '#4a4440', b: '#3a3430'}, canal: {mode: 'liquid', deep: '#0a3a10', mid: '#2ec44a', hot: '#c8ff6a', foam: '#e6ffb0', speed: 0.5, glow: '#5dff7a', floaters: 'cans'},
    neon: ['#7CFF6B', '#FF4D6D', 0.45], particles: 'dust', music: 'mus_battle_lofi', amb: 'amb_basement'},
  backyard: {sky: '#f6b27a', fog: '#f3c08f', hemi: ['#ffe2b8', '#4a6a2a', 1.15], key: ['#ffd29a', 2.8, -14, 18, 22], rim: ['#ffb070', 0.7], exposure: 0.98, bloom: 0.12,
    court: {kind: 'grass', a: '#5fae3e', b: '#6aa83c', line: '#ffffff', pad: '#c9b48a'},
    outer: {kind: 'grass', a: '#3f8a2e', b: '#356f25'}, canal: {mode: 'liquid', deep: '#0a4f8a', mid: '#2fa8e6', hot: '#bff0ff', foam: '#ffffff', speed: 0.25, glow: '#6cc8ff', floaters: 'ducks'},
    neon: ['#7CFF6B', '#FF4D6D', 0.0], particles: 'pollen', music: 'mus_battle_backyard', amb: 'amb_backyard'},
  parking: {sky: '#9fc8f0', fog: '#b9d6f2', hemi: ['#e4f0ff', '#4a4a50', 1.2], key: ['#fff4e0', 2.9, -10, 26, 16], rim: ['#a0c0ff', 0.5], exposure: 0.98, bloom: 0.1,
    court: {kind: 'asphalt', a: '#4a4c52', b: '#4e4b50', line: '#f5c518', pad: '#7a7c82'},
    outer: {kind: 'asphalt', a: '#3a3c42', b: '#33353a'}, canal: {mode: 'liquid', deep: '#1a2230', mid: '#3a5a7a', hot: '#c0a0ff', foam: '#c8d6e6', speed: 0.35, glow: '#8ab0ff', floaters: 'cans', sheen: 1},
    neon: ['#7CFF6B', '#FF4D6D', 0.0], particles: 'none', music: 'mus_battle_parking', amb: 'amb_parking'},
  plaza: {sky: '#0a0d18', fog: '#0a0d18', hemi: ['#9fb0ff', '#3a2a30', 1.35], key: ['#fff1dc', 3.3, -7, 26, 30], rim: ['#7f9bff', 1.1], exposure: 1.2, bloom: 0.42,
    court: {kind: 'pavers', a: '#4e6a50', b: '#566650', line: '#7CFF6B', pad: '#787c84'},
    outer: {kind: 'asphalt', a: '#22242c', b: '#1a1c22'}, canal: {mode: 'liquid', deep: '#021708', mid: '#1a8c29', hot: '#8cff73', foam: '#c0ffb0', speed: 0.45, glow: '#5dff7a', floaters: 'coins'},
    neon: ['#7CFF6B', '#FF4D6D', 1.0], particles: 'none', music: 'mus_battle', amb: 'amb_plaza'},
  beach: {sky: '#7fd0ff', fog: '#a8e0ff', hemi: ['#d8f0ff', '#8a7048', 0.95], key: ['#fff0d0', 2.5, -8, 30, 12], rim: ['#ffe6b0', 0.4], exposure: 0.86, bloom: 0.08,
    court: {kind: 'sand', a: '#d9b67a', b: '#d6b073', line: '#ff7a59', pad: '#f3e2b8'},
    outer: {kind: 'sand', a: '#c9a66a', b: '#bf9a5e'}, canal: {mode: 'liquid', deep: '#0a6e8a', mid: '#2ad0d8', hot: '#e0fff8', foam: '#ffffff', speed: 0.3, glow: '#7ff0ff', floaters: 'ducks', waves: 1},
    neon: ['#7CFF6B', '#FF4D6D', 0.0], particles: 'none', music: 'mus_battle_summer', amb: 'amb_beach'},
  exchange: {sky: '#101826', fog: '#101826', hemi: ['#dfe8ff', '#28303c', 1.1], key: ['#f2f6ff', 2.5, -6, 28, 22], rim: ['#6fd0ff', 0.8], exposure: 1.0, bloom: 0.28,
    court: {kind: 'marble', a: '#e8dfc6', b: '#e4dbc2', dark: '#3c7c58', line: '#c9a24a', pad: '#2a2e36'},
    outer: {kind: 'carpet', a: '#1c2a46', b: '#16223a'}, canal: {mode: 'ticker', deep: '#03100a', mid: '#13a84a', hot: '#9dff8a', foam: '#ff4d6d', speed: 1, glow: '#4dffa0', floaters: 'none'},
    neon: ['#4dffa0', '#ff4d6d', 0.7], particles: 'none', music: 'mus_battle_exchange', amb: 'amb_exchange'},
  casino: {sky: '#1a0a1c', fog: '#1a0a1c', hemi: ['#ffd8a0', '#3a1022', 1.3], key: ['#ffd89a', 3.2, -6, 26, 24], rim: ['#c77dff', 1.2], exposure: 1.15, bloom: 0.5,
    court: {kind: 'carpet', a: '#8c1a2a', b: '#7a1626', line: '#ffc84a', pad: '#3a0c18'},
    outer: {kind: 'carpet', a: '#3a0c1e', b: '#2a0816'}, canal: {mode: 'gold', deep: '#5a3000', mid: '#d99a1a', hot: '#fff1a0', foam: '#ffffff', speed: 0.3, glow: '#ffc84a', floaters: 'chips'},
    neon: ['#ffc84a', '#c77dff', 0.9], particles: 'sparkle', music: 'mus_battle_casino', amb: 'amb_casino'},
  cold: {sky: '#bfe0ff', fog: '#d6ecff', hemi: ['#e8f4ff', '#5a7898', 0.85], key: ['#f0f8ff', 2.2, -10, 24, 20], rim: ['#9fd0ff', 0.8], exposure: 0.82, bloom: 0.1,
    court: {kind: 'ice', a: '#cfe4f4', b: '#d8e8f6', line: '#4cc9f0', pad: '#ffffff'},
    outer: {kind: 'snow', a: '#d6e6f4', b: '#c4d8ea'}, canal: {mode: 'ice', deep: '#0a3a6a', mid: '#3c8ccc', hot: '#e8f8ff', foam: '#ffffff', speed: 0.12, glow: '#9fe0ff', floaters: 'ice'},
    neon: ['#4cc9f0', '#ff6f91', 0.5], particles: 'snow', music: 'mus_battle_cold', amb: 'amb_cold'},
  penthouse: {sky: '#3a1a4a', fog: '#5a2a5a', hemi: ['#ffc0e8', '#2a1a3a', 1.35], key: ['#ffb8a0', 3.0, -12, 20, 18], rim: ['#b07dff', 1.3], exposure: 1.15, bloom: 0.5,
    court: {kind: 'deck', a: '#d09858', b: '#c88e50', line: '#ffffff', pad: '#d8d0c8'},
    outer: {kind: 'gravel', a: '#3a3440', b: '#2e2a34'}, canal: {mode: 'liquid', deep: '#0a2a6a', mid: '#2a7aff', hot: '#b8f0ff', foam: '#ffffff', speed: 0.2, glow: '#5aa8ff', floaters: 'none', lit: 1},
    neon: ['#ff6fd8', '#ffb84a', 0.85], particles: 'none', music: 'mus_battle_penthouse', amb: 'amb_penthouse'},
  moon: {sky: '#03030a', fog: '#05050f', hemi: ['#c8d0ff', '#202028', 0.75], key: ['#ffffff', 3.0, -16, 22, 10], rim: ['#7a6fff', 1.0], exposure: 0.95, bloom: 0.45,
    court: {kind: 'regolith', a: '#7e7e86', b: '#7a7880', line: '#c77dff', pad: '#bcbcc4'},
    outer: {kind: 'regolith', a: '#6a6a72', b: '#5a5a62'}, canal: {mode: 'rift', deep: '#0a0220', mid: '#5a2aa8', hot: '#e8b8ff', foam: '#ffffff', speed: 0.3, glow: '#a35bff', floaters: 'none'},
    neon: ['#7CFF6B', '#FF4D6D', 0.8], particles: 'stars', music: 'mus_battle_space', amb: 'amb_moon'},
  factory: {sky: '#2a3a3e', fog: '#56686a', hemi: ['#f0fff6', '#56686a', 1.25], key: ['#fff8ec', 2.5, -6, 28, 20], rim: ['#7cffc0', 0.9], exposure: 0.92, bloom: 0.3,
    court: {kind: 'labtile', a: '#e8eeea', b: '#e2e9e5', line: '#58cfa0', pad: '#f6f9f6', rough: 0.42},
    outer: {kind: 'concrete', a: '#9aa6a2', b: '#8a9692'}, canal: {mode: 'liquid', deep: '#04502c', mid: '#18e070', hot: '#c8ffd8', foam: '#e8fff0', speed: 0.35, glow: '#38ff90', floaters: 'capsules'},
    neon: ['#7CFF6B', '#FF4D6D', 0.6], particles: 'sparkle', music: 'mus_battle_factory', amb: 'amb_basement'},
  dump: {sky: '#7a2e1a', fog: '#8a4020', hemi: ['#ffd0a0', '#3a1c10', 1.15], key: ['#ffb070', 3.0, -14, 18, 16], rim: ['#ff7a3a', 1.1], exposure: 1.0, bloom: 0.3,
    court: {kind: 'dirt', a: '#9a5f38', b: '#925934', line: '#d9a05a', pad: '#b27c4e'},
    outer: {kind: 'gravel', a: '#5a3622', b: '#4a2c1c'}, canal: {mode: 'liquid', deep: '#2c3406', mid: '#9ac214', hot: '#e6ff50', foam: '#f4ffb0', speed: 0.22, glow: '#c6e81e', floaters: 'cans'},
    neon: ['#7CFF6B', '#FF4D6D', 0.5], particles: 'dust', music: 'mus_battle_dump', amb: 'amb_parking'},
  cemetery: {sky: '#14122a', fog: '#1e1a3a', hemi: ['#c8c4ff', '#2a2a3a', 1.5], key: ['#d0dcff', 2.9, -10, 24, 16], rim: ['#2ee6c8', 1.2], exposure: 1.1, bloom: 0.42,
    court: {kind: 'flagstone', a: '#9a96aa', b: '#938fa4', line: '#2ee6c8', pad: '#a8a4b6'},
    outer: {kind: 'gravel', a: '#2e2c3a', b: '#26242f'}, canal: {mode: 'liquid', deep: '#04333a', mid: '#14b8a6', hot: '#a0fff0', foam: '#d8fff8', speed: 0.2, glow: '#27e0c8', floaters: 'none'},
    neon: ['#7CFF6B', '#FF4D6D', 0.8], particles: 'wisps', music: 'mus_battle_cemetery', amb: 'amb_cold'},
  trench: {sky: '#07203e', fog: '#0c3358', hemi: ['#a8dcff', '#14304e', 1.2], key: ['#d8f2ff', 2.6, -6, 28, 18], rim: ['#ff7ac8', 0.9], exposure: 1.0, bloom: 0.3,
    court: {kind: 'sand', a: '#dcb68c', b: '#d6b088', line: '#ffffff', pad: '#ecd0a8'},
    outer: {kind: 'gravel', a: '#2c4c70', b: '#24405e'}, canal: {mode: 'liquid', deep: '#06306a', mid: '#1a9ae0', hot: '#3cc4ff', foam: '#9fe8ff', speed: 0.3, glow: '#27beff', floaters: 'none', waves: 1},
    neon: ['#7CFF6B', '#FF4D6D', 0.6], particles: 'bubbles', music: 'mus_battle_trench', amb: 'amb_moon'},
  mine: {sky: '#120f18', fog: '#1a1620', hemi: ['#d8c8d8', '#1a1418', 1.05], key: ['#ffd8a8', 2.6, -8, 24, 18], rim: ['#3ee0ff', 1.2], exposure: 1.05, bloom: 0.48,
    court: {kind: 'slate', a: '#b4a4b6', b: '#ac9eb2', line: '#d89a4a', pad: '#c0b4c2', rough: 0.72},
    outer: {kind: 'gravel', a: '#2f2c36', b: '#262430'}, canal: {mode: 'lava', deep: '#5a1200', mid: '#ff4a00', hot: '#ffb020', foam: '#ff8a20', speed: 0.2, glow: '#ff8a1e', floaters: 'none'},
    neon: ['#7CFF6B', '#FF4D6D', 0.7], particles: 'embers', music: 'mus_battle_mine', amb: 'amb_basement'},
  clouds: {sky: '#a8d4ff', fog: '#d8d0f4', hemi: ['#fff4ff', '#a898d0', 1.0], key: ['#fff6e0', 2.3, -8, 26, 18], rim: ['#ffc0f0', 0.7], exposure: 0.85, bloom: 0.14,
    court: {kind: 'palace', a: '#f4eef2', b: '#f0e8ee', line: '#e0b040', pad: '#e8e0f0', rough: 0.38},
    outer: {kind: 'snow', a: '#e4d8f2', b: '#d8cce8'}, canal: {mode: 'rainbow', deep: '#b070e0', mid: '#ffb0f0', hot: '#ffffff', foam: '#ffffff', speed: 0.35, glow: '#ffb0f0', floaters: 'none'},
    neon: ['#7CFF6B', '#FF4D6D', 0.45], particles: 'sparkle', music: 'mus_battle_clouds', amb: 'amb_penthouse'},
  metaverse: {sky: '#140828', fog: '#1c0c36', hemi: ['#d0a8ff', '#1a0a2a', 1.15], key: ['#ffc0ec', 2.2, -8, 24, 18], rim: ['#27e8ff', 1.2], exposure: 1.05, bloom: 0.34,
    court: {kind: 'neongrid', a: '#7c4a8a', b: '#744484', line: '#ff3ad0', pad: '#865294', rough: 0.6},
    outer: {kind: 'gravel', a: '#1c1030', b: '#160c28'}, canal: {mode: 'pixels', deep: '#041a2a', mid: '#0fb8e0', hot: '#d8ffff', foam: '#27e8ff', speed: 0.6, glow: '#27e8ff', floaters: 'cubes'},
    neon: ['#7CFF6B', '#FF4D6D', 0.9], particles: 'glitch', music: 'mus_battle_metaverse', amb: 'amb_plaza'},
};
// the kit pieces strewn over the ground around each court (src/render/arena.js scatter; 'name!' keeps its full size)
const SCATTER = {
  basement: ['box_stack', 'pizza_stack', 'can_pyramid', 'crt_tv', 'laundry_pile', 'desk_fan', 'washer', 'gaming_chair', 'box_stack'],
  backyard: ['bush', 'bush', 'bush', 'yard_tree!', 'gnome', 'flamingo', 'lawn_chair', 'tiki_torch', 'hose_reel', 'cooler'],
  parking: ['cones', 'cones', 'hydrant', 'cart', 'car_red!', 'car_teal!', 'lamp_post', 'parking_sign', 'cones'],
  plaza: ['barrel_stack', 'crate_stack', 'street_lamp', 'vending', 'atm', 'manhole', 'crate_stack'],
  beach: ['palm!', 'palm!', 'umbrella', 'beach_ball', 'surfboards', 'sandcastle', 'cooler', 'dumbbells'],
  exchange: ['ex_papers', 'ex_papers', 'ex_plant', 'ex_desk', 'ex_bell', 'ex_board', 'ex_plant'],
  casino: ['ca_chips', 'ca_chips', 'ca_coins', 'ca_dice', 'ca_slot', 'ca_roulette', 'ca_coins'],
  cold: ['co_pine!', 'co_pine!', 'co_pine!', 'co_rocks', 'co_snowman', 'co_crystal', 'co_bags', 'co_igloo!'],
  penthouse: ['pe_palm!', 'pe_lounger', 'pe_champagne', 'pe_hottub', 'pe_car_lime!', 'pe_car_pink!', 'pe_lounger'],
  moon: ['mo_rock', 'mo_rock', 'mo_crater!', 'mo_flag', 'mo_dish', 'mo_rover', 'mo_lander'],
  factory: ['fa_pills', 'fa_pills', 'fa_pipes', 'fa_beacon', 'fa_beacon', 'fa_terminal', 'fa_tank!', 'fa_deadbin'],
  dump: ['du_tires', 'du_tires!', 'du_bags', 'du_crates', 'du_cones!', 'du_blocks!', 'du_drum!', 'du_crt'],
  cemetery: ['ce_rock', 'ce_rock', 'ce_grave', 'ce_graves', 'ce_pumpkin', 'ce_candles', 'ce_tree!', 'ce_lantern', 'ce_fence'],
  trench: ['tr_rocks', 'tr_rocks', 'tr_coral', 'tr_tube', 'tr_kelp', 'tr_star', 'tr_clam', 'tr_chest'],
  mine: ['mi_boulder', 'mi_boulder', 'mi_pillar!', 'mi_crates', 'mi_pick', 'mi_crystals', 'mi_boulder', 'mi_lamp'],
  clouds: ['cl_cloud!', 'cl_cloud!', 'cl_cloud', 'cl_puff', 'cl_puff', 'cl_urn', 'cl_rainbow!', 'cl_harp'],
  metaverse: ['me_rubble', 'me_rubble', 'me_column', 'me_ruin', 'me_plot!', 'me_cube_c', 'me_cube_m', 'me_palm'],
};
for (const [id, s] of Object.entries(SCATTER)) if (THEMES[id]) THEMES[id].scatter = s;
// grounds with a grid or a pattern (planks, tiles, slabs, carpet) skip the anti-tiling blend: two offset copies would ghost
for (const id of ['basement', 'plaza', 'exchange', 'casino', 'penthouse', 'factory', 'cemetery', 'mine', 'metaverse']) THEMES[id].outer.anti = 0;
// under the bright keys, white dice, papers and gold coins blow out in bloom: dim them a little more
Object.assign(THEMES.casino, {scatterDim: 0.55}); Object.assign(THEMES.exchange, {scatterDim: 0.5}); Object.assign(THEMES.penthouse, {scatterDim: 0.7}); Object.assign(THEMES.moon, {scatterDim: 0.75});
export const themeOf = id => THEMES[id] || THEMES.plaza;

// ---------- the court: one canvas per arena, px per tile; returns colour + normal maps
export function paintCourt(T, px) {
  const W = 18 * px, Hh = 32 * px, [c, g] = canvas(W, Hh), [hc, hg] = canvas(W, Hh), C = T.court;
  hg.fillStyle = '#c0c0c0'; hg.fillRect(0, 0, W, Hh);
  const half = j => j >= 17 ? 0 : 1, base = j => half(j) === 0 ? C.a : C.b;
  const speck = (x, y, w, h, n, a, seed) => { for (let k = 0; k < n; k++) { const s = H(seed, k); g.fillStyle = `rgba(${s > 0.5 ? '255,255,255' : '0,0,0'},${a * (0.5 + s)})`; g.fillRect(x + H(k, seed, 3) * w, y + H(seed, k, 7) * h, 1 + s * 2.5, 1 + s * 2.5); } };
  for (const [z0, z1] of [[0, 15], [17, 32]]) {
    const y0 = z0 * px, hgt = (z1 - z0) * px, col = base(z0 + 1);
    g.fillStyle = col; g.fillRect(0, y0, W, hgt);
    const k = C.kind;
    if (k === 'pavers' || k === 'ice') {
      const grout = Math.max(2, px * 0.05), bev = Math.max(2, px * 0.09);
      for (let j = z0; j < z1; j++) for (let i = 0; i < 18; i++) {
        const v = H(i, j) * 2 - 1, lane = (Math.abs(i + 0.5 - 3.5) < 1.6 || Math.abs(i + 0.5 - 14.5) < 1.6) ? 1 : 0, x = i * px, y = j * px;
        g.fillStyle = rgb(col, 1 + v * (k === 'ice' ? 0.03 : 0.07) + lane * (k === 'ice' ? 0.02 : 0.09) + ((i + j) % 2 ? 0.035 : -0.02)); g.fillRect(x, y, px, px);
        if (k === 'ice') { g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = 1.2; g.beginPath(); let cx = x + H(i, j, 1) * px, cy = y + H(j, i, 2) * px; g.moveTo(cx, cy); for (let q = 0; q < 3; q++) { cx += (H(i, j, q + 5) - 0.5) * px * 0.7; cy += (H(j, i, q + 9) - 0.5) * px * 0.7; g.lineTo(cx, cy); } g.stroke(); }
        g.fillStyle = 'rgba(255,255,255,0.08)'; g.fillRect(x, y, px, bev); g.fillRect(x, y, bev, px);
        g.fillStyle = 'rgba(0,0,0,0.15)'; g.fillRect(x, y + px - bev, px, bev); g.fillRect(x + px - bev, y, bev, px);
        hg.fillStyle = '#fff'; hg.fillRect(x + grout, y + grout, px - grout * 2, px - grout * 2);
        speck(x, y, px, px, px * 0.4, 0.04, i * 31 + j);
      }
      g.fillStyle = k === 'ice' ? 'rgba(160,200,230,0.6)' : 'rgba(10,12,16,0.85)';
      for (let i = 0; i <= 18; i++) g.fillRect(i * px - 1, y0, 2, hgt);
      for (let j = z0; j <= z1; j++) g.fillRect(0, j * px - 1, W, 2);
    } else if (k === 'grass') {
      // mowed stripes two tiles wide, worn dirt lanes, stepping stones
      for (let j = z0; j < z1; j++) { g.fillStyle = rgb(col, j % 4 < 2 ? 1.08 : 0.92); g.fillRect(0, j * px, W, px); }
      for (let n = 0; n < 9000 * (hgt / (16 * px)); n++) { const x = H(n, z0) * W, y = y0 + H(z0, n, 2) * hgt, s = H(n, 9); g.strokeStyle = s > 0.5 ? 'rgba(200,255,140,0.18)' : 'rgba(20,60,10,0.2)'; g.lineWidth = 1; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (s - 0.5) * 3, y - 3 - s * 4); g.stroke(); }
      for (const lx of [3.5, 14.5]) { const gr = g.createLinearGradient((lx - 1.6) * px, 0, (lx + 1.6) * px, 0); gr.addColorStop(0, 'rgba(120,90,50,0)'); gr.addColorStop(0.5, 'rgba(140,105,60,0.35)'); gr.addColorStop(1, 'rgba(120,90,50,0)'); g.fillStyle = gr; g.fillRect((lx - 1.6) * px, y0, 3.2 * px, hgt); }
      for (let n = 0; n < 14; n++) { const i = [3.5, 14.5][n % 2], j = z0 + 1 + (n >> 1) * 2; if (j >= z1) continue; g.fillStyle = '#b8b0a2'; g.beginPath(); g.ellipse(i * px + (H(n, 3) - 0.5) * px * 0.4, j * px + px / 2, px * 0.42, px * 0.3, H(n, 4), 0, Math.PI * 2); g.fill(); g.fillStyle = 'rgba(0,0,0,0.18)'; g.beginPath(); g.ellipse(i * px + px * 0.05, j * px + px * 0.6, px * 0.42, px * 0.3, 0, 0, Math.PI * 2); g.fill(); }
      for (let n = 0; n < 60; n++) { const x = H(n, 77) * W, y = y0 + H(77, n) * hgt; g.fillStyle = ['#fff6a0', '#ffffff', '#ff9ad0'][n % 3]; g.beginPath(); g.arc(x, y, px * 0.06, 0, 7); g.fill(); }
    } else if (k === 'asphalt' || k === 'regolith' || k === 'sand' || k === 'concrete') {
      speck(0, y0, W, hgt, W * hgt / (k === 'sand' ? 60 : 90), k === 'sand' ? 0.05 : 0.07, z0 + 11);
      if (k === 'sand') for (let n = 0; n < 50; n++) { g.strokeStyle = 'rgba(160,120,60,0.18)'; g.lineWidth = 2; g.beginPath(); const y = y0 + H(n, 5) * hgt; g.moveTo(0, y); for (let x = 0; x <= W; x += px) g.lineTo(x, y + Math.sin(x / px * 0.9 + n) * px * 0.15); g.stroke(); }
      if (k === 'concrete') for (let n = 0; n < 8; n++) { g.fillStyle = `rgba(40,30,20,${0.08 + H(n, 2) * 0.1})`; g.beginPath(); g.ellipse(H(n, 1) * W, y0 + H(1, n) * hgt, px * (0.5 + H(n, 3) * 1.4), px * (0.4 + H(n, 4)), 0, 0, 7); g.fill(); }
      if (k === 'regolith') for (let n = 0; n < 18; n++) { const x = H(n, 21) * W, y = y0 + H(21, n) * hgt, r = px * (0.4 + H(n, 22) * 1.3); const gr = g.createRadialGradient(x, y, r * 0.2, x, y, r); gr.addColorStop(0, 'rgba(0,0,0,0.22)'); gr.addColorStop(0.75, 'rgba(0,0,0,0.05)'); gr.addColorStop(0.85, 'rgba(255,255,255,0.18)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
        const hgr = hg.createRadialGradient(x, y, r * 0.1, x, y, r); hgr.addColorStop(0, '#888'); hgr.addColorStop(0.8, '#c0c0c0'); hgr.addColorStop(0.88, '#e8e8e8'); hgr.addColorStop(1, '#c0c0c0'); hg.fillStyle = hgr; hg.beginPath(); hg.arc(x, y, r, 0, 7); hg.fill(); }
      if (k === 'asphalt') {
        // parking stalls along both sides of each half, arrows down the middle
        g.strokeStyle = C.line; g.lineWidth = px * 0.08; g.globalAlpha = 0.8;
        for (let j = z0 + 1; j < z1; j += 2) { g.beginPath(); g.moveTo(0, j * px); g.lineTo(2.2 * px, j * px); g.moveTo(W, j * px); g.lineTo(W - 2.2 * px, j * px); g.stroke(); }
        g.fillStyle = C.line; for (let j = z0 + 2; j < z1 - 1; j += 4) { const x = 9 * px, y = j * px, dir = z0 >= 17 ? -1 : 1; g.beginPath(); g.moveTo(x, y + dir * px * 0.6); g.lineTo(x - px * 0.35, y); g.lineTo(x - px * 0.12, y); g.lineTo(x - px * 0.12, y - dir * px * 0.6); g.lineTo(x + px * 0.12, y - dir * px * 0.6); g.lineTo(x + px * 0.12, y); g.lineTo(x + px * 0.35, y); g.closePath(); g.fill(); }
        g.globalAlpha = 1;
        for (let n = 0; n < 5; n++) { g.fillStyle = 'rgba(0,0,0,0.25)'; g.beginPath(); g.ellipse(H(n, 41) * W, y0 + H(41, n) * hgt, px * 0.6, px * 0.4, H(n, 3), 0, 7); g.fill(); }
      }
      if (k === 'concrete') {   // blue tape lane lines
        g.fillStyle = C.line; g.globalAlpha = 0.75; for (const lx of [2, 5, 13, 16]) g.fillRect(lx * px - px * 0.06, y0 + px * 0.3, px * 0.12, hgt - px * 0.6); g.globalAlpha = 1;
      }
    } else if (k === 'labtile') {
      // white lab tile, one per game tile, with mint guide lines round the half and a box in front of the Battlestation
      const bev = Math.max(2, px * 0.05), gr = Math.max(1, px * 0.03);
      for (let j = z0; j < z1; j++) for (let i = 0; i < 18; i++) {
        const x = i * px, y = j * px; g.fillStyle = rgb(col, 1 + (H(i, j) - 0.5) * 0.05 + ((i + j) % 2 ? 0.012 : -0.012)); g.fillRect(x, y, px, px);
        g.fillStyle = 'rgba(255,255,255,0.22)'; g.fillRect(x, y, px, bev); g.fillRect(x, y, bev, px);
        g.fillStyle = 'rgba(50,70,65,0.14)'; g.fillRect(x, y + px - bev, px, bev); g.fillRect(x + px - bev, y, bev, px);
        hg.fillStyle = '#fff'; hg.fillRect(x + gr, y + gr, px - gr * 2, px - gr * 2);
      }
      g.fillStyle = 'rgba(70,90,85,0.6)'; for (let i = 0; i <= 18; i++) g.fillRect(i * px - 1, y0, 2, hgt); for (let j = z0; j <= z1; j++) g.fillRect(0, j * px - 1, W, 2);
      g.strokeStyle = C.line; g.lineWidth = px * 0.16; g.strokeRect(0.7 * px, y0 + 0.5 * px, W - 1.4 * px, hgt - px);
      g.strokeRect(4.5 * px, z0 >= 17 ? (z1 - 7.5) * px : y0 + 0.5 * px, 9 * px, 7 * px);
    } else if (k === 'dirt') {
      // packed dirt: blotches, gravel and tyre tracks
      speck(0, y0, W, hgt, W * hgt / 70, 0.07, z0 + 5);
      for (let n = 0; n < 34; n++) { const r = px * (0.6 + H(n, 62) * 2.2); g.fillStyle = H(n, 63) > 0.5 ? `rgba(40,20,8,${0.06 + H(n, 64) * 0.1})` : `rgba(255,190,120,${0.04 + H(n, 64) * 0.07})`; g.beginPath(); g.ellipse(H(n, 61 + z0) * W, y0 + H(61 + z0, n) * hgt, r, r * (0.5 + H(n, 65) * 0.4), H(n, 66) * 3, 0, 7); g.fill(); }
      g.strokeStyle = 'rgba(45,22,10,0.24)'; g.lineWidth = px * 0.24; g.setLineDash([px * 0.09, px * 0.07]);
      for (let n = 0; n < 4; n++) for (const off of [0, px * 0.8]) { const sx = H(n, 71 + z0) * W + off, sy = y0 + H(71 + z0, n) * hgt; g.beginPath(); g.moveTo(sx, sy); g.bezierCurveTo(sx + px * 3, sy + px * 3, sx - px * 2, sy + px * 6, sx + px * 4, sy + px * 9); g.stroke(); }
      g.setLineDash([]);
    } else if (k === 'flagstone' || k === 'slate') {
      // stone laid in rows: small worn flags with moss in the joints, or big slabs of slate with cracks
      const fl = k === 'flagstone', rh = (fl ? 1.25 : 2) * px, rw = (fl ? 1.75 : 3) * px, jt = Math.max(2, px * (fl ? 0.05 : 0.04));
      for (let r = 0; r * rh < hgt; r++) {
        const y = y0 + r * rh, hh = Math.min(rh, y0 + hgt - y); let x = -H(r, z0, 5) * rw;
        for (let q = 0; x < W; q++) {
          const w = rw * (0.72 + H(q, r, z0) * 0.56);
          g.fillStyle = rgb(col, 1 + (H(q, r, z0 + 3) - 0.5) * (fl ? 0.28 : 0.2)); g.fillRect(x, y, w, hh);
          g.fillStyle = 'rgba(255,255,255,0.07)'; g.fillRect(x, y, w, px * 0.06);
          g.fillStyle = 'rgba(0,0,0,0.16)'; g.fillRect(x, y + hh - px * 0.07, w, px * 0.07); g.fillRect(x + w - px * 0.05, y, px * 0.05, hh);
          hg.fillStyle = '#fff'; hg.fillRect(x + jt, y + jt, w - jt * 2, hh - jt * 2);
          g.fillStyle = 'rgba(14,12,20,0.78)'; g.fillRect(x, y, jt, hh); g.fillRect(x, y, w, jt);
          x += w;
        }
      }
      speck(0, y0, W, hgt, W * hgt / 90, 0.06, z0 + 17);
      if (fl) for (let n = 0; n < 60; n++) { g.fillStyle = `rgba(96,140,72,${0.1 + H(n, 81) * 0.22})`; g.beginPath(); g.ellipse(H(n, 82 + z0) * W, y0 + H(82 + z0, n) * hgt, px * (0.1 + H(n, 83) * 0.35), px * (0.06 + H(n, 84) * 0.14), H(n, 85) * 3, 0, 7); g.fill(); }
      else for (let n = 0; n < 14; n++) { g.strokeStyle = 'rgba(8,8,12,0.5)'; g.lineWidth = 1.4; g.beginPath(); let cx = H(n, 91 + z0) * W, cy = y0 + H(91 + z0, n) * hgt; g.moveTo(cx, cy); for (let q = 0; q < 4; q++) { cx += (H(n, q, 92) - 0.5) * px * 1.1; cy += (H(q, n, 93) - 0.5) * px * 1.1; g.lineTo(cx, cy); } g.stroke(); }
    } else if (k === 'palace') {
      // big polished marble slabs with lilac veins and a gold inlay round the half
      for (let j = z0; j < z1; j += 2) for (let i = 0; i < 18; i += 2) {
        const x = i * px, y = j * px, w = 2 * px, hh = Math.min(2, z1 - j) * px; g.fillStyle = rgb(col, 1 + (H(i, j) - 0.5) * 0.06); g.fillRect(x, y, w, hh);
        for (let v = 0; v < 3; v++) { g.strokeStyle = `rgba(110,85,160,${0.12 + H(i, j, v) * 0.16})`; g.lineWidth = 1 + H(j, i, v) * 1.4; g.beginPath(); let vx = x + H(i, j, v + 3) * w, vy = y; g.moveTo(vx, vy); for (let q = 0; q < 6; q++) { vx += (H(i, j, q + v * 7) - 0.5) * px * 0.8; vy += hh / 6; g.lineTo(vx, vy); } g.stroke(); }
        g.fillStyle = 'rgba(255,255,255,0.14)'; g.fillRect(x, y, w, 2); g.fillStyle = 'rgba(70,50,110,0.38)'; g.fillRect(x, y + hh - 2, w, 2); g.fillRect(x + w - 2, y, 2, hh);
        hg.fillStyle = '#f4f4f4'; hg.fillRect(x + 2, y + 2, w - 4, hh - 4);
      }
      g.strokeStyle = C.line; g.lineWidth = px * 0.1; g.strokeRect(1.1 * px, y0 + 0.7 * px, W - 2.2 * px, hgt - 1.4 * px);
    } else if (k === 'neongrid') {
      // muted plum panels, one per game tile, with soft thin magenta lines and a hot one round the half
      for (let j = z0; j < z1; j++) for (let i = 0; i < 18; i++) { g.fillStyle = rgb(col, 1 + (H(i, j) - 0.5) * 0.09); g.fillRect(i * px, j * px, px, px); }
      for (const [st, w] of [['rgba(255,58,208,0.06)', px * 0.14], ['rgba(255,58,208,0.4)', Math.max(1.5, px * 0.028)]]) {
        g.strokeStyle = st; g.lineWidth = w; g.beginPath();
        for (let i = 0; i <= 18; i++) { g.moveTo(i * px, y0); g.lineTo(i * px, y0 + hgt); }
        for (let j = z0; j <= z1; j++) { g.moveTo(0, j * px); g.lineTo(W, j * px); }
        g.stroke();
      }
      g.strokeStyle = C.line; g.lineWidth = px * 0.1; g.strokeRect(0.12 * px, y0 + 0.12 * px, W - 0.24 * px, hgt - 0.24 * px);
    } else if (k === 'marble') {
      for (let j = z0; j < z1; j++) for (let i = 0; i < 18; i++) {
        const dark = (i + j) % 2 === 0, x = i * px, y = j * px;
        g.fillStyle = dark ? (C.dark || '#2b2f37') : col; g.fillRect(x, y, px, px);
        g.strokeStyle = dark ? 'rgba(255,255,255,0.12)' : 'rgba(80,80,90,0.25)'; g.lineWidth = 1.4; g.beginPath(); let vx = x, vy = y + H(i, j) * px; g.moveTo(vx, vy); for (let q = 0; q < 5; q++) { vx += px / 5; vy += (H(i, j, q) - 0.5) * px * 0.5; g.lineTo(vx, vy); } g.stroke();
        g.fillStyle = 'rgba(255,255,255,0.1)'; g.fillRect(x, y, px, 2);
        hg.fillStyle = '#f0f0f0'; hg.fillRect(x + 1, y + 1, px - 2, px - 2);
      }
      g.strokeStyle = C.line; g.lineWidth = px * 0.07; g.strokeRect(1.2 * px, y0 + 0.6 * px, W - 2.4 * px, hgt - 1.2 * px);
    } else if (k === 'carpet') {
      for (let n = 0; n < W * hgt / 40; n++) { g.fillStyle = `rgba(${H(n, z0) > 0.5 ? '255,200,200' : '0,0,0'},0.05)`; g.fillRect(H(z0, n) * W, y0 + H(n, 3) * hgt, 2, 2); }
      g.strokeStyle = C.line; g.globalAlpha = 0.55; g.lineWidth = px * 0.05;
      for (let j = z0; j < z1; j++) for (let i = 0; i < 18; i++) if ((i + j) % 2 === 0) { const x = (i + 0.5) * px, y = (j + 0.5) * px, r = px * 0.42; g.beginPath(); g.moveTo(x, y - r); g.lineTo(x + r, y); g.lineTo(x, y + r); g.lineTo(x - r, y); g.closePath(); g.stroke(); g.fillStyle = C.line; g.beginPath(); g.arc(x, y, px * 0.07, 0, 7); g.fill(); }
      g.globalAlpha = 1; g.lineWidth = px * 0.12; g.strokeRect(0.6 * px, y0 + 0.4 * px, W - 1.2 * px, hgt - 0.8 * px);
    } else if (k === 'deck') {
      for (let i = 0; i < 18 * 3; i++) { const x = i * px / 3; g.fillStyle = rgb(col, 0.9 + H(i, z0) * 0.2); g.fillRect(x, y0, px / 3, hgt); g.fillStyle = 'rgba(40,20,10,0.55)'; g.fillRect(x, y0, 1.5, hgt); hg.fillStyle = '#909090'; hg.fillRect(x, y0, 2, hgt);
        for (let j = z0; j < z1; j += 3) { const yy = (j + H(i, j) * 3) * px; g.fillRect(x, yy, px / 3, 1.5); } }
      for (let n = 0; n < 400; n++) { g.strokeStyle = 'rgba(60,30,10,0.12)'; g.beginPath(); const x = H(n, 6) * W, y = y0 + H(6, n) * hgt; g.moveTo(x, y); g.lineTo(x + 1, y + px * 0.8); g.stroke(); }
    }
    // the worn paths down the lanes (every surface but the rug-like ones)
    if (!['grass', 'carpet', 'marble', 'labtile', 'palace', 'neongrid'].includes(k)) for (const lx of [3.5, 14.5]) { const gr = g.createLinearGradient((lx - 1.5) * px, 0, (lx + 1.5) * px, 0); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, `rgba(255,255,255,${k === 'regolith' ? 0.06 : 0.05})`); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect((lx - 1.5) * px, y0, 3 * px, hgt); }
  }
  // a faint tile grid on surfaces without their own (helps placing)
  if (!['pavers', 'ice', 'marble', 'labtile', 'palace', 'neongrid'].includes(C.kind)) { g.strokeStyle = 'rgba(0,0,0,0.07)'; g.lineWidth = 1; for (let i = 1; i < 18; i++) { g.beginPath(); g.moveTo(i * px, 0); g.lineTo(i * px, Hh); g.stroke(); } for (let j = 1; j < 32; j++) { g.beginPath(); g.moveTo(0, j * px); g.lineTo(W, j * px); g.stroke(); } }
  // tower pads
  for (let s = 0; s < 2; s++) for (const t of TOWER_POS[s]) {
    const R = (t.type === 'hq' ? 2.75 : 2.15) * px, cx = t.x * px, cy = t.z * px;
    const gr = g.createRadialGradient(cx, cy, R * 0.2, cx, cy, R); gr.addColorStop(0, rgb(C.pad, 1.05)); gr.addColorStop(0.9, rgb(C.pad, 0.9)); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.beginPath(); g.arc(cx, cy, R, 0, 7); g.fill();
    g.strokeStyle = s === 0 ? 'rgba(124,255,107,0.6)' : 'rgba(255,77,109,0.6)'; g.lineWidth = px * 0.12; g.setLineDash([px * 0.5, px * 0.25]); g.beginPath(); g.arc(cx, cy, R * 0.86, 0, 7); g.stroke(); g.setLineDash([]);
    hg.fillStyle = '#e0e0e0'; hg.beginPath(); hg.arc(cx, cy, R * 0.95, 0, 7); hg.fill();
  }
  // the deploy line along each bank
  for (const [z, col] of [[17, 'rgba(124,255,107,0.45)'], [15, 'rgba(255,77,109,0.45)']]) { g.fillStyle = col; for (let x = 0; x < W; x += px * 0.5) g.fillRect(x, z * px - (z === 17 ? -px * 0.12 : px * 0.2), px * 0.28, px * 0.08); }
  return {map: tex(c, true), nrm: normals(hc, hg, W, Hh, C.kind === 'grass' ? 1.2 : 2.2)};
}

// (one pass over the height's red channel with the edges clamped by index, no per-pixel closures: ~5x faster on a phone)
function normals(hc, hg, W, Hh, k) {
  const src = hg.getImageData(0, 0, W, Hh).data, [nc, ng] = canvas(W, Hh), out = ng.createImageData(W, Hh), o = out.data, K = k / 255;
  for (let y = 0; y < Hh; y++) {
    const up = (y > 0 ? y - 1 : 0) * W, dn = (y < Hh - 1 ? y + 1 : y) * W, row = y * W;
    for (let x = 0; x < W; x++) {
      const l0 = x > 0 ? x - 1 : 0, r0 = x < W - 1 ? x + 1 : x;
      const dx = (src[(row + r0) << 2] - src[(row + l0) << 2]) * K, dy = (src[(dn + x) << 2] - src[(up + x) << 2]) * K;
      const il = 127.5 / Math.sqrt(dx * dx + dy * dy + 1), p = (row + x) << 2;
      o[p] = 127.5 - dx * il; o[p + 1] = 127.5 + dy * il; o[p + 2] = 127.5 + il; o[p + 3] = 255;
    }
  }
  ng.putImageData(out, 0, 0); const t = new THREE.CanvasTexture(nc); t.anisotropy = 8; return t;
}
function tex(c, srgb, rep) { const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; if (rep) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); } return t; }

// ---------- the ground around the court (a tiling texture)
export function paintOuter(T) {
  const S = 512, [c, g] = canvas(S, S), O = T.outer;
  g.fillStyle = O.a; g.fillRect(0, 0, S, S);
  const n = (k, a, sz) => { for (let i = 0; i < k; i++) { const s = Math.random(); g.fillStyle = `rgba(${s > 0.5 ? '255,255,255' : '0,0,0'},${a * Math.random()})`; g.fillRect(Math.random() * S, Math.random() * S, 1 + s * sz, 1 + s * sz); } };
  if (O.kind === 'grass') { for (let i = 0; i < 14000; i++) { const x = Math.random() * S, y = Math.random() * S, s = Math.random(); g.strokeStyle = s > 0.5 ? 'rgba(170,240,110,0.25)' : 'rgba(10,40,5,0.3)'; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (s - 0.5) * 3, y - 3 - s * 5); g.stroke(); } }
  else if (O.kind === 'snow') { n(6000, 0.06, 2); for (let i = 0; i < 300; i++) { g.fillStyle = 'rgba(255,255,255,0.8)'; g.fillRect(Math.random() * S, Math.random() * S, 1.5, 1.5); } }
  else if (O.kind === 'carpet') { n(9000, 0.06, 2); g.strokeStyle = 'rgba(255,200,80,0.18)'; g.lineWidth = 3; for (let x = 0; x < S; x += 64) for (let y = 0; y < S; y += 64) { g.beginPath(); g.moveTo(x + 32, y + 8); g.lineTo(x + 56, y + 32); g.lineTo(x + 32, y + 56); g.lineTo(x + 8, y + 32); g.closePath(); g.stroke(); } }
  else if (O.kind === 'gravel') { for (let i = 0; i < 9000; i++) { const s = Math.random(); g.fillStyle = `rgba(${s > 0.5 ? '200,190,210' : '10,8,14'},${0.15 + Math.random() * 0.2})`; g.beginPath(); g.arc(Math.random() * S, Math.random() * S, 0.8 + s * 2.2, 0, 7); g.fill(); } }
  else if (O.kind === 'sand') { n(12000, 0.07, 2); for (let i = 0; i < 30; i++) { g.strokeStyle = 'rgba(150,110,50,0.15)'; g.lineWidth = 2; g.beginPath(); const y = Math.random() * S; g.moveTo(0, y); for (let x = 0; x <= S; x += 16) g.lineTo(x, y + Math.sin(x / 30 + i) * 5); g.stroke(); } }
  else if (O.kind === 'regolith') { n(10000, 0.08, 2.5); for (let i = 0; i < 12; i++) { const x = Math.random() * S, y = Math.random() * S, r = 10 + Math.random() * 40; const gr = g.createRadialGradient(x, y, r * 0.2, x, y, r); gr.addColorStop(0, 'rgba(0,0,0,0.25)'); gr.addColorStop(0.85, 'rgba(255,255,255,0.12)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); } }
  else { n(9000, 0.08, 2.5); for (let i = 0; i < 14; i++) { g.strokeStyle = `rgba(0,0,0,${0.15 + Math.random() * 0.2})`; g.lineWidth = 1 + Math.random() * 2; g.beginPath(); let x = Math.random() * S, y = Math.random() * S; g.moveTo(x, y); for (let k = 0; k < 6; k++) { x += (Math.random() - 0.5) * 70; y += (Math.random() - 0.5) * 70; g.lineTo(x, y); } g.stroke(); } }
  return tex(c, true, 12);
}

// ---------- the river: one shader, five looks (liquid, gold, ice, rift, ticker)
export function canalMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {uT: {value: 0}, uDeep: {value: new THREE.Color()}, uMid: {value: new THREE.Color()}, uHot: {value: new THREE.Color()}, uFoam: {value: new THREE.Color()}, uSpeed: {value: 0.4}, uMode: {value: 0}, uSheen: {value: 0}, uWaves: {value: 0}},
    vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform float uT, uSpeed, uMode, uSheen, uWaves; uniform vec3 uDeep, uMid, uHot, uFoam; varying vec3 vW;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
      float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
      float fbm(vec2 p){ float a=.5, s=0.; for(int k=0;k<4;k++){ s+=a*n(p); p*=2.03; a*=.5; } return s; }
      void main(){
        float t = uT * uSpeed, edge = smoothstep(0., .55, min(vW.z - 15., 17. - vW.z));
        vec3 col;
        if (uMode < .5) {            // liquid
          vec2 p = vec2(vW.x * .55 - t, vW.z * 1.6);
          float f = fbm(p + vec2(fbm(p * .7 + t * .2), 0.) * 1.4);
          float streak = smoothstep(.62, .82, fbm(vec2(vW.x * .3 - t * 2., vW.z * 3.2)));
          col = mix(uDeep, uMid, f * .9 * edge + .1) + uHot * streak * .55 * edge;
          if (uWaves > .5) col += uFoam * smoothstep(.75, .95, sin(vW.x * 1.3 - uT * 2. + fbm(vW.xz * .8) * 4.) * .5 + .5) * .35 * edge;
          if (uSheen > .5) { float s = fbm(vW.xz * .9 + t * .3); col += (vec3(sin(s*12.), sin(s*12.+2.), sin(s*12.+4.)) * .5 + .5) * .25 * smoothstep(.45, .7, s); }
        } else if (uMode < 1.5) {    // gold: molten, bright, sparkling
          vec2 p = vec2(vW.x * .4 - t, vW.z * 1.4); float f = fbm(p + fbm(p * 1.3 + t) * 1.2);
          col = mix(uDeep, uMid, f * 1.2) + uHot * pow(f, 3.) * 1.4;
          col += vec3(1.) * step(.985, h(floor(vW.xz * 9.) + floor(uT * 6.))) * edge;
        } else if (uMode < 2.5) {    // ice: still, cracked, a slow shimmer
          float f = fbm(vW.xz * 1.2 + t * .1), c = smoothstep(.02, .0, abs(fbm(vW.xz * 2.) - .5));
          col = mix(uMid, uHot, f * .6) + uFoam * c * .5;
        } else if (uMode < 3.5) {    // rift: deep space with drifting stars
          vec2 p = vec2(vW.x * .3 - t * .5, vW.z * 1.2); float f = fbm(p + fbm(p * 2. + t * .3));
          col = mix(uDeep, uMid, f * f * 1.6) + uHot * pow(fbm(p * 3.), 4.) * 2.;
          vec2 g = floor(vW.xz * 6. + vec2(uT * .4, 0.)); col += vec3(1.) * step(.992, h(g)) * (.6 + .4 * sin(uT * 4. + h(g) * 40.));
        } else if (uMode < 4.5) {    // ticker: scrolling green and red candles
          float x = vW.x * 2. - uT * 3.; float id = floor(x), fx = fract(x), up = step(.45, h(vec2(id, 3.)));
          float body = step(.3, fx) * step(fx, .7) * step(abs(vW.z - 16.) , .2 + h(vec2(id, 5.)) * .6);
          float wick = step(.47, fx) * step(fx, .53) * step(abs(vW.z - 16.), .5 + h(vec2(id, 7.)) * .4);
          col = uDeep + mix(uFoam, uMid, up) * max(body, wick * .7) * 1.4 + uMid * .06;
        } else if (uMode < 5.5) {    // rainbow: bands along the river, rippling and sparkling
          float hue = (vW.z - 15.) * .5 + fbm(vec2(vW.x * .5 - t, vW.z * 1.4)) * .22 + sin(vW.x * .6 - uT * .8) * .05;
          col = .5 + .5 * cos(6.283 * (hue + vec3(0., .33, .67)));
          vec2 sq = vec2(vW.x - t * 2., vW.z) * 6., sg = floor(sq); float sv = h(sg);   // sparkles ride the flow and fade on their own, never in one global step
          col += uHot * step(.9, sv) * pow(.5 + .5 * sin(uT * 2.5 + sv * 60.), 4.) * smoothstep(.45, .1, length(fract(sq) - .5)) * edge;
        } else if (uMode < 6.5) {    // pixels: a stream of blinking cells
          vec2 q = vec2(vW.x - t, vW.z) * 2.5, g = floor(q), c = fract(q);
          float v = h(g), pulse = .5 + .5 * sin(uT * 2.5 + v * 40.), cell = step(.07, c.x) * step(c.x, .93) * step(.07, c.y) * step(c.y, .93);
          col = mix(uDeep, uMid, step(.42, v) * (.45 + .55 * pulse) * cell) + uHot * step(.93, v) * pulse * cell * .8;
        } else {                     // lava: a dark crust cut by hot veins
          vec2 p = vec2(vW.x * .7 - t, vW.z * 1.6); float f = fbm(p + fbm(p * 1.3 + t * .4) * .9), vein = smoothstep(.08, .0, abs(f - .5));
          col = mix(uDeep, uMid, smoothstep(.25, .62, f)) + uHot * (vein * .8 + pow(f, 4.) * .4);
        }
        col += uFoam * pow(1. - edge, 3.) * .3;
        gl_FragColor = vec4(col, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}
export const CANAL_MODE = {liquid: 0, gold: 1, ice: 2, rift: 3, ticker: 4, rainbow: 5, pixels: 6, lava: 7};
