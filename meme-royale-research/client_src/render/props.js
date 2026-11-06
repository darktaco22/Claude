// The spells' props, built from the shapes on their cards: a chart's candlesticks (green or red), the god candle, a golden ban
// hammer, a chunky downvote arrow, a parachute carrying a coin, an ice block holding a hardware wallet, a potion flask, a fuel
// nozzle, a tombstone, a cut diamond. Each is made once; prop(name) hands out a clone (geometry and materials shared: tint a clone by
// swapping its material, never by editing it).
import * as THREE from 'three';

// a box with rounded edges (its normals from the rounding: smooth all round)
export function rbox(w, h, d, r = 0.05, s = 3) {
  const g = new THREE.BoxGeometry(w, h, d, s * 2, s * 2, s * 2), p = g.attributes.position, nm = g.attributes.normal, v = new THREE.Vector3(), c = new THREE.Vector3();
  const hw = w / 2 - r, hh = h / 2 - r, hd = d / 2 - r;
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i); c.set(Math.max(-hw, Math.min(hw, v.x)), Math.max(-hh, Math.min(hh, v.y)), Math.max(-hd, Math.min(hd, v.z)));
    v.sub(c); if (v.lengthSq() < 1e-12) v.fromBufferAttribute(nm, i); v.normalize(); nm.setXYZ(i, v.x, v.y, v.z); v.multiplyScalar(r).add(c); p.setXYZ(i, v.x, v.y, v.z);
  }
  return g;
}
const std = o => new THREE.MeshStandardMaterial(o);
function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; }

export const MAT = {};
function mats() {
  if (MAT.gold) return;
  Object.assign(MAT, {
    green: std({color: '#1fd04c', emissive: '#14b83c', emissiveIntensity: 0.55, roughness: 0.32, metalness: 0.05}),
    red: std({color: '#ee2a40', emissive: '#c0102a', emissiveIntensity: 0.5, roughness: 0.32, metalness: 0.05}),
    wick: std({color: '#2a2f38', roughness: 0.6}),
    gold: std({color: '#ffc23a', metalness: 0.92, roughness: 0.24, emissive: '#5a3800', emissiveIntensity: 0.35}),
    darkGold: std({color: '#b07a12', metalness: 0.9, roughness: 0.35}),
    wood: std({color: '#5a321a', roughness: 0.75}),
    grip: std({color: '#22150c', roughness: 0.9}),
    stone: std({color: '#8a8f99', roughness: 0.92}),
    moss: std({color: '#4e5a3c', roughness: 0.95}),
    steel: std({color: '#c9ced6', metalness: 0.9, roughness: 0.28}),
    black: std({color: '#15171c', roughness: 0.45, metalness: 0.2}),
    cork: std({color: '#a9784a', roughness: 0.85}),
  });
  // the coin's face: gold, a raised rim, the U
  MAT.coinFace = std({map: canvasTex(128, 128, (g, w) => {
    const r = g.createRadialGradient(54, 50, 6, 64, 64, 64); r.addColorStop(0, '#fff2a8'); r.addColorStop(0.55, '#ffcb3a'); r.addColorStop(1, '#b8800e');
    g.fillStyle = r; g.fillRect(0, 0, w, w); g.lineWidth = 8; g.strokeStyle = '#a06c08'; g.beginPath(); g.arc(64, 64, 54, 0, 7); g.stroke();
    g.font = '900 78px "Lilita One", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#1c1404'; g.fillText('U', 64, 70); }),
    metalness: 0.75, roughness: 0.3, emissive: '#4a3000', emissiveIntensity: 0.4});
}

const P = {};
function build(name) {
  mats(); const g = new THREE.Group();
  if (name === 'candleG' || name === 'candleR') {   // a candlestick: a body and its wick through it
    const m = name === 'candleG' ? MAT.green : MAT.red;
    const body = new THREE.Mesh(rbox(0.5, 1, 0.5, 0.07), m); body.position.y = 0.5;
    const wick = new THREE.Mesh(rbox(0.09, 1.7, 0.09, 0.03, 1), MAT.wick); wick.position.y = 0.5;
    g.add(wick, body);
  } else if (name === 'rocket') {                 // PUMP's: a green candle with fins, a lit wick on top
    const body = new THREE.Mesh(rbox(0.7, 1.6, 0.7, 0.1, 3), MAT.green); body.position.y = 0.8;
    const wick = new THREE.Mesh(rbox(0.1, 0.4, 0.1, 0.03, 1), MAT.wick); wick.position.y = 1.75;
    for (let i = 0; i < 3; i++) { const f = new THREE.Mesh(rbox(0.08, 0.6, 0.5, 0.03, 1), MAT.green); const a = i / 3 * Math.PI * 2; f.position.set(Math.cos(a) * 0.42, 0.25, Math.sin(a) * 0.42); f.rotation.y = -a; g.add(f); }
    g.add(body, wick);
  } else if (name === 'godcandle') {               // the colossal one: glowing from within, brighter at the top
    const tex = canvasTex(64, 256, (c, w, h) => { const l = c.createLinearGradient(0, 0, 0, h); l.addColorStop(0, '#d6ffc0'); l.addColorStop(0.25, '#5cff6e'); l.addColorStop(1, '#0e8a2e');
      c.fillStyle = l; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(255,255,255,0.25)'; c.fillRect(6, 0, 6, h); c.fillStyle = 'rgba(0,0,0,0.18)'; c.fillRect(w - 12, 0, 12, h); });
    const body = new THREE.Mesh(rbox(1.5, 6, 1.5, 0.16, 4), std({map: tex, emissiveMap: tex, emissive: '#ffffff', emissiveIntensity: 1.6, roughness: 0.3}));
    body.position.y = 3; const wick = new THREE.Mesh(rbox(0.26, 9, 0.26, 0.08, 1), std({color: '#7CFF6B', emissive: '#7CFF6B', emissiveIntensity: 2.2})); wick.position.y = 3;
    g.add(wick, body);
  } else if (name === 'hammer') {                  // gold head with darker bands at its faces, a wooden handle wrapped in grip
    const head = new THREE.Mesh(rbox(1.05, 1.05, 2.3, 0.14, 3), MAT.gold);
    for (const s of [-1, 1]) { const band = new THREE.Mesh(rbox(1.16, 1.16, 0.24, 0.08, 2), MAT.darkGold); band.position.z = s * 0.95; head.add(band);
      const face = new THREE.Mesh(rbox(0.9, 0.9, 0.14, 0.06, 2), MAT.gold); face.position.z = s * 1.18; head.add(face); }
    const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.15, 2.4, 12), MAT.wood); handle.position.y = 1.65;
    for (let i = 0; i < 4; i++) { const r = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.04, 6, 14), MAT.grip); r.rotation.x = Math.PI / 2; r.position.y = 2.1 + i * 0.18; g.add(r); }
    const knob = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 8), MAT.darkGold); knob.position.y = 2.9;
    g.add(head, handle, knob);
  } else if (name === 'arrow') {                   // a chunky arrow pointing down (its tip at the origin), bevelled, its sides darker
    const s = new THREE.Shape(); s.moveTo(-0.17, 1.15); s.lineTo(0.17, 1.15); s.lineTo(0.17, 0.42); s.lineTo(0.42, 0.42); s.lineTo(0, 0); s.lineTo(-0.42, 0.42); s.lineTo(-0.17, 0.42); s.closePath();
    const geo = new THREE.ExtrudeGeometry(s, {depth: 0.28, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.05, bevelSegments: 3}); geo.translate(0, 0, -0.14);
    g.add(new THREE.Mesh(geo, [std({color: '#ff2a40', emissive: '#c80c26', emissiveIntensity: 0.55, roughness: 0.25, metalness: 0.1}),
      std({color: '#8e0a1a', emissive: '#4a000c', emissiveIntensity: 0.4, roughness: 0.4})]));
  } else if (name === 'parachute') {               // a glossy green canopy bulging in its gores, dark seams, a scalloped hem, its
    // lines, a big coin hanging under it
    const can = new THREE.SphereGeometry(1, 48, 8, 0, Math.PI * 2, 0, Math.PI * 0.44), cols = [], pos = can.attributes.position, v = new THREE.Vector3();
    const A = new THREE.Color('#2cc23c'), B = new THREE.Color('#62ec70'), SEAM = new THREE.Color('#0e6a1c'), c = new THREE.Color();
    for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i); const a = Math.atan2(v.z, v.x), f = ((a + Math.PI) / (Math.PI * 2) * 10) % 1, bulge = Math.sin(f * Math.PI);
      const hem = 1 - v.y; v.multiplyScalar(1 + bulge * 0.07); v.y -= (1 - bulge) * hem * 0.12; pos.setXYZ(i, v.x, v.y, v.z);
      c.copy(A).lerp(B, bulge * bulge * 0.7).lerp(SEAM, Math.max(0, 1 - bulge * 6)); cols.push(c.r, c.g, c.b); }
    can.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3)); can.scale(0.85, 0.7, 0.85); can.computeVertexNormals();
    const canopy = new THREE.Mesh(can, std({vertexColors: true, roughness: 0.28, metalness: 0.05, side: THREE.DoubleSide, emissive: '#0c4a12', emissiveIntensity: 0.35})); canopy.position.y = 1.55;
    const rim = []; for (let i = 0; i < 10; i++) { const a = (i + 0.5) / 10 * Math.PI * 2; rim.push(Math.cos(a) * 0.84, 1.55 + 0.12, Math.sin(a) * 0.84, 0, 0.5, 0); }
    const lines = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(rim, 3)), new THREE.LineBasicMaterial({color: '#f4f8ec', transparent: true, opacity: 0.9}));
    const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.14, 32), [MAT.darkGold, MAT.coinFace, MAT.coinFace]); coin.rotation.x = Math.PI / 2; coin.position.y = 0;
    g.add(canopy, lines, coin);
  } else if (name === 'coin') {
    const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.09, 28), [MAT.darkGold, MAT.coinFace, MAT.coinFace]); coin.rotation.x = Math.PI / 2; g.add(coin);
  } else if (name === 'icespike') {               // a cluster of ice crystals breaking out of the ground (it grows from y = 0)
    const ice = std({color: '#9fdcff', emissive: '#2f9be0', emissiveIntensity: 0.55, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.88, envMapIntensity: 2});
    for (const [x, z, h, w, tx, tz] of [[0, 0, 1.15, 0.2, 0, 0], [0.2, 0.08, 0.75, 0.15, 0.1, 0.45], [-0.17, 0.1, 0.65, 0.14, 0.15, -0.5], [0.04, -0.2, 0.55, 0.12, -0.45, 0.1]]) {
      const geo = new THREE.ConeGeometry(w, h, 5, 1); geo.translate(0, h / 2, 0);
      const m = new THREE.Mesh(geo, ice); m.position.set(x, -0.05, z); m.rotation.set(tx, Math.random() * 6, tz); g.add(m); }
  } else if (name === 'iceblock') {                // clear blue ice, frosted at its edges, a hardware wallet frozen in it
    const crack = canvasTex(128, 128, (c, w) => { c.fillStyle = '#0a2a44'; c.fillRect(0, 0, w, w); c.strokeStyle = 'rgba(200,240,255,0.9)'; c.lineWidth = 1.5;
      for (let i = 0; i < 9; i++) { c.beginPath(); let x = Math.random() * w, y = Math.random() * w; c.moveTo(x, y); for (let j = 0; j < 4; j++) { x += (Math.random() - 0.5) * 50; y += (Math.random() - 0.5) * 50; c.lineTo(x, y); } c.stroke(); } });
    const ice = new THREE.Mesh(rbox(1.7, 1.7, 1.7, 0.18, 3), std({color: '#7cc8ff', transparent: true, opacity: 0.6, roughness: 0.06, metalness: 0.1, emissive: '#cfefff', emissiveMap: crack, emissiveIntensity: 1.2, envMapIntensity: 2, depthWrite: false}));
    ice.renderOrder = 7; ice.position.y = 0.85;
    const dev = new THREE.Mesh(rbox(0.42, 0.85, 0.14, 0.06, 2), MAT.black); dev.position.y = 0.85; dev.rotation.set(0.2, 0.5, 0.25);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.28, 0.32), std({color: '#000', emissive: '#4ad8ff', emissiveIntensity: 1.6})); scr.position.set(0, 0.12, 0.075); dev.add(scr);
    const btn = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.05, 12), MAT.steel); btn.rotation.x = Math.PI / 2; btn.position.set(0, -0.25, 0.075); dev.add(btn);
    g.add(dev, ice);
  } else if (name === 'flask') {                   // a round-bottomed potion flask: clear glass (bright only at its rim and in a
    // highlight), pink hopium swirled with gold in its belly (hopium turns 'liq''s map), a gold lip and band, a cork
    const prof = [[0, 0], [0.42, 0.06], [0.62, 0.3], [0.66, 0.6], [0.55, 0.9], [0.24, 1.08], [0.18, 1.2], [0.18, 1.52], [0.24, 1.58], [0.24, 1.64], [0, 1.64]].map(([x, y]) => new THREE.Vector2(x, y));
    const glass = new THREE.Mesh(new THREE.LatheGeometry(prof, 32), new THREE.ShaderMaterial({transparent: true, depthWrite: false, uniforms: {uCol: {value: new THREE.Color('#ffd8f4')}},
      vertexShader: 'varying vec3 vN; varying vec3 vV; void main() { vec4 p = modelViewMatrix * vec4(position, 1.); vN = normalize(normalMatrix * normal); vV = -normalize(p.xyz); gl_Position = projectionMatrix * p; }',
      fragmentShader: `uniform vec3 uCol; varying vec3 vN; varying vec3 vV;
        void main() { vec3 n = normalize(vN), v = normalize(vV); float f = pow(1. - abs(dot(n, v)), 2.2), s = pow(max(0., dot(reflect(-v, n), normalize(vec3(-.4, .6, .7)))), 30.);
          gl_FragColor = vec4(uCol * (f * 1.4 + .06) + vec3(s * 2.5), .06 + f * .7 + s * .8); }`}));
    glass.renderOrder = 7;
    const lip = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.045, 8, 20), MAT.gold); lip.rotation.x = Math.PI / 2; lip.position.y = 1.58; g.add(lip);
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.19, 0.035, 8, 20), MAT.gold); band.rotation.x = Math.PI / 2; band.position.y = 1.2; g.add(band);
    const swirl = canvasTex(128, 64, (c, w, h) => { const d = c.createImageData(w, h);   // pink, gold ribbons, white-pink streaks
      for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const u = i / w, v = j / h, q = Math.sin((u * 3 + v * 1.6) * Math.PI * 2 + Math.sin(v * 9 + u * Math.PI * 2) * 1.4);
        const gd = Math.max(0, q) ** 6, wh = Math.max(0, -q) ** 10, k = (j * w + i) * 4;
        d.data[k] = 255; d.data[k + 1] = 70 + gd * 150 + wh * 160; d.data[k + 2] = 190 - gd * 120 + wh * 50; d.data[k + 3] = 255; }
      c.putImageData(d, 0, 0); });
    swirl.wrapS = swirl.wrapT = THREE.RepeatWrapping;
    const liq = new THREE.Mesh(new THREE.LatheGeometry(prof.slice(0, 4).concat([new THREE.Vector2(0.62, 0.78), new THREE.Vector2(0, 0.78)]).map(v => new THREE.Vector2(v.x * 0.9, v.y * 0.95 + 0.03)), 32),
      std({map: swirl, emissiveMap: swirl, emissive: '#ffffff', emissiveIntensity: 1.1, roughness: 0.3}));
    liq.name = 'liq';
    const cork = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.16, 0.3, 12), MAT.cork); cork.position.y = 1.68;
    g.add(liq, glass, cork);
  } else if (name === 'nozzle') {                  // a fuel nozzle: grip, trigger guard, the spout bent down, the hose off the back
    const red = std({color: '#d8202c', roughness: 0.4, metalness: 0.15});
    const grip = new THREE.Mesh(rbox(0.36, 0.95, 0.42, 0.12, 2), MAT.black); grip.rotation.z = -0.35; grip.position.set(0.1, 0, 0);
    const body = new THREE.Mesh(rbox(1.05, 0.5, 0.48, 0.14, 2), red); body.position.set(-0.35, 0.42, 0);
    const guard = new THREE.Mesh(new THREE.TorusGeometry(0.26, 0.045, 6, 16, Math.PI), MAT.steel); guard.position.set(-0.3, 0.05, 0); guard.rotation.z = Math.PI;
    const spout = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(-0.8, 0.45, 0), new THREE.Vector3(-1.4, 0.4, 0), new THREE.Vector3(-1.75, 0.05, 0), new THREE.Vector3(-1.85, -0.35, 0)]), 16, 0.1, 10), MAT.steel);
    const hose = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(0.25, -0.45, 0), new THREE.Vector3(0.5, -0.9, 0), new THREE.Vector3(1.2, -0.6, 0.2), new THREE.Vector3(1.8, 0.6, 0.4), new THREE.Vector3(2.2, 2.4, 0.6)]), 24, 0.13, 8), MAT.black);
    g.add(grip, body, guard, spout, hose);
  } else if (name === 'tomb') {                    // a tombstone: an arched slab, a U carved in it, a mound of earth at its foot
    const s = new THREE.Shape(); s.moveTo(-0.45, 0); s.lineTo(0.45, 0); s.lineTo(0.45, 0.85); s.absarc(0, 0.85, 0.45, 0, Math.PI, false); s.lineTo(-0.45, 0);
    const geo = new THREE.ExtrudeGeometry(s, {depth: 0.2, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 2}); geo.translate(0, 0, -0.1);
    const slab = new THREE.Mesh(geo, MAT.stone);
    const carve = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.55), new THREE.MeshStandardMaterial({map: canvasTex(64, 64, (c, w) => { c.font = '900 50px "Lilita One", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = '#3a3e46'; c.fillText('U', 32, 36); }), transparent: true, roughness: 1}));
    carve.position.set(0, 0.78, 0.15);
    const mound = new THREE.Mesh(new THREE.SphereGeometry(0.6, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2).scale(1, 0.35, 0.8), std({color: '#4a3424', roughness: 1})); mound.position.z = 0.55;
    g.add(slab, carve, mound);
  } else if (name === 'diamond') {                 // DIAMOND HANDS': a brilliant cut: a flat table, a shallow crown, a deep point; pale ice-blue, lit from within
    const prof = [[0, 0], [0.92, 1.05], [0.56, 1.42], [0, 1.42]].map(([x, y]) => new THREE.Vector2(x, y)), geo = new THREE.LatheGeometry(prof, 8).toNonIndexed(); geo.computeVertexNormals(); geo.translate(0, -1, 0);
    g.add(new THREE.Mesh(geo, std({color: '#bfeaff', emissive: '#4ab0e8', emissiveIntensity: 0.55, roughness: 0.08, metalness: 0.15, envMapIntensity: 2.2})));
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return g;
}
export function prop(name) { return (P[name] ||= build(name)).clone(); }
