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
sets2.dress_basement(BASE)                                         # more things, each on a real surface, then checked
sets2.dress_cafe(sets2.ORIGIN['CAFE'])
sets2.dress_rooftop(ROOF)
_C = sets2.ORIGIN['CAFE']
sets2.check_dressing({'couch': (BASE.x - 9.8, BASE.x + 9.8, BASE.y - 8.8, BASE.y + 8.8, 4.95),
                      'shelf': (BASE.x - 9.8, BASE.x + 9.8, BASE.y - 8.8, BASE.y + 8.8, 4.95),
                      'mini_fridge': (BASE.x - 9.8, BASE.x + 9.8, BASE.y - 8.8, BASE.y + 8.8, 4.95),
                      'side_': (BASE.x - 9.8, BASE.x + 9.8, BASE.y - 8.8, BASE.y + 8.8, 4.95),
                      'debris': (_C.x - 5.85, _C.x + 5.85, _C.y - 4.85, _C.y + 4.85, 4.15),
                      'ceiling_tile': (_C.x - 5.85, _C.x + 5.85, _C.y - 4.85, _C.y + 4.85, 4.15),
                      'elec_box': (ROOF.x - 16.5, ROOF.x + 16.5, ROOF.y - 16.5, ROOF.y + 16.5, 30)})
for m_ in bpy.data.materials:                                     # the rooftop in rain: a wet, reflective floor
    if m_.name.startswith(('roof', 'ground_roof')) and m_.use_nodes and 'Principled BSDF' in m_.node_tree.nodes:
        m_.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.12
        if m_.name.startswith(('roof_gravel', 'ground_roof')):
            sets2.wet_floor(m_)                                       # puddles between wet gravel, rain in the puddles
if 'rooftop_sky' in bpy.data.materials:
    sets2.night_sky(bpy.data.materials['rooftop_sky'])            # city glow on the horizon, clouds
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
    ROCKET = mxsets.candle('rocket', 'green', PROPS, size=2.6, trail=0.0, glow=4.0)   # (a long trail read as a green bar)
    ROCKET.rotation_euler = (0, 0, 0)                               # upright over his raised right paw, the streak below it
    place(ROCKET, A['anon'], paw_top(P, -1, 0.8, 1.8, 0.2, only=AN_RF), 0.24, AN_RF)
    P = posed(A['anon'], 'attack2', 0.4)
    AN_REACH = paw_fwd(P, AN_RF)
    SAVE = mxsets.candle('save_candle', 'green', PROPS, size=1.5, glow=2.0)
    place(SAVE, A['anon'], AN_REACH, 0.1, AN_RF)
    # Toshi's key ring of seed words: a glowing ring at her chest
    key_m = mxsets.material('seed_key', (1.0, 0.75, 0.2), emit=(1.0, 0.7, 0.15), strength=1.2)
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
shot('bull_crack', 3.0, S('anon', distance=5.0, angle=6, bearing=180, lens=35, frame='center', fstop=4.0, move='push', amount=0.2,
                          look_offset=(-0.2, 8.0, 1.0)), 'FLOOR')                 # close on the fissure and the falling chunk

# ---------------------------------------------------------------- 1. the rug: Mom's basement
a = ANIM
mensa.cut(a, BASE + Vector((2.5, 0.72, 0)), 20)
michi.cut(a, BASE + Vector((-1.2, 0.2, 0)), 120)
slerf.cut(a, BASE + Vector((0.8, 1.2, 0)), 200)
anon.cut(a, BASE + Vector((-0.2, -1.2, 0)), 30)
shot('base_wide', 2.2, S('anon', size='WS', angle=8, bearing=200, lens=20, frame='center', fstop=5.6, move='push', amount=0.1), 'BASEMENT')
line('n10', [S('mensa', size='MCU', bearing=35, lens=60, frame='right', fstop=2.0, move='push', amount=0.1)], 'BASEMENT')
michi.walk(ANIM - 0.4, BASE + Vector((-0.4, 0.3, 0)), speed=1.0)
line('m10', [S('michi', size='MS', bearing=25, lens=45, frame='left', fstop=2.8, **{'with': ['slerf']})], 'BASEMENT', pad=0.15)
mensa.turn(ANIM, 200, 0.6)                                       # he spins the chair round
CRT_T = ANIM                                                      # the CRT fills with Jeanphils: one, four, sixteen
line('n11', [S('mensa', size='MS', bearing=-25, lens=40, frame='center', fstop=2.8, fixed_heading=200),   # (camera held while he spins)
             S('mensa', size='MCU', lens=21, frame=(0.0, 0.0), fstop=5.6, crt=True)], 'BASEMENT',
     weights=[1, 1.2])                                           # (the second shot: the CRT, placed on its screen below)
line('a10', [S('anon', size='MCU', bearing=-20, lens=60, frame='right', fstop=2.0, move='push', amount=0.12)], 'BASEMENT')
line('s10', [S('slerf', size='MCU', angle='low', bearing=10, lens=55, frame='center', fstop=2.0)], 'BASEMENT', pad=0.8)
line('a11', [S('anon', size='CU', bearing=25, lens=75, frame='left', fstop=1.8)], 'BASEMENT')
line('s11', [S('slerf', size='MCU', bearing=-30, lens=70, frame='center', fstop=2.0, move='push', amount=0.12)], 'BASEMENT', pad=0.5)
line('mo10', [S('anon', size='WS', angle=-12, bearing=180, lens=35, frame='center', fstop=4.0, **{'with': ['michi', 'slerf']})],
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
line('f10', [S('fine', size='MCU', bearing=25, lens=55, frame='left', fstop=2.0)], 'CAFE')
line('a12', [S('anon', size='MCU', bearing=30, lens=55, frame='left', fstop=2.2)], 'CAFE')
line('f11', [S('fine', size='CU', bearing=10, lens=70, frame='center', fstop=1.8, move='push', amount=0.08)], 'CAFE')
line('f12', [S('fine', size='MS', bearing=-35, lens=40, frame='left', fstop=2.8, **{'with': ['toshi']}),
             S('toshi', size='MCU', bearing=20, lens=60, frame='center', fstop=2.0)], 'CAFE', weights=[1.3, 1])
line('t10', [S('toshi', size='MCU', bearing=-10, lens=70, frame='right', fstop=2.0)], 'CAFE')
H_walk = heading_to(CAFE + Vector((4.6, -0.6, 0)), CAFE + Vector((0.3, 0.4, 0)))   # (camera held on his walk heading: as he
line('f13', [S('swordcat', size='MS', angle=-5, bearing=-55, lens=35, frame='center', fstop=2.8, move='push', amount=0.15,  # turned
               fixed_heading=H_walk)], 'CAFE')                    # into the walk the camera swung 1.8 m in a frame)
# the test: Swordcat at striking distance (1.3 m); three attacks, Anon blocks, leans out (slow motion), catches the blade
DUEL = ANIM
swordcat.walk(DUEL - 2.8, CAFE + Vector((0.3, 0.4, 0)), speed=2.4, then='ready')   # arrives before the duel (late, he slid
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
swordcat.play(DUEL + 2.2, 'attack1', 1.0)
# the catch, measured on the blade prop (prop_blade, parented to his right hand): his thrust (attack1 at 60 %) holds the blade
# level at 1.31 m, pointing straight ahead, the point 0.96 m out a hand's width from the tip; Anon's raised paws (win at 25 %) meet 0.29 m in front of him at 1.47 m, 0.82 m apart. Anon steps
# in so the middle of his paws is on the blade.
def rot_(v, H):
    r = math.radians(180 - H)
    return Vector((v.x * math.cos(r) - v.y * math.sin(r), v.x * math.sin(r) + v.y * math.cos(r), 0))
Hs = heading_to(swordcat.pos, anon.pos)
catch_w = swordcat.pos + rot_(Vector((-0.26, -0.96, 0)), Hs)
Ha = (Hs + 180) % 360
CATCH_AT = catch_w - rot_(Vector((0, -0.29, 0)), Ha)
anon.hold(DUEL + 2.2)
anon.pos, anon.H = CATCH_AT, Ha
anon.keys.append([DUEL + 2.45, *CATCH_AT, Ha, 0])
anon.play(DUEL + 2.45, 'win@0.25')                                # both paws up: the blade caught between them
swordcat.play(DUEL + 2.5, 'attack1@0.6')                          # freeze on the thrust, the blade between his paws
EVENTS_CATCH = DUEL + 2.62
shot('duel_wide', 1.4, S('anon', size='WS', bearing=90, lens=32, frame='center', fstop=4.0, **{'with': ['swordcat']}), 'CAFE')
shot('duel_block', 0.9, S('anon', size='MS', bearing=60, lens=45, frame='center', fstop=2.8, **{'with': ['swordcat']}), 'CAFE')
shot('duel_lean', 2.4, S('anon', size='MS', angle='low', bearing=100, lens=35, frame='center', fstop=3.2, move='arc', amount=40,
                         **{'with': ['swordcat']}), 'CAFE', speed=0.3, hand=None)
shot('duel_catch', 1.6, S('anon', size='MS', bearing=-90, lens=40, frame='center', fstop=3.2, look_offset=(-0.55, 0.4, -0.05),
                          **{'with': ['swordcat']}), 'CAFE', speed=0.4, hand=None)
CATCH_PT = catch_w + Vector((0, 0, 1.31))                         # the insert: the blade between his paws, side-on, slow
shot('catch_insert', 1.1, S('anon', size='CU', lens=42, frame=(0.0, 0.0), fstop=2.8, catch_insert=True), 'CAFE', speed=0.25, hand=None)
swordcat.play(ANIM, 'idle')
anon.play(ANIM, 'idle')
line('w10', [S('swordcat', size='MCU', bearing=-35, lens=60, frame='left', fstop=2.0)], 'CAFE', pad=0.4)
toshi.walk(ANIM, CAFE + Vector((2.0, -0.2, 0)), speed=1.0)
line('t11', [S('toshi', size='MS', bearing=-60, lens=45, frame='center', fstop=2.8, **{'with': ['anon']})], 'CAFE')
line('f14', [S('fine', size='MCU', bearing=-45, lens=50, frame='center', fstop=2.4, move='pull', amount=0.3)], 'CAFE', pad=0.6)

# ---------------------------------------------------------------- 3. the Jeanphil brawl and the flight (rooftop, rain)
a = ANIM
ROOF_A = a
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
line('j11', [S('anon', size='WS', angle=32, bearing=180, lens=24, frame='center', fstop=4.0, **{'with': ['jean'] + CLONES})],
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
shot('launch', 1.2, S('anon', size='WS', angle='low', bearing=20, lens=28, frame='center', fstop=4.0, look_offset=(0, 0, 0.4)), 'ROOFTOP')
shot('flight', 1.8, S('anon', distance=3.4, angle=-30, bearing=40, lens=24, frame='center', fstop=5.6, eye=1.25), 'ROOFTOP', hand=None)
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
line('a15', [S('anon', size='MS', bearing=20, lens=45, frame='left', fstop=2.8)], 'WHITE')
line('wh11', [S('whale', size='MCU', angle=-18, bearing=-25, lens=55, frame='right', fstop=2.8, look_offset=(0, 0, 0.18)),
              S('anon', distance=4.0, bearing=180, lens=30, frame='center', fstop=5.6, look_offset=(0, 7.5, 2.2))], 'WHITE',
     weights=[1, 1.3])
line('wh12', [S('whale', size='MCU', angle=-18, bearing=0, lens=60, frame='center', fstop=2.0, move='push', amount=0.12, look_offset=(0, 0, 0.18))], 'WHITE')
line('a16', [S('anon', size='MCU', bearing=-20, lens=70, frame='right', fstop=2.0)], 'WHITE')
line('wh13', [S('whale', size='MS', angle=-12, bearing=40, lens=40, frame='left', fstop=2.8)], 'WHITE')
DOORS_T = ANIM
line('wh14', [S('anon', size='WS', angle=14, bearing=180, lens=24, frame='center', fstop=5.6, look_offset=(0, 3.4, 1.05)),
              S('whale', size='MCU', angle=-18, bearing=-15, lens=60, frame='right', fstop=2.4, look_offset=(0, 0, 0.18))], 'WHITE', weights=[1.2, 1])
anon.walk(ANIM - 0.2, WHITE + Vector((2.4, 2.3, 0)), speed=0.8)
line('a17', [S('anon', size='MS', bearing=150, lens=35, frame='center', fstop=4.0, move='track')], 'WHITE', pad=0.6)
line('wh15', [S('whale', size='MCU', angle=-20, bearing=0, lens=70, frame='center', fstop=2.0, dutch=-6, look_offset=(0, 0, 0.18))], 'WHITE', pad=0.4)
anon.turn(ANIM, 200, 0.3)
line('a18', [S('anon', size='CU', bearing=0, lens=70, frame='center', fstop=1.8, fixed_heading=200)], 'WHITE', pad=0.8)   # (he turns as it starts)

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
anon.play(SAVE_T + 0.55, 'idle')                                 # he straightens up from the push
shot('the_save', 1.8, S('anon', size='MS', bearing=115, lens=35, frame='center', fstop=3.2, **{'with': ['michi']}), 'ROOFTOP')
line('m12', [S('michi', size='CU', bearing=20, lens=75, frame='left', fstop=1.8)], 'ROOFTOP', pad=0.3)
H_a19 = heading_to(anon.pos, michi.pos)
anon.turn(ANIM, H_a19, 0.35)                                      # he turns to her as he answers (after her close-up)
michi.turn(ANIM, heading_to(michi.pos, anon.pos), 0.35)           # and she to him
line('a19', [S('anon', size='MCU', bearing=35, lens=60, frame='left', fstop=2.0, fixed_heading=H_a19)], 'ROOFTOP', pad=0.2)
FALL_T = ANIM - 0.2                                               # he collapses: the fall lands at FALL_T + 0.9
anon.play(FALL_T, 'die', 1.6)
anon.hold(FALL_T + 0.6)
anon.pos = anon.pos - Vector((0, 0, 0.27))                       # lying on his back the tail props him up: lower him onto the
anon.keys.append([FALL_T + 0.95, *anon.pos, anon.H, 0])          # roof while the tail swings flat (below)
shot('collapse', 1.8, S('anon', size='WS', angle=40, bearing=160, lens=35, frame='center', fstop=4.0, **{'with': ['michi']}), 'ROOFTOP')
shot('last_jean', 2.4, S('jean', size='CU', bearing=-10, lens=85, frame='center', fstop=1.8, move='push', amount=0.15), 'ROOFTOP')
END_FILM, END_A = FILM, ANIM

# ================================================================ animated objects
if not DRY:
    crt = bpy.data.objects.get('rain_crt')
    tv_ = bpy.data.objects.get('crt_tv.001')
    if crt is not None and tv_ is not None:                    # the TV model's sticky notes overhang the glass: lift them off
        import bmesh
        inv_ = crt.matrix_world.inverted()
        hx_, hy_ = crt.dimensions.x * 0.5, crt.dimensions.y * 0.5
        for ob_ in [c for c in tv_.children_recursive if c.type == 'MESH' and c.name.startswith('body')]:
            bm_ = bmesh.new(); bm_.from_mesh(ob_.data)
            seed_ = set()
            for f_ in bm_.faces:
                lp_ = inv_ @ (ob_.matrix_world @ f_.calc_center_median())
                if abs(lp_.x) < hx_ and abs(lp_.y) < hy_ and lp_.z > -0.012:
                    seed_.add(f_)
            isl_, todo_ = set(seed_), list(seed_)          # whole notes: every face linked to one over the screen
            while todo_:
                for e_ in todo_.pop().edges:
                    for g_ in e_.link_faces:
                        if g_ not in isl_:
                            isl_.add(g_); todo_.append(g_)
            if seed_ and len(isl_) < len(bm_.faces) * 0.2:     # (never the TV's shell itself)
                bmesh.ops.delete(bm_, geom=list(isl_), context='FACES')
                bm_.to_mesh(ob_.data)
                print('CRT notes removed', ob_.name, len(isl_))
            bm_.free()
    if crt is not None:
        for k, n_ in enumerate((1, 4, 16)):
            m_ = mxsets.image_material(f'crt_jean{n_}', os.path.join(HERE, 'pack', 'props', f'crt_jean{n_}.png'), emit=2.5)
            pl = crt.copy(); pl.data = crt.data.copy()
            pl.data.materials.clear(); pl.data.materials.append(m_)
            pl.name = f'crt_jean{n_}'
            mxsets.collection('BASEMENT').objects.link(pl)
            nrm = crt.matrix_world.to_quaternion() @ Vector((0, 0, 1))
            pl.location = crt.location + nrm * (0.02 + 0.004 * (k + 1))     # in front of the bezel's sticky notes
            ins_ = next((x for x in SHOTS if x['cam'].get('crt')), None)        # timed to the insert: the cut lands on one face
            t_ = (ins_['a0'] + 0.15 + k * 0.8) if ins_ else (CRT_T + 0.6 + k * 1.1)
            show(pl.name, [(0, False), (t_, True), (CRT_T + 9.0, False)])
    # the fall: his tail curls straight down under him; swing it out flat along the roof (a hook on the tail, pivoting at its
    # root, weighted from root to tip) while the rig lowers him onto the roof (as in episode 1's fall)
    an = A['anon']
    body = skin(an)
    tail = {v.index: min(1.0, max(0.0, (v.co.y - 0.24) / 0.22)) ** 1.2 for v in body.data.vertices if v.co.y > 0.24 and v.co.z < 0.75}
    vg = body.vertex_groups.new(name='tail_hook')
    for i_, w_ in tail.items():
        vg.add([i_], w_, 'REPLACE')
    sc.frame_set(int(F(FALL_T + 1.5)))
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
    animate(hook_e, 'rotation_quaternion', [(F(0), ident), (F(FALL_T + 0.3), ident), (F(FALL_T + 0.9), tuple(q))], 'BEZIER')
    print('TAIL base', tuple(round(v, 2) for v in base), 'tip', tuple(round(v, 2) for v in tipc), 'swing', round(math.degrees(q.angle)), 'deg')

    # the bull cracks: a glowing red fissure drawn over its side (points found by rays, so it lies on the surface), growing
    # from the shoulder down while the camera pushes in, and a chunk of gold breaks off and falls
    dg = bpy.context.evaluated_depsgraph_get()
    crack_pts = []
    for k in range(12):
        x = FLOOR.x - 1.4 + k * 0.24
        z = 3.1 - k * 0.17 + (0.09 if k % 2 else -0.09)
        hit, loc, _n, _i, hob, _m = sc.ray_cast(dg, Vector((x, FLOOR.y + 6.0, z)), Vector((0, 1, 0)), distance=6.0)
        if hit and hob.name.startswith('ex_bull'):                  # only on the bull (a hit on a leg then the plinth
            crack_pts.append(loc - Vector((0, 0.01, 0)))           # drew a segment through the air)
        elif crack_pts:
            break
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
    for o_ in bpy.data.objects:                                   # the bull's laser eyes sputter and die as it cracks
        if o_.name.startswith('fx_glow_eyes') and o_.parent and o_.parent.name.startswith('exchange_ex_bull'):
            show(o_.name, [(0, True), (BULL_T + 0.7, False), (BULL_T + 0.78, True), (BULL_T + 0.86, False),
                           (BULL_T + 0.95, True), (BULL_T + 1.0, False)])
    # the rocket: flames out of its base (crossed flame cards) and a bright green-white light, only in flight
    for k in range(3):
        fc_ = mxsets.plane(f'rocket_flame{k}', 0.3, 1.1, (0, 0, -0.78), sets2.flame_material(f'rocket_flame_m{k}', 4.0 + k),
                           PROPS, parent=ROCKET, rot=(math.radians(-90), 0, math.radians(60 * k)))
        fc_.visible_shadow = False
        fc_['cine_ignore'] = True
    # the exhaust: a green flare out of the candle's base, 3 m long, flickering and fading to nothing (origin at its top)
    plume_m = sets2.exhaust_material('plume')                     # bright at the nozzle, fading out below (a solid
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.1, radius2=0.03, depth=1.0)   # streak read as a pole), flaring wider
    plume = bpy.context.active_object
    plume.name = 'rocket_plume'
    for c_ in list(plume.users_collection):
        c_.objects.unlink(plume)
    PROPS.objects.link(plume)
    plume.data.materials.append(plume_m)
    plume.data.transform(Matrix.Translation((0, 0, -0.5)))
    plume.parent = ROCKET
    plume.location = (0, 0, -0.25)
    plume.visible_shadow = False
    plume['cine_ignore'] = True
    animate(plume, 'scale', [(F(0), (1, 1, 0.001)), (F(LAUNCH), (1, 1, 0.001)), (F(LAUNCH + 0.5), (1.0, 1.0, 2.6))], 'LINEAR')
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

# ---------------------------------------------------------------- effects: lightning over the roof, sparks
FLASHES = [ROOF_A + 0.35, CLONE_T + 0.05, LIQ + 0.25]                  # lightning over the roof (big flash 0.2 s in)
if not DRY:
    # lightning: a cold sun that strobes (two quick flickers, then the big flash) and the sky lighting up with it
    bolt = bpy.data.objects.new('lightning', bpy.data.lights.new('lightning', 'SUN'))
    bolt.data.color = (0.72, 0.85, 1.0)
    bolt.data.angle = math.radians(6)
    bolt.rotation_euler = (math.radians(35), 0, math.radians(-30))
    mxsets.collection('L_ROOFTOP').objects.link(bolt)
    en_, sky_ = [(F(0), 0.0)], [(F(0), 0.0)]
    for t_ in FLASHES:
        for dt_, e_ in ((0.0, 4.0), (0.05, 0.3), (0.1, 2.0), (0.14, 0.2), (0.2, 9.0), (0.32, 2.5), (0.45, 0.0)):
            en_.append((F(t_ + dt_), e_))
            sky_.append((F(t_ + dt_), e_ * 1.6))
    bolt.data.animation_data_create()
    act_ = bpy.data.actions.new('lightning_energy')
    bolt.data.animation_data.action = act_
    fc_ = act_.fcurves.new('energy')
    for f_, v_ in en_:
        fc_.keyframe_points.insert(f_, v_).interpolation = 'LINEAR'
    skym_ = bpy.data.materials.get('rooftop_sky')
    if skym_ and 'sky_flash' in skym_.node_tree.nodes:
        sock_ = skym_.node_tree.nodes['sky_flash'].inputs[1]
        for f_, v_ in sky_:
            sock_.default_value = v_
            sock_.keyframe_insert('default_value', frame=f_)
        for fc in skym_.node_tree.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    print('LIGHTNING at', [round(t_, 2) for t_ in FLASHES])

    def burst(name, where_, t_, dur, **kw):
        cloud_, spark_ = sets2.spark_burst(name, where_, PROPS, **kw)
        kb_ = cloud_.data.shape_keys.key_blocks['burst']
        for f_, v_ in ((F(0), 0.0), (F(t_), 0.0), (F(t_ + dur * 0.35), 0.75), (F(t_ + dur), 1.0)):
            kb_.value = v_
            kb_.keyframe_insert('value', frame=f_)
        animate(spark_, 'scale', [(F(0), (0, 0, 0)), (F(t_) - 0.02, (0, 0, 0)), (F(t_), (1, 1, 1)),
                                  (F(t_ + dur * 0.6), (1, 1, 1)), (F(t_ + dur), (0, 0, 0))], 'LINEAR')
        return cloud_
    burst('launch_sparks', CENTRE + Vector((0, 0, 0.15)), LAUNCH - 0.05, 0.8, count=260, radius=2.6, seed=4, up=0.9,
          colour=(0.4, 1.0, 0.5), strength=30.0, size=0.02)                     # green: the candle's own fire hitting the roof

if not DRY:                                                        # the duel from the open side of the café, side-on to the fight
    wh_ = make_where({n: sorted(x.keys, key=lambda k: k[0]) for n, x in A.items()})
    for s_ in SHOTS:
        if s_['name'] in ('duel_wide', 'duel_block', 'duel_lean'):
            a_mid = s_['a0'] + (s_['t1'] - s_['t0']) * s_['s0'] * 0.5
            pa, ha = wh_('anon', a_mid)
            ps, _ = wh_('swordcat', a_mid)
            mid = (Vector(pa) + Vector(ps)) / 2
            d_ = (Vector(ps) - Vector(pa)).normalized()
            perp = Vector((-d_.y, d_.x, 0))
            if perp.y > 0:                                         # the side away from the counter (This-Is-Fine and Toshi)
                perp = -perp
            dist, up = {'duel_wide': (3.4, 0.6), 'duel_block': (2.9, 0.75), 'duel_lean': (2.9, 0.6)}[s_['name']]
            s_['cam']['lens'] = 28 if s_['name'] != 'duel_wide' else s_['cam'].get('lens', 32)
            look = mid + Vector((0, 0, 1.0))
            s_['cam']['look_offset'] = list(look - cine.eye_point('anon', pa, ha))
            s_['cam']['cam_at'] = list(look + perp * dist + Vector((0, 0, up)) - d_ * (0.3 if s_['name'] == 'duel_lean' else 0))
            s_['cam']['cam_at1'] = list(look + perp * (dist * 0.9) + Vector((0, 0, up)) + d_ * (0.3 if s_['name'] == 'duel_lean' else 0))

    for s_ in SHOTS:
        if s_['cam'].get('catch_insert'):
            pa, _ = wh_('anon', s_['a0'])
            ps, _ = wh_('swordcat', s_['a0'])
            d_ = (Vector(ps) - Vector(pa)).normalized()
            perp = Vector((-d_.y, d_.x, 0))
            if perp.y > 0:
                perp = -perp
            # measured on the blade itself at that moment: side-on to the steel, on the open side, aimed at its last third
            # (where it meets Anon's paws and bag); the planned catch point sat 12 cm low and the near paw filled the frame
            sc.frame_set(int(F(s_['a0'])) + 1)
            bl_ = next((o for o in bpy.data.objects if o.name.startswith('prop_blade') and o.parent
                        and o.parent.name.startswith('swordcat')), None)
            look_ = CATCH_PT
            if bl_ is not None:
                bb_ = [bl_.matrix_world @ Vector(v) for v in bl_.bound_box]
                _, e0, e1 = max(((a - b).length, a, b) for a in bb_ for b in bb_)
                tip_, hilt_ = (e0, e1) if (e0 - Vector(pa)).length < (e1 - Vector(pa)).length else (e1, e0)
                look_ = hilt_.lerp(tip_, 0.7)
                ax_ = (tip_ - hilt_); ax_.z = 0; ax_.normalize()
                perp = Vector((-ax_.y, ax_.x, 0))
                if perp.y > 0:
                    perp = -perp
            s_['cam']['look_at'] = list(look_)
            s_['cam']['cam_at'] = list(look_ + perp * 0.95 + Vector((0, 0, 0.18)))
            s_['cam']['cam_at1'] = list(look_ + perp * 0.8 + Vector((0, 0, 0.12)))
            print('CATCH insert look', tuple(round(v, 2) for v in look_))
            burst('catch_sparks', look_, EVENTS_CATCH - 0.06, 0.5, count=70, radius=0.55, seed=11, up=0.5)   # steel on steel

if not DRY:                                                        # the CRT insert: straight onto its screen, easing in
    crt = bpy.data.objects.get('rain_crt')
    for s_ in SHOTS:
        if s_['cam'].get('crt') and crt is not None:
            c_ = sum((crt.matrix_world @ Vector(v) for v in crt.bound_box), Vector()) / 8   # the screen's centre, not its origin
            n_ = (crt.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
            if n_.dot(Vector(make_where({k: sorted(x.keys, key=lambda q: q[0]) for k, x in A.items()})('mensa', s_['a0'])[0]) - c_) < 0:
                n_ = -n_                                            # the screen side faces Mensa
            feet, head = make_where({k: sorted(x.keys, key=lambda q: q[0]) for k, x in A.items()})('mensa', s_['a0'] + 0.5)
            s_['cam']['look_at'] = list(c_)             # (an offset from Mensa drifted as he turned)
            rt_ = (-n_).cross(Vector((0, 0, 1))).normalized()       # a touch to the right: Mensa's head sits left of the lens
            s_['cam']['cam_at'] = list(c_ + n_ * 0.52 + rt_ * 0.05 + Vector((0, 0, 0.02)))
            s_['cam']['cam_at1'] = list(c_ + n_ * 0.74 + rt_ * 0.4 + Vector((0, 0, 0.05)))   # pulls back as the grid multiplies

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


EVENTS = {'duel': DUEL + 0.55, 'swing2': DUEL + 1.3, 'catch': EVENTS_CATCH, 'clones': CLONE_T, 'wave': WAVE_T, 'launch': LAUNCH,
          'doors': DOORS_T, 'liquidation': LIQ, 'save': SAVE_T}
EVENTS = {k: film_of(v) for k, v in EVENTS.items()}
EVENTS['lightning'] = [film_of(t_ + 0.2) for t_ in FLASHES]
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
