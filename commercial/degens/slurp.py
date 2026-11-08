"""A synthetic straw slurp: sucked air through liquid (band-passed noise with a fast gurgle), bubble
pops and a rattly dry finish. python3 slurp.py out.wav"""
import sys, numpy as np, soundfile as sf
sr = 44100; rng = np.random.default_rng(4); dur = 0.95; n = int(sr * dur); t = np.arange(n) / sr
def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
noise = rng.normal(0, 1, n)
air = bandpass(noise, 900, 4200)
# the gurgle: liquid modulating the airflow at ~22-35 Hz, wobbling
gurgle = 0.5 + 0.5 * np.sin(2 * np.pi * (22 + 13 * np.sin(2 * np.pi * 1.7 * t)) * t + rng.normal(0, 0.4, n).cumsum() * 0.002)
env = np.clip(t / 0.06, 0, 1) * np.clip((dur - t) / 0.12, 0, 1)
slurp = air * gurgle ** 2.2 * env * (0.6 + 0.6 * (t > 0.55))           # louder rattle near the bottom of the drink
# bubbles: short rising chirps
for k in range(26):
    t0 = rng.uniform(0.05, dur - 0.08); f0 = rng.uniform(380, 900); L = rng.uniform(0.012, 0.03)
    m = (t >= t0) & (t < t0 + L); tt = t[m] - t0
    slurp[m] += np.sin(2 * np.pi * (f0 * tt + 6000 * tt ** 2)) * np.exp(-tt / (L / 3)) * rng.uniform(0.6, 1.4) * (1.6 if t0 > 0.55 else 0.7)
slurp /= np.abs(slurp).max(); sf.write(sys.argv[1], (slurp * 0.8).astype(np.float32), sr); print('slurp', dur, 's')
