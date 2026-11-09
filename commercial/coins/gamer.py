"""WAIT... THEY'RE COINS?  A realistic gamer (MakeHuman via MPFB 2, CC0) plays MEME ROYALE on his phone at 3 AM and
finds out every card is a real meme coin.

    blender -b -P gamer.py -- --out scene.blend [--samples 8]

Reuses the Degens Anonymous toolkit (commercial/degens): humans.py (the person), rigctl.py (pose + IK), grips.py
(the solved phone grip), props.py, room.py and assets.py (Poly Haven CC0 props). Frame f shows t = (f - 1) / 30.
The phone screen plays the PNG sequence from phone_screen.py (real gameplay + the coin screens)."""
import bpy, sys, os, math, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); DG = os.path.join(HERE, '..', 'degens'); sys.path.insert(0, DG)
os.environ.setdefault('DA_STUDIO', os.path.join(DG, 'studio'))
import humans, rigctl, assets, props, room, grips
import director as D

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return ARGS[ARGS.index(k) + 1] if k in ARGS else d
FPS = 30; NF = int(arg('--frames', 880)); T = lambda f: (f - 1) / FPS
SCREEN = arg('--screen', os.environ.get('GM_SCREEN', ''))
clamp, lerp, ease, ramp, pulse, win = D.clamp, D.lerp, D.ease, D.ramp, D.pulse, D.win

# ------------------------------------------------------------------ the lines (Kokoro, audio/vo/lines.json)
VO = json.load(open(os.path.join(HERE, 'audio', 'vo', 'lines.json')))
LINES = [('k_useless', 0.8), ('k_dollar', 5.0), ('k_real', 11.2), ('k_list', 13.4), ('k_chill', 16.95), ('k_research', 18.6),
         ('k_three', 23.0), ('k_mom', 24.9), ('m_bed', 27.5)]
def talk(t):
    for i, t0 in LINES:
        if VO[i]['who'] != 'kyle': continue
        e = VO[i]['env']; j = int((t - t0) * FPS)
        if 0 <= j < len(e): return e[j]
    return 0.0
# shots: (start, kind)
CUTS = [(0.0, 'wide'), (3.6, 'ots'), (7.2, 'face'), (9.0, 'ots'), (11.0, 'face'), (13.2, 'ots'), (16.9, 'face'),
        (18.2, 'medium'), (21.6, 'ots'), (24.6, 'wide2')]
def shot(t):
    k = CUTS[0]
    for c in CUTS:
        if t >= c[0]: k = c
    return k

# ------------------------------------------------------------------ the person
humans.CAST['kyle'] = dict(
    phen=dict(gender=1.0, age=0.42, muscle=0.35, weight=0.62, height=0.55, proportions=0.5, race=dict(caucasian=0.85, asian=0.1, african=0.05)),
    skin='young_caucasian_male2', hair='short02', brows='eyebrow001', lashes='eyelashes01',
    clothes=['elvs_crude_t-shirt_male', 'cortu_cargo_pants', 'shoes02'],
    tint={'elvs_crude_t-shirt_male': (0.0, 0.25, 0.35, (0.16, 0.18, 0.22))})

def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = int(arg('--samples', 8)); sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.denoising_prefilter = 'ACCURATE'
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False; sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = 720, 1280
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.3
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
    w = bpy.data.worlds.new('night'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.004, 0.005, 0.012, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0

# ------------------------------------------------------------------ the bedroom (3 AM): Kyle on the edge of his bed
C = lambda: bpy.context.scene.collection
def box(name, size, loc, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m)
    if bevel:
        b = o.modifiers.new('b', 'BEVEL'); b.width = bevel; b.segments = 4
        for p in o.data.polygons: p.use_smooth = True
    return o
def emis(name, col, s): return props.mat(name, col, emit=col, estr=s)
def fabric(name, col, rough=0.95):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Sheen Weight'].default_value = 0.6
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 180; nz.inputs['Detail'].default_value = 2
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 0.25
    mx.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs['Color'], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    return m
def bedroom():
    S = {}
    floor = room.pbr('floor', 'wooden_floor_02', scale=0.6); wall = room.pbr('wall', 'beige_wall_001', scale=0.5, tint=(0.55, 0.6, 0.75))
    room.plane('floor', (8, 8), (0, 1.0, 0), (0, 0, 0), floor)
    room.plane('wall_back', (8, 3), (0, 2.6, 1.5), (math.pi / 2, 0, 0), wall)
    room.plane('wall_left', (8, 3), (-2.2, 1.0, 1.5), (math.pi / 2, 0, math.pi / 2), wall)
    room.plane('wall_right', (8, 3), (2.4, 1.0, 1.5), (math.pi / 2, 0, -math.pi / 2), wall)
    room.plane('ceiling', (8, 8), (0, 1.0, 2.7), (math.pi, 0, 0), props.mat('ceil', (0.5, 0.5, 0.55), 0.9))
    # the bed: dark frame, mattress, a rumpled navy duvet, pillows (Poly Haven) against the wall
    wood = props.mat('bedwood', (0.08, 0.05, 0.035), 0.55)
    box('bed_frame', (1.5, 2.1, 0.28), (0.15, 1.45, 0.14), wood, 0.01)
    box('mattress', (1.42, 2.0, 0.2), (0.15, 1.45, 0.36), fabric('sheet', (0.75, 0.75, 0.78)), 0.04)
    duvet = box('duvet', (1.48, 1.35, 0.07), (0.15, 1.78, 0.48), fabric('duvet', (0.05, 0.07, 0.16)), 0.03)
    sd = duvet.modifiers.new('wr', 'DISPLACE'); tx = bpy.data.textures.new('rumple', 'CLOUDS'); tx.noise_scale = 0.25; sd.texture = tx; sd.strength = 0.05
    sub = duvet.modifiers.new('s', 'SUBSURF'); sub.levels = 2; duvet.modifiers.move(2, 0)
    box('headboard', (1.5, 0.08, 0.9), (0.15, 2.52, 0.45), wood, 0.015)
    try:
        pl, _ = assets.load('throw_pillows_01'); pl.location = (0.15, 2.3, 0.47); pl.rotation_euler.z = math.pi
    except Exception as e: print('pillows', e)
    # the desk with the monitor (MEME ROYALE on it), an energy drink pile, the arm lamp
    try:
        dk, _ = assets.load('metal_office_desk'); dk.location = (-1.65, 0.7, 0); dk.rotation_euler.z = math.pi / 2
        lo, hi = assets.dims(dk); top = hi.z
    except Exception as e: print('desk', e); top = 0.75
    # (the desk's monitor is off camera: its glow is the 'monitor_glow' light)
    for i, (x, y) in enumerate([(-1.45, 0.45), (-1.38, 0.52), (-1.5, 0.58), (-1.42, 1.05)]):
        c = props.can(f'can{i}'); c.location = (x, y, top + 0.0); c.rotation_euler.z = i * 1.3
    for i, (x, y, ry) in enumerate([(-0.9, -0.2, 1.6), (0.9, 0.3, 0.4), (1.1, 0.0, 1.57)]):
        c = props.can(f'floorcan{i}'); c.location = (x, y, 0.033); c.rotation_euler = (math.pi / 2, 0, ry)
    try:
        lp, _ = assets.load('desk_lamp_arm_01'); lp.location = (-1.95, 0.35, top)
    except Exception as e: print('lamp', e)
    try:
        bx, _ = assets.load('cardboard_box_01'); bx.location = (1.25, 1.9, 0); bx.scale = (0.9, 0.9, 0.9)
    except Exception as e: print('box', e)
    # the poster over the bed: the game's key art
    post = room.printed('poster', os.path.join(HERE, '..', 'assets', 'bg_title_wide.jpg'))
    room.plane('poster', (1.2, 0.68), (0.15, 2.585, 1.55), (math.pi / 2, 0, math.pi), post)
    # the RGB strip along the top of the headboard wall (purple), and the hallway door on the right wall
    box('led', (1.8, 0.015, 0.012), (0.15, 2.57, 2.05), emis('led', (0.55, 0.12, 1.0), 40))
    door = box('door', (0.05, 0.9, 2.05), (2.37, 0.2, 1.025), props.mat('doorm', (0.55, 0.52, 0.48), 0.6), 0.005)
    S['door'] = door
    return S

def lights():
    L = {}
    def area(name, col, e, loc, rot, size=0.5):
        ld = bpy.data.lights.new(name, 'AREA'); ld.color = col; ld.energy = e; ld.size = size
        o = bpy.data.objects.new(name, ld); C().objects.link(o); o.location = loc; o.rotation_euler = rot; L[name] = o; return o
    area('led_wash', (0.6, 0.2, 1.0), 120, (0.15, 2.4, 2.1), (math.radians(-60), 0, 0), 1.6)        # purple rim from behind
    area('monitor_glow', (0.45, 0.6, 1.0), 35, (-1.75, 0.8, 1.1), (math.radians(90), 0, math.radians(-110)), 0.5)
    area('moon', (0.35, 0.45, 0.8), 25, (1.5, -2.0, 2.4), (math.radians(50), 0, math.radians(30)), 2.0)  # soft fill from the window side
    ld = bpy.data.lights.new('hall', 'AREA'); ld.color = (1.0, 0.8, 0.55); ld.energy = 0; ld.shape = 'RECTANGLE'; ld.size = 0.12; ld.size_y = 2.0
    o = bpy.data.objects.new('hall', ld); C().objects.link(o); o.location = (2.3, -0.27, 1.0); o.rotation_euler = (0, math.radians(-90), 0); L['hall'] = o
    return L

# ------------------------------------------------------------------ main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_render()
    S = bedroom(); L = lights()
    rig, body, parts = humans.build('kyle')
    a = rigctl.Actor('kyle', rig, body); a.parts = parts
    c, M, w = grips.phone(a, 'R'); a.G = {'phone': (c, M)}; print('GRIP phone', {k: round(v * 1000, 1) for k, v in w.items()})
    ph = props.phone('kyle_phone', os.path.join(SCREEN, 's_0001.png'))
    sm = bpy.data.materials[ph['screen_mat']]; img = [n for n in sm.node_tree.nodes if n.type == 'TEX_IMAGE'][0]
    img.image.source = 'SEQUENCE'; img.image_user.frame_duration = NF; img.image_user.frame_start = 1; img.image_user.use_auto_refresh = True
    em = sm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']; em.default_value = 2.6
    gl = bpy.data.objects[ph['glow']]; gl.data.energy = 1.4
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); C().objects.link(cam); bpy.context.scene.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24; cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.0
    SEAT = Matrix.Translation((0.15, 0.62, 0))           # on the edge of the bed (mattress top 0.46), facing -Y
    hipc = (a.hip['L'] + a.hip['R']) / 2
    root0 = Vector((0, 0.035 - hipc.y, 0.46 + 0.095 - hipc.z))
    sx = {'L': 1, 'R': -1}
    st = dict(yaw=0.0, pitch=0.45, lean=math.radians(10))
    K = rigctl.Keys()
    for f in range(1, NF + 1):
        t = T(f); kind = shot(t)[1]
        # ---------------- where he looks, how he sits
        yawT, pitchT, leanT = 0.0, 0.42, math.radians(12)        # hunched over the phone
        shocked = 0.0
        if win(t, 7.2, 9.0): pitchT = 0.36; yawT = 0.12            # squints, head tilt
        if win(t, 11.0, 13.2): pitchT = 0.05; leanT = math.radians(4); shocked = 1.0     # "No way."
        if win(t, 16.9, 18.2): pitchT = -0.05; leanT = math.radians(2); shocked = 1.0    # "Chill Guy is a COIN?!"
        if win(t, 18.2, 21.3): pitchT = -0.12; leanT = math.radians(-12)                 # leans back, stares at the ceiling
        if win(t, 24.6, 29.4): yawT = 0.95 * ramp(t, 24.6, 24.9); pitchT = 0.0; leanT = math.radians(6)   # shouts at the door
        sp = 0.22 if not (win(t, 11.0, 11.4) or win(t, 16.9, 17.2)) else 0.5
        st['yaw'] = lerp(st['yaw'], yawT, sp); st['pitch'] = lerp(st['pitch'], pitchT, sp); st['lean'] = lerp(st['lean'], leanT, sp * 0.8)
        Q = {}; root_loc = root0.copy(); lean = st['lean'] + math.sin(t * 2.0) * 0.01
        for b, wgt in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)):
            Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), lean * wgt))
        tv = talk(t); nod = math.sin(t * 9) * 0.03 * (tv > 0.15)
        yaw = st['yaw'] + (math.sin(t * 5.3) * 0.05 * shocked); pitch = st['pitch'] + nod
        for b, wgt in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)):
            Q[b] = a.local_q(b, rigctl.qrot((0, 0, 1), yaw * wgt) @ rigctl.qrot((1, 0, 0), (pitch - lean * 0.9) * wgt))
        if win(t, 7.2, 9.0):     # the suspicious head tilt
            Q['head'] = Q['head'] @ a.local_q('head', rigctl.qrot((0, 1, 0), 0.18 * ramp(t, 7.3, 7.8)))
        # ---------------- face
        blink = 1.0 if (t % 3.3) < 0.12 and not shocked else 0.0
        squint = 0.3 if win(t, 7.3, 9.0) else 0.0
        lid = 0.55 * blink + squint - 0.22 * shocked
        for s in 'LR':
            Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), lid))
            Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink + 0.15 * squint))
        jaw = tv * 0.13 + shocked * 0.12 * (tv < 0.1)
        Q['jaw'] = a.local_q('jaw', rigctl.qrot((1, 0, 0), jaw))
        phv = math.sin(t * 13.0) * 0.5 + 0.5
        shape = {'v_aa': tv * 0.42 + shocked * 0.2 * (tv < 0.1), 'v_ow': tv * 0.3 * phv + shocked * 0.25 * (tv < 0.1), 'v_ee': tv * 0.25 * (1 - phv),
                 'v_mm': 0.25 if (0 < tv < 0.08) else 0.0, 'v_ff': 0.0}
        # ---------------- feet
        feet, poles = {}, {}
        for s in 'LR':
            hip = a.hip[s] + root_loc
            ank = Vector((hip.x + sx[s] * 0.07, -(a.thigh + 0.06), 0.085))
            if s == 'R': ank.z += max(0.0, math.sin(t * 30)) * 0.02 * (shocked > 0.5)        # the excited leg bounce
            Fm = a.rest[f'foot.{s}'].copy(); Fm.translation = ank
            feet['foot', s] = SEAT @ Fm; poles['foot', s] = SEAT @ Vector((hip.x + sx[s] * 0.08, -1.2, 0.55))
        # ---------------- hands: the phone in his right hand in front of his eyes; the left on his thigh
        head = a.fk(Q, root_loc, 'head')
        eyes = head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04))))
        G = a.G
        def phone_frame(s, dist=0.36, drop=0.2, toward=None):
            flat = Vector((0, -1, 0)); zup = Vector((0, 0, 1))
            tgt = eyes + flat * dist - zup * drop
            n = ((toward if toward is not None else eyes) - tgt).normalized(); upp = (zup - n * zup.dot(n)).normalized()
            X = upp * a.idx_sign[s]; Y = n.cross(X)
            F = a.frame(Vector(), Y, n); F.translation = tgt - F.to_3x3() @ G['phone'][1].translation; return F
        def lap(s):
            hip = a.hip[s] + root_loc; knee = hip + Vector((0, -a.thigh * 0.95, -0.06))
            sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation; reach = (a.uarm + a.farm) * 0.95
            for u in [0.62 - 0.04 * i for i in range(9)]:
                pos = hip.lerp(knee, u) + Vector((-sx[s] * 0.01, 0, 0.085))
                F = a.frame(pos, (-sx[s] * 0.15, -1, -0.15), (sx[s] * 0.2, 0, -1))
                if (a.hand_matrix_for_palm(s, F).translation - sh).length <= reach: break
            return F
        hands = {'L': lap('L')}; shapes = {'L': 'flat', 'R': 'phone'}
        if win(t, 18.2, 21.3):      # phone held up over his face while he leans back
            hands['R'] = phone_frame('R', 0.30, 0.06)
        elif win(t, 24.6, 29.4):    # phone lowered to his chest while he yells at the door
            hands['R'] = phone_frame('R', 0.26, 0.5)
        else:
            hands['R'] = phone_frame('R')
        if win(t, 22.0, 22.25):     # the thumb hits BUY
            hands['R'] = Matrix.Translation(Vector((0, 0, -0.01)) * pulse(t, 22.0, 22.25, 0.1)) @ hands['R']
        reach = (a.uarm + a.farm) * 0.985
        for s in 'LR':
            wp = a.hand_matrix_for_palm(s, hands[s]).translation; sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation; dv = wp - sh
            if dv.length > reach: hands[s] = Matrix.Translation(dv.normalized() * (reach - dv.length)) @ hands[s]
        for s in 'LR': D.curl_Q(a, s, shapes[s], Q) if shapes[s] != 'phone' else Q.update(grips.curlQ(a, s, G['phone'][0]))
        H = {('hand', s): SEAT @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
        for s, tuck in (('L', 0.0), ('R', 1.0)):
            pv = Vector((sx[s] * 0.7, 0.45, -0.45)).lerp(Vector((sx[s] * 0.22, 0.35, -0.75)), tuck)
            poles['hand', s] = SEAT @ (a.shoulder[s] + root_loc + pv)
        a.key_pose(f, SEAT, Q, root_loc, H, feet, poles, shape)
        Wp = SEAT @ hands['R'] @ G['phone'][1]; ph.rotation_mode = 'QUATERNION'
        for i in range(3): K.add(ph, 'location', i, f, Wp.translation[i])
        for i in range(4): K.add(ph, 'rotation_quaternion', i, f, Wp.to_quaternion()[i])
        # ---------------- the hallway light comes on when Mom answers
        K.add(L['hall'].data, 'energy', 0, f, 220.0 * ramp(t, 27.3, 27.45))
        # ---------------- camera
        eyeW = SEAT @ eyes; phW = Wp.translation; c0 = shot(t)[0]; u = t - c0
        if kind == 'wide':
            loc = Vector((0.9, -2.3, 1.25)).lerp(Vector((0.65, -1.75, 1.15)), ease(u / 3.6)); look = eyeW + Vector((0, 0, -0.35)); lens = 30
        elif kind == 'wide2':
            loc = Vector((-0.75, -1.9, 1.2)) + Vector((0.05, 0.08, 0)) * u; look = eyeW + Vector((0.25, 0, -0.3)); lens = 32
        elif kind == 'ots':     # over his right shoulder down onto the phone
            back = SEAT @ (a.shoulder['R'] + root_loc + Vector((-0.12, 0.30, 0.20)))
            loc = back + Vector((0, 0, 0)) - (back - phW).normalized() * (0.06 * ease(u / 3))
            look = phW; lens = 42
        elif kind == 'face':
            loc = eyeW + Vector((-0.12, -0.62, -0.05)) - Vector((0, 0.08, 0)) * ease(u / 2); look = eyeW + Vector((0, 0, -0.03)); lens = 50
        else:   # medium, from low: he leans back with the phone over his face
            loc = eyeW + Vector((0.55, -1.35, -0.35)); look = eyeW + Vector((0, 0, -0.15)); lens = 35
        d = (look - loc); rot = d.to_track_quat('-Z', 'Y').to_euler()
        for i in range(3): K.add(cam, 'location', i, f, loc[i]); K.add(cam, 'rotation_euler', i, f, rot[i])
        K.add(cam.data, 'lens', 0, f, lens); K.add(cam.data, 'dof.focus_distance', 0, f, (look - loc).length)
    a.K.flush(); K.flush()
    cut_frames = {int(round(c * FPS)) + 1 for c, _ in CUTS}
    for idb in (cam, cam.data):
        ad = idb.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cut_frames else 'LINEAR'
    for o in bpy.data.objects:
        if o.type == 'LIGHT': o.visible_camera = False
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg('--out', 'gamer.blend')), compress=False)
    print('SAVED', arg('--out'))

if __name__ == '__main__':
    main()
