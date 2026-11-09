"""CASH 4 GOLD (a Meme Royale commercial): builds the scene and keys every frame.
blender -b -P director.py -- --out scene.blend [--frames N]
Env: W, PH, DA_TEX, GD (folder with useless.glb and slerf.glb), VO (folder with vo.json), SCR (gameplay screen folders)."""
import bpy, sys, os, math, json, random
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'whale'), os.path.join(H, '..', 'degens')]
from mathutils import Vector, Matrix, Quaternion
import rigctl, grips, props, humans, wprops
import pawnshop, cast
from pawnshop import COUNTER_H

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
say('g_ring', 2.8); say('b_forty', 5.5); say('g_perfect', 6.95); say('m_harold', 8.9); say('b_ashes', 12.25); say('m_big', 14.55)
say('b_useless', 17.0); say('b_line', 19.4); say('b_free', 22.6); say('g_rugged', 27.15); say('m_look', 29.65); say('s_wen', 32.45)
END = 38.2; ENDCARD = 34.1
NF = int(arg('--frames', round(END * FPS)))
T = lambda f: (f - 1) / FPS
CUTS = [2.6, 5.35, 6.8, 8.7, 11.45, 14.4, 16.0, 19.2, 22.45, 25.45, 26.95, 29.5, 30.95, 32.3, ENDCARD]
SPOT = {'broker': (0.0, 0.58, 0.0), 'groom': (-0.72, -0.56, math.pi), 'grandma': (0.72, -0.56, math.pi)}
UNITS = {'useless': dict(loc=(-0.2, -0.13, COUNTER_H), rot=0.0, scale=0.34, show=15.95,
                         sched=[(0, 'idle', 0, 1, 9), (16.0, 'ready', 0.15, 1.0, 1), (17.4, 'lose', 0.3, 1.1, 1), (20.5, 'idle', 0.4, 1, 6), (30.95, 'win', 0.2, 1.0, 1), (34.6, 'idle', 0.4, 1, 3)]),
         'slerf': dict(loc=(1.35, -2.35, 0.0), rot=math.pi, scale=0.85, show=0.0,
                       sched=[(0, 'idle', 0, 0.8, 9), (32.3, 'hit', 0.06, 0.9, 1), (32.75, 'emote', 0.25, 1.0, 1, 40), (33.9, 'idle', 0.5, 0.8, 3)])}
SCREENS = {'broker': ('rug', 22.4), 'groom': ('battle', 26.9), 'grandma': ('candle', 29.4)}   # gameplay clip and its start


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
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8; sc.cycles.transmission_bounces = 6; sc.cycles.volume_bounces = 0
    sc.render.resolution_x = 720; sc.render.resolution_y = 1280; sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.1
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'


# ------------------------------------------------------------------ props
CONST = []
def make_props():
    P = {}
    P['cig'] = props.cigarette('broker_cig', os.environ['PH'])
    P['ring'] = ring('ring'); P['urn'] = urn('urn')
    tex = os.environ['DA_TEX']
    for k in ['broker', 'groom', 'grandma']:
        P[k + '_phone'] = props.phone(k + '_phone', wprops.screen_img(f'{tex}/pscr_{k}.png', 'alert'))
        CONST.append(P[k + '_phone']['screen_mat'])
        clip, t0 = SCREENS[k]; sequence_screen(P[k + '_phone'], os.path.join(os.environ['SCR'], 'scr_' + clip), t0)
    return P


def sequence_screen(ph, folder, t0):
    """Play a gameplay clip (PNG sequence) on the phone from time t0, holding its last frame."""
    sm = bpy.data.materials[ph['screen_mat']]; nt = sm.node_tree; tx = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    files = sorted(os.listdir(folder)); img = bpy.data.images.load(os.path.join(folder, files[0])); img.source = 'SEQUENCE'
    tx.image = img; iu = tx.image_user; iu.frame_duration = len(files); iu.frame_start = int(round(t0 * FPS)) + 1; iu.frame_offset = 0
    iu.use_auto_refresh = True; iu.use_cyclic = False


def ring(name):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0105, minor_radius=0.0018, major_segments=48, minor_segments=12)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(props.mat(name + '_gold', (1.0, 0.76, 0.33), rough=0.15, metal=1.0))
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.0032, subdivisions=3, location=(0.0105, 0, 0.002)); d = bpy.context.active_object
    d.name = name + '_stone'; d.data.materials.append(props.mat(name + '_diamond', (1, 1, 1), rough=0.0, trans=1.0, ior=2.4)); d.parent = o
    for p in o.data.polygons: p.use_smooth = True
    return o


def urn(name):
    """A brass cremation urn with its lid. Origin at the base, +Z up. Held at the body (R = 0.075)."""
    u = wprops.lathe(name, [(0.0, 0.0), (0.06, 0.0), (0.062, 0.012), (0.05, 0.03), (0.075, 0.09), (0.08, 0.15), (0.07, 0.2), (0.05, 0.225),
                            (0.052, 0.235), (0.0, 0.235)], segs=48)
    u.data.materials.append(props.mat(name + '_brass', (0.62, 0.42, 0.18), rough=0.28, metal=1.0))
    lid = wprops.lathe(name + '_lid', [(0.0, 0.235), (0.055, 0.235), (0.05, 0.255), (0.02, 0.27), (0.012, 0.29), (0.0, 0.295)], segs=48)
    lid.data.materials.append(u.data.materials[0]); lid.parent = u
    for o in (u, lid):
        for p in o.data.polygons: p.use_smooth = True
    u['R'] = 0.078; u['H'] = 0.295
    return u


# ------------------------------------------------------------------ actors
HEADS = {}; MOUTH = {}
def mw_of(k):
    x, y, face = SPOT[k]; return Matrix.Translation((x, y, 0)) @ Matrix.Rotation(face, 4, 'Z'), face


def grip_setup(A, P):
    for a in A.values(): a.G = {}
    a = A['broker']; c, sp, M, cl = grips.cigarette(a, 'R'); a.G['cig'] = (c, sp, M)
    c, M, w = grips.phone(a, 'L'); a.G['phone'] = (c, M)
    for k in ('groom', 'grandma'):
        c, M, w = grips.phone(A[k], 'L'); A[k].G['phone'] = (c, M)
    a = A['grandma']
    for s in 'LR':
        c, M, w = grips.cylinder(a, s, P['urn']['R'], 0.06, 0.16); a.G['urn' + s] = (c, M)


def fingers(a, s, shape, Q):
    if isinstance(shape, tuple) and shape[0] == 'mix':
        _, s0, s1, w = shape; A0, B0 = {}, {}; fingers(a, s, s0, A0); fingers(a, s, s1, B0)
        for bn in set(A0) | set(B0): Q[bn] = A0.get(bn, Quaternion()).slerp(B0.get(bn, Quaternion()), w)
        return
    if shape in a.G:
        g = a.G[shape]; Q.update(grips.curlQ(a, s, g[0], g[1] if len(g) == 3 else None)); return
    sh = {'rest': dict(t=(0.15, 0.1, 0.1), i=(0.25, 0.3, 0.2), m=(0.3, 0.35, 0.25), r=(0.35, 0.4, 0.3), p=(0.4, 0.45, 0.3)),
          'flat': dict(t=(0.05, 0.05, 0.05), i=(0.04, 0.06, 0.04), m=(0.04, 0.06, 0.04), r=(0.06, 0.08, 0.04), p=(0.08, 0.1, 0.04)),
          'push': dict(t=(0.3, 0.3, 0.2), i=(0.05, 0.1, 0.05), m=(0.7, 0.8, 0.5), r=(0.9, 0.9, 0.6), p=(0.95, 0.95, 0.6))}[shape]
    for fi, key in enumerate('timrp', start=1):
        for j in range(1, 4):
            bn = f'finger{fi}-{j}.{s}'
            if bn in a.curl_axis: Q[bn] = a.local_q(bn, rigctl.qrot(a.curl_axis[bn], sh[key][j - 1]))


def blend(F0, F1, k2, arc=Vector((0, -0.08, 0))):
    p = F0.translation.lerp(F1.translation, k2) + arc * math.sin(math.pi * k2)
    q = F0.to_quaternion().slerp(F1.to_quaternion(), k2); M = q.to_matrix().to_4x4(); M.translation = p; return M


def phone_frame(a, eyes, s, G, dist=0.33, drop=0.24, screen_dir=None, at=None):
    """Hand frame holding the phone in front of the face (screen toward the eyes), or, with screen_dir/at,
    held so the screen faces screen_dir with its centre at `at` (both in rig space)."""
    zup = Vector((0, 0, 1))
    if screen_dir is None:
        tgt = eyes + Vector((0, -1, 0)) * dist - zup * drop; n = (eyes - tgt).normalized()
    else:
        tgt = at; n = Vector(screen_dir).normalized()
    upp = (zup - n * zup.dot(n)).normalized(); X = upp * a.idx_sign[s]; Y = n.cross(X)
    F = a.frame(Vector(), Y, n); F.translation = tgt - F.to_3x3() @ G['phone'][1].translation
    return F


def em_path(m):
    nt = m.node_tree
    return 'nodes["Principled BSDF"].inputs["Emission Strength"].default_value' if 'Principled BSDF' in nt.nodes else 'nodes["em"].inputs["Strength"].default_value'


def solve(a, k, t, f, st, P, K):
    sx = {'L': 1, 'R': -1}
    mw, face = mw_of(k)
    off = {'broker': 0.4, 'groom': 1.7, 'grandma': 2.9}[k]
    root_loc = Vector((math.sin(t * 0.8 + off) * 0.008, 0, -0.004 + math.sin(t * 2.0 + off) * 0.003))
    Q = {}
    lean = math.radians({'broker': 8, 'groom': 6, 'grandma': 9}[k]) + math.sin(t * 2.0 + off) * 0.01
    # leaning in toward the glass / counter for their business
    if k == 'broker': lean += 0.12 * pulse(t, 16.0, 19.0, 0.5) + 0.08 * pulse(t, 22.45, 25.4, 0.4)
    # ---- gaze: whoever is talking (across the glass), the coin, the phone, the sloth
    spk = speaker(t); tgt = None
    if spk and spk != k and spk in HEADS: tgt = HEADS[spk][f]
    if spk == 'slerf' or (k == 'broker' and win(t, 19.2, 22.3)): tgt = HEADS['slerf'][f]
    if win(t, 15.95, 19.2) or win(t, 30.9, 32.3): tgt = Vector((-0.2, -0.13, COUNTER_H + 0.35))       # the coin on the counter
    if k == 'groom' and win(t, 2.8, 4.6): tgt = Vector((-0.6, -0.15, COUNTER_H))                        # his ring going under the glass
    lookdown = 0.0
    phone_up = 0.0
    if k == 'groom': phone_up = ease(ramp(t, 26.5, 26.95))
    if k == 'grandma': phone_up = ease(ramp(t, 29.0, 29.45))
    if k == 'broker': phone_up = pulse(t, 22.25, 27.1, 0.45)
    if k != 'broker' and phone_up > 0.3: tgt = None; lookdown = 0.45 * phone_up
    if k == 'grandma' and t > 29.6: lookdown = 0.25                     # showing the phone to Harold
    yawT = pitchT = 0.0
    hp = HEADS[k][f]
    if tgt is not None:
        dv = tgt - hp; ang = math.atan2(dv.x, -dv.y) - face; ang = math.atan2(math.sin(ang), math.cos(ang))
        yawT = clamp(ang, -1.1, 1.1); pitchT = clamp(-math.atan2(dv.z, Vector((dv.x, dv.y)).length), -0.35, 0.45)
    pitchT += lookdown
    st['yaw'] = lerp(st['yaw'], yawT, 0.15); st['pitch'] = lerp(st['pitch'], pitchT, 0.15)
    for b, w in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), lean * w))
    tv = talk(k, t); nod = math.sin(t * 8 + off) * 0.035 * (tv > 0.1)
    yaw, pitch = st['yaw'], st['pitch'] + nod
    for b, w in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((0, 0, 1), yaw * w) @ rigctl.qrot((1, 0, 0), (pitch - lean * 0.9) * w))
    for s in 'LR': Q[f'eye.{s}'] = a.local_q(f'eye.{s}', rigctl.qrot((0, 0, 1), (yawT - yaw) * 0.8))
    blink = 1.0 if ((t + off) % 3.6) < 0.12 else 0.0
    lid = 0.55 * blink + (0.22 if k == 'broker' else 0.05)          # the pawnbroker's heavy, bored lids
    for s in 'LR':
        Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), lid))
        Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink))
    Q['jaw'] = a.local_q('jaw', rigctl.qrot((1, 0, 0), tv * 0.11))
    ph = math.sin(t * 13.0 + off) * 0.5 + 0.5
    shape = {'v_aa': tv * 0.38, 'v_ow': tv * 0.3 * ph, 'v_ee': tv * 0.25 * (1 - ph), 'v_mm': 0.25 if (0 < tv < 0.08) else 0.0, 'v_ff': 0.0}
    if k == 'groom' and win(t, 27.0, 29.6): shape['v_ee'] = max(shape['v_ee'], 0.3)       # grinning at the phone
    feet, poles = {}, {}
    for s in 'LR':
        feet['foot', s] = mw @ a.rest[f'foot.{s}'].copy(); poles['foot', s] = mw @ Vector((a.hip[s].x + sx[s] * 0.05, -1.0, 0.5))
    head = a.fk(Q, root_loc, 'head')
    mouth = head @ (a.rest['head'].inverted() @ a.mouth)
    lip = head @ (a.rest['head'].inverted() @ getattr(a, 'lip', a.mouth))
    eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
    fwd = (head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, -1, 0)))).normalized()
    up = (head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, 0, 1)))).normalized()
    MOUTH[k] = (mw @ mouth, mw.to_3x3() @ fwd)
    G = a.G; hands, shapes, place = {}, {}, {}
    # the counter top in this person's rig space: its near edge is 0.25 m in front of them (the counter is at y = +/-0.31)
    def on_counter(s, fwd_=0.42, out=0.17):
        p = Vector((sx[s] * out, -fwd_, COUNTER_H + 0.034))
        return a.frame(p, (-sx[s] * 0.25, -1, -0.14), (0, -0.14, -1))
    for s in 'LR': hands[s] = on_counter(s); shapes[s] = 'flat'
    if k == 'broker':
        # a cigarette between two fingers, hand up by her shoulder; one drag, then the smoke
        Fc = a.frame(a.shoulder['R'] + root_loc + Vector((0.04, -0.2, 0.02)), (0.15, -0.35, 1.0), (0.85, 0.2, 0.0)); shapes['R'] = 'cig'
        hands['R'] = Fc
        drag = pulse(t, 11.5, 12.15, 0.22)
        if drag > 0.001:
            z = (fwd * math.cos(0.15) - up * math.sin(0.15)).normalized(); y = up - z * up.dot(z); x = y.cross(z)
            Ml = Matrix((x.normalized(), y.normalized(), z)).transposed().to_4x4(); Ml.translation = lip + z * 0.005
            hands['R'] = blend(Fc, Ml @ G['cig'][2].inverted(), drag, Vector((0.04, -0.08, 0)))
            if drag > 0.6: shape['v_mm'] = 0.45; shape['v_aa'] *= 0.3
        place['cig'] = hands['R'] @ G['cig'][2]
        if phone_up > 0.001:
            # holds the phone up to the glass, screen toward the customers (and us)
            at = Vector((0.38, -0.5, 1.47)); Fp = phone_frame(a, eyes, 'L', G, screen_dir=(0, -1, 0.05), at=at)
            hands['L'] = blend(on_counter('L'), Fp, phone_up, Vector((0, -0.05, 0.08))); shapes['L'] = ('mix', 'flat', 'phone', clamp(phone_up * 1.4))
            place['broker_phone'] = hands['L'] @ G['phone'][1] if phone_up > 0.6 else None
        else: place['broker_phone'] = None
    if k == 'groom':
        # slides his ring under the glass with two fingers, 2.9 - 4.5 s
        u = ease(ramp(t, 2.9, 4.4))
        rpos = Vector((-0.06, lerp(-0.34, -0.53, u), COUNTER_H + 0.0019))
        if t < 2.75: place['ring'] = None
        else: place['ring'] = Matrix.Translation(rpos)
        if win(t, 2.7, 4.8):
            Fr = a.frame(rpos + Vector((0.0, 0.07, 0.012)), (0.1, -1, -0.12), (0, 0, -1))
            k2 = pulse(t, 2.75, 4.75, 0.25); hands['R'] = blend(on_counter('R'), Fr, k2, Vector((0, 0, 0.05))); shapes['R'] = 'push'
        if phone_up > 0.001:
            Fp = phone_frame(a, eyes, 'L', G, 0.24, 0.3); hands['L'] = blend(on_counter('L'), Fp, phone_up); shapes['L'] = ('mix', 'flat', 'phone', clamp(phone_up * 1.4))
            place['groom_phone'] = hands['L'] @ G['phone'][1]
        else: place['groom_phone'] = None
    if k == 'grandma':
        # carries Harold in, sets him on the counter at 9.1 s, keeps a hand on the lid
        Mu_counter = Matrix.Translation((0.0, -0.47, COUNTER_H))
        Mu_held = Matrix.Translation((0.0, -0.3, 1.05)) @ Matrix.Rotation(0.0, 4, 'Z')
        set_k = ease(ramp(t, 8.75, 9.35))
        Mu = blend(Mu_held, Mu_counter, set_k, Vector((0, -0.03, 0.06)))
        place['urn'] = Mu
        for s in 'LR':
            R = P['urn']['R']; side = Vector((sx[s] * (R + 0.01), 0.0, 0.11))
            Fh = a.frame(Mu.translation + side, (0, -0.2, 1), (-sx[s], 0, 0)) if False else None
            Fg = Mu @ Matrix.Translation((sx[s] * 0.0, 0, 0)) @ (G['urn' + s][1].inverted())
            # turn the grip so each palm faces the urn from its own side
            Rz = Matrix.Rotation(math.radians(90 if s == 'L' else -90), 4, 'Z')
            Fg = Mu @ Rz @ G['urn' + s][1].inverted()
            keep = 1.0 - ease(ramp(t, 9.35, 9.9)) if s == 'R' else 1.0 - ease(ramp(t, 9.5, 10.1)) * 0.0
            if s == 'L' and t > 9.6: keep = 1.0 - ease(ramp(t, 9.6, 10.1))
            hands[s] = blend(on_counter(s, 0.33, 0.24), Fg, keep); shapes[s] = ('mix', 'flat', 'urn' + s, keep)
        if phone_up > 0.001:
            # holds the phone out toward the urn so Harold can see the GOD CANDLE (screen toward the counter)
            at = Vector((0.12, -0.42, 1.28)); Fp = phone_frame(a, eyes, 'L', G, screen_dir=(0.15, -0.6, 0.5), at=at)
            hands['L'] = blend(hands['L'], Fp, phone_up); shapes['L'] = ('mix', 'flat', 'phone', clamp(phone_up * 1.4))
            place['grandma_phone'] = hands['L'] @ G['phone'][1]
        else: place['grandma_phone'] = None
    # reach limit
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
        if M is None: K.add(ob, 'hide_render', 0, f, 1); continue
        if pk == 'ring' and t > 4.8: M = Matrix.Translation((-0.06, -0.53, COUNTER_H + 0.0019))       # it stays in the slot
        K.add(ob, 'hide_render', 0, f, 0)
        W = mw @ M; loc, q = W.translation, W.to_quaternion(); ob.rotation_mode = 'QUATERNION'
        for i in range(3): K.add(ob, 'location', i, f, loc[i])
        for i in range(4): K.add(ob, 'rotation_quaternion', i, f, q[i])
    pk = k + '_phone'
    if pk in P:
        on = place.get(pk) is not None
        sm = bpy.data.materials[P[pk]['screen_mat']]; K.add(sm.node_tree, em_path(sm), 0, f, 2.6 if on else 0.0)
        gl = bpy.data.objects[P[pk]['glow']]; K.add(gl.data, 'energy', 0, f, 3.5 if on else 0.0)
    if k == 'broker':
        em = bpy.data.materials[P['cig']['ember']]; K.add(em.node_tree, em_path(em), 0, f, 3.0 + 10 * pulse(t, 11.6, 12.1, 0.15))


# ------------------------------------------------------------------ smoke
# ------------------------------------------------------------------ camera
def make_camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24; cd.dof.use_dof = True
    cam.rotation_mode = 'QUATERNION'; return cam


def camera(cam, t, f, P, K):
    def shot(pos, tgt, fov, fstop=2.8):
        pos = Vector(pos); tgt = Vector(tgt); return pos, (tgt - pos).to_track_quat('-Z', 'Y'), fov, (tgt - pos).length, fstop
    def at(k, cam_xy, z=0.0, fov=30, tz=-0.1):
        h = HEADS[k][f]; return shot(Vector((cam_xy[0], cam_xy[1], h.z + z)), h + Vector((0, 0, tz)), fov)
    coin = Vector((-0.2, -0.13, COUNTER_H + 0.3))
    hd = Vector((math.sin(t * 1.3) * 0.005 + math.sin(t * 3.1) * 0.003, 0, math.sin(t * 1.7 + 1) * 0.004))
    if t < 2.6:
        k = ease(ramp(t, 0, 2.6)); r = shot(Vector((-1.2, -9.4, 1.5)).lerp(Vector((-1.4, -6.6, 1.65)), k), Vector((-1.45, -4.2, 1.75)), 36, 5.6)
    elif t < 5.35:   # the groom, through the glass from her side; his ring sliding in
        r = at('groom', (-0.45, 0.85), -0.05, 32, -0.18)
    elif t < 6.8: r = at('broker', (-0.3, -1.25), 0.0, 28)
    elif t < 8.7: r = at('groom', (-0.5, 0.8), 0.0, 28)
    elif t < 11.45: r = at('grandma', (0.45, 0.85), -0.05, 32, -0.2)
    elif t < 14.4: r = at('broker', (0.25, -1.2), 0.0, 28)
    elif t < 16.0: r = at('grandma', (0.5, 0.8), 0.0, 28)
    elif t < 19.2: r = shot(Vector((-0.05, -1.75, 1.45)), coin + Vector((0.2, 0.3, 0.15)), 36, 4.0)     # the coin, her behind the glass
    elif t < 22.45: r = shot(Vector((0.05, -0.25, 1.12)), SLERF_FACE, 40, 4.0)
    elif t < 25.45: r = at('broker', (0.1, -1.05), -0.08, 34, -0.18)
    elif t < 26.95:   # insert: the phone held against the glass
        pp = P['broker_phone'].matrix_world.translation if f > 0 else Vector((-0.12, 0.08, 1.47))
        r = shot(Vector((0.4, -0.36, 1.47)), PHONE_AT.get(f, Vector((0.38, 0.08, 1.47))), 32, 2.8)
    elif t < 29.5:    # over the groom's shoulder, down at his game
        pp = PHONE_AT_G.get(f, HEADS['groom'][f] + Vector((0, 0.3, -0.3)))
        r = shot(HEADS['groom'][f] + Vector((-0.22, -0.28, 0.2)), pp, 34, 4.0)
    elif t < 30.95: r = at('grandma', (0.85, 0.8), 0.14, 38, -0.22)
    elif t < 32.3: r = shot(Vector((-0.55, -1.7, 1.4)), coin + Vector((0.1, 0.25, 0.1)), 36, 4.0)
    elif t < ENDCARD: r = shot(Vector((0.15, -0.5, 1.08)), SLERF_FACE, 32, 4.0)
    else: r = shot(Vector((0.0, -3.4, 1.65)), Vector((0.0, 0.3, 1.35)), 40, 5.6)
    pos, q, fov, focus, fstop = r; pos = pos + hd
    for i in range(3): K.add(cam, 'location', i, f, pos[i])
    for i in range(4): K.add(cam, 'rotation_quaternion', i, f, q[i])
    K.add(cam.data, 'lens', 0, f, 12.0 / math.tan(math.radians(fov) / 2))
    K.add(cam.data, 'dof.focus_distance', 0, f, focus); K.add(cam.data, 'dof.aperture_fstop', 0, f, fstop)


PHONE_AT = {}; PHONE_AT_G = {}
SLERF_FACE = Vector((1.3, -1.95, 0.98))


def make_lights():
    sc = bpy.context.scene; L = {}
    def light(name, kind, loc, energy, color, size=0.3, tgt=None):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); o.data.energy = energy; o.data.color = color
        if kind == 'AREA': o.data.size = size
        else: o.data.shadow_soft_size = size
        o.location = loc; sc.collection.objects.link(o)
        if tgt: o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        L[name] = o; return o
    for i, (x, y) in enumerate(((-1.5, -2.4), (0, -2.4), (1.5, -2.4), (-1.5, 0.9), (0, 0.9), (1.5, 0.9))):
        light(f'tube{i}', 'AREA', (x, y, 2.86), 55 if y > 0 else 45, (0.82, 0.92, 1.0), 0.9, (x, y, 0))
    light('lamp', 'POINT', (1.1, 0.25, 1.42), 25, (1.0, 0.7, 0.4), 0.06)
    light('neon_y', 'AREA', (-1.45, -3.95, 2.0), 60, (1.0, 0.72, 0.2), 1.4, (-1.0, -1.5, 1.4))
    light('neon_r', 'AREA', (-1.45, -3.95, 1.35), 25, (1.0, 0.15, 0.2), 0.8, (-0.8, -1.5, 1.2))
    light('out_neon', 'AREA', (-1.45, -4.6, 2.0), 60, (1.0, 0.72, 0.2), 1.6, (-1.45, -7.0, 0.0))     # spill on the wet lot
    for o in L.values(): o.visible_camera = False; o.visible_glossy = False
    return L


def lights(L, t, f, K):
    # an old tube that stutters now and then
    st = 1.0 - 0.75 * (pulse(t, 7.3, 7.42, 0.02) + pulse(t, 20.6, 20.7, 0.02) + pulse(t, 20.8, 20.86, 0.02))
    K.add(L['tube1'].data, 'energy', 0, f, 45 * st)
    K.add(L['neon_y'].data, 'energy', 0, f, 60 * (0.93 + 0.07 * math.sin(t * 50) * math.sin(t * 7)))


# ------------------------------------------------------------------ build
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    setup_render()
    S = pawnshop.build()
    U = {}
    for n, u in UNITS.items():
        rig, mesh = cast.load_unit(os.path.join(os.environ['GD'], n + '.glb'), n)
        rig.location = u['loc']; rig.rotation_mode = 'XYZ'; rig.rotation_euler = (0, 0, u['rot']); rig.scale = (u['scale'],) * 3
        cast.schedule(rig, n, u['sched']); U[n] = (rig, mesh)
    A = {}
    for k in cast.KEYS:
        rig, body, parts = cast.build(k); A[k] = rigctl.Actor(k, rig, body); A[k].parts = parts
    P = make_props(); grip_setup(A, P)
    cam = make_camera(); L = make_lights()
    import smoke as SM
    puffs = SM.make('bsmoke', 14, 12.2)
    sc = bpy.context.scene; Kx = rigctl.Keys(); st = {k: dict(yaw=0.0, pitch=0.0) for k in A}
    frames = range(1, NF + 1)
    for k, a in A.items():
        mw, _ = mw_of(k)
        for f in frames: HEADS.setdefault(k, {})[f] = mw @ a.rest['head'].translation + Vector((0, 0, 0.08))
    for n, (rig, mesh) in U.items():
        hb = [b for b in rig.pose.bones if b.name.endswith('Head')]
        for f in frames:
            HEADS.setdefault(n, {})[f] = (rig.matrix_world @ hb[0].head) if hb else rig.matrix_world.translation + Vector((0, 0, 1.0))
    for n, (rig, mesh) in U.items():
        if UNITS[n]['show'] > 0:
            for f in frames:
                v = 1 if T(f) < UNITS[n]['show'] else 0
                Kx.add(rig, 'hide_render', 0, f, v); Kx.add(mesh, 'hide_render', 0, f, v)
    for f in frames:
        t = T(f)
        for k, a in A.items(): solve(a, k, t, f, st[k], P, Kx)
        # where the phones will be, for the inserts (keyed matrices are known after the solve of this frame)
        camera(cam, t, f, P, Kx); lights(L, t, f, Kx)
        SM.frame(puffs, MOUTH.get('broker') if t > 12.15 else None, t, f, Kx)
    for a in A.values(): a.K.flush()
    Kx.flush()
    # second camera pass for the phone inserts, now that the phones' keyed positions exist
    for f in frames:
        t = T(f)
        if 25.45 <= t < 29.5:
            sc.frame_set(f)
            PHONE_AT[f] = P['broker_phone'].matrix_world @ Vector((0, 0, 0.008))
            PHONE_AT_G[f] = P['groom_phone'].matrix_world @ Vector((0, 0, 0.008))
    K2 = rigctl.Keys()
    for f in frames:
        t = T(f)
        if 25.45 <= t < 29.5: camera(cam, t, f, P, K2)
    # merge: overwrite those camera keys
    for (idb, path, idx), pts in K2.d.items():
        fc = idb.animation_data.action.fcurves.find(path, index=idx)
        for fr_, val in pts:
            for kp in fc.keyframe_points:
                if int(round(kp.co.x)) == fr_: kp.co.y = val
        fc.update()
    cut_frames = {int(math.ceil(c * FPS)) + 1 for c in CUTS}
    for idb in (cam, cam.data):
        for fc in idb.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cut_frames else 'LINEAR'
    for m in [bpy.data.materials[n] for n in CONST]:
        ad = m.node_tree.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    json.dump(dict(lines=LINES, cuts=CUTS, end=END, endcard=ENDCARD), open(os.path.join(os.environ['W'], 'timeline.json'), 'w'), indent=1)
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False)
    print('SAVED', arg('--out'), NF, 'frames')


if __name__ == '__main__':
    main()
