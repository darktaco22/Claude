"""Voice lines for "I WILL FIND YOU" with Kokoro (hexgrad/kokoro via kokoro-onnx, Apache-2.0).
python3 voices.py KOKORO_DIR OUT_DIR   -> OUT_DIR/<id>.wav (44.1 kHz) and lines.json (id, who, text, duration, envelope)"""
import sys, json, os, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
kdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
k = Kokoro(f'{kdir}/kokoro-v1.0.onnx', f'{kdir}/voices-v1.0.bin')
VOICE = {'neet': ('am_onyx', 0.86), 'grandma': ('bf_isabella', 0.9)}
LINES = [
    ('n_who', 'neet', "I don't know who you are."),
    ('n_sol', 'neet', "I don't know how much SOL you have."),
    ('n_cards', 'neet', "But what I do have... is a very particular set of cards."),
    ('n_season', 'neet', "Cards I have acquired over a very long... ranked season."),
    ('n_find', 'neet', "I will look for you. I will find you."),
    ('n_copium', 'neet', "And I will out-COPIUM you."),
    ('g_hello', 'grandma', "Oh! Hello, dear."),
    ('g_rug', 'grandma', "Rugged, sweetie."),
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
