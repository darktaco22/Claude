"""MEME ROYALE: "A NATURAL HISTORY".  A deadpan wildlife documentary about the arena at dawn: the Pepe (down 94%), the paper-handed herd
(a 2% dip), two males on the bridge (no whitepaper), a god candle, and the rug pull - which the narrator turns out to be in.
Built on the clash arena (its court, units and FX code) without the stadium: a meadow, hills, trees and mist instead.

  python3 tex.py TEX_DIR ; python3 voices.py KOKORO_DIR VO_DIR
  blender -b --factory-startup -P scene.py -- --out scene.blend --tex TEX_DIR --vo VO_DIR      (writes edl.json; render with render_edl.py)
24 fps, 1280x544 (2.35:1); finish.py grades, letterboxes, titles and mixes the sound."""
import bpy, bmesh, math, json, os, sys, random
from mathutils import Vector, Matrix, Quaternion, Euler, noise

MYHERE = os.path.dirname(os.path.abspath(__file__)); CL = os.path.join(MYHERE, '..', 'clash', 'scene.py')
src = open(CL).read().split('\n')
def line(prefix): return next(i for i, l in enumerate(src) if l.startswith(prefix))
i_stad = line('# ================================================================ the stadium'); i_units = line('# ================================================================ units')
i_battle = line('# ================================================================ CLASH AT THE BRIDGE: the battle'); i_ns = line('N_, S_ = heading(0, 1)')
g = globals(); g['__file__'] = CL
exec(compile('\n'.join(src[:i_stad]), CL, 'exec'), g)                   # helpers, the arena, sky, ground
exec(compile('\n'.join(src[i_units:i_battle]), CL, 'exec'), g)          # units, FX (explode, rubble ...)
exec(compile('\n'.join(src[i_battle:i_ns]), CL, 'exec'), g)             # smooth(), sparks(), dust(), stand(), fight()
HERE = MYHERE; TEXD = arg('--tex', os.path.expanduser('~/wild_work/tex')); VOD = arg('--vo', os.path.expanduser('~/wild_work/vo'))
VO = json.load(open(os.path.join(VOD, 'vo.json')))
sc.render.resolution_x, sc.render.resolution_y = 1280, 544
sc.cycles.samples = int(arg('--samples', '10')); T_END = 62.0; sc.frame_end = F(T_END)
rnd = random.Random(11)
DUST = smoke_mat('dust_soft', (0.3, 0.27, 0.2), 0.3)
def sm(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def vis(o, windows):
    """Visible only inside the (f_on, f_off) windows, by keyed scale."""
    s = o.scale.copy(); o.scale = s * 0.0001; o.keyframe_insert('scale', frame=0)
    for f0, f1 in windows:
        o.scale = s * 0.0001; o.keyframe_insert('scale', frame=f0 - 1); o.scale = s; o.keyframe_insert('scale', frame=f0)
        if f1: o.keyframe_insert('scale', frame=f1); o.scale = s * 0.0001; o.keyframe_insert('scale', frame=f1 + 1)
    const(o); o.scale = s
def hold(u, name, f0, speed=1.0, blend=3):
    """Play a clip once from f0 and hold its last pose."""
    a = u['clips'][name]; a0, a1 = a.frame_range; tr = u['arm'].animation_data.nla_tracks.new(); s = tr.strips.new(f'{name}_{f0}h', int(f0), a)
    s.action_frame_start = a0; s.action_frame_end = a1; s.scale = (FPS / 30.0) / speed; s.extrapolation = 'HOLD_FORWARD'; s.blend_type = 'REPLACE'; s.use_auto_blend = False; s.blend_in = blend
def glow(name, col, strength, alpha):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = strength; mx.inputs['Fac'].default_value = alpha
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs['Surface']); return m
def pt_light(name, loc, col, parent=None, soft=2.0):
    ld = bpy.data.lights.new(name, 'POINT'); ld.color = col; ld.shadow_soft_size = soft; ld.energy = 0; o = bpy.data.objects.new(name, ld); COL.objects.link(o); o.location = loc
    if parent: o.parent = parent
    return o
def ekeys(lo, ks):
    for f, e in ks: lo.data.energy = e; lo.data.keyframe_insert('energy', frame=f)

# ================================================================ the timeline (animation seconds)
T_PLIP = 19.0                      # a tiny red candle; the herd bolts
T_D0, T_KO = 25.0, 30.0            # the duel on the bridge; both land a punch at once
T_RUMBLE, T_ERUPT = 33.0, 36.0     # the ground cracks; the god candle
T_RUG = 45.0                       # the rug goes
T_RED, T_TIP, T_FALL = T_RUG + 0.5, T_RUG + 1.4, T_RUG + 3.3      # the candle turns red, tips over, lands
T_AFT = T_FALL + 2.0
PEPE_P = Vector((-10.0, -22.0, 0)); HC = Vector((32.0, -19.0, 0)); G = Vector((22.0, -9.0, 0)); TC = Vector((31.4, -25.7, 0))
GH, GW = 28.0, 3.4

# ================================================================ the land: meadow, hills, trees, grass, birds
def ground_h(x, y):
    r = math.hypot(x - 20, y + 16); m = sm((r - 85) / 240.0)
    return m * (9.0 + 15.0 * (0.5 + 0.5 * noise.noise(Vector((x * 0.004, y * 0.004, 0.3)))) + 5.0 * noise.noise(Vector((x * 0.013, y * 0.013, 1.7)))) + 0.25 * sm((r - 30) / 60.0) * noise.noise(Vector((x * 0.05, y * 0.05, 5.0)))
bpy.data.objects.remove(bpy.data.objects['ground'])
bm = bmesh.new(); N = 180; S = 1600.0
vs = [[bm.verts.new((20 + (i / N - 0.5) * S, -16 + (j / N - 0.5) * S, 0)) for j in range(N + 1)] for i in range(N + 1)]
for row in vs:
    for v in row:
        # a finer grid near the arena: pull the vertices toward the centre
        dx, dy = v.co.x - 20, v.co.y + 16; r = math.hypot(dx, dy) / (S / 2); k = 0.25 + 0.75 * min(1.0, r) ** 1.5
        v.co.x = 20 + dx * k; v.co.y = -16 + dy * k; v.co.z = ground_h(v.co.x, v.co.y) - 0.03
for i in range(N):
    for j in range(N): bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
me = bpy.data.meshes.new('land'); bm.to_mesh(me); bm.free(); LAND = bpy.data.objects.new('land', me); COL.objects.link(LAND)
for p in me.polygons: p.use_smooth = True
GRASSM = texmat('meadow', 'grass.jpg', 0.09, 0.95, tint=(0.7, 0.95, 0.45)); me.materials.append(GRASSM)
# trees: flat-topped, savanna style
BARK = mat('bark', (0.09, 0.06, 0.04), 0.9); LEAF = mat('leaf', (0.07, 0.13, 0.03), 0.9); LEAF2 = mat('leaf2', (0.12, 0.15, 0.04), 0.9)
tr_ = random.Random(5)
for i in range(60):
    a = tr_.uniform(0, 2 * math.pi); r = tr_.uniform(62, 330); x = 20 + r * math.cos(a); y = -16 + r * math.sin(a); z = ground_h(x, y); h = tr_.uniform(4.5, 8.0)
    if 15 < x < 110 and -30 < y < -8: continue                       # the troll's way out stays clear
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.38, radius2=0.2, depth=h, location=(x, y, z + h / 2)); bpy.context.object.data.materials.append(BARK)
    for k in range(3):
        o = ico('canopy', 1.0, (x + tr_.uniform(-1.6, 1.6), y + tr_.uniform(-1.6, 1.6), z + h + tr_.uniform(-0.2, 0.7)), LEAF if k % 2 else LEAF2, 2); rr = tr_.uniform(2.6, 4.4); o.scale = (rr, rr * tr_.uniform(0.8, 1.1), rr * 0.32)
# grass: blades in the foreground of the long-lens shots (one mesh per patch)
BLADE = bpy.data.materials.new('blade'); BLADE.use_nodes = True; nt = BLADE.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.6
tc = nt.nodes.new('ShaderNodeTexCoord'); sx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sx.inputs[0])
rp = nt.nodes.new('ShaderNodeValToRGB'); E_ = rp.color_ramp.elements; E_[0].position = 0.0; E_[0].color = (0.03, 0.075, 0.012, 1); E_[1].position = 0.6; E_[1].color = (0.27, 0.34, 0.07, 1)
nt.links.new(sx.outputs['Z'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], b.inputs['Base Color'])
tl = nt.nodes.new('ShaderNodeBsdfTranslucent'); nt.links.new(rp.outputs['Color'], tl.inputs['Color']); mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = 0.45
out = nt.nodes['Material Output']; nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs['Surface'])
def grass(name, cx, cy, R, n, seed, hmin=0.25, hmax=0.7, hole=None):
    r_ = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        a = r_.uniform(0, 2 * math.pi); r = min(R, abs(r_.gauss(0, R * 0.5))); x = cx + r * math.cos(a); y = cy + r * math.sin(a)
        if hole and math.hypot(x - hole[0], y - hole[1]) < hole[2]: continue
        if 23.6 < x < 40.4 and -24.6 < y < -13.4: continue             # not under the rug
        if -0.5 < x < 18.5 and -32.5 < y < 0.5: continue             # not on the court
        h = r_.uniform(hmin, hmax); w = r_.uniform(0.012, 0.028); ya = r_.uniform(0, math.pi); wx, wy = math.cos(ya) * w, math.sin(ya) * w
        la = r_.uniform(0, 2 * math.pi); ln = r_.uniform(0.05, 0.4) * h; lx, ly = math.cos(la) * ln, math.sin(la) * ln; prev = None
        for k in range(4):
            u = k / 3; c = Vector((x + lx * u * u, y + ly * u * u, h * u)); ww = 1 - u * 0.92
            cur = (bm.verts.new(c - Vector((wx, wy, 0)) * ww), bm.verts.new(c + Vector((wx, wy, 0)) * ww))
            if prev: bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
            prev = cur
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); COL.objects.link(o); me.materials.append(BLADE); o.visible_shadow = False; return o
grass('g_pepe', PEPE_P.x, PEPE_P.y, 7.0, 9000, 1, hole=(PEPE_P.x, PEPE_P.y, 0.5)); grass('g_pepe_fg', -25.0, -23.2, 4.5, 5000, 2, 0.35, 0.9); grass('g_pepe_s', -8.6, -30.5, 4.0, 5000, 3, 0.3, 0.8)
grass('g_glide', -13.5, -36.5, 7.5, 8000, 4, 0.25, 0.65); grass('g_herd_fg', 29.0, -42.0, 5.0, 6000, 5, 0.35, 0.9); grass('g_herd', HC.x, HC.y, 12.0, 9000, 6, 0.15, 0.4)
grass('g_candle', G.x, G.y, 10.0, 7000, 7, 0.1, 0.3, hole=(G.x, G.y, 4.5)); grass('g_dip', 31.6, -27.5, 3.5, 5000, 8, 0.07, 0.2)
# drifting motes in the low sun, a flock of birds
MOTE = mat('mote', (1, 0.9, 0.7), 0.5, emit=(1.0, 0.85, 0.6), estr=2.0)
def motes(name, c, R, n, seed, drift):
    r_ = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        p = Vector((r_.uniform(-R, R), r_.uniform(-R, R), r_.uniform(0.2, 4.5))); s = r_.uniform(0.003, 0.007)
        vv = [bm.verts.new(p + Vector(d) * s) for d in ((1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
        for a_, b_, c_ in ((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)): bm.faces.new((vv[a_], vv[b_], vv[c_]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); COL.objects.link(o); me.materials.append(MOTE); o.visible_shadow = False
    o.location = c; key(o, 'location', 1); o.location = Vector(c) + Vector(drift); key(o, 'location', F(T_END)); linear(o); return o
motes('m_pepe', (PEPE_P.x - 3, PEPE_P.y - 2, 0), 9, 260, 1, (2.5, 1.0, 0.8)); motes('m_herd', (HC.x, HC.y - 4, 0), 12, 300, 2, (-2.0, 1.5, 0.6)); motes('m_glide', (-12, -34, 0), 7, 200, 3, (1.5, 1.0, 0.5))
bm = bmesh.new(); br = random.Random(9)
for i in range(17):
    c = Vector((br.uniform(-14, 14) + (i % 5) * 3, br.uniform(-8, 8), br.uniform(-2.5, 2.5))); s = br.uniform(0.5, 0.8); d = br.uniform(-0.25, 0.35)
    a_ = bm.verts.new(c); bm.faces.new((a_, bm.verts.new(c + Vector((-0.25, s, d))), bm.verts.new(c + Vector((0.3, s * 0.45, d * 0.4))))); bm.faces.new((a_, bm.verts.new(c + Vector((-0.25, -s, d))), bm.verts.new(c + Vector((0.3, -s * 0.45, d * 0.4)))))
me = bpy.data.meshes.new('birds'); bm.to_mesh(me); bm.free(); BIRDS = bpy.data.objects.new('birds', me); COL.objects.link(BIRDS); me.materials.append(mat('bird', (0.02, 0.02, 0.02), 0.9))
BIRDS.location = (-70, 40, 34); key(BIRDS, 'location', 1); BIRDS.location = (60, 70, 44); key(BIRDS, 'location', F(9.0)); linear(BIRDS)

# ================================================================ the cast
def actor(uid, h, subd=False): u = unit(uid, h); smooth(u, subd); return u
def face(dx, dy): return heading(dx, dy)
# the Pepe: he stands in the meadow and does nothing, for the whole film
PEPE = actor('pepe', 2.4, True); place(PEPE, PEPE_P, face(0.25, -1)); clip(PEPE, 'idle', 1, F(T_END) + 2, 0.8)
# the herd
HERD = []
for j, (uid, h, dx, dy, hd) in enumerate((('popcat', 2.0, -3.6, 1.6, 0.6), ('pnut', 1.9, -1.5, -1.2, -0.5), ('michi', 2.0, 0.6, 1.9, 2.4), ('apu', 2.1, 2.4, -0.4, -2.0),
                                          ('pippin', 1.9, 4.4, 1.5, 1.2), ('nyancat', 2.0, -0.4, 3.9, 3.0), ('moodeng', 2.3, 2.7, 3.6, -1.2), ('wojak', 2.1, -2.9, -3.0, 0.3))):
    u = actor(uid, h, j < 4); u['home'] = (HC.x + dx * 1.45, HC.y + dy * 1.3); u['hd'] = hd; u['j'] = j; HERD.append(u); r = u['root']
    place(u, (u['home'][0], u['home'][1], 0), hd, 1); clip(u, 'idle', 1, F(T_PLIP + 0.25 + 0.07 * j), 0.9 + 0.05 * (j % 3), 0)
    key(r, 'location', F(T_PLIP + 0.25 + 0.07 * j)); key(r, 'rotation_euler', F(T_PLIP + 0.25 + 0.07 * j))
    # the bolt: a start, then flat out to the east
    t0 = T_PLIP + 0.25 + 0.07 * j; clip(u, 'hit', F(t0), F(t0 + 0.3), 1.6, 1); far = (HC.x + 62 + 3 * j, HC.y + dy * 3.5 + (j % 3 - 1) * 4)
    ta = run_to(u, [u['home'], far], t0 + 0.3, 8.5 + 0.5 * (j % 3), 'run', 1.6)
    # ... and back for the candle: they crowd onto the rug, facing it
    ang = math.radians(200 + j * 20); slot = (HC.x + 4.6 * math.cos(ang) * (1.0 if j % 2 else 0.6) + (j - 3.5) * 0.9, HC.y + 2.4 * math.sin(ang) * (1 if j % 2 else 0.5) + 0.6); u['slot'] = slot
    t1 = T_ERUPT + 1.2 + 0.12 * j; back = (HC.x + 30 + 2 * j, HC.y + dy * 2.5)
    place(u, (back[0], back[1], 0), 0, F(t1) - 1)
    tb = run_to(u, [back, slot], t1, 9.5, 'run', 1.6); u['t_back'] = tb
    fh = face(G.x - slot[0], G.y - slot[1]); r.rotation_euler = (0, 0, fh + (0.0 if abs(fh - r.rotation_euler.z) < math.pi else (2 * math.pi if r.rotation_euler.z > fh else -2 * math.pi))); key(r, 'rotation_euler', F(tb) + 5)
    clip(u, 'win', F(tb), F(T_RUG + 0.04 * j), 1.0 + 0.06 * (j % 3))
    vis(r, [(F(T_PLIP - 4.8), F(ta)), (F(t1), None)])
# the two males on the left bridge
CH = actor('chillhouse', 3.0, True); GT = actor('goat', 3.0, True)
BX, BY = 3.5, -16.0
for u, y, hd, ph_ in ((CH, BY - 1.25, heading(0, 1), 0), (GT, BY + 1.25, heading(0, -1), 1)):
    place(u, (BX, y, 0), hd, 1); clip(u, 'ready', 1, F(T_D0 + 1.4), 1.0, 0); fight(u, T_D0 + 1.4, T_KO - 0.42, 1.0, ph_)
    a = u['clips']['attack2']; hitf = (UJ[u['id']]['clips']['attack2']['hit'] or 0.33) * FPS / 0.8; clip(u, 'attack2', F(T_KO) - int(hitf), F(T_KO) + 3, 0.8, 2); hold(u, 'die', F(T_KO) + 2, 1.0, 2)
    r = u['root']; key(r, 'location', F(T_KO)); r.location.y += -0.9 if u is CH else 0.9; key(r, 'location', F(T_KO) + 9)
for i, t in enumerate((T_D0 + 1.75, T_D0 + 2.5, T_D0 + 3.25, T_D0 + 4.0)): sparks(Vector((BX + 0.2 * (i % 2), BY, 2.3)), t, 12, 40 + i, 5.0)
sparks(Vector((BX, BY, 2.5)), T_KO, 46, 60, 10.0); dust(Vector((BX, BY - 1.6, 0.4)), T_KO + 0.3, 1.2, 61, 5); dust(Vector((BX, BY + 1.6, 0.4)), T_KO + 0.3, 1.2, 62, 5)
SHOCKM = mat('shockm', (1, 0.9, 0.6), 0.3, emit=(1.0, 0.85, 0.5), estr=30)
def shock(c, t, R, m=SHOCKM, n=16, thick=0.06):
    e = bpy.data.objects.new('shock', None); COL.objects.link(e); e.location = c
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=thick, major_segments=64, location=(0, 0, 0)); tor = bpy.context.object; tor.data.materials.append(m); tor.parent = e; tor.visible_shadow = False
    for f, s in ((F(t) - 1, 0.001), (F(t), 1.0), (F(t) + n, R), (F(t) + n + 1, 0.001)): e.scale = (s, s, min(s, 1.0)); key(e, 'scale', f)
    linear(e)
shock((BX, BY, 2.3), T_KO, 9.0)
for u in (CH, GT): vis(u['root'], [(F(T_D0 - 0.6), None)])
# the troll, at the east end of the rug
TROLL = actor('troll', 2.5, True); TX0 = HC.x + 8.9; r = TROLL['root']
place(TROLL, (TX0, HC.y, 0), heading(-1, 0), F(T_ERUPT + 3.0)); clip(TROLL, 'ready', F(T_ERUPT + 3.0), F(T_RUG), 0.8, 0)
TRUN = 30.0; T_RUNEND = T_RUG + 1.6
def troll_dx(t):
    if t < T_RUG: return 0.0
    if t < T_RUNEND: return TRUN * (t - T_RUG)
    return TRUN * (T_RUNEND - T_RUG) + 1.25 * (t - T_RUNEND)
key(r, 'rotation_euler', F(T_RUG) - 2); r.rotation_euler = (0, 0, heading(1, 0) - 2 * math.pi if heading(1, 0) > heading(-1, 0) else heading(1, 0)); key(r, 'rotation_euler', F(T_RUG) + 1)
for f in range(F(T_RUG), F(T_END) + 1):
    t = (f - 1) / FPS; x = TX0 + troll_dx(t); r.location = (x, HC.y, ground_h(x, HC.y)); key(r, 'location', f)
linear(r); clip(TROLL, 'run', F(T_RUG), F(T_RUNEND), 2.4, 1); clip(TROLL, 'walk', F(T_RUNEND), F(T_END) + 2, 1.0, 4); vis(r, [(F(T_ERUPT + 3.0), None)])

# ================================================================ a dip of two percent
REDC_ = mat('redcandle', (0.8, 0.02, 0.01), 0.4, emit=(1.0, 0.02, 0.01), estr=0.55)
tc_ = bpy.data.objects.new('tinycandle', None); COL.objects.link(tc_); tc_.location = TC
box('tc_body', (0.11, 0.11, 0.34), (0, 0, 0.25), REDC_, parent=tc_); box('tc_wick', (0.02, 0.02, 0.62), (0, 0, 0.31), REDC_, parent=tc_)
for f, s in ((F(T_PLIP) - 1, 0.001), (F(T_PLIP) + 3, 1.25), (F(T_PLIP) + 6, 0.92), (F(T_PLIP) + 9, 1.0)): tc_.scale = (1.2, 1.2, 1.2 * s); key(tc_, 'scale', f)
tc_.scale = (0.001,) * 3; key(tc_, 'scale', F(T_PLIP) - 2); const(tc_, ()); dust(TC + Vector((0, 0, 0.05)), T_PLIP, 0.22, 70, 4)
for j, u in enumerate(HERD): dust(Vector((u['home'][0] + 1.5, u['home'][1], 0.2)), T_PLIP + 0.6 + 0.07 * j, 0.45, 71 + j, 3); dust(Vector((u['home'][0] + 7, u['home'][1], 0.2)), T_PLIP + 1.0 + 0.07 * j, 0.55, 81 + j, 3)

# ================================================================ the god candle
GCM = bpy.data.materials.new('godcandle'); GCM.use_nodes = True; nt = GCM.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.25
GREEN, REDV = (0.01, 0.8, 0.1, 1), (0.9, 0.012, 0.008, 1)
tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.35; nz.inputs['Detail'].default_value = 4
nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); rgb = nt.nodes.new('ShaderNodeRGB'); rgb.name = 'tint'; rgb.outputs[0].default_value = GREEN
mxc = nt.nodes.new('ShaderNodeMixRGB'); mxc.blend_type = 'MULTIPLY'; mxc.inputs[0].default_value = 0.55; nt.links.new(rgb.outputs[0], mxc.inputs[1]); nt.links.new(nz.outputs['Color'], mxc.inputs[2])
nt.links.new(rgb.outputs[0], b.inputs['Base Color']); nt.links.new(mxc.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 0.85
for f, c in ((F(T_RED) - 1, GREEN), (F(T_RED) + 2, REDV), (F(T_RED) + 4, GREEN), (F(T_RED) + 6, REDV)): rgb.outputs[0].default_value = c; rgb.outputs[0].keyframe_insert('default_value', frame=f)
GC = bpy.data.objects.new('GC', None); COL.objects.link(GC); GC.location = G
body = box('gc_body', (GW, GW, GH), (0, 0, GH / 2), GCM, parent=GC); wick = box('gc_wick', (0.5, 0.5, 7.0), (0, 0, GH + 3.5), GCM, parent=GC)
# it comes up out of the ground: fast, a little overshoot
for t, z in ((T_ERUPT - 0.02, -GH - 8), (T_ERUPT + 0.55, 1.5), (T_ERUPT + 0.75, -0.6), (T_ERUPT + 0.95, 0.0)): GC.location = (G.x, G.y, z); key(GC, 'location', F(t))
# ... and, after the rug, falls over to the south like a tree
nf = F(T_FALL) - F(T_TIP)
for i in range(nf + 1):
    u_ = i / nf; GC.rotation_euler = (math.radians(89.0) * u_ ** 2.4, 0, 0); key(GC, 'rotation_euler', F(T_TIP) + i)
for i, a in enumerate((87.6, 89.0)): GC.rotation_euler = (math.radians(a), 0, 0); key(GC, 'rotation_euler', F(T_FALL) + 3 + 3 * i)
GC.rotation_euler = (0, 0, 0); GL = []
for i, z in enumerate((3.0, 12.0, 22.0)):
    lo = pt_light(f'gc_l{i}', (0, -GW, z), (0.15, 1.0, 0.3), GC, 3.0); GL.append(lo)
    ekeys(lo, ((F(T_ERUPT) - 1, 0), (F(T_ERUPT) + 3, 30000), (F(T_ERUPT) + 20, 9000), (F(T_RED) - 1, 9000), (F(T_FALL), 7000), (F(T_FALL) + 30, 3000)))
    for f, c in ((F(T_RED) - 1, (0.15, 1.0, 0.3)), (F(T_RED) + 6, (1.0, 0.08, 0.04))): lo.data.color = c; lo.data.keyframe_insert('color', frame=f)
# before it: cracks glowing green, pebbles lifting off the ground, the light under the grass
CRK = mat('crack', (0.1, 1, 0.3), 0.4, emit=(0.12, 1.0, 0.3), estr=28)
cr = random.Random(21)
for i in range(11):
    a = i * 2 * math.pi / 11 + cr.uniform(-0.2, 0.2); p = Vector((G.x, G.y, 0.012)); tgrow = T_RUMBLE + cr.uniform(0.0, 1.2)
    for k in range(4):
        L = cr.uniform(1.3, 2.6); a += cr.uniform(-0.6, 0.6); d = Vector((math.cos(a), math.sin(a), 0)); w = 0.34 * (1 - k * 0.2)
        o = box('crack', (L, w, 0.02), p + d * L / 2, CRK, rot=(0, 0, a)); o.visible_shadow = False
        f0 = F(tgrow + k * 0.45); o.scale = (0.001,) * 3; key(o, 'scale', f0 - 1); o.scale = (1, 0.3, 1); key(o, 'scale', f0 + 4); o.scale = (1, 1, 1); key(o, 'scale', F(T_ERUPT) - 3)
        o.scale = (1, 2.2, 1); key(o, 'scale', F(T_ERUPT)); o.scale = (1, 0.5, 1); key(o, 'scale', F(T_ERUPT) + 40); p = p + d * L
under = pt_light('under', (G.x, G.y, 0.6), (0.15, 1.0, 0.3), None, 1.5); ekeys(under, ((F(T_RUMBLE), 0), (F(T_RUMBLE) + 30, 1200), (F(T_ERUPT) - 2, 6000), (F(T_ERUPT) + 6, 0)))
for i in range(46):
    a = cr.uniform(0, 2 * math.pi); r = cr.uniform(1.2, 7.5); s = cr.uniform(0.04, 0.13); p = Vector((G.x + r * math.cos(a), G.y + r * math.sin(a), s * 0.4))
    o = box('pebble', (s, s * cr.uniform(0.6, 1.1), s * cr.uniform(0.5, 0.9)), p, RUB[i % 3]); t0 = T_RUMBLE + cr.uniform(0.2, 1.6); hz = cr.uniform(0.3, 1.9)
    key(o, 'location', F(t0)); key(o, 'rotation_euler', F(t0))
    for k in range(1, 9):
        t = t0 + (T_ERUPT - t0) * k / 8; o.location = p + Vector((0, 0, hz * sm(k / 8) + 0.05 * math.sin(k * 1.7 + i))); key(o, 'location', F(t)); o.rotation_euler = (k * 0.2 * (i % 3), k * 0.15, k * 0.1); key(o, 'rotation_euler', F(t))
    v = Vector((math.cos(a), math.sin(a), 0)) * cr.uniform(6, 16); vz = cr.uniform(6, 16); p1 = o.location.copy()
    for k in range(1, 12):
        tt_ = k * 0.12; o.location = p1 + v * tt_ + Vector((0, 0, max(-p1.z + 0.05, vz * tt_ - 4.9 * tt_ * tt_))); key(o, 'location', F(T_ERUPT + tt_))
explode(G + Vector((0, 0, 0.5)), T_ERUPT, 3.0, FIREGRN, 70, 31, DUST, light=(0.3, 1.0, 0.35))
GSH = mat('gshock', (0.3, 1, 0.5), 0.3, emit=(0.25, 1.0, 0.4), estr=30); shock((G.x, G.y, 0.4), T_ERUPT + 0.05, 46.0, GSH, 30, 0.05); shock((G.x, G.y, 9.0), T_ERUPT + 0.35, 30.0, GSH, 26, 0.04)
BEAM = glow('beam', (0.05, 1.0, 0.2), 2.0, 0.07)
bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=900, vertices=24, location=(G.x, G.y, 450)); beam = bpy.context.object; beam.data.materials.append(BEAM); beam.visible_shadow = False
for f, s in ((F(T_ERUPT) - 8, 0.001), (F(T_ERUPT) - 2, 0.5), (F(T_ERUPT) + 2, 2.6), (F(T_ERUPT) + 30, 2.0), (F(T_ERUPT) + 70, 0.001)): beam.scale = (s, s, 1); key(beam, 'scale', f)
for j, u in enumerate(HERD): dust(Vector((u['slot'][0] + 3.0, u['slot'][1], 0.2)), u['t_back'] - 0.3, 0.5, 120 + j, 2)

# ================================================================ the rug, and the pull
RUGM = texmat('rug', os.path.join(TEXD, 'rug.png'), box=False, rough=0.95); RW, RD = 16.0, 10.5
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=64, y_segments=42, size=0.5); uvl = bm.loops.layers.uv.new('uv')
for f_ in bm.faces:
    for l_ in f_.loops: l_[uvl].uv = (l_.vert.co.x + 0.5, l_.vert.co.y + 0.5)
me = bpy.data.meshes.new('rug'); bm.to_mesh(me); bm.free()
RUG = bpy.data.objects.new('rug', me); COL.objects.link(RUG); RUG.scale = (RW, RD, 1); me.materials.append(RUGM); RUG.location = (HC.x, HC.y, 0.035)
for p in me.polygons: p.use_smooth = True
wv = RUG.modifiers.new('wave', 'WAVE'); wv.use_x = True; wv.use_y = False; wv.width = 0.22; wv.narrowness = 4.0; wv.speed = 0.06; wv.height = 0.0; wv.time_offset = -400
for f, h in ((F(T_RUG) - 2, 0.0), (F(T_RUG) + 2, 0.5), (F(T_RUNEND), 0.35)): wv.height = h; wv.keyframe_insert('height', frame=f)
ROPE = mat('rope', (0.75, 0.6, 0.35), 0.9); bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=1.0, vertices=8); rope = bpy.context.object; rope.data.materials.append(ROPE)
a_, b_ = Vector((HC.x + RW / 2, HC.y, 0.05)), Vector((TX0 - 0.25, HC.y, 1.55)); rope.location = (a_ + b_) / 2 - Vector(RUG.location); rope.rotation_euler = (b_ - a_).to_track_quat('Z', 'Y').to_euler(); rope.scale = (1 / RW, 1 / RD, (b_ - a_).length)
rope.parent = RUG
def rug_dx(t):
    for tt_, d in ((T_RUG - 1.7, 0.16), (T_RUG - 1.05, 0.2)):          # two test tugs
        if tt_ <= t < tt_ + 0.5: return d * math.exp(-(t - tt_) * 7) * math.cos((t - tt_) * 30) if t > tt_ + 0.08 else d * (t - tt_) / 0.08
    return troll_dx(t)
for f in range(F(T_RUG - 2.0), F(T_RUNEND) + 2):
    t = (f - 1) / FPS; x = HC.x + rug_dx(t); RUG.location = (x, HC.y, 0.035 + (0.0 if t < T_RUG else min(0.9, (t - T_RUG) * 3.0))); key(RUG, 'location', f)
linear(RUG); vis(RUG, [(F(T_ERUPT + 0.9), F(T_RUNEND))])
bpy.ops.mesh.primitive_cylinder_add(radius=0.42, depth=5.4, vertices=20); roll = bpy.context.object; roll.data.materials.append(RUGM); roll.parent = TROLL['root']
k_ = UJ['troll']['height'] / 2.5; roll.scale = (k_,) * 3; roll.location = Vector((0.45, 0.1, 1.95)) * k_; roll.rotation_euler = (math.radians(80), 0, math.radians(8)); vis(roll, [(F(T_RUNEND) + 1, None)])
# the herd leaves the ground
def tumble(u, t, drift, up, dur, turns):
    r = u['root']; sc.frame_set(F(t)); p0 = r.location.copy(); rz = r.rotation_euler.z; n = int(dur * FPS)
    for i in range(n + 1):
        u_ = i / n; r.location = p0 + Vector((drift[0], drift[1], 0)) * u_ + Vector((0, 0, up * 4 * u_ * (1 - u_))); key(r, 'location', F(t) + i)
        r.rotation_euler = (turns * 2 * math.pi * sm(u_), 0, rz + 0.8 * u_ * (1 if turns > 0 else -1)); key(r, 'rotation_euler', F(t) + i)
    hold(u, 'die', F(t), 2.6 / (dur + 0.5), 1)
for j, u in enumerate(HERD):
    tumble(u, T_RUG + 0.04 * j, (-1.2 - 0.5 * (j % 3), (j % 2 - 0.5) * 1.6), 3.2 + 0.9 * (j % 4), 1.5 + 0.12 * (j % 3), (-1 if j % 3 else -2))
    dust(Vector((u['slot'][0] - 1.4, u['slot'][1], 0.3)), T_RUG + 1.6 + 0.04 * j, 0.9, 140 + j, 4)
# coins: they rain on the party, then go up with the rug
COINM = mat('coin', (1.0, 0.72, 0.18), 0.25, emit=(1.0, 0.6, 0.1), estr=0.5, metal=1.0); cn = random.Random(33)
bpy.ops.mesh.primitive_cylinder_add(radius=0.17, depth=0.035, vertices=14); coin0 = bpy.context.object; coin0.data.materials.append(COINM); COINS = []
for i in range(130):
    o = coin0.copy(); COL.objects.link(o); x = HC.x + cn.uniform(-RW / 2 + 0.5, RW / 2 - 1.5); y = HC.y + cn.uniform(-RD / 2 + 0.5, RD / 2 - 0.5)
    ts = T_ERUPT + 1.6 + cn.random() ** 1.3 * (T_RUG - 1.4 - T_ERUPT - 1.6); z0 = cn.uniform(14, 26); tf = math.sqrt(2 * z0 / 9.8); sx_, sy_ = cn.uniform(-3, 3), cn.uniform(-2, 2); w = (cn.uniform(-9, 9), cn.uniform(-9, 9), cn.uniform(-3, 3))
    for k in range(9):
        u_ = k / 8; tt_ = tf * u_; o.location = (x + sx_ * (1 - u_), y + sy_ * (1 - u_), 0.06 + z0 - 4.9 * tt_ * tt_); key(o, 'location', F(ts + tt_)); o.rotation_euler = tuple(w_ * (tf - tt_) for w_ in w); key(o, 'rotation_euler', F(ts + tt_))
    # a small bounce, then at rest on the rug
    o.location.z = 0.45; key(o, 'location', F(ts + tf + 0.14)); o.location.z = 0.06; key(o, 'location', F(ts + tf + 0.28)); key(o, 'location', F(T_RUG) + i % 4); key(o, 'rotation_euler', F(T_RUG) + i % 4)
    v = Vector((cn.uniform(-2.5, 6.5), cn.uniform(-4, 4), 0)); vz = cn.uniform(5, 12); tl_ = 2 * vz / 9.8; p0 = o.location.copy(); t0 = T_RUG + (i % 4) / FPS
    for k in range(1, 11):
        u_ = k / 10; tt_ = tl_ * u_; o.location = p0 + v * tt_ + Vector((0, 0, vz * tt_ - 4.9 * tt_ * tt_ - 0.03 * u_)); key(o, 'location', F(t0 + tt_)); o.rotation_euler = tuple(w_ * tt_ * 0.8 for w_ in w[:2]) + (w[2],); key(o, 'rotation_euler', F(t0 + tt_))
    o.rotation_euler = (0, 0, w[2]); key(o, 'rotation_euler', F(t0 + tl_) + 2); linear(o); vis(o, [(F(ts), None)]); COINS.append(o)
bpy.data.objects.remove(coin0)
# one more, for the Pepe: it comes a long way, and lands on his head
T_BONK = T_FALL + 4.4; o = COINS[0].copy(); COL.objects.link(o); o.animation_data_clear(); hp = PEPE_P + Vector((0.05, -0.02, 2.47)); o.scale = (1.5,) * 3
for k in range(13):
    u_ = k / 12; o.location = hp + Vector((14.0, 2.0, 0)) * (1 - u_) + Vector((0, 0, 7.0 * 4 * (1 - u_) * u_ * 0.5 + 9.0 * (1 - u_))); key(o, 'location', F(T_BONK - 1.2 * (1 - u_))); o.rotation_euler = (u_ * 14, u_ * 9, 0); key(o, 'rotation_euler', F(T_BONK - 1.2 * (1 - u_)))
for k in range(1, 9):
    tt_ = k * 0.09; o.location = hp + Vector((-1.6, -0.8, 0)) * tt_ + Vector((0, 0, 3.2 * tt_ - 4.9 * tt_ * tt_)); key(o, 'location', F(T_BONK + tt_)); o.rotation_euler = (14 + tt_ * 9, 9 + tt_ * 5, 0); key(o, 'rotation_euler', F(T_BONK + tt_))
linear(o); vis(o, [(F(T_BONK - 1.2), F(T_BONK + 0.72))])
# the candle lands: dust along its whole length, the ground jumps
for k in range(9):
    y = G.y - 3 - k * 3.2; explode(Vector((G.x + (k % 2 - 0.5) * 1.5, y, 0.4)), T_FALL + 0.01 * k, 2.6, FIRE if k % 3 == 0 else FIREG, 10, 200 + k, DUST, light=(1.0, 0.3, 0.1)); dust(Vector((G.x + (k % 2) * 3 - 1.5, y, 0.5)), T_FALL + 0.1, 2.6, 220 + k, 5)
shock((G.x, G.y - 15, 0.4), T_FALL, 40.0, mat('rshock', (1, 0.3, 0.2), 0.3, emit=(1.0, 0.25, 0.1), estr=30), 30, 0.05)
# dust still hanging in the air afterwards
for k in range(16): dust(Vector((G.x + cn.uniform(-3, 16), G.y - cn.uniform(4, 30), cn.uniform(0.5, 3.0))), T_FALL + 0.6 + 0.35 * k, 2.4, 300 + k, 3)

# ================================================================ dawn: a low sun in the north, warm mist
SUNROT = float(arg('--sunrot', '228')); SUNEL = float(arg('--sunel', '11'))
wnt = sc.world.node_tree; sk = wnt.nodes.new('ShaderNodeTexSky'); sk.sky_type = 'NISHITA'; sk.sun_elevation = math.radians(SUNEL); sk.sun_rotation = math.radians(180 - SUNROT)
sk.sun_disc = True; sk.sun_size = math.radians(2.2); sk.sun_intensity = 0.25; sk.air_density = 1.0; sk.dust_density = 3.0; sk.ozone_density = 1.0
wnt.links.new(sk.outputs[0], wnt.nodes['Background'].inputs['Color']); wnt.nodes['Background'].inputs['Strength'].default_value = float(arg('--sky', '0.3'))
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); COL.objects.link(sun); sun.data.energy = float(arg('--sun', '5.5')); sun.data.angle = math.radians(3); sun.data.color = (1.0, 0.62, 0.36)
sun.rotation_euler = (math.radians(90 - SUNEL), 0, math.radians(SUNROT))
def keylight(name, loc, target, e, size=4.0, col=(1.0, 0.95, 0.85)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = e; ld.size = size; ld.color = col; o = bpy.data.objects.new(name, ld); COL.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); o.visible_camera = False; return o
def on(lo, wins):
    e = lo.data.energy; lo.data.energy = 0; lo.data.keyframe_insert('energy', frame=0)
    for a, b_ in wins:
        lo.data.energy = 0; lo.data.keyframe_insert('energy', frame=F(a) - 1); lo.data.energy = e; lo.data.keyframe_insert('energy', frame=F(a)); lo.data.keyframe_insert('energy', frame=F(b_)); lo.data.energy = 0; lo.data.keyframe_insert('energy', frame=F(b_) + 1)
    for k in lo.data.animation_data.action.fcurves[0].keyframe_points: k.interpolation = 'CONSTANT'
on(keylight('pepe_fill', (PEPE_P.x - 7, PEPE_P.y - 9, 3.5), (PEPE_P.x, PEPE_P.y, 1.6), 2600, 6, (0.8, 0.88, 1.0)), [(5.6, 14.0), (49.3, T_END)])
on(keylight('herd_fill', (HC.x - 6, HC.y - 16, 5), (HC.x, HC.y, 1.2), 7000, 10, (0.8, 0.88, 1.0)), [(14.0, 24.0), (40.3, 49.2)]); on(keylight('duel_fill', (BX - 9, BY - 6, 4), (BX, BY, 2), 4000, 7, (0.8, 0.88, 1.0)), [(24.0, 31.5)])
sc.view_layers[0].use_pass_mist = True; sc.world.mist_settings.start = 12.0; sc.world.mist_settings.depth = float(arg('--mist', '340')); sc.world.mist_settings.falloff = 'QUADRATIC'
sc.use_nodes = True; ct = sc.node_tree; ct.nodes.clear(); rl = ct.nodes.new('CompositorNodeRLayers'); mxn = ct.nodes.new('CompositorNodeMixRGB'); cp = ct.nodes.new('CompositorNodeComposite')
mu = ct.nodes.new('CompositorNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = float(arg('--mistmax', '0.4')); ct.links.new(rl.outputs['Mist'], mu.inputs[0])
mxn.inputs[2].default_value = (1.0, 0.8, 0.62, 1); ct.links.new(mu.outputs[0], mxn.inputs[0]); ct.links.new(rl.outputs['Image'], mxn.inputs[1]); ct.links.new(mxn.outputs[0], cp.inputs[0])

# ================================================================ the edit
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); COL.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.dof.use_dof = True; cam.data.clip_end = 3000; cam.data.clip_start = 0.05
SHOTS = []; _t = [0.0]; CUES = []; LOWER = []; EV = {}
def SH(name, dur, a0, s, p0, p1, l0, l1, lens, fstop=2.8, shake=0.0, lens1=None, ec=0, roll=None, focus=None):
    SHOTS.append(dict(name=name, t0=round(_t[0], 4), t1=round(_t[0] + dur, 4), a0=a0, s0=s, s1=s, p0=list(p0), p1=list(p1), l0=list(l0), l1=list(l1), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake, ec=ec, roll=roll, focus=focus)); _t[0] += dur
def now(): return _t[0]
def say(i, t): CUES.append((i, round(t, 3), round(t + VO[i]['dur'], 3)))
def ft(a, k=-1): s = SHOTS[k]; return s['t0'] + (a - s['a0']) / s['s0']          # the film time of an animation time, in shot k
def D(i): return VO[i]['dur']
HEAD = PEPE_P + Vector((0, -0.05, 2.05))
# --- 1. dawn
SH('dawn wide', 2.7, 0.0, 1, (-31, -63, 9.5), (-25, -56, 6.5), (9, -14, 4.5), (9, -14, 4), 28, 8.0, 0.1); say('n1a', 0.6)
SH('dawn glide', 0.5 + D('n1b'), 3.0, 1, (-16.5, -40.5, 0.7), (-12.5, -36.5, 0.95), (5, -12, 5), (5, -12, 5), 35, 2.2, 0.12, focus=38); say('n1b', SHOTS[-1]['t0'] + 0.15)
# --- 2. the Pepe
SH('pepe profile', 0.5 + D('n2a'), 6.0, 1, (-31, -23.6, 1.5), (-29.6, -23.4, 1.6), HEAD, HEAD, 150, 2.8, 0.06); say('n2a', SHOTS[-1]['t0'] + 0.35); LOWER.append((SHOTS[-1]['t0'] + 0.8, 0, 'THE PEPE', 'Rana memetica  ·  Status: down bad'))
SH('pepe front', 0.35 + D('n2b'), 9.5, 1, (-7.2, -33.5, 1.15), (-7.6, -31.6, 1.3), HEAD + Vector((0, 0, -0.25)), HEAD + Vector((0, 0, -0.15)), 85, 2.0, 0.06); say('n2b', SHOTS[-1]['t0'] + 0.15); LOWER[-1] = LOWER[-1][:1] + (now() - 0.3,) + LOWER[-1][2:]
# --- 3. the herd
SH('herd graze', 0.4 + D('n3a'), T_PLIP - 4.5, 1, (26, -49, 1.5), (27.5, -48, 1.5), (HC.x, HC.y, 1.2), (HC.x, HC.y, 1.2), 75, 2.8, 0.06); say('n3a', SHOTS[-1]['t0'] + 0.2); LOWER.append((SHOTS[-1]['t0'] + 0.6, now() - 0.2, 'THE PAPER-HANDED HERD', 'Manus chartacea  ·  Diet: exit liquidity'))
SH('the dip', 0.5 + D('n3b'), T_PLIP - 0.45, 1, (TC.x + 1.0, TC.y - 7.2, 0.6), (TC.x + 0.9, TC.y - 6.9, 0.62), TC + Vector((0, 0, 0.75)), TC + Vector((0, 0, 0.75)), 85, 2.8, 0.05); say('n3b', SHOTS[-1]['t0'] + 0.55); EV['plip'] = ft(T_PLIP)
SH('stampede', 1.35 + D('n3c'), T_PLIP + 0.3, 1, (21, -37, 2.1), (22, -36.5, 2.0), (HC.x + 2, HC.y, 1.2), (HC.x + 26, HC.y + 2, 1.4), 28, 4.0, 0.35, ec=2); say('n3c', SHOTS[-1]['t0'] + 1.2); EV['stampede'] = ft(T_PLIP + 0.4)
# --- 4. the duel
SH('duel wide', 0.4 + D('n4a'), T_D0 - 0.4, 1, (-9, -22.5, 1.7), (-8, -21.5, 1.7), (BX, BY, 1.9), (BX, BY, 1.9), 50, 2.8, 0.08); say('n4a', SHOTS[-1]['t0'] + 0.2)
SH('duel close', 2.1, T_D0 + 1.9, 0.5, (BX - 7.0, BY - 1.6, 2.4), (BX - 6.4, BY - 1.2, 2.4), (BX, BY, 2.0), (BX, BY, 2.0), 40, 2.8, 0.15); say('n4b', SHOTS[-1]['t0'] + 0.15); EV['punches'] = [ft(T_D0 + 2.5), ft(T_D0 + 3.25)]
SH('double ko', D('n4b') - 2.1 + 0.8, T_KO - 0.7, 0.5, (-7.5, -16.0, 0.9), (-7.0, -16.0, 1.0), (BX, BY, 1.9), (BX, BY, 1.5), 40, 2.8, 0.2); EV['ko'] = ft(T_KO)
# --- 5. the god candle
d_ = 0.25 + D('n5a')
SH('rumble', d_, T_ERUPT - 0.25 - d_, 1, (G.x + 6.2, G.y - 7.0, 2.6), (G.x + 5.4, G.y - 6.2, 2.2), (G.x, G.y, 0.2), (G.x, G.y, 0.4), 28, 2.8, 0.5); say('n5a', SHOTS[-1]['t0'] + 0.15); EV['rumble'] = SHOTS[-1]['t0']
SH('eruption', 2.2, T_ERUPT - 0.25, 0.6, (G.x + 6.5, G.y - 9.0, 0.5), (G.x + 6.8, G.y - 9.5, 0.55), (G.x, G.y, 1.5), (G.x, G.y, 21), 15, 5.6, 0.9, ec=2); EV['erupt'] = ft(T_ERUPT); say('n5b', ft(T_ERUPT) + 0.7)
SH('valley', 1.9, T_ERUPT + 1.9, 1, (54, -66, 9), (48, -68, 13), (G.x + 4, G.y - 4, 12), (G.x + 4, G.y - 4, 12.5), 24, 5.6, 0.12); say('n5c', SHOTS[-1]['t0'] + 0.35)
SH('party', D('n5c') - 1.55 + 0.5, T_ERUPT + 4.6, 1, (HC.x - 2.0, HC.y + 7.2, 1.5), (HC.x - 0.6, HC.y + 7.0, 1.6), (HC.x + 0.8, HC.y - 0.5, 1.5), (HC.x + 0.8, HC.y - 0.5, 1.5), 40, 2.8, 0.12)
# --- 6. the rug
d_ = max(2.05, 0.55 + D('n6a'))
SH('tug', d_, T_RUG - 0.12 - d_, 1, (HC.x + 4.6, HC.y - 9.0, 0.95), (HC.x + 4.9, HC.y - 8.7, 0.9), (HC.x + 7.4, HC.y, 0.7), (HC.x + 7.6, HC.y, 0.8), 35, 2.8, 0.06); say('n6a', SHOTS[-1]['t0'] + 0.3); EV['tugs'] = [ft(T_RUG - 1.7), ft(T_RUG - 1.05)]
SH('the pull', 0.8 + D('n6b') + 0.25, T_RUG - 0.12, 0.3, (HC.x - 1.5, HC.y - 17.5, 1.2), (HC.x - 0.5, HC.y - 16.5, 1.4), (HC.x, HC.y, 2.6), (HC.x - 0.5, HC.y, 3.0), 28, 4.0, 0.15); EV['pull'] = ft(T_RUG); say('n6b', ft(T_RUG) + 0.4); EV['red'] = ft(T_RED)
d_ = 0.4 + D('n6c') + 1.25
SH('timber', d_, T_FALL - 0.8 * (d_ - 1.1), 0.8, (G.x + 15, G.y - 30, 0.6), (G.x + 15, G.y - 30, 0.6), (G.x, G.y - 4, 14), (G.x + 1, G.y - 20, 3), 18, 5.6, 0.35, ec=1); EV['fall'] = ft(T_FALL); say('n6c', SHOTS[-1]['t0'] + 0.35)
EV['chair'] = CUES[-1][2] + 0.2; EV['door'] = CUES[-1][2] + 1.15
# --- 7. afterwards
SH('aftermath', 2.0, T_AFT + 0.4, 1, (38.0, -20.6, 1.7), (38.6, -20.5, 1.75), (95, -19, 2.4), (97.5, -19, 2.4), 150, 4.0, 0.05, focus=57)
d_ = 0.4 + D('n7a') + 0.4 + D('n7b') + 0.45
SH('pepe again', d_, T_BONK - (0.4 + D('n7a') + 0.12), 1, (-31, -23.6, 1.5), (-29.2, -23.35, 1.6), HEAD, HEAD, 150, 2.8, 0.06); EV['bonk'] = ft(T_BONK)
say('n7a', SHOTS[-1]['t0'] + 0.4); say('n7b', CUES[-1][2] + 0.4); LOWER.append((SHOTS[-1]['t0'] + 0.9, now() - 0.3, 'THE PEPE', 'Rana memetica  ·  Status: down worse'))
T_CARD = now(); say('n8', T_CARD + 0.4); T_FILM = T_CARD + 0.4 + D('n8') + 0.7
for a, b_ in zip(CUES, CUES[1:]):
    if b_[1] < a[2] + 0.05: print('VO OVERLAP', a, b_)
N_3D = int(round(T_CARD * FPS)); print('3D ends at', round(T_CARD, 2), 's, frames', N_3D, '; film', round(T_FILM, 2), 's')
for s in SHOTS: print(f"  {s['name']:14s} {s['t0']:6.2f}-{s['t1']:6.2f}  frames {int(s['t0'] * FPS) + 1}-{int(round(s['t1'] * FPS))}  anim {s['a0']:.2f}-{s['a0'] + (s['t1'] - s['t0']) * s['s0']:.2f}")
json.dump(dict(fps=FPS, first=1, last=N_3D, t_card=T_CARD, t_film=T_FILM, shots=SHOTS, cues=CUES, lower=LOWER, ev=EV, subs={k: v['sub'] for k, v in VO.items()}), open(os.path.join(MYHERE, 'edl.json'), 'w'), indent=0)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=False)
print('SAVED', OUT)
