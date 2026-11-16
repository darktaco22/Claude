"""Finish DEPLOYED: grade, captions, the Thumb's HUD and tower health on the arena shots, banners, end card and the sound mix.

    python3 finish.py FRAMES_DIR OUT_DIR VO_DIR [f1,f2,...]
->  OUT_DIR/c_####.jpg (1920x1080, 24 fps) + mix.wav        (SOUND_ONLY=1 skips the picture)

Frames may be .png or .jpg. The HUD and the clock come from the recorded match (pack/match.json), the same data that
drove the animation. Sound: the game's own effects and music (../comeback/audio), its announcer lines (a_*), Kokoro
voices for the characters and a few synthesized sounds. Nobody has listened to the mix.
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
import monitor
import textures

A = os.path.join(HERE, '..', 'assets')
AU = os.path.join(HERE, '..', 'comeback', 'audio')
PACK = os.path.join(HERE, 'pack')
E = json.load(open(os.path.join(HERE, 'edl.json')))
MATCH = json.load(open(os.path.join(PACK, 'match.json')))
STATE = monitor.State(MATCH)
SHOTS = E['shots']
FPS = E['fps']
PRE = E['pre']
W, H = 1920, 1080
N3D = E['last']
T_CARD = E['t_card']
T_FILM = E['t_film']
NF = int(round(T_FILM * FPS))
FR, OUT, VOD = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
CARDS_DIR = os.environ.get('CARDS', os.path.join(PACK, 'cards'))
os.makedirs(OUT, exist_ok=True)

INK = (20, 10, 39)
WHITE = (255, 255, 255)
GOLD = (255, 205, 80)
COP = (178, 80, 246)
SPEAKER = {'sarge': ('SARGE', (196, 170, 96)), 'egg': ('CUPSEY', (120, 220, 130)), 'ket': ('KET', (240, 150, 170)),
           'chill': ('CHILL GUY', (226, 178, 120)), 'house': ('CHILLHOUSE', (230, 110, 90)), 'pilot': ('PILOT', (130, 180, 255)),
           'game': ('GAME', (200, 140, 255))}
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


def match_time(t):
    """Film time to match time (negative before the match)."""
    s = shot_at(t)
    return s['a0'] + (t - s['t0']) * s['s0'] - PRE


def project(s, t, point):
    """Screen position of a world point in shot s at film time t (pinhole camera, no handheld shake); None if behind the camera."""
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
    if z < 0.3:
        return None
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
    a = a * np.array([1.02, 1.0, 0.95], np.float32) + 0.03 * (1 - lum) ** 2 * np.array([-0.1, 0.15, 0.5], np.float32)
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
    wide = next(s for s in SHOTS if s['name'] == 'hold_wide')
    if wide['t0'] + 0.3 <= t < wide['t1']:
        k = out_back((t - wide['t0'] - 0.3) / 0.45)
        alpha = 255 * fade(t, wide['t0'] + 0.3, wide['t1'], 0.3)
        text(d, (W / 2, H / 2 - 30 + 40 * (1 - k)), 'DEPLOYED', lil(210), rgba(GOLD, alpha), 'mm', 14, 10, rgba(INK, alpha))
        text(d, (W / 2, H / 2 + 110), 'A MEME ROYALE STORY', rub(34, 700), rgba(WHITE, alpha), 'mm', 12, 3, rgba(INK, alpha))


def banner(d, t, f0, f1, string, color=(150, 20, 30)):
    if f0 <= t < f1:
        k = out_back((t - f0) / 0.3)
        alpha = 255 * fade(t, f0, f1, 0.2)
        height = 150 * k
        y = 190
        d.rectangle((0, y - height / 2, W, y + height / 2), fill=rgba(color, alpha * 0.92))
        d.rectangle((0, y - height / 2, W, y - height / 2 + 6), fill=rgba(GOLD, alpha))
        d.rectangle((0, y + height / 2 - 6, W, y + height / 2), fill=rgba(GOLD, alpha))
        text(d, (W / 2, y), string, lil(72), rgba(WHITE, alpha), 'mm', 3, 5, rgba(INK, alpha))


def draw_banners(d, t):
    for item in events('tower_down'):
        banner(d, t, item['f'] + 0.1, item['f'] + 2.4, 'YOUR TOWER FELL' if item['team'] == 0 else 'ENEMY TOWER DOWN!',
               (150, 20, 30) if item['team'] == 0 else (24, 120, 50))
    for item in events('overdose'):
        banner(d, t, item['f'], item['f'] + 2.6, 'COPIUM OVERDOSE  x2', (92, 36, 160))
    for item in events('victory'):
        if item['f'] <= t < item['f1']:
            u = t - item['f']
            alpha = 255 * fade(t, item['f'], item['f1'], 0.25)
            rng = np.random.default_rng(3)
            for _ in range(140):
                x0, speed, phase, size = rng.uniform(0, W), rng.uniform(260, 620), rng.uniform(0, 6.28), rng.uniform(8, 18)
                color = [(255, 205, 80), (178, 80, 246), (90, 200, 255), (255, 110, 130), (120, 230, 140)][int(rng.integers(0, 5))]
                y = -60 + speed * u + 40 * math.sin(phase + u * 3)
                x = x0 + 50 * math.sin(phase + u * 2.2)
                if 0 < y < H:
                    d.rectangle((x, y, x + size, y + size * 0.6), fill=rgba(color, alpha))
            text(d, (W / 2, 250 + 60 * (1 - out_back(u / 0.4))), 'VICTORY!', lil(260), rgba(GOLD, alpha), 'mm', 10, 12, rgba(INK, alpha))


TOWER_MAX = {'rig': 2600, 'hq': 4400}
import hud
PW, PH = 720, 1558                       # the phone picture is drawn at this size, then fitted into the film frame
PK = PW / 924.0
OPPONENT = 'ULTRA CHAD'
DRAG_LEAD = 0.85
PLAYS = [item for item in MATCH['log'] if item['what'] == 'thumb']
ILLEGAL = [item for item in MATCH['log'] if item['what'] == 'illegal']
DOWNS = [item for item in MATCH['log'] if item['what'] == 'tower_down']


def project_px(s, t, point, cw, ch):
    """Pinhole projection into a cw x ch image (Blender sensor fit: 36 mm across the larger side)."""
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
    if z < 0.3:
        return None
    lens = s['lens'] + (s['lens1'] - s['lens']) * u
    k = lens / 36.0 * max(cw, ch)
    return cw / 2 + float(v @ right) / z * k, ch / 2 - float(v @ up) / z * k


def gpt(x, z, h=0.0):
    return (x - 9.0, 16.0 - z, h)


def draw_towers(im, s, t, m, cw, ch, k):
    frame = STATE.frame(max(0.0, m))
    for e in frame['e']:
        if e[1] != 't' or e[9]:
            continue
        spot = project_px(s, t, gpt(e[4], e[5], 5.0 if e[2] == 'rig' else 6.0), cw, ch)
        if spot is None or not (-60 < spot[0] < cw + 60 and -60 < spot[1] < ch + 60):
            continue
        hud.hp_pill(im, spot[0], spot[1] + (0 if e[2] == 'rig' else 8 * k), k, e[8], e[3])


def ease_io(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def phone_state(m):
    state = dict(STATE.at(m))
    state['press'] = None
    return state


def draw_phone_hud(im, s, t):
    """The game's screen, drawn on a PW x PH picture of the arena from the game's camera."""
    m = match_time(t)
    cw, ch = im.size
    state = phone_state(m)
    d = ImageDraw.Draw(im, 'RGBA')
    draw_towers(im, s, t, m, cw, ch, PK)
    river = project_px(s, t, gpt(18.0, 16.0, 0.0), cw, ch)
    hud.top_pills(im, PK, OPPONENT, 7521, state['clock'] if m >= 0 else 180, True, y=40 * PK)
    hud.w_badges(im, PK, state['ws'], river[1] if river else ch * 0.42)
    box = hud.tray_box(cw, ch, PK)
    hud.emote_button(im, PK, 28 * PK, box[1] - 112 * PK)
    drag = None
    # a drag in progress (or an illegal one): the card follows the finger from its slot to the spot
    items = [(p['t'], p['slot'], p['x'], p['z'], False, p['card']) for p in PLAYS]
    for item in ILLEGAL:
        hand_now, _, _ = STATE.hand_queue(item['t'] - 0.01)
        if item['card'] in hand_now:
            items.append((item['t'], hand_now.index(item['card']), item.get('x', 9.0), item.get('z', 8.0), True, item['card']))
    for tp, slot, gx, gz, bad, card in items:
        lead = 1.1 if bad else DRAG_LEAD
        if tp - lead <= m < tp:
            u = ease_io((m - (tp - lead)) / (lead * 0.92))
            x0 = box[0] + (183 + 177 * slot + 76) * PK
            y0 = box[1] + (25 + 95) * PK
            target = project_px(s, t, gpt(gx, gz, 0.0), cw, ch)
            if target is not None:
                gxp, gyp = x0 + (target[0] - x0) * u, y0 + (target[1] - y0) * u
                drag = (slot, gxp, gyp)
                ring = (200, 70, 90, 150) if bad else (120, 235, 130, 150)
                if u > 0.15:
                    rr = 62 * PK
                    d.ellipse((target[0] - rr, target[1] - rr * 0.55, target[0] + rr, target[1] + rr * 0.55), fill=ring, outline=(255, 255, 255, 220), width=max(2, int(3 * PK)))
        if bad and tp <= m < tp + 0.55:                   # the card slides back
            slot_x = box[0] + (183 + 177 * slot + 76) * PK
            target = project_px(s, t, gpt(gx, gz, 0.0), cw, ch)
            if target is not None:
                u = ease_io((m - tp) / 0.5)
                drag = (slot, target[0] + (slot_x - target[0]) * u, target[1] + (box[1] + 120 * PK - target[1]) * u)
        if not bad and tp <= m < tp + 0.7:                # the drop: a ring spreads out where the unit lands
            target = project_px(s, t, gpt(gx, gz, 0.0), cw, ch)
            if target is not None:
                u = (m - tp) / 0.7
                rr = (40 + 90 * u) * PK
                d.ellipse((target[0] - rr, target[1] - rr * 0.55, target[0] + rr, target[1] + rr * 0.55), outline=(255, 255, 255, int(220 * (1 - u))), width=max(2, int(4 * PK)))
        if not bad and tp <= m < tp + 1.8:                # the card's name floats up from the spot
            target = project_px(s, t, gpt(gx, gz, 2.2 + 1.2 * (m - tp)), cw, ch)
            if target is not None:
                hud.popup(im, target[0], target[1], hud.NAMES.get(card, card.upper()), PK, 0, int(255 * min(1.0, (tp + 1.8 - m) / 0.6)))
    hud.tray(im, state, CARDS_DIR, PK, drag=drag)
    d = ImageDraw.Draw(im, 'RGBA')
    # messages and banners
    if 0 <= m < 2.4:
        text(d, (cw / 2, ch * 0.30), 'FIGHT!', lil(int(150 * PK)), rgba(WHITE, 255 * min(1.0, (2.4 - m) / 0.6)), 'mm', 4, 9 * PK, rgba(INK, 255))
    if 1.2 <= m < 4.5:
        a = min(1.0, (4.5 - m) / 0.5)
        d.rounded_rectangle((cw * 0.12, ch * 0.62, cw * 0.88, ch * 0.62 + 92 * PK), int(22 * PK), fill=rgba((30, 60, 130), 235 * a), outline=rgba((120, 170, 255), 255 * a), width=max(2, int(3 * PK)))
        text(d, (cw / 2, ch * 0.62 + 46 * PK), 'Drag a card onto your side of the arena', lil(int(32 * PK)), rgba(WHITE, 255 * a), 'mm', 0, 3 * PK, rgba(INK, 255 * a))
    for item in ILLEGAL:
        if item['t'] - 0.05 <= m < item['t'] + 1.5:
            a = min(1.0, (item['t'] + 1.5 - m) / 0.4)
            d.rounded_rectangle((cw * 0.28, ch * 0.20, cw * 0.72, ch * 0.20 + 70 * PK), int(18 * PK), fill=rgba((40, 20, 70), 240 * a), outline=rgba((255, 255, 255), 90 * a), width=2)
            text(d, (cw / 2, ch * 0.20 + 35 * PK), "Can't drop here", lil(int(30 * PK)), rgba(WHITE, 255 * a), 'mm', 0, 3 * PK, rgba(INK, 255 * a))
    for item in DOWNS:
        if item['t'] + 0.1 <= m < item['t'] + 2.5:
            ours = item['team'] == 0
            u = out_back((m - item['t'] - 0.1) / 0.3)
            a = 255 * min(1.0, (item['t'] + 2.5 - m) / 0.3)
            y = ch * 0.40
            h = 110 * PK * u
            d.rectangle((0, y - h / 2, cw, y + h / 2), fill=rgba((150, 20, 30) if ours else (24, 120, 50), a * 0.92))
            d.rectangle((0, y - h / 2, cw, y - h / 2 + 5 * PK), fill=rgba(GOLD, a))
            d.rectangle((0, y + h / 2 - 5 * PK, cw, y + h / 2), fill=rgba(GOLD, a))
            text(d, (cw / 2, y), 'YOUR TOWER FELL' if ours else 'ENEMY TOWER DOWN!', lil(int(50 * PK)), rgba(WHITE, a), 'mm', 2, 4 * PK, rgba(INK, a))
    if 120.0 <= m < 122.8:
        u = out_back((m - 120.0) / 0.3)
        a = 255 * min(1.0, (122.8 - m) / 0.3)
        y, h = ch * 0.40, 120 * PK * u
        d.rectangle((0, y - h / 2, cw, y + h / 2), fill=rgba((92, 36, 160), a * 0.92))
        d.rectangle((0, y - h / 2, cw, y - h / 2 + 5 * PK), fill=rgba(GOLD, a))
        d.rectangle((0, y + h / 2 - 5 * PK, cw, y + h / 2), fill=rgba(GOLD, a))
        text(d, (cw / 2, y), 'COPIUM OVERDOSE  x2', lil(int(48 * PK)), rgba(WHITE, a), 'mm', 2, 4 * PK, rgba(INK, a))
    if m >= 180.0:
        u = m - 180.0
        rng = np.random.default_rng(3)
        for _ in range(90):
            x0, speed, phase, size = rng.uniform(0, cw), rng.uniform(160, 420), rng.uniform(0, 6.28), rng.uniform(7, 14)
            color = [(255, 205, 80), (178, 80, 246), (90, 200, 255), (255, 110, 130), (120, 230, 140)][int(rng.integers(0, 5))]
            y = -40 + speed * u + 30 * math.sin(phase + u * 3)
            x = x0 + 30 * math.sin(phase + u * 2.2)
            if 0 < y < ch:
                d.rectangle((x, y, x + size, y + size * 0.6), fill=rgba(color, 255))
        text(d, (cw / 2, ch * 0.30 + 40 * PK * (1 - out_back(u / 0.4))), 'VICTORY!', lil(int(150 * PK)), rgba(GOLD, 255), 'mm', 4, 9 * PK, rgba(INK, 255))
    return im


def phone_picture(src, s, t):
    """Fit the portrait phone picture into the 16:9 film frame: a blurred, darkened copy behind, the phone in front."""
    base = src.resize((PW, PH), Image.LANCZOS).convert('RGBA')
    draw_phone_hud(base, s, t)
    back = base.convert('RGB').resize((W, int(W * PH / PW)), Image.BILINEAR)
    top = (back.height - H) // 2
    back = back.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(38))
    back = Image.fromarray((np.asarray(back, np.float32) * 0.50).astype(np.uint8)).convert('RGBA')
    ph = H - 140
    pw = int(ph * PW / PH)
    screen = base.convert('RGB').resize((pw, ph), Image.LANCZOS).convert('RGBA')
    mask = Image.new('L', (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), 42, fill=255)
    x0, y0 = (W - pw) // 2, 24
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0 - 6, y0 + 10, x0 + pw + 6, y0 + ph + 14), 50, fill=(0, 0, 0, 170))
    back.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    bezel = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bezel).rounded_rectangle((x0 - 10, y0 - 10, x0 + pw + 10, y0 + ph + 10), 52, fill=(18, 18, 24, 255), outline=(84, 84, 100, 255), width=3)
    back.alpha_composite(bezel)
    back.paste(screen, (x0, y0), mask)
    return back


def draw_game_hud(im, t, s):
    """Cinematic arena shots keep a light version of the game's HUD: tower health pills, the clock and the score."""
    m = match_time(t)
    state = STATE.at(m)
    draw_towers(im, s, t, m, W, H, 0.82)
    hud.top_pills(im, 0.8, OPPONENT, 7521, state['clock'], True, y=4)
    hud.w_badges(im, 0.8, state['ws'], 215)


def draw_time_jump(d, t):
    """A cut that skips match time gets the clock for a moment."""
    for previous, current in zip(SHOTS, SHOTS[1:]):
        gap = current['a0'] - (previous['a0'] + (previous['t1'] - previous['t0']) * previous['s0'])
        if abs(gap) > 1.5 and current['game']:
            u = t - current['t0']
            if 0 <= u < 1.3:
                m = current['a0'] - PRE
                alpha = 255 * fade(t, current['t0'], current['t0'] + 1.3, 0.25)
                text(d, (W / 2, 160), monitor.clock_text(STATE.frame(max(0.0, m))['clock']), lil(150), rgba(WHITE, alpha), 'mm', 4, 9, rgba(INK, alpha))


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
    k3 = ease((u - 2.6) / 0.4)
    text(d, (W / 2, 905), 'DRAG WITH PURPOSE', rub(30, 800), rgba(GOLD, 230 * k3), 'mm', 7)
    d = ImageDraw.Draw(im, 'RGBA')
    fade_out = ease((T_FILM - t) / 0.5)
    if fade_out < 1:
        im = Image.fromarray((np.asarray(im.convert('RGB'), np.float32) * fade_out).astype(np.uint8))
    return im.convert('RGB')


BOOMS = [item['f'] for item in events('tower_down')]
JUMPS = [item['f'] for item in events('jump')]


def frame(f):
    t = (f - 1) / FPS
    if f > N3D:
        im = end_card(t)
    else:
        path = next(q for q in (os.path.join(FR, f'f_{f:04d}.png'), os.path.join(FR, f'f_{f:04d}.jpg')) if os.path.exists(q))
        src = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)
        src = src.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))
        a = np.asarray(src, np.float32) / 255.0
        zoom = 1.0 + sum(0.05 * decay(t, b, 0.6) ** 2 for b in BOOMS)
        a = grade(punch(a, zoom))
        flash = max([0.35 * decay(t, b, 0.2) for b in BOOMS] + [0.0])
        if flash > 0:
            a = a * (1 - flash) + np.array([1.0, 0.9, 0.75], np.float32) * flash * 1.15
        a = a * VIG * ease(t / 0.8) * ease((T_CARD - t) / 0.12)
        a = a + np.random.default_rng(f).normal(0, 0.007, (H, W, 1)).astype(np.float32)
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        s = shot_at(t)
        in_game = s.get('game', False)
        if s.get('phone'):
            im = phone_picture(Image.open(path).convert('RGB'), s, t)
            im = Image.fromarray((np.clip(np.asarray(im.convert('RGB'), np.float32) / 255.0 * VIG * ease(t / 0.8) * ease((T_CARD - t) / 0.12), 0, 1) * 255).astype(np.uint8)).convert('RGBA')
            d = ImageDraw.Draw(im, 'RGBA')
            draw_captions(d, t, y=H - 88)
            im = im.convert('RGB')
            im.save(os.path.join(OUT, f'c_{f:04d}.jpg'), quality=95, subsampling=0)
            return
        if in_game:
            draw_game_hud(im, t, s)
        d = ImageDraw.Draw(im, 'RGBA')
        draw_title(d, t)
        draw_banners(d, t)
        draw_time_jump(d, t)
        draw_captions(d, t)
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
    x = np.arange(int(dur * SR)) / SR
    u = x / dur
    freq = f0 * (f1 / f0) ** (u ** shape)
    phase = 2 * np.pi * np.cumsum(freq) / SR + vibrato * np.sin(2 * np.pi * 7 * x)
    signal = (np.sin(phase) + 0.3 * np.sin(2 * phase)) * np.clip(x / 0.02, 0, 1) * np.clip((dur - x) / 0.05, 0, 1)
    put('fx', mono(signal), t, gain)


def klaxon(t, dur=1.2, gain=0.2):
    x = np.arange(int(dur * SR)) / SR
    gate = (np.sin(2 * np.pi * 2.2 * x) > -0.2).astype(np.float32)
    signal = np.sign(np.sin(2 * np.pi * 310 * x)) * 0.5 + np.sign(np.sin(2 * np.pi * 466 * x)) * 0.35
    put('fx', mono(lowpass(signal, 8) * gate * np.clip((dur - x) / 0.1, 0, 1)), t, gain)


def is_hold(s):
    return not s.get('game', False) and s['name'] != 'ext_ship' and not s['name'].startswith(('fall_',))


# dialogue: levelled; the pilot through a radio; the game's announcer as recorded
for cue in E['cues']:
    x = load(os.path.join(VOD, cue['id'] + '.wav'))
    target = 0.11 if cue['who'] == 'game' else 0.085
    x = x * (target / (float(np.sqrt((x ** 2).mean())) + 1e-9))
    if cue['who'] == 'pilot':
        m = x[:, 0]
        m = m - lowpass(m, 60)
        m = np.tanh(lowpass(m, 5) * 5) * 0.4 + rng.normal(0, 0.004, len(m))
        x = mono(m)
        tone(cue['f'] - 0.12, 1800, 1800, 0.06, 0.08)
        tone(cue['f'] + cue['dur'] + 0.05, 1400, 1400, 0.06, 0.08)
    put('vo', x, cue['f'], 1.0)

# ambience: the engines inside the ship, wind and a garden outside
t_ramp = first('match_start')['f']
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
    if s.get('game', False):
        yard_env[i0:i1] = 1.0
        wind_env[i0:i1] = 0.2
    elif s['name'] == 'ext_ship':
        hold_env[i0:i1] = 0.7
        wind_env[i0:i1] = 0.8
    elif s['name'].startswith('fall_'):
        wind_env[i0:i1] = 1.0
    else:
        hold_env[i0:i1] = 1.0
        wind_env[i0:i1] = 0.7 if s['t0'] >= t_ramp else 0.0
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

# music: a snare march in the briefing, the game's battle music on the arena shots, its overdose music from 2:00
brief0 = SHOTS[0]['t0']
beat_len = 0.5
k = 0
while brief0 + k * beat_len < t_ramp:
    tb = brief0 + k * beat_len
    snare(tb, 0.08)
    if k % 2 == 1:
        snare(tb + beat_len * 0.5, 0.05)
    if k % 8 == 0:
        thud(tb, 0.2, 60, 'mus')
    k += 1
for m_, dt, dur in ((50, 0.0, 14.0), (57, 0.0, 14.0), (62, 2.0, 12.0), (66, 5.0, 9.0)):
    strings(m_, brief0 + 2.0 + dt, min(dur, t_ramp - brief0 - 3.0), 0.06, attack=2.5, release=1.0, bright=5)
battle = game('mus_battle')
overdose_music = game('mus_overdose')
t_od = first('overdose')['f']
music_env = np.zeros(n, np.float32)
od_env = np.zeros(n, np.float32)
for s in SHOTS:
    if s['t0'] >= t_ramp:
        i0, i1 = int(s['t0'] * SR), int(s['t1'] * SR)
        (od_env if (t_od <= s['t0'] < t_od + 24.0) else music_env)[i0:i1] = 1.0 if s.get('game', False) else 0.45
for env_ in (music_env, od_env):
    env_[:] = np.convolve(env_, np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
loop = np.concatenate([battle] * (int(END * SR / len(battle)) + 2))[:n]
loop_od = np.concatenate([overdose_music] * (int(END * SR / len(overdose_music)) + 2))[:n]
BUS['mus'] += loop * music_env[:, None] * 0.2 + loop_od * od_env[:, None] * 0.22
menu = game('mus_menu')
put('mus', menu[:int((T_FILM - T_CARD + 0.5) * SR)], T_CARD, 0.3)

# effects, each on its own recorded event
put('fx', game('battle_start'), first('match_start')['f'], 0.5)
for item in events('klaxon'):
    klaxon(item['f'])
for item in events('jump'):
    whoosh(item['f'] - 0.1, 1.4, 0.35)
for item in events('land'):
    put('fx', game('deploy_spell' if item.get('spell') else 'deploy_drop'), item['f'] - 0.05, 0.55)
    thud(item['f'], 0.45, 80)
for item in events('card_pop'):
    put('fx', game('emote_pop'), item['f'], 0.18)
for item in events('tower_down'):
    put('fx', game('tower_destroy'), item['f'], 0.8)
    put('fx', game('rocket_explode'), item['f'], 0.55)
for item in events('coins'):
    for j in range(14):
        tone(item['f'] + 0.2 + j * 0.09, rng.uniform(1100, 2000), rng.uniform(700, 1000), 0.08, 0.06)
for item in events('hit'):
    put('fx', game('punch_heavy' if item.get('heavy') else 'tower_hit'), item['f'], 0.18, pan=rng.uniform(-0.5, 0.5))
for item in events('boom'):
    put('fx', game('rocket_explode'), item['f'], 0.25, pan=rng.uniform(-0.5, 0.5))
for item in events('tshot'):
    put('fx', game('tower_shot'), item['f'], 0.2)
for item in events('illegal'):
    tone(item['f'], 220, 140, 0.35, 0.22, shape=0.7)
    tone(item['f'] + 0.12, 220, 140, 0.35, 0.18, shape=0.7)
put('fx', game('victory'), first('victory')['f'], 0.55)
put('fx', game('crowd_cheer'), first('cheer')['f'], 0.4)
put('fx', game('crowd_ooh'), BOOMS[0] + 0.3, 0.3) if BOOMS else None

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
