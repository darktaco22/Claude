# Text overlays for the TikTok cut (1080x1920 PNGs with alpha), in the game's Lilita One font, TikTok caption style:
# white letters with a thick black stroke and a soft shadow, kept inside the safe area (clear of the app's side bar and
# bottom caption area).  Usage: python3 make_overlays.py FONT OUTDIR
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FONT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1920

def text_png(name, lines, size, y, fill=(255, 255, 255), stroke=10, maxw=900, bg=None):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = ImageFont.truetype(FONT, size)
    d = ImageDraw.Draw(im)
    boxes = [d.textbbox((0, 0), l, font=f, stroke_width=stroke) for l in lines]
    lh = int(size * 1.08)
    if bg:   # a solid band behind (the title card look)
        top = y - 30; bot = y + lh * len(lines) + 20
        ImageDraw.Draw(im).rounded_rectangle((60, top, W - 60, bot), 36, fill=bg)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    for i, (l, b) in enumerate(zip(lines, boxes)):
        x = (W - (b[2] - b[0])) // 2
        ds.text((x + 6, y + i * lh + 8), l, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im)
    for i, (l, b) in enumerate(zip(lines, boxes)):
        x = (W - (b[2] - b[0])) // 2
        d.text((x, y + i * lh), l, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
    im.save(os.path.join(OUT, name + ".png"))

# the hook / title, held at the top the whole video (as in the reference short)
text_png("title", ["DAY 1 OF TRYING TO", "BREAK MEME ROYALE"], 92, 150)
# beats (centre-low, above TikTok's caption area)
Y = 1180
text_png("c_wait", ["WAIT FOR IT..."], 104, Y, fill=(255, 226, 74))
text_png("c_plan", ["THE PLAN:", "SPAM USELESS ARMY"], 92, Y)
text_png("c_fork", ["+ HARD FORK", "COPIES EVERY COIN"], 92, Y, fill=(178, 255, 120))
text_png("c_mult", ["THEY KEEP", "MULTIPLYING"], 96, Y)
text_png("c_hot", ["MY PHONE IS", "GETTING HOT"], 96, Y, fill=(255, 140, 90))
text_png("c_1000", ["1,000+ USELESS", "ON THE MAP"], 96, Y, fill=(255, 226, 74))
text_png("c_works", ["IT ACTUALLY", "WORKED"], 112, Y, fill=(178, 255, 120))
text_png("c_day2", ["DAY 2: 10,000?", "FOLLOW FOR PART 2"], 88, Y, fill=(255, 226, 74))
# the live counter plate digits are drawn per frame by the edit script (counter.py)
