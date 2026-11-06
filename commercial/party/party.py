"""
MEME ROYALE: the house party. Every character from the game at a night pool party at a modern villa, one camera sweep
over the pool, the deck and through the house.

    blender -b --factory-startup -P party.py -- --models DIR --ph DIR [--w 1280 --h 720] [--frames 720]
        [--save party.blend] [--stills 1,200,400 OUTDIR] [--render OUTDIR] [--clean]

--clean leaves out the smoking, the bong and the table gag (a cut for store listings).
The characters are the game's own models; every move is in moves.py. Furniture and the night sky are Poly Haven (CC0).
"""
import bpy, math, os, random, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moves as M
import resource
def MEM(tag): print("MEM", tag, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024), "MB", flush=True)

argv = sys.argv[sys.argv.index("--") + 1:]
A = lambda k, d=None, t=str: t(argv[argv.index(k) + 1]) if k in argv else d
MODELS = os.path.abspath(A("--models")); PH = os.path.abspath(A("--ph"))
N = A("--frames", 900, int); FPS = 30
CLEAN = "--clean" in argv
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N
sc.render.fps = FPS

# ------------------------------------------------------------------------------------------------ materials
def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1,)
_M = {}
def mat(name, color, rough=0.5, metal=0.0, emit=0.0, alpha=1.0, emit_color=None, trans=0.0):
    if name in _M: return _M[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = srgb(emit_color or color); b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha; m.surface_render_method = "BLENDED"
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
    _M[name] = m; return m
def soft(name, color, alpha=0.35, emit=0.0):
    """Smoke and powder: opaque-ish in the middle, fading to nothing at the silhouette, so a sphere reads as a soft puff."""
    if name in _M: return _M[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N_ = nt.nodes
    b = N_["Principled BSDF"]; b.inputs["Base Color"].default_value = srgb(color); b.inputs["Roughness"].default_value = 1.0
    if emit: b.inputs["Emission Color"].default_value = srgb(color); b.inputs["Emission Strength"].default_value = emit
    lw = N_.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    inv = N_.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    pw = N_.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.5
    mu = N_.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = alpha
    tr = N_.new("ShaderNodeBsdfTransparent"); mx = N_.new("ShaderNodeMixShader"); out = N_["Material Output"]
    nt.links.new(lw.outputs["Facing"], inv.inputs[1]); nt.links.new(inv.outputs[0], pw.inputs[0]); nt.links.new(pw.outputs[0], mu.inputs[0])
    nt.links.new(mu.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(b.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"]); m.surface_render_method = "BLENDED"
    _M[name] = m; return m
def obj_mat(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o
def box(name, x0, x1, y0, y1, z0, z1, m, bevel=None):
    if bevel is None:   # every solid gets a small bevel so its edges catch the light
        bevel = 0.012 if min(x1 - x0, y1 - y0, z1 - z0) > 0.05 else 0.0
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object; o.name = name; o.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = 2
    return obj_mat(o, m)
def cyl(name, loc, r, d, m, rot=(0, 0, 0), v=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, location=loc, rotation=rot, vertices=v)
    o = bpy.context.active_object; o.name = name; o.data.shade_smooth(); return obj_mat(o, m)
def sphere(name, loc, r, m, seg=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.active_object; o.name = name; o.data.shade_smooth(); return obj_mat(o, m)
def light(name, kind, loc, energy, color="#FFFFFF", size=0.2, rot=(0, 0, 0), spot=None, shadow=False):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); sc.collection.objects.link(L)
    L.location = loc; L.rotation_euler = rot; L.data.energy = energy; L.data.color = srgb(color)[:3]
    L.data.use_shadow = shadow
    if kind in ("POINT", "SPOT"): L.data.shadow_soft_size = size
    if kind == "AREA": L.data.size = size
    if spot: L.data.spot_size = spot; L.data.spot_blend = 0.4
    return L
def import_gltf(path, loc, rot_z=0.0, scale=1.0):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(os.path.basename(path), None); sc.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, rot_z); root.scale = (scale,) * 3
    return root

# ------------------------------------------------------------------------------------------------ the night sky
world = bpy.data.worlds.new("night"); sc.world = world; world.use_nodes = True
wn = world.node_tree; env = wn.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(PH, "kloppenheim_02_puresky_2k.hdr"))
bg = wn.nodes["Background"]; bg.inputs["Strength"].default_value = 0.35
wn.links.new(env.outputs["Color"], bg.inputs["Color"])

moon = light("moon", "SUN", (0, 0, 20), 0.6, "#AFC4FF", rot=(math.radians(50), math.radians(-20), math.radians(30)), shadow=True)
# ------------------------------------------------------------------------------------------------ the villa
DECK = mat("deck", "#8E8478", rough=0.6)
LAWN = mat("lawn", "#1F3A1C", rough=0.9)
WALL = mat("wall", "#EDEBE6", rough=0.55)
DARK = mat("frame", "#1B1B1F", rough=0.4, metal=0.5)
WOOD = mat("wood", "#7A4E2D", rough=0.5)
GLASS = mat("glass", "#9FC6D8", rough=0.02, alpha=0.16)
FLOOR = mat("floor", "#6E6760", rough=0.25)
TILE = mat("tile", "#1AA7D6", rough=0.3, emit=0.6, emit_color="#38C8FF")
WATER = bpy.data.materials.new("water"); WATER.use_nodes = True
wnt = WATER.node_tree; wb = wnt.nodes["Principled BSDF"]
wb.inputs["Base Color"].default_value = srgb("#2EC5FF"); wb.inputs["Roughness"].default_value = 0.03
wb.inputs["Alpha"].default_value = 0.42; WATER.surface_render_method = "BLENDED"
wb.inputs["Emission Color"].default_value = srgb("#1E9BFF"); wb.inputs["Emission Strength"].default_value = 0.35
tc = wnt.nodes.new("ShaderNodeTexCoord"); mp = wnt.nodes.new("ShaderNodeMapping"); nz = wnt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 4
bump = wnt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
wnt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); wnt.links.new(mp.outputs[0], nz.inputs["Vector"])
wnt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); wnt.links.new(bump.outputs[0], wb.inputs["Normal"])
mp.inputs["Location"].default_value = (0, 0, 0); mp.inputs["Location"].keyframe_insert("default_value", frame=1)
mp.inputs["Location"].default_value = (1.2, 0.8, 2.0); mp.inputs["Location"].keyframe_insert("default_value", frame=N)

WZ = -0.12   # the water's surface
PX, PY = 6.0, 2.5
box("lawn", -40, 40, -40, 40, -0.32, -0.3, LAWN)
# the deck around the pool (four slabs leave the pool's hole)
box("deck_s", -12, 12, -9, -PY, -0.3, 0.0, DECK); box("deck_n", -12, 12, PY, 5.0, -0.3, 0.0, DECK)
box("deck_w", -12, -PX, -PY, PY, -0.3, 0.0, DECK); box("deck_e", PX, 12, -PY, PY, -0.3, 0.0, DECK)
# the pool: tiled walls and floor, coping, water
box("pool_floor", -PX, PX, -PY, PY, -1.6, -1.5, TILE)
for (a, b_, c_, d) in ((-PX, PX, -PY - 0.1, -PY), (-PX, PX, PY, PY + 0.1), (-PX - 0.1, -PX, -PY, PY), (PX, PX + 0.1, -PY, PY)):
    box("pool_wall", a, b_, c_, d, -1.6, 0.0, TILE)
COPING = mat("coping", "#F4F1EA", rough=0.4)
for (a, b_, c_, d) in ((-PX - 0.35, PX + 0.35, -PY - 0.35, -PY), (-PX - 0.35, PX + 0.35, PY, PY + 0.35), (-PX - 0.35, -PX, -PY, PY), (PX, PX + 0.35, -PY, PY)):
    box("coping", a, b_, c_, d, 0.0, 0.05, COPING, bevel=0.01)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, WZ)); water = bpy.context.active_object; water.name = "water"
water.scale = (2 * PX, 2 * PY, 1); bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.modifier_add(type="SUBSURF"); obj_mat(water, WATER)
for i in range(3):   # the pool's underwater lights
    x = -PX + 2 + i * (2 * PX - 4) / 2
    light(f"poolL{i}", "POINT", (x, -PY + 0.3, -0.9), 320, "#4FD8FF", 0.3)
    light(f"poolR{i}", "POINT", (x, PY - 0.3, -0.9), 320, "#4FD8FF", 0.3)

# the house: ground floor (glass front with the doors slid open), upper floor cantilevered over the deck, flat roofs
GY0, GY1 = 5.0, 13.0
box("gf_floor", -9.5, 9.5, GY0, GY1, -0.3, 0.02, FLOOR)
box("gf_back", -9.5, 9.5, GY1 - 0.3, GY1, 0, 3.4, mat("inwall", "#5A4A6A", rough=0.6))
box("gf_west", -9.5, -9.2, GY0, GY1, 0, 3.4, WALL); box("gf_east", 9.2, 9.5, GY0, GY1, 0, 3.4, WALL)
box("gf_ceiling", -9.5, 9.5, GY0 - 0.6, GY1, 3.4, 3.7, WALL)
for x0 in (-9.2, -6.2, -3.2, 2.6, 5.6):   # glass panes, the middle left open
    box("pane", x0, x0 + 2.9, GY0, GY0 + 0.04, 0.02, 3.4, GLASS)
for x in (-9.2, -6.2, -3.2, -0.3, 2.6, 5.6, 8.5, 9.2):
    box("mullion", x - 0.04, x + 0.04, GY0 - 0.02, GY0 + 0.06, 0.02, 3.4, DARK)
box("slats", -9.5, -6.5, GY1 - 0.32, GY1 - 0.3, 0.3, 3.2, WOOD)
# upper floor
box("uf", -6.5, 9.5, 6.5, GY1, 3.7, 6.9, WALL)
box("uf_glass", -6.3, 9.3, 6.48, 6.52, 3.8, 6.7, GLASS)
box("uf_roof", -7.2, 10.2, 5.6, 13.6, 6.9, 7.15, WALL)
box("balcony", -6.5, 9.5, 4.4, 6.5, 3.7, 3.85, WALL)
box("balc_glass", -6.5, 9.5, 4.4, 4.44, 3.85, 4.85, GLASS)
box("eave_led", -9.4, 9.4, GY0 - 0.55, GY0 - 0.5, 3.36, 3.39, mat("eave_led", "#FFC98A", emit=6.0))
# inside: warm ceiling light, a sofa and the coffee table, the kitchen island bar with stools, plants, pendant lamps
for (x, y) in ((-4.5, 9), (4.0, 9)):
    light(f"room{x}", "AREA", (x, y, 3.3), 260, "#FFC08A", 4.0, rot=(0, 0, 0))
# a rug, a TV glowing purple, and the game's logo, huge, on the back wall
box("rug", -7.6, -2.8, 7.4, 11.6, 0.02, 0.035, mat("rug", "#7A1E5A", rough=0.9))
box("tv", -6.6, -3.8, GY1 - 0.36, GY1 - 0.32, 1.0, 2.6, mat("tv", "#B44BFF", emit=3.0))
LOGO = os.path.join(os.path.dirname(MODELS), "logo.png")
if os.path.exists(LOGO):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.9, GY1 - 0.34, 2.15), rotation=(math.pi / 2, 0, 0))
    lg = bpy.context.active_object; lg.scale = (1.9 * 1024 / 971, 1.9, 1)
    lm = bpy.data.materials.new("logo"); lm.use_nodes = True; ln = lm.node_tree; ln.nodes.clear()
    lo = ln.nodes.new("ShaderNodeOutputMaterial"); le = ln.nodes.new("ShaderNodeEmission"); lt = ln.nodes.new("ShaderNodeTexImage")
    lt.image = bpy.data.images.load(LOGO); le.inputs["Strength"].default_value = 1.2
    tr = ln.nodes.new("ShaderNodeBsdfTransparent"); mx = ln.nodes.new("ShaderNodeMixShader")
    ln.links.new(lt.outputs["Color"], le.inputs["Color"]); ln.links.new(lt.outputs["Alpha"], mx.inputs[0])
    ln.links.new(tr.outputs[0], mx.inputs[1]); ln.links.new(le.outputs[0], mx.inputs[2]); ln.links.new(mx.outputs[0], lo.inputs[0])
    obj_mat(lg, lm)
import_gltf(os.path.join(PH, "sofa_03/sofa_03.gltf"), (-5.2, 10.6, 0.02), math.pi, 1.0)
import_gltf(os.path.join(PH, "modern_coffee_table_01/modern_coffee_table_01.gltf"), (-5.2, 8.9, 0.02), 0, 1.0)
box("island", 2.2, 6.4, 9.0, 10.0, 0.02, 1.0, mat("island", "#2A2A30", rough=0.3, metal=0.2), bevel=0.02)
box("island_top", 2.1, 6.5, 8.95, 10.05, 1.0, 1.06, mat("marble", "#F2EFEA", rough=0.15), bevel=0.01)
for i, x in enumerate((2.6, 3.6, 4.6, 5.6)):
    import_gltf(os.path.join(PH, "bar_chair_round_01/bar_chair_round_01.gltf"), (x, 8.45, 0.02), 0, 1.0)
for i, (x, y, col) in enumerate(((2.3, 9.15, "#3B7A2E"), (2.3, 9.4, "#8A2A1E"), (2.3, 9.65, "#C8A93A"), (2.3, 9.9, "#3A5A8A"), (6.0, 9.6, "#6A2A6A"), (6.2, 9.6, "#2A6A5A"))):
    cyl(f"bottle{i}", (x, y, 1.22), 0.045, 0.32, mat(f"btl{i}", col, rough=0.05, alpha=0.7, emit=0.3))   # lined up at the ends, not in front of the snorters
for (x, y, n) in ((-8.6, 12.0, "potted_plant_01"), (8.4, 12.0, "potted_plant_02"), (-8.4, 5.6, "potted_plant_02"), (8.6, 5.6, "potted_plant_01")):
    import_gltf(os.path.join(PH, f"{n}/{n}.gltf"), (x, y, 0.02), 0, 1.4)
for x in (2.8, 4.3, 5.8):
    import_gltf(os.path.join(PH, "modern_ceiling_lamp_01/modern_ceiling_lamp_01.gltf"), (x, 9.5, 2.3), 0, 1.0)

# palms: a leaning trunk of rings and a crown of drooping fronds
TRUNK = mat("trunk", "#6B5038", rough=0.9); FROND = mat("frond", "#3A7A2E", rough=0.55)
FROND.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.0
import bmesh
_FROND_MESH = None
def frond_mesh():
    """One palm frond: a curving rachis with ~36 pairs of tapering leaflets drooping from it (shared by every palm)."""
    global _FROND_MESH
    if _FROND_MESH: return _FROND_MESH
    bm = bmesh.new(); L = 2.8; n = 36
    def spine(t):   # along x, arching up then down
        return Vector((L * t, 0, 0.55 * t - 1.25 * t * t))
    for i in range(n):
        t = 0.08 + 0.9 * i / n; p = spine(t); p2 = spine(t + 0.02)
        tang = (p2 - p).normalized()
        length = 0.62 * math.sin(math.pi * min(1.0, t * 1.15)) + 0.08
        for side in (-1, 1):
            out = Vector((0, side, 0)).lerp(Vector((0, side * 0.7, -0.7)), 0.5).normalized()
            tip = p + out * length + tang * 0.12
            w = 0.035 + 0.02 * (1 - t)
            v1 = bm.verts.new(p - tang * w); v2 = bm.verts.new(p + tang * w)
            v3 = bm.verts.new(tip + tang * 0.01); v4 = bm.verts.new(p + out * length * 0.5 + tang * w * 1.6)
            bm.faces.new((v1, v4, v3)); bm.faces.new((v4, v2, v3))
    for i in range(12):   # the rachis itself, a thin ribbon
        t0, t1 = i / 12, (i + 1) / 12
        a0, a1 = spine(t0), spine(t1); w0, w1 = 0.03 * (1 - t0) + 0.008, 0.03 * (1 - t1) + 0.008
        vs = [bm.verts.new(a0 + Vector((0, -w0, 0))), bm.verts.new(a0 + Vector((0, w0, 0))), bm.verts.new(a1 + Vector((0, w1, 0))), bm.verts.new(a1 + Vector((0, -w1, 0)))]
        bm.faces.new(vs)
    me = bpy.data.meshes.new("frond"); bm.to_mesh(me); bm.free()
    me.materials.append(FROND); _FROND_MESH = me
    return me
def palm(x, y, h=6.0, lean=(0.4, 0.2)):
    """A palm: one continuous tapering, curving trunk with growth rings, a crown of fronds and a few coconuts."""
    top = Vector((x + lean[0], y + lean[1], h))
    curve = bpy.data.curves.new("palm_trunk", "CURVE"); curve.dimensions = "3D"
    sp = curve.splines.new("BEZIER"); sp.bezier_points.add(2)
    pts = [Vector((x, y, -0.3)), Vector((x + lean[0] * 0.25, y + lean[1] * 0.25, h * 0.5)), top]
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    for bp, r in zip(sp.bezier_points, (1.0, 0.8, 0.6)): bp.radius = r
    curve.bevel_depth = 0.2; curve.bevel_resolution = 4; curve.resolution_u = 24; curve.use_fill_caps = True
    o = bpy.data.objects.new("palm_trunk", curve); sc.collection.objects.link(o); o.data.materials.append(TRUNK)
    me = frond_mesh()
    for j in range(14):
        a = j / 14 * math.tau + random.uniform(-0.1, 0.1)
        f = bpy.data.objects.new("frond", me); sc.collection.objects.link(f)
        f.location = top; f.rotation_euler = (random.uniform(-0.15, 0.15), math.radians(random.uniform(-25, 10) - (25 if j % 2 else 0)), a)
        s_ = random.uniform(0.85, 1.15); f.scale = (s_, s_, s_)
    for k in range(4):
        sphere("coconut", top + Vector((math.cos(k * 1.6) * 0.18, math.sin(k * 1.6) * 0.18, -0.25)), 0.11, mat("coconut", "#5A3B1E", rough=0.7), seg=10)
for (x, y, l) in ((-11, 3.5, (0.6, -0.3)), (-10.5, -6.5, (0.5, 0.4)), (11, 3.8, (-0.6, -0.2)), (11.2, -6.0, (-0.5, 0.3)), (-12.5, -1.5, (0.3, 0.1)), (12.6, -1.2, (-0.3, 0.1))):
    palm(x, y, 6.2 + random.uniform(-0.6, 0.8), l)

# loungers and umbrellas on the south deck, string lights over it, a DJ booth, coloured party spots
for i, x in enumerate((-8.0, -6.9)):   # inside the walkers' lap, off their path
    box("lounger", x - 0.35, x + 0.35, -6.4, -4.5, 0.0, 0.35, mat("lounger", "#F7F7F2", rough=0.5), bevel=0.04)
BULB = mat("bulb", "#FFD58A", emit=8.0)
for row, y in enumerate((-3.5, -7.5)):
    for i in range(24):
        x = -10 + i * (20 / 23); sag = 0.55 * math.sin(math.pi * i / 23)
        sphere("bulb", (x, y, 3.2 - sag), 0.05, BULB, seg=8)
    for x in (-10, 12.3):   # the east pole stands clear of the bong session
        cyl("pole", (x, y, 1.6), 0.04, 3.2, DARK, v=8)
    light(f"string{row}", "AREA", (0, y, 2.8), 500, "#FFC27A", 6.0, rot=(0, 0, 0))
box("dj_booth", 6.85, 7.35, -6.0, -3.6, 0.0, 1.05, mat("booth", "#111115", rough=0.3, metal=0.3), bevel=0.03)
box("dj_led", 6.83, 6.85, -5.9, -3.7, 0.15, 0.95, mat("led", "#FF2BD6", emit=6.0))
for y in (-6.4, -3.2):
    box("speaker", 7.3, 8.1, y - 0.35, y + 0.35, 0.0, 1.6, mat("spk", "#18181C", rough=0.5), bevel=0.03)
    cyl("cone", (7.28, y, 1.05), 0.22, 0.04, mat("cone", "#333338", rough=0.3), rot=(0, math.pi / 2, 0))
for i, (x, col) in enumerate(((-2, "#FF2BD6"), (2, "#2BE0FF"), (5, "#FFE02B"), (-6, "#8A2BFF"))):
    sp = light(f"party{i}", "SPOT", (x, -9.5, 5.5), 2200, col, 0.2, spot=math.radians(28), shadow=(i < 2))
    for f in range(1, N + 1, 30):
        sp.rotation_euler = (math.radians(45 + 12 * math.sin(f / 23 + i)), math.radians(18 * math.sin(f / 31 + i * 2)), 0)
        sp.keyframe_insert("rotation_euler", frame=f)
# floats in the pool (glossy vinyl, from flamingo.py)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flamingo.py")).read().split("if __name__")[0], globals())
bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.2, major_segments=72, minor_segments=28, location=(4.8, 1.4, WZ + 0.08))
donut = obj_mat(bpy.context.active_object, _vinyl("donut_vinyl", "#FF6FB5")); donut.data.shade_smooth()
bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.22, major_segments=72, minor_segments=28, location=(-4.2, -1.2, WZ + 0.08))
_rg = obj_mat(bpy.context.active_object, _vinyl("ring_vinyl", "#FFD23A")); _rg.data.shade_smooth()
# the flamingo: a proper inflatable (flamingo.py), bobbing and turning slowly
FLAMINGO = build_flamingo((-1.8, 1.6, WZ + 0.08))
for f in range(1, N + 1, 24):
    FLAMINGO.location.z = WZ + 0.08 + 0.025 * math.sin(f / 10); FLAMINGO.rotation_euler = (0.03 * math.sin(f / 13), 0.04 * math.sin(f / 9), 0.15 * math.sin(f / 70))
    FLAMINGO.keyframe_insert("location", frame=f); FLAMINGO.keyframe_insert("rotation_euler", frame=f)

# ------------------------------------------------------------------------------------------------ architecture, the kitchen, the mess
CUP = mat("cup", "#D8232A", rough=0.35)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dressing.py")).read(), globals())
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "environment.py")).read(), globals())
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "coins.py")).read(), globals())
MEM("env")

# ------------------------------------------------------------------------------------------------ the guests
CUP = mat("cup", "#D8232A", rough=0.35); CIG = mat("cig", "#F5F2EA", rough=0.6); EMBER = mat("ember", "#FF6A1A", emit=12.0)
SMOKE = soft("smoke", "#E8E8EE", alpha=0.45)
NOTE = mat("note", "#7DBF6A", rough=0.6); POWDER = mat("powder", "#FFFFFF", rough=0.8, emit=0.3)

def recolor(rig, hue=0.5, sat=1.0, val=1.0, tint=None):
    """New memes from the game's own models: shift the hue, saturation and brightness of a character's textures."""
    for o in rig.children:
        if o.type != "MESH": continue
        for sl in o.material_slots:
            m = sl.material
            if not m or not m.use_nodes: continue
            nt = m.node_tree; b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if not b or not b.inputs["Base Color"].links: continue
            src = b.inputs["Base Color"].links[0].from_socket
            hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Hue"].default_value = hue
            hs.inputs["Saturation"].default_value = sat; hs.inputs["Value"].default_value = val
            nt.links.new(src, hs.inputs["Color"]); out = hs.outputs["Color"]
            if tint:
                mx = nt.nodes.new("ShaderNodeMixRGB"); mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
                mx.inputs[2].default_value = srgb(tint); nt.links.new(out, mx.inputs[1]); out = mx.outputs[0]
            nt.links.new(out, b.inputs["Base Color"])

def load(cid, model=None, look=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, (model or cid) + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    keep = [o for o in new if not (o.type == "MESH" and o.parent is None)]
    for o in new:
        if o.type == "MESH" and o.parent is None: bpy.data.objects.remove(o)   # the game's selection sphere
    for o in keep:
        if o.type == "MESH" and "--nosubd" not in argv:
            sd = o.modifiers.new("smooth", "SUBSURF"); sd.levels = 0; sd.render_levels = 1; sd.uv_smooth = "PRESERVE_BOUNDARIES"; sd.quality = 1; sd.use_limit_surface = False; sd.use_creases = False
    if look: recolor(rig, **look)
    return M.Char(rig, cid)

def face(dx, dy):   # the ctrl's z rotation so the character faces (dx, dy)
    return math.atan2(dx, -dy)

def to_local(c, p):
    """A world point into the character's space (its controller is placed before this is called)."""
    loc, rot = c.ctrl.location, c.ctrl.rotation_euler.z
    d = Vector(p) - loc
    ca, sa = math.cos(-rot), math.sin(-rot)
    return Vector((ca * d.x - sa * d.y, sa * d.x + ca * d.y, d.z))

def attach(c, obj, bone="RightHand", offset=(0, 0.08, 0.03), rot=(0, 0, 0)):
    if bone.endswith("Hand") and "mixamorig:" + bone not in c.rig.data.bones:   # no hand bone: carry it at the wrist
        fa = c.rig.data.bones.get("mixamorig:" + bone.replace("Hand", "ForeArm"))
        if fa: bone = fa.name.split(":")[-1]; offset = (offset[0], offset[1] + fa.length, offset[2])
    if "mixamorig:" + bone not in c.rig.data.bones:
        bpy.data.objects.remove(obj); return None
    cn = obj.constraints.new("CHILD_OF"); cn.target = c.rig; cn.subtarget = "mixamorig:" + bone
    cn.set_inverse_pending = False; cn.inverse_matrix.identity()   # new Child Of constraints auto-set an inverse: that threw every prop metres off its bone
    obj.location = offset; obj.rotation_euler = rot
    return obj

def place(c, x, y, rot, z=0.0):
    c.ctrl.location = (x, y, z); c.ctrl.rotation_euler = (0, 0, rot)

def puff_loop(c, period, phase, mouth_local, start=1):
    """Smoke rising from the mouth after each drag."""
    t0 = ((1 - phase) % 1.0) * period + 0.35 * period
    t = t0
    while t * FPS < N:
        f = int(t * FPS) + start
        s = sphere("puff", (0, 0, 0), 0.08, SMOKE, seg=20); s.parent = c.ctrl
        s.location = mouth_local; s.scale = (0.01,) * 3; s.keyframe_insert("location", frame=max(1, f - 1)); s.keyframe_insert("scale", frame=max(1, f - 1))
        s.scale = (1, 1, 1); s.keyframe_insert("scale", frame=f + 4)
        s.location = mouth_local + Vector((random.uniform(-0.1, 0.1), -0.25, 0.7)); s.scale = (3, 3, 3)
        s.keyframe_insert("location", frame=f + 50); s.keyframe_insert("scale", frame=f + 46)
        s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=f + 54)
        t += period

guests = {}
def guest(cid, x, y, rot, move, z=0.0, **kw):
    c = load(cid); place(c, x, y, rot, z); guests[cid] = c
    c.bake(move, 1, N, step=2, **kw); return c

look_at = lambda c, other: to_local(c, Vector(other.ctrl.location) + Vector((0, 0, other.headp.z)))

def bone_geom(c, bone="Head", thresh=0.35):
    """The real extent of the mesh a bone carries, in that bone's own space (x side, y up the bone, z forward): the
    centre and half-sizes of the vertices weighted to it (and its end/eye children), measured in the rest pose."""
    bpy.context.view_layer.update()
    inv = (c.rig.matrix_world @ c.rig.data.bones["mixamorig:" + bone].matrix_local).inverted()
    names = {"mixamorig:" + bone} | ({"mixamorig:HeadTop_End", "mixamorig:LeftEye", "mixamorig:RightEye"} if bone == "Head" else set())
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3); n = 0
    for o in c.rig.children:
        if o.type != "MESH": continue
        idx = {g.index for g in o.vertex_groups if g.name in names}
        if not idx: continue
        mw = o.matrix_world
        for v in o.data.vertices:
            if any(g.group in idx and g.weight > thresh for g in v.groups):
                p = inv @ (mw @ v.co); n += 1
                lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    if n < 10: return None
    return (lo + hi) / 2, (hi - lo) / 2

def party_girl(c, hair, dress, bow=None):
    """Long hair (a cap over the top and back of the head and a fall down the back, leaving the face clear), a dress
    (a flared skirt on the hips, a bodice on the chest) and an optional bow, all sized from the character's own mesh."""
    HAIR = mat("hair_" + hair, hair, rough=0.45); retex(HAIR, hair, hair, kind="noise", scale=60.0, rough=0.45, bump=0.4)
    DRESS = mat("dress_" + dress, dress, rough=0.3, metal=0.25)
    hg = bone_geom(c, "Head")
    if hg:
        C, h = hg
        cap = sphere("hair_cap", (0, 0, 0), 1.0, HAIR, seg=32); cap.scale = (h.x * 1.1, h.y * 0.98, h.z * 0.82)
        attach(c, cap, bone="Head", offset=tuple(C + Vector((0, 0.2 * h.y, -0.34 * h.z))))
        fall = sphere("hair_fall", (0, 0, 0), 1.0, HAIR, seg=32); fall.scale = (h.x * 1.02, h.y * 1.25, h.z * 0.42)
        attach(c, fall, bone="Head", offset=tuple(C + Vector((0, -0.85 * h.y, -0.62 * h.z))))
        if bow:
            BOW = mat("bow_" + bow, bow, rough=0.35)
            for sx in (-1, 1):
                bpy.ops.mesh.primitive_cone_add(radius1=h.x * 0.28, radius2=0.0, depth=h.x * 0.5, vertices=16)
                b_ = obj_mat(bpy.context.active_object, BOW); b_.data.shade_smooth()
                attach(c, b_, bone="Head", offset=tuple(C + Vector((sx * h.x * 0.3, 1.12 * h.y, -0.1 * h.z))), rot=(0, sx * math.pi / 2, 0))
            attach(c, sphere("bow_knot", (0, 0, 0), h.x * 0.09, BOW, seg=12), bone="Head", offset=tuple(C + Vector((0, 1.12 * h.y, -0.1 * h.z))))
    hp = bone_geom(c, "Hips")
    if hp:
        C, h = hp; r = max(h.x, h.z) * 1.08; d = max(0.15, c.leg * 0.5)
        bpy.ops.mesh.primitive_cone_add(radius1=r * 1.5, radius2=r, depth=d, vertices=40, end_fill_type="NOTHING")
        sk = obj_mat(bpy.context.active_object, DRESS); sk.data.shade_smooth()
        sk.modifiers.new("solid", "SOLIDIFY").thickness = 0.012
        attach(c, sk, bone="Hips", offset=tuple(C + Vector((0, h.y * 0.5 - d / 2, 0))), rot=(-math.pi / 2, 0, 0))
    sp = bone_geom(c, "Spine1")
    if sp:
        C, h = sp; r = max(h.x, h.z) * 1.06
        bo = cyl("bodice", (0, 0, 0), 1.0, 1.0, DRESS, v=40); bo.scale = (max(h.x, 0.05) * 1.08, max(h.z, 0.05) * 1.1, max(0.12, h.y * 2.0))
        attach(c, bo, bone="Spine1", offset=tuple(C), rot=(-math.pi / 2, 0, 0))

def beanie(c):
    """dogwifhat's pink knitted beanie, sized and seated from the head's real mesh (bone_geom)."""
    KNIT = mat("knit", "#FF5FA8", rough=0.95)
    retex(KNIT, "#FF5FA8", "#E0408A", kind="noise", scale=120.0, rough=0.95, bump=0.6)
    hg = bone_geom(c, "Head")
    if not hg: print("BEANIE: no head mesh"); return
    C, h = hg; top = C + Vector((0, h.y * 0.55, -0.05 * h.z))
    cap = sphere("beanie", (0, 0, 0), 1.0, KNIT, seg=32); cap.scale = (h.x * 0.95, h.y * 0.62, h.z * 0.92)
    attach(c, cap, bone="Head", offset=tuple(top))
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.12, major_segments=48, minor_segments=12)
    band = obj_mat(bpy.context.active_object, KNIT); band.data.shade_smooth(); band.scale = (h.x * 0.93, h.z * 0.9, h.y * 0.9)
    attach(c, band, bone="Head", offset=tuple(top - Vector((0, h.y * 0.08, 0))), rot=(math.pi / 2, 0, 0))
    attach(c, sphere("pompom", (0, 0, 0), max(h.x, h.z) * 0.22, KNIT, seg=16), bone="Head", offset=tuple(top + Vector((0, h.y * 0.62, 0))))
    print(f"BEANIE {c.name}: head half-size {tuple(round(v, 3) for v in h)}")

# motion capture (CMU, cgspeed's BVH) for the dancers, drinkers, smokers, the laugh and the drunk; retarget.py
import retarget as RT
CMU = os.path.abspath(A("--cmu"))
USED = ["113_04", "111_05", "60_01", "18_15", "93_08", "90_32", "120_21", "85_14", "90_30", "55_02", "79_33", "80_29", "13_09", "13_14", "91_09", "141_12", "120_05"]
CLIPS = {c: RT.sample(os.path.join(CMU, "data", f"{int(c.split('_')[0]):03d}", c + ".bvh")) for c in USED}
MEM("clips")
def mocap(cid, x, y, rot, cname, start=0.0, travel=0.12, speed=1.0, z=0.0, model=None, look=None):
    c = load(cid, model, look); place(c, x, y, rot, z); guests[cid] = c
    if c.ik: RT.apply(c, CLIPS[cname], 1, N, start=start, travel=travel, speed=speed)
    else: c.play("win", 1)
    return c

# the DJ, and the dance floor in front of the booth
mocap("triplet", 7.8, -4.8, face(-1, 0), "111_05", start=3.0, travel=0.0)   # the DJ
dancers = ["giga", "neet", "alon", "mitch", "mensa", "thisisfine", "baton", "goat", "brett", "slerf", "bome", "npcwojak"]   # BOME (a big book) off the camera line to the DJ
spots = [(1.2, -4.4), (2.6, -4.6), (4.0, -4.35), (5.3, -4.6), (1.6, -5.6), (3.1, -6.0), (4.6, -5.5), (2.2, -7.1), (3.8, -7.3), (5.4, -6.8), (6.7, -8.3), (6.3, -5.7)]   # BOME (a big book) at the back, out of the camera's corridor (it filled the frame)
# new memes made from the game's own models
LOOKS = {"brett": ("pepe", {"hue": 0.78, "sat": 1.15, "val": 1.0}),                    # Brett: the blue frog
         "npcwojak": ("wojak", {"hue": 0.5, "sat": 0.0, "val": 0.95, "tint": "#C9CCD2"}),  # NPC Wojak: grey, blank
         "pinkwojak": ("wojak", {"hue": 0.5, "sat": 0.4, "val": 1.05, "tint": "#FF8FB0"}), # Pink Wojak: the panic seller
         "doge": ("bonk", {"hue": 0.48, "sat": 0.55, "val": 1.2, "tint": "#F2D9A8"}),       # DOGE: the original Shiba
         "wif": ("bonk", {"hue": 0.49, "sat": 0.65, "val": 1.1, "tint": "#E8C9A0"}),        # dogwifhat
         "fwog": ("pepe", {"hue": 0.47, "sat": 0.8, "val": 1.25, "tint": "#D8FFC8"})}       # Fwog: a small pale frog
DANCE_CLIP = {"giga": ("60_01", 2.0), "neet": ("18_15", 1.0), "alon": ("93_08", 0.5), "mitch": ("90_32", 0.5), "thisisfine": ("113_04", 1.0),
              "baton": ("85_14", 3.0), "goat": ("90_30", 0.5), "slerf": ("55_02", 1.0), "mensa": ("141_12", 0.0), "bome": ("120_05", 0.0),
              "brett": ("141_12", 2.0), "npcwojak": ("120_21", 3.0)}
for i, (cid, (x, y)) in enumerate(zip(dancers, spots)):
    cl, st = DANCE_CLIP[cid]
    md, lk = LOOKS.get(cid, (None, None))
    mocap(cid, x + random.uniform(-0.15, 0.15), y, face(7.8 - x, -4.8 - y) + random.uniform(-0.4, 0.4), cl, start=st, travel=0.1, model=md, look=lk)

MEM("dancers")
# in the pool: treading water (sunk to the shoulders), one on the donut
for cid, (x, y) in (("moodeng", (-4.7, -0.7)), ("zcat", (1.5, 1.2)), ("cupsey", (3.4, -0.9)), ("pudgy", (-0.3, 0.6)), ("nyancat", (4.8, 1.4))):
    c = load(cid); guests[cid] = c
    zsink = WZ - c.shoulderL.z + 0.08
    place(c, x, y, face(random.uniform(-1, 1), -1), zsink)
    c.bake(M.swim, 1, N, step=2, phase=random.random())

# cannonballs: a run along the deck, a leap, a tucked fall, a splash, then treading water
SPL = mat("splash", "#E9FBFF", rough=0.1, alpha=0.75, emit=0.5)
def cannonball(cid, x, f_jump):
    c = load(cid); guests[cid] = c
    y_run0, y_edge, y_land = -5.8, -2.7, -0.6
    zsink = WZ - c.shoulderL.z + 0.08
    f_run0, f_air, f_land = f_jump - 30, f_jump, f_jump + 22
    if not c.ik: c.play_seq([("idle", 1, f_run0), ("run", f_run0, f_land), ("idle", f_land, N)])
    for f in range(1, N + 1, 2):
        if f < f_run0:
            p = Vector((x, y_run0, 0)); pose = M.cheer(c, f / FPS); pose["hips"] = Vector((0, 0, 0))
        elif f < f_air:
            k = (f - f_run0) / (f_air - f_run0); p = Vector((x, y_run0 + (y_edge - y_run0) * k, 0))
            pose = M.dance_step(c, f / FPS * 2)
        elif f < f_land:
            k = (f - f_air) / (f_land - f_air)
            p = Vector((x, y_edge + (y_land - y_edge) * k, 0.0 + 1.6 * math.sin(math.pi * k) * (1 - k * 0.3) - (0 - zsink) * k ** 2))
            pose = M.tuck(c, 0)
        else:
            k = min(1.0, (f - f_land) / 12); p = Vector((x, y_land, zsink + 0.3 * (1 - k) - 0.25 * math.sin(math.pi * k)))
            pose = M.swim(c, f / FPS)
        pose["loc"] = p; pose["rot"] = face(0, 1) if f < f_land else face(0, -1)
        c.key(f, pose)
    # the splash: a crown of drops and a ring on the water
    for i in range(26):
        a = i / 26 * math.tau; s = sphere("drop", (x, y_land, WZ), random.uniform(0.04, 0.09), SPL, seg=8)
        v = Vector((math.cos(a) * random.uniform(0.8, 2.0), math.sin(a) * random.uniform(0.8, 2.0), random.uniform(3.0, 5.0)))
        s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=f_land - 1); s.keyframe_insert("location", frame=f_land - 1)
        s.scale = (1, 1, 1); s.keyframe_insert("scale", frame=f_land)
        for j in range(1, 26, 3):
            tt = j / FPS; s.location = (x + v.x * tt, y_land + v.y * tt, max(WZ, WZ + v.z * tt - 4.9 * tt * tt)); s.keyframe_insert("location", frame=f_land + j)
        s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=f_land + 27)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.4, minor_radius=0.04, location=(x, y_land, WZ + 0.01))
    ring = obj_mat(bpy.context.active_object, SPL)
    ring.scale = (0.01,) * 3; ring.keyframe_insert("scale", frame=f_land - 1); ring.scale = (1, 1, 1); ring.keyframe_insert("scale", frame=f_land)
    ring.scale = (5, 5, 1); ring.keyframe_insert("scale", frame=f_land + 40); ring.scale = (0.01,) * 3; ring.keyframe_insert("scale", frame=f_land + 41)
cannonball("popcat", -1.6, 200)

MEM("cannonball")
# poolside drinkers, chatting, red cups in hand
# walkers: a slow lap of the west and south deck with a drink in hand, on the game's own walk cycle
def walk_loop(c, pts, speed, offset=0.0, clip_speed=None, f_from=1, play=True):
    """Walk a closed polyline at `speed` m/s, facing along it; the walk clip's rate matches the pace (no sliding)."""
    segs = [(Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])) for i in range(len(pts))]
    L = sum((b - a).length for a, b in segs)
    if play: c.play("walk", 1, speed=clip_speed or speed / 1.1)
    prev = None
    for f in range(f_from, N + 1, 2):
        d = (speed * (f - f_from + 1) / FPS + offset) % L
        for a, b in segs:
            sl = (b - a).length
            if d <= sl:
                p = a.lerp(b, d / sl); dirv = (b - a).normalized(); break
            d -= sl
        rot = face(dirv.x, dirv.y)
        if prev is not None:
            while rot - prev > math.pi: rot -= math.tau
            while rot - prev < -math.pi: rot += math.tau
        prev = rot
        c.key(f, {"clip_driven": True, "loc": Vector((p.x, p.y, 0)), "rot": rot})
lap = [(-10.4, -3.4), (-10.4, -8.2), (-0.8, -8.4), (-0.8, -7.2), (-9.0, -7.0), (-9.0, -3.4)]
for i, cid in enumerate(("chillguy", "jeanphil")):
    c = load(cid); guests[cid] = c
    walk_loop(c, lap, 0.9, offset=i * 9.0)
    attach(c, cyl("cup", (0, 0, 0), 0.045, 0.13, CUP), offset=(0, 0.07, 0.04), rot=(math.pi / 2, 0, 0))
# chatters by the deck's west side
# the conga line: round and round the pool, the game's own walk
def loop_point(s):   # a rounded rectangle 1 m outside the coping, s in metres along it
    W2, H2, R = PX + 0.75, PY + 0.75, 1.0
    segs = [2 * (W2 - R), math.pi * R / 2, 2 * (H2 - R), math.pi * R / 2] * 2
    L = sum(segs); s %= L
    corners = [(W2 - R, -(H2 - R)), (W2 - R, H2 - R), (-(W2 - R), H2 - R), (-(W2 - R), -(H2 - R))]
    starts = [(-(W2 - R), -H2), (W2, -(H2 - R)), (W2 - R, H2), (-W2, H2 - R)]
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for k in range(4):
        st = segs[2 * k]
        if s < st:
            x0, y0 = starts[k]; dx, dy = dirs[k]; return Vector((x0 + dx * s, y0 + dy * s, 0)), (dx, dy)
        s -= st
        if s < segs[2 * k + 1]:
            cx, cy = corners[k]; a0 = -math.pi / 2 + k * math.pi / 2; a = a0 + s / R
            return Vector((cx + R * math.cos(a), cy + R * math.sin(a), 0)), (-math.sin(a), math.cos(a))
        s -= segs[2 * k + 1]
    return Vector((0, -H2, 0)), (1, 0)
ch_d = mocap("chillhouse", -6.2, -10.2, face(1, -0.2), "91_09", start=0.0, travel=0.25)   # staggering drunk on the lawn...
for f in range(1, N + 1, 6):   # ...and really getting somewhere: weaving east across the lawn, clear of the fire pit
    u = (f - 1) / (N - 1)
    x_, y_ = -6.2 + 6.7 * u, -10.2 - 1.6 * u + 0.35 * math.sin(u * 9)
    dx_, dy_ = 6.7, -1.6 + 0.35 * 9 * math.cos(u * 9)
    ch_d.ctrl.location = (x_, y_, 0); ch_d.ctrl.rotation_euler = (0, 0, face(dx_, dy_) + 0.25 * math.sin(u * 23))
    ch_d.ctrl.keyframe_insert("location", frame=f); ch_d.ctrl.keyframe_insert("rotation_euler", frame=f)
for i, cid in enumerate(("useless", "wif", "bonk", "pnut")):
    md, lk = LOOKS.get(cid, (None, None))
    c = load(cid, md, lk); guests[cid] = c; c.play("walk", 1, speed=1.15)
    if cid == "wif": beanie(c)
    for f in range(1, N + 1, 2):
        p, (dx, dy) = loop_point(1.15 * f / FPS - (0.0, 1.6, 3.2, 5.0)[i] + 6.0)   # PNUT (long, a big tail) and BONK (a bat) get extra room
        c.key(f, {"clip_driven": True, "loc": p, "rot": face(dx, dy)})
    for fc in c.ctrl.animation_data.action.fcurves:   # no flips where the angle wraps
        if fc.data_path == "rotation_euler" and fc.array_index == 2:
            prev = None
            for k in fc.keyframe_points:
                if prev is not None:
                    while k.co.y - prev > math.pi: k.co.y -= math.tau
                    while k.co.y - prev < -math.pi: k.co.y += math.tau
                prev = k.co.y

# the kitchen bar: drinks
c = load("dope"); guests["dope"] = c   # DOPE wanders the living room
walk_loop(c, [(-1.5, 6.4), (1.8, 6.4), (1.8, 7.6), (-1.5, 7.6)], 0.7, offset=2.0)
# from frame 531 (the camera is looking west, away from him) he circles the dining table instead: his old loop was right
# in the camera's path from the living room to the kitchen (his head filled the frame)
walk_loop(c, [(0.4, 10.0), (0.4, 11.95), (-3.1, 11.95), (-3.1, 10.0)], 0.7, f_from=531, play=False)

MEM("bar")
# the two couples
def couple(a, b, x, y, ang):
    ca, cb = load(a), load(b); guests[a] = ca; guests[b] = cb
    dx, dy = math.sin(ang), -math.cos(ang)
    gap = 0.17 + 0.5 * (ca.arm + cb.arm) * 0.25
    place(ca, x - dx * gap, y - dy * gap, face(dx, dy)); place(cb, x + dx * gap, y + dy * gap, face(-dx, -dy))
    ca.bake(M.kiss, 1, N, step=2, partner_head=look_at(ca, cb))
    cb.bake(M.kiss, 1, N, step=2, partner_head=look_at(cb, ca), phase=0.5)
couple("pepe", "pippin", 8.7, 2.3, math.pi / 2)     # under the north end of the pergola
couple("troll", "michi", -7.6, 6.3, math.pi / 2)     # inside, by the west window


# THE WHALE on the balcony, making it rain on the pool
BILL = bpy.data.materials.new("bill"); BILL.use_nodes = True
_bt = BILL.node_tree; _bb = _bt.nodes["Principled BSDF"]; _bi = _bt.nodes.new("ShaderNodeTexImage")
_bi.image = bpy.data.images.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "bill.png"))
_bt.links.new(_bi.outputs["Color"], _bb.inputs["Base Color"]); _bt.links.new(_bi.outputs["Color"], _bb.inputs["Emission Color"])
_bb.inputs["Emission Strength"].default_value = 0.35; _bb.inputs["Roughness"].default_value = 0.6
wh = load("whale"); guests["whale"] = wh; place(wh, 1.2, 5.45, face(0, -1), z=3.85)   # his throwing arm clears the glass
wh.bake(M.make_it_rain, 1, N, step=2)
stack = attach(wh, box("cash_stack", -0.09, 0.09, -0.04, 0.04, -0.02, 0.06, BILL), offset=(0, 0.1, 0.02))
# ...with a party girl on each side of him, flinging it too (both made from the game's Wojak)
THROWERS = [1.2]
for cid, x, hair, dress, bow, ph in (("wojakgirl", -0.2, "#F3D27A", "#FF4FA3", "#FF2B8A", 0.33), ("doomergirl", 2.6, "#141218", "#1B1B22", None, 0.66)):
    g = load(cid, "wojak", {"hue": 0.5, "sat": 0.9, "val": 1.05, "tint": "#FFE4D6"}); guests[cid] = g
    place(g, x, 4.95, face((1.2 - x) * 0.25, -1), z=3.85)
    party_girl(g, hair, dress, bow)
    g.bake(M.make_it_rain, 1, N, step=2, phase=ph)
    attach(g, box("cash_stack", -0.09, 0.09, -0.04, 0.04, -0.02, 0.06, BILL), offset=(0, 0.1, 0.02))
    THROWERS.append(x)
bill_mesh = None
NB = 480
for i in range(NB):
    f0 = 10 + int(i * (N - 70) / NB) + random.randint(0, 3)
    if bill_mesh is None:
        bpy.ops.mesh.primitive_plane_add(size=1); tmp = bpy.context.active_object; bill_mesh = tmp.data; bill_mesh.materials.append(BILL); bpy.data.objects.remove(tmp)
    b = bpy.data.objects.new("bill", bill_mesh); sc.collection.objects.link(b)
    S0 = (0.32, 0.14, 1)
    x0 = THROWERS[i % len(THROWERS)] + random.uniform(-0.4, 0.4)
    b.location = (x0, 4.3, 4.9); b.scale = (0.0001,) * 3; b.keyframe_insert("scale", frame=1); b.keyframe_insert("scale", frame=f0 - 1)
    b.keyframe_insert("location", frame=f0 - 1)
    b.scale = S0; b.keyframe_insert("scale", frame=f0)
    vx, vy = random.uniform(-2.6, 2.6), random.uniform(-3.4, -0.8)
    land = None
    for j in range(0, 150, 5):   # a slow flutter down: lift, drag, sway
        tt = j / FPS; z = 4.9 + 1.0 * tt - 0.85 * tt * tt
        x = x0 + vx * tt * 0.8 + 0.3 * math.sin(tt * 4 + i); y = 4.3 + vy * tt * 0.8
        floor = WZ + 0.01 if (abs(x) < PX and abs(y) < PY) else 0.012
        if z <= floor: z = floor; land = land or j
        b.location = (x, y, z)
        b.rotation_euler = ((math.sin(tt * 5 + i) * 1.2) if not land else 0, (math.cos(tt * 4 + i) * 0.9) if not land else 0, tt * 2 + i)
        b.keyframe_insert("location", frame=f0 + j); b.keyframe_insert("rotation_euler", frame=f0 + j)

# SWORDCAT: off the balcony, a backflip, into the pool
sw = load("swordcat"); guests["swordcat"] = sw
F_FLIP = 384
zsink = WZ - sw.shoulderL.z + 0.08
for f in range(1, N + 1, 2):
    if f < F_FLIP:
        pose = M.cheer(sw, f / FPS); p = Vector((-3.0, 4.95, 3.85)); rx = 0.0
    elif f < F_FLIP + 26:
        k = (f - F_FLIP) / 26
        p = Vector((-3.0 + 0.2 * k, 4.95 + (0.1 - 4.95) * k, 3.85 + 2.2 * math.sin(math.pi * k) * (1 - 0.4 * k) - (3.85 - zsink) * k ** 1.6))
        pose = M.tuck(sw, 0); rx = -math.tau * min(1.0, k * 1.05)
    else:
        k = min(1.0, (f - F_FLIP - 26) / 12); p = Vector((-2.8, 0.1, zsink - 0.35 * math.sin(math.pi * k))); pose = M.swim(sw, f / FPS); rx = 0.0
    pose["loc"] = p; pose["rot"] = face(0, -1); pose["rx"] = rx
    sw.key(f, pose)
for i in range(30):
    a = i / 30 * math.tau; s = sphere("drop", (-2.8, 0.1, WZ), random.uniform(0.04, 0.1), SPL, seg=8)
    v = Vector((math.cos(a) * random.uniform(0.8, 2.4), math.sin(a) * random.uniform(0.8, 2.4), random.uniform(3.5, 6.0)))
    fl = F_FLIP + 26
    s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=fl - 1); s.keyframe_insert("location", frame=fl - 1)
    s.scale = (1, 1, 1); s.keyframe_insert("scale", frame=fl)
    for j in range(1, 30, 3):
        tt = j / FPS; s.location = (-2.8 + v.x * tt, 0.1 + v.y * tt, max(WZ, WZ + v.z * tt - 4.9 * tt * tt)); s.keyframe_insert("location", frame=fl + j)
    s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=fl + 31)


def snort_fx(lines, line_pts, period, phase, name):
    """Each snort: the next line on the table shrinks away as the nose slides along it, and a small white puff comes up."""
    PUFF = soft("powder_puff", "#FFFFFF", alpha=0.8, emit=0.5)
    k = 0; t = ((0.22 - phase) % 1.0) * period
    for ln in lines:
        ln.scale = (1, 1, 1); ln.keyframe_insert("scale", frame=1)
    while t * FPS < N:
        i = k % len(lines); ln = lines[i]; p = line_pts[i]
        f_a = int(t * FPS) + 1; f_b = int((t + 0.33 * period) * FPS) + 1
        if i == 0 and k > 0:   # a fresh set racked up
            for l2 in lines:
                l2.scale = (1, 1, 1); l2.keyframe_insert("scale", frame=f_a - 2)
        ln.scale = (1, 1, 1); ln.keyframe_insert("scale", frame=f_a)
        ln.scale = (0.02, 1, 1); ln.keyframe_insert("scale", frame=f_b)
        for j in range(9):   # the puff at the end of the line, and a little burst at the snap back
            s = sphere("puff_" + name, p, 0.025, PUFF, seg=16)
            s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=1); s.keyframe_insert("scale", frame=f_b - 2); s.keyframe_insert("location", frame=f_b - 2)
            s.scale = (1, 1, 1); s.keyframe_insert("scale", frame=f_b)
            s.location = (p[0] + random.uniform(-0.12, 0.12), p[1] + random.uniform(-0.12, 0.12), p[2] + random.uniform(0.12, 0.3))
            s.scale = (2.2,) * 3; s.keyframe_insert("location", frame=f_b + 18); s.keyframe_insert("scale", frame=f_b + 14)
            s.scale = (0.01,) * 3; s.keyframe_insert("scale", frame=f_b + 22)
        k += 1; t += period

if not CLEAN:
    CRATE = mat("crate", "#E0601A", rough=0.6)
    def snort_station(cid, x, y_edge, toward, table_z, phase, n_lines, model=None):
        """A snorter at a table. The bend comes from M.snort with the character's own proportions; a short character gets
        a beer crate to stand on so the bend is deep, and the lines go exactly where that nose lands, running along the
        slide (local x) so the nose travels down each line."""
        c = load(cid, model); guests[cid] = c
        H = max(0.2, (c.headp - c.hip).z); dip = 0.12 * c.leg
        lift = max(0.0, (table_z + 0.05 - 0.3 * H) - (c.hip.z - dip))
        k = max(-0.95, min(0.95, (table_z - lift + 0.05 - (c.hip.z - dip)) / H)); full = min(math.acos(k), 1.65)
        v = c.headp - c.hip
        d = -(0.1 + v.y * math.cos(full) - v.z * math.sin(full) - 0.12)     # how far in front of the ctrl the nose lands
        y = y_edge + toward * max(0.4, d - 0.05)                           # stand back from the edge (knees clear), nose just inside it
        place(c, x, y, face(0, -toward), z=lift)
        if lift > 0.02:
            box("crate_" + cid, x - 0.26, x + 0.26, y - 0.2, y + 0.24, 0.0, lift, CRATE, bevel=0.02)
        c.bake(M.snort, 1, N, step=1, table_z=table_z - lift, reach=0.6, period=3.2, phase=phase)
        attach(c, cyl("note", (0, 0, 0), 0.012, 0.12, NOTE), offset=(0, 0.05, 0.02), rot=(math.pi / 2, 0, 0))
        ly = y - toward * d; sx = -toward     # local x in world: +x when facing -y
        lines, pts = [], []
        for i in range(n_lines):
            yy = ly + toward * (i - (n_lines - 1) / 2) * 0.035
            lines.append(box("line", x - 0.13, x + 0.13, yy - 0.008, yy + 0.008, table_z, table_z + 0.006, POWDER))
            pts.append((x + sx * 0.12, yy, table_z + 0.01))   # where the nose finishes the line
        snort_fx(lines, pts, 3.2, phase, cid)
        print(f"SNORT {cid}: H {H:.2f} lift {lift:.2f} bend {math.degrees(full):.0f} nose {d:.2f} at y {ly:.2f}")
        return c
    # the coffee table in the living room (x -5.5..-4.9, y 8.3..9.5, top 0.41), and LMAO in hysterics beside him
    snort_station("farter", -5.2, 8.3, -1, 0.41, 0.0, 3)
    mocap("lmao", -4.2, 8.5, face(-1, 0.4), "13_14", start=1.0, travel=0.0)
    # KET and CATE behind the kitchen island (the marble's back edge is y 10.05)
    snort_station("ket", 3.5, 10.05, 1, 1.06, 0.0, 4)
    snort_station("cate", 5.1, 10.05, 1, 1.06, 0.45, 4)
    box("card", 4.25, 4.35, 9.75, 9.95, 1.06, 1.064, mat("blackcard", "#111111", rough=0.3, metal=0.5))

    GAS = soft("gas", "#7BE04A", alpha=0.5, emit=0.8)
    for k in range(8):
        g = sphere("gas", (-5.9, 7.7, 0.6), 0.14, GAS, seg=20)
        for f in range(1, N + 1, 35):
            ph = ((f / 105) + k / 8) % 1.0
            g.location = (-5.9 + 0.6 * ph * math.sin(k), 7.6 - 0.6 * ph, 0.55 + 0.9 * ph); g.scale = (0.5 + 1.6 * ph,) * 3
            g.keyframe_insert("location", frame=f); g.keyframe_insert("scale", frame=f)
    # smokers under the pergola: a real drag, the ember flaring, held in, blown at the sky; BATON coughs his lungs out
    def set_mouth(c):
        """Where the lips are, in the character's own space, from the head's real mesh (front, lower third)."""
        hg = bone_geom(c, "Head")
        if not hg: return
        C_, h = hg
        bpy.context.view_layer.update()
        Mx = c.ctrl.matrix_world.inverted() @ c.rig.matrix_world @ c.rig.data.bones["mixamorig:Head"].matrix_local
        c.mouth_bone = C_ + Vector((0, -0.4 * h.y, 0.92 * h.z)); c.mouth = Mx @ c.mouth_bone
    def key_emit(m, f, v):
        i = m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]; i.default_value = v; i.keyframe_insert("default_value", frame=f)
    def cycles(period, phase, x0):
        """Frames where a cycle reaches phase-fraction x0."""
        n = 0; out = []
        while True:
            t = (n + x0 - phase) * period
            if t * FPS > N: return out
            if t >= 0: out.append((n, int(t * FPS) + 1))
            n += 1
    def puff(parent, p0, p1, f0, life, r0, r1, name="puff"):
        s = sphere(name, (0, 0, 0), 0.06, SMOKE, seg=20); s.parent = parent
        s.location = p0; s.scale = (0.001,) * 3
        s.keyframe_insert("scale", frame=1); s.keyframe_insert("scale", frame=max(1, f0 - 1)); s.keyframe_insert("location", frame=max(1, f0 - 1))
        s.scale = (r0,) * 3; s.keyframe_insert("scale", frame=f0 + 2)
        s.location = p1; s.scale = (r1,) * 3; s.keyframe_insert("location", frame=f0 + life); s.keyframe_insert("scale", frame=f0 + life - 6)
        s.scale = (0.001,) * 3; s.keyframe_insert("scale", frame=f0 + life + 4)
    P_SM = 5.0
    for i, (cid, x, y, tx, ty) in enumerate((("walter", 9.0, -0.3, 9.8, -1.1), ("floki", 9.8, -1.1, 9.0, -0.3), ("toshi", 8.85, -2.0, 9.6, -0.9))):   # BATON has no hand bones
        ph = i * 0.31; cough = (cid == "toshi")
        c = load(cid); guests[cid] = c; place(c, x, y, face(tx - x, ty - y)); set_mouth(c)
        c.bake(M.smoke_real, 1, N, step=2, period=P_SM, phase=ph, toward=to_local(c, (tx, ty, 1.5)), cough=cough)
        EM = mat("ember_" + cid, "#FF6A1A", emit=5.0)
        attach(c, cyl("cig", (0, 0, 0), 0.008, 0.09, CIG), offset=(0.02, 0.07, 0.03), rot=(0, 0, math.pi / 2))
        attach(c, sphere("ember", (0, 0, 0), 0.011, EM, seg=12), offset=(0.065, 0.07, 0.03))
        key_emit(EM, 1, 5.0)
        for n, f in cycles(P_SM, ph, M.SMOKE_T["drag"][0]):      # the ember flares on every drag
            fd = int((M.SMOKE_T["drag"][1] - M.SMOKE_T["drag"][0]) * P_SM * FPS)
            key_emit(EM, f, 5.0); key_emit(EM, f + 6, 70.0); key_emit(EM, f + fd, 55.0); key_emit(EM, f + fd + 8, 5.0)
        m = c.mouth if hasattr(c, "mouth") else c.headp + Vector((0, -0.12, 0.06))
        for n, f in cycles(P_SM, ph, M.SMOKE_T["exhale"][0]):
            fe = int((M.SMOKE_T["exhale"][1] - M.SMOKE_T["exhale"][0]) * P_SM * FPS)
            if cough and n % 2 == 1:   # bursts with each hack
                for j in range(7):
                    puff(c.ctrl, m + Vector((0, -0.08, -0.05)), m + Vector((random.uniform(-0.25, 0.25), -0.45, random.uniform(-0.2, 0.15))), f + int(j * fe / 7), 26, 0.6, 1.6)
            else:              # a long stream, up and away from the tipped-back head
                for j in range(9):
                    fj = f + 4 + int(j * (fe - 10) / 9)
                    puff(c.ctrl, m + Vector((0, -0.06, 0.05)), m + Vector((random.uniform(-0.2, 0.2), -0.35 - 0.04 * j, 0.9 + random.uniform(0, 0.3))), fj, 48, 0.5, 2.4)
    # the bong: WOJAK and APU in turns, on lounge chairs either side of a little table
    P_B = 9.0
    BAG_M = {}
    def bean_bag(c, color):
        """A big squashy bean bag sized to this guest: the seat just under their dropped hips, rising into a slumped
        back behind them, a dent where they sit. Parented to the guest, so it sits where they sit."""
        if color not in BAG_M:
            BAG_M[color] = mat("beanbag_" + color, color, rough=0.85); retex(BAG_M[color], color, color, kind="noise", scale=90.0, rough=0.85, bump=0.5)
        seat_z = max(0.18, c.hip.z - c.leg * 0.45 - 0.06)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=64, ring_count=32)
        b = obj_mat(bpy.context.active_object, BAG_M[color]); b.name = "beanbag"
        for v in b.data.vertices:
            x, y, z = v.co; back = max(0.0, y); front = max(0.0, -y)
            # high under the hips, rising into a slumped back behind, sloping right down at the front so the thighs lie
            # on it (a flat-topped front had his thighs straight through the bag and his shins coming out the bottom)
            top = (seat_z + 0.45 * back ** 1.5) * max(0.15, 1.0 - 1.25 * front ** 1.2)
            Z = (z + 1) / 2 * top - 0.07 * math.exp(-(x * x + (y - 0.1) ** 2) / 0.18) * max(0.0, z)
            v.co = (0.5 * x * (1 + 0.08 * (1 - z)), 0.42 * y, max(0.0, Z))   # centred under the hips
        b.data.shade_smooth(); sd = b.modifiers.new("smooth", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
        b.parent = c.ctrl; b.location = (0, 0.12, 0)
        return b
    light("bong_lamp", "AREA", (10.6, -3.4, 2.7), 260, "#FFB070", 1.6)        # a warm lamp over the loungers
    light("bong_rim", "POINT", (12.2, -3.4, 1.4), 120, "#9A6BFF", 0.3)        # and a purple rim from the palms
    cyl("side_table", (10.6, -3.4, 0.2), 0.05, 0.4, OAK, v=16); cyl("side_table_top", (10.6, -3.4, 0.41), 0.22, 0.03, OAK, v=40)
    BONG = mat("bong", "#7FE0C8", rough=0.02, alpha=0.45, emit=0.4)
    WATER_B = mat("bong_water", "#3FB8A8", rough=0.05, alpha=0.6, emit=0.3)
    CHAMBER = soft("chamber", "#F4F4F4", alpha=0.9, emit=0.4)
    BOWL_EM = mat("bowl_ember", "#FF5A10", emit=3.0)
    bong = bpy.data.objects.new("bong_root", None); sc.collection.objects.link(bong)
    def part(o): o.parent = bong; return o
    part(sphere("bong_base", (0, 0, 0.11), 0.11, BONG, seg=32))
    part(sphere("bong_water", (0, 0, 0.075), 0.095, WATER_B, seg=24)).scale = (1, 1, 0.55)
    part(cyl("bong_tube", (0, 0, 0.42), 0.042, 0.5, BONG, v=32))
    part(cyl("bong_stem", (-0.075, 0, 0.21), 0.011, 0.16, BONG, rot=(0, math.radians(-42), 0), v=12))
    bpy.ops.mesh.primitive_cone_add(radius1=0.016, radius2=0.03, depth=0.04, vertices=20, location=(-0.13, 0, 0.275))
    part(obj_mat(bpy.context.active_object, mat("bowl", "#C8CCD2", rough=0.2, metal=0.9)))
    ember_b = part(sphere("bowl_ember", (-0.13, 0, 0.295), 0.017, BOWL_EM, seg=12))
    ch = cyl("chamber", (0, 0, 0), 0.036, 1.0, CHAMBER, v=24)
    for v in ch.data.vertices: v.co.z += 0.5                     # its origin at the bottom so it fills upward
    part(ch); ch.location = (0, 0, 0.2); ch.scale = (1, 1, 0.001)
    lighter = part(box("lighter", -0.012, 0.012, -0.007, 0.007, -0.03, 0.03, mat("lighter", "#E8302A", rough=0.3), bevel=0.0))
    lighter.location = (-0.18, -0.02, 0.22)
    bpy.ops.mesh.primitive_cone_add(radius1=0.008, radius2=0.0, depth=0.035, vertices=12, location=(-0.18, -0.02, 0.27))
    flame = part(obj_mat(bpy.context.active_object, mat("lighter_flame", "#FFB23A", emit=30.0)))
    bubbles = [part(sphere("bubble", (0, 0, 0.06), 0.011, mat("bubble", "#E8FFFA", rough=0.0, alpha=0.5), seg=10)) for _ in range(7)]
    for o in (lighter, flame, *bubbles): o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=1)
    TABLE = (Vector((10.6, -3.4, 0.43)), face(0, 1) - math.pi / 2)
    bong.location, bong.rotation_euler.z = TABLE[0], TABLE[1]; bong.keyframe_insert("location", frame=1); bong.keyframe_insert("rotation_euler", frame=1)
    key_emit(BOWL_EM, 1, 3.0)
    def at_table(f):
        bong.location = TABLE[0]; bong.rotation_euler = (0, 0, TABLE[1]); bong.scale = (1, 1, 1)
        for k in ("location", "rotation_euler", "scale"): bong.keyframe_insert(k, frame=f)
    for cid, x, y, rot, ph in (("wojak", 10.6, -4.2, face(0, 1), 0.0), ("apu", 10.6, -2.6, face(0, -1), 0.5)):
        c = load(cid); guests[cid] = c; place(c, x, y, rot); set_mouth(c)
        bean_bag(c, "#5B2A86" if cid == "wojak" else "#1F7A5A")
        top = M.bong_rig(c, 0.5) + Vector((0, -0.03, 0.0))   # the mouthpiece at the lips, leaning in
        s_ = max(0.55, min(1.0, (top.z - 0.02) / 0.67))      # a shorter guest gets a shorter bong (it's the same bong, no one checks)
        TILT = math.radians(-27); Rt = Matrix.Rotation(TILT, 3, "X")   # tipped away: lips on the mouthpiece, the base out over the knees
        root = top - Rt @ Vector((0, 0, 0.67 * s_)); bowl = root + (Rt @ Vector((-0.13, 0, 0.295))) * s_
        c.bake(M.bong_session, 1, N, step=2, period=P_B, phase=ph, bong_top=top, bowl=bowl)
        if hasattr(c, "mouth_bone"):   # measure where the mouth really is mid-hit, put the mouthpiece on the lips, bake again
            fm = cycles(P_B, ph, 0.25)[0][1]; sc.frame_set(fm); bpy.context.view_layer.update()
            Hm = c.rig.matrix_world @ c.rig.pose.bones["mixamorig:Head"].matrix
            m_loc = c.ctrl.matrix_world.inverted() @ (Hm @ c.mouth_bone)
            top = m_loc + Vector((0, -0.035, -0.03)); s_ = max(0.55, min(1.0, (top.z - 0.02) / 0.67))
            root = top - Rt @ Vector((0, 0, 0.67 * s_)); bowl = root + (Rt @ Vector((-0.13, 0, 0.295))) * s_
            c.bake(M.bong_session, 1, N, step=2, period=P_B, phase=ph, bong_top=top, bowl=bowl)
            sc.frame_set(1)
            print(f"BONG {cid}: measured mouth {tuple(round(v, 2) for v in m_loc)}")
        bpy.context.view_layer.update(); W = c.ctrl.matrix_world
        mouth_seat = (c.mouth if hasattr(c, "mouth") else c.headp) + Vector((0, 0.12, -c.leg * 0.45))
        print(f"BONG {cid}: mouthpiece z {top.z:.2f} bong scale {s_:.2f}")
        for n, f0 in cycles(P_B, ph, 0.0):
            fr = lambda xx: f0 + int(xx * P_B * FPS)
            at_table(f0)
            for xx in (M.BONG_T["grab"][1], M.BONG_T["put"][0]):
                bong.location = W @ root; bong.rotation_euler = (TILT, 0, rot); bong.scale = (s_,) * 3
                for k in ("location", "rotation_euler", "scale"): bong.keyframe_insert(k, frame=fr(xx))
            at_table(fr(M.BONG_T["put"][1]))
            h0, h1 = fr(M.BONG_T["hit"][0]), fr(M.BONG_T["hit"][1]); c0, c1 = fr(M.BONG_T["clear"][0]), fr(M.BONG_T["clear"][1])
            # the lighter comes up and the flame flickers; the bowl glows; bubbles rise; the chamber fills milky white
            for o, sz in ((lighter, 1.0), (flame, 1.0)):
                o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=h0 - 2)
                o.scale = (sz,) * 3; o.keyframe_insert("scale", frame=h0 + 2)
                if o is flame:
                    for ff in range(h0 + 4, h1, 3):
                        o.scale = (1.0, 1.0, random.uniform(0.7, 1.4)); o.keyframe_insert("scale", frame=ff)
                o.scale = (sz,) * 3; o.keyframe_insert("scale", frame=h1 - 1)
                o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=h1 + 2)
            key_emit(BOWL_EM, h0, 3.0); key_emit(BOWL_EM, h0 + 8, 45.0); key_emit(BOWL_EM, h1, 40.0); key_emit(BOWL_EM, h1 + 10, 3.0)
            for b_ in bubbles:
                for ff in range(h0, h1, 4):
                    b_.location = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 0.03); b_.scale = (1, 1, 1)
                    b_.keyframe_insert("location", frame=ff); b_.keyframe_insert("scale", frame=ff)
                    b_.location.z = 0.11; b_.keyframe_insert("location", frame=ff + 3)
                b_.scale = (0.001,) * 3; b_.keyframe_insert("scale", frame=h1 + 1)
            ch.location = (0, 0, 0.2); ch.scale = (1, 1, 0.001); ch.keyframe_insert("location", frame=h0); ch.keyframe_insert("scale", frame=h0)
            ch.scale = (1, 1, 0.44); ch.keyframe_insert("scale", frame=h1); ch.keyframe_insert("location", frame=h1)
            ch.location = (0, 0, 0.64); ch.scale = (1, 1, 0.001); ch.keyframe_insert("location", frame=c1); ch.keyframe_insert("scale", frame=c1)   # cleared, up into the mouth
            # held in, then a huge cloud at the sky, then a coughing fit
            e0, e1 = fr(M.BONG_T["exhale"][0]), fr(M.BONG_T["exhale"][1])
            for j in range(12):
                fj = e0 + int(j * (e1 - e0) / 12)
                puff(c.ctrl, mouth_seat + Vector((0, 0.05, 0.0)), mouth_seat + Vector((random.uniform(-0.35, 0.35), random.uniform(-0.5, 0.1), 1.3 + random.uniform(0, 0.5))), fj, 60, 0.8, 4.2, "cloud")
            k0, k1 = fr(M.BONG_T["cough"][0]), fr(M.BONG_T["cough"][1])
            for j in range(6):
                puff(c.ctrl, mouth_seat + Vector((0, -0.1, -0.05)), mouth_seat + Vector((random.uniform(-0.3, 0.3), -0.6, random.uniform(-0.3, 0.2))), k0 + int(j * (k1 - k0) / 6), 24, 0.6, 1.8)

else:
    for cid, x in (("farter", -5.6), ("lmao", -4.8)):
        guest(cid, x, 8.3, face(0, -1), M.cheer, phase=random.random())
    for i, cid in enumerate(("whale", "walter", "floki", "baton", "wojak", "apu")):
        guest(cid, 9.2 + (i % 2) * 0.8, 2.0 - i * 1.2, face(-1, -0.3), M.DANCES[i % 5], phase=random.random())

# no guest stands or walks on litter: drop loose trash within reach of anyone's path
def ctrl_track(c, step=10):
    ad = c.ctrl.animation_data
    if not (ad and ad.action): return [c.ctrl.location.copy()]
    fx = {fc.array_index: fc for fc in ad.action.fcurves if fc.data_path == "location"}
    return [Vector((fx[0].evaluate(f) if 0 in fx else c.ctrl.location.x, fx[1].evaluate(f) if 1 in fx else c.ctrl.location.y, 0)) for f in range(1, N + 1, step)]
tracks = [p for c in guests.values() for p in ctrl_track(c)]
gone = 0
for o in list(bpy.data.objects):
    base = o.name.split(".")[0]
    if base not in ("cup", "can", "pizzabox", "pizza", "pep", "bottle_trash", "cup_trash") or o.constraints or o.parent: continue
    bb = [o.matrix_world @ Vector(q) for q in o.bound_box]; p = sum(bb, Vector()) / 8   # the real centre (some have origins at 0)
    if p.z > 0.4: continue
    if any((Vector((p.x, p.y, 0)) - q).length < 0.6 for q in tracks):
        bpy.data.objects.remove(o); gone += 1
print("litter cleared from paths:", gone)
print("guests:", len(guests))
MEM("guests")

# ------------------------------------------------------------------------------------------------ the camera: one sweep
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 24; cam.data.clip_end = 300
tgt = bpy.data.objects.new("CamTarget", None); sc.collection.objects.link(tgt)
tcn = cam.constraints.new("TRACK_TO"); tcn.target = tgt; tcn.track_axis = "TRACK_NEGATIVE_Z"; tcn.up_axis = "UP_Y"

# DOGE by the pool's south-west corner, the doge words floating round him (they turn to face the camera)
DOGE_AT = (-7.4, -3.9)   # off the camera's path down to the pool (it brushed past him), clear of the conga and the loungers
dg = mocap("doge", DOGE_AT[0], DOGE_AT[1], face(0.9, -0.6), "120_05", start=1.0, travel=0.05, model="bonk", look=LOOKS["doge"][1])
COMIC = bpy.data.fonts.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ComicNeue-Bold.ttf"))
for k, (word, col, off) in enumerate((("wow", "#FF4FD8", (-0.9, 0, 2.3)), ("such party", "#3BE8FF", (0.8, 0, 2.0)),
                                       ("much rich", "#FFE23B", (-0.7, 0, 1.4)), ("very bass", "#7CFF4A", (0.9, 0, 1.1)))):
    cu = bpy.data.curves.new("doge_" + word, "FONT"); cu.body = word; cu.font = COMIC; cu.size = 0.28; cu.align_x = "CENTER"; cu.extrude = 0.01
    o = bpy.data.objects.new("doge_" + word, cu); sc.collection.objects.link(o)
    o.data.materials.append(mat("doge_" + col, col, emit=3.0))
    base = Vector((DOGE_AT[0], DOGE_AT[1], 0)) + Vector(off)   # the words float round DOGE himself
    for f in range(1, N + 1, 15):
        o.location = base + Vector((0.08 * math.sin(f / 13 + k), 0, 0.08 * math.sin(f / 9 + k * 2))); o.keyframe_insert("location", frame=f)
    tc_ = o.constraints.new("TRACK_TO"); tc_.target = cam; tc_.track_axis = "TRACK_Z"; tc_.up_axis = "UP_Y"
# PINK WOJAK at the pool edge, in despair, while everyone else parties
pw = load("pinkwojak", "wojak", LOOKS["pinkwojak"][1]); guests["pinkwojak"] = pw; place(pw, -3.0, -4.3, face(0.2, -1))
pw.bake(M.despair, 1, N, step=2)
# FWOG riding the pizza float, arms up
fw = load("fwog", "pepe", LOOKS["fwog"][1]); guests["fwog"] = fw; place(fw, -3.6, 1.5, face(0.3, -1), z=WZ + 0.12)
fw.ctrl.scale = (0.55, 0.55, 0.55)
fw.bake(M.cheer, 1, N, step=2)
for f in range(1, N + 1, 30):
    fw.ctrl.location.z = WZ + 0.12 + 0.02 * math.sin(f / 13); fw.ctrl.keyframe_insert("location", frame=f)
# laser eyes on the DJ (the Bitcoin meme)
LASER = mat("laser", "#FF1A1A", emit=25.0)
dj = guests["triplet"]
for sx in (-1, 1):
    beam = cyl("laser", (0, 0, 0), 0.007, 2.2, LASER, v=8)
    if not attach(dj, beam, bone="Head", offset=(sx * 0.06, 0.12, 1.2)):
        print("LASER: no head bone on", [b.name for b in dj.rig.data.bones][:6]); break
    for f in range(1, N + 1, 6):
        beam.scale = (1 + 0.4 * random.random(), 1 + 0.4 * random.random(), 1); beam.keyframe_insert("scale", frame=f)

path = [  # frame, camera, look-at: one sweep, slow where the jokes are
    (1, (-17, -21, 11), (0, 2, 1)),
    (110, (-10.5, -10.5, 4.2), (-2.5, 0, 0.4)),
    (170, (-6.4, -5.8, 1.6), (-0.8, -0.4, 0.3)),      # low over the pool: floats, junk, the cannonball
    (235, (-2.0, -6.2, 1.5), (1.5, -0.6, 0.4)),     # a little further back from Pink Wojak and his sign
    (300, (1.0, -11.4, 2.6), (4.0, -5.2, 1.0)),       # the dance floor and the DJ
    (345, (3.6, -10.4, 2.0), (5.0, -4.8, 1.2)),
    (380, (1.0, -1.0, 3.0), (1.0, 5.0, 4.4)),         # up level with the balcony: the Whale and his girls making it rain, the backflip
    (430, (-0.6, -1.2, 1.5), (-1.8, 3.8, 2.6)),
    (480, (-0.6, 3.4, 1.7), (-4.4, 8.6, 0.8)),        # through the doors: the table, LMAO, the window kiss
    (540, (-2.0, 6.4, 1.6), (-5.2, 8.8, 0.7)),
    (580, (2.7, 7.0, 1.8), (4.2, 10.2, 1.0)),         # the kitchen island: KET and CATE at their lines...
    (612, (3.6, 7.25, 1.85), (4.4, 10.2, 1.0)),       # ...held for a good second and a half, creeping along
    (632, (1.8, 6.3, 1.9), (7.0, 1.0, 1.0)),          # turn from the kitchen to look out through the open doors...
    (650, (1.9, 4.3, 2.0), (8.6, 0.0, 1.1)),          # ...and out through them (not through a pane)
    (670, (6.2, 4.4, 2.0), (9.4, -0.6, 1.1)),         # out east, under the pergola
    (700, (6.4, 0.8, 1.6), (9.8, -1.8, 1.0)),         # the smokers
    (735, (8.0, -3.4, 2.0), (10.6, -3.4, 0.7)),       # the bong session, side on, from over the DJ's speaker
    (772, (8.3, -3.35, 1.9), (10.6, -3.4, 0.7)),      # ...and stay with it, creeping in
    (792, (7.4, -2.3, 3.9), (3.0, -7.0, 0.8)),        # then up over the LED wall
    (815, (3.0, -9.4, 2.2), (-1.0, -4.0, 0.8)),       # the conga, the walkers, the drunk on the lawn
    (N, (17, -19, 10), (-1.5, -2.5, 2.2)),            # and up and away, the rocket climbing in the frame
]
for f, p, l in path:
    cam.location = p; cam.keyframe_insert("location", frame=f)
    tgt.location = l; tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"; k.handle_left_type = k.handle_right_type = "AUTO"

# trees the camera flies through or brushes past (dark foliage filling the frame): leave them out of the render
_cf = {fc.array_index: fc for fc in cam.animation_data.action.fcurves if fc.data_path == "location"}
cam_pts = [Vector([_cf[i].evaluate(f) for i in range(3)]) for f in range(1, N + 1, 3)]
def _near(p, r, top):
    return any((Vector((q.x - p.x, q.y - p.y))).length < r and q.z < top + 1.5 for q in cam_pts)
hidden = 0
crowns = {}
for o in bpy.data.objects:
    if o.name.startswith(("frond", "coconut")): crowns.setdefault((round(o.location.x, 1), round(o.location.y, 1)), []).append(o)
for o in bpy.data.objects:
    if o.name.startswith("palm_trunk"):
        top = o.data.splines[0].bezier_points[-1].co
        if _near(top, 3.4, top.z):
            o.hide_render = True; hidden += 1
            for (cx, cy), parts in crowns.items():
                if abs(cx - top.x) < 0.3 and abs(cy - top.y) < 0.3:
                    for p_ in parts: p_.hide_render = True
    elif o.name.endswith("_inst") and o.instance_collection and any(k in o.name for k in ("tree", "shrub", "fern", "potted", "planter")):   # foliage only
        sc_ = o.scale.x; big = "tree" in o.name
        if _near(o.location, (5.5 if big else 3.5) * sc_, o.location.z + (9.0 if big else 3.0) * sc_): o.hide_render = True; hidden += 1
# and, for the aerial opening and closing, foliage standing in the near half of the view of the house
_tf = {fc.array_index: fc for fc in tgt.animation_data.action.fcurves if fc.data_path == "location"}
views = [(Vector([_cf[i].evaluate(f) for i in range(3)]), Vector([_tf[i].evaluate(f) for i in range(3)])) for f in list(range(1, 70, 6)) + list(range(830, N + 1, 6))]
def _blocks(p, r):
    """Foliage in the foreground of the frame: inside the 24 mm frustum (widened by its crown) and within 15 m."""
    for a, b in views:
        fw = (b - a).normalized(); rt = fw.cross(Vector((0, 0, 1))).normalized(); up = rt.cross(fw)
        d = p - a; z = d.dot(fw)
        if 0.5 < z < 15.0 and abs(d.dot(rt)) / z < 0.75 + r / z and abs(d.dot(up)) / z < 0.42 + r / z: return True
    return False
for o in bpy.data.objects:
    if o.hide_render: continue
    if o.name.startswith("palm_trunk"):
        top = o.data.splines[0].bezier_points[-1].co
        if _blocks(Vector(top) - Vector((0, 0, 1.0)), 3.0):
            o.hide_render = True; hidden += 1
            for (cx, cy), parts in crowns.items():
                if abs(cx - top.x) < 0.3 and abs(cy - top.y) < 0.3:
                    for p_ in parts: p_.hide_render = True
    elif o.name.endswith("_inst") and o.instance_collection and any(k in o.name for k in ("tree", "shrub", "fern", "potted", "planter")):
        h_ = (6.0 if "tree" in o.name else 1.2) * o.scale.x
        if _blocks(o.location + Vector((0, 0, h_)), (7.0 if "tree" in o.name else 2.0) * o.scale.x): o.hide_render = True; hidden += 1   # (a jacaranda crown is wide)
print("trees cleared from the camera's path:", hidden)

# TO THE MOON: the inflatable rocket on the lawn really launches at the end, into the closing aerial
F_IGN, F_LIFT = 818, 838   # while the closing aerial has the rocket in shot
rk = bpy.data.objects.get("rocket")
if rk:
    base = rk.location.copy()
    flame = next((o for o in rk.children if o.name.startswith("Cone") and o.active_material and o.active_material.name == "flame"), None)
    glow = bpy.data.objects.new("rocket_glow", bpy.data.lights.new("rocket_glow", "POINT")); sc.collection.objects.link(glow)
    glow.parent = rk; glow.location = (0, 0, -0.35); glow.data.color = (1.0, 0.55, 0.2); glow.data.shadow_soft_size = 0.4
    glow.data.energy = 0.0; glow.data.keyframe_insert("energy", frame=F_IGN)
    for f in range(F_IGN, N + 1, 2):   # ignition flicker, then full thrust
        k = min(1.0, (f - F_IGN) / (F_LIFT - F_IGN))
        glow.data.energy = (1500 + 3500 * k) * random.uniform(0.75, 1.15); glow.data.keyframe_insert("energy", frame=f)
        if flame:
            flame.scale = (1 + 0.5 * k, 1 + 0.5 * k, (1 + 3.0 * k) * random.uniform(0.85, 1.15)); flame.keyframe_insert("scale", frame=f)
    if flame:
        flame.scale = (1, 1, 1); flame.keyframe_insert("scale", frame=F_IGN - 1)
    rk.location = base; rk.keyframe_insert("location", frame=F_LIFT)
    rk.keyframe_insert("location", frame=1)
    for f in range(F_LIFT + 2, N + 1, 2):   # lift-off: slow, then faster and faster, a little wobble
        t = (f - F_LIFT) / FPS
        rk.location = base + Vector((0.15 * math.sin(t * 3.0) * t, 0.1 * math.cos(t * 2.3) * t, 0.5 * 4.0 * t * t))
        rk.keyframe_insert("location", frame=f)
    for fc in rk.animation_data.action.fcurves:
        if fc.data_path == "location":
            for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
    # the launch cloud billowing out over the grass, and a smoke trail left hanging in the air
    for j in range(22):
        a = j / 22 * math.tau; f0 = F_IGN + 4 + int(j * 0.8)
        s_ = sphere("launch_cloud", (0, 0, 0), 0.25, SMOKE, seg=20)
        s_.location = base + Vector((0, 0, 0.2)); s_.scale = (0.001,) * 3
        s_.keyframe_insert("location", frame=1); s_.keyframe_insert("scale", frame=1); s_.keyframe_insert("scale", frame=f0 - 1); s_.keyframe_insert("location", frame=f0 - 1)
        s_.scale = (1.0,) * 3; s_.keyframe_insert("scale", frame=f0 + 3)
        s_.location = base + Vector((math.cos(a) * random.uniform(1.6, 2.6), math.sin(a) * random.uniform(1.6, 2.6), random.uniform(0.3, 0.9)))
        s_.scale = (random.uniform(1.8, 2.6),) * 3; s_.keyframe_insert("location", frame=f0 + 60); s_.keyframe_insert("scale", frame=f0 + 60)
    for f in range(F_LIFT, N + 1, 2):
        t = (f - F_LIFT) / FPS; p = base + Vector((0.15 * math.sin(t * 3.0) * t, 0.1 * math.cos(t * 2.3) * t, 0.5 * 4.0 * t * t - 0.3))
        s_ = sphere("trail", (0, 0, 0), 0.22, SMOKE, seg=16)
        s_.location = p; s_.scale = (0.001,) * 3; s_.keyframe_insert("scale", frame=1); s_.keyframe_insert("scale", frame=f - 1)
        s_.scale = (1.0,) * 3; s_.keyframe_insert("scale", frame=f + 1)
        s_.location = p + Vector((random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), -0.2)); s_.scale = (2.6,) * 3
        s_.keyframe_insert("scale", frame=min(N + 40, f + 50)); s_.keyframe_insert("location", frame=min(N + 40, f + 50))
    print("rocket launch at", F_LIFT, "flame", flame.name if flame else None)

# ------------------------------------------------------------------------------------------------ render
r = sc.render
r.engine = "CYCLES"   # faster than EEVEE on this machine's software GPU, and better glass and water
sc.cycles.device = "CPU"; sc.cycles.samples = A("--samples", 12, int); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.transparent_max_bounces = 12; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
r.use_persistent_data = True
r.resolution_x = A("--w", 1280, int); r.resolution_y = A("--h", 720, int); r.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"; sc.view_settings.exposure = 0.0
r.use_motion_blur = False
r.image_settings.file_format = "PNG"
sc.use_nodes = True
nt = sc.node_tree; nt.nodes.clear()
rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare"); co = nt.nodes.new("CompositorNodeComposite")
gl.glare_type = "FOG_GLOW"; gl.threshold = 1.0; gl.size = 7; gl.mix = -0.6
nt.links.new(rl.outputs["Image"], gl.inputs["Image"]); nt.links.new(gl.outputs["Image"], co.inputs["Image"])
if "--save" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(A("--save")))
if "--stills" in argv:
    fr = [int(x) for x in argv[argv.index("--stills") + 1].split(",")]; od = argv[argv.index("--stills") + 2]; os.makedirs(od, exist_ok=True)
    for f in fr:
        sc.frame_set(f); r.filepath = os.path.join(od, f"party_{f:04d}.png"); bpy.ops.render.render(write_still=True)
if "--render" in argv:
    r.use_overwrite = False; r.use_placeholder = True
    r.filepath = os.path.join(os.path.abspath(A("--render")), "f_"); bpy.ops.render.render(animation=True)
