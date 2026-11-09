"""NO UTILITY sound: an original music-box score written to the edit, a pad and a horn (synthesized here), and the game's
own sounds (assets/audio: hits, coin jingles, deploys, the announcer, the victory fanfare). No laugh track, no voices
but the game's. python3 audio.py TIMELINE.json GAME_AUDIO_DIR OUT.m4a"""
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
tl = json.load(open(sys.argv[1])); GA = sys.argv[2]; out = sys.argv[3]
SR = 44100; END = tl['end'] + 3.0; N = int(END * SR)
gen = os.path.join(os.path.dirname(os.path.abspath(out)), 'gen_sfx'); os.makedirs(gen, exist_ok=True)
rng = np.random.default_rng(11)
def mf(m): return 440.0 * 2 ** ((m - 69) / 12)
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def m(s): return NOTE[s[:-1]] + 12 * (int(s[-1]) + 1)


def tine(f, dur=2.4, vel=1.0):
    """A music-box tine: inharmonic partials, a bright click, a long decay."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
         + 0.12 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12))
    y[:int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    return y * vel


def put(buf, t0, y, g=1.0):
    s = int(t0 * SR); e = min(len(buf), s + len(y))
    if s < len(buf): buf[s:e] += y[:e - s] * g


def write(name, a, norm=True):
    a = np.asarray(a, np.float32)
    if norm: a /= max(1e-6, np.abs(a).max()); a *= 0.9
    p = f'{gen}/{name}.wav'; sf.write(p, a, SR); return p


# --- the theme. A minor lullaby in 3/4; the morning answers it in C major.
def phrase(buf, t0, beat, notes, vel=0.8):
    for b, n, v in notes: put(buf, t0 + b * beat, tine(mf(m(n)), 2.6, v * vel))
A = [(0, 'E5', 1), (1, 'A5', .8), (2, 'C6', .9), (3, 'B5', 1), (4, 'A5', .7), (5, 'E5', .7), (6, 'F5', .9), (7, 'A5', .8), (8, 'D6', 1),
     (9, 'C6', .9), (10.5, 'B5', .7), (0, 'A3', .5), (3, 'E3', .45), (6, 'D3', .45), (9, 'E3', .45)]
Am = [(0, 'E5', 1), (1, 'G5', .8), (2, 'C6', .9), (3, 'B5', 1), (4, 'G5', .7), (5, 'D5', .7), (6, 'F5', .9), (7, 'A5', .8), (8, 'D6', 1),
      (9, 'C6', 1), (10, 'E6', .9), (11, 'G6', .8), (12, 'C6', 1), (0, 'C3', .5), (3, 'G2', .45), (6, 'F2', .45), (9, 'C3', .5),
      (12, 'C3', .5), (12, 'E5', .6), (12, 'G5', .6)]
box = np.zeros(N)
phrase(box, 0.8, 0.68, A)                                                  # the line-up
for tt, n in ((9.3, 'E5'), (10.25, 'C5')): put(box, tt, tine(mf(m(n)), 3.0, 0.55))      # alone: two notes, slower
for tt, n in ((16.75, 'A5'), (17.15, 'C6'), (17.55, 'E6')): put(box, tt, tine(mf(m(n)), 2.5, 0.9))   # the light finds them
slow = [(b, n, v) for b, n, v in A if b <= 9]                              # after the horn, the theme again, slower, unfinished
phrase(box, 27.0, 0.95, slow[:7], 0.6)
phrase(box, tl['morning'] + 0.2, 0.62, Am)                                 # the morning: major
write('box', box)


# --- a soft string pad (detuned saws, low-passed): the stand, and the morning
def pad(chords, length):
    y = np.zeros(int(length * SR))
    for (t0, t1, notes, g) in chords:
        n0, n1 = int(t0 * SR), int(t1 * SR); t = np.arange(n1 - n0) / SR
        env = np.minimum(1, t / 1.2) * np.minimum(1, (t[-1] - t) / 1.0)
        s = np.zeros(n1 - n0)
        for nn in notes:
            f = mf(m(nn))
            for d in (-0.12, 0.0, 0.11): s += ((2 * ((f * (1 + d / 100) * t) % 1) - 1))
        y[n0:n1] += s * env * g
    k = int(SR / 900); y = np.convolve(y, np.ones(k) / k, mode='same'); y = np.convolve(y, np.ones(k) / k, mode='same')
    return y
P = pad([(16.4, 18.4, ['A3', 'C4', 'E4'], 0.5), (18.0, 22.0, ['A2', 'E3', 'A3', 'C4'], 0.55), (22.0, 26.1, ['F2', 'C3', 'A3', 'C4', 'F4'], 0.8),
         (tl['morning'], END, ['C3', 'G3', 'C4', 'E4'], 0.5)], END)
write('pad', P)

# --- heartbeat under the countdown, the horn, a muffled crowd roar beyond the tunnel walls
hb = np.zeros(N); t = np.arange(int(0.35 * SR)) / SR; thump = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 14)
for k in range(int(tl['stand']) + 1, int(tl['horn'])): put(hb, k, thump, 1.0); put(hb, k + 0.22, thump, 0.6)
write('heart', hb)
t = np.arange(int(2.6 * SR)) / SR; env = np.minimum(1, t / 0.08) * np.exp(-np.maximum(0, t - 1.6) * 3)
horn = sum((2 * ((f * t) % 1) - 1) * a for f, a in ((110, 1), (164.8, 0.6), (220, 0.5)))
k = int(SR / 1400); horn = np.convolve(horn, np.ones(k) / k, mode='same') * env
write('horn', horn)
roar = np.zeros(N); noise = rng.normal(0, 1, N)
k = int(SR / 500); noise = np.convolve(noise, np.ones(k) / k, mode='same')
for tt in [p[1] + 0.9 for p in tl['picks']]:
    s = int(tt * SR); L = int(2.0 * SR); e = min(N, s + L); u = np.arange(e - s) / SR
    roar[s:e] += noise[s:e] * np.sin(np.pi * u / 2.0) ** 2
write('roar', roar)

# --- the mix: [file, start s, volume, extra ffmpeg filters]
G = lambda n: f'{gen}/{n}.wav'; X = lambda n: f'{GA}/{n}.mp3'
CH, IM, ST, HO = tl['charge'], tl['impact'], tl['stand'], tl['horn']
cues = [(G('box'), 0, 0.85, 'aecho=0.8:0.7:120|260:0.35|0.22,'), (G('pad'), 0, 0.32, 'aecho=0.8:0.6:180:0.3,'),
        (G('heart'), 0, 0.55, ''), (G('horn'), HO, 0.6, 'aecho=0.8:0.8:300|700:0.4|0.25,'), (G('roar'), 0, 0.2, 'lowpass=f=700,')]
for p in tl['picks']: cues.append((X('deploy_drop'), p[1] + 0.02, 0.25, 'lowpass=f=2500,'))
# the arena
cues += [(X('amb_cold'), tl['arena'][0], 0.35, f"atrim=0:{tl['chosen'] - tl['arena'][0]},afade=t=out:st={tl['chosen'] - tl['arena'][0] - 0.3}:d=0.3,"),
         (X('mus_battle_cold'), tl['arena'][0], 0.28, f"atrim=8:{8 + tl['chosen'] - tl['arena'][0]},lowpass=f=1800,afade=t=out:st={tl['chosen'] - tl['arena'][0] - 0.4}:d=0.4,"),
         (X('unit_die_1'), 11.95, 0.5, ''), (X('punch_heavy_1'), 12.25, 0.6, ''), (X('whale_slam'), 12.95, 0.7, ''),
         (X('card_pick'), 15.8, 0.7, ''), (X('deploy_drop'), 16.6, 0.4, 'lowpass=f=3000,'),
         (X('amb_cold'), tl['deploy'], 0.3, f"atrim=0:{HO + 3 - tl['deploy']},"),
         (X('deploy_drop'), tl['deploy'] + 0.25, 0.8, ''), (X('coin_jingle_1'), tl['deploy'] + 0.33, 0.5, ''),
         (X('charge_rush'), CH, 0.8, ''), (X('punch_heavy_1'), IM, 0.9, ''), (X('coin_jingle_1'), IM + 0.03, 0.7, ''),
         (X('coin_jingle_2'), IM + 0.1, 0.6, ''), (X('unit_die_1'), IM + 0.55, 0.45, ''),
         (X('punch_light_1'), 22.42, 0.7, ''), (X('coin_jingle_2'), 22.45, 0.4, ''), (X('swing_1'), 22.55, 0.6, ''), (X('punch_heavy_1'), 22.78, 0.8, ''),
         (X('coin_jingle_1'), 22.8, 0.5, ''), (X('punch_light_2'), 24.47, 0.7, ''), (X('swing_2'), 24.65, 0.6, ''), (X('punch_heavy_1'), 24.88, 0.85, ''),
         (X('coin_jingle_2'), 24.9, 0.5, ''), (X('swing_1'), 25.8, 0.5, '')]
for k in range(int(ST), int(HO)): cues.append((X('countdown_tick'), k, 0.6, ''))
cues += [(X('coin_jingle_1'), 27.75, 0.35, 'aecho=0.8:0.7:200:0.3,'),
         (X('victory'), tl['victory'][0], 0.22, 'lowpass=f=1500,aecho=0.8:0.8:250:0.4,'), (X('vo_victory'), tl['victory'][0] + 0.15, 0.3, 'lowpass=f=2500,aecho=0.8:0.8:250:0.4,'),
         (X('card_pick'), tl['victory'][0] + 2.5, 0.6, ''), (X('ui_swoosh'), tl['victory'][0] + 2.6, 0.5, ''), (X('card_pick'), tl['victory'][0] + 3.15, 0.7, ''),
         (X('deploy_drop'), tl['morning'] + 0.62, 0.45, 'lowpass=f=3000,'), (X('coin_jingle_1'), tl['morning'] + 1.05, 0.5, ''),
         (X('coin_jingle_2'), tl['morning'] + 1.15, 0.45, ''), (X('bark_useless'), tl['morning'] + 1.2, 0.6, '')]
ins, flt = [], []
for i, (p, t0, vol, extra) in enumerate(cues):
    ins += ['-i', p]; ms = int(t0 * 1000)
    flt.append(f'[{i}:a]aresample={SR},aformat=channel_layouts=mono,{extra}volume={vol},adelay={ms}|{ms}[c{i}]')
n = len(cues); mix = ''.join(f'[c{i}]' for i in range(n))
flt.append(f'{mix}amix=inputs={n}:normalize=0:dropout_transition=0,loudnorm=I=-15:TP=-1.5:LRA=13,apad,atrim=0:{END},afade=t=in:d=0.4,afade=t=out:st={END - 1.2}:d=1.2[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', str(SR), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(n, 'cues ->', out)
