"""Generate the Trophy Road narration with Chatterbox (MIT, Resemble AI) on CPU. Resumable: skips existing wavs."""
import json, time, sys
from pathlib import Path
import torch, torchaudio as ta
here = Path(__file__).parent; out = here / 'out'; out.mkdir(exist_ok=True)
lines = json.load(open(here / 'lines.json'))
_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, 'map_location': torch.device('cpu')})   # checkpoints were saved on CUDA
from chatterbox.tts import ChatterboxTTS
m = ChatterboxTTS.from_pretrained(device='cpu')
CFG = {'c': dict(ref='caster_ref.wav', exaggeration=0.9, cfg_weight=0.3, temperature=0.85),   # excited hype announcer
       'a': dict(ref='analyst_ref.wav', exaggeration=0.45, cfg_weight=0.5, temperature=0.7)}  # dry deadpan analyst
t0 = time.time(); report = {}
for key, v in lines.items():
    for role, txt in (('c', v['caster']), ('a', v['analyst'])):
        if not txt: continue
        f = out / f'v3_{key}_{role}.wav'
        if f.exists(): continue
        c = CFG[role]; best = None
        for attempt in range(3):                        # guard against rambling / truncated generations
            wav = m.generate(txt, audio_prompt_path=str(here / 'refs' / c['ref']), exaggeration=c['exaggeration'],
                             cfg_weight=c['cfg_weight'], temperature=c['temperature'])
            d = wav.shape[-1] / m.sr
            if 0.04 * len(txt) <= d <= 0.10 * len(txt) + 2.0: best = wav; break
            best = best if best is not None else wav
        ta.save(str(f), best, m.sr); report[f.name] = round(best.shape[-1] / m.sr, 2)
        print(f.name, report[f.name], f'{time.time()-t0:.0f}s', flush=True)
json.dump(report, open(out / 'report.json', 'w'), indent=1)
print('CHATTERBOX-DONE', len(report))
