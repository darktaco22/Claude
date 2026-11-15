"""Textures for "DEPLOYED": stencil labels and the states of the hold's monitor (the Thumb's game screen).

    python3 textures.py CARDS_DIR OUT_DIR

The monitor shows the game's own card art, the purple Copium bar (colours from the game's stylesheet) and a big
pink thumb. Each state is one PNG: screen_<name>.png.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', 'assets', 'lilita.ttf')
W, H = 1056, 636
INK = (20, 10, 39)
COP, COP_HI, COP_EMPTY = (178, 80, 246), (217, 166, 255), (44, 21, 84)
HAND = [('lmao', 4), ('airdrop', 3), ('chillhouse', 5), ('cupsey', 4)]


def font(size):
    return ImageFont.truetype(FONT, size)


def text(draw, xy, string, size, fill=(255, 255, 255), anchor='mm', stroke=4):
    draw.text(xy, string, font=font(size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=INK)


def stencil(path, string, size=(1024, 256), color=(235, 225, 190, 235), font_size=150, bg=None):
    image = Image.new('RGBA', size, bg or (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((size[0] // 2, size[1] // 2), string, font=font(font_size), fill=color, anchor='mm')
    image.save(path)


def thumb(image, x, y, press=False):
    """A big pink thumb coming in from the bottom right."""
    layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    pink, dark = (246, 170, 160), (190, 105, 105)
    width = 150 if not press else 160
    draw.rounded_rectangle((x - width // 2, y - 40, x + width // 2, y + 520), 75, fill=pink, outline=dark, width=6)
    draw.rounded_rectangle((x - 46, y - 22, x + 46, y + 70), 34, fill=(255, 214, 205), outline=dark, width=4)   # nail
    for k in range(2):
        draw.arc((x - 50, y + 150 + k * 26, x + 50, y + 190 + k * 26), 20, 160, fill=dark, width=4)             # knuckle
    layer = layer.rotate(-18, center=(x, y + 200), resample=Image.BICUBIC)
    shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 110), (14, 14), layer.split()[3])
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    image.alpha_composite(layer)


def screen(cards_dir, copium, picked=None, dead=(), gone=(), title='ARENA 2  ·  BACKYARD BBQ', clock='2:41',
           message=None, message_color=(255, 255, 255), thumb_at=None, flash=False, only=None, big=None, sub=None):
    image = Image.new('RGBA', (W, H), (42, 16, 112, 255))
    draw = ImageDraw.Draw(image)
    for y in range(H):                                            # soft vertical gradient
        shade = int(30 * y / H)
        draw.line((0, y, W, y), fill=(42 - shade // 2, 16, 112 - shade))
    draw.rectangle((0, 0, W, 64), fill=INK)
    text(draw, (24, 32), title, 30, anchor='lm', stroke=0, fill=(255, 210, 90))
    text(draw, (W - 24, 32), clock, 34, anchor='rm', stroke=0)

    if big:
        text(draw, (W // 2, 230), big, 150, fill=message_color, stroke=10)
        if sub:
            text(draw, (W // 2, 350), sub, 54, stroke=6)
    elif message:
        text(draw, (W // 2, 150), message, 64, fill=message_color, stroke=7)

    if not big:
        card_w, card_h, gap = 168, 210, 26
        hand = [item for item in HAND if item[0] not in gone]
        if only:
            hand = [item for item in HAND if item[0] == only]
        x0 = (W - (len(hand) * card_w + (len(hand) - 1) * gap)) // 2
        for index, (uid, cost) in enumerate(hand):
            x = x0 + index * (card_w + gap)
            y = 250 - (26 if uid == picked else 0)
            art = Image.open(os.path.join(cards_dir, uid + '.webp')).convert('RGBA').resize((card_w, card_h), Image.LANCZOS)
            if uid in dead:
                art = art.convert('LA').convert('RGBA')
                art = Image.eval(art, lambda value: int(value * 0.55))
            mask = Image.new('L', (card_w, card_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w, card_h), 16, fill=255)
            image.paste(art, (x, y), mask)
            outline = (255, 226, 90) if uid == picked else INK
            draw.rounded_rectangle((x - 3, y - 3, x + card_w + 3, y + card_h + 3), 18, outline=outline, width=7 if uid == picked else 5)
            draw.ellipse((x - 16, y - 16, x + 40, y + 40), fill=COP, outline=INK, width=4)
            text(draw, (x + 12, y + 12), str(cost), 34, stroke=3)
            if uid in dead:
                draw.line((x + 20, y + 20, x + card_w - 20, y + card_h - 20), fill=(255, 60, 60), width=16)
                draw.line((x + card_w - 20, y + 20, x + 20, y + card_h - 20), fill=(255, 60, 60), width=16)

        # copium bar
        bar_x, bar_y, bar_w, bar_h = 150, 520, 780, 60
        draw.rounded_rectangle((bar_x - 8, bar_y - 8, bar_x + bar_w + 8, bar_y + bar_h + 8), 18, fill=INK)
        seg = bar_w / 10
        for k in range(10):
            lit = k < copium
            color = (COP_HI if flash else COP) if lit else COP_EMPTY
            draw.rounded_rectangle((bar_x + k * seg + 4, bar_y, bar_x + (k + 1) * seg - 4, bar_y + bar_h), 10, fill=color)
            if lit:
                draw.rounded_rectangle((bar_x + k * seg + 10, bar_y + 6, bar_x + (k + 1) * seg - 10, bar_y + 22), 6, fill=COP_HI)
        can = Image.open(os.path.join(cards_dir, 'ui_sm_icon_copium.webp')).convert('RGBA').resize((92, 114), Image.LANCZOS)
        image.alpha_composite(can, (44, 492))
        text(draw, (90, 560), str(copium), 46, stroke=5)
    if thumb_at:
        thumb(image, *thumb_at, press=picked is not None)
    return image.convert('RGB')


def main(cards_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stencil(os.path.join(out_dir, 'deck_one.png'), 'DECK ONE', (1024, 256))
    stencil(os.path.join(out_dir, 'copium.png'), 'COPIUM', (640, 200), (255, 240, 255, 240), 130)
    stencil(os.path.join(out_dir, 'airdrop.png'), 'AIRDROP', (512, 512), (40, 28, 16, 255), 104, bg=(150, 108, 62, 255))
    slots = {'lmao': 342, 'airdrop': 536, 'chillhouse': 730, 'cupsey': 924}
    states = {
        'idle': dict(copium=2, thumb_at=(860, 420)),
        'lmao': dict(copium=4, picked='lmao', thumb_at=(300, 430), message='COPIUM: 4'),
        'lmao_dead': dict(copium=0, dead=('lmao',), thumb_at=(860, 440), message='LMAO ELIMINATED', message_color=(255, 90, 90), clock='2:33'),
        'airdrop': dict(copium=3, picked='airdrop', gone=('lmao',), thumb_at=(400, 430), message='AIRDROP', clock='2:10'),
        'tower': dict(copium=1, gone=('lmao', 'airdrop'), message='LEFT TOWER DESTROYED', message_color=(255, 90, 90), clock='1:32',
                      thumb_at=(900, 470)),
        'wagmi': dict(copium=5, gone=('lmao', 'airdrop'), message='EMOTE SENT: WAGMI', message_color=(255, 226, 90), clock='1:20',
                      thumb_at=(900, 200)),
        'full_a': dict(copium=10, gone=('lmao', 'airdrop'), message='COPIUM IS FULL!', message_color=(217, 166, 255), clock='0:58',
                       thumb_at=(900, 470)),
        'full_b': dict(copium=10, gone=('lmao', 'airdrop'), message='COPIUM IS FULL!', message_color=(255, 255, 255), clock='0:58',
                       thumb_at=(900, 470), flash=True),
        'last': dict(copium=4, only='cupsey', picked='cupsey', message='LAST CARD', clock='0:30', thumb_at=(560, 440)),
        'victory': dict(copium=0, big='VICTORY!', message_color=(255, 226, 90), sub='paperhands420 left the match', clock='0:21'),
        'clout': dict(copium=0, big='+28 CLOUT', message_color=(120, 255, 140), sub='NEW ARENA: STRIP MALL LOT',
                      title='ARENA 3  ·  STRIP MALL LOT', clock=''),
        'next': dict(copium=0, big='NEXT MATCH', message_color=(255, 90, 90), sub='in 3 ... 2 ...', title='ARENA 3  ·  STRIP MALL LOT', clock=''),
    }
    for name, options in states.items():
        screen(cards_dir, **options).save(os.path.join(out_dir, f'screen_{name}.png'))
    # the emote bubble that pops over the king tower
    bubble = Image.new('RGBA', (900, 560), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubble)
    draw.rounded_rectangle((20, 20, 880, 420), 90, fill=(255, 255, 255, 255), outline=INK, width=16)
    draw.polygon(((300, 410), (420, 410), (250, 545)), fill=(255, 255, 255, 255), outline=INK)
    draw.line((300, 412, 420, 412), fill=(255, 255, 255, 255), width=20)
    draw.line((300, 410, 250, 545), fill=INK, width=14)
    draw.line((420, 410, 250, 545), fill=INK, width=14)
    draw.text((450, 215), 'WAGMI', font=font(230), fill=(255, 190, 40), anchor='mm', stroke_width=14, stroke_fill=INK)
    bubble.save(os.path.join(out_dir, 'bubble_wagmi.png'))
    # disconnect icon for the frozen opponents
    icon = Image.new('RGBA', (400, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    draw.ellipse((10, 10, 390, 390), fill=(30, 20, 50, 235), outline=(255, 80, 80), width=18)
    for k, radius in enumerate((150, 105, 60)):
        draw.arc((200 - radius, 250 - radius, 200 + radius, 250 + radius), 225, 315, fill=(255, 255, 255), width=24)
    draw.ellipse((178, 232, 222, 276), fill=(255, 255, 255))
    draw.line((90, 90, 310, 310), fill=(255, 80, 80), width=30)
    icon.save(os.path.join(out_dir, 'disconnect.png'))
    print('TEXTURES', len(states) + 5)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
