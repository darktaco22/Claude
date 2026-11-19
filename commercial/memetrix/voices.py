"""Dialogue for "THE MEMETRIX" (Kokoro via kokoro-onnx, Apache-2.0; stock synthetic voices, no real person).

    python3 voices.py KOKORO_DIR OUT_DIR      -> OUT_DIR/<id>.wav + vo.json ({id: {dur, sub, who}})

A Matrix parody with Meme Royale's least-used characters. Every line is original; only the genre tropes are borrowed.
Cast: ANON (zcat, paper bag, the chosen one), SLERF (sloth mentor, talks... very... slowly), MICHI (the fighter),
MENSA (operator), FARTER (the traitor), ALON (the kid with the bent card), BOME (the book that knows how it ends),
JEANPHIL (lead agent), the TRIPLETS (agent clones, in unison), MOM (off screen).
Slow lines: ' / ' splits a line into pieces said separately with a pause between (Slerf's delivery).
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

VOICES = {
    'anon': ('am_adam', 'en-us', 1.05),
    'slerf': ('bm_george', 'en-gb', 0.78),
    'michi': ('af_nicole', 'en-us', 1.0),
    'mensa': ('am_fenrir', 'en-us', 1.1),
    'farter': ('am_santa', 'en-us', 1.0),
    'alon': ('af_sky', 'en-us', 1.12),
    'bome': ('bf_isabella', 'en-gb', 0.95),
    'jean': ('am_michael', 'en-us', 0.82),
    'mom': ('af_heart', 'en-us', 1.08),
    'tri': (('am_echo', 'am_eric', 'am_liam'), 'en-us', 0.9),    # three voices layered = one agent in three bodies
}
PAUSE = 0.3                                                       # seconds between Slerf's pieces

LINES = [  # id, speaker, text as spoken, speed factor, caption
    # --- 1. the trading floor at night: the chart has Anon
    ('a01', 'anon', "I haven't slept since the halving.", 1.0, None),
    ('m01', 'michi', 'Anon. He has been looking for you.', 1.0, None),
    ('a02', 'anon', 'Who?', 1.0, None),
    ('m02', 'michi', 'The one who has been holding since the first candle.', 1.0, None),
    # --- 2. the choice
    ('s01', 'slerf', 'What if / I told you / the chart / is not real.', 1.0, 'What if... I told you... the chart... is not real.'),
    ('a03', 'anon', 'Sir, could you talk a little faster? Gas fees are going up.', 1.08, None),
    ('s02', 'slerf', 'No.', 1.0, None),
    ('s03', 'slerf', 'Red candle / you see how deep the dip goes. / Green candle / you go back to believing / number go up.', 1.12,
     'Red candle... you see how deep the dip goes. Green candle... you go back to believing... number go up.'),
    ('a04', 'anon', 'Can I take both?', 1.0, None),
    ('s04', 'slerf', "That is / called / a wick.", 1.0, "That's... called... a wick."),
    # --- 3. the basement of the real
    ('s05', 'slerf', 'Welcome / to the basement / of the real.', 1.0, 'Welcome... to the basement... of the real.'),
    ('mo1', 'mom', 'Honey! Are your little friends staying for dinner?', 1.0, None),
    ('s06', 'slerf', 'No thank you, Missus Anon! We already ate, it was lovely, have a good night!', 1.75, 'No thank you, Mrs. Anon! We already ate, it was lovely, have a good night!'),
    ('n01', 'mensa', "I don't even see the code anymore. All I see is frog, cat, frog, dog, frog, frog, hippo.", 1.0, None),
    ('f01', 'farter', 'Between you and me? Ignorance is bullish.', 1.0, None),
    # --- 4. the training program
    ('n02', 'mensa', 'Loading the trading program.', 1.0, None),
    ('a05', 'anon', 'I know candlesticks.', 0.95, None),
    ('s07', 'slerf', 'Show / me.', 1.0, 'Show... me.'),
    ('s08', 'slerf', 'You think / PH:ðat ɪz lˈɛvəɹɪdʒ / you are trading?', 1.0, "You think... that's leverage... you're trading?"),
    # (en-gb says lˈiːvəɹɪdʒ, 'LEE-ver-idge', which reads as 'leave-ridge': spelled out in phonemes with the LEV vowel)
    # --- 5. the waiting room and the book
    ('k01', 'alon', "Don't try to read the chart. That's impossible. Only realise the truth.", 1.0, None),
    ('a06', 'anon', 'What truth?', 1.0, None),
    ('k02', 'alon', 'There is no chart.', 0.95, None),
    ('b01', 'bome', "So. You're not the One.", 1.0, None),
    ('b02', 'bome', "You're the one percent. Of holders. Cookie?", 1.0, None),
    # --- 6. the agents
    ('j01', 'jean', 'Mister. Anon.', 0.9, 'Mister... Anon.'),
    ('t01', 'tri', 'Sell.', 1.0, None),
    ('m03', 'michi', 'Anon! How did you do that?', 1.05, None),
    ('a08', 'anon', 'Diamond hands.', 1.0, None),
    ('j02', 'jean', "He's. Bullish.", 0.9, "He's... bullish."),
    ('a09', 'anon', "No. I'm just not selling.", 0.95, None),
]


def trim(audio):
    loud = np.where(np.abs(audio) > 0.01)[0]
    return audio[max(0, loud[0] - 400): loud[-1] + 2400]


def say(kokoro, text, voice, speed, lang):
    voices = voice if isinstance(voice, tuple) else (voice,)
    ph = text.startswith('PH:')                                   # 'PH:' = the piece is given as phonemes (fixed pronunciation)
    takes = [trim(kokoro.create(text[3:] if ph else text, voice=v, speed=speed, lang=lang, is_phonemes=ph)[0]) for v in voices]
    n = max(len(a) for a in takes)
    mix = sum(np.pad(a, (0, n - len(a))) for a in takes) / (len(takes) ** 0.6)
    return mix.astype(np.float32)


def main(kokoro_dir: str, out_dir: str, only=None) -> None:
    os.makedirs(out_dir, exist_ok=True)
    kokoro = Kokoro(f'{kokoro_dir}/kokoro-v1.0.onnx', f'{kokoro_dir}/voices-v1.0.bin')
    rate = 24000
    result = json.load(open(f'{out_dir}/vo.json')) if only and os.path.exists(f'{out_dir}/vo.json') else {}
    for line_id, who, text, factor, caption in LINES:
        if only and line_id not in only:
            continue
        voice, lang, speed = VOICES[who]
        pieces = [p.strip() for p in text.split(' / ')]
        gap = np.zeros(int(PAUSE * rate), np.float32)
        parts = []
        for i, piece in enumerate(pieces):
            if i:
                parts.append(gap)
            parts.append(say(kokoro, piece, voice, speed * factor, lang))
        audio = np.concatenate(parts)
        sf.write(f'{out_dir}/{line_id}.wav', audio, rate)
        result[line_id] = {'dur': round(len(audio) / rate, 3), 'sub': caption or text.replace(' / ', ' '), 'who': who}
        print(line_id, who, result[line_id]['dur'], result[line_id]['sub'])
    with open(f'{out_dir}/vo.json', 'w') as handle:
        json.dump(result, handle, indent=1)
    print('TOTAL', round(sum(item['dur'] for item in result.values()), 1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(',') if len(sys.argv) > 3 else None)
