"""WHO SOLD? v2: re-record the changed narrator lines with Chatterbox (CPU), cloning the existing narrator take. Whisper QC + retries. Resumable."""
import json, re, sys, time, difflib
from pathlib import Path
import torch, torchaudio as ta, numpy as np
here = Path(__file__).parent; out = here / 'out'; out.mkdir(exist_ok=True)
lines = json.load(open(here / 'lines_v2.json'))
_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, 'map_location': torch.device('cpu')})
from chatterbox.tts import ChatterboxTTS
from faster_whisper import WhisperModel
m = ChatterboxTTS.from_pretrained(device='cpu'); asr = WhisperModel('tiny.en', device='cpu', compute_type='int8')
norm = lambda s: re.sub(r'[^a-z ]', '', s.lower().replace('-', ' ')).split()
SET = {'default': dict(exaggeration=0.35, cfg_weight=0.6, temperature=0.6), 'n13b': dict(exaggeration=0.5, cfg_weight=0.5, temperature=0.7)}
report = {}; t0 = time.time()
for key, txt in lines.items():
    f = out / f'{key}.wav'
    if f.exists(): continue
    c = SET.get(key, SET['default']); best = None; bs = -1
    for seed in range(100, 108):
        torch.manual_seed(seed); np.random.seed(seed)
        wav = m.generate(txt, audio_prompt_path=str(here / 'ref_narrator.wav'), **c)
        tmp = out / 'tmp.wav'; ta.save(str(tmp), wav, m.sr)
        segs, _ = asr.transcribe(str(tmp), language='en'); hyp = ' '.join(s.text for s in segs)
        d = wav.shape[-1] / m.sr; sc = difflib.SequenceMatcher(None, norm(txt), norm(hyp)).ratio()
        peak = float(wav.abs().max()); ok = sc >= 0.93 and 0.045 * len(txt) <= d <= 0.095 * len(txt) + 1.5 and peak < 0.99
        print(key, seed, round(d, 2), round(sc, 3), 'OK' if ok else 'no', '|', hyp, flush=True)
        if sc > bs: bs, best, bh = sc, wav, hyp
        if ok: best, bs, bh = wav, sc, hyp; break
    ta.save(str(f), best, m.sr); report[key] = dict(dur=round(best.shape[-1] / m.sr, 2), score=round(bs, 3), heard=bh); print('SAVED', key, f'{time.time()-t0:.0f}s', flush=True)
(out / 'tmp.wav').unlink(missing_ok=True)
rp = out / 'report.json'; old = json.load(open(rp)) if rp.exists() else {}; old.update(report); json.dump(old, open(rp, 'w'), indent=1)
print('V2-DONE', len(list(out.glob('n*.wav'))))
