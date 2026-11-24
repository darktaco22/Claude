"""Dialogue for "THE MEMETRIX II: LIQUIDATION" (Kokoro via kokoro-onnx, stock synthetic voices, no real person).

    python3 voices.py KOKORO_DIR OUT_DIR [id,id,...]   -> OUT_DIR/<id>.wav + vo.json ({id: {dur, sub, who}})

Same conventions as episode 1 (../memetrix/voices.py): ' / ' splits a line into pieces said with a pause between,
'PH:' marks a piece given as phonemes. New: 'jean12' layers one take twelve times with small delays and pitch-free
level changes (the copied agent speaking from twelve bodies, slightly out of sync).
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'memetrix'))
from voices import PAUSE, say, trim  # noqa: E402  (episode 1's recorder)

VOICES = {
    'anon': ('am_adam', 'en-us', 1.05),
    'slerf': ('bm_george', 'en-gb', 0.78),
    'michi': ('af_nicole', 'en-us', 1.0),
    'mensa': ('am_fenrir', 'en-us', 1.1),
    'jean': ('am_michael', 'en-us', 0.82),
    'jean12': ('am_michael', 'en-us', 0.82),
    'mom': ('af_heart', 'en-us', 1.08),
    'whale': ('bm_lewis', 'en-gb', 0.8),          # deep, slow, calm
    'swordcat': ('af_kore', 'en-us', 0.9),        # two words, low and level
    'fine': ('am_puck', 'en-us', 0.95),           # This-Is-Fine: warm, unbothered
    'toshi': ('af_sky', 'en-us', 1.12),           # small, quiet
}

LINES = [  # id, speaker, text as spoken, speed factor, caption
    # --- 1. the rug
    ('n10', 'mensa', "It's not a dip. It's a rug. Somebody's pulling the floor out from under the whole Memetrix.", 1.0, None),
    ('m10', 'michi', 'Jeanphil?', 1.0, None),
    ('n11', 'mensa', "Jeanphil. He's not chasing us anymore. He's copying himself. Every wallet he touches becomes him.", 1.0, None),
    ('a10', 'anon', "Then we find who's paying him.", 1.0, None),
    ('s10', 'slerf', 'The Whale / has / the exit.', 1.0, 'The Whale... has... the exit.'),
    ('a11', 'anon', 'Where is the exit, Slerf?', 1.0, '...Where is the exit, Slerf?'),
    ('s11', 'slerf', 'Nobody knows the only one who knows is the Keyholder and the Keyholder is at the café!', 2.3,
     'Nobody-knows-the-only-one-who-knows-is-the-Keyholder-and-the-Keyholder-is-at-the-café!'),
    ('mo10', 'mom', "Honey, are you going out? It's very red outside!", 1.0, None),
    # --- 2. the burning café
    ('f10', 'fine', 'Sit. Have a coffee. Everything is fine.', 1.0, None),
    ('a12', 'anon', 'Your café is on fire.', 1.0, None),
    ('f11', 'fine', "It's been on fire since twenty twenty one. You get used to it.", 1.0, "It's been on fire since 2021. You get used to it."),
    ('f12', 'fine', 'You want the Keyholder. Everyone wants the Keyholder. She opens any door in the Memetrix.', 1.0, None),
    ('t10', 'toshi', 'Twelve words. I never say them out loud.', 1.0, None),
    ('f13', 'fine', 'Swordcat decides who walks out with her.', 1.0, None),
    ('w10', 'swordcat', 'He holds.', 1.0, None),
    ('t11', 'toshi', 'Then I go with him.', 1.0, None),
    ('f14', 'fine', 'This is fine.', 0.95, None),
    # --- 3. the brawl and the flight
    ('j10', 'jean', 'Mister. Anon. You missed me.', 0.9, 'Mister... Anon. You missed me.'),
    ('j11', 'jean12', 'Me. Too.', 0.85, 'Me. Too.'),
    ('a13', 'anon', 'Get the Keyholder to the edge.', 1.05, None),
    ('m11', 'michi', "Anon! There's no way down!", 1.05, None),
    ('a14', 'anon', 'Who said down?', 1.0, None),
    # --- 4. the Whale
    ('wh10', 'whale', 'Hello, Anon. You are the sixth.', 1.0, None),
    ('a15', 'anon', 'Sixth what?', 1.0, None),
    ('wh11', 'whale', 'Every cycle, the market makes someone who will not sell. Every cycle, I sell to him.', 1.0, None),
    ('wh12', 'whale', 'Someone has to be the exit liquidity. It has always been you.', 1.0, None),
    ('a16', 'anon', 'Then why am I still here?', 1.0, None),
    ('wh13', 'whale', 'Because this time, you brought friends.', 1.0, None),
    ('wh14', 'whale', 'Left. You sell to me now, the crash stops, and the basement survives. / Right. You hold. / '
     'And the girl on the roof is liquidated.', 1.0,
     'Left: you sell to me now, the crash stops, and the basement survives. Right: you hold... and the girl on the roof is liquidated.'),
    ('a17', 'anon', "I don't sell.", 0.95, None),
    ('wh15', 'whale', 'Nobody / holds / forever.', 0.9, 'Nobody... holds... forever.'),
    ('a18', 'anon', 'Watch me.', 0.95, None),
    # --- 5. liquidation
    ('m12', 'michi', 'How?', 0.9, '...How?'),
    ('a19', 'anon', 'Bought the dip.', 0.95, None),
]


def clones(audio, rate, n=12, seed=7):
    """One take from n bodies: copies delayed 0-90 ms with slightly different levels, summed and normalised."""
    rng = np.random.default_rng(seed)
    pad = int(0.1 * rate)
    mix = np.zeros(len(audio) + pad, np.float32)
    for k in range(n):
        d = 0 if k == 0 else int(rng.uniform(0.008, 0.09) * rate)
        mix[d:d + len(audio)] += audio * (1.0 if k == 0 else rng.uniform(0.35, 0.7))
    return (mix / np.abs(mix).max() * np.abs(audio).max() * 1.1).astype(np.float32)


def main(kokoro_dir, out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    kokoro = Kokoro(f'{kokoro_dir}/kokoro-v1.0.onnx', f'{kokoro_dir}/voices-v1.0.bin')
    rate = 24000
    result = json.load(open(f'{out_dir}/vo.json')) if only and os.path.exists(f'{out_dir}/vo.json') else {}
    for line_id, who, text, factor, caption in LINES:
        if only and line_id not in only:
            continue
        voice, lang, speed = VOICES[who]
        gap = np.zeros(int(PAUSE * rate), np.float32)
        parts = []
        for i, piece in enumerate(p.strip() for p in text.split(' / ')):
            if i:
                parts.append(gap)
            parts.append(say(kokoro, piece, voice, speed * factor, lang))
        audio = np.concatenate(parts)
        if who == 'jean12':
            audio = clones(audio, rate)
        sf.write(f'{out_dir}/{line_id}.wav', audio, rate)
        result[line_id] = {'dur': round(len(audio) / rate, 3), 'sub': caption or text.replace(' / ', ' '),
                           'who': 'jean' if who == 'jean12' else who}
        print(line_id, who, result[line_id]['dur'], result[line_id]['sub'])
    with open(f'{out_dir}/vo.json', 'w') as handle:
        json.dump(result, handle, indent=1)
    print('TOTAL', round(sum(item['dur'] for item in result.values()), 1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(',') if len(sys.argv) > 3 else None)
