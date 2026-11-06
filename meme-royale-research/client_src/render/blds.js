// The buildings players drop (SHILL TURRET, MINING RIG, BAG LAUNCHER, HONEYPOT, MEME MINT, TROLL FARM, LASER EYES, BUBBLE MACHINE,
// SNIPER BOT, TOKEN BURNER, VESTING VAULT, BACKDOOR): a model per sim 'bld', dropped in, aiming, puffing, crumbling. Those without a
// model are made of primitives here (chunky, bevel-free toys).
import * as THREE from 'three';
import {loadGLB, cloneGLB} from './assets.js';
import {TEAM_COL} from './arena.js';
import {CARDS} from '../data.js';
import {S} from './kit.js';

// drawn bigger than their footprint, like the towers and the troops
export const BLD_VIS = 1.3;
// the buildings with a model of their own (assets/blds/<id>.glb, from Tripo by tools/chars/bld_build.py: on the ground, widest
// side 1, its front facing +z): yaw turns it more, w its width in footprint radii, top its coil or muzzle as a share of its height,
// muz how far ahead of the middle that is (model units)
const GLB = {shillturret: {aim: true}, baglauncher: {aim: true}, miningrig: {}, honeypot: {}, mememint: {}, trollfarm: {},
  lasereyes: {aim: true, top: 0.6, muz: 0.42}, bubblemachine: {aim: true, yaw: -Math.PI / 4, top: 0.66, muz: 0.4}, sniperbot: {aim: true, yaw: -0.52, top: 0.75, muz: 0.62}, tokenburner: {}, vestingvault: {}, backdoor: {}};
const box = (w, h, d, x, y, z, mat, to) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); b.position.set(x, y, z); to.add(b); return b; };
const cyl = (r0, r1, h, x, y, z, mat, to, n = 14) => { const c = new THREE.Mesh(new THREE.CylinderGeometry(r0, r1, h, n), mat); c.position.set(x, y, z); to.add(c); return c; };

export class BuildingViews {
  constructor(stage, fx) { this.stage = stage; this.fx = fx; if (fx) fx.blds = this; this.root = new THREE.Group(); stage.scene.add(this.root); this.views = new Map(); }
  clear() { for (const v of this.views.values()) { this.root.remove(v.g); this.free(v); } this.views.clear(); }
  async rigModel() { if (!this.rigP) this.rigP = loadGLB('assets/arena/tower_rig.glb').catch(() => null); return this.rigP; }
  // a model building: the model in a pivot that aims (turret, launcher), squashes when it fires or sends a troop out, and rises
  // out of its hatch (honeypot); ball: where its zaps start
  async model(e) {
    const o = GLB[e.card], glb = await loadGLB(`assets/blds/${e.card}.glb`).catch(() => null); if (!glb) return null;
    const m = cloneGLB(glb).scene, box = new THREE.Box3().setFromObject(m), sz = box.getSize(new THREE.Vector3());
    const k = Math.min(e.r * 2 * (o.w || 1.15) / Math.max(sz.x, sz.z), (CARDS[e.card].bld.h || 1.6) * 1.35 / sz.y);
    // one that doesn't aim turns its front (the side on its card) to the camera, whichever side it is on
    m.scale.setScalar(k / BLD_VIS); m.rotation.y = (o.yaw || 0) + (o.aim || e.team !== 0 ? 0 : Math.PI);
    // (Tripo's metal reads near black under the arena's light: half metal, more of the sky in it)
    m.traverse(c => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; c.material.metalness = Math.min(c.material.metalness, 0.5); c.material.envMapIntensity = 1.6; } });
    const pivot = new THREE.Group(); pivot.add(m);
    const ball = new THREE.Object3D(); ball.position.set(0, sz.y * k / BLD_VIS * (o.top || 1), (o.muz || 0) * k / BLD_VIS); pivot.add(ball);
    return {g: pivot, pivot, ball, head: o.aim ? pivot : null, jar: e.card === 'honeypot' ? pivot : null, deep: sz.y * k / BLD_VIS + 0.1};
  }
  turret(team) {
    const g = new THREE.Group(), col = TEAM_COL[team];
    const dark = new THREE.MeshStandardMaterial({color: '#22262e', metalness: 0.6, roughness: 0.45}), metal = new THREE.MeshStandardMaterial({color: '#9aa0aa', metalness: 0.8, roughness: 0.3});
    const glow = new THREE.MeshStandardMaterial({color: col.clone().multiplyScalar(0.5), emissive: col, emissiveIntensity: 1.6});
    const box = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.8, 1.3), dark); box.position.y = 0.4; g.add(box);
    for (const z of [-0.66, 0.66]) { const led = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.08, 0.02), glow); led.position.set(0, 0.55, z); g.add(led); }
    const head = new THREE.Group(); head.position.y = 0.85; g.add(head);
    const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.14, 0.9, 16, 1, true), new THREE.MeshStandardMaterial({color: '#f2eedf', side: THREE.DoubleSide, roughness: 0.5}));
    cone.rotation.x = Math.PI / 2; cone.position.set(0, 0.3, 0.35); head.add(cone);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.05, 8, 20), glow); ring.position.set(0, 0.3, 0.8); head.add(ring);
    const pivot = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.28, 0.3, 12), metal); pivot.position.y = 0.05; head.add(pivot);
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return {g, head};
  }
  // ---- the new buildings, each {g, head?, ...parts the update animates}
  mats(team) {
    const M = (color, o = {}) => new THREE.MeshStandardMaterial({color, roughness: 0.55, ...o}), col = TEAM_COL[team];
    return {steel: M('#3b404b', {metalness: 0.6, roughness: 0.4}), dark: M('#1d2028', {metalness: 0.4}), gold: M('#ffc84a', {metalness: 0.85, roughness: 0.25, emissive: '#4a3000', emissiveIntensity: 0.4}),
      wood: M('#8a5a32', {roughness: 0.8}), bag: M('#c9a46a', {roughness: 0.9}), glow: M(col.clone().multiplyScalar(0.5), {emissive: col, emissiveIntensity: 1.8}), white: M('#f2eedf')};
  }
  // BAG LAUNCHER: a stubby mortar on a ring of sandbags (money bags), turning to aim
  launcher(team) {
    const m = this.mats(team), g = new THREE.Group(), head = new THREE.Group();
    for (let k = 0; k < 7; k++) { const a = k / 7 * Math.PI * 2, b = new THREE.Mesh(new THREE.SphereGeometry(0.28, 10, 8).scale(1.2, 0.8, 1), m.bag); b.position.set(Math.cos(a) * 0.62, 0.2, Math.sin(a) * 0.62); b.rotation.y = -a; g.add(b); }
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.6, 0.35, 16), m.steel); base.position.y = 0.2; g.add(base);
    head.position.y = 0.45; g.add(head);
    const tilt = new THREE.Group(); tilt.rotation.x = -0.75; head.add(tilt);
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.4, 0.95, 16, 1, true), m.dark); barrel.position.y = 0.4; barrel.material.side = THREE.DoubleSide; tilt.add(barrel);
    const lip = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.07, 8, 20), m.gold); lip.rotation.x = Math.PI / 2; lip.position.y = 0.88; tilt.add(lip);
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.05, 8, 20), m.glow); band.rotation.x = Math.PI / 2; band.position.y = 0.2; tilt.add(band);
    const bag = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 8), m.bag); bag.position.y = 0.82; tilt.add(bag);
    const pin = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.14, 0.14), m.steel); pin.position.y = 0.05; head.add(pin);
    return {g, head, tilt, bag};
  }
  // HONEYPOT: a fat honey jar with a zapper coil on its lid; it hides under a hatch until something comes close
  honeypot(team) {
    const m = this.mats(team), g = new THREE.Group(), jar = new THREE.Group();
    const hatch = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.72, 0.06, 24), m.dark); hatch.position.y = 0.03; g.add(hatch);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.72, 0.05, 8, 28), m.glow); rim.rotation.x = Math.PI / 2; rim.position.y = 0.06; g.add(rim);
    const prof = [[0, 0], [0.42, 0], [0.56, 0.18], [0.6, 0.5], [0.52, 0.85], [0.36, 0.98], [0.36, 1.08], [0, 1.08]].map(([x, y]) => new THREE.Vector2(x, y));
    const honey = new THREE.MeshStandardMaterial({color: '#ffb21e', roughness: 0.18, metalness: 0.05, emissive: '#7a3d00', emissiveIntensity: 0.55, transparent: true, opacity: 0.93});
    jar.add(new THREE.Mesh(new THREE.LatheGeometry(prof, 20), honey));
    const lid = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.14, 20), m.gold); lid.position.y = 1.14; jar.add(lid);
    const drip = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 6).scale(1, 1.5, 1), honey); drip.position.set(0.5, 0.78, 0.12); jar.add(drip);
    const coil = new THREE.Group(); coil.position.y = 1.2; jar.add(coil);
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.07, 0.6, 8), m.steel); rod.position.y = 0.3; coil.add(rod);
    for (const [y, r] of [[0.2, 0.2], [0.36, 0.16], [0.5, 0.12]]) { const t = new THREE.Mesh(new THREE.TorusGeometry(r, 0.035, 6, 16), m.gold); t.rotation.x = Math.PI / 2; t.position.y = y; coil.add(t); }
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.13, 12, 10), new THREE.MeshStandardMaterial({color: '#fff6c0', emissive: '#ffe066', emissiveIntensity: 2.2})); ball.position.y = 0.66; coil.add(ball);
    g.add(jar);
    return {g, jar, ball, top: 1.86};
  }
  // MEME MINT: a coin press: a steel block, a gold stamp that slams down when a USELESS comes out of the chute
  mint(team) {
    const m = this.mats(team), g = new THREE.Group();
    const base = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.55, 1.1), m.steel); base.position.y = 0.28; g.add(base);
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.08, 20), m.gold); plate.position.y = 0.6; g.add(plate);
    for (const x of [-0.5, 0.5]) { const post = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1.15, 0.16), m.dark); post.position.set(x, 1.1, -0.1); g.add(post); }
    const beam = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.22, 0.3), m.dark); beam.position.set(0, 1.72, -0.1); g.add(beam);
    const stamp = new THREE.Group(); stamp.position.y = 1.3; g.add(stamp);
    const ram = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.5, 10), m.steel); ram.position.y = 0.2; stamp.add(ram);
    const die = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.2, 20), m.gold); die.position.y = -0.1; stamp.add(die);
    const chute = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.6), m.gold); chute.position.set(0, 0.32, 0.72); chute.rotation.x = 0.35; g.add(chute);
    const led = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.08, 0.02), m.glow); led.position.set(0, 0.42, 0.56); g.add(led);
    for (let k = 0; k < 5; k++) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.05, 14), m.gold); c.position.set(-0.45 + (k % 3) * 0.08, 0.58 + k * 0.05, 0.38); g.add(c); }
    return {g, stamp};
  }
  // TROLL FARM: a server rack shed with blinking lights, a dish on the roof and a door the trolls come out of
  farm(team) {
    const m = this.mats(team), g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.5, 1.4), m.dark); body.position.y = 0.75; g.add(body);
    const roof = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.16, 1.55), m.steel); roof.position.y = 1.58; g.add(roof);
    const leds = [];
    for (let r = 0; r < 4; r++) for (const sx of [-1, 1]) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.07, 0.9), new THREE.MeshStandardMaterial({color: '#111', emissive: TEAM_COL[team], emissiveIntensity: 1.5})); l.position.set(sx * 0.81, 0.4 + r * 0.28, 0); g.add(l); leds.push(l); }
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.95, 0.06), m.steel); door.position.set(0, 0.48, 0.72); g.add(door);
    const face = new THREE.Mesh(new THREE.CircleGeometry(0.2, 18), m.white); face.position.set(0, 1.16, 0.71); g.add(face);
    const grin = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.025, 6, 14, Math.PI), m.dark); grin.rotation.z = Math.PI; grin.position.set(0, 1.13, 0.72); g.add(grin);
    const dish = new THREE.Mesh(new THREE.SphereGeometry(0.36, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2.6), new THREE.MeshStandardMaterial({color: '#d8dbe2', metalness: 0.5, roughness: 0.35, side: THREE.DoubleSide}));
    dish.rotation.x = Math.PI * 0.75; dish.position.set(0.45, 1.95, -0.3); g.add(dish);
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.4, 6), m.steel); mast.position.set(0.45, 1.75, -0.3); g.add(mast);
    return {g, leds, door};
  }
  // ---- the second wave's stand-ins, until a model has its line in GLB (own: their geometry goes with them; ball: where shots and
  // beams start; a non-aimer's front turned to the camera, as a model's is)
  // LASER EYES: a stone idol on a plinth, its head turning to stare; the eyes are what burn
  idol(team) {
    const m = this.mats(team), g = new THREE.Group(), head = new THREE.Group(), stone = new THREE.MeshStandardMaterial({color: '#8d8879', roughness: 0.95}), dark = new THREE.MeshStandardMaterial({color: '#5c584d', roughness: 1});
    box(1.35, 0.4, 1.35, 0, 0.2, 0, dark, g); box(1, 0.7, 0.95, 0, 0.75, 0, stone, g); box(1.02, 0.08, 0.97, 0, 0.55, 0, m.glow, g);
    head.position.y = 1.1; g.add(head);
    box(1, 0.78, 0.9, 0, 0.39, 0, stone, head); box(0.24, 0.26, 0.74, 0, 0.88, -0.04, dark, head); box(1.1, 0.16, 0.22, 0, 0.6, 0.42, dark, head); box(0.18, 0.3, 0.16, 0, 0.26, 0.48, dark, head); box(0.5, 0.07, 0.04, 0, 0.07, 0.46, dark, head);
    const eyes = new THREE.MeshStandardMaterial({color: '#400808', emissive: '#ff2a18', emissiveIntensity: 1.2});
    for (const s of [-1, 1]) { const o = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 8), eyes); o.position.set(s * 0.22, 0.42, 0.46); head.add(o); }
    const ball = new THREE.Object3D(); ball.position.set(0, 0.42, 0.52); head.add(ball);
    return {g, head, ball, eyes, own: true};
  }
  // BUBBLE MACHINE: a tank of soap on stubby legs, a funnel turning to aim, the next bubble swelling in its mouth
  bubbler(team) {
    const m = this.mats(team), g = new THREE.Group(), head = new THREE.Group(), soap = new THREE.MeshStandardMaterial({color: '#7fd4ff', roughness: 0.12, metalness: 0.1, emissive: '#1a6aa0', emissiveIntensity: 0.5});
    for (const [x, z] of [[-0.42, -0.42], [0.42, -0.42], [-0.42, 0.42], [0.42, 0.42]]) cyl(0.07, 0.09, 0.3, x, 0.15, z, m.dark, g, 8);
    cyl(0.58, 0.62, 0.65, 0, 0.6, 0, m.steel, g); cyl(0.64, 0.64, 0.08, 0, 0.42, 0, m.glow, g); const dome = new THREE.Mesh(new THREE.SphereGeometry(0.54, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), soap); dome.position.y = 0.92; g.add(dome);
    head.position.y = 1.15; g.add(head);
    const horn = cyl(0.26, 0.1, 0.55, 0, 0, 0.32, m.gold, head); horn.rotation.x = Math.PI / 2;
    const next = new THREE.Mesh(new THREE.SphereGeometry(0.26, 12, 8), new THREE.MeshStandardMaterial({color: '#bfe8ff', emissive: '#4aa8e0', emissiveIntensity: 0.35, roughness: 0.08, metalness: 0.2, transparent: true, opacity: 0.5, depthWrite: false})); next.position.z = 0.68; head.add(next);
    const ball = new THREE.Object3D(); ball.position.z = 0.72; head.add(ball);
    return {g, head, ball, next, own: true};
  }
  // SNIPER BOT: a long rifle on a tripod: its barrel to the sky until it has set up, then level
  sniper(team) {
    const m = this.mats(team), g = new THREE.Group(), head = new THREE.Group(), rise = new THREE.Group(), gun = new THREE.Group();
    for (let k = 0; k < 3; k++) { const a = k / 3 * Math.PI * 2 + 0.5, l = cyl(0.05, 0.07, 1, Math.cos(a) * 0.32, 0.42, Math.sin(a) * 0.32, m.steel, g, 6); l.rotation.set(Math.sin(a) * 0.62, 0, -Math.cos(a) * 0.62); }
    box(0.5, 0.34, 0.44, 0, 0.92, 0, m.dark, g); box(0.52, 0.06, 0.46, 0, 0.82, 0, m.glow, g);
    head.position.y = 1.1; g.add(head); head.add(rise); rise.add(gun);
    box(0.3, 0.26, 0.8, 0, 0.1, 0, m.dark, gun);
    const barrel = cyl(0.05, 0.05, 1.25, 0, 0.12, 0.95, m.steel, gun, 8); barrel.rotation.x = Math.PI / 2;
    const brake = cyl(0.09, 0.09, 0.2, 0, 0.12, 1.55, m.dark, gun, 8); brake.rotation.x = Math.PI / 2;
    const scope = cyl(0.08, 0.08, 0.5, 0, 0.34, 0.1, m.steel, gun, 8); scope.rotation.x = Math.PI / 2; const lens = cyl(0.085, 0.085, 0.03, 0, 0.34, 0.36, m.glow, gun, 8); lens.rotation.x = Math.PI / 2;
    const ball = new THREE.Object3D(); ball.position.set(0, 0.12, 1.68); gun.add(ball);
    return {g, head, ball, rise, gun, own: true};
  }
  // TOKEN BURNER: a fat iron furnace with a chimney, the fire showing in its mouth
  burner(team) {
    const m = this.mats(team), g = new THREE.Group(), iron = new THREE.MeshStandardMaterial({color: '#6a5a50', roughness: 0.8, metalness: 0.15}), fire = new THREE.MeshStandardMaterial({color: '#401000', emissive: '#ff7a1a', emissiveIntensity: 2}); g.rotation.y = team === 0 ? Math.PI : 0;
    cyl(0.66, 0.74, 1.05, 0, 0.53, 0, iron, g, 16); cyl(0.76, 0.76, 0.08, 0, 0.22, 0, m.dark, g, 16); cyl(0.7, 0.7, 0.08, 0, 0.92, 0, m.glow, g, 16);
    box(0.62, 0.46, 0.1, 0, 0.5, 0.67, fire, g); for (const x of [-0.18, 0, 0.18]) box(0.05, 0.5, 0.05, x, 0.5, 0.74, m.dark, g);
    cyl(0.17, 0.2, 0.6, 0.26, 1.3, -0.1, iron, g, 10); cyl(0.2, 0.2, 0.06, 0.26, 1.6, -0.1, m.dark, g, 10);
    return {g, fire, own: true};
  }
  // VESTING VAULT: a squat steel safe, a round door with its wheel, gold stacked on top
  vault(team) {
    const m = this.mats(team), g = new THREE.Group(), plate = new THREE.MeshStandardMaterial({color: '#8c95a4', roughness: 0.5, metalness: 0.25}); g.rotation.y = team === 0 ? Math.PI : 0;
    box(1.4, 1.1, 1.3, 0, 0.55, 0, plate, g); box(1.44, 0.07, 1.34, 0, 0.14, 0, m.glow, g);
    const door = cyl(0.46, 0.46, 0.1, 0, 0.58, 0.68, m.dark, g, 20); door.rotation.x = Math.PI / 2;
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.04, 6, 16), m.gold); wheel.position.set(0, 0.58, 0.76); g.add(wheel); box(0.42, 0.05, 0.05, 0, 0.58, 0.76, m.gold, g); box(0.05, 0.42, 0.05, 0, 0.58, 0.76, m.gold, g);
    for (const [x, z] of [[-0.3, 0.12], [0.3, 0.12], [0, -0.22]]) box(0.5, 0.18, 0.26, x, 1.2, z, m.gold, g); box(0.5, 0.18, 0.26, 0, 1.38, 0.05, m.gold, g);
    return {g, own: true};
  }
  // BACKDOOR: a door standing on its own in a lit frame, nothing behind it but the dark; ajar, and it swings when one comes through
  backdoor(team) {
    const m = this.mats(team), g = new THREE.Group(), door = new THREE.Group(), panel = new THREE.MeshStandardMaterial({color: '#7a6a8c', roughness: 0.6, metalness: 0.15}); g.rotation.y = team === 0 ? Math.PI : 0;
    box(1.2, 0.1, 0.6, 0, 0.05, 0, m.dark, g); for (const x of [-0.56, 0.56]) { box(0.12, 1.4, 0.16, x, 0.75, 0, m.dark, g); box(0.03, 1.3, 0.17, x * 0.88, 0.72, 0, m.glow, g); } box(1.24, 0.12, 0.16, 0, 1.46, 0, m.dark, g);
    box(1, 1.3, 0.03, 0, 0.75, -0.03, new THREE.MeshBasicMaterial({color: '#07040c'}), g);
    door.position.set(-0.49, 0.75, 0.04); g.add(door); box(0.96, 1.3, 0.06, 0.48, 0, 0, panel, door); box(0.08, 0.08, 0.08, 0.84, -0.05, 0.05, m.gold, door);
    return {g, door, ajar: 0.45, own: true};
  }
  // (own stand-ins: their geometry; the team's materials are a few and go with the context)
  free(v) { if (v.parts?.own) v.parts.g.traverse(o => o.geometry?.dispose()); }
  async make(e) {
    const v = {ent: e, g: new THREE.Group(), born: performance.now(), drop: 1};
    v.g.position.set(e.x, 5, e.z); v.g.rotation.y = e.team === 0 ? Math.PI : 0; this.root.add(v.g); this.views.set(e.id, v);
    const ring = new THREE.Mesh(new THREE.RingGeometry(e.r * 1.05, e.r * 1.25, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({color: TEAM_COL[e.team], transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false}));
    ring.position.y = 0.04; v.g.add(ring); v.m = new THREE.Group(); v.m.scale.setScalar(BLD_VIS); v.g.add(v.m);
    if (GLB[e.card] && (v.parts = await this.model(e))) {
      v.m.add(v.parts.g); v.head = v.parts.head;
    } else if (e.card === 'miningrig') {
      const glb = await this.rigModel();
      if (glb) { const m = cloneGLB(glb).scene; m.scale.setScalar(0.55); m.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; if (/^team/i.test(o.name || '') || /^team/i.test(o.parent?.name || '')) { o.material = o.material.clone(); o.material.color.set('#7a3ac8'); o.material.emissive = new THREE.Color('#b250f6'); o.material.emissiveIntensity = 1.8; } } }); v.m.add(m); }
    } else {
      const T = e.card === 'baglauncher' ? this.launcher(e.team) : e.card === 'honeypot' ? this.honeypot(e.team) : e.card === 'mememint' ? this.mint(e.team) : e.card === 'trollfarm' ? this.farm(e.team)
        : e.card === 'lasereyes' ? this.idol(e.team) : e.card === 'bubblemachine' ? this.bubbler(e.team) : e.card === 'sniperbot' ? this.sniper(e.team) : e.card === 'tokenburner' ? this.burner(e.team) : e.card === 'vestingvault' ? this.vault(e.team) : e.card === 'backdoor' ? this.backdoor(e.team) : this.turret(e.team);
      v.m.add(T.g); v.head = T.head; v.parts = T;
      T.g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    }
  }
  // the sim said: it fired (a recoil, a zap), it sent out a troop (the stamp slams, the door flaps)
  shot(id) { const v = this.views.get(id); if (v) v.kick = 1; }
  spawned(id) { const v = this.views.get(id); if (v) v.kick = 1; }
  // the honeypot's coil, the idol's eyes, a muzzle (whatever is its ball), in the world, for where its shot starts
  coilWorld(id, out = new THREE.Vector3()) { const v = this.views.get(id); if (!v?.parts?.ball) return null; return v.parts.ball.getWorldPosition(out); }
  update(battle, dt, alpha) {
    const seen = new Set();
    for (const e of battle.ents.values()) {
      if (e.kind !== 'bld') continue; seen.add(e.id);
      let v = this.views.get(e.id);
      if (!v) { this.make(e); continue; }
      v.ent = e;
      // the drop
      if (v.drop > 0) { v.drop = Math.max(0, v.drop - dt * 3.2); v.g.position.y = v.drop * v.drop * 5; if (v.drop === 0) { this.fx.land(v.g.position, e.r, e.team, 20); } }
      if (v.head && e.target) { let d = e.aim - v.g.rotation.y - v.head.rotation.y; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2; v.head.rotation.y += d * Math.min(1, dt * 10); }
      const P = v.parts, kick = v.kick = Math.max(0, (v.kick || 0) - dt * 4);
      if (P?.pivot) { const q = Math.sin(Math.min(1, kick) * Math.PI); P.pivot.scale.set(1 + q * 0.06, 1 - q * 0.1, 1 + q * 0.06); }
      if (P?.tilt) { P.tilt.position.z = -kick * 0.25; P.bag.visible = kick < 0.2; }
      if (P?.jar) {             // up while it has a target, back down under its hatch
        const deep = P.deep || 1.25, want = e.hidden && e.state !== 'deploy' ? -deep : 0; P.jar.position.y += (want - P.jar.position.y) * Math.min(1, dt * (want < 0 ? 5 : 12));
        P.jar.visible = P.jar.position.y > 0.05 - deep; if (P.ball.material) P.ball.material.emissiveIntensity = 1.6 + kick * 4 + Math.sin(performance.now() / 70) * 0.4;
      }
      if (P?.stamp) P.stamp.position.y = 1.3 - Math.sin(kick * Math.PI) * 0.55;
      if (P?.leds) for (const l of P.leds) if (Math.random() < dt * 6) l.material.emissiveIntensity = Math.random() < 0.6 ? 1.8 : 0.2;
      if (P?.door) P.door.rotation.y = (P.ajar || 0) + Math.sin(kick * Math.PI) * 1.2;
      if (P?.eyes) P.eyes.emissiveIntensity = !e.beamOn ? 1.2 : e.beamT < 2 ? 2.4 : e.beamT < 4 ? 3.6 : 5;                 // (the idol's stare heats up)
      if (P?.next) P.next.scale.setScalar(0.35 + (1 - kick) * 0.65);                                                       // (the next bubble swells)
      if (P?.gun) P.gun.position.z = -kick * 0.14;
      if (P?.rise) { const k = e.state === 'deploy' ? Math.max(0, e.st) / (CARDS[e.card].bld.setup || 1) : 0; P.rise.rotation.x = -1.25 * k; }   // (level once it's set up)
      if (P?.fire) P.fire.emissiveIntensity = 1.7 + kick * 3 + Math.sin(performance.now() / 65) * 0.4;
      // a little life of their own (few sprites; by the card, so a model gets them too)
      const top = e.h * BLD_VIS, qu = Math.random();
      if (e.card === 'tokenburner') { if (qu < dt * 9) this.fx.add.emit({x: e.x + (e.team === 0 ? -0.34 : 0.34), y: top * 1.02, z: e.z, vy: 1.3, life: 0.5, s0: 0.85, s1: 0.2, c: [1, 0.55, 0.15], cell: 13}); }
      else if (e.card === 'bubblemachine') { if (qu < dt * 2.5) this.fx.sp.emit({kind: S.BUBBLE, x: e.x + (Math.random() - 0.5) * 0.7, y: top * 0.8, z: e.z + (Math.random() - 0.5) * 0.7, vy: 0.9, g: -0.2, life: 1, w0: 0.1, w1: 0.34, c: [0.72, 0.93, 1.3], a0: 1, a1: 0.7, add: 0.5}); }
      else if (e.card === 'backdoor') { if (qu < dt * 5) this.fx.sp.emit({kind: S.WISP, x: e.x, y: top * 0.75, z: e.z, vy: 0.2, life: 0.7, w0: 0.7, w1: 1.2, c: [0.65, 0.35, 1.3], a0: 0.45, a1: 0, add: 1}); }
      else if (e.card === 'vestingvault') { if (qu < dt * 1.3) this.fx.sp.emit({kind: S.FLARE, x: e.x + (Math.random() - 0.5) * 0.8, y: top * 0.95, z: e.z + (Math.random() - 0.5) * 0.5, life: 0.4, w0: 0.45, w1: 0, c: [1.8, 1.4, 0.6], a0: 1, a1: 1, add: 1, rot: 0}); }
      // the rig puffs copium; an ageing building sags a little and smokes near its end
      if (e.card === 'miningrig' && Math.random() < dt * 3) this.fx.add.emit({x: e.x + (Math.random() - 0.5) * 0.6, y: 2.2, z: e.z, vy: 0.8, life: 1.4, s0: 0.5, s1: 1.2, c: [0.7, 0.45, 1], a0: 0.5, cell: 0});
      const k = e.hp / e.max; if (k < 0.35 && Math.random() < dt * 4) this.fx.norm.emit({x: e.x, y: 1.2, z: e.z, vy: 0.9, life: 1.6, s0: 0.5, s1: 1.3, c: [0.2, 0.2, 0.24], a0: 0.45, cell: 3});
      v.g.scale.y = 0.85 + 0.15 * Math.max(0.3, k);
    }
    for (const [id, v] of this.views) if (!seen.has(id)) { this.root.remove(v.g); this.free(v); this.views.delete(id); }
  }
}
