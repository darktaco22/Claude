"""Low-res stills at chosen times: blender -b scene.blend -P sheet.py -- OUTDIR t1 t2 ...  (or 'f:N' frames)"""
import bpy, sys, os
A = sys.argv[sys.argv.index('--') + 1:]; out = A[0]; os.makedirs(out, exist_ok=True)
sc = bpy.context.scene; sc.render.resolution_percentage = int(os.environ.get('PCT', '50')); sc.cycles.samples = int(os.environ.get('SPP', '8'))
for x in A[1:]:
    f = int(x[2:]) if x.startswith('f:') else int(round(float(x) * 30)) + 1
    sc.frame_set(f); sc.render.filepath = f'{out}/s_{f:04d}.png'; bpy.ops.render.render(write_still=True)
