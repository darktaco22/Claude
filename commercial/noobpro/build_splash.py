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

# ================= TIP 2: SPLASH EATS SWARMS =================
# the enemy drops two USELESS (8 gold coins) down the left lane.
# NOOB answers with CHILL GUY (one coin per swing): the swarm eats him and reaches the tower.
# PRO answers with LMAO! behind the tower: one laugh's splash wipes the pack, the second the rest; then LMAO! counter-pushes.
COIN_H = 1.79; NC = 8
GRID = [(-0.45, 0), (0.45, 0), (-0.45, -0.9), (0.45, -0.9), (-0.45, -1.8), (0.45, -1.8), (-0.45, -2.7), (0.45, -2.7)]
SPD = 2.6 / FPS
def line(p0, p1, f0):
    """frames from f0 walking p0 -> p1 at SPD; returns ({f: (x, z, hd)}, arrival frame)"""
    A_, B_ = Vector(p0), Vector(p1); n = max(1, int(round((B_ - A_).length / SPD))); hd = face(B_.x - A_.x, B_.y - A_.y)
    return {f0 + i: (*A_.lerp(B_, i / n), hd) for i in range(n + 1)}, f0 + n
def hold_at(p, hd, f0, f1): return {f: (p[0], p[1], hd) for f in range(f0, f1 + 1)}
COINS = {}   # name -> {'u', 'path', 'dies', 'team'}
def coin_unit(name, team=1):
    u = unit('useless.glb', COIN_H); COINS[name] = {'u': u, 'path': {}, 'dies': None, 'dmg': []}; return COINS[name]
def finish_coin(c, f_show, f_end):
    u = c['u']; P_ = c['path']; key_path(u, P_)
    show(u['root'], f_show, min(f_end, (c['dies'] + 40) if c['dies'] else f_end))

# ---------------- NOOB (61-362)
CG_AT = (3.5, 18.8); F_CG = 100
CG = unit('chillguy.glb', 2.15 * 1.4 ** 0.85)
drop(CG, *CG_AT, F_CG, face(0, -1)); clip(CG, 'ready', F_CG - 7, F_CG + 30)
RING = [(-1.0, -0.55), (1.0, -0.55), (-0.25, -1.1), (0.75, -1.05), (-1.15, 0.35), (1.15, 0.35), (-0.6, 0.95), (0.6, 0.95)]
KILL_N = {0: 158, 2: 194, 1: 230}          # Chill Guy's three kills, one per 1.2 s swing
F_CG_DIE = 236
TOWER_SPOTS = [(1.3, 24.0), (5.7, 24.0), (1.25, 25.2), (5.75, 25.2), (1.6, 22.9)]
N_SHOTS = []                               # (frame, coin) tower shots
noob = []
for i, (ox, oz) in enumerate(GRID):
    c = coin_unit(f'n{i}'); u = c['u']; st = (3.5 + ox, 10.5 + oz)
    drop(u, *st, 24 + (i % 2), face(0, 1)); c['path'].update(hold_at(st, face(0, 1), 18, 61))
    clip(u, 'ready', 17, 61)
    tgt = (CG_AT[0] + RING[i][0], CG_AT[1] + RING[i][1])
    p, arr = line(st, tgt, 61 + i // 2 * 3); c['path'].update(p); clip(u, 'run', 61 + i // 2 * 3, arr)
    hd = face(CG_AT[0] - tgt[0], CG_AT[1] - tgt[1])
    if i in KILL_N:
        k = KILL_N[i]; c['path'].update(hold_at(tgt, hd, arr, k + 40)); clip(u, 'attack1', arr, k)
        clip(u, 'die', k, k + 40); c['dies'] = k
    else:
        c['path'].update(hold_at(tgt, hd, arr, F_CG_DIE + 6))
        clip(u, 'attack' + str(1 + i % 3), arr, F_CG_DIE + 6)
        j = [x for x in range(NC) if x not in KILL_N].index(i); spot = TOWER_SPOTS[j]
        p2, arr2 = line(tgt, spot, F_CG_DIE + 6 + j * 3); c['path'].update(p2); clip(u, 'run', F_CG_DIE + 6 + j * 3, arr2)
        hd2 = face(3.5 - spot[0], 25.5 - spot[1]); c['spot_arr'] = arr2
        end = 362
        if j in (0, 1):                     # the tower picks two off (two cannonballs each)
            k = 300 if j == 0 else 342; c['dies'] = k; end = k
            clip(u, 'die', k, k + 40)
        c['path'].update(hold_at(spot, hd2, arr2, min(362, end + 40))); clip(u, 'attack' + str(1 + j % 3), arr2, end)
    finish_coin(c, 18, 362); noob.append(c)
# Chill Guy swings at the coin in front, then goes down under the swarm
f = F_CG + 30
clip(CG, 'ready', f, 150)
for k in (158, 194, 230): clip(CG, 'attack1', k - 22, k + 6)
clip(CG, 'ready', 164, 172); clip(CG, 'ready', 200, 208)
clip(CG, 'die', F_CG_DIE, F_CG_DIE + 70)
show(CG['root'], F_CG - 6, F_CG_DIE + 66)
# Chill Guy turns to face whoever he hits
for k, i in ((150, 0), (186, 2), (222, 1)):
    tx, tz = CG_AT[0] + RING[i][0], CG_AT[1] + RING[i][1]
    CG['root'].location = P(*CG_AT); CG['root'].rotation_euler = (0, 0, face(tx - CG_AT[0], tz - CG_AT[1]))
    CG['root'].keyframe_insert('location', frame=k); CG['root'].keyframe_insert('rotation_euler', frame=k)
cg_hp = {}
for f_ in range(1, LAST + 1):
    alive = sum(1 for c in noob if c['path'].get(f_) and (c['dies'] is None or f_ < c['dies']) and f_ >= 150)
    cg_hp[f_] = 1.0 if f_ < 150 else None
hp = 1.0
for f_ in range(1, LAST + 1):
    if 150 <= f_ < F_CG_DIE: hp -= 1.0 / (F_CG_DIE - 150)
    cg_hp[f_] = max(0.0, hp) if f_ < F_CG_DIE else 0.0
# the tower: 56 a hit from every coin at it, one a second
thp1 = {}; hp = 2600.0
for f_ in range(1, LAST + 1):
    if f_ <= 362:
        for c in noob:
            arr = c.get('spot_arr')
            if arr and f_ >= arr + 10 and (c['dies'] is None or f_ < c['dies']) and (f_ - arr) % 30 == 10: hp -= 56
    thp1[f_] = hp / 2600
HIT1 = [f_ for f_ in range(2, 363) if thp1[f_] < thp1[f_ - 1]]

# ---------------- PRO (363-720)
LM_AT = (5.8, 22.6); F_LM = 404
LM = unit('lmao.glb', 2.15 * 1.35 ** 0.85)
drop(LM, *LM_AT, F_LM, face(-0.6, -1)); clip(LM, 'ready', F_LM - 7, 440)
pro = []
for i, (ox, oz) in enumerate(GRID):
    c = coin_unit(f'p{i}'); u = c['u']; st = (3.5 + ox, 10.5 + oz)
    drop(u, *st, 372 + (i % 2), face(0, 1)); c['path'].update(hold_at(st, face(0, 1), 366, 392)); clip(u, 'ready', 365, 392)
    p, arr = line(st, (3.5 + ox, 21.0 + oz), 392); c['path'].update(p); clip(u, 'run', 392, arr); pro.append(c)
def cpos(c, f_): return c['path'].get(f_) or c['path'][max(k for k in c['path'] if k <= f_)]
# laugh 1: thrown at f457, lands f467 on the pack's middle; every coin within 1.6 goes; laugh 2 cleans up
LAUGHS = []
def laugh(f_throw, f_land, victims):
    xs = [cpos(c, f_land)[0] for c in victims]; zs = [cpos(c, f_land)[1] for c in victims]
    ctr = (sum(xs) / len(xs), sum(zs) / len(zs)); LAUGHS.append((f_throw, f_land, ctr)); return ctr
f1_land = 467
ctr1 = (3.5, cpos(pro[3], f1_land)[1])
hit1 = [c for c in pro if math.hypot(cpos(c, f1_land)[0] - ctr1[0], cpos(c, f1_land)[1] - ctr1[1]) <= 1.6]
rest = [c for c in pro if c not in hit1]
laugh(457, f1_land, hit1)
f2_land = 512
if rest: laugh(502, f2_land, rest)
for c in hit1: c['dies'] = f1_land
for c in rest: c['dies'] = f2_land
for c in pro:
    u = c['u']; k = c['dies']; x, z, hd = cpos(c, k)
    c['path'] = {f_: v for f_, v in c['path'].items() if f_ <= k}; c['path'].update(hold_at((x, z), hd, k, k + 40))
    clip(u, 'die', k, k + 40)
    finish_coin(c, 366, 720)
clip(LM, 'attack1', 440, 482); clip(LM, 'attack2', 485, 520); clip(LM, 'ready', 520, 530)
DIE = f2_land if rest else f1_land
clip(LM, 'emote', 530, 600)
# counter-push: LMAO! walks over the bridge
cp, cp_arr = walk_path([LM_AT, (4.4, 19.0), (3.9, 16.0), (3.6, 11.5)], 604, 1.6)
hold(LM, *LM_AT, face(-0.6, -1), F_LM, 603); key_path(LM, cp); clip(LM, 'walk', 600, 721)
show(LM['root'], F_LM - 6, 720)

# the laughs: a glowing yellow ball on an arc, a splash ring and a flash where it lands
MLAUGH = mat('laugh', srgb('#ffd23a'), 0.3, emit=srgb('#ffd23a'), estr=12)
MRING = mat('splash', srgb('#fff2a0'), 0.3, emit=srgb('#ffe14a'), estr=8)
for (ft, fl, ctr) in LAUGHS:
    src = P(*LM_AT, 2.6); dst = P(*ctr, 0.4)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.38, location=src, segments=16, ring_count=10); ball = bpy.context.object
    ball.data.materials.append(MLAUGH)
    for f_ in range(ft, fl + 1):
        t = (f_ - ft) / (fl - ft); p = src.lerp(dst, t); p.z += math.sin(t * math.pi) * 2.2
        ball.location = p; ball.keyframe_insert('location', frame=f_)
    show(ball, ft, fl)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.09, location=P(*ctr, 0.15)); ring = bpy.context.object
    ring.data.materials.append(MRING)
    for f_, s_ in ((fl - 1, 0.0001), (fl, 0.3), (fl + 6, 1.6), (fl + 10, 1.75), (fl + 11, 0.0001)):
        ring.scale = (s_, s_, 1 if s_ > 0.01 else 0.0001); ring.keyframe_insert('scale', frame=f_)
    fl_l = bpy.data.lights.new('splash', 'POINT'); fl_l.color = srgb('#ffd23a'); fl_l.shadow_soft_size = 1.5
    fo = bpy.data.objects.new('splash', fl_l); sc.collection.objects.link(fo); fo.location = P(*ctr, 1.2)
    for f_, e in ((fl - 1, 0), (fl, 2500), (fl + 4, 1200), (fl + 10, 0)):
        fl_l.energy = e; fl_l.keyframe_insert('energy', frame=f_)
    ovl['events'].append({'f': fl, 'kind': 'splash', 'x': ctr[0], 'z': ctr[1]})

# ---------------------------------------------------------------- tower crew (the game seats them on every tower)
for key in ('myL', 'myR', 'enL', 'enR'):
    x, z = TPOS[key]; u = unit('chillguy.glb', 1.87); u['root'].location = P(x, z, 3.86)
    u['root'].rotation_euler = (0, 0, math.pi if key.startswith('my') else 0.0); clip(u, 'idle', 1, LAST + 1)
for key in ('myK', 'enK'):
    x, z = TPOS[key]; u = unit('neet.glb', 2.2); u['root'].location = P(x, z + (0.55 if key == 'myK' else -0.55), 3.75)
    u['root'].rotation_euler = (0, 0, math.pi if key == 'myK' else 0.0); clip(u, 'sit', 1, LAST + 1)

# ---------------------------------------------------------------- tower cannons
MBALL = mat('ball', srgb('#2b2b2b'), 0.4, metal=0.5)
def tower_pos(key):
    return Vector(TW[key].location) + Vector((0, 0, 4.9))
def shot_at(key, f0, getpos, speed=22.0):
    src = tower_pos(key); x, z = getpos(f0); tgt = P(x, z, 0.8)
    n = max(3, int((tgt - src).length / speed * FPS))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=src, segments=12, ring_count=8); b_ = bpy.context.object
    b_.data.materials.append(MBALL)
    for i in range(n + 1):
        t = i / n; x, z = getpos(f0 + i); tgt = P(x, z, 0.8); p = src.lerp(tgt, t); p.z += math.sin(t * math.pi) * 1.2
        b_.location = p; b_.keyframe_insert('location', frame=f0 + i)
    show(b_, f0, f0 + n); ovl['shots'].append({'from': key, 'f0': f0, 'f1': f0 + n})
# the left tower's cannon on the two coins it kills in the noob run (two shots each)
for c, k in [(c, c['dies']) for c in noob if c['dies'] in (300, 342)]:
    for fs in (k - 34 - 10, k - 10):
        shot_at('myL', fs, lambda f_, c=c: cpos(c, f_)[:2])
# the pro run: the cannon fires on the pack as it crosses, before the laughs land
for fs in (440, 464, 488):
    alive = [c for c in pro if c['dies'] > fs + 10]
    if alive: shot_at('myL', fs, lambda f_, c=alive[0]: cpos(c, f_)[:2])
# tower hits: a shake on each coin hit
root = TW['myL']; base = root.location.copy()
for f_ in HIT1[::2]:
    for ff, dx in ((f_ - 1, 0), (f_, 0.06), (f_ + 2, -0.05), (f_ + 4, 0)):
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
for f, cx, cz, d in ((1, *GAME), (40, *GAME), (100, 5.6, 20.0, 44), (362, 5.4, 21.0, 41), (363, *GAME), (400, *GAME),
                     (450, 5.6, 19.8, 43), (600, 5.6, 19.4, 43), (720, 5.2, 17.6, 45)):
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
OVU = [('chillguy', CG['root'], 0, 1.4, 1380, F_CG, F_CG_DIE - 1, cg_hp), ('lmao', LM['root'], 0, 1.35, 640, F_LM, 720, None)]
for c in noob + pro:
    fd = 24 if c in noob else 372
    OVU.append((c['u']['root'].name, c['u']['root'], 1, 0.8, 135, fd, (c['dies'] - 1) if c['dies'] else (362 if c in noob else 720), None))
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
    rows[f] = R
ovl['frames'] = rows
CUES = [['ui_swoosh', 4, 1.0], ['emote_pop', 8, 1.0], ['emote_pop', 14, 1.0], ['emote_pop', 20, 1.0],
        ['deploy_drop', 24, 0.9], ['bark_useless', 30, 0.8], ['deploy_drop', F_CG, 0.9], ['bark_chillguy', F_CG + 4, 0.8],
        ['card_deny', 285, 1.0], ['ui_swoosh', 354, 1.0], ['deploy_drop', 372, 0.9], ['bark_useless', 378, 0.8],
        ['deploy_drop', F_LM, 0.9], ['bark_lmao', F_LM + 4, 0.8], ['w_fanfare', DIE + 14, 0.9], ['emo_lmao', 534, 0.9], ['victory', 722, 0.8]]
for k in (158, 194, 230): CUES += [['atk_chillguy', k - 4, 0.6], ['die_useless', k, 0.5], ['coin_jingle', k + 1, 0.5]]
CUES.append(['die_chillguy', F_CG_DIE, 0.9])
for f_ in range(150, F_CG_DIE, 11): CUES.append(['atk_useless', f_, 0.25])
for f_ in HIT1[::2]: CUES.append(['tower_hit', f_, 0.35])
for (ft, fl, ctr) in LAUGHS: CUES += [['atk_lmao', ft - 2, 0.9], ['die_useless', fl, 0.7], ['coin_jingle', fl + 1, 0.8], ['coins', fl + 3, 0.6]]
for s_ in ovl['shots']: CUES += [['tower_shot', s_['f0'], 0.45], ['tower_hit', s_['f1'], 0.35]]
ovl['marks'] = {'title': [1, 60], 'noob': [61, 362], 'pro': [363, 720], 'x_at': 285, 'check_at': DIE + 14, 'endcard': [721, 810],
                'drop_lmao': F_LM, 'drop_cg': F_CG, 'whale_die': DIE, 'tower_hits': HIT1, 'idol_hits': [], 'drop_idol': -99, 'drop_useless': -99,
                'caps_noob': ['Chill Guy hits ONE coin at a time.', 'The swarm eats him alive.'],
                'caps_pro': ['LMAO! hits EVERYTHING in its splash.', 'One laugh. Whole swarm gone.'],
                'title2': 'vs SWARMS', 'cues': CUES,
                'hud': {'noob': {'hand': ['chillguy', 'lmao', 'troll', 'ket'], 'next': 'useless', 'plays': [[F_CG - 6, 0]], 'cop': 5.6},
                        'pro': {'hand': ['lmao', 'chillguy', 'troll', 'ket'], 'next': 'useless', 'plays': [[F_LM - 6, 0]], 'cop': 6.2}}}
if OVL: json.dump(ovl, open(OVL, 'w'))
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT))
print('BUILT', OUT, 'frames', LAST)
