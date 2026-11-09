"""LAST WILL & TESTAMENT soundtrack: Kokoro voice lines at the director's times, rain and thunder against the
glass, the heart monitor (beeps that race, then the flatline tone, then one blip), phone buzz and pings,
sips, a decanter glug, a vape pull, the cigar drag. No laugh track or canned reactions of any kind.
python3 audio.py TIMELINE.json VO_DIR SFX_DIR OUT.m4a"""
import sys, os, json, subprocess, math
import numpy as np, soundfile as sf
tl_path, vo, sfx, out = sys.argv[1:5]
TL = json.load(open(tl_path)); END = TL['end']; FLAT = TL['flatline']; PING = TL['ping']; REVIVE = TL['revive']
SR = 44100; gen = os.path.join(os.path.dirname(out), 'gen_sfx'); os.makedirs(gen, exist_ok=True)
rng = np.random.default_rng(7)


def write(name, a):
    a = np.asarray(a, np.float32); a /= max(1e-6, np.abs(a).max()); sf.write(f'{gen}/{name}.wav', a * 0.9, SR); return f'{gen}/{name}.wav'


def env(n, a=0.005, r=0.05):
    t = np.arange(n) / SR; e = np.minimum(1, t / a) * np.minimum(1, (n / SR - t) / r); return np.clip(e, 0, 1)


def lowpass(x, k):
    from numpy.lib.stride_tricks import sliding_window_view
    return np.convolve(x, np.ones(k) / k, mode='same')


# the monitor: a clean 980 Hz beep with a soft attack, and the continuous flatline tone
n = int(0.11 * SR); t = np.arange(n) / SR
write('beep', np.sin(2 * math.pi * 980 * t) * env(n, 0.004, 0.06) + 0.25 * np.sin(2 * math.pi * 1960 * t) * env(n, 0.004, 0.03))
n = int(4.2 * SR); t = np.arange(n) / SR
write('flat', np.sin(2 * math.pi * 980 * t) * env(n, 0.01, 0.9) + 0.2 * np.sin(2 * math.pi * 1960 * t) * env(n, 0.01, 0.9))
# phone buzz on the duvet: 175 Hz motor, three pulses, muffled by the bedding
n = int(1.1 * SR); t = np.arange(n) / SR
gate = ((t % 0.36) < 0.24).astype(float); buzz = (np.sign(np.sin(2 * math.pi * 175 * t)) * 0.6 + np.sin(2 * math.pi * 350 * t) * 0.3) * gate
write('buzz', lowpass(buzz, 6) * env(n, 0.01, 0.05))
# the fin on the glass: a soft thud and a tick
n = int(0.25 * SR); t = np.arange(n) / SR
write('tap', np.exp(-t * 40) * (np.sin(2 * math.pi * 90 * t) + 0.4 * rng.normal(0, 1, n) * np.exp(-t * 200)))
# a decanter glug: bubbles (short decaying tones rising in pitch) over a liquid wash
n = int(1.0 * SR); t = np.arange(n) / SR; g = lowpass(rng.normal(0, 0.25, n), 30)
for k, t0 in enumerate([0.05, 0.22, 0.38, 0.55, 0.7]):
    m = t >= t0; u = t[m] - t0; f = 140 + 60 * k + 300 * u; g[m] += np.sin(2 * math.pi * f * u) * np.exp(-u * 18)
write('glug', g * env(n, 0.02, 0.2))
# vape pull: a soft airy hiss with a crackle; the exhale is longer and breathier
n = int(0.7 * SR); t = np.arange(n) / SR
write('vape', lowpass(rng.normal(0, 1, n), 4) * np.sin(math.pi * t / t[-1]) ** 2 * 0.6 + (rng.random(n) > 0.9985) * rng.normal(0, 0.6, n))
n = int(1.6 * SR); t = np.arange(n) / SR
write('exhale', lowpass(rng.normal(0, 1, n), 9) * np.sin(math.pi * t / t[-1]) ** 1.5)
# the bed taking his weight when he jolts and when he sits back up
n = int(0.6 * SR); t = np.arange(n) / SR
write('creak', np.sin(2 * math.pi * (180 + 40 * np.sin(t * 9)) * t) * np.exp(-t * 6) * 0.5 + lowpass(rng.normal(0, 0.4, n), 20) * np.exp(-t * 9))


def heartbeat_times():
    out = []; t = 0.3
    while t < FLAT - 0.05:
        bpm = 72 if t < 37.6 else (72 + 90 * min(1, max(0, (t - 37.6) / 2.0)))
        out.append(t); t += 60.0 / bpm
    out.append(55.85); t = REVIVE + 0.4
    while t < END: out.append(t); t += 60.0 / 64
    return out


G = lambda n: f'{gen}/{n}.wav'; X = lambda n: f'{sfx}/{n}.wav'
cues = []      # (path, t, volume, filters)
for L in TL['lines']: cues.append((f"{vo}/{L['id']}.wav", L['t'], 1.0, 'highpass=f=80,aecho=0.8:0.25:28:0.10,'))
for b in heartbeat_times(): cues.append((G('beep'), b + 0.2, 0.025 if b < 37.6 else 0.06, ''))
cues += [(G('flat'), FLAT, 0.07, 'atrim=0:3.6,afade=t=out:st=2.6:d=1.0,'), (G('buzz'), 37.35, 0.5, ''), (G('tap'), 39.95, 0.8, ''),
         (G('creak'), FLAT, 0.35, ''), (G('creak'), REVIVE, 0.35, ''), (G('glug'), 29.15, 0.55, ''), (G('vape'), 20.45, 0.35, ''),
         (G('exhale'), 21.1, 0.25, ''), (X('sip'), 10.6, 0.5, ''), (X('sip'), 30.4, 0.45, ''),
         (X('drag'), 53.95, 0.7, ''), (G('exhale'), 54.85, 0.4, '')]
for i, k in enumerate(['wife', 'son', 'priest', 'lawyer']): cues.append((X('ding'), PING + i * 0.07, 0.75, ''))
# thunder with the flashes; rain on the glass throughout (looped), louder in the window shot
for t0, v in [(0.7, 0.9), (FLAT + 0.05, 1.0), (REVIVE + 0.05, 0.6)]: cues.append((X('thunder'), t0 + 0.25, v * (0.5 if t0 < 3 else 0.25), 'lowpass=f=1800,' if t0 > 3 else ''))
ins, flt = [], []
for i, (p, t0, vol, extra) in enumerate(cues):
    ins += ['-i', p]; ms = int(t0 * 1000)
    flt.append(f'[{i}:a]aresample={SR},aformat=channel_layouts=mono,{extra}volume={vol},adelay={ms}|{ms}[c{i}]')
n = len(cues)
ins += ['-stream_loop', '-1', '-i', X('rain')]
flt.append(f"[{n}:a]aresample={SR},aformat=channel_layouts=mono,atrim=0:{END},lowpass=f=2500,volume='if(lt(t,3.3),0.22,if(lt(t,3.9),0.22-(t-3.3)/0.6*0.19,0.03))':eval=frame[rain]")
mix = ''.join(f'[c{i}]' for i in range(n)) + '[rain]'
flt.append(f'{mix}amix=inputs={n + 1}:normalize=0:dropout_transition=0,loudnorm=I=-15:TP=-1.5:LRA=11,apad,atrim=0:{END},afade=t=out:st={END - 0.6}:d=0.6[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', str(SR), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(n + 1, 'cues ->', out)
