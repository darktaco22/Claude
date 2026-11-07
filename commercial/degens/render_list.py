"""Render a list of frames: blender -b scene.blend -P render_list.py -- frames.txt"""
import bpy, os, sys
fl = [int(x) for x in open(sys.argv[sys.argv.index('--') + 1]).read().split()]
sc = bpy.context.scene; sc.render.use_overwrite = True
for f in fl:
    sc.frame_set(f); sc.render.filepath = os.environ['W'] + f'/frames/f_{f:04d}.png'
    bpy.ops.render.render(write_still=True); print('DONE', f, flush=True)
