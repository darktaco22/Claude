import torch, torchaudio
from chatterbox.tts import ChatterboxTTS
torch.set_num_threads(2)
m = ChatterboxTTS.from_pretrained(device="cpu")
lines = {
  "dj": ("Put your hands up, Meme Royale! Let's go!", 0.9),
  "cannonball": ("Cannonballllll!", 1.0),
  "watchthis": ("Yo, watch this! Woooo!", 1.0),
  "rain": ("Make it rain, baby! Money for everybody!", 0.9),
  "hippo": ("Who let the hippo in the pool?!", 0.8),
  "conga": ("Conga line! Everybody in!", 0.9),
  "fine": ("This is fine. Everything is fine.", 0.5),
}
for k, (text, ex) in lines.items():
    wav = m.generate(text, exaggeration=ex, cfg_weight=0.4)
    torchaudio.save(f"{k}.wav", wav, m.sr); print("ok", k, wav.shape[-1] / m.sr, flush=True)
