"""Render a list of frames: blender -b scene.blend -P render_list.py -- frames.txt
Resumable: finished frames go to frames.txt.done and are skipped on the next run.
RENDER_BUDGET=seconds (optional) stops cleanly before that time is used up and exits with code 3 if frames
remain, so a job launched as a tracked background task (2 h cap) can be relaunched on its completion
notification. See RENDERING.md for why renders must not be launched detached."""
import bpy, os, sys, time
T0 = time.time(); BUDGET = float(os.environ.get('RENDER_BUDGET', '0') or 0)
lst = sys.argv[sys.argv.index('--') + 1]
fl = [int(x) for x in open(lst).read().split()]
done_file = lst + '.done'                      # frames finished with this scene: survives restarts
done = set(int(x) for x in open(done_file).read().split()) if os.path.exists(done_file) else set()
fl = [f for f in fl if f not in done]
sc = bpy.context.scene; sc.render.use_overwrite = True
last = 0.0
for i, f in enumerate(fl):
    if BUDGET and time.time() - T0 + 1.5 * last > BUDGET:      # next frame would overrun: stop cleanly
        print('BUDGET-STOP', len(fl) - i, 'frames left', flush=True); os._exit(3)
    t = time.time()
    sc.frame_set(f); sc.render.filepath = os.environ['W'] + f'/frames/f_{f:04d}.png'
    bpy.ops.render.render(write_still=True); print('DONE', f, flush=True)
    with open(done_file, 'a') as fh: fh.write(f'{f} ')
    last = time.time() - t
