"""THE REAPING graphics (1080x1920 RGBA). Reuses the WHO SOLD? font set."""
import sys, math, random
sys.path.insert(0, '/root/road/who'); import gfx as WG
from PIL import Image, ImageDraw, ImageFilter
F, new, wrap = WG.F, WG.new, WG.wrap
W, H = 1080, 1920; GOLD = (217, 169, 58, 255); G2 = (255, 214, 120, 255)
def gold_text(im, xy, text, font, anchor='mm', glow=True):
    """gold gradient text with a soft glow"""
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).text(xy, text, font=font, fill=255, anchor=anchor)
    if glow: im.alpha_composite(Image.merge('RGBA', [Image.new('L', im.size, 255), Image.new('L', im.size, 190), Image.new('L', im.size, 80), m.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.55))]))
    grad = Image.new('RGBA', im.size); gd = ImageDraw.Draw(grad); bb = m.getbbox() or (0, 0, W, H)
    for y in range(bb[1], bb[3] + 1):
        k = (y - bb[1]) / max(1, bb[3] - bb[1]); c = [int(G2[i] * (1 - k) + (150, 100, 30)[i] * k) for i in range(3)]; gd.line((0, y, W, y), fill=tuple(c) + (255,))
    im.paste(grad, (0, 0), m)
def title(path):
    im = new((0, 0, 0, 255)); d = ImageDraw.Draw(im)
    d.text((540, 760), 'M E M E    R O Y A L E', font=F('med', 40), fill=(200, 196, 186, 255), anchor='mm')
    gold_text(im, (540, 930), 'THE', F('serif', 120)); gold_text(im, (540, 1090), 'REAPING', F('serif', 210))
    d = ImageDraw.Draw(im); d.line((300, 1225, 780, 1225), fill=GOLD, width=4)
    d.text((540, 1290), 'THIS NOVEMBER, NOBODY VOLUNTEERS.', font=F('med', 34), fill=(200, 196, 186, 255), anchor='mm'); im.save(path); return path
def word(text, path, sub=None, y=960):
    """trailer word card: transparent, serif gold over a dark band"""
    im = new(); band = new(); ImageDraw.Draw(band).rectangle((0, y - 190, W, y + 190), fill=(0, 0, 0, 170)); im.alpha_composite(band.filter(ImageFilter.GaussianBlur(40)))
    gold_text(im, (540, y), text, F('serif', 150))
    if sub: ImageDraw.Draw(im).text((540, y + 130), sub, font=F('med', 36), fill=(230, 226, 214, 255), anchor='mm')
    im.save(path); return path
def black_word(text, path):
    im = new((0, 0, 0, 255)); gold_text(im, (540, 960), text, F('serif', 150)); im.save(path); return path
def tagline(path):
    im = new((0, 0, 0, 255)); d = ImageDraw.Draw(im)
    for i, l in enumerate(['MAY THE COPIUM', 'BE EVER IN', 'YOUR FAVOR.']): gold_text(im, (540, 790 + i * 170), l, F('serif', 120))
    im.save(path); return path
def context_tag(path):
    im = new(); d = ImageDraw.Draw(im); t = 'THE 1ST ANNUAL MEME REAPING  ·  STRIP MALL LOT'; f = F('bold', 30); w = d.textlength(t, font=f)
    d.rectangle((540 - w / 2 - 28, 150, 540 + w / 2 + 28, 212), fill=(0, 0, 0, 175)); d.rectangle((540 - w / 2 - 28, 208, 540 + w / 2 + 28, 212), fill=GOLD)
    d.text((540, 181), t, font=f, fill=(255, 255, 255, 240), anchor='mm'); im.save(path); return path
def chyron(path):
    im = new(); d = ImageDraw.Draw(im); y = 1240
    d.rectangle((50, y, 1030, y + 150), fill=(14, 10, 40, 235)); d.rectangle((50, y, 66, y + 150), fill=(255, 196, 40, 255))
    d.text((96, y + 50), 'THE POPCAT HOUR', font=F('bebas', 92), fill=(255, 255, 255, 255), anchor='lm')
    d.text((98, y + 116), 'Pre-Games interview  ·  Tribute: Wojak', font=F('med', 34), fill=(210, 206, 235, 255), anchor='lm')
    d.rounded_rectangle((860, y + 24, 1004, y + 78), radius=10, fill=(214, 30, 38, 255)); d.ellipse((876, y + 42, 894, y + 60), fill=(255, 255, 255, 255)); d.text((950, y + 51), 'LIVE', font=F('bold', 30), fill=(255, 255, 255, 255), anchor='mm')
    im.save(path); return path
def sky(portrait, name, path, seed=1):
    """the fallen tribute's face in the night sky (the cannon card)"""
    random.seed(seed); im = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(im)
    for y in range(H): k = y / H; d.line((0, y, W, y), fill=(int(6 + 18 * k), int(8 + 20 * k), int(22 + 40 * k), 255))
    for _ in range(420): x, y, r = random.randint(0, W), random.randint(0, H), random.choice([1, 1, 1, 2, 2, 3]); a = random.randint(90, 255); d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))
    src = Image.open(portrait).convert('RGB'); s = min(src.size); src = src.crop(((src.width - s) // 2, int(src.height * 0.1), (src.width - s) // 2 + s, int(src.height * 0.1) + s)).resize((620, 620))
    src = Image.blend(src, Image.new('RGB', src.size, (120, 150, 210)), 0.35).convert('RGBA')
    mk = Image.new('L', (620, 620), 0); ImageDraw.Draw(mk).ellipse((0, 0, 619, 619), fill=255); mk = mk.filter(ImageFilter.GaussianBlur(24))
    src.putalpha(mk.point(lambda v: int(v * 0.78))); glow = Image.new('RGBA', (W, H)); ImageDraw.Draw(glow).ellipse((540 - 380, 760 - 380, 540 + 380, 760 + 380), fill=(140, 170, 255, 70)); im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(80)))
    im.alpha_composite(src, (540 - 310, 760 - 310)); d = ImageDraw.Draw(im)
    gold_text(im, (540, 1200), name, F('serif', 110)); ImageDraw.Draw(im).text((540, 1300), 'ELIMINATED', font=F('med', 38), fill=(200, 206, 230, 255), anchor='mm'); im.save(path); return path
def endcard(path, logo='/home/user/Claude/commercial/kid/logo.png'):
    im = new((4, 4, 8, 255)); lg = Image.open(logo).convert('RGBA'); lg = lg.resize((640, int(640 * lg.height / lg.width))); im.alpha_composite(lg, (220, 330)); d = ImageDraw.Draw(im)
    gold_text(im, (540, 1080), 'IN ARENAS NOW', F('serif', 104)); d = ImageDraw.Draw(im)
    d.text((540, 1210), 'FREE ON PC + MOBILE', font=F('bold', 48), fill=(240, 240, 244, 255), anchor='mm')
    d.text((540, 1300), 'memeroyale.imaginestudio.fun', font=F('med', 42), fill=(220, 220, 228, 255), anchor='mm'); d.text((540, 1366), '@MemeRoyaleGames', font=F('med', 40), fill=GOLD, anchor='mm')
    d.text((540, 1740), 'No tributes volunteered in the making of this film.', font=F('type', 30), fill=(140, 140, 148, 255), anchor='mm'); im.save(path); return path
caption = WG.caption
if __name__ == '__main__':
    G = '/root/road/reap/g/'
    title(G + 'title.png'); word('NINE MEMES.', G + 'w_nine.png'); word('ONE ARENA.', G + 'w_arena.png'); word('TEN COPIUM.', G + 'w_copium.png'); tagline(G + 'tag.png'); context_tag(G + 'ctx.png'); chyron(G + 'chy.png')
    sky('/root/road/who/g/still_troll.png', 'TROLL', G + 'sky_t.png'); endcard(G + 'end.png')
    S = Image.new('RGB', (6 * 270, 480), (60, 80, 100))
    for i, n in enumerate(['title', 'w_nine', 'tag', 'ctx', 'chy', 'sky_t']):
        a = Image.open(G + n + '.png'); bg = Image.new('RGBA', a.size, (70, 90, 110, 255)); bg.alpha_composite(a); S.paste(bg.convert('RGB').resize((270, 480)), (i * 270, 0))
    S.save('/root/road/reap/gsheet.png')
