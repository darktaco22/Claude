# The world around the villa, and better surfaces (run inside party.py's namespace, after dressing.py).
# A city skyline across the water (Poly Haven's Shanghai Bund, CC0) seen from a hilltop lot: terrain, trees, a perimeter wall.
import bpy, math, random, os
from mathutils import Vector

rng2 = random.Random(5)

# ------------------------------------------------------------------------------------------------ sky: the city at night
hdr = os.path.join(PH, "shanghai_bund_4k.hdr")
if os.path.exists(hdr):
    env.image = bpy.data.images.load(hdr)
    mapn = wn.nodes.new("ShaderNodeMapping"); tcw = wn.nodes.new("ShaderNodeTexCoord")
    mapn.inputs["Rotation"].default_value = (0, 0, math.radians(A("--sky_rot", 200, float)))
    wn.links.new(tcw.outputs["Generated"], mapn.inputs["Vector"]); wn.links.new(mapn.outputs[0], env.inputs["Vector"])
    bg.inputs["Strength"].default_value = A("--sky", 0.55, float)

# ------------------------------------------------------------------------------------------------ surfaces
def retex(m, color_a, color_b, kind="brick", scale=6.0, rough=0.5, bump=0.3, mortar=None, emit=0.0, emit_color=None):
    """Give an existing material a procedural pattern: brick (planks, tiles) or noise (grass, plaster)."""
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    for l in list(b.inputs["Base Color"].links): nt.links.remove(l)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "brick":
        t = nt.nodes.new("ShaderNodeTexBrick"); t.inputs["Scale"].default_value = scale
        t.inputs["Color1"].default_value = srgb(color_a); t.inputs["Color2"].default_value = srgb(color_b)
        t.inputs["Mortar"].default_value = srgb(mortar or color_b); t.inputs["Mortar Size"].default_value = 0.012
        t.inputs["Brick Width"].default_value = 1.2; t.inputs["Row Height"].default_value = 0.3
        nt.links.new(tc.outputs["Object"], t.inputs["Vector"]); col = t.outputs["Color"]; fac = t.outputs["Fac"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = scale; t.inputs["Detail"].default_value = 8
        r = nt.nodes.new("ShaderNodeValToRGB"); r.color_ramp.elements[0].color = srgb(color_a); r.color_ramp.elements[1].color = srgb(color_b)
        nt.links.new(tc.outputs["Object"], t.inputs["Vector"]); nt.links.new(t.outputs["Fac"], r.inputs[0]); col = r.outputs["Color"]; fac = t.outputs["Fac"]
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    if bump:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nt.links.new(fac, bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = srgb(emit_color or color_a); b.inputs["Emission Strength"].default_value = emit
retex(DECK, "#B8A78E", "#9C8A72", kind="brick", scale=1.2, rough=0.55, bump=0.15, mortar="#6E6252")          # travertine pavers
retex(TILE, "#1E9BD0", "#1580B3", kind="brick", scale=18.0, rough=0.25, bump=0.1, mortar="#DDEFF5", emit=0.5, emit_color="#2AB8F0")  # pool mosaic
retex(LAWN, "#1D3518", "#2C4A22", kind="noise", scale=40.0, rough=0.95, bump=0.4)
retex(WALL, "#ECEAE4", "#DCD8CF", kind="noise", scale=4.0, rough=0.6, bump=0.05)
retex(FLOOR, "#5E5751", "#7A7169", kind="brick", scale=0.9, rough=0.25, bump=0.03, mortar="#3E3833")     # large-format floor tiles
# real glass and real water now (Cycles refracts them)
gb = GLASS.node_tree.nodes["Principled BSDF"]
gb.inputs["Alpha"].default_value = 1.0; gb.inputs["Transmission Weight"].default_value = 1.0; gb.inputs["Roughness"].default_value = 0.0
gb.inputs["IOR"].default_value = 1.45; gb.inputs["Base Color"].default_value = srgb("#E8F3F6")
wb.inputs["Alpha"].default_value = 1.0; wb.inputs["Transmission Weight"].default_value = 1.0; wb.inputs["IOR"].default_value = 1.33
wb.inputs["Base Color"].default_value = srgb("#BDEFFF"); wb.inputs["Emission Strength"].default_value = 0.05; wb.inputs["Roughness"].default_value = 0.02
bump.inputs["Strength"].default_value = 0.12

# ------------------------------------------------------------------------------------------------ the hilltop lot
# the lawn grows to the horizon; the land falls away to the south and east (toward the city), hills rise behind
for o in [o for o in bpy.data.objects if o.name.startswith("lawn")]:
    bpy.data.objects.remove(o)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=160, size=900, location=(0, 0, -0.31))
terrain = bpy.context.active_object; terrain.name = "terrain"
for v in terrain.data.vertices:
    x, y = v.co.x, v.co.y
    r = math.hypot(x, y)
    if r < 26: continue
    k = min(1.0, (r - 26) / 60)
    north = max(0.0, y) / 300.0
    v.co.z = -18 * k * (1 - north) + 40 * k * north * north + 3 * math.sin(x / 23) * math.cos(y / 31) * k
terrain.data.shade_smooth(); obj_mat(terrain, LAWN)
# a stone perimeter wall with lamp posts, and a gate in it
STONE2 = bpy.data.materials.get("stone") or mat("stone2", "#77706A")
for (x0, x1, y0, y1) in ((-18, 18, -18.4, -18.0), (-18, 18, 18.0, 18.4), (-18.4, -18.0, -18, 18.4), (18.0, 18.4, -18, 18.4)):
    if y0 == -18.4:
        box("wall_s1", -18, -2.5, y0, y1, -0.3, 1.5, STONE2); box("wall_s2", 2.5, 18, y0, y1, -0.3, 1.5, STONE2)
    else:
        box("wall_p", x0, x1, y0, y1, -0.3, 1.5, STONE2)
LAMP = mat("lamp_glow", "#FFD9A0", emit=12.0)
for i in range(13):
    x = -18 + i * 3.0
    for y in (-18.2, 18.2):
        cyl("lamppost", (x, y, 1.9), 0.05, 0.8, BLACK, v=8); sphere("lamp", (x, y, 2.35), 0.1, LAMP, seg=10)
for x in (-2.6, 2.6):
    box("gate_pier", x - 0.3, x + 0.3, -18.6, -17.8, -0.3, 2.4, STONE2)
# trees and planting: Poly Haven's CC0 models, imported once each and placed as instances (cheap in memory)
LEAF = [mat("leaf_a", "#1F3D1A", rough=0.9), mat("leaf_b", "#2A4D20", rough=0.9), mat("leaf_c", "#183214", rough=0.9)]
BARK = mat("bark", "#3D2C1F", rough=0.95)
def tz(x, y):   # the terrain's height (as built above)
    r = math.hypot(x, y)
    if r < 26: return -0.3
    k = min(1.0, (r - 26) / 60); north = max(0.0, y) / 300.0
    return -0.31 - 18 * k * (1 - north) + 40 * k * north * north + 3 * math.sin(x / 23) * math.cos(y / 31) * k
_lib = {}
def asset(name):
    """Import a Poly Haven glTF once into a hidden collection; return it for instancing."""
    if name in _lib: return _lib[name]
    col = bpy.data.collections.new("lib_" + name)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(PH, name, name + ".gltf"))
    for o in [o for o in bpy.data.objects if o not in before]:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    _lib[name] = col; return col
def place_asset(name, x, y, z=None, s=1.0, rot=None):
    e = bpy.data.objects.new(name + "_inst", None); sc.collection.objects.link(e)
    e.instance_type = "COLLECTION"; e.instance_collection = asset(name)
    e.location = (x, y, tz(x, y) if z is None else z); e.rotation_euler = (0, 0, rng2.uniform(0, math.tau) if rot is None else rot); e.scale = (s, s, s)
    return e
for i in range(46):   # big trees beyond the wall and over the hills
    a = rng2.uniform(0, math.tau); r = rng2.uniform(22, 75)
    x, y = math.cos(a) * r, math.sin(a) * r
    if y < -20 and abs(x) < 10: continue   # keep the view down to the city open
    place_asset(rng2.choice(("jacaranda_tree", "jacaranda_tree", "quiver_tree_02")), x, y, s=rng2.uniform(0.8, 1.3))
for i in range(22):   # shrubs along the perimeter wall, inside it
    t = i / 22
    if t < 0.5: x, y = -17.0 + 34 * (t / 0.5), 17.2
    else: x, y = (-17.2 if i % 2 else 17.2), -14 + 30 * ((t - 0.5) / 0.5)
    place_asset(rng2.choice(("shrub_02", "shrub_04", "shrub_03")), x, y, z=-0.3, s=rng2.uniform(1.4, 2.2))
for i in range(12):   # a bed of shrubs and ferns along the back of the house
    place_asset(rng2.choice(("shrub_04", "fern_02", "shrub_03")), -9 + i * 1.6, 13.7, z=-0.3, s=rng2.uniform(1.0, 1.5))
for (x, y) in ((-11.6, 2.6), (-11.0, 4.6), (11.6, 2.9), (11.8, 4.8), (-10.0, -7.2), (11.0, -7.0)):   # ferns at the palms' feet
    place_asset("fern_02", x, y, z=0.0, s=1.3)
for (x, y) in ((-8.6, 5.8), (8.6, 5.8), (-2.6, 5.4), (2.6, 5.4)):
    place_asset("potted_plant_04", x, y, z=0.02, s=2.2)
# more palms on the lawn, a driveway with a gravel finish, street lamps along it, wine on the island
for (x, y) in ((-15, -12), (14.5, -12.5), (-15.5, 10), (15.5, 9.5), (-6, -15), (6, -15.5)):
    palm(x, y, 6.5 + rng2.uniform(-0.5, 1.0), (rng2.uniform(-0.6, 0.6), rng2.uniform(-0.4, 0.4)))
for y in (-14, -7, 0, 7):
    place_asset("street_lamp_02", 17.4, y, z=-0.3, s=1.0, rot=math.pi)
place_asset("wine_bottles_01", 5.9, 9.55, z=1.06, s=1.0, rot=0.3)
GRAVEL = mat("gravel", "#8D857B", rough=0.95); retex(GRAVEL, "#7C756C", "#A39B90", kind="noise", scale=90.0, rough=0.95, bump=0.5)
box("driveway", 12.5, 17.8, -17.8, 14.0, -0.3, -0.28, GRAVEL)
# neighbours' houses on the hills behind, windows lit
NWIN = mat("nwin", "#FFC98A", emit=6.0); NWALL = mat("nwall", "#3A3A40", rough=0.8)
for i in range(9):
    x = -90 + i * 22 + rng2.uniform(-5, 5); y = rng2.uniform(80, 140)
    z = 40 * ((y / 300.0) ** 2) * min(1, (math.hypot(x, y) - 26) / 60) - 0.3
    w, d_, h = rng2.uniform(8, 14), rng2.uniform(6, 9), rng2.uniform(4, 7)
    box("neighbour", x - w / 2, x + w / 2, y - d_ / 2, y + d_ / 2, z, z + h, NWALL)
    for k in range(4):
        wx = x - w / 2 + (k + 0.6) * w / 4.5
        box("nwindow", wx, wx + 0.9, y - d_ / 2 - 0.05, y - d_ / 2, z + 1.2, z + 2.4, NWIN)

# ------------------------------------------------------------------------------------------------ photographic surfaces (Poly Haven CC0 PBR)
TEX = os.path.join(PH, "tex")
def pbr(m, tex, scale=1.0, tint=None, rough_mul=1.0, bump=1.0, emit=0.0):
    """Swap a material's surface for a Poly Haven texture set, box-projected in object space at `scale` metres per tile."""
    d = os.path.join(TEX, tex)
    if m is None or not os.path.isdir(d): return
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    for inp in ("Base Color", "Roughness", "Normal"):
        for l in list(b.inputs[inp].links): nt.links.remove(l)
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale, 1 / scale, 1 / scale)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def img(name, colour):
        p = os.path.join(d, name + ".jpg")
        if not os.path.exists(p): return None
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(p, check_existing=True)
        if not colour: t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"; t.projection_blend = 0.2
        nt.links.new(mp.outputs[0], t.inputs["Vector"]); return t
    dif = img("diff", True); rgh = img("rough", False); nor = img("nor", False)
    if dif:
        if tint:
            mx = nt.nodes.new("ShaderNodeMixRGB"); mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
            mx.inputs[2].default_value = srgb(tint); nt.links.new(dif.outputs["Color"], mx.inputs[1]); nt.links.new(mx.outputs[0], b.inputs["Base Color"])
        else:
            nt.links.new(dif.outputs["Color"], b.inputs["Base Color"])
    if rgh:
        mt = nt.nodes.new("ShaderNodeMath"); mt.operation = "MULTIPLY"; mt.inputs[1].default_value = rough_mul
        nt.links.new(rgh.outputs["Color"], mt.inputs[0]); nt.links.new(mt.outputs[0], b.inputs["Roughness"])
    if nor:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = bump
        nt.links.new(nor.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Strength"].default_value = emit
pbr(DECK, "rectangular_paving", 2.0, tint="#F2E6D6")
pbr(TILE, "blue_floor_tiles_01", 0.8, emit=0.35)
pbr(LAWN, "leafy_grass", 2.5, tint="#7FA070", bump=0.6)
pbr(WALL, "plastered_wall_04", 2.5, tint="#FFFDF8")
pbr(FLOOR, "herringbone_parquet", 1.6)
pbr(bpy.data.materials.get("inwall"), "painted_plaster_wall", 2.0, tint="#9A86B8")
pbr(bpy.data.materials.get("stone"), "rustic_stone_wall_02", 2.0)
pbr(bpy.data.materials.get("marble"), "marble_01", 1.2, rough_mul=0.4)
pbr(bpy.data.materials.get("oak"), "oak_veneer_01", 1.0)
pbr(bpy.data.materials.get("wood"), "oak_veneer_01", 1.0, tint="#C08A5A")
pbr(bpy.data.materials.get("cabinet"), "black_oak_veneer", 1.0)
pbr(bpy.data.materials.get("island"), "black_oak_veneer", 1.0)
pbr(bpy.data.materials.get("rug"), "quatrefoil_jacquard_fabric", 0.8, tint="#C04A8A")
pbr(bpy.data.materials.get("bark"), "bark_brown_02", 1.0)
pbr(bpy.data.materials.get("trunk"), "palm_tree_bark", 1.0)
pbr(GRAVEL, "gravel_floor_02", 1.5)
pbr(bpy.data.materials.get("coping"), "concrete_floor_02", 1.0, tint="#FFFFFF")
pbr(bpy.data.materials.get("steel"), "metal_plate", 1.0, rough_mul=0.5)
