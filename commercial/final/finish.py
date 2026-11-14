"""Finish "THE FINAL":  python3 finish.py FRAMES_DIR OUT_DIR VO_DIR [f1,f2,...]
->  OUT_DIR/c_####.png (1920x1080, 24 fps) + mix.wav

Picture: the 3D frames upscaled and graded for a clean broadcast look, then a full graphics package drawn at
1080p: opening title, commentator names, tale-of-the-tape cards, score bug with clock and win probability, LIVE and
REPLAY bugs, replay wipes, telestrator, lower thirds, a news ticker, closed captions, a cinema letterbox for the
slow-motion walk, the full-time board and the end card.
Sound: two commentators, a looping stadium crowd with reactions, the game's own effects and music, a synthesized
broadcast sting and a slow orchestral build for the walk.
Env: SOUND_ONLY=1 skips the picture; CAPTIONS=0 hides captions.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FR, OUT, VOD = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'assets')
AU = os.path.join(HERE, '..', 'comeback', 'audio')
SFX = os.path.join(HERE, '..', 'degens', 'audio', 'sfx')
E = json.load(open(os.path.join(HERE, 'edl.json')))
SHOTS = E['shots']
S = {s['name']: s for s in SHOTS}
FPS = 24
N3D = E['last']
T_CARD = E['t_card']
T_FILM = E['t_film']
NF = int(round(T_FILM * FPS))
EV = E['ev']
GFX = {g[0]: (g[1], g[2]) for g in E['gfx']}
CUE = {i: (t0, t1) for i, t0, t1 in E['cues']}
W, H = 1920, 1080
ONLY = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
CAPTIONS = os.environ.get('CAPTIONS', '1') != '0'

BLUE = (38, 110, 255)
RED = (232, 44, 40)
GOLD = (255, 196, 64)
INK = (12, 14, 22)
WHITE = (255, 255, 255)

_fonts = {}


def rub(size, weight=500):
    key = (size, weight)
    if key not in _fonts:
        f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        _fonts[key] = f
    return _fonts[key]


def lil(size):
    key = ('lil', size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(A, 'lilita.ttf'), size)
    return _fonts[key]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def out_back(x):
    x = max(0.0, min(1.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def decay(t, t0, dur):
    return max(0.0, 1 - (t - t0) / dur) if t >= t0 else 0.0


def fade(t, t0, t1, d=0.3):
    return ease((t - t0) / d) * ease((t1 - t) / d)


def rgba(c, a=255):
    return (c[0], c[1], c[2], int(max(0, min(255, a))))


def shot_at(t):
    return next((s for s in SHOTS if s['t0'] <= t < s['t1']), SHOTS[-1])


def project(s, t, point):
    """Screen position of a world point in shot s at film time t (pinhole camera, no handheld shake)."""
    u = ease((t - s['t0']) / (s['t1'] - s['t0']))
    p = np.array(s['p0']) + (np.array(s['p1']) - np.array(s['p0'])) * u
    look = np.array(s['l0']) + (np.array(s['l1']) - np.array(s['l0'])) * u
    fwd = look - p
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0, 0, 1.0]))
    right = right / np.linalg.norm(right)
    up = np.cross(right, fwd)
    v = np.array(point) - p
    z = float(v @ fwd)
    lens = s['lens'] + (s['lens1'] - s['lens']) * u
    k = lens / 36.0 * W
    return W / 2 + float(v @ right) / z * k, H / 2 - float(v @ up) / z * k, k / z


# ---------------------------------------------------------------- picture: grade
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RR = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
VIG = (1 - 0.2 * RR ** 1.4)[..., None]


def punch(a, k):
    if k <= 1.0005:
        return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    w, h = im.size
    nw, nh = w / k, h / k
    box = (int((w - nw) / 2), int((h - nh) / 2), int((w - nw) / 2 + nw), int((h - nh) / 2 + nh))
    return np.asarray(im.crop(box).resize((w, h), Image.BILINEAR), np.float32) / 255.0


def grade(a, cinema=0.0):
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum) * (1.12 - 0.1 * cinema)
    a = np.clip((a - 0.012) * 1.07, 0, 1) ** 1.03
    if cinema > 0:
        tint = a * np.array([1.05, 0.99, 0.9], np.float32) + 0.05 * (1 - lum) ** 2 * np.array([-0.2, 0.1, 0.5], np.float32)
        a = a * (1 - cinema) + tint * cinema
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.78) / 0.22, 0, 1) * a
    hb = Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b1 = np.asarray(hb.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR), np.float32) / 255.0
    return a + b1 * (0.26 + 0.2 * cinema)


# ---------------------------------------------------------------- graphics helpers
def panel(d, box, fill, radius=10, outline=None, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(d, xy, s, font, fill, anchor='lm', sp=0):
    if not sp:
        d.text(xy, s, font=font, fill=fill, anchor=anchor)
        return d.textlength(s, font=font)
    ws = [d.textlength(c, font=font) for c in s]
    tot = sum(ws) + sp * (len(s) - 1)
    x = xy[0] - (tot / 2 if anchor[0] == 'm' else (tot if anchor[0] == 'r' else 0))
    for c, w_ in zip(s, ws):
        d.text((x, xy[1]), c, font=font, fill=fill, anchor='l' + anchor[1])
        x += w_ + sp
    return tot


def crown(d, x, y, s, fill):
    pts = [(x - s, y + s * 0.6), (x - s, y - s * 0.3), (x - s * 0.45, y + s * 0.15), (x, y - s * 0.7), (x + s * 0.45, y + s * 0.15),
           (x + s, y - s * 0.3), (x + s, y + s * 0.6)]
    d.polygon(pts, fill=fill)


# win probability for Pepe, by film time
PROB = [(EV['kick'], 12.0), (EV['swat'], 12.0), (EV['swat'] + 0.8, 6.0), (EV['t1'], 6.0), (EV['t1'] + 0.8, 2.1), (EV['t2'], 2.1),
        (EV['t2'] + 0.8, 0.3), (EV['use'], 0.3), (EV['use'] + 1.0, 0.1), (EV['kfall'] + 0.2, 0.1), (EV['kfall'] + 1.2, 100.0)]
SCORE = [(0, 0, 0), (EV['t1'] + 0.5, 0, 1), (EV['t2'] + 0.5, 0, 2), (EV['kfall'] + 0.7, 3, 2)]
T_MATCH0 = S['kickoff']['t0']
T_MATCH1 = T_CARD
CINEMA = (S['walk hero']['t0'], S['squad pass']['t1'])
REPLAY = GFX['replay']
TICKER = ('BREAKING: Local frog still holding     ◆     Whale denies moving markets     ◆     Analysts expect number to go up, or down     ◆     '
          'Useless listed on zero exchanges     ◆     Giga asked for comment, flexes instead     ◆     Blue fans seen buying back in at the top     ◆     '
          'Stadium roof funded by transaction fees, does not exist     ◆     Meme Royale: free to play, still     ◆     ')


def interp(pts, t):
    return float(np.interp(t, [p[0] for p in pts], [p[1] for p in pts]))


def score_at(t):
    b, r = 0, 0
    for t0, b_, r_ in SCORE:
        if t >= t0:
            b, r = b_, r_
    return b, r


def draw_scorebug(d, t, k):
    """Top left: teams, crowns, clock, and Pepe's win probability underneath."""
    x, y = 60 - 40 * (1 - k), 48
    a = 255 * k
    panel(d, (x, y, x + 520, y + 64), rgba(INK, a * 0.9), 12)
    d.rectangle((x, y + 8, x + 8, y + 56), fill=rgba(BLUE, a))
    d.rectangle((x + 512, y + 8, x + 520, y + 56), fill=rgba(RED, a))
    b, r = score_at(t)
    text(d, (x + 26, y + 33), 'PEPE', rub(30, 700), rgba(WHITE, a))
    text(d, (x + 494, y + 33), 'GIGA', rub(30, 700), rgba(WHITE, a), 'rm')
    for team, n, x0, col in (('b', b, x + 196, BLUE), ('r', r, x + 324, RED)):
        panel(d, (x0 - 34, y + 8, x0 + 34, y + 56), rgba(col, a), 8)
        bounce = 1.0
        for t0, b_, r_ in SCORE[1:]:
            if (team == 'b' and b_ == n or team == 'r' and r_ == n) and 0 <= t - t0 < 0.5:
                bounce = 1 + 0.5 * decay(t, t0, 0.5)
        text(d, (x0, y + 33), str(n), lil(int(44 * bounce)), rgba(WHITE, a), 'mm')
    crown(d, x + 260, y + 30, 13, rgba(GOLD, a))
    # clock
    mt = max(0.0, t - EV['kick'])
    panel(d, (x + 530, y, x + 640, y + 64), rgba(INK, a * 0.9), 12)
    text(d, (x + 585, y + 33), f'{int(mt // 60)}:{int(mt % 60):02d}', rub(30, 600), rgba(GOLD, a), 'mm')
    # win probability
    if t >= EV['kick']:
        p = interp(PROB, t)
        k2 = ease((t - EV['kick']) / 0.5) * k
        y2 = y + 74
        panel(d, (x, y2, x + 640, y2 + 40), rgba(INK, 255 * k2 * 0.82), 10)
        text(d, (x + 16, y2 + 21), 'PEPE WIN PROBABILITY', rub(19, 600), rgba((190, 200, 220), 255 * k2), sp=1)
        bx0, bx1 = x + 286, x + 548
        d.rounded_rectangle((bx0, y2 + 13, bx1, y2 + 27), radius=7, fill=rgba(RED, 255 * k2))
        wbar = max(4, (bx1 - bx0) * p / 100.0)
        d.rounded_rectangle((bx0, y2 + 13, bx0 + wbar, y2 + 27), radius=7, fill=rgba(BLUE, 255 * k2))
        label = f'{p:.0f}%' if p >= 10 else f'{p:.1f}%'
        text(d, (x + 628, y2 + 21), label, rub(22, 700), rgba(WHITE if p < 50 else GOLD, 255 * k2), 'rm')


def draw_live(d, t, k, replay):
    x, y = W - 60, 48
    if replay:
        blink = 0.65 + 0.35 * math.sin(t * 9)
        panel(d, (x - 190, y, x, y + 54), rgba(GOLD, 255 * k), 10)
        text(d, (x - 95, y + 28), 'REPLAY', rub(30, 800), rgba(INK, 255 * k * blink + 255 * (1 - blink) * 0.6), 'mm', 2)
    else:
        panel(d, (x - 132, y, x, y + 54), rgba(INK, 230 * k), 10)
        blink = 0.5 + 0.5 * math.sin(t * 5)
        d.ellipse((x - 116, y + 17, x - 96, y + 37), fill=rgba(RED, 255 * k * (0.45 + 0.55 * blink)))
        text(d, (x - 84, y + 28), 'LIVE', rub(28, 800), rgba(WHITE, 255 * k), 'lm', 2)


def draw_ticker(d, t, k):
    y = H - 54 + 60 * (1 - k)
    d.rectangle((0, y, W, H), fill=rgba(INK, 235))
    d.rectangle((0, y, W, y + 3), fill=rgba(GOLD, 255))
    font = rub(26, 500)
    wtot = d.textlength(TICKER, font=font)
    x = 250 - ((t - T_MATCH0) * 150) % wtot
    while x < W:
        d.text((x, y + 29), TICKER, font=font, fill=rgba((235, 238, 245), 255), anchor='lm')
        x += wtot
    d.rectangle((0, y + 3, 232, H), fill=rgba(GOLD, 255))
    text(d, (116, y + 30), 'MR SPORT', rub(26, 800), rgba(INK, 255), 'mm', 1)


def draw_title(d, t, t0, t1):
    k = fade(t, t0, t1, 0.45)
    if k <= 0:
        return
    u = t - t0
    w_ = 1180 * out_back(u / 0.6)
    y = 690
    d.rectangle((W / 2 - w_ / 2, y - 6, W / 2 + w_ / 2, y + 96), fill=rgba(INK, 225 * k))
    d.rectangle((W / 2 - w_ / 2, y - 12, W / 2 + w_ / 2, y - 6), fill=rgba(GOLD, 255 * k))
    k2 = ease((u - 0.35) / 0.4) * k
    text(d, (W / 2, y + 46), 'MEME ROYALE CHAMPIONSHIP', rub(58, 800), rgba(WHITE, 255 * k2), 'mm', 6)
    k3 = ease((u - 0.7) / 0.4) * k
    w3 = 420 * out_back((u - 0.6) / 0.5)
    d.rectangle((W / 2 - w3 / 2, y + 104, W / 2 + w3 / 2, y + 176), fill=rgba(GOLD, 255 * k3))
    text(d, (W / 2, y + 141), 'THE FINAL', rub(50, 800), rgba(INK, 255 * k3), 'mm', 10)


def draw_names(d, t, t0, t1):
    k = fade(t, t0, t1, 0.35)
    if k <= 0:
        return
    for i, (name, role, x) in enumerate((('CHIP LEDGER', 'Play-by-play', 150), ('BASIL HODL', 'Analysis', 1090))):
        kk = ease((t - t0 - 0.15 * i) / 0.4) * k
        y = 846 + 26 * (1 - kk)
        panel(d, (x, y, x + 600, y + 62), rgba(INK, 235 * kk), 8)
        d.rectangle((x, y, x + 10, y + 62), fill=rgba(GOLD, 255 * kk))
        text(d, (x + 30, y + 32), name, rub(38, 800), rgba(WHITE, 255 * kk), sp=2)
        panel(d, (x, y + 62, x + 330, y + 104), rgba(GOLD, 255 * kk), 6)
        text(d, (x + 30, y + 84), role.upper(), rub(24, 700), rgba(INK, 255 * kk), sp=2)


def draw_card(d, t, t0, t1, name, colour, corner, rows, left):
    """Tale of the tape: a side panel whose rows arrive one by one."""
    k = fade(t, t0, t1, 0.35)
    if k <= 0:
        return
    u = t - t0
    wpanel = 600
    slide = (1 - out_back(u / 0.5)) * 120
    x = (110 - slide) if left else (W - 110 - wpanel + slide)
    y = 250
    panel(d, (x, y, x + wpanel, y + 110), rgba(colour, 245 * k), 10)
    text(d, (x + 30, y + 36), corner, rub(24, 700), rgba(WHITE, 220 * k), sp=3)
    text(d, (x + 30, y + 76), name, lil(60), rgba(WHITE, 255 * k))
    for i, (label, value) in enumerate(rows):
        kk = ease((u - 0.45 - 0.33 * i) / 0.3) * k
        if kk <= 0:
            continue
        yy_ = y + 122 + i * 80 + 14 * (1 - kk)
        panel(d, (x, yy_, x + wpanel, yy_ + 70), rgba(INK, 232 * kk), 8)
        text(d, (x + 30, yy_ + 36), label, rub(25, 600), rgba((170, 182, 205), 255 * kk), sp=2)
        text(d, (x + wpanel - 30, yy_ + 36), value, rub(36, 800), rgba(WHITE, 255 * kk), 'rm')


def draw_lower(d, t, t0, t1, title, sub, colour):
    k = fade(t, t0, t1, 0.35)
    if k <= 0:
        return
    kk = out_back((t - t0) / 0.45)
    x, y = 130 - 60 * (1 - kk), 800
    wt = d.textlength(title, font=lil(58)) + 70
    panel(d, (x, y, x + wt, y + 82), rgba(colour, 245 * k), 8)
    text(d, (x + 32, y + 42), title, lil(58), rgba(WHITE, 255 * k))
    ws = d.textlength(sub, font=rub(30, 500)) + 64
    panel(d, (x, y + 82, x + ws, y + 136), rgba(INK, 235 * k), 8)
    text(d, (x + 32, y + 110), sub, rub(30, 500), rgba((235, 238, 245), 255 * k))


def draw_wipe(im, t, t0):
    """A gold diagonal bar with the logo colours sweeps the screen at a replay cut."""
    u = (t - t0 + 0.22) / 0.44
    if not 0 < u < 1:
        return
    d = ImageDraw.Draw(im, 'RGBA')
    xc = -500 + (W + 1000) * u
    for dx, w_, col in ((-260, 150, BLUE), (-90, 300, GOLD), (140, 150, RED)):
        d.polygon([(xc + dx - w_ / 2 + 260, 0), (xc + dx + w_ / 2 + 260, 0), (xc + dx + w_ / 2 - 260, H), (xc + dx - w_ / 2 - 260, H)],
                  fill=rgba(col, 255))


def hand_circle(d, cx, cy, rx, ry, prog, colour, width=9):
    """A telestrator ellipse, drawn on progressively, slightly wobbly, overshooting like a pen."""
    n = int(70 * prog * 1.08)
    pts = []
    for i in range(n + 1):
        a = -math.pi / 2 + 2 * math.pi * 1.08 * i / 70
        w_ = 1 + 0.035 * math.sin(a * 3.1) + 0.02 * math.sin(a * 7.3)
        pts.append((cx + rx * w_ * math.cos(a), cy + ry * w_ * math.sin(a) + 4 * math.sin(a * 2)))
    if len(pts) > 1:
        d.line(pts, fill=colour, width=width, joint='curve')


def hand_arrow(d, x0, y0, x1, y1, prog, colour, width=9):
    xe, ye = x0 + (x1 - x0) * prog, y0 + (y1 - y0) * prog
    d.line([(x0, y0), (xe, ye)], fill=colour, width=width)
    if prog > 0.95:
        ang = math.atan2(y1 - y0, x1 - x0)
        for da in (2.6, -2.6):
            d.line([(x1, y1), (x1 + 34 * math.cos(ang + da), y1 + 34 * math.sin(ang + da))], fill=colour, width=width)


def draw_telestrator(d, t):
    s = S['replay']
    yel = rgba((255, 232, 40), 245)
    t0, t1 = GFX['tele_tower']
    if t0 <= t < s['t1']:
        x, y, k = project(s, t, (3.5, -25.5, 3.0))
        a = 245 * ease((t1 + 0.25 - t) / 0.25)
        col = rgba((255, 232, 40), a)
        hand_circle(d, x, y, 2.7 * k, 3.6 * k, ease((t - t0) / 0.55), col)
        b6 = CUE['b06'][0]
        for label, dt, dy in (('FINE', 2.75, -1.0), ('STILL FINE', 3.75, 0.2)):
            kk = ease((t - b6 - dt) / 0.18)
            if kk > 0 and a > 0:
                xx_, yy_ = x + 3.4 * k, y + dy * 1.9 * k
                hand_arrow(d, xx_ + 150, yy_, xx_ + 20, yy_, kk, col, 7)
                text(d, (xx_ + 168, yy_), label, lil(int(54 * (0.8 + 0.2 * out_back(kk)))), col)
    t0, t1 = GFX['tele_whale']
    if t0 <= t < t1:
        a_time = s['a0'] + (t - s['t0']) * s['s0']
        wy = -19.5 - 4.0 * (a_time - (E['times']['t1'] - 1.5))
        x, y, k = project(s, t, (3.5, wy, 2.2))
        kk = ease((t - t0) / 0.2)
        hand_arrow(d, x, y - 5.4 * k, x, y - 2.6 * k, kk, yel, 9)
        text(d, (x, y - 6.3 * k), 'WHALE', lil(60), yel, 'mm')


def draw_fulltime(d, t):
    t0 = EV['kfall'] + 2.2
    t1 = S['stadium']['t1'] - 0.2
    k = fade(t, t0, t1, 0.4)
    if k <= 0:
        return
    u = t - t0
    w_ = 900 * out_back(u / 0.5)
    y = 300
    d.rectangle((W / 2 - w_ / 2, y, W / 2 + w_ / 2, y + 70), fill=rgba(GOLD, 255 * k))
    text(d, (W / 2, y + 36), 'FULL TIME', rub(44, 800), rgba(INK, 255 * k * ease((u - 0.2) / 0.3)), 'mm', 12)
    k2 = ease((u - 0.35) / 0.4) * k
    d.rectangle((W / 2 - 450, y + 70, W / 2 + 450, y + 230), fill=rgba(INK, 235 * k2))
    d.rectangle((W / 2 - 450, y + 70, W / 2 - 434, y + 230), fill=rgba(BLUE, 255 * k2))
    d.rectangle((W / 2 + 434, y + 70, W / 2 + 450, y + 230), fill=rgba(RED, 255 * k2))
    text(d, (W / 2 - 250, y + 150), 'PEPE', lil(84), rgba(WHITE, 255 * k2), 'mm')
    text(d, (W / 2 + 250, y + 150), 'GIGA', lil(84), rgba((150, 156, 170), 255 * k2), 'mm')
    text(d, (W / 2, y + 150), '3 – 2', lil(96), rgba(GOLD, 255 * k2), 'mm')
    k3 = ease((u - 1.0) / 0.4) * k
    panel(d, (W / 2 - 330, y + 240, W / 2 + 330, y + 292), rgba(INK, 225 * k3), 8)
    text(d, (W / 2, y + 267), 'WINNING CARD:  USELESS', rub(28, 700), rgba(GOLD, 255 * k3), 'mm', 3)


def draw_captions(d, t):
    if not CAPTIONS:
        return
    for i, t0, t1 in E['cues']:
        if t0 - 0.05 <= t < t1 + 0.12:
            who = E['who'][i]
            line = E['subs'][i]
            font = rub(32, 500)
            tag = 'CHIP' if who == 'chip' else 'BASIL'
            wtag = d.textlength(tag, font=rub(24, 800)) + 28
            wl = d.textlength(line, font=font) + 40
            y = (H - 124) if T_MATCH0 <= t < T_MATCH1 else (H - 96)
            x = W / 2 - (wtag + wl) / 2
            d.rectangle((x, y, x + wtag, y + 52), fill=rgba(GOLD if who == 'chip' else (210, 214, 226), 245))
            text(d, (x + wtag / 2, y + 27), tag, rub(24, 800), rgba(INK, 255), 'mm')
            d.rectangle((x + wtag, y, x + wtag + wl, y + 52), fill=rgba((0, 0, 0), 200))
            text(d, (x + wtag + 20, y + 27), line, font, rgba(WHITE, 255))


BG = None


def end_card(t):
    global BG
    if BG is None:
        b = Image.open(os.path.join(A, 'bg_title_wide.jpg')).convert('RGB')
        k = max(W / b.width, H / b.height)
        b = b.resize((int(b.width * k) + 1, int(b.height * k) + 1), Image.LANCZOS)
        b = b.crop(((b.width - W) // 2, (b.height - H) // 2, (b.width - W) // 2 + W, (b.height - H) // 2 + H)).filter(ImageFilter.GaussianBlur(14))
        BG = (np.asarray(b, np.float32) / 255.0 * 0.34, Image.open(os.path.join(A, 'logo.png')).convert('RGBA'))
    bg, logo = BG
    u = t - T_CARD
    a = bg * ease(u / 0.5) * (1 - 0.5 * RR)[..., None]
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    k = ease((u - 0.15) / 0.5)
    s = int(470 * (1.06 - 0.06 * k))
    lg = logo.resize((s, int(s * logo.height / logo.width)), Image.LANCZOS)
    lg.putalpha(lg.getchannel('A').point(lambda v: int(v * k)))
    im.alpha_composite(lg, ((W - lg.width) // 2, 230 - (lg.height - 446) // 2))
    d = ImageDraw.Draw(im, 'RGBA')
    k2 = ease((u - 0.9) / 0.5)
    text(d, (W / 2, 760), 'FREE TO PLAY', rub(56, 800), rgba((255, 236, 200), 255 * k2), 'mm', 10)
    text(d, (W / 2, 840), 'memeroyale.imaginestudio.fun', rub(32, 500), rgba(WHITE, 190 * k2), 'mm', 2)
    b13 = CUE['b13'][0]
    k3 = ease((t - b13 - 0.2) / 0.4)
    text(d, (W / 2, 930), 'THERE ARE NO MESSAGES', rub(24, 600), rgba(GOLD, 200 * k3), 'mm', 6)
    draw_captions(d, t)
    return im.convert('RGB')


def overlays(im, t):
    d = ImageDraw.Draw(im, 'RGBA')
    s = shot_at(t)
    in_replay = REPLAY[0] <= t < REPLAY[1]
    cin = fade(t, CINEMA[0], CINEMA[1], 0.5)
    if cin > 0:                                          # the broadcast gives way to cinema for the walk
        bar = int(132 * cin)
        d.rectangle((0, 0, W, bar), fill=(0, 0, 0, 255))
        d.rectangle((0, H - bar, W, H), fill=(0, 0, 0, 255))
    g = 1 - cin
    if 'title' in GFX:
        draw_title(d, t, *GFX['title'])
    draw_names(d, t, *GFX['names'])
    draw_card(d, t, *GFX['card_giga'], 'GIGA', RED, 'RED CORNER  ·  CHAMPION',
              (('RECORD', '44 – 0'), ('PRICE CHECKS', '0'), ('JAWLINE', 'Registered'), ('WEAKNESS', 'None found')), True)
    draw_card(d, t, *GFX['card_pepe'], 'PEPE', BLUE, 'BLUE CORNER  ·  CHALLENGER',
              (('RECORD', '3 – 41'), ('PORTFOLIO', '−99%'), ('STRATEGY', 'Holding'), ('MORALE', 'Unclear')), False)
    if T_MATCH0 <= t < T_MATCH1 and g > 0.02:
        k = ease((t - T_MATCH0) / 0.5) * ease((T_MATCH1 - t) / 0.3) * g
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer, 'RGBA')
        draw_scorebug(dl, t, 1.0)
        draw_live(dl, t, 1.0, in_replay)
        draw_ticker(dl, t, 1.0)
        if k < 0.999:
            layer.putalpha(layer.getchannel('A').point(lambda v: int(v * k)))
        im.alpha_composite(layer)
        d = ImageDraw.Draw(im, 'RGBA')
    elif t < T_MATCH0:
        draw_live(d, t, ease((t - 0.6) / 0.5), False)
    if in_replay:
        draw_telestrator(d, t)
    draw_lower(d, t, *GFX['lower_useless'], 'USELESS', 'Utility: none   ·   Roadmap: none   ·   Vibes: immaculate', BLUE)
    draw_lower(d, t, *GFX['lower_pepe'], 'PEPE', 'Champion   ·   Statement: none', BLUE)
    draw_fulltime(d, t)
    draw_captions(d, t)
    for tw in (REPLAY[0], REPLAY[1]):
        draw_wipe(im, t, tw)
    return im


def frame(f):
    t = (f - 1) / FPS
    if f > N3D:
        im = end_card(t)
    else:
        src = Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGB').resize((W, H), Image.LANCZOS)
        src = src.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))
        a = np.asarray(src, np.float32) / 255.0
        k = 1.0
        fl = 0.0
        for name, zoom, flash in (('swat', 0.03, 0.2), ('t1', 0.06, 0.45), ('t2', 0.05, 0.4), ('kfall', 0.08, 0.6), ('t1_replay', 0.03, 0.0)):
            d_ = decay(t, EV[name], 0.7)
            k += zoom * d_ * d_
            fl = max(fl, flash * decay(t, EV[name], 0.2))
        for tb in EV['hero_boom']:
            fl = max(fl, 0.22 * decay(t, tb, 0.3))
        a = punch(a, k)
        cin = fade(t, CINEMA[0], CINEMA[1], 0.5)
        a = grade(a, cin)
        if fl > 0:
            a = a * (1 - fl) + np.array([1.0, 0.9, 0.75], np.float32) * fl * 1.15
        a = a * VIG * ease(t / 0.8) * ease((T_CARD - t) / 0.3)
        a = a + np.random.default_rng(f).normal(0, 0.006 + 0.008 * cin, (H, W, 1)).astype(np.float32)
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        im = overlays(im, t).convert('RGB')
    im.save(os.path.join(OUT, f'c_{f:04d}.png'), compress_level=3)


for f in ([] if os.environ.get('SOUND_ONLY') else (ONLY or range(1, NF + 1))):
    frame(f)
print('FRAMES-DONE')
if ONLY:
    sys.exit(0)

# ---------------------------------------------------------------- sound
SR = 48000
END = NF / FPS
n = int(END * SR) + SR
rng = np.random.default_rng(23)
BUS = {k: np.zeros((n, 2), np.float32) for k in ('vo', 'mus', 'amb', 'fx')}


def load(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def game(name):
    return load(os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3')))


def put(bus, x, t, g=1.0, pan=0.0):
    i = int(t * SR)
    m = min(len(x), n - i)
    if m > 0 and i >= 0:
        BUS[bus][i:i + m] += x[:m] * g * np.array([1 - max(0, pan), 1 + min(0, pan)], np.float32)


def env(pts, length):
    return np.interp(np.arange(length) / SR, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)


def mono(s):
    return np.stack([s, s], 1).astype(np.float32)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, 'same')


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def strings(m, t, dur, g=0.1, att=1.2, rel=1.6, bright=7):
    L = int((dur + rel) * SR)
    x = np.arange(L) / SR
    s = np.zeros(L)
    for det in (-0.06, 0.0, 0.07):
        f = midi(m + det)
        ph = 2 * np.pi * f * x + 0.9 * np.sin(2 * np.pi * (4.6 + det * 3) * x) * np.clip(x / 1.5, 0, 1)
        for h in range(1, bright + 1):
            s += np.sin(ph * h + h * det * 20) / h ** 1.35
    e = np.clip(x / att, 0, 1) ** 1.5 * np.clip((dur + rel - x) / rel, 0, 1) ** 1.5
    put('mus', mono(s * e), t, g / 3)


def brass(m, t, dur, g=0.12):
    """A bright, short fanfare voice: saw-like harmonics with a fast attack."""
    L = int((dur + 0.25) * SR)
    x = np.arange(L) / SR
    s = np.zeros(L)
    for det in (-0.04, 0.05):
        f = midi(m + det)
        for h in range(1, 13):
            s += np.sin(2 * np.pi * f * h * x) / h ** 0.9 * np.clip(x / (0.02 + 0.01 * h), 0, 1)
    e = np.clip(x / 0.03, 0, 1) * np.clip((dur + 0.25 - x) / 0.25, 0, 1) * (0.75 + 0.25 * np.exp(-x / 0.15))
    put('mus', mono(s * e), t, g / 4)


def pluck(m, t, g=0.2, dur=0.5, pan=0.0):
    L = int(dur * SR)
    x = np.arange(L) / SR
    f = midi(m)
    s = sum(np.sin(2 * np.pi * f * h * x) * np.exp(-x * (5 + 4 * h)) / h for h in range(1, 6))
    put('mus', mono(s), t, g, pan)


def timp(t, m=38, g=0.6):
    L = int(1.4 * SR)
    x = np.arange(L) / SR
    f = midi(m)
    s = (np.sin(2 * np.pi * (f * x + 8 * np.exp(-x * 30) / 30)) * np.exp(-x / 0.35) + 0.5 * np.sin(2 * np.pi * f * 1.5 * x) * np.exp(-x / 0.15)
         + rng.normal(0, 1, L) * np.exp(-x / 0.01) * 0.3)
    put('mus', mono(s), t, g)


def choir(m, t, dur, g=0.1):
    L = int((dur + 2.0) * SR)
    x = np.arange(L) / SR
    s = np.zeros(L)
    for det in (-0.09, 0.0, 0.1):
        f = midi(m + det)
        ph = 2 * np.pi * f * x + 1.2 * np.sin(2 * np.pi * (5.0 + det) * x)
        for h in range(1, 14):
            fr = f * h
            amp = math.exp(-((fr - 750) / 260) ** 2) + 0.6 * math.exp(-((fr - 1200) / 320) ** 2) + 0.12 / h
            s += np.sin(ph * h) * amp
    e = np.clip(x / 0.5, 0, 1) * np.clip((dur + 2.0 - x) / 2.0, 0, 1) ** 2
    put('mus', mono(s * e), t, g / 3)


def boom(t, f0=50, dur=2.2, g=0.9):
    x = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * (f0 * x - 10 * x * x / dur)) * np.exp(-x / (dur * 0.35)) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.05) * 0.5
    put('fx', mono(s), t, g)


def whoosh(t, dur=1.0, g=0.4):
    x = np.arange(int(dur * SR)) / SR
    u = x / dur
    k = lowpass(rng.normal(0, 1, len(x)), 120) * 12
    e = np.sin(np.pi * u) ** 2
    put('fx', mono(k * e + 0.25 * np.sin(2 * np.pi * (80 + 300 * u) * x) * e), t, g)


def thud(t, g=0.5, f0=90):
    x = np.arange(int(0.3 * SR)) / SR
    s = np.sin(2 * np.pi * (f0 * x - 60 * x * x)) * np.exp(-x / 0.05) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.008) * 0.4
    put('fx', mono(s), t, g)


def whistle(t, dur=0.7, g=0.25):
    x = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * (2900 * x + 14 * np.sin(2 * np.pi * 38 * x))) * np.clip(x / 0.02, 0, 1) * np.clip((dur - x) / 0.05, 0, 1)
    s += 0.25 * lowpass(rng.normal(0, 1, len(x)), 6) * np.clip((dur - x) / 0.05, 0, 1)
    put('fx', mono(s), t, g)


def sting(t, g=1.0):
    """The broadcast ident: timpani roll into a four-chord brass fanfare."""
    for k in range(8):
        timp(t + 0.07 * k, 38, 0.18 + 0.05 * k)
    for dt, notes, du in ((0.6, (50, 62, 66, 69), 0.35), (1.0, (50, 62, 66, 69), 0.22), (1.25, (55, 62, 67, 71), 0.4), (1.7, (57, 64, 69, 73, 76), 1.5)):
        for m in notes:
            brass(m, t + dt, du, 0.16 * g)
        timp(t + dt, 38 if dt < 1.2 else 45, 0.5)
    strings(81, t + 1.7, 1.6, 0.07, att=0.2)


def stinger(t):
    """A short two-note tag for the replay wipes."""
    whoosh(t - 0.22, 0.5, 0.5)
    brass(74, t, 0.12, 0.1)
    brass(81, t + 0.1, 0.25, 0.1)


# the commentators, levelled against each other
for i, t0, t1 in E['cues']:
    x = load(os.path.join(VOD, i + '.wav'))
    rms = float(np.sqrt((x ** 2).mean())) + 1e-9
    put('vo', x * (0.085 / rms), t0, 1.0)

# the stadium: a continuous crowd bed, swelling and dropping with the match
cheer = game('crowd_cheer')
bed = np.zeros((n, 2), np.float32)
L = len(cheer)
xf = int(0.8 * SR)
pos = 0
k = 0
while pos < n:
    seg = cheer.copy() if k % 2 == 0 else cheer[::-1].copy()
    seg[:xf] *= np.linspace(0, 1, xf)[:, None]
    seg[-xf:] *= np.linspace(1, 0, xf)[:, None]
    m = min(L, n - pos)
    bed[pos:pos + m] += seg[:m]
    pos += L - xf
    k += 1
bed = np.stack([lowpass(bed[:, 0], 9), lowpass(bed[:, 1], 9)], 1).astype(np.float32)
walk0, walk1 = S['walk hero']['t0'], S['squad pass']['t1']
level = env([(0, 0.0), (0.8, 0.5), (S['booth']['t0'], 0.34), (EV['kick'] - 0.3, 0.34), (EV['kick'] + 0.3, 0.55), (EV['kick'] + 3, 0.38),
             (EV['swat'], 0.38), (EV['swat'] + 0.3, 0.6), (EV['swat'] + 2.5, 0.36), (EV['t1'], 0.36), (EV['t1'] + 0.3, 0.7), (EV['t1'] + 3, 0.34),
             (EV['t2'], 0.34), (EV['t2'] + 0.3, 0.65), (EV['t2'] + 3, 0.28), (EV['use'], 0.25), (EV['use'] + 0.4, 0.1), (EV['walk'], 0.14),
             (walk0 - 0.3, 0.2), (walk0 + 0.6, 0.05), (walk1 - 0.4, 0.05), (walk1 + 0.3, 0.2), (EV['tap'] - 0.3, 0.2), (EV['tap'] + 0.1, 0.02),
             (EV['kfall'] - 0.05, 0.02), (EV['kfall'] + 0.5, 1.0), (EV['kfall'] + 5, 0.8), (S['interview']['t0'], 0.5), (S['interview']['t0'] + 0.6, 0.16),
             (T_CARD - 0.3, 0.14), (T_CARD + 0.4, 0.0)], n)
BUS['amb'] += bed * level[:, None] * 0.55
for name, t, g in (('crowd_cheer', EV['kick'], 0.35), ('crowd_ooh', EV['swat'] + 0.1, 0.55), ('crowd_cheer', EV['t1'] + 0.2, 0.45),
                   ('crowd_boo', EV['t1'] + 0.9, 0.25), ('crowd_ooh', EV['t2'] + 0.1, 0.45), ('crowd_boo', S['exits']['t0'] + 0.4, 0.3),
                   ('crowd_gasp', EV['use'] + 0.15, 0.4), ('crowd_laugh', CUE['c10'][1] + 0.15, 0.5), ('crowd_gasp', EV['tap'] + 0.25, 0.3),
                   ('crowd_cheer', EV['kfall'] + 0.3, 0.9), ('crowd_cheer', EV['kfall'] + 3.5, 0.6)):
    try:
        put('amb', game(name), t, g)
    except Exception as err:
        print('sfx', name, err)

# the opening ident and the tale of the tape
sting(0.15)
t_g = S['giga hero']['t0']
t_p = S['pepe hero']['t0']
t_k = S['kickoff']['t0']
for m in (38, 45, 50, 57):
    strings(m, t_g, t_p - t_g - 0.3, 0.1, att=0.3, rel=0.4, bright=9)
for k in range(int((t_p - t_g) / 0.5)):
    timp(t_g + 0.5 * k, 38 if k % 2 == 0 else 45, 0.3)
brass(62, t_g + 0.1, 0.5, 0.1)
brass(69, t_g + 0.6, 0.9, 0.1)
for m in (47, 54, 59, 62):
    strings(m, t_p, t_k - t_p - 0.3, 0.09, att=0.6, rel=0.5, bright=5)
for k, (m, dt) in enumerate(((74, 0.5), (73, 2.0), (71, 3.6), (66, 5.4))):
    pluck(m, t_p + dt, 0.22, 1.2)

# the match: the game's own battle music under the commentary, until Useless lands
try:
    mus = game('mus_battle')
    need = int((EV['use'] - t_k + 0.3) * SR)
    reps = int(np.ceil(need / len(mus)))
    mus = np.concatenate([mus] * reps)[:need]
    e = env([(0, 0), (0.5, 1), (need / SR - 0.25, 1), (need / SR, 0)], need)
    put('mus', mus * e[:, None], t_k, 0.5)
except Exception as err:
    print('music', err)
whistle(EV['kick'] - 0.05, 0.75, 0.3)
try:
    put('fx', game('battle_start'), EV['kick'], 0.45)
    put('fx', game('deploy_drop'), EV['whale_land'] - 0.15, 0.7)
    put('fx', game('whale_slam'), EV['swat'], 0.9)
    put('fx', game('punch_heavy'), EV['swat'], 0.8)
    put('fx', game('unit_die'), EV['swat'] + 0.3, 0.4)
    for t_, g_ in ((EV['t1'], 1.0), (EV['t2'], 0.9)):
        put('fx', game('tower_destroy'), t_, g_)
        put('fx', game('rocket_explode'), t_, 0.7)
    put('fx', game('tower_destroy'), EV['t1_replay'], 0.5)
    put('fx', game('deploy_spell'), EV['cast'], 0.7)
    put('fx', game('deploy_drop'), EV['use'] - 0.15, 0.6)
    put('fx', game('card_reveal_legendary'), EV['use'] + 0.1, 0.5)
except Exception as err:
    print('sfx', err)
thud(EV['whale_land'], 0.7, 70)
boom(EV['t1'], 46, 2.4, 1.0)
boom(EV['t2'], 46, 2.2, 0.9)
boom(EV['t1_replay'], 40, 2.6, 0.6)
stinger(REPLAY[0])
stinger(REPLAY[1])
thud(EV['use'], 0.5, 110)
pluck(86, EV['use'] + 0.05, 0.3, 1.2)

# the walk: everything drops away; a slow build in D, a heartbeat, then silence for the tap
tw = EV['walk']
ta = S['arrive']['t0']
for k, m in enumerate((38, 50, 57)):
    strings(m, tw + 0.2, walk0 - tw + 0.4, 0.07, att=1.5, rel=0.6, bright=5)
prog = ((38, 50, 57, 62, 65), (36, 48, 55, 60, 64), (34, 46, 53, 58, 62), (33, 45, 52, 57, 61, 64))
seg = (ta + 1.2 - walk0) / 4
for k, notes in enumerate(prog):
    for m in notes:
        strings(m, walk0 + k * seg, seg + 0.3, 0.085 + 0.02 * k, att=0.8, rel=0.9, bright=8)
    for m in notes[2:]:
        choir(m + 12, walk0 + k * seg, seg - 0.6, 0.05 + 0.02 * k)
    timp(walk0 + k * seg, notes[0], 0.55 + 0.08 * k)
t = walk0 + 0.2
while t < walk1:
    thud(t, 0.5, 55)
    thud(t + 0.24, 0.32, 50)
    t += 1.05
for tb in EV['hero_boom']:
    boom(tb, 38, 3.0, 0.9)
    try:
        put('fx', lowpass(game('rocket_explode')[:, 0], 30)[:, None] * np.ones((1, 2), np.float32), tb, 0.8)
    except Exception as err:
        print('sfx', err)
sw = game('swing')
for k in range(4):
    put('fx', sw, EV['pass'] - 0.3 + 0.28 * k, 0.4, 0.6 * (-1) ** k)
whoosh(EV['pass'] - 0.5, 1.6, 0.6)
pluck(61, EV['notice'], 0.3, 0.8)
pluck(49, EV['notice'], 0.25, 1.0)
for m in (33, 45, 57, 61, 64, 69):
    strings(m, ta + 0.2, EV['tap'] - ta - 0.5, 0.11, att=0.6, rel=0.15, bright=9)
x_ = np.arange(int((EV['tap'] - ta) * SR)) / SR
put('mus', mono(lowpass(rng.normal(0, 1, len(x_)), 3) * (x_ / x_[-1]) ** 2 * 0.3), ta, 0.25)      # a cymbal-like rise
# the tap, the silence, the crack
try:
    put('fx', load(os.path.join(SFX, 'ding.wav')), EV['tap'], 0.8)
except Exception as err:
    print('sfx', err)
    pluck(96, EV['tap'], 0.5, 0.8)
tc = EV['crack']
for k in range(7):
    x_ = np.arange(int(0.09 * SR)) / SR
    put('fx', mono(rng.normal(0, 1, len(x_)) * np.exp(-x_ / 0.012)), tc + 0.11 * k * (1 - 0.06 * k), 0.25 + 0.06 * k, 0.4 * (-1) ** k)
x_ = np.arange(int((EV['kfall'] - tc) * SR)) / SR
u_ = x_ / x_[-1]
put('fx', mono(np.sin(2 * np.pi * (150 - 95 * u_) * x_ + 6 * np.sin(2 * np.pi * 17 * x_)) * (0.2 + 0.8 * u_) * 0.5), tc, 0.3)
# the collapse and the win
tk = EV['kfall']
boom(tk, 34, 3.6, 1.4)
boom(tk + 0.03, 58, 2.2, 0.9)
for nm, g_ in (('hq_destroy', 1.0), ('tower_destroy', 0.8), ('house_stomp', 0.7)):
    try:
        put('fx', game(nm), tk, g_)
    except Exception as err:
        print('sfx', nm, err)
try:
    put('mus', game('victory'), tk + 1.0, 0.6)
except Exception as err:
    print('music', err)
ti = S['interview']['t0']
for m in (50, 62, 66, 69, 74, 78):
    strings(m, tk + 0.4, ti - tk - 0.6, 0.1, att=0.3, rel=0.8, bright=9)
for k, m in enumerate((86, 90, 93, 98, 93, 90, 86, 81, 86, 90, 93, 98)):
    pluck(m, tk + 1.2 + k * 0.3, 0.12, 1.2, 0.4 * (-1) ** k)
# the interview: a very long second
try:
    put('fx', load(os.path.join(SFX, 'sniff.wav')), CUE['c14'][1] + 1.2, 0.5, 0.3)
except Exception as err:
    print('sfx', err)
thud(ti + 0.45, 0.25, 140)                                # the microphone arrives
# the end card
sting(T_CARD + 0.05, 0.8)

# mix: music, crowd and effects duck under the commentary
ve = np.abs(BUS['vo']).max(axis=1)
k = int(0.12 * SR)
ve = np.convolve((ve > 0.01).astype(np.float32), np.ones(k) / k, 'same')
ve = np.convolve(ve, np.ones(k * 3) / (k * 3), 'same')
v_ = np.clip(ve * 1.5, 0, 1)[:, None]
act = ve > 0.5
for name in BUS:
    print('bus', name, 'rms while the commentators speak: %.1f dB' % (20 * math.log10(float(np.sqrt((BUS[name][act] ** 2).mean())) + 1e-9)))
mix = BUS['vo'] * 2.6 + BUS['mus'] * (1 - 0.6 * v_) * 0.55 + BUS['fx'] * (1 - 0.4 * v_) * 0.75 + BUS['amb'] * (1 - 0.45 * v_) * 1.0
fo = np.ones(n, np.float32)
i0 = int((END - 1.0) * SR)
fo[i0:int(END * SR)] = np.linspace(1, 0, int(END * SR) - i0)
fo[int(END * SR):] = 0
mix = np.tanh(mix * fo[:, None] * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(END * SR)], SR)
print('MIX-DONE')
