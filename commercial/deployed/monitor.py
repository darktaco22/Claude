"""The Thumb's screen: the game's own HUD (hand of 4, NEXT card, Copium bar, clock) drawn from the recorded match.

    python3 monitor.py MATCH_JSON CARDS_DIR OUT_DIR [fps]      -> OUT_DIR/m_00001.png ... (528 x 318) and monitor.mp4
    import monitor; monitor.State(match).at(t) -> dict; monitor.tray(image, state, cards_dir, ...) draws the tray

Everything shown is data from the real simulation (`pack/match.json`, recorded by sim/record.mjs): which four cards are in
the hand, which is NEXT, how much Copium there is and what the clock says.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', 'assets', 'lilita.ttf')
INK = (20, 10, 39)
COP, COP_HI, COP_EMPTY = (178, 80, 246), (217, 166, 255), (44, 21, 84)
COST = {'lmao': 4, 'airdrop': 3, 'chillhouse': 5, 'cupsey': 4, 'ket': 3, 'chillguy': 3, 'dope': 2, 'pudgy': 3}
PRE = -46.0                                       # the film starts this long before the match


def font(size):
    return ImageFont.truetype(FONT, size)


class State:
    """Hand, queue, Copium, clock and flash messages at match time t (t < 0: before the match)."""

    def __init__(self, match):
        self.match = match
        plan = match['plan']
        self.hand0, self.queue0 = plan['order0'][:4], plan['order0'][4:]
        self.plays = [item for item in match['log'] if item['what'] == 'thumb']
        self.illegal = [item for item in match['log'] if item['what'] == 'illegal']
        self.downs = [item for item in match['log'] if item['what'] == 'tower_down']
        self.frames = match['frames']
        self.times = [frame['t'] for frame in self.frames]

    def hand_queue(self, t):
        hand, queue, last = self.hand0, self.queue0, None
        for play in self.plays:
            if play['t'] <= t:
                hand, queue, last = play['hand'], play['queue'], play
        return hand, queue, last

    def frame(self, t):
        index = max(0, min(len(self.frames) - 1, int(t * 10)))
        return self.frames[index]

    def at(self, t):
        hand, queue, last = self.hand_queue(t)
        frame = self.frame(max(0.0, t))
        message, color = None, (255, 255, 255)
        for item in self.illegal:
            if item['t'] - 0.1 <= t < item['t'] + 1.4:
                message, color = "CAN'T DEPLOY HERE", (255, 90, 90)
        for item in self.downs:
            if item['t'] <= t < item['t'] + 2.5:
                message, color = ('YOUR TOWER FELL' if item['team'] == 0 else 'ENEMY TOWER DOWN!'), ((255, 90, 90) if item['team'] == 0 else (120, 255, 140))
        if 120.0 <= t < 122.5:
            message, color = 'COPIUM OVERDOSE!', COP_HI
        if t >= 180.0:
            message, color = 'VICTORY!', (255, 226, 90)
        if t < 0:
            message, color = 'WAITING FOR THE THUMB', (200, 200, 220)
        return {'hand': hand, 'next': queue[0], 'copium': frame['cop'] if t >= 0 else 5.0, 'clock': max(0.0, frame['clock']) if t >= 0 else 180.0,
                'message': message, 'color': color, 'ws': frame['ws'], 'last': last, 'press': last and 0 <= t - last['t'] < 0.6}


def clock_text(seconds):
    return f'{int(seconds) // 60}:{int(seconds) % 60:02d}'


_art = {}


def card_art(cards_dir, uid, size):
    key = (uid, size)
    if key not in _art:
        art = Image.open(os.path.join(cards_dir, uid + '.webp')).convert('RGBA').resize(size, Image.LANCZOS)
        mask = Image.new('L', size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), max(6, size[0] // 9), fill=255)
        art.putalpha(mask)
        _art[key] = art
    return _art[key]


def tray(image, state, cards_dir, box=None, scale=1.0, highlight=None):
    """Compatibility wrapper: the game's tray, drawn by hud.py (scale = hud k)."""
    import hud
    hud.tray(image, state, cards_dir, scale, bottom=None if box is None else box[1] + box[3])


def screen(state, cards_dir, size=(528, 318)):
    """The whole screen shown on the hold's monitor: the Thumb's game UI (time, score, tray)."""
    import hud
    w, h = size
    image = Image.new('RGBA', size, (62, 60, 78, 255))
    draw = ImageDraw.Draw(image)
    for y in range(h):
        shade = int(26 * y / h)
        draw.line((0, y, w, y), fill=(70 - shade, 68 - shade, 92 - shade))
    k = w / 924.0
    hud.top_pills(image, k, 'ULTRA CHAD', 7521, state['clock'], True)
    ImageDraw.Draw(image).text((w // 2, 40), f"{state['ws'][0]}  :  {state['ws'][1]}", font=font(30), fill=(255, 255, 255), anchor='mm', stroke_width=4, stroke_fill=INK)
    if state['message']:
        draw = ImageDraw.Draw(image)
        draw.text((w // 2, 112), state['message'], font=font(30), fill=state['color'], anchor='mm', stroke_width=4, stroke_fill=INK)
    hud.tray(image, state, cards_dir, k, bottom=h - 4)
    return image.convert('RGB')


def build(match_path, cards_dir, out_dir, fps=10):
    match = json.load(open(match_path))
    state = State(match)
    os.makedirs(out_dir, exist_ok=True)
    end = 192.0
    count = int((end - PRE) * fps)
    for index in range(count):
        t = PRE + index / fps
        screen(state.at(t), cards_dir).save(os.path.join(out_dir, f'm_{index + 1:05d}.png'))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', os.path.join(out_dir, 'm_%05d.png'), '-c:v', 'libx264', '-crf', '20',
                    '-pix_fmt', 'yuv420p', os.path.join(out_dir, 'monitor.mp4')], check=True)
    print('MONITOR', count, 'frames')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 10)
