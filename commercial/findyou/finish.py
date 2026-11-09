"""I WILL FIND YOU: subtitles, the montage's day cards, the full-screen RUG PULL insert (real gameplay), the end card,
and the sound: Kokoro voices, a synthesized thriller score (drone, hits, thunder) and the game's own music and sounds.
python3 finish.py FRAMES_DIR CAP_GRAN_DIR OUT_DIR    (FRAMES_DIR: f_####.png from the render; frames 991-1080 come from the capture)"""
import os, sys, json, math, glob, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); AU = os.path.join(HERE, 'audio')
FR, CG, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
W, H = 720, 1280; FPS = 30; N3D = 1128; END = 1218
VO = json.load(open(os.path.join(AU, 'vo', 'lines.json')))
LINES = [('n_who', 5.0), ('n_sol', 7.0), ('n_cards', 9.9), ('n_season', 13.9), ('n_find', 17.6), ('n_copium', 20.4),
         ('g_hello', 31.0), ('g_rug', 36.3)]
THUNDER = [1.8, 9.6, 17.3, 26.2, 28.6]
def font(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def serif(s):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, s)
    return font(s)
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        nx = (cur + ' ' + w).strip()
        if d.textlength(nx, font=f) > maxw and cur: lines.append(cur); cur = w
        else: cur = nx
    return lines + [cur]
G = sorted(glob.glob(os.path.join(CG, 'f_*.png')))
LOGO = Image.open(os.path.join(A, 'logo.png')).convert('RGBA')
# ---- the look: a cold thriller grade for the hunt, a warm one for Sunny Acres; lightning; vignette; film grain
_yy, _xx = np.mgrid[0:H, 0:W]; VIG = 1 - 0.38 * (((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.6)) ** 2)
VIG = np.clip(VIG, 0.45, 1.0)[..., None].astype(np.float32)
def grade(a, t, f):
    insert = 991 <= f <= 1080; end = f > N3D
    if end or insert: return a
    if t < 30.0:      # teal shadows, a little crushed
        lum = a.mean(axis=2, keepdims=True)
        a = a * np.array([0.92, 1.0, 1.06], np.float32) + (0.04 * (1 - lum)) * np.array([-0.4, 0.3, 0.6], np.float32)
        a = np.clip((a - 0.02) * 1.06, 0, 1)
        flash = sum(max(0.0, 1 - abs(t - th - d) / 0.06) * w for th in THUNDER for d, w in ((0.0, 1.0), (0.18, 0.55), (0.3, 0.75)))
        if flash > 0: a = a + flash * 0.22 * np.array([0.85, 0.9, 1.0], np.float32)
    else:             # warm afternoon
        a = a * np.array([1.05, 1.0, 0.92], np.float32)
    # bloom: the monitor, the RGB strip, the window and the lightning bleed a soft glow into the frame
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.85) / 0.15, 0, 1) * a
    hb = Image.fromarray((hi * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
    a = a + np.asarray(hb.resize((W, H), Image.BILINEAR), np.float32) / 255.0 * 0.3
    a = a * VIG
    g = np.random.default_rng(f).normal(0, 0.018, (H, W, 1)).astype(np.float32)
    return a + g

def frame(f):
    t = (f - 1) / FPS
    if 991 <= f <= 1080:      # Grandma's phone, full screen: the real game, her RUG PULL on NEET's push
        g = Image.open(G[max(0, min(len(G) - 1, (f - 1) - 900 + 20))]).convert('RGB')
        k = 1.0 + 0.06 * ease((t - 33.0) / 3.0); w, h = int(W * k), int(H * k)
        base = g.resize((w, h), Image.LANCZOS).crop(((w - W) // 2, (h - H) // 2, (w - W) // 2 + W, (h - H) // 2 + H)).convert('RGBA')
    elif f <= N3D: base = Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGBA')
    else: base = Image.new('RGBA', (W, H), (8, 6, 14, 255))
    d = ImageDraw.Draw(base)
    if f <= N3D:
        for i, t0 in LINES:
            if t0 <= t < t0 + VO[i]['dur'] + 0.3:
                f_ = serif(36) if VO[i]['who'] == 'neet' else font(40)
                col = (235, 235, 240) if VO[i]['who'] == 'neet' else (255, 220, 150)
                lines = wrap(d, VO[i]['text'], f_, W - 100)
                for j, ln in enumerate(lines):
                    d.text((W / 2, H - 210 + j * 48 - (len(lines) - 1) * 48), ln, font=f_, fill=col, stroke_width=4, stroke_fill=(5, 5, 8), anchor='mm')
        # the montage: the case's day cards, typewriter style
        for t0, t1, txt in ((22.4, 24.0, 'DAY 1'), (24.0, 25.4, 'DAY 4'), (25.4, 27.0, 'DAY 9'), (27.0, 30.0, 'DAY 12 · 2:14 AM')):
            if t0 <= t < t1:
                n = int(len(txt) * min(1, (t - t0) / 0.4)); d.text((52, 110), txt[:n], font=serif(44), fill=(240, 240, 240), stroke_width=3, stroke_fill=(0, 0, 0))
        if 30.0 <= t < 31.6:
            a = int(255 * (1 - ease((t - 31.1) / 0.5)))
            d.text((52, 110), 'SUNNY ACRES · 3:00 PM', font=serif(40), fill=(255, 255, 255, a), stroke_width=3, stroke_fill=(0, 0, 0, a))
    else:     # the end card
        u = t - N3D / FPS
        lg = LOGO.copy(); lg.thumbnail((470, 470)); k = ease(u / 0.35)
        if k > 0.02:
            w, h = int(lg.width * k), int(lg.height * k); base.alpha_composite(lg.resize((w, h)), (int(W / 2 - w / 2), int(330 - h / 2)))
        for j, (tx, sz, col, t_) in enumerate([('Someone out there', 52, (235, 235, 240), 0.5), ('is better than you.', 52, (235, 235, 240), 0.8),
                                               ('Find them.', 92, (255, 214, 80), 1.3)]):
            if u > t_: d.text((W / 2, 640 + j * 80 + (30 if j == 2 else 0)), tx, font=font(sz), fill=col, stroke_width=5, stroke_fill=(10, 6, 20), anchor='mm')
        if u > 1.8:
            d.rounded_rectangle((50, 1010, W - 50, 1090), 36, fill=(255, 214, 80)); d.text((W / 2, 1050), 'PLAY FREE · memeroyale.imaginestudio.fun', font=font(27), fill=(20, 10, 48), anchor='mm')
    out = grade(np.asarray(base.convert('RGB')).astype(np.float32) / 255.0, t, f)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, f'c_{f:04d}.png'))

if not os.environ.get('MIXONLY'):
    for f in range(1, END + 1): frame(f)
    print('FRAMES-DONE')

# ---------------------------------------------------------------- sound
SR = 48000; L = END / FPS; n = int(L * SR); tt = np.arange(n) / SR
rng = np.random.default_rng(7)
def lowpass(x, a): y = np.empty_like(x); acc = 0.0
def lp(x, k):
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y
def env(t0, a, d, length):
    e = np.zeros(n); i0 = int(t0 * SR); m = min(n - i0, int(length * SR)); x = np.arange(m) / SR
    e[i0:i0 + m] = np.minimum(1, x / max(a, 1e-3)) * np.exp(-x / d); return e
score = np.zeros(n)
# the drone under the monologue (A1 + E2 + A2, slow tremolo), swelling into "I will find you", gone at the montage
sw = np.clip((tt - 3.0) / 3.0, 0, 1) * np.clip((22.4 - tt) / 0.4, 0, 1) * (0.55 + 0.45 * np.clip((tt - 14) / 6, 0, 1))
drone = (np.sin(2 * np.pi * 55 * tt) + 0.6 * np.sin(2 * np.pi * 82.41 * tt) + 0.4 * np.sin(2 * np.pi * 110 * tt + 0.3)) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.25 * tt))
score += 0.10 * drone * sw
# low hits: a downward sine sweep with a long tail, on the big beats
for th in (4.6, 9.8, 17.55, 22.35, 33.45):
    i0 = int(th * SR); m = min(n - i0, int(2.5 * SR)); x = np.arange(m) / SR
    score[i0:i0 + m] += 0.45 * np.sin(2 * np.pi * (70 * x - 18 * x * x)) * np.exp(-x / 0.7)
# thunder: a crack (bright noise) and a long rolling rumble (low-passed noise)
noise = rng.standard_normal(n)
rumble = np.zeros(n)
for th in THUNDER:
    i0 = int(th * SR); m = min(n - i0, int(4.0 * SR)); x = np.arange(m) / SR
    seg = noise[i0:i0 + m] * (np.exp(-x / 0.08) * 0.8 + np.exp(-x / 1.2) * 0.5 * (1 + 0.5 * np.sin(2 * np.pi * 3 * x)))
    rumble[i0:i0 + m] += seg
# a cheap low-pass for the rumble (block average)
k = 24; rumble = np.convolve(rumble, np.ones(k) / k, mode='same')
score += 0.55 * rumble
# rain under the basement and the stakeout
rain = np.convolve(noise, np.ones(6) / 6, mode='same') * 0.035 * (((tt < 22.4) | ((tt >= 27.0) & (tt < 30.0))).astype(float))
score += rain
score = np.tanh(score * 1.2) * 0.9
sf.write(os.path.join(OUT, 'score.wav'), np.stack([score, score], 1).astype(np.float32), SR)
cues = [(f'vo/{i}.wav', t0, 1.0) for i, t0 in LINES]
cues += [('spell_rug.mp3', 0.15, 0.6), ('hq_destroy.mp3', 1.2, 0.6), ('defeat.mp3', 1.6, 0.7), ('crowd_laugh.mp3', 2.0, 0.55),
         ('deploy_spell.mp3', 33.2, 0.8), ('spell_rug.mp3', 33.45, 1.0), ('die_useless.mp3', 33.5, 0.6), ('die_useless.mp3', 33.55, 0.6),
         ('ui_tap.mp3', 32.75, 0.7),
        *[('ui_tap.mp3', t0 + 0.06 * k, 0.25) for t0, n_ in ((22.4, 5), (24.0, 5), (25.4, 5), (27.0, 16)) for k in range(n_)], ('card_reveal.mp3', N3D / FPS + 0.05, 0.8)]
ins = ['-i', os.path.join(OUT, 'score.wav'), '-i', os.path.join(AU, 'mus_battle_cemetery.mp3'), '-i', os.path.join(AU, 'mus_menu.mp3')]
flt = [f'[0:a]volume=1.0[s]',
       f'[1:a]atrim=0:8,volume=0.5,afade=t=in:d=0.3,afade=t=out:st=7.2:d=0.6,adelay=22400|22400[m1]',
       f'[2:a]atrim=0:{L - 30.0},volume=0.35,afade=t=in:d=0.4,afade=t=out:st={L - 30.0 - 1.0}:d=1.0,adelay=30000|30000[m2]']
for j, (p, t0, v) in enumerate(cues):
    ins += ['-i', os.path.join(AU, p)]; ms = int(t0 * 1000)
    flt.append(f'[{j + 3}:a]aresample=48000,adelay={ms}|{ms},volume={v}[a{j}]')
flt.append('[s][m1][m2]' + ''.join(f'[a{j}]' for j in range(len(cues))) + f'amix=inputs={len(cues) + 3}:normalize=0:duration=first,alimiter=limit=0.9[out]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[out]', '-ac', '2', '-ar', '48000', os.path.join(OUT, 'mix.wav')], check=True)
print('MIX-DONE')
