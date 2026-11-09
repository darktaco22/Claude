"""Map the real-engine captures onto film frames as image sequences (symlinks): python3 link_seq.py CAP_LOSS CAP_GRAN OUT_DIR
OUT_DIR/loss/m_####.png: the monitor (from the RUG PULL on, then the DEFEAT screen held);
OUT_DIR/gran/g_####.png: Grandma's phone, film t -> battle t = film t - 28.1 (her RUG PULL lands in the insert at ~33.5 s)."""
import os, sys, glob, json
cl, cg, out = sys.argv[1:4]; NF = 1128; FPS = 30
def frames(d):
    fs = sorted(glob.glob(os.path.join(d, 'f_*.png'))); return fs
def link(src_list, dst_dir, prefix, pick):
    os.makedirs(dst_dir, exist_ok=True)
    for f in range(1, NF + 1):
        s = src_list[max(0, min(len(src_list) - 1, pick(f)))]; d = os.path.join(dst_dir, f'{prefix}_{f:04d}.png')
        if os.path.lexists(d): os.remove(d)
        os.symlink(os.path.abspath(s), d)
L = frames(cl); G = frames(cg) if os.path.isdir(cg) else L
# loss capture frames are numbered by capture index (battle starts at its start); the shot range began at battle 2.5 s
first_loss = int(os.path.basename(L[0])[2:6])
def lpick(f):
    t = (f - 1) / FPS
    if t < 4.6: return 30 + int(2.4 * (f - 1))       # the cold open: her RUG PULL, his king falls, DEFEAT (sped up), then held
    if t >= 22.0: return 25 + (f - 1 - 660)          # the montage: he replays the moment, frame by frame
    return len(L) - 1
link(L, os.path.join(out, 'loss'), 'm', lpick)
first_g = int(os.path.basename(G[0])[2:6]) if G else 0
def gpick(f):
    return (f - 1) - 900 + 20                      # film 30.0 s = capture shot 20; her RUG PULL (shot ~125) lands at ~33.5 s
link(G, os.path.join(out, 'gran'), 'g', gpick)
print('LINKED', len(L), len(G), 'first', first_loss, first_g)
