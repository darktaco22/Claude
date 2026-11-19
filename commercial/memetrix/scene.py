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
from mathutils import Matrix, Vector

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
        base = clip.split('@')[0]
        self.items.append((a, clip if base in self.clips else 'idle', speed, hard))

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
            elif clean and it[1] == clean[-1][1] and it[1].split('@')[0] not in ONE_SHOT:
                continue
            else:
                clean.append(it)
        for index, (a, name, speed, hard) in enumerate(clean):
            f0 = F(a)
            f1 = F(clean[index + 1][0]) if index + 1 < len(clean) else F(end)
            if f1 - f0 < 1:
                continue
            base, _, frac = name.partition('@')
            action = self.clips[base]
            a0, a1 = action.frame_range
            track = self.arm.animation_data.nla_tracks.new()
            strip = track.strips.new(f'{name}_{index}', int(f0), action)
            if frac:                                               # a held pose: half a frame of the clip stretched over the span
                hf = a0 + (a1 - a0) * float(frac)
                strip.action_frame_start, strip.action_frame_end = hf, hf + 0.5
                strip.scale = max(1.0, (f1 - f0 + 2) / 0.5)
                strip.repeat = 1.0
            else:
                strip.scale = (FPS / 30.0) / speed
                length = (a1 - a0) * strip.scale
                strip.repeat = 1.0 if base in ONE_SHOT else max(0.01, (f1 - f0) / max(1e-6, length))
            strip.extrapolation = 'HOLD_FORWARD'
            strip.blend_type = 'REPLACE'
            strip.use_auto_blend = False
            strip.blend_in = 0 if hard or not index else (6 if name == 'die' else 3)


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


def glue(obj, actor, anchors, radius=0.05, only=None):
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
    if only is not None:                                    # far-away stand-ins for vertices outside the allowed set
        pts = [p if i in only else p + Vector((0, 0, 1000)) for i, p in enumerate(pts)]
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


def fitted_shades(actor, name, centre_z, sep, lens_w, lens_h, max_wrap=0.9):
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
        b = max(-max_wrap, min(max_wrap, b))
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
    # the agents' shades, fitted the same way to eyes measured on front and side grids (the old ones sat on Jeanphil's brow
    # and 10 cm above the triplets' eyes, on plain wood, where nobody could see them)
    AGENT_EYES = {'jean': (1.465, 0.047, 0.08, 0.052, 0.9), 'tri1': (1.405, 0.105, 0.155, 0.135, 0.3),
                  'tri2': (1.405, 0.105, 0.155, 0.135, 0.3), 'tri3': (1.405, 0.105, 0.155, 0.135, 0.3)}
    # (centre z, half separation, lens width, lens height, max wrap slope: the planks' faces are flat)
    for n, (cz, sep, lw, lh, mw) in AGENT_EYES.items():
        shades = fitted_shades(A[n], 'shades_' + n, centre_z=cz, sep=sep, lens_w=lw, lens_h=lh, max_wrap=mw)
        r = A[n].rig.location
        anchors = [Vector((r.x + x, surface_y(A[n], x, cz) or r.y - 0.15, r.z + cz)) for x in (-sep, sep)]
        anchors.append(Vector((r.x, surface_y(A[n], 0, cz + lh) or r.y - 0.15, r.z + cz + lh)))
        glue(shades, A[n], anchors)
    # props in the paws, placed on the measured paw of the pose the character holds when it matters (the characters' own
    # clips, held: forcing their arms with IK twisted Slerf's gauntlets into his face and Anon's paws into his body)
    def posed(actor, clip, frac):
        act = actor.clips[clip]
        actor.arm.animation_data.action = act
        a0, a1 = act.frame_range
        sc.frame_set(int(round(a0 + (a1 - a0) * frac)))
        bpy.context.view_layer.update()
        body = skin(actor)
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [body.matrix_world @ v.co - actor.rig.location for v in ev.data.vertices]

    def bone_verts(actor, bone, wmin=0.5):
        body = skin(actor)
        gi = body.vertex_groups[bone].index
        return {v.index for v in body.data.vertices for g in v.groups if g.group == gi and g.weight >= wmin}

    def paw_top(P, side, zmin=0.0, zmax=9.0, xmin=0.0, only=None):
        cand = [p for i, p in enumerate(P) if zmin < p.z < zmax and (p.x * side) > xmin and (only is None or i in only)]
        ex = max(cand, key=lambda p: p.x * side)
        region = [p for p in cand if (p - ex).length < 0.16]
        return max(region, key=lambda p: p.z)

    def paw_fwd(P, only):
        cand = [p for i, p in enumerate(P) if i in only]
        tip = min(cand, key=lambda p: p.y)
        return max((p for p in cand if (p - tip).length < 0.12), key=lambda p: p.z)

    def place(obj, actor, local, up, only=None):
        anchor = actor.rig.location + local
        obj.location = anchor + Vector((0, 0, up))
        glue(obj, actor, [anchor], radius=0.04, only=only)

    SL_POSE = 'attack1@0.3'                                       # Slerf: right paw forward at 0.93 m, left out to the side
    P = posed(A['slerf'], 'attack1', 0.3)
    SL_RED = paw_top(P, -1, 0.5, 1.4, only=bone_verts(A['slerf'], 'mixamorig:RightHand'))
    SL_GREEN = paw_top(P, 1, 0.4, 1.4, only=bone_verts(A['slerf'], 'mixamorig:LeftHand'))
    SL_RED, SL_GREEN = SL_GREEN, SL_RED                            # red on the left paw, held out to the side at 0.82 m: Anon
    CS = 1.5                                                       # held candles 50 % bigger, standing ON the paw (centred on it
    STAND = 0.085 * CS + 0.015                                     # they sank into the fist and hid behind the gauntlet)
    place(mxsets.candle('candle_red_s', 'red', PROPS, size=CS), A['slerf'], SL_RED, STAND, bone_verts(A['slerf'], 'mixamorig:LeftHand'))
    place(mxsets.candle('candle_green_s', 'green', PROPS, size=CS), A['slerf'], SL_GREEN, STAND, bone_verts(A['slerf'], 'mixamorig:RightHand'))
    # (takes it from the side, clear of Slerf's body: from the front his bag pushed into Slerf's fist)
    # (centred on the top of the paw: gripped in the fist, not balanced on it)
    A['slerf'].arm.animation_data.action = None
    AN_TAKE = 'attack2@0.4'                                       # Anon: right paw punched a metre forward (measured on the
    P = posed(A['anon'], 'attack2', 0.4)                          # forearm's vertices; the 'reach' of attack1 was the bag tipping)
    AN_RF = bone_verts(A['anon'], 'mixamorig:RightForeArm', 0.3)
    AN_REACH = paw_fwd(P, AN_RF)
    RED_ANON = mxsets.candle('candle_red_a', 'red', PROPS, size=CS)
    place(RED_ANON, A['anon'], AN_REACH, STAND - 0.06, AN_RF)      # gripped low in his paw, at Slerf's candle height
    AN_DIAMOND = 'win@0.25'                                       # Anon: both paws up
    P = posed(A['anon'], 'win', 0.25)
    gem_m = bpy.data.materials.new('diamond')
    gem_m.use_nodes = True
    g = gem_m.node_tree.nodes['Principled BSDF']
    g.inputs['Base Color'].default_value = (0.85, 0.97, 1.0, 1)
    g.inputs['Roughness'].default_value = 0.0
    g.inputs['IOR'].default_value = 2.4
    g.inputs['Transmission Weight'].default_value = 1.0
    g.inputs['Emission Color'].default_value = (0.6, 0.95, 1.0, 1)
    g.inputs['Emission Strength'].default_value = 3.0
    for side, sx in (('Right', -1), ('Left', 1)):
        top = paw_top(P, sx, 0.8, 1.8, 0.2, only=bone_verts(A['anon'], f'mixamorig:{side}ForeArm', 0.3))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.06, location=(0, 0, 0))
        gem = bpy.context.active_object
        gem.name = f'diamond_{side}'
        gem.scale = (1, 1, 1.4)
        for c in list(gem.users_collection):
            c.objects.unlink(gem)
        PROPS.objects.link(gem)
        gem.data.materials.append(gem_m)
        gem.visible_shadow = False
        place(gem, A['anon'], top, 0.08, bone_verts(A['anon'], f'mixamorig:{side}ForeArm', 0.3))
        print('DIAMOND', side, tuple(round(v, 2) for v in top))
    # Anon takes the cookie with a short reach (paw forward at about 1 m high)
    P = posed(A['anon'], 'attack2', 0.1)
    AN_CK = paw_fwd(P, AN_RF)
    COOKIE_A = mxsets.cookie('cookie_a', PROPS)
    COOKIE_A.rotation_euler = (math.radians(70), 0, 0)
    place(COOKIE_A, A['anon'], AN_CK, 0.04, AN_RF)
    # Bome: the cookie on his right glove (the book's gloves stick out sideways; he turns to offer it)
    P = posed(A['bome'], 'idle', 0.1)
    BM_RH = bone_verts(A['bome'], 'mixamorig:RightHand', 0.4)
    BM_G = paw_top(P, -1, 0.5, 2.0, 0.4, only=BM_RH)
    A['bome'].arm.animation_data.action = None
    # Farter holds his phone up to his face (left hand forward at 1 m in a held attack pose); the screen faces his eyes
    P = posed(A['farter'], 'attack1', 0.3)
    FL = bone_verts(A['farter'], 'mixamorig:LeftHand', 0.4)
    FH = sum((P[i] for i in FL), Vector()) / len(FL)
    eye_f = Vector((0, -0.12, cine.EYES['farter']))
    look = (eye_f - FH).normalized()
    phone = bpy.data.objects.new('phone', None)
    PROPS.objects.link(phone)
    case_m = mxsets.material('phone_case', (0.03, 0.03, 0.035), rough=0.3, metal=0.5)
    scr_m = mxsets.image_material('phone_screen', os.path.join(HERE, 'pack', 'props', 'phone_chart.png'), emit=2.2)
    mxsets.box('phone_body', (0.085, 0.012, 0.17), (0, 0, 0), case_m, PROPS, parent=phone, bevel=0.006)
    scr = mxsets.plane('phone_glass', 0.076, 0.152, (0, -0.0065, 0), scr_m, PROPS, parent=phone, rot=(math.radians(90), 0, 0))
    pl = bpy.data.objects.new('phone_light', bpy.data.lights.new('phone_light', 'AREA'))
    pl.data.size = 0.12
    pl.data.color = (0.3, 1.0, 0.45)
    pl.data.energy = 6.0
    sc.collection.objects.link(pl)
    pl.parent = phone
    pl.location = (0, -0.02, 0)
    pl.rotation_euler = (math.radians(90), 0, 0)
    phone.rotation_mode = 'QUATERNION'
    phone.rotation_quaternion = (-look).to_track_quat('Y', 'Z')        # the screen side (-Y) faces his eyes
    place(phone, A['farter'], FH + Vector((0, 0, 0.0)), 0.06, FL)
    A['farter'].arm.animation_data.action = None
    print('PHONE at', tuple(round(v, 2) for v in FH), 'BOME glove', tuple(round(v, 2) for v in BM_G), 'ANON cookie reach', tuple(round(v, 2) for v in AN_CK))
    P = posed(A['anon'], 'attack2', 0.7)                          # Anon: right paw up at the bag's mouth for the swallow
    AN_MOUTH_PAW = paw_fwd(P, AN_RF)
    # the spine bend for the dodge: which way is back (the rig faces -Y: back is +Y)
    A['anon'].arm.animation_data.action = None
    pb = A['anon'].arm.pose.bones['mixamorig:Spine1']
    pb.rotation_mode = 'QUATERNION'
    h0 = bone_world(A['anon'], 'mixamorig:Head')
    bpy.context.view_layer.update()
    head0 = A['anon'].arm.matrix_world @ A['anon'].arm.pose.bones['mixamorig:Head'].head
    pb.rotation_quaternion = (math.cos(0.25), math.sin(0.25), 0, 0)
    bpy.context.view_layer.update()
    head1 = A['anon'].arm.matrix_world @ A['anon'].arm.pose.bones['mixamorig:Head'].head
    pb.rotation_quaternion = (1, 0, 0, 0)
    BEND_SIGN = 1.0 if head1.y > head0.y else -1.0
    print('PAWS slerf red', tuple(round(v, 2) for v in SL_RED), 'green', tuple(round(v, 2) for v in SL_GREEN),
          'anon reach', tuple(round(v, 2) for v in AN_REACH), 'mouth paw', tuple(round(v, 2) for v in AN_MOUTH_PAW), 'bend sign', BEND_SIGN)
    COOKIE = mxsets.cookie('cookie', PROPS)
    CARD = mxsets.bent_card('card', PROPS, os.path.join(HERE, 'pack', 'cards', 'marketcrash.webp'))
    # Alon holds the card up in front of his chest: the card rides his body (lean pivot), an IK arm puts his wrist at its
    # lower edge (his rig has no hand bones; the forearm tail is the wrist). Influence keyed with the basement scene.
    al = A['alon']
    al_rig = al.rig.location.copy()
    al_sh = bone_world(al, 'mixamorig:RightArm') - al_rig
    ALON_GRIP = Vector((al_sh.x * 0.3, al_sh.y - 0.27, al_sh.z - 0.12))
    al_tgt = bpy.data.objects.new('ik_alon_Right', None)
    sc.collection.objects.link(al_tgt)
    al_tgt.parent = al.tilt_obj
    al_tgt.location = ALON_GRIP
    al_con = al.arm.pose.bones['mixamorig:RightForeArm'].constraints.new('IK')
    al_con.name = 'IK'
    al_con.target = al_tgt
    al_con.chain_count = 2
    al_con.influence = 0.0
    CARD.parent = al.tilt_obj
    CARD.matrix_parent_inverse.identity()
    CARD.location = ALON_GRIP + Vector((0.0, -0.03, 0.10))
    CARD.rotation_euler = (math.radians(90), 0, 0)
    P = posed(A['bome'], 'idle', 0.1)
    place(COOKIE, A['bome'], BM_G, 0.025, BM_RH)                                 # on top of his right glove
    A['bome'].arm.animation_data.action = None
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

ANON_MOUTH = Vector((0, -0.51, 1.10))                             # the bag's mouth hole, rig-local (measured: front at -0.51)
if not DRY:
    A['alon'].arm.animation_data.action = bpy.data.actions.new('alon_ik_influence')

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
line('s01', [S('slerf', size='MS', bearing=-65, lens=50, frame='center', fstop=2.4, **{'with': ['anon']}),
             S('slerf', size='MCU', angle='low', bearing=12, lens=65, frame='left', move='push', amount=0.18, fstop=2.0)], 'FLOOR', weights=[1, 1.4])
line('a03', [S('anon', size='CU', bearing=25, lens=70, frame='right', fstop=2.0)], 'FLOOR')
line('s02', [S('slerf', size='CU', bearing=0, lens=85, frame='center', fstop=1.8)], 'FLOOR', pad=0.45)
CANDLES_ON = ANIM                                                # the paws come out with a candle on each
slerf.play(CANDLES_ON, 'attack1@0.3')
line('s03', [S('slerf', size='MS', bearing=-30, angle='low', lens=40, frame='center', move='arc', amount=50, fstop=2.8),
             S('slerf', size='MS', bearing=-8, angle=-6, lens=45, frame='center', fstop=2.4, move='push', amount=0.12),
             S('slerf', size='MS', bearing=55, lens=55, frame='center', fstop=2.4, move='push', amount=0.1, **{'with': ['anon']})], 'FLOOR',
     weights=[1.2, 1.2, 1.2])
line('a04', [S('anon', size='CU', bearing=30, lens=75, frame='right', dutch=6, fstop=1.8)], 'FLOOR')
line('s04', [S('slerf', size='WS', bearing=90, lens=35, frame='left', fstop=4.0, look_offset=(0, -1.0, 0))], 'FLOOR', pad=0.45)
TAKE = ANIM
# Anon steps to where his reaching right paw meets the red candle on Slerf's right paw (Slerf faces -Y: rig = world axes;
# Anon faces +Y: his local (x, y) is (-x, -y) in the world)
SL_RED_W = SLERF_AT + (SL_RED if not DRY else Vector((-0.84, -0.74, 0.93)))
AN_R = AN_REACH if not DRY else Vector((-0.47, -0.83, 1.0))
TAKE_AT = Vector((SL_RED_W.x + AN_R.x, SL_RED_W.y + AN_R.y + 0.02, 0))
anon.walk(TAKE - 1.3, TAKE_AT, speed=1.4, then='idle')
anon.turn(TAKE - 0.35, 0, 0.3)
anon.play(TAKE, AN_TAKE if not DRY else 'attack1')
shot('take_red', 1.4, S('anon', distance=2.6, bearing=95, lens=35, frame='center', fstop=3.5, look_offset=(0.0, 0.55, -0.3),
                         **{'with': ['slerf']}), 'FLOOR')
anon.play(TAKE + 0.9, 'idle')
slerf.play(TAKE + 0.9, 'idle')
SWALLOW = ANIM
anon.play(SWALLOW, 'idle@0.3', hard=True)
MOUTH_L = Vector((-0.05, -0.03, 1.07))                           # under the snout, measured on a front grid of the idle pose
shot('swallow', 1.6, S('anon', lens=45, frame='center', fstop=4.0),
     'FLOOR', glitch='rain_out')
if not DRY:
    print('TAKE at', tuple(round(v, 2) for v in TAKE_AT), 'anon candle centre z', round(AN_R.z + STAND - 0.06, 2), 'slerf candle centre z', round(SL_RED_W.z + STAND, 2))
    show('candle_red_s', [(0, False), (CANDLES_ON + 0.1, True), (TAKE + 0.22, False)])
    show('candle_red_a', [(0, False), (TAKE + 0.22, True), (SWALLOW, False)])
    show('candle_green_s', [(0, False), (CANDLES_ON + 0.1, True), (ANIM, False)])

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
line('mo1', [S('slerf', distance=5.8, fixed_heading=90, bearing=0, angle=-6, lens=26, frame='center', fstop=5.6,
                 look_offset=(-10.3, 2.55, 1.55), move='push', amount=0.12)],
     'BASEMENT')                                                 # up the stairs to Mom's lit door
slerf.turn(ANIM, 240)
line('s06', [S('slerf', size='MCU', bearing=-20, lens=60, frame='right', fstop=2.2)], 'BASEMENT', pad=0.3)
mensa.play(ANIM, 'idle', 1.4)
line('n01', [S('mensa', size='MS', bearing=150, lens=40, frame='left', fstop=2.8, move='push', amount=0.15),
             S('mensa', size='CU', bearing=-80, lens=70, frame='right', fstop=2.0)], 'BASEMENT', weights=[1.2, 1])
farter.play(ANIM - 0.6, 'attack1@0.3')                          # Farter, apart from the others, staring at his phone
shot('phone_insert', 1.5, S('farter', distance=1.35, bearing=155, angle=20, lens=45, frame='center', fstop=2.8, move='push', amount=0.2),
     'BASEMENT')                                                 # over his shoulder: the chart that only goes up
line('f01', [S('farter', size='MCU', bearing=35, lens=55, frame='right', fstop=2.0, move='push', amount=0.12)], 'BASEMENT', pad=0.35,
     lead=0.25)

# ---------------------------------------------------------------- 4. the training program
a = ANIM
anon.cut(a, DOJO + Vector((-1.3, 0, 0)), 90)
slerf.cut(a, DOJO + Vector((1.3, 0, 0)), 270)
line('n02', [cine.establish('anon', 22)], 'DOJO', pad=0.5, lead=0.3)
line('a05', [cine.vertigo('anon', 40)], 'DOJO', pad=0.4)
line('s07', [S('slerf', size='MS', angle='low', bearing=-20, lens=50, frame='left', fstop=2.2)], 'DOJO')
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
LIE_DROP = 0.27                                                  # lying on his back the tail propped him 34 cm off the mat:
anon.keys.append([FIGHT + 3.6, *anon.pos, anon.H, 0])            # lower him onto it while the tail is swung out flat (below)
anon.pos = anon.pos - Vector((0, 0, LIE_DROP))
anon.keys.append([FIGHT + 3.95, *anon.pos, anon.H, 0])
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
    for side, ik in SLERF_IK.items():
        animate(ik['tgt'], 'location', [(F(a_), tuple(v)) for a_, v in ik['keys']], 'BEZIER')
        animate(A['slerf'].arm, f'pose.bones["mixamorig:{side}ForeArm"].constraints["IK"].influence',
                [(F(a_), v) for a_, v in ik['inf']], 'BEZIER')
shot('fight_track', 1.5, cine.chaos('anon', 28), 'DOJO')
shot('fight_arc', 1.7, S('anon', size='WS', bearing=70, lens=32, frame='center', move='arc', amount=80, fstop=4.0, angle=24,
                         look_offset=(0.67, 0, -0.3), **{'with': ['slerf']}), 'DOJO')
shot('fight_fall', 1.4, S('anon', size='WS', angle='high', bearing=80, lens=35, frame='center', fstop=3.2), 'DOJO')
line('s08', [S('anon', size='WS', angle='high', bearing=150, lens=35, frame='left', fstop=2.8, eye=0.35),
             S('slerf', size='MCU', angle='low', bearing=20, lens=55, frame='right', fstop=2.0)], 'DOJO', weights=[1, 1.2])

# ---------------------------------------------------------------- 5. the waiting room and the book
a = ANIM
LIE_END = a
ALON_AT = BASE + Vector((-2.6, 5.4, 0))
BOME_AT = BASE + Vector((-5.9, 5.2, 0.35))
alon.cut(a, ALON_AT, 160)
ALON_IN = a
bome.cut(a, BOME_AT, 170)
anon.cut(a, BASE + Vector((-2.2, 2.4, 0)), 0)
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
OFFER = ANIM + 1.0                                              # "...Cookie?": the glove with the cookie comes round to Anon
line('b02', [S('anon', size='CU', bearing=40, lens=75, frame='left', fstop=1.8),
             S('bome', size='MS', bearing=-70, lens=40, frame='center', fstop=2.8, move='push', amount=0.1, **{'with': ['anon']})],
     'BASEMENT', pad=0.3, weights=[0.7, 1])
COOKIE_T = ANIM + 0.45
shot('cookie_take', 1.6, S('anon', distance=2.6, bearing=-55, lens=35, frame='center', fstop=4.0, look_offset=(0, 0.3, -0.2),
                           **{'with': ['bome']}), 'BASEMENT')
# geometry: Bome turns so his right glove points at Anon and sinks to Anon's reach; Anon steps to the glove
G = BM_G if not DRY else Vector((-0.97, -0.1, 1.1))
AC = AN_CK if not DRY else Vector((-0.1, -0.4, 1.0))
anon_here = Vector((BASE.x - 4.4, BASE.y + 3.9, 0))
v = (anon_here - Vector((BOME_AT.x, BOME_AT.y, 0))).normalized()
phi = math.atan2(-v.y, -v.x)                                     # rig rotation that turns local -X (his right glove) onto v
H_OFFER = 180 - math.degrees(phi)
z_offer = max(-0.1, (AC.z + 0.04) - (G.z + 0.025))
glove = Vector((BOME_AT.x + G.x * math.cos(phi) - G.y * math.sin(phi), BOME_AT.y + G.x * math.sin(phi) + G.y * math.cos(phi), z_offer + G.z))
H_A = heading_to(anon_here, glove)
pa = math.radians(180 - H_A)
paw = Vector((AC.x * math.cos(pa) - AC.y * math.sin(pa), AC.x * math.sin(pa) + AC.y * math.cos(pa), 0))
ANON_CK_AT = Vector((glove.x - paw.x, glove.y - paw.y, 0))
for k in range(int((OFFER - a) / 0.5)):                          # the book floats, bobbing gently, until he offers
    t = a + k * 0.5
    bome.keys.append([t, BOME_AT.x, BOME_AT.y, BOME_AT.z + 0.08 * math.sin(k * 0.9), 170 + 6 * math.sin(k * 0.5), 0])
bome.keys.append([OFFER, BOME_AT.x, BOME_AT.y, BOME_AT.z, 170, 0])
bome.keys.append([OFFER + 0.6, BOME_AT.x, BOME_AT.y, BASE.z + z_offer, H_OFFER, 0])
bome.pos, bome.H = Vector((BOME_AT.x, BOME_AT.y, BASE.z + z_offer)), H_OFFER
bome.play(OFFER, 'idle@0.1')
anon.walk(OFFER + 0.2, ANON_CK_AT, speed=1.2, then='idle')
anon.turn(COOKIE_T - 0.4, H_A, 0.2)
anon.play(COOKIE_T - 0.1, 'attack2@0.1')
anon.play(COOKIE_T + 0.9, 'idle')
if not DRY:
    print('COOKIE offer: bome H', round(H_OFFER), 'sinks to', round(z_offer, 2), 'glove', tuple(round(x_, 2) for x_ in glove),
          'anon at', tuple(round(x_, 2) for x_ in ANON_CK_AT), 'facing', round(H_A))

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
BULLET_Z = [float(z) for z in os.environ.get('BULLET_Z', '1.57,1.63,1.59,1.67,1.58,1.64,1.61').split(',')]
anon.play(BT, 'ready', 0.15)
LEAN = 16
anon.lean(BT, 0)
anon.lean(BT + 0.14, -LEAN)                                       # fully back before the first candle arrives (BT + 0.19)
anon.lean(BT + 0.40, -LEAN)
anon.lean(BT + 0.75, 0)
anon.play(BT + BT_FILM * BT_SPEED + 0.6, 'idle')                 # the slowed 'hit' clip would run ~8 s past the dodge
shot('bullet_time', BT_FILM, S('anon', distance=2.9, angle=-4, bearing=100, lens=24, frame='center', move='arc', amount=130, fstop=4.0,
                                  ease='smooth', eye=1.0), 'ROOFTOP', speed=BT_SPEED, hand=None, bullet=True)
PROJ = []
PROJ_AT = []
BULLET_V = 10.0                                                        # m/s of animation time (0.8 m/s on screen in bullet time)
for k in range(7):                                                     # fired at the end of the shot of Jeanphil, they reach Anon
    start = ROOF + Vector((0.22 + 0.03 * (k - 3), 7.3, 1.35 + 0.015 * k))       # between BT + 0.19 and BT + 0.31, just over
    at = ROOF + Vector((0.07 * (k - 3), 4.2, BULLET_Z[k]))                     # his leaned-back bag (heights checked on the mesh)
    end = start + (at - start) * ((start.y - (ROOF.y - 6.0)) / (start.y - at.y))
    t_on = FIRE + 0.84 + k * 0.035                                   # staggered: they read one by one
    PROJ.append((start, end, t_on, t_on + (start - end).length / BULLET_V))
    PROJ_AT.append(at)
shot('after_dodge', 1.0, S('anon', size='MS', bearing=20, lens=40, frame='center', fstop=2.8), 'ROOFTOP')
line('m03', [S('michi', size='MCU', bearing=-30, lens=60, frame='right', fstop=2.0)], 'ROOFTOP')
A08 = ANIM                                                       # "Diamond hands.": both paws up, a diamond in each
anon.play(A08, AN_DIAMOND if not DRY else 'win')
line('a08', [S('anon', size='MS', angle=-8, bearing=0, lens=45, frame='center', fstop=2.8, move='push', amount=0.1)], 'ROOFTOP')
# second barrage: he lifts a paw, the candles stop in the air, turn green and drop
FIRE2 = ANIM
if not DRY:
    show('diamond_Right', [(0, False), (A08 + 0.15, True)])
    show('diamond_Left', [(0, False), (A08 + 0.15, True)])
jean.play(FIRE2, 'attack2', 1.0)
anon.play(FIRE2 + 0.2, 'win', 0.8)
STOP = []
for k in range(7):
    start = ROOF + Vector((0.22 + 0.03 * (k - 3), 7.3, 1.35 + 0.015 * k))
    hx = (-1.0, -0.7, -0.4, 0.0, 0.4, 0.7, 1.0)[k]                         # a wall of candles 1.6 m in front of him, the middle one
    hang = ROOF + Vector((hx, 5.8 + 0.12 * (k % 2), 1.95 if k == 3 else 0.9 + 0.22 * (k % 3)))    # high: drops clear of him
    STOP.append((start, hang, FIRE2 + 0.3 + k * 0.04))
shot('freeze_ots', 1.9, S('jean', over='anon', size='MS', lens=50, frame=(-1 / 3, 1 / 3), fstop=4.0), 'ROOFTOP')
TURN_GREEN = ANIM
shot('freeze_insert', 1.6, S('anon', size='MS', bearing=70, lens=35, frame='center', fstop=5.6, look_offset=(0, 0.8, -0.1), move='arc',
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
        c = mxsets.candle(f'proj{k}', 'red', PROPS, size=1.5, trail=0.8, glow=3.0)
        c.rotation_euler = (math.radians(90), 0, 0)
        animate(c, 'location', [(F(0), (0, 0, -50)), (F(t_on) - 0.02, (0, 0, -50)), (F(t_on), tuple(start)), (F(t_off), tuple(end)),
                                (F(t_off) + 0.02, (0, 0, -50))])
        proj_objs.append(c.name)
        animate(bpy.data.objects[f'proj{k}_trail'], 'scale', [(F(t_on), (1, 1, 0.02)), (F(t_on + 0.3), (1, 1, 1))], 'LINEAR')
    flash_m = mxsets.material('muzzle', (1.0, 0.5, 0.3), emit=(1.0, 0.45, 0.25), strength=25.0)
    for name_, t_fl in (('muzzle1', PROJ[0][2]), ('muzzle2', STOP[0][2])):     # a flash at Jeanphil's hand as each barrage leaves
        fl = mxsets.sphere(name_, 0.05, tuple(PROJ[3][0]), flash_m, PROPS)
        fll = bpy.data.objects.new(name_ + '_light', bpy.data.lights.new(name_ + '_light', 'POINT'))
        fll.data.color = (1.0, 0.45, 0.25)
        fll.data.shadow_soft_size = 0.1
        sc.collection.objects.link(fll)
        fll.parent = fl
        fll.data.animation_data_create()
        fa = bpy.data.actions.new(name_ + '_light_energy')
        fll.data.animation_data.action = fa
        fc = fa.fcurves.new('energy')
        for f_, v_ in ((F(t_fl) - 0.5, 0.0), (F(t_fl), 600.0), (F(t_fl + 0.1), 0.0)):
            fc.keyframe_points.insert(f_, v_)
        fl.visible_shadow = False
        animate(fl, 'scale', [(F(0), (0, 0, 0)), (F(t_fl) - 0.5, (0, 0, 0)), (F(t_fl) + 0.5, (1.4, 1.4, 1.4)), (F(t_fl + 0.12), (0, 0, 0))], 'LINEAR')
    for k, (start, hang, t_on) in enumerate(STOP):
        for colour in ('red', 'green'):
            c = mxsets.candle(f'stop{k}_{colour}', colour, PROPS, size=1.3, trail=0.0)
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
    animate(CARD, 'modifiers["bend"].angle', [(F(BEND + 0.15), 0.0), (F(BEND + 1.1), math.radians(160))], 'BEZIER')  # in the insert
    animate(A['alon'].arm, 'pose.bones["mixamorig:RightForeArm"].constraints["IK"].influence',
            [(F(ALON_IN - 0.05), 0.0), (F(ALON_IN), 1.0), (F(BEND + 8.0), 1.0), (F(BEND + 8.4), 0.0)], 'LINEAR')
    show('cookie', [(0, False), (OFFER - 3.5, True), (COOKIE_T + 0.15, False)])
    show('cookie_a', [(0, False), (COOKIE_T + 0.15, True), (COOKIE_T + 1.6, False)])
    show('card', [(0, False), (BEND - 6.0, True), (BEND + 8.0, False)])
    for actor in A.values():
        actor.finish(END_A + 2.0)
    # the fall: his tail curls straight down under him; swing it out flat along the mat (a hook on the tail, pivoting at its
    # root, weighted from root to tip) while the rig lowers him onto the mat
    an = A['anon']
    body = skin(an)
    tail = {v.index: min(1.0, max(0.0, (v.co.y - 0.24) / 0.22)) ** 1.2 for v in body.data.vertices if v.co.y > 0.24 and v.co.z < 0.75}
    vg = body.vertex_groups.new(name='tail_hook')
    for i_, w_ in tail.items():
        vg.add([i_], w_, 'REPLACE')
    sc.frame_set(int(F(FIGHT + 4.5)))
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    co = [v.co.copy() for v in ev.data.vertices]
    root_ = [co[i_] for i_, w_ in tail.items() if w_ < 0.12]
    tip_ = [co[i_] for i_, w_ in tail.items() if w_ > 0.9]
    rest_ = [co[i_] for i_ in range(len(co)) if i_ not in tail]
    base = sum(root_, Vector()) / len(root_)
    tipc = sum(tip_, Vector()) / len(tip_)
    centre = sum(rest_, Vector()) / len(rest_)
    out = base - centre
    out.z = 0
    out.normalize()
    target = (out + Vector((0, 0, 0.75))).normalized()
    q = (tipc - base).normalized().rotation_difference(target)
    hook_e = bpy.data.objects.new('tail_hook', None)
    sc.collection.objects.link(hook_e)
    hook_e.parent = body.parent                                    # (parented to the mesh it deforms made a dependency cycle
    hook_e.matrix_parent_inverse = body.matrix_parent_inverse.copy()   # and stretched the tail into a rod)
    assert (body.matrix_basis - Matrix.Identity(4)).to_3x3().median_scale < 1e-6 and body.matrix_basis.translation.length < 1e-6, \
        'the skin has its own transform: compose it into the hook'
    hook_e.location = base
    hook_e.rotation_mode = 'QUATERNION'
    hk = body.modifiers.new('tail_hook', 'HOOK')
    hk.object = hook_e
    hk.vertex_group = 'tail_hook'
    hk.falloff_type = 'NONE'
    bpy.context.view_layer.update()
    hk.matrix_inverse = hook_e.matrix_world.inverted() @ body.matrix_world   # identity until the hook turns
    hk.center = base
    ident = (1.0, 0.0, 0.0, 0.0)
    animate(hook_e, 'rotation_quaternion', [(F(0), ident), (F(FIGHT + 3.3), ident), (F(FIGHT + 3.9), tuple(q)),
                                            (F(LIE_END) - 0.02, tuple(q)), (F(LIE_END), ident)], 'BEZIER')
    print('TAIL base', tuple(round(v, 2) for v in base), 'tip', tuple(round(v, 2) for v in tipc), 'swing', round(math.degrees(q.angle)), 'deg')
    # the dodge: Anon's spine bends back (an NLA strip over the clips, blended in and out), peak while the candles pass
    an = A['anon']
    bend = bpy.data.actions.new('anon_bend')
    peak = {'mixamorig:Spine': 22, 'mixamorig:Spine1': 24, 'mixamorig:Spine2': 20, 'mixamorig:Neck': 12}
    for bname, deg in peak.items():
        an.arm.pose.bones[bname].rotation_mode = 'QUATERNION'
        for idx in range(4):
            fc = bend.fcurves.new(f'pose.bones["{bname}"].rotation_quaternion', index=idx, action_group=bname)
            for t_, k_ in ((0.0, 0), (0.12, 1), (0.47, 1), (0.67, 0)):
                ang = math.radians(deg) * k_ * BEND_SIGN / 2
                q = (math.cos(ang), math.sin(ang), 0, 0)
                fc.keyframe_points.insert(F(BT + t_), q[idx]).interpolation = 'BEZIER'
    tr = an.arm.animation_data.nla_tracks.new()
    st = tr.strips.new('bend', int(F(BT)) - 1, bend)
    st.blend_type = 'COMBINE'
    st.extrapolation = 'NOTHING'
    # the swallow (close-up): find the bag's mouth hole on the posed mesh (a ray from in front at the snout's height), then the
    # candle rises into frame, tips to point into the hole and slides in; the camera is placed on that point (below)
    w_ = make_where({n: sorted(x.keys, key=lambda k: k[0]) for n, x in A.items()})
    feet, head = w_('anon', SWALLOW + 0.5)
    sc.frame_set(int(F(SWALLOW + 0.5)))
    fwd = Vector((math.sin(math.radians(head)), math.cos(math.radians(head)), 0))
    side = Vector((fwd.y, -fwd.x, 0))
    dg = bpy.context.evaluated_depsgraph_get()
    mouth = None
    for dz in (1.07, 1.05, 1.09, 1.03):
        o_ = Vector(feet) + fwd * 2.0 + Vector((0, 0, dz))
        hit, loc, nrm, _, obj, _ = sc.ray_cast(dg, o_, -fwd, distance=3.0)
        if hit and cine.owner(obj) == 'anon':
            mouth = loc
            break
    assert mouth is not None, 'no mouth found'
    EAT_MOUTH, EAT_FWD, EAT_SIDE = mouth, fwd, side
    eat = mxsets.candle('candle_eat', 'red', PROPS, size=1.5)
    eat.rotation_mode = 'QUATERNION'
    gone = (0, 0, -50)
    t0_ = SWALLOW + 0.15
    up = Vector((0, 0, 1)).to_track_quat('Z', 'Y')
    inward = (-fwd).to_track_quat('Z', 'Y')                                # the candle's top end points into the mouth
    animate(eat, 'location', [(F(0), gone), (F(t0_) - 0.02, gone), (F(t0_), tuple(mouth + fwd * 0.16 - Vector((0, 0, 0.42)))),
                              (F(t0_ + 0.45), tuple(mouth + fwd * 0.22)), (F(t0_ + 0.75), tuple(mouth - fwd * 0.05)),
                              (F(t0_ + 0.77), gone)], 'BEZIER')
    animate(eat, 'rotation_quaternion', [(F(t0_), tuple(up)), (F(t0_ + 0.2), tuple(up)), (F(t0_ + 0.45), tuple(inward))], 'BEZIER')
    animate(eat, 'scale', [(F(t0_ + 0.55), (1, 1, 1)), (F(t0_ + 0.75), (0.2, 0.2, 0.2))], 'LINEAR')
    print('SWALLOW mouth', tuple(round(v, 3) for v in mouth))
    EAT_IN = t0_ + 0.75
    eg = bpy.data.objects.new('candle_eat_glow', bpy.data.lights.new('candle_eat_glow', 'POINT'))
    eg.data.color = (1.0, 0.12, 0.08)
    eg.data.energy = 14.0
    eg.data.shadow_soft_size = 0.05
    sc.collection.objects.link(eg)
    eg.parent = eat
    print('SWALLOW mouth', tuple(round(v, 2) for v in mouth))
    # the candles skim 18 cm over the bent body: measure its top at the peak of the bend
    body = skin(an)
    bp = []
    for tt in (0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45):
        sc.frame_set(int(F(BT + tt)), subframe=F(BT + tt) % 1)
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        bp += [body.matrix_world @ v.co for v in ev.data.vertices][::2]
    rz = {}
    for k in range(7):
        x_ = ROOF.x + 0.2 * (k - 3)
        near = [p.z for p in bp if abs(p.x - x_) < 0.25]
        top_all = max(p.z for p in bp)
        rz[k] = (max(near) if near else top_all - 0.2) + 0.22 + 0.12 * (k % 3)
        PROJ_AT[k] = Vector((x_, ROOF.y + 4.2, rz[k]))
    print('BENT top', round(max(p.z for p in bp), 2), 'bullet heights', [round(v, 2) for v in rz.values()])
    # re-aim the first barrage from Jeanphil's posed right hand at each launch (a guessed point floated off the hand)
    jarm = A['jean'].arm
    for k, (start, end, t_on, t_off) in enumerate(PROJ):
        sc.frame_set(int(F(t_on)), subframe=F(t_on) - int(F(t_on)))
        hand = jarm.matrix_world @ jarm.pose.bones['mixamorig:RightHand'].tail + Vector((0, -0.12, 0))
        at = PROJ_AT[k]
        d = (at - hand).normalized()
        end = hand + d * ((hand.y - (ROOF.y - 6.0)) / max(1e-3, -d.y))
        t_off = t_on + (end - hand).length / BULLET_V
        c = bpy.data.objects[f'proj{k}']
        c.animation_data_clear()
        c.rotation_mode = 'QUATERNION'
        c.rotation_quaternion = d.to_track_quat('Z', 'Y')            # candle axis along the flight (trail behind)
        animate(c, 'location', [(F(0), (0, 0, -50)), (F(t_on) - 0.02, (0, 0, -50)), (F(t_on), tuple(hand)), (F(t_off), tuple(end)),
                                (F(t_off) + 0.02, (0, 0, -50))])
        if k == 0:
            m1 = bpy.data.objects['muzzle1']
            m1.location = hand
            print('FIRE hand', tuple(round(v, 2) for v in hand), 'reaches anon at', round(t_on + (hand.y - (ROOF.y + 4.2)) / (-d.y) / BULLET_V - BT, 3), 's after BT')
    GLOW = {'candle_red_s': (1.0, 0.12, 0.08), 'candle_green_s': (0.15, 1.0, 0.3), 'candle_red_a': (1.0, 0.12, 0.08)}
    for name, steps in VIS:
        if name in GLOW:                                           # each candle lights the faces near it in its own colour
            gl = bpy.data.objects.new(name + '_glow', bpy.data.lights.new(name + '_glow', 'POINT'))
            gl.data.color = GLOW[name]
            gl.data.shadow_soft_size = 0.06
            sc.collection.objects.link(gl)
            gl.parent = bpy.data.objects[name]
            gl.location = (0, 0, 0.05)
            en = []
            for a_, on in steps:
                en += [(F(a_) - 0.02, en[-1][1] if en else 0.0), (F(a_), 18.0 if on else 0.0)]
            gl.data.animation_data_create()
            act_ = bpy.data.actions.new(name + '_glow_energy')
            gl.data.animation_data.action = act_
            fc = act_.fcurves.new('energy')
            for f_, v_ in en[1:]:
                fc.keyframe_points.insert(f_, v_).interpolation = 'CONSTANT'
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
        if s_['name'] == 'phone_insert':                          # Farter's view of his screen, over the top of the phone
            a_mid = s_['a0'] + (s_['t1'] - s_['t0']) * 0.5
            sc.frame_set(int(F(a_mid)))
            feet, head = make_where({n: sorted(x.keys, key=lambda k: k[0]) for n, x in A.items()})('farter', a_mid)
            ph = bpy.data.objects['phone']
            c = ph.matrix_world.translation.copy()
            n = (ph.matrix_world.to_quaternion() @ Vector((0, -1, 0))).normalized()   # out of the screen
            s_['cam']['look_offset'] = list(c - cine.eye_point('farter', feet, head))
            s_['cam']['cam_at'] = list(c + n * 0.42 + Vector((0, 0, 0.05)))
            s_['cam']['cam_at1'] = list(c + n * 0.30 + Vector((0, 0, 0.03)))
            s_['cam']['lens'] = 40
        if s_['name'] == 'swallow':                               # close on the bag's mouth, a little to his left, easing in
            feet, head = make_where({n: sorted(x.keys, key=lambda k: k[0]) for n, x in A.items()})('anon', s_['a0'] + 0.5)
            s_['cam']['look_offset'] = list(EAT_MOUTH + Vector((0, 0, -0.06)) - cine.eye_point('anon', feet, head))
            s_['cam']['cam_at'] = list(EAT_MOUTH + EAT_FWD * 0.95 + EAT_SIDE * 0.32 + Vector((0, 0, -0.02)))
            s_['cam']['cam_at1'] = list(EAT_MOUTH + EAT_FWD * 0.72 + EAT_SIDE * 0.22 + Vector((0, 0, -0.03)))
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


EVENTS = {'take': TAKE + 0.45, 'fight': FIGHT, 'fall': FIGHT + 3.55, 'push': FIGHT + 2.72, 'card_bend': BEND + 0.15, 'cookie': COOKIE_T + 0.15, 'fire': FIRE + 0.3,
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
