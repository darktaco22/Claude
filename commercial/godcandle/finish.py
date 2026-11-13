"""Finish GOD CANDLE:  python3 finish.py FRAMES_DIR OUT_DIR [first last]  ->  OUT_DIR/c_####.png (1920x1080, 2.35:1 letterbox, 24 fps) + mix.wav
The picture: the graded 3D frames (bloom, anamorphic streaks, warm/teal grade, vignette, grain), flashes and a chromatic-aberration / zoom punch on
the big moments (the candle leaving the phone, the ceiling, the cut to the sky, the slam), and the title card.
The sound: the game's own music, crowd, impacts and announcer-free stings plus synthesized taps, a cash register, risers, whooshes and booms."""
import os, sys, json, math, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FR, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); AU = os.path.join(HERE, '..', 'comeback', 'audio')
E = json.load(open(os.path.join(HERE, 'edl.json'))); SHOTS = E['shots']; FPS = 24; NFILM = E['last']; HOLD = 40; NF = NFILM + HOLD
T_SWAP, T_CEIL, T_FLASH, T_DROP, T_IMP = E['t_swap'], E['t_ceil'], E['t_flash'], E['t_drop'], E['t_imp']; T_SP0, UA, UB = E.get('t_sp0', T_FLASH + 0.05), E.get('ua', 1.083), E.get('ub', 1.983)
W, H = 1920, 1080; CH = 816; Y0 = (H - CH) // 2
ONLY = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
def font(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def rub(s, w=600):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def anim(t):
    s = next((x for x in SHOTS if x['t0'] <= t < x['t1']), None)
    if s is None: return None
    u = (t - s['t0']) / (s['t1'] - s['t0']); return s['a0'] + (t - s['t0']) * (s['s0'] + (s['s1'] - s['s0']) * u * 0.5)
FT = [(f, anim((f - 1) / FPS)) for f in range(1, NFILM + 1)]
def fts(a):
    """Every film time (seconds) that shows animation time a."""
    out = []
    for (f0, a0), (f1, a1) in zip(FT, FT[1:]):
        if a0 is not None and a1 is not None and a1 >= a0 and a0 <= a < a1 and a1 - a0 < 1.0: out.append(((f0 - 1) + (a - a0) / (a1 - a0)) / FPS)
    return out
def ft(a, d=None): r = fts(a); return r[0] if r else d
def cut_times():
    return [s['t0'] for s in SHOTS]
# ---------------------------------------------------------------- picture
yy, xx = np.mgrid[0:CH, 0:W].astype(np.float32)
RR = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - CH / 2) / (CH / 2)) ** 2
VIG = (1 - 0.38 * RR ** 1.25)[..., None]
T_EV = dict(swap=ft(T_SWAP, -9), ceil=ft(T_CEIL, -9), imp=ft(T_IMP, -9), flash=min(cut_times(), key=lambda c: abs(c - (ft(T_DROP - 0.01, -9) or -9))) if ft(T_DROP - 0.01) else -9,
            space=min(cut_times(), key=lambda c: abs(c - (ft(T_FLASH - 0.01, -9) or -9))) if ft(T_FLASH - 0.01) else -9)   # 'space' = the smash cut out of the sky, 'flash' = the cut back into the fall
def bump(t, t0, dur): return max(0.0, 1 - abs(t - t0) / dur) if dur > 0 else 0.0
def decay(t, t0, dur): return max(0.0, 1 - (t - t0) / dur) if t >= t0 else 0.0
def punch(a, k, cx=0.5, cy=0.5):
    """Zoom in by k (>=1) around the centre."""
    if k <= 1.0005: return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)); w, h = im.size; nw, nh = w / k, h / k
    return np.asarray(im.crop((int((w - nw) * cx), int((h - nh) * cy), int((w - nw) * cx + nw), int((h - nh) * cy + nh))).resize((w, h), Image.BILINEAR), np.float32) / 255.0
def aberrate(a, px):
    if px < 0.5: return a
    r = np.roll(a[..., 0], int(px), axis=1); b = np.roll(a[..., 2], -int(px), axis=1); return np.stack([r, a[..., 1], b], axis=2)
def radial_blur(a, k):
    if k < 0.01: return a
    acc = a.copy(); n = 1
    for s in (1.015, 1.03, 1.05, 1.075):
        acc += punch(a, 1 + (s - 1) * k * 6); n += 1
    return acc / n
def grade(a, t, f):
    lum = a.mean(axis=2, keepdims=True); a = lum + (a - lum) * 1.14
    a = a * np.array([1.05, 1.0, 0.95], np.float32) + 0.05 * (1 - lum) ** 2 * np.array([-0.3, 0.12, 0.55], np.float32)
    a = np.clip((a - 0.02) * 1.1, 0, 1) ** 1.05
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.78) / 0.22, 0, 1) * a
    hb = Image.fromarray((hi * 255).astype(np.uint8)).resize((W // 4, CH // 4), Image.BILINEAR)
    b1 = np.asarray(hb.filter(ImageFilter.GaussianBlur(9)).resize((W, CH), Image.BILINEAR), np.float32) / 255.0
    st = np.asarray(hb.resize((W // 16, CH // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, CH), Image.BILINEAR), np.float32) / 255.0   # anamorphic streak: wide horizontal blur
    a = a + b1 * 0.5 + st * np.array([0.25, 0.5, 0.3], np.float32) * 0.9
    return a
def frame(f):
    t = (f - 1) / FPS
    if f <= NFILM:
        src = Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGB').resize((W, CH), Image.LANCZOS); a = np.asarray(src, np.float32) / 255.0
    else:
        src = Image.open(os.path.join(FR, f'f_{NFILM:04d}.png')).convert('RGB').resize((W, CH), Image.LANCZOS); a = np.asarray(src, np.float32) / 255.0
        a = a * (1 - 0.55 * ease((f - NFILM) / 14.0))
    # camera punches and aberration on the big moments
    k = 1.0; ab = 0.0; fl = 0.0; col = np.array([1.0, 1.0, 1.0], np.float32); rb = 0.0
    d = decay(t, T_EV['swap'], 0.5); k += 0.06 * d; ab += 10 * d; fl = max(fl, 0.5 * decay(t, T_EV['swap'], 0.25)); col = np.array([0.6, 1.0, 0.7], np.float32) if d > 0 else col
    d = decay(t, T_EV['ceil'], 0.5); k += 0.05 * d; ab += 8 * d; fl = max(fl, 0.35 * decay(t, T_EV['ceil'], 0.2))
    fc = T_EV['flash']
    if fc > 0: fl = max(fl, 0.9 * bump(t, fc, 0.14))
    sc_ = T_EV['space']
    if sc_ > 0: fl = max(fl, 1.0 * bump(t, sc_, 0.16)); d = decay(t, sc_, 0.35); k += 0.05 * d; ab += 10 * d
    d = decay(t, T_EV['imp'], 1.1); k += 0.12 * d * d; ab += 22 * d * d; fl = max(fl, 1.0 * decay(t, T_EV['imp'] - 0.01, 0.35) ** 1.5); rb = 0.7 * d * d; col = np.array([0.75, 1.0, 0.8], np.float32) if d > 0.7 else col
    if k > 1: a = punch(a, k)
    a = radial_blur(a, rb); a = aberrate(a, ab)
    eb = 0.0                                                     # soft edges while it falls (and a little after): the eye stays on the candle and the arena
    if T_EV['flash'] > 0 and T_EV['flash'] <= t < T_EV['imp']: eb = 1.0
    elif t >= T_EV['imp'] > 0: eb = 0.45
    if eb > 0:
        bl = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)), np.float32) / 255.0
        mk = np.clip((RR - 0.22) * 1.25, 0, 1)[..., None] * eb; a = a * (1 - mk) + bl * mk
    a = grade(a, t, f)
    if fl > 0: a = a * (1 - min(1, fl)) + col * min(1, fl) * 1.25
    a = a * VIG
    a = a + np.random.default_rng(f).normal(0, 0.011, (CH, W, 1)).astype(np.float32)
    canvas = np.zeros((H, W, 3), np.float32); canvas[Y0:Y0 + CH] = a
    im = Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8))
    if f > NFILM - 6:       # the title
        u = (f - (NFILM - 6)) / 22.0; k_ = ease(u); d = ImageDraw.Draw(im, 'RGBA'); s = int(150 * (1.18 - 0.18 * k_))
        glowl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glowl); gd.text((W / 2, H / 2 + 20), 'GOD CANDLE', font=font(s), fill=(60, 255, 120, int(210 * k_)), anchor='mm')
        glowl = glowl.filter(ImageFilter.GaussianBlur(22)); im = Image.alpha_composite(im.convert('RGBA'), glowl).convert('RGB'); d = ImageDraw.Draw(im, 'RGBA')
        d.text((W / 2, H / 2 + 20), 'GOD CANDLE', font=font(s), fill=(235, 255, 235, int(255 * k_)), anchor='mm', stroke_width=5, stroke_fill=(10, 60, 24, int(255 * k_)))
        if u > 0.6: d.text((W / 2, H / 2 + 130), 'MEME ROYALE', font=rub(40, 700), fill=(180, 255, 200, int(255 * ease((u - 0.6) / 0.4))), anchor='mm')
    im.save(os.path.join(OUT, f'c_{f:04d}.png'))
for f in ([] if os.environ.get('SOUND_ONLY') else (ONLY or range(1, NF + 1))): frame(f)
print('FRAMES-DONE')
if ONLY: sys.exit(0)

# ---------------------------------------------------------------- sound
SR = 48000; n = int(NF / FPS * SR) + SR; mix = np.zeros((n, 2), np.float32); rng = np.random.default_rng(23)
def load(name):
    p = os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3'))
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()
def put(x, t, g=1.0):
    i = int(t * SR); m = min(len(x), n - i)
    if m > 0 and i >= 0: mix[i:i + m] += x[:m] * g
def seg(x, t0, t1): return x[int(t0 * SR):int(t1 * SR)]
def envelope(pts, length): return np.interp(np.arange(length) / SR, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)[:, None]
def mono(s): return np.stack([s, s], 1).astype(np.float32)
def lowpass(x, k): return np.convolve(x, np.ones(k) / k, 'same')
def tap(t, g=0.5):
    x = np.arange(int(0.08 * SR)) / SR; s = (np.sin(2 * np.pi * 1700 * x) * np.exp(-x / 0.012) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.004) * 0.5); put(mono(s), t, g)
def ding(t, g=0.4):
    x = np.arange(int(0.9 * SR)) / SR; s = (np.sin(2 * np.pi * 1318 * x) + 0.6 * np.sin(2 * np.pi * 1975 * x) + 0.3 * np.sin(2 * np.pi * 2637 * x)) * np.exp(-x / 0.25); put(mono(s), t, g)
def boom(t, f0=55, dur=2.0, g=0.9):
    x = np.arange(int(dur * SR)) / SR; s = np.sin(2 * np.pi * (f0 * x - 12 * x * x / dur)) * np.exp(-x / (dur * 0.35)) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.05) * 0.5; put(mono(s), t, g)
def riser(t0, t1, g=0.5, f0=90, f1=1400):
    x = np.arange(int((t1 - t0) * SR)) / SR; u = x / (t1 - t0); ph = 2 * np.pi * (f0 * x + (f1 - f0) * x * x / (2 * (t1 - t0))); nz = rng.normal(0, 1, len(x)); k = nz - np.concatenate([[0], nz[:-1]]) * (1 - u)
    put(mono((k * 0.25 + np.sin(ph) * 0.5) * u ** 2), t0, g)
def whoosh(t, dur=1.0, g=0.4, up=True):
    x = np.arange(int(dur * SR)) / SR; u = x / dur; nz = rng.normal(0, 1, len(x)); k = lowpass(nz, 120) * 12; env = np.sin(np.pi * (u if up else u)) ** 2; put(mono(k * env + 0.25 * np.sin(2 * np.pi * (80 + 300 * u) * x) * env), t, g)
def crash(t, g=0.7):
    x = np.arange(int(1.4 * SR)) / SR; s = rng.normal(0, 1, len(x)) * np.exp(-x / 0.25) + np.sin(2 * np.pi * 70 * x) * np.exp(-x / 0.2); put(mono(s), t, g)
def coin(t, g=0.2):
    x = np.arange(int(0.5 * SR)) / SR; f = rng.uniform(2200, 3600); s = (np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 1.5 * x)) * np.exp(-x / 0.09); put(mono(s), t, g)
END = NF / FPS
# the room at 3 AM: a hum, a distant city, a fridge; a lo-fi pulse that builds
tt = np.arange(int(END * SR)) / SR; hum = (np.sin(2 * np.pi * 55 * tt) + 0.4 * np.sin(2 * np.pi * 110 * tt)) * 0.05; put(mono(hum) * envelope([(0, 0), (0.3, 1), (ft(T_SWAP, 4) - 0.1, 1), (ft(T_SWAP, 4), 0.2), (END, 0.0)], len(tt)), 0.0)
mm = load('mus_menu'); x = seg(mm, 3.0, 3.0 + (ft(T_SWAP, 4)) + 1.0); put(x * envelope([(0, 0), (0.8, 0.35), (len(x) / SR - 1.0, 0.35), (len(x) / SR, 0.0)], len(x)), 0.0)
for a_ in (1.0, 1.65, 2.2):
    for x_ in fts(a_)[:1]: tap(x_, 0.5)
for x_ in fts(2.55)[:1]: ding(x_, 0.45); ding(x_ + 0.12, 0.3)                 # the order goes through
t_sw = ft(T_SWAP, 4.0)
riser(ft(2.7, t_sw - 0.8), t_sw, 0.7, 120, 2400)                               # the chart goes parabolic
boom(t_sw, 48, 2.4, 1.0); crash(t_sw, 0.45); whoosh(t_sw, 1.2, 0.5)           # it leaves the screen
t_ce = ft(T_CEIL, t_sw + 1.2); crash(t_ce, 0.9); boom(t_ce, 62, 1.8, 0.8)      # through the ceiling
whoosh(ft(4.5, t_sw + 1.0), 1.6, 0.6); riser(ft(4.5, t_sw + 1.0), ft(T_FLASH - 0.02, t_sw + 2.5), 0.5, 140, 3200)
t_sp = ft(T_FLASH - 0.01, t_sw + 2.6); t_fl = ft(T_DROP - 0.01, t_sp + 3.5)         # t_sp: the smash cut into space, t_fl: the cut back into the fall (the music starts there)
boom(t_sp, 40, 2.4, 0.9)                                                                   # the riser ends on a hit, then silence and a low hum
xs = np.arange(int((t_fl - t_sp) * SR)) / SR; hum_ = (np.sin(2 * np.pi * 55 * xs) + 0.6 * np.sin(2 * np.pi * 82.4 * xs) + 0.05 * np.sin(2 * np.pi * 1320 * xs) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * xs))) * 0.11
put(mono(hum_) * envelope([(0, 0), (0.25, 1), (len(xs) / SR - 0.5, 1), (len(xs) / SR, 0.3)], len(xs)), t_sp)
whoosh(t_sp + 0.05, 0.9, 0.3, up=False)
for x_ in fts(T_SP0 + UA)[:1]: ding(x_, 0.22)                                              # the apex: a soft chime as it floats
riser(ft(T_SP0 + UB, t_fl - 1.0), t_fl, 0.5, 80, 1500)                                      # it tips over and the fall builds
mo = load('mus_overdose'); L_ = END - t_fl; x = seg(mo, 6.0, 6.0 + L_)
put(x * envelope([(0, 0.0), (0.05, 0.9), (L_ - 12, 0.8), (L_ - 6, 0.55), (L_, 0.3)], len(x)), t_fl)                                           # the music kicks in at the cut to the sky
cheer = load('crowd_cheer'); gasp = load('crowd_gasp'); ooh = load('crowd_ooh')
whoosh(t_fl, 1.4, 0.7)
put(gasp, ft(T_DROP + 1.2, t_fl + 2.0), 0.9)
t_im = ft(T_IMP, END - 6)
riser(t_im - 2.2, t_im, 0.55, 100, 1800)
for a_ in (T_DROP + 0.2, T_DROP + 1.0, T_DROP + 1.8, T_DROP + 2.5):
    for x_ in fts(a_)[:1]: whoosh(x_, 0.7, 0.35)
boom(t_im, 38, 3.4, 1.3); boom(t_im + 0.02, 62, 2.0, 0.9); crash(t_im, 1.0)
for nm, g_ in (('rocket_explode', 1.0), ('tower_destroy', 0.9), ('hq_destroy', 0.8), ('whale_slam', 1.0), ('house_stomp', 0.9)):
    try: put(load(nm), t_im, g_)
    except Exception as e: print('sfx', nm, e)
for i in range(46): coin(t_im + 0.5 + rng.uniform(0, 2.6), 0.14 + 0.1 * rng.random())
x = cheer; put(x * envelope([(0, 0), (0.4, 1), (len(x) / SR - 0.5, 1), (len(x) / SR, 0)], len(x)), t_im + 1.4, 0.8); put(ooh, t_im + 0.3, 0.7)
boom(END - 3.0, 44, 2.6, 0.7)
# a duck on the music at the impact so the boom lands
mix = np.tanh(mix * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(NF / FPS * SR)], SR)
print('MIX-DONE')
