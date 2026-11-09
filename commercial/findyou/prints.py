"""The printed things in the film: the corkboard's evidence, the retirement home's sign, the mug.
python3 prints.py  -> findyou/tex/*.png"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); CARDS = os.path.join(HERE, '..', 'coins', 'cards')
OUT = os.path.join(HERE, 'tex'); os.makedirs(OUT, exist_ok=True)
def lil(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def rub(s, w=600):
    f = ImageFont.truetype(os.path.join(A, 'rubik.ttf'), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def marker(s): return lil(s)

# the suspect's profile, printed off the game
im = Image.new('RGB', (600, 760), (245, 242, 235)); d = ImageDraw.Draw(im)
d.rectangle((0, 0, 600, 110), fill=(40, 22, 90)); d.text((300, 55), 'PLAYER PROFILE', font=lil(56), fill=(255, 214, 80), anchor='mm')
d.rectangle((150, 150, 450, 450), fill=(70, 70, 80)); d.text((300, 300), '?', font=lil(240), fill=(200, 200, 210), anchor='mm')
d.text((300, 500), 'xX_Grandma_Rugs_Xx', font=lil(50), fill=(30, 20, 60), anchor='mm')
for i, (k, v) in enumerate([('WINS', '9,999'), ('RUG PULLS', '1,337'), ('LOSSES', '0')]):
    d.text((90, 570 + i * 55), k, font=rub(36, 700), fill=(80, 80, 90)); d.text((510, 570 + i * 55), v, font=rub(36, 800), fill=(200, 30, 40), anchor='ra')
im.save(f'{OUT}/profile.png')

# sticky notes in a marker hand
for name, col, lines in [('note1', (255, 236, 110), ['WHO RUGS', 'AT 3 PM??']), ('note2', (255, 170, 190), ['SHE NEVER', 'MISSES']),
                         ('note3', (160, 230, 255), ['ALWAYS', 'ONLINE', 'AFTER', 'BINGO?']), ('note4', (190, 255, 160), ['FOLLOW', 'THE', 'COPIUM'])]:
    im = Image.new('RGB', (400, 400), col); d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines): d.text((200, 200 - (len(lines) - 1) * 40 + i * 80), ln, font=marker(72), fill=(25, 25, 40), anchor='mm')
    im.save(f'{OUT}/{name}.png')

# the chat screenshot
im = Image.new('RGB', (620, 300), (20, 22, 30)); d = ImageDraw.Draw(im)
d.text((30, 30), 'xX_Grandma_Rugs_Xx:', font=rub(34, 800), fill=(255, 90, 110)); d.text((30, 90), 'gg ez :)', font=rub(64, 800), fill=(255, 255, 255))
d.text((30, 200), 'NEET:  ...', font=rub(34, 800), fill=(124, 255, 107))
im.save(f'{OUT}/chat.png')

# a blurry long-lens photo of the retirement home
im = Image.new('RGB', (640, 460), (60, 70, 90)); d = ImageDraw.Draw(im)
d.rectangle((0, 300, 640, 460), fill=(50, 90, 50)); d.rectangle((80, 80, 560, 320), fill=(190, 170, 150))
for x in range(110, 560, 90): d.rectangle((x, 120, x + 50, 190), fill=(250, 230, 160))
d.rectangle((160, 250, 480, 300), fill=(240, 240, 235)); d.text((320, 275), 'SUNNY ACRES', font=lil(40), fill=(40, 90, 60), anchor='mm')
im = im.filter(ImageFilter.GaussianBlur(2.5)); d = ImageDraw.Draw(im)
d.ellipse((140, 230, 500, 320), outline=(220, 20, 30), width=7)
im.save(f'{OUT}/photo.png')

# a printed map with a circle
im = Image.new('RGB', (620, 460), (232, 228, 214)); d = ImageDraw.Draw(im)
for i in range(0, 620, 70): d.line((i, 0, i + 120, 460), fill=(200, 196, 180), width=10)
for j in range(0, 460, 80): d.line((0, j, 620, j + 40), fill=(205, 200, 185), width=8)
d.ellipse((300, 170, 420, 260), outline=(220, 20, 30), width=8); d.text((360, 300), 'HERE.', font=marker(56), fill=(200, 20, 30), anchor='mm')
im.save(f'{OUT}/map.png')

# the sign outside the home
im = Image.new('RGB', (1400, 520), (245, 242, 230)); d = ImageDraw.Draw(im)
d.rectangle((14, 14, 1386, 506), outline=(60, 110, 70), width=14)
d.text((700, 170), 'SUNNY ACRES', font=lil(190), fill=(50, 105, 65), anchor='mm')
d.text((700, 330), 'RETIREMENT LIVING', font=lil(90), fill=(90, 90, 90), anchor='mm')
d.text((700, 440), 'Bingo Tuesdays · Wi-Fi in every room', font=rub(54, 700), fill=(120, 110, 100), anchor='mm')
im.save(f'{OUT}/sign.png')

# grandma's mug
im = Image.new('RGB', (1024, 300), (250, 248, 244)); d = ImageDraw.Draw(im)
d.text((512, 150), '#1 GRANDMA', font=lil(150), fill=(200, 60, 110), anchor='mm')
im.save(f'{OUT}/mug.png')
print('PRINTS-DONE')
