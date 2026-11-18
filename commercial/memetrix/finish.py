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
CARD_LEN = 4.0
T_FILM = T_CARD + CARD_LEN
NF = int(round(T_FILM * FPS))
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


MESSAGES = [(0.5, 2.1, 'Wake up, Anon...'), (2.1, 3.3, 'The chart has you...'), (3.3, 4.2, 'Follow the green candle.')]


def opening(t):
    """0..TITLE: code rain, typed messages on a black terminal line, then the title over the rain."""
    a = rain_array(t, 0.55 + 0.45 * ease(t / 0.6))
    msg_on = t < 4.2
    if msg_on:
        a = a * 0.35
    a = a * VIG * ease(t / 0.4)
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im, 'RGBA')
    for t0, t1, msg in MESSAGES:
        if t0 <= t < t1:
            shown = msg[:int((t - t0) / 0.055)]
            cursor = '_' if int(t * 3) % 2 == 0 else ' '
            text(d, (180, H / 2), shown + cursor, mono_font(44), rgba(GREEN), 'lm')
    if t >= 4.0:
        k = ease((t - 4.0) / 0.35)
        jitter = int(6 * (1 - k) * math.sin(t * 90))
        glow = Image.new('RGBA', (W, H))
        gd = ImageDraw.Draw(glow)
        text(gd, (W / 2 + jitter, H / 2 - 30), 'THE MEMETRIX', lil(180), rgba(GREEN, 255 * k), 'mm')
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)))
        im.alpha_composite(glow)
        text(d, (W / 2, H / 2 + 90), 'A  MEME ROYALE  PARODY', rub(30, 700), rgba(WHITE, 220 * k), 'mm')
    return im


BG = None


def end_card(t):
    global BG
    if BG is None:
        BG = Image.open(os.path.join(A, 'logo.png')).convert('RGBA')
    u = t - T_CARD
    a = rain_array(t, 0.35) * ease(u / 0.4) * VIG
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    k = ease((u - 0.1) / 0.5)
    size = int(420 * (1.05 - 0.05 * k))
    mark = BG.resize((size, int(size * BG.height / BG.width)), Image.LANCZOS)
    mark.putalpha(mark.getchannel('A').point(lambda v: int(v * k)))
    im.alpha_composite(mark, ((W - mark.width) // 2, 170))
    d = ImageDraw.Draw(im, 'RGBA')
    k2 = ease((u - 0.7) / 0.4)
    text(d, (W / 2, 690), 'THERE IS NO CHART.', rub(54, 800), rgba(GREEN, 255 * k2), 'mm')
    text(d, (W / 2, 770), 'FREE TO PLAY  ·  memeroyale.imaginestudio.fun', rub(30, 500), rgba(WHITE, 200 * k2), 'mm')
    out = ease((T_FILM - t) / 0.5)
    rgb = im.convert('RGB')
    if out < 1:
        rgb = Image.fromarray((np.asarray(rgb, np.float32) * out).astype(np.uint8))
    return rgb


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


def frame(f):
    t = (f - 1) / FPS
    if t < TITLE:
        im = opening(t).convert('RGB')
    elif f > N3D:
        im = end_card(t)
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
        a = a + np.random.default_rng(f).normal(0, 0.008, (H, W, 1)).astype(np.float32)
        a[:BAR] = 0
        a[H - BAR:] = 0
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        draw_captions(ImageDraw.Draw(im, 'RGBA'), t)
        im = im.convert('RGB')
    im.save(os.path.join(OUT, f'c_{f:04d}.jpg'), quality=94, subsampling=0)


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


def put(bus, x, t, gain=1.0):
    i = int(t * SR)
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

# opening: typing, a low drone under the rain, a hit on the title
for t0, t1, msg in MESSAGES:
    for k in range(len(msg)):
        key_click(t0 + k * 0.055)
pad([38, 45, 50], 0.0, TITLE + 0.5, 0.06, 0.8, 1.5)
tone(4.0, 60, 40, 1.4, 0.3)
whoosh(3.9, 0.6, 0.3)

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
put('fx', game('punch_heavy'), EV['fall'], 0.45)
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
put('fx', game('victory'), T_CARD + 0.2, 0.35)

# silence the music in the bullet time and the freeze; mix with effects and music ducked under speech
mute = np.ones(n, np.float32)
i0, i1 = int(bt['t0'] * SR), int(bt['t1'] * SR)
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
