"""THE REAPING score + sfx, synthesized (44.1 kHz mono float arrays)."""
import sys, numpy as np
sys.path.insert(0, '/root/road/who'); import synth as S
SR = 44100; t = S.t; env = S.env; lp = S.lp; hp = S.hp; reverb = S.reverb
def saw(f, d, det=0.0):
    tt = t(d); return 2 * ((tt * f * (1 + det)) % 1.0) - 1
def braam(d=3.2, root=36.71):
    """big low brass hit: detuned saw stack, swelling filter, saturation, tail"""
    n = int(d * SR); x = np.zeros(n)
    for f, g in [(root, 1.0), (root * 2, 0.8), (root * 3, 0.45), (root * 1.5 * 2, 0.35)]:
        for det in (-0.004, 0.0, 0.005): x += saw(f, d, det)[:n] * g
    tt = np.arange(n) / SR; cut = 180 + 2600 * np.exp(-tt * 1.6) * (1 - np.exp(-tt * 30))
    y = np.zeros(n); a = 0.0
    for i in range(0, n, 256):   # time-varying one-pole lowpass in blocks
        k = 1 - np.exp(-2 * np.pi * cut[i] / SR); seg = x[i:i + 256]; o = np.empty_like(seg)
        for j, v in enumerate(seg): a += k * (v - a); o[j] = a
        y[i:i + 256] = o
    y = np.tanh(y * 1.6) * env(n, 0.04, d * 0.7); y = reverb(y, 2.6, 0.3); y = y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))
    sub = np.sin(2 * np.pi * root * tt) * np.exp(-tt * 1.2) * 0.8
    return (y / (np.abs(y).max() + 1e-9) * 0.85 + sub) / 1.6
def cannon(d=3.5):
    """distant cannon: thump + crack + long rumble"""
    n = int(d * SR); tt = np.arange(n) / SR; rng = np.random.default_rng(5)
    th = np.sin(2 * np.pi * (48 * np.exp(-tt * 3) + 28) * tt) * np.exp(-tt * 4.0)
    cr = hp(rng.standard_normal(n), 900) * np.exp(-tt * 40) * 0.5
    ru = lp(rng.standard_normal(n), 160) * np.exp(-tt * 1.3) * 2.2
    y = th + cr + ru; y = reverb(y, 3.2, 0.45)[:n]; return y / (np.abs(y).max() + 1e-9)
def crickets(d=2.0):
    n = int(d * SR); tt = np.arange(n) / SR; y = np.zeros(n)
    for f0, ph, rate in [(4400, 0.0, 3.1), (4700, 0.37, 2.6)]:
        car = np.sin(2 * np.pi * f0 * tt); chirp = (np.sin(2 * np.pi * 32 * tt) > 0.2).astype(float)
        gate = ((tt * rate + ph) % 1.0) < 0.22; y += car * chirp * gate * 0.25
    return lp(y, 7000) * env(n, 0.05, 0.3)
def pulse(d, bpm=124, notes=(0, 0, 3, 0, 5, 0, 3, 7), root=73.42):
    """staccato low-string ostinato (8ths)"""
    n = int(d * SR); y = np.zeros(n); step = 60 / bpm / 2; i = 0; tt0 = t(step * 0.9)
    while i * step < d:
        f = root * 2 ** (notes[i % len(notes)] / 12); s = int(i * step * SR)
        b = (saw(f, step * 0.9) + 0.5 * saw(f * 2, step * 0.9, 0.003)) * np.exp(-tt0 * 9)
        b = lp(b, 1400); m = min(len(b), n - s)
        if m > 0: y[s:s + m] += b[:m] * (0.75 + 0.25 * (i % 2 == 0))
        i += 1
    return y * 0.5
def pad(d, chord=(0, 3, 7), root=146.83):
    n = int(d * SR); y = np.zeros(n)
    for iv in chord:
        f = root * 2 ** (iv / 12)
        for det in (-0.003, 0.003): y += saw(f, d, det)[:n]
    y = lp(y, 1200) * env(n, 1.2, 1.5); return y / (np.abs(y).max() + 1e-9) * 0.5
def jingle():
    """talk-show sting: bright major arpeggio"""
    notes = [0, 4, 7, 12, 16]; out = np.zeros(int(1.6 * SR))
    for i, iv in enumerate(notes):
        f = 523.25 * 2 ** (iv / 12); b = S.note(f, 0.9, 0.8); s = int(i * 0.09 * SR); out[s:s + len(b)] += b[:len(out) - s] * 0.6
    return reverb(out, 1.4, 0.25)[:len(out)]
def hop():
    """comic 'boing'-less step-back: a quick cartoon slide-whistle down"""
    d = 0.5; tt = t(d); f = 1400 * np.exp(-tt * 3.2) + 300; ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(len(tt), 0.01, 0.15) * 0.45
whoosh, riser, boom, heartbeat, tick = S.whoosh, S.riser, S.boom, S.heartbeat, S.tick
if __name__ == '__main__':
    import soundfile as sf
    for nm, a in [('braam', braam()), ('cannon', cannon()), ('crickets', crickets()), ('pulse', pulse(4)), ('pad', pad(3)), ('jingle', jingle()), ('hop', hop())]:
        sf.write(f'/root/road/reap/test_{nm}.wav', a.astype('float32'), SR); print(nm, round(len(a) / SR, 2), round(float(np.abs(a).max()), 3), np.isfinite(a).all())
