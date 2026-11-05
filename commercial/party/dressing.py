# Set dressing for party.py (run inside its namespace): architecture, the kitchen, and the mess.
# Uses party.py's helpers: box, cyl, sphere, mat, light, obj_mat, import_gltf, sc, N, FPS, PX, PY, WZ, GY0, GY1, PH.
import bpy, math, random, os
from mathutils import Vector

rng = random.Random(23)
STEEL = mat("steel", "#C9CCD1", rough=0.25, metal=0.9)
BLACK = mat("black_metal", "#141416", rough=0.35, metal=0.6)
OAK = mat("oak", "#A0703F", rough=0.45)
CAB = mat("cabinet", "#2B2D33", rough=0.35)
HEDGE = mat("hedge", "#24451F", rough=0.95)

def stone_mat():
    m = bpy.data.materials.new("stone"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    v = nt.nodes.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 3.5
    r = nt.nodes.new("ShaderNodeValToRGB"); r.color_ramp.elements[0].color = (0.22, 0.2, 0.18, 1); r.color_ramp.elements[1].color = (0.55, 0.5, 0.45, 1)
    nt.links.new(v.outputs["Distance"], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    nt.links.new(v.outputs["Distance"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85
    return m

# ------------------------------------------------------------------------------------------------ architecture
# steel columns under the cantilevered upper floor and the balcony
for x in (-6.2, -1.0, 4.2, 9.2):
    box("column", x - 0.09, x + 0.09, 4.42, 4.6, 0.0, 3.7, BLACK)
# a stone-clad wing on the west, a chimney through the roof
STONE = stone_mat()
box("stone_wing", -12.5, -9.5, 7.0, 13.0, 0.0, 4.2, STONE)
box("stone_cap", -12.6, -9.4, 6.9, 13.1, 4.2, 4.35, WALL)
box("chimney", -11.4, -10.6, 11.0, 12.2, 4.2, 8.2, STONE)
# a roof parapet and a planted roof edge
for (x0, x1, y0, y1) in ((-7.2, 10.2, 5.6, 5.75), (-7.2, 10.2, 13.45, 13.6), (-7.2, -7.05, 5.6, 13.6), (10.05, 10.2, 5.6, 13.6)):
    box("parapet", x0, x1, y0, y1, 7.15, 7.55, WALL)
# a pergola of oak slats over the east deck, on four posts
for (x, y) in ((8.2, -2.6), (12.0, -2.6), (8.2, 3.2), (12.0, 3.2)):
    box("post", x - 0.08, x + 0.08, y - 0.08, y + 0.08, 0.0, 2.8, OAK)
for i in range(14):
    y = -2.6 + i * (5.8 / 13)
    box("slat", 8.0, 12.2, y - 0.04, y + 0.04, 2.8, 2.95, OAK)
# steps down from the deck to the lawn, hedges along the deck, a fire pit on the lawn
for i in range(3):
    box("step", -4, 4, -9.0 - 0.4 * (i + 1), -9.0 - 0.4 * i, -0.3 - 0.1 * (i + 1), -0.3 - 0.1 * i + 0.1, DECK)
for x0 in (-12, 5):
    box("hedge", x0, x0 + 7, -9.6, -9.0, -0.3, 0.6, HEDGE, bevel=0.15)
box("firepit", -9.4, -7.4, -12.6, -10.6, -0.3, 0.25, STONE, bevel=0.05)
FLAME = mat("flame", "#FF8A1E", emit=14.0, emit_color="#FF7A10")
for i in range(7):
    a = i / 7 * math.tau
    fl = sphere("flame", (-8.4 + 0.35 * math.cos(a), -11.6 + 0.35 * math.sin(a), 0.45), 0.16, FLAME, seg=8)
    for f in range(1, N + 1, 4):   # flicker
        fl.scale = (0.8 + 0.2 * math.sin(f * 0.7 + i), 0.8 + 0.2 * math.cos(f * 0.9 + i), 1.4 + 0.8 * abs(math.sin(f * 0.5 + i * 1.3)))
        fl.keyframe_insert("scale", frame=f)
light("fire", "POINT", (-8.4, -11.6, 1.0), 420, "#FF8A30", 0.4)
# garden lights along the lawn
for i in range(10):
    x = -11 + i * 2.4
    cyl("bollard", (x, -13.2, -0.05), 0.06, 0.5, BLACK, v=8); sphere("bollard_light", (x, -13.2, 0.22), 0.05, mat("bollard_led", "#FFE2A8", emit=10.0), seg=8)

# ------------------------------------------------------------------------------------------------ inside: the kitchen, the living room
# kitchen along the back wall: base cabinets, worktop, sink, a tall fridge, upper cabinets, a hood
box("base_cab", 1.4, 8.0, GY1 - 1.0, GY1 - 0.32, 0.02, 0.9, CAB, bevel=0.01)
box("worktop", 1.35, 8.05, GY1 - 1.05, GY1 - 0.3, 0.9, 0.95, mat("marble", "#F2EFEA", rough=0.15), bevel=0.005)
box("sink", 3.0, 3.8, GY1 - 0.85, GY1 - 0.45, 0.88, 0.955, STEEL)
cyl("tap", (3.4, GY1 - 0.4, 1.12), 0.015, 0.34, STEEL, v=10)
box("fridge", 8.05, 9.15, GY1 - 0.95, GY1 - 0.32, 0.02, 2.3, STEEL, bevel=0.02)
box("fridge_line", 8.04, 9.16, GY1 - 0.96, GY1 - 0.95, 1.4, 1.42, BLACK)
box("upper_cab", 1.4, 5.0, GY1 - 0.65, GY1 - 0.32, 1.65, 2.45, CAB, bevel=0.01)
box("upper_cab2", 6.6, 8.0, GY1 - 0.65, GY1 - 0.32, 1.65, 2.45, CAB, bevel=0.01)
box("hood", 5.3, 6.3, GY1 - 0.85, GY1 - 0.32, 1.9, 2.4, STEEL, bevel=0.01)
box("hob", 5.3, 6.3, GY1 - 0.95, GY1 - 0.4, 0.95, 0.97, BLACK)
box("cab_led", 1.4, 8.0, GY1 - 0.66, GY1 - 0.62, 1.62, 1.64, mat("cab_led", "#FFD7A0", emit=8.0))
# waterfall ends on the island
box("island_end_w", 2.05, 2.15, 8.95, 10.05, 0.02, 1.06, mat("marble", "#F2EFEA"))
box("island_end_e", 6.45, 6.55, 8.95, 10.05, 0.02, 1.06, mat("marble", "#F2EFEA"))
# ceiling beams, a staircase up the west side, a dining table, framed card art, a floor lamp, a WAGMI neon
for i in range(9):
    x = -9 + i * 2.25
    box("beam", x - 0.07, x + 0.07, GY0 - 0.5, GY1, 3.22, 3.4, OAK)
for i in range(14):
    box("stair", -9.2, -8.0, 7.2 + i * 0.32, 7.52 + i * 0.32, 0.0, 0.22 * (i + 1), OAK)
box("stair_glass", -8.0, -7.96, 7.2, 11.7, 0.6, 3.4, GLASS)
box("dining", -2.6, -0.2, 10.4, 11.5, 0.72, 0.77, OAK, bevel=0.01)
for x in (-2.4, -0.4):
    for y in (10.5, 11.4):
        box("dleg", x - 0.04, x + 0.04, y - 0.04, y + 0.04, 0.02, 0.72, BLACK)
CARDS = os.path.join(os.path.dirname(MODELS), "cards")
for (cid, x) in (("pepe", -8.0), ("giga", -2.2), ("popcat", 0.4)):
    p = os.path.join(CARDS, cid + ".png")
    if not os.path.exists(p): continue
    box("frame", x - 0.62, x + 0.62, GY1 - 0.34, GY1 - 0.3, 1.25, 2.75, mat("goldframe", "#C9A23A", rough=0.3, metal=0.8))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, GY1 - 0.35, 2.0), rotation=(math.pi / 2, 0, 0))
    pl = bpy.context.active_object; pl.scale = (1.1, 1.375, 1)
    m = bpy.data.materials.new("art_" + cid); m.use_nodes = True; nt = m.node_tree
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(p)
    nt.links.new(tx.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.links.new(tx.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Emission Color"])
    nt.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.4
    obj_mat(pl, m)
cyl("lamp_pole", (-2.6, 12.0, 0.8), 0.02, 1.6, BLACK, v=8); sphere("lamp_shade", (-2.6, 12.0, 1.65), 0.2, mat("lampshade", "#FFE7C2", emit=4.0))
def neon(text, loc, rot, size, color, strength=10.0):
    cu = bpy.data.curves.new("neon", "FONT"); cu.body = text; cu.size = size; cu.align_x = "CENTER"; cu.extrude = 0.02
    o = bpy.data.objects.new("neon_" + text, cu); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; o.data.materials.append(mat("neon_" + color, color, emit=strength))
    return o
neon("WAGMI", (-8.6, 9.6, 2.2), (math.pi / 2, 0, math.pi / 2), 0.55, "#FF2BD6")
neon("MEME ROYALE PARTY", (1.5, GY0 - 0.62, 3.45), (math.pi / 2, 0, 0), 0.42, "#FFC52E", 12.0)

# ------------------------------------------------------------------------------------------------ the mess
def scatter(n, region, make, z=0.0, avoid_pool=True):
    out = []
    x0, x1, y0, y1 = region
    while len(out) < n:
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if avoid_pool and -PX - 0.5 < x < PX + 0.5 and -PY - 0.5 < y < PY + 0.5: continue
        out.append(make(x, y, z))
    return out
cup_mesh = None
def cup(x, y, z):
    global cup_mesh
    if cup_mesh is None:
        cup_mesh = cyl("cup_trash", (0, 0, 0), 0.045, 0.12, CUP).data
    o = bpy.data.objects.new("cup", cup_mesh); sc.collection.objects.link(o)
    tipped = rng.random() < 0.7
    o.location = (x, y, z + (0.045 if tipped else 0.06)); o.rotation_euler = (math.pi / 2 if tipped else 0, 0, rng.uniform(0, math.tau))
    return o
CAN_M = [mat(f"can{i}", c, rough=0.25, metal=0.8) for i, c in enumerate(("#C0C4CC", "#D23A3A", "#2A7AD2", "#E8C33A", "#2E9E4E"))]
def can(x, y, z):
    o = cyl("can", (x, y, z + 0.033), 0.033, 0.12, rng.choice(CAN_M), rot=(math.pi / 2, 0, rng.uniform(0, math.tau)), v=12); return o
BOTTLE_M = [mat("btl_g", "#2F6B2A", rough=0.05, alpha=0.75), mat("btl_b", "#6B3E1A", rough=0.05, alpha=0.75)]
def bottle(x, y, z):
    o = cyl("bottle_trash", (x, y, z + 0.04), 0.04, 0.3, rng.choice(BOTTLE_M), rot=(math.pi / 2, 0, rng.uniform(0, math.tau)), v=12); return o
PIZZA_BOX = mat("pizzabox", "#C9A274", rough=0.8); PIZZA = mat("pizza", "#E8A33A", rough=0.6); PEP = mat("pepperoni", "#B3261E", rough=0.5)
def pizza_box(x, y, z):
    a = rng.uniform(0, math.tau)
    b = box("pizzabox", x - 0.22, x + 0.22, y - 0.22, y + 0.22, z, z + 0.05, PIZZA_BOX); b.rotation_euler = (0, 0, a)
    if rng.random() < 0.6:
        cyl("pizza", (x, y, z + 0.055), 0.19, 0.01, PIZZA)
        for k in range(5):
            cyl("pep", (x + rng.uniform(-0.12, 0.12), y + rng.uniform(-0.12, 0.12), z + 0.062), 0.03, 0.005, PEP, v=10)
    return b
CONF = [mat(f"conf{i}", c, rough=0.4, emit=0.3) for i, c in enumerate(("#FF2BD6", "#2BE0FF", "#FFE02B", "#7CFF8C", "#FF6A2B", "#B44BFF"))]
conf_mesh = None
def confetti(x, y, z):
    global conf_mesh
    if conf_mesh is None:
        bpy.ops.mesh.primitive_plane_add(size=0.035); tmp = bpy.context.active_object
        conf_mesh = tmp.data; conf_mesh.materials.append(CONF[0]); bpy.data.objects.remove(tmp)
    o = bpy.data.objects.new("confetti", conf_mesh); sc.collection.objects.link(o)
    o.location = (x, y, z + 0.003); o.rotation_euler = (0, 0, rng.uniform(0, math.tau))
    o.material_slots[0].link = "OBJECT"; o.material_slots[0].material = rng.choice(CONF)
    return o
DECK_R = (-11.5, 11.5, -8.8, 4.8); IN_R = (-8.8, 8.8, 5.4, 12.2)
scatter(45, DECK_R, cup); scatter(16, IN_R, cup, 0.02, avoid_pool=False)
scatter(30, DECK_R, can); scatter(8, IN_R, can, 0.02, avoid_pool=False)
scatter(12, DECK_R, bottle); scatter(5, IN_R, bottle, 0.02, avoid_pool=False)
scatter(5, DECK_R, pizza_box); scatter(3, (-7.5, -3.0, 7.4, 11.4), pizza_box, 0.035, avoid_pool=False)
scatter(420, DECK_R, confetti); scatter(160, IN_R, confetti, 0.02, avoid_pool=False)
# cans and cups floating in the pool, the shopping cart sunk in the deep end, a pizza float, a lounger adrift
for i in range(14):
    x, y = rng.uniform(-PX + 0.4, PX - 0.4), rng.uniform(-PY + 0.4, PY - 0.4)
    o = cup(x, y, WZ - 0.03) if i % 2 else can(x, y, WZ - 0.03)
    for f in range(1, N + 1, 30):
        o.location.z = WZ - 0.02 + 0.02 * math.sin(f / 13 + i); o.keyframe_insert("location", frame=f)
cx, cy = 2.8, 1.6
for (a, b_, c_, d, e, g) in ((cx - 0.45, cx + 0.45, cy - 0.3, cy + 0.3, -0.95, -0.92), (cx - 0.45, cx + 0.45, cy - 0.3, cy - 0.28, -0.95, -0.35),
                             (cx - 0.45, cx + 0.45, cy + 0.28, cy + 0.3, -0.95, -0.35), (cx - 0.47, cx - 0.45, cy - 0.3, cy + 0.3, -0.95, -0.35),
                             (cx + 0.45, cx + 0.47, cy - 0.3, cy + 0.3, -0.95, -0.35), (cx + 0.47, cx + 0.75, cy - 0.02, cy + 0.02, -0.35, -0.33)):
    box("cart", a, b_, c_, d, e, g, STEEL)
for (x, y) in ((cx - 0.4, cy - 0.25), (cx + 0.4, cy - 0.25), (cx - 0.4, cy + 0.25), (cx + 0.4, cy + 0.25)):
    cyl("wheel", (x, y, -1.42), 0.06, 0.04, BLACK, rot=(math.pi / 2, 0, 0), v=12)
pz = cyl("pizza_float", (-3.6, 1.5, WZ + 0.06), 0.7, 0.14, PIZZA, v=3)
pz.rotation_euler = (0, 0, 0.6)
for k in range(4):
    cyl("pep_f", (-3.6 + rng.uniform(-0.25, 0.25), 1.5 + rng.uniform(-0.2, 0.2), WZ + 0.14), 0.09, 0.02, PEP, v=12)
lg = box("lounger_adrift", -0.6, 0.1, -1.9, -0.2, WZ - 0.05, WZ + 0.12, mat("lounger", "#F7F7F2"), bevel=0.04); lg.rotation_euler = (0, 0, 0.5)
# toilet paper over the palms and the balcony, balloons, traffic cones in silly places
TP = mat("tp", "#FAFAF7", rough=0.9)
for (x, y) in ((-11, 3.5), (11, 3.8), (11.2, -6.0)):
    for k in range(4):
        a = k / 4 * math.tau
        for j in range(5):
            box("tp", x + math.cos(a) * (0.6 + 0.3 * j) - 0.06, x + math.cos(a) * (0.6 + 0.3 * j) + 0.06,
                y + math.sin(a) * (0.6 + 0.3 * j) - 0.01, y + math.sin(a) * (0.6 + 0.3 * j) + 0.01, 5.0 - 0.9 * j - 0.45, 5.0 - 0.9 * j + 0.45, TP)
for j in range(12):
    x = -6 + j * 1.3
    box("tp_rail", x - 0.06, x + 0.06, 4.39, 4.41, 3.3 + 0.2 * math.sin(j), 4.85, TP)
BAL = [mat(f"bal{i}", c, rough=0.15, emit=0.2) for i, c in enumerate(("#FF2BD6", "#2BE0FF", "#FFE02B", "#B44BFF", "#FF6A2B"))]
for i in range(28):
    if i < 16: x, y, z = rng.uniform(-8.5, 8.5), rng.uniform(5.5, 12.3), rng.uniform(2.6, 3.1)
    else: x, y, z = rng.uniform(6.8, 8.4), rng.uniform(-6.4, -3.2), rng.uniform(1.6, 2.4)
    b = sphere("balloon", (x, y, z), 0.16, rng.choice(BAL), seg=12); b.scale = (1, 1, 1.2)
    cyl("string", (x, y, z - 0.6), 0.003, 1.0, TP, v=6)
    for f in range(1, N + 1, 40):
        b.location.z = z + 0.05 * math.sin(f / 17 + i); b.keyframe_insert("location", frame=f)
CONE = mat("cone", "#FF6A00", rough=0.5)
def cone(x, y, z, rx=0.0):
    bpy.ops.mesh.primitive_cone_add(radius1=0.16, radius2=0.03, depth=0.45, location=(x, y, z + 0.225), rotation=(rx, 0, 0), vertices=16)
    obj_mat(bpy.context.active_object, CONE)
cone(2.0, 9.0, 7.55)                      # on the roof
cone(-1.2, 1.6, 1.25)                     # on the flamingo's head
cone(7.5, -4.4, 1.05, rx=math.pi / 2)     # knocked over on the DJ booth
cone(-9.0, -6.2, 0.35)                    # on a lounger
# a trash can that gave up
cyl("bin", (-10.8, -8.0, 0.4), 0.28, 0.8, BLACK)
for k in range(6):
    cup(-10.8 + rng.uniform(-0.2, 0.2), -8.0 + rng.uniform(-0.2, 0.2), 0.8 + 0.05 * k)
