"""7 CENTS (a Meme Royale commercial): builds the scene and keys every frame.
blender -b -P director.py -- --out scene.blend [--frames N]
Env: W, PH, DA_TEX, VO (folder with vo.json), SCR (folder with scr_shop/, wallet.png, scr_candle/)."""
import bpy, sys, os, math, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'pawn'), os.path.join(H, '..', 'whale'), os.path.join(H, '..', 'degens')]
from mathutils import Vector, Matrix, Quaternion
import rigctl, grips, props, humans, wprops, assets
import kitchen, cast
from kitchen import ISL_H

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return ARGS[ARGS.index(k) + 1] if k in ARGS else d
FPS = 30
VO = json.load(open(os.path.join(os.environ['VO'], 'vo.json')))
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, k: a + (b - a) * k
def ramp(t, a, b): return clamp((t - a) / (b - a))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
def win(t, a, b): return a <= t < b
def pulse(t, a, b, f=0.15): return clamp(min((t - a) / f, (b - t) / f))

LINES = []
def say(i, t): LINES.append(dict(id=i, who=VO[i]['who'], t=t, end=t + VO[i]['dur'], text=VO[i]['text']))
say('k_one', 6.95); say('d_wallet', 10.6); say('m_college', 16.6); say('k_whale', 18.4); say('d_seven', 20.15)
say('k_pocket', 21.75); say('r_morning', 23.85); say('k_letsgo', 25.3)
END = 30.8; ENDCARD = 26.8; MORNING = 8.4
NF = int(arg('--frames', round(END * FPS)))
T = lambda f: (f - 1) / FPS
CUTS = [2.4, 6.6, MORNING, 10.4, 13.6, 15.0, 16.45, 18.25, 19.95, 21.6, 23.6, 24.95, ENDCARD]
SPOT = {'kid': (-0.35, -0.86, math.pi), 'dad': (0.38, 0.82, 0.0), 'mom': (-0.42, 0.86, 0.0), 'repo': (2.62, -1.4, -math.pi / 2)}
PRESENT = {'kid': (0, 99), 'dad': (MORNING, 99), 'mom': (MORNING, 99), 'repo': (23.0, 25.2)}


def talk(k, t):
    for L in LINES:
        if L['who'] == k and L['t'] <= t < L['end']:
            env = VO[L['id']]['env']; i = int((t - L['t']) * FPS); return env[min(i, len(env) - 1)]
    return 0.0


def speaker(t):
    best = None
    for L in LINES:
        if L['t'] - 0.25 <= t < L['end'] + 0.4: best = L['who']
    return best


def setup_render():
    sc = bpy.context.scene; sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 8; sc.cycles.use_denoising = True
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8; sc.cycles.transmission_bounces = 4; sc.cycles.volume_bounces = 0
    sc.render.resolution_x = 720; sc.render.resolution_y = 1280; sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'


CONST = []
def make_props():
    P = {}; tex = os.environ['DA_TEX']; scr = os.environ['SCR']
    P['kid_phone'] = props.phone('kid_phone', os.path.join(scr, 'wallet.png')); seq(P['kid_phone'], os.path.join(scr, 'scr_shop'), 2.4)
    P['kid_phone2'] = props.phone('kid_phone2', os.path.join(scr, 'wallet.png')); seq(P['kid_phone2'], os.path.join(scr, 'scr_candle'), 25.0)
    P['dad_phone'] = props.phone('dad_phone', os.path.join(scr, 'wallet.png'))
    for k in ('kid_phone', 'kid_phone2', 'dad_phone'): CONST.append(P[k]['screen_mat'])
    P['mug'] = props.mug('dad_mug', (0.85, 0.85, 0.82)); P['mug'].location = (0.0, 0.26, ISL_H + P['mug']['H'] * 0.45)
    P['carafe'] = carafe('carafe')
    P['tv'] = assets.load('Television_01')[0]; P['tv'].scale = (0.85,) * 3
    return P


def seq(ph, folder, t0):
    sm = bpy.data.materials[ph['screen_mat']]; nt = sm.node_tree; tx = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    files = sorted(os.listdir(folder)); img = bpy.data.images.load(os.path.join(folder, files[0])); img.source = 'SEQUENCE'
    tx.image = img; iu = tx.image_user; iu.frame_duration = len(files); iu.frame_start = int(round(t0 * FPS)) + 1; iu.frame_offset = 0
    iu.use_auto_refresh = True; iu.use_cyclic = False


def carafe(name):
    """A glass coffee carafe with a black collar and handle, half full. Origin at the handle grip, +Z up."""
    g = wprops.lathe(name, [(0.0, -0.12), (0.07, -0.12), (0.075, -0.06), (0.07, 0.0), (0.045, 0.04), (0.042, 0.06), (0.0, 0.06)], segs=40)
    g.data.materials.append(wprops.glass_mat(name + '_glass'))
    c = wprops.liquid_mat(name + '_coffee', (0.12, 0.05, 0.02)); l = wprops.lathe(name + '_liq', [(0.0, -0.115), (0.065, -0.115), (0.07, -0.06), (0.0, -0.06)], segs=32)
    l.data.materials.append(c); l.parent = g
    col = wprops.lathe(name + '_collar', [(0.047, 0.035), (0.05, 0.035), (0.05, 0.065), (0.047, 0.065)], segs=32, cap_bottom=False)
    col.data.materials.append(props.mat(name + '_black', (0.02, 0.02, 0.02), 0.35)); col.parent = g
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.095, 0, -0.02)); h = bpy.context.active_object; h.scale = (0.018, 0.022, 0.11); h.parent = g
    h.data.materials.append(props.mat(name + '_hblack', (0.02, 0.02, 0.02), 0.35))
    for o in (g, l, col):
        for p in o.data.polygons: p.use_smooth = True
    g.location = (0, 0, 0)
    return g


HEADS = {}
def mw_of(k):
    x, y, face = SPOT[k]; return Matrix.Translation((x, y, 0)) @ Matrix.Rotation(face, 4, 'Z'), face


def grip_setup(A, P):
    for a in A.values(): a.G = {}
    for k in ('kid', 'dad'):
        c, M, w = grips.phone(A[k], 'L'); A[k].G['phone'] = (c, M)
    c, M, w = grips.cylinder(A['mom'], 'L', 0.012, -0.06, 0.04); A['mom'].G['carafe'] = (c, M)


def fingers(a, s, shape, Q):
    if isinstance(shape, tuple) and shape[0] == 'mix':
        _, s0, s1, w = shape; A0, B0 = {}, {}; fingers(a, s, s0, A0); fingers(a, s, s1, B0)
        for bn in set(A0) | set(B0): Q[bn] = A0.get(bn, Quaternion()).slerp(B0.get(bn, Quaternion()), w)
        return
    if shape in a.G:
        g = a.G[shape]; Q.update(grips.curlQ(a, s, g[0], g[1] if len(g) == 3 else None)); return
    sh = {'rest': dict(t=(0.15, 0.1, 0.1), i=(0.25, 0.3, 0.2), m=(0.3, 0.35, 0.25), r=(0.35, 0.4, 0.3), p=(0.4, 0.45, 0.3)),
          'flat': dict(t=(0.05, 0.05, 0.05), i=(0.04, 0.06, 0.04), m=(0.04, 0.06, 0.04), r=(0.06, 0.08, 0.04), p=(0.08, 0.1, 0.04)),
          'tap': dict(t=(0.3, 0.3, 0.2), i=(0.1, 0.15, 0.1), m=(0.9, 1.0, 0.6), r=(1.0, 1.0, 0.7), p=(1.05, 1.0, 0.7))}[shape]
    for fi, key in enumerate('timrp', start=1):
        for j in range(1, 4):
            bn = f'finger{fi}-{j}.{s}'
            if bn in a.curl_axis: Q[bn] = a.local_q(bn, rigctl.qrot(a.curl_axis[bn], sh[key][j - 1]))


def blend(F0, F1, k2, arc=Vector((0, -0.06, 0))):
    p = F0.translation.lerp(F1.translation, k2) + arc * math.sin(math.pi * k2)
    q = F0.to_quaternion().slerp(F1.to_quaternion(), k2); M = q.to_matrix().to_4x4(); M.translation = p; return M


def phone_frame(a, eyes, s, G, dist=0.3, drop=0.28):
    zup = Vector((0, 0, 1)); tgt = eyes + Vector((0, -1, 0)) * dist - zup * drop; n = (eyes - tgt).normalized()
    upp = (zup - n * zup.dot(n)).normalized(); X = upp * a.idx_sign[s]; Y = n.cross(X)
    F = a.frame(Vector(), Y, n); F.translation = tgt - F.to_3x3() @ G['phone'][1].translation; return F


def em_path(m):
    return 'nodes["Principled BSDF"].inputs["Emission Strength"].default_value'


PHONE_AT = {}
def solve(a, k, t, f, st, P, K):
    sx = {'L': 1, 'R': -1}
    mw, face = mw_of(k)
    on = PRESENT[k][0] <= t < PRESENT[k][1]
    K.add(a.rig, 'hide_render', 0, f, 0 if on else 1)
    for o in a.rig.children: K.add(o, 'hide_render', 0, f, 0 if on else 1)
    off = {'kid': 0.4, 'dad': 1.7, 'mom': 2.9, 'repo': 0.9}[k]
    root_loc = Vector((math.sin(t * 0.8 + off) * 0.007, 0, -0.004 + math.sin(t * 2.0 + off) * 0.003))
    Q = {}
    lean = math.radians({'kid': 10, 'dad': 6, 'mom': 3, 'repo': -4}[k]) + math.sin(t * 2.0 + off) * 0.01
    if k == 'kid' and t < MORNING: lean += math.radians(8)                 # hunched over the phone at night
    spk = speaker(t); tgt = None
    if spk and spk != k and spk in HEADS: tgt = HEADS[spk][f]
    lookdown = 0.0
    phone_k = k in ('kid', 'dad')
    if k == 'kid' and not (win(t, 18.2, 20.0) or win(t, 21.5, 23.6) or win(t, 23.6, 24.9)): lookdown = 0.55; tgt = None    # glued to the phone
    if k == 'dad' and win(t, 10.4, 16.2): lookdown = 0.45; tgt = None if t < 14.6 else tgt          # reading the wallet, then looks up at Mom
    if k == 'mom' and t > 16.4: tgt = HEADS['kid'][f] if t > 18.2 else HEADS['dad'][f]
    if k in ('dad', 'mom') and win(t, 23.6, 24.95): tgt = HEADS['repo'][f]                          # all eyes on the repo man
    if k == 'repo': tgt = HEADS['dad'][f]
    yawT = pitchT = 0.0; hp = HEADS[k][f]
    if tgt is not None:
        dv = tgt - hp; ang = math.atan2(dv.x, -dv.y) - face; ang = math.atan2(math.sin(ang), math.cos(ang))
        yawT = clamp(ang, -1.2, 1.2); pitchT = clamp(-math.atan2(dv.z, Vector((dv.x, dv.y)).length), -0.35, 0.45)
    pitchT += lookdown
    st['yaw'] = lerp(st['yaw'], yawT, 0.15); st['pitch'] = lerp(st['pitch'], pitchT, 0.15)
    for b, w in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), lean * w))
    tv = talk(k, t); nod = math.sin(t * 8 + off) * 0.03 * (tv > 0.1)
    yaw, pitch = st['yaw'], st['pitch'] + nod
    for b, w in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((0, 0, 1), yaw * w) @ rigctl.qrot((1, 0, 0), (pitch - lean * 0.9) * w))
    for s in 'LR': Q[f'eye.{s}'] = a.local_q(f'eye.{s}', rigctl.qrot((0, 0, 1), (yawT - yaw) * 0.8))
    blink = 1.0 if ((t + off) % 3.4) < 0.12 else 0.0
    wide = 0.0
    if k == 'mom' and win(t, 15.6, 18.2): wide = -0.12                                               # frozen, eyes wide
    lid = 0.55 * blink + (0.2 if (k == 'kid' and t < MORNING) else 0.05) + wide
    for s in 'LR':
        Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), lid))
        Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink))
    Q['jaw'] = a.local_q('jaw', rigctl.qrot((1, 0, 0), tv * 0.11))
    ph = math.sin(t * 13.0 + off) * 0.5 + 0.5
    shape = {'v_aa': tv * 0.38, 'v_ow': tv * 0.3 * ph, 'v_ee': tv * 0.25 * (1 - ph), 'v_mm': 0.25 if (0 < tv < 0.08) else 0.0, 'v_ff': 0.0}
    if k == 'kid' and t < MORNING: shape['v_ee'] = max(shape['v_ee'], 0.25)                           # the little grin
    feet, poles = {}, {}
    for s in 'LR':
        feet['foot', s] = mw @ a.rest[f'foot.{s}'].copy(); poles['foot', s] = mw @ Vector((a.hip[s].x + sx[s] * 0.05, -1.0, 0.5))
    head = a.fk(Q, root_loc, 'head')
    eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
    G = a.G; hands, shapes, place = {}, {}, {}
    def hang(s):
        sh = a.shoulder[s] + root_loc; return a.frame(sh + Vector((sx[s] * 0.07, -0.05, -(a.uarm + a.farm) * 0.93)), (0, -0.15, -1), (-sx[s], 0, 0))
    def on_counter(s, fwd_=0.48, out=0.18):
        return a.frame(Vector((sx[s] * out, -fwd_, ISL_H + 0.034)), (-sx[s] * 0.25, -1, -0.14), (0, -0.14, -1))
    for s in 'LR': hands[s] = hang(s); shapes[s] = 'rest'
    if phone_k:
        Fp = phone_frame(a, eyes, 'L', G, 0.26 if k == 'kid' else 0.32, 0.2 if k == 'kid' else 0.3)
        hands['L'] = Fp; shapes['L'] = 'phone'
        # the other hand: the kid's thumb taps the screen at night; Dad's hand rests on the island
        if k == 'kid':
            Mph = Fp @ G['phone'][1]
            tapping = t < MORNING or win(t, 24.95, 26.8)
            hit = 0.0
            if tapping:
                for tt in (2.65, 3.4, 4.0, 4.5, 4.9, 5.25, 5.55, 5.82, 6.08, 25.2, 25.6):
                    hit = max(hit, pulse(t, tt - 0.12, tt + 0.1, 0.08))
            tip = Mph @ Vector((0.0, -0.035, 0.0085 + 0.02 * (1 - hit)))
            Fr = a.frame(tip + Vector((-0.02, 0.07, -0.06)), (-0.3, -0.7, 0.6), (0.4, 0.4, 0.8)) if tapping else on_counter('R', 0.5, 0.2)
            hands['R'] = Fr; shapes['R'] = 'tap' if tapping else 'flat'
        else:
            hands['R'] = on_counter('R', 0.44, 0.2); shapes['R'] = 'flat'
        name = 'kid_phone' if (k == 'kid' and t < MORNING) else ('kid_phone2' if k == 'kid' else 'dad_phone')
        place[name] = Fp @ G['phone'][1]
        if k == 'kid': place['kid_phone2' if t < MORNING else 'kid_phone'] = None
        if k == 'dad': PHONE_AT[f] = mw @ (Fp @ G['phone'][1]) @ Vector((0, 0, 0.008))
        if k == 'kid' and on:
            Wp = mw @ (Fp @ G['phone'][1]); PHONE_AT.setdefault('kid', {})[f] = Wp @ Vector((0, 0, 0.008)); PHONE_AT.setdefault('kidn', {})[f] = (Wp.to_3x3() @ Vector((0, 0, 1))).normalized()
    if k == 'mom':
        # pouring Dad's coffee; at "312 times" she freezes, carafe still tilted over the mug
        cup = mw.inverted() @ Vector((0.0, 0.26, ISL_H + 0.2))
        tilt = 0.9 * ease(ramp(t, 14.4, 15.2))
        Mc = Matrix.Translation(cup + Vector((0.11, 0.0, 0.02))) @ Matrix.Rotation(tilt, 4, 'Y')
        Fc = Mc @ G['carafe'][1].inverted()
        hands['L'] = Fc; shapes['L'] = 'carafe'; place['carafe'] = Mc
        hands['R'] = on_counter('R', 0.42, 0.22); shapes['R'] = 'flat'
    if k == 'repo':
        # the family TV, carried out at chest height; a hand on each side
        Mt = Matrix.Translation((0.0, -0.36, 1.0))
        place['tv'] = Mt
        for s in 'LR':
            hands[s] = a.frame(Vector((sx[s] * 0.28, -0.36, 1.12)), (0, -0.4, -1), (-sx[s], 0, 0)); shapes[s] = 'flat'
    reach = (a.uarm + a.farm) * 0.985
    for s in 'LR':
        wpos = a.hand_matrix_for_palm(s, hands[s]).translation; sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation; dv = wpos - sh
        if dv.length > reach: hands[s] = Matrix.Translation(dv.normalized() * (reach - dv.length)) @ hands[s]
    for s in 'LR': fingers(a, s, shapes[s], Q)
    Hm = {('hand', s): mw @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
    for s in 'LR': poles['hand', s] = mw @ (a.shoulder[s] + root_loc + Vector((sx[s] * 0.6, 0.45, -0.5)))
    a.key_pose(f, mw, Q, root_loc, Hm, feet, poles, shape)
    for pk, M in place.items():
        ob = P[pk]
        hide = 1 if (M is None or not on) else 0
        K.add(ob, 'hide_render', 0, f, hide)
        for ch in ob.children_recursive:
            if ch.type == 'MESH': K.add(ch, 'hide_render', 0, f, hide)
        if hide: continue
        W = mw @ M; loc, q = W.translation, W.to_quaternion(); ob.rotation_mode = 'QUATERNION'
        for i in range(3): K.add(ob, 'location', i, f, loc[i])
        for i in range(4): K.add(ob, 'rotation_quaternion', i, f, q[i])
        if pk.endswith('phone') or pk.endswith('phone2'):
            sm = bpy.data.materials[ob['screen_mat']]; K.add(sm.node_tree, em_path(sm), 0, f, 3.2 if t < MORNING else 2.4)
            gl = bpy.data.objects[ob['glow']]; K.add(gl.data, 'energy', 0, f, 1.5 if t < MORNING else 0.8)
    for pk in [p for p in place if place[p] is None or not on]:
        ob = P[pk]
        if pk.endswith('phone') or pk.endswith('phone2'):
            gl = bpy.data.objects[ob['glow']]; K.add(gl.data, 'energy', 0, f, 0.0)


def make_camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24; cd.dof.use_dof = True
    cam.rotation_mode = 'QUATERNION'; return cam


def camera(cam, t, f, K):
    def shot(pos, tgt, fov, fstop=2.8):
        pos = Vector(pos); tgt = Vector(tgt); return pos, (tgt - pos).to_track_quat('-Z', 'Y'), fov, (tgt - pos).length, fstop
    def at(k, cam_xy, z=0.0, fov=30, tz=-0.1):
        h = HEADS[k][f]; return shot(Vector((cam_xy[0], cam_xy[1], h.z + z)), h + Vector((0, 0, tz)), fov)
    hd = Vector((math.sin(t * 1.3) * 0.005 + math.sin(t * 3.1) * 0.003, 0, math.sin(t * 1.7 + 1) * 0.004))
    kp = PHONE_AT.get('kid', {}).get(f, HEADS['kid'][f] + Vector((0, 0.3, -0.3)))
    kn = PHONE_AT.get('kidn', {}).get(f, Vector((0, -1, 0.5)).normalized())
    def screen_insert(dist=0.3):     # along the screen's facing, from a touch above: the screen always reads
        return shot(kp + kn * dist + Vector((0, 0, 0.05)), kp, 30, 4.0)
    if t < 2.4: k = ease(ramp(t, 0, 2.4)); r = shot(Vector((1.9, -3.1, 1.75)).lerp(Vector((1.3, -2.4, 1.6)), k), HEADS['kid'][f] + Vector((0, 0, -0.25)), 36, 4.0)
    elif t < 6.6: r = screen_insert(0.3)                                                               # the shop, her thumb tapping
    elif t < MORNING: r = at('kid', (-0.3, 0.05), -0.12, 28, -0.12)                                      # her face in the phone light
    elif t < 10.4: r = shot(Vector((-2.3, -2.9, 1.75)), Vector((0.0, 0.3, 1.25)), 40, 5.6)
    elif t < 13.6: r = at('dad', (0.55, -0.35), -0.05, 30, -0.15)
    elif t < 15.0: r = shot(HEADS['dad'][f] + Vector((0.2, 0.25, 0.22)), PHONE_AT.get(f, HEADS['dad'][f] + Vector((0, -0.3, -0.3))), 30, 4.0)
    elif t < 16.45: r = at('dad', (0.55, -0.4), -0.05, 30, -0.15)
    elif t < 18.25: r = at('mom', (-0.85, -0.55), 0.05, 40, -0.32)
    elif t < 19.95: r = at('kid', (-0.25, 0.1), 0.0, 30, -0.12)
    elif t < 21.6: r = at('dad', (0.5, -0.4), -0.02, 30, -0.12)
    elif t < 23.6: r = at('kid', (-0.45, 0.12), 0.0, 30, -0.12)
    elif t < 24.95: r = shot(Vector((-1.6, 0.7, 1.65)), Vector((2.6, -1.4, 1.35)), 38, 5.6)               # the repo man in the doorway
    elif t < ENDCARD: r = screen_insert(0.34)
    else: r = shot(Vector((-2.3, -2.9, 1.75)), Vector((0.0, 0.3, 1.25)), 40, 5.6)
    pos, q, fov, focus, fstop = r; pos = pos + hd
    for i in range(3): K.add(cam, 'location', i, f, pos[i])
    for i in range(4): K.add(cam, 'rotation_quaternion', i, f, q[i])
    K.add(cam.data, 'lens', 0, f, 12.0 / math.tan(math.radians(fov) / 2))
    K.add(cam.data, 'dof.focus_distance', 0, f, focus); K.add(cam.data, 'dof.aperture_fstop', 0, f, fstop)


def make_lights():
    sc = bpy.context.scene; L = {}
    def light(name, kind, loc, energy, color, size=0.3, tgt=None):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); o.data.energy = energy; o.data.color = color
        if kind == 'AREA': o.data.size = size
        elif kind != 'SUN': o.data.shadow_soft_size = size
        o.location = loc; sc.collection.objects.link(o)
        if tgt: o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        L[name] = o; return o
    light('sun', 'SUN', (0, 6, 5), 0.0, (1.0, 0.86, 0.66), tgt=(0.3, 0.0, 0.5)); L['sun'].data.angle = 0.03
    light('sky_fill', 'AREA', (-0.7, 2.2, 1.7), 0.0, (0.75, 0.85, 1.0), 1.8, (0, -1, 1.0))
    light('room_fill', 'AREA', (0.0, -1.5, 2.6), 0.0, (1.0, 0.95, 0.88), 3.0, (0, 0, 0))
    light('moon', 'AREA', (-0.7, 2.3, 1.8), 25.0, (0.45, 0.55, 1.0), 1.6, (0.0, -1.0, 0.9))
    light('cab_glow', 'AREA', (-1.8, BACKY(), 1.45), 6.0, (1.0, 0.75, 0.45), 1.2, (-1.8, 1.5, 0.9))
    for o in L.values(): o.visible_camera = False; o.visible_glossy = False
    return L


def BACKY(): return kitchen.BACK_Y - 0.3


def lights(L, t, f, K):
    m = 1.0 if t >= MORNING else 0.0
    K.add(L['sun'].data, 'energy', 0, f, 4.5 * m); K.add(L['sky_fill'].data, 'energy', 0, f, 120 * m); K.add(L['room_fill'].data, 'energy', 0, f, 90 * m)
    K.add(L['moon'].data, 'energy', 0, f, 60 * (1 - m)); K.add(L['cab_glow'].data, 'energy', 0, f, 14 * (1 - m))
    wt = bpy.context.scene.world.node_tree
    for i, (n, d_) in enumerate(zip((0.55, 0.72, 1.0), (0.02, 0.03, 0.06))): K.add(wt, 'nodes["Background"].inputs[0].default_value', i, f, n if m else d_)
    K.add(wt, 'nodes["Background"].inputs[1].default_value', 0, f, 2.5 if m else 1.0)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    setup_render()
    kitchen.build()
    A = {}
    for k in cast.KEYS:
        rig, body, parts = cast.build(k); A[k] = rigctl.Actor(k, rig, body); A[k].parts = parts
    P = make_props(); grip_setup(A, P)
    cam = make_camera(); L = make_lights()
    sc = bpy.context.scene; Kx = rigctl.Keys(); st = {k: dict(yaw=0.0, pitch=0.0) for k in A}
    frames = range(1, NF + 1)
    for k, a in A.items():
        mw, _ = mw_of(k)
        for f in frames: HEADS.setdefault(k, {})[f] = mw @ a.rest['head'].translation + Vector((0, 0, 0.08))
    for f in frames:
        t = T(f)
        for k, a in A.items(): solve(a, k, t, f, st[k], P, Kx)
        camera(cam, t, f, Kx); lights(L, t, f, Kx)
    for a in A.values(): a.K.flush()
    Kx.flush()
    for o in bpy.data.objects:
        if o.type == 'LIGHT': o.visible_camera = False; o.visible_glossy = False
    cut_frames = {int(math.ceil(c * FPS)) + 1 for c in CUTS}
    for idb in (cam, cam.data):
        for fc in idb.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cut_frames else 'LINEAR'
    const = [bpy.data.materials[n].node_tree for n in CONST] + [l.data for l in L.values()] + [sc.world.node_tree]
    for idb in const:
        ad = idb.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    json.dump(dict(lines=LINES, cuts=CUTS, end=END, endcard=ENDCARD, morning=MORNING), open(os.path.join(os.environ['W'], 'timeline.json'), 'w'), indent=1)
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False)
    print('SAVED', arg('--out'), NF, 'frames')


if __name__ == '__main__':
    main()
