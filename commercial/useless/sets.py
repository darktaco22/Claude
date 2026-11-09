"""The two sets for NO UTILITY.
TUNNEL: the stone passage under our king tower where the cards wait, lit by lanterns, its gate opening onto a blaze of
arena light (placed at x = TX, far from the arena).
ARENA: the real Meme Royale "cold" arena: the game's own ground texture, aurora backdrop, Rig Towers, Battlestation and
bridges (assets/arena/*.glb), a frozen river, snowy pines (the game draws its own pines procedurally) and falling snow.
Axes: Z up. Our side is -Y, the enemy is +Y."""
import bpy, math, os, random
from mathutils import Vector
import game
from room import pbr, plane
from penthouse import flat, box

G = game.G
TX = 120.0                                  # the tunnel's x offset
TW, TL, TH = 4.4, 22.0, 4.2                # tunnel width, length (y -11..11), height
GATE_Y = 11.0
BRIDGE_X = 5.0
OUR_KING = Vector((0, -13.5, 0)); ENEMY_KING = Vector((0, 13.5, 0))
OUR_PRINC = [Vector((-BRIDGE_X, -9.0, 0)), Vector((BRIDGE_X, -9.0, 0))]
EN_PRINC = [Vector((-BRIDGE_X, 9.0, 0)), Vector((BRIDGE_X, 9.0, 0))]
OURS = (0.25, 0.85, 0.45); THEIRS = (1.0, 0.27, 0.38)


def img_mat(name, path, emit=0.0, repeat=1.0, normal=None, tint=(1, 1, 1), rough=0.8, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (repeat, repeat, 1)
    nt.links.new(tc.outputs['UV'], mp.inputs[0])
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path); nt.links.new(mp.outputs[0], t.inputs[0])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1
    nt.links.new(t.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (*tint, 1)
    nt.links.new(mx.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    if emit:
        nt.links.new(mx.outputs[2], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    if normal:
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(normal); n.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mp.outputs[0], n.inputs[0]); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.6
        nt.links.new(n.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    if alpha: nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    return m


def team(root_objs, rgb):
    """Recolour a placed tower's team parts (its own team_* meshes / team_glow material) for one side."""
    for o in root_objs:
        if o.type != 'MESH': continue
        for i, ms in enumerate(o.material_slots):
            if ms.material and ms.material.name.startswith('team_glow'):
                m = ms.material.copy(); b = m.node_tree.nodes.get('Principled BSDF')
                if b:
                    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Emission Color'].default_value = (*rgb, 1)
                    b.inputs['Emission Strength'].default_value = 1.5
                ms.material = m
        if o.name.startswith(('team_paint', 'team_cloth')):
            for ms in o.material_slots:
                if ms.material:
                    m = ms.material.copy(); b = m.node_tree.nodes.get('Principled BSDF')
                    if b:
                        # keep the texture, multiply by the team colour
                        nt = m.node_tree; src = b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].links else None
                        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
                        if src: nt.links.new(src, mx.inputs[6])
                        mx.inputs[7].default_value = (*rgb, 1); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
                    ms.material = m


# ---------------------------------------------------------------- the tunnel
def tunnel():
    T = {}
    floor = pbr('t_floor', 'cobblestone_floor_08', scale=1.0, tint=(0.75, 0.66, 0.56))
    wall = pbr('t_wall', 'castle_wall_slates', scale=1.0, tint=(0.62, 0.55, 0.48))
    y0, y1 = -TL / 2, GATE_Y
    plane('t_floor', (TW, y1 - y0 + 6), (TX, (y0 + y1) / 2 + 3, 0), (0, 0, 0), floor, uv_scale=0.4)
    for s in (-1, 1):
        plane('t_wall', (y1 - y0, TH), (TX + s * TW / 2, (y0 + y1) / 2, TH / 2), (math.pi / 2, 0, -s * math.pi / 2), wall, uv_scale=0.4)
    plane('t_ceil', (TW, y1 - y0), (TX, (y0 + y1) / 2, TH), (math.pi, 0, 0), wall, uv_scale=0.4)
    plane('t_back', (TW, TH), (TX, y0, TH / 2), (math.pi / 2, 0, 0), wall, uv_scale=0.4)
    # ceiling ribs (arches) every 3.6 m
    rib = flat('t_rib', (0.22, 0.17, 0.13), 0.7)
    for y in [y0 + 1.5 + 3.6 * i for i in range(6)]:
        box('t_rib', (TX - TW / 2, y - 0.18, TH - 0.35), (TX + TW / 2, y + 0.18, TH), rib)
        for s in (-1, 1): box('t_pillar', (TX + s * TW / 2 - 0.22 * (s > 0) - 0.0 * (s < 0), y - 0.2, 0), (TX + s * TW / 2 + 0.22 * (s < 0), y + 0.2, TH), rib)
    # the gate: a wall with an opening; beyond it, the blaze of the arena
    gw, gh = 3.0, 3.4
    for (a, b, c, d) in ((-TW / 2, -gw / 2, 0, TH), (gw / 2, TW / 2, 0, TH), (-gw / 2, gw / 2, gh, TH)):
        box('t_gatewall', (TX + a, GATE_Y - 0.4, c), (TX + b, GATE_Y, d), wall)
    port = flat('t_portcullis', (0.08, 0.07, 0.06), 0.5, 0.8)
    for i in range(7): box('t_bar', (TX - gw / 2 + 0.2 + i * 0.43 - 0.03, GATE_Y - 0.25, gh - 0.55), (TX - gw / 2 + 0.2 + i * 0.43 + 0.03, GATE_Y - 0.2, gh), port)
    box('t_barh', (TX - gw / 2, GATE_Y - 0.26, gh - 0.62), (TX + gw / 2, GATE_Y - 0.19, gh - 0.55), port)
    blaze = flat('t_blaze', (1, 0.9, 0.7), 1.0, emit=((1.0, 0.86, 0.62), 6.0))
    T['blaze'] = plane('t_outside', (14, 10), (TX, GATE_Y + 4.0, 4.0), (math.pi / 2, 0, math.pi), blaze)
    T['blaze_mat'] = blaze
    # lanterns on the walls (Poly Haven Lantern_01) with flickering lights
    import assets
    T['lanterns'] = []
    for i, y in enumerate((-8.0, -3.0, 2.0, 7.0)):
        for s in (-1, 1):
            r, _ = assets.load('Lantern_01'); r.location = (TX + s * (TW / 2 - 0.25), y, 2.3); r.scale = (1.3,) * 3
            L = bpy.data.objects.new(f'lan_{i}_{s}', bpy.data.lights.new(f'lan_{i}_{s}', 'POINT')); L.data.energy = 40
            L.data.color = (1.0, 0.62, 0.3); L.data.shadow_soft_size = 0.08; L.location = (TX + s * (TW / 2 - 0.3), y, 2.45)
            bpy.context.scene.collection.objects.link(L); T['lanterns'].append(L)
    # the light that chooses: a shaft from the gate, a visible beam cone, and a spot
    sp = bpy.data.objects.new('choose', bpy.data.lights.new('choose', 'SPOT')); sp.data.energy = 0; sp.data.color = (1.0, 0.86, 0.6)
    sp.data.spot_size = math.radians(24); sp.data.spot_blend = 0.6; sp.data.shadow_soft_size = 0.2
    bpy.context.scene.collection.objects.link(sp); T['choose'] = sp
    bm = beam_mat('beam'); T['beam_mat'] = bm
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.95, radius2=0.25, depth=TH, location=(TX, 0, TH / 2), end_fill_type='NOTHING')
    cone = bpy.context.active_object; cone.name = 'beam'; cone.data.materials.append(bm); cone.visible_shadow = False
    for p in cone.data.polygons: p.use_smooth = True
    T['beam'] = cone
    gl = bpy.data.objects.new('gate_sun', bpy.data.lights.new('gate_sun', 'AREA')); gl.data.shape = 'RECTANGLE'
    gl.data.size = gw; gl.data.size_y = gh; gl.data.energy = 900; gl.data.color = (1.0, 0.84, 0.6)
    gl.location = (TX, GATE_Y + 0.3, gh / 2 + 0.3); gl.rotation_euler = (math.radians(-90 + 8), 0, 0)
    bpy.context.scene.collection.objects.link(gl); T['gate_sun'] = gl
    T['dust'] = motes('dust', (TX - TW / 2, -9, 0.2), (TX + TW / 2, GATE_Y, TH - 0.2), 700, 0.0045, fall=0.0, drift=0.25,
                      mat=flat('dust_m', (1, 0.9, 0.7), 0.5, emit=((1.0, 0.85, 0.6), 0.5)))
    return T


def beam_mat(name):
    """A soft additive shaft: emission fading along the cone and towards its silhouette (facing ratio)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); add = nt.nodes.new('ShaderNodeAddShader')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.85, 0.6, 1)
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.0; nt.links.new(inv.outputs[0], pw.inputs[0])
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(sep.outputs['Z'], mul.inputs[1])
    st = nt.nodes.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; st.inputs[1].default_value = 0.0; st.name = 'strength'
    nt.links.new(mul.outputs[0], st.inputs[0]); nt.links.new(st.outputs[0], em.inputs['Strength'])
    nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1]); nt.links.new(add.outputs[0], out.inputs[0])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m


def motes(name, lo, hi, n, r, fall=0.0, mat=None, seed=3, drift=0.15):
    """Deterministic particles (geometry nodes, driven by scene time): points scattered in a box drift on noise and,
    with fall > 0, fall at that speed and wrap around (snow)."""
    me = bpy.data.meshes.new(name); rng = random.Random(seed)
    lo = Vector(lo); hi = Vector(hi); sz = hi - lo
    me.from_pydata([(rng.uniform(lo.x, hi.x), rng.uniform(lo.y, hi.y), rng.uniform(lo.z, hi.z)) for _ in range(n)], [], [])
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; Lk = ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    pos = N.new('GeometryNodeInputPosition'); tm = N.new('GeometryNodeInputSceneTime')
    # noise drift
    noi = N.new('ShaderNodeTexNoise'); noi.noise_dimensions = '4D'; noi.inputs['Scale'].default_value = 0.6
    Lk.new(pos.outputs[0], noi.inputs['Vector']); sc = N.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 0.08
    Lk.new(tm.outputs['Seconds'], sc.inputs[0]); Lk.new(sc.outputs[0], noi.inputs['W'])
    sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; Lk.new(noi.outputs['Color'], sub.inputs[0]); sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    amp = N.new('ShaderNodeVectorMath'); amp.operation = 'SCALE'; amp.inputs['Scale'].default_value = drift * 4
    Lk.new(sub.outputs[0], amp.inputs[0])
    p2 = N.new('ShaderNodeVectorMath'); p2.operation = 'ADD'; Lk.new(pos.outputs[0], p2.inputs[0]); Lk.new(amp.outputs[0], p2.inputs[1])
    if fall > 0:   # z' = lo.z + mod(z - lo.z - fall * t, size.z)
        sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(p2.outputs[0], sep.inputs[0])
        ft = N.new('ShaderNodeMath'); ft.operation = 'MULTIPLY'; ft.inputs[1].default_value = fall; Lk.new(tm.outputs['Seconds'], ft.inputs[0])
        a = N.new('ShaderNodeMath'); a.operation = 'SUBTRACT'; Lk.new(sep.outputs['Z'], a.inputs[0]); Lk.new(ft.outputs[0], a.inputs[1])
        a2 = N.new('ShaderNodeMath'); a2.operation = 'SUBTRACT'; a2.inputs[1].default_value = lo.z; Lk.new(a.outputs[0], a2.inputs[0])
        md = N.new('ShaderNodeMath'); md.operation = 'FLOORED_MODULO'; md.inputs[1].default_value = sz.z; Lk.new(a2.outputs[0], md.inputs[0])
        a3 = N.new('ShaderNodeMath'); a3.operation = 'ADD'; a3.inputs[1].default_value = lo.z; Lk.new(md.outputs[0], a3.inputs[0])
        cmb = N.new('ShaderNodeCombineXYZ'); Lk.new(sep.outputs['X'], cmb.inputs['X']); Lk.new(sep.outputs['Y'], cmb.inputs['Y']); Lk.new(a3.outputs[0], cmb.inputs['Z'])
        newp = cmb.outputs[0]
    else: newp = p2.outputs[0]
    setp = N.new('GeometryNodeSetPosition'); Lk.new(gi.outputs[0], setp.inputs['Geometry']); Lk.new(newp, setp.inputs['Position'])
    ico = N.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value = r; ico.inputs['Subdivisions'].default_value = 1
    inst = N.new('GeometryNodeInstanceOnPoints'); Lk.new(setp.outputs[0], inst.inputs['Points']); Lk.new(ico.outputs['Mesh'], inst.inputs['Instance'])
    rnd = N.new('FunctionNodeRandomValue'); rnd.inputs[2].default_value = 0.5; rnd.inputs[3].default_value = 1.4
    Lk.new(rnd.outputs[1], inst.inputs['Scale'])
    sm = N.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = mat; Lk.new(inst.outputs[0], sm.inputs['Geometry'])
    Lk.new(sm.outputs[0], go.inputs[0])
    md_ = o.modifiers.new('gn', 'NODES'); md_.node_group = ng
    o.visible_shadow = False
    return o


# ---------------------------------------------------------------- the arena
def pine(loc, s, rng, mats):
    g, snow = mats
    parts = []
    for i, (r, h, z) in enumerate(((1.1, 1.6, 0.5), (0.85, 1.4, 1.35), (0.55, 1.2, 2.1))):
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r * s, radius2=0.0, depth=h * s, location=(loc[0], loc[1], z * s + h * s / 2))
        c = bpy.context.active_object; c.data.materials.append(g); c.rotation_euler.z = rng.uniform(0, 6.28); parts.append(c)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r * s * 0.72, radius2=0.0, depth=h * s * 0.55, location=(loc[0], loc[1], z * s + h * s * 0.72 + 0.04 * s))
        c = bpy.context.active_object; c.data.materials.append(snow); c.rotation_euler.z = rng.uniform(0, 6.28); parts.append(c)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.14 * s, depth=0.6 * s, location=(loc[0], loc[1], 0.3 * s))
    c = bpy.context.active_object; c.data.materials.append(flat('trunk', (0.2, 0.12, 0.07), 0.8)); parts.append(c)
    return parts


def arena():
    A = {}
    gd = f'{G}/arenas/cold'
    ground = img_mat('a_ground', f'{gd}/ground.webp', repeat=1.0, normal=f'{gd}/ground_n.webp', tint=(0.92, 0.95, 1.0), rough=0.55)
    # ground: two banks either side of the river, generous run-off all round
    for s in (-1, 1):
        o = plane('a_ground', (60, 34), (0, s * (1.3 + 17), 0), (0, 0, 0), ground, uv_scale=0.09)
    water = flat('a_ice', (0.04, 0.22, 0.45), 0.08); b = water.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (0.1, 0.45, 0.9, 1); b.inputs['Emission Strength'].default_value = 0.25
    plane('a_river', (60, 2.6), (0, 0, -0.35), (0, 0, 0), water)
    bank = flat('a_bank', (0.42, 0.55, 0.78), 0.7)
    for s in (-1, 1): box('a_bankwall', (-30, s * 1.3 - 0.06, -0.36), (30, s * 1.3 + 0.06, 0.0), bank)
    # bridges
    for x in (-BRIDGE_X, BRIDGE_X):
        r, objs = game.place(f'{G}/arena/bridge.glb', (x, 0, 0.0), math.pi / 2, 1.0, name=f'bridge_{x}')
        team(objs, (0.55, 0.8, 1.0))
    # towers: ours (-Y) facing +Y, theirs facing -Y. Our left princess tower is a ruin.
    A['towers'] = {}
    def tower(kind, loc, rz, col, key):
        r, objs = game.place(f'{G}/arena/{kind}.glb', loc, rz, 1.2 * game.WORLD, name=key); team(objs, col); A['towers'][key] = (r, objs); return r
    tower('battlestation', OUR_KING, 0.0, OURS, 'our_king')
    tower('tower_rig_ruin', OUR_PRINC[0], 0.4, OURS, 'our_left_ruin')
    tower('tower_rig', OUR_PRINC[1], 0.0, OURS, 'our_right')
    tower('battlestation', ENEMY_KING, math.pi, THEIRS, 'en_king')
    for i, p in enumerate(EN_PRINC): tower('tower_rig_ruin', p, math.pi + 0.5 * (i - 0.5), THEIRS, f'en_{i}')
    # backdrop: the game's aurora painting on a cylinder all round
    bd = img_mat('a_backdrop', f'{gd}/backdrop.webp', emit=1.0, tint=(1, 1, 1), rough=1.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=46, depth=44, location=(0, 4, 14), end_fill_type='NOTHING')
    cyl = bpy.context.active_object; cyl.name = 'backdrop'; cyl.data.materials.append(bd); cyl.visible_shadow = False
    for p in cyl.data.polygons: p.use_smooth = True
    uv = cyl.data.uv_layers[0]
    for poly in cyl.data.polygons:
        for li in poly.loop_indices:
            v = cyl.data.vertices[cyl.data.loops[li].vertex_index].co
            ang = math.atan2(v.y, v.x); u = (ang / (2 * math.pi)) % 1.0 * 2.0      # the painting twice around
            uv.data[li].uv = (u, min(0.999, 0.1 + 1.25 * (v.z + 22) / 44))
    # fix the seam: polygons spanning the wrap get u + 2
    for poly in cyl.data.polygons:
        us = [uv.data[li].uv.x for li in poly.loop_indices]
        if max(us) - min(us) > 1.0:
            for li in poly.loop_indices:
                if uv.data[li].uv.x < 1.0: uv.data[li].uv.x += 2.0
    cyl.visible_diffuse = False; cyl.visible_glossy = True
    A['backdrop_mat'] = bd
    # snowy pines and snow piles outside the playfield
    rng = random.Random(23); mats = (flat('pine', (0.05, 0.25, 0.16), 0.8), flat('pine_snow', (0.93, 0.96, 1.0), 0.6))
    for _ in range(70):
        while True:
            x, y = rng.uniform(-26, 26), rng.uniform(-24, 30)
            if abs(x) > 10.5 or abs(y) > 19: break
        pine((x, y), rng.uniform(0.55, 1.0), rng, mats)
    sp = flat('snowpile', (0.92, 0.95, 1.0), 0.7)
    for _ in range(40):
        x, y = rng.uniform(-24, 24), rng.uniform(-22, 26)
        if abs(x) < 9.5 and abs(y) < 17: continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.0, location=(x, y, -0.3))
        o = bpy.context.active_object; o.scale = (rng.uniform(0.8, 2.0), rng.uniform(0.8, 1.8), rng.uniform(0.4, 0.8)); o.data.materials.append(sp)
    # falling snow over the whole field
    A['snow'] = motes('snow', (-16, -22, 0.0), (16, 18, 12), 9000, 0.016, fall=0.9, drift=0.35,
                      mat=flat('snow_m', (1, 1, 1), 0.5, emit=((0.85, 0.92, 1.0), 0.6)), seed=7)
    return A
