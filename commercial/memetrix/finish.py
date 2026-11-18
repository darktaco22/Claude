"""Finish THE MEMETRIX: opening (code rain, typed messages, title), grade per world, letterbox, captions, transitions,
end card and the sound mix.

    python3 finish.py FRAMES_DIR OUT_DIR [f1,f2,...]
->  OUT_DIR/c_####.jpg (1920x1080, 24 fps) + mix.wav        (SOUND_ONLY=1 skips the picture)

Frames may be .png or .jpg (any size; scaled to 1080p). Sound: Kokoro voices, the game's own music and effects
(../comeback/audio) and a few synthesized sounds (typing, drones, whooshes). No film music or film sound is used.
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
from coderain import Rain  # noqa: E402

FR, OUT = sys.argv[1], sys.argv[2]
ONLY = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
os.makedirs(OUT, exist_ok=True)
A = os.path.join(HERE, '..', 'assets')
AU = os.path.join(HERE, '..', 'comeback', 'audio')
VOD = os.path.join(HERE, 'pack', 'vo')
E = json.load(open(os.path.join(HERE, 'edl.json')))
SHOTS = E['shots']
FPS = E['fps']
TITLE = E['title']
EV = E['events']
CUES = sorted(E['cue_rows'], key=lambda c: c['f'])
T_CARD = E['end']
PRE = float(os.environ.get('PRE', '6.0'))            # extra opening in front of the film (the film itself is shifted by PRE)
OPEN = PRE + TITLE                                  # the 2D opening runs 0..OPEN of the output
SHIFT = int(round(PRE * FPS))
END_LEN = 14.0                                      # closing: cast cards, logo, call to action
T_FILM = T_CARD + END_LEN                           # in film time
NF = int(round((PRE + T_FILM) * FPS))               # output frames
N3D = int(round(T_CARD * FPS))
W, H = 1920, 1080
BAR = 98                                            # letterbox: about 2.2:1 picture
INK = (8, 14, 10)
WHITE = (255, 255, 255)
GREEN = (90, 255, 130)
SPEAKER = {'anon': ('ANON', (205, 180, 140)), 'slerf': ('SLERF', (200, 150, 110)), 'michi': ('MICHI', (210, 150, 255)),
           'mensa': ('MENSA', (230, 170, 120)), 'farter': ('FARTER', (255, 210, 80)), 'alon': ('ALON', (150, 200, 255)),
           'bome': ('BOME', (190, 120, 255)), 'jean': ('AGENT JEANPHIL', (170, 180, 170)), 'tri': ('AGENTS', (240, 140, 80)),
           'mom': ('MOM (UPSTAIRS)', (255, 170, 190))}

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


def mono_font(size):
    key = ('mono', size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', size)
    return _fonts[key]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fade(t, t0, t1, d=0.3):
    return ease((t - t0) / d) * ease((t1 - t) / d)


def rgba(c, a=255):
    return (c[0], c[1], c[2], int(max(0, min(255, a))))


def shot_at(t):
    return next((s for s in SHOTS if s['t0'] <= t < s['t1']), SHOTS[-1])


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RR = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
VIG = (1 - 0.28 * RR ** 1.4)[..., None]
RAIN = Rain(W, H, cell=26, seed=3, loop=4.0)


# ---------------------------------------------------------------- grade per world
def bloom(a, thresh=0.72, amount=0.3, blur=10):
    hi = np.clip((a.max(axis=2, keepdims=True) - thresh) / (1 - thresh), 0, 1) * a
    small = Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    return a + np.asarray(small.filter(ImageFilter.GaussianBlur(blur)).resize((W, H), Image.BILINEAR), np.float32) / 255.0 * amount


def grade(a, world):
    lum = a.mean(axis=2, keepdims=True)
    if world in ('FLOOR', 'ROOFTOP'):              # inside the Memetrix: green cast, crushed blacks, hard highlights
        a = lum + (a - lum) * 0.85
        a = a * np.array([0.86, 1.06, 0.84], np.float32) + 0.04 * (1 - lum) ** 3 * np.array([-0.2, 0.35, -0.1], np.float32)
        a = np.clip((a - 0.025) * 1.1, 0, 1) ** 1.08
        return bloom(a, 0.68, 0.35)
    if world == 'BASEMENT':                        # the real world: warm bulbs, cold shadows, a bit drab
        a = lum + (a - lum) * 0.92
        a = a * np.array([1.05, 0.99, 0.9], np.float32) + 0.05 * (1 - lum) ** 2 * np.array([-0.15, 0.0, 0.3], np.float32)
        return bloom(np.clip(a * 1.03, 0, 1) ** 1.02, 0.8, 0.22)
    a = lum + (a - lum) * 1.12                     # the training program: clean, saturated, pink
    a = a * np.array([1.04, 0.97, 1.05], np.float32)
    return bloom(np.clip(a, 0, 1), 0.75, 0.32)


def lens(a, f):
    """Anamorphic streaks and halation on highlights, chromatic aberration toward the edges, grain that follows brightness."""
    hi = np.clip((a.max(axis=2, keepdims=True) - 0.7) / 0.3, 0, 1) * a
    small = Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).resize((W // 8, H // 8), Image.BILINEAR)
    sm = np.asarray(small, np.float32) / 255.0
    k = np.exp(-np.abs(np.arange(-40, 41)) / 12.0)
    k /= k.sum()
    horiz = np.stack([np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, sm[..., c]) for c in range(3)], 2)
    horiz = np.asarray(Image.fromarray((np.clip(horiz, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255.0
    a = a + horiz * np.array([0.35, 0.55, 1.0], np.float32) * 0.45                               # blue anamorphic streak
    halo = np.asarray(Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255.0
    a = a + halo * np.array([1.0, 0.35, 0.2], np.float32) * 0.18                                 # red halation
    r = np.roll(a[..., 0], 2, axis=1) * (RR > 0.6) + a[..., 0] * (RR <= 0.6)
    b = np.roll(a[..., 2], -2, axis=1) * (RR > 0.6) + a[..., 2] * (RR <= 0.6)
    a = np.stack([r, a[..., 1], b], 2)
    lum = a.mean(axis=2, keepdims=True)
    grain = np.random.default_rng(f).normal(0, 1, (H // 2, W // 2, 1)).astype(np.float32)
    grain = np.asarray(Image.fromarray(((grain[..., 0] * 0.25 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR),
                       np.float32)[..., None] / 255.0 - 0.5
    return a + grain * 0.05 * (0.4 + 0.6 * (1 - lum))


def rain_array(t, amount=1.0):
    return np.asarray(RAIN.frame(t), np.float32) / 255.0 * amount


# ---------------------------------------------------------------- graphics
def text(d, xy, string, font, fill, anchor='lm', stroke=0, stroke_fill=None):
    d.text(xy, string, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def wrap(d, string, font, limit):
    if d.textlength(string, font=font) <= limit:
        return [string]
    words = string.split()
    best = None
    for k in range(1, len(words)):
        a, b = ' '.join(words[:k]), ' '.join(words[k:])
        width = max(d.textlength(a, font=font), d.textlength(b, font=font))
        if best is None or width < best[0]:
            best = (width, [a, b])
    return best[1]


def draw_captions(d, t):
    for i, cue in enumerate(CUES):
        end = cue['f'] + cue['dur'] + 0.15
        if i + 1 < len(CUES):
            end = min(end, CUES[i + 1]['f'] - 0.02)
        if not cue['f'] - 0.05 <= t < end:
            continue
        tag, colour = SPEAKER[cue['who']]
        font = rub(32, 500)
        tag_font = rub(22, 800)
        tag_w = d.textlength(tag, font=tag_font) + 28
        rows = wrap(d, cue['sub'], font, W - tag_w - 160)
        line_w = max(d.textlength(r, font=font) for r in rows) + 40
        box_h = 52 if len(rows) == 1 else 92
        top = H - BAR - box_h - 18
        x = W / 2 - (tag_w + line_w) / 2
        d.rounded_rectangle((x, top, x + tag_w + line_w, top + box_h), 9, fill=rgba((0, 0, 0), 200))
        d.rounded_rectangle((x, top, x + tag_w, top + box_h), 9, fill=rgba(colour, 245))
        d.rectangle((x + tag_w - 9, top, x + tag_w, top + box_h), fill=rgba(colour, 245))
        text(d, (x + tag_w / 2, top + box_h / 2 + 1), tag, tag_font, rgba(INK), 'mm')
        for n, row in enumerate(rows):
            text(d, (x + tag_w + 20, top + 27 + 38 * n), row, font, rgba(WHITE))


# ---------------------------------------------------------------- titles: the opening and the closing (2D, drawn here)
MESSAGES = [(1.0, 2.65, 'Wake up, Anon...'), (2.75, 4.25, 'The chart has you...'), (4.35, 5.8, 'Follow the green candle.')]
TYPE = 0.06                                          # seconds per typed character
DIVE = (5.8, 7.6)                                    # the zoom into the code
SLAM = 7.6                                           # the title lands
MELT = (10.3, OPEN)                                  # the title burns away into the film
RAIN_FAR = Rain(W, H, cell=12, seed=11, loop=4.0)
RAIN_NEAR = Rain(W, H, cell=54, seed=5, loop=4.0)
CAST = [('THE CHOSEN ONE', 'ZCAT', 'a09_0', 0.5), ('THE MENTOR', 'SLERF', 's02_0', 0.5), ('THE FIGHTER', 'MICHI', 'm03_0', 0.5),
        ('THE OPERATOR', 'MENSA', 'n01_1', 0.6), ('THE TRAITOR', 'FARTER', 'f01_0', 0.25), ('THE KID', 'ALON', 'k01_0', 0.4),
        ('THE ORACLE', 'BOME', 'b01_0', 0.5), ('AGENT', 'JEANPHIL', 'j01_0', 0.5), ('AGENTS', 'TRIPLETS', 't01_0', 0.5)]
CARD0, CARD_DUR = 0.5, 0.8                           # closing: cast cards from T_CARD + 0.5, 0.8 s each
LOGO_T = CARD0 + CARD_DUR * len(CAST) + 0.2          # closing: the logo builds in


def arr(im):
    return np.asarray(im, np.float32) / 255.0


def to_im(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def blur(a, r):
    return arr(to_im(a).filter(ImageFilter.GaussianBlur(r)))


def zoom(a, z, cx=W / 2, cy=H / 2):
    """Scale about a point (z > 1 pushes in; never below 1, the crop must stay inside the picture)."""
    z = max(1.0, z)
    w, h = W / z, H / z
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return arr(to_im(a).resize((W, H), Image.BILINEAR, box=box))


def zoom_blur(a, z, spread, n=5):
    """Radial streaks: the average of the picture pushed in by slightly different amounts."""
    return sum(zoom(a, z * (1 + spread * k / (n - 1))) for k in range(n)) / n


def chroma(a, px):
    px = int(px)
    if px == 0:
        return a
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], px, axis=1)
    out[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return out


def tear(a, t, amount):
    rng = np.random.default_rng(int(t * 997))
    out = a.copy()
    for _ in range(int(14 * amount)):
        y0 = int(rng.integers(0, H - 30))
        h = int(rng.integers(4, 30))
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], int(rng.integers(-120, 120) * amount), axis=1)
    return out


SCAN = (1 - 0.22 * ((np.arange(H) % 3) == 0)).astype(np.float32)[:, None, None]


def text_mask(string, font, xy, anchor='mm', spacing=0.0):
    """White-on-black text as a float mask (letter spacing in px when spacing > 0)."""
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    if spacing <= 0:
        d.text(xy, string, font=font, fill=255, anchor=anchor)
    else:
        widths = [d.textlength(ch, font=font) for ch in string]
        total = sum(widths) + spacing * (len(string) - 1)
        x = xy[0] - total / 2 if anchor[0] == 'm' else xy[0]
        for ch, w_ in zip(string, widths):
            d.text((x, xy[1]), ch, font=font, fill=255, anchor='l' + anchor[1])
            x += w_ + spacing
    return np.asarray(im, np.float32)[..., None] / 255.0


def glow_of(mask, colour, r1=6, r2=22, k1=0.9, k2=0.55):
    c = mask * (np.array(colour, np.float32) / 255.0)
    return blur(c, r1) * k1 + blur(c, r2) * k2


def flare(a, x, y, strength, colour=(0.45, 0.9, 1.0)):
    """Anamorphic lens flare: a long horizontal streak through (x, y) and ghosts mirrored through the centre."""
    if strength <= 0.01:
        return a
    col = np.array(colour, np.float32)
    streak = np.exp(-((yy - y) / 3.0) ** 2) * np.exp(-np.abs(xx - x) / 700.0)
    core = np.exp(-(((xx - x) / 60.0) ** 2 + ((yy - y) / 60.0) ** 2))
    out = a + (streak[..., None] * col * 0.9 + core[..., None] * 0.9) * strength
    for k, (f, r) in enumerate(((-0.4, 40), (-0.8, 22), (0.3, 70))):
        gx, gy = W / 2 + (W / 2 - x) * f, H / 2 + (H / 2 - y) * f
        ring = np.exp(-(((xx - gx) ** 2 + (yy - gy) ** 2) ** 0.5 - r) ** 2 / 30.0) * 0.25 + np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (r * r)) * 0.12
        out = out + ring[..., None] * col * strength * 0.5
    return out


TITLE_FONT = lil(230)
TITLE_XY = (W / 2, H / 2 - 40)
TITLE_MASK = None
NOISE = None


def title_mask():
    global TITLE_MASK, NOISE
    if TITLE_MASK is None:
        TITLE_MASK = text_mask('THE MEMETRIX', TITLE_FONT, TITLE_XY)
        NOISE = blur(np.random.default_rng(4).random((H, W, 1)).astype(np.float32).repeat(3, 2), 3)[..., :1]
        NOISE = (NOISE - NOISE.min()) / (NOISE.max() - NOISE.min())
    return TITLE_MASK


def chrome(mask, t):
    """Green chrome fill: a vertical metal gradient with a bright horizon line and a specular sweep."""
    ys = np.nonzero(mask[..., 0].max(axis=1) > 0.5)[0]
    top, bot = (ys.min(), ys.max()) if len(ys) else (0, H)
    v = np.clip((yy - top) / max(1, bot - top), 0, 1)[..., None]
    hi = np.array([0.85, 1.0, 0.88], np.float32)
    mid = np.array([0.2, 0.85, 0.42], np.float32)
    low = np.array([0.02, 0.28, 0.12], np.float32)
    grad = np.where(v < 0.5, hi + (mid - hi) * (v / 0.5), mid + (low - mid) * ((v - 0.5) / 0.5))
    horizon = np.exp(-((v - 0.52) / 0.03) ** 2) * 0.6
    sweep_x = -400 + (t - (SLAM + 0.8)) * 1500.0
    sweep = np.exp(-(((xx - sweep_x) + (yy - H / 2) * 0.45) / 55.0) ** 2)[..., None]
    return (grad + horizon + sweep * 1.4) * mask, sweep_x


EMBERS = None


def embers(t):
    """Sparks leaving the title as it burns away."""
    global EMBERS
    if EMBERS is None:
        m = title_mask()[..., 0]
        ys, xs = np.nonzero(m > 0.5)
        rng = np.random.default_rng(8)
        pick = rng.choice(len(xs), 420, replace=False)
        EMBERS = [(xs[i], ys[i], rng.uniform(-40, 40), rng.uniform(120, 420), rng.uniform(0, 0.5), rng.uniform(1.5, 3.5))
                  for i in pick]
    im = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(im)
    u = t - MELT[0]
    for x, y, vx, vy, delay, r in EMBERS:
        k = u - delay
        if k <= 0:
            continue
        life = max(0.0, 1 - k / 0.7)
        px, py = x + vx * k, y - vy * k - 60 * k * k
        c = (int(160 * life + 60), int(255 * life), int(170 * life + 40))
        d.ellipse((px - r, py - r, px + r, py + r), fill=c)
    a = arr(im)
    return a + blur(a, 5) * 1.2


def message_layer(t):
    """The typed terminal line with phosphor glow; tears and splits as each message ends."""
    for t0, t1, msg in MESSAGES:
        if t0 <= t < t1:
            shown = msg[:int((t - t0) / TYPE)]
            cursor = '_' if int(t * 3) % 2 == 0 else ' '
            m = text_mask(shown + cursor, mono_font(56), (220, H / 2), 'lm')
            layer = m * np.array([0.45, 1.0, 0.6], np.float32) + glow_of(m, (60, 255, 120), 5, 18, 0.8, 0.5)
            end = ease((t - (t1 - 0.18)) / 0.18)
            if end > 0:
                layer = tear(chroma(layer, 22 * end), t, end) * (1 - 0.6 * end)
            return layer * (0.92 + 0.08 * math.sin(t * 61))
    if t < MESSAGES[0][0]:                                   # the cursor alone, blinking in the dark
        if int(t * 3) % 2 == 0:
            m = text_mask('_', mono_font(56), (220, H / 2), 'lm')
            return m * np.array([0.45, 1.0, 0.6], np.float32) + glow_of(m, (60, 255, 120), 5, 18, 0.8, 0.5)
    return np.zeros((H, W, 3), np.float32)


def depth_rain(t, z):
    """Three layers of code at different depths: the far one soft and dim, the near one big and bright."""
    far = blur(np.asarray(RAIN_FAR.frame(t), np.float32) / 255.0, 2) * 0.35
    mid = rain_array(t, 0.75)
    near = np.asarray(RAIN_NEAR.frame(t), np.float32) / 255.0
    return zoom(far, z * 0.85) + zoom(mid, z) + blur(zoom(near, z * 1.25), 1.5) * 0.9


def opening(tt):
    """0..OPEN of the output: terminal messages, the dive into the code, the title, the title burning away."""
    a = np.zeros((H, W, 3), np.float32)
    if tt < DIVE[0]:
        far = np.asarray(RAIN_FAR.frame(tt), np.float32) / 255.0
        a = blur(far, 3) * 0.10 * ease((tt - 0.6) / 1.5)
        a = a + message_layer(tt)
    elif tt < SLAM:                                          # the dive: faster and faster into the code, then white
        u = (tt - DIVE[0]) / (DIVE[1] - DIVE[0])
        z = 1 + 1.4 * u ** 1.6
        a = zoom_blur(depth_rain(tt, z), 1.0, 0.03 + 0.25 * u ** 2)
        burst = np.exp(-RR * (6 - 4.5 * u))[..., None] * np.array([0.6, 1.0, 0.75], np.float32) * ease((u - 0.55) / 0.45) * 1.6
        a = a * ease(u / 0.15) + burst
        a = chroma(a, 8 * u)
    else:                                                    # the title
        u = tt - SLAM
        m = title_mask()
        bg = zoom(depth_rain(tt, 2.4 + 0.08 * u), 1.0) * 0.28
        fill_rain = np.clip(np.asarray(RAIN_NEAR.frame(tt), np.float32) / 255.0 * 2.2 + 0.08, 0, 1) * np.array([0.5, 1, 0.6], np.float32)
        metal, sweep_x = chrome(m, tt)
        k = ease((u - 0.35) / 0.8)
        fill = fill_rain * m * (1 - k) + metal * k
        if tt >= MELT[0]:                                    # burn away: noise threshold eats the letters, edges glow
            v = (tt - MELT[0]) / (MELT[1] - MELT[0])
            keep = (NOISE > v * 1.15).astype(np.float32)
            edge = ((NOISE > v * 1.15 - 0.06) & (NOISE <= v * 1.15)).astype(np.float32)
            fill = fill * keep + edge * m * np.array([0.7, 1.0, 0.6], np.float32) * 2.0
            m = m * keep
            bg = bg * (1 - v)
        a = bg + glow_of(m, (70, 255, 130), 8, 30, 0.7 * (1 + 1.5 * math.exp(-u * 3)), 0.6) + fill
        if tt >= MELT[0]:
            a = a + embers(tt)
        sub_k = ease((u - 1.0) / 0.7) * (1 - ease((tt - MELT[0]) / 0.3))
        if sub_k > 0:
            sm = text_mask('A MEME ROYALE PARODY', rub(32, 700), (W / 2, H / 2 + 120), 'mm', spacing=6 + 14 * ease((u - 1.0) / 1.6))
            a = a + sm * sub_k * 0.95 + glow_of(sm, (120, 255, 160), 4, 12, 0.4, 0.2) * sub_k
        a = flare(a, float(np.clip(sweep_x, -200, W + 200)), TITLE_XY[1], ease((u - 0.8) / 0.2) * (1 - ease((u - 1.9) / 0.4)))
        flash = math.exp(-u * 7)                               # the slam: white flash, shake, colour split
        a = a + flash * 0.9
        a = chroma(a, 14 * math.exp(-u * 5))
        shake = int(16 * math.exp(-u * 6) * math.sin(u * 70))
        a = np.roll(a, shake, axis=0)
        a = a * (1 - ease((tt - (OPEN - 0.25)) / 0.25))
    a = a * SCAN * VIG
    return lens(a, int(tt * FPS))


STILLS = {}


def still(shot_name, u):
    """A graded frame of a shot, for the cast cards."""
    key = (shot_name, u)
    if key not in STILLS:
        s_ = next(x for x in SHOTS if x['name'] == shot_name)
        f = int((s_['t0'] + (s_['t1'] - s_['t0']) * u) * FPS) + 1
        path = next(q for q in (os.path.join(FR, f'f_{f:04d}.png'), os.path.join(FR, f'f_{f:04d}.jpg')) if os.path.exists(q))
        im = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)
        STILLS[key] = grade(arr(im), s_['set'])
    return STILLS[key]


LOGO = None


def closing(t):
    """T_CARD..T_FILM: glitch out of the film, nine cast cards with stills, the logo and the call to action."""
    global LOGO
    u = t - T_CARD
    far = blur(np.asarray(RAIN_FAR.frame(t), np.float32) / 255.0, 2.5)
    a = far * 0.16 + rain_array(t, 0.10)
    d_h = 0.0
    if u < CARD0:                                            # out of the film: the picture shreds into code
        g = 1 - ease(u / CARD0)
        a = tear(chroma(a + rain_array(t, 0.6) * g, 18 * g), t, g)
    n = int((u - CARD0) // CARD_DUR)
    if 0 <= n < len(CAST) and u >= CARD0:
        role, name, shot_name, su = CAST[n]
        v = (u - CARD0 - n * CARD_DUR) / CARD_DUR
        pw, ph = 880, 495
        px, py = 250, (H - ph) // 2 + 20                          # panel + names centred as one block
        pic = still(shot_name, su)
        pic = zoom(pic, 1.0 + 0.07 * v)
        panel = np.asarray(to_im(pic).resize((pw, ph), Image.LANCZOS), np.float32) / 255.0
        frame_a = np.zeros((H, W, 3), np.float32)
        frame_a[py:py + ph, px:px + pw] = panel
        border = np.zeros((H, W, 1), np.float32)
        border[py - 3:py + ph + 3, px - 3:px + pw + 3] = 1
        border[py:py + ph, px:px + pw] = 0
        frame_a = frame_a + glow_of(border, (80, 255, 140), 3, 14, 0.9, 0.5) + border * 0.8
        rm = text_mask(role, rub(30, 700), (1220, H / 2 - 50), 'lm', spacing=5)
        nm = text_mask(name, lil(118), (1210, H / 2 + 40), 'lm', spacing=2 + 30 * (1 - ease(v / 0.3)))
        txt = rm * np.array([0.45, 1.0, 0.6], np.float32) + nm * (0.4 + 0.6 * ease(v / 0.25)) + glow_of(nm, (90, 255, 150), 6, 20, 0.5, 0.3)
        hdr = text_mask('STARRING', rub(26, 800), (W / 2, 150), 'mm', spacing=16)
        a = a + frame_a + txt + hdr * 0.55
        whip = max(1 - ease(v / 0.12), ease((v - 0.88) / 0.12))      # whip pan between cards: horizontal smear
        if whip > 0.02:
            d_h = whip
    if u >= LOGO_T - 0.2:
        if LOGO is None:
            LOGO = Image.open(os.path.join(A, 'logo.png')).convert('RGBA')
        v = u - LOGO_T
        size = int(520 * (1.0 + 0.05 * ease(v / 6.0)))
        mark = LOGO.resize((size, int(size * LOGO.height / LOGO.width)), Image.LANCZOS)
        layer = Image.new('RGBA', (W, H))
        top = 140 - (size - 520) // 4
        layer.alpha_composite(mark, ((W - mark.width) // 2, top))
        la = np.asarray(layer, np.float32) / 255.0
        rgb, alpha = la[..., :3], la[..., 3:]
        scan_y = top + (mark.height + 40) * ease(v / 1.0)          # built line by line, a bright scanline at the edge
        built = (yy[..., None] < scan_y).astype(np.float32)
        jitter = np.where(np.abs(yy - scan_y) < 30, 1.0, 0.0)[..., None]
        line = np.exp(-((yy - scan_y) / 4.0) ** 2)[..., None] * alpha.max() * (1 - ease((v - 1.0) / 0.3))
        rgb_shift = np.roll(rgb, 14, axis=1) * jitter + rgb * (1 - jitter)
        sweep_x = -300 + (v - 1.3) * 1500.0
        sheen = np.exp(-(((xx - sweep_x) + (yy - 400) * 0.5) / 70.0) ** 2)[..., None]
        logo_a = (rgb_shift + sheen * 0.8) * alpha * built
        a = a * (1 - alpha * built * 0.9) + logo_a + blur(alpha * built * np.array([0.3, 1.0, 0.5], np.float32), 26) * 0.45
        a = a + line * np.array([0.6, 1.0, 0.7], np.float32) * np.exp(-np.abs(xx - W / 2) / 500)[..., None] * 1.5
        a = flare(a, float(np.clip(sweep_x, -200, W + 200)), 400, ease((v - 1.3) / 0.2) * (1 - ease((v - 2.3) / 0.4)) * 0.8)
        tag = 'THERE IS NO CHART.'
        shown = tag[:max(0, int((v - 1.6) / 0.07))]
        if shown:
            tm = text_mask(shown, rub(64, 800), (W / 2, 760), 'mm')
            flick = 1.0 if v > 1.6 + len(tag) * 0.07 + 0.25 or int(v * 30) % 3 else 0.55
            a = a + (tm * np.array([0.45, 1.0, 0.6], np.float32) + glow_of(tm, (70, 255, 130), 6, 22, 0.8, 0.5)) * flick
        k2 = ease((v - 3.2) / 0.6)
        if k2 > 0:
            cm = text_mask('FREE TO PLAY  ·  memeroyale.imaginestudio.fun', rub(32, 500), (W / 2, 850), 'mm', spacing=1)
            a = a + cm * 0.85 * k2
    if d_h > 0:
        k = int(4 + 120 * d_h)
        a = sum(np.roll(a, s_, axis=1) for s_ in range(-k, k + 1, max(1, k // 6))) / len(range(-k, k + 1, max(1, k // 6)))
    a = a * SCAN * VIG * ease((T_FILM - t) / 0.7)
    return lens(a, int(t * FPS))


def glitch(a, t, amount):
    """Chromatic split and row tearing, mixed toward the code rain."""
    if amount <= 0:
        return a
    shift = int(18 * amount)
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], shift, axis=1)
    out[..., 2] = np.roll(a[..., 2], -shift, axis=1)
    rng = np.random.default_rng(int(t * 1000))
    for _ in range(int(10 * amount)):
        y0 = rng.integers(0, H - 40)
        h = rng.integers(6, 40)
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], rng.integers(-80, 80), axis=1)
    return out * (1 - amount) + rain_array(t) * amount


def frame(o):
    """Output frame o: the opening (0..OPEN), then film frame f = o - SHIFT (3D up to T_CARD, then the closing)."""
    tt = (o - 1) / FPS
    f = o - SHIFT
    t = (f - 1) / FPS
    if tt < OPEN:
        im = to_im(opening(tt))
    elif f > N3D:
        im = to_im(closing(t))
    else:
        path = next(q for q in (os.path.join(FR, f'f_{f:04d}.png'), os.path.join(FR, f'f_{f:04d}.jpg')) if os.path.exists(q))
        src = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))
        a = np.asarray(src, np.float32) / 255.0
        s = shot_at(t)
        a = grade(a, s['set'])
        if s.get('glitch') == 'rain_out':                    # the swallow: the picture breaks into code, then white
            u = (t - s['t0']) / (s['t1'] - s['t0'])
            a = glitch(a, t, ease((u - 0.35) / 0.5))
            a = a + ease((u - 0.85) / 0.15)
        if s.get('glitch') == 'rain_in':                     # waking up: out of white and code
            u = (t - s['t0']) / (s['t1'] - s['t0'])
            a = glitch(a, t, 1 - ease(u / 0.35)) + (1 - ease(u / 0.12))
        flash = 0.0
        for key in ('turn_green',):
            if EV.get(key) and 0 <= t - EV[key] < 0.4:
                flash = 0.35 * (1 - (t - EV[key]) / 0.4)
        a = a * (1 - flash) + np.array([0.6, 1.0, 0.65], np.float32) * flash
        a = a * VIG * ease((t - TITLE) / 0.25) * ease((T_CARD - t) / 0.3)
        a = lens(a, f)
        a[:BAR] = 0
        a[H - BAR:] = 0
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        draw_captions(ImageDraw.Draw(im, 'RGBA'), t)
        im = im.convert('RGB')
    im.save(os.path.join(OUT, f'c_{o:04d}.jpg'), quality=94, subsampling=0)


if __name__ == '__main__':
    for f in ([] if os.environ.get('SOUND_ONLY') else (ONLY or range(1, NF + 1))):
        frame(f)
    print('FRAMES-DONE')
    if ONLY:
        sys.exit(0)

# ================================================================ sound
SR = 48000
END = NF / FPS
n = int(END * SR) + SR
rng = np.random.default_rng(29)
BUS = {k: np.zeros((n, 2), np.float32) for k in ('vo', 'mus', 'amb', 'fx')}


def load(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def game(name):
    return load(os.path.join(AU, name + ('.wav' if os.path.exists(os.path.join(AU, name + '.wav')) else '.mp3')))


OFFSET = PRE                                         # film-time sounds are shifted by PRE; the opening block sets 0


def put(bus, x, t, gain=1.0):
    i = int((t + OFFSET) * SR)
    m = min(len(x), n - i)
    if m > 0 and i >= 0:
        BUS[bus][i:i + m] += x[:m] * gain


def mono(sig):
    return np.stack([sig, sig], 1).astype(np.float32)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, 'same')


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad(notes, t, dur, gain=0.05, attack=1.5, release=2.0):
    """Dark detuned saw pad (synthesized)."""
    length = int((dur + release) * SR)
    x = np.arange(length) / SR
    sig = np.zeros(length)
    for m in notes:
        for det in (-0.08, 0.0, 0.09):
            ph = 2 * np.pi * midi(m + det) * x
            for h in range(1, 7):
                sig += np.sin(ph * h) / h ** 1.6
    env = np.clip(x / attack, 0, 1) * np.clip((dur + release - x) / release, 0, 1)
    put('mus', mono(lowpass(sig, 6) * env), t, gain / len(notes))


def kick(t, gain=0.35):
    x = np.arange(int(0.25 * SR)) / SR
    sig = np.sin(2 * np.pi * (55 * x + 90 * (1 - np.exp(-x / 0.03)) * 0.03)) * np.exp(-x / 0.12)
    put('mus', mono(sig), t, gain)


def hat(t, gain=0.05):
    x = np.arange(int(0.05 * SR)) / SR
    sig = rng.normal(0, 1, len(x))
    sig = sig - lowpass(sig, 4)
    put('mus', mono(sig * np.exp(-x / 0.01)), t, gain)


def whoosh(t, dur=0.8, gain=0.25, low=False):
    x = np.arange(int(dur * SR)) / SR
    u = x / dur
    noise = lowpass(rng.normal(0, 1, len(x)), 300 if low else 90) * (20 if low else 10)
    put('fx', mono(noise * np.sin(np.pi * u) ** 2), t, gain)


def key_click(t, gain=0.06):
    x = np.arange(int(0.03 * SR)) / SR
    sig = rng.normal(0, 1, len(x)) * np.exp(-x / 0.004) + 0.4 * np.sin(2 * np.pi * 1800 * x) * np.exp(-x / 0.006)
    put('fx', mono(sig), t, gain)


def tone(t, f0, f1, dur, gain=0.15):
    x = np.arange(int(dur * SR)) / SR
    freq = f0 * (f1 / f0) ** (x / dur)
    sig = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.clip(x / 0.02, 0, 1) * np.clip((dur - x) / 0.08, 0, 1)
    put('fx', mono(sig), t, gain)


def section(name):
    """Film time span of the shots on one set, as a list of (t0, t1) runs."""
    runs = []
    for s in SHOTS:
        if s['set'] == name:
            if runs and abs(runs[-1][1] - s['t0']) < 1e-3:
                runs[-1][1] = s['t1']
            else:
                runs.append([s['t0'], s['t1']])
    return runs


# dialogue, levelled; Mom through the floor (muffled)
for cue in CUES:
    x = load(os.path.join(VOD, cue['id'] + '.wav'))
    x = x * (0.085 / (float(np.sqrt((x ** 2).mean())) + 1e-9))
    if cue['who'] == 'mom':
        m = lowpass(x[:, 0], 14)
        x = mono(m * 1.3)
    put('vo', x, cue['f'])



def zap(t, gain=0.12):
    """A digital glitch: a short burst of bit-crushed noise and a falling blip."""
    x = np.arange(int(0.16 * SR)) / SR
    noise = np.sign(rng.normal(0, 1, len(x))) * (np.floor(x * 900) % 2)
    sig = noise * np.exp(-x / 0.05) * 0.5 + np.sin(2 * np.pi * np.cumsum(1800 * np.exp(-x / 0.03) + 200) / SR) * np.exp(-x / 0.06)
    put('fx', mono(sig), t, gain)


def riser(t, dur, gain=0.25):
    """Rising tone and swelling noise into a hit."""
    x = np.arange(int(dur * SR)) / SR
    u = x / dur
    freq = 70 * (900 / 70) ** u ** 1.5
    sig = np.sin(2 * np.pi * np.cumsum(freq) / SR) * 0.4 + lowpass(rng.normal(0, 1, len(x)), 30) * 6 * u
    put('fx', mono(sig * u ** 2), t, gain)


def impact(t, gain=0.5):
    """Sub drop and a boom for a title landing."""
    x = np.arange(int(2.2 * SR)) / SR
    sub = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-x / 0.6) + 24) / SR) * np.exp(-x / 0.9)
    boom = lowpass(rng.normal(0, 1, len(x)), 60) * 12 * np.exp(-x / 0.25)
    put('fx', mono(sub * 0.9 + boom), t, gain)


# opening (output time): drone, the terminal typing and glitches, the dive, the title slam, the burn into the film
OFFSET = 0.0
pad([38, 45, 50], 0.0, OPEN, 0.06, 1.5, 1.5)
for t0, t1, msg in MESSAGES:
    for k in range(len(msg)):
        key_click(t0 + k * TYPE)
    zap(t1 - 0.15, 0.10)
riser(DIVE[0], SLAM - DIVE[0], 0.3)
whoosh(DIVE[0] + 0.4, SLAM - DIVE[0] - 0.4, 0.35, low=True)
impact(SLAM, 0.6)
put('fx', game('rocket_explode'), SLAM, 0.18)
tone(SLAM + 0.8, 1800, 2600, 0.5, 0.03)                              # the light sweep: a thin shimmer
whoosh(MELT[0], 0.8, 0.25)
zap(OPEN - 0.1, 0.12)
OFFSET = PRE                                                         # everything below is placed in film time

# the Memetrix: a dark pulse; the basement: hum; the dojo: the game's battle music
bpm = 96
for t0, t1 in sorted(section('FLOOR') + section('ROOFTOP')):
    pad([40, 47, 52], t0, t1 - t0, 0.05)
    beat = 60 / bpm
    k = 0
    while t0 + k * beat < t1:
        if t0 > EV['bullet_time'] - 10 or k % 2 == 0:          # the agents' scene runs on a full four-on-the-floor
            kick(t0 + k * beat, 0.22)
        hat(t0 + k * beat + beat / 2, 0.035)
        k += 1
for t0, t1 in section('BASEMENT'):
    x = np.arange(int((t1 - t0) * SR)) / SR
    hum = 0.5 * np.sin(2 * np.pi * 60 * x) + 0.25 * np.sin(2 * np.pi * 120 * x) + 0.2 * lowpass(rng.normal(0, 1, len(x)), 50) * 8
    put('amb', mono(hum * np.clip(x / 0.3, 0, 1) * np.clip((t1 - t0 - x) / 0.3, 0, 1)), t0, 0.03)
battle = game('mus_battle')
for t0, t1 in section('DOJO'):
    seg = battle[:int((t1 - t0) * SR)]
    env = np.clip(np.arange(len(seg)) / SR / 0.5, 0, 1) * np.clip((t1 - t0 - np.arange(len(seg)) / SR) / 0.6, 0, 1)
    put('mus', seg * env[:, None], t0, 0.28)

# effects on the story beats
put('fx', game('spell_pump'), EV['take'] - 0.2, 0.3)
whoosh(EV['take'] + 1.5, 1.2, 0.35)
for k in range(3):
    put('fx', game('swing'), EV[f'swing{k}'], 0.4)
for k in range(2):                                                      # Slerf's paw blocks swings one and two
    put('fx', game('tower_hit'), EV[f'swing{k}'] + 0.12, 0.25)
if 'push' in EV:
    put('fx', game('punch_heavy'), EV['push'], 0.45)                    # the lazy push lands
put('fx', game('house_stomp'), EV['fall'], 0.35)                        # Anon hits the mat
whoosh(EV['card_bend'], 1.4, 0.12)
put('fx', game('emote_pop'), EV['cookie'], 0.35)
put('fx', game('tower_shot'), EV['fire'], 0.45)
bt = next(s for s in SHOTS if s.get('bullet'))
x = np.arange(int((bt['t1'] - bt['t0']) * SR)) / SR                    # bullet time: everything drops to a slow, deep rush
rush = lowpass(rng.normal(0, 1, len(x)), 400) * 30 * np.sin(np.pi * x / x[-1]) ** 0.5
put('fx', mono(rush), bt['t0'], 0.3)
tone(bt['t0'], 90, 45, bt['t1'] - bt['t0'], 0.18)
for k in range(7):
    whoosh(bt['t0'] + 0.6 + k * 0.55, 1.4, 0.18, low=True)
put('fx', game('tower_shot'), EV['fire2'], 0.45)
put('fx', game('spell_pump'), EV['turn_green'], 0.45)
for k in range(7):
    put('fx', game('deploy_drop'), EV['drop'] + k * 0.08, 0.12)
# closing: out of the film, a whoosh per cast card, the menu music, the logo landing, the tagline typed
zap(T_CARD, 0.14)
menu = game('mus_menu')
seg = menu[:int((END_LEN - 0.4) * SR)]
env = np.clip(np.arange(len(seg)) / SR / 0.8, 0, 1) * np.clip(((END_LEN - 0.4) - np.arange(len(seg)) / SR) / 1.5, 0, 1)
put('mus', seg * env[:, None], T_CARD + 0.3, 0.3)
for k in range(len(CAST)):
    whoosh(T_CARD + CARD0 + k * CARD_DUR - 0.08, 0.3, 0.10)
    key_click(T_CARD + CARD0 + k * CARD_DUR + 0.05, 0.05)
impact(T_CARD + LOGO_T, 0.4)
put('fx', game('victory'), T_CARD + LOGO_T + 0.3, 0.3)
for k in range(len('THERE IS NO CHART.')):
    key_click(T_CARD + LOGO_T + 1.6 + k * 0.07, 0.05)

# silence the music in the bullet time and the freeze; mix with effects and music ducked under speech
mute = np.ones(n, np.float32)
i0, i1 = int((bt['t0'] + PRE) * SR), int((bt['t1'] + PRE) * SR)
mute[i0:i1] = 0.15
speech = np.abs(BUS['vo']).max(axis=1)
k = int(0.12 * SR)
speech = np.convolve((speech > 0.01).astype(np.float32), np.ones(k) / k, 'same')
speech = np.convolve(speech, np.ones(k * 3) / (k * 3), 'same')
duck = np.clip(speech * 1.5, 0, 1)[:, None]
active = speech > 0.5
mix = BUS['vo'] * 2.6 + BUS['mus'] * mute[:, None] * (1 - 0.65 * duck) * 0.6 + BUS['fx'] * (1 - 0.6 * duck) * 0.6 + BUS['amb'] * 0.8
for name, gain in (('vo', 2.6), ('mus', 0.6 * 0.35), ('fx', 0.6 * 0.4), ('amb', 0.8)):
    level = 20 * math.log10(float(np.sqrt(((BUS[name] * gain)[active] ** 2).mean())) + 1e-9)
    print(f'bus {name} level while someone speaks (after gain and ducking, approx.): {level:.1f} dB')
fade_out = np.ones(n, np.float32)
i0 = int((END - 1.0) * SR)
fade_out[i0:int(END * SR)] = np.linspace(1, 0, int(END * SR) - i0)
fade_out[int(END * SR):] = 0
mix = np.tanh(mix * fade_out[:, None] * 0.9) * 0.95
sf.write(os.path.join(OUT, 'mix.wav'), mix[:int(END * SR)], SR)
print('MIX-DONE')
