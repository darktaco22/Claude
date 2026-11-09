"""7 CENTS soundtrack: Kokoro voices, rain (loud outside, muffled inside), fluorescent hum, the ring scraping
under the glass, the urn's clank, coin clinks, the cigarette drag, the game's RUG PULL / GOD CANDLE moments,
SLERF's snort, and an end-card stinger. No laugh track or canned reactions.
python3 audio.py TIMELINE.json VO_DIR SFX_DIR OUT.m4a"""
import sys, os, json, subprocess, math
import numpy as np, soundfile as sf
tl, vo, sfx, out = sys.argv[1:5]
TL = json.load(open(tl)); END = TL['end']; EC = TL['endcard']; MO = TL['morning']
SR = 44100; gen = os.path.join(os.path.dirname(out), 'gen_sfx'); os.makedirs(gen, exist_ok=True); rng = np.random.default_rng(11)
def write(n, a): a = np.asarray(a, np.float32); a /= max(1e-6, np.abs(a).max()); sf.write(f'{gen}/{n}.wav', a * 0.9, SR); return f'{gen}/{n}.wav'
def env(n, a=0.005, r=0.05): t = np.arange(n) / SR; return np.clip(np.minimum(1, t / a) * np.minimum(1, (n / SR - t) / r), 0, 1)
def lp(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
def clink(f0, n=0.6, decay=9.0):
    N = int(n * SR); t = np.arange(N) / SR
    return sum(np.sin(2 * math.pi * f0 * r * t) * np.exp(-t * decay * r ** 0.5) / r for r in (1, 2.76, 5.4, 8.9))
write('clink', clink(2200)); write('coin', clink(3100, 0.5, 12))
N = int(1.5 * SR); t = np.arange(N) / SR
write('scrape', lp(rng.normal(0, 1, N), 3) * (0.4 + 0.6 * np.abs(np.sin(t * 9))) * env(N, 0.05, 0.2))
N = int(0.9 * SR); t = np.arange(N) / SR
write('clank', clink(420, 0.9, 5) + lp(rng.normal(0, 0.8, N), 12) * np.exp(-t * 30))
N = int(1.2 * SR); t = np.arange(N) / SR
write('exhale', lp(rng.normal(0, 1, N), 9) * np.sin(math.pi * t / t[-1]) ** 1.5)
N = int(1.4 * SR); t = np.arange(N) / SR   # RUG PULL: a whoosh and a spill of coins
wh = lp(rng.normal(0, 1, N), 5) * np.exp(-((t - 0.25) / 0.18) ** 2)
coins = np.zeros(N)
for k in range(26):
    s0 = int(rng.uniform(0.25, 1.1) * SR); c = clink(rng.uniform(2600, 4200), 0.25, 18) * rng.uniform(0.2, 0.6); e = min(N, s0 + len(c)); coins[s0:e] += c[:e - s0]
write('rug', wh * 0.8 + coins)
N = int(1.6 * SR); t = np.arange(N) / SR   # GOD CANDLE: a rising shimmer
f = 300 * 2 ** (t * 1.6); ph = 2 * math.pi * np.cumsum(f) / SR
write('candle', (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * env(N, 0.05, 0.4))
N = int(1.6 * SR); t = np.arange(N) / SR   # USELESS's victory: three bright coin notes
v = np.zeros(N)
for k, (t0, f0) in enumerate([(0.0, 2400), (0.14, 3000), (0.28, 3600)]):
    s0 = int(t0 * SR); c = clink(f0, 0.9, 6); e = min(N, s0 + len(c)); v[s0:e] += c[:e - s0]
write('win', v)
N = int(0.5 * SR); t = np.arange(N) / SR   # SLERF's snort awake
write('snort', lp(rng.normal(0, 1, N), 14) * np.exp(-t * 7) * (1 + np.sin(2 * math.pi * 38 * t)))
N = int(3.5 * SR); t = np.arange(N) / SR   # end card stinger: a fat major chord with a sub hit
ch = sum(np.sin(2 * math.pi * fq * t) * (0.6 if fq < 200 else 1.0) for fq in (98, 196, 247, 294, 392)) * np.exp(-t * 1.1)
write('sting', ch + 1.5 * np.sin(2 * math.pi * 49 * t) * np.exp(-t * 4))
N = int(END * SR); t = np.arange(N) / SR   # neon transformer buzz
write('buzz', (np.sign(np.sin(2 * math.pi * 120 * t)) * 0.3 + np.sin(2 * math.pi * 240 * t) * 0.2) * 0.5)

G = lambda n: f'{gen}/{n}.wav'; X = lambda n: f'{sfx}/{n}.wav'
N = int(0.35 * SR); t = np.arange(N) / SR
write('tap', np.exp(-t * 60) * np.sin(2 * math.pi * 1800 * t) * 0.6 + lp(rng.normal(0, 1, N), 3) * np.exp(-t * 90) * 0.3)
N = int(0.5 * SR); t = np.arange(N) / SR
write('chaching', sum(np.sin(2 * math.pi * f0 * t) * np.exp(-t * 7) for f0 in (1320, 1760, 2640)) + clink(3400, 0.5, 10) * 0.6)
N = int(END * SR); t = np.arange(N) / SR
birds = np.zeros(N)
for k in range(28):
    s0 = int(rng.uniform(MO, END - 1) * SR); M = int(0.18 * SR); u = np.arange(M) / SR; f = rng.uniform(2800, 4200) + 1800 * np.sin(u * rng.uniform(40, 70))
    e = min(N, s0 + M); birds[s0:e] += (np.sin(2 * math.pi * np.cumsum(f) / SR) * np.sin(math.pi * u / u[-1]))[:e - s0] * rng.uniform(0.3, 0.8)
write('birds', birds)
cues = []
for L in TL['lines']: cues.append((f"{vo}/{L['id']}.wav", L['t'], 1.0 if L['who'] != 'kid' or L['t'] > MO else 0.8, 'highpass=f=90,aecho=0.8:0.15:18:0.06,'))
taps = [0.25, 1.05, 1.65, 2.15, 2.55, 2.9, 3.18, 3.44, 3.68, 3.9]
for tt in taps:
    cues += [(G('tap'), 2.4 + tt, 0.35, ''), (G('chaching'), 2.4 + tt + 0.32, 0.3, '')]
cues += [(X('room'), 0.0, 0.05, f'atrim=0:{MO},lowpass=f=600,'), (G('birds'), 0.0, 0.18, ''), (G('candle'), 25.0, 0.35, ''),
         (G('sting'), EC, 0.6, ''), (G('clank'), 23.7, 0.12, '')]
ins, flt = [], []
for i, (p, t0, vol, extra) in enumerate(cues):
    ins += ['-i', p]; ms = int(t0 * 1000)
    flt.append(f'[{i}:a]aresample={SR},aformat=channel_layouts=mono,{extra}volume={vol},adelay={ms}|{ms}[c{i}]')
n = len(cues); mix = ''.join(f'[c{i}]' for i in range(n))
flt.append(f'{mix}amix=inputs={n}:normalize=0:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=11,apad,atrim=0:{END},afade=t=out:st={END - 0.5}:d=0.5[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', str(SR), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(n, 'cues ->', out)
