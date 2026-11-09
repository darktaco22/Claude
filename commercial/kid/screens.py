"""Phone screens for 7 CENTS: the real Meme Royale shop (screenshot) and, in its style, (its font, purple panels with gold borders) from the game's
own shop data (client data.js: GEM_PACKS, OFFERS). python3 screens.py OUTDIR
  shop/0001..: the kid's night montage: the shop, WHALE VAULT $49.99 tapped again and again, the purchase count racing to 312
  wallet.png: Dad's family wallet the next morning: 0.07 USDC, and the Meme Royale charges stacked down the screen."""
import os, sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); OUT = sys.argv[1]
LIL = os.path.join(H, '..', 'assets', 'lilita.ttf'); SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s: ImageFont.truetype(LIL, s); S_ = lambda s: ImageFont.truetype(SANS, s)
W, Hh = 540, 1140
PACKS = [('Pocket of Gems', 80, 0.99, None), ('Bag of Gems', 500, 4.99, None), ('Box of Gems', 1200, 9.99, 'POPULAR'),
         ('Chest of Gems', 2600, 19.99, None), ('Whale Vault', 7000, 49.99, 'BEST VALUE')]
PURPLE = (58, 30, 120); DEEP = (24, 12, 52); GOLD = (255, 196, 46); WHITE = (255, 255, 255)


def gem(d, cx, cy, r, c=(80, 230, 255)):
    pts = [(cx, cy - r), (cx + r * 0.85, cy - r * 0.2), (cx, cy + r), (cx - r * 0.85, cy - r * 0.2)]
    d.polygon(pts, fill=c, outline=(255, 255, 255)); d.line([(cx - r * 0.85, cy - r * 0.2), (cx + r * 0.85, cy - r * 0.2)], fill=(255, 255, 255), width=2)


def stroke_text(d, xy, s, font, fill=WHITE, sw=5, anchor='mm'):
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0))


def shop_frame(gems, n, tap, pop):
    im = Image.new('RGB', (W, Hh), DEEP); d = ImageDraw.Draw(im)
    for y in range(Hh):
        k = y / Hh; d.line([(0, y), (W, y)], fill=(int(30 + 30 * k), int(14 + 10 * k), int(66 + 40 * k)))
    # top bar: gems counter, coins
    d.rounded_rectangle([20, 30, 260, 92], 18, fill=(12, 6, 30), outline=GOLD, width=3); gem(d, 55, 61, 18)
    stroke_text(d, (160, 61), f'{gems:,}', F(36))
    d.rounded_rectangle([280, 30, 520, 92], 18, fill=(12, 6, 30), outline=GOLD, width=3)
    d.ellipse([297, 43, 333, 79], fill=GOLD, outline=(160, 100, 0), width=3); stroke_text(d, (420, 61), '100', F(36))
    stroke_text(d, (W // 2, 150), 'SHOP', F(72), GOLD, 7)
    stroke_text(d, (W // 2, 222), 'GEMS', F(40))
    y0 = 262
    for i, (lab, g, usd, tag) in enumerate(PACKS):
        big = lab == 'Whale Vault'; h = 200 if big else 120; y = y0
        box = [24, y, W - 24, y + h]
        d.rounded_rectangle(box, 22, fill=PURPLE if not big else (92, 40, 170), outline=GOLD, width=5 if big else 3)
        gem(d, 90, y + h // 2, 34 if big else 24)
        if big:
            for k in range(5): gem(d, 60 + k * 18, y + h // 2 + 40 - (k % 2) * 14, 16)
        stroke_text(d, (140, y + h // 2 - (22 if big else 14)), lab.upper(), F(36 if big else 27), WHITE, 5, 'lm')
        stroke_text(d, (150, y + h // 2 + (26 if big else 22)), f'{g:,} gems', F(28 if big else 24), (190, 230, 255), 4, 'lm')
        bx = [W - 172, y + h // 2 - 34, W - 40, y + h // 2 + 34]
        pressed = big and tap > 0
        d.rounded_rectangle([bx[0], bx[1] + (6 if pressed else 0), bx[2], bx[3] + (6 if pressed else 0)], 18, fill=(40, 200, 90) if not pressed else (30, 150, 70), outline=(0, 0, 0), width=3)
        stroke_text(d, ((bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2 + (6 if pressed else 0)), f'${usd:.2f}', F(32))
        if tag:
            tw = 22 * len(tag) + 20
            d.rounded_rectangle([W - 40 - tw, y - 16, W - 40, y + 22], 12, fill=(235, 50, 80) if tag == 'BEST VALUE' else (255, 140, 0), outline=(0, 0, 0), width=3)
            stroke_text(d, (W - 40 - tw // 2, y + 3), tag, F(26), WHITE, 3)
        if pressed:      # the tap ripple on the price button
            r = 30 + 60 * tap; cx, cy = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=4)
        y0 += h + 26
    if pop > 0:          # PURCHASE COMPLETE, with the running count
        ov = Image.new('RGBA', (W, Hh), (0, 0, 0, int(150 * pop))); im = Image.alpha_composite(im.convert('RGBA'), ov)
        d = ImageDraw.Draw(im); s = 0.85 + 0.15 * pop
        cy = 560; hw, hh = int(220 * s), int(150 * s)
        d.rounded_rectangle([W // 2 - hw, cy - hh, W // 2 + hw, cy + hh], 26, fill=(70, 30, 140), outline=GOLD, width=6)
        stroke_text(d, (W // 2, cy - 80), 'PURCHASE', F(int(52 * s)), GOLD, 6); stroke_text(d, (W // 2, cy - 22), 'COMPLETE!', F(int(52 * s)), GOLD, 6)
        gem(d, W // 2 - 90, cy + 55, 26); stroke_text(d, (W // 2 + 20, cy + 55), '+7,000', F(int(46 * s)), (150, 240, 255), 5)
        stroke_text(d, (W // 2, cy + 115), f'x{n}', F(int(40 * s)), WHITE, 5)
        im = im.convert('RGB')
    return im


def shop_sequence(out, secs=4.2, fps=30):
    """The real shop (shop_real.png: a screenshot of Meme Royale's SHOP from a throwaway free account, the GEMS row swiped to
    the Whale Vault). Each tap: a ripple on $49.99, a generic wallet sheet slides up and is approved, the real gem
    counter jumps by 7,000. Taps come faster and faster; the counter races past two million."""
    os.makedirs(out, exist_ok=True)
    base = Image.open(os.path.join(H, 'shop_real.png')).convert('RGB')                 # 1170 x 2532
    taps = [0.25, 1.05, 1.65, 2.15, 2.55, 2.9, 3.18, 3.44, 3.68, 3.9]
    counts = [1, 2, 3, 5, 9, 19, 48, 120, 211, 312]
    N = int(secs * fps); PX, PY = 975, 1355
    for i in range(N):
        t = i / fps; im = base.copy(); d = ImageDraw.Draw(im)
        n = 0; tap = 0.0; sheet = 0.0
        for k, tt in enumerate(taps):
            if t >= tt + 0.32: n = counts[k]
            u = t - tt
            if 0 <= u < 0.14: tap = u / 0.14
            nxt = (taps[k + 1] - tt) if k + 1 < len(taps) else 0.6
            if 0.06 <= u < min(0.34, nxt): sheet = max(sheet, min(1.0, (u - 0.06) / 0.08) * (1.0 if u < 0.28 else max(0.0, 1 - (u - 0.28) / 0.06)))
        # the gem counter (cover the 100, write the new total in the game's font and colour)
        d.rounded_rectangle([935, 180, 1050, 240], 10, fill=(48, 29, 118))
        g = 100 + 7000 * n; fs = 52 if g < 100000 else 40 if g < 1000000 else 30
        d.text((990, 210), f'{g:,}', font=F(fs), fill=(232, 214, 255), anchor='mm')
        # the kid's account name over the throwaway one
        d.rounded_rectangle([196, 40, 600, 114], 8, fill=(48, 29, 118)); d.text((210, 78), 'kayla_2013', font=F(46), fill=(255, 255, 255), anchor='lm')
        if tap > 0:
            r = int(40 + 130 * tap)
            d.ellipse([PX - r, PY - r, PX + r, PY + r], outline=(255, 255, 255), width=8)
        if sheet > 0:
            ov = Image.new('RGBA', im.size, (0, 0, 0, int(120 * sheet))); im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB'); d = ImageDraw.Draw(im)
            y0 = int(2532 - 760 * sheet)
            d.rounded_rectangle([0, y0, 1170, 2600], 60, fill=(24, 24, 30))
            d.rounded_rectangle([525, y0 + 26, 645, y0 + 40], 7, fill=(80, 80, 92))
            d.text((585, y0 + 120), 'Confirm payment', font=S_(54), fill=(235, 235, 240), anchor='mm')
            d.text((585, y0 + 210), 'Meme Royale  ·  Whale Vault', font=S_(40), fill=(150, 150, 165), anchor='mm')
            d.text((585, y0 + 330), '- 49.99 USDC', font=S_(84), fill=(255, 255, 255), anchor='mm')
            d.rounded_rectangle([90, y0 + 470, 1080, y0 + 600], 65, fill=(120, 90, 255))
            d.text((585, y0 + 535), 'Approve', font=S_(52), fill=(255, 255, 255), anchor='mm')
        if n > 1:
            stroke_text(d, (585, 1600), f'x{n}', F(120), GOLD, 12)
        im.resize((540, 1168), Image.LANCZOS).save(f'{out}/{i + 1:04d}.png')


def wallet(path):
    im = Image.new('RGB', (W, Hh), (247, 248, 250)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 300], fill=(20, 22, 30))
    d.text((W // 2, 60), 'Family Wallet', font=S_(30), fill=(200, 205, 215), anchor='mm')
    d.text((W // 2, 150), '$0.07', font=S_(96), fill=WHITE, anchor='mm'); d.text((W // 2, 225), '0.07 USDC', font=S_(28), fill=(150, 160, 175), anchor='mm')
    d.text((30, 330), 'Recent activity', font=S_(28), fill=(30, 30, 40))
    y = 380; rr = random.Random(4)
    for i in range(9):
        d.rounded_rectangle([20, y, W - 20, y + 74], 14, fill=WHITE, outline=(225, 228, 235))
        d.ellipse([34, y + 13, 82, y + 61], fill=(110, 50, 200)); d.text((58, y + 37), 'M', font=S_(26), fill=WHITE, anchor='mm')
        d.text((96, y + 24), 'Meme Royale', font=S_(25), fill=(25, 25, 35), anchor='lm'); d.text((96, y + 54), f'Whale Vault  ·  2:{59 - i * 3:02d} AM', font=S_(19), fill=(130, 135, 150), anchor='lm')
        d.text((W - 36, y + 37), '-$49.99', font=S_(27), fill=(220, 40, 50), anchor='rm'); y += 84
    d.text((W // 2, y + 26), '+ 303 more', font=S_(26), fill=(110, 50, 200), anchor='mm')
    im.save(path)


if __name__ == '__main__':
    shop_sequence(os.path.join(OUT, 'scr_shop')); wallet(os.path.join(OUT, 'wallet.png')); print('screens ->', OUT)
