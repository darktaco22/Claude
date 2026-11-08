"""30 -> 60 fps with RIFE (nihui/rife-ncnn-vulkan, rife-v4.6), never blending across a cut.
python3 interp60.py FRAMES_DIR OUT_DIR RIFE_DIR"""
import os, sys, shutil, subprocess, math
src, out, R = sys.argv[1:4]
import json
TL = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timeline.json')))
CUTS = TL['cuts'] + [TL['end'] - 0.25]
cut_first = {int(math.ceil(c * 30)) + 1 for c in CUTS}          # first 30 fps frame of each new shot
tmp_in = out + '_in'; os.makedirs(tmp_in, exist_ok=True); os.makedirs(out, exist_ok=True)
N = int(round(TL['end'] * 30))
for f in range(1, N + 1):
    d = f'{tmp_in}/{f:08d}.png'
    if not os.path.exists(d): os.link(f'{src}/f_{f:04d}.png', d)
subprocess.run([f'{R}/rife-ncnn-vulkan', '-i', tmp_in, '-o', out, '-m', f'{R}/rife-v4.6', '-n', str(2 * N), '-j', '1:2:2'], check=True)
# output 2k-1 = source k, output 2k = between k and k+1; across a cut, hold source k instead
fixed = 0
for k in range(1, N):
    if k + 1 in cut_first:
        shutil.copyfile(f'{src}/f_{k:04d}.png', f'{out}/{2 * k:08d}.png'); fixed += 1
print('60 fps frames', len(os.listdir(out)), 'cut frames held', fixed)
