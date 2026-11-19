"""Before/after pairs: frames_jpg/50dff5a2ee (the film the user has) vs a check render. Usage: ba.py CHECK_DIR OUT_PREFIX f1,f2,... [labels]"""
import sys, json
from PIL import Image, ImageDraw, ImageFont
chk, out, frames = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
labels = sys.argv[4].split('|') if len(sys.argv) > 4 else [''] * len(frames)
E = json.load(open('/home/user/dep/commercial/memetrix/edl.json'))
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
W_, H_ = 640, 360
rows = []
for f, lab in zip(frames, labels):
    a = Image.open(f'/home/user/dep/commercial/memetrix/frames_jpg/50dff5a2ee/f_{f:04d}.jpg').convert('RGB').resize((W_, H_))
    b = Image.open(f'{chk}/f_{f:04d}.png').convert('RGB').resize((W_, H_))
    r = Image.new('RGB', (W_ * 2 + 12, H_ + 34), (20, 20, 20)); r.paste(a, (0, 34)); r.paste(b, (W_ + 12, 34))
    d = ImageDraw.Draw(r); d.text((8, 5), 'BEFORE  ' + lab, font=font, fill=(255, 120, 120)); d.text((W_ + 20, 5), 'AFTER', font=font, fill=(120, 255, 140))
    rows.append(r)
for g in range(0, len(rows), 4):
    chunk = rows[g:g + 4]
    S = Image.new('RGB', (chunk[0].width, sum(r.height for r in chunk) + 8 * (len(chunk) - 1)), (0, 0, 0))
    y = 0
    for r in chunk: S.paste(r, (0, y)); y += r.height + 8
    S.save(f'{out}_{g // 4 + 1}.jpg', quality=88)
