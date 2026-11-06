"""Render QA stills: blender -b scene.blend -P qa.py -- outdir t1,t2,... [pct] [samples]"""
import bpy, sys, time
a = sys.argv[sys.argv.index('--') + 1:]
out, ts = a[0], [float(x) for x in a[1].split(',')]
sc = bpy.context.scene
sc.render.resolution_percentage = int(a[2]) if len(a) > 2 else 40
sc.cycles.samples = int(a[3]) if len(a) > 3 else 16
for t in ts:
    f = int(round(t * 30)) + 1; sc.frame_set(f)
    sc.render.filepath = f'{out}/qa_{t:05.2f}.png'; t0 = time.time()
    bpy.ops.render.render(write_still=True); print('QA', t, round(time.time() - t0, 1), 's')
