"""The game's own HUD, redrawn from a real phone screenshot (reference/user_screenshot_moon.png, 924 x 1999).

Everything is drawn on an RGBA image whose width is CW; k = CW / 924 scales the screenshot's pixel sizes. Used by monitor.py (the
Thumb's screen on the ship), finish.py (the phone shots and the overlays on the cinematic arena shots).
Layout from the screenshot: name pill top left, TIME LEFT pill top right, red/green W badges on the right river bank, tower health
pills (red enemy, green ours), an emote button above the tray, and the tray: a green-bordered panel with NEXT + a small card on the
left, four cards (hex cost badge top left, name under the art) and the purple Copium bottle with a 10-segment bar below.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', 'assets', 'lilita.ttf')
INK = (18, 12, 36)
PANEL = (22, 20, 44)
GREEN = (74, 200, 96)
RED = (234, 64, 96)
PURPLE, PURPLE_HI, PURPLE_EMPTY = (178, 96, 246), (214, 168, 255), (40, 26, 84)
BADGE = (122, 70, 214)
COST = {'lmao': 4, 'airdrop': 3, 'chillhouse': 5, 'cupsey': 4, 'ket': 3, 'chillguy': 3, 'dope': 2, 'pudgy': 3, 'troll': 2, 'bonk': 3}
NAMES = {'lmao': 'LMAO', 'airdrop': 'AIRDROP', 'chillhouse': 'CHILLHOUSE', 'cupsey': 'CUPSEY', 'ket': 'KET', 'chillguy': 'CHILL GUY', 'dope': 'DOPE',
         'pudgy': 'PUDGY', 'troll': 'TROLL', 'bonk': 'BONK', 'neet': 'NEET', 'apu': 'APU', 'farter': 'FARTER', 'zcat': 'ZCAT', 'popcat': 'POPCAT'}
SPELLS = {'airdrop'}
_fonts, _art = {}, {}


def font(size):
    size = max(6, int(size))
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def text(d, xy, string, size, fill=(255, 255, 255, 255), anchor='mm', stroke=0, stroke_fill=INK + (255,)):
    d.text(xy, string, font=font(size), fill=fill, anchor=anchor, stroke_width=int(stroke), stroke_fill=stroke_fill)


def card_art(cards_dir, uid, w, h):
    key = (uid, w, h)
    if key not in _art:
        path = os.path.join(cards_dir, uid + '.webp')
        art = Image.open(path).convert('RGBA').resize((w, h), Image.LANCZOS)
        mask = Image.new('L', (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), max(5, w // 11), fill=255)
        art.putalpha(mask)
        _art[key] = art
    return _art[key]


def hexagon(d, cx, cy, r, string, k):
    pts = [(cx + r * math.cos(math.radians(60 * i + 30)), cy + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.polygon(pts, fill=BADGE + (255,), outline=INK + (255,))
    d.line(pts + [pts[0]], fill=INK + (255,), width=max(2, int(3 * k)))
    inner = [(cx + r * 0.82 * math.cos(math.radians(60 * i + 30)), cy + r * 0.82 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.line(inner + [inner[0]], fill=(168, 120, 255, 255), width=max(1, int(2 * k)))
    text(d, (cx, cy + 1), string, r * 1.15, stroke=max(1, 2 * k))


def clock_text(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60}:{seconds % 60:02d}'


def tray_box(cw, ch, k):
    """(x0, y0, x1, y1) of the tray in a canvas cw x ch."""
    return (14 * k, ch - 390 * k, cw - 14 * k, ch - 32 * k)


def tray(im, state, cards_dir, k, drag=None, bottom=None):
    """The Thumb's tray. `state`: hand (4 uids), next (uid), copium (float). `drag` = (slot, x, y): that card follows the finger."""
    cw, ch = im.size
    x0, y0, x1, y1 = tray_box(cw, ch, k)
    if bottom is not None:
        y1 = bottom
        y0 = y1 - 358 * k
    d = ImageDraw.Draw(im, 'RGBA')
    d.rounded_rectangle((x0, y0, x1, y1), int(30 * k), fill=PANEL + (240,), outline=GREEN + (255,), width=max(3, int(5 * k)))
    d.rounded_rectangle((x0 + 8 * k, y0 + 8 * k, x1 - 8 * k, y1 - 8 * k), int(24 * k), outline=(14, 70, 40, 255), width=max(1, int(2 * k)))
    # NEXT
    nw, nh = int(86 * k), int(107 * k)
    nx, ny = int(x0 + 48 * k), int(y0 + 81 * k)
    text(d, (x0 + 90 * k, y0 + 52 * k), 'NEXT', 25 * k, (230, 230, 245, 255), stroke=2 * k)
    im.alpha_composite(card_art(cards_dir, state['next'], nw, nh), (nx, ny))
    d.rounded_rectangle((nx, ny, nx + nw, ny + nh), max(5, nw // 11), outline=(240, 240, 250, 255), width=max(2, int(3 * k)))
    hexagon(d, nx + 12 * k, ny + 12 * k, 21 * k, str(COST.get(state['next'], 3)), k)
    # the four cards
    cwid, chei = int(153 * k), int(191 * k)
    for index, uid in enumerate(state['hand']):
        cx = int(x0 + 183 * k + index * 177 * k)
        cy = int(y0 + 25 * k)
        affordable = state['copium'] >= COST.get(uid, 3)
        picked = drag is not None and drag[0] == index
        if picked:                                       # the card is in the finger: a hole stays in the tray
            d.rounded_rectangle((cx, cy, cx + cwid, cy + chei), max(5, cwid // 11), fill=(10, 8, 24, 255))
            continue
        lift = int(14 * k) if (state.get('press') == index) else 0
        art = card_art(cards_dir, uid, cwid, chei).copy()
        if not affordable:
            shade = Image.new('RGBA', art.size, (12, 10, 30, 125))
            art = Image.alpha_composite(art, Image.composite(shade, Image.new('RGBA', art.size, (0, 0, 0, 0)), art.getchannel('A')))
        im.alpha_composite(art, (cx, cy - lift))
        frame = (90, 214, 255, 255) if uid in SPELLS else ((245, 245, 255, 255) if affordable else (120, 110, 150, 255))
        d.rounded_rectangle((cx, cy - lift, cx + cwid, cy - lift + chei), max(5, cwid // 11), outline=frame, width=max(2, int(4 * k)))
        text(d, (cx + cwid / 2, cy - lift + chei - 20 * k), NAMES.get(uid, uid.upper()), 22 * k, (255, 255, 255, 255) if affordable else (200, 195, 220, 255), stroke=3 * k)
        hexagon(d, cx + 12 * k, cy - lift + 14 * k, 25 * k, str(COST.get(uid, 3)), k)
    # copium: the bottle, the number, ten segments
    bx0, bx1, by0, by1 = x0 + 132 * k, x1 - 40 * k, y0 + 262 * k, y0 + 306 * k
    d.rounded_rectangle((bx0 - 5 * k, by0 - 5 * k, bx1 + 5 * k, by1 + 5 * k), int(14 * k), fill=(26, 20, 60, 255), outline=(98, 70, 190, 255), width=max(2, int(3 * k)))
    seg = (bx1 - bx0) / 10
    for index in range(10):
        part = max(0.0, min(1.0, state['copium'] - index))
        left, right = bx0 + index * seg + 3 * k, bx0 + (index + 1) * seg - 3 * k
        d.rounded_rectangle((left, by0, right, by1), int(8 * k), fill=PURPLE_EMPTY + (255,))
        if part > 0.02:
            d.rounded_rectangle((left, by0, left + (right - left) * part, by1), int(8 * k), fill=(PURPLE_HI if part >= 1 else PURPLE) + (255,))
            d.rounded_rectangle((left + 3 * k, by0 + 4 * k, left + (right - left) * part - 3 * k, by0 + 14 * k), int(4 * k), fill=(240, 220, 255, 140))
    try:
        icon = card_art_icon(cards_dir, int(86 * k), int(106 * k))
        im.alpha_composite(icon, (int(x0 + 24 * k), int(y0 + 238 * k)))
    except OSError:
        pass
    text(d, (x0 + 66 * k, y0 + 285 * k), str(int(state['copium'])), 46 * k, stroke=5 * k)
    # a card in the finger
    if drag is not None:
        slot, gx, gy = drag
        uid = state['hand'][slot]
        big = card_art(cards_dir, uid, int(cwid * 1.12), int(chei * 1.12)).copy()
        big.putalpha(big.getchannel('A').point(lambda v: int(v * 0.92)))
        im.alpha_composite(big, (int(gx - big.width / 2), int(gy - big.height / 2)))
        d = ImageDraw.Draw(im, 'RGBA')
        d.rounded_rectangle((gx - big.width / 2, gy - big.height / 2, gx + big.width / 2, gy + big.height / 2), max(5, cwid // 11), outline=(255, 226, 90, 255), width=max(2, int(4 * k)))
        hexagon(d, gx - big.width / 2 + 12 * k, gy - big.height / 2 + 14 * k, 25 * k, str(COST.get(uid, 3)), k)


def card_art_icon(cards_dir, w, h):
    key = ('copium_icon', w, h)
    if key not in _art:
        _art[key] = Image.open(os.path.join(cards_dir, 'ui_sm_icon_copium.webp')).convert('RGBA').resize((w, h), Image.LANCZOS)
    return _art[key]


def pill(d, box, k, fill=(30, 28, 46, 238), outline=(78, 74, 100, 255)):
    d.rounded_rectangle(box, int(22 * k), fill=fill, outline=outline, width=max(2, int(3 * k)))


def top_pills(im, k, name, trophies, clock_seconds, enemy=True, y=0):
    """Name pill top left (the opponent's name in pink), TIME LEFT pill top right."""
    cw = im.size[0]
    d = ImageDraw.Draw(im, 'RGBA')
    pill(d, (14 * k, y + 14 * k, 228 * k, y + 120 * k), k)
    text(d, (30 * k, y + 50 * k), name, 33 * k, (255, 120, 150, 255) if enemy else (130, 255, 150, 255), 'lm', 3 * k)
    d.ellipse((30 * k, y + 78 * k, 62 * k, y + 106 * k), fill=(255, 196, 60, 255), outline=INK + (255,), width=max(2, int(2 * k)))
    text(d, (76 * k, y + 92 * k), f'{trophies:,}', 33 * k, (255, 205, 80, 255), 'lm', 3 * k)
    pill(d, (cw - 186 * k, y + 14 * k, cw - 14 * k, y + 108 * k), k)
    text(d, (cw - 100 * k, y + 36 * k), 'TIME LEFT', 21 * k, (205, 205, 225, 255), stroke=2 * k)
    text(d, (cw - 100 * k, y + 76 * k), clock_text(clock_seconds), 55 * k, (255, 120, 120, 255) if clock_seconds < 30 else (255, 255, 255, 255), stroke=4 * k)


def w_badges(im, k, ws, y_river):
    """Red (the opponent's) and green (ours) W score badges on the right river bank."""
    cw = im.size[0]
    d = ImageDraw.Draw(im, 'RGBA')
    for team, dy, color in ((1, -78, (226, 54, 70)), (0, 22, (86, 204, 90))):
        cx, cy = cw - 84 * k, y_river + dy * k
        d.rounded_rectangle((cx - 66 * k, cy - 36 * k, cx + 62 * k, cy + 36 * k), int(34 * k), fill=(24, 22, 40, 240), outline=(60, 58, 80, 255), width=max(2, int(3 * k)))
        d.ellipse((cx - 62 * k, cy - 34 * k, cx - 62 * k + 68 * k, cy + 34 * k), fill=color + (255,), outline=INK + (255,), width=max(2, int(3 * k)))
        text(d, (cx - 28 * k, cy + 1), 'W', 40 * k, stroke=3 * k)
        text(d, (cx + 30 * k, cy + 1), str(ws[team]), 42 * k, stroke=3 * k)


def hp_pill(im, cx, cy, k, value, team, alpha=255):
    d = ImageDraw.Draw(im, 'RGBA')
    w, h = 132 * k, 42 * k
    fill = (106, 226, 88) if team == 0 else (238, 70, 100)
    d.rounded_rectangle((cx - w / 2 - 4 * k, cy - h / 2 - 4 * k, cx + w / 2 + 4 * k, cy + h / 2 + 4 * k), int(18 * k), fill=INK + (alpha,))
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), int(15 * k), fill=fill + (alpha,))
    d.rounded_rectangle((cx - w / 2 + 6 * k, cy - h / 2 + 4 * k, cx + w / 2 - 6 * k, cy - h / 2 + 12 * k), int(4 * k), fill=(255, 255, 255, int(alpha * 0.35)))
    text(d, (cx, cy + 1), f'{int(value):,}', 30 * k, (255, 255, 255, alpha), stroke=4 * k)


def emote_button(im, k, x, y):
    d = ImageDraw.Draw(im, 'RGBA')
    d.rounded_rectangle((x, y, x + 92 * k, y + 98 * k), int(26 * k), fill=(24, 22, 38, 240), outline=(66, 64, 88, 255), width=max(2, int(3 * k)))
    cx, cy = x + 46 * k, y + 46 * k
    d.ellipse((cx - 34 * k, cy - 32 * k, cx + 34 * k, cy + 30 * k), fill=(250, 250, 250, 255), outline=INK + (255,), width=max(2, int(3 * k)))
    d.polygon([(cx - 22 * k, cy + 24 * k), (cx - 30 * k, cy + 44 * k), (cx - 4 * k, cy + 28 * k)], fill=(250, 250, 250, 255))
    d.arc((cx - 22 * k, cy - 6 * k, cx + 22 * k, cy + 20 * k), 10, 170, fill=INK + (255,), width=max(2, int(4 * k)))
    for sx in (-13, 13):
        d.ellipse((cx + sx * k - 5 * k, cy - 14 * k, cx + sx * k + 5 * k, cy - 4 * k), fill=INK + (255,))


def popup(im, x, y, string, k, team=0, alpha=255):
    """The name that floats up over a unit when its card is played."""
    d = ImageDraw.Draw(im, 'RGBA')
    color = (255, 150, 190, alpha) if team == 1 else (210, 255, 200, alpha)
    text(d, (x, y), string, 30 * k, color, stroke=5 * k, stroke_fill=INK + (alpha,))
