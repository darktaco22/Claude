"""The trader's phone: the real pump.fun mobile token page (ref_ui.png, a screenshot of the app) with the price, the chart and a buy sheet
animated on top, frame by frame (1080x2340, 24 fps), plus the three monitors on his desk.
  python3 ui.py OUT_DIR [first last]    ->  OUT_DIR/u_0001.png ...  and  ui.json (where the god candle stands on the screen, where the finger taps)
  python3 ui.py OUT_DIR monitors        ->  OUT_DIR/mon0..2.png
Timeline (seconds): the chart ticks; 1.0 he taps BUY, the buy sheet slides up; 1.65 he taps the 5 SOL chip; 2.2 he taps the big Buy button;
2.3-2.55 it spins; 2.55 the sheet closes on a 'bought' toast; 2.7-3.4 the chart goes parabolic (the last candle swells, the axis rescales until the
older candles are specks); 3.4 the candle leaves the screen."""
import os, sys, json, math, random
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets')
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
W, H = 1080, 2340; FPS = 24; T_END = 6.4
KX, KY = W / 924.0, H / 1999.0                         # the reference was read in a 924 x 1999 view: X(d), Y(d) map those coordinates
def X(d): return d * KX
def Y(d): return d * KY
BASEIMG = Image.open(os.path.join(HERE, 'ref_ui.png')).convert('RGB')
def rub(s, w=600):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), int(s))
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
BG = (9, 9, 9); GRN = (74, 222, 128); RED = (242, 54, 69); AXIS = (178, 181, 190); MINT = (134, 239, 172); DOT = (24, 24, 27); WHITE = (250, 250, 250); CARD = (24, 24, 27); EDGE = (48, 48, 54)
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, u): return a + (b - a) * u
T_BUY, T_CHIP, T_CONF, T_SPIN1, T_TOAST, T_P0, T_P1, T_SWAP = 1.0, 1.65, 2.2, 2.3, 2.55, 2.7, 3.4, 3.4
BUY_XY = (X(397), Y(1865)); CHIP_XY = (880, 1830); CONF_XY = (540, 2020)
SHEET_Y = 1380
# ---- the chart data: ~88 one-minute candles tracing the path in the reference, market cap in dollars
NC = 88; XL = X(610); DX = XL / (NC - 1)
PATH = [(0, 255), (8, 215), (15, 205), (25, 215), (45, 178), (55, 172), (90, 205), (130, 207), (190, 205), (225, 192), (255, 158), (280, 148), (300, 142), (330, 180), (350, 172), (372, 150),
        (392, 138), (420, 170), (468, 232), (474, 195), (500, 208), (520, 213), (545, 190), (556, 252), (561, 262), (575, 218), (595, 236), (610, 245.75)]
def path_at(xd):
    for (x0, v0), (x1, v1) in zip(PATH, PATH[1:]):
        if x0 <= xd <= x1: return (v0 + (v1 - v0) * (xd - x0) / (x1 - x0)) * 1000
    return PATH[-1][1] * 1000
rr = random.Random(4); ser = []
for i in range(NC):
    xd = i * DX / KX; p = path_at(xd); o_ = p * (1 + rr.gauss(0, 0.012)); c_ = path_at(min(610, xd + DX / KX)) * (1 + rr.gauss(0, 0.012))
    hi = max(o_, c_) * (1 + abs(rr.gauss(0, 0.012))); lo = min(o_, c_) * (1 - abs(rr.gauss(0, 0.012))); ser.append([o_, c_, hi, lo])
ser[-1][1] = 245750.0; BASE = 245750.0; ser[-1][0] = BASE * 0.998
PYT, PYB = Y(480), Y(1380); LO0, HI0 = 132800.0, 285200.0
TOP_MC = 12.4e6
def last_candle(tu):
    """(open, close, high, low, width_px) of the live candle at tu."""
    if tu < T_P0:
        j = math.sin(tu * 9.0) * 0.004 + math.sin(tu * 23.0) * 0.0025; c = BASE * (1 + j); return BASE * 0.998, c, max(BASE, c) * 1.002, min(BASE, c) * 0.998, 4
    u = ease((tu - T_P0) / (T_P1 - T_P0)); e = u ** 2.2; c = BASE * math.exp(math.log(TOP_MC / BASE) * e); w = 4 + (150 - 4) * ease((tu - 3.0) / 0.4)
    return BASE * 0.998, c, c, BASE * 0.99, w
def axis(tu):
    c = last_candle(tu)[1]; k = ease((tu - T_P0) / 0.35) if tu > T_P0 else 0.0
    return lerp(LO0, 0.0, k), max(HI0, c * 1.05 if tu > T_P0 else HI0)
def yof(v, lo, hi): return PYB - (v - lo) / (hi - lo) * (PYB - PYT)
def fmt_axis(v): return f'{v / 1e6:.2f}M' if v >= 1e6 else f'{v / 1e3:.2f}k'
def fmt_mc(v): return f'${v / 1e6:.2f}M' if v >= 1e6 else f'${v / 1e3:.2f}K'
def nice_step(span):
    raw = span / 6.0; mag = 10 ** math.floor(math.log10(raw)); f = raw / mag
    return (1 if f < 1.5 else 2 if f < 3.5 else 5 if f < 7.5 else 10) * mag
def grad_candle(im, x0, x1, y0, y1):
    """The god candle, 2D: dark green at the foot to near-white at the top, with a bright wick edge."""
    if y1 - y0 < 2 or x1 - x0 < 2: return
    g = Image.new('RGB', (max(1, int(x1 - x0)), max(1, int(y1 - y0)))); d = ImageDraw.Draw(g); n = g.size[1]
    for k in range(n):
        u = 1 - k / max(1, n - 1); d.line((0, k, g.size[0], k), fill=(int(5 + 215 * u ** 1.6), int(110 + 145 * u ** 0.9), int(30 + 175 * u ** 1.8)))
    d.rectangle((int(g.size[0] * 0.1), 0, int(g.size[0] * 0.2), n), fill=(210, 255, 200)); im.paste(g, (int(x0), int(y0)))
def marker(d, cx, cy, ring=None):
    r = 28
    if ring: d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(60, 50, 20), outline=ring, width=5); d.ellipse((cx - 14, cy - 12, cx + 14, cy + 12), fill=(140, 110, 70))
    else:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GRN); d.ellipse((cx - 13, cy - 16, cx + 13, cy + 3), fill=(9, 30, 15)); d.rounded_rectangle((cx - 13, cy - 2, cx + 13, cy + 13), 4, fill=(9, 30, 15))
def tap_ring(im, cx, cy, t0, tu):
    if not (t0 <= tu <= t0 + 0.35): return im
    u = (tu - t0) / 0.35; r = 20 + 70 * u; ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, int(160 * (1 - u))), width=6)
    return Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
def screen(tu):
    im = BASEIMG.copy(); d = ImageDraw.Draw(im); lo, hi = axis(tu); lc = last_candle(tu); mc = lc[1]
    # the price block
    d.rectangle((X(690), Y(235), W, Y(348)), fill=BG)
    d.text((X(889), Y(268)), fmt_mc(mc), font=rub(53, 700), fill=WHITE, anchor='rm')
    pct = (mc / BASE - 1) * 100; lab = f'{pct:,.1f}%' if pct < 1000 else f'{pct:,.0f}%'; fw = d.textlength(lab, font=rub(33, 600)) + 78
    d.rounded_rectangle((X(889) - fw, Y(298), X(889), Y(337)), 10, fill=(14, 46, 18)); d.text((X(889) - fw + 66, Y(318)), lab, font=rub(33, 600), fill=(110, 195, 120), anchor='lm')
    ax, ay = X(889) - fw + 34, Y(318); d.line((ax, ay + 12, ax, ay - 12), fill=(110, 195, 120), width=4); d.line((ax - 9, ay - 3, ax, ay - 12, ax + 9, ay - 3), fill=(110, 195, 120), width=4)
    # the chart: dotted grid, axis, candles, the live price tag
    d.rectangle((0, Y(468), W, Y(1398)), fill=BG)
    for gx in range(14, int(X(790)), 26):
        for gy in range(int(Y(484)), int(Y(1396)), 26): d.rectangle((gx, gy, gx + 2, gy + 2), fill=DOT)
    step = nice_step(hi - lo); v = math.ceil(lo / step) * step
    while v < hi:
        y = yof(v, lo, hi)
        if PYT - 4 <= y <= PYB + 4 and v > 0: d.text((X(902), y), fmt_axis(v), font=rub(32, 500), fill=AXIS, anchor='rm')
        v += step
    fade = 1.0 - ease((tu - T_P0) / 0.3) if tu > T_P0 else 1.0
    for i in range(NC):
        o_, c_, h_, l_ = ser[i] if i < NC - 1 else lc[:4]; x = XL - (NC - 1 - i) * DX; wd = 4 if i < NC - 1 else lc[4]
        if i == NC - 1 and wd > 30:
            if tu < T_SWAP: grad_candle(im, x - wd / 2, x + wd / 2, yof(h_, lo, hi), yof(l_, lo, hi)); d = ImageDraw.Draw(im)
            continue
        col = GRN if c_ >= o_ else RED; d.line((x, yof(h_, lo, hi), x, yof(l_, lo, hi)), fill=col, width=2); y0 = yof(max(o_, c_), lo, hi); y1 = yof(min(o_, c_), lo, hi); d.rectangle((x - wd / 2, y0, x + wd / 2, max(y1, y0 + 2)), fill=col)
    if fade > 0.02 and tu < T_P0 + 0.3:
        for (xd, yd, ring) in ((556, 689, None), (423, 1115, None), (516, 930, (250, 200, 30))): marker(d, X(xd), Y(yd), ring)
    ly = yof(mc, lo, hi)
    for x in range(0, int(X(780)), 11): d.line((x, ly, x + 4, ly), fill=GRN, width=2)
    d.rectangle((X(782), ly - Y(18), W - 4, ly + Y(18)), fill=GRN); d.text((X(845), ly), fmt_axis(mc), font=rub(32, 500), fill=(10, 30, 16), anchor='mm')
    # the BUY button, pressed
    if T_BUY <= tu < T_BUY + 0.12:
        d.rounded_rectangle((X(35) + 5, Y(1805) + 5, X(760) - 5, Y(1925) - 5), 40, fill=(108, 205, 148)); d.text(((X(35) + X(760)) / 2, (Y(1805) + Y(1925)) / 2), 'Buy', font=rub(62, 600), fill=(10, 40, 22), anchor='mm')
    # the buy sheet slides up over a dimmed screen, then away
    sy = H
    if T_BUY + 0.1 <= tu < T_TOAST: sy = lerp(H, SHEET_Y, ease((tu - T_BUY - 0.1) / 0.4))
    if T_TOAST <= tu < T_TOAST + 0.38: sy = lerp(SHEET_Y, H, ease((tu - T_TOAST) / 0.38))
    if sy < H:
        dim = 0.6 * (1 - (sy - SHEET_Y) / (H - SHEET_Y)); im = Image.blend(im, Image.new('RGB', im.size, (0, 0, 0)), dim); d = ImageDraw.Draw(im); y = sy
        d.rounded_rectangle((0, y, W, H + 80), 48, fill=CARD); d.rounded_rectangle((W / 2 - 46, y + 22, W / 2 + 46, y + 30), 4, fill=(80, 80, 86))
        d.rounded_rectangle((48, y + 70, 1032, y + 160), 28, fill=(14, 14, 15)); d.rounded_rectangle((54, y + 76, 540, y + 154), 24, fill=GRN); d.text((297, y + 115), 'Buy', font=rub(46, 600), fill=(10, 40, 22), anchor='mm'); d.text((786, y + 115), 'Sell', font=rub(46, 600), fill=AXIS, anchor='mm')
        d.rounded_rectangle((48, y + 210, 1032, y + 370), 30, fill=(9, 9, 9), outline=EDGE, width=3)
        amt = '5' if tu >= T_CHIP + 0.1 else '0'; d.text((90, y + 290), amt, font=rub(100, 600), fill=WHITE if amt == '5' else (90, 90, 96), anchor='lm'); d.text((990, y + 290), 'SOL', font=rub(50, 600), fill=AXIS, anchor='rm')
        for k, (lab, cx) in enumerate((('0.1', 190), ('0.5', 420), ('1', 650), ('5', 880))):
            on = (k == 3 and tu >= T_CHIP + 0.1); d.rounded_rectangle((cx - 100, y + 410, cx + 100, y + 490), 26, fill=(20, 60, 34) if on else (36, 36, 40), outline=GRN if on else None, width=4 if on else 0)
            d.text((cx, y + 450), lab, font=rub(44, 600), fill=GRN if on else WHITE, anchor='mm')
        pr = T_CONF <= tu < T_CONF + 0.12; sh = 6 if pr else 0
        d.rounded_rectangle((48 + sh, y + 560 + sh, 1032 - sh, y + 720 - sh), 44, fill=(108, 205, 148) if pr else MINT)
        if T_SPIN1 <= tu < T_TOAST:
            a = (tu - T_SPIN1) * 14; d.arc((540 - 46, y + 640 - 46, 540 + 46, y + 640 + 46), math.degrees(a), math.degrees(a) + 250, fill=(10, 40, 22), width=12)
        else: d.text((540, y + 640), 'Buy', font=rub(66, 600), fill=(10, 40, 22), anchor='mm')
    # toast
    if T_TOAST <= tu < 3.45:
        k = ease((tu - T_TOAST) / 0.25) * (1 - ease((tu - 3.1) / 0.3)); ty = Y(540) - 60 * (1 - k)
        if k > 0.02: d.rounded_rectangle((200, ty - 54, 880, ty + 54), 54, fill=(24, 40, 28), outline=GRN, width=3); d.text((560, ty), 'Buy order placed', font=rub(46, 600), fill=GRN, anchor='mm'); d.line((326, ty, 342, ty + 16, 372, ty - 16), fill=GRN, width=7)
    im = tap_ring(im, BUY_XY[0], BUY_XY[1], T_BUY, tu); im = tap_ring(im, CHIP_XY[0], CHIP_XY[1], T_CHIP, tu); im = tap_ring(im, CONF_XY[0], CONF_XY[1], T_CONF, tu)
    im = im.convert('RGBA')
    if tu > 3.0:
        k = ease((tu - 3.0) / 0.4); im = Image.alpha_composite(im, Image.new('RGBA', (W, H), (60, 255, 130, int(150 * k))))
    if tu > T_SWAP:
        k = min(1.0, (tu - T_SWAP) / 0.25); im = Image.alpha_composite(im, Image.new('RGBA', (W, H), (255, 255, 255, int(235 * (1 - k) + 25 * k))))
    if T_P0 < tu < T_SWAP:                                         # the UI can't take it: it shakes
        s = (tu - T_P0) / (T_SWAP - T_P0); dx = int(math.sin(tu * 90) * 14 * s); dy = int(math.cos(tu * 77) * 10 * s); im = im.transform(im.size, Image.AFFINE, (1, 0, dx, 0, 1, dy))
    return im.convert('RGB')
def monitor(path, seed, bear, w=1920, h=1080):
    r = random.Random(seed); im = Image.new('RGB', (w, h), (9, 9, 9)); d = ImageDraw.Draw(im); p = 100.0
    for k in range(0, h, 120): d.line((0, k, w, k), fill=(26, 26, 30), width=2)
    xs = []
    for i in range(46):
        o_ = p; c_ = p + r.gauss(-1.2 if bear else 1.2, 6); xs.append((o_, c_, max(o_, c_) + abs(r.gauss(0, 3)), min(o_, c_) - abs(r.gauss(0, 3)))); p = c_
    lo = min(x[3] for x in xs); hi = max(x[2] for x in xs)
    for i, (o_, c_, h_, l_) in enumerate(xs):
        x = 80 + i * 38; yy = lambda v: 980 - (v - lo) / (hi - lo) * 860; col = GRN if c_ >= o_ else RED
        d.line((x, yy(h_), x, yy(l_)), fill=col, width=4); d.rectangle((x - 12, yy(max(o_, c_)), x + 12, yy(min(o_, c_)) + 3), fill=col)
    d.text((70, 30), 'IGS / SOL   ' + ('-18.4%' if bear else '+312%'), font=rub(70, 700), fill=RED if bear else GRN); im.save(path)
if len(sys.argv) > 2 and sys.argv[2] == 'monitors':
    for k in range(3): monitor(os.path.join(OUT, f'mon{k}.png'), 40 + k, k == 1)
    sys.exit(0)
lo, hi = axis(T_SWAP); oc = last_candle(T_SWAP)
info = dict(w=W, h=H, x=XL, y_base=yof(BASE, lo, hi), y_top=yof(oc[1], lo, hi), wpx=oc[4], tend=T_END, t_swap=T_SWAP, taps=[[T_BUY, BUY_XY[0], BUY_XY[1]], [T_CHIP, CHIP_XY[0], CHIP_XY[1]], [T_CONF, CONF_XY[0], CONF_XY[1]]])
json.dump(info, open(os.path.join(OUT, 'ui.json'), 'w'))
first = int(sys.argv[2]) if len(sys.argv) > 2 else 1; last = int(sys.argv[3]) if len(sys.argv) > 3 else int(T_END * FPS)
for n in range(first, last + 1): screen((n - 1) / FPS).save(os.path.join(OUT, f'u_{n:04d}.png'))
print('UI-DONE', info)
