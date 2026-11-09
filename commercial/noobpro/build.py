"""NOOB vs PRO in MEME ROYALE: a vertical 'pro tip' short, built in Blender from the game's own models.

blender -b --factory-startup -P build.py -- --out scene.blend [--overlay overlay.json] [--samples 24]

Deterministic: every position, clip and hit is computed here from the timeline below, so every worker that runs
this builds the identical scene and renders identical frames. The 2D layer (HP bars, captions, the red X and the
green check, the end card) is drawn afterwards by overlay.py from overlay.json, which this script also writes.

Field coordinates are the game's: x 0..18 across, z 0..32 from the enemy's end to mine; Blender X = x, Y = -z.
"""
import bpy, math, json, os, sys
from mathutils import Vector

A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None):
    return A[A.index(k) + 1] if k in A else d
OUT = arg('--out', 'scene.blend'); OVL = arg('--overlay'); SAMPLES = int(arg('--samples', '16'))
HERE = os.path.dirname(os.path.abspath(__file__)); M = os.path.join(HERE, 'models')
FPS = 30; LAST = 720

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = LAST
sc.render.resolution_x, sc.render.resolution_y = 720, 1280
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.03
sc.render.film_transparent = False; sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'

P = lambda x, z, y=0.0: Vector((x, -z, y))

# ---------------------------------------------------------------- materials
def mat(name, color, rough=0.6, emit=None, estr=0.0, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = estr
    return m
def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

def floor_mat():
    m = bpy.data.materials.new('floor'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.85
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 1, 1)
    ck = N.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 1.0
    ck.inputs['Color1'].default_value = (*srgb('#b9ab93'), 1); ck.inputs['Color2'].default_value = (*srgb('#a59880'), 1)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; nz.inputs['Detail'].default_value = 4
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.25
    L.new(tc.outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], ck.inputs['Vector']); L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    L.new(ck.outputs['Color'], mix.inputs['A']); L.new(nz.outputs['Color'], mix.inputs['B'])
    L.new(mix.outputs['Result'], b.inputs['Base Color'])
    # grout lines on the tile edges
    br = N.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 1.0; br.offset = 0.0; br.squash = 1.0
    br.inputs['Mortar Size'].default_value = 0.03; br.inputs['Brick Width'].default_value = 1.0; br.inputs['Row Height'].default_value = 1.0
    br.inputs['Mortar'].default_value = (*srgb('#6f6455'), 1)
    L.new(mp.outputs['Vector'], br.inputs['Vector'])
    mix2 = N.new('ShaderNodeMix'); mix2.data_type = 'RGBA'
    L.new(br.outputs['Fac'], mix2.inputs['Factor']); L.new(mix.outputs['Result'], mix2.inputs['A']); mix2.inputs['B'].default_value = (*srgb('#6f6455'), 1)
    L.new(mix2.outputs['Result'], b.inputs['Base Color'])
    return m

def river_mat():
    m = bpy.data.materials.new('goo'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Base Color'].default_value = (*srgb('#39ff4a'), 1); b.inputs['Roughness'].default_value = 0.15
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.4; nz.inputs['Detail'].default_value = 3
    tc = N.new('ShaderNodeTexCoord'); L.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (*srgb('#0f8a2a'), 1)
    ramp.color_ramp.elements[1].position = 0.7; ramp.color_ramp.elements[1].color = (*srgb('#7dff6a'), 1)
    L.new(nz.outputs['Fac'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    L.new(ramp.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 0.6
    return m

def box(name, loc, size, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m)
    if bevel: md = o.modifiers.new('b', 'BEVEL'); md.width = bevel; md.segments = 2
    return o

# ---------------------------------------------------------------- the arena
MF = floor_mat(); MR = river_mat()
ML = mat('lane', srgb('#d24b4b'), 0.8); MW = mat('wall', srgb('#4b3f36'), 0.9); MWT = mat('walltop', srgb('#d8b45a'), 0.4, metal=0.6)
MBANK = mat('bank', srgb('#5a4a3a'), 0.9)
for zz0, zz1 in ((0, 15.1), (16.9, 32)):
    f = box('floor', P(9, (zz0 + zz1) / 2, -0.05), (18, zz1 - zz0, 0.1), MF)
box('river', P(9, 16, -0.25), (18, 1.8, 0.1), MR)
for zz in (15.05, 16.95): box('bank', P(9, zz, -0.15), (18, 0.12, 0.3), MBANK)
# the lane carpets from each princess tower to its bridge (the reference's red line)
for x in (3.5, 14.5):
    for zz0, zz1 in ((6.5, 15.0), (17.0, 25.5)):
        box('lane', P(x, (zz0 + zz1) / 2, 0.004), (0.55, zz1 - zz0, 0.01), ML)
# the outer wall
for x in (-0.6, 18.6): box('wall', P(x, 16, 0.5), (1.2, 33.2, 1.0), MW, 0.06); box('walltop', P(x, 16, 1.02), (1.25, 33.2, 0.06), MWT)
for z in (-0.6, 32.6): box('wall', P(9, z, 0.5), (19.2, 1.2, 1.0), MW, 0.06)
# outside the arena: a dark ground so the frame edges aren't empty
box('ground', P(9, 16, -0.3), (60, 70, 0.1), mat('out', srgb('#2a2140'), 1.0))

def import_glb(fn):
    before = set(bpy.data.objects); acts_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.join(M, fn))
    new = [o for o in bpy.data.objects if o not in before]; acts = [a for a in bpy.data.actions if a not in acts_before]
    root = bpy.data.objects.new(fn.split('.')[0] + '_root', None); sc.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    return root, new, acts

TEAM = {0: srgb('#2f7bff'), 1: srgb('#ff3b3b')}
def tower(x, z, team):
    root, objs, _ = import_glb('tower_rig.glb'); root.location = P(x, z)
    if team == 1: root.rotation_euler.z = math.pi
    m = mat(f'team{team}', TEAM[team], 0.5)
    for o in objs:
        if o.type == 'MESH' and o.name.split('.')[0] in ('team_cloth', 'team_paint'):
            o.data.materials.clear(); o.data.materials.append(m)
    muz = [o for o in objs if o.name.startswith('muzzle')][0]
    return root, muz
TW = {}
for (x, z, t, key) in ((3.5, 25.5, 0, 'myL'), (14.5, 25.5, 0, 'myR'), (3.5, 6.5, 1, 'enL'), (14.5, 6.5, 1, 'enR')):
    TW[key] = tower(x, z, t)
# the king towers: the rig tower scaled up
for (z, t, key) in ((29.5, 0, 'myK'), (2.5, 1, 'enK')):
    TW[key] = tower(9, z, t); TW[key][0].scale = (1.3, 1.3, 1.15)
for x in (3.5, 14.5):
    root, objs, _ = import_glb('bridge.glb'); root.location = P(x, 16, 0.0)

# ---------------------------------------------------------------- units
def unit(fn, h):
    root, objs, acts = import_glb(fn)
    for o in objs:
        if o.name.startswith('Icosphere'): o.hide_render = True; o.hide_viewport = True
    arm = [o for o in objs if o.type == 'ARMATURE'][0]
    clips = {a.name.split('_')[0]: a for a in acts}
    for a in acts: a.use_fake_user = True
    root.scale = (h / 1.68,) * 3
    arm.animation_data_create(); arm.animation_data.action = None
    return {'root': root, 'arm': arm, 'clips': clips, 'tracks': []}

def clip(u, name, f0, f1, speed=1.0):
    """Play clip `name` from frame f0 to f1 (looped / held), on its own NLA track so strips never collide."""
    a = u['clips'][name]; a0, a1 = a.frame_range
    tr = u['arm'].animation_data.nla_tracks.new(); tr.name = f'{name}_{f0}'
    s = tr.strips.new(f'{name}_{f0}', int(f0), a); s.action_frame_start = a0; s.action_frame_end = a1
    s.scale = 1.0 / speed; s.repeat = max(0.01, (f1 - f0) / ((a1 - a0) / speed))
    s.extrapolation = 'NOTHING'; s.blend_type = 'REPLACE'
    s.use_auto_blend = False; s.blend_in = s.blend_out = 0
    u['tracks'].append(tr)

def show(objs_root, f_on, f_off):
    """Visible from f_on to f_off (inclusive) in renders, by keyed scale on the root (0 when hidden)."""
    r = objs_root; s = r.scale.copy()
    for f, v in ((1, 0), (f_on - 1, 0), (f_on, 1), (f_off, 1), (f_off + 1, 0)):
        if f < 1: continue
        r.scale = s * (v if v else 0.0001); r.keyframe_insert('scale', frame=f)
    for fc in r.animation_data.action.fcurves:
        if fc.data_path == 'scale':
            for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
    r.scale = s

def face(dx, dz):  # model forward is Blender -Y = field +z
    return math.atan2(dx, dz)

# ---------------------------------------------------------------- the timeline (frames at 30 fps)
# a tiny deterministic "sim": paths, hits and HP for both segments; HP is drawn by overlay.py
track = {}          # name -> {frame: (x, z)} root positions
ovl = {'hp': {}, 'shots': [], 'events': []}
def lerp(a, b, t): return a + (b - a) * t

def walk_path(pts, f0, speed):
    """pts: [(x,z),...]; returns {frame: (x, z, heading)} from f0 until the end of the path, at `speed` tiles/s"""
    out = {}; f = f0; segs = list(zip(pts, pts[1:])); per = speed / FPS
    pos = Vector((pts[0][0], pts[0][1]))
    for a, b in segs:
        A_, B_ = Vector(a), Vector(b); d = (B_ - A_).length; n = max(1, int(round(d / per)))
        hd = face(B_.x - A_.x, B_.y - A_.y)
        for i in range(n):
            p = A_.lerp(B_, i / n); out[f] = (p.x, p.y, hd); f += 1
    out[f] = (pts[-1][0], pts[-1][1], out[f - 1][2]); return out, f

def key_path(u, path, z_off=0.0):
    r = u['root']
    for f, (x, z, hd) in sorted(path.items()):
        r.location = P(x, z, z_off); r.keyframe_insert('location', frame=f)
        r.rotation_euler = (0, 0, hd); r.keyframe_insert('rotation_euler', frame=f)

def drop(u, x, z, f, hd=0.0):
    """The deploy: falls in from above over 6 frames."""
    r = u['root']
    for ff, y in ((f - 6, 3.0), (f, 0.0)):
        r.location = P(x, z, y); r.keyframe_insert('location', frame=ff)
        r.rotation_euler = (0, 0, hd); r.keyframe_insert('rotation_euler', frame=ff)
    ovl['events'].append({'f': f, 'kind': 'drop', 'x': x, 'z': z})

def hold(u, x, z, hd, f0, f1):
    r = u['root']
    for ff in (f0, f1):
        r.location = P(x, z); r.keyframe_insert('location', frame=ff); r.rotation_euler = (0, 0, hd); r.keyframe_insert('rotation_euler', frame=ff)

# --- NOOB: the whale crosses, a LMAO! is dropped in its way, it walks past and smashes the tower
W1 = unit('whale.glb', 3.4)
drop(W1, 3.5, 10.5, 24); clip(W1, 'ready', 17, 61)
path1, arr1 = walk_path([(3.5, 10.5), (3.5, 22.4)], 61, 2.1)
key_path(W1, path1); clip(W1, 'walk', 61, arr1, 1.4)
HIT1 = []
f = arr1
while f < 362:
    clip(W1, 'attack1', f, f + 34, 1.0); clip(W1, 'ready', f + 34, f + 42); HIT1.append(f + 21); f += 42
show(W1['root'], 18, 362)
LM = unit('lmao.glb', 2.0)
lmx, lmz = 3.5, 19.6
drop(LM, lmx, lmz, 112, face(0, -1)); clip(LM, 'ready', 105, 120)
# LMAO! swings at the whale while it comes; the whale (buildings only) shoves it aside and keeps going
f_shove = min(f for f, (x, z, h) in path1.items() if z > lmz - 1.9)
hold(LM, lmx, lmz, face(0, -1), 112, f_shove)
for ff in range(f_shove, f_shove + 12):
    t = (ff - f_shove) / 11; x = lmx - 1.35 * (1 - (1 - t) ** 2)
    LM['root'].location = P(x, lmz + 0.3 * t); LM['root'].keyframe_insert('location', frame=ff)
lm_end = (lmx - 1.35, lmz + 0.3)
for ff in range(f_shove + 12, 362, 3):     # keep turning to face the whale and swinging
    wx, wz, _ = path1.get(ff, path1[max(path1)])
    LM['root'].location = P(*lm_end); LM['root'].rotation_euler = (0, 0, face(wx - lm_end[0], wz - lm_end[1]))
    LM['root'].keyframe_insert('location', frame=ff); LM['root'].keyframe_insert('rotation_euler', frame=ff)
f = 120
while f < 362:
    if f_shove <= f < f_shove + 14: clip(LM, 'hit', f, f + 14); f += 14; continue
    clip(LM, 'attack1', f, f + 42); f += 42
show(LM['root'], 106, 362)

# --- PRO: the whale crosses again; LASER EYES in the middle pulls it, both towers and the laser shred it, USELESS finishes
W2 = unit('whale.glb', 3.4)
drop(W2, 3.5, 10.5, 372); clip(W2, 'ready', 365, 392)
IDOL = (9.0, 21.6)
p_a, f_a = walk_path([(3.5, 10.5), (3.5, 16.6)], 392, 2.1)
d = Vector((IDOL[0] - 3.5, IDOL[1] - 16.6)); stop = Vector((3.5, 16.6)) + d.normalized() * (d.length - 2.1)
p_b, arr2 = walk_path([(3.5, 16.6), (stop.x, stop.y)], f_a, 2.1)
path2 = {**p_a, **p_b}; key_path(W2, path2); clip(W2, 'walk', 392, arr2, 1.4)
HIT2 = []; f = arr2; DIE = 612
while f + 34 < DIE:
    clip(W2, 'attack1', f, f + 34); clip(W2, 'ready', f + 34, f + 42); HIT2.append(f + 21); f += 42
clip(W2, 'ready', f, DIE)
clip(W2, 'die', DIE, DIE + 70, 1.1)
show(W2['root'], 366, 700)
# shrink away after the die clip
r = W2['root']; s0 = r.scale.copy()
for ff, v in ((DIE + 62, 1.0), (DIE + 78, 0.0001)):
    r.scale = s0 * v; r.keyframe_insert('scale', frame=ff)

# LASER EYES: our own build (the game draws it procedurally): a gold pedestal and a PEPE-green idol with laser eyes
MG = mat('gold', srgb('#f2c14e'), 0.3, metal=0.9); MGR = mat('idol', srgb('#5fbf3a'), 0.5)
MEYE = mat('eye', (1, 0.05, 0.02), 0.3, emit=(1, 0.05, 0.02), estr=25)
idol = bpy.data.objects.new('lasereyes_root', None); sc.collection.objects.link(idol); idol.location = P(*IDOL); idol.scale = (1.45,) * 3
def child(o): o.parent = idol; return o
bpy.ops.mesh.primitive_cylinder_add(radius=0.85, depth=0.5, location=(0, 0, 0.25)); child(bpy.context.object).data.materials.append(MG)
bpy.ops.mesh.primitive_cylinder_add(radius=0.6, depth=0.5, location=(0, 0, 0.75)); child(bpy.context.object).data.materials.append(MG)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.62, location=(0, 0, 1.45)); hd = child(bpy.context.object); hd.scale = (1, 0.9, 0.85); hd.data.materials.append(MGR)
bpy.ops.object.shade_smooth()
for ex in (-0.24, 0.24):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(ex, -0.52, 1.55)); child(bpy.context.object).data.materials.append(MEYE)
eye_light = bpy.data.lights.new('eyeglow', 'POINT'); eye_light.energy = 60; eye_light.color = (1, 0.1, 0.05)
el = bpy.data.objects.new('eyeglow', eye_light); sc.collection.objects.link(el); el.parent = idol; el.location = (0, -0.8, 1.6)
F_IDOL = 438
for ff, y in ((F_IDOL - 6, 3.0), (F_IDOL, 0.0)):
    idol.location = P(*IDOL, y); idol.keyframe_insert('location', frame=ff)
ovl['events'].append({'f': F_IDOL, 'kind': 'drop', 'x': IDOL[0], 'z': IDOL[1]})
show(idol, F_IDOL - 6, 720)
# the idol turns to track the whale once it's in reach
for ff in range(F_IDOL, 721, 2):
    wx, wz, _ = path2.get(ff, path2[max(path2)]) if ff < DIE + 60 else (3.5, 16.6, 0)
    idol.rotation_euler = (0, 0, face(wx - IDOL[0], wz - IDOL[1])); idol.keyframe_insert('rotation_euler', frame=ff)

# USELESS: four gold coins dropped on the whale as it reaches the idol
US = []
F_US = arr2 + 6
for i, (ox, oz) in enumerate([(-0.9, -0.9), (0.9, -0.9), (-1.0, 0.8), (0.95, 0.85)]):
    u = unit('useless.glb', 1.45); wx, wz = stop.x, stop.y
    ux, uz = wx + ox * 1.6, wz + oz * 1.6
    drop(u, ux, uz, F_US + i * 2, face(wx - ux, wz - uz)) if i == 0 else None
    r = u['root']
    for ff, y in ((F_US + i * 2 - 6, 3.0), (F_US + i * 2, 0.0)):
        r.location = P(ux, uz, y); r.keyframe_insert('location', frame=ff)
        r.rotation_euler = (0, 0, face(wx - ux, wz - uz)); r.keyframe_insert('rotation_euler', frame=ff)
    # step in to melee range
    tx, tz = wx + ox * 1.15, wz + oz * 1.15
    for ff, (x, z) in ((F_US + 8 + i * 2, (ux, uz)), (F_US + 22 + i * 2, (tx, tz))):
        r.location = P(x, z); r.keyframe_insert('location', frame=ff)
    clip(u, 'ready', F_US + i * 2, F_US + 8 + i * 2); clip(u, 'run', F_US + 8 + i * 2, F_US + 22 + i * 2)
    f = F_US + 22 + i * 2
    while f < DIE + 4: clip(u, 'attack' + str(1 + (i + f // 25) % 3), f, f + 25); f += 25
    clip(u, 'ready', f, DIE + 10 + i * 3); clip(u, 'win', DIE + 10 + i * 3, 720)
    show(r, F_US - 8, 720); US.append(u)


# ---------------------------------------------------------------- tower cannons, laser, HP
MBALL = mat('ball', srgb('#2b2b2b'), 0.4, metal=0.5)
MFLASH = mat('flash', (1, 0.7, 0.2), 0.5, emit=(1, 0.55, 0.1), estr=30)
def tower_pos(key):
    root, muz = TW[key]; return Vector(root.location) + Vector((0, 0, 4.0))
balls = []
def shot(key, f0, target_path, speed=22.0):
    """a cannonball from tower `key` fired at frame f0 at whatever follows target_path; returns the impact frame"""
    src = tower_pos(key)
    tx, tz, _ = target_path.get(f0, target_path[max(target_path)]); tgt = P(tx, tz, 1.4)
    n = max(3, int((tgt - src).length / speed * FPS))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=src, segments=12, ring_count=8); b = bpy.context.object
    b.data.materials.append(MBALL)
    for i in range(n + 1):
        t = i / n; ff = f0 + i
        tx, tz, _ = target_path.get(ff, target_path[max(target_path)]); tgt = P(tx, tz, 1.4)
        p = src.lerp(tgt, t); p.z += math.sin(t * math.pi) * 1.2
        b.location = p; b.keyframe_insert('location', frame=ff)
    show(b, f0, f0 + n); ovl['shots'].append({'from': key, 'f0': f0, 'f1': f0 + n})
    return f0 + n
def wpos(path, f): return path.get(f, path[max(path)] if f > max(path) else path[min(path)])
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

TPOS = {'myL': (3.5, 25.5), 'myR': (14.5, 25.5), 'myK': (9, 29.5)}
dmg1 = []; dmg2 = []
for key in ('myL', 'myR', 'myK'):
    rng = 8.6 if key != 'myK' else 8.0
    for (path, f0, f1, out) in ((path1, 61, 362, dmg1), (path2, 392, DIE, dmg2)):
        nxt = None
        for f in range(f0, f1):
            x, z, _ = wpos(path, f)
            if dist((x, z), TPOS[key]) <= rng and (nxt is None or f >= nxt):
                imp = shot(key, f, path); out.append((imp, 88)); nxt = f + 24
# the laser: a red beam from the idol's eyes to the whale every 9 frames while it's in reach
MLAS = mat('laser', (1, 0.1, 0.05), 0.3, emit=(1, 0.08, 0.03), estr=40)
bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=1.0, vertices=8); beam = bpy.context.object; beam.data.materials.append(MLAS)
beam.scale = (0.0001,) * 3; beam.keyframe_insert('scale', frame=1)
for f in range(F_IDOL + 4, DIE, 9):
    x, z, _ = wpos(path2, f)
    if dist((x, z), IDOL) > 6.0: continue
    a = P(*IDOL, 2.25); b = P(x, z, 1.9); mid = (a + b) / 2; L = (b - a).length
    beam.location = mid; beam.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    for ff, s in ((f - 1, 0.0001), (f, 1), (f + 4, 1), (f + 5, 0.0001)):
        beam.scale = (s, s, L if s > 0.01 else 0.0001); beam.keyframe_insert('scale', frame=ff)
        beam.keyframe_insert('location', frame=ff); beam.keyframe_insert('rotation_euler', frame=ff)
    dmg2.append((f, 60))
for fc in beam.animation_data.action.fcurves:
    for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
for i, u in enumerate(US):
    f = F_US + 22 + i * 2
    while f < DIE: dmg2.append((f + 10, 56)); f += 25
for f in range(f_shove - 40, 362, 42): dmg1.append((f + 23, 40))   # LMAO! barely scratches it

# HP curves for the overlay: the whale in the noob run ends at about 75%, the pro whale reaches 0 exactly at DIE
def hp_curve(dmgs, total, f_end=None):
    dmgs = sorted(d for d in dmgs if f_end is None or d[0] <= f_end)
    s = sum(v for _, v in dmgs) or 1; k = (total / s) if f_end else 1.0
    out = {}; hp = 1.0; i = 0
    for f in range(1, LAST + 1):
        while i < len(dmgs) and dmgs[i][0] <= f: hp -= dmgs[i][1] * k / (total if f_end else 4700); i += 1
        out[f] = max(0.0, hp)
    return out
whp1 = hp_curve(dmg1, 4700); whp2 = hp_curve(dmg2, 1.0 * 4700, DIE)
whp2 = {f: (0.0 if f >= DIE else v) for f, v in whp2.items()}
thp1 = {}; hp = 1.0
for f in range(1, LAST + 1):
    if f in HIT1: hp -= 515 / 2600
    thp1[f] = hp
ihp = {}; hp = 1.0
for f in range(1, LAST + 1):
    if f in HIT2: hp -= 0.28
    ihp[f] = hp

# tower hits: a shake and a flash light on each whale slam
for key, hits, path in (('myL', HIT1, path1),):
    root = TW[key][0]; base = root.location.copy()
    for f in hits:
        for ff, dx in ((f - 1, 0), (f, 0.12), (f + 2, -0.1), (f + 4, 0.05), (f + 6, 0)):
            root.location = base + Vector((dx, 0, 0)); root.keyframe_insert('location', frame=ff)

# ---------------------------------------------------------------- light, world, camera
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.2; sun.angle = math.radians(3); sun.color = (1, 0.96, 0.9)
so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(38), math.radians(-18), math.radians(25))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (*srgb('#8fb6ff'), 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9

cd = bpy.data.cameras.new('cam'); cd.lens = 38; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
TILT = math.radians(34)
def cam_at(f, cx, cz, height):
    # look at field point (cx, cz) from above, tilted towards the enemy so the units read as 3D
    tgt = P(cx, cz); pos = tgt + Vector((0, -math.sin(TILT) * height, math.cos(TILT) * height))
    cam.location = pos; cam.rotation_euler = (TILT, 0, 0)
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
# intro: wide over the whole half, settle on the left lane; pro: the same lane, a touch wider to see the middle
for f, cx, cz, h in ((1, 9.0, 19.0, 34), (60, 5.0, 19.6, 21), (362, 5.0, 19.8, 20), (363, 6.0, 19.0, 26), (392, 5.8, 19.6, 22),
                     (450, 6.6, 20.4, 22), (720, 6.8, 20.6, 20.5)):
    cam_at(f, cx, cz, h)
for fc in cam.animation_data.action.fcurves:
    for k in fc.keyframe_points:
        k.interpolation = 'BEZIER'
        if k.co[0] in (362, 363): k.interpolation = 'CONSTANT'

# ---------------------------------------------------------------- overlay data (2D projections for the HP bars)
from bpy_extras.object_utils import world_to_camera_view
rows = {}
for f in range(1, LAST + 1):
    sc.frame_set(f); R = {}
    def scr(v):
        c = world_to_camera_view(sc, cam, v); return [round(c.x, 4), round(1 - c.y, 4), round(c.z, 2)]
    if 18 <= f <= 362:
        x, z, _ = wpos(path1, max(f, 24)); R['whale'] = scr(P(x, z, 4.0)) + [round(whp1[f], 3)]
    if 366 <= f < DIE:
        x, z, _ = wpos(path2, max(f, 372)); R['whale'] = scr(P(x, z, 4.0)) + [round(whp2[f], 3)]
    R['myL'] = scr(P(3.5, 25.5, 5.3)) + [round(thp1[f] if f <= 362 else 1.0, 3)]
    R['myR'] = scr(P(14.5, 25.5, 5.3)) + [1.0]
    R['myK'] = scr(P(9, 29.5, 6.3)) + [1.0]
    if F_IDOL <= f <= 720: R['idol'] = scr(P(*IDOL, 3.3)) + [round(ihp[f], 3)]
    rows[f] = R
ovl['frames'] = rows
ovl['marks'] = {'title': [1, 60], 'noob': [61, 362], 'pro': [363, 720], 'x_at': 268, 'check_at': DIE + 12,
                'drop_lmao': 112, 'drop_idol': F_IDOL, 'drop_useless': F_US, 'whale_die': DIE, 'tower_hits': HIT1,
                'idol_hits': HIT2, 'endcard': [721, 810]}
if OVL: json.dump(ovl, open(OVL, 'w'))
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT))
print('BUILT', OUT, 'frames', LAST)
