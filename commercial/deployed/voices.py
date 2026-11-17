"""Dialogue for "DEPLOYED" (Kokoro via kokoro-onnx, Apache-2.0; stock synthetic voices, no real person).

    python3 voices.py KOKORO_DIR OUT_DIR      -> OUT_DIR/<id>.wav + vo.json ({id: {dur, sub, who}})

Cast: SARGE (Walter, jumpmaster), EGG (Cupsey, the rookie), KET (dry veteran), CHILL (Chill Guy), HOUSE (Chillhouse),
PILOT (on the radio). The announcer is the game's own voice (vo_fight, vo_overdose, vo_victory). Game terms are the real ones: Copium, Clout, Arena 2
Backyard BBQ, Arena 3 Strip Mall Lot, emote WAGMI, bot name paperhands420.
"""
import json
import os
import subprocess
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
    # --- the briefing, before the match
    ('p01', 'pilot', 'Tower, this is Deck One. Eight cards on board. One player on the controls. Pray for us.', 1.0, None),
    ('s01', 'sarge', 'Listen up! Eight of us. Four at the door. Four on the bench.', 1.0, None),
    ('e01', 'egg', "What's the difference?", 1.0, None),
    ('s02', 'sarge', 'Door cards can be played. Bench cards wait. The Thumb drags a door card onto the field, that card jumps, and the next one on the bench steps up.', 1.02, None),
    ('e02', 'egg', 'And the one who jumped?', 1.0, None),
    ('s03', 'sarge', 'Back of the line.', 0.95, None),
    ('k01', 'ket', 'Jump, fight, back in the queue. The circle of life.', 1.0, None),
    ('c01', 'chill', 'With a deposit.', 0.95, None),
    ('s04', 'sarge', 'Every jump costs Copium. Cupsey, four. L M A O, four. Chillhouse, five.', 1.0, 'Every jump costs Copium. Cupsey, four. LMAO, four. Chillhouse, five.'),
    ('e03', 'egg', "And if he doesn't have enough?", 1.0, None),
    ('k02', 'ket', 'We wait.', 0.95, None),
    ('s05', 'sarge', "And if he has too much? Copium stops at ten. Everything above that is wasted.", 1.0, None),
    ('c02', 'chill', 'Like my knees.', 0.95, None),
    # --- the first minute
    ('s06', 'sarge', "Match on! Eyes on the screen! Wait for the Thumb!", 1.08, None),
    ('k03', 'ket', 'Two Copium. The cheap one.', 1.0, None),
    ('s07', 'sarge', "Chillhouse! Five Copium! He can afford you!", 1.06, None),
    ('h01', 'house', "Sorry. I'm a house.", 1.0, None),
    ('e04', 'egg', "He's dragging onto the enemy side!", 1.05, None),
    ('s08', 'sarge', "Can't deploy past the river. Not until one of their towers falls.", 1.0, None),
    ('k04', 'ket', "He's a toucher.", 0.95, None),
    ('e05', 'egg', "Why me? I'm a healer!", 1.05, None),
    ('s09', 'sarge', 'Then heal! Jump!', 1.08, None),
    ('s10', 'sarge', "Left tower's down!", 1.06, None),
    ('e11', 'egg', 'Why am I never picked?', 1.05, None),
    ('s21', 'sarge', "Nobody's hurt. Sit.", 1.0, None),
    ('s22', 'sarge', 'Defend first. Then push.', 1.02, None),
    ('c03', 'chill', 'He was dragging.', 0.95, None),
    ('k05', 'ket', 'The wrong side.', 0.95, None),
    ('c04', 'chill', "Finally. I soak hits. I can't be stunned or knocked back. I'm basically furniture.", 1.0, None),
    # --- the airdrop and the first tower
    ('s11', 'sarge', "Airdrop! Their whole push is on the other side. He dropped it on our side.", 1.0, None),
    ('k06', 'ket', 'Free coins. For the lawn.', 0.95, None),
    ('s12', 'sarge', "Their left tower is down!", 1.06, None),
    ('e06', 'egg', 'Who did that?', 1.0, None),
    ('k07', 'ket', 'Units keep fighting after they jump. Remember?', 1.0, None),
    ('s13', 'sarge', 'Cards rotate. Units stay.', 0.97, None),
    ('s20', 'sarge', 'Second tower down! Two towers to none!', 1.06, None),
    # --- Copium overdose
    ('s14', 'sarge', 'Copium overdose! Everything fills twice as fast!', 1.06, None),
    ('e07', 'egg', 'Is that good?', 1.0, None),
    ('k08', 'ket', 'For a dragger? Yes.', 0.95, None),
    ('e08', 'egg', "I've jumped three times! Same four cards!", 1.05, None),
    ('c05', 'chill', "It's a rotation.", 0.95, None),
    ('e09', 'egg', "Why am I still out there? I'm right here!", 1.0, None),
    ('s15', 'sarge', "Don't stack a push. Three cards, then defend.", 1.05, None),
    # --- the finish
    ('s16', 'sarge', 'Twenty seconds! Hold the line!', 1.08, None),
    ('h02', 'house', 'Rent is due.', 0.95, None),
    ('s17', 'sarge', 'Time! Two towers to none!', 1.06, None),
    ('k09', 'ket', 'He defended. Then he pushed.', 0.95, None),
    ('e10', 'egg', "That's a strategy.", 1.0, None),
    ('s18', 'sarge', "That's the game.", 0.92, None),
    ('c06', 'chill', 'Next match. Same eight.', 0.95, None),
    ('s19', 'sarge', 'Meme Royale. Free to play. Drag with purpose.', 0.97, None),
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
    game_audio = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'comeback', 'audio')
    for line_id, clip, caption in (('a_fight', 'vo_fight', 'FIGHT!'), ('a_overdose', 'vo_overdose', 'COPIUM OVERDOSE!'), ('a_victory', 'vo_victory', 'VICTORY!'),
                                   ('a_overtime', 'vo_overtime', 'OVERTIME!')):
        out_path = f'{out_dir}/{line_id}.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(game_audio, clip + '.mp3'), '-ac', '1', '-ar', '24000', out_path], check=True)
        info = sf.info(out_path)
        result[line_id] = {'dur': round(info.duration, 3), 'sub': caption, 'who': 'game'}
    with open(f'{out_dir}/vo.json', 'w') as handle:
        json.dump(result, handle, indent=1)
    print('TOTAL', round(sum(item['dur'] for item in result.values()), 1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
