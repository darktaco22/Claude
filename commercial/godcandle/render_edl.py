"""Render film frames of GOD CANDLE: blender -b scene.blend -P render_edl.py -- frames.txt
Every film frame shows the animation at the time its shot maps it to (speed ramps s0 -> s1 give slow motion), from that shot's camera
(fixed, a dolly, an orbit, or following the god candle).  Resumable (frames.txt.done), budgeted (RENDER_BUDGET s, exit 3)."""
import bpy, os, sys, time, json, math
from mathutils import Vector, Quaternion, Matrix, noise
T0 = time.time(); BUDGET = float(os.environ.get('RENDER_BUDGET', '0') or 0)
lst = sys.argv[sys.argv.index('--') + 1]; E = json.load(open(os.environ.get('EDL') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'edl.json')))
fl = [int(x) for x in open(lst).read().split()]; done_file = lst + '.done'
done = set(int(x) for x in open(done_file).read().split()) if os.path.exists(done_file) else set()
fl = [f for f in fl if f not in done]; sc = bpy.context.scene; cam = sc.camera; FPS = E['fps']; sc.render.use_overwrite = True; GC = bpy.data.objects['GC']; WORLD0 = sc.world
def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def setup(f):
    t = (f - 1) / FPS; s = next((s for s in E['shots'] if s['t0'] <= t < s['t1']), E['shots'][-1]); dur = s['t1'] - s['t0']
    u = (t - s['t0']) / dur; a = s['a0'] + (t - s['t0']) * (s['s0'] + (s['s1'] - s['s0']) * u * 0.5); af = a * FPS + 1
    sc.frame_set(int(af), subframe=af - int(af)); sp = s['s0'] + (s['s1'] - s['s0']) * u; sc.render.motion_blur_shutter = max(0.1, 0.4 * sp)
    u = s.get('u0', 0) + (1 - s.get('u0', 0)) * u                # a shot may start part-way along its camera move
    if s.get('sp') and 'space' in bpy.data.worlds: sc.world = bpy.data.worlds['space']; cam.data.clip_end = 300000.0         # the space shots: black sky, far planes
    else: sc.world = WORLD0; cam.data.clip_end = 3000.0
    cp = GC.matrix_world.translation.copy(); H = GC.scale.x * 13.2; ec = s.get('ec', 0)
    e = ease(u) if ec == 0 else (u * u if ec == 1 else (1 - (1 - u) ** 2 if ec == 2 else u))
    if s['orb']:
        cx, cy, cz, r, g0, g1, h0, h1 = s['orb']; ang = g0 + (g1 - g0) * e; p = Vector((cx + r * math.sin(ang), cy - r * math.cos(ang), cz + h0 + (h1 - h0) * e))
    else: p = Vector(s['p0']).lerp(Vector(s['p1']), e)
    l = Vector(s['l0']).lerp(Vector(s['l1']), e)
    if s['fp'] == 1: p = p + cp
    elif s['fp'] == 3: p = cp + p * H
    if s['fl'] == 1: l = l + cp
    elif s['fl'] == 3: l = cp + l * H
    sh = s['shake']
    if sh:
        n1 = noise.noise_vector(Vector((t * 2.3, s.get('seed', s['t0']), 0.0))); n2 = noise.noise_vector(Vector((t * 9.0, s.get('seed', s['t0']) + 7, 3.0)))
        l = l + (n1 * 0.10 + n2 * 0.035) * sh * (p - l).length * 0.12; p = p + n1 * 0.04 * sh
    d = l - p; cam.location = p; cam.rotation_mode = 'QUATERNION'; q = d.to_track_quat('-Z', 'Y'); rl = s.get('roll')
    if rl: q = q @ Quaternion((0, 0, 1), rl[0] + (rl[1] - rl[0]) * e)
    if s.get('up1'):                                             # ease the camera's up vector toward a given one (level with the phone at the end of the push-in)
        up = Vector((0, 0, 1)).lerp(Vector(s['up1']), e).normalized(); zc = (-d).normalized(); xc = up.cross(zc).normalized(); yc = zc.cross(xc); q = Matrix((xc, yc, zc)).transposed().to_quaternion()
    cam.rotation_quaternion = q
    cam.data.lens = s['lens'] + (s['lens1'] - s['lens']) * e; cam.data.dof.focus_distance = max(0.5, d.length); cam.data.dof.aperture_fstop = s['fstop'] + (s.get('fstop1', s['fstop']) - s['fstop']) * e
last = 0.0
for i, f in enumerate(fl):
    if BUDGET and time.time() - T0 + 1.5 * last > BUDGET: print('BUDGET-STOP', len(fl) - i, 'frames left', flush=True); os._exit(3)
    t = time.time(); setup(f); sc.render.filepath = os.environ['W'] + f'/frames/f_{f:04d}.png'
    bpy.ops.render.render(write_still=True); print('DONE', f, flush=True)
    with open(done_file, 'a') as fh: fh.write(f'{f} ')
    last = time.time() - t
