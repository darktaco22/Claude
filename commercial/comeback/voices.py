"""The stadium announcer (Kokoro, hexgrad/kokoro via kokoro-onnx, Apache-2.0): python3 voices.py KOKORO_DIR -> audio/an_*.wav"""
import sys, os, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
kdir = sys.argv[1]; out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio')
k = Kokoro(f'{kdir}/kokoro-v1.0.onnx', f'{kdir}/voices-v1.0.bin')
LINES = [('an_two', 'am_michael', 1.12, "Two crowns to nothing! Somebody stop this!"),
         ('an_exits', 'am_michael', 1.05, "The fans are heading for the exits."),
         ('an_wait', 'am_michael', 1.15, "Wait. What is that?!"),
         ('an_candle', 'am_michael', 1.1, "GOD CANDLE!"),
         ('an_game', 'am_michael', 1.15, "Two, one! We have got a game!"),
         ('an_whale', 'am_michael', 1.15, "Here comes the whale!"),
         ('an_tied', 'am_michael', 1.15, "It's all tied up!"),
         ('an_done', 'am_michael', 1.1, "He did it! The comeback is complete!"),
         ('an_tag', 'am_onyx', 0.9, "Meme Royale. It's not over, until it's over.")]
for i, v, sp, text in LINES:
    a, sr = k.create(text, voice=v, speed=sp, lang='en-us')
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - 300): nz[-1] + 2500]
    sf.write(f'{out}/{i}.raw.wav', a, sr)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{out}/{i}.raw.wav', '-ar', '48000', f'{out}/{i}.wav'], check=True); os.remove(f'{out}/{i}.raw.wav')
    print(i, round(len(a) / sr, 2), text)
