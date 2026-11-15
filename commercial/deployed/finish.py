"""Finish DEPLOYED: grade, captions, the Thumb's HUD on the top-down shots, banners, end card, and the sound mix.

    python3 finish.py FRAMES_DIR OUT_DIR VO_DIR [f1,f2,...]
->  OUT_DIR/c_####.jpg (1920x1080, 24 fps) + mix.wav        (SOUND_ONLY=1 skips the picture)

Picture frames may be .png or .jpg (workers push JPEGs). Sound uses the game's own effects and music
(../comeback/audio) plus synthesized engine drone, klaxon, slide whistle and strings. Nobody has listened to the mix.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textures

A = os.path.join(HERE, '..', 'assets')
AU = os.path.join(HERE, '..', 'comeback', 'audio')
E = json.load(open(os.path.join(HERE, 'edl.json')))
SHOTS = E['shots']
FPS = E['fps']
W, H = 1920, 1080
N3D = E['last']
T_CARD = E['t_card']
T_FILM = E['t_film']
NF = int(round(T_FILM * FPS))
FR, OUT, VOD = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
CARDS_DIR = os.environ.get('CARDS', os.path.join(HERE, 'pack', 'cards'))
os.makedirs(OUT, exist_ok=True)

INK = (20, 10, 39)
WHITE = (255, 255, 255)
GOLD = (255, 205, 80)
COP = (178, 80, 246)
SPEAKER = {'sarge': ('SARGE', (196, 170, 96)), 'egg': ('CUPSEY', (120, 220, 130)), 'ket': ('KET', (240, 150, 170)),
           'chill': ('CHILL GUY', (226, 178, 120)), 'house': ('CHILLHOUSE', (230, 110, 90)), 'pilot': ('PILOT', (130, 180, 255)),
           'sys': ('GAME', (200, 140, 255))}
EVENTS = E['events']


def events(kind):
    return [item for item in EVENTS if item['kind'] == kind]


def first(kind):
    return events(kind)[0]


_fonts = {}


def rub(size, weight=500):
    key = (size, weight)
    if key not in _fonts:
        font = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), size)
        try:
            font.set_variation_by_axes([weight])
        except Exception:
            pass
        _fonts[key] = font
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


def rgba(color, alpha=255):
    return (color[0], color[1], color[2], int(max(0, min(255, alpha))))


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
    return W / 2 + float(v @ right) / z * k, H / 2 - float(v @ up) / z * k


# ---------------------------------------------------------------- picture: grade
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RR = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
VIG = (1 - 0.24 * RR ** 1.4)[..., None]


def punch(a, k):
    if k <= 1.0005:
        return a
    image = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    nw, nh = W / k, H / k
    box = (int((W - nw) / 2), int((H - nh) / 2), int((W - nw) / 2 + nw), int((H - nh) / 2 + nh))
    return np.asarray(image.crop(box).resize((W, H), Image.BILINEAR), np.float32) / 255.0


def grade(a):
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum) * 1.1
    a = np.clip((a - 0.01) * 1.06, 0, 1) ** 1.02
    a = a * np.array([1.02, 1.0, 0.95], np.float32) + 0.03 * (1 - lum) ** 2 * np.array([-0.1, 0.15, 0.5], np.float32)   # warm lights, teal shadows
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.76) / 0.24, 0, 1) * a
    small = Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    bloom = np.asarray(small.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR), np.float32) / 255.0
    return a + bloom * 0.3


# ---------------------------------------------------------------- graphics
def text(d, xy, string, font, fill, anchor='lm', spacing=0, stroke=0, stroke_fill=None):
    if not spacing:
        d.text(xy, string, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)
        return d.textlength(string, font=font)
    widths = [d.textlength(c, font=font) for c in string]
    total = sum(widths) + spacing * (len(string) - 1)
    x = xy[0] - (total / 2 if anchor[0] == 'm' else (total if anchor[0] == 'r' else 0))
    for c, width in zip(string, widths):
        d.text((x, xy[1]), c, font=font, fill=fill, anchor='l' + anchor[1], stroke_width=stroke, stroke_fill=stroke_fill)
        x += width + spacing
    return total


def draw_captions(d, t, y=None):
    for cue in E['cues']:
        if cue['f'] - 0.05 <= t < cue['f'] + cue['dur'] + 0.15:
            tag, color = SPEAKER[cue['who']]
            font = rub(34, 500)
            tag_w = d.textlength(tag, font=rub(24, 800)) + 30
            line_w = d.textlength(cue['sub'], font=font) + 44
            top = y if y is not None else H - 104
            x = W / 2 - (tag_w + line_w) / 2
            d.rounded_rectangle((x, top, x + tag_w + line_w, top + 56), 10, fill=rgba((0, 0, 0), 205))
            d.rounded_rectangle((x, top, x + tag_w, top + 56), 10, fill=rgba(color, 250))
            d.rectangle((x + tag_w - 10, top, x + tag_w, top + 56), fill=rgba(color, 250))
            text(d, (x + tag_w / 2, top + 29), tag, rub(24, 800), rgba(INK, 255), 'mm')
            text(d, (x + tag_w + 22, top + 29), cue['sub'], font, rgba(WHITE, 255))


def draw_title(d, t):
    item = first('title')
    t0 = item['f']
    if t0 <= t < t0 + 4.6:
        string = item['text']
        shown = string[:int(max(0, (t - t0) / 0.045))]
        alpha = 255 * fade(t, t0, t0 + 4.6, 0.4)
        text(d, (96, H - 150), shown, rub(34, 700), rgba(WHITE, alpha), 'lm', 8, 3, rgba(INK, alpha))
        if int(t * 3) % 2 == 0 and len(shown) < len(string):
            width = sum(d.textlength(c, font=rub(34, 700)) + 8 for c in shown)
            d.rectangle((96 + width + 4, H - 168, 96 + width + 22, H - 132), fill=rgba(WHITE, alpha))
    wide = next(s for s in SHOTS if s['name'] == 'hold_wide')
    if wide['t0'] + 0.3 <= t < wide['t1']:
        k = out_back((t - wide['t0'] - 0.3) / 0.45)
        alpha = 255 * fade(t, wide['t0'] + 0.3, wide['t1'], 0.3)
        text(d, (W / 2, H / 2 - 30 + 40 * (1 - k)), 'DEPLOYED', lil(210), rgba(GOLD, alpha), 'mm', 14, 10, rgba(INK, alpha))
        text(d, (W / 2, H / 2 + 110), 'A MEME ROYALE STORY', rub(34, 700), rgba(WHITE, alpha), 'mm', 12, 3, rgba(INK, alpha))


_cache = {}


def card_art(uid, size):
    key = (uid, size)
    if key not in _cache:
        art = Image.open(os.path.join(CARDS_DIR, uid + '.webp')).convert('RGBA').resize(size, Image.LANCZOS)
        mask = Image.new('L', size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), 16, fill=255)
        art.putalpha(mask)
        _cache[key] = art
    return _cache[key]


HUD_HAND = {'lmao': (['lmao', 'airdrop', 'chillhouse', 'cupsey'], 4, '2:41'), 'airdrop': (['airdrop', 'chillhouse', 'cupsey'], 3, '2:10'),
            'chillhouse': (['chillhouse', 'cupsey'], 10, '0:58'), 'cupsey': (['cupsey'], 4, '0:30')}
COST = {'lmao': 4, 'airdrop': 3, 'chillhouse': 5, 'cupsey': 4}


def draw_hud(im, t):
    """On the top-down shots we see what the Thumb sees: the game's HUD, his card, and his thumb."""
    for item in events('hud'):
        if not item['f'] <= t < item['f1']:
            continue
        d = ImageDraw.Draw(im, 'RGBA')
        hand, copium, clock = HUD_HAND[item['card']]
        d.rectangle((0, 0, W, 86), fill=rgba(INK, 235))
        text(d, (40, 44), 'ARENA 2  ·  BACKYARD BBQ', lil(40), rgba(GOLD, 255))
        text(d, (W - 40, 44), clock, lil(46), rgba(WHITE, 255), 'rm')
        text(d, (W / 2, 44), "THE THUMB'S VIEW", rub(26, 800), rgba((255, 120, 120), 255 if int(t * 2) % 2 == 0 else 150), 'mm', 8)
        d.rectangle((0, H - 250, W, H), fill=rgba(INK, 225))
        card_w, card_h, gap = 150, 188, 22
        x0 = W / 2 - (len(hand) * card_w + (len(hand) - 1) * gap) / 2
        for index, uid in enumerate(hand):
            x = int(x0 + index * (card_w + gap))
            y = H - 236 - (22 if uid == item['card'] else 0)
            im.alpha_composite(card_art(uid, (card_w, card_h)), (x, y))
            d.rounded_rectangle((x - 3, y - 3, x + card_w + 3, y + card_h + 3), 18, outline=rgba(GOLD if uid == item['card'] else INK, 255),
                                width=6)
            d.ellipse((x - 14, y - 14, x + 36, y + 36), fill=rgba(COP, 255), outline=rgba(INK, 255), width=4)
            text(d, (x + 11, y + 11), str(COST[uid]), lil(30), rgba(WHITE, 255), 'mm')
        bar_x, bar_w = 300, W - 600
        d.rounded_rectangle((bar_x - 6, H - 40, bar_x + bar_w + 6, H - 10), 10, fill=rgba((10, 5, 20), 255))
        seg = bar_w / 10
        for k in range(10):
            d.rounded_rectangle((bar_x + k * seg + 3, H - 36, bar_x + (k + 1) * seg - 3, H - 14), 6,
                                fill=rgba(COP if k < copium else (44, 21, 84), 255))
        u = (t - item['f']) / (item['f1'] - item['f'])
        s = shot_at(t)
        tx, ty = project(s, t, s['l0'])
        if item.get('target'):
            radius = 150 + 14 * math.sin(t * 9)
            d.ellipse((tx - radius, ty - radius, tx + radius, ty + radius), outline=rgba((255, 230, 90), 230), width=10)
            d.ellipse((tx - radius * 0.55, ty - radius * 0.55, tx + radius * 0.55, ty + radius * 0.55), outline=rgba((255, 230, 90), 150), width=5)
        press = ease(u / 0.25) * (1 - ease((u - 0.55) / 0.3))                 # the thumb comes down, taps, and leaves
        textures.thumb(im, int(tx + 60), int(ty + 40 + 520 * (1 - press)), press=press > 0.9)


def draw_banner(d, t):
    for item in events('banner'):
        if item['f'] <= t < item['f1']:
            k = out_back((t - item['f']) / 0.3)
            alpha = 255 * fade(t, item['f'], item['f1'], 0.2)
            height = 150 * k
            d.rectangle((0, H / 2 - 60 - height / 2, W, H / 2 - 60 + height / 2), fill=rgba((150, 20, 30), alpha * 0.92))
            d.rectangle((0, H / 2 - 60 - height / 2, W, H / 2 - 60 - height / 2 + 6), fill=rgba(GOLD, alpha))
            d.rectangle((0, H / 2 - 60 + height / 2 - 6, W, H / 2 - 60 + height / 2), fill=rgba(GOLD, alpha))
            text(d, (W / 2, H / 2 - 60), item['text'], lil(64), rgba(WHITE, alpha), 'mm', 3, 5, rgba(INK, alpha))
    for item in events('victory'):
        if item['f'] <= t < item['f1']:
            u = t - item['f']
            k = out_back(u / 0.4)
            alpha = 255 * fade(t, item['f'], item['f1'], 0.25)
            rng = np.random.default_rng(3)
            for _ in range(140):                                               # confetti
                x0, speed, phase, size = rng.uniform(0, W), rng.uniform(260, 620), rng.uniform(0, 6.28), rng.uniform(8, 18)
                color = [(255, 205, 80), (178, 80, 246), (90, 200, 255), (255, 110, 130), (120, 230, 140)][int(rng.integers(0, 5))]
                y = -60 + speed * u + 40 * math.sin(phase + u * 3)
                x = x0 + 50 * math.sin(phase + u * 2.2)
                if 0 < y < H:
                    d.rectangle((x, y, x + size, y + size * 0.6), fill=rgba(color, alpha))
            text(d, (W / 2, 250 + 60 * (1 - k)), 'VICTORY!', lil(260), rgba(GOLD, alpha), 'mm', 10, 12, rgba(INK, alpha))


BG = None


def end_card(t):
    global BG
    if BG is None:
        back = Image.open(os.path.join(A, 'bg_title_wide.jpg')).convert('RGB')
        k = max(W / back.width, H / back.height)
        back = back.resize((int(back.width * k) + 1, int(back.height * k) + 1), Image.LANCZOS)
        back = back.crop(((back.width - W) // 2, (back.height - H) // 2, (back.width - W) // 2 + W, (back.height - H) // 2 + H))
        BG = (np.asarray(back.filter(ImageFilter.GaussianBlur(14)), np.float32) / 255.0 * 0.34, Image.open(os.path.join(A, 'logo.png')).convert('RGBA'))
    back, logo = BG
    u = t - T_CARD
    a = back * ease(u / 0.5) * (1 - 0.5 * RR)[..., None]
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    k = ease((u - 0.15) / 0.5)
    size = int(470 * (1.06 - 0.06 * k))
    mark = logo.resize((size, int(size * logo.height / logo.width)), Image.LANCZOS)
    mark.putalpha(mark.getchannel('A').point(lambda v: int(v * k)))
    im.alpha_composite(mark, ((W - mark.width) // 2, 210 - (mark.height - 446) // 2))
    d = ImageDraw.Draw(im, 'RGBA')
    k2 = ease((u - 0.9) / 0.5)
    text(d, (W / 2, 740), 'FREE TO PLAY', rub(56, 800), rgba((255, 236, 200), 255 * k2), 'mm', 10)
    text(d, (W / 2, 815), 'memeroyale.imaginestudio.fun', rub(32, 500), rgba(WHITE, 190 * k2), 'mm', 2)
    k3 = ease((u - 3.4) / 0.4)
    text(d, (W / 2, 905), 'PLAY BETTER THAN THIS GUY', rub(30, 800), rgba(GOLD, 230 * k3), 'mm', 7)
    if k3 > 0:
        textures.thumb(im, W - 330, int(H - 300 + 400 * (1 - out_back(k3))))
    d = ImageDraw.Draw(im, 'RGBA')
    draw_captions(d, t, y=H - 84)
    fade_out = ease((T_FILM - t) / 0.5)
    if fade_out < 1:
        im = Image.fromarray((np.asarray(im.convert('RGB'), np.float32) * fade_out).astype(np.uint8))
    return im.convert('RGB')


BOOM = first('boom')['f']
POP = first('pop')['f']
FREEZE = first('freeze')['f']


def frame(f):
    t = (f - 1) / FPS
    if f > N3D:
        im = end_card(t)
    else:
        path = next(q for q in (os.path.join(FR, f'f_{f:04d}.png'), os.path.join(FR, f'f_{f:04d}.jpg')) if os.path.exists(q))
        src = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)
        src = src.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))
        a = np.asarray(src, np.float32) / 255.0
        zoom = 1.0 + 0.06 * decay(t, BOOM, 0.7) ** 2 + 0.03 * decay(t, POP, 0.4) ** 2
        a = grade(punch(a, zoom))
        flash = 0.4 * decay(t, BOOM, 0.2)
        if flash > 0:
            a = a * (1 - flash) + np.array([1.0, 0.9, 0.75], np.float32) * flash * 1.15
        if FREEZE <= t < FREEZE + 3.0:                                         # the world goes a little grey while they are frozen
            lum = a.mean(axis=2, keepdims=True)
            k = 0.35 * fade(t, FREEZE, FREEZE + 3.0, 0.3)
            a = a * (1 - k) + lum * k
        a = a * VIG * ease(t / 0.8) * ease((T_CARD - t) / 0.12)
        a = a + np.random.default_rng(f).normal(0, 0.007, (H, W, 1)).astype(np.float32)
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        draw_hud(im, t)
        d = ImageDraw.Draw(im, 'RGBA')
        draw_title(d, t)
        draw_banner(d, t)
        in_hud = any(item['f'] <= t < item['f1'] for item in events('hud'))
        draw_captions(d, t, y=H - 330 if in_hud else None)
        im = im.convert('RGB')
    im.save(os.path.join(OUT, f'c_{f:04d}.jpg'), quality=95, subsampling=0)


for f in ([] if os.environ.get('SOUND_ONLY') else (ONLY or range(1, NF + 1))):
    frame(f)
print('FRAMES-DONE')
if ONLY:
    sys.exit(0)

# ================================================================ sound
SR = 48000
END = NF / FPS
n = int(END * SR) + SR
rng = np.random.default_rng(23)
BUS = {k: np.zeros((n, 2), np.float32) for k in ('vo', 'mus', 'amb', 'fx')}


def load(path):
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(result.stdout, np.float32).reshape(-1, 2).copy()


def game(name):
    return load(os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3')))


def put(bus, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    m = min(len(x), n - i)
    if m > 0 and i >= 0:
        BUS[bus][i:i + m] += x[:m] * gain * np.array([1 - max(0, pan), 1 + min(0, pan)], np.float32)


def mono(signal):
    return np.stack([signal, signal], 1).astype(np.float32)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, 'same')


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def strings(m, t, dur, gain=0.1, attack=1.2, release=1.6, bright=7):
    length = int((dur + release) * SR)
    x = np.arange(length) / SR
    signal = np.zeros(length)
    for detune in (-0.06, 0.0, 0.07):
        phase = 2 * np.pi * midi(m + detune) * x + 0.9 * np.sin(2 * np.pi * (4.6 + detune * 3) * x) * np.clip(x / 1.5, 0, 1)
        for h in range(1, bright + 1):
            signal += np.sin(phase * h + h * detune * 20) / h ** 1.35
    envelope = np.clip(x / attack, 0, 1) ** 1.5 * np.clip((dur + release - x) / release, 0, 1) ** 1.5
    put('mus', mono(signal * envelope), t, gain / 3)


def brass(m, t, dur, gain=0.12):
    length = int((dur + 0.25) * SR)
    x = np.arange(length) / SR
    signal = np.zeros(length)
    for detune in (-0.04, 0.05):
        for h in range(1, 13):
            signal += np.sin(2 * np.pi * midi(m + detune) * h * x) / h ** 0.9 * np.clip(x / (0.02 + 0.01 * h), 0, 1)
    envelope = np.clip(x / 0.03, 0, 1) * np.clip((dur + 0.25 - x) / 0.25, 0, 1) * (0.75 + 0.25 * np.exp(-x / 0.15))
    put('mus', mono(signal * envelope), t, gain / 4)


def snare(t, gain=0.2):
    x = np.arange(int(0.16 * SR)) / SR
    signal = rng.normal(0, 1, len(x)) * np.exp(-x / 0.035) + 0.5 * np.sin(2 * np.pi * 190 * x) * np.exp(-x / 0.02)
    put('mus', mono(signal), t, gain)


def thud(t, gain=0.5, f0=90, bus='fx'):
    x = np.arange(int(0.3 * SR)) / SR
    signal = np.sin(2 * np.pi * (f0 * x - 60 * x * x)) * np.exp(-x / 0.05) + rng.normal(0, 1, len(x)) * np.exp(-x / 0.008) * 0.4
    put(bus, mono(signal), t, gain)


def whoosh(t, dur=1.0, gain=0.4):
    x = np.arange(int(dur * SR)) / SR
    u = x / dur
    noise = lowpass(rng.normal(0, 1, len(x)), 120) * 12
    envelope = np.sin(np.pi * u) ** 2
    put('fx', mono(noise * envelope + 0.25 * np.sin(2 * np.pi * (80 + 300 * u) * x) * envelope), t, gain)


def tone(t, f0, f1, dur, gain=0.2, vibrato=0.0, shape=1.0):
    """A sine glide from f0 to f1: slide whistle (falling), squeak (rising), blips."""
    x = np.arange(int(dur * SR)) / SR
    u = x / dur
    freq = f0 * (f1 / f0) ** (u ** shape)
    phase = 2 * np.pi * np.cumsum(freq) / SR + vibrato * np.sin(2 * np.pi * 7 * x)
    signal = (np.sin(phase) + 0.3 * np.sin(2 * phase)) * np.clip(x / 0.02, 0, 1) * np.clip((dur - x) / 0.05, 0, 1)
    put('fx', mono(signal), t, gain)


def klaxon(t, dur=1.4, gain=0.22):
    x = np.arange(int(dur * SR)) / SR
    gate = (np.sin(2 * np.pi * 2.2 * x) > -0.2).astype(np.float32)
    signal = np.sign(np.sin(2 * np.pi * 310 * x)) * 0.5 + np.sign(np.sin(2 * np.pi * 466 * x)) * 0.35
    put('fx', mono(lowpass(signal, 8) * gate * np.clip((dur - x) / 0.1, 0, 1)), t, gain)


def splash(t, gain=0.5):
    x = np.arange(int(1.6 * SR)) / SR
    signal = lowpass(rng.normal(0, 1, len(x)), 14) * 4 * np.exp(-x / 0.45) * np.clip(x / 0.03, 0, 1)
    put('fx', mono(signal), t, gain)
    thud(t, 0.5, 60)


def boing(t, gain=0.3):
    x = np.arange(int(0.9 * SR)) / SR
    freq = 120 + 260 * np.exp(-x / 0.25) * (1 + 0.5 * np.sin(2 * np.pi * 11 * x))
    signal = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-x / 0.35)
    put('fx', mono(signal), t, gain)


def is_hold(s):
    return s['p0'][2] > 30 and not s['name'].startswith('thumb_view')


# dialogue: levelled; the pilot through a radio, the game's announcer slightly bright
for cue in E['cues']:
    x = load(os.path.join(VOD, cue['id'] + '.wav'))
    x = x * (0.085 / (float(np.sqrt((x ** 2).mean())) + 1e-9))
    if cue['who'] == 'pilot':
        m = x[:, 0]
        m = m - lowpass(m, 60)                                                  # thin it out, add hiss and a click
        m = np.tanh(lowpass(m, 5) * 5) * 0.4 + rng.normal(0, 0.004, len(m))
        x = mono(m)
        tone(cue['f'] - 0.12, 1800, 1800, 0.06, 0.08)
        tone(cue['f'] + cue['dur'] + 0.05, 1400, 1400, 0.06, 0.08)
    put('vo', x, cue['f'], 1.0)

# ambience: engine drone in the hold (louder wind once the ramp is open), a quiet garden outside
t_ramp = first('ramp')['f']
length = n
x = np.arange(length) / SR
drone = (np.sin(2 * np.pi * 55 * x) + 0.6 * np.sin(2 * np.pi * 82.5 * x + 0.5 * np.sin(2 * np.pi * 0.7 * x)) + 0.4 * np.sin(2 * np.pi * 110.3 * x)) * 0.05
drone += lowpass(rng.normal(0, 1, length), 90) * 0.5 * (1 + 0.3 * np.sin(2 * np.pi * 9.5 * x))
wind = lowpass(rng.normal(0, 1, length), 18) * 0.5 * (1 + 0.4 * np.sin(2 * np.pi * 0.23 * x))
hold_env = np.zeros(length, np.float32)
wind_env = np.zeros(length, np.float32)
yard_env = np.zeros(length, np.float32)
for s in SHOTS:
    i0, i1 = int(s['t0'] * SR), int(s['t1'] * SR)
    if is_hold(s):
        hold_env[i0:i1] = 1.0
        wind_env[i0:i1] = 0.9 if s['t0'] >= t_ramp else 0.0
    else:
        yard_env[i0:i1] = 1.0
        wind_env[i0:i1] = 0.25
smooth = int(0.08 * SR)
for env_ in (hold_env, wind_env, yard_env):
    env_[:] = np.convolve(env_, np.ones(smooth) / smooth, 'same')
BUS['amb'] += mono(drone * hold_env * 0.9 + wind * wind_env * 0.5)
birds = np.zeros(length)
for k in range(int(END * 1.3)):
    tb = rng.uniform(0, END)
    xb = np.arange(int(0.12 * SR)) / SR
    chirp = np.sin(2 * np.pi * (rng.uniform(2600, 4200) + 900 * np.sin(2 * np.pi * rng.uniform(18, 30) * xb)) * xb) * np.sin(np.pi * xb / 0.12) ** 2
    i = int(tb * SR)
    birds[i:i + len(chirp)] += chirp[:max(0, length - i)] * rng.uniform(0.2, 0.6)
BUS['amb'] += mono(birds * yard_env * 0.05)

# music: a snare march under the briefing, the game's battle music on the ground, strings for the speech
brief0 = next(s for s in SHOTS if s['name'] == 'hold_wide')['t0']
brief1 = t_ramp
beat = 0.5
k = 0
while brief0 + k * beat < brief1:
    tb = brief0 + k * beat
    snare(tb, 0.1)
    if k % 2 == 1:
        snare(tb + beat * 0.5, 0.06)
        snare(tb + beat * 0.75, 0.06)
    if k % 8 == 0:
        thud(tb, 0.25, 60, 'mus')
    k += 1
battle = game('mus_battle')
loop = np.concatenate([battle] * (int(END * SR / len(battle)) + 2))[:n]
music_env = np.zeros(n, np.float32)
t_swell = first('music_swell')['f']
t_scream = first('scream')['f']
for s in SHOTS:
    if not is_hold(s) and not (t_swell <= s['t0'] < FREEZE + 4) and s['name'] != 'ext_ship':
        music_env[int(s['t0'] * SR):int(s['t1'] * SR)] = 1.0
music_env[int(t_ramp * SR):int(t_swell * SR)] = np.maximum(music_env[int(t_ramp * SR):int(t_swell * SR)], 0.35)
music_env[int(FREEZE * SR):] = 0.0
music_env = np.convolve(music_env, np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
BUS['mus'] += loop * music_env[:, None] * 0.22
for m, dt, dur in ((50, 0.0, 9.0), (57, 0.0, 9.0), (62, 1.0, 8.0), (66, 3.2, 5.8), (69, 5.2, 4.0), (74, 6.6, 2.8)):   # the speech: a noble D major
    strings(m, t_swell + dt, min(dur, t_scream - t_swell - dt + 0.4), 0.11, attack=1.6, release=0.5)
for m in (38, 45, 50, 57, 62):                                                  # opening pad
    strings(m, 0.2, 7.5, 0.06, attack=2.5, release=2.0, bright=5)

# effects
for item in events('klaxon'):
    klaxon(item['f'])
whoosh(t_ramp, 2.2, 0.5)
thud(t_ramp + 2.0, 0.6, 70)
put('fx', game('laugh_blast'), first('laugh')['f'], 0.5)
fall_whistles = [(first('laugh')['f'] + 1.6, 2.2), (first('pop')['f'] + 0.1, 2.1), (t_scream, 4.6)]
for t0, dur in fall_whistles:
    tone(t0, 1900, 420, dur, 0.1, vibrato=0.6, shape=1.4)
tone(t_scream, 900, 1500, 0.5, 0.12, vibrato=2.0)                               # the egg's yelp on the way out
tone(t_scream + 0.5, 1500, 700, 3.6, 0.07, vibrato=3.0)
for item in events('land'):
    put('fx', game('deploy_drop'), item['f'] - 0.05, 0.6)
    thud(item['f'], 0.5, 80)
for item in events('bonk'):
    put('fx', game('punch_heavy'), item['f'], 0.55)
put('fx', game('unit_die'), first('unit_die')['f'], 0.6)
put('fx', game('swing'), first('kick')['f'] - 0.1, 0.6)
thud(first('kick')['f'], 0.6, 110)
put('fx', game('deploy_spell'), first('coins')['f'], 0.5)
for item in events('plop'):
    tone(item['f'], rng.uniform(900, 1500), rng.uniform(500, 700), 0.09, 0.05 if item.get('quiet') else 0.16)
lucky = [item for item in events('plop') if not item.get('quiet')][0]
put('fx', game('w_gain'), lucky['f'], 0.5)
put('fx', game('tower_destroy'), BOOM, 0.8)
put('fx', game('rocket_explode'), BOOM, 0.6)
put('fx', game('emote_pop'), first('emote')['f'], 0.7)
alarm = first('alarm')
tb = alarm['f']
while tb < alarm['f1']:
    tone(tb, 880, 880, 0.18, 0.07)
    tone(tb + 0.25, 660, 660, 0.18, 0.07)
    tb += 0.55
thud(first('thud')['f'], 0.9, 70)
put('fx', game('house_stomp'), first('thud')['f'], 0.6)
tone(POP, 300, 1400, 0.09, 0.3)
thud(POP, 0.5, 140)
boing(first('boing')['f'], 0.4)
splash(first('splash')['f'], 0.5)
tone(first('squeak')['f'], 1500, 2300, 0.14, 0.2)
tone(first('squeak')['f'] + 0.16, 2300, 1400, 0.18, 0.2)
put('fx', game('swing'), first('shove')['f'], 0.6)
tone(FREEZE, 600, 90, 0.5, 0.25, shape=0.6)                                     # everything winds down
for item in events('blip'):
    tone(item['f'], 1200, 800, 0.1, 0.12)
for item in events('clunk'):
    thud(item['f'], 0.5, 120)
put('fx', game('victory'), first('victory')['f'], 0.6)
put('fx', game('crowd_cheer'), first('cheer')['f'], 0.35)
put('fx', game('crowd_boo'), first('groan')['f'], 0.3)
menu = game('mus_menu')
put('mus', menu[:int((T_FILM - T_CARD + 0.5) * SR)], T_CARD, 0.3)

# mix: music, ambience and effects duck under speech
speech = np.abs(BUS['vo']).max(axis=1)
k = int(0.12 * SR)
speech = np.convolve((speech > 0.01).astype(np.float32), np.ones(k) / k, 'same')
speech = np.convolve(speech, np.ones(k * 3) / (k * 3), 'same')
duck = np.clip(speech * 1.5, 0, 1)[:, None]
active = speech > 0.5
for name in BUS:
    level = 20 * math.log10(float(np.sqrt((BUS[name][active] ** 2).mean())) + 1e-9)
    print(f'bus {name} rms while someone speaks: {level:.1f} dB')
mix = BUS['vo'] * 2.6 + BUS['mus'] * (1 - 0.6 * duck) * 0.6 + BUS['fx'] * (1 - 0.35 * duck) * 0.8 + BUS['amb'] * (1 - 0.5 * duck) * 0.8
fade_out = np.ones(n, np.float32)
i0 = int((END - 1.0) * SR)
fade_out[i0:int(END * SR)] = np.linspace(1, 0, int(END * SR) - i0)
fade_out[int(END * SR):] = 0
mix = np.tanh(mix * fade_out[:, None] * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(END * SR)], SR)
print('MIX-DONE')
