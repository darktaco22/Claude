"""Render film frames: blender -b scene.blend -P render_edl.py -- frames.txt
Every film frame shows the animation at the time its shot maps it to (speed s0: slow motion), from that shot's camera.
Resumable (frames.txt.done), budgeted (RENDER_BUDGET s, exit 3).  Env: W (work folder), EDL (alternate edl), SCALE (percent, for tests)."""
import bpy, os, sys, time, json, math
from mathutils import Vector, Quaternion, noise
T0 = time.time(); BUDGET = float(os.environ.get('RENDER_BUDGET', '0') or 0)
lst = sys.argv[sys.argv.index('--') + 1]; E = json.load(open(os.environ.get('EDL') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'edl.json')))
fl = [int(x) for x in open(lst).read().split()]; done_file = lst + '.done'
done = set(int(x) for x in open(done_file).read().split()) if os.path.exists(done_file) else set()
fl = [f for f in fl if f not in done]; sc = bpy.context.scene; cam = sc.camera; FPS = E['fps']; sc.render.use_overwrite = True
cam.data.dof.aperture_ratio = 1.6          # an anamorphic lens: oval highlights out of focus
sc.render.resolution_percentage = int(os.environ.get('SCALE', '100')); OUTD = os.environ.get('OUT', os.environ['W'] + '/frames'); os.makedirs(OUTD, exist_ok=True)
if os.environ.get('SAMPLES'): sc.cycles.samples = int(os.environ['SAMPLES'])
def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def setup(f):
    t = (f - 1) / FPS; s = next((s for s in E['shots'] if s['t0'] <= t < s['t1']), E['shots'][-1]); dur = s['t1'] - s['t0']
    u = (t - s['t0']) / dur; a = s['a0'] + (t - s['t0']) * s['s0']; af = a * FPS + 1
    sc.frame_set(int(af), subframe=af - int(af)); sc.render.motion_blur_shutter = max(0.1, 0.4 * s['s0'])
    ec = s.get('ec', 0); e = ease(u) if ec == 0 else (u * u if ec == 1 else (1 - (1 - u) ** 2 if ec == 2 else u))
    p = Vector(s['p0']).lerp(Vector(s['p1']), e); l = Vector(s['l0']).lerp(Vector(s['l1']), e); sh = s['shake']
    if sh:
        n1 = noise.noise_vector(Vector((t * 2.3, s['t0'], 0.0))); n2 = noise.noise_vector(Vector((t * 9.0, s['t0'] + 7, 3.0)))
        l = l + (n1 * 0.10 + n2 * 0.035) * sh * (p - l).length * 0.12; p = p + n1 * 0.04 * sh
    d = l - p; cam.location = p; cam.rotation_mode = 'QUATERNION'; q = d.to_track_quat('-Z', 'Y'); rl = s.get('roll')
    if rl: q = q @ Quaternion((0, 0, 1), rl[0] + (rl[1] - rl[0]) * e)
    cam.rotation_quaternion = q; cam.data.lens = s['lens'] + (s['lens1'] - s['lens']) * e
    cam.data.dof.focus_distance = s.get('focus') or max(0.3, d.length); cam.data.dof.aperture_fstop = s['fstop']
last = 0.0
for i, f in enumerate(fl):
    if BUDGET and time.time() - T0 + 1.5 * last > BUDGET: print('BUDGET-STOP', len(fl) - i, 'frames left', flush=True); os._exit(3)
    t = time.time(); setup(f); sc.render.filepath = OUTD + f'/f_{f:04d}.png'
    bpy.ops.render.render(write_still=True); print('DONE', f, round(time.time() - t, 1), flush=True)
    with open(done_file, 'a') as fh: fh.write(f'{f} ')
    last = time.time() - t
