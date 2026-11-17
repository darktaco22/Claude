"""Repaint the mall's roof sign in Poly Haven's Mall Parking Lot HDRI (CC0) as MEME MALL and flatten a toy-store banner. usage: blender -b -P sign_fix.py -- ASSETS"""
import sys, os
A = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/root/reap3d"; HERE = os.path.dirname(os.path.abspath(__file__))
import bpy, numpy as np
im = bpy.data.images.load(A + '/ph/mall_parking_lot_16k.hdr'); w, h = im.size
a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(h, w, 4)
X0, TOP = 9666, h - 4957
def ld(p):
    m = bpy.data.images.load(p); mw, mh = m.size; x = np.empty(mw * mh * 4, np.float32); m.pixels.foreach_get(x); return x.reshape(mh, mw, 4)[..., 0]
pm, tm = ld(HERE + '/hdri/panelmask.png'), ld(HERE + '/hdri/textmask.png')   # bottom-up rows
ph_, pw_ = pm.shape; xa = X0 + 190; ytop = 92                     # crop top-down y of the panel's top
rb = h - 1 - (TOP + ytop + ph_ - 1)                               # bottom-up row of the panel's bottom
reg = a[rb:rb + ph_, xa:xa + pw_, :3]
L = reg.mean(2); sky = np.percentile(L, 95)
redpx = reg[(reg[..., 0] > reg[..., 1] * 1.12) & (L < sky * 0.6)]
base = np.percentile(redpx, 50, axis=0) if len(redpx) > 50 else np.array([0.35, 0.12, 0.13])
panel_col = np.array([0.30, 0.035, 0.045]) * (base.mean() / 0.2)   # deep red, at the brightness of the backlit original
v = np.linspace(0.8, 1.15, ph_)[:, None, None]                      # bottom-up: darker at the bottom
panel = panel_col[None, None, :] * v
letter = np.array([2.2, 2.1, 1.95]) * (base.mean() / 0.2) * 1.4    # warm white, lit
out = reg * (1 - pm[..., None]) + panel * pm[..., None]
out = out * (1 - tm[..., None]) + letter[None, None, :] * tm[..., None]
# a thin bright top edge (sky glare on the frame)
edge = np.zeros_like(pm); edge[-6:, :] = 1; edge *= pm
out = out * (1 - edge[..., None] * 0.6) + (np.array([1.6, 1.5, 1.4]) * base.mean() / 0.2)[None, None, :] * edge[..., None] * 0.6
a[rb:rb + ph_, xa:xa + pw_, :3] = out
# the 'будинок' banner text: flatten to the banner's own color (crop x 1990-2294, y 325-369+)
bx0, bx1 = X0 + 2000, X0 + 2294; t0, t1 = 318, 430
r0, r1 = h - 1 - (TOP + t1), h - 1 - (TOP + t0)
br = a[r0:r1 + 1, bx0:bx1, :3]; Lb = br.mean(2); med = np.median(br.reshape(-1, 3), axis=0)
Lm = br.mean(2); mask = (np.abs(Lm - np.median(Lm)) > np.median(Lm) * 0.10).astype(np.float32)
for _ in range(3):   # dilate (numpy only)
    m2 = mask.copy(); m2[1:] = np.maximum(m2[1:], mask[:-1]); m2[:-1] = np.maximum(m2[:-1], mask[1:]); m2[:, 1:] = np.maximum(m2[:, 1:], mask[:, :-1]); m2[:, :-1] = np.maximum(m2[:, :-1], mask[:, 1:]); mask = m2
a[r0:r1 + 1, bx0:bx1, :3] = br * (1 - mask[..., None]) + med[None, None, :] * mask[..., None]
print('SIGN base', base, 'panel', panel_col, 'sky', sky)
im.pixels.foreach_set(a.ravel()); im.filepath_raw = A + '/ph/mall_meme_16k.hdr'; im.file_format = 'HDR'; im.save()
c = a[h - 1 - (TOP + 450):h - 1 - (TOP + 0), X0:X0 + 2294, :3][::-1]; c = c / (1 + c); c = np.clip(c * 1.6, 0, 1) ** (1 / 2.2)

