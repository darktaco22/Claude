"""DAWN PATROL sound: war drums, a low brass pad, radial-engine drones with a Doppler pass, falling-bomb whistles, flak and the blasts are
synthesized here; hits, slams, the tower and the fanfare are the game's own sounds. In the first-person shot the world goes deaf.
python3 audio.py TIMELINE.json GAME_AUDIO_DIR OUT.m4a"""
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
tl = json.load(open(sys.argv[1])); GA = sys.argv[2]; out = sys.argv[3]
SR = 44100; END = tl['end'] + 3.0; N = int(END * SR); rng = np.random.default_rng(5)
gen = os.path.join(os.path.dirname(os.path.abspath(out)), 'gen_air'); os.makedirs(gen, exist_ok=True)
SH = {s['name']: s for s in tl['shots']}; T = lambda n: SH[n]['t0']; E = lambda n: SH[n]['t1']
def at(shot, u): s = SH[shot]; return s['t0'] + u / s['slow']
def mf(m): return 440.0 * 2 ** ((m - 69) / 12)
def put(buf, t0, y, g=1.0):
    s = int(t0 * SR); e = min(len(buf), s + len(y))
    if 0 <= s < len(buf): buf[s:e] += y[:e - s] * g
def lp(y, hz):
    k = max(1, int(SR / hz)); return np.convolve(np.convolve(y, np.ones(k) / k, mode='same'), np.ones(k) / k, mode='same')
def write(name, a):
    a = np.asarray(a, np.float32); a /= max(1e-6, np.abs(a).max()); p = f'{gen}/{name}.wav'; sf.write(p, a * 0.9, SR); return p
def smooth(x, hz): k = max(1, int(SR / hz)); return np.convolve(x, np.ones(k) / k, mode='same')


def drum(vel=1.0, f0=62.0):
    t = np.arange(int(0.9 * SR)) / SR; f = f0 * (1 + 1.6 * np.exp(-t * 26))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5) + 0.25 * lp(rng.normal(0, 1, len(t)), 900) * np.exp(-t * 30)
    return y * vel


def blast(size):
    t = np.arange(int(2.6 * SR)) / SR; f = 70 * np.exp(-t * 2.2) + 28
    y = lp(rng.normal(0, 1, len(t)), 500) * np.exp(-t * 2.4) * 1.4 + np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.9) + 0.5 * lp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 16)
    return np.tanh(y * 1.6) * (0.45 + 0.25 * size)


def whistle(dur):
    """A falling bomb: a pitch that sinks while the noise gets nearer."""
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur; f = 3200 - 2100 * k ** 0.7
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.25 + 0.75 * k) + 0.5 * lp(rng.normal(0, 1, n), 4000) * k ** 2
    return y * np.minimum(1, t / 0.05) * (0.3 + 0.7 * k)


def pom():
    t = np.arange(int(0.3 * SR)) / SR; y = np.sin(2 * np.pi * np.cumsum(180 * np.exp(-t * 12) + 60) / SR) * np.exp(-t * 14) + 0.5 * lp(rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 40)
    return np.tanh(y * 1.5) * 0.6


# --- the planes: engine drone (two radial engines, a little out of step), loudest while they are overhead (a Doppler pass in the flyover)
def engine(t0, t1, gain_fn, f0=52.0, pass_at=None, pass_len=1.0):
    n0, n1 = int(t0 * SR), min(N, int(t1 * SR)); tt = np.arange(n1 - n0) / SR + t0
    f = f0 * np.ones(len(tt))
    if pass_at is not None: f = f * (1 + 0.28 * (1 / (1 + np.exp(-(tt - pass_at) * 4.0 / pass_len)) * -1 + 0.5) * 2)          # high while it approaches, low when it leaves
    ph = np.cumsum(f) / SR; y = np.zeros(len(tt))
    for d, g in ((1.0, 1.0), (1.037, 0.8)):
        y += g * (2 * ((ph * d) % 1) - 1) * (0.55 + 0.45 * np.sin(2 * np.pi * 9.0 * d * tt) ** 2)                 # the beat of the cylinders
    y = lp(y, 900) + 0.25 * lp(rng.normal(0, 1, len(tt)), 2500) * (0.4 + 0.6 * np.sin(2 * np.pi * 13 * tt) ** 2)
    return y * gain_fn(tt)


eng = np.zeros(N)
sm = lambda a, b, c, d: (lambda tt: np.clip((tt - a) / (b - a), 0, 1) * np.clip((d - tt) / (d - c), 0, 1))
f_over = at('flyover', 1.05)
put(eng, T('looks_up') + 0.6, engine(T('looks_up') + 0.6, E('flyover') + 0.8, sm(T('looks_up') + 0.6, T('flyover') + 0.3, f_over + 0.3, E('flyover') + 0.8), 48, pass_at=f_over, pass_len=0.9)[:], 1.0)
put(eng, T('cockpit'), engine(T('cockpit'), E('flak') + 0.3, sm(T('cockpit'), T('cockpit') + 0.4, E('flak'), E('flak') + 0.3), 56)[:], 0.9)
put(eng, T('bombrun'), engine(T('bombrun'), E('lane'), sm(T('bombrun'), T('bombrun') + 0.2, T('bombrun') + 1.4, T('bombrun') + 2.4), 62, pass_at=at('bombrun', 1.0), pass_len=0.8)[:], 0.7)
put(eng, T('hit'), engine(T('hit'), E('hit') + 0.4, sm(T('hit'), T('hit') + 0.2, E('hit'), E('hit') + 0.4), 50)[:], 0.9)
put(eng, T('dive'), engine(T('dive'), at('dive', 1.35), lambda tt: np.clip((tt - T('dive')) / 1.0, 0, 1) ** 2, 70, pass_at=at('dive', 1.2), pass_len=1.0)[:] * 1.0, 1.0)
put(eng, T('home'), engine(T('home'), E('home') + 0.6, sm(T('home'), T('home') + 0.3, T('home') + 1.5, E('home') + 0.6), 46, pass_at=T('home') + 1.5, pass_len=1.4)[:], 0.85)
write('engines', eng)

# --- drums: a march that builds from the look at the sky to the bomb run, drops out in the burning cockpit, returns for the dive
drums = np.zeros(N); beat = 0.5
def bar(t0, pat, vel): [put(drums, t0 + b * beat, drum(v * vel, 62 if v > 0.7 else 78)) for b, v in pat]
t = T('looks_up') + 0.4
while t < T('hit') - 0.2:
    k = min(1.0, (t - T('looks_up')) / (T('charge_wide') - T('looks_up'))); bar(t, [(0, 1.0), (1, 0.5), (1.5, 0.5), (2, 0.9), (3, 0.5), (3.5, 0.6)], 0.4 + 0.6 * k); t += 4 * beat
t = T('dive') - 0.5
while t < T('chute') - 0.3:
    bar(t, [(0, 1.0), (0.5, 0.5), (1, 0.8), (1.5, 0.5), (2, 1.0), (2.5, 0.5), (3, 0.8), (3.25, 0.6), (3.5, 0.7), (3.75, 0.6)], 0.9); t += 4 * beat
t = T('charge_wide')                                                  # full battle drums through the charge, the duels, the giants and the air support
while t < E('aerial_support') - 0.2:
    bar(t, [(0, 1.0), (0.5, 0.6), (1, 0.9), (1.5, 0.6), (2, 1.0), (2.5, 0.6), (3, 0.9), (3.25, 0.7), (3.5, 0.8), (3.75, 0.7)], 0.95); t += 4 * beat
for tt in (at('dive', 1.35), at('dive', 1.7), T('home') + 0.1, at('titan', 1.6), at('titan', 2.6), at('slam', 0.85)): put(drums, tt, drum(1.3, 50))
write('drums', drums)

# --- a low brass pad
pad = np.zeros(N)
def chord(t0, t1, notes, g, hz=700):
    n0, n1 = int(t0 * SR), min(N, int(t1 * SR)); tt = np.arange(n1 - n0) / SR; env = np.minimum(1, tt / 0.9) * np.minimum(1, (tt[-1] - tt) / 0.9); s = np.zeros(n1 - n0)
    for m in notes:
        for d in (-0.14, 0.0, 0.12): s += 2 * ((mf(m) * (1 + d / 100) * tt) % 1) - 1
    pad[n0:n1] += lp(s, hz) * env * g
D2, F2, A2, Bb1, C2, D3, F3, A3, Fs3 = 38, 41, 45, 34, 36, 50, 53, 57, 54
chord(0.3, T('looks_up') + 0.5, [D2, A2], 0.35, 300); chord(0.2, T('pinned'), [D2, A2, D3], 0.3, 500); chord(T('looks_up'), T('flak') + 0.2, [D2, A2, D3, F3], 0.6); chord(T('flak'), T('bombrun') + 0.2, [Bb1, F2, D3], 0.7); chord(T('wing_pass'), T('flak') + 0.2, [D2, A2, D3, F3], 0.7)
chord(T('bombrun'), T('giga') + 0.2, [D2, A2, D3, F3, A3], 0.8); chord(T('giga'), T('titan'), [Bb1, F2, D3, F3], 0.8); chord(T('titan'), T('hit') + 0.2, [D2, A2, D3, F3, A3, 62], 0.95, 1000); chord(T('dive'), T('chute') + 0.2, [C2, 43, 52, 55, 62], 0.9, 1100)
chord(T('chute'), T('home') + 0.2, [D2, A2, D3, Fs3], 0.6, 600); chord(T('home'), END, [D2, A2, D3, Fs3, A3, 62], 0.85, 1200)
write('pad', pad)

# --- blasts (the muffled ones are in the first-person shot), whistles, flak, the AA guns
ex = np.zeros(N); exm = np.zeros(N); wh = np.zeros(N); fl = np.zeros(N); gun = np.zeros(N)
for e in tl['fx']:
    if e['kind'] == 'boom':
        sh = next((s for s in tl['shots'] if s['t0'] <= e['t'] < s['t1']), None); nm = sh['name'] if sh else ''
        if nm == 'pinned': put(exm, e['t'], blast(e['size']))
        elif nm in ('flak', 'giga', 'hit', 'barrel_roll', 'charge_wide', 'duel') and e['size'] < 1.5: put(fl, e['t'], blast(e['size'] * 0.7), 0.8)
        else: put(ex, e['t'], blast(e['size']))
        if nm in ('bombrun', 'lane', 'dive', 'wing_pass', 'carpet', 'aerial_support') and e['size'] >= 1.9:
            d = 0.62 / sh['slow']; put(wh, e['t'] - d, whistle(d), 0.9)
for tt in np.arange(T('flak') + 0.1, E('flak'), 0.2): put(gun, tt, pom(), 0.7 * (0.6 + 0.4 * rng.random()))
for tt in np.arange(T('giga'), E('giga'), 0.26): put(gun, tt, pom(), 0.6)
for nm_ in ('barrel_roll', 'charge_wide', 'aerial_support'):
    for tt in np.arange(T(nm_) + 0.1, E(nm_), 0.22): put(gun, tt, pom(), 0.55 * (0.6 + 0.4 * rng.random()))
write('blasts', ex); write('blasts_muffled', lp(exm, 220)); write('flak', fl); write('whistles', wh); write('guns', gun)
POV = [(0.0, E('pinned') + 0.4)]; tt = np.arange(N) / SR
env = np.zeros(N)
for a, b in POV: env = np.maximum(env, np.clip(np.minimum((tt - a) / 0.25, (b + 0.8 - tt) / 1.0), 0, 1))
ring = (np.sin(2 * np.pi * 3150 * tt) + 0.5 * np.sin(2 * np.pi * 5230 * tt)) * env; hb = np.zeros(N); th = np.arange(int(0.35 * SR)) / SR; thump = np.sin(2 * np.pi * 50 * th) * np.exp(-th * 13)
t = 0.4
while t < E('pinned') + 0.2: put(hb, t, thump, 0.9); put(hb, t + 0.24, thump, 0.55); t += 0.95
t = T('hit')                                                           # a heartbeat in the burning cockpit
while t < E('hit'): put(hb, t, thump, 0.8); put(hb, t + 0.24, thump, 0.5); t += 0.7
write('ring', ring); write('heart', hb)

G = lambda n: f'{gen}/{n}.wav'; X = lambda n: f'{GA}/{n}.mp3'
cues = [(G('drums'), 0, 0.9, 'aecho=0.8:0.6:90:0.25,'), (G('pad'), 0, 0.42, 'aecho=0.8:0.6:200:0.3,'), (G('engines'), 0, 0.16, ''), (G('blasts'), 0, 1.0, 'aecho=0.8:0.7:140|330:0.3|0.2,'),
        (G('blasts_muffled'), 0, 0.9, ''), (G('flak'), 0, 0.8, 'aecho=0.8:0.7:200:0.3,'), (G('whistles'), 0, 0.45, ''), (G('guns'), 0, 0.6, 'aecho=0.8:0.6:120:0.3,'), (G('ring'), 0, 0.10, ''), (G('heart'), 0, 0.7, ''),
        (X('amb_cold'), 0, 0.3, ''), (X('amb_cold'), 22.0, 0.3, ''), (X('amb_cold'), 44.0, 0.3, ''), (X('amb_cold'), 66.0, 0.3, ''),
        (X('charge_rush'), T('charge_wide'), 0.7, 'asetrate=28000,'), (X('battle_start'), T('charge_wide') + 0.1, 0.6, ''), (X('swing_1'), at('muster', 0.6), 0.5, 'asetrate=30000,'), (X('swing_2'), at('muster', 1.0), 0.5, ''), (X('swing_1'), at('muster', 1.4), 0.5, ''),
        (X('swing_2'), at('duel', 0.25), 0.7, ''), (X('punch_heavy_1'), at('duel', 0.9), 0.9, ''), (X('swing_1'), at('duel', 1.2), 0.7, ''), (X('unit_die_1'), at('duel', 1.5), 0.6, ''), (X('punch_light_1'), at('duel', 0.5), 0.6, ''),
        (X('swing_2'), at('slam', 0.3), 0.8, 'asetrate=22050,'), (X('punch_heavy_1'), at('slam', 0.85), 1.0, ''), (X('unit_die_1'), at('slam', 1.1), 0.5, 'asetrate=30000,'),
        (X('whale_slam'), at('titan', 1.6), 1.0, ''), (X('punch_heavy_1'), at('titan', 1.6), 0.9, ''), (X('whale_slam'), at('titan', 2.6), 0.9, 'asetrate=36000,'), (X('bark_useless'), at('titan', 1.0), 0.5, 'asetrate=18000,'), (X('unit_die_1'), at('carpet', 0.6), 0.5, ''), (X('unit_die_1'), at('carpet', 1.0), 0.5, 'asetrate=30000,'), (X('unit_die_1'), at('carpet', 1.4), 0.5, ''),
        (X('ui_swoosh'), T('wing_pass') + 0.1, 0.7, 'asetrate=20000,'), (X('ui_swoosh'), T('barrel_roll') + 0.2, 0.6, 'asetrate=24000,'), (X('ui_swoosh'), T('aerial_support') + 0.1, 0.6, 'asetrate=18000,'),
        (X('battle_start'), T('looks_up') + 0.2, 0.5, ''), (X('charge_rush'), T('flyover'), 0.6, 'asetrate=30000,'), (X('ui_swoosh'), T('flyover') + 0.3, 0.6, 'asetrate=20000,'),
        (X('swing_1'), at('flyover', 1.0), 0.6, 'asetrate=30000,'), (X('swing_2'), at('flak', 0.5), 0.6, ''), (X('swing_1'), at('flak', 1.4), 0.6, 'asetrate=30000,'),
        (X('whale_slam'), at('giga', 0.5), 0.9, ''), (X('bark_useless'), at('giga', 0.4), 0.6, 'asetrate=22050,'), (X('unit_die_1'), at('bombrun', 1.0), 0.5, ''), (X('unit_die_1'), at('bombrun', 1.3), 0.5, 'asetrate=30000,'),
        (X('punch_heavy_1'), at('hit', 0.35), 1.0, ''), (X('tower_hit_1'), at('hit', 0.35), 0.8, ''), (X('unit_die_1'), at('hit', 0.5), 0.5, ''),
        (X('ui_swoosh'), T('dive') + 0.1, 0.8, 'asetrate=16000,'), (X('tower_hit_2'), at('dive', 1.35), 0.9, ''), (X('tower_destroy'), at('dive', 1.4), 1.0, ''),
        (X('coin_jingle_1'), T('chute') + 0.3, 0.45, 'aecho=0.8:0.8:300:0.4,'), (X('victory'), T('home') + 0.8, 0.45, 'aecho=0.8:0.8:250:0.4,'), (X('vo_victory'), T('home') + 1.0, 0.4, 'aecho=0.8:0.8:250:0.4,')]
cues = [c for c in cues if os.path.exists(c[0])]
ins, flt = [], []
for i, (p, t0, vol, extra) in enumerate(cues):
    ins += ['-i', p]; ms = max(0, int(t0 * 1000))
    flt.append(f'[{i}:a]aresample={SR},aformat=channel_layouts=mono,{extra}aresample={SR},volume={vol},adelay={ms}|{ms}[c{i}]')
n = len(cues); mix = ''.join(f'[c{i}]' for i in range(n))
flt.append(f'{mix}amix=inputs={n}:normalize=0:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=14,apad,atrim=0:{END},afade=t=in:d=0.5,afade=t=out:st={END - 1.2}:d=1.2[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', str(SR), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(n, 'cues ->', out)
