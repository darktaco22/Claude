"""Falling green "code": half-width katakana mixed with meme tickers and price glyphs.

    python3 coderain.py OUT_DIR W H FRAMES [SEED]     -> OUT_DIR/r_0001.png ... (loops seamlessly)

Used as the screen texture inside the scene (512 x 512, 48 frames) and full-screen in the finish (title, transitions).
`frame(t, w, h)` can be imported to draw one image at any time t (seconds).
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_JP = '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'
FONT_MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
KANA = [chr(c) for c in range(0xFF66, 0xFF9E)]
TICKERS = ['PEPE', 'BONK', 'SLERF', 'MICHI', 'ZCAT', 'MENSA', 'POPCAT', 'WIF', 'GIGA', 'NEET', 'COPE', 'HODL']
SYMBOLS = list('0123456789$%+-<>=') + ['▲', '▼']


class Rain:
    def __init__(self, w, h, cell=18, seed=7, loop=2.0):
        self.w, self.h, self.cell, self.loop = w, h, cell, loop
        rnd = random.Random(seed)
        self.cols = []
        for x in range(0, w, cell):
            # each column: speed in rows/second chosen so that it wraps an integer number of times per loop (seamless)
            rows = h // cell + 12
            laps = rnd.choice([1, 1, 2, 2, 3])
            speed = rows * laps / loop
            glyphs = []
            for _ in range(rows):
                r = rnd.random()
                if r < 0.06:
                    glyphs.append(rnd.choice(TICKERS)[0])
                elif r < 0.30:
                    glyphs.append(rnd.choice(SYMBOLS))
                else:
                    glyphs.append(rnd.choice(KANA))
            self.cols.append(dict(x=x, rows=rows, speed=speed, phase=rnd.random() * rows, trail=rnd.randint(8, 22),
                                  glyphs=glyphs, flicker=rnd.random()))
        self.font_jp = ImageFont.truetype(FONT_JP, int(cell * 0.95))
        self.font_mono = ImageFont.truetype(FONT_MONO, int(cell * 0.85))

    def frame(self, t):
        img = Image.new('RGB', (self.w, self.h), (0, 3, 0))
        draw = ImageDraw.Draw(img)
        for c in self.cols:
            head = (c['phase'] + c['speed'] * (t % self.loop)) % c['rows']
            for k in range(c['trail']):
                row = int(head) - k
                y = (row % c['rows']) * self.cell - 6 * self.cell
                if y < -self.cell or y > self.h:
                    continue
                fade = 1.0 - k / c['trail']
                # glyphs change now and then (about 3 times a second), deterministically from time
                gi = (row + int((t % self.loop) * 3 + c['flicker'] * 7) * (1 if k % 5 == 0 else 0)) % c['rows']
                ch = c['glyphs'][gi]
                if k == 0:
                    colour = (200, 255, 210)
                else:
                    colour = (int(10 * fade), int(60 + 180 * fade ** 1.5), int(25 * fade))
                font = self.font_jp if ord(ch) > 0x2000 and ch not in '▲▼' else self.font_mono
                draw.text((c['x'], y), ch, fill=colour, font=font)
        glow = img.filter(ImageFilter.GaussianBlur(self.cell * 0.35))
        return Image.blend(img, glow, 0.35).point(lambda v: min(255, int(v * 1.25)))


if __name__ == '__main__':
    out, w, h, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 7
    os.makedirs(out, exist_ok=True)
    rain = Rain(w, h, cell=max(12, w // 40), seed=seed, loop=n / 24.0)
    for i in range(n):
        rain.frame(i / 24.0).save(os.path.join(out, f'r_{i + 1:04d}.png'))
    print('wrote', n, 'frames to', out)
