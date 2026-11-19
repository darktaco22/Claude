import sys, glob, json, os
from PIL import Image, ImageDraw
src, out, per = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6
E = json.load(open('/home/user/dep/commercial/memetrix/edl.json'))
names = [s['name'] for s in E['shots']]
files = sorted(glob.glob(src + '/a_*.png'))
shots = sorted({int(os.path.basename(f).split('_')[1]) for f in files})
w, h = Image.open(files[0]).size
w, h = w // 1, h // 1
for g in range(0, len(shots), per):
    grp = shots[g:g + per]
    S = Image.new('RGB', (w * 3, h * len(grp)))
    d = ImageDraw.Draw(S)
    for r, k in enumerate(grp):
        for c in range(3):
            f = f'{src}/a_{k:02d}_{c}.png'
            if os.path.exists(f):
                S.paste(Image.open(f).convert('RGB').resize((w, h)), (c * w, r * h))
        d.rectangle([0, r * h, 200, r * h + 16], fill='black')
        d.text((3, r * h + 2), f'{k} {names[k]}', fill='yellow')
    S.save(f'{out}_{g // per:02d}.jpg', quality=85)
