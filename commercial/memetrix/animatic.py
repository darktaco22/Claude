"""Animatic: three small frames per shot (start, middle, end) and a labelled sheet per section.
    blender -b W/scene.blend -P animatic.py -- OUT_DIR        (env SCALE=25, SAMPLES=8)"""
import os
import subprocess
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('W', '/tmp')
sys.argv = [sys.argv[0], '--', '/dev/null']
import render_edl as R  # noqa: E402

out = os.environ.get('ANIM_OUT', '/tmp/animatic')
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.resolution_percentage = int(os.environ.get('SCALE', '25'))
sc.cycles.samples = int(os.environ.get('SAMPLES', '8'))
tiles = []
ONLY = set(filter(None, os.environ.get('ONLY', '').split(',')))      # ONLY=s05_0,fight_arc: just these shots
for i, s in enumerate(R.E['shots']):
    if ONLY and s['name'] not in ONLY:
        continue
    for j, u in enumerate((0.08, 0.5, 0.92)):
        t = s['t0'] + (s['t1'] - s['t0']) * u
        f = int(t * R.FPS) + 1
        path = os.path.join(out, f'a_{i:02d}_{j}.png')
        if not os.path.exists(path):
            R.setup(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
        tiles.append((path, f"{i} {s['name']} {t:.1f}s"))
        print('ANIM', i, j, flush=True)
rows = 12
for page in range(0, len(tiles), 3 * rows):
    chunk = tiles[page:page + 3 * rows]
    args, filt = [], ''
    for k, (path, label) in enumerate(chunk):
        args += ['-i', path]
        filt += f"[{k}:v]scale=480:270,drawtext=text='{label}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6[t{k}];"
    layout = '|'.join(f'{(k % 3) * 480}_{(k // 3) * 270}' for k in range(len(chunk)))
    filt += ''.join(f'[t{k}]' for k in range(len(chunk))) + f'xstack=inputs={len(chunk)}:layout={layout}:fill=black'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args, '-filter_complex', filt, '-q:v', '4',
                    os.path.join(out, f'sheet_{page // (3 * rows) + 1}.jpg')], check=True)
print('ANIMATIC-DONE', out)
