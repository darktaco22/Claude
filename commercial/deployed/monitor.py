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


def tray(image, state, cards_dir, box, scale=1.0, highlight=None):
    """Draw the game's tray (NEXT, four cards, Copium bar) inside `box` = (x, y, w, h) of an RGBA image."""
    x0, y0, w, h = box
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), int(14 * scale), fill=(24, 12, 48, 235), outline=(120, 70, 200, 255), width=max(2, int(3 * scale)))
    card_h = int(h * 0.62)
    card_w = int(card_h * 0.8)
    gap = int(10 * scale)
    nx = x0 + int(14 * scale)
    ny = y0 + int(h * 0.1)
    next_h = int(card_h * 0.72)
    next_w = int(next_h * 0.8)
    draw.text((nx + next_w // 2, ny - int(2 * scale)), 'NEXT', font=font(int(14 * scale)), fill=(255, 255, 255, 255), anchor='mb')
    image.alpha_composite(card_art(cards_dir, state['next'], (next_w, next_h)), (nx, ny + int(4 * scale)))
    draw.ellipse((nx - 5, ny + 2, nx + int(22 * scale), ny + int(28 * scale)), fill=COP + (255,), outline=INK + (255,), width=2)
    draw.text((nx + int(8 * scale), ny + int(15 * scale)), str(COST[state['next']]), font=font(int(18 * scale)), fill=(255, 255, 255, 255), anchor='mm')
    cx = nx + next_w + int(22 * scale)
    for index, uid in enumerate(state['hand']):
        x = cx + index * (card_w + gap)
        lift = int(10 * scale) if (highlight == index or (state.get('press') and state['last'] and state['last']['slot'] == index)) else 0
        y = y0 + int(h * 0.06) - lift
        image.alpha_composite(card_art(cards_dir, uid, (card_w, card_h)), (x, y))
        draw.rounded_rectangle((x - 2, y - 2, x + card_w + 2, y + card_h + 2), max(6, card_w // 9), outline=(255, 226, 90, 255) if lift else INK + (255,), width=max(2, int(3 * scale)))
        draw.ellipse((x - 7, y - 7, x + int(24 * scale), y + int(24 * scale)), fill=COP + (255,), outline=INK + (255,), width=2)
        draw.text((x + int(8.5 * scale), y + int(8.5 * scale)), str(COST[uid]), font=font(int(18 * scale)), fill=(255, 255, 255, 255), anchor='mm')
    # copium bar
    bx, by = x0 + int(60 * scale), y0 + int(h * 0.76)
    bw, bh = w - int(76 * scale), int(h * 0.17)
    draw.rounded_rectangle((bx - 4, by - 4, bx + bw + 4, by + bh + 4), int(8 * scale), fill=(14, 6, 28, 255))
    seg = bw / 10
    for k in range(10):
        fill = max(0.0, min(1.0, state['copium'] - k))
        left = bx + k * seg + 2
        draw.rounded_rectangle((left, by, bx + (k + 1) * seg - 2, by + bh), int(5 * scale), fill=COP_EMPTY + (255,))
        if fill > 0.02:
            draw.rounded_rectangle((left, by, left + (seg - 4) * fill, by + bh), int(5 * scale), fill=(COP_HI if fill >= 1 and state['copium'] >= 9.99 else COP) + (255,))
    draw.text((x0 + int(30 * scale), by + bh // 2), str(int(state['copium'])), font=font(int(26 * scale)), fill=(255, 255, 255, 255), anchor='mm',
              stroke_width=max(2, int(3 * scale)), stroke_fill=INK)


def screen(state, cards_dir, size=(528, 318)):
    """The whole screen shown on the hold's monitor."""
    w, h = size
    image = Image.new('RGBA', size, (42, 16, 112, 255))
    draw = ImageDraw.Draw(image)
    for y in range(h):
        shade = int(34 * y / h)
        draw.line((0, y, w, y), fill=(44 - shade // 2, 16, 118 - shade))
    draw.rectangle((0, 0, w, 32), fill=INK)
    draw.text((12, 16), 'ARENA 2  ·  BACKYARD BBQ', font=font(16), fill=(255, 210, 90), anchor='lm')
    draw.text((w - 12, 16), clock_text(state['clock']), font=font(20), fill=(255, 255, 255), anchor='rm')
    draw.text((w // 2, 16), f"{state['ws'][0]} : {state['ws'][1]}", font=font(18), fill=(255, 255, 255), anchor='mm')
    if state['message']:
        draw.text((w // 2, 96), state['message'], font=font(34), fill=state['color'], anchor='mm', stroke_width=4, stroke_fill=INK)
    tray(image, state, cards_dir, (10, h - 150, w - 20, 140), 0.85)
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
