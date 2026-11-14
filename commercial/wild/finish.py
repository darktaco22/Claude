"""Finish "A NATURAL HISTORY":  python3 finish.py FRAMES_DIR OUT_DIR VO_DIR [f1,f2,...]  ->  OUT_DIR/c_####.png (1920x1080, 2.35:1 letterbox, 24 fps) + mix.wav
The picture: the graded 3D frames (warm dawn grade, bloom, halation, vignette, grain), flashes and punches on the big moments, the opening title,
the species lower thirds, subtitles in the lower bar, and the end card.
The sound: the narrator, a synthesized score (strings, plucks, timpani, a choir swell for the candle), dawn birds and wind, the game's own
effects, and - after "Excuse me" - a chair and a door."""
import os, sys, json, math, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FR, OUT, VOD = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); AU = os.path.join(HERE, '..', 'comeback', 'audio'); SFX = os.path.join(HERE, '..', 'degens', 'audio', 'sfx')
E = json.load(open(os.path.join(HERE, 'edl.json'))); SHOTS = E['shots']; FPS = 24; N3D = E['last']; T_CARD = E['t_card']; T_FILM = E['t_film']; NF = int(round(T_FILM * FPS)); EV = E['ev']
W, H = 1920, 1080; CH = 816; Y0 = (H - CH) // 2
ONLY = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
def lil(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def rub(s, w=500):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def bump(t, t0, dur): return max(0.0, 1 - abs(t - t0) / dur)
def decay(t, t0, dur): return max(0.0, 1 - (t - t0) / dur) if t >= t0 else 0.0
def fade(t, t0, t1, d=0.35): return ease((t - t0) / d) * ease((t1 - t) / d)
def spaced(d, xy, text, font, fill, sp=0, anchor='l'):
    """Text with letter spacing; anchor l / m (centre) / r on x, baseline-middle on y."""
    ws = [d.textlength(c, font=font) for c in text]; tot = sum(ws) + sp * (len(text) - 1); x = xy[0] - (tot / 2 if anchor == 'm' else (tot if anchor == 'r' else 0))
    for c, w_ in zip(text, ws):
        for dx, dy, al in ((0, 3, 0.55), (0, 0, 0.0)) if len(fill) == 4 else ((0, 0, 0.0),):
            d.text((x + dx, xy[1] + dy), c, font=font, fill=(0, 0, 0, int(fill[3] * al)) if al else fill, anchor='lm', stroke_width=3 if al else 0, stroke_fill=(0, 0, 0, int(fill[3] * al * 0.5)) if al else None)
        x += w_ + sp
    return tot
# ---------------------------------------------------------------- picture
yy, xx = np.mgrid[0:CH, 0:W].astype(np.float32)
RR = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - CH / 2) / (CH / 2)) ** 2
VIG = (1 - 0.34 * RR ** 1.3)[..., None]
def punch(a, k):
    if k <= 1.0005: return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)); w, h = im.size; nw, nh = w / k, h / k
    return np.asarray(im.crop((int((w - nw) / 2), int((h - nh) / 2), int((w - nw) / 2 + nw), int((h - nh) / 2 + nh))).resize((w, h), Image.BILINEAR), np.float32) / 255.0
def aberrate(a, px):
    if px < 0.5: return a
    return np.stack([np.roll(a[..., 0], int(px), axis=1), a[..., 1], np.roll(a[..., 2], -int(px), axis=1)], axis=2)
def grade(a):
    lum = a.mean(axis=2, keepdims=True); a = lum + (a - lum) * 1.1
    a = a * np.array([1.04, 1.0, 0.95], np.float32) + 0.045 * (1 - lum) ** 2 * np.array([-0.2, 0.1, 0.45], np.float32)       # warm highlights, a little teal in the shadows
    a = np.clip((a - 0.015) * 1.08, 0, 1) ** 1.04
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.74) / 0.26, 0, 1) * a
    hb = Image.fromarray((hi * 255).astype(np.uint8)).resize((W // 4, CH // 4), Image.BILINEAR)
    b1 = np.asarray(hb.filter(ImageFilter.GaussianBlur(10)).resize((W, CH), Image.BILINEAR), np.float32) / 255.0
    b2 = np.asarray(hb.filter(ImageFilter.GaussianBlur(34)).resize((W, CH), Image.BILINEAR), np.float32) / 255.0
    return a + b1 * 0.36 + b2 * np.array([1.0, 0.72, 0.5], np.float32) * 0.26                                              # bloom, and a wide warm halation
BG = None
def card(t):
    """The end card: the key art, dimmed and blurred, the logo, the line."""
    global BG
    if BG is None:
        b = Image.open(os.path.join(A, 'bg_title_wide.jpg')).convert('RGB'); k = max(W / b.width, H / b.height); b = b.resize((int(b.width * k) + 1, int(b.height * k) + 1), Image.LANCZOS)
        b = b.crop(((b.width - W) // 2, (b.height - H) // 2, (b.width - W) // 2 + W, (b.height - H) // 2 + H)).filter(ImageFilter.GaussianBlur(14)); BG = (np.asarray(b, np.float32) / 255.0 * 0.34, Image.open(os.path.join(A, 'logo.png')).convert('RGBA'))
    bg, logo = BG; u = t - T_CARD; a = bg * ease(u / 0.5); yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32); a = a * (1 - 0.5 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2))[..., None]
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA'); k = ease((u - 0.15) / 0.5); s = int(470 * (1.06 - 0.06 * k)); lg = logo.resize((s, int(s * logo.height / logo.width)), Image.LANCZOS)
    lg.putalpha(lg.getchannel('A').point(lambda v: int(v * k))); im.alpha_composite(lg, ((W - lg.width) // 2, 250 - (lg.height - 446) // 2)); d = ImageDraw.Draw(im, 'RGBA')
    k2 = ease((u - 0.9) / 0.5); spaced(d, (W / 2, 770), 'FREE TO PLAY', rub(54, 700), (255, 236, 200, int(255 * k2)), 10, 'm')
    k3 = ease((u - 1.5) / 0.5); spaced(d, (W / 2, 842), 'MERCIFULLY.', rub(30, 500), (255, 220, 170, int(215 * k3)), 8, 'm')
    spaced(d, (W / 2, 930), 'memeroyale.imaginestudio.fun', rub(30, 400), (255, 255, 255, int(170 * k2)), 2, 'm')
    return im.convert('RGB')
def overlays(im, t):
    d = ImageDraw.Draw(im, 'RGBA')
    # the opening title
    k = fade(t, 0.9, 5.2, 0.7)
    if k > 0:
        spaced(d, (W / 2, Y0 + CH * 0.70), 'MEME ROYALE', rub(34, 600), (255, 244, 225, int(235 * k)), 22, 'm')
        w_ = 520 * ease((t - 0.9) / 1.2); d.line([(W / 2 - w_ / 2, Y0 + CH * 0.70 + 36), (W / 2 + w_ / 2, Y0 + CH * 0.70 + 36)], fill=(255, 214, 150, int(200 * k)), width=2)
        spaced(d, (W / 2, Y0 + CH * 0.70 + 86), 'A NATURAL HISTORY', rub(64, 400), (255, 250, 240, int(255 * k)), 14, 'm')
    # species lower thirds
    for t0, t1, title, sub in E['lower']:
        k = fade(t, t0, t1, 0.4)
        if k <= 0: continue
        x = 150 - 30 * (1 - ease((t - t0) / 0.5)); y = Y0 + CH - 150; h_ = 86 * ease((t - t0) / 0.45)
        d.line([(x, y + 43 - h_ / 2), (x, y + 43 + h_ / 2)], fill=(255, 205, 120, int(255 * k)), width=4)
        spaced(d, (x + 24, y + 20), title, rub(42, 700), (255, 250, 240, int(255 * k)), 5)
        spaced(d, (x + 24, y + 68), sub, rub(27, 400), (255, 232, 196, int(235 * k)), 1)
    # subtitles, in the lower bar
    for i, t0, t1 in E['cues']:
        if t0 - 0.05 <= t < t1 + 0.15 and t < T_CARD:
            d.text((W / 2, Y0 + CH + (H - Y0 - CH) / 2 - 4), E['subs'][i], font=rub(34, 400), fill=(255, 255, 255, 225), anchor='mm')
    return im
def frame(f):
    t = (f - 1) / FPS
    if f > N3D:
        im = card(t)
    else:
        a = np.asarray(Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGB').resize((W, CH), Image.LANCZOS), np.float32) / 255.0
        k = 1.0; ab = 0.0; fl = 0.0; col = np.array([1.0, 1.0, 1.0], np.float32)
        d = decay(t, EV['erupt'], 0.9); k += 0.08 * d * d; ab += 14 * d * d
        if d > 0: fl = max(fl, 0.8 * decay(t, EV['erupt'], 0.3) ** 1.5); col = np.array([0.7, 1.0, 0.78], np.float32)
        d = decay(t, EV['ko'], 0.5); k += 0.05 * d; ab += 8 * d; fl = max(fl, 0.45 * decay(t, EV['ko'], 0.16))
        d = decay(t, EV['pull'], 0.5); k += 0.03 * d; ab += 5 * d
        d = decay(t, EV['fall'], 0.9); k += 0.09 * d * d; ab += 16 * d * d; fl = max(fl, 0.55 * decay(t, EV['fall'], 0.22))
        if k > 1: a = punch(a, k)
        a = aberrate(a, ab); a = grade(a)
        if fl > 0: a = a * (1 - min(1, fl)) + col * min(1, fl) * 1.2
        a = a * VIG * ease(t / 0.9) * ease((T_CARD - t) / 0.3 + 0.0)                # in from black; a short dip to black before the card
        a = a + np.random.default_rng(f).normal(0, 0.012, (CH, W, 1)).astype(np.float32)
        canvas = np.zeros((H, W, 3), np.float32); canvas[Y0:Y0 + CH] = a
        im = Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8))
    overlays(im, t).save(os.path.join(OUT, f'c_{f:04d}.png'))
for f in ([] if os.environ.get('SOUND_ONLY') else (ONLY or range(1, NF + 1))): frame(f)
print('FRAMES-DONE')
if ONLY: sys.exit(0)

# ---------------------------------------------------------------- sound
SR = 48000; END = NF / FPS; n = int(END * SR) + SR; rng = np.random.default_rng(23)
BUS = {k: np.zeros((n, 2), np.float32) for k in ('vo', 'mus', 'amb', 'fx')}
def load(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()
def game(name): return load(os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3')))
def put(bus, x, t, g=1.0, pan=0.0):
    i = int(t * SR); m = min(len(x), n - i)
    if m > 0 and i >= 0: BUS[bus][i:i + m] += x[:m] * g * np.array([1 - max(0, pan), 1 + min(0, pan)], np.float32)
def env(pts, length): return np.interp(np.arange(length) / SR, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)
def mono(s): return np.stack([s, s], 1).astype(np.float32)
def lowpass(x, k): return np.convolve(x, np.ones(k) / k, 'same')
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def strings(m, t, dur, g=0.1, att=1.2, rel=1.6, bright=7):
    """A soft section: three detuned voices, harmonics rolled off, slow attack, a little vibrato."""
    L = int((dur + rel) * SR); x = np.arange(L) / SR; s = np.zeros(L)
    for det in (-0.06, 0.0, 0.07):
        f = midi(m + det); ph = 2 * np.pi * f * x + 0.9 * np.sin(2 * np.pi * (4.6 + det * 3) * x) * np.clip(x / 1.5, 0, 1)
        for h in range(1, bright + 1): s += np.sin(ph * h + h * det * 20) / h ** 1.35
    e = np.clip(x / att, 0, 1) ** 1.5 * np.clip((dur + rel - x) / rel, 0, 1) ** 1.5; put('mus', mono(s * e), t, g / 3)
def pluck(m, t, g=0.2, dur=0.5, pan=0.0):
    L = int(dur * SR); x = np.arange(L) / SR; f = midi(m); s = sum(np.sin(2 * np.pi * f * h * x) * np.exp(-x * (5 + 4 * h)) / h for h in range(1, 6)); put('mus', mono(s), t, g, pan)
def timp(t, m=38, g=0.6):
    L = int(1.4 * SR); x = np.arange(L) / SR; f = midi(m); s = np.sin(2 * np.pi * (f * x + 8 * np.exp(-x * 30) / 30)) * np.exp(-x / 0.35) + 0.5 * np.sin(2 * np.pi * f * 1.5 * x) * np.exp(-x / 0.15) + rng.normal(0, 1, L) * np.exp(-x / 0.01) * 0.3; put('mus', mono(s), t, g)
def choir(m, t, dur, g=0.1):
    """Aah: harmonics shaped by two vowel formants."""
    L = int((dur + 2.0) * SR); x = np.arange(L) / SR; s = np.zeros(L)
    for det in (-0.09, 0.0, 0.1):
        f = midi(m + det); ph = 2 * np.pi * f * x + 1.2 * np.sin(2 * np.pi * (5.0 + det) * x)
        for h in range(1, 14):
            fr = f * h; amp = math.exp(-((fr - 750) / 260) ** 2) + 0.6 * math.exp(-((fr - 1200) / 320) ** 2) + 0.12 / h; s += np.sin(ph * h) * amp
    e = np.clip(x / 0.5, 0, 1) * np.clip((dur + 2.0 - x) / 2.0, 0, 1) ** 2; put('mus', mono(s * e), t, g / 3)
def boom(t, f0=50, dur=2.2, g=0.9):
    x = np.arange(int(dur * SR)) / SR; s = np.sin(2 * np.pi * (f0 * x - 10 * x * x / dur)) * np.exp(-x / (dur * 0.35)) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.05) * 0.5; put('fx', mono(s), t, g)
def whoosh(t, dur=1.0, g=0.4):
    x = np.arange(int(dur * SR)) / SR; u = x / dur; k = lowpass(rng.normal(0, 1, len(x)), 120) * 12; e = np.sin(np.pi * u) ** 2; put('fx', mono(k * e + 0.25 * np.sin(2 * np.pi * (80 + 300 * u) * x) * e), t, g)
def rumble(t0, t1, g=0.5):
    x = np.arange(int((t1 - t0) * SR)) / SR; u = x / (t1 - t0); s = lowpass(rng.normal(0, 1, len(x)), 400) * 30 + np.sin(2 * np.pi * 36 * x) * 0.8 + np.sin(2 * np.pi * 47 * x + 3 * np.sin(2 * np.pi * 3 * x)) * 0.5; put('fx', mono(s * u ** 1.6), t0, g)
def coin(t, g=0.2):
    x = np.arange(int(0.5 * SR)) / SR; f = rng.uniform(2200, 3600); s = (np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 1.5 * x)) * np.exp(-x / 0.09); put('fx', mono(s), t, g, rng.uniform(-0.5, 0.5))
def chirp(t, g=0.06):
    """One bird: two or three quick upward notes."""
    f0 = rng.uniform(2600, 5200); pan = rng.uniform(-0.8, 0.8)
    for k in range(rng.integers(2, 5)):
        L = int(rng.uniform(0.05, 0.11) * SR); x = np.arange(L) / SR; u = x / (L / SR); s = np.sin(2 * np.pi * (f0 * x * (1 + 0.25 * u) + 30 * np.sin(2 * np.pi * 28 * x))) * np.sin(np.pi * u) ** 2; put('amb', mono(s), t + k * rng.uniform(0.09, 0.16), g, pan)
def thud(t, g=0.5):
    x = np.arange(int(0.3 * SR)) / SR; s = np.sin(2 * np.pi * (90 * x - 60 * x * x)) * np.exp(-x / 0.05) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.008) * 0.4; put('fx', mono(s), t, g)
CUE = {i: (t0, t1) for i, t0, t1 in E['cues']}; S = {s['name']: s for s in SHOTS}
# the narrator
for i, t0, t1 in E['cues']: put('vo', load(os.path.join(VOD, i + '.wav')), t0, 1.0)
# dawn: wind and birds, all the way through (the birds leave when the herd does, and after the candle)
x = np.arange(n) / SR; wind = lowpass(rng.normal(0, 1, n), 900) * 14 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * x)); put('amb', mono(wind), 0, 0.05)
t = 0.3
while t < END - 4:
    if not (EV['stampede'] < t < EV['stampede'] + 2.5 or EV['rumble'] < t < S['aftermath']['t1']): chirp(t, 0.035 + 0.035 * rng.random())
    t += rng.uniform(0.25, 1.1)
# the score.  D major, slow: the dawn theme
def chord(notes, t, dur, g=0.1, **kw):
    for m in notes: strings(m, t, dur, g, **kw)
t_p = S['pepe profile']['t0']; t_h = S['herd graze']['t0']; t_dip = EV['plip']; t_du = S['duel wide']['t0']; t_r = EV['rumble']; t_e = EV['erupt']; t_tug = S['tug']['t0']; t_pull = EV['pull']; t_fall = EV['fall']; t_pa = S['pepe again']['t0']
chord((50, 57, 62, 66), 0.2, t_p / 2, 0.12); chord((69, 74), 1.6, t_p / 2 - 1.4, 0.07, att=2.0); chord((43, 55, 62, 67, 71), t_p / 2 + 0.2, t_p / 2 - 0.2, 0.12); strings(78, t_p / 2 + 1.0, t_p / 2 - 1.4, 0.05, att=2.0)
# the Pepe: one held low chord, a lone high line
chord((47, 54, 59, 62), t_p, t_h - t_p - 0.6, 0.11)
for k, (m, dt, du) in enumerate(((74, 0.6, 1.6), (73, 2.3, 1.2), (71, 3.6, 1.9), (66, 5.4, 1.4))): strings(m, t_p + dt, du, 0.075, att=0.5, rel=1.0, bright=5)
# the herd: plucked, light on its feet
seq = (62, 66, 69, 66, 64, 67, 71, 67, 62, 66, 69, 74, 73, 69, 66, 64); k = 0; t = t_h + 0.2
while t < t_dip - 0.15: pluck(seq[k % 16], t, 0.2, 0.5, 0.3 * (-1) ** k); pluck(seq[k % 16] - 24 if k % 4 == 0 else 0, t, 0.16 if k % 4 == 0 else 0.0, 0.7); t += 0.27; k += 1
pluck(61, t_dip, 0.3, 0.9); pluck(49, t_dip, 0.25, 1.2)                           # the dip: one wrong note, and silence
for k in range(22): pluck(74 - k if k % 2 else 86 - k, EV['stampede'] + 0.1 + k * 0.085, 0.16, 0.25, 0.5 * (-1) ** k)      # the stampede: down the scale, fast
try: put('fx', load(os.path.join(SFX, 'stampede.wav')), EV['stampede'], 0.5)
except Exception as e_: print('sfx', e_)
put('fx', game('crowd_gasp'), t_dip + 0.25, 0.35); thud(t_dip, 0.25)
strings(57, CUE['n3c'][0] - 0.2, 1.8, 0.07, att=0.6); strings(64, CUE['n3c'][0] - 0.2, 1.8, 0.05, att=0.6)
# the duel: a low drone, timpani, punches
chord((38, 45, 50), t_du, t_r - t_du - 0.8, 0.14, bright=9); chord((62, 63), t_du + 0.6, EV['ko'] - t_du - 0.6, 0.045, att=1.5)
for k in range(int((EV['ko'] - t_du) / 0.62)): timp(t_du + 0.3 + k * 0.62, 38 if k % 2 == 0 else 45, 0.3 + 0.03 * k)
ph_ = game('punch_heavy'); sw = game('swing')
for t in EV['punches']: put('fx', ph_, t, 0.5); put('fx', sw, t - 0.2, 0.35)
put('fx', ph_, EV['ko'], 0.95); put('fx', ph_, EV['ko'] + 0.03, 0.8); boom(EV['ko'], 60, 1.4, 0.6); timp(EV['ko'], 38, 0.8); put('fx', game('unit_die'), EV['ko'] + 0.5, 0.5); thud(EV['ko'] + 1.3, 0.5); thud(EV['ko'] + 1.42, 0.45)
# the god candle: a rumble under a rising cluster, then the full chord, a choir, bells
rumble(t_r, t_e, 0.55)
for k, m in enumerate((50, 57, 62, 66, 69, 74)): strings(m, t_r + 0.4 * k, t_e - t_r - 0.4 * k - 0.1, 0.05 + 0.012 * k, att=1.5, rel=0.3)
boom(t_e, 40, 3.2, 1.2); boom(t_e + 0.03, 66, 1.8, 0.8); whoosh(t_e - 0.1, 1.6, 0.7)
try: put('fx', game('rocket_launch'), t_e, 0.7); put('fx', game('spell_pump'), t_e + 0.1, 0.7)
except Exception as e_: print('sfx', e_)
L_ = t_tug + 0.6 - t_e
chord((38, 50, 57, 62, 66, 69, 74), t_e, L_ - 0.4, 0.15, att=0.25, rel=0.25, bright=9)
for m in (62, 66, 69, 74, 78): choir(m, t_e + 0.1, L_ - 0.5 - 1.9, 0.11)
for k, m in enumerate((86, 90, 93, 98, 93, 90, 86, 81, 86, 90, 93, 98)): pluck(m, t_e + 1.4 + k * 0.33, 0.12, 1.2, 0.4 * (-1) ** k)
cheer = game('crowd_cheer'); put('fx', cheer[:int(min(len(cheer) / SR, t_tug + 1.5 - S['valley']['t0']) * SR)] * env([(0, 0), (0.6, 1), (t_tug + 0.6 - S['valley']['t0'], 1), (t_tug + 1.5 - S['valley']['t0'], 0)], int(min(len(cheer) / SR, t_tug + 1.5 - S['valley']['t0']) * SR))[:, None], S['valley']['t0'], 0.3)
for k in range(40): coin(S['valley']['t0'] + 0.8 + rng.uniform(0, t_tug - S['valley']['t0']), 0.07 + 0.06 * rng.random())
# the rug: two plucks for the tugs, everything stops; the pull is a whoosh into silence
for t in EV['tugs']: pluck(45, t, 0.5, 0.5); pluck(57, t, 0.3, 0.4); thud(t, 0.3)
whoosh(t_pull - 0.25, 1.1, 0.9); put('fx', sw, t_pull, 0.8); thud(t_pull + 0.05, 0.6)
for k in range(8): put('fx', sw, t_pull + 0.5 + 0.28 * k, 0.16, 0.5 * (-1) ** k)
for k in range(30): coin(t_pull + 0.4 + rng.uniform(0, 3.2), 0.05 + 0.05 * rng.random())
strings(49, t_pull + 0.8, t_fall - t_pull - 1.2, 0.09, att=2.0, rel=0.4, bright=4); strings(56, t_pull + 1.6, t_fall - t_pull - 2.0, 0.06, att=2.0, rel=0.4, bright=4)          # a held, uneasy fifth, falling away
# timber
x = np.arange(int((t_fall - EV['red'] - 0.2) * SR)) / SR; u = x / x[-1]; creak = np.sin(2 * np.pi * (140 - 90 * u) * x + 6 * np.sin(2 * np.pi * 17 * x)) * (0.3 + 0.7 * u) * 0.5; put('fx', mono(creak * np.clip(x / 0.3, 0, 1)), max(EV['red'], S['timber']['t0']), 0.22)
whoosh(t_fall - 0.9, 1.0, 0.8); boom(t_fall, 36, 3.4, 1.3); boom(t_fall + 0.02, 58, 2.0, 0.9)
for nm, g_ in (('hq_destroy', 0.9), ('tower_destroy', 0.8), ('house_stomp', 0.8)):
    try: put('fx', game(nm), t_fall, g_)
    except Exception as e_: print('sfx', nm, e_)
# "Excuse me." - a chair, steps, a door
try:
    put('fx', load(os.path.join(SFX, 'chair_scrape.wav')), EV['chair'], 0.9, -0.3)
    for k in range(5): thud(EV['chair'] + 0.55 + 0.17 * k, 0.16 * (1 - 0.12 * k))
    put('fx', load(os.path.join(SFX, 'door_slam.wav')), EV['door'], 0.8, -0.4)
except Exception as e_: print('sfx', e_)
# the Pepe again: the dawn chord comes back, quieter; the coin; the last chord under the card
chord((50, 57, 62, 66), t_pa + 0.2, T_CARD - t_pa - 0.4, 0.085, att=1.8); strings(74, t_pa + 1.2, T_CARD - t_pa - 2.0, 0.045, att=1.5)
coin(EV['bonk'], 0.45); thud(EV['bonk'], 0.35); coin(EV['bonk'] + 0.62, 0.12)
chord((38, 50, 57, 62, 66, 74), T_CARD + 0.1, END - T_CARD - 1.2, 0.14, att=0.5, rel=1.0); pluck(86, T_CARD + 0.15, 0.25, 1.5); pluck(90, T_CARD + 0.45, 0.2, 1.5); pluck(93, T_CARD + 0.75, 0.2, 1.8)
# mix: the music and the effects duck under the narrator
ve = np.abs(BUS['vo']).max(axis=1); k = int(0.12 * SR); ve = np.convolve((ve > 0.01).astype(np.float32), np.ones(k) / k, 'same'); ve = np.convolve(ve, np.ones(k * 3) / (k * 3), 'same'); v_ = np.clip(ve * 1.5, 0, 1)[:, None]; duck = 1 - 0.62 * v_; fxduck = 1 - 0.45 * v_
act = ve > 0.5
for k_ in BUS: print('bus', k_, 'rms while the narrator speaks: %.1f dB' % (20 * math.log10(float(np.sqrt((BUS[k_][act] ** 2).mean())) + 1e-9)))
mix = BUS['vo'] * 2.6 + BUS['mus'] * duck * 0.62 + BUS['fx'] * fxduck * 0.75 + BUS['amb'] * 1.5
fo = np.ones(n, np.float32); i0 = int((END - 1.0) * SR); fo[i0:int(END * SR)] = np.linspace(1, 0, int(END * SR) - i0); fo[int(END * SR):] = 0
mix = np.tanh(mix * fo[:, None] * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(END * SR)], SR)
print('MIX-DONE')
