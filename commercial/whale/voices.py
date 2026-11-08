"""Generate every line with Kokoro at its natural pace, trim silence, and write a lip-sync envelope
(mouth openness at 30 fps) to vo.json.  python3 voices.py KOKORO_DIR OUT_DIR"""
import sys, json, os, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import VOICE, LINES
kdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
k = Kokoro(f'{kdir}/kokoro-v1.0.onnx', f'{kdir}/voices-v1.0.bin')
meta = {}
for i, who, text in LINES:
    v, sp = VOICE[who]
    a, sr = k.create(text, voice=v, speed=sp, lang='en-us')
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - 300): nz[-1] + 1500]
    if who == 'whale':   # an old, sick man: a touch lower and slower, keeping the formants natural
        sf.write(f'{out}/{i}.raw.wav', a, sr)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{out}/{i}.raw.wav', '-af', f'asetrate={sr}*0.93,aresample={sr},atempo=1.0', f'{out}/{i}.tmp.wav'], check=True)
        a, sr = sf.read(f'{out}/{i}.tmp.wav'); os.remove(f'{out}/{i}.tmp.wav'); os.remove(f'{out}/{i}.raw.wav')
    sf.write(f'{out}/{i}.wav', a, sr)
    hop = sr // 30; rms = np.array([np.sqrt(np.mean(a[j:j + hop] ** 2)) for j in range(0, len(a), hop)])
    env = np.clip(rms / (np.percentile(rms, 95) + 1e-9), 0, 1)
    meta[i] = {'who': who, 'text': text, 'dur': round(len(a) / sr, 3), 'env': [round(float(x), 3) for x in env]}
    print(f'{i:9s} {who:7s} {meta[i]["dur"]:.2f}s  {text}')
json.dump(meta, open(f'{out}/vo.json', 'w'))
