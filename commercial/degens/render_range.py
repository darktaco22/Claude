import bpy, os, sys
a = sys.argv[sys.argv.index('--') + 1:]
sc = bpy.context.scene; sc.frame_start, sc.frame_end = int(a[0]), int(a[1])
sc.render.use_overwrite = True; sc.render.use_placeholder = False
sc.render.filepath = os.environ['W'] + '/frames/f_'
bpy.ops.render.render(animation=True)
