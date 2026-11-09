"""Voice lines for "Wait... they're COINS?" with Kokoro (hexgrad/kokoro via kokoro-onnx, Apache-2.0).
python3 voices.py KOKORO_DIR OUT_DIR   -> OUT_DIR/<id>.wav (44.1 kHz) and lines.json (id, who, text, duration, envelope)"""
import sys, json, os, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
kdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
k = Kokoro(f'{kdir}/kokoro-v1.0.onnx', f'{kdir}/voices-v1.0.bin')
VOICE = {'kyle': ('am_puck', 1.08), 'mom': ('af_sarah', 1.0)}
LINES = [
    ('k_useless', 'kyle', 'Come on, Useless. Do something useful for once.'),
    ('k_dollar', 'kyle', 'Hold on. Why is there a dollar sign on it?'),
    ('k_real', 'kyle', "No way. Useless is a real coin?!"),
    ('k_list', 'kyle', "LMAO's a coin. KET's a coin. Pepe's a coin!"),
    ('k_chill', 'kyle', 'Chill Guy is a COIN?!'),
    ('k_research', 'kyle', "I haven't been gaming. I've been doing... research."),
    ('k_three', 'kyle', 'Three dollars... and twelve cents.'),
    ('k_mom', 'kyle', "Mom! Can I borrow your card? It's for research!"),
    ('m_bed', 'mom', 'Kyle! It is three in the morning!'),
]
meta = {}
for i, who, text in LINES:
    v, sp = VOICE[who]
    a, sr = k.create(text, voice=v, speed=sp, lang='en-us')
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - 300): nz[-1] + 1500]
    sf.write(f'{out}/{i}.raw.wav', a, sr)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{out}/{i}.raw.wav', '-ar', '44100', f'{out}/{i}.wav'], check=True); os.remove(f'{out}/{i}.raw.wav')
    # a mouth-opening envelope at 30 fps (RMS, normalised) for the lip-sync
    hop = sr // 30; env = [float(np.sqrt(np.mean(a[j:j + hop] ** 2))) for j in range(0, len(a), hop)]
    m = max(env) or 1; env = [round(min(1.0, e / m * 1.25), 3) for e in env]
    meta[i] = dict(who=who, text=text, dur=round(len(a) / sr, 3), env=env)
    print(f'{i:11s} {who:5s} {len(a) / sr:5.2f}s  {text}')
json.dump(meta, open(f'{out}/lines.json', 'w'))
