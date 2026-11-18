"""THE MEMETRIX: builds scene.blend and edl.json (shots as camera-toolkit data, cues, character tracks).

    blender -b -P scene.py -- [--out W/scene.blend] [--lib W/chars.blend]       (DRY=1: edl.json only, no .blend)

Film time = animation time except in slow-motion shots (speed s0 < 1). Shots are dicts for tools/cine.py, solved once
here against the real geometry (cine.solve) so nothing blocks a face. See HANDOFF.md for the story and the plan.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import assets  # noqa: E402
import cine  # noqa: E402
import mxsets  # noqa: E402
from track import heading_to, make_where  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(key, default=None):
    return ARGS[ARGS.index(key) + 1] if key in ARGS else default


WORK = os.environ.get('W', os.path.expanduser('~/mx_work'))
OUT = arg('--out', WORK + '/scene.blend')
LIB = arg('--lib', WORK + '/chars.blend')
DRY = bool(os.environ.get('DRY'))
FPS = 24
VO = json.load(open(os.path.join(HERE, 'pack', 'vo', 'vo.json')))

# eye heights (m) of the cast, for framing; checked on the animatic
cine.EYES.update({'anon': 1.24, 'slerf': 1.30, 'michi': 1.30, 'mensa': 1.42, 'farter': 1.42, 'alon': 1.38, 'bome': 1.45,
                  'jean': 1.47, 'tri1': 1.48, 'tri2': 1.48, 'tri3': 1.48})
cine.EYE_FWD.update({'mensa': 0.35, 'anon': 0.08})
cine.FRAME_SCALE = 1.35                                       # big cartoon heads: every shot size a bit wider than for people
CAST = {'anon': 'zcat', 'slerf': 'slerf', 'michi': 'michi', 'mensa': 'mensa', 'farter': 'farter', 'alon': 'alon',
        'bome': 'bome', 'jean': 'jeanphil', 'tri1': 'triplet', 'tri2': 'triplet', 'tri3': 'triplet'}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 8
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.volume_bounces = 0
sc.cycles.volume_step_rate = 4.0
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.fps = FPS
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
sc.render.threads_mode = 'FIXED'
sc.render.threads = 4

mxsets.world()
FLOOR = mxsets.ORIGIN['FLOOR']
BASE = mxsets.ORIGIN['BASEMENT']
DOJO = mxsets.ORIGIN['DOJO']
mxsets.build_floor()
mxsets.build_basement()
mxsets.build_dojo()
mxsets.build_rooftop()
ROOF = mxsets.ORIGIN['ROOFTOP']
PROPS = mxsets.collection('PROPS')

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.dof.use_dof = True
cam.data.dof.aperture_ratio = 1.4
cam.data.clip_start = 0.05
cam.data.clip_end = 2000
fill = bpy.data.objects.new('camfill', bpy.data.lights.new('camfill', 'AREA'))
fill.data.size = 1.2
fill.data.color = (1.0, 0.95, 0.88)
fill.data.energy = 0.0
fill.parent = cam
fill.location = (0.5, 0.35, 0.0)
sc.collection.objects.link(fill)
rim = bpy.data.objects.new('rimlight', bpy.data.lights.new('rimlight', 'AREA'))
rim.data.size = 1.0
rim.data.energy = 0.0
sc.collection.objects.link(rim)
sc.render.motion_blur_shutter = 0.45


def F(a):
    return a * FPS + 1


def animate(obj, path, samples, interp='LINEAR'):
    samples = sorted({frame: value for frame, value in samples}.items())
    if not samples:
        return
    obj.animation_data_create()
    action = obj.animation_data.action or bpy.data.actions.new(obj.name + 'Action')
    obj.animation_data.action = action
    dims = len(samples[0][1]) if isinstance(samples[0][1], (tuple, list, Vector)) else 0
    for index in range(max(dims, 1)):
        curve = action.fcurves.find(path, index=index) or action.fcurves.new(path, index=index)
        curve.keyframe_points.add(len(samples))
        flat = []
        for frame, value in samples:
            flat += [frame, value[index] if dims else value]
        curve.keyframe_points.foreach_set('co', flat)
        for point in curve.keyframe_points:
            point.interpolation = interp
        curve.update()


# ================================================================ actors
ONE_SHOT = ('attack1', 'attack2', 'attack3', 'emote', 'hit', 'die', 'ready', 'win', 'lose')


class Actor:
    """A character on a rig empty (heading) and a tilt empty (lean, for the slow-motion backbend)."""

    def __init__(self, name, char):
        self.name = name
        self.rig = bpy.data.objects.new('RIG-' + name, None)
        self.tilt_obj = bpy.data.objects.new('TILT-' + name, None)
        for obj in (self.rig, self.tilt_obj):
            sc.collection.objects.link(obj)
        self.tilt_obj.parent = self.rig
        self.char = char
        self.arm = char['armature'] if char else None
        self.clips = char['clips'] if char else {}
        if char:
            for root in char['roots']:
                root.parent = self.tilt_obj
                root.location = (0, 0, 0)
                root.rotation_euler = (0, 0, 0)
            self.arm.animation_data_create()
        self.keys = []                       # [a, x, y, z, H, step]
        self.tilts = []                      # (a, degrees)
        self.talks = []                      # (a0, a1): speaking, the body nods and sways a little
        self.items = []                      # (a, clip, speed)
        self.pos, self.H = Vector((0, 0, -100)), 180.0

    def cut(self, a, pos, H, clip='idle'):
        """Jump to a place (scene change)."""
        self.pos, self.H = Vector(pos), H
        self.keys.append([a, *self.pos, H, 1])
        if clip:
            self.play(a, clip, hard=True)

    def hold(self, a):
        self.keys.append([a, *self.pos, self.H, 0])

    def turn(self, a, H, dur=0.35):
        self.hold(a)
        self.H = H
        self.keys.append([a + dur, *self.pos, H, 0])

    def face(self, a, other, dur=0.35):
        self.turn(a, heading_to(self.pos, other.pos), dur)

    def walk(self, a, target, speed=1.2, clip='walk', then='idle'):
        target = Vector(target)
        H = heading_to(self.pos, target)
        self.hold(a)
        self.keys.append([a + 0.2, *self.pos, H, 0])
        arrive = a + 0.2 + (target - self.pos).length / speed
        self.play(a, clip)
        self.pos, self.H = target, H
        self.keys.append([arrive, *target, H, 0])
        if then:
            self.play(arrive, then)
        return arrive

    def play(self, a, clip, speed=1.0, hard=False):
        self.items.append((a, clip if clip in self.clips else 'idle', speed, hard))

    def lean(self, a, deg):
        self.tilts.append((a, deg))

    def finish(self, end):
        keys = sorted(self.keys, key=lambda k: k[0])
        loc, rot = [], []
        for i, k in enumerate(keys):
            f = F(k[0])
            if k[5] and i:                                  # a cut: hold the old place up to just before
                j = i - 1                                   # (the last key strictly earlier: two cuts at one moment must not
                while j > 0 and keys[j][0] >= k[0] - 1e-6:  #  hand the second one's 'before' to the first one's target)
                    j -= 1
                prev = keys[j]
                loc.append((f - 0.02, (prev[1], prev[2], prev[3])))
                rot.append((f - 0.02, (0, 0, math.radians(180 - prev[4]))))
            loc.append((f, (k[1], k[2], k[3])))
            rot.append((f, (0, 0, math.radians(180 - k[4]))))
        # unwrap headings so turns take the short way
        for i in range(1, len(rot)):
            z0, z = rot[i - 1][1][2], rot[i][1][2]
            while z - z0 > math.pi:
                z -= math.tau
            while z - z0 < -math.pi:
                z += math.tau
            rot[i] = (rot[i][0], (0, 0, z))
        animate(self.rig, 'location', loc)
        animate(self.rig, 'rotation_euler', rot)
        if self.tilts or self.talks:
            tilts = sorted(self.tilts) or [(0.0, 0.0)]

            def lean_at(t):
                if t <= tilts[0][0]:
                    return tilts[0][1]
                for (t0, d0), (t1, d1) in zip(tilts, tilts[1:]):
                    if t < t1:
                        return d0 + (d1 - d0) * (t - t0) / (t1 - t0)
                return tilts[-1][1]
            samples = {a: (math.radians(d), 0.0, 0.0) for a, d in tilts}
            for a0, a1 in self.talks:
                steps = int((a1 - a0 + 0.6) * 6)
                for k in range(steps + 1):
                    t = a0 - 0.3 + k / 6
                    env = min(1.0, max(0.0, (t - a0 + 0.3) / 0.3), max(0.0, (a1 + 0.3 - t) / 0.3))
                    nod = 2.2 * math.sin(2 * math.pi * 1.6 * t + a0) * env
                    sway = 1.4 * math.sin(2 * math.pi * 0.7 * t + 2 * a0) * env
                    samples[t] = (math.radians(lean_at(t) + nod), math.radians(sway), 0.0)
            animate(self.tilt_obj, 'rotation_euler', [(F(a), v) for a, v in samples.items()], 'BEZIER')
        if not self.arm:
            return
        items = sorted(self.items, key=lambda it: it[0])
        clean = []
        for it in items:
            if clean and abs(it[0] - clean[-1][0]) < 1e-6:
                clean[-1] = it[:3] + (it[3] or clean[-1][3],)
            elif clean and it[1] == clean[-1][1] and it[1] not in ONE_SHOT:
                continue
            else:
                clean.append(it)
        for index, (a, name, speed, hard) in enumerate(clean):
            f0 = F(a)
            f1 = F(clean[index + 1][0]) if index + 1 < len(clean) else F(end)
            if f1 - f0 < 1:
                continue
            action = self.clips[name]
            a0, a1 = action.frame_range
            track = self.arm.animation_data.nla_tracks.new()
            strip = track.strips.new(f'{name}_{index}', int(f0), action)
            strip.scale = (FPS / 30.0) / speed
            length = (a1 - a0) * strip.scale
            strip.repeat = 1.0 if name in ONE_SHOT else max(0.01, (f1 - f0) / max(1e-6, length))
            strip.extrapolation = 'HOLD_FORWARD'
            strip.blend_type = 'REPLACE'
            strip.use_auto_blend = False
            strip.blend_in = 0 if hard or not index else 3


names = list(CAST)
if DRY:
    chars = [None] * len(names)
else:
    chars = assets.load_many(LIB, [CAST[n] for n in names], sc.collection)
A = {n: Actor(n, c) for n, c in zip(names, chars)}
for n, actor in A.items():
    actor.rig['actor'] = n                                     # the camera solver looks through a shot's own subject
OFF = (0, 0, -100)
for actor in A.values():
    actor.cut(0.0, OFF, 180)


def bone_world(actor, bone):
    bpy.context.view_layer.update()
    return actor.arm.matrix_world @ actor.arm.data.bones[bone].head_local


def face_point(actor, eye):
    """The front of the face at eye height in bind pose (ray cast from in front, the rigs face -Y)."""
    bpy.context.view_layer.update()
    origin = Vector((actor.rig.location.x, actor.rig.location.y - 3.0, actor.rig.location.z + eye))
    hit, loc, *_ = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, Vector((0, 1, 0)), distance=4.0)
    return loc if hit else origin + Vector((0, 2.75, 0))


def skin(actor):
    """The actor's skinned body mesh (the one the armature deforms)."""
    return next(o for o in actor.rig.children_recursive if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))


def glue(obj, actor, anchors, radius=0.05):
    """Pin a prop to the deformed skin, not to a bone: parent it to three skin vertices (one near each anchor point,
    or, with a single anchor, three spread out around it). Bones lie about where the surface is on cartoon rigs
    (Slerf's face slides off the head bone in the emote; zcat and alon have no hand weights at all)."""
    body = skin(actor)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    mw_body = body.matrix_world
    pts = [mw_body @ v.co for v in ev.data.vertices]
    assert len(pts) == len(body.data.vertices), 'skin topology changed by a modifier'
    if len(anchors) >= 3:
        picks = [min(range(len(pts)), key=lambda i: (pts[i] - Vector(p)).length) for p in anchors[:3]]
    else:
        c = Vector(anchors[0])
        near = sorted(range(len(pts)), key=lambda i: (pts[i] - c).length)
        r = radius
        cand = [i for i in near if (pts[i] - c).length < r]
        while len(cand) < 12:
            r *= 1.5
            cand = [i for i in near if (pts[i] - c).length < r]
        a = cand[0]
        b = max(cand, key=lambda i: (pts[i] - pts[a]).length)
        cc = max(cand, key=lambda i: (pts[b] - pts[a]).cross(pts[i] - pts[a]).length)
        picks = [a, b, cc]
    keep = obj.matrix_world.copy()
    obj.parent = body
    obj.parent_type = 'VERTEX_3'
    obj.parent_vertices = picks
    obj.matrix_parent_inverse.identity()
    obj.matrix_basis.identity()
    bpy.context.view_layer.update()
    frame = obj.matrix_world.copy()                     # the three vertices' frame, as Blender builds it
    obj.matrix_parent_inverse = frame.inverted()
    obj.matrix_basis = keep
    bpy.context.view_layer.update()
    err = (obj.matrix_world.translation - keep.translation).length
    print('GLUE', obj.name, 'to', body.name, picks, 'error %.4f m' % err)
    return obj


def surface_y(actor, x, z, reach=4.0):
    """How far forward (-Y) the body surface comes at rig-relative (x, z), bind pose, facing -Y. None if nothing there."""
    origin = Vector((actor.rig.location.x + x, actor.rig.location.y - 3.0, actor.rig.location.z + z))
    hit, loc, *_ = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, Vector((0, 1, 0)), distance=reach)
    return loc.y if hit else None


def fitted_shades(actor, name, centre_z, sep, lens_w, lens_h):
    """Big wraparound shades fitted to a face: each lens centred on an eye (rig-relative x = +-sep, z = centre_z),
    laid along the curve of the cheek just clear of the skin (a flat lens in front of a sloth's snout floats 10 cm off
    the eye and the eye shows past it at three-quarter angles); a bridge over the snout and temples back into the head. Measured eye positions, never guessed (see tools/PLAYBOOK.md)."""
    bpy.context.view_layer.update()
    lens_m = mxsets.material('shades_lens', (0.005, 0.005, 0.007), rough=0.04, metal=0.4)
    frame_m = mxsets.material('shades_frame', (0.02, 0.02, 0.022), rough=0.3, metal=0.8)
    rx, ry, rz = actor.rig.location
    parts = []
    inner, outer = {}, {}
    for s in (-1, 1):
        cx = s * sep
        # the face curves back from the snout to the temple: fit a line to the front of each column under the lens and
        # lay the lens along it (wraparound), just clear of the skin, instead of floating it in front of the snout
        cols = []
        for u in (-0.8, -0.4, 0.0, 0.4, 0.8):
            x = cx + u * lens_w / 2
            ys = [surface_y(actor, x, centre_z + v * lens_h / 2) for v in (-0.6, -0.3, 0.0, 0.3, 0.6)]
            ys = [y for y in ys if y is not None]
            if ys:
                cols.append((x, min(ys)))
        mx_ = sum(x for x, _ in cols) / len(cols)
        my_ = sum(y for _, y in cols) / len(cols)
        b = sum((x - mx_) * (y - my_) for x, y in cols) / sum((x - mx_) ** 2 for x, _ in cols)
        b = max(-0.9, min(0.9, b))
        c = min(y - (my_ + b * (x - mx_)) for x, y in cols)            # every column stays behind the lens
        loc = Vector((rx + cx, my_ + b * (cx - mx_) + c - 0.022, rz + centre_z))
        yaw = math.atan(b)
        across = Vector((math.cos(yaw), math.sin(yaw), 0))
        lens = mxsets.sphere(f'{name}_lens{s}', 1.0, loc, lens_m, PROPS, scale=(lens_w / 2, 0.018, lens_h / 2))
        rim = mxsets.sphere(f'{name}_rim{s}', 1.0, loc + Vector((-math.sin(yaw), math.cos(yaw), 0)) * 0.006, frame_m, PROPS,
                            scale=(lens_w / 2 + 0.012, 0.012, lens_h / 2 + 0.012))
        for o in (lens, rim):
            o.rotation_euler = (0, 0, yaw)
        parts += [lens, rim]
        print(f'SHADES lens {s}: wrap {math.degrees(yaw):.0f} deg, {(my_ + b * (cx - mx_)) - loc.y:.3f} m off the skin')
        inner[s] = loc - across * (s * lens_w / 2) + Vector((0, 0, lens_h * 0.18))
        outer[s] = loc + across * (s * lens_w / 2) + Vector((0, 0.01, lens_h * 0.18))
    snout = surface_y(actor, 0.0, centre_z + lens_h * 0.18) or inner[1].y
    top = Vector((rx, min(snout - 0.012, inner[1].y), inner[1].z))
    rods = [(inner[-1], top), (top, inner[1])]
    for s in (-1, 1):
        rods.append((outer[s], outer[s] + Vector((s * 0.02, 0.22, 0.01))))
    for k, (p0, p1) in enumerate(rods):
        d = p1 - p0
        rod = mxsets.cylinder(f'{name}_rod{k}', 0.007, d.length, (p0 + p1) / 2, frame_m, PROPS, verts=10)
        rod.rotation_mode = 'QUATERNION'
        rod.rotation_quaternion = d.to_track_quat('Z', 'Y')
        parts.append(rod)
    holder = bpy.data.objects.new(name, None)
    PROPS.objects.link(holder)
    holder.location = (rx, inner[1].y, rz + centre_z)
    bpy.context.view_layer.update()
    for o in parts:
        mw = o.matrix_world.copy()
        o.parent = holder
        o.matrix_world = mw
        o.visible_shadow = False
    return holder


# props on bones: posed at the origin in bind pose first
if not DRY:
    for k, actor in enumerate(A.values()):                     # spread out, or the face ray hits whoever stands in front
        actor.rig.location = (k * 6.0, 0, -50)
        actor.rig.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    sl = A['slerf'].rig.location                                  # eyes measured on a front grid: z 1.255, x +-0.155
    shades = fitted_shades(A['slerf'], 'shades_slerf', centre_z=1.272, sep=0.155, lens_w=0.20, lens_h=0.13)
    glue(shades, A['slerf'], [face_point(A['slerf'], 1.26) + Vector((x, 0, 0)) for x in (-0.15, 0.15)] +
         [sl + Vector((0, surface_y(A['slerf'], 0, 1.42) - sl.y, 1.42))])
    for n in ('jean', 'tri1', 'tri2', 'tri3'):
        shades = mxsets.sunglasses('shades_' + n, PROPS, width=0.2)
        p = face_point(A[n], cine.EYES[n] + 0.02) + Vector((0, -0.03, 0))
        shades.location = p
        r = A[n].rig.location
        glue(shades, A[n], [Vector((r.x + x, surface_y(A[n], x, cine.EYES[n]) or p.y, r.z + cine.EYES[n])) for x in (-0.05, 0.05)] +
             [Vector((r.x, surface_y(A[n], 0, cine.EYES[n] + 0.1) or p.y, r.z + cine.EYES[n] + 0.1))])
    RED_SLERF = mxsets.candle('candle_red_s', 'red', PROPS)
    GREEN_SLERF = mxsets.candle('candle_green_s', 'green', PROPS)
    for c_, bone in ((RED_SLERF, 'mixamorig:RightHand'), (GREEN_SLERF, 'mixamorig:LeftHand')):
        hand = bone_world(A['slerf'], bone)
        c_.location = hand + Vector((0, -0.08, 0.05))
        glue(c_, A['slerf'], [hand], radius=0.06)
    zbones = [b.name for b in A['anon'].arm.data.bones]
    zarm = next((b for b in ('mixamorig:RightHand', 'mixamorig:RightForeArm', 'mixamorig:RightArm') if b in zbones), zbones[-1])
    RED_ANON = mxsets.candle('candle_red_a', 'red', PROPS)
    RED_ANON.location = bone_world(A['anon'], zarm) + Vector((0, -0.12, 0.0))
    glue(RED_ANON, A['anon'], [bone_world(A['anon'], zarm)], radius=0.05)
    COOKIE = mxsets.cookie('cookie', PROPS)
    CARD = mxsets.bent_card('card', PROPS, os.path.join(HERE, 'pack', 'cards', 'marketcrash.webp'))
    abones = [b.name for b in A['alon'].arm.data.bones]
    ahand = next((b for b in ('mixamorig:RightHand', 'mixamorig:LeftHand') if b in abones), abones[-1])
    CARD.rotation_euler = (math.radians(90), 0, 0)
    CARD.location = bone_world(A['alon'], ahand) + Vector((0.0, -0.06, -0.12))
    glue(CARD, A['alon'], [bone_world(A['alon'], ahand)], radius=0.05)
    COOKIE.location = A['bome'].rig.location + Vector((0.45, -0.35, 1.0))     # held out in front, rides the book's bob
    glue(COOKIE, A['bome'], [COOKIE.location.copy()], radius=0.15)
    COOKIE['actor'] = 'bome'
    CARD['actor'] = 'alon'
# Slerf's training rig: each paw can follow an IK target (empties on his lean pivot, so they lean with him). Influence 0
# leaves the clip alone; keyed up to 1 for the blocks and the push in the dojo fight.
SLERF_IK = {}
if not DRY:
    sl_rig = A['slerf'].rig.location.copy()
    for side, sx in (('Right', -1), ('Left', 1)):
        shoulder = bone_world(A['slerf'], f'mixamorig:{side}Arm') - sl_rig
        hand = bone_world(A['slerf'], f'mixamorig:{side}Hand') - sl_rig
        tgt = bpy.data.objects.new(f'ik_slerf_{side}', None)
        sc.collection.objects.link(tgt)
        tgt.parent = A['slerf'].tilt_obj
        tgt.location = hand
        con = A['slerf'].arm.pose.bones[f'mixamorig:{side}ForeArm'].constraints.new('IK')
        con.name = 'IK'
        con.target = tgt
        con.chain_count = 2
        con.influence = 0.0
        SLERF_IK[side] = dict(tgt=tgt, shoulder=shoulder, hand=hand, reach=(hand - shoulder).length, sx=sx, keys=[], inf=[])

VIS = []                     # (object name, [(a, visible)])


def show(obj_name, steps):
    VIS.append((obj_name, steps))


# ================================================================ timeline
FILM = 0.0
ANIM = 0.0
SHOTS = []
CUES = []
NOTES = []
TITLE = 5.0                  # the opening is 2D in the finish: code rain, title, the typed messages
FILM = TITLE
ANIM = TITLE


def shot(name, dur, cam_shot, where_set, speed=1.0, hand=('INVESTIGATION', 0.3), **extra):
    """A shot of film length `dur` (animation advances dur * speed)."""
    global FILM, ANIM
    SHOTS.append(dict(name=name, t0=round(FILM, 4), t1=round(FILM + dur, 4), a0=round(ANIM, 4), s0=speed, set=where_set,
                      cam=cam_shot, hand=list(hand) if hand else None, **extra))
    FILM += dur
    ANIM += dur * speed


def line(line_id, cams, where_set, lead=0.1, pad=0.25, weights=None, actor=None, talk=True):
    """A recorded line with its shots. The line starts `lead` into the first shot; the shots share line + pad."""
    dur = VO[line_id]['dur']
    CUES.append((line_id, round(FILM + lead, 4)))
    speakers = {'tri': ['tri1', 'tri2', 'tri3'], 'mom': []}.get(VO[line_id]['who'], [VO[line_id]['who']])
    for who in speakers:
        if who in A:
            A[who].talks.append((ANIM + lead, ANIM + lead + dur))
    total = lead + dur + pad
    weights = weights or [1] * len(cams)
    for i, c in enumerate(cams):
        shot(f'{line_id}_{i}', total * weights[i] / sum(weights), c, where_set)
    return total


def S(subject, **kw):
    return dict(subject=subject, **kw)


# ---------------------------------------------------------------- 1. the trading floor: the chart has Anon
anon, slerf, michi, mensa, farter, alon, bome, jean = (A[n] for n in ('anon', 'slerf', 'michi', 'mensa', 'farter', 'alon', 'bome', 'jean'))
tris = [A['tri1'], A['tri2'], A['tri3']]
mxsets.prop('exchange', 'ex_desk', mxsets.collection('FLOOR'), FLOOR + Vector((0, -0.7, 0)), 180, 0.75)
ANON_DESK = FLOOR + Vector((0, -2.25, 0))
a = ANIM
anon.cut(a, ANON_DESK, 0)
anon.play(a, 'idle', 0.6)
michi.cut(a, FLOOR + Vector((-6.5, -9.0, 0)), 20)
shot('floor_establish', 3.0, S('anon', size='EWS', angle=38, bearing=200, move='crane', amount=-22, lens=24, frame='center', fstop=8.0), 'FLOOR')
shot('anon_screen', 1.6, S('anon', size='MCU', bearing=8, angle=4, move='push', amount=0.15, lens=50, frame='center', fstop=2.0,
                           clutter_max=0.5), 'FLOOR')
line('a01', [S('anon', size='CU', bearing=-25, lens=75, frame='right', fstop=1.8, move='push', amount=0.06)], 'FLOOR')
michi.walk(ANIM - 1.5, FLOOR + Vector((-3.0, -2.9, 0)), speed=1.3)
line('m01', [S('michi', size='WS', bearing=-40, lens=35, frame='left', fstop=2.8, move='track'),
             S('michi', size='MCU', bearing=-30, lens=60, frame='left', fstop=2.4)], 'FLOOR', weights=[1, 1.2])
anon.face(ANIM - 1.2, michi)
michi.face(ANIM - 1.2, anon)
line('a02', [cine.reaction('anon', 85)], 'FLOOR')
line('m02', [S('michi', size='MCU', bearing=-22, lens=70, frame='left', fstop=2.2, move='push', amount=0.12)], 'FLOOR')

# ---------------------------------------------------------------- 2. the choice, under the bull
a = ANIM
SLERF_AT = FLOOR + Vector((0, 7.4, 0))
slerf.cut(a, SLERF_AT, 180)
anon.cut(a, FLOOR + Vector((0, 2.2, 0)), 0)
michi.cut(a, FLOOR + Vector((-1.4, 0.4, 0)), 15)
anon.walk(a, FLOOR + Vector((0, 5.7, 0)), speed=1.6)
shot('aisle_walk', 3.0, S('anon', size='WS', bearing=160, lens=35, frame='center', move='track', fstop=2.8, angle=12, lead=False), 'FLOOR')
shot('slerf_reveal', 1.8, S('slerf', size='WS', angle='low', bearing=40, lens=28, frame='center', move='push', amount=0.2, fstop=4.0), 'FLOOR')
line('s01', [S('slerf', over='anon', size='MS', lens=50, frame=(-1 / 3, 1 / 3), fstop=2.4),
             S('slerf', size='MCU', angle='low', bearing=12, lens=65, frame='left', move='push', amount=0.18, fstop=2.0)], 'FLOOR', weights=[1, 1.4])
line('a03', [S('anon', size='CU', bearing=25, lens=70, frame='right', fstop=2.0)], 'FLOOR')
line('s02', [S('slerf', size='CU', bearing=0, lens=85, frame='center', fstop=1.8)], 'FLOOR', pad=0.45)
slerf.play(ANIM, 'emote', 0.6)                                  # the paws come out with the candles
CANDLES_ON = ANIM
line('s03', [S('slerf', size='MS', bearing=-30, angle='low', lens=40, frame='center', move='arc', amount=50, fstop=2.8),
             S('slerf', size='MS', bearing=-8, angle=-6, lens=45, frame='center', fstop=2.4, move='push', amount=0.12),
             S('slerf', size='MCU', bearing=35, lens=70, frame='left', fstop=2.0, move='push', amount=0.12)], 'FLOOR',
     weights=[1.2, 1.2, 1.2])
line('a04', [S('anon', size='CU', bearing=30, lens=75, frame='right', dutch=6, fstop=1.8)], 'FLOOR')
line('s04', [S('slerf', size='WS', bearing=90, lens=35, frame='left', fstop=4.0, look_offset=(0, -1.0, 0))], 'FLOOR', pad=0.45)
TAKE = ANIM
anon.play(TAKE, 'attack1', 0.7)
shot('take_red', 1.2, S('anon', size='MS', bearing=-45, lens=45, frame='right', fstop=2.0, move='push', amount=0.2), 'FLOOR')
anon.play(ANIM, 'emote', 0.9)
shot('swallow', 1.5, S('anon', size='MCU', bearing=0, lens=60, frame='center', fstop=2.0, move='dolly_zoom', amount=-0.2), 'FLOOR',
     glitch='rain_out')
if not DRY:
    show('candle_red_s', [(0, False), (CANDLES_ON, True), (TAKE + 0.45, False)])
    show('candle_red_a', [(0, False), (TAKE + 0.45, True), (ANIM - 0.4, False)])
    show('candle_green_s', [(0, False), (CANDLES_ON, True), (ANIM, False)])

# ---------------------------------------------------------------- 3. the basement of the real
a = ANIM
anon.cut(a, BASE + Vector((0.2, -1.3, 0)), 160, clip='die')
anon.play(a, 'die', 0.25)
slerf.cut(a, BASE + Vector((0.6, 0.4, 0)), 200)
mensa.cut(a, BASE + Vector((2.5, 0.72, 0)), 20)                       # 30 cm back from the screens
farter.cut(a, BASE + Vector((4.4, 2.0, 0)), 200)
michi.cut(a, BASE + Vector((-1.6, 0.6, 0)), 140)
shot('wake_bird', 2.4, S('anon', distance=3.6, angle='bird', bearing=0, lens=28, frame='center', move='arc', amount=-40, fstop=5.6, eye=0.25, clutter_max=0.3),
     'BASEMENT', glitch='rain_in')
anon.play(ANIM - 0.3, 'ready', 0.8)
line('s05', [S('slerf', size='MS', angle=5, bearing=0, lens=35, frame='center', fstop=3.2),
             S('anon', size='MCU', angle='high', bearing=10, lens=50, frame='right', fstop=2.4)], 'BASEMENT', weights=[1.3, 1])
line('mo1', [S('slerf', distance=4.0, bearing=-40, lens=24, frame='right', fstop=5.6, look_offset=(-9.2, 6.0, 1.0), move='push', amount=0.1)], 'BASEMENT')
slerf.turn(ANIM, 240)
line('s06', [S('slerf', size='MCU', bearing=-20, lens=60, frame='right', fstop=2.2)], 'BASEMENT', pad=0.3)
mensa.play(ANIM, 'idle', 1.4)
line('n01', [S('mensa', size='MS', bearing=150, lens=40, frame='left', fstop=2.8, move='push', amount=0.15),
             S('mensa', size='CU', bearing=-80, lens=70, frame='right', fstop=2.0)], 'BASEMENT', weights=[1.2, 1])
farter.play(ANIM, 'emote', 0.8)
line('f01', [S('farter', size='MS', bearing=0, lens=50, frame='center', fstop=2.4, move='push', amount=0.1)], 'BASEMENT', pad=0.35)

# ---------------------------------------------------------------- 4. the training program
a = ANIM
anon.cut(a, DOJO + Vector((-1.3, 0, 0)), 90)
slerf.cut(a, DOJO + Vector((1.3, 0, 0)), 270)
line('n02', [cine.establish('anon', 22)], 'DOJO', pad=0.5, lead=0.3)
line('a05', [cine.vertigo('anon', 40)], 'DOJO', pad=0.4)
line('s07', [S('slerf', size='MCU', angle='low', bearing=-20, lens=50, frame='left', fstop=2.2)], 'DOJO')
FIGHT = ANIM
STRIKE_X = 1.3 - 1.35                                          # Anon steps in to striking distance (1.35 m centre to centre:
                                                               # at 0.95 his bag went into Slerf's belly on every swing)
anon.walk(FIGHT - 0.95, DOJO + Vector((STRIKE_X, 0, 0)), speed=2.2, clip='walk', then=None)
anon.play(FIGHT, 'attack1', 1.2)
anon.play(FIGHT + 0.9, 'attack2', 1.2)
anon.play(FIGHT + 1.8, 'attack3', 1.2)
slerf.play(FIGHT, 'idle', 0.4)
slerf.hold(FIGHT)
anon.hold(FIGHT + 2.72)                                         # the push lands: he goes down as he slides back 1.1 m
anon.play(FIGHT + 2.72, 'die', 1.8)                             # ('hit' then 'die' popped him upright between the two;
                                                                # at 1.0x the clip staggers 1.5 s before he drops)
anon.pos = DOJO + Vector((STRIKE_X - 1.1, 0, 0))
anon.keys.append([FIGHT + 3.35, *anon.pos, anon.H, 0])
slerf.hold(FIGHT + 2.35)                                        # one slow step in for the push
slerf.pos = DOJO + Vector((1.0, 0, 0))
slerf.keys.append([FIGHT + 2.7, *slerf.pos, slerf.H, 0])
# Slerf, bored: blocks swing one with the right paw, swing two with the left, leans out of swing three, then one lazy push
slerf.lean(FIGHT + 1.85, 0)
slerf.lean(FIGHT + 2.1, -16)
slerf.lean(FIGHT + 2.4, -16)
slerf.lean(FIGHT + 2.65, 4)
slerf.lean(FIGHT + 3.0, 0)
if not DRY:
    def paw(side, where_, fwd, up=0.05, inward=0.35):
        ik = SLERF_IK[side]
        sh = ik['shoulder']
        return Vector((sh.x * inward, sh.y - fwd * ik['reach'], sh.z + up))

    def block(side, contact):
        ik = SLERF_IK[side]
        ik['keys'] += [(contact - 0.3, paw(side, 0, 0.9)), (contact + 0.5, paw(side, 0, 0.9))]
        ik['inf'] += [(contact - 0.28, 0.0), (contact - 0.08, 1.0), (contact + 0.22, 1.0), (contact + 0.55, 0.0)]
    block('Right', FIGHT + 0.25)
    block('Left', FIGHT + 1.15)
    R_ = SLERF_IK['Right']
    R_['keys'] += [(FIGHT + 2.3, paw('Right', 0, 0.45, up=0.0)), (FIGHT + 2.55, paw('Right', 0, 0.4, up=-0.05, inward=0.5)),
                   (FIGHT + 2.72, paw('Right', 0, 0.98, up=-0.12, inward=0.2)), (FIGHT + 3.0, paw('Right', 0, 0.98, up=-0.12, inward=0.2))]
    R_['inf'] += [(FIGHT + 2.3, 0.0), (FIGHT + 2.5, 1.0), (FIGHT + 3.0, 1.0), (FIGHT + 3.45, 0.0)]
    A['slerf'].arm.animation_data.action = bpy.data.actions.new('slerf_ik_influence')   # its own action, on top of the NLA clips
    for side, ik in SLERF_IK.items():
        animate(ik['tgt'], 'location', [(F(a_), tuple(v)) for a_, v in ik['keys']], 'BEZIER')
        animate(A['slerf'].arm, f'pose.bones["mixamorig:{side}ForeArm"].constraints["IK"].influence',
                [(F(a_), v) for a_, v in ik['inf']], 'BEZIER')
shot('fight_track', 1.5, cine.chaos('anon', 28), 'DOJO')
shot('fight_arc', 1.7, S('anon', size='WS', bearing=120, lens=32, frame='center', move='arc', amount=120, fstop=4.0, angle=18,
                         look_offset=(0.67, 0, -0.3), **{'with': ['slerf']}), 'DOJO')
shot('fight_fall', 1.4, S('anon', size='WS', angle='high', bearing=80, lens=35, frame='center', fstop=3.2), 'DOJO')
line('s08', [S('anon', size='WS', angle='high', bearing=150, lens=35, frame='left', fstop=2.8, eye=0.35),
             S('slerf', size='MCU', angle='low', bearing=20, lens=55, frame='right', fstop=2.0)], 'DOJO', weights=[1, 1.2])

# ---------------------------------------------------------------- 5. the waiting room and the book
a = ANIM
ALON_AT = BASE + Vector((-2.6, 5.4, 0))
BOME_AT = BASE + Vector((-5.9, 5.2, 0.35))
alon.cut(a, ALON_AT, 160)
bome.cut(a, BOME_AT, 170)
anon.cut(a, BASE + Vector((-2.2, 2.4, 0)), 0)
for k in range(40):                                            # the book floats, bobbing gently
    t = a + k * 0.5
    bome.keys.append([t, BOME_AT.x, BOME_AT.y, BOME_AT.z + 0.08 * math.sin(k * 0.9), 170 + 6 * math.sin(k * 0.5), 0])
anon.cut(a, BASE + Vector((-2.4, 4.0, 0)), 0)
anon.face(a, alon, 0.01)
shot('waiting_room', 1.4, S('alon', size='WS', bearing=200, lens=28, frame='left', fstop=4.0, look_offset=(0.1, -0.8, 0)), 'BASEMENT')
CARD_AT = ALON_AT + Vector((0.12, -0.42, 0.82))
line('k01', [S('alon', size='MCU', bearing=45, lens=60, frame='right', fstop=2.0)], 'BASEMENT')
line('a06', [S('anon', size='CU', bearing=30, lens=70, frame='left', fstop=2.0)], 'BASEMENT')
BEND = ANIM
line('k02', [S('alon', distance=1.2, bearing=-10, lens=85, frame='center', fstop=4.0, look_offset=(0.12, -0.42, -0.56), focus=0.9),
             S('alon', size='CU', bearing=-50, lens=75, frame='right', fstop=1.8, move='push', amount=0.08)], 'BASEMENT', weights=[1.4, 1], pad=0.9)
anon.walk(ANIM - 0.3, BASE + Vector((-4.4, 3.9, 0)), speed=1.3)
anon.face(ANIM + 1.2, bome)
shot('book_reveal', 1.6, S('bome', size='MS', bearing=10, lens=40, frame='center', move='crane', amount=-12, fstop=2.8), 'BASEMENT')
line('b01', [S('bome', size='MCU', bearing=-40, lens=60, frame='right', fstop=2.2)], 'BASEMENT')
COOKIE_T = ANIM + 1.3
line('b02', [S('anon', size='CU', bearing=40, lens=75, frame='left', fstop=1.8),
             S('bome', size='MCU', bearing=-25, lens=60, frame='right', fstop=2.2, move='push', amount=0.1)], 'BASEMENT', pad=0.5, weights=[0.8, 1])

# ---------------------------------------------------------------- 6. the agents, on the rooftop (the bullet-time dodge)
a = ANIM
anon.cut(a, ROOF + Vector((0, 4.2, 0)), 0)
michi.cut(a, ROOF + Vector((-2.8, 1.4, 0)), 30)
jean.cut(a, ROOF + Vector((0, 8.0, 0)), 180)
for t_, (x, y) in zip(tris, ((-3.2, 6.4), (3.2, 6.4), (0.0, -3.5))):
    t_.cut(a, ROOF + Vector((x, y, 0)), heading_to((x, y), (0, 4.2)))
tris[2].walk(a + 0.5, ROOF + Vector((0.0, -2.0, 0)), speed=0.8)
shot('agents_wide', 2.6, S('anon', size='EWS', angle=4, bearing=200, lens=20, frame='center', fstop=8.0, move='crane', amount=6,
                           look_offset=(0, 2.0, 1.2)), 'ROOFTOP')
line('j01', [S('jean', size='MCU', angle='low', bearing=0, lens=60, frame='center', move='push', amount=0.2, fstop=2.0)], 'ROOFTOP', pad=0.3)
line('t01', [S('anon', size='WS', bearing=0, lens=24, frame='center', fstop=4.0, angle=12, look_offset=(0, 3.0, 0.2))], 'ROOFTOP', pad=0.3)
FIRE = ANIM
jean.play(FIRE, 'attack1', 1.0)
shot('fire', 1.0, S('jean', size='MS', bearing=-25, lens=40, frame='right', fstop=2.8, angle='low'), 'ROOFTOP')
# bullet time: the candles crawl past; Anon bends back; the camera circles him
BT = ANIM
BT_FILM = 5.2
BT_SPEED = 0.08
anon.play(BT, 'hit', 0.12)
anon.lean(BT, 0)
anon.lean(BT + 0.30, -52)
anon.lean(BT + BT_FILM * BT_SPEED + 0.25, -52)
anon.lean(BT + BT_FILM * BT_SPEED + 0.6, 0)
anon.play(BT + BT_FILM * BT_SPEED + 0.6, 'idle')                 # the slowed 'hit' clip would run ~8 s past the dodge
shot('bullet_time', BT_FILM, S('anon', size='WS', angle='low', bearing=60, lens=30, frame='center', move='arc', amount=300, fstop=4.0,
                                  ease='smooth', eye=0.8), 'ROOFTOP', speed=BT_SPEED, hand=None, bullet=True)
PROJ = []
for k in range(7):                                                     # red candles from Jeanphil's hand, past Anon's leaned body
    start = ROOF + Vector((0.22 + 0.04 * (k - 3), 7.35, 0.98 + 0.03 * k))
    end = ROOF + Vector((0.5 * (k - 3) * 0.6, -6.0, 1.05 + 0.12 * (k % 3)))
    t_on = FIRE + 0.35 + k * 0.03
    PROJ.append((start, end, t_on, t_on + 1.15))
shot('after_dodge', 1.0, S('anon', size='MS', bearing=20, lens=40, frame='center', fstop=2.8), 'ROOFTOP')
line('m03', [S('michi', size='MCU', bearing=-30, lens=60, frame='right', fstop=2.0)], 'ROOFTOP')
line('a08', [cine.hero('anon', 45)], 'ROOFTOP')
# second barrage: he lifts a paw, the candles stop in the air, turn green and drop
FIRE2 = ANIM
jean.play(FIRE2, 'attack2', 1.0)
anon.play(FIRE2 + 0.2, 'win', 0.8)
STOP = []
for k in range(7):
    start = ROOF + Vector((0.22 + 0.04 * (k - 3), 7.35, 0.98 + 0.03 * k))
    hang = ROOF + Vector((0.3 * (k - 3), 5.6 + 0.15 * (k % 2), 1.0 + 0.12 * (k % 3)))
    STOP.append((start, hang, FIRE2 + 0.3 + k * 0.04))
shot('freeze_ots', 1.9, S('jean', over='anon', size='MS', lens=50, frame=(-1 / 3, 1 / 3), fstop=4.0), 'ROOFTOP')
TURN_GREEN = ANIM
shot('freeze_insert', 1.6, S('anon', size='MCU', bearing=0, lens=40, frame='center', fstop=5.6, look_offset=(0, 1.5, -0.2), move='arc',
                             amount=25), 'ROOFTOP')
line('j02', [S('jean', size='MCU', angle=-10, bearing=20, lens=70, frame='left', dutch=-8, fstop=2.0)], 'ROOFTOP', pad=0.4)
line('a09', [S('anon', size='CU', bearing=-20, lens=75, frame='right', fstop=1.8, move='push', amount=0.12, ease='settle')], 'ROOFTOP', pad=0.4)
shot('final_hero', 2.6, S('anon', size='MLS', angle='low', bearing=0, lens=28, frame='center', move='pull', amount=0.6, fstop=4.0), 'ROOFTOP')
END_FILM = FILM
END_A = ANIM

# ================================================================ projectiles, card, cookie (animated objects)
if not DRY:
    proj_objs = []
    for k, (start, end, t_on, t_off) in enumerate(PROJ):
        c = mxsets.candle(f'proj{k}', 'red', PROPS, size=2.6, trail=1.6)
        c.rotation_euler = (math.radians(90), 0, 0)
        animate(c, 'location', [(F(0), (0, 0, -50)), (F(t_on) - 0.02, (0, 0, -50)), (F(t_on), tuple(start)), (F(t_off), tuple(end)),
                                (F(t_off) + 0.02, (0, 0, -50))])
        proj_objs.append(c.name)
    for k, (start, hang, t_on) in enumerate(STOP):
        for colour in ('red', 'green'):
            c = mxsets.candle(f'stop{k}_{colour}', colour, PROPS, size=2.6, trail=0.0)
            c.rotation_euler = (math.radians(90), 0, 0)
            t_hang = t_on + 0.45
            if colour == 'red':
                keys = [(F(0), (0, 0, -50)), (F(t_on) - 0.02, (0, 0, -50)), (F(t_on), tuple(start)), (F(t_hang), tuple(hang)),
                        (F(TURN_GREEN + 0.6 + k * 0.08), tuple(hang)), (F(TURN_GREEN + 0.6 + k * 0.08) + 0.02, (0, 0, -50))]
            else:
                drop = Vector((hang.x, hang.y, 0.06))
                t_g = TURN_GREEN + 0.6 + k * 0.08
                keys = [(F(0), (0, 0, -50)), (F(t_g) - 0.02, (0, 0, -50)), (F(t_g), tuple(hang)), (F(t_g + 0.5), tuple(hang)),
                        (F(t_g + 0.9), tuple(drop))]
            animate(c, 'location', keys)
    animate(CARD, 'modifiers["bend"].angle', [(F(BEND + 0.6), 0.0), (F(BEND + 2.0), math.radians(160))], 'BEZIER')
    show('cookie', [(0, False), (COOKIE_T, True)])
    show('card', [(0, False), (BEND - 6.0, True), (BEND + 8.0, False)])
    for actor in A.values():
        actor.finish(END_A + 2.0)
    for name, steps in VIS:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        base = tuple(obj.scale)                                    # keep the object's own size (the card is 16 x 22 cm)

        def sized(on):
            return base if on else tuple(v * 1e-4 for v in base)
        samples = []
        for a_, on in steps:
            samples.append((F(a_) - 0.02, samples[-1][1] if samples else sized(on)))
            samples.append((F(a_), sized(on)))
        animate(obj, 'scale', samples[1:], 'CONSTANT')

# ================================================================ solve every shot against the built scene
if not DRY:
    for s_ in SHOTS:
        if s_['name'] == 'k02_0':
            a_mid = s_['a0'] + (s_['t1'] - s_['t0']) * 0.5
            sc.frame_set(int(F(a_mid)))
            feet, head = make_where({n: sorted(x.keys, key=lambda k: k[0]) for n, x in A.items()})('alon', a_mid)
            card_at = CARD.matrix_world.translation
            s_['cam']['look_offset'] = list(card_at - cine.eye_point('alon', feet, head))
            print('CARD at', tuple(round(v, 2) for v in card_at), 'offset', [round(v, 2) for v in s_['cam']['look_offset']])

tracks = {n: actor.keys for n, actor in A.items()}
tracks = {n: sorted(k, key=lambda x: x[0]) for n, k in tracks.items()}
where = make_where(tracks)
solved = 0
if not DRY:
    for s in SHOTS:
        a_mid = s['a0'] + (s['t1'] - s['t0']) * s['s0'] * 0.5
        sc.frame_set(int(F(a_mid)))
        cam_shot, note = cine.solve(s['cam'], where, sc, s['a0'], s['a0'] + (s['t1'] - s['t0']) * s['s0'], samples=5)
        if note != 'clear':
            NOTES.append(f"{s['name']}: {note}")
            s['cam'] = cam_shot
            solved += 1
for note in NOTES:
    print('SOLVE', note)
problems = cine.check_rules([dict(subject=s['cam']['subject'], size=s['cam'].get('size'), bearing=s['cam'].get('bearing', 30),
                                  over=s['cam'].get('over')) for s in SHOTS])
for p in problems:
    k = int(p.split(':')[0].split()[1])
    print('RULES', SHOTS[k - 1]['name'], '->', SHOTS[k]['name'], p)

def film_of(a):
    for s_ in SHOTS:
        span = (s_['t1'] - s_['t0']) * s_['s0']
        if s_['a0'] - 1e-6 <= a < s_['a0'] + span:
            return round(s_['t0'] + (a - s_['a0']) / s_['s0'], 4)
    return None


EVENTS = {'take': TAKE + 0.45, 'fight': FIGHT, 'fall': FIGHT + 3.55, 'push': FIGHT + 2.72, 'card_bend': BEND + 0.6, 'cookie': COOKIE_T, 'fire': FIRE + 0.3,
          'bullet_time': BT, 'fire2': FIRE2 + 0.3, 'turn_green': TURN_GREEN + 0.6, 'drop': TURN_GREEN + 1.3}
EVENTS.update({f'swing{k}': FIGHT + 0.9 * k + 0.25 for k in range(3)})
EVENTS = {k: film_of(v) for k, v in EVENTS.items()}
cue_rows = [dict(id=i, f=t, dur=VO[i]['dur'], who=VO[i]['who'], sub=VO[i]['sub']) for i, t in CUES]
edl = dict(fps=FPS, title=TITLE, events=EVENTS, cue_rows=cue_rows, end=round(END_FILM, 4), last=int(round(END_FILM * FPS)), shots=SHOTS, cues=CUES, tracks=tracks,
           eyes=cine.EYES, eye_fwd=cine.EYE_FWD, frame_scale=cine.FRAME_SCALE, notes=NOTES)
with open(os.path.join(HERE, 'edl.json'), 'w') as fh:
    json.dump(edl, fh, indent=0)
print(f'EDL {len(SHOTS)} shots, film {END_FILM:.1f} s ({edl["last"]} frames), {len(CUES)} cues, {solved} shots moved by the solver')
if not DRY:
    sc.frame_start, sc.frame_end = 1, int(F(END_A + 1))
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=False)
    print('SAVED', OUT)
