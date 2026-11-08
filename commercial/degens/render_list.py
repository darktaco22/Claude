"""Render a list of frames: blender -b scene.blend -P render_list.py -- frames.txt"""
import bpy, os, sys
lst = sys.argv[sys.argv.index('--') + 1]
fl = [int(x) for x in open(lst).read().split()]
done_file = lst + '.done'                      # frames finished with this scene: survives restarts
done = set(int(x) for x in open(done_file).read().split()) if os.path.exists(done_file) else set()
fl = [f for f in fl if f not in done]
sc = bpy.context.scene; sc.render.use_overwrite = True
for f in fl:
    sc.frame_set(f); sc.render.filepath = os.environ['W'] + f'/frames/f_{f:04d}.png'
    bpy.ops.render.render(write_still=True); print('DONE', f, flush=True)
    with open(done_file, 'a') as fh: fh.write(f'{f} ')
