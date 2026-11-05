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

argv = sys.argv[sys.argv.index("--") + 1:]
A = lambda k, d=None, t=str: t(argv[argv.index(k) + 1]) if k in argv else d
MODELS = os.path.abspath(A("--models")); PH = os.path.abspath(A("--ph"))
N = A("--frames", 720, int); FPS = 30
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
def obj_mat(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o
def box(name, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
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
def light(name, kind, loc, energy, color="#FFFFFF", size=0.2, rot=(0, 0, 0), spot=None):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); sc.collection.objects.link(L)
    L.location = loc; L.rotation_euler = rot; L.data.energy = energy; L.data.color = srgb(color)[:3]
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
bg = wn.nodes["Background"]; bg.inputs["Strength"].default_value = 0.9
wn.links.new(env.outputs["Color"], bg.inputs["Color"])

# ------------------------------------------------------------------------------------------------ the villa
DECK = mat("deck", "#CFC6B8", rough=0.6)
LAWN = mat("lawn", "#1F3A1C", rough=0.9)
WALL = mat("wall", "#EDEBE6", rough=0.55)
DARK = mat("frame", "#1B1B1F", rough=0.4, metal=0.5)
WOOD = mat("wood", "#7A4E2D", rough=0.5)
GLASS = mat("glass", "#9FC6D8", rough=0.02, alpha=0.16)
FLOOR = mat("floor", "#BDB7AE", rough=0.2)
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
for i in range(6):   # the pool's underwater lights
    x = -PX + 1 + i * (2 * PX - 2) / 5
    light(f"poolL{i}", "POINT", (x, -PY + 0.3, -0.9), 180, "#4FD8FF", 0.3)
    light(f"poolR{i}", "POINT", (x, PY - 0.3, -0.9), 180, "#4FD8FF", 0.3)

# the house: ground floor (glass front with the doors slid open), upper floor cantilevered over the deck, flat roofs
GY0, GY1 = 5.0, 13.0
box("gf_floor", -9.5, 9.5, GY0, GY1, -0.3, 0.02, FLOOR)
box("gf_back", -9.5, 9.5, GY1 - 0.3, GY1, 0, 3.4, WALL)
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
for x in range(-6, 10, 2):   # warm wall-washers under the eaves
    light(f"eave{x}", "SPOT", (x, GY0 - 0.4, 3.35), 120, "#FFC98A", 0.1, rot=(0, 0, 0), spot=math.radians(80))
# inside: warm ceiling light, a sofa and the coffee table, the kitchen island bar with stools, plants, pendant lamps
for (x, y) in ((-6, 8), (-2, 10.5), (3, 8), (6.5, 10.5)):
    light(f"room{x}", "AREA", (x, y, 3.3), 260, "#FFD3A0", 2.5, rot=(0, 0, 0))
import_gltf(os.path.join(PH, "sofa_03/sofa_03.gltf"), (-5.2, 10.6, 0.02), math.pi, 1.0)
import_gltf(os.path.join(PH, "modern_coffee_table_01/modern_coffee_table_01.gltf"), (-5.2, 8.9, 0.02), 0, 1.0)
box("island", 2.2, 6.4, 9.0, 10.0, 0.02, 1.0, mat("island", "#2A2A30", rough=0.3, metal=0.2), bevel=0.02)
box("island_top", 2.1, 6.5, 8.95, 10.05, 1.0, 1.06, mat("marble", "#F2EFEA", rough=0.15), bevel=0.01)
for i, x in enumerate((2.6, 3.6, 4.6, 5.6)):
    import_gltf(os.path.join(PH, "bar_chair_round_01/bar_chair_round_01.gltf"), (x, 8.45, 0.02), 0, 1.0)
for i, (x, col) in enumerate(((2.5, "#3B7A2E"), (2.75, "#8A2A1E"), (3.0, "#C8A93A"), (3.25, "#3A5A8A"), (6.0, "#6A2A6A"), (6.2, "#2A6A5A"))):
    cyl(f"bottle{i}", (x, 9.6, 1.22), 0.045, 0.32, mat(f"btl{i}", col, rough=0.05, alpha=0.7, emit=0.3))
for (x, y, n) in ((-8.6, 12.0, "potted_plant_01"), (8.4, 12.0, "potted_plant_02"), (-8.4, 5.6, "potted_plant_02"), (8.6, 5.6, "potted_plant_01")):
    import_gltf(os.path.join(PH, f"{n}/{n}.gltf"), (x, y, 0.02), 0, 1.4)
for x in (2.8, 4.3, 5.8):
    import_gltf(os.path.join(PH, "modern_ceiling_lamp_01/modern_ceiling_lamp_01.gltf"), (x, 9.5, 2.3), 0, 1.0)
    light(f"pend{x}", "POINT", (x, 9.5, 2.1), 60, "#FFC070", 0.1)

# palms: a leaning trunk of rings and a crown of drooping fronds
TRUNK = mat("trunk", "#6B5038", rough=0.9); FROND = mat("frond", "#2E6B2A", rough=0.7)
def palm(x, y, h=6.0, lean=(0.4, 0.2)):
    top = Vector((x + lean[0], y + lean[1], h))
    for i in range(12):
        k = i / 12; p = Vector((x, y, 0)).lerp(top, k) + Vector((lean[0] * 0.3 * math.sin(k * math.pi), 0, 0))
        cyl("trunk", p, 0.2 - 0.06 * k, h / 12 + 0.02, TRUNK, v=10)
    for j in range(9):
        a = j / 9 * math.tau
        bpy.ops.mesh.primitive_plane_add(size=1, location=top)
        f = bpy.context.active_object; f.scale = (2.6, 0.5, 1); bpy.ops.object.transform_apply(scale=True)
        f.data.vertices[0].co.z -= 0.0; obj_mat(f, FROND)
        bd = f.modifiers.new("bend", "SIMPLE_DEFORM"); bd.deform_method = "BEND"; bd.deform_axis = "Y"; bd.angle = math.radians(-60)
        f.rotation_euler = (0, math.radians(-12), a); f.location = top + Vector((math.cos(a) * 1.25, math.sin(a) * 1.25, -0.1))
    light(f"palmup{x}", "SPOT", (x + 0.6, y - 0.6, 0.1), 300, "#FFB060", 0.1, rot=(math.radians(10), 0, 0), spot=math.radians(35))
for (x, y, l) in ((-11, 3.5, (0.6, -0.3)), (-10.5, -6.5, (0.5, 0.4)), (11, 3.8, (-0.6, -0.2)), (11.2, -6.0, (-0.5, 0.3)), (-12.5, -1.5, (0.3, 0.1)), (12.6, -1.2, (-0.3, 0.1))):
    palm(x, y, 6.2 + random.uniform(-0.6, 0.8), l)

# loungers and umbrellas on the south deck, string lights over it, a DJ booth, coloured party spots
for i, x in enumerate((-9.5, -8.3)):
    box("lounger", x - 0.35, x + 0.35, -8.5, -6.6, 0.0, 0.35, mat("lounger", "#F7F7F2", rough=0.5), bevel=0.04)
BULB = mat("bulb", "#FFD58A", emit=8.0)
for row, y in enumerate((-3.5, -7.5)):
    for i in range(24):
        x = -10 + i * (20 / 23); sag = 0.55 * math.sin(math.pi * i / 23)
        sphere("bulb", (x, y, 3.2 - sag), 0.05, BULB, seg=8)
    for x in (-10, 10):
        cyl("pole", (x, y, 1.6), 0.04, 3.2, DARK, v=8)
    for x in (-6, 0, 6):
        light(f"string{row}{x}", "POINT", (x, y, 2.7), 90, "#FFC27A", 0.3)
box("dj_booth", 7.0, 8.2, -6.0, -3.6, 0.0, 1.05, mat("booth", "#111115", rough=0.3, metal=0.3), bevel=0.03)
box("dj_led", 6.98, 7.0, -5.9, -3.7, 0.15, 0.95, mat("led", "#FF2BD6", emit=6.0))
for y in (-6.4, -3.2):
    box("speaker", 7.3, 8.1, y - 0.35, y + 0.35, 0.0, 1.6, mat("spk", "#18181C", rough=0.5), bevel=0.03)
    cyl("cone", (7.28, y, 1.05), 0.22, 0.04, mat("cone", "#333338", rough=0.3), rot=(0, math.pi / 2, 0))
for i, (x, col) in enumerate(((-2, "#FF2BD6"), (2, "#2BE0FF"), (5, "#FFE02B"), (-6, "#8A2BFF"))):
    sp = light(f"party{i}", "SPOT", (x, -9.5, 5.5), 1500, col, 0.2, spot=math.radians(28))
    for f in range(1, N + 1, 30):
        sp.rotation_euler = (math.radians(45 + 12 * math.sin(f / 23 + i)), math.radians(18 * math.sin(f / 31 + i * 2)), 0)
        sp.keyframe_insert("rotation_euler", frame=f)
# floats in the pool
bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.2, location=(4.8, 1.4, WZ + 0.08))
donut = obj_mat(bpy.context.active_object, mat("donut", "#FF6FB5", rough=0.25))
bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.22, location=(-4.2, -1.2, WZ + 0.08))
obj_mat(bpy.context.active_object, mat("ring", "#FFD23A", rough=0.25))
# the flamingo: body, neck and head
FL = mat("flamingo", "#FF5A9A", rough=0.3)
sphere("fl_body", (-1.8, 1.6, WZ + 0.25), 0.45, FL).scale = (1.3, 0.8, 0.55)
cyl("fl_neck", (-1.3, 1.6, WZ + 0.8), 0.07, 0.8, FL, rot=(0, math.radians(15), 0))
sphere("fl_head", (-1.2, 1.6, WZ + 1.2), 0.13, FL)
cyl("fl_beak", (-1.05, 1.6, WZ + 1.18), 0.04, 0.18, mat("beak", "#222222"), rot=(0, math.radians(70), 0))

# ------------------------------------------------------------------------------------------------ the guests
CUP = mat("cup", "#D8232A", rough=0.35); CIG = mat("cig", "#F5F2EA", rough=0.6); EMBER = mat("ember", "#FF6A1A", emit=12.0)
SMOKE = mat("smoke", "#E8E8EE", rough=1.0, alpha=0.28)
NOTE = mat("note", "#7DBF6A", rough=0.6); POWDER = mat("powder", "#FFFFFF", rough=0.8, emit=0.3)

def load(cid):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, cid + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    for o in new:
        if o.type == "MESH" and o.parent is None: bpy.data.objects.remove(o)   # the game's selection sphere
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
    if not c.ik:
        bpy.data.objects.remove(obj); return None
    cn = obj.constraints.new("CHILD_OF"); cn.target = c.rig; cn.subtarget = "mixamorig:" + bone
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
        s = sphere("puff", (0, 0, 0), 0.08, SMOKE, seg=8); s.parent = c.ctrl
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

# the DJ, and the dance floor in front of the booth
guest("triplet", 7.6, -4.8, face(-1, 0), M.dance_shuffle, phase=0.0)   # the DJ
dancers = ["giga", "neet", "alon", "mitch", "mensa", "thisisfine", "toshi", "goat", "bome", "slerf"]
spots = [(1.2, -4.0), (2.6, -4.4), (4.0, -3.9), (5.3, -4.6), (1.6, -5.6), (3.1, -6.0), (4.6, -5.5), (2.2, -7.1), (3.8, -7.3), (5.4, -6.8)]
for i, (cid, (x, y)) in enumerate(zip(dancers, spots)):
    mv = M.DANCES[i % len(M.DANCES)]
    guest(cid, x + random.uniform(-0.15, 0.15), y, face(7.6 - x, -4.8 - y) + random.uniform(-0.6, 0.6), mv, phase=random.random())

# in the pool: treading water (sunk to the shoulders), one on the donut
for cid, (x, y) in (("moodeng", (-3.0, 0.8)), ("zcat", (1.5, 1.2)), ("cupsey", (3.4, -0.9)), ("pudgy", (-0.6, -1.1)), ("nyancat", (4.8, 1.4))):
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
    if not c.ik: c.play("run", 1)
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
cannonball("popcat", -1.6, 196)
cannonball("swordcat", 0.9, 226)

# poolside drinkers, chatting, red cups in hand
group = [("chillguy", -4.4, -4.3), ("ket", -3.5, -5.1), ("cate", -5.2, -5.2)]
centre = Vector((-4.4, -4.9, 1.2))
for i, (cid, x, y) in enumerate(group):
    c = load(cid); guests[cid] = c; place(c, x, y, face(centre.x - x, centre.y - y))
    c.bake(M.hold_cup, 1, N, step=2, phase=i * 0.37, toward=to_local(c, centre + Vector((0, 0, 0.3))))
    attach(c, cyl("cup", (0, 0, 0), 0.045, 0.13, CUP), offset=(0, 0.07, 0.04), rot=(math.pi / 2, 0, 0))
# chatters by the deck's west side
group = [("bonk", -1.2, -6.4), ("chillhouse", -0.3, -7.2), ("pnut", -2.0, -7.3)]
centre = Vector((-1.15, -7.0, 1.2))
for i, (cid, x, y) in enumerate(group):
    c = load(cid); guests[cid] = c; place(c, x, y, face(centre.x - x, centre.y - y))
    c.bake(M.chat, 1, N, step=2, phase=i * 0.31, toward=to_local(c, centre))

# the kitchen bar: drinks
for i, (cid, x) in enumerate((("jeanphil", 2.9), ("useless", 4.1), ("dope", 5.3))):
    c = load(cid); guests[cid] = c; place(c, x, 8.25, face(0.3 * (i - 1), -1))
    c.bake(M.hold_cup if i != 1 else M.chat, 1, N, step=2, phase=i * 0.29)
    if i != 1:
        attach(c, cyl("cup", (0, 0, 0), 0.045, 0.13, mat("cup2", "#F2C14E", rough=0.2, alpha=0.8)), offset=(0, 0.07, 0.04), rot=(math.pi / 2, 0, 0))

# the two couples
def couple(a, b, x, y, ang):
    ca, cb = load(a), load(b); guests[a] = ca; guests[b] = cb
    dx, dy = math.sin(ang), -math.cos(ang)
    gap = 0.17 + 0.5 * (ca.arm + cb.arm) * 0.25
    place(ca, x - dx * gap, y - dy * gap, face(dx, dy)); place(cb, x + dx * gap, y + dy * gap, face(-dx, -dy))
    ca.bake(M.kiss, 1, N, step=2, partner_head=look_at(ca, cb))
    cb.bake(M.kiss, 1, N, step=2, partner_head=look_at(cb, ca), phase=0.5)
couple("pepe", "pippin", 7.4, 0.4, math.pi / 2)      # at the pool's east end
couple("troll", "michi", -1.6, 7.2, math.pi / 2)     # inside, by the window

if not CLEAN:
    # the coffee table in the living room: two leaning over it, rolled notes in hand
    for cid, x, rot in (("farter", -5.75, face(0.3, 1)), ("lmao", -4.65, face(-0.3, 1))):
        c = load(cid); guests[cid] = c; place(c, x, 8.25, rot)
        c.bake(M.lean_over_table, 1, N, step=2, table_z=0.42, phase=0.3 if cid == "lmao" else 0.0)
        attach(c, cyl("note", (0, 0, 0), 0.012, 0.12, NOTE), offset=(0, 0.05, 0.02), rot=(math.pi / 2, 0, 0))
    for i in range(3):
        box("line", -5.55 + i * 0.12, -5.52 + i * 0.12, 8.75, 9.0, 0.425, 0.432, POWDER)
    # smokers on the east deck
    for i, (cid, x, y, tx, ty) in enumerate((("whale", 9.8, 1.6, 9.0, 2.3), ("walter", 9.0, 2.3, 9.8, 1.6), ("floki", 9.6, -1.0, 8.8, -1.6), ("baton", 8.8, -1.6, 9.6, -1.0))):
        c = load(cid); guests[cid] = c; place(c, x, y, face(tx - x, ty - y))
        ph = i * 0.23
        c.bake(M.smoke, 1, N, step=2, period=4.0, phase=ph, toward=to_local(c, Vector((tx, ty, 1.3))))
        cig = attach(c, cyl("cig", (0, 0, 0), 0.008, 0.09, CIG), offset=(0.02, 0.07, 0.03), rot=(0, 0, math.pi / 2))
        ember = attach(c, sphere("ember", (0, 0, 0), 0.011, EMBER, seg=8), offset=(0.065, 0.07, 0.03))
        puff_loop(c, 4.0, ph, c.headp + Vector((0, -0.18, -0.02)))
    # the bong, on two lounge chairs by the east palms
    for cid, x, y, rot in (("wojak", 10.6, -4.2, face(0, 1)), ("apu", 10.6, -2.6, face(0, -1))):
        import_gltf(os.path.join(PH, "mid_century_lounge_chair/mid_century_lounge_chair.gltf"), (x, y + (0.25 if rot == face(0, 1) else -0.25), 0.0), rot + math.pi, 1.0)
        c = load(cid); guests[cid] = c; place(c, x, y, rot)
        c.bake(M.sit_bong, 1, N, step=2, phase=0.0 if cid == "wojak" else 0.5)
    BONG = mat("bong", "#7FE0C8", rough=0.02, alpha=0.45, emit=0.4)
    cyl("bong", (10.6, -3.4, 0.35), 0.06, 0.7, BONG); sphere("bong_base", (10.6, -3.4, 0.08), 0.12, BONG)
    cyl("bong_stem", (10.68, -3.4, 0.25), 0.012, 0.22, BONG, rot=(0, math.radians(40), 0))
    for k in range(10):   # a cloud drifting up between them
        s = sphere("cloud", (10.6, -3.4, 1.0), 0.15, SMOKE, seg=8)
        for f in range(1, N + 1, 40):
            ph = (f / 40 + k * 0.1) % 1.0
            s.location = (10.6 + 0.4 * math.sin(k + f / 50), -3.4 + 0.3 * math.cos(k * 2 + f / 60), 0.9 + 1.4 * ph)
            s.scale = (1 + 3 * ph,) * 3; s.keyframe_insert("location", frame=f); s.keyframe_insert("scale", frame=f)
else:
    for cid, x in (("farter", -5.6), ("lmao", -4.8)):
        guest(cid, x, 8.3, face(0, -1), M.cheer, phase=random.random())
    for i, cid in enumerate(("whale", "walter", "floki", "baton", "wojak", "apu")):
        guest(cid, 9.2 + (i % 2) * 0.8, 2.0 - i * 1.2, face(-1, -0.3), M.DANCES[i % 5], phase=random.random())

print("guests:", len(guests))

# ------------------------------------------------------------------------------------------------ the camera: one sweep
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 24; cam.data.clip_end = 300
tgt = bpy.data.objects.new("CamTarget", None); sc.collection.objects.link(tgt)
tcn = cam.constraints.new("TRACK_TO"); tcn.target = tgt; tcn.track_axis = "TRACK_NEGATIVE_Z"; tcn.up_axis = "UP_Y"
path = [  # frame, camera, look-at
    (1, (-15, -19, 10), (0, 2, 1)),
    (110, (-9.5, -9.5, 3.8), (-2.5, 0, 0.4)),
    (200, (-3.6, -4.4, 1.0), (0.5, -0.6, 0.3)),      # low over the pool: the cannonballs
    (290, (2.6, -9.2, 1.9), (4.2, -5.0, 1.1)),       # the dance floor and the DJ
    (370, (0.4, -1.2, 2.0), (0.0, 6.0, 1.2)),        # over the pool to the open doors
    (450, (-1.2, 5.6, 1.6), (-5.0, 8.8, 0.7)),       # inside: the table, the couple at the window
    (520, (1.6, 6.6, 1.7), (4.2, 8.6, 1.2)),         # the bar
    (610, (7.0, 3.6, 2.0), (9.6, -0.6, 1.0)),        # out east: the smokers, the couple at the pool's end
    (680, (8.6, -6.6, 2.4), (10.6, -3.4, 0.8)),      # the lounge chairs
    (N, (17, -16, 9), (1, 0, 1)),                    # and up and away
]
for f, p, l in path:
    cam.location = p; cam.keyframe_insert("location", frame=f)
    tgt.location = l; tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"; k.handle_left_type = k.handle_right_type = "AUTO"

# ------------------------------------------------------------------------------------------------ render
r = sc.render
r.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.taa_render_samples = A("--samples", 16, int)
sc.eevee.use_shadows = True
sc.eevee.shadow_ray_count = 1; sc.eevee.shadow_step_count = 4
r.resolution_x = A("--w", 1280, int); r.resolution_y = A("--h", 720, int); r.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"; sc.view_settings.exposure = 0.3
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
