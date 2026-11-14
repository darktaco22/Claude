"""Narration for "A Natural History" (Kokoro via kokoro-onnx, Apache-2.0).  python3 voices.py KOKORO_DIR OUT_DIR   -> OUT_DIR/<id>.wav + vo.json (durations)"""
import sys, json, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
kdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
k = Kokoro(f'{kdir}/kokoro-v1.0.onnx', f'{kdir}/voices-v1.0.bin')
VOICE = sys.argv[3] if len(sys.argv) > 3 else 'bm_george'
LINES = [  # id, text as spoken, speed, subtitle
 ('n1a', 'The arena, at dawn.', 0.97, 'The arena, at dawn.'),
 ('n1b', 'For millions of years, nothing here has had any utility.', 0.99, 'For millions of years, nothing here has had any utility.'),
 ('n2a', 'The Pepay. Patient. Dignified.', 0.95, 'The Pepe. Patient. Dignified.'),
 ('n2b', 'Down ninety-four percent, and telling no one.', 0.99, 'Down ninety-four percent, and telling no one.'),
 ('n3a', 'Nearby, the paper-handed herd grazes in peace.', 0.99, 'Nearby, the paper-handed herd grazes in peace.'),
 ('n3b', 'A dip, of two percent.', 0.97, 'A dip of two percent.'),
 ('n3c', 'They will return at the top.', 0.99, 'They will return at the top.'),
 ('n4a', 'Two males compete for dominance.', 0.99, 'Two males compete for dominance.'),
 ('n4b', 'Neither has read the white paper. There is no white paper.', 1.0, 'Neither has read the whitepaper. There is no whitepaper.'),
 ('n5a', 'And then, the rarest sight in nature.', 0.95, 'And then, the rarest sight in nature.'),
 ('n5b', 'A god candle.', 0.9, 'A god candle.'),
 ('n5c', 'The whole valley rejoices. Nobody sells.', 0.99, 'The whole valley rejoices. Nobody sells.'),
 ('n6a', 'Ah. The rug pull.', 0.93, 'Ah. The rug pull.'),
 ('n6b', 'I should mention, that I am also in this one.', 0.99, 'I should mention that I am also in this one.'),
 ('n6c', 'Excuse me.', 0.94, 'Excuse me.'),
 ('n7a', 'The Pepay. Now down ninety-nine.', 0.95, 'The Pepe. Now down ninety-nine.'),
 ('n7b', 'Still telling no one.', 0.94, 'Still telling no one.'),
 ('n8', 'Meme Royale. Free to play. Mercifully.', 0.95, 'Free to play. Mercifully.'),
]
J = {}
for i, text, sp, sub in LINES:
    a, sr = k.create(text, voice=VOICE, speed=sp, lang='en-gb')
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - 400): nz[-1] + 2400]
    sf.write(f'{out}/{i}.wav', a, sr); J[i] = {'dur': round(len(a) / sr, 3), 'sub': sub}; print(i, J[i]['dur'], text)
json.dump(J, open(f'{out}/vo.json', 'w'), indent=1); print('total', sum(v['dur'] for v in J.values()))
