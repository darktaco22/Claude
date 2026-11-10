"""Finish the stadium commercial: python3 finish.py FRAMES_DIR OUT_DIR  -> OUT_DIR/c_####.png (1920x1080, 24 fps, 1488 frames) + mix.wav
The picture: an opening card, the graded 3D frames (bloom, warm grade, vignette, grain), the end card (logo, phone with real
gameplay, tagline). The sound: the game's own music, announcer stings, crowd and effects, a PA announcer (Kokoro), and
synthesized drums, risers and impacts."""
import os, sys, json, math, glob, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FR, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); AU = os.path.join(HERE, 'audio')
W, H, FPS, N3A, N3B, NF = 1920, 1080, 24, 49, 1392, 1488
ONLY = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
def font(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def rub(s, w=700):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
T_C, T_T1, T_T2, T_T3, T_BOMB = 21.2, 24.9, 41.6, 47.3, 56.5
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.34 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.25)[..., None]
def grade(a, t, f):
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum) * 1.14                                             # richer colour
    a = a * np.array([1.05, 1.0, 0.93], np.float32) + 0.025 * (1 - lum) * np.array([-0.2, 0.1, 0.5], np.float32)   # warm lights, cool shadows
    a = np.clip((a - 0.015) * 1.05, 0, 1)
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.8) / 0.2, 0, 1) * a
    hb = Image.fromarray((hi * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(9))
    a = a + np.asarray(hb.resize((W, H), Image.BILINEAR), np.float32) / 255.0 * 0.38
    for tb, col in ((T_C, (0.5, 1.0, 0.5)), (T_T1, (1.0, 0.85, 0.6)), (T_T2, (1.0, 0.85, 0.6)), (T_T3, (1.0, 0.9, 0.5))):   # a flash on each hit
        fl = max(0.0, 1 - abs(t - tb - 0.03) / 0.09)
        if fl > 0: a = a + fl * 0.35 * np.array(col, np.float32)
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
        b = ease((u - 0.9) / 0.5); d.text((560, 760), "It's not over until it's over.", font=font(64), fill=(255, 255, 255, int(255 * b)), anchor='mm', stroke_width=5, stroke_fill=(10, 10, 30, int(255 * b)))
    if u > 1.6:
        b = ease((u - 1.6) / 0.5); d.rounded_rectangle((250, 850, 870, 934), 42, fill=(255, 214, 80, int(255 * b)))
        d.text((560, 892), 'PLAY FREE  ·  memeroyale.imaginestudio.fun', font=font(30), fill=(20, 10, 48, int(255 * b)), anchor='mm')
    return np.asarray(im.convert('RGB'), np.float32) / 255.0
def frame(f):
    t = (f - 1) / FPS
    if f < N3A:      # the opening card
        im = Image.new('RGB', (W, H), (0, 0, 0)); d = ImageDraw.Draw(im); a = min(1.0, t / 0.4, (2.0 - t) / 0.4)
        if t > 0.25 and a > 0:
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
SR = 48000; n = int(NF / FPS * SR) + SR; mix = np.zeros((n, 2), np.float32); rng = np.random.default_rng(11)
def load(name):
    p = os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3'))
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()
def put(x, t, g=1.0, pan=0.0):
    i = int(t * SR)
    if i < 0: x = x[-i:]; i = 0
    m = min(len(x), n - i)
    if m > 0: mix[i:i + m, 0] += x[:m, 0] * g * (1 - max(0, pan)); mix[i:i + m, 1] += x[:m, 1] * g * (1 + min(0, pan))
def fade(x, a=0.02, b=0.05):
    x = x.copy(); na, nb = int(a * SR), int(b * SR)
    if na: x[:na] *= np.linspace(0, 1, na)[:, None]
    if nb: x[-nb:] *= np.linspace(1, 0, nb)[:, None]
    return x
def seg(x, t0, t1): return x[int(t0 * SR):int(t1 * SR)]
def envelope(pts, length):      # pts [(t, gain)] -> per-sample gain
    ts = np.arange(length) / SR; return np.interp(ts, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)[:, None]
# --- music: the game's battle theme while red runs away with it; silence under the candle; the game's OVERDOSE theme for the comeback
mb = load('mus_battle'); mo = load('mus_overdose'); mm = load('mus_menu')
x = seg(mb, 20.0, 20.0 + 19.6); put(x * envelope([(0, 0), (2.0, 0), (3.2, 0.55), (17.0, 0.5), (19.0, 0.28), (19.6, 0.0)], len(x)), 0.0)
x = seg(mo, 6.0, 6.0 + 37.0); put(x * envelope([(0, 0.0), (0.05, 0.9), (4.0, 0.8), (26.0, 0.85), (33.0, 0.8), (35.3, 0.5), (37.0, 0.0)], len(x)), T_C)
x = seg(mm, 4.0, 4.0 + 5.2); put(x * envelope([(0, 0), (0.4, 0.75), (3.6, 0.75), (5.2, 0.0)], len(x)), 57.6)
# --- the crowd: a continuous roar granulated from the game's own crowd sounds, swelling with the story
def roar(src, length, dens=30):
    out = np.zeros((int(length * SR), 2), np.float32); L = len(src)
    for i in range(int(length * dens)):
        r = rng.uniform(0.7, 1.35); g = int(rng.uniform(0.5, 1.0) * L); s0 = rng.integers(0, L - g + 1); piece = src[s0:s0 + g]
        idx = (np.arange(int(len(piece) / r)) * r).astype(int); piece = piece[idx] * np.hanning(len(idx))[:, None]
        p0 = rng.integers(0, max(1, len(out) - len(piece))); pan = rng.uniform(0.3, 1.0)
        out[p0:p0 + len(piece), 0] += piece[:, 0] * pan; out[p0:p0 + len(piece), 1] += piece[:, 1] * (1.3 - pan)
    return out / max(1e-6, np.abs(out).max())
cheer = load('crowd_cheer'); ooh = load('crowd_ooh'); boo = load('crowd_boo'); gasp = load('crowd_gasp'); laugh = load('crowd_laugh')
bed = roar(cheer, 62, 34) * 0.7 + roar(ooh, 62, 10) * 0.3
put(bed * envelope([(0, 0), (1.6, 0), (2.4, 0.5), (8, 0.42), (15, 0.34), (19.0, 0.3), (19.4, 0.12), (T_C, 0.1), (T_C + 0.5, 0.42), (T_T1, 0.5), (T_T1 + 0.4, 0.8), (29, 0.55), (35, 0.5),
                         (T_T2 - 2.5, 0.42), (T_T2, 0.4), (T_T2 + 0.4, 0.95), (45, 0.7), (T_T3, 0.75), (T_T3 + 0.3, 1.25), (52.3, 1.0), (52.6, 0.4), (56.3, 0.35), (56.6, 0.8), (58.0, 0.5), (59.0, 0.0), (63, 0)], len(bed)), 0.0)
for t, s, g in ((12.2, laugh, 0.9), (8.2, laugh, 0.5), (16.4, boo, 0.6), (17.6, boo, 0.5), (T_C + 0.15, gasp, 1.3), (T_T1 + 0.2, gasp, 0.9), (27.8, gasp, 1.0), (28.3, ooh, 0.8), (T_T2 + 0.3, ooh, 0.9), (56.7, gasp, 1.1), (57.1, laugh, 1.0)):
    put(s, t, g)
# --- the game's effects and announcer
for t, name, g in ((2.2, 'vo_rumble', 0.9), (6.2, 'tower_hit', 0.5), (6.9, 'tower_hit', 0.45), (8.0, 'laugh_blast', 0.5), (19.1, 'deploy_spell', 0.9), (T_C - 0.35, 'spell_pump', 1.2), (T_C, 'rocket_explode', 1.3), (T_C + 0.1, 'unit_die', 0.7),
                   (21.55, 'deploy_drop', 0.8), (21.8, 'deploy_drop', 0.7), (22.4, 'charge_rush', 1.0), (24.0, 'punch_heavy', 0.7), (24.4, 'swing', 0.7), (T_T1, 'tower_destroy', 1.4), (T_T1, 'rocket_explode', 0.9),
                   (35.6, 'deploy_drop', 0.9), (35.3, 'vo_overtime', 0.9), (36.3, 'charge_rush', 0.9), (37.9, 'whale_slam', 1.0), (38.0, 'unit_die', 0.7), (41.2, 'whale_slam', 1.2), (T_T2, 'tower_destroy', 1.4), (T_T2, 'rocket_explode', 0.9),
                   (46.4, 'punch_heavy', 0.8), (46.8, 'swing', 0.8), (T_T3, 'hq_destroy', 1.5), (T_T3, 'rocket_explode', 1.1), (48.3, 'vo_victory', 1.1), (48.9, 'victory', 0.7), (T_BOMB, 'acorn_boom', 1.3), (T_BOMB, 'rocket_explode', 0.6),
                   (25.7, 'level_up', 0.6), (42.5, 'level_up', 0.6), (48.0, 'level_up', 0.6)):
    try: put(load(name), t, g)
    except Exception as e: print('sfx', name, e)
# --- the PA announcer: band-passed with a short stadium slap
def pa(x):
    m = x.mean(axis=1); X = np.fft.rfft(m); fr = np.fft.rfftfreq(len(m), 1 / SR); X *= (1 / (1 + (300 / np.maximum(fr, 1)) ** 4)) * (1 / (1 + (fr / 3800) ** 4)); m = np.fft.irfft(X, len(m)).astype(np.float32)
    m = np.tanh(m * 2.2) * 0.6; out = np.zeros((len(m) + SR, 2), np.float32)
    for d_, g, pn in ((0.0, 1.0, 0.5), (0.11, 0.35, 0.2), (0.23, 0.22, 0.8), (0.41, 0.12, 0.4)):
        i = int(d_ * SR); out[i:i + len(m), 0] += m * g * pn * 2; out[i:i + len(m), 1] += m * g * (1 - pn) * 2
    return out
for t, name, g in ((3.1, 'an_two', 1.0), (16.2, 'an_exits', 0.9), (19.5, 'an_wait', 1.0), (21.75, 'an_candle', 1.25), (25.9, 'an_game', 1.1), (36.5, 'an_whale', 1.05), (42.6, 'an_tied', 1.1), (49.6, 'an_done', 1.15)):
    put(pa(load(name)), t, g)
put(load('an_tag'), 58.5, 1.25)
# --- synthesized: sub impacts, taiko, risers, a spark fizz
def boom(t, f0=62, dur=1.6, g=0.9):
    x = np.arange(int(dur * SR)) / SR; s = np.sin(2 * np.pi * (f0 * x - 14 * x * x / dur)) * np.exp(-x / (dur * 0.35)); s += rng.normal(0, 1, len(x)) * np.exp(-x / 0.05) * 0.5
    put(np.stack([s, s], 1).astype(np.float32), t, g)
def taiko(t, g=0.5, f0=95):
    x = np.arange(int(0.5 * SR)) / SR; s = np.sin(2 * np.pi * (f0 * x - 60 * x * x)) * np.exp(-x / 0.12) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.012) * 0.4
    put(np.stack([s, s], 1).astype(np.float32), t, g)
def riser(t0, t1, g=0.5):
    x = np.arange(int((t1 - t0) * SR)) / SR; u = x / (t1 - t0); nz = rng.normal(0, 1, len(x)); k = np.cumsum(nz) ; k = nz - np.concatenate([[0], nz[:-1]]) * (1 - u)   # brightening noise
    s = (k * 0.25 + np.sin(2 * np.pi * (110 * x + 220 * x * x / (t1 - t0) / 2 * 3)) * 0.5) * u ** 2
    put(np.stack([s, s], 1).astype(np.float32), t0, g)
for t in (T_C, T_T1, T_T2, T_T3): boom(t)
boom(T_BOMB, 80, 0.9, 0.6); boom(2.0, 50, 2.2, 0.7)
shots = json.load(open(os.path.join(HERE, 'shots.json')))
for s_ in shots:
    if 6 <= s_['t0'] < 19: taiko(s_['t0'], 0.45)
for i in range(16): taiko(39.0 + i * (T_T2 - 39.0) / 16 * (1 - 0.012 * i), 0.3 + 0.02 * i, 85 + 3 * i)   # the slow-motion slam: accelerating drums
riser(19.0, T_C, 0.55); riser(39.2, T_T2, 0.45); riser(45.2, T_T3, 0.5)
x = np.arange(int((T_BOMB - 52.9) * SR)) / SR; fz = rng.normal(0, 1, len(x)) * (0.5 + 0.5 * np.sin(2 * np.pi * 37 * x)) * 0.07; fz = fz - np.concatenate([[0], fz[:-1]]) * 0.9
put(np.stack([fz, fz], 1).astype(np.float32), 52.9, 1.0)
mix = np.tanh(mix * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(NF / FPS * SR)], SR)
print('MIX-DONE')
