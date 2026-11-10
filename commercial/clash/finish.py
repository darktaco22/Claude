"""Finish CLASH AT THE BRIDGE: python3 finish.py FRAMES_DIR OUT_DIR  -> OUT_DIR/c_####.png (1920x1080, 24 fps, 1488 frames) + mix.wav
The picture: an opening card, the graded 3D frames (bloom, warm grade, vignette, grain), the end card (logo, phone with real
gameplay, tagline). The sound: the game's own music, announcer stings, crowd and effects, a PA announcer (Kokoro), and
synthesized drums, risers and impacts."""
import os, sys, json, math, glob, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FR, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); AU = os.path.join(HERE, 'audio')
W, H, FPS, N3A, N3B, NF = 1920, 1080, 24, 37, 744, 840
ONLY = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
def font(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def rub(s, w=700):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
T_FIGHT, T_MEET, T_SLAM, T_TOWER, T_WIN = 15.0, 16.3, 23.6, 24.6, 27.4
THUNDER = [2.6, 14.4, 23.6, 28.6]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.34 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.25)[..., None]
def grade(a, t, f):
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum) * 1.18                                             # richer colour
    a = a * np.array([1.06, 0.99, 0.92], np.float32) + 0.05 * (1 - lum) ** 2 * np.array([-0.3, 0.15, 0.6], np.float32)   # orange lights, teal shadows
    a = np.clip((a - 0.02) * 1.1, 0, 1); a = a ** 1.06
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.8) / 0.2, 0, 1) * a
    hb = Image.fromarray((hi * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(9))
    a = a + np.asarray(hb.resize((W, H), Image.BILINEAR), np.float32) / 255.0 * 0.5
    fl = sum(max(0.0, 1 - abs(t - th - d) / 0.06) * w_ for th in THUNDER for d, w_ in ((0.0, 1.0), (0.17, 0.5), (0.29, 0.8)))      # lightning
    if fl > 0: a = a + fl * 0.16 * np.array([0.8, 0.88, 1.0], np.float32)
    fl = max(0.0, 1 - abs(t - T_TOWER - 0.03) / 0.09)
    if fl > 0: a = a + fl * 0.3 * np.array([1.0, 0.85, 0.6], np.float32)
    a = a * VIG
    return a + np.random.default_rng(f).normal(0, 0.012, (H, W, 1)).astype(np.float32)

BG = Image.open(os.path.join(A, 'bg_title_wide.jpg')).convert('RGB').resize((W, H), Image.LANCZOS)
BG = Image.fromarray((np.asarray(BG.filter(ImageFilter.GaussianBlur(5)), np.float32) * VIG ** 3 * np.array([0.42, 0.45, 0.62], np.float32)).astype(np.uint8))      # darker, cooler: the logo and the phone carry the card
LOGO = Image.open(os.path.join(A, 'logo.png')).convert('RGBA')
PH = None
def phone_frames():
    global PH
    if PH is None:
        d = os.path.join(OUT, 'phone'); os.makedirs(d, exist_ok=True)
        if not glob.glob(d + '/p_*.png'):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '1', '-i', os.path.join(HERE, '..', 'findyou', 'cap_gran_0123.mp4'), '-t', '5', '-vf', 'fps=24,scale=380:788:force_original_aspect_ratio=increase,crop=380:788', d + '/p_%03d.png'], check=True)
        PH = sorted(glob.glob(d + '/p_*.png'))
    return PH
def end_card(f):
    u = (f - N3B - 1) / FPS; im = BG.copy().convert('RGBA'); d = ImageDraw.Draw(im)
    a = ease(u / 0.5)
    k = 0.9 + 0.1 * ease(u / 0.6); lw = int(640 * k); lg = LOGO.resize((lw, int(lw * LOGO.height / LOGO.width)), Image.LANCZOS)
    if a < 1: lg.putalpha(lg.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(lg, (560 - lw // 2, 430 - lg.height // 2))
    # the phone, with the real game on it
    px, py, pw, ph_ = 1210, 120 + int(40 * (1 - ease(u / 0.7))), 420, 840
    d.rounded_rectangle((px, py, px + pw, py + ph_), 54, fill=(12, 12, 16, int(255 * a)), outline=(70, 70, 80, int(255 * a)), width=4)
    pf = phone_frames(); g = Image.open(pf[min(len(pf) - 1, int(u * FPS) % len(pf))]).convert('RGBA')
    m = Image.new('L', g.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, g.width, g.height), 36, fill=int(255 * a)); g.putalpha(m)
    im.alpha_composite(g, (px + 20, py + 26))
    if u > 0.9:
        b = ease((u - 0.9) / 0.5); d.text((560, 760), 'ENTER THE ARENA.', font=font(64), fill=(255, 255, 255, int(255 * b)), anchor='mm', stroke_width=5, stroke_fill=(10, 10, 30, int(255 * b)))
    if u > 1.6:
        b = ease((u - 1.6) / 0.5); d.rounded_rectangle((250, 850, 870, 934), 42, fill=(255, 214, 80, int(255 * b)))
        d.text((560, 892), 'PLAY FREE  ·  memeroyale.imaginestudio.fun', font=font(30), fill=(20, 10, 48, int(255 * b)), anchor='mm')
    return np.asarray(im.convert('RGB'), np.float32) / 255.0
def frame(f):
    t = (f - 1) / FPS
    if f < N3A:      # the opening card
        im = Image.new('RGB', (W, H), (0, 0, 0)); d = ImageDraw.Draw(im); a = min(1.0, t / 0.3, (1.45 - t) / 0.3)
        if t > 0.1 and a > 0:
            c = int(255 * max(0, a)); d.text((W / 2, H / 2 - 20), 'IMAGINE STUDIO', font=font(110), fill=(c, c, c), anchor='mm'); d.text((W / 2, H / 2 + 70), 'presents', font=rub(36, 500), fill=(int(c * 0.7),) * 3, anchor='mm')
        out = np.asarray(im, np.float32) / 255.0
    elif f <= N3B:
        a = np.asarray(Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGB').resize((W, H), Image.LANCZOS), np.float32) / 255.0
        out = grade(a, t, f)
        if f < N3A + 8: out = out * ((f - N3A + 1) / 8)                       # fade up
        if f > N3B - 5: out = out * ((N3B - f) / 5)                           # dip to the end card
    else: out = end_card(f)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, f'c_{f:04d}.png'))
for f in ([] if os.environ.get('SOUND_ONLY') else (ONLY or range(1, NF + 1))): frame(f)
print('FRAMES-DONE')
if ONLY: sys.exit(0)

# ================================================================ sound
SR = 48000; n = int(NF / FPS * SR) + SR; mix = np.zeros((n, 2), np.float32); rng = np.random.default_rng(23)
AU = os.path.join(HERE, '..', 'comeback', 'audio')
def load(name):
    p = os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3'))
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()
def put(x, t, g=1.0):
    i = int(t * SR); m = min(len(x), n - i)
    if m > 0: mix[i:i + m] += x[:m] * g
def seg(x, t0, t1): return x[int(t0 * SR):int(t1 * SR)]
def envelope(pts, length): return np.interp(np.arange(length) / SR, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)[:, None]
def mono(s): return np.stack([s, s], 1).astype(np.float32)
# music: a low drone and war drums for the stand-off; the game's OVERDOSE theme from the charge; the menu theme under the logo
tt = np.arange(int(15.2 * SR)) / SR
dr = (np.sin(2 * np.pi * 49 * tt) + 0.6 * np.sin(2 * np.pi * 73.4 * tt) + 0.35 * np.sin(2 * np.pi * 98 * tt + 0.4)) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.2 * tt))
put(mono(dr) * envelope([(0, 0), (1.5, 0.16), (13.5, 0.22), (15.0, 0.3), (15.2, 0)], len(tt)), 0.0)
def taiko(t, g=0.5, f0=80):
    x = np.arange(int(0.7 * SR)) / SR; s = np.sin(2 * np.pi * (f0 * x - 45 * x * x)) * np.exp(-x / 0.16) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.012) * 0.35
    put(mono(s), t, g)
def boom(t, f0=58, dur=1.8, g=0.9):
    x = np.arange(int(dur * SR)) / SR; s = np.sin(2 * np.pi * (f0 * x - 13 * x * x / dur)) * np.exp(-x / (dur * 0.35)) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.05) * 0.5
    put(mono(s), t, g)
def thunder(t, g=0.8):
    x = np.arange(int(3.2 * SR)) / SR; nz = rng.normal(0, 1, len(x)); k = np.cumsum(nz); k = k - np.convolve(k, np.ones(4000) / 4000, 'same'); k /= np.abs(k).max() + 1e-9
    s = k * (np.exp(-x / 0.9) + 0.4 * np.exp(-((x - 0.6) / 0.25) ** 2)) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.03) * 0.6
    put(mono(s), t, g)
def riser(t0, t1, g=0.5):
    x = np.arange(int((t1 - t0) * SR)) / SR; u = x / (t1 - t0); nz = rng.normal(0, 1, len(x)); k = nz - np.concatenate([[0], nz[:-1]]) * (1 - u)
    put(mono((k * 0.25 + np.sin(2 * np.pi * (90 * x + 200 * x * x / (t1 - t0))) * 0.5) * u ** 2), t0, g)
t = 4.5; i = 0
while t < 14.9:      # the march: a drum pattern that tightens
    taiko(t, 0.55 if i % 4 == 0 else 0.32, 78 if i % 4 == 0 else 96); t += 0.5 if t < 9.2 else (0.375 if t < 13.6 else 0.19); i += 1
for th in THUNDER: thunder(th + 0.05, 0.85 if th < 20 else 0.6)
riser(13.2, T_FIGHT, 0.5); riser(22.0, T_SLAM, 0.55)
mo = load('mus_overdose'); x = seg(mo, 6.0, 6.0 + 16.2); put(x * envelope([(0, 0.0), (0.05, 0.95), (7.0, 0.85), (9.6, 0.9), (12.4, 0.9), (14.6, 0.55), (16.2, 0.0)], len(x)), T_FIGHT)
mm = load('mus_menu'); x = seg(mm, 4.0, 4.0 + 5.0); put(x * envelope([(0, 0), (0.4, 0.75), (3.6, 0.75), (5.0, 0.0)], len(x)), 30.4)
# the crowd
def roar(src, length, dens=30):
    out = np.zeros((int(length * SR), 2), np.float32); L = len(src)
    for i in range(int(length * dens)):
        r = rng.uniform(0.7, 1.35); g = int(rng.uniform(0.5, 1.0) * L); s0 = rng.integers(0, L - g + 1); piece = src[s0:s0 + g]
        idx = (np.arange(int(len(piece) / r)) * r).astype(int); piece = piece[idx] * np.hanning(len(idx))[:, None]
        p0 = rng.integers(0, max(1, len(out) - len(piece))); pan = rng.uniform(0.3, 1.0)
        out[p0:p0 + len(piece), 0] += piece[:, 0] * pan; out[p0:p0 + len(piece), 1] += piece[:, 1] * (1.3 - pan)
    return out / max(1e-6, np.abs(out).max())
cheer = load('crowd_cheer'); ooh = load('crowd_ooh'); gasp = load('crowd_gasp')
bed = roar(cheer, 35, 34) * 0.7 + roar(ooh, 35, 10) * 0.3
put(bed * envelope([(0, 0), (1.2, 0), (2.0, 0.22), (4.5, 0.2), (7.0, 0.34), (9.2, 0.3), (12, 0.36), (14.0, 0.3), (T_FIGHT, 0.55), (T_MEET, 0.7), (22.4, 0.6), (23.0, 0.35), (T_SLAM, 0.4), (T_SLAM + 0.3, 0.9),
                         (T_TOWER, 1.0), (T_TOWER + 0.4, 1.3), (T_WIN, 1.0), (T_WIN + 0.5, 1.3), (30.6, 1.0), (31.4, 0.3), (32.5, 0.0), (36, 0)], len(bed)), 0.0)
for t_, s_, g in ((T_SLAM + 0.2, gasp, 1.2), (17.7, ooh, 0.8), (19.4, ooh, 0.8), (21.0, ooh, 0.8)): put(s_, t_, g)
# the game's own announcer and effects
for t_, name, g in ((1.6, 'vo_rumble', 0.9), (7.4, 'laugh_blast', 0.6), (T_FIGHT - 0.25, 'vo_fight', 1.3), (T_FIGHT + 0.1, 'charge_rush', 1.0), (T_MEET, 'punch_heavy', 1.0), (T_MEET + 0.1, 'swing', 0.8),
                    (16.7, 'swing', 0.7), (17.25, 'deploy_spell', 0.9), (17.5, 'punch_heavy', 0.9), (17.6, 'rocket_explode', 0.9), (17.6, 'unit_die', 0.7), (17.7, 'punch_heavy', 0.8), (18.5, 'swing', 0.7), (19.1, 'punch_heavy', 0.9),
                    (19.1, 'unit_die', 0.6), (19.3, 'punch_heavy', 1.0), (19.3, 'unit_die', 0.7), (19.8, 'punch_heavy', 0.9), (19.95, 'deploy_spell', 0.8), (20.3, 'rocket_explode', 0.7), (20.9, 'punch_heavy', 1.0), (20.9, 'unit_die', 0.7),
                    (T_SLAM - 0.05, 'whale_slam', 1.4), (T_SLAM, 'house_stomp', 1.0), (T_TOWER, 'tower_destroy', 1.5), (T_TOWER, 'rocket_explode', 1.1), (T_WIN + 0.2, 'vo_victory', 1.2), (T_WIN + 0.9, 'victory', 0.7), (25.4, 'level_up', 0.5)):
    try: put(load(name), t_, g)
    except Exception as e: print('sfx', name, e)
for t_ in (16.7, 17.6, 18.5, 19.4, 20.2, 16.6, 17.4, 18.2):      # steel on steel
    x = np.arange(int(0.35 * SR)) / SR; s_ = (np.sin(2 * np.pi * 2900 * x) + 0.6 * np.sin(2 * np.pi * 4350 * x) + 0.4 * np.sin(2 * np.pi * 6100 * x)) * np.exp(-x / 0.07) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.006)
    put(mono(s_), t_, 0.16)
boom(T_MEET, 60, 1.2, 0.7); boom(T_SLAM, 50, 2.2, 1.0); boom(T_TOWER, 58, 1.8, 0.9); boom(1.5, 46, 2.4, 0.6)
mix = np.tanh(mix * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(NF / FPS * SR)], SR)
print('MIX-DONE')
