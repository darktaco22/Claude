// The menus' sky: one painting (clouds framing the sides and a sea of them below, a glow in the middle for the arena) in the
// light of the player's own clock (dawn, day, dusk, night), brought to life on a little WebGL canvas. The clouds billow and
// sway in place (a slow warp, only where the mask says clouds), the glow breathes, and over the painting the shader draws
// what each light has: at night a sky of stars (sharp points at any screen size, each with its own slow beat), big
// four-pointed sparkles, a shooting star now and then and specks of light rising off the clouds; at dusk the first
// stars, embers and orange rays; at dawn the last stars, gold motes, pink rays and birds; by day the sun's rays, white
// wisps and birds. High thin veils drift across every light. The painting (starless: the stars are all drawn here) and its
// mask come from tools/ui/skyanim.py. Behind every menu screen, hidden in battle (style.css #sky), drawn at 30 fps only
// while the menus show and no bag opening covers them. Without WebGL (or with reduced motion) the painting stands still as #sky's CSS background.
// ?sky=day (dawn, dusk, night) forces a light, for a look; ?skyt=12.5 stops its clock at that second.
const LIGHTS = ['dawn', 'day', 'dusk', 'night'];

export function period(d = new Date()) {
  const h = d.getHours() + d.getMinutes() / 60;
  return h >= 5.5 && h < 7.5 ? 'dawn' : h >= 7.5 && h < 17.5 ? 'day' : h >= 17.5 && h < 20 ? 'dusk' : 'night';
}

// each light's touches. star: how bright the stars are, how far down the painting they reach (0 top .. 1 bottom), the
// sparkles, the chance of a shooting star in each 7 s; ray, mote (the rising specks), veil: colour and strength; birds
const LOOK = {
  night: {star: [1, 0.62, 1, 0.6], ray: [0.35, 0.85, 1, 0.05], mote: [0.5, 1, 0.92, 0.85], veil: [0.4, 0.55, 0.95, 0.09], birds: 0},
  dusk: {star: [0.8, 0.3, 0.55, 0.2], ray: [1, 0.62, 0.38, 0.17], mote: [1, 0.7, 0.32, 0.9], veil: [1, 0.55, 0.72, 0.1], birds: 0},
  dawn: {star: [0.5, 0.2, 0.3, 0], ray: [1, 0.8, 0.72, 0.17], mote: [1, 0.9, 0.66, 0.55], veil: [1, 0.86, 0.92, 0.12], birds: 1},
  day: {star: [0, 0, 0, 0], ray: [1, 0.98, 0.88, 0.2], mote: [1, 1, 1, 0.3], veil: [1, 1, 1, 0.15], birds: 1},
};

// the painting is zoomed in by ZOOM about FOOT (a point of the screen, 0..1 across and down: the foot of the home's arena),
// so its glow stays behind the arena and as big beside it as before the arena grew by that much (the CSS one too: #sky::before)
const ZOOM = 1.19, FOOT = [0.5, 0.56];

const VS = `attribute vec2 a; varying vec2 v; void main() { v = a * 0.5 + 0.5; gl_Position = vec4(a, 0.0, 1.0); }`;
// (p: the painting, 0..1 down from its top left; S: the screen in CSS pixels, up from its bottom left, so every size and
// speed is the same on a phone and a desktop; the hash has no sine in it: a phone's sine of a big number is noise)
const FS = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 v; uniform sampler2D img, msk; uniform vec4 fit, star, ray, mote, veil; uniform vec2 res; uniform float t, k, birds;
float h(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { s += a * n(p); p = p * 2.07 + 13.7; a *= 0.5; } return s; }
// one layer of stars: in some cells of a grid one star, kept off its cell's edges so it is never cut (cell and radius r in
// CSS px); each has its own size, colour and slow beat, brightening and dimming over the sky, never darker than it
vec3 stars(vec2 S, float cell, float dens, float r, float seed) {
  vec2 id = floor(S / cell) + seed, f = fract(S / cell);
  if (h(id) > dens) return vec3(0.0);
  vec2 d = (f - 0.25 - 0.5 * vec2(h(id + 1.7), h(id + 4.3))) * cell;
  float rr = r * (0.6 + 0.8 * h(id + 9.1)), b = exp(-dot(d, d) / (rr * rr));
  float beat = 0.55 + 0.45 * sin(t * (0.6 + 1.6 * h(id + 2.2)) + 6.283 * h(id + 5.5));
  vec3 col = h(id + 3.3) > 0.84 ? vec3(1.0, 0.84, 0.58) : mix(vec3(0.7, 0.84, 1.0), vec3(1.0), h(id + 6.6));
  return col * b * beat * (0.4 + 0.6 * h(id + 7.7));
}
// the big four-pointed sparkles: a core, two thin crossed rays that grow and shrink with a slow pulse, a soft halo
vec3 sparkles(vec2 S, float cell, float dens) {
  vec2 id = floor(S / cell) + 71.0, f = fract(S / cell);
  if (h(id) > dens) return vec3(0.0);
  vec2 d = (f - 0.3 - 0.4 * vec2(h(id + 1.3), h(id + 2.9))) * cell * k, a = abs(d);
  float pu = 0.5 + 0.5 * sin(t * (0.45 + 0.5 * h(id + 4.1)) + 6.283 * h(id + 8.2));
  float L = (6.0 + 7.0 * h(id + 5.7)) * k * (0.5 + 0.5 * pu);
  float arms = exp(-a.x / L * 2.4) * exp(-a.y * a.y * 0.8) + exp(-a.y / L * 2.4) * exp(-a.x * a.x * 0.8);
  float core = exp(-dot(d, d) * 0.3), halo = exp(-dot(d, d) / (L * L * 0.5)) * 0.2;
  vec3 col = h(id + 6.1) > 0.5 ? vec3(1.0, 0.86, 0.55) : vec3(0.72, 0.86, 1.0);
  return col * (arms * 0.9 + core + halo) * (0.4 + 0.6 * pu);
}
// a shooting star: maybe one in each 7 s (star.w its chance), across the upper sky in under a second, its tail growing
float shoot(vec2 S) {
  float c = floor(t / 7.0), u = t - c * 7.0;
  if (u > 0.9 || h(vec2(c, 9.0)) > star.w) return 0.0;
  u /= 0.9;
  float side = h(vec2(c, 1.0)) > 0.5 ? 1.0 : -1.0;
  vec2 dir = normalize(vec2(side, -0.45)), s0 = vec2(res.x * ((side > 0.0 ? 0.08 : 0.5) + 0.42 * h(vec2(c, 2.0))), res.y * (0.8 + 0.15 * h(vec2(c, 3.0))));
  vec2 d = S - s0 - dir * min(res.x, 600.0) * 0.45 * u;
  float along = -dot(d, dir), across = dot(d, vec2(-dir.y, dir.x)), len = min(res.x, 600.0) * 0.18 * min(1.0, u * 2.5);
  float tail = step(0.0, along) * step(along, len) * (1.0 - along / max(len, 1.0)) * exp(-across * across * k * k / 0.8);
  return (tail * 0.8 + exp(-dot(d, d) * k * k / 2.2) * 1.4) * sin(3.14159 * u);
}
// specks of light rising off the clouds, swaying, each fading in and out on its own
float motes(vec2 S) {
  vec2 Q = S - vec2(0.0, t * 13.0), id = floor(Q / 70.0), f = fract(Q / 70.0);
  if (h(id + 31.0) > 0.42) return 0.0;
  vec2 d = (f - vec2(0.3 + 0.4 * h(id + 2.0) + 0.1 * sin(t * 0.7 + 6.283 * h(id + 5.0)), 0.3 + 0.4 * h(id + 3.0))) * 70.0;
  float life = max(sin(t * (0.22 + 0.2 * h(id + 7.0)) + 6.283 * h(id + 9.0)), 0.0);
  return (exp(-dot(d, d) * k * k / 2.0) + exp(-dot(d, d) / 26.0) * 0.3) * life * life;
}
// a little flock in a loose line, wings beating, crossing the upper sky in 16 s of each 26
float flock(vec2 S) {
  float c = floor(t / 26.0), u = (t - c * 26.0) / 16.0;
  if (u > 1.0) return 0.0;
  float dir = h(vec2(c, 4.0)) > 0.5 ? 1.0 : -1.0;
  vec2 lead = vec2(mix(-80.0, res.x + 80.0, dir > 0.0 ? u : 1.0 - u), res.y * (0.64 + 0.16 * h(vec2(c, 5.0))) + sin(u * 7.0) * 5.0);
  float a = 0.0;
  for (int i = 0; i < 5; i++) {
    float fi = float(i);
    vec2 d = (S - lead - vec2(-dir * fi * 17.0, (mod(fi, 2.0) * 2.0 - 1.0) * fi * 5.0 + h(vec2(c, fi)) * 8.0)) / (1.0 - fi * 0.07);
    float x = abs(d.x), y = x * (0.1 + 0.55 * (0.5 + 0.5 * sin(t * 8.0 + fi * 1.9))) - x * x * 0.025;
    if (x < 6.0) a = max(a, exp(-(d.y - y) * (d.y - y) * k * k / 0.7) * (1.0 - x / 7.0));
  }
  return a;
}
void main() {
  vec2 p = vec2(v.x, 1.0 - v.y) * fit.xy + fit.zw, S = gl_FragCoord.xy / k;
  float m = texture2D(msk, p).r;
  vec2 q = p * vec2(3.0, 4.5);
  vec2 d = vec2(n(q + vec2(t * 0.08, t * 0.02)), n(q * 1.3 + vec2(7.0 - t * 0.06, t * 0.03))) - 0.5;
  d = d * 0.022 + vec2(sin(t * 0.3 + p.y * 5.0) * 0.008, sin(t * 0.23 + p.x * 4.0) * 0.003);
  vec3 c = texture2D(img, p + d * m).rgb;
  float lum = dot(c, vec3(0.3, 0.55, 0.15));
  // the glow breathes; rays turn slowly round it (two fans the other way about, whole-number counts: no seam)
  vec2 g = (p - vec2(0.5, 0.3)) * vec2(1.0, 1.5);
  float r = length(g), an = atan(g.y, g.x);
  c *= 1.0 + exp(-r * r / 0.05) * 0.07 * sin(t * 0.55);
  float fan = (0.5 + 0.5 * sin(an * 8.0 + t * 0.06)) * (0.65 + 0.35 * sin(an * 13.0 - t * 0.045 + 2.0));
  c += ray.rgb * ray.a * fan * fan * exp(-r * 2.6) * smoothstep(0.02, 0.2, r) * (1.0 - 0.6 * m);   // (faded at the heart: they'd pinch to a point)
  // the clouds' lit rims shimmer
  c += c * m * smoothstep(0.45, 0.85, lum) * 0.06 * (0.5 + 0.5 * sin(t * 0.9 + n(p * 7.0) * 6.283));
  // high thin veils drifting across the upper sky
  float vl = smoothstep(0.5, 0.85, fbm(p * vec2(2.2, 6.0) + vec2(t * 0.008, t * 0.002))) * (1.0 - smoothstep(0.3, 0.6, p.y));
  c += veil.rgb * veil.a * vl * (1.0 - 0.8 * m);
  // the stars, only in open sky, fading as it brightens, behind the veils, down to the light's own line
  if (star.x > 0.0) {
    float sky = (1.0 - smoothstep(0.08, 0.45, m)) * (1.0 - smoothstep(0.3, 0.62, lum)) * (1.0 - vl * 0.7) * (1.0 - smoothstep(star.y - 0.18, star.y, p.y));
    if (sky > 0.0) c += (stars(S, 9.0, 0.24, 0.55, 0.0) + stars(S, 26.0, 0.36, 1.05, 37.0) * 1.2 + sparkles(S, 110.0, 0.42) * star.z + vec3(0.85, 0.93, 1.0) * shoot(S)) * star.x * sky;
  }
  if (mote.a > 0.0) c += mote.rgb * mote.a * motes(S) * smoothstep(0.36, 0.6, p.y);
  if (birds > 0.0) { float b = flock(S) * birds; c = mix(c, c * 0.3 + vec3(0.04, 0.06, 0.12), b * 0.75); }
  gl_FragColor = vec4(c, 1.0);
}`;

export function mountSky() {
  const el = document.createElement('div'); el.id = 'sky'; el.setAttribute('aria-hidden', 'true');
  document.body.prepend(el);
  const Q = new URLSearchParams(location.search), force = Q.get('sky'), stop = Q.has('skyt') ? +Q.get('skyt') : null;
  let light = null, canvas = null, gl = null, prog = null, tex = {}, ready = false, raf = 0, last = 0, t0 = performance.now();
  const still = matchMedia('(prefers-reduced-motion: reduce)');
  const load = (url, unit) => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = url; }).then(im => {
    if (!gl) return;
    const tx = tex[unit] || (tex[unit] = gl.createTexture()); gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tx);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im);
    for (const [k, val] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, val);
    return im;
  });
  const set = () => {
    const p = LIGHTS.includes(force) ? force : period(); if (p === light) return;
    light = p; document.body.dataset.sky = p;
    if (gl) load(`/assets/ui/sky_${p}.webp`, 0).then(() => { if (light === p) { ready = true; canvas.classList.add('on'); } }).catch(() => {});
  };
  // the WebGL layer: none on a reduced-motion setting or where WebGL is missing (the CSS painting stays)
  if (!still.matches) {
    canvas = document.createElement('canvas');
    gl = canvas.getContext('webgl', {alpha: false, antialias: false, depth: false, stencil: false, powerPreference: 'low-power'});
    if (gl) {
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
      prog = gl.createProgram(); gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { console.warn('sky:', gl.getProgramInfoLog(prog), gl.getShaderInfoLog(gl.getAttachedShaders(prog)[1])); gl = null; }
    }
    if (gl) {
      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const a = gl.getAttribLocation(prog, 'a'); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
      gl.uniform1i(gl.getUniformLocation(prog, 'img'), 0); gl.uniform1i(gl.getUniformLocation(prog, 'msk'), 1);
      el.append(canvas);
      load('/assets/ui/sky_mask.webp', 1).catch(() => { gl = null; canvas.remove(); });
      canvas.addEventListener('webglcontextlost', e => { e.preventDefault(); gl = null; canvas.remove(); cancelAnimationFrame(raf); });
    } else canvas = null;
  }
  const U = gl && Object.fromEntries(['fit', 't', 'k', 'res', 'star', 'ray', 'mote', 'veil', 'birds'].map(u => [u, gl.getUniformLocation(prog, u)]));
  // under the bag opening (opaque, over every menu) none of it shows: its frames are skipped, the phone's GPU left to the
  // cards flying out (style.css hides it there too)
  const covered = () => document.querySelector('#ui > .bagopen');
  const draw = now => {
    raf = 0;
    if (!gl || !document.body.classList.contains('menu') || document.hidden) return;   // the menus' 'menu' class wakes it (below)
    raf = requestAnimationFrame(draw);
    if (!ready || now - last < 32 || covered()) return; last = now;
    const k = Math.min(devicePixelRatio || 1, 1.5), w = Math.round(el.clientWidth * k), h = Math.round(el.clientHeight * k);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h); }
    // cover: the painting is 2:3, kept centred across and 30 % down, like the CSS one under it; then zoomed about FOOT
    const ia = 2 / 3, sa = w / h, sx = sa > ia ? 1 : sa / ia, sy = sa > ia ? ia / sa : 1, z = 1 - 1 / ZOOM;
    gl.uniform4f(U.fit, sx / ZOOM, sy / ZOOM, (1 - sx) / 2 + FOOT[0] * sx * z, (1 - sy) * 0.3 + FOOT[1] * sy * z);
    const L = LOOK[light] || LOOK.night;
    gl.uniform1f(U.t, stop ?? (now - t0) / 1000 % 3600); gl.uniform1f(U.k, k); gl.uniform2f(U.res, w / k, h / k);
    gl.uniform4fv(U.star, L.star); gl.uniform4fv(U.ray, L.ray); gl.uniform4fv(U.mote, L.mote); gl.uniform4fv(U.veil, L.veil); gl.uniform1f(U.birds, L.birds);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  };
  const wake = () => { if (gl && !raf) raf = requestAnimationFrame(draw); };
  new MutationObserver(wake).observe(document.body, {attributes: true, attributeFilter: ['class']});
  document.addEventListener('visibilitychange', wake);
  set(); setInterval(set, 60000); wake();
}
