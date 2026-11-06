import sys, glob, os
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
fs = sorted(glob.glob(f'{d}/qa_*.png')); ims = [Image.open(f).convert('RGB') for f in fs]
w, h = ims[0].size; sh = Image.new('RGB', (cols * w, ((len(ims) + cols - 1) // cols) * (h + 20)), 'white'); dr = ImageDraw.Draw(sh)
for i, (f, im) in enumerate(zip(fs, ims)):
    x, y = (i % cols) * w, (i // cols) * (h + 20); sh.paste(im, (x, y + 20)); dr.text((x + 4, y + 4), os.path.basename(f)[3:-4], fill='black')
sh.save(out, quality=85)
