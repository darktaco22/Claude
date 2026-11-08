import bpy, time, sys
sc = bpy.context.scene; a = sys.argv[sys.argv.index('--') + 1:]
out, w, h, spp, mb, t = a[0], int(a[1]), int(a[2]), int(a[3]), a[4] == '1', float(a[5])
sc.render.resolution_x, sc.render.resolution_y = w, h; sc.cycles.samples = spp; sc.render.use_motion_blur = mb
sc.frame_set(int(t * 30) + 1); sc.render.filepath = out
t0 = time.time(); bpy.ops.render.render(write_still=True); print('BENCH', w, spp, mb, t, round(time.time() - t0, 1))
