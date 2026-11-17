// THE REAPING props, built inside the game scene with the game's own three.js: lectern, glass bowl of name slips, banner.
window.__props = (async () => {
  const THREE = await import('/v/-OSbT01_3H/vendor/three.module.js');
  const G = window.__game, sc = G.stage.scene;
  if (window.__propG) sc.remove(window.__propG);
  const g = new THREE.Group(); window.__propG = g; sc.add(g);
  const P = window.__PROPS || {};
  const std = (c, r = 0.6, m = 0) => new THREE.MeshStandardMaterial({color: c, roughness: r, metalness: m});
  const add = (geo, mat, x, y, z, parent = g) => { const o = new THREE.Mesh(geo, mat); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true; parent.add(o); return o; };
  const canvasTex = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
  // ---- lectern + glass bowl
  if (P.bowl) {
    const [bx, bz, bs = 1] = P.bowl; const L = new THREE.Group(); L.position.set(bx, 0, bz); L.scale.setScalar(bs); g.add(L);
    const wood = std('#5a3520', 0.55), gold = std('#d9a93a', 0.3, 0.9);
    add(new THREE.CylinderGeometry(0.62, 0.78, 0.12, 40), gold, 0, 0.06, 0, L);
    add(new THREE.CylinderGeometry(0.34, 0.46, 1.25, 40), wood, 0, 0.74, 0, L);
    add(new THREE.CylinderGeometry(0.62, 0.42, 0.14, 40), gold, 0, 1.42, 0, L);
    const pts = []; for (let i = 0; i <= 24; i++) { const a = i / 24 * Math.PI * 0.62; pts.push(new THREE.Vector2(0.05 + Math.sin(a) * 0.62, 1.49 + (1 - Math.cos(a)) * 0.62)); }
    const glass = new THREE.MeshStandardMaterial({color: '#e4f6ff', roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.3, side: THREE.DoubleSide, envMapIntensity: 4, depthWrite: false});
    const bowl = add(new THREE.LatheGeometry(pts, 64), glass, 0, 0, 0, L); bowl.castShadow = false; bowl.renderOrder = 5;
    const rim = add(new THREE.TorusGeometry(0.05 + Math.sin(Math.PI * 0.62) * 0.62, 0.018, 8, 64), new THREE.MeshStandardMaterial({color: '#ffffff', transparent: true, opacity: 0.6, roughness: 0.05}), 0, 1.49 + (1 - Math.cos(Math.PI * 0.62)) * 0.62, 0, L); rim.rotation.x = Math.PI / 2;
    // folded name slips, piled
    let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    const paper = std('#f4efe2', 0.85);
    for (let i = 0; i < 70; i++) {
      const r = 0.48 * Math.sqrt(rnd()), a = rnd() * Math.PI * 2, y = 1.54 + rnd() * 0.32 + (0.48 - r) * 0.25;
      const o = add(new THREE.BoxGeometry(0.16, 0.012, 0.09), paper, Math.cos(a) * r, y, Math.sin(a) * r, L); o.rotation.set(rnd() * 1.2 - 0.6, rnd() * 6.3, rnd() * 1.2 - 0.6); o.castShadow = false;
    }
    window.__bowlTop = [bx, (1.49 + (1 - Math.cos(Math.PI * 0.62)) * 0.62) * bs, bz];
  }
  // ---- the chosen slip: rises out of the bowl and turns to camera (battle time)
  if (P.slip && window.__bowlTop) {
    const [t0, name] = P.slip; const [bx, by, bz] = window.__bowlTop;
    const tex = canvasTex(1024, 600, (c, W, H) => { c.fillStyle = '#f6f1e3'; c.fillRect(0, 0, W, H); c.strokeStyle = '#d8cfb6'; c.lineWidth = 6; c.beginPath(); c.moveTo(0, H / 2); c.lineTo(W, H / 2); c.stroke();
      c.fillStyle = '#1b1b1f'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.font = `900 ${Math.round(H * 0.42)}px "Courier New", monospace`; c.fillText(name, W / 2, H * 0.53); });
    const slip = add(new THREE.PlaneGeometry(0.62, 0.36), new THREE.MeshStandardMaterial({map: tex, roughness: 0.9, side: THREE.DoubleSide, emissive: '#ffffff', emissiveIntensity: 0.12, emissiveMap: tex}), bx, by - 0.3, bz);
    slip.castShadow = false; slip.visible = false;
    const sm = x => x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x);
    const U = G.units, ou = U.update.bind(U);
    U.update = (dt, a) => { ou(dt, a); const m = window.__match, t = m && m.running ? m.b.t : 0; const u = sm((t - t0) / 0.9);
      slip.visible = t >= t0; slip.position.set(bx, by - 0.35 + u * 1.15 + Math.sin(t * 2.2) * 0.015 * u, bz + u * 0.35);
      slip.rotation.set(-0.15 * (1 - u), (1 - u) * 3.6, (1 - u) * 0.8); slip.scale.setScalar(0.55 + 0.45 * u); };
  }
  // ---- banner on two poles
  if (P.banner) {
    const [x, z, w, h, y0] = P.banner;
    const tex = canvasTex(2048, Math.round(2048 * h / w), (c, W, H) => {
      c.fillStyle = '#121014'; c.fillRect(0, 0, W, H);
      c.strokeStyle = '#d9a93a'; c.lineWidth = H * 0.035; c.strokeRect(H * 0.05, H * 0.05, W - H * 0.1, H - H * 0.1);
      c.fillStyle = '#d9a93a'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.font = `900 ${Math.round(H * 0.16)}px Georgia, serif`; c.fillText('THE 1ST ANNUAL', W / 2, H * 0.27);
      c.font = `900 ${Math.round(H * 0.42)}px Georgia, serif`; c.fillText('MEME REAPING', W / 2, H * 0.6);
      c.font = `700 ${Math.round(H * 0.11)}px Georgia, serif`; c.fillText('STRIP MALL LOT  ·  ATTENDANCE MANDATORY', W / 2, H * 0.86);
    });
    const ban = add(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({map: tex, roughness: 0.8, side: THREE.DoubleSide}), x, y0 + h / 2, z); ban.castShadow = false;
    const pole = std('#2a2a2e', 0.4, 0.8);
    for (const dx of [-w / 2 - 0.08, w / 2 + 0.08]) { add(new THREE.CylinderGeometry(0.07, 0.07, y0 + h + 0.3, 12), pole, x + dx, (y0 + h + 0.3) / 2, z); add(new THREE.SphereGeometry(0.13, 16, 12), std('#d9a93a', 0.3, 0.9), x + dx, y0 + h + 0.35, z); }
  }
  // ---- red carpet strip / stage
  if (P.stage) { const [x, z, w, d] = P.stage; add(new THREE.BoxGeometry(w, 0.02, d), std('#6b1418', 0.9), x, 0.011, z); }
  return 'props ok';
})();
