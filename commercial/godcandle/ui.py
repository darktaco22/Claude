"""The trader's phone: a pump.fun-style token page drawn frame by frame (1080x2340, 24 fps) for the phone's screen, plus the three
monitors on his desk.  python3 ui.py OUT_DIR [first last]   ->  OUT_DIR/u_0001.png ...   and  ui.json (where the god candle sits on the screen).
Timeline (seconds): the chart ticks; 1.2 he taps the 5 SOL chip; 2.0 he taps PLACE TRADE; 2.1-2.5 it spins; 2.5 'bought' toast and the
chart goes parabolic (the last candle swells and the axis rescales until the older candles are specks); 3.3 the candle leaves the screen."""
import os, sys, json, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets')
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
W, H = 1080, 2340; FPS = 24; T_END = 6.4
def rub(s, w=600):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def lil(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
BG = (14, 16, 20); CARD = (26, 29, 36); EDGE = (44, 48, 58); TXT = (236, 240, 246); DIM = (140, 148, 162); GRN = (38, 226, 112); RED = (240, 64, 76)
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def fmt(v):
    if v < 1000: return f'${v:.0f}'
    if v < 1e6: return f'${v / 1e3:.1f}K'
    return f'${v / 1e6:.2f}M'
# ---- the chart data: a drifting random walk of market cap in dollars
rr = random.Random(21); NC = 30; ser = []; p = 9300.0
for i in range(NC):
    d = p * rr.gauss(0.012 if i % 3 else -0.02, 0.035); o_, c_ = p, p + d; hi = max(o_, c_) + abs(rr.gauss(0, 0.012)) * p; lo = min(o_, c_) - abs(rr.gauss(0, 0.012)) * p; ser.append([o_, c_, hi, lo]); p = c_
BASE = ser[-1][1]
PX0, PX1, PY0, PY1 = 40, 930, 330, 1250       # the plot (x, y of its edges)
XL = PX1 - 30                                   # the live candle's x
T_P0, T_P1 = 2.5, 3.3                           # the pump
TOP_MC = 1.28e6
def last_candle(tu):
    """(open, close, high, low, width_px) of the live candle at tu."""
    if tu < T_P0:
        j = math.sin(tu * 9.0) * 0.012 + math.sin(tu * 23.0) * 0.006; c = BASE * (1 + j); return BASE, c, max(BASE, c) * 1.006, min(BASE, c) * 0.994, 14
    u = ease((tu - T_P0) / (T_P1 - T_P0)); e = u ** 2.2
    c = BASE * math.exp(math.log(TOP_MC / BASE) * e); w = 14 + (186 - 14) * ease((tu - 2.85) / 0.45)
    return BASE, c, c * 1.0, BASE * 0.99, w
def chart_geom(tu):
    """The axis rescales to fit; returns f(price)->y plus the live candle's pixel box."""
    cs = ser[:-1] + [list(last_candle(tu)[:4])]
    lo = min(c[3] for c in cs); hi = max(c[2] for c in cs); pad = (hi - lo) * 0.05 + 1; lo -= pad; hi += pad * 0.4
    if tu > T_P0: lo = 0.0
    return (lambda v: PY1 - (v - lo) / (hi - lo) * (PY1 - PY0)), lo, hi
def grad_candle(im, x0, x1, y0, y1, a=1.0):
    """The god candle, 2D: dark green at the foot to near-white at the top, with a bright wick."""
    if y1 - y0 < 2: return
    g = Image.new('RGB', (max(1, int(x1 - x0)), max(1, int(y1 - y0))))
    d = ImageDraw.Draw(g); n = g.size[1]
    for k in range(n):
        u = 1 - k / max(1, n - 1); d.line((0, k, g.size[0], k), fill=(int(5 + 215 * u ** 1.6), int(110 + 145 * u ** 0.9), int(30 + 175 * u ** 1.8)))
    d.rectangle((int(g.size[0] * 0.1), 0, int(g.size[0] * 0.2), n), fill=(210, 255, 200))
    if a < 1: g = Image.blend(im.crop((int(x0), int(y0), int(x0) + g.size[0], int(y0) + g.size[1])), g, a)
    im.paste(g, (int(x0), int(y0)))
def draw_chart(im, d, tu):
    d.rounded_rectangle((20, 290, 1060, 1310), 28, fill=CARD)
    f, lo, hi = chart_geom(tu)
    for k in range(6):                                              # grid + axis
        v = lo + (hi - lo) * k / 5; y = f(v); d.line((PX0, y, PX1, y), fill=(38, 42, 52), width=2); d.text((PX1 + 16, y - 16), fmt(max(v, 1)).replace('$', ''), font=rub(28, 500), fill=DIM)
    for k in range(7): d.line((PX0 + k * (PX1 - PX0) / 6, PY0, PX0 + k * (PX1 - PX0) / 6, PY1), fill=(34, 38, 47), width=2)
    for k, lab in enumerate(('3:00', '3:03', '3:06', '3:09')): d.text((PX0 + 30 + k * 250, PY1 + 20), lab, font=rub(26, 500), fill=DIM)
    n = NC; dx = (XL - PX0 - 20) / (n - 1)
    for i in range(n):
        o_, c_, hi_, lo_ = ser[i] if i < n - 1 else last_candle(tu)[:4]; wd = 14 if i < n - 1 else last_candle(tu)[4]; x = PX0 + 20 + dx * i if i < n - 1 else XL
        up = c_ >= o_; col = GRN if up else RED
        if i == n - 1 and tu >= T_P0 and wd > 30:
            if tu < 3.3: grad_candle(im, x - wd / 2, x + wd / 2, f(hi_), f(lo_))
            continue
        d.line((x, f(hi_), x, f(lo_)), fill=col, width=3); d.rectangle((x - wd / 2, f(max(o_, c_)), x + wd / 2, max(f(max(o_, c_)) + 4, f(min(o_, c_)))), fill=col)
    # price tag of the live candle
    c = last_candle(tu)[1]; y = f(c); tag = fmt(c)
    d.rounded_rectangle((PX1 + 6, y - 20, 1052, y + 20), 8, fill=GRN); d.text((PX1 + 14, y - 16), tag.replace('$', ''), font=rub(26, 700), fill=(5, 20, 10))
def tap_ring(im, cx, cy, t0, tu):
    """A touch ripple where the finger lands."""
    if not (t0 <= tu <= t0 + 0.35): return
    u = (tu - t0) / 0.35; r = 20 + 70 * u; ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, int(160 * (1 - u))), width=6)
    im.alpha_composite(ov)
def screen(tu):
    im = Image.new('RGBA', (W, H), BG + (255,)); d = ImageDraw.Draw(im)
    # status bar + header
    d.text((70, 40), '3:07', font=rub(40, 700), fill=TXT); d.text((W - 70, 40), '5G  ▮▮▮  62%', font=rub(32, 500), fill=TXT, anchor='ra')
    d.text((40, 112), '‹', font=rub(80, 400), fill=TXT); d.text((W / 2, 56), 'pump.fun', font=lil(44), fill=GRN, anchor='mm')
    d.ellipse((90, 150, 200, 260), fill=(255, 205, 60)); d.text((145, 205), '♛', font=rub(66, 600), fill=(90, 40, 0), anchor='mm')
    d.text((222, 150), '$ROYALE', font=lil(70), fill=TXT); d.text((224, 228), 'Meme Royale', font=rub(34, 500), fill=DIM)
    if tu < T_P0: mc = BASE * (1 + 0.012 * math.sin(tu * 9.0)); pct = 312 + 3 * math.sin(tu * 9)
    else: mc = last_candle(tu)[1]; pct = 312 + (mc / BASE - 1) * 100
    d.text((W - 40, 156), 'MKT CAP', font=rub(28, 500), fill=DIM, anchor='ra'); d.text((W - 40, 190), fmt(mc), font=lil(64), fill=GRN, anchor='ra')
    draw_chart(im, d, tu)
    d = ImageDraw.Draw(im)
    # Buy / Sell
    d.rounded_rectangle((30, 1350, 1050, 1450), 24, fill=CARD); d.rounded_rectangle((36, 1356, 540, 1444), 20, fill=GRN); d.text((288, 1400), 'Buy', font=lil(56), fill=(5, 22, 12), anchor='mm'); d.text((795, 1400), 'Sell', font=lil(56), fill=DIM, anchor='mm')
    # amount
    amt = '5' if tu >= 1.2 else '0'; d.rounded_rectangle((30, 1480, 1050, 1630), 28, fill=CARD, outline=EDGE, width=3)
    d.text((70, 1555), amt, font=lil(100), fill=TXT if tu >= 1.2 else DIM, anchor='lm'); d.text((1010, 1555), 'SOL ◎', font=lil(54), fill=DIM, anchor='rm')
    for k, (lab, cx) in enumerate((('1 SOL', 160), ('5 SOL', 395), ('10 SOL', 650), ('MAX', 900))):
        on = (k == 1 and tu >= 1.2); d.rounded_rectangle((cx - 105, 1660, cx + 105, 1740), 22, fill=(20, 70, 44) if on else CARD, outline=GRN if on else EDGE, width=4 if on else 3)
        d.text((cx, 1700), lab, font=lil(44), fill=GRN if on else TXT, anchor='mm')
    # PLACE TRADE
    press = 0.0
    if 1.98 <= tu < 2.12: press = 1.0
    bx0, by0, bx1, by1 = 40, 1800, 1040, 1950; sh = 6 if press else 0
    d.rounded_rectangle((bx0 + sh, by0 + sh, bx1 - sh, by1 - sh), 34, fill=(22, 170, 84) if press else GRN)
    if 2.1 <= tu < 2.5:
        a = (tu - 2.1) * 12; d.arc((520 - 44, 1875 - 44, 520 + 44, 1875 + 44), math.degrees(a), math.degrees(a) + 250, fill=(5, 22, 12), width=11)
    else: d.text((540, 1873), 'Place trade' if not (2.5 <= tu < 3.4) else '✓  Trade placed', font=lil(72), fill=(5, 22, 12), anchor='mm')
    # trades
    d.text((40, 2000), 'Trades', font=lil(56), fill=TXT); rows = [('9xK2…f1', 'sold', '0.8 SOL', RED), ('Hq7d…a3', 'bought', '2.1 SOL', GRN), ('B3mw…0c', 'bought', '0.4 SOL', GRN), ('4pRe…zz', 'bought', '1.3 SOL', GRN)]
    if tu >= 2.5: rows = [('you', 'bought', '5 SOL', GRN)] + rows
    for k, (a_, b_, c_, col) in enumerate(rows[:4]):
        y = 2090 + k * 62; d.text((50, y), a_, font=rub(36, 600), fill=GRN if a_ == 'you' else TXT); d.text((520, y), b_, font=rub(36, 600), fill=col); d.text((1040, y), c_, font=rub(36, 600), fill=TXT, anchor='ra')
    # touch ripples
    tap_ring(im, 395, 1700, 1.2, tu); tap_ring(im, 540, 1875, 2.0, tu)
    # the pump: the screen floods green, the whole thing glows and then the candle has left
    if tu > 3.0:
        k = ease((tu - 3.0) / 0.35); ov = Image.new('RGBA', (W, H), (60, 255, 130, int(150 * k))); im = Image.alpha_composite(im, ov)
    if tu > 3.3:
        k = min(1.0, (tu - 3.3) / 0.25); ov = Image.new('RGBA', (W, H), (255, 255, 255, int(235 * (1 - k) + 25 * k))); im = Image.alpha_composite(im, ov)
    if 2.5 < tu < 3.35:                                              # a camera-shake of the UI: it can't take it
        s = (tu - 2.5) / 0.85; dx = int(math.sin(tu * 90) * 14 * s); dy = int(math.cos(tu * 77) * 10 * s); im = im.transform(im.size, Image.AFFINE, (1, 0, dx, 0, 1, dy))
    return im.convert('RGB')
def monitor(path, seed, bear, w=1920, h=1080):
    r = random.Random(seed); im = Image.new('RGB', (w, h), (10, 12, 16)); d = ImageDraw.Draw(im); p = 100.0
    for k in range(0, h, 120): d.line((0, k, w, k), fill=(26, 30, 38), width=2)
    xs = []
    for i in range(46):
        o_ = p; c_ = p + r.gauss(-1.2 if bear else 1.2, 6); xs.append((o_, c_, max(o_, c_) + abs(r.gauss(0, 3)), min(o_, c_) - abs(r.gauss(0, 3)))); p = c_
    lo = min(x[3] for x in xs); hi = max(x[2] for x in xs)
    for i, (o_, c_, h_, l_) in enumerate(xs):
        x = 80 + i * 38; yy = lambda v: 980 - (v - lo) / (hi - lo) * 860; col = GRN if c_ >= o_ else RED
        d.line((x, yy(h_), x, yy(l_)), fill=col, width=4); d.rectangle((x - 12, yy(max(o_, c_)), x + 12, yy(min(o_, c_)) + 3), fill=col)
    d.text((70, 30), '$ROYALE / SOL   ' + ('-18.4%' if bear else '+312%'), font=lil(70), fill=RED if bear else GRN); im.save(path)
if len(sys.argv) > 2 and sys.argv[2] == 'monitors':
    for k in range(3): monitor(os.path.join(OUT, f'mon{k}.png'), 40 + k, k == 1)
    sys.exit(0)
# where the candle stands on the screen at the moment it leaves (tu = 3.3)
f, lo, hi = chart_geom(3.3); oc = last_candle(3.3); info = dict(w=W, h=H, x=XL, y_base=f(BASE), y_top=f(oc[1]), wpx=oc[4], tend=T_END)
json.dump(info, open(os.path.join(OUT, 'ui.json'), 'w'))
first = int(sys.argv[2]) if len(sys.argv) > 2 else 1; last = int(sys.argv[3]) if len(sys.argv) > 3 else int(T_END * FPS)
for n in range(first, last + 1):
    screen((n - 1) / FPS).save(os.path.join(OUT, f'u_{n:04d}.png'))
print('UI-DONE', info)
