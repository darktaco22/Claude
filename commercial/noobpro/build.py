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

def box(name, loc, size, m, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def import_glb(fn):
    before = set(bpy.data.objects); acts_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.join(M, fn))
    new = [o for o in bpy.data.objects if o not in before]; acts = [a for a in bpy.data.actions if a not in acts_before]
    root = bpy.data.objects.new(fn.split('.')[0] + '_root', None); sc.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    return root, new, acts

# ---------------------------------------------------------------- the arena: the live game's own MOM'S BASEMENT, exported
# from its three.js scene (court, canal, bridges, towers, fences, kit, props, backdrop) by export_arena.js
_, ARENA, _ = import_glb('arena_basement.glb')
UNITS = set(json.load(open(os.path.join(M, 'units.json'))))
for o in list(ARENA):   # the towers' crew comes in without its skeleton: put back below, animated
    if o.type == 'MESH' and any(m and m.name.split('.')[0] in UNITS for m in o.data.materials): bpy.data.objects.remove(o)
ARENA = [o for o in bpy.data.objects if o.name in {x.name for x in bpy.data.objects}]
# the canal: the game draws it with its own shader (glowing green energy-drink goo): rebuilt here as a node material
def goo_mat():
    m = bpy.data.materials.new('goo'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.2
    tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 1.6
    L.new(tc.outputs['Object'], vo.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); E_ = ramp.color_ramp.elements
    E_[0].position = 0.0; E_[0].color = (*srgb('#d8ff9a'), 1); E_[1].position = 0.09; E_[1].color = (*srgb('#1fd23c'), 1)
    e = E_.new(0.35); e.color = (*srgb('#0a7a1c'), 1)
    L.new(vo.outputs['Distance'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    L.new(ramp.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.6
    return m
GOO = goo_mat()
# the room around the court is the game's procedural "world" (src/render/world.js): coloured per vertex in its own shader.
# Here: the same vertex colours through a plain material; the canal's flat sheet gets the goo
def vcol_mat(layer):
    m = bpy.data.materials.new('world_' + layer); m.use_nodes = True; N = m.node_tree.nodes
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.85
    vc = N.new('ShaderNodeVertexColor'); vc.layer_name = layer; m.node_tree.links.new(vc.outputs['Color'], b.inputs['Base Color'])
    return m
VCM = {}
for o in ARENA:
    if o.type != 'MESH': continue
    for i, m in enumerate(o.data.materials):
        if not (m and m.name.startswith('SHADER_')): continue
        d = o.dimensions; nv = len(o.data.vertices)
        if nv <= 8 and max(d) > 15: o.data.materials[i] = GOO                 # the liquid sheet under the court
        elif max(d) < 2.0: o.hide_render = True                               # sprite cards (sparkles, labels)
        elif o.data.color_attributes:
            L = o.data.color_attributes[0].name; o.data.materials[i] = VCM.setdefault(L, vcol_mat(L))
        else: o.hide_render = True
for o in ARENA:   # the game's glow strips and bulbs: brighter emission so Cycles reads them as lit
    if o.type == 'MESH':
        for m in o.data.materials:
            if m and m.use_nodes and m.name.startswith('glow'):
                bs = m.node_tree.nodes.get('Principled BSDF')
                if bs: bs.inputs['Emission Strength'].default_value = max(4.0, bs.inputs['Emission Strength'].default_value)

# the towers (in the export) for the hit shake: every object whose origin sits on a tower's footprint
TPOS = {'myL': (3.5, 25.5), 'myR': (14.5, 25.5), 'myK': (9, 29.5), 'enL': (3.5, 6.5), 'enR': (14.5, 6.5), 'enK': (9, 2.5)}
TW = {}
for key, (x, z) in TPOS.items():
    e = bpy.data.objects.new('tower_' + key, None); sc.collection.objects.link(e); e.location = P(x, z); TW[key] = e
for o in ARENA:
    if o.type == 'MESH' and o.parent and o.parent.name.startswith('arena_basement_root'):
        t = o.matrix_world.translation; hit = None
        for key, (x, z) in TPOS.items():
            if abs(t.x - x) < 1.2 and abs(-t.y - z) < 1.2 and any(m and m.name.startswith(('tower_rig', 'battlestation')) for m in o.data.materials): hit = key
        if hit:
            mw = o.matrix_world.copy(); o.parent = TW[hit]; o.matrix_world = mw
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
W1 = unit('whale.glb', 4.37)
drop(W1, 3.5, 10.5, 24); clip(W1, 'ready', 17, 61)
path1, arr1 = walk_path([(3.5, 10.5), (3.5, 22.4)], 61, 2.1)
key_path(W1, path1); clip(W1, 'walk', 61, arr1, 1.4)
HIT1 = []
f = arr1
while f < 362:
    clip(W1, 'attack1', f, f + 34, 1.0); clip(W1, 'ready', f + 34, f + 42); HIT1.append(f + 21); f += 42
show(W1['root'], 18, 362)
LM = unit('lmao.glb', 2.77)
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
W2 = unit('whale.glb', 4.37)
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
MSTONE = mat('stone', srgb('#8d8879'), 0.95); MDARK = mat('stonedark', srgb('#5c584d'), 1.0)
MGLOW = mat('teamglow', tuple(c * 0.5 for c in srgb('#7CFF6B')), 0.55, emit=srgb('#7CFF6B'), estr=1.8 * 3)
MEYE = mat('eye', srgb('#400808'), 0.4, emit=srgb('#ff2a18'), estr=1.2 * 12)
idol = bpy.data.objects.new('lasereyes_root', None); sc.collection.objects.link(idol); idol.location = P(*IDOL); idol.scale = (1.35,) * 3
head = bpy.data.objects.new('lasereyes_head', None); sc.collection.objects.link(head); head.parent = idol; head.location = (0, 0, 1.1)
def gbox(w, h, d, x, y, z, m, par):   # three's box(w, h, d, x, y, z) in the group's frame (y up, z toward the target)
    return box('le', (x, -z, y), (w, d, h), m, par)
gbox(1.35, 0.4, 1.35, 0, 0.2, 0, MDARK, idol); gbox(1, 0.7, 0.95, 0, 0.75, 0, MSTONE, idol); gbox(1.02, 0.08, 0.97, 0, 0.55, 0, MGLOW, idol)
gbox(1, 0.78, 0.9, 0, 0.39, 0, MSTONE, head); gbox(0.24, 0.26, 0.74, 0, 0.88, -0.04, MDARK, head); gbox(1.1, 0.16, 0.22, 0, 0.6, 0.42, MDARK, head)
gbox(0.18, 0.3, 0.16, 0, 0.26, 0.48, MDARK, head)
for sx in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(sx * 0.22, -0.46, 0.42), segments=10, ring_count=8)
    e = bpy.context.object; e.parent = head; e.data.materials.append(MEYE)
eye_light = bpy.data.lights.new('eyeglow', 'POINT'); eye_light.energy = 40; eye_light.color = (1, 0.15, 0.08)
el = bpy.data.objects.new('eyeglow', eye_light); sc.collection.objects.link(el); el.parent = head; el.location = (0, -0.8, 0.42)
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
    u = unit('useless.glb', 1.79); wx, wz = stop.x, stop.y
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


# ---------------------------------------------------------------- tower crew (the game seats them on every tower)
for key in ('myL', 'myR', 'enL', 'enR'):
    x, z = TPOS[key]; u = unit('chillguy.glb', 1.87); u['root'].location = P(x, z, 3.86)
    u['root'].rotation_euler = (0, 0, math.pi if key.startswith('my') else 0.0); clip(u, 'idle', 1, LAST + 1)
for key in ('myK', 'enK'):
    x, z = TPOS[key]; u = unit('neet.glb', 2.2); u['root'].location = P(x, z + (0.55 if key == 'myK' else -0.55), 3.75)
    u['root'].rotation_euler = (0, 0, math.pi if key == 'myK' else 0.0); clip(u, 'sit', 1, LAST + 1)

# ---------------------------------------------------------------- tower cannons, laser, HP
MBALL = mat('ball', srgb('#2b2b2b'), 0.4, metal=0.5)
MFLASH = mat('flash', (1, 0.7, 0.2), 0.5, emit=(1, 0.55, 0.1), estr=30)
def tower_pos(key):
    return Vector(TW[key].location) + Vector((0, 0, 4.9))
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
    a = P(*IDOL, 2.05); b = P(x, z, 2.4); mid = (a + b) / 2; L = (b - a).length
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
    root = TW[key]; base = root.location.copy()
    for f in hits:
        for ff, dx in ((f - 1, 0), (f, 0.12), (f + 2, -0.1), (f + 4, 0.05), (f + 6, 0)):
            root.location = base + Vector((dx, 0, 0)); root.keyframe_insert('location', frame=ff)

# ---------------------------------------------------------------- light, world, camera
def sun_from(name, col, energy, frm):   # three DirectionalLight at position frm aiming at the origin
    L = bpy.data.lights.new(name, 'SUN'); L.energy = energy; L.color = srgb(col); L.angle = math.radians(2)
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o)
    d = Vector((frm[0], -frm[2], frm[1])); o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); return o
sun_from('key', '#ffcf8a', 2.4 * 1.6, (-6, 24, 26)); sun_from('rim', '#7fa0ff', 0.6 * 1.6, (16, 14, -18))
gl = bpy.data.lights.new('canal', 'POINT'); gl.energy = 900; gl.color = srgb('#5dff7a'); gl.shadow_soft_size = 2
g_o = bpy.data.objects.new('canal', gl); sc.collection.objects.link(g_o); g_o.location = P(9, 16, 1.2)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; nt = w.node_tree
# the hemisphere light: warm from above, dark brown from below; the camera sees the game's background colour
bg = nt.nodes['Background']; geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (*srgb('#2a1c14'), 1); mix.inputs['B'].default_value = (*srgb('#ffd9a8'), 1)
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
nt.links.new(geo.outputs['Incoming'], sep.inputs['Vector']); nt.links.new(sep.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], mix.inputs['Factor'])
nt.links.new(mix.outputs['Result'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.85
lp = nt.nodes.new('ShaderNodeLightPath'); bg2 = nt.nodes.new('ShaderNodeBackground'); bg2.inputs['Color'].default_value = (*srgb('#1b1410'), 1)
ms = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes['World Output']
nt.links.new(lp.outputs['Is Camera Ray'], ms.inputs['Fac']); nt.links.new(bg.outputs['Background'], ms.inputs[1]); nt.links.new(bg2.outputs['Background'], ms.inputs[2])
nt.links.new(ms.outputs['Shader'], out.inputs['Surface'])

# the game's battle camera: 36 degree vertical field of view, pitched 60 degrees, framing the court for a 9:16 phone
cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24; cd.lens = 12 / math.tan(math.radians(18))
cd.clip_start = 0.5; cd.clip_end = 300
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
PITCH = math.radians(60)
def cam_at(f, cx, cz, d):
    tgt = P(cx, cz); pos = tgt + Vector((0, -math.cos(PITCH) * d, math.sin(PITCH) * d))
    cam.location = pos; cam.rotation_euler = (math.radians(90) - PITCH, 0, 0)
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
GAME = (9.0, 19.63, 67.37)   # the exact framing the live game uses at 720x1280
for f, cx, cz, d in ((1, *GAME), (40, *GAME), (110, 6.2, 20.6, 46), (362, 6.0, 21.0, 43), (363, *GAME), (400, *GAME),
                     (470, 7.4, 20.8, 47), (720, 7.6, 21.0, 44)):
    cam_at(f, cx, cz, d)
for fc in cam.animation_data.action.fcurves:
    for k in fc.keyframe_points:
        k.interpolation = 'BEZIER'
        if k.co[0] in (362, 363): k.interpolation = 'CONSTANT'

# ---------------------------------------------------------------- overlay data (2D projections for the HP bars)
from bpy_extras.object_utils import world_to_camera_view
rows = {}
def visH(h): return 2.15 * h ** 0.85
# what the game's overlay (src/render/overlay.js) draws: tower plates, unit bars with level badges, deploy clocks
TOWERS = [('myL', 3.5, 25.5, 0, 'rig'), ('myR', 14.5, 25.5, 0, 'rig'), ('myK', 9, 29.5, 0, 'hq'),
          ('enL', 3.5, 6.5, 1, 'rig'), ('enR', 14.5, 6.5, 1, 'rig'), ('enK', 9, 2.5, 1, 'hq')]
TDEF = {'rig': (2600, 4.2, 1.45), 'hq': (4400, 5.0, 1.95)}
OVU = [  # name, root, team, card h, max hp, deploy frame, last frame, hp curve
    ('whale1', W1['root'], 1, 2.3, 4700, 24, 362, whp1), ('lmao', LM['root'], 0, 1.35, 640, 112, 362, None),
    ('whale2', W2['root'], 1, 2.3, 4700, 372, DIE - 1, whp2)] + \
    [(f'us{i}', u['root'], 0, 0.8, 135, F_US + i * 2, 720, None) for i, u in enumerate(US)]
for f in range(1, LAST + 1):
    sc.frame_set(f); R = {'t': [], 'u': []}
    def scr(v):
        c = world_to_camera_view(sc, cam, v); return [round(c.x, 4), round(1 - c.y, 4)]
    for key, x, z, team, typ in TOWERS:
        mx, h, r = TDEF[typ]; hp = mx * (thp1[f] if (key == 'myL' and f <= 362) else 1.0)
        pt = P(x, z + r * 1.2, 0) if team == 0 else P(x, z, h * 1.2 + (2.2 if typ == 'hq' else 2.3))
        R['t'].append(scr(pt) + [team, typ, round(hp), mx])
    for name, root, team, h, mx, fd, fe, curve in OVU:
        if not (fd <= f <= fe): continue
        loc = root.matrix_world.translation; H = visH(h) * 1.05
        hp = (curve[f] if curve else 1.0) * mx
        R['u'].append(scr(Vector((loc.x, loc.y, loc.z + H + 0.2))) + [team, round(hp), mx, round(min(1.0, (f - fd) / 30), 3), f - fd])
    if F_IDOL <= f <= 720:
        R['b'] = scr(P(*IDOL, 1.6 * 1.3 + 0.6)) + [0, round(ihp[f], 3)]
    rows[f] = R
ovl['frames'] = rows
ovl['marks'] = {'title': [1, 60], 'noob': [61, 362], 'pro': [363, 720], 'x_at': 268, 'check_at': DIE + 12,
                'drop_lmao': 112, 'drop_idol': F_IDOL, 'drop_useless': F_US, 'whale_die': DIE, 'tower_hits': HIT1,
                'idol_hits': HIT2, 'endcard': [721, 810]}
if OVL: json.dump(ovl, open(OVL, 'w'))
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT))
print('BUILT', OUT, 'frames', LAST)
