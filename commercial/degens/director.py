"""DEGENS ANONYMOUS, realistic remake: builds the whole film in Blender and keys every frame.

    blender -b -P director.py -- --out scene.blend [--frames N]

Timing, dialogue, sound cues, shots and lights are the original skit's (director.js), unchanged.
Frame f shows time t = (f - 1) / 30.
"""
import bpy, sys, os, math, json, random
from mathutils import Vector, Matrix, Quaternion, Euler
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import humans, rigctl, assets, props, room, grips

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None):
    return ARGS[ARGS.index(k) + 1] if k in ARGS else d
STUDIO = os.environ['DA_STUDIO']           # the original skit's folder (vo.json, models/neet.glb)
FPS, END = 30, 48.4
NF = int(arg('--frames', round(END * FPS)))
fr = lambda t: t * FPS + 1
T = lambda f: (f - 1) / FPS

clamp = lambda v, a=0.0, b=1.0: max(a, min(b, v))
lerp = lambda a, b, k: a + (b - a) * k
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
out3 = lambda t: 1 - (1 - clamp(t)) ** 3
win = lambda t, a, b: a <= t < b
ramp = lambda t, a, b: ease((t - a) / (b - a))
def pulse(t, a, b, f=0.15): return clamp(min((t - a) / f, (b - t) / f))
def vlerp(a, b, k): return a.lerp(b, k)

# ------------------------------------------------------------------ dialogue (the original lines)
VO = json.load(open(f'{STUDIO}/vo.json'))
LINES = []
def say(i, who, t, text): LINES.append(dict(id=i, who=who, t=t, end=t + VO[i]['dur'], text=text))
say('p_welcome', 'pam', 3.5, 'Welcome back, everyone. Who would like to share?')
say('neet_leaving', 'neet_ext', 1.75, 'Leaving the basement!')
say('n_hi', 'gary', 7.9, "Hi. I'm NEET.")
say('all2_p', 'pam', 9.3, 'Hi, NEET.'); say('all2_l', 'linda', 9.36, ''); say('all2_e', 'earl', 9.33, ''); say('all2_c', 'chad', 9.42, '')
say('n_four', 'gary', 11.0, "It's been... four minutes... since my last trade.")
say('p_record2', 'pam', 13.6, "That's a new record, NEET.")
say('l_casino', 'linda', 16.9, 'I told my husband I lost our savings at the casino.')
say('l_less', 'linda', 20.75, "Because that's less embarrassing.")
say('e_kidney', 'earl', 22.95, 'I sold a kidney to buy the dip.')
say('e_other', 'earl', 26.45, "I'm thinking about selling the other one.")
say('neet_letsgo', 'gary', 28.85, "Let's go!")
say('c_stop', 'chad', 30.05, "I'm not addicted. I can stop anytime.")
say('c_after', 'chad', 32.85, 'After this one.')
say('p_break', 'pam', 36.9, "Let's... take a five minute break.")
say('p_next', 'pam', 46.0, 'Same time next week.')
def talk(k, t):
    v = 0.0
    for L in LINES:
        if L['who'] == k and L['t'] <= t < L['end']:
            e = VO[L['id']]['env']; i = int((t - L['t']) * 30)
            v = max(v, e[i] if i < len(e) else 0.0)
    return v
def speaker(t):
    for L in LINES:
        if L['text'] and L['t'] - 0.2 <= t < L['end'] + 0.4: return L['who']
    return None

ORDER = ['chad', 'earl', 'pam', 'linda', 'gary']
RUN = {'gary': 39.35, 'linda': 39.5, 'chad': 39.45, 'earl': 39.6}
ARRIVE = {'gary': 40.45, 'linda': 40.78, 'chad': 40.98, 'earl': 41.16}   # at the doorway
EXIT = Vector((4.75, -1.2, 0))
LANE = {'chad': [(-0.5, -0.35), (2.6, -1.05)], 'earl': [(0.0, -0.15), (2.7, -1.3)], 'linda': [(1.5, -0.05), (2.8, -1.2)], 'gary': [(2.4, -0.95)]}

# ================================================================== build
def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = int(arg('--samples', 8)); sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.denoising_prefilter = 'ACCURATE'
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False; sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = int(arg('--w', 720)), int(arg('--h', 1280))
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    sc.render.use_motion_blur = False
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.75
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
    w = bpy.data.worlds.new('night'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(f"{os.environ['PH']}/cobblestone_street_night/cobblestone_street_night.hdr")
    nt.links.new(env.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.25
    sc.cycles.film_exposure = 1.0


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    setup_render()
    S = room.basement(); X = room.exterior(); rain = room.rain()
    seats = S['seats']
    SEAT = dict(zip(ORDER, seats))
    # ---------------- the cast
    A = {}
    for k in ['chad', 'earl', 'pam', 'linda']:
        rig, body, parts = humans.build(k)
        A[k] = rigctl.Actor(k, rig, body); A[k].parts = parts
    NEET = load_neet(SEAT['gary'])
    P = make_props(A)
    find_lips(A['earl'])
    place_oxygen(P, SEAT['earl'], A)
    for k, a in A.items():
        hs, pk = {'pam': ('L', 'pam_mug'), 'linda': ('L', 'linda_mug'), 'earl': ('R', 'earl_cig'), 'chad': ('R', 'chad_can')}[k]
        ph = 'R' if k in ('pam', 'linda') else 'L'
        a.G = {}
        if pk == 'earl_cig':
            c, sp, M, cl = grips.cigarette(a, hs); a.G['cig'] = (c, sp, M); print('GRIP', k, 'cig clearance mm', round(cl * 1000, 1))
        else:
            o = P[pk]; H = o['H']; z0, z1 = (-H * 0.45, H * 0.55) if 'mug' in pk else (-H * 0.42, H * 0.58)
            c, M, w = grips.cylinder(a, hs, o['R'], z0, z1); a.G['hold'] = (c, M); print('GRIP', k, pk, {f: round(v * 1000, 1) for f, v in w.items()})
        c, M, w = grips.phone(a, ph); a.G['phone'] = (c, M); print('GRIP', k, 'phone', {f: round(v * 1000, 1) for f, v in w.items()})
    cam = make_camera()
    smoke = make_smoke()
    # ---------------- per-frame solve
    Kx = rigctl.Keys()
    state = {k: dict(yaw=0.0, pitch=0.0) for k in ORDER}
    HEADS = head_positions(A, NEET, SEAT)
    for pas in (0, 1):
      if pas == 1:
        for a in A.values(): a.K.flush()
        Kx.flush()
        global SEAT_HEADS, SEAT_P, SEAT_NEET
        SEAT_HEADS, SEAT_P, SEAT_NEET = HEADS, P, NEET
        seat_fix(A, S, SEAT)
        global CIG_SEAT; CIG_SEAT = SEAT['earl']; cig_fix(A['earl'], P)
        hand_fix(A, P, SEAT)                 # after the cigarette is seated, so it is lifted clear of his leg too
        for a in A.values(): a.K.d = {}
        state = {k: dict(yaw=0.0, pitch=0.0) for k in ORDER}
      for f in (range(1, NF + 1) if pas == 1 else [int(fr(10.0))]):
        t = T(f)
        for k in ['chad', 'earl', 'pam', 'linda']:
            solve_actor(A[k], k, t, f, SEAT[k], state[k], HEADS, P, Kx)
        chairs(S, t, f, Kx)
        lights(S, X, t, f, Kx)
        camera(cam, t, f, HEADS, SEAT, Kx)
        smoke_frame(smoke, A['earl'], t, f, Kx)
        door(S, t, f, Kx)
        neet_frame(NEET, t, f, SEAT['gary'], Kx)
    for a in A.values(): a.K.flush()
    for o in bpy.data.objects:
        if o.type == 'LIGHT': o.visible_camera = False; o.visible_glossy = o.data.type != 'AREA' or o.name.startswith('tube')
    Kx.flush()
    # constant interpolation where cuts and switches must be instant
    for ob in [cam, cam.data] + [x for x in bpy.data.lights] + [bpy.data.materials[m] for m in CONST_MATS if m in bpy.data.materials]:
        idb = ob.node_tree if isinstance(ob, bpy.types.Material) else ob
        ad = idb.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    verify(A, P)
    if '--seatcheck' in ARGS: seat_report(A, S)
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False)
    print('SAVED', arg('--out'))

CONST_MATS = []
MOUTH = {}
def em_path(m, node='Principled BSDF', sock='Emission Strength'):
    n = m.node_tree.nodes[node]; i = list(n.inputs).index(n.inputs[sock])
    return f'nodes["{node}"].inputs[{i}].default_value'

# ================================================================== NEET (the game's model)
NEET_SCHED = [
    (0, 'walk', 0.01, 1), (3.2, 'sit', 0.01, 1), (7.3, 'idle', 0.5, 1), (15.3, 'win', 0.25, 1), (16.4, 'sit', 0.45, 1),
    (21.1, 'sitlaugh', 0.3, 1), (24.6, 'sit', 0.5, 1), (28.75, 'sitfistpump', 0.15, 1), (30.6, 'sit', 0.5, 1),
    (34.45, 'sityell', 0.2, 0.6), (35.6, 'sit', 0.6, 1), (39.3, 'run', 0.2, 1)]

def load_neet(seat, height=1.82):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f'{STUDIO}/models/neet.glb')
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == 'ARMATURE'); mesh = next(o for o in new if o.type == 'MESH' and o.parent is rig)
    root = bpy.data.objects.new('NEET', None); bpy.context.scene.collection.objects.link(root)
    rig.parent = root
    acts = {a.name.split('_neet_rig')[0]: a for a in bpy.data.actions if a.name.endswith('_neet_rig')}
    rig.animation_data_create(); rig.animation_data.action = None
    for pb in rig.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]; h = max(v.z for v in bb) - min(v.z for v in bb)
    s = height / h; root.scale = (s, s, s)
    # NLA: one track per schedule entry, later entries above, each blending in over its fade
    ad = rig.animation_data
    for i, (t0, clip, fade, speed) in enumerate(NEET_SCHED):
        tr = ad.nla_tracks.new(); tr.name = f'{i:02d}_{clip}'
        a = acts[clip]; length = a.frame_range[1] - a.frame_range[0]
        st = tr.strips.new(clip, int(round(fr(t0))), a)
        st.scale = 1.0 / speed
        loop = clip in ('walk', 'sit', 'idle', 'win', 'run')
        if loop:
            nxt = NEET_SCHED[i + 1][0] if i + 1 < len(NEET_SCHED) else END + 1
            st.repeat = max(1.0, (fr(nxt) + 30 - fr(t0)) / (length * st.scale))
        st.blend_in = max(0.01, fade * FPS); st.extrapolation = 'HOLD_FORWARD'
        st.blend_type = 'REPLACE'; st.use_auto_blend = False
    # where the seat is relative to his hips in the sit clip: put his seat on the chair
    sc = bpy.context.scene
    sc.frame_set(int(fr(5.0)))
    hips = rig.pose.bones['mixamorig:Hips']
    hw = rig.matrix_world @ hips.head
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    under = [mesh.matrix_world @ v.co for v in me.vertices]
    seat_z = min(p.z for p in under if (p - hw).length < 0.35 and p.z < hw.z)
    feet_z = min(p.z for p in under)
    ev.to_mesh_clear()
    root['sit_dz'] = room.SEAT_H + 0.005 - seat_z
    root['feet_z'] = feet_z
    root['hip_dy'] = hw.y - root.location.y
    print('NEET scale', s, 'sit seat z', seat_z, 'feet', feet_z, 'dz', root['sit_dz'])
    for o in new:
        o.hide_render = False
    return dict(root=root, rig=rig, mesh=mesh)


def neet_frame(N, t, f, seat, K):
    root = N['root']
    x, y, face, z = seat['x'], seat['y'], seat['face'], 0.0
    if t < 3.2:
        k = clamp(t / 3.0); a = Vector((61.25, -3.9)); b = Vector((60.2, -0.15)); p = a.lerp(b, k); x, y = p.x, p.y
        face = math.atan2(b.x - a.x, -(b.y - a.y))
    elif t >= RUN['gary']:
        p, face, vis = run_path('gary', seat, t); x, y = p.x, p.y; z = 0.0
        K.add(N['mesh'], 'hide_render', 0, f, 0 if vis else 1)
    else:
        sit = 1.0 - (ramp(t, 7.3, 7.6) - ramp(t, 16.4, 16.8))
        # the sit clip sits on air: lift/lower him so he lands on the chair; push back a little onto it
        z = 0.0          # his own sit clip, untouched; his stool is fitted to it
    if t < RUN['gary']:
        K.add(N['mesh'], 'hide_render', 0, f, 0)
    for i, v in enumerate((x, y, z)): K.add(root, 'location', i, f, v)
    K.add(root, 'rotation_euler', 2, f, face)

# ================================================================== props and wardrobe
def make_props(A):
    P = {}
    tex = os.environ.get('DA_TEX', '/tmp')
    P['pam_mug'] = props.mug('pam_mug', (0.06, 0.22, 0.48))
    P['linda_mug'] = props.mug('linda_mug', None, text=["WORLD'S", 'BEST MOM'])
    # the wine bottle hidden in Linda's mug, and her straw
    root, ms = assets.load('wine_bottles_01')
    bt = next(m for m in ms if 'bordeaux' in m.name)
    for m in ms:
        if m is not bt: bpy.data.objects.remove(m)
    bt.parent = None; mwb = bt.matrix_world.copy(); bt.matrix_world = mwb
    bpy.data.objects.remove(root)
    bb = [mwb @ Vector(c) for c in bt.bound_box]; c = sum(bb, Vector()) / 8; zmin = min(v.z for v in bb)
    bt.data.transform(Matrix.Translation(-(bt.matrix_world.inverted() @ Vector((c.x, c.y, zmin)))))
    bt.matrix_world = Matrix.Diagonal((0.88, 0.88, 0.88, 1)); bt.parent = P['linda_mug']
    bt.location = (0, 0, -P['linda_mug']['H'] * 0.45 + 0.012)
    bt['top'] = max(v.z for v in bb) - zmin
    st = props.straw('linda_straw', 0.26); st.parent = P['linda_mug']
    st.location = (0.004, 0.0, bt.location.z + bt['top'] * 0.88 - 0.05); st.rotation_euler = (0.0, 0.12, 0)
    P['linda_straw'] = st
    P['chad_can'] = props.can('chad_can')
    P['earl_cig'] = props.cigarette('earl_cig', os.environ['PH'])
    for k in ['chad', 'earl', 'pam', 'linda']:
        P[k + '_phone'] = props.phone(k + '_phone', screen(k))
        CONST_MATS.append(P[k + '_phone']['screen_mat'])
    CONST_MATS.append(P['earl_cig']['ember'])
    # Chad's cap, worn backwards, on his head bone
    cap = props.cap('chad_cap'); fit_to_head(A['chad'], cap, back=True); P['chad_cap'] = cap
    glasses_off_skin(A['chad'], 'frankyaye_glasses_library_male'); glasses_off_skin(A['pam'], 'spamrakuen_tbm_glasses_frames_01')
    # Earl's oxygen: tank by his chair, cannula on his face
    P['oxy'] = props.oxygen('oxy')
    cannula(A['earl'], P)
    return P

def place_oxygen(P, seat, A):
    M = Matrix.Translation((seat['x'], seat['y'], 0)) @ Matrix.Rotation(seat['face'], 4, 'Z')
    P['oxy'].matrix_world = M @ Matrix.Translation((0.34, 0.16, 0)) @ Matrix.Rotation(0.4, 4, 'Z')     # tight beside his chair
    bpy.context.view_layer.update()
    valve = P['oxy'].matrix_world @ Vector((0, 0.0, 0.7))
    P['valve'] = valve
    line = props.tube_curve('cannula_line', [valve + Vector((0, 0, 0.0)), valve + Vector((0, 0, 0.25)), valve + Vector((-0.1, -0.1, 0.5)), valve + Vector((-0.2, -0.1, 0.7)), valve + Vector((-0.3, -0.1, 0.8))], r=0.0024, m=P['cannula_mat'])
    for bp in line.data.splines[0].bezier_points: bp.handle_left_type = bp.handle_right_type = 'FREE'
    P['cannula_line'] = line
    # the chin point in head-bone space
    pass
    return P


def screen(k):
    """A phone screen image: a trading app with a launch alert (Pam's: her dev wallet)."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = 540, 1120; im = Image.new('RGB', (w, h), (8, 10, 14)); d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(props.FONT_B, 40); fs = ImageFont.truetype(props.FONT_B, 26)
    d.rectangle((0, 0, w, 70), fill=(14, 16, 22)); d.text((24, 16), '9:41', font=fs, fill=(230, 230, 230))
    d.rounded_rectangle((20, 100, w - 20, 230), 26, fill=(32, 34, 42))
    d.rounded_rectangle((40, 122, 120, 202), 18, fill=(150, 60, 230)); d.text((150, 120), 'LAUNCHPAD', font=fs, fill=(170, 170, 180))
    d.text((150, 156), '$ROYALE just launched', font=fs, fill=(255, 255, 255))
    pts = [(30 + i * 24, 900 - (i ** 1.6) * 6 - random.Random(i).uniform(0, 30)) for i in range(21)]
    d.line(pts, fill=(43, 255, 106), width=8)
    d.text((40, 300), '$ROYALE', font=fb, fill=(200, 255, 90)); d.text((40, 360), '+2,413,907%' if k == 'pam' else '0.0001', font=fb, fill=(43, 255, 106))
    d.rounded_rectangle((40, 980, w - 40, 1070), 22, fill=(43, 200, 90)); d.text((w / 2 - 50, 1005), 'BUY', font=fb, fill=(0, 0, 0))
    p = f"{os.environ.get('DA_TEX', '/tmp')}/screen_{k}.png"; im.save(p); return p


def body_points(actor):
    """Landmarks on the actor's real (morphed) head, read from the evaluated body mesh at rest."""
    b = actor.body
    saved = [(m, m.show_viewport) for m in b.modifiers]
    for m, _ in saved:
        if m.type != 'ARMATURE': m.show_viewport = False
    bpy.context.view_layer.update()
    ev = b.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    V = [b.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    for m, sv in saved: m.show_viewport = sv
    rest = actor.rest
    hz = rest['head'].translation.z; hy = rest['head'].translation.y
    headv = [v for v in V if v.z > hz - 0.12]
    top = max(headv, key=lambda v: v.z)
    nose = min((v for v in headv if abs(v.x) < 0.012 and v.z < hz + 0.06), key=lambda v: v.y)
    earL = max((v for v in headv if abs(v.z - (hz + 0.02)) < 0.03), key=lambda v: v.x)
    earR = min((v for v in headv if abs(v.z - (hz + 0.02)) < 0.03), key=lambda v: v.x)
    chin = min((v for v in headv if abs(v.x) < 0.012 and v.z < nose.z - 0.05), key=lambda v: v.z + v.y * 0.5)
    back = max((v for v in headv if abs(v.x) < 0.02 and abs(v.z - top.z + 0.07) < 0.02), key=lambda v: v.y)
    front = min((v for v in headv if abs(v.x) < 0.02 and abs(v.z - top.z + 0.07) < 0.02), key=lambda v: v.y)
    return dict(top=top, nose=nose, earL=earL, earR=earR, chin=chin, back=back, front=front)


def bone_parent(o, actor, bone):
    """Parent o to a bone, keeping its current world transform (rig at rest)."""
    mw = o.matrix_world.copy()
    o.parent = actor.rig; o.parent_type = 'BONE'; o.parent_bone = bone
    bpy.context.view_layer.update()
    o.matrix_world = mw


def fit_to_head(actor, cap, back=True):
    """Fit the cap to the skull: rim just above the brow, crown a hair's thickness over the scalp.
    Hair that would poke through the cap is then masked away."""
    L = body_points(actor)
    top = L['top'].z
    width = L['earL'].x - L['earR'].x; length = L['back'].y - L['front'].y
    s = max(width / 0.196, length / 0.224) * 1.04
    eye_z = actor.rest['eye.L'].translation.z
    rim = eye_z + 0.045
    zs = (top + 0.012 - rim) / (0.085 * s)
    cap.scale = (s, s, s * zs)
    cap.location = (0.0, (L['back'].y + L['front'].y) / 2 + 0.006, rim)
    cap.rotation_euler = (math.radians(-8), 0, 0)
    bpy.context.view_layer.update()
    crown = [o for o in cap.children if o.name.endswith('_crown') or o.name.endswith('_cuff')]
    hair = [o for n, o in actor.parts.items() if n == humans.CAST[actor.name]['hair']]
    for h in hair:
        print('CAP hair masked', humans.mask_under(h, crown, reach=0.08, inside=0.08))
    bone_parent(cap, actor, 'head')


def cannula(actor, P):
    L = body_points(actor); n = L['nose']
    tube = props.mat('cannula', (0.78, 0.9, 0.95), rough=0.15, trans=0.6, ior=1.4)
    pts = []
    for sx in (1, -1):
        ear = L['earL'] if sx > 0 else L['earR']
        pts.append([Vector((sx * 0.006, n.y + 0.012, n.z - 0.013)), Vector((sx * 0.03, n.y + 0.02, n.z - 0.02)),
                    Vector((sx * 0.065, n.y + 0.055, n.z - 0.03)), Vector((ear.x + sx * 0.004, ear.y - 0.012, ear.z + 0.035)),
                    Vector((ear.x + sx * 0.002, ear.y + 0.025, ear.z + 0.0)), Vector((ear.x - sx * 0.008, ear.y + 0.012, ear.z - 0.05)),
                    Vector((ear.x * 0.75, ear.y - 0.03, ear.z - 0.085)), Vector((sx * 0.035, L['chin'].y + 0.012, L['chin'].z + 0.006)),
                    Vector((0.0, L['chin'].y - 0.012, L['chin'].z - 0.008))])
    path = pts[0] + list(reversed(pts[1]))[1:]          # nostril L ... chin front ... nostril R
    path = outside_skin(actor, path, gap=0.007, steps=3)
    loop = props.tube_curve('cannula_face_curve', path, r=0.0021, m=tube)
    skin_to_body(actor, loop, 'cannula_face', gap=0.0025)
    # a hook point under the chin follows the head; the line drops to the tank beside the chair
    hk = bpy.data.objects.new('cannula_hook', None); bpy.context.scene.collection.objects.link(hk)
    hk.location = Vector((0.0, L['chin'].y - 0.012, L['chin'].z - 0.008)); bone_parent(hk, actor, 'head')
    P['cannula_hook'] = hk; P['cannula_mat'] = tube
    P['chin_local'] = actor.rest['head'].inverted() @ Vector((0.0, L['chin'].y - 0.022, L['chin'].z - 0.018))   # clear of the jaw when he talks


# ================================================================== the actor solve
GRIP = {}
def curl_Q(actor, s, kind, Q):
    """Finger curls (radians per joint) for a hand shape."""
    shapes = {
        'rest': dict(t=(0.15, 0.1, 0.1), i=(0.25, 0.3, 0.2), m=(0.3, 0.35, 0.25), r=(0.35, 0.4, 0.3), p=(0.4, 0.45, 0.3)),
        'grip': dict(t=(0.35, 0.4, 0.3), i=(0.75, 0.8, 0.5), m=(0.8, 0.85, 0.55), r=(0.85, 0.85, 0.55), p=(0.9, 0.85, 0.55)),
        'cig':  dict(t=(0.25, 0.2, 0.15), i=(0.25, 0.25, 0.15), m=(0.3, 0.3, 0.2), r=(0.9, 1.0, 0.7), p=(1.0, 1.0, 0.7)),
        'phone': dict(t=(0.2, 0.15, 0.1), i=(0.6, 0.5, 0.3), m=(0.7, 0.55, 0.3), r=(0.75, 0.6, 0.35), p=(0.8, 0.6, 0.35)),
        'flat': dict(t=(0.05, 0.05, 0.05), i=(0.05, 0.08, 0.05), m=(0.05, 0.08, 0.05), r=(0.08, 0.1, 0.05), p=(0.1, 0.12, 0.05)),
        'fist': dict(t=(0.5, 0.6, 0.5), i=(1.2, 1.3, 0.9), m=(1.25, 1.3, 0.9), r=(1.3, 1.3, 0.9), p=(1.35, 1.3, 0.9)),
    }
    sh = shapes[kind]
    for fi, key in enumerate('timrp', start=1):
        for j in range(1, 4):
            bn = f'finger{fi}-{j}.{s}'
            if bn in actor.curl_axis:
                Q[bn] = actor.local_q(bn, rigctl.qrot(actor.curl_axis[bn], sh[key][j - 1]))


SEAT_FIX = {}
HAND_FIX = {}
NEET_FIX = (0.0, 0.0)
SEAT_S = {}
def seated_basics(a):
    hipc = (a.hip['L'] + a.hip['R']) / 2
    dy, dz = SEAT_FIX.get(a.name, (0.0, 0.0))
    return Vector((0, 0.035 - hipc.y - dy, 0.5 * SEAT_S.get(a.name, room.CHAIR_S) + 0.095 - hipc.z + dz))


def finger_Q(a, s, shape):
    Q = {}
    if shape == 'grip': Q.update(grips.curlQ(a, s, a.G['hold'][0]))
    elif shape == 'phone': Q.update(grips.curlQ(a, s, a.G['phone'][0]))
    elif shape == 'cig': Q.update(grips.curlQ(a, s, a.G['cig'][0], a.G['cig'][1]))
    else: curl_Q(a, s, shape, Q)
    return Q


def set_fingers(a, s, shape, Q):
    if isinstance(shape, tuple):
        _, s0, s1, w = shape
        A = finger_Q(a, s, s0) if not isinstance(s0, tuple) else finger_Q(a, s, s0[2]); B = finger_Q(a, s, s1)
        for bn in set(A) | set(B):
            Q[bn] = A.get(bn, Quaternion()).slerp(B.get(bn, Quaternion()), w)
    else:
        Q.update(finger_Q(a, s, shape))


def run_path(k, seat, t):
    """Position and heading on the stampede route; visible until through the door."""
    t0 = RUN[k]; t1 = ARRIVE[k]
    u = clamp((t - t0 - 0.22) / (t1 - t0 - 0.22))
    pts = [Vector((seat['x'], seat['y'], 0))] + [Vector((x, y, 0)) for x, y in LANE[k]] + [Vector((4.1, -1.2, 0)), EXIT + Vector((0.8, 0, 0))]
    seg = [(b - a).length for a, b in zip(pts, pts[1:])]; tot = sum(seg)
    d = ease(u) * (tot - seg[-1]) + max(0.0, (t - t1)) * 4.5   # keep running through the doorway
    d = min(d, tot)
    acc = 0
    for a, b, L in zip(pts, pts[1:], seg):
        if acc + L >= d or b is pts[-1]:
            k2 = clamp((d - acc) / L); p = a.lerp(b, k2); dirv = (b - a).normalized(); break
        acc += L
    face0 = seat['face']; face1 = math.atan2(dirv.x, -dirv.y)
    df = math.atan2(math.sin(face1 - face0), math.cos(face1 - face0))
    face = face0 + df * clamp((t - t0) / 0.35)
    return p, face, p.x < 4.55


def solve_actor(a, k, t, f, seat, st, HEADS, P, K):
    SEATM = Matrix.Translation((seat['x'], seat['y'], 0)) @ Matrix.Rotation(seat['face'], 4, 'Z')
    mw = SEATM.copy()
    root_loc = seated_basics(a)
    Q = {}
    spk = speaker(t)
    sx = {'L': 1, 'R': -1}
    running = k in RUN and t >= RUN[k]
    vis = True
    # ---------------- gaze target
    target = HEADS[spk](t) if spk and spk != k else None
    yawT, pitchT = 0.0, 0.0
    hp = HEADS[k](t)
    if target is not None:
        dv = target - hp; ang = math.atan2(dv.x, -dv.y) - seat['face']; ang = math.atan2(math.sin(ang), math.cos(ang))
        yawT = clamp(ang, -1.0, 1.0); pitchT = clamp(-math.atan2(dv.z, Vector((dv.x, dv.y)).length), -0.3, 0.3)
    elif spk == k:
        yawT = 0.0
    phone_up = 0.0
    if k == 'chad': phone_up = max(phone_up, pulse(t, 32.25, 34.0, 0.25))
    if t < 39.45: phone_up = max(phone_up, ramp(t, 34.45, 34.9))
    if k == 'pam': phone_up = max(phone_up, ramp(t, 34.45, 34.9) * (1 - ramp(t, 36.6, 37.0)), ramp(t, 42.0, 42.5))
    lit = (34.4 < t < 39.45) or (k == 'chad' and 32.25 < t < 34.0) or (k == 'pam' and t > 42.0)
    if 34.4 < t < 36.7 and k != 'pam' or (k == 'pam' and 34.4 < t < 36.6):
        pitchT = 0.42; yawT = 0.0
    if win(t, 35.2, 36.7) and k != 'pam':
        yawT = math.sin((t - 35.2) * 2.2 + ORDER.index(k)) * 0.8; pitchT = 0.15
    if k == 'pam' and t > 42.0: pitchT = 0.35 * ramp(t, 42.0, 42.4); yawT = 0.0
    if k == 'pam' and t > 44.6: pitchT = 0.35 - 0.3 * ramp(t, 45.6, 46.2)    # looks up to us for the last line
    st['yaw'] = lerp(st['yaw'], yawT, 0.14); st['pitch'] = lerp(st['pitch'], pitchT, 0.14)
    # ---------------- body
    breathe = math.sin(t * 2.2 + ORDER.index(k)) * 0.012
    lean = math.radians(5) + breathe
    sb = 0.0
    if running:
        u = t - RUN[k]; sb = clamp(u / 0.22)
        p, face, vis = run_path(k, seat, t)
        mw = Matrix.Translation((p.x, p.y, 0)) @ Matrix.Rotation(face, 4, 'Z')
        stand = Vector((0, 0, 0)); bob = abs(math.sin(u * 11)) * 0.05 * clamp((u - 0.22) / 0.2)
        root_loc = root_loc.lerp(stand + Vector((0, -0.04, -0.05 + bob)), sb)
        lean = lerp(lean, math.radians(16), sb)
        K.add(a.rig, 'hide_render', 0, f, 0 if vis else 1)
        for o in a.rig.children: K.add(o, 'hide_render', 0, f, 0 if vis else 1)
    else:
        K.add(a.rig, 'hide_render', 0, f, 0)
        for o in a.rig.children: K.add(o, 'hide_render', 0, f, 0)
    for b, w in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), lean * w))
    talkv = talk(k, t)
    nod = math.sin(t * 9 + ORDER.index(k)) * 0.03 * (talkv > 0.1)
    yaw, pitch = st['yaw'], st['pitch'] + nod
    for b, w in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)):
        q = rigctl.qrot((0, 0, 1), yaw * w) @ rigctl.qrot((1, 0, 0), (pitch - lean * 0.9) * w)
        Q[b] = a.local_q(b, q)
    # eyes: the rest of the turn
    for s in 'LR':
        Q[f'eye.{s}'] = a.local_q(f'eye.{s}', rigctl.qrot((0, 0, 1), (yawT - yaw) * 0.8))
    # ---------------- face: blink, jaw, visemes
    off = {'pam': 0.3, 'linda': 2.2, 'earl': 0.7, 'chad': 1.6}[k]
    blink = 1.0 if ((t + off) % 3.7) < 0.12 else 0.0
    if 34.4 < t < 36.7 or running: blink = 0.0
    lid = 0.55 * blink + (0.18 if k == 'earl' else 0.0) - (0.15 if (34.4 < t < 36.7 or running) else 0.0)
    for s in 'LR':
        Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), lid))
        Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink))
    jaw = talkv * 0.11 + (0.14 if running else 0.0)
    Q['jaw'] = a.local_q('jaw', rigctl.qrot((1, 0, 0), jaw))
    ph = math.sin(t * 13.0 + off) * 0.5 + 0.5
    shape = {'v_aa': talkv * 0.38, 'v_ow': talkv * 0.3 * ph, 'v_ee': talkv * 0.25 * (1 - ph), 'v_mm': 0.25 if (0 < talkv < 0.08) else 0.0, 'v_ff': 0.0}
    if k == 'pam' and talkv < 0.05: shape['v_ee'] = 0.12          # a pleasant host's half smile
    if k == 'chad' and win(t, 29.6, 29.95): shape['v_mm'] = 0.6     # the sniff
    # ---------------- feet
    feet, poles = {}, {}
    for s in 'LR':
        hip = a.hip[s] + root_loc
        ank = Vector((hip.x + sx[s] * 0.05, -(a.thigh + 0.08), 0.085))
        if (k, s) == ('linda', 'L'): ank += Vector((-0.17, 0.12, 0))     # her foot tucked in, clear of NEET's
        Fm = a.rest[f'foot.{s}'].copy()
        if k == 'chad' and not running:   # the jittery leg
            ank.z += max(0.0, math.sin(t * 34 + (0 if s == 'L' else 2.0))) * 0.03
        if running:
            u = t - RUN[k]; ph2 = u * 11.0 + (0 if s == 'L' else math.pi)
            sw = math.sin(ph2); lift = max(0.0, math.cos(ph2)) * 0.2
            standing = Vector((a.ankle[s].x + sx[s] * 0.02, a.ankle[s].y - 0.02 + sw * 0.38 * clamp((u - 0.22) / 0.2), a.ankle[s].z + lift * clamp((u - 0.22) / 0.2)))
            ank = ank.lerp(standing, sb)
        Fm.translation = ank
        feet['foot', s] = mw @ Fm
        poles['foot', s] = mw @ Vector((hip.x + sx[s] * 0.08, -1.2, 0.55))
    # ---------------- hands
    head = a.fk(Q, root_loc, 'head')
    mouth = head @ (a.rest['head'].inverted() @ a.mouth); nose = head @ (a.rest['head'].inverted() @ a.nose)
    lip = head @ (a.rest['head'].inverted() @ getattr(a, 'lip', a.mouth))
    eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
    fwd = head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, -1, 0)))
    up = head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, 0, 1)))
    hands = {}; shapes = {}; place = {}
    MOUTH[k] = mw @ mouth; MOUTH[k + '_fwd'] = mw.to_3x3() @ fwd
    def lap(s, holding=None):
        hf = HAND_FIX.get((k, s), Vector()); hip = a.hip[s] + root_loc + Vector((sx[s] * hf.x, hf.y, hf.z))
        knee = hip + Vector((0, -a.thigh * 0.95, -0.06))
        if holding:
            pos = hip.lerp(knee, 0.6) + Vector((sx[s] * 0.05, -0.02, 0.12))   # palm at the thigh's outer side, the cup over the thigh
            return a.frame(pos, (sx[s] * 0.25, -1, -0.35), (-sx[s], 0, 0.0))
        # rest on the thigh as far toward the knee as the arm comfortably reaches
        sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation; reach = (a.uarm + a.farm) * 0.95
        for u in [0.62 - 0.04 * i for i in range(9)]:
            pos = hip.lerp(knee, u) + Vector((-sx[s] * 0.01, 0, 0.085))
            F = a.frame(pos, (-sx[s] * 0.15, -1, -0.15), (sx[s] * 0.2, 0, -1))
            if (a.hand_matrix_for_palm(s, F).translation - sh).length <= reach: break
        return F
    G = a.G
    def phone_frame(s):
        flat = Vector((0, -1, 0)); zup = Vector((0, 0, 1))          # from the body, not the gaze: looking down doesn't pull it into the chest
        tgt = eyes + flat * 0.37 - zup * 0.22
        n = (eyes - tgt).normalized(); upp = (zup - n * zup.dot(n)).normalized()
        X = upp * a.idx_sign[s]; Y = n.cross(X)
        F = a.frame(Vector(), Y, n)
        F.translation = tgt - F.to_3x3() @ (G['phone'][1].translation + Vector((0, 0, 0)))
        return F
    def cyl_grip(s, palm, R):
        """Prop matrix for the solved grip (fingers touching, never inside)."""
        return palm @ G['hold'][1]
    def palm_from_cyl(s, M, R):
        return M @ G['hold'][1].inverted()
    def blend(F0, F1, k2, arc=Vector((0, -0.12, 0))):
        p = F0.translation.lerp(F1.translation, k2) + arc * math.sin(math.pi * k2)
        q = F0.to_quaternion().slerp(F1.to_quaternion(), k2)
        M = q.to_matrix().to_4x4(); M.translation = p; return M
    # defaults
    for s in 'LR':
        hands[s] = lap(s); shapes[s] = 'flat'
    # who holds what (in which hand)
    hold = {'pam': ('L', 'pam_mug'), 'linda': ('L', 'linda_mug'), 'earl': ('R', 'earl_cig'), 'chad': ('R', 'chad_can')}[k]
    phand = 'R' if k in ('pam', 'linda') else 'L'
    hs, pk = hold
    if pk.endswith('mug') or pk.endswith('can'):
        R = P[pk]['R']
        F = lap(hs, True); hands[hs] = F; shapes[hs] = 'grip'
        Mprop = cyl_grip(hs, F, R)
        # sips: rim (or straw) to the lips
        sip = 0.0
        if k == 'linda': sip = max(pulse(t, 19.95, 20.65, 0.25), pulse(t, 8.0, 8.6, 0.2))
        if k == 'pam': sip = pulse(t, 42.5, 43.3, 0.25)
        if sip > 0.001:
            zl = Mprop.to_3x3().col[2]
            if k == 'linda':
                tilt = 0.42; st_ = P['linda_straw']          # leaned toward her face so the mug stays off her chest
                tip_local = st_.location + st_.rotation_euler.to_matrix() @ Vector((0, 0, 0.26))
            else:
                tilt = 0.85; H = P[pk]['H']
            z_m = (up * math.cos(tilt) - fwd * math.sin(tilt)).normalized()
            xx = Mprop.to_3x3().col[0]; xx = (xx - z_m * xx.dot(z_m)).normalized(); yy = z_m.cross(xx)
            Rm = Matrix((xx, yy, z_m)).transposed()
            lip = mouth + fwd * 0.006
            if k == 'linda':
                c = lip - Rm @ tip_local
            else:
                fp = (fwd - z_m * fwd.dot(z_m)).normalized()
                c = lip - up * 0.006 - z_m * (H * 0.55) + fp * (R - 0.003)
            Mm = Rm.to_4x4(); Mm.translation = c
            Fm = palm_from_cyl(hs, Mm, R)
            hands[hs] = blend(F, Fm, sip); Mprop = cyl_grip(hs, hands[hs], R)
        place[pk] = Mprop
    if pk == 'earl_cig':
        F = lap('R', True); shapes['R'] = 'cig'      # resting thumb-up, so the cigarette points outward
        hands['R'] = F
        def cig_in_palm(F):
            return F @ G['cig'][2]
        def cig_at_lips(droop=0.35):
            z = (fwd * math.cos(droop) - up * math.sin(droop)).normalized(); y = up - z * up.dot(z); x = y.cross(z)
            # the filter's end pressed 4 mm between his lips (the filter end is 11 mm behind the origin)
            M = Matrix((x.normalized(), y.normalized(), z)).transposed().to_4x4(); M.translation = lip + z * 0.005; return M
        def palm_for_cig(M):
            return M @ G['cig'][2].inverted()
        drag = max(pulse(t, 13.0, 13.8, 0.3), pulse(t, 25.1, 26.0, 0.3))
        place_in = pulse(t, 22.15, 22.8, 0.25)            # puts it in his mouth (off camera)
        in_mouth = win(t, 22.5, 25.4)
        Mlips = cig_at_lips(0.62 if in_mouth else 0.15)       # hanging from his lips it droops under its own weight
        Fl = palm_for_cig(Mlips)
        k2 = max(drag, place_in)
        hands['R'] = blend(F, Fl, k2, Vector((0.06, -0.12, 0)))
        place['earl_cig'] = Mlips if in_mouth else cig_in_palm(hands['R'])
        if in_mouth or drag > 0.6:
            shape['v_mm'] = max(shape['v_mm'], 0.45 if drag > 0.6 else 0.35); shape['v_aa'] *= 0.4    # lips closed round the filter
    # phones
    pphone = P[k + '_phone']
    if phone_up > 0.01 and not running:
        Fp = phone_frame(phand)
        hands[phand] = blend(hands[phand], Fp, clamp(phone_up)); shapes[phand] = ('mix', shapes[phand], 'phone', clamp(phone_up * 1.5))
        place[k + '_phone'] = hands[phand] @ G['phone'][1]
    else:
        place[k + '_phone'] = None
    # Chad wipes his nose (left hand), Pam and Linda clap (right hand pats the mug hand)
    if k == 'chad':
        wipe = pulse(t, 29.62, 30.1, 0.12)
        if wipe > 0.01:
            pos = nose - up * 0.03 + fwd * 0.07 + Vector((0.02, 0, 0)) * math.sin((t - 29.62) * 18)
            Fw = a.frame(pos, (-0.3, 0, 1), (0, 0, -1) if False else (-fwd).normalized())
            hands['L'] = blend(hands['L'], Fw, wipe); shapes['L'] = 'fist'
    if k in ('pam', 'linda') and win(t, 15.75, 16.65):
        # applause with the free hand: two slaps on her own thigh (the other hand holds the mug)
        c = max(pulse(t, 15.85, 16.08, 0.08), pulse(t, 16.25, 16.48, 0.08))
        up_ = ramp(t, 15.75, 15.85) * (1 - ramp(t, 16.55, 16.65))
        base_ = hands['R'].copy(); base_.translation = base_.translation + Vector((0, 0, 0.09 * up_ * (1 - c)))
        hands['R'] = base_; shapes['R'] = 'flat'
    if running:
        u = t - RUN[k]; swing = math.sin(u * 11.0) * clamp((u - 0.22) / 0.2)
        for s in 'LR':
            sh = a.shoulder[s] + root_loc
            sg = (swing if s == 'L' else -swing) * (0.4 if s == hold[0] else 1.0)
            pos = sh + Vector((sx[s] * (0.2 if s == hold[0] else 0.12), -0.18 - sg * 0.18 - (0.12 if s == hold[0] else 0), -0.38 + max(0, -sg) * 0.1 + max(0, sg) * 0.12))
            Fr = a.frame(pos, (0, -0.6, 0.6), (-sx[s], 0, 0))
            keepS = shapes[s]
            hands[s] = blend(hands[s], Fr, sb, Vector()); shapes[s] = keepS
    # ---------------- keep every hand within arm's reach (props move with their hand)
    reach = (a.uarm + a.farm) * 0.985
    attach = {'pam_mug': 'L', 'linda_mug': 'L', 'chad_can': 'R', 'earl_cig': 'R', k + '_phone': phand}
    for s in 'LR':
        wpos = a.hand_matrix_for_palm(s, hands[s]).translation
        sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation
        dv = wpos - sh
        if dv.length > reach:
            delta = dv.normalized() * (reach - dv.length)
            hands[s] = Matrix.Translation(delta) @ hands[s]
            for pk3, side in attach.items():
                if side == s and place.get(pk3) is not None and not (pk3 == 'earl_cig' and win(t, 22.5, 25.4)):
                    place[pk3] = Matrix.Translation(delta) @ place[pk3]
    # ---------------- key it all
    for s in 'LR':
        set_fingers(a, s, shapes[s], Q)
    H = {('hand', s): mw @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
    tuck = {'L': 0.0, 'R': 0.0}
    tuck[phand] = clamp(phone_up)
    for s in 'LR':
        pv = Vector((sx[s] * 0.7, 0.45, -0.45)).lerp(Vector((sx[s] * 0.22, 0.35, -0.75)), tuck[s])
        poles['hand', s] = mw @ (a.shoulder[s] + root_loc + pv)
    a.key_pose(f, mw, Q, root_loc, H, feet, poles, shape)
    # props follow the hands (re-derived from the posed hand, which the IK matches exactly)
    for pk2, M in place.items():
        ob = P[pk2]
        if running and not vis: M = None
        if M is None:
            K.add(ob, 'hide_render', 0, f, 1); continue
        K.add(ob, 'hide_render', 0, f, 0)
        if pk2 in ('pam_mug', 'linda_mug', 'chad_can', 'earl_cig') or pk2.endswith('_phone'):
            if running and pk2 in ('earl_cig', 'chad_can', 'linda_mug'):
                s = hold[0]
                if pk2 == 'earl_cig': M = cig_in_palm(hands['R'])
                else: M = cyl_grip(s, hands[s], P[pk2]['R'])
        W = mw @ M
        loc, q = W.translation, W.to_quaternion()
        ob.rotation_mode = 'QUATERNION'
        for i in range(3): K.add(ob, 'location', i, f, loc[i])
        for i in range(4): K.add(ob, 'rotation_quaternion', i, f, q[i])
    if k == 'earl':
        cu = P['cannula_line'].data; chin = mw @ (head @ P['chin_local'])
        side = (mw.to_3x3() @ Vector((1, 0, 0))); v = P['valve']
        # down in front of his chest, round the outside of his left knee, to the tank
        R3 = mw.to_3x3(); seat_o = mw.translation
        under = chin + R3 @ Vector((0.02, -0.15, -0.12))
        knee_out = seat_o + R3 @ Vector((0.30, -0.30, 0.66))
        cut = running and t > RUN['earl'] + 0.15
        pts = [v, v + Vector((0, 0, 0.22)), knee_out, under, chin] if not cut else [v, v + Vector((0, 0, 0.12)), v + Vector((0.05, -0.15, 0.0)), v + Vector((0.1, -0.25, -0.3)), v + Vector((0.12, -0.3, -0.65))]
        # handles keyed too (Catmull-Rom tangents): auto handles don't update during playback
        for j, p in enumerate(pts):
            tan = (pts[min(j + 1, len(pts) - 1)] - pts[max(j - 1, 0)]) * (0.5 if 0 < j < len(pts) - 1 else 1.0)
            for i in range(3):
                K.add(cu, f'splines[0].bezier_points[{j}].co', i, f, p[i])
                K.add(cu, f'splines[0].bezier_points[{j}].handle_left', i, f, (p - tan / 3)[i])
                K.add(cu, f'splines[0].bezier_points[{j}].handle_right', i, f, (p + tan / 3)[i])
        em = bpy.data.materials[P['earl_cig']['ember']]
        glow = 3.0 + pulse(t, 25.3, 26.0, 0.2) * 10 + pulse(t, 13.2, 13.7, 0.15) * 10
        K.add(em.node_tree, em_path(em), 0, f, glow)
    sm = bpy.data.materials[pphone['screen_mat']]
    K.add(sm.node_tree, em_path(sm), 0, f, 3.0 if (lit and place[k + '_phone'] is not None) else 0.0)
    gl = bpy.data.objects[pphone['glow']]
    K.add(gl.data, 'energy', 0, f, (1.2 if k != 'pam' else 0.9) if (lit and place[k + '_phone'] is not None) else 0.0)


def a_axes(fwd, up):
    """A rotation whose -Y is `fwd` (toward the camera side of a face) and Z is `up`."""
    z = up.normalized(); y = -(fwd - z * fwd.dot(z)).normalized(); x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()


# ================================================================== heads (for gazes and singles)
def head_positions(A, NEET, SEAT):
    out = {}
    for k, a in A.items():
        Q = {}; rl = seated_basics(a)
        hm = a.fk(Q, rl, 'head'); p = hm @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.04, 0.06))))
        seat = SEAT[k]; M = Matrix.Translation((seat['x'], seat['y'], 0)) @ Matrix.Rotation(seat['face'], 4, 'Z')
        w = M @ p
        out[k] = (lambda w: (lambda t: w.copy()))(w)
    # NEET: sample his real head through the clip schedule, then smooth it
    rig = NEET['rig']; root = NEET['root']; sc = bpy.context.scene
    hb = rig.pose.bones.get('mixamorig:Head')
    pts = {}
    hidden = [o for o in bpy.data.objects if o.type in ('MESH', 'CURVE') and o is not NEET['mesh'] and not o.hide_viewport]
    for o in hidden: o.hide_viewport = True
    for f in range(1, NF + 1, 3):
        t = T(f)
        neet_frame(NEET, t, f, SEAT['gary'], _Direct())
        sc.frame_set(f)
        pts[f] = (rig.matrix_world @ hb.head) + Vector((0, 0, 0.05))
    for o in hidden: o.hide_viewport = False
    fs = sorted(pts)
    def neet_head(t):
        f = clamp(fr(t), 1, fs[-1]); i = max(0, min(len(fs) - 2, int((f - 1) // 3)))
        a0, a1 = fs[i], fs[i + 1]; k2 = clamp((f - a0) / (a1 - a0))
        # light smoothing: average neighbours
        acc = Vector(); n = 0
        for j in range(max(0, i - 3), min(len(fs), i + 5)):
            acc += pts[fs[j]]; n += 1
        return (pts[a0].lerp(pts[a1], k2)) * 0.5 + (acc / n) * 0.5
    out['gary'] = neet_head; out['neet_ext'] = neet_head
    return out


class _Direct:
    """A Keys stand-in that sets values immediately (for sampling NEET before his keys exist)."""
    def add(self, idb, path, idx, frame, val):
        if path == 'location': idb.location[idx] = val
        elif path == 'hide_render': idb.hide_render = bool(val)
        elif path == 'rotation_euler': idb.rotation_euler[idx] = val


# ================================================================== camera, lights, set pieces
def make_camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24; cd.dof.use_dof = True
    cam.rotation_mode = 'QUATERNION'
    return cam


def b3(v):
    """three.js (x, y up, z toward camera) -> Blender."""
    return Vector((v[0], -v[2], v[1]))


def camera(cam, t, f, HEADS, SEAT, K):
    def shot(pos, tgt, fov, focus, fstop):
        pos = Vector(pos); tgt = Vector(tgt)
        q = (tgt - pos).to_track_quat('-Z', 'Y')
        return pos, q, fov, focus, fstop
    def single(k, side=0.0, dist=2.0, fov=32, up=0.0):
        s = SEAT[k]; h = HEADS[k](t); a = s['face'] + side
        p = Vector((h.x + math.sin(a) * dist, h.y - math.cos(a) * dist, h.z + 0.02 + up))
        return shot(p, (h.x, h.y, h.z - 0.2 + up * 0.5), fov, dist, 2.8)
    hd = Vector((math.sin(t * 1.3) * 0.008 + math.sin(t * 3.1) * 0.004, 0, math.sin(t * 1.7 + 1) * 0.006))
    L3 = lambda a, b, k: [lerp(x, y, k) for x, y in zip(a, b)]
    if t < 3.2:
        k = ramp(t, 0, 3.2); r = shot(b3(L3([62.4, 1.25, 5.9], [61.9, 1.35, 4.6], k)), b3([60.5, 1.55, 0.9]), 40, lerp(3.4, 4.2, k), 4.0)
    elif t < 7.2:
        k = ramp(t, 3.2, 7.2); r = shot(b3(L3([0, 1.8, 6.6], [0, 1.7, 5.7], k)), b3([0, 1.0, -0.6]), 38, 6.0, 5.6)
    elif t < 9.25: r = single('gary', -0.25, 2.5, 32, 0.0)
    elif t < 10.9: r = shot(b3([0, 1.75, 6.0]), b3([0, 1.0, -0.4]), 38, 6.0, 5.6)
    elif t < 13.5: r = single('gary', -0.2, 1.9, 30, 0.0)
    elif t < 15.3: r = single('pam', 0.1, 2.0, 30)
    elif t < 16.8: r = single('gary', -0.3, 2.7, 34, -0.1)
    elif t < 22.8:
        r = single('linda', -0.3, 1.55, 30, 0.0) if win(t, 19.9, 20.75) else single('linda', -0.35, 2.1 - ramp(t, 16.8, 22.8) * 0.35, 30)
    elif t < 29.1:
        r = single('earl', 0.3, 1.1, 30, 0.12) if win(t, 25.0, 26.4) else single('earl', 0.45, 2.2 - ramp(t, 22.8, 29.1) * 0.45, 30)
    elif t < 29.7: r = single('gary', -0.15, 2.3, 32, 0.1)
    elif t < 34.3: r = single('chad', 0.45, 2.0, 30)
    elif t < 36.7:
        k = ramp(t, 34.3, 36.7); r = shot(b3(L3([0, 1.75, 5.9], [0, 1.6, 5.1], k)), b3([0, 1.0, -0.3]), 38, 5.5, 5.6)
    elif t < 39.4: r = single('pam', 0.05, 1.8, 30)
    elif t < 41.6: r = shot(b3([0.6, 1.5, 4.8]), b3([1.4, 0.9, 0.2]), 42, 4.5, 5.6)
    elif t < 42.4: r = shot(b3([0, 1.4, 3.8]), b3([0, 1.0, -1.7]), 34, 3.9, 4.0)
    elif t < 44.6: r = single('pam', 0.0, 1.9, 30)
    else:
        k = ramp(t, 44.6, 48); r = single('pam', 0.0, 1.9 - k * 0.6, 30 - k * 2)
    pos, q, fov, focus, fstop = r
    pos = pos + hd
    for i in range(3): K.add(cam, 'location', i, f, pos[i])
    for i in range(4): K.add(cam, 'rotation_quaternion', i, f, q[i])
    K.add(cam.data, 'lens', 0, f, 12.0 / math.tan(math.radians(fov) / 2))     # sensor 24 mm tall
    K.add(cam.data, 'dof.focus_distance', 0, f, focus)
    K.add(cam.data, 'dof.aperture_fstop', 0, f, fstop)


def lights(S, X, t, f, K):
    flick = 0.25 if ((t * 13) % 7 < 0.6 or (22 < t < 22.3)) else 1.0
    ping = 0.12 if 34.42 < t < 39.4 else 1.0
    off = lambda i: 0.0 if t > (44.7, 45.1, 45.5)[i] else 1.0
    ks = [flick * ping * off(0), ping * off(1), ping * off(2)]
    for T_, kk in zip(S['tubes'], ks):
        K.add(T_['light'].data, 'energy', 0, f, T_['base'] * kk)
        K.add(T_['mat'].node_tree, em_path(T_['mat']), 0, f, T_['ebase'] * kk)
        if T_['mat'].name not in CONST_MATS: CONST_MATS.append(T_['mat'].name)
    K.add(S['fill'].data, 'energy', 0, f, 18 * min(ping, 1.0 if off(2) else 0.0) + (4 if not off(2) else 0))
    # outside: the neon stutters
    on = not ((t % 1.3) < 0.08 or win(t, 1.9, 2.0))
    K.add(X['neon_light'].data, 'energy', 0, f, (160 if on else 15) + (900 if win(t, 0.6, 0.75) else 0))
    K.add(X['neon_mat'].node_tree, 'nodes["Emission"].inputs[1].default_value', 0, f, 9.0 if on else 1.5)
    if X['neon_mat'].name not in CONST_MATS: CONST_MATS.append(X['neon_mat'].name)


def chairs(S, t, f, K):
    for i, (k, C) in enumerate(zip(ORDER, S['chairs'])):
        piv = C['pivot']; ch = C['chair']
        if 'base' not in ch: ch['base'] = tuple(ch.location)
        base = Vector(ch['base'])
        u = clamp((t - RUN[k] - 0.42) / 0.35) if k in RUN else 0.0        # once they're up and away
        sc_ = ch.scale.y
        # knocked backwards: tip over the back edge on the floor
        edge = Vector((0, 0.25 * sc_, 0))
        M = Matrix.Translation(base + edge) @ Matrix.Rotation(-1.35 * ease(u), 4, 'X') @ Matrix.Translation(-edge)
        loc = M.translation; e = M.to_euler()
        for j in range(3): K.add(ch, 'location', j, f, loc[j] + (0, 0, math.sin(math.pi * u) * 0.03)[j])
        K.add(ch, 'rotation_euler', 0, f, e.x)


def door(S, t, f, K):
    a = 0.0
    if 39.9 <= t < 41.2: a = -math.radians(105) * ease((t - 39.9) / 0.25)
    elif 41.2 <= t < 41.3: a = -math.radians(105) * (1 - (t - 41.2) / 0.1)
    K.add(S['door'], 'rotation_euler', 2, f, -a)


def make_smoke():
    m = bpy.data.materials.new('smoke'); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    out = nt.nodes['Material Output']
    vol = nt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Color'].default_value = (0.82, 0.82, 0.85, 1)
    oi = nt.nodes.new('ShaderNodeObjectInfo'); noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 9; noise.inputs['Detail'].default_value = 6
    tc = nt.nodes.new('ShaderNodeTexCoord'); grad = nt.nodes.new('ShaderNodeTexGradient'); grad.gradient_type = 'SPHERICAL'
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul2 = nt.nodes.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'
    cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.45; cr.inputs['From Max'].default_value = 0.75
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(tc.outputs['Object'], grad.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], cr.inputs['Value']); nt.links.new(cr.outputs[0], mul.inputs[0]); nt.links.new(grad.outputs['Fac'], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0]); nt.links.new(oi.outputs['Alpha'], mul2.inputs[1])
    sc = nt.nodes.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 12.0
    nt.links.new(mul2.outputs[0], sc.inputs[0]); nt.links.new(sc.outputs[0], vol.inputs['Density'])
    nt.links.new(vol.outputs[0], out.inputs['Volume'])
    puffs = []
    rr = random.Random(5)
    for i in range(14):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
        o = bpy.context.active_object; o.name = f'smoke{i}'; o.data.materials.append(m); o.visible_shadow = False
        puffs.append(dict(o=o, b=26.05 + i * 0.05, vx=rr.uniform(-0.05, 0.12), vy=rr.uniform(0.1, 0.2), vz=rr.uniform(0.12, 0.22), s=rr.uniform(0.7, 1.2)))
    return puffs


def smoke_frame(puffs, earl, t, f, K):
    a = earl
    for p in puffs:
        o = p['o']; age = t - p['b']
        K.add(o, 'hide_render', 0, f, 1 if (age < 0 or age > 3.0) else 0)
        if age < 0 or age > 3.0:
            K.add(o, 'color', 3, f, 0.0); K.add(o, 'scale', 0, f, 0.01); K.add(o, 'scale', 1, f, 0.01); K.add(o, 'scale', 2, f, 0.01)
            continue
        if not hasattr(smoke_frame, 'mouth'):
            smoke_frame.mouth = None
        # the exhale leaves his mouth toward the camera side and rises
        M = a.rig.matrix_world
        o0 = MOUTH['earl']; fw = MOUTH['earl_fwd']
        side = fw.cross(Vector((0, 0, 1))).normalized()
        pos = o0 + fw * (0.05 + p['vy'] * age) + side * (p['vx'] * age) + Vector((0, 0, p['vz'] * age * 0.9 - 0.02))
        sz = (0.025 + age * 0.09) * p['s']
        for i in range(3): K.add(o, 'location', i, f, pos[i]); K.add(o, 'scale', i, f, sz)
        K.add(o, 'color', 3, f, (1 - age / 3.0) ** 1.5 * 0.9 * clamp(age / 0.1))

SMOKE_ORIGIN = Vector()


def verify(A, P):
    """Check, at sample frames, that each hand reaches its target (props are placed from targets)."""
    sc = bpy.context.scene
    for a in A.values():
        for o in a.rig.children:
            if o.type == 'MESH': o.hide_viewport = True
    worst = 0.0
    for f in range(1, NF + 1, 15):
        sc.frame_set(f)
        for a in A.values():
            for s in 'LR':
                tgt = a.tgt['hand', s].matrix_world.translation
                wr = a.rig.matrix_world @ a.rig.pose.bones[f'wrist.{s}'].head
                e = (wr - tgt).length
                if e > worst: worst = e
                if e > 0.01: print(f'REACH {a.name} {s} f{f} t{T(f):.2f} err {e*100:.1f} cm')
    print('REACH worst', round(worst * 100, 2), 'cm')
    for a in A.values():
        for o in a.rig.children:
            if o.type == 'MESH': o.hide_viewport = False




# ================================================================== seat contact
def _world_mesh(o, dg):
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    V = [o.matrix_world @ v.co for v in me.vertices]; F = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear(); return V, F


def _inside(tree, p):
    """Behind the nearest surface (against its normal), within 3 cm: works for open shells too."""
    loc, nrm, idx, dist = tree.find_nearest(p, 0.03)
    return loc is not None and (p - loc).dot(nrm) < -0.0005


def penetration(actor_objs, chair, dg):
    """Contacts between a character and a chair, both ways: character vertices behind the chair's
    surface, and chair vertices behind the character's surface (thin chair legs through a calf)."""
    from mathutils.bvhtree import BVHTree
    TV, TF = [], []
    for c in [chair] + list(chair.children_recursive):
        if c.type == 'MESH':
            v, fcs = _world_mesh(c, dg); off = len(TV); TV += v; TF += [tuple(i + off for i in x) for x in fcs]
    tree = BVHTree.FromPolygons(TV, TF)
    lo = Vector([min(v[i] for v in TV) for i in range(3)]) - Vector((.1, .1, .1)); hi = Vector([max(v[i] for v in TV) for i in range(3)]) + Vector((.1, .1, .1))
    bad = []
    for o in actor_objs:
        V, F = _world_mesh(o, dg)
        for p in V:
            if all(lo[i] <= p[i] <= hi[i] for i in range(3)) and _inside(tree, p):
                bad.append((p, tree.find_nearest(p)[3]))
        if F:
            t2 = BVHTree.FromPolygons(V, F)
            for p in TV:
                loc, nrm, idx, dist = t2.find_nearest(p, 0.08)
                if loc is not None and (p - loc).dot(nrm) < -0.001:
                    bad.append((p, dist))
    return bad


def seat_fix_once(A, S, SEAT):
    """For each seated actor, the smallest (forward, up) shift of the hips that leaves no vertex of
    the body or clothes inside the chair, found by grid search at a seated frame."""
    sc = bpy.context.scene; f = int(fr(10.0))
    stool_fit(SEAT_NEET, S['chairs'][ORDER.index('gary')], SEAT['gary'])
    best = {k: None for k in A}
    combos = sorted(((dy, dz) for dy in [i * 0.01 for i in range(0, 9)] for dz in [i * 0.005 for i in range(0, 9)]), key=lambda c: c[0] * 1.5 + c[1])
    for dy, dz in combos:
        todo = [k for k in A if best[k] is None]
        if not todo: break
        for k in todo:
            SEAT_FIX[k] = (dy, dz)
            sc_ = SEAT_S.get(k, room.CHAIR_S); S['chairs'][ORDER.index(k)]['chair'].scale = (sc_, sc_, sc_)
            solve_actor(A[k], k, T(f), f, SEAT[k], dict(yaw=0.0, pitch=0.0), SEAT_HEADS, SEAT_P, rigctl.Keys())
            A[k].K.flush()
        sc.frame_set(f + 1); sc.frame_set(f); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        for k in todo:
            i = ORDER.index(k); a = A[k]
            objs = [o for o in a.rig.children if o.type == 'MESH' and not any(x in o.name for x in ('high-poly', 'teeth', 'tongue', 'eyelash', 'eyebrow'))]
            n = len([1 for _, dep in penetration(objs, S['chairs'][i]['chair'], dg) if dep > 0.005])
            if n == 0:
                best[k] = (dy + 0.003, dz + 0.003); print('SEAT', k, 'clear at forward', round(dy * 100, 1), 'cm, up', round(dz * 100, 1), 'cm')
    for k in A:
        if best[k] is None:
            print('SEAT', k, 'NOT CLEAR at chair', SEAT_S.get(k, room.CHAIR_S)); best[k] = None
        else:
            SEAT_FIX[k] = best[k]
    return [k for k in A if best[k] is None]


def seat_report(A, S):
    sc = bpy.context.scene
    for t in (10.0, 20.0, 30.0, 36.0):
        sc.frame_set(int(fr(t))); dg = bpy.context.evaluated_depsgraph_get()
        for i, k in enumerate(ORDER):
            if k not in A: continue
            a = A[k]; objs = [o for o in a.rig.children if o.type == 'MESH' and not any(x in o.name for x in ('high-poly', 'teeth', 'tongue', 'eyelash', 'eyebrow'))]
            bad = penetration(objs, S['chairs'][i]['chair'], dg)
            print('SEATCHECK', t, k, len(bad), 'deepest cm', round(max([d for _, d in bad] + [0]) * 100, 2))



def seat_fix(A, S, SEAT):
    """Seat everyone without clipping; a smaller chair for anyone whose legs are too short for it."""
    left = seat_fix_once(A, S, SEAT)
    for s_ in (0.88, 0.85, 0.82, 0.79):
        if not left: break
        sub = {k: A[k] for k in left}
        for k in left: SEAT_S[k] = s_
        left = seat_fix_once(sub, S, SEAT)
    for k in left: print('SEAT', k, 'STILL NOT CLEAR')
    for k, s_ in SEAT_S.items(): print('SEAT', k, 'chair scale', s_, 'seat height cm', round(50 * s_, 1))


def neet_fit(N, C, seat):
    """Move NEET (not change him) so his seated clips clear his chair: his back in front of the
    backrest's face, his seat on top of the seat, measured with rays on the chair (a clean mesh)."""
    from mathutils.bvhtree import BVHTree
    global NEET_FIX
    sc = bpy.context.scene; chair = C['chair']; piv = C['pivot']
    if NEET_FIX != (0.0, 0.0): return          # already fitted
    if N['root'].animation_data: N['root'].animation_data_clear()
    times = [t / 4 for t in range(int(3.4 * 4), int(7.2 * 4))] + [t / 4 for t in range(int(16.9 * 4), int(39.2 * 4))]
    for rnd in range(4):
        fwd = up = 0.0
        sc.frame_set(1); dg = bpy.context.evaluated_depsgraph_get()
        TV, TF = [], []
        for c in [chair] + list(chair.children_recursive):
            if c.type == 'MESH':
                v, fcs = _world_mesh(c, dg); off = len(TV); TV += v; TF += [tuple(i + off for i in x) for x in fcs]
        Mi = piv.matrix_world.inverted(); tree = BVHTree.FromPolygons([Mi @ v for v in TV], TF)
        seat_top = max(v.z for v in (Mi @ w for w in TV) if abs(v.x) < 0.15 and abs(v.y) < 0.12 and v.z < 0.7)
        for tt in times:
            ff = int(fr(tt)); neet_frame(N, tt, ff, seat, _Direct()); sc.frame_set(ff); bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get(); V, _ = _world_mesh(N['mesh'], dg)
            for w in V:
                p = Mi @ w
                if abs(p.x) > 0.24: continue
                if seat_top + 0.06 < p.z < 0.98:
                    h = tree.ray_cast(Vector((p.x, -0.6, p.z)), Vector((0, 1, 0)), 1.2)   # the backrest's front face
                    if h[0] is not None and h[0].y < 0.35 and p.y > h[0].y - 0.004:
                        fwd = max(fwd, p.y - h[0].y + 0.006)
                if p.z < seat_top + 0.06 and -0.3 < p.y < 0.2:
                    h = tree.ray_cast(Vector((p.x, p.y, 1.2)), Vector((0, 0, -1)), 1.5)
                    if h[0] is not None and h[0].z > p.z - 0.004 and h[0].z - p.z < 0.12:
                        up = max(up, h[0].z - p.z + 0.006)
        print('SEAT NEET round', rnd, 'needs forward cm', round(fwd * 100, 1), 'up cm', round(up * 100, 1))
        if fwd < 0.002 and up < 0.002: break
        NEET_FIX = (NEET_FIX[0] + fwd, NEET_FIX[1] + up)
    print('SEAT NEET moved forward', round(NEET_FIX[0] * 100, 1), 'cm, up', round(NEET_FIX[1] * 100, 1), 'cm')



def stool_fit(N, C, seat):
    """Put NEET's stool right under him: centred under his hips, top at the lowest his seat goes."""
    if C.get('fitted'): return
    sc = bpy.context.scene; rig = N['rig']; hb = rig.pose.bones['mixamorig:Hips']; piv = C['pivot']; st = C['chair']
    if N['root'].animation_data: N['root'].animation_data_clear()
    Mi = piv.matrix_world.inverted()
    times = [t / 4 for t in range(int(3.4 * 4), int(7.2 * 4))] + [t / 4 for t in range(int(16.9 * 4), int(39.2 * 4))]
    lows, xs, ys = [], [], []
    for tt in times:
        ff = int(fr(tt)); neet_frame(N, tt, ff, seat, _Direct()); sc.frame_set(ff); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get(); V, _ = _world_mesh(N['mesh'], dg)
        h = Mi @ (rig.matrix_world @ hb.head)
        pts = [Mi @ w for w in V]
        under = [p for p in pts if (Vector((p.x, p.y)) - Vector((h.x, h.y))).length < 0.13 and p.z < h.z]
        lows.append(min(p.z for p in under)); xs.append(h.x); ys.append(h.y)
    top = min(lows) - 0.002; cx = sum(xs) / len(xs); cy = sum(ys) / len(ys)
    s = top / 0.437
    st.scale = (1.15, 1.15, s); st.location = (cx, cy, 0)
    C['fitted'] = True
    print('SEAT NEET stool top cm', round(top * 100, 1), 'gap over his clips cm', round((max(lows) - min(lows)) * 100, 1), 'centre', round(cx, 3), round(cy, 3))



def unmasked_body(actor, on=True):
    """Switch the clothing masks off (True) or back on (False) for contact measurements."""
    for m in actor.body.modifiers:
        if m.type == 'MASK' and m.name != 'Hide helpers':
            m.show_viewport = not on


def outside_skin(actor, path, gap=0.0045, steps=4):
    """Densify a polyline and push every point to just outside the (unmasked) skin."""
    from mathutils.bvhtree import BVHTree
    unmasked_body(actor, True); bpy.context.view_layer.update()
    V, F = _world_mesh(actor.body, bpy.context.evaluated_depsgraph_get()); unmasked_body(actor, False)
    tree = BVHTree.FromPolygons(V, F)
    dense = []
    for p0, p1 in zip(path, path[1:]):
        for i in range(steps): dense.append(p0.lerp(p1, i / steps))
    dense.append(path[-1])
    def push(pts):
        res = []
        for p in pts:
            loc, nrm, i, dist = tree.find_nearest(p, 0.08)
            if loc is not None and ((p - loc).dot(nrm) < 0 or dist < gap):
                p = loc + nrm * gap
            res.append(p)
        return res
    def smooth(pts, n):
        for _ in range(n):
            pts = [pts[0]] + [pts[i] * 0.5 + (pts[i - 1] + pts[i + 1]) * 0.25 for i in range(1, len(pts) - 1)] + [pts[-1]]
        return pts
    out = push(dense)
    for _ in range(4):                       # smooth the path, then keep it off the skin, and repeat
        out = push(smooth(out, 3))
    return smooth(out, 3)                    # a final pass with no snapping: no ripples


def arm_regions(actor):
    o = actor.body; names = {g.index: g.name for g in o.vertex_groups}; bones = set(actor.rest)
    ARM = ('wrist', 'finger', 'metacarpal')       # the hand itself; arm-to-side contact is natural
    reg = []
    for v in o.data.vertices:
        gs = [(names[g.group], g.weight) for g in v.groups if names.get(g.group) in bones]
        b = max(gs, key=lambda x: x[1])[0] if gs else ''
        side = b[-1] if b.endswith(('.L', '.R')) else 'M'
        reg.append(('arm' + side) if b.startswith(ARM) else ('limb' if b.startswith(('upperarm', 'lowerarm', 'shoulder', 'clavicle')) else 'core'))
    return reg


def arm_contacts(actor, reg, held, dg):
    """Per side: arm/hand vertices behind the core body surface (> 2 mm), and held-prop vertices inside the body."""
    from mathutils.bvhtree import BVHTree
    V, F = _world_mesh(actor.body, dg); out = {}
    full = BVHTree.FromPolygons(V, [f for f in F if all(reg[i] == 'core' for i in f)])   # thighs, belly, chest: not the gripping hand
    for s in 'LR':
        other = 'armR' if s == 'L' else 'armL'
        core = BVHTree.FromPolygons(V, [f for f in F if all(reg[i] in ('core', other) for i in f)])
        n = 0
        for i, p in enumerate(V):
            if reg[i] != 'arm' + s: continue
            loc, nrm, _, dist = core.find_nearest(p, 0.03)
            if loc is not None and (p - loc).dot(nrm) < -0.002: n += 1
        ob = held.get(s)
        if ob is not None and not ob.hide_render:
            for c in [ob] + list(ob.children_recursive):
                if c.type != 'MESH': continue
                for p in _world_mesh(c, dg)[0]:
                    loc, nrm, _, dist = full.find_nearest(p, 0.03)
                    if loc is not None and (p - loc).dot(nrm) < -0.002: n += 1
        out[s] = n
    return out


def hand_fix(A, P, SEAT):
    """Smallest lift/outward/forward shift of each resting or holding hand that clears the body."""
    sc = bpy.context.scene; f = int(fr(10.0))
    regs = {k: arm_regions(a) for k, a in A.items()}
    held = {'pam': {'L': P['pam_mug']}, 'linda': {'L': P['linda_mug']}, 'earl': {'R': P['earl_cig']}, 'chad': {'R': P['chad_can']}}
    # lowest first: the first clear height is the hand resting on the thigh, not floating above it
    cands = [Vector((dx * 0.015, 0.0, dz * 0.005)) for dz in range(-6, 31) for dx in range(3)]
    todo = {(k, s) for k in A for s in 'LR'}
    for a in A.values(): unmasked_body(a, True)
    for c in cands:
        if not todo: break
        for key in todo: HAND_FIX[key] = c
        for k in {k for k, _ in todo}:
            Kp = rigctl.Keys()
            solve_actor(A[k], k, T(f), f, SEAT[k], dict(yaw=0.0, pitch=0.0), SEAT_HEADS, SEAT_P, Kp); A[k].K.flush(); Kp.flush()
        sc.frame_set(f + 1); sc.frame_set(f); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        res = {k: arm_contacts(A[k], regs[k], held[k], dg) for k in {k for k, _ in todo}}
        for key in list(todo):
            if res[key[0]][key[1]] == 0:
                HAND_FIX[key] = c + Vector((0, 0, 0.015 if key[0] == 'chad' else 0.01))     # a little air for breathing and Chad's bouncing leg
                todo.discard(key); print('HAND', key, 'clear with offset (out, fwd, up) cm', tuple(round(x * 100, 1) for x in c))
    for key in todo:
        print('HAND', key, 'NOT CLEAR'); HAND_FIX[key] = cands[-1]
    for a in A.values(): unmasked_body(a, False)



def skin_to_body(actor, curve_obj, name, gap=0.0025):
    """Turn a wire into a mesh that is pushed just outside the skin and skinned with the weights of the
    skin under it, so it moves with the face and neck instead of cutting through them."""
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(curve_obj.evaluated_get(dg))
    me.transform(curve_obj.matrix_world)
    mats = list(curve_obj.data.materials)
    bpy.data.objects.remove(curve_obj)
    unmasked_body(actor, True); bpy.context.view_layer.update()
    b = actor.body; ev = b.evaluated_get(bpy.context.evaluated_depsgraph_get()); bm = ev.to_mesh()
    V = [b.matrix_world @ v.co for v in bm.vertices]; F = [tuple(p.vertices) for p in bm.polygons]; ev.to_mesh_clear()
    unmasked_body(actor, False)
    tree = BVHTree.FromPolygons(V, F); kd = KDTree(len(V))
    for i, p in enumerate(V): kd.insert(p, i)
    kd.balance()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for m in mats: me.materials.append(m)
    gnames = {g.index: g.name for g in b.vertex_groups}; bones = set(actor.rest)
    groups = {}
    # weights blended from the 10 nearest skin vertices (inverse distance), so neighbouring tube
    # vertices bend together instead of stepping between bones
    for v in me.vertices:
        acc = {}
        near = kd.find_n(v.co, 40); tot = 0.0
        for co, idx, dd in near:
            w0 = math.exp(-(dd / 0.025) ** 2); tot += w0          # soft gaussian falloff: weights change continuously
            for g in b.data.vertices[idx].groups:
                gn = gnames[g.group]
                if gn in bones: acc[gn] = acc.get(gn, 0.0) + g.weight * w0
        s_ = sum(acc.values()) or 1.0
        for gn, w in acc.items():
            if w / s_ > 0.002:
                if gn not in groups: groups[gn] = o.vertex_groups.new(name=gn)
                groups[gn].add([v.index], w / s_, 'REPLACE')
    o.parent = actor.rig
    mod = o.modifiers.new('Armature', 'ARMATURE'); mod.object = actor.rig
    for p in me.polygons: p.use_smooth = True
    return o


def glasses_off_skin(actor, part_name, gap=0.002):
    """Push any glasses vertex that sits inside or on the skin back out (rest pose)."""
    from mathutils.bvhtree import BVHTree
    g = actor.parts.get(part_name)
    if g is None: return
    unmasked_body(actor, True); bpy.context.view_layer.update()
    V, F = _world_mesh(actor.body, bpy.context.evaluated_depsgraph_get()); unmasked_body(actor, False)
    tree = BVHTree.FromPolygons(V, F); inv = g.matrix_world.inverted(); n = 0
    for v in g.data.vertices:
        p = g.matrix_world @ v.co
        loc, nrm, fi, dist = tree.find_nearest(p, 0.05)
        if loc is not None and ((p - loc).dot(nrm) < 0 or dist < gap):
            v.co = inv @ (loc + nrm * gap); n += 1
    print('GLASSES', actor.name, 'vertices moved off the skin', n)



def find_lips(actor):
    """The gap between the lips (rest, armature space). A column of rays from in front of the face
    traces the profile; the upper and lower lips bulge forward and the seam is the deepest point
    between them."""
    from mathutils.bvhtree import BVHTree
    unmasked_body(actor, True); bpy.context.view_layer.update()
    V, F = _world_mesh(actor.body, bpy.context.evaluated_depsgraph_get()); unmasked_body(actor, False)
    tree = BVHTree.FromPolygons(V, F); m = actor.mouth
    prof = []
    for i in range(-25, 21):                      # lips only: below the nose, above the chin
        z = m.z + i * 0.001
        h = tree.ray_cast(Vector((0.0, m.y - 0.2, z)), Vector((0, 1, 0)), 0.4)
        if h[0] is not None: prof.append((z, h[0].y))
    # the two most forward bulges (lips), then the deepest point between them (the seam)
    lo = min(prof, key=lambda p: p[1])
    others = [p for p in prof if abs(p[0] - lo[0]) > 0.006]
    lo2 = min(others, key=lambda p: p[1])
    za, zb = sorted((lo[0], lo2[0]))
    between = [p for p in prof if za < p[0] < zb]
    seam = max(between, key=lambda p: p[1]) if between else ((za + zb) / 2, (lo[1] + lo2[1]) / 2)
    actor.lip = Vector((0.0, seam[1], seam[0]))
    print('LIPS', actor.name, 'lip bulges z', round(za, 3), round(zb, 3), 'seam', tuple(round(c, 3) for c in actor.lip), 'old mouth pt', tuple(round(c, 3) for c in m))



def cig_fix(a, P):
    """Close Earl's index and middle fingers to a real pinch and seat the cigarette in it, all measured
    on the evaluated (Blender-skinned) hand."""
    sc = bpy.context.scene; f = int(fr(10.0)); cig = P['earl_cig']
    def measure():
        Kp = rigctl.Keys(); solve_actor(a, 'earl', T(f), f, CIG_SEAT, dict(yaw=0.0, pitch=0.0), SEAT_HEADS, SEAT_P, Kp); a.K.flush(); Kp.flush()
        unmasked_body(a, True); hh = a.body.modifiers.get('Hide helpers'); hh.show_viewport = False
        sc.frame_set(f + 1); sc.frame_set(f); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        b = a.body; ev = b.evaluated_get(dg); me = ev.to_mesh(); V = [b.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
        unmasked_body(a, False); hh.show_viewport = True
        names = {g.index: g.name for g in b.vertex_groups}
        def dom(v):
            gs = [(names[g.group], g.weight) for g in v.groups if names[g.group] in a.rest]
            return max(gs, key=lambda x: x[1])[0] if gs else ''
        if not hasattr(cig_fix, 'doms'): cig_fix.doms = [dom(v) for v in b.data.vertices]
        P2 = [V[i] for i, n in enumerate(cig_fix.doms) if n in ('finger2-2.R',)]
        P3 = [V[i] for i, n in enumerate(cig_fix.doms) if n in ('finger3-2.R',)]
        return sum(P2, Vector()) / len(P2), sum(P3, Vector()) / len(P3)
    c, sp0, M = a.G['cig']
    best = None
    for s in [x * 0.03 for x in range(-12, 13)]:
        a.G['cig'] = (c, {'finger2': s, 'finger3': -s * 0.6}, M)
        c2, c3 = measure(); dd = (c2 - c3).length
        if best is None or abs(dd - 0.021) < abs(best[1] - 0.021): best = (s, dd)
    a.G['cig'] = (c, {'finger2': best[0], 'finger3': -best[0] * 0.6}, M)
    c2, c3 = measure(); gap = (c2 + c3) / 2
    # move the cigarette (in its palm frame) so the pinch is 16 mm past the filter's middle
    W = cig.matrix_world.copy(); ax = W.to_3x3().col[2].normalized()
    want = gap - ax * 0.016
    from mathutils.geometry import intersect_point_line
    palm_rot = W.to_3x3() @ M.to_3x3().inverted()
    M2 = M.copy(); M2.translation = M.translation + palm_rot.inverted() @ (want - W.translation)
    a.G['cig'] = (c, a.G['cig'][1], M2)
    print('CIG fingers', round(best[1] * 1000, 1), 'mm apart (spread', round(best[0], 2), '); cigarette moved', round((want - W.translation).length * 1000, 1), 'mm')


if __name__ == '__main__':
    main()
