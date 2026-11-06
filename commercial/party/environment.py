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
# trees: trunks with clumps of foliage, outside the wall and on the hills; tall cypresses along the wall
LEAF = [mat("leaf_a", "#1F3D1A", rough=0.9), mat("leaf_b", "#2A4D20", rough=0.9), mat("leaf_c", "#183214", rough=0.9)]
BARK = mat("bark", "#3D2C1F", rough=0.95)
def tree(x, y, h, w):
    cyl("trunk", (x, y, h * 0.3 - 0.3), 0.08 * w + 0.06, h * 0.6, BARK, v=8)
    for k in range(5):
        p = (x + rng2.uniform(-0.6, 0.6) * w, y + rng2.uniform(-0.6, 0.6) * w, h * rng2.uniform(0.55, 0.95))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=w * rng2.uniform(0.6, 1.0), location=p)
        f = bpy.context.active_object; f.data.shade_smooth(); obj_mat(f, rng2.choice(LEAF))
        d = f.modifiers.new("lumpy", "DISPLACE"); tx = bpy.data.textures.get("lumps") or bpy.data.textures.new("lumps", "CLOUDS")
        tx.noise_scale = 0.4; d.texture = tx; d.strength = 0.35 * w
def cypress(x, y, h):
    cyl("ctrunk", (x, y, 0.2), 0.07, 0.8, BARK, v=6)
    sphere("cypress", (x, y, h / 2), 0.5, rng2.choice(LEAF), seg=12).scale = (0.75, 0.75, h)
for i in range(70):
    a = rng2.uniform(0, math.tau); r = rng2.uniform(21, 70)
    x, y = math.cos(a) * r, math.sin(a) * r
    if y < -20 and abs(x) < 8: continue   # keep the view down to the city open
    z = 0.0
    tree(x, y, rng2.uniform(5, 9), rng2.uniform(1.4, 2.4))
for i in range(11):
    cypress(-17.2 + i * 3.4, 17.3, rng2.uniform(5.0, 6.5))
for y in range(-14, 16, 4):
    cypress(-17.3, y, rng2.uniform(4.5, 6.0)); cypress(17.3, y, rng2.uniform(4.5, 6.0))
# more palms on the lawn, shrubs along the house, a driveway with a gravel finish
for (x, y) in ((-15, -12), (14.5, -12.5), (-15.5, 10), (15.5, 9.5), (-6, -15), (6, -15.5)):
    palm(x, y, 6.5 + rng2.uniform(-0.5, 1.0), (rng2.uniform(-0.6, 0.6), rng2.uniform(-0.4, 0.4)))
for i in range(12):
    x = -9 + i * 1.6
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.55, location=(x, 13.6, 0.25))
    sh = bpy.context.active_object; sh.scale = (1.0, 0.7, 0.75); sh.data.shade_smooth(); obj_mat(sh, rng2.choice(LEAF))
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
