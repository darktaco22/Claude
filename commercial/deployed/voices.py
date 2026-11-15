"""Dialogue for "DEPLOYED" (Kokoro via kokoro-onnx, Apache-2.0; stock synthetic voices, no real person).

    python3 voices.py KOKORO_DIR OUT_DIR      -> OUT_DIR/<id>.wav + vo.json ({id: {dur, sub, who}})

Cast: SARGE (Walter, jumpmaster), EGG (Cupsey, the rookie), KET (dry veteran), CHILL (Chill Guy), HOUSE (Chillhouse),
PILOT (Farter, on the radio) and SYS (the game's announcer). Game terms are the real ones: Copium, Clout, Arena 2
Backyard BBQ, Arena 3 Strip Mall Lot, emote WAGMI, bot name paperhands420.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

VOICES = {
    'sarge': ('am_onyx', 'en-us', 1.05),
    'egg': ('am_puck', 'en-us', 1.08),
    'ket': ('af_bella', 'en-us', 0.97),
    'chill': ('am_liam', 'en-us', 0.9),
    'house': ('am_santa', 'en-us', 0.85),
    'pilot': ('am_eric', 'en-us', 1.08),
    'sys': ('bf_emma', 'en-gb', 1.0),
}

LINES = [  # id, speaker, text as spoken, speed factor, caption
    ('p01', 'pilot', 'Tower, this is Deck One. Eight cards on board, and one player at the controls. Pray for us.', 1.0, None),
    ('s01', 'sarge', 'Listen up, cards! In thirty seconds, the Thumb is going to play us.', 1.0, None),
    ('e01', 'egg', 'The Thumb, Sarge?', 1.0, None),
    ('s02', 'sarge', 'The player, son. Big. Pink. Makes every decision down there.', 1.0, None),
    ('e02', 'egg', 'And... he has a plan?', 1.0, None),
    ('k01', 'ket', 'He has four cards and a feeling.', 1.0, None),
    ('s03', 'sarge', 'He has been in Arena Two for eight months.', 1.0, None),
    ('c01', 'chill', "Nine. But who's counting.", 1.0, None),
    ('y01', 'sys', 'Copium: four.', 1.0, None),
    ('s04', 'sarge', "Green light! L M A O, you're up! Go, go, go!", 1.08, "Green light! LMAO, you're up! Go, go, go!"),
    ('y02', 'sys', 'L M A O has been eliminated.', 1.0, 'LMAO has been eliminated.'),
    ('e03', 'egg', 'He lasted two seconds!', 1.0, None),
    ('k02', 'ket', 'Personal best.', 0.95, None),
    ('s05', 'sarge', "Here it comes. Airdrop. Their whole push is on the bridge. Even he can't miss this.", 1.0, None),
    ('c02', 'chill', 'He got the duck, though.', 1.0, None),
    ('s06', 'sarge', 'He always gets the duck.', 0.95, None),
    ('y04', 'sys', 'Left tower destroyed.', 1.0, None),
    ('e04', 'egg', "We're losing! What's he doing now?", 1.0, None),
    ('k03', 'ket', "He's emoting.", 0.95, None),
    ('s07', 'sarge', "We are down a tower, and he is sending: we're all gonna make it.", 1.0,
     "We are down a tower, and he is sending \"we're all gonna make it\"."),
    ('c03', 'chill', 'Confidence is important.', 1.0, None),
    ('y05', 'sys', 'Copium: ten. Copium is full.', 1.0, None),
    ('s08', 'sarge', "He's leaking copium! Chillhouse! Move, move, move!", 1.08, None),
    ('h01', 'house', "Sorry. I'm a house.", 1.0, None),
    ('s09', 'sarge', 'Everybody push!', 1.05, None),
    ('k04', 'ket', 'I have seen rug pulls faster than this.', 1.0, None),
    ('y06', 'sys', 'Thirty seconds remaining. Last card: Cupsey.', 1.0, None),
    ('e05', 'egg', "Me? Sarge... I'm an egg.", 0.95, None),
    ('s10', 'sarge', "Son, we are all eggs up here. Some of us just haven't hit the ground yet.", 0.95, None),
    ('e06', 'egg', 'That is the worst speech I have ever heard.', 1.0, None),
    ('s11', 'sarge', "It's the only one I've got. Go!", 1.05, None),
    ('y07', 'sys', 'Opponent paper hands four twenty has left the match.', 1.0, 'Opponent paperhands420 has left the match.'),
    ('y08', 'sys', 'Victory!', 0.95, None),
    ('s12', 'sarge', 'He did it. The kid did absolutely nothing. And it worked.', 0.97, None),
    ('c04', 'chill', 'Classic us.', 1.0, None),
    ('y09', 'sys', 'Plus twenty-eight Clout. New arena unlocked: Strip Mall Lot.', 1.0, None),
    ('k05', 'ket', 'A parking lot. We fought for a parking lot.', 0.97, None),
    ('y10', 'sys', 'Next match in three. Two.', 0.95, None),
    ('s13', 'sarge', 'Meme Royale. Free to play. And please. Play better than this guy.', 0.97, None),
]


def main(kokoro_dir: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    kokoro = Kokoro(f'{kokoro_dir}/kokoro-v1.0.onnx', f'{kokoro_dir}/voices-v1.0.bin')
    result = {}
    for line_id, who, text, factor, caption in LINES:
        voice, lang, speed = VOICES[who]
        audio, rate = kokoro.create(text, voice=voice, speed=speed * factor, lang=lang)
        loud = np.where(np.abs(audio) > 0.01)[0]
        audio = audio[max(0, loud[0] - 400): loud[-1] + 2400]
        sf.write(f'{out_dir}/{line_id}.wav', audio, rate)
        result[line_id] = {'dur': round(len(audio) / rate, 3), 'sub': caption or text, 'who': who}
        print(line_id, who, result[line_id]['dur'], text)
    with open(f'{out_dir}/vo.json', 'w') as handle:
        json.dump(result, handle, indent=1)
    print('TOTAL', round(sum(item['dur'] for item in result.values()), 1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
