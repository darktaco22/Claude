"""LAST LINE sound: war drums, a low brass pad and the blasts are synthesized here; hits, slams, the tower and the fanfare are
the game's own sounds. In the first-person shots the world goes deaf: everything muffled under a ringing ear and a heartbeat.
python3 audio.py TIMELINE.json GAME_AUDIO_DIR OUT.m4a"""
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
tl = json.load(open(sys.argv[1])); GA = sys.argv[2]; out = sys.argv[3]
SR = 44100; END = tl['end'] + 3.0; N = int(END * SR); rng = np.random.default_rng(5)
gen = os.path.join(os.path.dirname(os.path.abspath(out)), 'gen_war'); os.makedirs(gen, exist_ok=True)
SH = {s['name']: s for s in tl['shots']}; POV = [(s['t0'], s['t1']) for s in tl['shots'] if s['pov'] >= 0.85]; POV = [(min(a for a, _ in POV), max(b for _, b in POV) + 2.6)]      # deaf until the brother's hand falls
def in_pov(t): return any(a <= t < b for a, b in POV)
def at(shot, u): s = SH[shot]; return s['t0'] + u / s['slow']
def mf(m): return 440.0 * 2 ** ((m - 69) / 12)
def put(buf, t0, y, g=1.0):
    s = int(t0 * SR); e = min(len(buf), s + len(y))
    if 0 <= s < len(buf): buf[s:e] += y[:e - s] * g
def lp(y, hz):
    k = max(1, int(SR / hz)); return np.convolve(np.convolve(y, np.ones(k) / k, mode='same'), np.ones(k) / k, mode='same')
def write(name, a):
    a = np.asarray(a, np.float32); a /= max(1e-6, np.abs(a).max()); p = f'{gen}/{name}.wav'; sf.write(p, a * 0.9, SR); return p


def drum(vel=1.0, f0=62.0):
    t = np.arange(int(0.9 * SR)) / SR; f = f0 * (1 + 1.6 * np.exp(-t * 26))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5) + 0.25 * lp(rng.normal(0, 1, len(t)), 900) * np.exp(-t * 30)
    return y * vel


def blast(size):
    t = np.arange(int(2.6 * SR)) / SR; f = 70 * np.exp(-t * 2.2) + 28
    y = lp(rng.normal(0, 1, len(t)), 500) * np.exp(-t * 2.4) * 1.4 + np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.9) + 0.5 * lp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 16)
    return np.tanh(y * 1.6) * (0.45 + 0.25 * size)


# --- drums: a march that builds to the charge, drops out when it goes deaf, comes back for the run
drums = np.zeros(N); beat = 0.5
def bar(t0, pat, vel): [put(drums, t0 + b * beat, drum(v * vel, 62 if v > 0.7 else 78)) for b, v in pat]
t = 3.6
while t < SH['blast']['t1'] - 0.2:
    k = min(1.0, (t - 3.6) / 8.0); bar(t, [(0, 1.0), (1, 0.5), (1.5, 0.5), (2, 0.9), (3, 0.5), (3.5, 0.6)], 0.45 + 0.55 * k); t += 4 * beat
t = SH['rage']['t0'] + 2.0
while t < SH['leap']['t0']:
    bar(t, [(0, 1.0), (0.5, 0.5), (1, 0.8), (1.5, 0.5), (2, 1.0), (2.5, 0.5), (3, 0.8), (3.25, 0.6), (3.5, 0.7), (3.75, 0.6)], 0.7 + 0.3 * min(1, (t - SH['rage']['t0']) / 7)); t += 4 * beat
for tt in (at('strike', 0.07), at('tower', 0.42), at('tower', 0.75), SH['after']['t0'] + 0.1): put(drums, tt, drum(1.3, 50))
write('drums', drums)

# --- a low brass pad (detuned saws through a soft filter)
pad = np.zeros(N)
def chord(t0, t1, notes, g, hz=700):
    n0, n1 = int(t0 * SR), min(N, int(t1 * SR)); tt = np.arange(n1 - n0) / SR; env = np.minimum(1, tt / 0.9) * np.minimum(1, (tt[-1] - tt) / 0.9); s = np.zeros(n1 - n0)
    for m in notes:
        for d in (-0.14, 0.0, 0.12): s += 2 * ((mf(m) * (1 + d / 100) * tt) % 1) - 1
    pad[n0:n1] += lp(s, hz) * env * g
D2, F2, A2, Bb1, C2, D3, F3, A3, Fs3 = 38, 41, 45, 34, 36, 50, 53, 57, 54
T = lambda n: SH[n]['t0']
chord(0.3, T('order') + 0.3, [D2, A2], 0.35, 300); chord(T('order'), T('enemy') + 0.2, [D2, A2, D3, F3], 0.6); chord(T('enemy'), T('clash') + 0.2, [Bb1, F2, D3], 0.7)
chord(T('clash'), T('pov_left') + 0.2, [D2, A2, D3, F3, A3], 0.8); chord(T('pov_left'), T('rage') + 0.6, [D2], 0.3, 160); chord(T('rage') + 0.3, T('run') + 0.2, [Bb1, F2, D3, F3], 0.7)
chord(T('run'), T('leap') + 0.2, [C2, 43, 52, 55], 0.75); chord(T('leap'), T('tower') + 0.2, [D2, A2, D3, F3, A3, 62], 0.9, 1100)
chord(T('tower'), T('after') + 0.2, [Bb1, F2, D3, F3, 58], 0.9, 1100); chord(T('after'), END, [D2, A2, D3, Fs3, A3, 62], 0.8, 1200)
write('pad', pad)

# --- the blasts (heard through the snow in first person), the ringing ear, the heartbeat
ex = np.zeros(N); exm = np.zeros(N)
for e in tl['fx']:
    if e['kind'] == 'boom': put(exm if in_pov(e['t']) else ex, e['t'], blast(e['size']))
write('blasts', ex); write('blasts_muffled', lp(exm, 220))
ring = np.zeros(N); hb = np.zeros(N); tt = np.arange(N) / SR; th = np.arange(int(0.35 * SR)) / SR; thump = np.sin(2 * np.pi * 50 * th) * np.exp(-th * 13)
env = np.zeros(N)
for a, b in POV + [(SH['blast']['t0'] + 0.5, SH['blast']['t1'])]: env = np.maximum(env, np.clip(np.minimum((tt - a) / 0.25, (b + 0.8 - tt) / 1.0), 0, 1))
ring = (np.sin(2 * np.pi * 3150 * tt) + 0.5 * np.sin(2 * np.pi * 5230 * tt)) * env
t = POV[0][0] if POV else END
while POV and t < POV[-1][1] + 0.6: put(hb, t, thump, 1.0); put(hb, t + 0.24, thump, 0.6); t += 0.95
for a, b in [(0.4, SH['order']['t0']), (SH['brother']['t0'], SH['rage']['t0'] + 1.6)]:
    t = a
    while t < b: put(hb, t, thump, 0.8); put(hb, t + 0.24, thump, 0.5); t += 0.85
write('ring', ring); write('heart', hb)

G = lambda n: f'{gen}/{n}.wav'; X = lambda n: f'{GA}/{n}.mp3'
cues = [(G('drums'), 0, 0.9, 'aecho=0.8:0.6:90:0.25,'), (G('pad'), 0, 0.42, 'aecho=0.8:0.6:200:0.3,'), (G('blasts'), 0, 1.0, 'aecho=0.8:0.7:140|330:0.3|0.2,'),
        (G('blasts_muffled'), 0, 0.9, ''), (G('ring'), 0, 0.10, ''), (G('heart'), 0, 0.7, ''),
        (X('amb_cold'), 0, 0.3, ''), (X('amb_cold'), 22.0, 0.3, ''),
        (X('battle_start'), SH['order']['t0'] + 0.5, 0.6, ''), (X('charge_rush'), SH['charge']['t0'], 0.8, ''), (X('charge_rush'), SH['stampede']['t0'], 0.7, 'asetrate=30000,'), (X('ui_swoosh'), SH['shell']['t0'], 0.8, 'asetrate=14000,'), (X('charge_rush'), SH['enemy']['t0'] + 0.2, 0.6, 'asetrate=38000,'),
        (X('ui_swoosh'), SH['clash']['t0'] - 0.1, 0.5, 'asetrate=22050,'), (X('swing_1'), at('clash', 0.3), 0.6, 'asetrate=30000,'), (X('punch_heavy_1'), at('clash', 0.46), 1.0, ''),
        (X('punch_light_1'), at('clash', 0.56), 0.7, ''), (X('unit_die_1'), at('clash', 0.62), 0.5, ''),
        (X('ui_swoosh'), SH['blast']['t0'], 0.5, 'asetrate=22050,'), (X('unit_die_1'), at('blast', 0.3), 0.5, ''),
        (X('punch_heavy_1'), at('pov_left', 0.32), 0.7, 'lowpass=f=420,'), (X('unit_die_1'), at('pov_left', 0.5), 0.6, 'lowpass=f=420,'),
        (X('whale_slam'), at('pov_right', 0.5), 0.9, 'lowpass=f=380,'), 
        (X('coin_jingle_1'), at('brother', 1.0), 0.45, 'aecho=0.8:0.8:300:0.4,'), (X('ui_swoosh'), at('rage', 0.9), 0.7, 'areverse,'), (X('punch_heavy_1'), at('rage', 1.25), 0.8, 'asetrate=30000,'), (X('coin_jingle_2'), at('rage', 1.3), 0.6, ''),
        (X('whale_slam'), at('slam', 0.55), 1.0, ''), (X('unit_die_1'), at('slam', 0.7), 0.5, ''),
        (X('charge_rush'), SH['run']['t0'], 0.7, ''), (X('coin_jingle_2'), SH['run']['t0'] + 0.3, 0.4, ''), (X('swing_2'), at('bridge', 0.2), 0.6, ''), (X('swing_1'), at('bridge', 0.6), 0.6, ''),
        (X('ui_swoosh'), SH['leap']['t0'] - 0.05, 0.7, 'asetrate=18000,'), (X('bark_useless'), SH['leap']['t0'] + 0.5, 0.7, 'asetrate=36000,aecho=0.8:0.8:300:0.4,'),
        (X('punch_heavy_1'), at('strike', 0.07), 1.0, ''), (X('tower_hit_1'), at('strike', 0.07), 0.8, ''), (X('unit_die_1'), at('strike', 0.5), 0.5, 'asetrate=30000,'),
        (X('tower_hit_2'), at('tower', 0.1), 0.9, ''), (X('tower_destroy'), at('tower', 0.42), 1.0, ''), (X('victory'), SH['after']['t0'] + 0.8, 0.45, 'aecho=0.8:0.8:250:0.4,'),
        (X('vo_victory'), SH['after']['t0'] + 1.0, 0.4, 'aecho=0.8:0.8:250:0.4,')]
cues = [c for c in cues if os.path.exists(c[0])]
ins, flt = [], []
for i, (p, t0, vol, extra) in enumerate(cues):
    ins += ['-i', p]; ms = max(0, int(t0 * 1000))
    flt.append(f'[{i}:a]aresample={SR},aformat=channel_layouts=mono,{extra}aresample={SR},volume={vol},adelay={ms}|{ms}[c{i}]')
n = len(cues); mix = ''.join(f'[c{i}]' for i in range(n))
flt.append(f'{mix}amix=inputs={n}:normalize=0:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=14,apad,atrim=0:{END},afade=t=in:d=0.5,afade=t=out:st={END - 1.2}:d=1.2[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', str(SR), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(n, 'cues ->', out)
