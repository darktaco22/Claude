"""LAST WILL & TESTAMENT: builds the whole skit and keys every frame.
blender -b -P director.py -- --out scene.blend [--frames N]
Needs env: W (work dir), PH (Poly Haven), DA_TEX, WHALE (whale.glb), VO (folder with vo.json from voices.py)."""
import bpy, sys, os, math, json, random
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'degens')]
from mathutils import Vector, Matrix, Quaternion
import rigctl, grips, props, humans
import penthouse, whale, cast, wprops

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

# ------------------------------------------------------------------ the timeline (seconds)
LINES = []
def say(i, t): LINES.append(dict(id=i, who=VO[i]['who'], t=t, end=t + VO[i]['dur'], text=VO[i]['text']))
say('l_intro', 3.7); say('w_cons', 9.3); say('wi_weeks', 12.1); say('w_bear', 14.9); say('l_wife', 16.7)
say('wi_bags', 20.1); say('w_down', 21.3); say('s_house', 24.1); say('w_lev', 26.0); say('p_conf', 31.0)
say('w_orph', 33.6); say('w_twice', 35.6); say('w_hold', 37.7); say('wi_dump', 44.3); say('s_grave', 45.75)
say('l_exit', 47.45); say('w_dip', 56.35)
END = 57.6
NF = int(arg('--frames', round(END * FPS)))
T = lambda f: (f - 1) / FPS
fr = lambda t: int(round(t * FPS)) + 1
FLATLINE = 40.35; PING = 43.6; REVIVE = 56.0
CUTS = [3.6, 9.05, 11.95, 14.75, 16.55, 19.95, 21.1, 23.95, 25.8, 28.85, 30.15, 33.35, 37.35, 39.45, 40.3, 42.5, 44.1, 45.65, 47.25, 52.35, 55.9]
# where everyone stands (x, y) and what they face
SPOT = {'lawyer': (-0.55, -1.75), 'wife': (0.98, 0.42), 'son': (1.25, -1.0), 'priest': (-1.02, -0.35)}
WHALE_SCHED = [(0, 'idle', 0, 1, 3), (9.2, 'lose', 0.35, 1.15, 1), (13.6, 'idle', 0.5, 1, 3), (21.2, 'emote', 0.35, 1, 1),
               (24.0, 'idle', 0.5, 1, 1), (27.3, 'win', 0.3, 1.1, 1), (30.6, 'idle', 0.6, 1, 2), (35.5, 'emote', 0.3, 1.1, 1),
               (38.0, 'idle', 0.5, 1, 1), (39.55, 'attack1', 0.15, 1.0, 1), (FLATLINE, 'hit', 0.06, 1.0, 1), (40.9, 'die', 0.2, 0.9, 1, 48),
               (REVIVE, 'idle', 0.3, 1.0, 2)]
PHONE_HAND = {'lawyer': 'R', 'wife': 'R', 'son': 'R', 'priest': 'R'}


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


# ------------------------------------------------------------------ render settings
def setup_render():
    sc = bpy.context.scene; sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 8; sc.cycles.use_denoising = True
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8; sc.cycles.transmission_bounces = 4; sc.cycles.volume_bounces = 0
    sc.render.resolution_x = 720; sc.render.resolution_y = 1280; sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.2
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'


# ------------------------------------------------------------------ props
CONST = []
def make_props(A, R):
    P = {}
    P['will'] = wprops.will_paper('will')
    P['martini'] = wprops.martini('martini')
    P['decanter'] = wprops.decanter('decanter')
    P['vape'] = wprops.vape('vape')
    P['flask'] = wprops.flask('flask')
    P['cigar'] = wprops.cigar('cigar')
    tex = os.environ['DA_TEX']
    for k in ['lawyer', 'wife', 'son', 'priest']:
        P[k + '_phone'] = props.phone(k + '_phone', wprops.screen_img(f'{tex}/scr_{k}.png', 'alert'))
    P['whale_phone'] = props.phone('whale_phone', wprops.screen_img(f'{tex}/scr_whale.png', 'sell'))
    for k in ['lawyer', 'wife', 'son', 'priest', 'whale']: CONST.append(P[k + '_phone']['screen_mat'])
    # nightstand dressing: a tumbler of scotch, an ashtray, a candle pair
    ns = Vector((-1.12, 0.92, 0.70))
    t = wprops.tumbler('tumbler', 0.35); t.location = ns + Vector((0.12, -0.06, 0.0))
    ash = wprops.lathe('ashtray', [(0.0, 0.0), (0.06, 0.0), (0.065, 0.025), (0.05, 0.025), (0.045, 0.012), (0.0, 0.012)], segs=10)
    ash.data.materials.append(wprops.glass_mat('ashtray_glass', (0.75, 0.8, 0.85))); ash.location = ns + Vector((-0.1, -0.05, 0))
    P['tumbler'] = t
    # the heart monitor by the bed's right side, screen toward the room
    beats = heartbeat_times()
    strip = wprops.ecg_strip(f'{tex}/ecg.png', beats, END + 3.0)
    mon = wprops.monitor('monitor', strip, END + 3.0); mon.location = (0.95, 1.0, 0); mon.rotation_euler = (0, 0, math.radians(-25)); P['monitor'] = mon
    # the priest's collar tab and the widow's veil ride their bones
    P['collar'] = wprops.collar('collar'); P['veil'] = wprops.veil('veil')
    return P


def heartbeat_times():
    """72 bpm, racing as he reads the sell order, then nothing; one blip when he comes back."""
    out = []; t = 0.3
    while t < FLATLINE - 0.05:
        bpm = 72 if t < 37.6 else (72 + 90 * ramp(t, 37.6, 39.6))
        out.append(t); t += 60.0 / bpm
    out.append(55.85); t = REVIVE + 0.4
    while t < END + 3: out.append(t); t += 60.0 / 64
    return out


# ------------------------------------------------------------------ actors
def standing_mw(k, t):
    x, y = SPOT[k]
    tgt = Vector((0.0, 0.55, 1.3))           # the Whale's head
    if k == 'lawyer': tgt = Vector((0.1, 0.4, 1.2))
    d = tgt - Vector((x, y, 0)); face = math.atan2(d.x, -d.y)
    if k == 'wife' and t > 52.0:             # she turns in to the bed for the cigar
        x, y = lerp(x, 0.82, ease(ramp(t, 52.3, 52.9))), lerp(y, 0.5, ease(ramp(t, 52.3, 52.9)))
    return Matrix.Translation((x, y, 0)) @ Matrix.Rotation(face, 4, 'Z'), face


def grip_setup(A, P):
    G = {}
    for k, a in A.items(): a.G = {}
    a = A['wife']; c, M, w = grips.cylinder(a, 'L', P['martini']['R'], P['martini']['z0'], P['martini']['z1']); a.G['martini'] = (c, M)
    c, sp, M, cl = grips.cigarette(a, 'R', r=P['cigar']['R'] * 0.9); a.G['cig'] = (c, sp, M)
    a = A['son']; c, M, w = grips.cylinder(a, 'L', P['decanter']['R'], P['decanter']['z0'], P['decanter']['z1']); a.G['decanter'] = (c, M)
    c, sp, M, cl = grips.cigarette(a, 'R', r=P['vape']['R'] * 0.95); a.G['vape'] = (c, sp, M)
    a = A['priest']; c, M, w = grips.phone(a, 'L', W=P['flask']['W'], L=P['flask']['L'], D=P['flask']['D'], yoff=0.04); a.G['flask'] = (c, M)
    for k, a in A.items():
        c, M, w = grips.phone(a, PHONE_HAND[k]); a.G['phone'] = (c, M)


def fingers(a, s, shape, Q):
    if isinstance(shape, tuple) and shape[0] == 'mix':
        _, s0, s1, w = shape; A0, B0 = {}, {}; fingers(a, s, s0, A0); fingers(a, s, s1, B0)
        for bn in set(A0) | set(B0): Q[bn] = A0.get(bn, Quaternion()).slerp(B0.get(bn, Quaternion()), w)
        return
    if shape in a.G:
        g = a.G[shape]; Q.update(grips.curlQ(a, s, g[0], g[1] if len(g) == 3 else None)); return
    sh = {'rest': dict(t=(0.15, 0.1, 0.1), i=(0.25, 0.3, 0.2), m=(0.3, 0.35, 0.25), r=(0.35, 0.4, 0.3), p=(0.4, 0.45, 0.3)),
          'hold': dict(t=(0.1, 0.15, 0.1), i=(0.08, 0.12, 0.08), m=(0.08, 0.12, 0.08), r=(0.1, 0.14, 0.08), p=(0.12, 0.15, 0.08)),
          'reach': dict(t=(0.2, 0.15, 0.1), i=(0.15, 0.2, 0.1), m=(0.2, 0.25, 0.15), r=(0.5, 0.6, 0.4), p=(0.6, 0.7, 0.45))}[shape]
    for fi, key in enumerate('timrp', start=1):
        for j in range(1, 4):
            bn = f'finger{fi}-{j}.{s}'
            if bn in a.curl_axis: Q[bn] = a.local_q(bn, rigctl.qrot(a.curl_axis[bn], sh[key][j - 1]))


def blend(F0, F1, k2, arc=Vector((0, -0.1, 0))):
    p = F0.translation.lerp(F1.translation, k2) + arc * math.sin(math.pi * k2)
    q = F0.to_quaternion().slerp(F1.to_quaternion(), k2)
    M = q.to_matrix().to_4x4(); M.translation = p; return M


HEADS = {}        # per frame: world head positions (filled by the first pass)
MOUTH = {}
WHALE_MOUTH = {}  # per frame: the cigar's world matrix in his mouth


def solve_actor(a, k, t, f, st, P, K):
    sx = {'L': 1, 'R': -1}
    mw, face = standing_mw(k, t)
    off = {'lawyer': 0.3, 'wife': 2.2, 'son': 1.1, 'priest': 0.7}[k]
    # weight shift and breathing
    sway = math.sin(t * 0.9 + off) * 0.012
    root_loc = Vector((sway, 0, -0.004 + math.sin(t * 2.0 + off) * 0.003))
    Q = {}
    lean = math.radians({'lawyer': 2, 'wife': -2, 'son': -4, 'priest': 6}[k]) + math.sin(t * 2.0 + off) * 0.01
    # ---- gaze
    spk = speaker(t); tgt = None
    if spk == 'whale' or (spk is None and t < 52): tgt = Vector((0.0, 0.58, 1.32))
    elif spk and spk != k and spk in HEADS: tgt = HEADS[spk].get(f)
    lookdown = 0.0
    if k == 'lawyer' and (win(t, 3.7, 8.6) and not win(t, 7.3, 8.3) or win(t, 16.7, 19.6) or win(t, 47.4, 52.2) and not win(t, 50.3, 51.2)): lookdown = 0.5
    phone_up = ease(ramp(t, PING + 0.15 + off * 0.08, PING + 0.6 + off * 0.08)) * (1 - ease(ramp(t, 47.0, 47.5)) if k == 'lawyer' else 1)
    if k == 'wife': phone_up *= 1 - ease(ramp(t, 51.6, 52.1))
    if phone_up > 0.3: lookdown = max(lookdown, 0.45 * phone_up); tgt = None
    yawT = pitchT = 0.0
    hp = HEADS.get(k, {}).get(f, mw @ (a.rest['head'].translation))
    if tgt is not None:
        dv = tgt - hp; ang = math.atan2(dv.x, -dv.y) - face; ang = math.atan2(math.sin(ang), math.cos(ang))
        yawT = clamp(ang, -1.0, 1.0); pitchT = clamp(-math.atan2(dv.z, Vector((dv.x, dv.y)).length), -0.35, 0.35)
    pitchT = pitchT + lookdown
    if k == 'wife' and win(t, 52.4, 55.6): yawT, pitchT = 0.15, 0.25
    if k == 'son' and win(t, 28.9, 30.0): pitchT = -0.35         # head back for the swig
    if t > FLATLINE and t < PING and k != 'lawyer': pitchT = max(pitchT, 0.2)
    st['yaw'] = lerp(st['yaw'], yawT, 0.15); st['pitch'] = lerp(st['pitch'], pitchT, 0.15)
    for b, w in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), lean * w))
    tv = talk(k, t); nod = math.sin(t * 8 + off) * 0.035 * (tv > 0.1)
    yaw, pitch = st['yaw'], st['pitch'] + nod
    for b, w in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)):
        Q[b] = a.local_q(b, rigctl.qrot((0, 0, 1), yaw * w) @ rigctl.qrot((1, 0, 0), (pitch - lean * 0.9) * w))
    for s in 'LR': Q[f'eye.{s}'] = a.local_q(f'eye.{s}', rigctl.qrot((0, 0, 1), (yawT - yaw) * 0.8))
    blink = 1.0 if ((t + off) % 3.9) < 0.12 else 0.0
    lid = 0.55 * blink + (0.12 if k == 'priest' else 0.0)
    for s in 'LR':
        Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), lid))
        Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink))
    Q['jaw'] = a.local_q('jaw', rigctl.qrot((1, 0, 0), tv * 0.11))
    ph = math.sin(t * 13.0 + off) * 0.5 + 0.5
    shape = {'v_aa': tv * 0.38, 'v_ow': tv * 0.3 * ph, 'v_ee': tv * 0.25 * (1 - ph), 'v_mm': 0.25 if (0 < tv < 0.08) else 0.0, 'v_ff': 0.0}
    # ---- feet: planted at rest
    feet, poles = {}, {}
    for s in 'LR':
        Fm = a.rest[f'foot.{s}'].copy(); feet['foot', s] = mw @ Fm
        poles['foot', s] = mw @ Vector((a.hip[s].x + sx[s] * 0.05, -1.0, 0.5))
    # ---- head frame for mouth-bound actions
    head = a.fk(Q, root_loc, 'head')
    mouth = head @ (a.rest['head'].inverted() @ a.mouth)
    eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
    fwd = (head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, -1, 0)))).normalized()
    up = (head.to_3x3() @ (a.rest['head'].to_3x3().inverted() @ Vector((0, 0, 1)))).normalized()
    MOUTH[k] = (mw @ mouth, mw.to_3x3() @ fwd)
    hands, shapes, place = {}, {}, {}
    def hang(s):
        sh = a.shoulder[s] + root_loc
        pos = sh + Vector((sx[s] * 0.07, -0.05, -(a.uarm + a.farm) * 0.93))
        return a.frame(pos, (0, -0.15, -1), (-sx[s], 0, 0))
    def waist(s, fwd_=0.27, h=-0.40, out=0.07):
        sh = a.shoulder[s] + root_loc
        return a.frame(sh + Vector((sx[s] * out, -fwd_, h)), (-sx[s] * 0.2, -1, 0.05), (-sx[s], 0, 0.15))
    for s in 'LR': hands[s] = hang(s); shapes[s] = 'rest'
    def to_lips(M_tip_local, z_axis_tilt, F_hold, prop_local):
        """Hand frame that puts a prop point (in prop space) at the lips, prop axis tilted up toward the face."""
        z_m = (up * math.cos(z_axis_tilt) - fwd * math.sin(z_axis_tilt)).normalized()
        xx = (F_hold @ prop_local).to_3x3().col[0]; xx = (xx - z_m * xx.dot(z_m)).normalized(); yy = z_m.cross(xx)
        Rm = Matrix((xx, yy, z_m)).transposed(); Mm = Rm.to_4x4(); Mm.translation = mouth + fwd * 0.004 - Rm @ M_tip_local
        return Mm @ prop_local.inverted(), Mm
    G = a.G
    # ---- who holds what
    if k == 'lawyer':
        # the will, both hands, reading height; the right hand leaves for the phone at the ping
        cen = a.shoulder['L'].lerp(a.shoulder['R'], 0.5) + root_loc + Vector((0, -0.33, -0.22))
        tilt = math.radians(55)
        nrm = Vector((0, -math.sin(tilt), math.cos(tilt)))      # page normal: up and toward his face
        Mw = Matrix.Translation(cen) @ Matrix.Rotation(-math.radians(35), 4, 'X')
        for s in 'LR':
            edge = cen + Vector((sx[s] * 0.115, 0.0, 0.0))
            hands[s] = a.frame(edge + Vector((sx[s] * 0.012, -0.02, -0.02)), (-sx[s] * 0.3, -0.6, 0.5), (-sx[s] * 0.8, 0, 0.5)); shapes[s] = 'hold'
        place['will'] = Mw
        if phone_up > 0.01:
            Fp = phone_frame(a, eyes, 'R', G); hands['R'] = blend(hands['R'], Fp, phone_up); shapes['R'] = ('mix', 'hold', 'phone', clamp(phone_up * 1.5))
            # the will drops to his left side, held in one hand
            Mw2 = Matrix.Translation(cen + Vector((0.18, 0.05, -0.2))) @ Matrix.Rotation(-math.radians(80), 4, 'X')
            place['will'] = blend(Mw, Mw2, phone_up, Vector())
            hands['L'] = blend(hands['L'], Mw2 @ Matrix.Translation((0.115, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Y'), phone_up, Vector())
    if k == 'wife':
        F = waist('L', 0.24, -0.33, 0.04); hands['L'] = F; shapes['L'] = 'martini'
        Mm = F @ G['martini'][1]
        sip = pulse(t, 10.4, 11.3, 0.3)
        if sip > 0.001:
            Fl, _ = to_lips(Vector((P['martini']['rim_r'] * 0.8, 0, P['martini']['rim'])), 0.9, F, G['martini'][1])
            hands['L'] = blend(F, Fl, sip); Mm = hands['L'] @ G['martini'][1]
        place['martini'] = Mm
        # the cigar: taken from his mouth, to her lips, a drag, held off to the side
        if t >= 52.4:
            grab = ease(ramp(t, 52.5, 53.1)); bring = ease(ramp(t, 53.25, 53.9)); away = ease(ramp(t, 55.0, 55.5))
            Wc = WHALE_MOUTH.get(f)
            Fhold = waist('R', 0.25, -0.18, 0.12); shapes['R'] = ('mix', 'reach', 'cig', clamp(grab * 1.4))
            if Wc is not None and bring < 0.001:
                Fg = mw.inverted() @ Wc @ G['cig'][2].inverted()          # palm frame that holds the cigar where it is
                hands['R'] = blend(hang('R'), Fg, grab, Vector((0, -0.12, 0.08)))
                if grab >= 0.999: place['cigar'] = Fg @ G['cig'][2]
            else:
                c_l = Vector((0, 0, 0.004))
                z_m = (fwd * math.cos(0.3) - up * math.sin(0.3)).normalized(); yy = up - z_m * up.dot(z_m); xx = yy.cross(z_m)
                Ml = Matrix((xx.normalized(), yy.normalized(), z_m)).transposed().to_4x4(); Ml.translation = mouth + fwd * 0.004
                Fl = Ml @ G['cig'][2].inverted()
                Fg = mw.inverted() @ (Wc if Wc is not None else (mw @ Ml)) @ G['cig'][2].inverted()
                Fh = blend(Fg, Fl, bring, Vector((0.05, -0.06, 0.04)))
                hands['R'] = blend(Fh, Fhold, away, Vector((0.0, -0.05, 0)))
                place['cigar'] = hands['R'] @ G['cig'][2]
                shapes['R'] = 'cig'
                if win(t, 53.9, 55.0): shape['v_mm'] = 0.45; shape['v_aa'] = 0.0
    if k == 'son':
        F = waist('L', 0.2, -0.36, 0.05); hands['L'] = F; shapes['L'] = 'decanter'
        Md = F @ G['decanter'][1]
        swig = pulse(t, 28.95, 30.05, 0.3)
        if swig > 0.001:
            Fl, _ = to_lips(Vector((0, 0.013, P['decanter']['lip'])), 1.35, F, G['decanter'][1])
            hands['L'] = blend(F, Fl, swig); Md = hands['L'] @ G['decanter'][1]
        place['decanter'] = Md
        Fv = waist('R', 0.18, -0.42, 0.08); hands['R'] = Fv; shapes['R'] = 'vape'
        hit = pulse(t, 20.4, 21.2, 0.25)          # a pull while his mother talks (seen over her shoulder)
        if hit > 0.001:
            Fl, _ = to_lips(Vector((0, 0, P['vape']['tip'])), 0.25, Fv, G['vape'][2]); hands['R'] = blend(Fv, Fl, hit)
        place['vape'] = hands['R'] @ G['vape'][2] if t < PING else None
        if t >= PING: shapes['R'] = 'rest'
    if k == 'priest':
        F = waist('L', 0.22, -0.38, 0.05); hands['L'] = F; shapes['L'] = 'flask'
        Mf = F @ G['flask'][1]
        nip = pulse(t, 30.15, 30.95, 0.25)
        if nip > 0.001:
            Fl, _ = to_lips(Vector((0, P['flask']['L'] * 0.55, 0)), 0.0, F, G['flask'][1] @ Matrix.Rotation(-math.pi / 2, 4, 'X'))
            hands['L'] = blend(F, Fl, nip); Mf = hands['L'] @ G['flask'][1]
        place['flask'] = Mf
        hands['R'] = a.frame(a.shoulder['R'] + root_loc + Vector((0.02, -0.22, -0.32)), (0.4, -0.7, 0.3), (0.6, 0, 0.6)); shapes['R'] = 'rest'
    # ---- phones (all at the ping)
    ph = PHONE_HAND[k]
    if k != 'lawyer':
        if phone_up > 0.01 and not (k == 'wife' and t > 52.1):
            Fp = phone_frame(a, eyes, ph, G); hands[ph] = blend(hands[ph], Fp, phone_up); shapes[ph] = ('mix', shapes[ph], 'phone', clamp(phone_up * 1.5))
            place[k + '_phone'] = hands[ph] @ G['phone'][1]
        else:
            place[k + '_phone'] = None
    else:
        place[k + '_phone'] = (hands['R'] @ G['phone'][1]) if phone_up > 0.01 else None
    # ---- reach limit
    reach = (a.uarm + a.farm) * 0.985
    for s in 'LR':
        wpos = a.hand_matrix_for_palm(s, hands[s]).translation; sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation
        dv = wpos - sh
        if dv.length > reach:
            delta = dv.normalized() * (reach - dv.length); hands[s] = Matrix.Translation(delta) @ hands[s]
            for pk, M in list(place.items()):
                if M is not None and pk != 'will' and owner(k, pk) == s: place[pk] = Matrix.Translation(delta) @ M
    for s in 'LR': fingers(a, s, shapes[s], Q)
    Hm = {('hand', s): mw @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
    for s in 'LR': poles['hand', s] = mw @ (a.shoulder[s] + root_loc + Vector((sx[s] * 0.6, 0.45, -0.5)))
    a.key_pose(f, mw, Q, root_loc, Hm, feet, poles, shape)
    for pk, M in place.items():
        ob = P[pk]
        if M is None: K.add(ob, 'hide_render', 0, f, 1); continue
        K.add(ob, 'hide_render', 0, f, 0)
        W = mw @ M; loc, q = W.translation, W.to_quaternion(); ob.rotation_mode = 'QUATERNION'
        for i in range(3): K.add(ob, 'location', i, f, loc[i])
        for i in range(4): K.add(ob, 'rotation_quaternion', i, f, q[i])
    if k.endswith('') and (k + '_phone') in P:
        sm = bpy.data.materials[P[k + '_phone']['screen_mat']]
        K.add(sm.node_tree, em_path(sm), 0, f, 3.0 if place.get(k + '_phone') is not None and t >= PING else 0.0)
        gl = bpy.data.objects[P[k + '_phone']['glow']]; K.add(gl.data, 'energy', 0, f, 5.0 if place.get(k + '_phone') is not None and t >= PING else 0.0)
    if k == 'son':
        lm = bpy.data.materials[P['vape']['led']]; K.add(lm.node_tree, em_path(lm), 0, f, 6.0 * pulse(t, 20.5, 21.1, 0.05))


def owner(k, pk):
    return {('wife', 'martini'): 'L', ('wife', 'cigar'): 'R', ('son', 'decanter'): 'L', ('son', 'vape'): 'R', ('priest', 'flask'): 'L'}.get((k, pk), PHONE_HAND[k] if pk.endswith('phone') else None)


def phone_frame(a, eyes, s, G):
    flat = Vector((0, -1, 0)); zup = Vector((0, 0, 1))
    tgt = eyes + flat * 0.33 - zup * 0.24
    n = (eyes - tgt).normalized(); upp = (zup - n * zup.dot(n)).normalized()
    X = upp * a.idx_sign[s]; Y = n.cross(X)
    F = a.frame(Vector(), Y, n); F.translation = tgt - F.to_3x3() @ G['phone'][1].translation
    return F


def em_path(m, node='Principled BSDF', sock='Emission Strength'):
    nt = m.node_tree
    if node in nt.nodes: return f'nodes["{node}"].inputs["{sock}"].default_value'
    return 'nodes["em"].inputs["Strength"].default_value'


# ------------------------------------------------------------------ the Whale's cigar and phone, smoke
def whale_frame(WR, WM, P, t, f, K):
    """The cigar sits in the corner of his mouth (rigid to his head bone) until the widow takes it; his phone
    lies on the duvet by his right fin, lit from the buzz until the sell."""
    hb = WR.pose.bones['mixamorig:Head']; Mh = WR.matrix_world @ hb.matrix
    Mc = Mh @ CIG_LOCAL
    WHALE_MOUTH[f] = Mc
    if t < 53.1:
        ob = P['cigar']; K.add(ob, 'hide_render', 0, f, 0); ob.rotation_mode = 'QUATERNION'
        loc, q = Mc.translation, Mc.to_quaternion()
        for i in range(3): K.add(ob, 'location', i, f, loc[i])
        for i in range(4): K.add(ob, 'rotation_quaternion', i, f, q[i])
    em = bpy.data.materials[P['cigar']['ember']]
    K.add(em.node_tree, em_path(em), 0, f, 3.0 + 9.0 * pulse(t, 53.95, 54.9, 0.2) + 1.5 * math.sin(t * 2.1) ** 2)
    sm = bpy.data.materials[P['whale_phone']['screen_mat']]
    lit = 37.35 <= t < FLATLINE + 1.2
    K.add(sm.node_tree, em_path(sm), 0, f, 2.6 if lit else 0.0)
    gl = bpy.data.objects[P['whale_phone']['glow']]; K.add(gl.data, 'energy', 0, f, 1.4 if lit else 0.0)


CIG_LOCAL = Matrix()


def make_smoke(name, n, t0, life=3.0, seed=5, color=(0.82, 0.82, 0.85)):
    m = bpy.data.materials.get('smoke') or _smoke_mat()
    rr = random.Random(seed); puffs = []
    for i in range(n):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
        o = bpy.context.active_object; o.name = f'{name}{i}'; o.data.materials.append(m); o.visible_shadow = False
        puffs.append(dict(o=o, b=t0 + i * 0.045, vx=rr.uniform(-0.06, 0.1), vy=rr.uniform(0.08, 0.18), vz=rr.uniform(0.1, 0.2), s=rr.uniform(0.7, 1.2), life=life))
    return puffs


def _smoke_mat():
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
    return m


def smoke_frame(puffs, src, t, f, K):
    for p in puffs:
        o = p['o']; age = t - p['b']; L = p['life']
        if age < 0 or age > L or src is None:
            K.add(o, 'hide_render', 0, f, 1); K.add(o, 'color', 3, f, 0.0)
            for i in range(3): K.add(o, 'scale', i, f, 0.01)
            continue
        K.add(o, 'hide_render', 0, f, 0)
        o0, fw = src; side = fw.cross(Vector((0, 0, 1))).normalized()
        pos = o0 + fw * (0.04 + p['vy'] * age) + side * (p['vx'] * age) + Vector((0, 0, p['vz'] * age * 0.9 - 0.02))
        sz = (0.022 + age * 0.085) * p['s']
        for i in range(3): K.add(o, 'location', i, f, pos[i]); K.add(o, 'scale', i, f, sz)
        K.add(o, 'color', 3, f, (1 - age / L) ** 1.5 * 0.85 * clamp(age / 0.1))


# ------------------------------------------------------------------ camera
def make_camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24; cd.dof.use_dof = True
    cam.rotation_mode = 'QUATERNION'; return cam


def camera(cam, t, f, K):
    def shot(pos, tgt, fov, fstop=2.8, focus=None):
        pos = Vector(pos); tgt = Vector(tgt); return pos, (tgt - pos).to_track_quat('-Z', 'Y'), fov, (focus or (tgt - pos).length), fstop
    def single(k, dx, dy, dz=0.05, fov=30, drift=0.0, tz=-0.12):
        h = HEADS[k][f]; p = h + Vector((dx, dy, dz)) + Vector((dx, dy, 0)).normalized() * -drift
        return shot(p, h + Vector((0, 0, tz)), fov)
    WH = HEADS['whale'][f]; WF = WH + Vector((0, -0.25, 0.05))          # his face is well in front of the head bone
    def ws(dx, dist, dz, fov, tz=0.0):      # along his upturned face: from in front and above
        p = WF + Vector((dx, -dist * 0.84, dist * 0.55 + dz)); p.z = min(p.z, 2.55)
        return shot(p, WF + Vector((0, 0, tz - 0.1)), fov)
    def at(k, cam_xy, z=0.0, fov=30, tz=-0.12, fstop=2.8):
        h = HEADS[k][f]; return shot(Vector((cam_xy[0], cam_xy[1], h.z + z)), h + Vector((0, 0, tz)), fov, fstop)
    hd = Vector((math.sin(t * 1.3) * 0.006 + math.sin(t * 3.1) * 0.003, 0, math.sin(t * 1.7 + 1) * 0.005))
    if t < 3.6:          # rain on the window, sliding right and down onto the bed
        k = ease(ramp(t, 0.0, 3.6))
        r = shot(Vector((-2.15, -0.6, 1.95)).lerp(Vector((0.55, -3.4, 1.85)), k), Vector((-2.2, 1.3, 1.85)).lerp(Vector((-0.15, 0.6, 1.0)), k), lerp(34, 40, k), 4.0)
    elif t < 9.05: r = at('lawyer', (0.0 - ramp(t, 3.6, 9.05) * 0.08, -0.45 - ramp(t, 3.6, 9.05) * 0.12), 0.05, 32)
    elif t < 11.95: r = ws(0.45, 2.7, 0.35, 30)
    elif t < 14.75: r = at('wife', (0.05, -0.62), 0.0, 30)
    elif t < 16.55: r = ws(-0.3, 2.2, 0.3, 28)
    elif t < 19.95: r = at('lawyer', (0.05, -0.5 - ramp(t, 16.55, 19.95) * 0.1), 0.05, 30)
    elif t < 21.1: r = at('wife', (0.15, -0.5), 0.0, 26)
    elif t < 23.95: r = ws(0.55, 2.9, 0.4, 32)
    elif t < 25.8: r = at('son', (0.35, -0.05), 0.0, 30)
    elif t < 28.85: r = ws(-0.15, 3.3 - ramp(t, 25.8, 28.85) * 0.5, 0.45, 34)
    elif t < 30.15: r = at('son', (0.4, -0.15), 0.05, 32)
    elif t < 33.35: r = at('priest', (-0.25, 0.25), 0.08, 32)
    elif t < 37.35: r = ws(0.3, 2.3 - ramp(t, 33.35, 37.35) * 0.3, 0.3, 28)
    elif t < 39.45: r = ws(0.7, 2.0, 0.2, 28)
    elif t < 40.3:       # insert: the phone on the duvet, SELL ALL, the fin coming down
        pp = PHONE_POS.get(f, WH + Vector((0.4, -0.3, -0.6)))
        r = shot(pp + Vector((0.05, -0.32, 0.38)), pp, 30, 2.8)
    elif t < 42.5:       # the flatline: him and the monitor
        k = ramp(t, 40.3, 42.5); r = shot(Vector((-0.45, -2.3, 1.7)).lerp(Vector((-0.35, -2.0, 1.65)), k), Vector((0.3, 0.6, 1.05)), 40, 4.0)
    elif t < 44.1: r = shot(Vector((0.2, -3.6, 1.7)), Vector((0.0, 0.2, 0.95)), 42, 5.6)
    elif t < 45.65: r = at('wife', (0.2, -0.3), -0.02, 30, -0.15)     # widow and son, each lit by a phone
    elif t < 47.25: r = at('son', (0.3, -0.25), 0.02, 30, -0.15)
    elif t < 52.35: r = at('lawyer', (0.1, -0.5 - ramp(t, 47.25, 52.35) * 0.15), 0.05, 30)
    elif t < 55.9:       # the widow takes the cigar
        a = HEADS['wife'][f]; c = a.lerp(WF, 0.4)
        r = shot(Vector((0.75, -1.45, 1.6)), c + Vector((0, 0, -0.1)), 36, 4.0)
    else: r = ws(0.15, 2.0, 0.25, 26 - ramp(t, 55.9, END) * 3)
    pos, q, fov, focus, fstop = r; pos = pos + hd
    for i in range(3): K.add(cam, 'location', i, f, pos[i])
    for i in range(4): K.add(cam, 'rotation_quaternion', i, f, q[i])
    K.add(cam.data, 'lens', 0, f, 12.0 / math.tan(math.radians(fov) / 2))
    K.add(cam.data, 'dof.focus_distance', 0, f, focus); K.add(cam.data, 'dof.aperture_fstop', 0, f, fstop)


PHONE_POS = {}


# ------------------------------------------------------------------ lights
def make_lights():
    sc = bpy.context.scene; L = {}
    def light(name, kind, loc, energy, color, size=0.3, tgt=None, spot=None):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); o.data.energy = energy; o.data.color = color
        if kind == 'AREA': o.data.size = size
        elif kind in ('POINT', 'SPOT'): o.data.shadow_soft_size = size
        if spot: o.data.spot_size = spot; o.data.spot_blend = 0.6
        o.location = loc; sc.collection.objects.link(o)
        if tgt: o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        L[name] = o; return o
    light('candle', 'POINT', (-1.2, 0.95, 1.05), 45, (1.0, 0.58, 0.28), 0.05)
    light('lamp_fill', 'AREA', (-1.6, -1.2, 2.4), 110, (1.0, 0.72, 0.45), 1.5, (0, 0.4, 1.0))
    light('monitor_glow', 'AREA', (0.9, 0.82, 1.38), 6, (0.3, 1.0, 0.55), 0.3, (0.1, 0.2, 1.2))
    light('city', 'AREA', (-2.2, 1.0, 1.9), 55, (0.45, 0.55, 0.95), 1.6, (0.3, -0.5, 1.0))
    light('room', 'AREA', (0.6, -2.8, 3.0), 60, (0.85, 0.7, 0.6), 2.5, (0.3, 0.0, 1.0))
    light('rim', 'AREA', (1.7, 1.5, 2.5), 45, (0.65, 0.72, 1.0), 1.0, (0, 0.3, 1.1))
    light('lightning', 'AREA', (-2.2, 3.5, 3.2), 0, (0.8, 0.85, 1.0), 4.0, (0, -1.0, 0.8))
    for o in L.values(): o.visible_camera = False; o.visible_glossy = False
    return L


FLASHES = [(0.7, 1.0), (1.0, 0.6), (FLATLINE + 0.05, 1.0), (FLATLINE + 0.25, 0.7), (REVIVE + 0.05, 0.6)]
def lights(L, t, f, K):
    fl = sum(s * math.exp(-max(0.0, t - t0) / 0.06) * (t >= t0) for t0, s in FLASHES)
    K.add(L['lightning'].data, 'energy', 0, f, 2500 * fl)
    K.add(L['candle'].data, 'energy', 0, f, 45 * (0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7.7)))
    K.add(L['monitor_glow'].data, 'color', 1, f, 1.0 if t < FLATLINE or t > 55.8 else 0.85)


def monitor_frame(P, t, f, K):
    m = bpy.data.materials[P['monitor']['screen_mat']]; mp = m.node_tree.nodes['scroll']
    total = END + 3.0; ws = P['monitor']['win_s']
    K.add(m.node_tree, 'nodes["scroll"].inputs["Location"].default_value', 0, f, (t - ws * 0.85) / total)


# ------------------------------------------------------------------ build
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    setup_render()
    S = penthouse.build()
    WR, WM = whale.load(os.environ['WHALE']); whale.place(WR); whale.schedule(WR, WHALE_SCHED)
    A = {}
    for k in cast.KEYS:
        rig, body, parts = cast.build(k); A[k] = rigctl.Actor(k, rig, body); A[k].parts = parts
    P = make_props(A, WR)
    grip_setup(A, P)
    cam = make_camera(); L = make_lights()
    smoke = make_smoke('wsmoke', 14, 54.85)
    global CIG_LOCAL
    CIG_LOCAL = cigar_local(WR)
    # the duvet, from his body over the whole clip schedule (never cuts into him)
    pts = whale.body_points(WM, range(1, NF + 1, 4))
    penthouse.duvet(pts, top_z=whale.HIP.z + 0.17)
    # the Whale's phone, on the duvet by his right fin
    place_whale_phone(WR, P)
    # collar and veil on their bones
    dress(A, P)
    # ---- pass 0: heads per frame (for gazes and singles)
    sc = bpy.context.scene; Kx = rigctl.Keys(); st = {k: dict(yaw=0.0, pitch=0.0) for k in A}
    frames = range(1, NF + 1)
    for f in frames:
        sc.frame_set(f); hb = WR.pose.bones['mixamorig:Head']
        HEADS.setdefault('whale', {})[f] = WR.matrix_world @ hb.head + (WR.matrix_world.to_3x3() @ (hb.matrix.to_3x3() @ Vector((0, 0.12, 0))))
        whale_frame(WR, WM, P, T(f), f, Kx)
        PHONE_POS[f] = P['whale_phone'].matrix_world.translation.copy()
    for k, a in A.items():
        for f in frames:
            t = T(f); mw, _ = standing_mw(k, t)
            HEADS.setdefault(k, {})[f] = mw @ a.rest['head'].translation + Vector((0, 0, 0.08))
    # ---- pass 1: everything
    for f in frames:
        t = T(f)
        for k, a in A.items(): solve_actor(a, k, t, f, st[k], P, Kx)
        camera(cam, t, f, Kx); lights(L, t, f, Kx); monitor_frame(P, t, f, Kx)
        smoke_frame(smoke, MOUTH.get('wife') if t > 54.8 else None, t, f, Kx)
    for a in A.values(): a.K.flush()
    Kx.flush()
    cut_frames = {int(math.ceil(c * FPS)) + 1 for c in CUTS}
    for idb in (cam, cam.data):
        for fc in idb.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cut_frames else 'LINEAR'
    for m in [bpy.data.materials[n] for n in CONST]:
        ad = m.node_tree.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    json.dump(dict(lines=LINES, cuts=CUTS, end=END, flatline=FLATLINE, ping=PING, revive=REVIVE), open(os.path.join(os.environ['W'], 'timeline.json'), 'w'), indent=1)
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False)
    print('SAVED', arg('--out'), NF, 'frames')


def cigar_local(WR):
    """The cigar in the left corner of his mouth, as a matrix in head-bone space. The corner was measured from his
    mesh (probe_mouth.py: where the grey head meets the white jaw, at x = 0.17 on the front surface) in his rest
    pose; the cigar points forward and out to his left, drooping, its mouth end 1.2 cm inside his lips."""
    hb = WR.pose.bones['mixamorig:Head']
    corner = Vector((0.17, -0.488, 1.266))
    d = Vector((0.5, -0.8, -0.28)).normalized(); up = Vector((0, 0, 1)); x = up.cross(d).normalized(); y = d.cross(x)
    M = Matrix((x, y, d)).transposed().to_4x4(); M.translation = corner - d * 0.012
    return hb.bone.matrix_local.inverted() @ M


def place_whale_phone(WR, P):
    ph = P['whale_phone']; ph.rotation_mode = 'QUATERNION'
    ph.location = (-0.42, -0.25, 0.0); ph.rotation_quaternion = Quaternion((0, 0, 1), math.radians(-15))
    # rest it on the duvet surface: ray down
    sc = bpy.context.scene; bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, *_ = sc.ray_cast(dg, Vector((-0.42, -0.25, 2.5)), Vector((0, 0, -1)))
    if hit:
        ph.location = loc + nrm * 0.0045; ph.rotation_quaternion = nrm.to_track_quat('Z', 'Y') @ Quaternion((0, 0, 1), math.radians(-15))


def dress(A, P):
    """Collar tab at the priest's throat; pillbox and veil on the widow's head (both on head/neck bones)."""
    a = A['priest']; c = P['collar']
    neck = a.rest['neck02']; front = neck.translation + Vector((0, -0.065, 0.02))
    c.location = front; c.rotation_euler = (math.radians(-12), 0, 0)
    bone_parent(c, a, 'neck02')
    a = A['wife']; v = P['veil']
    # sit the pillbox on the crown of her hair, a little forward and to her right, tilted (measured at rest)
    hair = a.parts[humans.CAST['wife']['hair']]; M = hair.matrix_world
    pts = [M @ vv.co for vv in hair.data.vertices]
    cx, cy = 0.035, a.rest['head'].translation.y - 0.01
    near = [p for p in pts if abs(p.x - cx) < 0.03 and abs(p.y - cy) < 0.03]
    top = max(p.z for p in near) if near else a.rest['head'].translation.z + 0.2
    v.location = (cx, cy, top - 0.012); v.rotation_euler = (math.radians(-10), math.radians(14), 0)
    print('VEIL hair top', round(top, 3))
    bone_parent(v, a, 'head')


def bone_parent(o, actor, bone):
    mw = o.matrix_world.copy() if o.parent is None else o.matrix_world.copy()
    bpy.context.view_layer.update(); mw = Matrix.Translation(o.location) @ o.rotation_euler.to_matrix().to_4x4()
    o.parent = actor.rig; o.parent_type = 'BONE'; o.parent_bone = bone
    bpy.context.view_layer.update(); o.matrix_world = actor.rig.matrix_world @ mw


if __name__ == '__main__':
    main()
