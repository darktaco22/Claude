"""THE MEMETRIX II: LIQUIDATION. Builds W/scene2.blend and edl.json (shots as camera-toolkit data, cues, character tracks).

    blender -b -P scene2.py -- [--out W/scene2.blend] [--lib W/chars.blend]

Same machinery as episode 1 (../memetrix/scene.py: actors on rig + tilt empties, held poses 'clip@frac', props glued to
measured skin vertices, fitted shades, solved cameras with 'with' partners and 'cam_at' inserts). See SCRIPT.md and PLAN.md.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EP1 = os.path.join(HERE, '..', 'memetrix')
sys.path.insert(0, HERE)
sys.path.insert(0, EP1)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import assets  # noqa: E402
import cine  # noqa: E402
import mxsets  # noqa: E402
import sets2  # noqa: E402
from track import heading_to, make_where  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(key, default=None):
    return ARGS[ARGS.index(key) + 1] if key in ARGS else default


WORK = os.environ.get('W', os.path.expanduser('~/mx_work'))
OUT = arg('--out', WORK + '/scene2.blend')
LIB = arg('--lib', WORK + '/chars.blend')
DRY = bool(os.environ.get('DRY'))
FPS = 24
VO = json.load(open(os.path.join(HERE, 'pack', 'vo', 'vo.json')))

CLONES = [f'jc{k}' for k in range(11)]                           # with Jeanphil himself: twelve
cine.EYES.update({'anon': 1.24, 'slerf': 1.30, 'michi': 1.30, 'mensa': 1.42, 'jean': 1.47, 'whale': 1.5, 'swordcat': 1.30,
                  'fine': 1.28, 'toshi': 1.21})                   # measured on front + side height grids
cine.EYES.update({n: 1.47 for n in CLONES})
cine.EYE_FWD.update({'mensa': 0.35, 'anon': 0.08})
cine.FRAME_SCALE = 1.35
CAST = {'anon': 'zcat', 'slerf': 'slerf', 'michi': 'michi', 'mensa': 'mensa', 'jean': 'jeanphil', 'whale': 'whale',
        'swordcat': 'swordcat', 'fine': 'thisisfine', 'toshi': 'toshi'}
CAST.update({n: 'jeanphil' for n in CLONES})

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
FLOOR, BASE, ROOF = mxsets.ORIGIN['FLOOR'], mxsets.ORIGIN['BASEMENT'], mxsets.ORIGIN['ROOFTOP']
CAFE, WHITE = sets2.ORIGIN['CAFE'], sets2.ORIGIN['WHITE']
mxsets.build_floor()
mxsets.build_basement()
mxsets.build_rooftop()
sets2.build_cafe()
sets2.build_white_room(sets2.episode1_stills(os.path.join(EP1, 'frames_jpg', '50dff5a2ee')))
sets2.rooftop_rain(mxsets.collection('ROOFTOP'), ROOF + Vector((0, 0, 2.0)))
for m_ in bpy.data.materials:                                     # the rooftop in rain: a wet, reflective floor
    if m_.name.startswith(('roof', 'ground_roof')) and m_.use_nodes and 'Principled BSDF' in m_.node_tree.nodes:
        m_.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.12
PROPS = mxsets.collection('PROPS')
for o_ in bpy.data.objects:                                       # the trading floor's bull, cracked
    if 'bull' in o_.name.lower() and o_.type == 'MESH':
        o_['cracked'] = True

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
            strip.blend_in = 0 if hard or not index else (6 if name == 'die' else 10 if name.startswith('present') else 3)



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



# ================================================================ cast
names = list(CAST)
chars = [None] * len(names) if DRY else assets.load_many(LIB, [CAST[n] for n in names], sc.collection)
A = {n: Actor(n, c) for n, c in zip(names, chars)}
for n, actor in A.items():
    actor.rig['actor'] = n
OFF = (0, 0, -100)
for actor in A.values():
    actor.cut(0.0, OFF, 180)


def bone_world(actor, bone):
    bpy.context.view_layer.update()
    return actor.arm.matrix_world @ actor.arm.data.bones[bone].head_local


def face_point(actor, eye):
    bpy.context.view_layer.update()
    origin = Vector((actor.rig.location.x, actor.rig.location.y - 3.0, actor.rig.location.z + eye))
    hit, loc, *_ = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, Vector((0, 1, 0)), distance=4.0)
    return loc if hit else origin + Vector((0, 2.75, 0))


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


# ================================================================ props and fitted details (bind pose, cast spread out)
if not DRY:
    for k, actor in enumerate(A.values()):
        actor.rig.location = (k * 6.0, 0, -50)
        actor.rig.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    sl = A['slerf'].rig.location
    shades = fitted_shades(A['slerf'], 'shades_slerf', centre_z=1.272, sep=0.155, lens_w=0.20, lens_h=0.13)
    glue(shades, A['slerf'], [face_point(A['slerf'], 1.26) + Vector((x, 0, 0)) for x in (-0.15, 0.15)] +
         [sl + Vector((0, surface_y(A['slerf'], 0, 1.42) - sl.y, 1.42))])
    for n in ['jean'] + CLONES:                                     # every Jeanphil wears the same fitted shades
        shades = fitted_shades(A[n], 'shades_' + n, centre_z=1.465, sep=0.047, lens_w=0.08, lens_h=0.052)
        r = A[n].rig.location
        glue(shades, A[n], [Vector((r.x + x, surface_y(A[n], x, 1.465) or r.y - 0.15, r.z + 1.465)) for x in (-0.047, 0.047)] +
             [Vector((r.x, surface_y(A[n], 0, 1.517) or r.y - 0.15, r.z + 1.517))])
    # Anon's paws: the right paw punched forward (attack2 at 40 %: the block, the catch) and both paws up (win at 25 %)
    AN_RF = bone_verts(A['anon'], 'mixamorig:RightForeArm', 0.3)
    P = posed(A['anon'], 'win', 0.25)
    ROCKET = mxsets.candle('rocket', 'green', PROPS, size=1.6, trail=0.0, glow=3.0)   # (a long trail read as a green bar)
    ROCKET.rotation_euler = (0, 0, 0)                               # upright over his raised right paw, the streak below it
    place(ROCKET, A['anon'], paw_top(P, -1, 0.8, 1.8, 0.2, only=AN_RF), 0.16, AN_RF)
    P = posed(A['anon'], 'attack2', 0.4)
    AN_REACH = paw_fwd(P, AN_RF)
    SAVE = mxsets.candle('save_candle', 'green', PROPS, size=1.5, glow=2.0)
    place(SAVE, A['anon'], AN_REACH, 0.1, AN_RF)
    # Toshi's key ring of seed words: a glowing ring at her chest
    key_m = mxsets.material('seed_key', (1.0, 0.85, 0.3), emit=(1.0, 0.8, 0.25), strength=4.0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.09, minor_radius=0.012)
    KEY = bpy.context.active_object
    KEY.name = 'seed_key'
    for c_ in list(KEY.users_collection):
        c_.objects.unlink(KEY)
    PROPS.objects.link(KEY)
    KEY.data.materials.append(key_m)
    KEY.rotation_euler = (math.radians(90), 0, 0)
    tk = A['toshi'].rig.location
    KEY.location = Vector((tk.x, (surface_y(A['toshi'], 0, 0.95) or tk.y - 0.3) - 0.06, tk.z + 0.95))
    glue(KEY, A['toshi'], [KEY.location + Vector((0, 0.06, 0))], radius=0.06)
    # the shockwave: a flat green ring that grows from Anon's feet
    wave_m = mxsets.material('shockwave', (0.3, 1.0, 0.45), emit=(0.3, 1.0, 0.45), strength=12.0)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.04, major_segments=96)
    WAVE = bpy.context.active_object
    WAVE.name = 'shockwave'
    for c_ in list(WAVE.users_collection):
        c_.objects.unlink(WAVE)
    PROPS.objects.link(WAVE)
    WAVE.data.materials.append(wave_m)
    WAVE.visible_shadow = False
    WAVE['cine_ignore'] = True
    for a_ in A.values():
        a_.arm.animation_data.action = None
VIS = []


def show(obj_name, steps):
    VIS.append((obj_name, steps))


# ================================================================ timeline
FILM = ANIM = TITLE = 5.0                                        # the 2D opening (finish.py) covers 0..TITLE plus PRE
SHOTS, CUES, NOTES = [], [], []


def shot(name, dur, cam_shot, where_set, speed=1.0, hand=('INVESTIGATION', 0.3), **extra):
    global FILM, ANIM
    SHOTS.append(dict(name=name, t0=round(FILM, 4), t1=round(FILM + dur, 4), a0=round(ANIM, 4), s0=speed, set=where_set,
                      cam=cam_shot, hand=list(hand) if hand else None, **extra))
    FILM += dur
    ANIM += dur * speed


def line(line_id, cams, where_set, lead=0.1, pad=0.25, weights=None):
    dur = VO[line_id]['dur']
    CUES.append((line_id, round(FILM + lead, 4)))
    who = VO[line_id]['who']
    for w in ({'jean': ['jean'] + CLONES} if line_id == 'j11' else {}).get(who, [who]):
        if w in A:
            A[w].talks.append((ANIM + lead, ANIM + lead + dur))
    total = lead + dur + pad
    weights = weights or [1] * len(cams)
    for i, c in enumerate(cams):
        shot(f'{line_id}_{i}', total * weights[i] / sum(weights), c, where_set)
    return total


def S(subject, **kw):
    return dict(subject=subject, **kw)


anon, slerf, michi, mensa, jean = (A[n] for n in ('anon', 'slerf', 'michi', 'mensa', 'jean'))
whale, swordcat, fine, toshi = (A[n] for n in ('whale', 'swordcat', 'fine', 'toshi'))
clones = [A[n] for n in CLONES]

# ---------------------------------------------------------------- 0. the crash: the bull cracks (3D tail of the cold open)
a = ANIM
BULL_T = a
anon.cut(a, FLOOR + Vector((0, 2.0, 0)), 0)                       # (off frame, so the floor has its subject for the solver)
shot('bull_crack', 3.0, S('anon', distance=9.0, angle=12, bearing=180, lens=28, frame='center', fstop=5.6, move='push', amount=0.15,
                          look_offset=(0, 6.0, 3.0)), 'FLOOR')

# ---------------------------------------------------------------- 1. the rug: Mom's basement
a = ANIM
mensa.cut(a, BASE + Vector((2.5, 0.72, 0)), 20)
michi.cut(a, BASE + Vector((-1.2, 0.2, 0)), 120)
slerf.cut(a, BASE + Vector((0.8, 1.2, 0)), 200)
anon.cut(a, BASE + Vector((-0.2, -1.2, 0)), 30)
shot('base_wide', 2.2, S('anon', size='WS', angle=8, bearing=200, lens=20, frame='center', fstop=5.6, move='push', amount=0.1), 'BASEMENT')
line('n10', [S('mensa', size='MCU', bearing=-70, lens=60, frame='right', fstop=2.0, move='push', amount=0.1)], 'BASEMENT')
michi.walk(ANIM - 0.4, BASE + Vector((-0.4, 0.3, 0)), speed=1.0)
line('m10', [S('michi', size='MCU', bearing=20, lens=60, frame='left', fstop=2.0)], 'BASEMENT', pad=0.15)
mensa.turn(ANIM, 200, 0.6)                                       # he spins the chair round
line('n11', [S('mensa', size='MS', bearing=10, lens=40, frame='center', fstop=2.8),
             S('mensa', size='MS', bearing=-80, lens=35, frame='right', fstop=4.0)], 'BASEMENT',
     weights=[1, 1.2])
line('a10', [S('anon', size='MCU', bearing=-20, lens=60, frame='right', fstop=2.0, move='push', amount=0.12)], 'BASEMENT')
line('s10', [S('slerf', size='MCU', angle='low', bearing=10, lens=55, frame='center', fstop=2.0)], 'BASEMENT', pad=0.8)
line('a11', [S('anon', size='CU', bearing=25, lens=75, frame='left', fstop=1.8)], 'BASEMENT')
line('s11', [S('slerf', size='CU', bearing=0, lens=70, frame='center', fstop=2.0, move='push', amount=0.2)], 'BASEMENT', pad=0.5)
line('mo10', [S('anon', size='WS', angle=-20, bearing=180, lens=24, frame='center', fstop=4.0, **{'with': ['michi', 'slerf']})],
     'BASEMENT', pad=0.4)

# ---------------------------------------------------------------- 2. the burning café
a = ANIM
fine.cut(a, CAFE + Vector((1.8, 1.4, 0)), 200)
toshi.cut(a, CAFE + Vector((3.0, 1.45, 0)), 190)
swordcat.cut(a, CAFE + Vector((4.6, -0.6, 0)), 230)
anon.cut(a, CAFE + Vector((1.2, -2.6, 0)), 10)
michi.cut(a, CAFE + Vector((0.2, -3.0, 0)), 15)
anon.walk(a + 0.3, CAFE + Vector((1.4, -0.4, 0)), speed=1.1)
shot('cafe_establish', 2.6, S('anon', distance=4.6, angle=14, bearing=200, lens=20, frame='center', fstop=5.6,
                              look_offset=(0.5, 1.6, 0)), 'CAFE')
line('f10', [S('fine', size='MCU', bearing=-15, lens=55, frame='right', fstop=2.0)], 'CAFE')
line('a12', [S('anon', size='MCU', bearing=30, lens=55, frame='left', fstop=2.2)], 'CAFE')
line('f11', [S('fine', size='CU', bearing=10, lens=70, frame='center', fstop=1.8, move='push', amount=0.08)], 'CAFE')
line('f12', [S('fine', size='MS', bearing=-35, lens=40, frame='left', fstop=2.8, **{'with': ['toshi']}),
             S('toshi', size='MCU', bearing=20, lens=60, frame='center', fstop=2.0)], 'CAFE', weights=[1.3, 1])
line('t10', [S('toshi', size='CU', bearing=-10, lens=75, frame='right', fstop=1.8)], 'CAFE')
line('f13', [S('swordcat', size='MS', angle='low', bearing=20, lens=40, frame='center', fstop=2.8, move='push', amount=0.15)], 'CAFE')
# the test: Swordcat at striking distance (1.3 m); three attacks, Anon blocks, leans out (slow motion), catches the blade
DUEL = ANIM
swordcat.walk(DUEL - 1.9, CAFE + Vector((0.3, 0.4, 0)), speed=2.4, then='ready')   # arrives before the duel (late, he slid
swordcat.face(DUEL - 0.1, anon, 0.15)                             # through it) and off the line to This-Is-Fine and Toshi
anon.face(DUEL - 0.1, swordcat, 0.2)
swordcat.play(DUEL + 0.4, 'attack1', 1.1)
anon.play(DUEL + 0.55, 'attack2@0.4')                             # the block: his paw meets the blade
anon.play(DUEL + 1.15, 'idle')
swordcat.play(DUEL + 1.3, 'attack2', 0.35)                        # slowed: the lean-out in slow motion
anon.lean(DUEL + 1.3, 0)
anon.lean(DUEL + 1.45, -22)
anon.lean(DUEL + 1.85, -22)
anon.lean(DUEL + 2.1, 0)
swordcat.play(DUEL + 2.2, 'attack3', 1.0)
anon.play(DUEL + 2.45, 'win@0.25')                                # both paws up: the blade caught between them
swordcat.play(DUEL + 2.62, 'attack3@0.45')                        # freeze on the strike
shot('duel_wide', 1.4, S('anon', size='WS', bearing=90, lens=32, frame='center', fstop=4.0, **{'with': ['swordcat']}), 'CAFE')
shot('duel_block', 0.9, S('anon', size='MS', bearing=60, lens=45, frame='center', fstop=2.8, **{'with': ['swordcat']}), 'CAFE')
shot('duel_lean', 2.4, S('anon', size='MS', angle='low', bearing=100, lens=35, frame='center', fstop=3.2, move='arc', amount=40,
                         **{'with': ['swordcat']}), 'CAFE', speed=0.3, hand=None)
shot('duel_catch', 1.6, S('anon', size='MCU', bearing=70, lens=50, frame='center', fstop=2.8, look_offset=(0, 0.3, 0.2),
                          **{'with': ['swordcat']}), 'CAFE', speed=0.4, hand=None)
swordcat.play(ANIM, 'idle')
anon.play(ANIM, 'idle')
line('w10', [S('swordcat', size='CU', bearing=35, lens=70, frame='right', fstop=1.8)], 'CAFE', pad=0.4)
toshi.walk(ANIM, CAFE + Vector((2.0, -0.2, 0)), speed=1.0)
line('t11', [S('toshi', size='MS', bearing=-60, lens=45, frame='center', fstop=2.8, **{'with': ['anon']})], 'CAFE')
line('f14', [S('fine', size='MCU', bearing=-45, lens=50, frame='center', fstop=2.4, move='pull', amount=0.3)], 'CAFE', pad=0.6)

# ---------------------------------------------------------------- 3. the Jeanphil brawl and the flight (rooftop, rain)
a = ANIM
anon.cut(a, ROOF + Vector((-1.0, -6.0, 0)), 20)
michi.cut(a, ROOF + Vector((-2.0, -6.6, 0)), 20)
toshi.cut(a, ROOF + Vector((-0.2, -6.8, 0)), 20)
jean.cut(a, ROOF + Vector((0, 4.0, 0)), 180)
CENTRE = ROOF + Vector((0, -0.8, 0))
anon.walk(a, CENTRE, speed=2.6, clip='run')
michi.walk(a + 0.2, ROOF + Vector((-6.0, -4.2, 0)), speed=2.4, clip='run')
toshi.walk(a + 0.3, ROOF + Vector((-6.4, -3.6, 0)), speed=2.4, clip='run')
shot('roof_run', 2.0, S('anon', size='WS', angle=8, bearing=160, lens=28, frame='center', fstop=4.0, move='track'), 'ROOFTOP')
line('j10', [S('jean', size='MCU', angle='low', bearing=0, lens=60, frame='center', fstop=2.0, move='push', amount=0.15)], 'ROOFTOP')
CLONE_T = ANIM                                                   # one by one the agents around the roof become Jeanphil
RING = 3.2
for k, c_ in enumerate(clones):
    ang = math.radians(15 + k * (330 / len(clones)))
    p_ = CENTRE + Vector((math.sin(ang) * RING, math.cos(ang) * RING, 0))
    c_.cut(a, p_, heading_to(p_, CENTRE))
anon.face(CLONE_T, jean, 0.3)
shot('clones_appear', 2.4, S('anon', size='EWS', angle=35, bearing=200, lens=24, frame='center', fstop=5.6, move='crane', amount=12),
     'ROOFTOP')
line('j11', [S('anon', size='WS', angle=15, bearing=180, lens=24, frame='center', fstop=4.0, **{'with': ['jean'] + CLONES})],
     'ROOFTOP', pad=0.3)
line('a13', [S('anon', size='MCU', bearing=-20, lens=60, frame='right', fstop=2.0, move='push', amount=0.1)], 'ROOFTOP')
# the brawl: they close in; Anon fights in a slow orbit; three pile on; the shockwave throws them all back
BRAWL = ANIM
for k, c_ in enumerate(clones):
    inner = CENTRE + (c_.pos - CENTRE).normalized() * 1.35
    c_.walk(BRAWL + 0.05 * k, inner, speed=1.6, then='ready')
anon.play(BRAWL + 0.9, 'attack1', 1.2)
anon.play(BRAWL + 1.6, 'attack2', 1.2)
anon.play(BRAWL + 2.3, 'attack3', 1.2)
for k, c_ in enumerate(clones[:3]):
    c_.play(BRAWL + 1.0 + k * 0.7, 'hit', 1.0)
shot('brawl_orbit', 3.6, S('anon', size='WS', angle=10, bearing=0, lens=28, frame='center', fstop=4.0, move='arc', amount=200,
                           **{'with': CLONES}), 'ROOFTOP', speed=0.8, hand=None)
WAVE_T = ANIM + 0.5
anon.play(WAVE_T - 0.3, 'win@0.25')
for k, c_ in enumerate(clones):
    out = CENTRE + (c_.pos - CENTRE).normalized() * (RING + 1.6)
    c_.hold(WAVE_T)
    c_.play(WAVE_T, 'hit', 0.8)
    c_.pos = out
    c_.keys.append([WAVE_T + 0.45, *out, c_.H, 0])
    c_.play(WAVE_T + 0.5, 'die', 1.2)
shot('shockwave', 2.6, S('anon', size='WS', angle=30, bearing=40, lens=24, frame='center', fstop=5.6, **{'with': CLONES}), 'ROOFTOP',
     speed=0.35, hand=None)
anon.play(ANIM, 'idle')
line('m11', [S('michi', size='MCU', bearing=-45, lens=55, frame='left', fstop=2.0, **{'with': ['toshi']})], 'ROOFTOP')
line('a14', [S('anon', size='CU', bearing=-30, lens=75, frame='right', fstop=1.8)], 'ROOFTOP', pad=0.15)
# the flight: the green candle ignites over his raised paw and he goes straight up into the rain
LAUNCH = ANIM + 0.3
anon.play(LAUNCH - 0.3, 'win@0.25')
anon.hold(LAUNCH)
anon.pos = CENTRE + Vector((0, 0, 28.0))
anon.keys.append([LAUNCH + 1.8, *anon.pos, anon.H, 0])
shot('launch', 1.2, S('anon', size='MS', angle='low', bearing=20, lens=28, frame='center', fstop=4.0), 'ROOFTOP')
shot('flight', 1.8, S('anon', distance=6.0, angle=-35, bearing=0, lens=24, frame='center', fstop=5.6, eye=0.8), 'ROOFTOP', hand=None)
FLIGHT_END = ANIM

# ---------------------------------------------------------------- 4. the Whale (the white room)
a = ANIM
anon.cut(a, WHITE + Vector((0, -3.5, 0)), 0, clip='walk')
whale.cut(a, WHITE + Vector((0, 4.6, 0.6)), 180)
for k in range(60):                                              # the Whale floats, rising and sinking slowly
    t_ = a + k * 0.6
    whale.keys.append([t_, WHITE.x, WHITE.y + 4.6, 0.6 + 0.08 * math.sin(k * 0.7), 180, 0])
anon.walk(a, WHITE + Vector((0, -0.6, 0)), speed=0.9)
shot('white_reveal', 3.2, S('anon', size='EWS', angle=6, bearing=180, lens=20, frame='center', fstop=8.0, move='push', amount=0.15,
                            look_offset=(0, 3.0, 0.6)), 'WHITE')
line('wh10', [S('whale', size='MS', angle=-20, bearing=0, lens=35, frame='center', fstop=4.0)], 'WHITE')
line('a15', [S('anon', size='MCU', bearing=20, lens=55, frame='left', fstop=2.4)], 'WHITE')
line('wh11', [S('whale', size='MCU', angle=-18, bearing=-25, lens=55, frame='right', fstop=2.8),
              S('anon', distance=4.0, bearing=180, lens=30, frame='center', fstop=5.6, look_offset=(0, 7.5, 2.2))], 'WHITE',
     weights=[1, 1.3])
line('wh12', [S('whale', size='MCU', angle=-18, bearing=0, lens=60, frame='center', fstop=2.0, move='push', amount=0.12)], 'WHITE')
line('a16', [S('anon', size='CU', bearing=-20, lens=75, frame='right', fstop=1.8)], 'WHITE')
line('wh13', [S('whale', size='MCU', angle=-18, bearing=20, lens=60, frame='left', fstop=2.4)], 'WHITE')
DOORS_T = ANIM
line('wh14', [S('anon', size='EWS', angle=28, bearing=180, lens=20, frame='center', fstop=5.6, look_offset=(0, 3.4, 0.6)),
              S('whale', size='MCU', angle=-18, bearing=-15, lens=60, frame='right', fstop=2.4)], 'WHITE', weights=[1.2, 1])
anon.walk(ANIM - 0.2, WHITE + Vector((2.4, 2.3, 0)), speed=0.8)
line('a17', [S('anon', size='MS', bearing=150, lens=35, frame='center', fstop=4.0, move='track')], 'WHITE', pad=0.6)
line('wh15', [S('whale', size='MCU', angle=-20, bearing=0, lens=70, frame='center', fstop=2.0, dutch=-6)], 'WHITE', pad=0.4)
anon.turn(ANIM, 200, 0.3)
line('a18', [S('anon', size='CU', bearing=0, lens=70, frame='center', fstop=1.8)], 'WHITE', pad=0.8)

# ---------------------------------------------------------------- 5. liquidation (rooftop, rain): the save and the last look
a = ANIM
michi.cut(a, ROOF + Vector((-6.0, -4.2, 0)), 200, clip='lose')
toshi.cut(a, ROOF + Vector((-7.8, -2.4, 0)), 160)          # (clear of the save and the collapse)
anon.cut(a, ROOF + Vector((-5.4, -2.2, 6.0)), 200)
for c_ in clones:
    c_.cut(a, OFF, 180)
jean.cut(a, ROOF + Vector((3.0, 4.0, 0)), 220)
LIQ = ANIM
shot('liquidating', 1.8, S('michi', size='MS', angle='high', bearing=10, lens=40, frame='center', fstop=2.8), 'ROOFTOP')
anon.hold(LIQ + 1.8)
anon.pos = ROOF + Vector((-5.5, -3.2, 0))
anon.keys.append([LIQ + 2.4, *anon.pos, anon.H, 0])                # he drops out of the rain beside her
anon.play(LIQ + 2.4, 'attack2@0.4')                                # and pushes the green candle into her chart
SAVE_T = LIQ + 2.6
michi.play(SAVE_T + 0.4, 'idle')
shot('the_save', 1.8, S('anon', size='MS', bearing=70, lens=35, frame='center', fstop=3.2, **{'with': ['michi']}), 'ROOFTOP')
line('m12', [S('michi', size='CU', bearing=20, lens=75, frame='left', fstop=1.8)], 'ROOFTOP', pad=0.3)
line('a19', [S('anon', size='MCU', bearing=-25, lens=60, frame='right', fstop=2.0)], 'ROOFTOP', pad=0.2)
anon.play(ANIM + 0.1, 'die', 0.8)
shot('collapse', 1.8, S('anon', size='WS', angle=25, bearing=60, lens=35, frame='center', fstop=4.0, **{'with': ['michi']}), 'ROOFTOP')
shot('last_jean', 2.4, S('jean', size='CU', bearing=-10, lens=85, frame='center', fstop=1.8, move='push', amount=0.15), 'ROOFTOP')
END_FILM, END_A = FILM, ANIM

# ================================================================ animated objects
if not DRY:
    # the bull cracks: a glowing red fissure drawn over its side (points found by rays, so it lies on the surface), growing
    # from the shoulder down while the camera pushes in, and a chunk of gold breaks off and falls
    dg = bpy.context.evaluated_depsgraph_get()
    crack_pts = []
    for k in range(12):
        x = FLOOR.x - 1.4 + k * 0.24
        z = 3.1 - k * 0.17 + (0.09 if k % 2 else -0.09)
        hit, loc, *_ = sc.ray_cast(dg, Vector((x, FLOOR.y + 6.0, z)), Vector((0, 1, 0)), distance=6.0)
        if hit:
            crack_pts.append(loc - Vector((0, 0.01, 0)))
    crack_m = mxsets.material('crack', (1.0, 0.1, 0.05), emit=(1.0, 0.12, 0.04), strength=12.0)
    cd = bpy.data.curves.new('bull_crack', 'CURVE')
    cd.dimensions = '3D'
    cd.bevel_depth = 0.018
    sp = cd.splines.new('POLY')
    sp.points.add(len(crack_pts) - 1)
    for p_, q_ in zip(sp.points, crack_pts):
        p_.co = (*q_, 1)
    crack = bpy.data.objects.new('bull_crack', cd)
    mxsets.collection('FLOOR').objects.link(crack)
    cd.materials.append(crack_m)
    animate(cd, 'bevel_factor_end', [(F(BULL_T + 0.2), 0.0), (F(BULL_T + 1.6), 1.0)], 'LINEAR')
    gold = mxsets.material('bull_chunk', (1.0, 0.72, 0.2), rough=0.25, metal=1.0)
    chunk = mxsets.box('bull_chunk', (0.35, 0.3, 0.28), (0, 0, 0), gold, PROPS, bevel=0.03)
    top = crack_pts[len(crack_pts) // 2] if crack_pts else FLOOR + Vector((0, 9.9, 2.0))
    animate(chunk, 'location', [(F(0), (0, 0, -50)), (F(BULL_T + 1.7) - 0.02, (0, 0, -50)), (F(BULL_T + 1.7), tuple(top)),
                                (F(BULL_T + 2.4), tuple(Vector((top.x - 0.2, top.y - 0.5, FLOOR.z + 1.2))))], 'LINEAR')
    animate(chunk, 'rotation_euler', [(F(BULL_T + 1.7), (0, 0, 0)), (F(BULL_T + 2.4), (1.2, 0.6, 0.3))], 'LINEAR')
    print('CRACK points', len(crack_pts))
    # the rocket: flames out of its base (crossed flame cards) and a bright green-white light, only in flight
    for k in range(3):
        fc_ = mxsets.plane(f'rocket_flame{k}', 0.16, 0.5, (0, 0, -0.42), sets2.flame_material(f'rocket_flame_m{k}', 4.0 + k),
                           PROPS, parent=ROCKET, rot=(math.radians(-90), 0, math.radians(60 * k)))
        fc_.visible_shadow = False
        fc_['cine_ignore'] = True
    show('rocket', [(0, False), (LAUNCH - 0.4, True), (FLIGHT_END, False)])
    show('save_candle', [(0, False), (LIQ + 1.9, True), (SAVE_T + 0.35, False)])
    show('seed_key', [(0, True)])
    for c_ in CLONES:                                             # the clones appear one by one
        show('shades_' + c_, [(0, True)])
    WAVE.location = CENTRE + Vector((0, 0, 0.08))
    animate(WAVE, 'scale', [(F(0), (0, 0, 0)), (F(WAVE_T) - 0.5, (0, 0, 0)), (F(WAVE_T), (0.2, 0.2, 1)), (F(WAVE_T + 0.6), (6.5, 6.5, 1)),
                            (F(WAVE_T + 0.62), (0, 0, 0))], 'LINEAR')
    wl = bpy.data.objects.new('shockwave_light', bpy.data.lights.new('shockwave_light', 'POINT'))
    wl.data.color = (0.3, 1.0, 0.45)
    sc.collection.objects.link(wl)
    wl.location = CENTRE + Vector((0, 0, 0.6))
    wl.data.animation_data_create()
    wa = bpy.data.actions.new('shockwave_light_energy')
    wl.data.animation_data.action = wa
    fc = wa.fcurves.new('energy')
    for f_, v_ in ((F(WAVE_T) - 0.5, 0.0), (F(WAVE_T), 4000.0), (F(WAVE_T + 0.6), 0.0)):
        fc.keyframe_points.insert(f_, v_)
    for actor in A.values():
        actor.finish(END_A + 2.0)
    # the clones become Jeanphil one by one: hidden (scale) until their moment
    for k, n in enumerate(CLONES):
        rig_ = A[n].rig
        animate(rig_, 'scale', [(F(0), (1e-4,) * 3), (F(CLONE_T + 0.12 * k) - 0.02, (1e-4,) * 3), (F(CLONE_T + 0.12 * k), (1, 1, 1))],
                'CONSTANT')

    GLOW = {'rocket': (0.15, 1.0, 0.3), 'save_candle': (0.15, 1.0, 0.3)}
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

# ================================================================ solve
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


EVENTS = {'duel': DUEL + 0.55, 'swing2': DUEL + 1.3, 'catch': DUEL + 2.62, 'clones': CLONE_T, 'wave': WAVE_T, 'launch': LAUNCH,
          'doors': DOORS_T, 'liquidation': LIQ, 'save': SAVE_T}
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
