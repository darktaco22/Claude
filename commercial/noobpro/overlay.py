"""The 2D layer of NOOB vs PRO, drawn over the rendered 3D frames, plus the sound mix.

python3 overlay.py FRAMES_DIR overlay.json OUT_DIR [HUD_DIR]
  FRAMES_DIR has f_0001.png .. f_0720.png (the Blender render); OUT_DIR gets c_0001.png .. c_0810.png
  (frames 721-810 are the end card) and mix.wav. assemble.sh turns those into the final mp4.
"""
import json, os, sys, math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FR, OVL, OUT = sys.argv[1:4]; HUD = sys.argv[4] if len(sys.argv) > 4 else os.path.join(FR, '..', 'hud')
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets')
os.makedirs(OUT, exist_ok=True)
O = json.load(open(OVL)); FRAMES = {int(k): v for k, v in O['frames'].items()}; MK = O['marks']
W, H = 720, 1280; FPS = 30; LAST3D = 720; END = 810
FONT = os.path.join(A, 'lilita.ttf')
def font(s): return ImageFont.truetype(FONT, s)
def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def pop(f, f0, dur=8):  # overshoot scale-in
    t = (f - f0) / dur
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    return 1 + 0.25 * math.sin(t * math.pi) if t > 0.6 else ease(t / 0.6) * 1.15

def text(d, xy, s, size, fill, stroke=6, sfill=(20, 10, 48), anchor='mm'):
    d.text(xy, s, font=font(size), fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor=anchor)

def scaled_text_img(s, size, fill, stroke=6):
    f = font(size); bb = f.getbbox(s, stroke_width=stroke)
    im = Image.new('RGBA', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(20, 10, 48))
    return im

def paste_scaled(base, im, cx, cy, k):
    if k <= 0.01: return
    w, h = max(1, int(im.width * k)), max(1, int(im.height * k)); r = im.resize((w, h), Image.LANCZOS)
    base.alpha_composite(r, (int(cx - w / 2), int(cy - h / 2)))

def red_x(k):
    s = 220; im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for w_, c in ((44, (20, 10, 48, 255)), (30, (235, 40, 40, 255))):
        d.line((30, 30, s - 30, s - 30), fill=c, width=w_); d.line((s - 30, 30, 30, s - 30), fill=c, width=w_)
    return im
def green_check(k):
    s = 220; im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(28, 118), (88, 178), (194, 46)]
    for w_, c in ((46, (20, 10, 48, 255)), (32, (60, 220, 90, 255))):
        d.line(pts, fill=c, width=w_, joint='curve')
        for p in pts: d.ellipse((p[0] - w_ / 2, p[1] - w_ / 2, p[0] + w_ / 2, p[1] + w_ / 2), fill=c)
    return im
XIMG, CIMG = red_x(1), green_check(1)

# ---- the game's own 2D layer (src/render/overlay.js), ported: tower plates, unit bars with level badges, deploy clocks
SC = 1.25                                   # the game's overlay scale at 720 px wide
COL = [(124, 255, 107), (255, 77, 109)]; DARKC = [(29, 74, 23), (74, 21, 32)]; INK = (11, 12, 16)
RUBIK = os.path.join(A, 'rubik.ttf')
def rubik(sz):
    f = ImageFont.truetype(RUBIK, int(sz))
    try: f.set_variation_by_axes([800])
    except Exception: pass
    return f
def game_layer(d, R):
    s = SC
    for x, y, team, typ, hp, mx in R['t']:
        X, Y = x * W, y * H; hq = typ == 'hq'; h = 13 * s
        Y += (h / 2 + 4 * s) if team == 0 else -(h / 2 + 2 * s)
        w = (84 if hq else 66) * s; x0, y0 = X - w / 2, Y - h / 2; k = max(0, hp / mx)
        if not (-60 < X < W + 60 and -30 < Y < H + 30): continue
        d.rounded_rectangle((x0 - 3, y0 - 3, x0 + w + 3, y0 + h + 3), int(6 * s), fill=INK + (230,))
        d.rounded_rectangle((x0, y0, x0 + w, y0 + h), int(4 * s), fill=DARKC[team])
        if k > 0:
            d.rounded_rectangle((x0, y0, x0 + max(h * 0.6, w * k), y0 + h), int(4 * s), fill=COL[team])
            d.rounded_rectangle((x0 + 2, y0 + 1.5, x0 + 2 + max(0, w * k - 4), y0 + 1.5 + h * 0.32), 3, fill=(255, 255, 255, 71))
        d.text((X, Y + 0.5), f'{int(math.ceil(hp)):,}', font=rubik(11 * s), fill=(242, 238, 223), stroke_width=int(3 * s / 2 + 0.5), stroke_fill=INK, anchor='mm')
        if hq:
            d.text((X + w / 2 + 12 * s, Y - 8 * s), 'ZZZ', font=font(int(10 * s)), fill=(201, 208, 255), stroke_width=2, stroke_fill=INK, anchor='mm')
    for x, y, team, hp, mx, dep, age in R['u']:
        X, Y = x * W, y * H
        if dep < 1.0:      # the deploy clock
            r = 8 * s; d.ellipse((X - r, Y - r, X + r, Y + r), fill=INK + (190,))
            d.pieslice((X - r + 2, Y - r + 2, X + r - 2, Y + r - 2), -90, -90 + 360 * dep, fill=COL[team]); continue
        dmg = hp < mx; recent = age < 30 + 48
        if not dmg and not recent: continue
        big = mx > 1500; w = (40 if big else 18 if mx < 300 else 28) * s; h = 5 * s; x0 = X - w / 2 + 4 * s; y0 = Y
        d.rounded_rectangle((x0 - 1.5, y0 - 1.5, x0 + w + 1.5, y0 + h + 1.5), 3, fill=INK + (217,))
        d.rounded_rectangle((x0, y0, x0 + max(1, w * max(0, hp / mx)), y0 + h), 2, fill=COL[team])
        bx = x0 - 7 * s
        d.rounded_rectangle((bx - 5 * s, y0 - 2.5 * s, bx + 5 * s, y0 + 7.5 * s), int(2 * s), fill=(42, 122, 34) if team == 0 else (154, 34, 56), outline=INK, width=2)
        d.text((bx, y0 + 2.6 * s), '11' if team == 1 else '9', font=rubik(7.5 * s), fill=(242, 238, 223), anchor='mm')
    if 'b' in R:
        x, y, team, k = R['b']; X, Y = x * W, y * H; w = 34 * s; h = 5 * s; x0 = X - w / 2
        d.rounded_rectangle((x0 - 1.5, Y - 1.5, x0 + w + 1.5, Y + h + 1.5), 3, fill=INK + (217,))
        d.rounded_rectangle((x0, Y, x0 + max(1, w * max(0, k)), Y + h), 2, fill=COL[team])

def bar(d, cx, cy, frac, color, w=96, h=14, label=None):
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle((x0 - 3, y0 - 3, x0 + w + 3, y0 + h + 3), 6, fill=(20, 10, 48))
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 4, fill=(60, 50, 80))
    if frac > 0: d.rounded_rectangle((x0, y0, x0 + max(h, w * frac), y0 + h), 4, fill=color)
    if label: text(d, (cx, cy - 18), label, 20, (255, 255, 255), 4)

def pill(d, xy, s, color):
    f = font(40); bb = f.getbbox(s); x, y = xy; w = bb[2] - bb[0] + 40
    d.rounded_rectangle((x, y, x + w, y + 62), 22, fill=(20, 10, 48)); d.rounded_rectangle((x + 4, y + 4, x + w - 4, y + 58), 18, fill=color)
    text(d, (x + w / 2, y + 30), s, 40, (255, 255, 255), 4)

LOGO = Image.open(os.path.join(A, 'logo.png')).convert('RGBA')
NOOB_CAP = ['The Whale only hits BUILDINGS.', 'Troops in its way? It walks past.']
PRO_CAP = ['Drop LASER EYES in the middle.', 'It pulls The Whale into BOTH towers.']

def frame(f):
    if f <= LAST3D:
        base = Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGBA')
    else:
        base = Image.open(os.path.join(FR, f'f_{LAST3D:04d}.png')).convert('RGBA').filter(ImageFilter.GaussianBlur(10))
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    if f <= LAST3D:
        game_layer(d, FRAMES[f])
        hp_ = os.path.join(HUD, f'h_{f:04d}.png')
        if os.path.exists(hp_): ov.alpha_composite(Image.open(hp_).convert('RGBA'))
    # segments
    t0, t1 = MK['title']
    if f <= t1 + 8:
        a = ease((f - t0) / 10) * (1 - ease((f - t1) / 8))
        if a > 0.01:
            band = Image.new('RGBA', (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
            bd.rectangle((0, 330, W, 720), fill=(20, 10, 48, int(150 * a)))
            ov.alpha_composite(band)
            k = pop(f, t0 + 4, 10)
            paste_scaled(ov, scaled_text_img('NOOB', 130, (255, 80, 80)), W / 2, 420, k * a)
            paste_scaled(ov, scaled_text_img('vs', 80, (255, 255, 255)), W / 2, 520, pop(f, t0 + 10, 8) * a)
            paste_scaled(ov, scaled_text_img('PRO', 130, (90, 230, 110)), W / 2, 620, pop(f, t0 + 16, 10) * a)
            paste_scaled(ov, scaled_text_img('in MEME ROYALE', 44, (255, 214, 80), 5), W / 2, 700, pop(f, t0 + 24, 8) * a)
    def segment(lab, color, f0, f1, mark_at, mark_img, caps):
        if not (f0 <= f <= f1): return
        pill(d, (W / 2 - (font(40).getbbox(lab)[2] + 40) / 2, 74), lab, color)
        paste_scaled(ov, scaled_text_img('Pro tip :', 52, (255, 255, 255), 5), W * 0.76, H * 0.30, pop(f, f0 + 6, 8))
        if f >= mark_at:
            paste_scaled(ov, mark_img, W * 0.76, H * 0.30 + 105, pop(f, mark_at, 9) * 0.75)
            kb = ease((f - mark_at - 10) / 6)
            if kb > 0: d.rectangle((0, H - 440, W, H - 310), fill=(20, 10, 48, int(150 * kb)))
            for i, c in enumerate(caps):
                k = ease((f - mark_at - 12 - 10 * i) / 8)
                if k > 0: text(d, (W / 2, H - 405 + 56 * i), c, 40, (255, 255, 255) if i else (255, 214, 80), 5)
    segment('NOOB', (220, 50, 50), MK['noob'][0], MK['noob'][1], MK['x_at'], XIMG, NOOB_CAP)
    segment('PRO', (40, 170, 70), MK['pro'][0], MK['pro'][1], MK['check_at'], CIMG, PRO_CAP)
    base.alpha_composite(ov)
    # the swipe between NOOB and PRO
    sw0 = MK['noob'][1] - 8
    if sw0 <= f <= sw0 + 18:
        t = (f - sw0) / 18; x = int(-W + 2 * W * ease(t)) if t < 0.5 else int(W * (ease(t) * 2 - 1))
        st = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.polygon([(x - 200, 0), (x + W, 0), (x + W + 200, H), (x, H)], fill=(255, 214, 80, 255))
        sd.text((x + W / 2 + 100, H / 2), 'NOW THE PRO', font=font(80), fill=(20, 10, 48), anchor='mm')
        base.alpha_composite(st)
    if f > LAST3D:   # end card
        dark = Image.new('RGBA', (W, H), (20, 10, 48, 170)); base.alpha_composite(dark)
        k = pop(f, LAST3D + 2, 10); lg = LOGO.copy(); lg.thumbnail((560, 560))
        paste_scaled(base, lg, W / 2, 470, k)
        d2 = ImageDraw.Draw(base)
        if f >= LAST3D + 12: paste_scaled(base, scaled_text_img('PLAY FREE', 96, (255, 255, 255), 7), W / 2, 820, pop(f, LAST3D + 12, 8))
        if f >= LAST3D + 18: paste_scaled(base, scaled_text_img('IN YOUR BROWSER', 52, (255, 214, 80), 5), W / 2, 905, pop(f, LAST3D + 18, 8))
        if f >= LAST3D + 26:
            d2.rounded_rectangle((70, 980, W - 70, 1050), 30, fill=(255, 214, 80)); text(d2, (W / 2, 1015), 'memeroyale.imaginestudio.fun', 36, (20, 10, 48), 0)
    base.convert('RGB').save(os.path.join(OUT, f'c_{f:04d}.png'))

ONLY = [int(x) for x in os.environ.get('ONLY', '').split(',') if x]
for f in (ONLY or range(1, END + 1)):
    frame(f)
print('OVERLAY-DONE')
if ONLY: sys.exit(0)

# ---------------------------------------------------------------- sound
AU = os.path.join(HERE, 'audio'); cues = []
def cue(name, f, vol=1.0): cues.append((name, f, vol))
cue('ui_swoosh', 4); cue('emote_pop', 8); cue('emote_pop', 14); cue('emote_pop', 20)
for e in O['events']:
    cue('bld_drop' if abs(e['f'] - MK['drop_idol']) < 2 else 'deploy_drop', e['f'], 0.9)
cue('bark_whale', 28, 0.8); cue('bark_lmao', MK['drop_lmao'] + 4, 0.8); cue('bark_whale', 376, 0.8); cue('bark_useless', MK['drop_useless'] + 4, 0.8)
for s in O['shots']: cue('tower_shot', s['f0'], 0.45); cue('tower_hit', s['f1'], 0.4)
for f in MK['tower_hits']: cue('whale_slam', f, 0.9)
for f in MK['idol_hits']: cue('whale_slam', f, 0.8)
cue('card_deny', MK['x_at'], 1.0); cue('ui_swoosh', MK['noob'][1] - 8, 1.0)
for f in range(MK['drop_idol'] + 10, MK['whale_die'], 18): cue('atk_lasereyes', f, 0.35)
for f in range(MK['drop_useless'] + 24, MK['whale_die'], 13): cue('atk_useless', f, 0.3)
cue('die_whale', MK['whale_die'], 1.0); cue('w_fanfare', MK['check_at'], 0.9); cue('victory', LAST3D + 2, 0.8)
inputs = ['-i', os.path.join(AU, 'mus_battle.mp3')]; flt = [f'[0:a]atrim=0:{END / FPS},volume=0.35,afade=t=out:st={END / FPS - 1.2}:d=1.2[m]']
for i, (n, f, v) in enumerate(cues):
    inputs += ['-i', os.path.join(AU, n + '.mp3')]; ms = int((f - 1) / FPS * 1000)
    flt.append(f'[{i + 1}:a]adelay={ms}|{ms},volume={v}[a{i}]')
flt.append('[m]' + ''.join(f'[a{i}]' for i in range(len(cues))) + f'amix=inputs={len(cues) + 1}:normalize=0:duration=first,alimiter=limit=0.9[out]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(flt), '-map', '[out]', '-ac', '2', '-ar', '48000',
                os.path.join(OUT, 'mix.wav')], check=True)
print('MIX-DONE', len(cues), 'cues')
