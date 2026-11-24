"""Render film frames of THE MEMETRIX II (episode 1's renderer with the café and white-room lights):  blender -b W/scene.blend -P render_edl.py -- frames.txt

Every film frame shows the animation at the time its shot maps it to (s0 < 1: slow motion), from the shot's camera,
placed by tools/cine.py (with recorded handheld from shakify on top). Only the shot's set has its lights on.
Resumable (frames.txt.done) and budgeted (RENDER_BUDGET seconds, then exit 3 = run again).
Env: W (work folder), EDL (alternate edl), SCALE (percent), SAMPLES, OUT, MB=1 (motion blur on bullet-time shots).
Frames before the title ends (film t < title) are not rendered: the finish draws the opening.
"""
import json
import os
import sys
import time

import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, os.path.join(HERE, '..', 'memetrix'))
import cine  # noqa: E402
import preflight  # noqa: E402
import shakify  # noqa: E402
from track import make_where  # noqa: E402

T0 = time.time()
BUDGET = float(os.environ.get('RENDER_BUDGET', '0') or 0)
frame_list = sys.argv[sys.argv.index('--') + 1]
E = json.load(open(os.environ.get('EDL') or os.path.join(HERE, 'edl.json')))
done_file = frame_list + '.done'
done = set(int(x) for x in open(done_file).read().split()) if os.path.exists(done_file) else set()
frames = [int(x) for x in open(frame_list).read().split() if int(x) not in done]

sc = bpy.context.scene
cam = sc.camera
FPS = E['fps']
cine.EYES.update(E['eyes'])
cine.EYE_FWD.update(E.get('eye_fwd', {}))
cine.FRAME_SCALE = E.get('frame_scale', 1.0)
where = make_where(E['tracks'])
sc.render.use_overwrite = True
sc.render.use_persistent_data = True
sc.render.resolution_percentage = int(os.environ.get('SCALE', '67'))
OUTD = os.environ.get('OUT', os.environ.get('W', '/tmp') + '/frames')
os.makedirs(OUTD, exist_ok=True)
if os.environ.get('SAMPLES'):
    sc.cycles.samples = int(os.environ['SAMPLES'])
LIGHTS = {name: bpy.data.collections.get('L_' + name) for name in ('FLOOR', 'BASEMENT', 'DOJO', 'ROOFTOP', 'CAFE', 'WHITE')}
FILL = bpy.data.objects.get('camfill')
RIM = bpy.data.objects.get('rimlight')
RIM_LOOK = {'FLOOR': (650.0, (0.55, 1.0, 0.65)), 'BASEMENT': (350.0, (0.6, 0.75, 1.0)), 'DOJO': (500.0, (0.4, 0.9, 1.0)),
            'ROOFTOP': (800.0, (0.6, 1.0, 0.75)), 'CAFE': (500.0, (1.0, 0.6, 0.3)), 'WHITE': (300.0, (1.0, 1.0, 1.0))}                                     # behind the subject, opposite the lens
FILL_POWER = {'FLOOR': 35.0, 'BASEMENT': 25.0, 'DOJO': 8.0, 'ROOFTOP': 30.0, 'CAFE': 15.0, 'WHITE': 10.0}          # a soft light beside the lens so faces read
if os.environ.get('NOHAZE'):
    for obj in bpy.data.objects:
        if obj.name.startswith('haze_'):
            obj.hide_render = True
RAIN = [mat.node_tree.nodes['rain'] for mat in bpy.data.materials if mat.use_nodes and 'rain' in mat.node_tree.nodes]


def shot_at(t):
    return next((s for s in E['shots'] if s['t0'] <= t < s['t1']), E['shots'][-1])


def setup(f):
    t = (f - 1) / FPS
    s = shot_at(t)
    u = (t - s['t0']) / max(1e-6, s['t1'] - s['t0'])
    a = s['a0'] + (t - s['t0']) * s['s0']
    af = a * FPS + 1
    sc.frame_set(int(af), subframe=af - int(af))
    for name, col in LIGHTS.items():
        if col is not None:
            col.hide_render = name != s['set']
    for node in RAIN:                                      # the code keeps falling at film speed, also in slow motion
        node.image_user.frame_start = sc.frame_current        # shown frame = current - start + 1 + offset (cyclic)
        node.image_user.frame_offset = int(t * 24) % 48
    if FILL is not None:
        FILL.data.energy = s.get('fill', FILL_POWER.get(s['set'], 20.0))
    pos = cine.place(cam, s['cam'], u, a, where, sc)
    if RIM is not None:
        feet, head = where(s['cam']['subject'], a)
        eye = cine.eye_point(s['cam']['subject'], feet, head)
        away = eye - pos
        away.z = 0
        away.normalize()
        power, colour = RIM_LOOK.get(s['set'], (400.0, (1, 1, 1)))
        RIM.location = eye + away * 1.6 + Vector((0, 0, 0.9))
        RIM.rotation_mode = 'QUATERNION'
        RIM.rotation_quaternion = (eye - RIM.location).to_track_quat('-Z', 'Y')
        RIM.data.energy = s.get('rim', power) * (1.0 if s['cam'].get('size') not in ('EWS',) else 0.0)
        RIM.data.color = colour
    hand = s.get('hand')
    if hand:
        k = hand[1] * min(1.0, 50.0 / cam.data.lens)
        dloc, drot = shakify.shake(hand[0], t, influence=k, loc_scale=0.6, offset=s['t0'] * 1.7)
        q = cam.rotation_quaternion @ Euler(drot, 'XYZ').to_quaternion()
        cam.rotation_quaternion = q
        cam.location = pos + q.to_matrix() @ Vector(dloc)
    # no blur on a shot's first frame: the shutter would straddle the cut and smear the previous set's pose into it
    sc.render.use_motion_blur = os.environ.get('MB', '1') != '0' and (t - s['t0']) * FPS > 0.5
    return s


if __name__ == '__main__':
    first_film = int(E['title'] * FPS) + 1
    frames = [f for f in frames if f >= first_film]
    if frames:
        setup(frames[0])
        sc.render.filepath = OUTD + '/check.png'
        preflight.report(preflight.check(sc, 1, sc.frame_end))
    last = 0.0
    for i, f in enumerate(frames):
        if BUDGET and time.time() - T0 + 1.5 * last > BUDGET:
            print('BUDGET-STOP', len(frames) - i, 'frames left', flush=True)
            os._exit(3)
        t = time.time()
        setup(f)
        sc.render.filepath = OUTD + f'/f_{f:04d}.png'
        bpy.ops.render.render(write_still=True)
        print('DONE', f, round(time.time() - t, 1), flush=True)
        with open(done_file, 'a') as fh:
            fh.write(f'{f} ')
        last = time.time() - t
