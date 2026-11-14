"""The rug (an ornate red and gold carpet, fringed at both ends).  python3 tex.py TEX_DIR"""
import sys, os, math
from PIL import Image, ImageDraw
out = sys.argv[1]; os.makedirs(out, exist_ok=True); W, H = 1600, 1050
im = Image.new('RGB', (W, H), (236, 224, 196)); d = ImageDraw.Draw(im)
F = 46                                                     # the fringe, at the two short ends
for y in range(6, H - 6, 9): d.line([(0, y), (F, y + 2)], fill=(214, 198, 160), width=4); d.line([(W - F, y + 2), (W, y)], fill=(214, 198, 160), width=4)
R = (120, 14, 18); G = (214, 160, 52); N = (22, 30, 74); C = (238, 222, 186)
d.rectangle([F, 0, W - F, H], fill=G); d.rectangle([F + 14, 14, W - F - 14, H - 14], fill=N); d.rectangle([F + 70, 70, W - F - 70, H - 70], fill=G); d.rectangle([F + 82, 82, W - F - 82, H - 82], fill=R)
for x in range(F + 42, W - F - 30, 56):                   # the border: diamonds
    for y in (42, H - 42): d.polygon([(x, y - 16), (x + 16, y), (x, y + 16), (x - 16, y)], fill=G); d.polygon([(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)], fill=R)
for y in range(98, H - 80, 56):
    for x in (F + 42, W - F - 42): d.polygon([(x, y - 16), (x + 16, y), (x, y + 16), (x - 16, y)], fill=G); d.polygon([(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)], fill=R)
for i, x in enumerate(range(F + 150, W - F - 110, 96)):   # the field: a lattice of small gold flowers
    for j, y in enumerate(range(150, H - 110, 96)):
        cx = x + (48 if j % 2 else 0); col = G if (i + j) % 2 else C
        for a in range(4): d.ellipse([cx + 13 * math.cos(a * math.pi / 2) - 7, y + 13 * math.sin(a * math.pi / 2) - 7, cx + 13 * math.cos(a * math.pi / 2) + 7, y + 13 * math.sin(a * math.pi / 2) + 7], fill=col)
        d.ellipse([cx - 5, y - 5, cx + 5, y + 5], fill=N)
cx, cy = W // 2, H // 2                                    # the medallion
for r, col in ((250, G), (236, N), (214, G), (202, R), (120, G), (108, N)): d.polygon([(cx, cy - r), (cx + r * 1.45, cy), (cx, cy + r), (cx - r * 1.45, cy)], fill=col)
for k in range(12): a = k * math.pi / 6; d.ellipse([cx + 60 * math.cos(a) - 16, cy + 60 * math.sin(a) - 16, cx + 60 * math.cos(a) + 16, cy + 60 * math.sin(a) + 16], fill=G)
d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=C); d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=R)
im.save(os.path.join(out, 'rug.png')); print('rug.png')
