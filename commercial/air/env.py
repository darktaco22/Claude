"""DAWN PATROL: a real 3D night graveyard around the playfield (tombstones, dead trees, a mausoleum, iron fences, lanterns, hills, ground mist, wisps),
so the camera moves through depth instead of past a flat wallpaper. build_env() is called after the game's arena (ground, towers, bridges) exists."""
import bpy, math, random
from mathutils import Vector

PI = math.pi


def _mat(name, base, rough=0.85, metal=0.0, emit=None, bump=0.35, scale=5.0, tint2=None, alpha=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 9; nz.inputs['Roughness'].default_value = 0.6
    L(tc.outputs['Object'], nz.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeValToRGB'); e = cr.color_ramp.elements; e[0].color = (*base, 1); e[1].color = (*(tint2 or tuple(c * 0.55 for c in base)), 1); e[0].position = 0.35; e[1].position = 0.65
    L(nz.outputs['Fac'], cr.inputs[0]); L(cr.outputs['Color'], b.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; L(nz.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    if emit:
        L(cr.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    if alpha is not None:
        b.inputs['Alpha'].default_value = alpha
    return m


def _glow(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Emission Color'].default_value = (*col, 1); b.inputs['Emission Strength'].default_value = strength; b.inputs['Roughness'].default_value = 0.6
    return m


def _mist(name, col, strength, alpha):
    """A soft ground-mist sheet: emissive teal, opaque only where a big noise says so."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; L = nt.links.new
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    out = nt.nodes['Material Output']
    tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.1; nz.inputs['Detail'].default_value = 5; L(tc.outputs['Object'], nz.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.42; cr.color_ramp.elements[1].position = 0.72; L(nz.outputs['Fac'], cr.inputs[0])
    gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'; L(tc.outputs['Object'], gr.inputs['Vector'])
    ramp2 = nt.nodes.new('ShaderNodeValToRGB'); ramp2.color_ramp.elements[0].position = 0.0; ramp2.color_ramp.elements[0].color = (1, 1, 1, 1); ramp2.color_ramp.elements[1].position = 0.95; ramp2.color_ramp.elements[1].color = (0, 0, 0, 1); L(gr.outputs['Fac'], ramp2.inputs[0])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L(cr.outputs['Color'], mul.inputs[0]); L(ramp2.outputs['Color'], mul.inputs[1])
    sc = nt.nodes.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = alpha; L(mul.outputs[0], sc.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = strength
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); L(sc.outputs[0], mx.inputs[0]); L(tr.outputs[0], mx.inputs[1]); L(em.outputs[0], mx.inputs[2]); L(mx.outputs[0], out.inputs['Surface'])
    return m


def _prim(kind, loc, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, **kw):
    if kind == 'cube': bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    elif kind == 'cyl': bpy.ops.mesh.primitive_cylinder_add(vertices=kw.get('v', 14), radius=0.5, depth=1.0, location=loc)
    elif kind == 'cone': bpy.ops.mesh.primitive_cone_add(vertices=kw.get('v', 10), radius1=0.5, radius2=kw.get('r2', 0.12) * 0.5 * 2, depth=1.0, location=loc)
    elif kind == 'sphere': bpy.ops.mesh.primitive_uv_sphere_add(segments=kw.get('v', 18), ring_count=kw.get('rc', 10), radius=0.5, location=loc)
    elif kind == 'plane': bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    o = bpy.context.active_object; o.scale = scale; o.rotation_euler = rot
    if mat: o.data.materials.append(mat)
    if kind in ('sphere', 'cyl', 'cone'):
        for p in o.data.polygons: p.use_smooth = True
    return o


def _tomb(rng, x, y, M):
    s = rng.uniform(0.8, 1.35); rz = rng.uniform(-0.5, 0.5) + (PI if y > 0 else 0.0); lean = rng.uniform(-0.12, 0.12); kind = rng.choice(('arch', 'arch', 'slab', 'cross', 'obelisk'))
    root = bpy.data.objects.new('tomb', None); bpy.context.scene.collection.objects.link(root); root.location = (x, y, 0.0); root.rotation_euler = (lean, 0, rz); root.scale = (s, s, s)
    def add(o): o.parent = root; return o
    mat = M['stone'] if rng.random() < 0.7 else M['stone2']
    if kind == 'arch':
        add(_prim('cube', (0, 0, 0.55), (0.9, 0.22, 1.1), mat=mat)); add(_prim('cyl', (0, 0, 1.1), (0.9, 0.9, 0.22), (PI / 2, 0, 0), mat, v=20))
        add(_prim('cube', (0, 0.0, 0.04), (1.15, 0.5, 0.1), mat=M['stone2']))
    elif kind == 'slab':
        add(_prim('cube', (0, 0, 0.45), (0.8, 0.18, 0.9), mat=mat)); add(_prim('cube', (0, 0, 0.93), (0.9, 0.24, 0.1), mat=mat)); add(_prim('cube', (0, 0.4, 0.05), (1.0, 0.5, 0.1), mat=M['stone2']))
    elif kind == 'cross':
        add(_prim('cube', (0, 0, 0.7), (0.22, 0.2, 1.4), mat=mat)); add(_prim('cube', (0, 0, 1.0), (0.8, 0.2, 0.22), mat=mat)); add(_prim('cube', (0, 0, 0.06), (0.8, 0.6, 0.12), mat=M['stone2']))
    else:
        add(_prim('cone', (0, 0, 1.0), (0.45, 0.45, 2.0), mat=mat, v=4, r2=0.12)); add(_prim('cube', (0, 0, 0.1), (0.8, 0.8, 0.2), mat=M['stone2']))
    if rng.random() < 0.35: add(_prim('sphere', (0.2, 0.3, 0.12), (0.5, 0.35, 0.22), mat=M['moss'], v=10, rc=6))
    return root


def _tree(rng, x, y, M, big=1.0):
    h = rng.uniform(5.5, 8.5) * big; root = bpy.data.objects.new('tree', None); bpy.context.scene.collection.objects.link(root); root.location = (x, y, 0); root.rotation_euler = (0, 0, rng.uniform(0, 6.28))
    def add(o): o.parent = root; return o
    lean = rng.uniform(-0.18, 0.18); add(_prim('cone', (math.sin(lean) * h * 0.5, 0, h * 0.5), (0.95 * big, 0.95 * big, h), (0, lean, 0), M['bark'], v=12, r2=0.26))
    for i in range(rng.randint(6, 10)):                                                         # gnarled branches that fork once
        z0 = rng.uniform(0.45, 0.95) * h; a = rng.uniform(0, 6.28); sp = rng.uniform(0.7, 1.25); ln = rng.uniform(2.0, 4.6) * big
        bx, by = math.cos(a) * 0.15, math.sin(a) * 0.15; d = Vector((math.cos(a) * math.sin(sp), math.sin(a) * math.sin(sp), math.cos(sp)))
        mid = Vector((bx, by, z0)) + d * ln * 0.5; rot = d.to_track_quat('Z', 'Y').to_euler()
        add(_prim('cone', tuple(mid), (0.28 * big, 0.28 * big, ln), tuple(rot), M['bark'], v=7, r2=0.2))
        tip = Vector((bx, by, z0)) + d * ln; a2 = a + rng.uniform(-0.9, 0.9); sp2 = sp + rng.uniform(-0.2, 0.5); d2 = Vector((math.cos(a2) * math.sin(sp2), math.sin(a2) * math.sin(sp2), math.cos(sp2))); l2 = ln * rng.uniform(0.4, 0.7)
        add(_prim('cone', tuple(tip + d2 * l2 * 0.5), (0.14 * big, 0.14 * big, l2), tuple(d2.to_track_quat('Z', 'Y').to_euler()), M['bark'], v=6, r2=0.2))
    return root


def build_env(A=None, seed=11):
    rng = random.Random(seed); sc = bpy.context.scene
    M = dict(stone=_mat('e_stone', (0.34, 0.33, 0.40), 0.85, bump=0.5, scale=7, tint2=(0.17, 0.18, 0.24)), stone2=_mat('e_stone2', (0.22, 0.22, 0.28), 0.9, bump=0.6, scale=4, tint2=(0.1, 0.1, 0.14)),
             moss=_mat('e_moss', (0.1, 0.22, 0.12), 0.95, bump=0.8, scale=14, tint2=(0.04, 0.1, 0.06)), bark=_mat('e_bark', (0.07, 0.055, 0.07), 0.95, bump=1.0, scale=9, tint2=(0.02, 0.015, 0.03)),
             iron=_mat('e_iron', (0.04, 0.04, 0.05), 0.55, metal=0.8, bump=0.1, scale=3), hill=_mat('e_hill', (0.025, 0.035, 0.075), 0.95, emit=0.6, bump=0.2, scale=2, tint2=(0.02, 0.025, 0.06)),
             lamp=_glow('e_lamp', (1.0, 0.62, 0.25), 22.0), teal=_glow('e_teal', (0.25, 1.0, 0.85), 14.0), door=_glow('e_door', (0.25, 1.0, 0.8), 9.0),
             pump=_glow('e_pump', (1.0, 0.42, 0.08), 4.0), wood=_mat('e_wood', (0.16, 0.1, 0.08), 0.8, bump=0.6, scale=12), mist=_mist('e_mist', (0.28, 0.85, 0.8), 0.9, 0.55), cloud=_mist('e_cloud', (0.35, 0.4, 0.75), 0.25, 0.9))
    # 1. hills on the horizon, dark against the sky (the sky itself is the world: gradient, stars, moon)
    for i in range(34):
        a = rng.uniform(0, 2 * PI); r = rng.uniform(46, 70); w = rng.uniform(14, 30); hh = rng.uniform(2.5, 8.0)
        _prim('sphere', (math.cos(a) * r, 4 + math.sin(a) * r, -1.0), (w, w * rng.uniform(0.8, 1.3), hh * 2), mat=M['hill'], v=16, rc=8)
    for i in range(40):                                                                          # far dead trees on the hills: silhouettes
        a = rng.uniform(0, 2 * PI); r = rng.uniform(34, 58)
        t = _tree(rng, math.cos(a) * r, 4 + math.sin(a) * r, M, rng.uniform(1.3, 2.3)); t.location.z = rng.uniform(0.0, 1.5)
    # 2. tombstones: dense outside the playfield corridor, a few at its edges
    n = 0
    while n < 150:
        x = rng.uniform(-22, 20); y = rng.uniform(-30, 36)
        if -9.5 < x < 6.5 and -22 < y < 22: continue                                           # keep the fight clear
        if abs(y) < 3.0 and abs(x) < 14: continue                                              # and the river
        _tomb(rng, x, y, M); n += 1
    for i in range(14):                                                                          # a handful just inside the fence line, never in the lanes
        x = rng.choice((-9.1, 6.1)) + rng.uniform(-0.5, 0.5); y = rng.uniform(-20, 20)
        if abs(y) < 3: continue
        _tomb(rng, x, y, M)
    # 3. dead trees along both sides
    for i in range(22):
        side = rng.choice((-1, 1)); x = (-12.5 if side < 0 else 9.5) + side * rng.uniform(0, 7); y = rng.uniform(-24, 30)
        _tree(rng, x, y, M, rng.uniform(0.9, 1.35))
    # 4. the mausoleum behind their tower, and a smaller crypt behind ours
    def crypt(cx, cy, sc, flip):
        root = bpy.data.objects.new('crypt', None); sc_ = bpy.context.scene; sc_.collection.objects.link(root); root.location = (cx, cy, 0); root.scale = (sc, sc, sc); root.rotation_euler = (0, 0, PI if flip else 0)
        def add(o): o.parent = root; return o
        add(_prim('cube', (0, 0, 2.2), (9.0, 6.0, 4.4), mat=M['stone'])); add(_prim('cube', (0, 0, 0.3), (10.2, 7.2, 0.6), mat=M['stone2']))
        for sx in (-1, 1):
            add(_prim('cyl', (sx * 3.2, -3.1, 2.4), (0.9, 0.9, 4.8), mat=M['stone'], v=18)); add(_prim('cube', (sx * 3.2, -3.1, 4.95), (1.3, 1.3, 0.3), mat=M['stone2']))
        pr = _prim('cube', (0, -3.0, 5.6), (9.6, 0.5, 0.5), mat=M['stone2']); add(pr)
        roof = _prim('cone', (0, 0, 6.6), (10.8, 5.6, 4.0), (0, 0, PI / 4), M['stone2'], v=4, r2=0.001); add(roof); roof.scale = (7.6, 7.6, 3.6)
        add(_prim('cube', (0, -3.05, 1.7), (3.0, 0.3, 3.4), mat=M['door'])); add(_prim('cyl', (0, -3.05, 3.4), (3.0, 3.0, 0.3), (PI / 2, 0, 0), M['door'], v=22))
        for k in range(5): add(_prim('cube', (0, -2.7 - 0.28 * k, 0.12 + 0.12 * (4 - k)), (4.2 + 0.7 * k, 0.4, 0.25), mat=M['stone2']))
        return root
    crypt(-1.5, 33.0, 2.4, True); crypt(2.5, -36.0, 1.8, False)
    lg = bpy.data.lights.new('crypt_glow', 'POINT'); lg.energy = 9000; lg.color = (0.3, 1.0, 0.82); lg.shadow_soft_size = 2.0; lo = bpy.data.objects.new('crypt_glow', lg); sc.collection.objects.link(lo); lo.location = (-1.5, 22.0, 3.0)
    # 5. iron fences along the corridor, with stone posts and lanterns
    for side, x in ((-1, -9.7), (1, 6.9)):
        y = -30.0
        while y < 34.0:
            _prim('cyl', (x, y, 0.8), (0.07, 0.07, 1.6), mat=M['iron'], v=8); _prim('cone', (x, y, 1.7), (0.1, 0.1, 0.22), mat=M['iron'], v=6, r2=0.01)
            y += 0.55
        for rz in (0.35, 1.2): _prim('cube', (x, 2.0, rz), (0.06, 64.0, 0.06), mat=M['iron'])
        for k, yy in enumerate([-26, -18, -10, -2, 6, 14, 22, 30]):
            post = _prim('cube', (x, yy, 1.15), (0.55, 0.55, 2.3), mat=M['stone']); _prim('cube', (x, yy, 2.35), (0.75, 0.75, 0.16), mat=M['stone2']); _prim('sphere', (x, yy, 2.6), (0.5, 0.5, 0.5), mat=M['stone2'], v=12, rc=8)
            _prim('cube', (x, yy, 2.95), (0.28, 0.28, 0.5), mat=M['lamp'])
            _prim('cone', (x, yy, 3.35), (0.5, 0.5, 0.35), mat=M['iron'], v=4, r2=0.01)
            if k % 2 == 0:
                ll = bpy.data.lights.new(f'lamp{side}_{k}', 'POINT'); ll.energy = 900; ll.color = (1.0, 0.62, 0.28); ll.shadow_soft_size = 0.3
                lo = bpy.data.objects.new(f'lamp{side}_{k}', ll); sc.collection.objects.link(lo); lo.location = (x, yy, 2.9)
    # 6. pumpkins and candles scattered at the verges
    for i in range(18):
        x = rng.choice((-1, 1)) * rng.uniform(8.0, 14.0) + (-1.5 if True else 0); y = rng.uniform(-24, 28)
        if -8.5 < x < 6.0 and -22 < y < 22: continue
        s = rng.uniform(0.35, 0.7); _prim('sphere', (x, y, s * 0.4), (s * 1.2, s * 1.2, s), mat=M['pump'], v=14, rc=8)
    # 7. ground mist, thickest at the edges, teal under the moon
    for i in range(34):
        x = rng.uniform(-18, 18); y = rng.uniform(-30, 34); s = rng.uniform(9, 17); z = rng.uniform(0.12, 0.9)
        _prim('plane', (x, y, z), (s, s, 1), (0, 0, rng.uniform(0, 6.28)), M['mist'])
    for i in range(16):                                                                          # thin haze higher up between the camera and the far hills
        x = rng.uniform(-22, 22); y = rng.uniform(14, 48); s = rng.uniform(16, 28); z = rng.uniform(3.0, 9.0)
        _prim('plane', (x, y, z), (s, s, 1), (0, 0, rng.uniform(0, 6.28)), M['mist'])
    # 8. low clouds drifting across the moon (huge soft sheets, high up)
    for i in range(9):
        _prim('plane', (rng.uniform(-30, 30), rng.uniform(25, 70), rng.uniform(16, 30)), (rng.uniform(30, 50), rng.uniform(14, 22), 1), (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, 6.28)), M['cloud'])
    return M
