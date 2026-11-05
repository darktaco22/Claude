"""
Synthesizes the commercial's soundtrack (music + sound effects) with numpy.
Every sound effect is placed on the same frame numbers as the animation in build_commercial.py (30 fps).

    python3 make_audio.py out.wav
"""
import sys, wave
import numpy as np

SR = 44100
FPS = 30
DUR = 20.0
N = int(SR * DUR)
rng = np.random.default_rng(3)
L = np.zeros(N)
R = np.zeros(N)

def t_of(frame):
    return (frame - 1) / FPS

def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * (1 + min(pan, 0))

def env(n, a=0.005, d=None, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    e *= np.exp(-curve * t / (d or (n / SR)))
    return e

def tone(freq, dur, kind="sine"):
    t = np.arange(int(dur * SR)) / SR
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "tri":
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1
    return np.sin(ph)

def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y

def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))

def hp(x):  # crude highpass
    return x - lowpass(x, 3000)

# ------------------------------------------------------------ drum kit
def kick():
    d = 0.35
    t = np.arange(int(d * SR)) / SR
    f = 50 + 120 * np.exp(-t * 30)
    return tone(f, d) * env(len(t), 0.001, 0.12, 3)

def clap():
    n = noise(0.18)
    return hp(n) * env(len(n), 0.001, 0.06, 3) * 0.8

_hat_src = hp(noise(0.06))
def hat():
    return _hat_src * env(len(_hat_src), 0.001, 0.02, 3)

# ------------------------------------------------------------ music
BPM = 120
beat = 60 / BPM
bars = int(DUR / (beat * 4)) + 1
# Cm - Ab - Eb - Bb (minor pop / trap-ish)
roots = [48, 44, 51, 46]
chords = [[60, 63, 67], [56, 60, 63], [63, 67, 70], [58, 62, 65]]
mtof = lambda m: 440 * 2 ** ((m - 69) / 12)

def muted(t):
    # dramatic silence during the rug pull, music back on PUMP IT
    return t_of(386) <= t < t_of(418)

for b in range(bars):
    for k in range(4):
        t = (b * 4 + k) * beat
        if t >= DUR - 0.3 or muted(t):
            continue
        intro = t < t_of(18)
        if not intro:
            add(kick(), t, 0.9)
            if k in (1, 3):
                add(clap(), t, 0.35)
        for h in (0, 0.5):
            if not muted(t + h * beat):
                add(hat(), t + h * beat, 0.18 if h else 0.1, pan=0.3)
        # bass: root on 8ths
        root = roots[b % 4]
        for h in (0, 0.5):
            tt = t + h * beat
            if muted(tt) or intro:
                continue
            s = tone(mtof(root - 12 + (12 if (k == 3 and h) else 0)), beat * 0.45, "saw")
            s = lowpass(s, 380) * env(len(s), 0.004, 0.25, 2)
            add(s, tt, 0.55)
        # plucky arp
        ch = chords[b % 4]
        for q in range(4):
            tt = t + q * beat / 4
            if muted(tt):
                continue
            note = ch[(k * 4 + q) % 3] + (12 if q % 2 else 0)
            s = tone(mtof(note), 0.16, "square")
            s = lowpass(s, 2200) * env(len(s), 0.002, 0.05, 3)
            add(s, tt, 0.07, pan=-0.25 if q % 2 else 0.25)

# pad
for b in range(bars):
    t = b * 4 * beat
    if t >= DUR:
        break
    ch = chords[b % 4]
    s = sum(tone(mtof(n) * (1 + d), 4 * beat, "saw") for n in ch for d in (-0.003, 0.003))
    s = lowpass(s, 900) * np.minimum(1, np.minimum(np.arange(len(s)) / (0.3 * SR), (len(s) - np.arange(len(s))) / (0.3 * SR)))
    g = 0.0 if muted(t) or muted(t + 2 * beat) else 0.03
    add(s, t, g)

# ------------------------------------------------------------ sound effects
def whoosh(dur=0.45, up=True):
    n = noise(dur)
    t = np.arange(len(n)) / SR
    cut = (600 + 5000 * (t / dur)) if up else (5600 - 5000 * (t / dur))
    out = np.empty_like(n)
    acc = 0.0
    for i, v in enumerate(n):
        a = np.exp(-2 * np.pi * cut[i] / SR)
        acc = (1 - a) * v + a * acc
        out[i] = acc
    e = np.sin(np.pi * t / dur) ** 2
    return out * e * 2.0

def impact(big=1.0):
    d = 0.9
    t = np.arange(int(d * SR)) / SR
    boom = tone(40 + 90 * np.exp(-t * 18), d) * env(len(t), 0.001, 0.35 * big, 3)
    crack = lowpass(noise(d), 2500) * env(len(t), 0.001, 0.08, 3)
    return boom + crack * 0.8

def boing(f0=220, f1=520, dur=0.25):
    t = np.arange(int(dur * SR)) / SR
    f = f0 + (f1 - f0) * (t / dur) + 30 * np.sin(2 * np.pi * 18 * t)
    return tone(f, dur, "tri") * env(len(t), 0.002, dur, 2)

def coin():
    s = tone(1975.5, 0.08, "square") * 0.5
    s2 = tone(2637, 0.3, "square") * 0.5
    a = lowpass(s, 6000) * env(len(s), 0.001, 0.08, 1)
    b = lowpass(s2, 6000) * env(len(s2), 0.001, 0.3, 4)
    return np.concatenate([a, b])

def riser(dur):
    t = np.arange(int(dur * SR)) / SR
    f = 200 * 2 ** (3 * t / dur)
    s = tone(f, dur, "saw") + tone(f * 1.5, dur, "saw") * 0.5
    return lowpass(s, 3000) * (t / dur) ** 2 * 0.5 + hp(noise(dur)) * (t / dur) ** 3 * 0.4

def slide_down(dur=0.7):
    t = np.arange(int(dur * SR)) / SR
    f = 330 * 2 ** (-1.0 * t / dur)
    s = tone(f * (1 + 0.01 * np.sin(2 * np.pi * 6 * t)), dur, "saw")
    return lowpass(s, 1400) * env(len(t), 0.02, dur, 1.5)

def shimmer(dur=1.2):
    out = np.zeros(int(dur * SR))
    for i, m in enumerate([84, 88, 91, 96, 100, 103]):
        s = tone(mtof(m), dur - i * 0.08) * env(int((dur - i * 0.08) * SR), 0.005, 0.5, 3)
        j = int(i * 0.08 * SR)
        s = s[: len(out) - j]
        out[j:j + len(s)] += s
    return out * 0.4

def stinger(notes, dur=0.5):
    s = sum(tone(mtof(n), dur, "saw") for n in notes)
    return lowpass(s, 2500) * env(int(dur * SR), 0.003, dur, 2.5)

# S1
add(whoosh(0.6, up=False), t_of(1), 0.35)
add(impact(), t_of(18), 0.9)
add(boing(), t_of(20), 0.25, pan=-0.4)
add(whoosh(0.5, up=False), t_of(36), 0.3)
add(impact(), t_of(50), 0.9)
add(boing(200, 420), t_of(52), 0.25, pan=0.4)
add(stinger([60, 67, 72, 75]), t_of(62), 0.35)
add(impact(0.6), t_of(62), 0.4)
# S2
add(whoosh(0.35), t_of(89), 0.4)
for i in range(4):
    add(whoosh(0.3), t_of(96 + i * 7), 0.25, pan=-0.6 + i * 0.4)
add(shimmer(1.4), t_of(176), 0.6)
add(stinger([72, 76, 79, 84], 0.8), t_of(184), 0.25)
# S3
add(whoosh(0.35), t_of(209), 0.4)
for f in range(227, 268, 6):
    add(kick(), t_of(f), 0.35, pan=0.2)
add(impact(1.6), t_of(268), 1.0)
add(impact(1.2), t_of(285), 0.7)
for i in range(16):
    add(coin(), t_of(286) + i * 0.06 + rng.uniform(0, 0.03), 0.12, pan=rng.uniform(-0.6, 0.6))
add(riser(0.75), t_of(298), 0.35)
add(impact(1.4), t_of(322), 0.7)
add(stinger([60, 64, 67, 72], 0.7), t_of(322), 0.3)
# S4
add(whoosh(0.3, up=True), t_of(384), 0.6)
add(boing(500, 900, 0.3), t_of(388), 0.25)
add(impact(0.8), t_of(406), 0.7)
add(slide_down(0.8), t_of(407), 0.35)
add(boing(150, 900, 0.4), t_of(418), 0.35)
add(impact(1.0), t_of(430), 0.7)
# S5
add(whoosh(0.35), t_of(449), 0.4)
add(riser(0.4), t_of(456), 0.3)
add(impact(2.0), t_of(468), 1.1)
add(stinger([48, 60, 63, 67, 72], 1.4), t_of(468), 0.4)
add(shimmer(1.6), t_of(470), 0.5)
for i in range(22):
    add(coin(), t_of(472) + i * 0.17 + rng.uniform(0, 0.1), 0.07, pan=rng.uniform(-0.7, 0.7))
add(stinger([60, 63, 67, 72], 0.6), t_of(492), 0.25)
add(impact(1.0), t_of(588), 0.6)
add(stinger([48, 60, 67, 72, 75], 1.0), t_of(588), 0.35)

# ------------------------------------------------------------ master
fade = np.ones(N)
fn = int(0.5 * SR)
fade[-fn:] = np.linspace(1, 0, fn)
mix = np.stack([L, R], axis=1) * fade[:, None]
mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.89
out = sys.argv[1] if len(sys.argv) > 1 else "soundtrack.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote", out)
