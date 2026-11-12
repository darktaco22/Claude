"""MEME ROYALE: "GOD CANDLE".  A degen on his phone at 3 AM taps BUY on a pump.fun-style app; over his shoulder the chart goes parabolic, the camera
dives into the screen, the last candle rips out of the phone, punches through the ceiling and rockets into the dusk sky, then falls and slams into
the Meme Royale arena.  Built on the clash stadium (its arena, stands, units, crowd and FX code).

  python3 ui.py UI_DIR ; python3 ui.py UI_DIR monitors           (the phone screen frames and the monitor pictures)
  blender -b --factory-startup -P scene.py -- --out scene.blend --ui UI_DIR      (writes edl.json next to it; render with render_edl.py)
24 fps, 1280x544 (2.35:1); finish.py grades, letterboxes and mixes the sound."""
import bpy, math, json, os, sys, random
from mathutils import Vector, Matrix, Quaternion, Euler

MYHERE = os.path.dirname(os.path.abspath(__file__)); CL = os.path.join(MYHERE, '..', 'clash', 'scene.py')
src = open(CL).read().split('\n')
def line(prefix): return next(i for i, l in enumerate(src) if l.startswith(prefix))
i_battle = line('# ================================================================ CLASH AT THE BRIDGE: the battle')
i_ns = line('N_, S_ = heading(0, 1)')
i_crowd = line('# ================================================================ the crowd')
i_crowdcall = line('crowd()')
g = globals(); g['__file__'] = CL
exec(compile('\n'.join(src[:i_battle]), CL, 'exec'), g)                 # helpers, arena, sky, stadium, units, FX (explode, dust ...)
exec(compile('\n'.join(src[i_battle:i_ns]), CL, 'exec'), g)             # smooth(), fighter(), sparks(), dust()
HERE = MYHERE; UI = arg('--ui', os.path.expanduser('~/gc_work/ui'))
sc.render.resolution_x, sc.render.resolution_y = 1280, 544
sc.cycles.samples = int(arg('--samples', '10')); sc.frame_end = 330
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.22
for o in list(bpy.data.objects):                                         # the clash film's blimp and its cables are in the way of the fall
    c = o.matrix_world.translation
    if o.name.startswith(('blimp', 'fin')) or (o.name.startswith('Cylinder') and 5.0 < c.x < 13.0 and abs(c.y + 16) < 2.5 and 12.5 < c.z < 36): bpy.data.objects.remove(o)
plane('ground2', 4000, 4000, (9, -16, -0.12), (0, 0, 0), GRASS)           # so the room is not floating in a void

# ---------------------------------------------------------------- the timeline (animation seconds)
GX, GY = 9.0, -21.0                                     # where it lands
T_SWAP, T_LAUNCH, T_CEIL, T_FLASH = 3.4, 4.5, 4.65, 6.2
T_DROP = 6.25; T_IMP = T_DROP + 3.2
ROOM = Vector((400.0, -16.0, 0.0))
def Rm(x, y, z): return ROOM + Vector((x, y, z))
def tick(a, b, f): return a + (b - a) * f
def sm(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def seg(o, a, b, r=None):
    d = Vector(b) - Vector(a); o.location = (Vector(a) + Vector(b)) / 2; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.scale = (r if r is not None else o.scale.x, r if r is not None else o.scale.y, d.length)
def cyl(name, mt, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=1.0, vertices=16); o = bpy.context.object; o.name = name
    for p in o.data.polygons: p.use_smooth = True
    o.data.materials.append(mt)
    if parent: o.parent = parent
    return o
def txt(body, size, loc, mt, align='LEFT'):
    bpy.ops.object.text_add(location=loc, rotation=(math.pi / 2, 0, 0)); o = bpy.context.object; o.data.body = body; o.data.size = size; o.data.extrude = 0.02; o.data.align_x = align; o.data.materials.append(mt); return o
def glow(name, col, strength, alpha):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = strength; mx.inputs['Fac'].default_value = alpha
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs['Surface']); return m
def imgmat(name, path, strength=1.2, seq=0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(path); ti.interpolation = 'Cubic'; ti.extension = 'EXTEND'
    if seq: ti.image.source = 'SEQUENCE'; iu = ti.image_user; iu.frame_duration = seq; iu.frame_start = 1; iu.frame_offset = 0; iu.use_auto_refresh = True; iu.use_cyclic = False
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength; o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(ti.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], o.inputs['Surface']); return m
def keyall(o, paths, frames_fn, f0, f1, step=1.0):
    """Key o's paths every `step` frames from f0 to f1: frames_fn(frame) sets the values."""
    n = int(round((f1 - f0) / step))
    for i in range(n + 1):
        fr = f0 + i * step; frames_fn(fr)
        for pth in paths: o.keyframe_insert(pth, frame=fr)
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
def tt(fr): return (fr - 1) / FPS

# ---------------------------------------------------------------- materials
SKIN = mat('skin', (0.82, 0.57, 0.44), 0.55); HOOD = mat('hoodie', (0.10, 0.075, 0.17), 0.9); JEANS = mat('jeans', (0.04, 0.06, 0.13), 0.8); SHOE = mat('shoe', (0.8, 0.8, 0.82), 0.5)
PHONE = mat('phonebody', (0.015, 0.015, 0.02), 0.25, metal=0.6); CARPET = mat('carpet', (0.035, 0.03, 0.05), 0.95); WALLM = mat('wallm', (0.07, 0.07, 0.1), 0.9); CEIL = mat('ceil', (0.55, 0.55, 0.58), 0.9)
DESK = mat('desk', (0.05, 0.035, 0.03), 0.5); BLK = mat('blk', (0.01, 0.01, 0.012), 0.4); BEAN = mat('bean', (0.2, 0.05, 0.08), 0.9)
LEDP = mat('ledp', (0.6, 0.2, 1.0), 0.3, emit=(0.65, 0.2, 1.0), estr=14); LEDC = mat('ledc', (0.2, 0.8, 1.0), 0.3, emit=(0.2, 0.8, 1.0), estr=9); NEONG = mat('neong', (0.2, 1.0, 0.4), 0.4, emit=(0.2, 1.0, 0.4), estr=12); NEONR = mat('neonr', (1.0, 0.15, 0.2), 0.4, emit=(1.0, 0.15, 0.2), estr=12)
CITY = mat('city', (0.2, 0.3, 0.9), 0.5, emit=(0.25, 0.35, 1.0), estr=3.0); CANM = mat('can', (0.1, 0.9, 0.3), 0.3, metal=0.8); PIZZA = mat('pizza', (0.55, 0.38, 0.2), 0.8)
GCM = None
def candle_mat():
    m = bpy.data.materials.new('godcandle'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.3
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sp.inputs[0])
    rp = nt.nodes.new('ShaderNodeValToRGB'); E = rp.color_ramp.elements; E[0].position = 0.0; E[0].color = (0.02, 0.38, 0.07, 1); E[1].position = 1.0; E[1].color = (0.85, 1.0, 0.75, 1); e = E.new(0.55); e.color = (0.12, 0.95, 0.22, 1)
    nt.links.new(sp.outputs['Z'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], b.inputs['Base Color']); nt.links.new(rp.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 3.2
    return m
GCM = candle_mat(); WICK = mat('wick', (0.5, 1.0, 0.42), 0.3, emit=(0.5, 1.0, 0.42), estr=14)
SPARKG = mat('sparkg', (0.5, 1, 0.5), 0.4, emit=(0.4, 1.0, 0.45), estr=45); COINM = mat('coin', (1.0, 0.7, 0.15), 0.25, emit=(1.0, 0.6, 0.1), estr=0.6, metal=1.0)
CRACK = mat('crack', (0.2, 1.0, 0.35), 0.4, emit=(0.2, 1.0, 0.35), estr=9); CRACKD = mat('crackd', (0.02, 0.025, 0.02), 0.9)

# ---------------------------------------------------------------- the room: a degen's bedroom at 3 AM
box('floor', (6.4, 6.4, 0.1), Rm(0, 0, -0.05), CARPET)
for (x, y, w, d) in ((0, 3.1, 6.4, 0.2), (0, -3.1, 6.4, 0.2), (-3.1, 0, 0.2, 6.4), (3.1, 0, 0.2, 6.4)): box('wall', (w, d, 2.8), Rm(x, y, 1.35), WALLM)
CEIL_CELLS = []
for ix in range(8):
    for iy in range(8): CEIL_CELLS.append(box('ceil', (0.78, 0.78, 0.1), Rm(-2.8 + 0.8 * ix, -2.8 + 0.8 * iy, 2.75), CEIL))
plane('window', 1.7, 1.15, Rm(-2.99, 0.9, 1.55), (math.pi / 2, 0, math.pi / 2), CITY); box('winframe', (0.06, 1.8, 1.25), Rm(-3.02, 0.9, 1.55), BLK)
box('desk', (3.2, 0.8, 0.06), Rm(0, 2.55, 0.76), DESK)
for sx in (-1.5, 1.5):
    box('deskleg', (0.06, 0.7, 0.76), Rm(sx, 2.55, 0.38), BLK)
for k, x in enumerate((-0.78, 0.0, 0.78)):
    box('stand', (0.06, 0.06, 0.25), Rm(x, 2.8, 0.9), BLK); box('bezel', (0.7, 0.04, 0.42), Rm(x, 2.74 - 0.01 * abs(k - 1), 1.2), BLK)
    p_ = plane('mon', 0.66, 0.38, Rm(x, 2.715 - 0.01 * abs(k - 1), 1.2), (math.pi / 2, 0, math.pi), imgmat(f'mon{k}', os.path.join(UI, f'mon{k}.png'), 1.1))
box('kbd', (0.5, 0.17, 0.02), Rm(0, 2.2, 0.8), LEDP); box('led1', (3.2, 0.03, 0.04), Rm(0, 3.0, 0.7), LEDP); box('led2', (0.04, 0.03, 1.5), Rm(-1.6, 3.0, 1.5), LEDC); box('led3', (0.04, 0.03, 1.5), Rm(1.6, 3.0, 1.5), LEDC)
for i, x in enumerate((-1.2, -1.1, 1.15, 1.3)):
    c = cyl('can', CANM); c.scale = (0.033, 0.033, 0.13); c.location = Rm(x, 2.4 + 0.05 * i, 0.85)
box('pizza', (0.42, 0.42, 0.05), Rm(-1.5, -0.3, 0.025), PIZZA); box('pizza2', (0.42, 0.42, 0.05), Rm(-1.45, -0.28, 0.075), PIZZA, rot=(0, 0, 0.4))
txt('LFG', 0.55, Rm(-1.9, 3.0, 2.05), NEONG); txt('NGMI', 0.4, Rm(1.1, 3.0, 2.1), NEONR)
# the trader, from behind: a hooded chibi in the game's spirit
TY = -1.2
ico('bean', 0.5, Rm(0, TY, 0.25), BEAN, 2).scale = (1, 1, 0.55)
box('torso', (0.46, 0.28, 0.56), Rm(0, TY, 0.84), HOOD); ico('shL', 0.1, Rm(-0.25, TY, 1.06), HOOD, 2); ico('shR', 0.1, Rm(0.25, TY, 1.06), HOOD, 2)
ico('head', 0.15, Rm(0, TY, 1.29), SKIN, 2); hood = ico('hood', 0.185, Rm(0, TY - 0.03, 1.31), HOOD, 2); hood.scale = (1, 1.05, 1.0); ico('hoodbunch', 0.1, Rm(0, TY - 0.15, 1.2), HOOD, 2)
S_R, S_L = Rm(0.25, TY, 1.04), Rm(-0.25, TY, 1.04); E_R, E_L = Rm(0.31, TY + 0.02, 0.78), Rm(-0.31, TY + 0.02, 0.78)
for a, b_ in ((S_R, E_R), (S_L, E_L)): seg(cyl('uarm', HOOD), a, b_, 0.062)
for sx in (-1, 1):
    seg(cyl('thigh', JEANS), Rm(sx * 0.14, TY, 0.52), Rm(sx * 0.16, TY + 0.46, 0.55), 0.09); seg(cyl('shin', JEANS), Rm(sx * 0.16, TY + 0.47, 0.5), Rm(sx * 0.16, TY + 0.52, 0.09), 0.07)
    box('shoe', (0.11, 0.24, 0.08), Rm(sx * 0.16, TY + 0.6, 0.05), SHOE)
# the phone, in his hands: screen normal n toward him (up and back), u to the screen's right, v up the screen
SW, SH_ = 0.068, 0.1473
P_ = Rm(-0.02, TY + 0.40, 1.02); n_ = Vector((0.1998, -0.8419, 0.37)).normalized(); u_ = Vector((1, 0, 0)); v_ = n_.cross(u_).normalized(); u_ = v_.cross(n_).normalized()
BASIS = Matrix(((u_.x, v_.x, n_.x), (u_.y, v_.y, n_.y), (u_.z, v_.z, n_.z)))
def ph(x, y, z=0.0): return P_ + u_ * x + v_ * y + n_ * z
PH = bpy.data.objects.new('phone', None); COL.objects.link(PH); PH.location = P_; PH.rotation_mode = 'QUATERNION'; PH.rotation_quaternion = BASIS.to_quaternion()
def child(o, loc, parent=PH, rot=None):
    o.parent = parent; o.location = loc
    if rot: o.rotation_euler = rot
    return o
child(box('pbody', (0.075, 0.157, 0.0085), (0, 0, 0), PHONE), (0, 0, -0.0044))
UIJ = json.load(open(os.path.join(UI, 'ui.json'))); NUI = len([f for f in os.listdir(UI) if f.startswith('u_')])
scr = plane('screen', SW, SH_, (0, 0, 0), (0, 0, 0), imgmat('screen', os.path.join(UI, 'u_0001.png'), 1.5, NUI)); child(scr, (0, 0, 0.0004)); scr.visible_shadow = False
def upx(x): return (x / UIJ['w'] - 0.5) * SW
def vpx(y): return (0.5 - y / UIJ['h']) * SH_
# left hand holds it from behind: a palm, four fingertips over the left edge, the sleeve back to the elbow
child(box('lpalm', (0.07, 0.1, 0.022), (0, 0, 0), SKIN), (0.004, -0.012, -0.02))
for k in range(4): child(box('lfing', (0.012, 0.02, 0.014), (0, 0, 0), SKIN), (-0.0385, 0.03 - k * 0.026, 0.001))
W_L = ph(0.004, -0.045, -0.03); seg(cyl('lfore', HOOD), E_L, W_L, 0.05); box('lcuff', (0.07, 0.05, 0.07), W_L, SKIN)
# right hand: a pointing fist.  HR sits at the wrist with +Z along the finger; the index tip is 0.125 along Z
HR = bpy.data.objects.new('HR', None); COL.objects.link(HR); HR.rotation_mode = 'QUATERNION'
child(box('fist', (0.052, 0.05, 0.06), (0, 0, 0), SKIN), (0, 0, 0.03), HR); child(box('index', (0.016, 0.016, 0.08), (0, 0, 0), SKIN), (0.006, 0.007, 0.085), HR); child(box('thumb', (0.015, 0.015, 0.04), (0, 0, 0), SKIN), (-0.03, 0.0, 0.05), HR)
FORE_R = cyl('rfore', HOOD); FORE_R.rotation_mode = 'QUATERNION'
A_LOC = Vector((-0.32, 0.55, -0.77)).normalized(); A_W = u_ * A_LOC.x + v_ * A_LOC.y + n_ * A_LOC.z
TAPS = [(t_, upx(x_), vpx(y_)) for t_, x_, y_ in UIJ['taps']]
PTS = [(0.0, 0.020, -0.075, 0.07), (0.6, 0.020, -0.07, 0.06)]
for (t_, x_, y_) in TAPS:                           # glide over, dip, press, lift
    PTS += [(t_ - 0.3, x_, y_, 0.03), (t_ - 0.05, x_, y_, 0.004), (t_, x_, y_, 0.0012), (t_ + 0.1, x_, y_, 0.0012), (t_ + 0.3, x_, y_, 0.03)]
PTS += [(TAPS[-1][0] + 0.6, 0.01, -0.07, 0.06), (TAPS[-1][0] + 1.6, 0.04, -0.11, 0.16), (9.0, 0.04, -0.11, 0.16)]
def tip_loc(t):
    for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(PTS, PTS[1:]):
        if t0 <= t <= t1: e = sm((t - t0) / (t1 - t0)); return Vector((tick(x0, x1, e), tick(y0, y1, e), tick(z0, z1, e)))
    return Vector(PTS[-1][1:])
def set_hand(fr):
    t = tt(fr); l = tip_loc(t); l.x += math.sin(t * 3.1) * 0.0015 * (1 if t < 1.0 else 0.2); tip = ph(l.x, l.y, l.z); W = tip - A_W * 0.125
    HR.location = W; HR.rotation_quaternion = A_W.to_track_quat('Z', 'Y'); seg(FORE_R, E_R, W, 0.05)
keyall(HR, ['location', 'rotation_quaternion'], lambda fr: (set_hand(fr)), F(0), F(T_FLASH))
for fr in range(F(0), F(T_FLASH) + 1):
    set_hand(fr); FORE_R.keyframe_insert('location', frame=fr); FORE_R.keyframe_insert('rotation_quaternion', frame=fr); FORE_R.keyframe_insert('scale', frame=fr)
for o in (HR, FORE_R):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

# ---------------------------------------------------------------- THE GOD CANDLE: out of the screen, through the ceiling, into the sky, down into the arena
HG = 13.2                                              # the game's candle: body 3.3 x 13.2 x 3.3
GC = bpy.data.objects.new('GC', None); COL.objects.link(GC); GC.rotation_mode = 'QUATERNION'
def cb(name, mt, foot=True):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
    if foot: o.data.transform(Matrix.Translation((0, 0, 0.5)))
    o.data.materials.append(mt); o.parent = GC; return o
BODY = cb('gc_body', GCM); WICKO = cb('gc_wick', WICK, False)
B0 = ph(upx(UIJ['x']), vpx(UIJ['y_base']), 0.0006); H0 = (UIJ['y_base'] - UIJ['y_top']) / UIJ['h'] * SH_; S0 = H0 / HG
Z0A = 300.0; A_UP = 2 * (Z0A - B0.z) / ((T_FLASH - T_LAUNCH) ** 2)
SKEY = [(T_SWAP, S0), (3.9, 0.02), (4.6, 0.08), (5.2, 0.22), (5.7, 0.55), (T_FLASH, 1.0)]
def S_of(t):
    if t >= T_FLASH: return 1.0
    for (t0, s0), (t1, s1) in zip(SKEY, SKEY[1:]):
        if t0 <= t <= t1: return math.exp(tick(math.log(s0), math.log(s1), (t - t0) / (t1 - t0)))
    return S0
def gc_shape(t):
    if t < T_SWAP: return 0.0001, 0.0001, 0.0001
    return tick(0.12, 0.25, sm((t - T_SWAP) / 0.7)) * HG, tick(0.03, 0.25, sm((t - T_SWAP) / 0.6)) * HG, HG
rg = random.Random(5); TILT = (0.045, -0.03); tf = T_IMP - T_DROP; gg = 2 * (Z0A + 0.35) / (tf * tf)
QP = BASIS.to_quaternion(); QW = Quaternion((1, 0, 0, 0))
def gc_state(t):
    """(location, quaternion, scale) of the candle at animation time t."""
    if t < T_SWAP: return B0, QP, 0.0001
    if t <= T_FLASH:
        q = QP.slerp(QW, sm((t - T_SWAP) / 1.1)) if t < T_SWAP + 1.1 else QW
        dz = 0.5 * A_UP * (t - T_LAUNCH) ** 2 if t > T_LAUNCH else 0.0
        sh = 0.0 if t < T_LAUNCH else 0.0; return B0 + Vector((0, 0, dz)), q, S_of(t)
    if t < T_DROP: return Vector((GX, GY, Z0A)), QW, 1.0
    if t < T_IMP: dt = t - T_DROP; return Vector((GX, GY, (Z0A + 0.35) * (1 - (dt / tf) ** 1.8) - 0.35)), Euler((TILT[0] * dt, TILT[1] * dt, 0.5 + 0.45 * dt)).to_quaternion(), 1.0
    return Vector((GX, GY, -0.35)), Euler((TILT[0] * tf, TILT[1] * tf, 0.5 + 0.45 * tf)).to_quaternion(), 1.0
prevq = [None]
def set_gc(fr):
    t = tt(fr); l, q, s = gc_state(t)
    if prevq[0] is not None and prevq[0].dot(q) < 0: q = -q
    prevq[0] = q.copy(); GC.location = l; GC.rotation_quaternion = q; GC.scale = (s, s, s)
    w, d, h = gc_shape(t); BODY.scale = (w, d, h); WICKO.scale = (0.5, 0.5, 1.5 * h); WICKO.location = (0, 0, h / 2)
for fr2 in range(F(0) * 2, F(T_IMP + 3.0) * 2):
    fr = fr2 / 2.0; set_gc(fr)
    for pth in ('location', 'rotation_quaternion', 'scale'): GC.keyframe_insert(pth, frame=fr)
    for o in (BODY, WICKO):
        o.keyframe_insert('scale', frame=fr)
    WICKO.keyframe_insert('location', frame=fr)
for o in (GC, BODY, WICKO):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if abs(kp.co[0] - F(T_FLASH)) < 0.01 and o is GC else 'LINEAR'
# the impact: squash, then the shock rattles it
sq = Vector(GC.scale)
for t, s in ((T_IMP - 0.01, (1, 1, 1)), (T_IMP + 0.04, (1.14, 1.14, 0.9)), (T_IMP + 0.12, (0.97, 0.97, 1.03)), (T_IMP + 0.22, (1.03, 1.03, 0.98)), (T_IMP + 0.4, (1, 1, 1))):
    GC.scale = s; GC.keyframe_insert('scale', frame=F(t))
# its light: dim in the phone, brighter and brighter, then it lights the whole stadium as it falls
LAMP = bpy.data.lights.new('gcl', 'POINT'); LAMP.color = (0.35, 1.0, 0.4); LAMP.shadow_soft_size = 1.5; LO = bpy.data.objects.new('gcl', LAMP); COL.objects.link(LO); LO.parent = GC; LO.location = (0, 0, 7)
for t, e in ((0, 0), (T_SWAP - 0.05, 0), (T_SWAP + 0.05, 30000), (3.9, 150000), (4.6, 400000), (T_CEIL + 0.2, 900000), (T_FLASH, 1200000), (T_DROP, 1200000), (T_IMP - 0.6, 260000), (T_IMP - 0.2, 400000), (T_IMP, 600000), (T_IMP + 0.04, 3000000), (T_IMP + 0.35, 220000), (T_IMP + 2.5, 90000), (T_IMP + 6, 60000)):
    LAMP.energy = e; LAMP.keyframe_insert('energy', frame=F(t))
for fc in LAMP.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
BEAMM = glow('beam', (0.3, 1.0, 0.4), 6.0, 0.25); TRLM = glow('trl', (0.35, 1.0, 0.45), 7.0, 0.3)
for i in range(9):      # flames streaming off its top while it falls
    o = ico('trail', 1.0, (0, 0, HG + 2.0 + i * 2.6), FIREGRN, 2); o.parent = GC; o.visible_shadow = False; s = 2.1 - i * 0.2; o.scale = (s, s, s * 2.2); show(o, F(T_DROP - 0.1), F(T_IMP) - 1)
for i in range(9):      # and out of its foot while it climbs
    o = ico('exhaust', 1.0, (0, 0, -2.0 - i * 2.4), FIREGRN, 2); o.parent = GC; o.visible_shadow = False; s = 2.0 - i * 0.18; o.scale = (s, s, s * 2.4); show(o, F(T_LAUNCH - 0.1), F(T_FLASH))
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=2.3, radius2=0.2, depth=30, location=(0, 0, HG + 16)); tc = bpy.context.object; tc.data.materials.append(TRLM); tc.parent = GC; tc.visible_shadow = False; show(tc, F(T_DROP - 0.1), F(T_IMP) - 1)

# re-entry: a white-hot shock cone ahead of its foot, flames sheathing its sides, streaming off behind it
PLASMA = glow('plasma', (1.0, 0.92, 0.75), 12.0, 0.45); PLASMA2 = glow('plasma2', (1.0, 0.45, 0.1), 9.0, 0.32)
for (r2, dep, zc, mt) in ((3.4, 11.0, -5.0, PLASMA), (4.8, 18.0, -8.5, PLASMA2)):
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.4, radius2=r2, depth=dep, location=(0, 0, zc)); o = bpy.context.object; o.data.materials.append(mt); o.parent = GC; o.visible_shadow = False; show(o, F(T_DROP - 0.1), F(T_IMP) - 1)
for i in range(12):
    ang = i / 12 * 6.283; o = ico('sheath', 1.0, (math.cos(ang) * 2.4, math.sin(ang) * 2.4, 3.0 + (i % 3) * 4.5), FIREG if i % 2 else FIREGRN, 2); o.parent = GC; o.visible_shadow = False; o.scale = (0.9, 0.9, 3.4); show(o, F(T_DROP - 0.1), F(T_IMP) - 1)

# ---------------------------------------------------------------- phone and room reactions
def spark_burst(c, t, n, seed, size, speed, dirv, spread=1.0, life=0.6):
    r_ = random.Random(seed); f0 = F(t)
    for i in range(n):
        v = (dirv + Vector((r_.uniform(-1, 1), r_.uniform(-1, 1), r_.uniform(-1, 1))) * spread).normalized() * speed * r_.uniform(0.4, 1.0)
        o = box('spk', (size * 0.25, size * 0.25, size * 2.0), c, SPARKG); o.visible_shadow = False; o.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()
        o.scale = (0.001,) * 3; key(o, 'scale', f0 - 1); o.scale = (1, 1, 1); key(o, 'scale', f0)
        for k_ in range(0, int(life * FPS) + 1, 2): tz = k_ / FPS; o.location = c + v * tz + Vector((0, 0, -0.5 * 9 * tz * tz)); key(o, 'location', f0 + k_)
        o.scale = (0.001,) * 3; key(o, 'scale', f0 + int(life * FPS) + 1); const(o); linear(o)
spark_burst(B0, T_SWAP, 60, 301, 0.006, 1.6, n_ + Vector((0, 0, 0.6)), 1.3, 0.7)
spark_burst(B0 + Vector((0, 0, 0.05)), T_SWAP + 0.15, 40, 302, 0.01, 2.6, Vector((0, 0, 1)), 1.0, 0.8)
PF = bpy.data.lights.new('phoneflash', 'POINT'); PF.color = (0.4, 1.0, 0.5); PFO = bpy.data.objects.new('phoneflash', PF); COL.objects.link(PFO); PFO.location = B0 + n_ * 0.1
for t, e in ((T_SWAP - 0.05, 0), (T_SWAP, 400), (T_SWAP + 0.3, 40), (T_SWAP + 0.8, 0)): PF.energy = e; PF.keyframe_insert('energy', frame=F(t))
CEN = Rm(B0.x - ROOM.x, B0.y - ROOM.y, 2.75)
def bursty(o, t, seed, speed):
    r_ = random.Random(seed); f0 = F(t); p0 = o.matrix_world.translation.copy(); d = Vector((p0.x - CEN.x, p0.y - CEN.y, 0)); d = d.normalized() if d.length > 0.01 else Vector((1, 0, 0))
    v = d * speed * r_.uniform(0.5, 1.3) + Vector((r_.uniform(-1, 1), r_.uniform(-1, 1), r_.uniform(2, 9))); spin = Vector((r_.uniform(-7, 7), r_.uniform(-7, 7), r_.uniform(-7, 7)))
    o.location = p0; key(o, 'location', f0 - 1); o.rotation_euler = (0, 0, 0); key(o, 'rotation_euler', f0 - 1); s0 = o.scale.copy(); n = int(2.2 * FPS)
    for k_ in range(0, n + 1, 2):
        tz = k_ / FPS; z = p0.z + v.z * tz - 0.5 * 9.8 * tz * tz; o.location = (p0.x + v.x * tz, p0.y + v.y * tz, max(z, 0.06)); key(o, 'location', f0 + k_); o.rotation_euler = spin * tz * (1 if z > 0.06 else 0.0); key(o, 'rotation_euler', f0 + k_)
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
for i, o in enumerate(CEIL_CELLS):
    c = o.matrix_world.translation; dist = Vector((c.x - CEN.x, c.y - CEN.y, 0)).length
    if dist < 1.6: bursty(o, T_CEIL + dist * 0.04, 500 + i, 3.5 + 3 * math.exp(-dist))
for i in range(40):        # plaster chunks
    r_ = random.Random(700 + i); o = box('chunk', (r_.uniform(0.05, 0.14),) * 3, CEN + Vector((r_.uniform(-0.5, 0.5), r_.uniform(-0.5, 0.5), 0)), CEIL); bursty(o, T_CEIL + 0.02, 800 + i, 5.0)
dust(CEN + Vector((0, 0, -0.2)), T_CEIL, 1.4, 41, 9); dust(CEN + Vector((0, 0, 0.3)), T_CEIL + 0.1, 1.9, 42, 7)
CL_ = bpy.data.lights.new('ceilflash', 'POINT'); CL_.color = (0.6, 1.0, 0.65); CLO = bpy.data.objects.new('ceilflash', CL_); COL.objects.link(CLO); CLO.location = CEN + Vector((0, 0, -0.4))
for t, e in ((T_CEIL - 0.05, 0), (T_CEIL, 20000), (T_CEIL + 0.3, 2000), (T_CEIL + 1.0, 0)): CL_.energy = e; CL_.keyframe_insert('energy', frame=F(t))

# ---------------------------------------------------------------- the beam on the ground, the cracks spreading
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.0, depth=700, location=(GX, GY, 350)); BEAM = bpy.context.object; BEAM.name = 'beam'; BEAM.data.materials.append(BEAMM); BEAM.visible_shadow = False
for t, s in ((0, 0.0001), (T_DROP - 0.9, 0.0001), (T_DROP - 0.55, 3.3), (T_IMP - 0.01, 3.4), (T_IMP + 0.05, 4.4), (T_IMP + 0.5, 0.0001)): BEAM.scale = (s, s, 1); key(BEAM, 'scale', F(t))
bpy.ops.mesh.primitive_plane_add(size=2, location=(GX, GY, 0.03)); DISC = bpy.context.object; DISC.data.materials.append(bpy.data.materials.new('disc')); dm = DISC.data.materials[0]; dm.use_nodes = True; nt = dm.node_tree; nt.nodes.clear()
tcn = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Location'].default_value = (-0.5, -0.5, 0); gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
rp = nt.nodes.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = 0.5; rp.color_ramp.elements[1].position = 1.0; em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.3, 1.0, 0.4, 1); em.inputs['Strength'].default_value = 10
trp = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); outn = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(tcn.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], gr.inputs['Vector']); nt.links.new(gr.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], mx.inputs['Fac'])
nt.links.new(trp.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], outn.inputs['Surface']); DISC.visible_shadow = False
for t, s in ((0, 0.0001), (T_DROP - 0.9, 0.0001), (T_IMP - 0.01, 5.0), (T_IMP + 0.03, 15.0), (T_IMP + 3.0, 9.0), (T_IMP + 8.0, 7.0)): DISC.scale = (s, s, 1); key(DISC, 'scale', F(t))
rc = random.Random(77)
def pbox(name, mt, org):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name; o.data.transform(Matrix.Translation(-Vector(org))); o.data.materials.append(mt); return o
def crack(ang, L, w, at, depth=0):
    cx, cy = at; cr = pbox('crk', CRACK, (-0.5, 0, 0)); cd = pbox('crkd', CRACKD, (-0.5, 0, 0))
    for o, ww, zz in ((cd, w * 2.6, 0.012), (cr, w, 0.03)):
        o.location = (cx, cy, zz); o.rotation_euler = (0, 0, ang); o.scale = (0.0001, ww, 0.04); key(o, 'scale', 1); key(o, 'location', 1); key(o, 'rotation_euler', 1)
        o.scale = (L * 0.22, ww, 0.04); key(o, 'scale', F(T_DROP - 0.55)); o.scale = (L * 0.4, ww, 0.04); key(o, 'scale', F(T_IMP - 0.02)); o.scale = (L, ww, 0.04); key(o, 'scale', F(T_IMP + 0.22)); key(o, 'scale', F(T_IMP + 10))
    if depth < 1:
        for j in range(2):
            u = rc.uniform(0.35, 0.8); b = ang + rc.choice((-1, 1)) * rc.uniform(0.45, 0.9)
            crack(b, L * rc.uniform(0.3, 0.5), w * 0.65, (cx + math.cos(ang) * L * u, cy + math.sin(ang) * L * u), depth + 1)
for i in range(18): crack(i / 18 * 6.283 + rc.uniform(-0.15, 0.15), rc.uniform(7, 16), rc.uniform(0.16, 0.34), (GX, GY))
SW_ = []
for mt in (glow('sw1', (0.35, 1.0, 0.45), 30, 0.95), glow('sw2', (0.9, 1.0, 0.9), 30, 0.9)):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.09, major_segments=96, location=(GX, GY, 0.35)); o = bpy.context.object; o.data.materials.append(mt); o.visible_shadow = False; SW_.append(o)
for o, k_, ln in ((SW_[0], 38.0, 26), (SW_[1], 52.0, 18)):
    for f, s in ((F(T_IMP) - 1, 0.001), (F(T_IMP), 0.8), (F(T_IMP) + ln, k_), (F(T_IMP) + ln + 1, 0.001)): o.scale = (s, s, min(s, 1.5)); key(o, 'scale', f)
    linear(o)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=48, ring_count=24, location=(GX, GY, 0)); DOME = bpy.context.object; DOME.data.materials.append(glow('dome', (0.4, 1.0, 0.5), 8.0, 0.22)); DOME.visible_shadow = False
for f, s in ((F(T_IMP) - 1, 0.001), (F(T_IMP), 1.5), (F(T_IMP) + 8, 20.0), (F(T_IMP) + 18, 30.0), (F(T_IMP) + 19, 0.001)): DOME.scale = (s, s, s * 0.7); key(DOME, 'scale', f)
linear(DOME)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=90, location=(GX, GY, 45)); PIL = bpy.context.object; PIL.data.materials.append(glow('pillar', (0.4, 1.0, 0.5), 14, 0.35)); PIL.visible_shadow = False
for t, s in ((0, 0.0001), (T_IMP - 0.01, 0.0001), (T_IMP, 2.8), (T_IMP + 0.4, 2.2), (T_IMP + 1.5, 1.4), (T_IMP + 4, 0.9), (T_IMP + 8, 0.0001)): PIL.scale = (s, s, 1); key(PIL, 'scale', F(t))
SPARK = SPARKG
explode(Vector((GX, GY, 1.6)), T_IMP, 7.5, FIREGRN, 120, 61, SMOKEG, light=(0.3, 1.0, 0.35))
explode(Vector((GX, GY, 0.8)), T_IMP + 0.05, 5.0, FIRE, 40, 62, DUST, light=(1.0, 0.7, 0.3))
for i in range(5): sparks(Vector((GX, GY, 1.0 + i)), T_IMP + 0.02 * i, 26, 70 + i, 14.0)
dust(Vector((GX, GY, 0.4)), T_IMP, 4.5, 90, 12)
for i in range(46):      # gold coins thrown up by the slam
    r_ = random.Random(900 + i); a = r_.uniform(0, 6.28); sp_ = r_.uniform(3, 15); v = Vector((math.cos(a) * sp_, math.sin(a) * sp_, r_.uniform(14, 30))); bpy.ops.mesh.primitive_cylinder_add(radius=0.38, depth=0.09, vertices=18); o = bpy.context.object; o.data.materials.append(COINM)
    p0 = Vector((GX, GY, 1.0)); spin = Vector((r_.uniform(-14, 14), r_.uniform(-14, 14), 0)); f0 = F(T_IMP) + 1; o.scale = (0.001,) * 3; key(o, 'scale', f0 - 1); o.scale = (1, 1, 1); key(o, 'scale', f0)
    for k_ in range(0, 150, 2):
        tz = k_ / FPS; z = p0.z + v.z * tz - 0.5 * 24 * tz * tz
        if z < 0.1: break
        o.location = p0 + Vector((v.x * tz, v.y * tz, 0)); o.location.z = z; key(o, 'location', f0 + k_); o.rotation_euler = (spin.x * tz, spin.y * tz, 0); key(o, 'rotation_euler', f0 + k_)
    const(o); linear(o)

# ---------------------------------------------------------------- the crowd and the fighters watching the sky
def_fan = '''def fan_sched(team, j):
    return [(0, 'idle', 1), (T_FLASH + 0.2 * j, 'ready', 1.0), (T_DROP + 1.0 + 0.5 * j, 'hit', 0.4), (T_IMP - 0.5, 'hit', 0.8), (T_IMP + 0.25, 'lose', 1.0 + 0.3 * j), (T_IMP + 1.4 + 0.5 * j, 'win', 1.0 + 0.3 * j)]
'''
cr_src = '\n'.join(src[i_crowd:i_crowdcall]); a0_ = cr_src.index('def fan_sched'); a1_ = cr_src.index('SOURCES = ')
exec(compile(cr_src[:a0_] + def_fan + cr_src[a1_:], CL, 'exec'), g)
KEEP_OUT = []
crowd()
CREW = {}; N_, S_ = heading(0, 1), heading(0, -1)
def melee(ub, hb, ur, hr, x, gap, phase):
    """A blue and a red fighter trading blows right where the candle will land; they look up as it comes, then it hits."""
    for uid, h, team, y, hd in ((ub, hb, 'b', GY - gap, N_), (ur, hr, 'r', GY + gap, S_)):
        u = fighter(uid, h, team); CREW[uid] = u; place(u, (x, y, 0), hd); fight(u, 0.3, T_DROP + 1.9, 1.1, phase)
        clip(u, 'hit', F(T_DROP + 1.9), F(T_IMP - 0.35), 0.4, 3); clip(u, 'emote', F(T_IMP - 0.35), F(T_IMP + 0.04), 1.2, 3)
        d = Vector((x - GX, y - GY, 0)); d = d if d.length > 0.1 else Vector((0, 1 if team == 'r' else -1, 0)); fling(u, T_IMP + 0.04, (d.x, d.y), up=11 + 3 * (phase % 3), dist=15 + 4 * (phase % 2), dur=2.6)
melee('whale', 4.6, 'giga', 3.4, GX, 3.6, 0)
melee('floki', 3.0, 'troll', 2.8, GX - 6.5, 1.3, 1); melee('bonk', 2.6, 'zcat', 2.5, GX + 6.5, 1.2, 2)
melee('swordcat', 2.7, 'baton', 2.7, GX - 11.5, 1.2, 0); melee('toshi', 2.7, 'triplet', 2.7, GX + 11.5, 1.2, 1)

# ---------------------------------------------------------------- the light
def keylight(name, loc, target, e, size=4.0, col=(1.0, 0.95, 0.85), spot=None):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = e; ld.size = size; ld.color = col; o = bpy.data.objects.new(name, ld); COL.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); COL.objects.link(sun); sun.data.energy = 1.0; sun.data.angle = math.radians(3); sun.data.color = (1.0, 0.6, 0.34); sun.rotation_euler = (math.radians(70), 0, math.radians(205))
keylight('red_wash', (9, 3, 16), (9, -9, 0), 9000, 14, (1.0, 0.25, 0.15)); keylight('blue_wash', (9, -35, 16), (9, -23, 0), 9000, 14, (0.2, 0.45, 1.0)); keylight('fill', (9, -40, 9), (9, -21, 2), 5000, 10, (0.7, 0.85, 1.0))
keylight('phonefill', ph(0, 0, 0.18), ph(0, 0, 1.0), 6, 0.2, (0.8, 0.95, 1.0)); keylight('rimwin', Rm(-2.6, -1.4, 1.7), Rm(0, TY, 1.1), 90, 1.0, (0.35, 0.5, 1.0)); keylight('ledfront', Rm(0, 2.7, 1.3), Rm(0, TY, 1.0), 80, 2.0, (0.75, 0.25, 1.0))
keylight('camfill', Rm(1.6, -2.7, 1.9), Rm(0, TY, 1.0), 30, 1.5, (1.0, 0.85, 0.7)); keylight('roomtop', Rm(0, 0, 2.5), Rm(0, 0, 0), 25, 2.5, (0.7, 0.75, 1.0))
lamp = bpy.data.lights.new('lamp', 'POINT'); lamp.energy = 25; lamp.color = (1.0, 0.7, 0.4); lo_ = bpy.data.objects.new('lamp', lamp); COL.objects.link(lo_); lo_.location = Rm(-1.2, 2.3, 1.2)
for o in bpy.data.objects:
    if o.type == 'LIGHT': o.visible_camera = False

# ---------------------------------------------------------------- the edit
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); COL.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.dof.use_dof = True; cam.data.clip_end = 3000; cam.data.clip_start = 0.01
SHOTS = []; _t = [0.0]
def SH(dur, a0, s0, s1, p0, p1, l0, l1, lens, fstop=2.8, shake=0.0, lens1=None, fp=0, fl=0, orb=None, ec=0, roll=None):
    SHOTS.append(dict(t0=round(_t[0], 4), t1=round(_t[0] + dur, 4), a0=a0, s0=s0, s1=s1, p0=list(p0), p1=list(p1), l0=list(l0), l1=list(l1), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake, fp=fp, fl=fl, orb=orb, ec=ec, roll=roll)); _t[0] += dur
# fp / fl: 0 = world, 1 = offset from the candle's foot (metres), 3 = offset in candle heights
# 1. over his shoulder, pushing in on the phone while he taps BUY; the chart goes parabolic and fills the frame
SH(T_SWAP, 0.0, 1, 1, Rm(0.75, -2.0, 1.55), ph(0.10, 0.03, 0.30), Rm(-0.02, TY + 0.4, 1.05), ph(0.022, 0.02, 0), 60, 2.0, 0.3, 100, ec=2)
# 2. the candle leaves the screen (slow motion), close
SH(1.3, T_SWAP, 0.35, 0.5, (0.12, -0.12, 0.06), (0.34, -0.30, 0.2), (0, 0, 0.05), (0, 0, 0.18), 24, 2.0, 0.2, fp=1, fl=1)
# 3. from behind and below: it rises past him, lighting the room green
SH(1.0, T_SWAP + 0.55, 0.5, 0.7, Rm(1.7, -1.9, 0.4), Rm(1.3, -1.5, 0.7), (0, 0, 0.6), (0, 0, 0.8), 22, 2.8, 0.4, fl=1)
# 4. up through the ceiling
SH(0.8, T_SWAP + 1.15, 0.6, 0.9, Rm(0.4, -0.5, 0.2), Rm(0.3, -0.6, 0.3), (0, 0, 1.0), (0, 0, 1.0), 16, 2.8, 0.5, fl=3)
# 5. the chase: out into the sky
SH(0.95, T_SWAP + 1.75, 1.1, 1.1, (1.2, -2.0, -0.3), (0.9, -3.0, -0.6), (0, 0, 0.5), (0, 0, 0.5), 24, 4.0, 0.3, fp=3, fl=3)
# 6. the fall, like a rocket coming back down: an onboard camera looking down from over its top, rolling; a long-lens chase; then the ground, among the fighters
SH(1.2, T_DROP, 0.85, 0.85, (0.0, -7.0, 22.0), (0.0, -6.0, 18.0), (0, 0, -60), (0, 0, -60), 22, 4.0, 0.5, fp=1, fl=1, roll=(0.0, 0.7))
SH(1.0, T_DROP + 1.05, 0.9, 0.9, (46, -56, 0), (38, -48, 0), (0, 0, 6), (0, 0, 6), 50, 4.0, 0.3, fp=1, fl=1, roll=(-0.12, 0.1))
SH(0.9, T_DROP + 1.95, 0.9, 0.9, (GX + 5.0, GY - 11.0, 0.5), (GX + 4.2, GY - 10.0, 0.7), (0, 0, 6), (0, 0, 6), 14, 4.0, 0.3, fl=1)
SH(1.0, T_IMP - 0.45, 0.6, 0.4, (GX + 3.8, GY - 7.5, 0.3), (GX + 3.4, GY - 7.0, 0.4), (0, 0, 6), (0, 0, 2), 12, 5.6, 0.3, fl=1)
# 7. the slam, in slow motion
SH(1.8, T_IMP + 0.06, 0.12, 0.3, (0, 0, 0), (0, 0, 0), (9, -21, 5), (9, -21, 6), 24, 4.0, 0.2, orb=[9, -21, 4.0, 14, 0.3, 2.8, -1.5, 2.5])
SH(1.2, T_IMP + 0.44, 0.3, 0.45, (9, -36, 0.35), (9, -32, 0.45), (9, -21, 2), (9, -21, 3), 16, 5.6, 0.3)
SH(1.0, T_IMP + 0.78, 0.45, 0.45, (9, -21.5, 40), (9.5, -21.5, 25), (9, -21, 0), (9, -21, 0), 20, 5.6, 0.3)
SH(1.0, T_IMP + 1.23, 0.5, 0.8, (22, -36, 6), (19, -35, 9), (9, -21, 6), (9, -21, 8), 35, 4.0, 0.3)
# 8. the aftermath: a crane up and back
SH(3.2, T_IMP + 1.8, 1.0, 1.0, (9, -30, 3), (9, -62, 32), (9, -21, 7), (9, -21, 9), 24, 4.0, 0.15, 32)
N_FILM = int(round(_t[0] * FPS)); print('FILM ends at', _t[0], 'frames', N_FILM)
json.dump(dict(fps=FPS, first=1, last=N_FILM, shots=SHOTS, t_swap=T_SWAP, t_ceil=T_CEIL, t_flash=T_FLASH, t_drop=T_DROP, t_imp=T_IMP), open(os.path.join(MYHERE, 'edl.json'), 'w'), indent=0)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=False)
print('SAVED', OUT)
