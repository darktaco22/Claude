"""Re-voice the skit with Kokoro (hexgrad/kokoro via kokoro-onnx, Apache-2.0), each line fitted to the
original line's length so the lip-sync stays in step.  python3 voices.py STUDIO_DIR KOKORO_DIR OUT_DIR"""
import sys, json, subprocess, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
studio, kdir, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
VO = json.load(open(f'{studio}/vo.json'))
k = Kokoro(f'{kdir}/kokoro-v1.0.onnx', f'{kdir}/voices-v1.0.bin')
VOICE = {'pam': ('af_sarah', 0.95), 'linda': ('af_bella', 1.0), 'earl': ('am_onyx', 0.92), 'chad': ('am_puck', 1.05), 'neet': ('am_adam', 0.95)}
LINES = [('p_welcome', 'pam', 'Welcome back, everyone. Who would like to share?'), ('neet_leaving', 'neet', 'Leaving the basement!'),
         ('n_hi', 'neet', "Hi. I'm Neet."), ('all2_p', 'pam', 'Hi, Neet.'), ('all2_l', 'linda', 'Hi, Neet.'), ('all2_e', 'earl', 'Hi, Neet.'), ('all2_c', 'chad', 'Hi, Neet.'),
         ('n_four', 'neet', "It's been... four minutes... since my last trade."), ('p_record2', 'pam', "That's a new record, Neet."),
         ('l_casino', 'linda', 'I told my husband I lost our savings at the casino.'), ('l_less', 'linda', "Because that's less embarrassing."),
         ('e_kidney', 'earl', 'I sold a kidney to buy the dip.'), ('e_other', 'earl', "I'm thinking about selling the other one."),
         ('neet_letsgo', 'neet', "Let's go!"), ('c_stop', 'chad', "I'm not addicted. I can stop anytime."), ('c_after', 'chad', 'After this one.'),
         ('p_break', 'pam', "Let's... take a five minute break."), ('p_next', 'pam', 'Same time next week.')]
for i, who, text in LINES:
    v, sp = VOICE[who]
    def gen(speed):
        a, sr = k.create(text, voice=v, speed=speed, lang='en-us')
        nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - 400): nz[-1] + 1200] if len(nz) else a   # trim silence
        return a, sr
    a, sr = gen(sp)
    # let the voice itself speak at the pace that fits the original line, then stretch only the remainder
    sp2 = max(0.6, min(1.4, sp * (len(a) / sr) / VO[i]['dur']))
    if abs(sp2 - sp) > 0.02: a, sr = gen(sp2)
    sf.write(f'{out}/{i}.raw.wav', a, sr)
    want = VO[i]['dur']; have = len(a) / sr; tempo = max(0.75, min(1.35, have / want))
    # atempo keeps pitch; fit the original timing (the lip-sync and subtitles follow it)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{out}/{i}.raw.wav', '-af', f'atempo={tempo:.4f}', '-ar', '44100', f'{out}/{i}.wav'], check=True)
    print(f'{i:13s} {who:6s} {v:9s} speed {sp2:.2f} had {have:.2f}s want {want:.2f}s tempo {tempo:.2f}')
