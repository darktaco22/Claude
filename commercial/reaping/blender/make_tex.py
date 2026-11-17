"""PIL textures for the Blender sets (banners, flags, screen, slips, signage). usage: python3 make_tex.py OUTDIR"""
import sys, os, math, random
sys.path.insert(0, '/root/road/reap'); sys.path.insert(0, '/root/road/who')
from PIL import Image, ImageDraw, ImageFilter
import rgfx
F = rgfx.F; OUT = sys.argv[1] if len(sys.argv) > 1 else '/root/reap3d/tex'; os.makedirs(OUT, exist_ok=True)
GOLD = (222, 178, 74); RED = (120, 14, 20); BLK = (14, 12, 14)
def fabric(w, h, base, seed=1):
    random.seed(seed); im = Image.new('RGB', (w, h), base); px = im.load()
    n = Image.effect_noise((w, h), 18).convert('L'); im = Image.composite(Image.new('RGB', (w, h), tuple(min(255, c + 14) for c in base)), im, n)
    d = ImageDraw.Draw(im)
    for x in range(0, w, 3): d.line((x, 0, x, h), fill=tuple(max(0, c - 6) for c in base))
    return im
def gold_txt(im, xy, t, font):
    d = ImageDraw.Draw(im); d.text((xy[0] + 3, xy[1] + 4), t, font=font, fill=(60, 40, 10), anchor='mm'); d.text(xy, t, font=font, fill=GOLD, anchor='mm')
def crest(d, cx, cy, s, col=GOLD):
    """ringed crown monogram"""
    d.ellipse((cx - s, cy - s, cx + s, cy + s), outline=col, width=max(4, int(s * 0.07)))
    d.ellipse((cx - s * 0.86, cy - s * 0.86, cx + s * 0.86, cy + s * 0.86), outline=col, width=max(2, int(s * 0.025)))
    w = s * 0.42; top = cy - s * 0.62; base = cy - s * 0.3
    d.polygon([(cx - w, base), (cx - w, top + s * 0.06), (cx - w * 0.5, top + s * 0.2), (cx, top), (cx + w * 0.5, top + s * 0.2), (cx + w, top + s * 0.06), (cx + w, base)], fill=col)
    for k in (-1, 0, 1): r = s * 0.05; x = cx + k * w * (1 if k else 0); y = top + (s * 0.06 if k else 0); d.ellipse((x - r, y - r - r, x + r, y + r - r), fill=col)
    d.text((cx, cy + s * 0.2), 'M', font=F('serif', int(s * 0.85)), fill=col, anchor='mm')
# main banner 3:1 (6.6 x 2.2 m)
im = fabric(3000, 1000, BLK); d = ImageDraw.Draw(im)
d.rectangle((40, 40, 2960, 960), outline=GOLD, width=14); d.rectangle((70, 70, 2930, 930), outline=GOLD, width=4)
crest(d, 250, 500, 170); crest(d, 2750, 500, 170)
gold_txt(im, (1500, 250), 'THE 1ST ANNUAL', F('serif', 120)); gold_txt(im, (1500, 520), 'MEME REAPING', F('serif', 290))
gold_txt(im, (1500, 800), 'STRIP MALL LOT  ·  ATTENDANCE MANDATORY', F('serif', 78)); im.save(OUT + '/banner.jpg', quality=93)
# hanging flag 1:4
im = fabric(700, 2800, RED, 2); d = ImageDraw.Draw(im); d.rectangle((0, 0, 700, 2800), outline=GOLD, width=26)
for x in (60, 640): d.line((x, 0, x, 2800), fill=GOLD, width=8)
crest(d, 350, 880, 270); d.text((350, 1400), 'MEME', font=F('serif', 120), fill=GOLD, anchor='mm'); d.text((350, 1540), 'ROYALE', font=F('serif', 104), fill=GOLD, anchor='mm')
d.polygon([(0, 2550), (350, 2800), (700, 2550), (700, 2800), (0, 2800)], fill=(0, 0, 0)); im.save(OUT + '/flag.png')
# jumbotron 16:9
im = Image.new('RGB', (1920, 1080), (4, 4, 8)); d = ImageDraw.Draw(im)
d.text((960, 300), 'L I V E', font=F('bold', 60), fill=(230, 40, 40), anchor='mm')
gold_txt(im, (960, 520), 'THE REAPING', F('serif', 230)); d.text((960, 760), 'MAY THE COPIUM BE EVER IN YOUR FAVOR', font=F('serif', 64), fill=(220, 210, 190), anchor='mm')
for y in range(0, 1080, 4): d.line((0, y, 1920, y), fill=(0, 0, 0))
im.save(OUT + '/screen.jpg', quality=93)
# name slip (folded paper, 2:1)
im = Image.new('RGB', (1200, 600), (244, 238, 222)); n = Image.effect_noise((1200, 600), 10).convert('L'); im = Image.composite(Image.new('RGB', (1200, 600), (232, 225, 206)), im, n)
d = ImageDraw.Draw(im); d.line((0, 300, 1200, 300), fill=(205, 196, 172), width=4)
d.text((600, 310), 'WOJAK', font=F('serif', 250), fill=(26, 22, 20), anchor='mm'); im.save(OUT + '/slip_wojak.jpg', quality=93)
im2 = Image.new('RGB', (1200, 600), (244, 238, 222)); im2 = Image.composite(Image.new('RGB', (1200, 600), (232, 225, 206)), im2, n); ImageDraw.Draw(im2).line((0, 300, 1200, 300), fill=(205, 196, 172), width=4); im2.save(OUT + '/slip_blank.jpg')
# lectern plaque
im = Image.new('RGB', (800, 800), (110, 18, 22)); d = ImageDraw.Draw(im); crest(d, 400, 400, 340); im.save(OUT + '/plaque.jpg')
# stage-side sign
im = fabric(1600, 600, (20, 20, 24), 3); d = ImageDraw.Draw(im); d.rectangle((20, 20, 1580, 580), outline=GOLD, width=10)
gold_txt(im, (800, 210), 'TRIBUTES', F('serif', 150)); d.text((800, 420), 'PLEASE REMAIN CALM AND IN LINE', font=F('serif', 64), fill=(220, 210, 190), anchor='mm'); im.save(OUT + '/sign.jpg')
print('textures ok', sorted(os.listdir(OUT)))
