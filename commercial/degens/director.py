"""DEGENS ANONYMOUS, realistic remake: builds the whole film in Blender and keys every frame.

    blender -b -P director.py -- --out scene.blend [--frames N]

Timing, dialogue, sound cues, shots and lights are the original skit's (director.js), unchanged.
Frame f shows time t = (f - 1) / 30.
"""
import bpy, sys, os, math, json, random
from mathutils import Vector, Matrix, Quaternion, Euler
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import humans, rigctl, assets, props, room

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
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.3
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
    place_oxygen(P, SEAT['earl'], A)
    cam = make_camera()
    smoke = make_smoke()
    # ---------------- per-frame solve
    Kx = rigctl.Keys()
    state = {k: dict(yaw=0.0, pitch=0.0) for k in ORDER}
    HEADS = head_positions(A, NEET, SEAT)
    for f in range(1, NF + 1):
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
    root['sit_dz'] = 0.505 - seat_z
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
        z = root['sit_dz'] * sit
        bk = Matrix.Rotation(face, 3, 'Z') @ Vector((0, 0.06 * sit, 0)); x += bk.x; y += bk.y
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
    # Earl's oxygen: tank by his chair, cannula on his face
    P['oxy'] = props.oxygen('oxy')
    cannula(A['earl'], P)
    return P

def place_oxygen(P, seat, A):
    M = Matrix.Translation((seat['x'], seat['y'], 0)) @ Matrix.Rotation(seat['face'], 4, 'Z')
    P['oxy'].matrix_world = M @ Matrix.Translation((0.46, 0.12, 0)) @ Matrix.Rotation(0.4, 4, 'Z')
    bpy.context.view_layer.update()
    valve = P['oxy'].matrix_world @ Vector((0, 0.0, 0.7))
    P['valve'] = valve
    line = props.tube_curve('cannula_line', [valve + Vector((0, 0, 0.0)), valve + Vector((0, 0, 0.25)), valve + Vector((-0.1, -0.1, 0.5)), valve + Vector((-0.3, -0.1, 0.8))], r=0.0024, m=P['cannula_mat'])
    for bp in line.data.splines[0].bezier_points: bp.handle_left_type = bp.handle_right_type = 'AUTO'
    P['cannula_line'] = line
    # the chin point in head-bone space
    a = A['earl']; hk = P['cannula_hook']; bpy.context.view_layer.update()
    P['chin_local'] = a.rest['head'].inverted() @ (a.rig.matrix_world.inverted() @ hk.matrix_world.translation)
    return P


def screen(k):
    """A phone screen image: a trading app with a launch alert (Pam's: her dev wallet)."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = 540, 1120; im = Image.new('RGB', (w, h), (8, 10, 14)); d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(props.FONT_B, 40); fs = ImageFont.truetype(props.FONT_B, 26)
    d.rectangle((0, 0, w, 70), fill=(14, 16, 22)); d.text((24, 16), '9:41', font=fs, fill=(230, 230, 230))
    d.rounded_rectangle((20, 100, w - 20, 230), 26, fill=(32, 34, 42))
    d.rounded_rectangle((40, 122, 120, 202), 18, fill=(150, 60, 230)); d.text((150, 120), 'LAUNCHPAD', font=fs, fill=(170, 170, 180))
    d.text((150, 156), '$SOBER just launched', font=fs, fill=(255, 255, 255))
    pts = [(30 + i * 24, 900 - (i ** 1.6) * 6 - random.Random(i).uniform(0, 30)) for i in range(21)]
    d.line(pts, fill=(43, 255, 106), width=8)
    d.text((40, 300), '$SOBER', font=fb, fill=(200, 255, 90)); d.text((40, 360), '+2,413,907%' if k == 'pam' else '0.0001', font=fb, fill=(43, 255, 106))
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
                    Vector((ear.x + sx * 0.002, ear.y + 0.025, ear.z + 0.0)), Vector((ear.x - sx * 0.01, ear.y + 0.02, ear.z - 0.06)),
                    Vector((sx * 0.03, L['chin'].y + 0.06, L['chin'].z - 0.04)), Vector((0.0, L['chin'].y + 0.05, L['chin'].z - 0.06))])
    loop = props.tube_curve('cannula_face', pts[0] + list(reversed(pts[1]))[:-1], r=0.0021, m=tube)
    bone_parent(loop, actor, 'head')
    # a hook point under the chin follows the head; the line drops to the tank beside the chair
    hk = bpy.data.objects.new('cannula_hook', None); bpy.context.scene.collection.objects.link(hk)
    hk.location = Vector((0.0, L['chin'].y + 0.05, L['chin'].z - 0.06)); bone_parent(hk, actor, 'head')
    P['cannula_hook'] = hk; P['cannula_mat'] = tube


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


def seated_basics(a):
    hipc = (a.hip['L'] + a.hip['R']) / 2
    return Vector((0, 0.035 - hipc.y, 0.5 + 0.095 - hipc.z))


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
    eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
    fwd = head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, -1, 0)))
    up = head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, 0, 1)))
    hands = {}; shapes = {}; place = {}
    MOUTH[k] = mw @ mouth; MOUTH[k + '_fwd'] = mw.to_3x3() @ fwd
    def lap(s, holding=None):
        hip = a.hip[s] + root_loc
        knee = hip + Vector((0, -a.thigh * 0.95, -0.06))
        if holding:
            pos = hip.lerp(knee, 0.55) + Vector((-sx[s] * 0.07, 0, 0.13))
            return a.frame(pos, (sx[s] * 0.25, -1, -0.35), (-sx[s], 0, 0.0))
        pos = hip.lerp(knee, 0.62) + Vector((-sx[s] * 0.01, 0, 0.085))
        return a.frame(pos, (-sx[s] * 0.15, -1, -0.15), (sx[s] * 0.2, 0, -1))
    def phone_frame(s):
        pos = eyes + fwd * 0.29 - up * 0.25 + Vector((-sx[s] * 0.0, 0, 0))
        n = (eyes - pos).normalized(); y = up - n * up.dot(n)
        return a.frame(pos, y, n)
    def cyl_grip(s, palm, R):
        """Prop matrix (rig space) for a cylinder of radius R gripped in this palm frame."""
        ax = palm.to_3x3()
        axis = ax.col[0] * a.idx_sign[s]                       # thumb side up
        center = palm.translation + ax.col[2] * (R + 0.012) + ax.col[1] * 0.03
        z = axis.normalized(); xx = ax.col[1].normalized(); xx = (xx - z * xx.dot(z)).normalized(); yy = z.cross(xx)
        M = Matrix((xx, yy, z)).transposed().to_4x4(); M.translation = center; return M
    def palm_from_cyl(s, M, R):
        """Inverse of cyl_grip: the palm frame that grips a cylinder placed at M."""
        xx = M.to_3x3().col[0].normalized(); z = M.to_3x3().col[2].normalized()
        X = z * a.idx_sign[s]; Y = xx; n = X.cross(Y)
        F = Matrix((X, Y, n)).transposed().to_4x4()
        F.translation = M.translation - n * (R + 0.012) - Y * 0.03
        return F
    def blend(F0, F1, k2, arc=Vector((0, -0.12, 0))):
        p = F0.translation.lerp(F1.translation, k2) + arc * math.sin(math.pi * k2)
        q = F0.to_quaternion().slerp(F1.to_quaternion(), k2)
        M = q.to_matrix().to_4x4(); M.translation = p; return M
    # defaults
    for s in 'LR':
        hands[s] = lap(s); shapes[s] = 'rest'
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
                tilt = 0.12; st_ = P['linda_straw']
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
        F = lap('R'); shapes['R'] = 'cig'
        hands['R'] = F
        def cig_in_palm(F):
            ax = F.to_3x3(); p = F.translation + ax.col[1] * 0.062 + ax.col[0] * (a.idx_sign['R'] * 0.011) - ax.col[2] * 0.004
            z = -ax.col[2]; y = ax.col[1]; x = y.cross(z)
            M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = p - z * 0.012; return M
        def cig_at_lips(droop=0.35):
            z = (fwd * math.cos(droop) - up * math.sin(droop)).normalized(); y = up - z * up.dot(z); x = y.cross(z)
            M = Matrix((x.normalized(), y.normalized(), z)).transposed().to_4x4(); M.translation = mouth + fwd * 0.004 - z * 0.004; return M
        def palm_for_cig(M):
            # the palm that holds this cigarette (inverse of cig_in_palm)
            z = M.to_3x3().col[2]; y = M.to_3x3().col[1]; n = -z; x = y.cross(n)
            Fp = Matrix((x, y, n)).transposed().to_4x4()
            p = M.translation + z * 0.012
            Fp.translation = p - (y * 0.062 + x * (a.idx_sign['R'] * 0.011) - n * 0.004)
            return Fp
        drag = max(pulse(t, 13.0, 13.8, 0.3), pulse(t, 25.1, 26.0, 0.3))
        place_in = pulse(t, 22.15, 22.8, 0.25)            # puts it in his mouth (off camera)
        in_mouth = win(t, 22.5, 25.4)
        Mlips = cig_at_lips(0.35 if in_mouth else 0.15)
        Fl = palm_for_cig(Mlips)
        k2 = max(drag, place_in)
        hands['R'] = blend(F, Fl, k2, Vector((0.06, -0.12, 0)))
        place['earl_cig'] = Mlips if in_mouth else cig_in_palm(hands['R'])
        if in_mouth:
            shape['v_mm'] = max(shape['v_mm'], 0.35); shape['v_aa'] *= 0.5
    # phones
    pphone = P[k + '_phone']
    if phone_up > 0.01 and not running:
        Fp = phone_frame(phand)
        hands[phand] = blend(hands[phand], Fp, clamp(phone_up)); shapes[phand] = 'phone' if phone_up > 0.4 else shapes[phand]
        ax = hands[phand].to_3x3()
        M = Matrix((ax.col[0], ax.col[1], ax.col[2])).transposed().to_4x4()
        M = hands[phand].copy(); M.translation = hands[phand].translation + ax.col[2] * 0.004 + ax.col[1] * 0.02
        place[k + '_phone'] = M
    else:
        place[k + '_phone'] = None
    # Chad wipes his nose (left hand), Pam and Linda clap (right hand pats the mug hand)
    if k == 'chad':
        wipe = pulse(t, 29.62, 30.1, 0.12)
        if wipe > 0.01:
            pos = nose - up * 0.025 + fwd * 0.04 + Vector((0.02, 0, 0)) * math.sin((t - 29.62) * 18)
            Fw = a.frame(pos, (-0.3, 0, 1), (0, 0, -1) if False else (-fwd).normalized())
            hands['L'] = blend(hands['L'], Fw, wipe); shapes['L'] = 'fist'
    if k in ('pam', 'linda') and win(t, 15.75, 16.65):
        c = max(pulse(t, 15.85, 16.08, 0.08), pulse(t, 16.25, 16.48, 0.08))
        mugF = hands['L']; ax = mugF.to_3x3(); nL = ax.col[2]
        back = mugF.translation - nL * 0.03 + ax.col[1] * 0.02
        Fc = a.frame(back - nL * (0.012 + (1 - c) * 0.09), ax.col[1], nL)
        hands['R'] = blend(hands['R'], Fc, ramp(t, 15.75, 15.85) * (1 - ramp(t, 16.55, 16.65))); shapes['R'] = 'flat'
    if running:
        u = t - RUN[k]; swing = math.sin(u * 11.0) * clamp((u - 0.22) / 0.2)
        for s in 'LR':
            sh = a.shoulder[s] + root_loc
            sg = swing if s == 'L' else -swing
            pos = sh + Vector((sx[s] * 0.12, -0.18 - sg * 0.18, -0.38 + max(0, -sg) * 0.1 + max(0, sg) * 0.12))
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
        curl_Q(a, s, shapes[s], Q)
    H = {('hand', s): mw @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
    for s in 'LR':
        poles['hand', s] = mw @ (a.shoulder[s] + root_loc + Vector((sx[s] * 0.7, 0.45, -0.45)))
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
        mid = chin + side * 0.12 + Vector((0, 0, -0.25)) + (mw.to_3x3() @ Vector((0, -0.12, 0)))
        cut = running and t > RUN['earl'] + 0.15
        pts = [v, v + Vector((0, 0, 0.22)), mid, chin] if not cut else [v, v + Vector((0, 0, 0.12)), v + Vector((0.05, -0.15, 0.0)), v + Vector((0.12, -0.3, -0.65))]
        for j, p in enumerate(pts):
            for i in range(3): K.add(cu, f'splines[0].bezier_points[{j}].co', i, f, p[i])
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
    K.add(S['fill'].data, 'energy', 0, f, 45 * min(ping, 1.0 if off(2) else 0.0) + (4 if not off(2) else 0))
    # outside: the neon stutters
    on = not ((t % 1.3) < 0.08 or win(t, 1.9, 2.0))
    K.add(X['neon_light'].data, 'energy', 0, f, (160 if on else 15) + (900 if win(t, 0.6, 0.75) else 0))
    K.add(X['neon_mat'].node_tree, 'nodes["Emission"].inputs[1].default_value', 0, f, 9.0 if on else 1.5)
    if X['neon_mat'].name not in CONST_MATS: CONST_MATS.append(X['neon_mat'].name)


def chairs(S, t, f, K):
    for i, (k, C) in enumerate(zip(ORDER, S['chairs'])):
        piv = C['pivot']; ch = C['chair']
        u = clamp((t - RUN[k] - 0.18) / 0.35) if k in RUN else 0.0
        ang = (1 if i % 2 else -1) * ease(u) * 1.45
        # tip over its side edge: rotate about the edge on the floor
        edge = Vector((-0.27 if ang > 0 else 0.27, 0, 0))
        M = Matrix.Translation(edge) @ Matrix.Rotation(ang, 4, 'Y') @ Matrix.Translation(-edge)
        loc = M.translation; e = M.to_euler()
        for j in range(3): K.add(ch, 'location', j, f, loc[j] + (0, 0, math.sin(math.pi * u) * 0.04)[j])
        K.add(ch, 'rotation_euler', 1, f, e.y)


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


if __name__ == '__main__':
    main()
