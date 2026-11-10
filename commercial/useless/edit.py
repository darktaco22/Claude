"""The edit: lays the film's frames and the gameplay cutaways (the extra frames after the film) out in film order as
symlinks, and holds the last frame under the end card. python3 edit.py TIMELINE.json FRAMES_DIR OUT_DIR -> prints the frame count."""
import sys, os, json
tl = json.load(open(sys.argv[1])); F, O = os.path.abspath(sys.argv[2]), sys.argv[3]; fps = tl['fps']; nf = round(tl['end'] * fps)
os.makedirs(O, exist_ok=True)
for x in os.listdir(O): os.unlink(os.path.join(O, x))
order = []; src = nf; s = 0
for x in tl.get('inserts', []):
    a = round(x['at'] * fps); order += range(s + 1, a + 1); order += range(src + 1, src + x['n'] + 1); s = a; src += x['n']
order += range(s + 1, nf + 1); order += [nf] * int(3.0 * fps)
for i, f in enumerate(order): os.symlink(f'{F}/f_{f:04d}.png', f'{O}/f_{i + 1:04d}.png')
print(len(order))
