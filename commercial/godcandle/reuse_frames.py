"""Reuse already-rendered frames after the edit changed: python3 reuse_frames.py OLD_EDL OLD_FRAMES_DIR NEW_FRAMES_DIR KEEP_FIRST
Copies every old frame whose shot (same cameras, lens and speed ramp) still exists in edl.json into its new film frame number, plus the first
KEEP_FIRST frames as they are.  Prints the frames that still have to be rendered, split by blend: room.txt (room shots), space.txt, arena.txt."""
import json, os, sys, shutil
old = json.load(open(sys.argv[1])); new = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'edl.json'))); OD, ND, KEEP = sys.argv[2], sys.argv[3], int(sys.argv[4])
FPS = new['fps']
def first(s): return int(round(s['t0'] * FPS)) + 1
def count(s): return int(round(s['t1'] * FPS)) - int(round(s['t0'] * FPS))
def key(s): return json.dumps([s['p0'], s['p1'], s['l0'], s['l1'], s['lens'], s['lens1'], s['s0'], s['s1'], round(s['t1'] - s['t0'], 3), s['orb'], s['fp'], s['fl'], s.get('roll')], sort_keys=True)
os_ = {}
for s in old['shots']: os_.setdefault(key(s), []).append(s)
have = set(range(1, KEEP + 1)); moved = 0
for s in new['shots']:
    cand = os_.get(key(s))
    if not cand: continue
    o = cand.pop(0)
    for k in range(count(s)):
        src = os.path.join(OD, f'f_{first(o) + k:04d}.png'); dst = os.path.join(ND, f'f_{first(s) + k:04d}.png')
        if os.path.exists(src):
            if os.path.abspath(src) != os.path.abspath(dst): shutil.copy2(src, dst)
            have.add(first(s) + k); moved += 1
print('reused', moved, 'frames, kept first', KEEP)
lists = dict(room=[], space=[], arena=[])
for i, s in enumerate(new['shots']):
    kind = 'space' if s.get('sp') else ('room' if i <= 5 else 'arena')
    lists[kind] += [f for f in range(first(s), first(s) + count(s)) if f not in have]
for k, v in lists.items():
    open(os.path.join(ND, '..', f'todo_{k}.txt'), 'w').write(' '.join(map(str, v)) + ' '); print(k, len(v), 'frames to render')
