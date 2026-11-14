"""Commentary for "The Final" (Kokoro via kokoro-onnx, Apache-2.0; stock synthetic voices, no real person).

    python3 voices.py KOKORO_DIR OUT_DIR      -> OUT_DIR/<id>.wav + vo.json ({id: {dur, sub, who}})

Two speakers: CHIP (play-by-play, American) and BASIL (analysis, British). "Pepe" is spelled "Pepay" for speech.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

VOICES = {'chip': ('am_michael', 'en-us', 1.06), 'basil': ('bm_george', 'en-gb', 0.97)}

LINES = [  # id, speaker, text as spoken, speed factor, caption
    ('c01', 'chip', 'Good evening, and welcome to the Meme Royale Championship Final!', 1.0, None),
    ('b01', 'basil', 'A sell-out crowd tonight, Chip. Which is remarkable, because the game is free.', 1.0, None),
    ('c02', 'chip', 'In the red corner, the undefeated champion. Giga!', 1.0, None),
    ('b02', 'basil', 'Forty-four wins. No losses. He has never once checked the price.', 1.0, None),
    ('c03', 'chip', 'And in the blue corner, the challenger. Pepay.', 0.97, 'And in the blue corner, the challenger. Pepe.'),
    ('b03', 'basil', "Down ninety-nine percent, and somehow still here. I admire it. I don't understand it.", 1.0, None),
    ('c04', 'chip', "And we're under way! Giga opens with the Whale, straight down the left!", 1.04, None),
    ('b04', 'basil', 'Lovely movement from the Whale. He moves markets, that one.', 1.0, None),
    ('c05', 'chip', "And Pepay's response is... nothing. He's played nothing.", 0.98, "And Pepe's response is... nothing. He's played nothing."),
    ('b05', 'basil', "He's holding, Chip. It's all he knows.", 0.97, None),
    ('c06', 'chip', 'Tower down! The Whale goes straight through it!', 1.06, None),
    ('b06', 'basil', "Let's see that again. Here's the tower. Tower's fine. Still fine. And there's the Whale.", 0.97, None),
    ('c07', 'chip', "You can't coach that.", 1.0, None),
    ('b07', 'basil', "No. He's simply enormous.", 0.96, None),
    ('c08', 'chip', "The second tower's gone! And the blue fans are heading for the exits!", 1.05, None),
    ('b08', 'basil', "Paper hands, the lot of them. They'll be back at the top.", 1.0, None),
    ('c09', 'chip', "Pepay has one card left. One. And he's playing it.", 0.98, "Pepe has one card left. One. And he's playing it."),
    ('c10', 'chip', "It's... Useless.", 0.9, None),
    ('b09', 'basil', "That's not my opinion, Chip. That is the name of the card.", 1.0, None),
    ('c11', 'chip', "He's just... walking. Nobody's marking him!", 1.0, None),
    ('b10', 'basil', "Well, why would you? He's Useless.", 0.97, None),
    ('c12', 'chip', "He's at the tower. He's at the king's tower!", 1.05, None),
    ('c13', 'chip', 'Useless has done it! Pepay is the champion!', 1.05, 'Useless has done it! Pepe is the champion!'),
    ('b11', 'basil', "Forty-four and one. I have never seen anything like it. Mostly because I looked away.", 1.0, None),
    ('c14', 'chip', 'Pepay! The new champion! Your thoughts?', 1.02, 'Pepe! The new champion! Your thoughts?'),
    ('b12', 'basil', 'Telling no one. Magnificent.', 0.94, None),
    ('c15', 'chip', "Meme Royale. Free to play. We'll be right back after these messages.", 1.0, None),
    ('b13', 'basil', "There are no messages. It's free.", 0.96, None),
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
    with open(f'{out_dir}/vo.json', 'w') as outfile:
        json.dump(result, outfile, indent=1)
    print('total', round(sum(v['dur'] for v in result.values()), 1))


if __name__ == '__main__':
    main(*sys.argv[1:3])
