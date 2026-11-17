"""THE REAPING voices: Chatterbox (CPU) cloning the existing Meme Royale cast takes in refs/. Whisper QC, several takes, keeps the best. Resumable."""
import json, re, time, difflib
from pathlib import Path
import torch, torchaudio as ta, numpy as np
here = Path(__file__).parent; out = here / 'out'; out.mkdir(exist_ok=True)
J = json.load(open(here / 'lines.json'))
_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, 'map_location': torch.device('cpu')})
from chatterbox.tts import ChatterboxTTS
from faster_whisper import WhisperModel
m = ChatterboxTTS.from_pretrained(device='cpu'); asr = WhisperModel('tiny.en', device='cpu', compute_type='int8')
norm = lambda s: re.sub(r'[^a-z ]', '', s.lower().replace('-', ' ')).split()
rp = out / 'report.json'; report = json.load(open(rp)) if rp.exists() else {}; t0 = time.time()
for key, role, txt in J['lines']:
    f = out / f'{key}.wav'
    if f.exists(): continue
    c = J['settings'][role]; qc = not key.startswith('aww'); best = None; bs = -1; bh = ''
    for seed in range(200, 206 if qc else 201):
        torch.manual_seed(seed); np.random.seed(seed)
        wav = m.generate(txt, audio_prompt_path=str(here / 'refs' / f'{role}.wav'), **c)
        d = wav.shape[-1] / m.sr
        if not qc: best, bs, bh = wav, 1.0, '(not checked)'; break
        tmp = out / 'tmp.wav'; ta.save(str(tmp), wav, m.sr)
        segs, _ = asr.transcribe(str(tmp), language='en'); hyp = ' '.join(s.text for s in segs)
        sc = difflib.SequenceMatcher(None, norm(txt), norm(hyp)).ratio()
        ok = sc >= 0.9 and d <= 0.11 * len(txt) + 1.6 and float(wav.abs().max()) < 0.99
        print(key, seed, round(d, 2), round(sc, 3), 'OK' if ok else 'no', '|', hyp, flush=True)
        if sc > bs: bs, best, bh = sc, wav, hyp
        if ok: break
    ta.save(str(f), best, m.sr); report[key] = dict(role=role, text=txt, dur=round(best.shape[-1] / m.sr, 2), score=round(bs, 3), heard=bh)
    json.dump(report, open(rp, 'w'), indent=1); print('SAVED', key, f'{time.time()-t0:.0f}s', flush=True)
(out / 'tmp.wav').unlink(missing_ok=True)
print('REAPING-VOICE-DONE', len(list(out.glob('*.wav'))))
