"""Check frames: python3 animatic.py list W [per_shot]   -> W/check.txt (frame numbers, per_shot evenly spaced in each shot)
                 python3 animatic.py sheet W OUT.jpg [cols] [width]  -> labelled contact sheet of W/check/*.png"""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HERE, 'edl.json')))


def frames(per_shot):
    result = []
    for shot in E['shots']:
        for k in range(per_shot):
            t = shot['t0'] + (shot['t1'] - shot['t0']) * (k + 0.5) / per_shot
            result.append((int(t * E['fps']) + 1, shot['name']))
    return result


if sys.argv[1] == 'list':
    per_shot = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
    chosen = [f for f, name in frames(per_shot) if not only or name in only]
    open(os.path.join(sys.argv[2], 'check.txt'), 'w').write(' '.join(str(f) for f in chosen))
    print(len(chosen), 'frames')
else:
    work, out = sys.argv[2], sys.argv[3]
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    width = int(sys.argv[5]) if len(sys.argv) > 5 else 320
    names = {}
    for shot in E['shots']:
        for f in range(int(shot['t0'] * E['fps']) + 1, int(shot['t1'] * E['fps']) + 2):
            names[f] = shot['name']
    files = sorted(n for n in os.listdir(os.path.join(work, 'check')) if n.startswith('f_'))
    height = width * 9 // 16
    sheet = Image.new('RGB', (cols * width, ((len(files) + cols - 1) // cols) * height))
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(files):
        image = Image.open(os.path.join(work, 'check', name)).convert('RGB').resize((width, height))
        x, y = (index % cols) * width, (index // cols) * height
        sheet.paste(image, (x, y))
        f = int(name[2:6])
        draw.rectangle((x, y, x + width, y + 12), fill=(0, 0, 0))
        draw.text((x + 3, y), f'{f} {names.get(f, "")}', fill=(255, 255, 0))
    sheet.save(out, quality=88)
