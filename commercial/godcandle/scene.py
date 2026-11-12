"""MEME ROYALE: "GOD CANDLE" - a pump.fun-style chart floats in the dusk sky over the arena; its last candle pumps, rips out of the
chart, falls through the sky and slams into the court.  Built on the clash stadium (its arena, stands, units, crowd and FX code).

blender -b --factory-startup -P scene.py -- --out scene.blend      (writes edl.json next to it; render with render_edl.py)
24 fps, 1280x544 (2.35:1); finish.py grades, letterboxes and mixes the sound."""
import bpy, math, json, os, sys, random, re
from mathutils import Vector, Matrix

MYHERE = os.path.dirname(os.path.abspath(__file__)); CL = os.path.join(MYHERE, '..', 'clash', 'scene.py')
src = open(CL).read().split('\n')
def line(prefix): return next(i for i, l in enumerate(src) if l.startswith(prefix))
i_battle = line('# ================================================================ CLASH AT THE BRIDGE: the battle')
i_ns = line('N_, S_ = heading(0, 1)')
i_crowd = line('# ================================================================ the crowd')
i_crowdcall = line('crowd()')
g = globals(); g['__file__'] = CL
exec(compile('\n'.join(src[:i_battle]), CL, 'exec'), g)                 # helpers, arena, sky, stadium, units, FX (explode, dust ...)
exec(compile('\n'.join(src[i_battle:i_ns]), CL, 'exec'), g)             # smooth(), fighter(), sparks(), dust(), the T_ constants
HERE = MYHERE
sc.render.resolution_x, sc.render.resolution_y = 1280, 544
sc.cycles.samples = int(arg('--samples', '10')); LAST = 340; sc.frame_end = LAST

# ---------------------------------------------------------------- the clash film's blimp and its cables are in the way of the fall
for o in list(bpy.data.objects):
    c = o.matrix_world.translation
    if o.name.startswith(('blimp', 'fin')) or (o.name.startswith('Cylinder') and 5.0 < c.x < 13.0 and abs(c.y + 16) < 2.5 and 12.5 < c.z < 36):
        bpy.data.objects.remove(o)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.22

# ---------------------------------------------------------------- the timeline (animation seconds)
GX, GY = 9.0, -21.0                                   # where it lands
T_PUMP, T_BREAK, T_FULL, T_HOVER, T_DROP, T_IMP = 4.0, 4.5, 5.0, 4.8, 5.8, 7.9
CH = Vector((-11.2, -17.0, 60.0))                     # the chart's centre; it faces -Y (we look at it from the blue end)
def tick(a, b, f): return a + (b - a) * f
def sm(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def track(o, path, t0, t1, fn, step=1.0, idx=-1):
    """Key o.path every `step` frames from t0 to t1; fn(u) -> value."""
    f0, f1 = F(t0), F(t1); n = max(1, int(round((f1 - f0) / step)))
    for i in range(n + 1):
        u = i / n; v = fn(u); fr = f0 + (f1 - f0) * u
        if idx >= 0: getattr(o, path)[idx] = v
        else: setattr(o, path, v)
        o.keyframe_insert(path, frame=fr, index=idx)
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
def glow(name, col, strength, alpha):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = strength; mx.inputs['Fac'].default_value = alpha
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs['Surface']); return m
def pbox(name, mt, org, parent=None):
    """A unit cube whose origin sits at `org`, in cube coordinates (-.5..+.5): (0,0,-.5) its foot, (-.5,0,0) its left end."""
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
    o.data.transform(Matrix.Translation(-Vector(org)))
    o.data.materials.append(mt)
    if parent: o.parent = parent
    return o
def txt(body, size, loc, mt, align='LEFT', bold=False):
    bpy.ops.object.text_add(location=loc, rotation=(math.pi / 2, 0, 0)); o = bpy.context.object; o.data.body = body; o.data.size = size; o.data.extrude = 0.04
    o.data.align_x = align; o.data.materials.append(mt); return o

# ---------------------------------------------------------------- materials
PG = mat('pump_green', (0.02, 0.9, 0.3), 0.35, emit=(0.05, 1.0, 0.35), estr=3.0); PR = mat('pump_red', (0.95, 0.12, 0.2), 0.35, emit=(1.0, 0.15, 0.22), estr=2.4)
PANEL = mat('panel', (0.045, 0.05, 0.06), 0.18, metal=0.3); GRID = mat('grid', (0.3, 0.32, 0.36), 0.6, emit=(0.4, 0.42, 0.5), estr=0.5)
FRAME = mat('frame', (0.1, 0.9, 0.3), 0.4, emit=(0.1, 1.0, 0.35), estr=2.2); TXT = mat('txt', (0.9, 0.95, 1.0), 0.5, emit=(0.8, 0.9, 1.0), estr=1.6); TXTG = mat('txtg', (0.2, 1.0, 0.4), 0.5, emit=(0.2, 1.0, 0.4), estr=2.5)
WICK = mat('wick', (0.5, 1.0, 0.42), 0.3, emit=(0.5, 1.0, 0.42), estr=14)
def candle_mat():
    m = bpy.data.materials.new('godcandle'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.3
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sp.inputs[0])
    rp = nt.nodes.new('ShaderNodeValToRGB'); E = rp.color_ramp.elements; E[0].position = 0.0; E[0].color = (0.02, 0.38, 0.07, 1); E[1].position = 1.0; E[1].color = (0.85, 1.0, 0.75, 1); e = E.new(0.55); e.color = (0.12, 0.95, 0.22, 1)
    nt.links.new(sp.outputs['Z'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], b.inputs['Base Color']); nt.links.new(rp.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 3.2
    return m
GCM = candle_mat(); SPARKG = mat('sparkg', (0.5, 1, 0.5), 0.4, emit=(0.4, 1.0, 0.45), estr=45); COINM = mat('coin', (1.0, 0.7, 0.15), 0.25, emit=(1.0, 0.6, 0.1), estr=0.6, metal=1.0)
CRACK = mat('crack', (0.2, 1.0, 0.35), 0.4, emit=(0.2, 1.0, 0.35), estr=9); CRACKD = mat('crackd', (0.02, 0.025, 0.02), 0.9)

# ---------------------------------------------------------------- the chart (world = CH + local x, z)
def Wp(x, z, y=0.0): return CH + Vector((x, y, z))
CHART = []                                              # everything that shatters
rr = random.Random(11)
NC = 34; XS = [-24.0 + 1.3 * i for i in range(NC + 1)]; XG = XS[-1]
p = 0.0; ser = []
for i in range(NC):
    d = rr.gauss(0.22, 1.0) if i % 3 else rr.gauss(-0.5, 0.8); o_, c_ = p, p + d; hi = max(o_, c_) + abs(rr.gauss(0, 0.5)); lo = min(o_, c_) - abs(rr.gauss(0, 0.5)); ser.append((o_, c_, hi, lo)); p = c_
mn = min(s[3] for s in ser); mxv = max(s[2] for s in ser); k = 8.0 / (mxv - mn)
ser = [tuple(-12.0 + (v - mn) * k for v in s) for s in ser]
GB = ser[-1][1]                                         # the last close: the god candle starts there
# panel: a pane of dark glass in cells, so it can shatter
CELLS = []
for ix in range(10):
    for iz in range(6):
        cx = -28 + 5.6 * (ix + 0.5); cz = -16 + 5.333 * (iz + 0.5)
        b_ = box('cell', (5.5, 0.5, 5.23), Wp(cx, cz, 0.7), PANEL); CELLS.append(b_); CHART.append(b_)
for (x, z, w, h) in ((0, 16.1, 56.4, 0.35), (0, -16.1, 56.4, 0.35), (-28.1, 0, 0.35, 32.4), (28.1, 0, 0.35, 32.4)):
    CHART.append(box('frame', (w, 0.6, h), Wp(x, z, 0.4), FRAME))
for zz in range(-12, 13, 4): CHART.append(box('hgrid', (54, 0.05, 0.06), Wp(0, zz, 0.42), GRID))
for xx in range(-24, 25, 6): CHART.append(box('vgrid', (0.06, 0.05, 28), Wp(xx, 0, 0.42), GRID))
CHART += [txt('$ROYALE / SOL', 1.9, Wp(-26.5, 12.4, -0.3), TXT), txt('MC  $69.4K', 1.5, Wp(-26.5, 9.8, -0.3), TXTG), txt('1m', 1.2, Wp(24.5, 12.6, -0.3), TXT)]
for zz, lab in ((-8, '0.00042'), (-4, '0.00051'), (0, '0.00063'), (4, '0.00080'), (8, '0.00104')): CHART.append(txt(lab, 0.95, Wp(25.2, zz - 0.4, -0.3), TXT))
CND = []
for i, (o_, c_, hi, lo) in enumerate(ser):
    up = c_ >= o_; mt = PG if up else PR; bot, top = min(o_, c_), max(o_, c_)
    bd = box('cn', (0.8, 0.5, max(0.18, top - bot)), Wp(XS[i], (top + bot) / 2, 0.0), mt); wk = box('wk', (0.1, 0.1, hi - lo), Wp(XS[i], (hi + lo) / 2, 0.0), mt)
    CND.append((bd, wk)); CHART += [bd, wk]
    t_on = 0.15 + i * 0.1                                # the chart ticks in live
    for o in (bd, wk): show(o, F(t_on))
    for o in (bd, wk): o.hide_render = False
# the last candle ticks up and down before it pumps
LBD, LWK = CND[-1]

# ---------------------------------------------------------------- THE GOD CANDLE
GC = bpy.data.objects.new('GC', None); COL.objects.link(GC); GC.location = Wp(XG, GB)
def cb(name, mt, org_z=True):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
    if org_z: o.data.transform(Matrix.Translation((0, 0, 0.5)))
    o.data.materials.append(mt); o.parent = GC; return o
BODY = cb('gc_body', GCM); WICKO = cb('gc_wick', WICK, False)
HC = 1.25; HG = 13.2; WG = 3.3; DG = 3.3
def gc_shape(t):
    """(w, d, h) of the body, and the wick's (width, length, centre z)."""
    u = (t - T_PUMP) / (T_FULL - T_PUMP); e = sm(u) ** 1.4
    h = tick(HC, HG, e) if t >= T_PUMP else HC; w = tick(0.8, WG, sm(u)) if t >= T_PUMP else 0.8; d = tick(0.5, DG, sm((t - 4.25) / 0.7)) if t >= T_PUMP else 0.5
    wl = h * 1.5 if t < T_PUMP else h * 1.5 + 5.0 * sm((t - T_PUMP) / 0.5) * (1 - 0.6 * sm((t - T_HOVER) / 0.8))
    return (w, d, h), (0.1 + 0.3 * sm(u), wl)
for fr in range(F(0.0), F(T_IMP + 3.0)):
    t = (fr - 1) / FPS; (w, d, h), (ww, wl) = gc_shape(min(t, T_FULL))
    BODY.scale = (w, d, h); BODY.keyframe_insert('scale', frame=fr)
    WICKO.scale = (ww, ww, wl); WICKO.location = (0, 0, h / 2 + (wl - 1.5 * h) / 2 * 0.0); WICKO.keyframe_insert('scale', frame=fr); WICKO.keyframe_insert('location', frame=fr)
for o in (BODY, WICKO):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
# its light: it gets brighter and brighter, and lights the whole stadium as it falls
LAMP = bpy.data.lights.new('gcl', 'POINT'); LAMP.color = (0.35, 1.0, 0.4); LAMP.shadow_soft_size = 1.5; LO = bpy.data.objects.new('gcl', LAMP); COL.objects.link(LO); LO.parent = GC; LO.location = (0, 0, 7)
for t, e in ((0, 0), (T_PUMP - 0.1, 0), (T_PUMP + 0.3, 20000), (T_FULL, 60000), (T_HOVER + 0.6, 120000), (T_DROP, 160000), (T_IMP - 0.6, 260000), (T_IMP, 400000), (T_IMP + 0.04, 3000000), (T_IMP + 0.35, 220000), (T_IMP + 2.5, 90000), (T_IMP + 6, 60000)):
    LAMP.energy = e; LAMP.keyframe_insert('energy', frame=F(t))
# motion: it hovers out of the chart (toward us), charges, drops, plants
ZB0 = GC.location.z; HOVER = Vector((GX, GY, ZB0 + 3.0)); SINK = -0.35
tf = T_IMP - T_DROP; gg = 2 * (HOVER.z - SINK) / (tf * tf)
rg = random.Random(5); TILT = (0.045, -0.03)
def gc_loc(t):
    if t < T_HOVER: return Vector(GC.location) if False else Wp(XG, GB)
    if t < T_DROP:
        u = sm((t - T_HOVER) / (T_DROP - T_HOVER - 0.15)); p0 = Wp(XG, GB); p_ = p0.lerp(HOVER, u)
        sh = max(0, (t - 5.2)) * 0.05; return p_ + Vector((math.sin(t * 61) * sh, math.cos(t * 53) * sh, math.sin(t * 47) * sh))
    if t < T_IMP: dt = t - T_DROP; return Vector((GX, GY, HOVER.z - 0.5 * gg * dt * dt))
    return Vector((GX, GY, SINK))
def gc_rot(t):
    if t < T_HOVER: return (0, 0, 0)
    if t < T_DROP: u = sm((t - T_HOVER) / (T_DROP - T_HOVER)); return (-0.14 * math.sin(u * math.pi * 0.9), 0.0, u * 0.5)
    if t < T_IMP: dt = t - T_DROP; return (TILT[0] * dt, TILT[1] * dt, 0.5 + 0.45 * dt)
    return (TILT[0] * tf, TILT[1] * tf, 0.5 + 0.45 * tf)
for fr2 in range(F(0) * 2, F(T_IMP + 3.0) * 2):
    fr = fr2 / 2.0; t = (fr - 1) / FPS
    GC.location = gc_loc(t); GC.rotation_euler = gc_rot(t); GC.keyframe_insert('location', frame=fr); GC.keyframe_insert('rotation_euler', frame=fr)
for fc in GC.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
# the impact: squash, then the shock rattles it
SQ = [(T_IMP - 0.01, (1, 1, 1)), (T_IMP + 0.04, (1.14, 1.14, 0.9)), (T_IMP + 0.12, (0.97, 0.97, 1.03)), (T_IMP + 0.22, (1.03, 1.03, 0.98)), (T_IMP + 0.4, (1, 1, 1))]
for t, s in SQ: GC.scale = s; GC.keyframe_insert('scale', frame=F(t))
# the trail: green flame streaming off its top, and a long glow, while it falls
TRAIL = []
BEAMM = glow('beam', (0.3, 1.0, 0.4), 6.0, 0.25); TRLM = glow('trl', (0.35, 1.0, 0.45), 7.0, 0.3)
for i in range(9):
    o = ico('trail', 1.0, (0, 0, HG + 2.0 + i * 2.6), FIREGRN, 2); o.parent = GC; o.visible_shadow = False
    s = 2.1 - i * 0.2; o.scale = (s, s, s * 2.2); show(o, F(T_DROP - 0.1), F(T_IMP) - 1); TRAIL.append(o)
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=2.3, radius2=0.2, depth=30, location=(0, 0, HG + 16)); tc = bpy.context.object; tc.data.materials.append(TRLM); tc.parent = GC; tc.visible_shadow = False
show(tc, F(T_DROP - 0.1), F(T_IMP) - 1)
# hover charge: crackling energy rings round it
RINGM = glow('ring', (0.4, 1.0, 0.5), 20.0, 0.8)
for i in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.05, major_segments=48, location=(0, 0, 0)); o = bpy.context.object; o.data.materials.append(RINGM); o.parent = GC; o.visible_shadow = False
    for t0 in (T_PUMP + 0.5 + 0.35 * i, T_HOVER + 0.3 + 0.3 * i):
        for fr2 in range(0, 22):
            u = fr2 / 21.0; o.location = (0, 0, tick(0.3, HG, u * u)); s = tick(5.5, 2.0, u); o.scale = (s, s, s); o.keyframe_insert('location', frame=F(t0) + fr2); o.keyframe_insert('scale', frame=F(t0) + fr2)
        o.scale = (0.001,) * 3; o.keyframe_insert('scale', frame=F(t0) + 22)
    o.scale = (0.001,) * 3; o.keyframe_insert('scale', frame=1)

# ---------------------------------------------------------------- the pane shatters, the chart blows out of the way
def burst_away(o, t, c, speed, seed, life=1.5, up=3.0):
    r_ = random.Random(seed); f0 = F(t); p0 = o.matrix_world.translation.copy(); s0 = o.scale.copy(); d = p0 - c; d.y = 0; d = d.normalized() if d.length > 0.01 else Vector((1, 0, 0))
    v = d * speed * r_.uniform(0.4, 1.3) + Vector((0, r_.uniform(-16, -3), r_.uniform(-1, up))); spin = Vector((r_.uniform(-6, 6), r_.uniform(-6, 6), r_.uniform(-6, 6)))
    if o.animation_data: pass
    o.location = p0; key(o, 'location', f0 - 1); o.rotation_euler = (0, 0, 0); key(o, 'rotation_euler', f0 - 1)
    n = int(life * FPS)
    for k_ in range(0, n + 1, 2):
        tt = k_ / FPS; o.location = p0 + v * tt + Vector((0, 0, -0.5 * 11 * tt * tt)); key(o, 'location', f0 + k_); o.rotation_euler = spin * tt; key(o, 'rotation_euler', f0 + k_)
    o.scale = s0; key(o, 'scale', f0 + n - 2); o.scale = (0.0001,) * 3; key(o, 'scale', f0 + n)
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
cg = Wp(XG, GB + 5)
for i, o in enumerate(CHART):
    dist = (o.matrix_world.translation - cg).length; burst_away(o, T_BREAK + dist * 0.011, cg, 9 + 14 * math.exp(-dist / 22), 100 + i, 1.3 + 0.4 * (i % 3))
# a green flash at the break
FL = bpy.data.lights.new('brk', 'POINT'); FL.color = (0.5, 1.0, 0.55); FO = bpy.data.objects.new('brk', FL); COL.objects.link(FO); FO.location = Wp(XG - 2, GB + 6, -4)
for t, e in ((T_BREAK - 0.05, 0), (T_BREAK, 900000), (T_BREAK + 0.25, 60000), (T_BREAK + 0.8, 0)): FL.energy = e; FL.keyframe_insert('energy', frame=F(t))
for i in range(36):
    r_ = random.Random(400 + i); a = r_.uniform(0, 6.28); v = Vector((math.cos(a) * r_.uniform(6, 26), r_.uniform(-24, -3), math.sin(a) * r_.uniform(6, 26))); o = box('spk', (0.06, 0.06, 0.55), Wp(XG, GB + 6, -0.5), SPARKG); o.visible_shadow = False
    o.rotation_euler = v.to_track_quat('Z', 'Y').to_euler(); o.scale = (0.001,) * 3; key(o, 'scale', F(T_BREAK) - 1); o.scale = (1, 1, 1); key(o, 'scale', F(T_BREAK))
    p0 = Wp(XG, GB + 6, -0.5)
    for k_ in range(0, 25, 2): tt = k_ / FPS; o.location = p0 + v * tt + Vector((0, 0, -0.5 * 10 * tt * tt)); key(o, 'location', F(T_BREAK) + k_)
    o.scale = (0.001,) * 3; key(o, 'scale', F(T_BREAK) + 25); const(o); linear(o)

# ---------------------------------------------------------------- the beam on the ground, the cracks spreading, and the court's lights going green
BEAM = None
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.0, depth=80, location=(GX, GY, 40)); BEAM = bpy.context.object; BEAM.name = 'beam'; BEAM.data.materials.append(BEAMM); BEAM.visible_shadow = False
for t, s in ((0, 0.0001), (T_DROP - 0.9, 0.0001), (T_DROP - 0.55, 3.3), (T_IMP - 0.01, 3.4), (T_IMP + 0.05, 4.4), (T_IMP + 0.5, 0.0001)): BEAM.scale = (s, s, 1); key(BEAM, 'scale', F(t))
# ground glow disc
bpy.ops.mesh.primitive_plane_add(size=2, location=(GX, GY, 0.03)); DISC = bpy.context.object; DISC.data.materials.append(bpy.data.materials.new('disc')); dm = DISC.data.materials[0]; dm.use_nodes = True; nt = dm.node_tree; nt.nodes.clear()
tcn = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Location'].default_value = (-0.5, -0.5, 0); gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
rp = nt.nodes.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = 0.5; rp.color_ramp.elements[1].position = 1.0; em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.3, 1.0, 0.4, 1); em.inputs['Strength'].default_value = 10
trp = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); outn = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(tcn.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], gr.inputs['Vector']); nt.links.new(gr.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], mx.inputs['Fac'])
nt.links.new(trp.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], outn.inputs['Surface']); DISC.visible_shadow = False
for t, s in ((0, 0.0001), (T_DROP - 0.9, 0.0001), (T_IMP - 0.01, 5.0), (T_IMP + 0.03, 15.0), (T_IMP + 3.0, 9.0), (T_IMP + 8.0, 7.0)): DISC.scale = (s, s, 1); key(DISC, 'scale', F(t))
# radial cracks
rc = random.Random(77); CRK = []
def crack(ang, L, w, at, depth=0):
    cx, cy = at; cr = pbox('crk', CRACK, (-0.5, 0, 0)); cd = pbox('crkd', CRACKD, (-0.5, 0, 0))
    for o, ww, zz in ((cd, w * 2.6, 0.012), (cr, w, 0.03)):
        o.location = (cx, cy, zz); o.rotation_euler = (0, 0, ang); o.scale = (0.0001, ww, 0.04); key(o, 'scale', 1)
        key(o, 'location', 1); key(o, 'rotation_euler', 1)
        o.scale = (L * 0.22, ww, 0.04); key(o, 'scale', F(T_DROP - 0.55)); o.scale = (L * 0.4, ww, 0.04); key(o, 'scale', F(T_IMP - 0.02)); o.scale = (L, ww, 0.04); key(o, 'scale', F(T_IMP + 0.22))
        o.scale = (L, ww, 0.04); key(o, 'scale', F(T_IMP + 10))
    CRK.append((cr, cd))
    if depth < 1:
        for j in range(2):
            u = rc.uniform(0.35, 0.8); b = ang + rc.choice((-1, 1)) * rc.uniform(0.45, 0.9)
            crack(b, L * rc.uniform(0.3, 0.5), w * 0.65, (cx + math.cos(ang) * L * u, cy + math.sin(ang) * L * u), depth + 1)
for i in range(18):
    crack(i / 18 * 6.283 + rc.uniform(-0.15, 0.15), rc.uniform(7, 16), rc.uniform(0.16, 0.34), (GX, GY))
# green shock: rings along the ground, a dome, a pillar of green light
SW = []
for (rad, mt) in ((1.0, glow('sw1', (0.35, 1.0, 0.45), 30, 0.95)), (1.0, glow('sw2', (0.9, 1.0, 0.9), 30, 0.9))):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.09, major_segments=96, location=(GX, GY, 0.35)); o = bpy.context.object; o.data.materials.append(mt); o.visible_shadow = False; SW.append(o)
for o, k_, ln in ((SW[0], 38.0, 26), (SW[1], 52.0, 18)):
    for f, s in ((F(T_IMP) - 1, 0.001), (F(T_IMP), 0.8), (F(T_IMP) + ln, k_), (F(T_IMP) + ln + 1, 0.001)): o.scale = (s, s, min(s, 1.5)); key(o, 'scale', f)
    linear(o)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=48, ring_count=24, location=(GX, GY, 0)); DOME = bpy.context.object; DOME.data.materials.append(glow('dome', (0.4, 1.0, 0.5), 8.0, 0.22)); DOME.visible_shadow = False
for f, s in ((F(T_IMP) - 1, 0.001), (F(T_IMP), 1.5), (F(T_IMP) + 8, 20.0), (F(T_IMP) + 18, 30.0), (F(T_IMP) + 19, 0.001)): DOME.scale = (s, s, s * 0.7); key(DOME, 'scale', f)
linear(DOME)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=90, location=(GX, GY, 45)); PIL = bpy.context.object; PIL.data.materials.append(glow('pillar', (0.4, 1.0, 0.5), 14, 0.35)); PIL.visible_shadow = False
for t, s in ((0, 0.0001), (T_IMP - 0.01, 0.0001), (T_IMP, 2.8), (T_IMP + 0.4, 2.2), (T_IMP + 1.5, 1.4), (T_IMP + 4, 0.9), (T_IMP + 8, 0.0001)): PIL.scale = (s, s, 1); key(PIL, 'scale', F(t))
# debris, dust, sparks, coins
SPARK = SPARKG
explode(Vector((GX, GY, 1.6)), T_IMP, 7.5, FIREGRN, 120, 61, SMOKEG, light=(0.3, 1.0, 0.35))
explode(Vector((GX, GY, 0.8)), T_IMP + 0.05, 5.0, FIRE, 40, 62, DUST, light=(1.0, 0.7, 0.3))
for i in range(5): sparks(Vector((GX, GY, 1.0 + i)), T_IMP + 0.02 * i, 26, 70 + i, 14.0)
dust(Vector((GX, GY, 0.4)), T_IMP, 4.5, 90, 12)
for i in range(46):
    r_ = random.Random(900 + i); a = r_.uniform(0, 6.28); sp_ = r_.uniform(3, 15); v = Vector((math.cos(a) * sp_, math.sin(a) * sp_, r_.uniform(14, 30))); bpy.ops.mesh.primitive_cylinder_add(radius=0.38, depth=0.09, vertices=18); o = bpy.context.object; o.data.materials.append(COINM)
    p0 = Vector((GX, GY, 1.0)); spin = Vector((r_.uniform(-14, 14), r_.uniform(-14, 14), 0)); f0 = F(T_IMP) + 1; o.scale = (0.001,) * 3; key(o, 'scale', f0 - 1); o.scale = (1, 1, 1); key(o, 'scale', f0)
    for k_ in range(0, 150, 2):
        tt = k_ / FPS; z = p0.z + v.z * tt - 0.5 * 24 * tt * tt
        if z < 0.1: break
        o.location = p0 + Vector((v.x * tt, v.y * tt, 0)); o.location.z = z; key(o, 'location', f0 + k_); o.rotation_euler = (spin.x * tt, spin.y * tt, 0); key(o, 'rotation_euler', f0 + k_)
    const(o); linear(o)

# ---------------------------------------------------------------- the crowd and the fighters watching
def_fan = '''def fan_sched(team, j):
    return [(0, 'idle', 1), (3.2 + 0.4 * j, 'emote', 0.8 + 0.3 * j), (T_BREAK + 0.2, 'hit', 0.4), (T_DROP + 0.1, 'ready', 1.0), (T_IMP - 0.4, 'hit', 0.5), (T_IMP + 0.25, 'lose', 1.0 + 0.3 * j), (T_IMP + 1.4 + 0.5 * j, 'win', 1.0 + 0.3 * j)]
'''
cr_src = '\n'.join(src[i_crowd:i_crowdcall]); a0_ = cr_src.index('def fan_sched'); a1_ = cr_src.index('SOURCES = ')
exec(compile(cr_src[:a0_] + def_fan + cr_src[a1_:], CL, 'exec'), g)
KEEP_OUT = []
crowd()
CREW = {}
for i, (uid, h, team) in enumerate((('pepe', 2.6, 'b'), ('whale', 4.6, 'b'), ('bonk', 2.6, 'b'), ('floki', 3.0, 'b'), ('swordcat', 2.7, 'b'), ('toshi', 2.7, 'b'), ('giga', 3.4, 'r'), ('troll', 2.8, 'r'), ('zcat', 2.5, 'r'), ('ket', 2.5, 'r'))):
    ang = 0.35 + i * 0.62; r_ = (6.5 if i % 2 == 0 else 10.5) + (1.5 if uid == 'whale' else 0); x, y = GX + math.cos(ang) * r_, GY + math.sin(ang) * r_ * 0.8
    u = fighter(uid, h, team); CREW[uid] = u; hd = heading(GX - x, GY - y)
    place(u, (x, y, 0), hd)
    sched(u, [(0, 'ready', 1.0), (T_BREAK, 'emote', 0.5), (T_HOVER + 0.4, 'hit', 0.45), (T_IMP - 0.5, 'hit', 0.8)])
    d = Vector((x - GX, y - GY, 0)); fling(u, T_IMP + 0.04, (d.x, d.y), up=11 + 3 * (i % 3), dist=14 + (7 - min(r_, 7)) * 0.0 + 4 * (i % 2), dur=2.4)

# ---------------------------------------------------------------- the light: dusk, the chart's own light, green under it all
def keylight(name, loc, target, e, size=4.0, col=(1.0, 0.95, 0.85)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = e; ld.size = size; ld.color = col; o = bpy.data.objects.new(name, ld); COL.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); COL.objects.link(sun); sun.data.energy = 1.0; sun.data.angle = math.radians(3); sun.data.color = (1.0, 0.6, 0.34)
sun.rotation_euler = (math.radians(70), 0, math.radians(205))
keylight('chartkey', (CH.x + 12, CH.y - 42, CH.z + 12), CH + Vector((8, 0, -6)), 60000, 26, (0.75, 0.85, 1.0)); keylight('chartrim', (CH.x - 40, CH.y + 18, CH.z + 20), CH, 30000, 18, (1.0, 0.5, 0.3))
keylight('red_wash', (9, 3, 16), (9, -9, 0), 9000, 14, (1.0, 0.25, 0.15)); keylight('blue_wash', (9, -35, 16), (9, -23, 0), 9000, 14, (0.2, 0.45, 1.0)); keylight('fill', (9, -40, 9), (9, -21, 2), 5000, 10, (0.7, 0.85, 1.0))
for o in bpy.data.objects:
    if o.type == 'LIGHT': o.visible_camera = False

# ---------------------------------------------------------------- the edit
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); COL.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.dof.use_dof = True; cam.data.clip_end = 3000
SHOTS = []; _t = [0.0]
def SH(dur, a0, s0, s1, p0, p1, l0, l1, lens, fstop=2.8, shake=0.0, lens1=None, fp=0, fl=0, orb=None):
    SHOTS.append(dict(t0=round(_t[0], 4), t1=round(_t[0] + dur, 4), a0=a0, s0=s0, s1=s1, p0=list(p0), p1=list(p1), l0=list(l0), l1=list(l1), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake, fp=fp, fl=fl, orb=orb)); _t[0] += dur
GBW = Wp(XG, GB)       # (9, -17, ~53): the candle's foot on the chart
# 1. the chart, live: a slow dolly across the candles
SH(2.4, 0.2, 1, 1, (-6, -33, 49), (1, -30, 52), (3, -17, 50), (11, -17, 52.5), 60, 2.0, 0.25, 85)
SH(1.1, 2.6, 1, 1, (-6, -31, 37), (0, -29, 40), (0, -17, 56), (7, -17, 57), 22, 2.8, 0.2)                       # low, looking up at the whole chart
# 2. the pump: it grows, rips through the glass
SH(1.2, 3.7, 0.5, 0.3, (16, -25, 49), (14.5, -22, 51), (9, -17, 52), (9, -17, 56), 35, 2.0, 0.3)
SH(1.4, 4.3, 0.25, 0.25, (9, -37, 45), (9, -28, 50), (9, -17, 55), (9, -17, 57), 20, 2.8, 0.7)
SH(1.0, 4.65, 0.3, 0.5, (5, -3, 49), (9, -6, 52), (9, -17, 54), (9, -17, 55.5), 28, 2.8, 0.5)
# 3. it hovers and charges: an orbit
SH(1.6, 4.9, 0.5, 0.7, (0, 0, 0), (0, 0, 0), (9, -19, 55), (9, -21, 57), 28, 2.8, 0.2, orb=[9, -19, 55.5, 17, -0.9, 1.5, -2.0, 3.0])
# 4. the fall
SH(1.0, 5.8, 0.85, 0.85, (0, -9, 15), (0, -6.5, 11), (0, 0, -12), (0, 0, -14), 24, 4.0, 0.4, fp=1, fl=1)
SH(0.8, 6.65, 0.8, 0.8, (12, -26, 0.6), (11.6, -25.5, 0.7), (0, 0, 3), (0, 0, 2), 14, 4.0, 0.3, 18, fp=0, fl=1)
SH(0.6, 7.29, 0.8, 0.8, (17, -8, 2), (15, -7, 1), (0, 0, 0), (0, 0, 0), 32, 2.8, 0.4, fp=1, fl=1)
SH(0.55, 7.77, 0.5, 0.2, (12.5, -23.5, 0.25), (12.3, -23.2, 0.3), (9, -21, 8), (9, -21, 2.5), 12, 5.6, 0.2)
# 5. the slam, in slow motion
SH(1.8, 7.96, 0.12, 0.3, (0, 0, 0), (0, 0, 0), (9, -21, 5), (9, -21, 6), 24, 4.0, 0.2, orb=[9, -21, 4.0, 14, 0.3, 2.8, -1.5, 2.5])
SH(1.2, 8.34, 0.3, 0.45, (9, -36, 0.35), (9, -32, 0.45), (9, -21, 2), (9, -21, 3), 16, 5.6, 0.3)
SH(1.0, 8.68, 0.45, 0.45, (9, -21.5, 40), (9.5, -21.5, 25), (9, -21, 0), (9, -21, 0), 20, 5.6, 0.3)
SH(1.0, 9.13, 0.5, 0.8, (22, -36, 6), (19, -35, 9), (9, -21, 6), (9, -21, 8), 35, 4.0, 0.3)
# 6. the aftermath: a crane up and back
SH(3.2, 9.7, 1.0, 1.0, (9, -30, 3), (9, -62, 32), (9, -21, 7), (9, -21, 9), 24, 4.0, 0.15, 32)
N_FILM = int(round(_t[0] * FPS))
print('FILM ends at', _t[0], 'frames', N_FILM)
json.dump(dict(fps=FPS, first=1, last=N_FILM, shots=SHOTS), open(os.path.join(MYHERE, 'edl.json'), 'w'), indent=0)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=False)
print('SAVED', OUT)
