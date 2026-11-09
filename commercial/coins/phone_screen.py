"""What Kyle's phone shows, frame by frame (540x1120 PNGs): the real Meme Royale gameplay, the USELESS card turning
out to have a ticker, a search, a chart, the card montage, and the buy screen that fails.
python3 phone_screen.py RAW_FRAMES_DIR,HUD_DIR OUT_DIR   (the NOOB vs PRO raw frames and HUD captures)"""
import os, sys, math, subprocess, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); CARDS = os.path.join(HERE, 'cards')
GAME, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
W, H = 540, 1120; FPS = 30; NF = 880
LIL = os.path.join(A, 'lilita.ttf'); RUB = os.path.join(A, 'rubik.ttf')
def lil(s): return ImageFont.truetype(LIL, s)
def rub(s, w=600):
    f = ImageFont.truetype(RUB, s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def T(f): return (f - 1) / FPS
INK = (20, 10, 48); GREEN = (40, 220, 110); RED = (240, 60, 70); BG = (14, 16, 24)

# the game footage: the raw Blender frames of the NOOB vs PRO tip with the game's own HUD on top (no captions)
RAW, HUDD = GAME.split(',')
def game(f):
    n = 430 + min(150, max(1, f))
    g = Image.open(os.path.join(RAW, f'f_{n:04d}.png')).convert('RGBA'); g.alpha_composite(Image.open(os.path.join(HUDD, f'h_{n:04d}.png')).convert('RGBA'))
    g = g.convert('RGB').resize((W, int(W * g.height / g.width)), Image.LANCZOS)
    im = Image.new('RGB', (W, H), (27, 20, 16)); im.paste(g, (0, (H - g.height) // 2)); return im

card = {c: Image.open(os.path.join(CARDS, c + '.webp')).convert('RGB') for c in os.listdir(CARDS) for c in [c.split('.')[0]]}
TICK = {'useless': ('$USELESS', '+4,200%'), 'lmao': ('$LMAO', '+880%'), 'ket': ('$KET', '+1,337%'), 'pepe': ('$PEPE', '+420%'),
        'chillguy': ('$CHILLGUY', '+690%'), 'wojak': ('$WOJAK', '+212%')}

def status_bar(d, dark=True):
    c = (240, 240, 245) if dark else (20, 20, 25)
    d.text((34, 26), '3:12', font=rub(24, 700), fill=c)
    d.rounded_rectangle((W - 92, 30, W - 46, 50), 5, outline=c, width=2); d.rectangle((W - 89, 33, W - 62, 47), fill=(240, 80, 80))   # low battery
    d.text((W - 150, 26), '5G', font=rub(22, 700), fill=c)

def up(d, xy, txt, font, fill, anchor='la'):
    bb = d.textbbox(xy, txt, font=font, anchor=anchor); h_ = bb[3] - bb[1]; x0 = bb[0] - h_ * 1.1
    d.polygon([(x0, bb[3]), (x0 + h_ * 0.9, bb[3]), (x0 + h_ * 0.45, bb[1])], fill=fill); d.text(xy, txt, font=font, fill=fill, anchor=anchor)

def chart(d, box, seed, up=True, prog=1.0):
    x0, y0, x1, y1 = box; rnd = random.Random(seed); n = 42; vals = []; v = 1.0
    for i in range(n):
        v *= 1 + (rnd.uniform(-0.05, 0.09) if i < n - 10 else rnd.uniform(0.02, 0.32)); vals.append(v)
    lo, hi = min(vals), max(vals); cw = (x1 - x0) / n
    for i, v in enumerate(vals[:max(1, int(n * prog))]):
        o = vals[i - 1] if i else v * 0.97; c = GREEN if v >= o else RED
        ya = y1 - (o - lo) / (hi - lo) * (y1 - y0); yb = y1 - (v - lo) / (hi - lo) * (y1 - y0)
        xc = x0 + i * cw + cw / 2
        d.line((xc, min(ya, yb) - 6, xc, max(ya, yb) + 6), fill=c, width=2)
        d.rectangle((xc - cw * 0.32, min(ya, yb), xc + cw * 0.32, max(ya, yb) + 1), fill=c)

def card_view(c, t0, t, tag=True):
    """the card big, then its ticker stamps on it"""
    im = Image.new('RGB', (W, H), (18, 10, 40)); d = ImageDraw.Draw(im)
    k = ease((t - t0) / 0.25); cw = int(440 * (0.85 + 0.15 * k)); ch = int(cw * 1.25)
    im.paste(card[c].resize((cw, ch), Image.LANCZOS), ((W - cw) // 2, 190))
    d.rounded_rectangle(((W - cw) // 2, 190, (W + cw) // 2, 190 + ch), 22, outline=(255, 214, 80), width=6)
    status_bar(d)
    if tag and t - t0 > 0.35:
        s = TICK[c]; kk = ease((t - t0 - 0.35) / 0.2)
        f = lil(int(66 * (0.6 + 0.4 * kk)))
        bb = d.textbbox((0, 0), s[0], font=f); w = bb[2] - bb[0] + 50
        cx = W // 2; y = 190 + ch - 40
        d.rounded_rectangle((cx - w // 2, y, cx + w // 2, y + 92), 26, fill=(255, 214, 80), outline=INK, width=5)
        d.text((cx, y + 46), s[0], font=f, fill=INK, anchor='mm')
        if t - t0 > 0.6:
            up(d, (cx + 18, y + 150), s[1] + '  LIVE', rub(40, 800), GREEN, 'mm')
    return im

def browser(t, t0):
    im = Image.new('RGB', (W, H), (246, 246, 250)); d = ImageDraw.Draw(im); status_bar(d, dark=False)
    d.rounded_rectangle((26, 80, W - 26, 140), 30, fill=(230, 231, 238))
    q = '$USELESS coin'; n = int(len(q) * min(1, (t - t0) / 0.55))
    d.text((60, 110), q[:n] + ('|' if int(t * 4) % 2 else ''), font=rub(30, 500), fill=(30, 30, 40), anchor='lm')
    if t - t0 > 0.65:
        for i, (a, b) in enumerate([('USELESS (USELESS) price today', 'Price, chart and market cap for $USELESS…'),
                                    ('Is $USELESS useless?', "It's in the name. Holders: 'it's a lifestyle'…"),
                                    ('USELESS is up 4,200% this month', 'Analysts confused, holders not…')]):
            y = 190 + i * 150
            d.text((40, y), a, font=rub(30, 700), fill=(40, 70, 200)); d.text((40, y + 48), b, font=rub(24, 400), fill=(90, 90, 100))
    return im

def coin_page(c, t, t0, buy=None):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im); status_bar(d)
    s = TICK[c]; th = card[c].resize((110, 138), Image.LANCZOS); im.paste(th, (34, 92))
    d.text((164, 110), s[0], font=lil(56), fill=(255, 255, 255)); d.text((164, 178), 'meme coin · MemeDEX', font=rub(24, 500), fill=(150, 150, 170))
    d.text((34, 270), '$0.4207', font=rub(70, 800), fill=(255, 255, 255))
    up(d, (70, 360), s[1] + '  (30d)', rub(36, 800), GREEN)
    chart(d, (30, 440, W - 30, 800), hash(c) % 997, prog=min(1, max(0.05, (t - t0) / 0.9)))
    if buy is not None:
        press = 0 if buy < 0.6 else 1
        d.rounded_rectangle((40, 900, W - 40, 1010), 30, fill=(28, 170, 90) if not press else (18, 120, 64))
        d.text((W // 2, 955), 'BUY ' + s[0], font=lil(54), fill=(255, 255, 255), anchor='mm')
        d.text((W // 2, 860), 'Amount: ALL OF IT', font=rub(28, 700), fill=(200, 200, 215), anchor='mm')
        if buy > 1.0:
            k = ease((buy - 1.0) / 0.2); y = int(-120 + 220 * k)
            d.rounded_rectangle((30, y, W - 30, y + 150), 26, fill=(60, 14, 22), outline=RED, width=4)
            d.text((W // 2, y + 50), 'Insufficient funds', font=rub(36, 800), fill=(255, 120, 130), anchor='mm')
            d.text((W // 2, y + 104), 'Balance: $3.12', font=rub(32, 700), fill=(255, 255, 255), anchor='mm')
    return im

for f in range(1, NF + 1):
    t = T(f)
    if t < 4.6: im = game(f + 6)
    elif t < 9.0:                                  # he taps the card: it has a ticker
        im = game(int(4.6 * 30) + 6); im = im.filter(ImageFilter.GaussianBlur(6)); dk = Image.new('RGB', im.size, (0, 0, 0)); im = Image.blend(im, dk, 0.5)
        cv = card_view('useless', 4.6, t); im = Image.blend(im, cv, min(1.0, (t - 4.6) / 0.15))
    elif t < 9.75: im = browser(t, 9.0)
    elif t < 13.2: im = coin_page('useless', t, 9.75)
    elif t < 16.9:
        seq = [('lmao', 13.2), ('ket', 14.1), ('pepe', 15.0), ('chillguy', 15.9)]
        c, t0 = [x for x in seq if t >= x[1]][-1]; im = card_view(c, t0, t)
    elif t < 21.6: im = coin_page('chillguy', t, 16.9)
    else: im = coin_page('useless', t, 21.0, buy=t - 21.6)
    im.save(os.path.join(OUT, f's_{f:04d}.png'))
print('SCREEN-DONE', NF)
