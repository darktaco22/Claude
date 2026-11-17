"""Render film frames of DEPLOYED (shots may hide collections/objects by name and set the camera fill light):  blender -b scene.blend -P render_edl.py -- frames.txt

Every film frame shows the animation at the time its shot maps it to (speed s0: slow motion), from that shot's
camera. Resumable (frames.txt.done) and budgeted (RENDER_BUDGET seconds, then exit 3 = run again).
Env: W (work folder), EDL (alternate edl), SCALE (percent, for tests), SAMPLES, OUT.

Uses the toolkit: recorded handheld shake (shakify), a pre-flight check, and stock-footage explosion cards whose
video frame is set here from animation time, so they play in true slow motion.
"""
import json
import os
import sys
import time

import bpy
from mathutils import Euler, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import preflight
import shakify

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
sc.render.use_overwrite = True
sc.render.use_persistent_data = True
sc.render.resolution_percentage = int(os.environ.get('SCALE', '67'))
OUTD = os.environ.get('OUT', os.environ['W'] + '/frames')
os.makedirs(OUTD, exist_ok=True)
if os.environ.get('SAMPLES'):
    sc.cycles.samples = int(os.environ['SAMPLES'])

if os.environ.get('NOMB'):
    sc.render.use_motion_blur = False
if os.environ.get('NOHAZE') and bpy.data.objects.get('haze'):
    bpy.data.objects.remove(bpy.data.objects['haze'])
if os.environ.get('NOSUBD'):
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                mod.render_levels = 0
if os.environ.get('BOUNCES'):
    k = int(os.environ['BOUNCES'])
    sc.cycles.max_bounces = k
    sc.cycles.diffuse_bounces = min(k, 2)
    sc.cycles.glossy_bounces = k
    sc.cycles.transmission_bounces = k
    sc.cycles.transparent_max_bounces = 6
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
CARDS = []
for card in E.get('cards', []):
    obj = bpy.data.objects[card['name']]
    node = obj.data.materials[0].node_tree.nodes['clip']
    node.image_user.use_auto_refresh = True
    CARDS.append((card, obj, node))


HOLD = {}                                   # card/sarge key -> every object of those hold actors (the rig, its children, the ring)
for obj in bpy.data.objects:
    if obj.name.startswith('RIG-') and 'hold' in obj:
        group = HOLD.setdefault(obj['hold'], [])
        group.append(obj)
        group.extend(obj.children_recursive)
        ring = bpy.data.objects.get('ring-' + obj.name[4:])
        if ring is not None:
            group.append(ring)
BASE_RES = (sc.render.resolution_x, sc.render.resolution_y)
HIDEABLE = sorted({name for shot_ in E['shots'] for name in (shot_.get('hide') or ())})
FILL = bpy.data.objects.get('camfill')


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def set_cards(anim_time):
    """Show each explosion card at the video frame that matches the animation time (60 fps source)."""
    for card, obj, node in CARDS:
        k = int((anim_time - card['t0']) * card['fps']) + 1
        visible = 1 <= k <= card['n'] or card.get('always', False)
        k = max(1, min(card['n'], k))
        obj.hide_render = not visible
        if visible:
            # Blender shows video frame (scene frame - frame_start + 1), clamped to the clip BEFORE any offset,
            # so the start is moved rather than the offset
            node.image_user.frame_duration = card['n']
            node.image_user.frame_offset = 0
            node.image_user.frame_start = sc.frame_current - k + 1


def setup(f):
    t = (f - 1) / FPS
    s = next((s for s in E['shots'] if s['t0'] <= t < s['t1']), E['shots'][-1])
    u = (t - s['t0']) / (s['t1'] - s['t0'])
    a = s['a0'] + (t - s['t0']) * s['s0']
    af = a * FPS + 1
    sc.frame_set(int(af), subframe=af - int(af))
    sc.render.motion_blur_shutter = max(0.1, 0.4 * s['s0'])
    set_cards(a)

    ec = s.get('ec', 0)
    e = ease(u) if ec == 0 else (u * u if ec == 1 else (1 - (1 - u) ** 2 if ec == 2 else u))
    p = Vector(s['p0']).lerp(Vector(s['p1']), e)
    look = Vector(s['l0']).lerp(Vector(s['l1']), e)
    impact = s['shake']
    if impact:
        n1 = noise.noise_vector(Vector((t * 2.3, s['t0'], 0.0)))
        n2 = noise.noise_vector(Vector((t * 9.0, s['t0'] + 7, 3.0)))
        look = look + (n1 * 0.10 + n2 * 0.035) * impact * (p - look).length * 0.12
        p = p + n1 * 0.04 * impact
    d = look - p
    cam.location = p
    cam.rotation_mode = 'QUATERNION'
    q = d.to_track_quat('-Z', 'Y')
    hand = s.get('hand')
    if hand:
        # recorded handheld motion; long lenses get proportionally less so the subject stays framed
        k = hand[1] * min(1.0, 50.0 / s['lens'])
        dloc, drot = shakify.shake(hand[0], t, influence=k, loc_scale=0.6, offset=s['t0'] * 1.7)
        q = q @ Euler(drot, 'XYZ').to_quaternion()
        cam.location = p + q.to_matrix() @ Vector(dloc)
    cam.rotation_quaternion = q
    cam.data.lens = s['lens'] + (s['lens1'] - s['lens']) * e
    cam.data.dof.focus_distance = s.get('focus') or max(0.3, d.length)
    cam.data.dof.aperture_fstop = s['fstop']
    hidden = set(s.get('hide') or ())
    for name in HIDEABLE:
        target = bpy.data.collections.get(name) or bpy.data.objects.get(name)
        if target is not None:
            target.hide_render = name in hidden
    sc.render.use_motion_blur = bool(s.get('mb'))
    res = s.get('res') or BASE_RES
    sc.render.resolution_x, sc.render.resolution_y = int(res[0]), int(res[1])
    keep = s.get('keep')
    for key, objs in HOLD.items():
        for obj in objs:
            if keep is not None and not s.get('phone'):
                obj.hide_render = key not in keep           # solo close-up: nobody else in the frame
            elif s.get('phone'):
                if obj.name.startswith('RIG-'):             # the crew still inside the hovering ship must not show from above
                    pos = obj.matrix_world.translation
                    inside = pos.z > 18.9 and pos.y > -8.3 and abs(pos.x) < 3.6
                    for member in [obj] + list(obj.children_recursive):
                        member.hide_render = inside
                    ring = bpy.data.objects.get('ring-' + obj.name[4:])
                    if ring is not None:
                        ring.hide_render = inside
            else:
                obj.hide_render = False
    if FILL is not None:
        FILL.data.energy = s.get('fill', 0.0)


if frames:
    setup(frames[0])
    sc.render.filepath = OUTD + '/check.png'
    preflight.report(preflight.check(sc, 1, E['last']))

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
