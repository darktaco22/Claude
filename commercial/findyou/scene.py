"""I WILL FIND YOU. NEET loses to xX_Grandma_Rugs_Xx and swears revenge; the hunt; the reveal.

    blender -b -P scene.py -- --out scene.blend
Env: PH (Poly Haven assets), FY_LOSS / FY_GRAN (PNG sequences of the real-engine captures for the monitor and the phone).
Three sets side by side: the basement (x=0), the stakeout outside Sunny Acres (x=60) and the retirement-home lounge (x=-60).
NEET is the game's own model and clips. Grandma is a MakeHuman person (MPFB 2, CC0) posed with the Degens toolkit."""
import bpy, sys, os, math, json, random
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); DG = os.path.join(HERE, '..', 'degens'); sys.path.insert(0, DG)
os.environ.setdefault('DA_STUDIO', os.path.join(DG, 'studio'))
import humans, rigctl, assets, props, room, grips
import director as D

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return ARGS[ARGS.index(k) + 1] if k in ARGS else d
FPS = 30; NF = int(arg('--frames', 1128)); T = lambda f: (f - 1) / FPS
clamp, lerp, ease, ramp, pulse, win = D.clamp, D.lerp, D.ease, D.ramp, D.pulse, D.win
TEX = os.path.join(HERE, 'tex'); CARDS = os.path.join(HERE, '..', 'coins', 'cards')
VO = json.load(open(os.path.join(HERE, 'audio', 'vo', 'lines.json')))
LINES = [('n_who', 5.0), ('n_sol', 7.0), ('n_cards', 9.9), ('n_season', 13.9), ('n_find', 17.6), ('n_copium', 20.4),
         ('g_hello', 31.0), ('g_rug', 36.3)]
def talk(who, t):
    for i, t0 in LINES:
        if VO[i]['who'] != who: continue
        e = VO[i]['env']; j = int((t - t0) * FPS)
        if 0 <= j < len(e): return e[j]
    return 0.0
THUNDER = [1.8, 9.6, 17.3, 26.2, 28.6]
# shots: start time, name
CUTS = [(0.0, 'monitor'), (3.0, 'neet_face'), (4.6, 'mono_wide'), (9.6, 'mono_med'), (13.7, 'mono_close'), (17.4, 'mono_xcu'),
        (22.4, 'board_pan'), (24.0, 'neet_monitor'), (25.4, 'board_string'), (27.0, 'stakeout'), (30.0, 'lounge_wide'),
        (31.6, 'gran_close'), (33.0, 'insert'), (36.0, 'gran_close2')]
def shot(t):
    k = CUTS[0]
    for c in CUTS:
        if t >= c[0]: k = c
    return k
C = lambda: bpy.context.scene.collection
K = rigctl.Keys()

def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = int(arg('--samples', 8)); sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'; sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = 720, 1280
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.2
    sc.render.use_persistent_data = True; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.006, 0.007, 0.012, 1); bg.inputs[1].default_value = 1.0

def box(name, size, loc, m, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot); o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m)
    if bevel: b = o.modifiers.new('b', 'BEVEL'); b.width = bevel; b.segments = 3
    return o
def imgmat(name, path, emit=0.0, rough=0.7):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(path); nt.links.new(ti.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if emit: nt.links.new(ti.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    return m, ti
def seqmat(name, first_png, emit):
    m, ti = imgmat(name, first_png, emit)
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0, 0, 0, 1)
    for l in list(m.node_tree.links):
        if l.to_socket.name == 'Base Color': m.node_tree.links.remove(l)
    ti.image.source = 'SEQUENCE'; ti.image_user.frame_duration = 9999; ti.image_user.use_auto_refresh = True
    return m, ti
def area(name, col, e, loc, rot, size=0.5):
    ld = bpy.data.lights.new(name, 'AREA'); ld.color = col; ld.energy = e; ld.size = size
    o = bpy.data.objects.new(name, ld); C().objects.link(o); o.location = loc; o.rotation_euler = rot; return o
def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()

# ================================================================== the basement (NEET's lair), x = 0
def basement():
    S = {}
    room.plane('b_floor', (8, 8), (0, 0, 0), (0, 0, 0), room.pbr('bfloor', 'old_linoleum_flooring_01', 1.0, tint=(0.5, 0.5, 0.55)))
    wall = room.pbr('bwall', 'concrete_block_wall', 1.0, tint=(0.45, 0.47, 0.55))
    room.plane('b_back', (8, 3), (0, 2.2, 1.5), (math.pi / 2, 0, 0), wall)
    room.plane('b_left', (8, 3), (-2.0, 0, 1.5), (math.pi / 2, 0, math.pi / 2), wall)
    room.plane('b_right', (8, 3), (2.3, 0, 1.5), (math.pi / 2, 0, -math.pi / 2), wall)
    room.plane('b_ceiling', (8, 8), (0, 0, 2.6), (math.pi, 0, 0), props.mat('bceil', (0.2, 0.2, 0.22), 0.9))
    # the high window behind him: rain, and the lightning
    room.plane('b_window', (1.0, 0.36), (0.5, 2.19, 2.25), (math.pi / 2, 0, math.pi), props.mat('bwin', (0.05, 0.07, 0.1), 0.1, emit=(0.25, 0.32, 0.45), estr=0.4))
    S['lightning'] = area('lightning', (0.75, 0.82, 1.0), 0, (0.5, 2.6, 2.3), (math.radians(-100), 0, 0), 1.0)
    # the gaming chair NEET sits on (seat at room.SEAT_H), and the desk with the monitor in front of him (the camera side)
    chair = props.mat('chair', (0.02, 0.02, 0.025), 0.45); red = props.mat('chairred', (0.5, 0.02, 0.03), 0.5)
    box('seat', (0.55, 0.52, 0.1), (0, 0.95, room.SEAT_H - 0.05), chair, 0.03)
    box('back', (0.55, 0.1, 0.85), (0, 1.25, room.SEAT_H + 0.4), chair, 0.04)
    box('stripe', (0.12, 0.102, 0.8), (0, 1.25, room.SEAT_H + 0.4), red)
    box('pole', (0.06, 0.06, room.SEAT_H - 0.1), (0, 0.95, (room.SEAT_H - 0.1) / 2), props.mat('pole', (0.1, 0.1, 0.1), 0.3, metal=0.8))
    desk = props.mat('desk', (0.06, 0.05, 0.045), 0.6)
    box('desk', (0.7, 1.4, 0.04), (-0.85, 0.9, 0.74), desk, 0.005)
    for y in (0.3, 1.5): box('leg', (0.6, 0.04, 0.72), (-0.85, y, 0.36), desk)
    MON = Vector((-0.8, 0.55, 1.02)); MROT = math.radians(-35)
    mon = box('monitor', (0.62, 0.04, 0.38), MON, props.mat('monb', (0.01, 0.01, 0.012), 0.3), 0.01, rot=(0, 0, MROT))
    box('monstand', (0.06, 0.06, 0.12), MON + Vector((0, 0.02, -0.21)), props.mat('monb2', (0.02, 0.02, 0.02), 0.4))
    fwd = Vector((math.sin(-MROT) * -1, math.cos(MROT), 0)).normalized()   # the screen's facing (toward NEET)
    fwd = Vector((-math.sin(MROT), math.cos(MROT), 0))
    sm, ti = seqmat('mon_screen', os.path.join(os.environ['FY_LOSS'], 'm_0001.png'), 2.2)
    scr = room.plane('mon_scr', (0.215, 0.36), MON + fwd * 0.022, (math.pi / 2, 0, math.pi + MROT), sm)       # portrait game window on a landscape monitor
    S['mon_ti'] = ti
    room.plane('mon_bg', (0.6, 0.36), MON + fwd * 0.0215, (math.pi / 2, 0, math.pi + MROT), props.mat('monbg', (0, 0, 0), 0.4, emit=(0.02, 0.01, 0.06), estr=1.0))
    S['monglow'] = area('monglow', (0.6, 0.72, 1.0), 70, MON + fwd * 0.1, (0, 0, 0), 0.5); aim(S['monglow'], (0, 0.85, 1.2))
    S['MON'] = MON; S['MONF'] = fwd
    k = area('neet_key', (0.55, 0.65, 1.0), 25, (0.9, -0.6, 1.6), (0, 0, 0), 0.6); aim(k, (0, 0.85, 1.2))
    rim = area('neet_rim', (0.5, 0.55, 0.9), 40, (0.6, 1.9, 2.0), (0, 0, 0), 0.8); aim(rim, (0, 0.95, 1.3))
    for i, (x, y) in enumerate([(-0.65, 0.85), (-1.0, 1.0), (-0.75, 1.2), (-1.05, 0.35), (-0.6, 1.4)]):
        c = props.can(f'can{i}'); c.location = (x, y, 0.76); c.rotation_euler.z = i
    for i, (x, y) in enumerate([(-0.9, 0.9), (0.95, 1.4), (1.1, 0.6)]):
        c = props.can(f'fcan{i}'); c.location = (x, y, 0.033); c.rotation_euler = (math.pi / 2, 0, i * 1.1)
    try:
        bx, _ = assets.load('cardboard_box_01'); bx.location = (-1.5, 1.6, 0)
    except Exception as e: print(e)
    # the corkboard on the left wall, the evidence on it, and red string between the pins
    cork = bpy.data.materials.new('cork'); cork.use_nodes = True; nt = cork.node_tree; b = nt.nodes['Principled BSDF']
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 90; nz.inputs['Detail'].default_value = 6
    rp = nt.nodes.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (0.25, 0.13, 0.05, 1); rp.color_ramp.elements[1].color = (0.55, 0.36, 0.18, 1)
    nt.links.new(nz.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.95
    bx_ = box('corkboard', (0.03, 1.8, 1.1), (-1.97, 0.9, 1.45), cork)
    frame_m = props.mat('frame', (0.15, 0.1, 0.06), 0.6)
    box('cork_frame_t', (0.04, 1.86, 0.04), (-1.965, 0.9, 2.02), frame_m); box('cork_frame_b', (0.04, 1.86, 0.04), (-1.965, 0.9, 0.88), frame_m)
    items = [('profile.png', 0.9, 1.62, 0.32, 0.40, -3), ('rug.webp', 0.25, 1.70, 0.24, 0.30, 4), ('chat.png', 1.55, 1.75, 0.34, 0.16, 2),
             ('photo.png', 1.55, 1.25, 0.34, 0.25, -4), ('map.png', 0.3, 1.15, 0.32, 0.24, 3), ('note1.png', 1.15, 1.08, 0.16, 0.16, 8),
             ('note2.png', 0.62, 1.10, 0.15, 0.15, -6), ('note3.png', 1.62, 0.98, 0.14, 0.14, 5), ('useless.webp', 0.65, 1.88, 0.15, 0.19, -8),
             ('note4.png', 0.15, 1.85, 0.13, 0.13, 7)]
    pins = []
    pin_m = props.mat('pin', (0.8, 0.05, 0.05), 0.3)
    for i, (fn, y, z, w, h, rot) in enumerate(items):
        p = os.path.join(TEX, fn) if os.path.exists(os.path.join(TEX, fn)) else os.path.join(CARDS, fn)
        m, _ = imgmat(f'ev{i}', p, 0.0, 0.8)
        room.plane(f'ev{i}', (w, h), (-1.950 + i * 0.0006, y, z), (math.pi / 2, math.radians(rot), math.pi / 2), m)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012, location=(-1.935, y, z + h * 0.42)); bpy.context.object.data.materials.append(pin_m)
        pins.append(Vector((-1.932, y, z + h * 0.42)))
    rs = props.mat('string', (0.75, 0.02, 0.03), 0.6)
    for a, b_ in [(0, 1), (0, 2), (0, 3), (0, 4), (3, 4), (2, 5), (4, 6), (3, 7), (1, 8), (0, 9), (5, 6)]:
        A, B = pins[a], pins[b_]; mid = (A + B) / 2; L = (B - A).length
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0025, depth=L, location=mid, vertices=6); o = bpy.context.object
        o.rotation_euler = (B - A).to_track_quat('Z', 'Y').to_euler(); o.data.materials.append(rs)
    S['pins'] = pins
    # the lamp over the board (a hard spot for the hunt montage)
    S['boardspot'] = area('boardspot', (1.0, 0.85, 0.65), 0, (-1.2, 0.9, 2.4), (0, math.radians(-50), 0), 0.25)
    area('fill_b', (0.35, 0.4, 0.7), 6, (1.5, -1.2, 2.2), (math.radians(55), 0, math.radians(40)), 1.5)
    return S

# ================================================================== the stakeout: outside Sunny Acres at night, x = 60
def stakeout():
    S = {}; ox = 60.0
    room.plane('s_ground', (30, 30), (ox, 4, 0), (0, 0, 0), room.pbr('sasph', 'asphalt_02', 0.5, rough_mul=0.6))
    room.plane('s_bldg', (20, 6), (ox, 9.0, 3), (math.pi / 2, 0, 0), room.pbr('sbrick', 'dark_brick_wall', 0.4, tint=(0.75, 0.7, 0.65)))
    for x in (-5, -2, 1, 4):
        room.plane(f's_win{x}', (1.2, 0.9), (ox + x, 8.98, 2.4), (math.pi / 2, 0, 0), props.mat(f'swin{x}', (0.3, 0.25, 0.15), 0.3, emit=(1.0, 0.8, 0.5), estr=2.5))
    m, _ = imgmat('sign', os.path.join(TEX, 'sign.png'), 1.2, 0.6)
    box('signboard', (2.6, 0.08, 1.0), (ox + 0.6, 5.0, 1.45), props.mat('signback', (0.2, 0.2, 0.2), 0.6))
    room.plane('sign', (2.5, 0.93), (ox + 0.6, 4.955, 1.45), (math.pi / 2, 0, 0), m)
    for x in (-0.6, 1.8): box('signpost', (0.08, 0.08, 1.0), (ox + x, 5.0, 0.5), props.mat('post', (0.2, 0.2, 0.2), 0.5))
    area('signlight', (1.0, 0.9, 0.7), 60, (ox + 0.6, 4.2, 0.2), (math.radians(-70), 0, 0), 0.8)
    # the hedge NEET hides behind (in front of the camera)
    hedge = bpy.data.materials.new('hedge'); hedge.use_nodes = True; nt = hedge.node_tree; b = nt.nodes['Principled BSDF']
    vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 40
    rp = nt.nodes.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (0.005, 0.02, 0.005, 1); rp.color_ramp.elements[1].color = (0.04, 0.12, 0.03, 1)
    nt.links.new(vo.outputs['Distance'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], b.inputs['Base Color'])
    h = box('hedge', (3.4, 0.7, 0.95), (ox, 2.5, 0.475), hedge, 0.2)
    d = h.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.new('leafy', 'CLOUDS'); tx.noise_scale = 0.08; d.texture = tx; d.strength = 0.12
    sub = h.modifiers.new('s', 'SUBSURF'); sub.levels = 3; h.modifiers.move(2, 0)
    r_ = area('neet_back', (0.6, 0.7, 1.0), 120, (ox + 0.3, 3.4, 2.2), (0, 0, 0), 1.2); aim(r_, (ox + 0.25, 1.95, 1.0))
    area('moon_s', (0.4, 0.5, 0.85), 80, (ox - 3, -2, 5), (math.radians(40), 0, math.radians(-30)), 3.0)
    S['lightning_s'] = area('lightning_s', (0.75, 0.82, 1.0), 0, (ox + 2, -1, 8), (math.radians(20), 0, 0), 6.0)
    # rain: thin streaks, looped downward
    rain = bpy.data.objects.new('rain', None); C().objects.link(rain); rm = props.mat('rainm', (0.6, 0.7, 0.85), 0.1, emit=(0.5, 0.6, 0.8), estr=0.6)
    rnd = random.Random(3)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.003, depth=0.35, vertices=4); proto = bpy.context.object; proto.data.materials.append(rm)
    for i in range(500):
        o = proto.copy(); C().objects.link(o); o.parent = rain
        o.location = (ox + rnd.uniform(-4, 4), rnd.uniform(-1, 8), rnd.uniform(0, 8)); o.rotation_euler = (0.12, 0, 0)
    bpy.data.objects.remove(proto)
    S['rain'] = rain
    return S

# ================================================================== the lounge at Sunny Acres, x = -60 (afternoon)
def lounge():
    S = {}; ox = -60.0
    room.plane('l_floor', (8, 8), (ox, 0, 0), (0, 0, 0), room.pbr('lfloor', 'wooden_floor_02', 0.6))
    wall = room.pbr('lwall', 'painted_plaster_wall', 0.6, tint=(1.0, 0.92, 0.8))
    room.plane('l_back', (8, 3), (ox, 2.0, 1.5), (math.pi / 2, 0, 0), wall)
    room.plane('l_left', (8, 3), (ox - 2.2, 0, 1.5), (math.pi / 2, 0, math.pi / 2), wall)
    room.plane('l_ceiling', (8, 8), (ox, 0, 2.7), (math.pi, 0, 0), props.mat('lceil', (0.85, 0.83, 0.8), 0.9))
    room.plane('l_window', (1.3, 1.2), (ox + 1.4, 1.99, 1.5), (math.pi / 2, 0, math.pi), props.mat('lwin', (1, 1, 1), 0.2, emit=(1.0, 0.95, 0.85), estr=6))
    area('l_sun', (1.0, 0.88, 0.7), 900, (ox + 1.4, 2.6, 1.6), (math.radians(-95), 0, 0), 1.4)
    area('l_fill', (1.0, 0.92, 0.85), 120, (ox - 1.0, -2.5, 2.2), (math.radians(60), 0, math.radians(-25)), 2.5)
    try:
        ch, _ = assets.load('ArmChair_01'); ch.location = (ox, 0.95, 0); ch.rotation_euler.z = 0.0
        lo, hi = assets.dims(ch); print('ARMCHAIR dims', lo, hi); S['chair'] = ch
    except Exception as e: print('armchair', e)
    try:
        st, _ = assets.load('side_table_01'); st.location = (ox + 0.75, 0.75, 0)
        lo, hi = assets.dims(st); S['table_top'] = hi.z
    except Exception as e: print('table', e); S['table_top'] = 0.6
    mug = props.mug('gran_mug', (0.95, 0.95, 0.95), ['#1', 'GRANDMA']); mug.location = (ox + 0.72, 0.72, S['table_top'] + 0.048); mug.rotation_euler.z = 2.4
    yarn = bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(ox - 0.55, 0.6, 0.07)); y = bpy.context.object
    y.data.materials.append(props.mat('yarn', (0.75, 0.15, 0.35), 0.95))
    for aid, loc in (('wall_clock', (ox - 0.9, 1.97, 2.0)), ('potted_plant_02', (ox - 1.6, 1.5, 0)), ('hanging_picture_frame_02', (ox - 0.2, 1.97, 1.9))):
        try:
            o, _ = assets.load(aid); o.location = loc
            if aid != 'potted_plant_02': o.rotation_euler = (0, 0, 0)
        except Exception as e: print(aid, e)
    return S

# ================================================================== NEET
def load_neet():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'neet.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == 'ARMATURE'); mesh = next(o for o in new if o.type == 'MESH' and o.name.startswith('neet'))
    for o in new:
        if o.name.startswith('Icosphere'): o.hide_render = True
    root = bpy.data.objects.new('NEET', None); C().objects.link(root); rig.parent = root
    acts = {a.name.split('_neet_rig')[0]: a for a in bpy.data.actions if a.name.endswith('_neet_rig')}
    rig.animation_data_create(); rig.animation_data.action = None
    for pb in rig.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]; h = max(v.z for v in bb) - min(v.z for v in bb)
    s = 1.7 / h; root.scale = (s, s, s)
    return dict(root=root, rig=rig, mesh=mesh, acts=acts)

NEET_SCHED = [(0.0, 'sitangry', 1.0), (2.9, 'sit', 1.0), (17.35, 'sitangry', 0.9), (20.1, 'sit', 1.0), (22.3, 'idle', 1.0)]
def neet_nla(N):
    ad = N['rig'].animation_data
    for i, (t0, clip, speed) in enumerate(NEET_SCHED):
        tr = ad.nla_tracks.new(); a = N['acts'][clip]; length = a.frame_range[1] - a.frame_range[0]
        st = tr.strips.new(clip, int(round(t0 * FPS + 1)), a); st.scale = 1.0 / speed
        nxt = NEET_SCHED[i + 1][0] if i + 1 < len(NEET_SCHED) else NF / FPS + 1
        if clip in ('sit', 'idle'): st.repeat = max(1.0, ((nxt - t0) * FPS + 30) / (length * st.scale))
        st.blend_in = 6; st.extrapolation = 'HOLD_FORWARD'; st.blend_type = 'REPLACE'; st.use_auto_blend = False
    # the delivery: a slow, heavy head motion layered over the clips (combine), small pushes on his words
    act = bpy.data.actions.new('neet_head'); ad.action = act; ad.action_blend_type = 'COMBINE'
    pb = N['rig'].pose.bones['mixamorig:Head']; pb.rotation_mode = 'QUATERNION'
    for f in range(1, int(22.3 * FPS)):
        t = T(f); tv = talk('neet', t)
        nod = 0.05 * tv * math.sin(t * 7.0) + (0.04 if win(t, 4.6, 22.3) else 0.0)       # chin slightly down: menace
        tilt = 0.03 * math.sin(t * 0.7)
        q = rigctl.qrot((1, 0, 0), nod) @ rigctl.qrot((0, 0, 1), tilt)
        for i in range(4): K.add(N['rig'], 'pose.bones["mixamorig:Head"].rotation_quaternion', i, f, q[i])
    return act

def seat_neet(N):
    """Put his sit clip's seat on the chair (seat top at room.SEAT_H), facing the camera (-Y)."""
    sc = bpy.context.scene; sc.frame_set(int(6 * FPS))
    rig, mesh, root = N['rig'], N['mesh'], N['root']
    root.location = (0, 0.95, 0); root.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
    hips = rig.pose.bones['mixamorig:Hips']; hw = rig.matrix_world @ hips.head
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    pts = [mesh.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    seat_z = min(p.z for p in pts if (Vector((p.x, p.y)) - Vector((hw.x, hw.y))).length < 0.3 and p.z < hw.z)
    dy = 0.95 - hw.y
    return Vector((0, 0.95 + dy * 0.6, room.SEAT_H + 0.005 - seat_z))

# ================================================================== Grandma
def grandma_actor():
    humans.CAST['grandma'] = dict(humans.CAST['pam']); humans.CAST['grandma']['hair'] = 'toigo_curled_under_bob'; humans.CAST['grandma']['tint'] = {
        'toigo_fisherman_sweater': (0.92, 0.9, 1.15, (0.82, 0.55, 0.62)), 'toigo_curled_under_bob': (0.0, 0.08, 2.3, (0.95, 0.94, 0.93))}     # dusty-rose cardigan, white hair
    rig, body, parts = humans.build('grandma')
    a = rigctl.Actor('grandma', rig, body); a.parts = parts
    c, M, w = grips.phone(a, 'R'); a.G = {'phone': (c, M)}
    return a

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True); setup_render()
    B = basement(); S = stakeout(); L = lounge()
    N = load_neet(); neet_nla(N); sit_loc = seat_neet(N)
    a = grandma_actor()
    ph = props.phone('gran_phone', os.path.join(os.environ['FY_GRAN'], 'g_0001.png'))
    sm = bpy.data.materials[ph['screen_mat']]; ti = [n for n in sm.node_tree.nodes if n.type == 'TEX_IMAGE'][0]
    ti.image.source = 'SEQUENCE'; ti.image_user.frame_duration = 9999; ti.image_user.use_auto_refresh = True
    sm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.8
    bpy.data.objects[ph['glow']].data.energy = 0.6
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); C().objects.link(cam); bpy.context.scene.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.2
    # grandma in the armchair: seat height measured off the chair
    seat_h = 0.45
    if 'chair' in L:
        lo, hi = assets.dims(L['chair']); seat_h = lo.z + (hi.z - lo.z) * 0.47
    GS = Matrix.Translation((-60.0, 0.78, 0.0))
    hipc = (a.hip['L'] + a.hip['R']) / 2; root0 = Vector((0, 0.035 - hipc.y, seat_h + 0.095 - hipc.z))
    sx = {'L': 1, 'R': -1}; st = dict(yaw=0.0, pitch=0.55)
    # monitor / phone image sequence offsets: the loss capture starts at the RUG PULL; the grandma capture's frame 1 = t 30
    B['mon_ti'].image_user.frame_offset = 0; ti.image_user.frame_offset = 0
    N['root'].location = sit_loc; bpy.context.scene.frame_set(150); bpy.context.view_layer.update()
    NH = N['rig'].matrix_world @ N['rig'].pose.bones['mixamorig:Head'].head + Vector((0, -0.06, 0.07)); print('NEET head', NH)
    for f in range(1, NF + 1):
        t = T(f); kind = shot(t)[1]
        # ---------------- NEET: where he is in each part
        if t < 22.3: loc, rz = sit_loc, 0.0
        elif t < 27.0: loc, rz = Vector((-1.2, 1.55, 0)), math.radians(-90)        # standing at the board, facing it
        else: loc, rz = Vector((60.25, 1.95, -0.52)), math.pi                      # crouched behind the hedge, peeking at the home
        for i in range(3): K.add(N['root'], 'location', i, f, loc[i])
        K.add(N['root'], 'rotation_euler', 2, f, rz)
        # ---------------- lightning
        flash = sum(max(0.0, 1 - abs(t - th - d) / 0.05) * w for th in THUNDER for d, w in ((0.0, 1.0), (0.18, 0.6), (0.3, 0.8)))
        K.add(B['lightning'].data, 'energy', 0, f, 3000 * flash); K.add(S['lightning_s'].data, 'energy', 0, f, 20000 * flash)
        K.add(B['boardspot'].data, 'energy', 0, f, 160.0 if 22.3 <= t < 27.0 else 0.0)
        K.add(S['rain'], 'location', 2, f, -((t * 9.0) % 2.0))
        # ---------------- Grandma
        yawT, pitchT, smile = 0.0, 0.55, 0.12
        if win(t, 30.7, 32.6) or t >= 36.1: pitchT = 0.0; smile = 0.55
        st['yaw'] = lerp(st['yaw'], yawT, 0.2); st['pitch'] = lerp(st['pitch'], pitchT, 0.2)
        Q = {}; lean = math.radians(-4) + math.sin(t * 1.6) * 0.008; root_loc = root0
        for bn, wgt in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)):
            Q[bn] = a.local_q(bn, rigctl.qrot((1, 0, 0), lean * wgt))
        tv = talk('grandma', t)
        for bn, wgt in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)):
            Q[bn] = a.local_q(bn, rigctl.qrot((0, 0, 1), st['yaw'] * wgt) @ rigctl.qrot((1, 0, 0), (st['pitch'] - lean * 0.9 + math.sin(t * 8) * 0.02 * (tv > 0.1)) * wgt))
        blink = 1.0 if (t % 3.9) < 0.12 else 0.0
        for s in 'LR':
            Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), 0.5 * blink + 0.12 * smile))
            Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink + 0.12 * smile))
        Q['jaw'] = a.local_q('jaw', rigctl.qrot((1, 0, 0), tv * 0.1))
        ph_ = math.sin(t * 12.0) * 0.5 + 0.5
        shape = {'v_aa': tv * 0.25, 'v_ow': tv * 0.22 * ph_, 'v_ee': smile * 0.15 + tv * 0.12 * (1 - ph_), 'v_mm': 0.35 * (tv < 0.05), 'v_ff': 0.0}
        feet, poles = {}, {}
        for s in 'LR':
            hip = a.hip[s] + root_loc; ank = Vector((hip.x + sx[s] * 0.06, -(a.thigh + 0.04), 0.085))
            Fm = a.rest[f'foot.{s}'].copy(); Fm.translation = ank
            feet['foot', s] = GS @ Fm; poles['foot', s] = GS @ Vector((hip.x + sx[s] * 0.08, -1.2, 0.55))
        head = a.fk(Q, root_loc, 'head')
        eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
        G = a.G
        def phone_frame(s, dist, drop):
            flat = Vector((0, -1, 0)); zup = Vector((0, 0, 1)); tgt = eyes + flat * dist - zup * drop
            n = (eyes + Vector((0, 0, 0.05)) - tgt).normalized(); upp = (zup - n * zup.dot(n)).normalized()
            X = upp * a.idx_sign[s]; Y = n.cross(X); F = a.frame(Vector(), Y, n); F.translation = tgt - F.to_3x3() @ G['phone'][1].translation; return F
        def lap(s):
            hip = a.hip[s] + root_loc; knee = hip + Vector((0, -a.thigh * 0.95, -0.06))
            sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation; reach = (a.uarm + a.farm) * 0.95
            for u in [0.6 - 0.04 * i for i in range(9)]:
                pos = hip.lerp(knee, u) + Vector((-sx[s] * 0.01, 0, 0.085)); F = a.frame(pos, (-sx[s] * 0.15, -1, -0.15), (sx[s] * 0.2, 0, -1))
                if (a.hand_matrix_for_palm(s, F).translation - sh).length <= reach: break
            return F
        hands = {'L': lap('L'), 'R': phone_frame('R', 0.34, 0.36)}
        if win(t, 32.7, 33.0): hands['R'] = Matrix.Translation(Vector((0, 0, -0.012)) * pulse(t, 32.7, 33.0, 0.1)) @ hands['R']   # the tap
        for s in 'LR':
            wp = a.hand_matrix_for_palm(s, hands[s]).translation; sh_ = a.fk(Q, root_loc, f'upperarm01.{s}').translation; dv = wp - sh_
            reach = (a.uarm + a.farm) * 0.985
            if dv.length > reach: hands[s] = Matrix.Translation(dv.normalized() * (reach - dv.length)) @ hands[s]
        D.curl_Q(a, 'L', 'rest', Q); Q.update(grips.curlQ(a, 'R', G['phone'][0]))
        H = {('hand', s): GS @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
        for s, tuck in (('L', 0.0), ('R', 1.0)):
            poles['hand', s] = GS @ (a.shoulder[s] + root_loc + Vector((sx[s] * 0.7, 0.45, -0.45)).lerp(Vector((sx[s] * 0.22, 0.35, -0.75)), tuck))
        a.key_pose(f, GS, Q, root_loc, H, feet, poles, shape)
        Wp = GS @ hands['R'] @ G['phone'][1]; ph.rotation_mode = 'QUATERNION'
        for i in range(3): K.add(ph, 'location', i, f, Wp.translation[i])
        for i in range(4): K.add(ph, 'rotation_quaternion', i, f, Wp.to_quaternion()[i])
        geyes = GS @ eyes
        # ---------------- camera
        c0 = shot(t)[0]; u = t - c0; nheadZ = sit_loc.z + 1.15
        nh = NH.copy()                       # NEET's face (seated)
        if kind == 'monitor':   mon_c = B['MON'] + B['MONF'] * 0.02; loc = mon_c + B['MONF'] * (0.75 - 0.2 * ease(u / 3)) + Vector((0.12, 0, 0.12)); look = mon_c; lens = 45
        elif kind == 'neet_face': loc = nh + Vector((0.4, -1.35, -0.02)); look = nh; lens = 50
        elif kind == 'mono_wide': loc = nh + Vector((0.0, -2.7, 0.05)) + Vector((0, 0.45, -0.03)) * ease(u / 5); look = nh + Vector((0, 0, -0.3)); lens = 35
        elif kind == 'mono_med':  loc = nh + Vector((0.0, -1.8, 0.02)) + Vector((0, 0.2, 0)) * ease(u / 4); look = nh + Vector((0, 0, -0.12)); lens = 45
        elif kind == 'mono_close': loc = nh + Vector((0.0, -1.15, 0.03)) + Vector((0, 0.12, 0)) * ease(u / 3.7); look = nh; lens = 50
        elif kind == 'mono_xcu':  loc = nh + Vector((0.0, -0.85, 0.06)) + Vector((0, 0.1, 0)) * ease(u / 5); look = nh + Vector((0, 0, 0.06)); lens = 60
        elif kind == 'board_pan': loc = Vector((-0.55, 1.25 - 0.55 * ease(u / 1.6), 1.5)); look = Vector((-1.97, 0.95 - 0.1 * ease(u / 1.6), 1.45)); lens = 32
        elif kind == 'neet_monitor': loc = Vector((0.9, 1.9, 1.8)); look = Vector((-1.4, 0.9, 1.35)); lens = 26
        elif kind == 'board_string': loc = Vector((-1.15, 0.55, 1.4)) + Vector((0, 0.15, 0.03)) * ease(u / 1.6); look = Vector((-1.95, 1.3, 1.35)); lens = 38
        elif kind == 'stakeout':  loc = Vector((60.8, 0.6, 1.0)) + Vector((0, 0.2, 0)) * ease(u / 3); look = Vector((60.35, 5.0, 1.25)); lens = 30
        elif kind == 'lounge_wide': loc = Vector((-59.6, -1.9, 1.3)) + Vector((-0.1, 0.45, -0.05)) * ease(u / 1.6); look = geyes + Vector((0, 0, -0.25)); lens = 35
        elif kind in ('gran_close', 'insert'): loc = geyes + Vector((0.05, -0.75, 0.02)) - Vector((0, 0.06, 0)) * ease(u / 1.4); look = geyes; lens = 50
        else: loc = geyes + Vector((-0.12, -0.6, 0.0)); look = geyes; lens = 55
        d = look - loc; rot = d.to_track_quat('-Z', 'Y').to_euler()
        for i in range(3): K.add(cam, 'location', i, f, loc[i]); K.add(cam, 'rotation_euler', i, f, rot[i])
        K.add(cam.data, 'lens', 0, f, lens); K.add(cam.data, 'dof.focus_distance', 0, f, d.length)
    a.K.flush(); K.flush()
    cut_frames = {int(round(c * FPS)) + 1 for c, _ in CUTS} | {int(round(22.3 * FPS)) + 1, int(round(27.0 * FPS)) + 1}
    for idb in (cam, cam.data, N['root']):
        ad = idb.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cut_frames or idb is N['root'] else 'LINEAR'
    for o in bpy.data.objects:
        if o.type == 'LIGHT': o.visible_camera = False
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg('--out', 'scene.blend')), compress=False)
    print('SAVED', arg('--out'))

if __name__ == '__main__':
    main()
