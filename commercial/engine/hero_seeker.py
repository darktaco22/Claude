"""
Hero shot: PEPE (the game's own model and animation, from the live game's assets) plays MEME ROYALE on a phone.
The phone's screen shows the game's portrait gameplay, captured frame by frame from the real engine.

    blender -b --factory-startup -P hero_seeker.py -- --model pepe.glb --screen DIR_OR_PNG --first N
        [--w 1280 --h 720 --samples 24] [--save hero.blend] [--stills 1,60,120 OUTDIR] [--render OUTDIR]

Shot (150 frames, 30 fps): the camera starts in front of PEPE, who is hunched over the phone grinning, and swings
round over his shoulder, pushing in until the phone's screen fills the frame (the edit cuts to the full gameplay).
"""
import bpy, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
A = lambda k, d=None, t=str: t(argv[argv.index(k) + 1]) if k in argv else d
MODEL = os.path.abspath(A("--model"))
SCREEN = os.path.abspath(A("--screen"))
FIRST = A("--first", 0, int)
N = 150
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N
sc.render.fps = 30

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1,)

def mat(name, color, rough=0.4, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = hexc(color); b.inputs["Emission Strength"].default_value = emit
    return m

# ---------------------------------------------------------------- the character
bpy.ops.import_scene.gltf(filepath=MODEL)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig)
for o in list(bpy.data.objects):
    if o.type == "MESH" and o is not body and o.parent != rig:
        bpy.data.objects.remove(o)   # the game's selection sphere
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.get("idle_" + rig.name) or next(a for a in bpy.data.actions if a.name.startswith("idle"))
for fc in rig.animation_data.action.fcurves:   # the idle loops for the whole shot
    fc.modifiers.new("CYCLES")

# the phone, held at chest height in front of him, its screen toward his face
H = body.dimensions.z
phone_w, phone_h, phone_d = 0.33 * H / 1.69, 0.62 * H / 1.69, 0.03   # a cartoon-sized phone: reads at this framing
hold = Vector((0.0, -0.34 * H / 1.69, 0.98 * H / 1.69))
phone = bpy.data.objects.new("Phone", None); sc.collection.objects.link(phone)
phone.location = hold
phone.rotation_euler = (math.radians(35), 0, 0)   # screen tilted up toward his face
# body: a rounded slab, dark with a warm metal edge
bpy.ops.mesh.primitive_cube_add(size=1)
slab = bpy.context.active_object; slab.name = "PhoneBody"
slab.scale = (phone_w, phone_d, phone_h); bpy.ops.object.transform_apply(scale=True)
bv = slab.modifiers.new("bevel", "BEVEL"); bv.width = 0.035; bv.segments = 6
slab.data.materials.append(mat("phone_body", "#15121C", rough=0.3, metal=0.6))
slab.parent = phone
# a thin edge band
bpy.ops.mesh.primitive_cube_add(size=1)
band = bpy.context.active_object; band.scale = (phone_w + 0.006, phone_d * 0.6, phone_h + 0.006); bpy.ops.object.transform_apply(scale=True)
bv = band.modifiers.new("bevel", "BEVEL"); bv.width = 0.037; bv.segments = 6
band.data.materials.append(mat("phone_edge", "#C9B48A", rough=0.25, metal=0.9)); band.parent = phone
# camera bump on the back
bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.012, location=(-phone_w * 0.28, phone_d * 0.55, phone_h * 0.36), rotation=(math.pi / 2, 0, 0))
cam_b = bpy.context.active_object; cam_b.location.y = -phone_d * 0.55; cam_b.data.materials.append(mat("lens", "#050507", rough=0.05, metal=0.2)); cam_b.parent = phone
# the screen: the game's frames, on the side facing -y (toward him after the tilt)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, phone_d / 2 + 0.0015, 0), rotation=(-math.pi / 2, 0, 0))
scr = bpy.context.active_object; scr.name = "Screen"
scr.scale = (-phone_w * 0.92, -phone_h * 0.95, 1); bpy.ops.object.transform_apply(scale=True)
sm = bpy.data.materials.new("screen"); sm.use_nodes = True
nt = sm.node_tree; nt.nodes.clear()
outn = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); tex = nt.nodes.new("ShaderNodeTexImage")
if os.path.isdir(SCREEN):
    files = sorted(f for f in os.listdir(SCREEN) if f.endswith(".png"))
    files = [f for f in files if int(f[2:6]) >= FIRST]
    img = bpy.data.images.load(os.path.join(SCREEN, files[0])); img.source = "SEQUENCE"
    tex.image = img; tex.image_user.frame_duration = len(files); tex.image_user.frame_start = 1
    tex.image_user.frame_offset = int(files[0][2:6]) - 1; tex.image_user.use_auto_refresh = True
else:
    tex.image = bpy.data.images.load(SCREEN)
em.inputs["Strength"].default_value = 1.6
nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], outn.inputs[0])
scr.data.materials.append(sm); scr.parent = phone
# round the screen's corners with the bezel: a slightly larger dark plane behind it
glow = bpy.data.objects.new("ScreenLight", bpy.data.lights.new("ScreenLight", "AREA")); sc.collection.objects.link(glow)
glow.data.energy = 25; glow.data.size = phone_w; glow.data.color = (0.6, 0.85, 1.0); glow.parent = phone
glow.location = (0, 0.12, 0); glow.rotation_euler = (math.pi / 2, 0, 0)

# hands on the phone's sides (IK), head turned to the screen
def target(name, loc):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e); e.parent = phone; e.location = loc; return e
tl = target("hand_L", (phone_w * 0.62, 0.02, -phone_h * 0.12))
tr = target("hand_R", (-phone_w * 0.62, 0.02, -phone_h * 0.12))
pl = target("pole_L", (phone_w * 3.0, 0.4, -phone_h * 1.2))
pr = target("pole_R", (-phone_w * 3.0, 0.4, -phone_h * 1.2))
look = bpy.data.objects.new("look", None); sc.collection.objects.link(look)
pb = rig.pose.bones
for side, t, pole in (("Left", tl, pl), ("Right", tr, pr)):
    c = pb[f"mixamorig:{side}ForeArm"].constraints.new("IK")
    c.target = t; c.chain_count = 2; c.pole_target = pole; c.pole_angle = math.radians(-90)
    c = pb[f"mixamorig:{side}Hand"].constraints.new("COPY_ROTATION"); c.target = phone; c.influence = 0.6
c = pb["mixamorig:Head"].constraints.new("DAMPED_TRACK"); c.target = look; c.track_axis = "TRACK_Z"; c.influence = 0.55
c = pb["mixamorig:Spine2"].constraints.new("DAMPED_TRACK"); c.target = look; c.track_axis = "TRACK_Z"; c.influence = 0.15
# a little life in the hands while he plays, then he turns the phone round to show us (frames 62-80)
for f in range(1, 61, 10):
    k = (f // 10) % 2
    phone.location = hold + Vector((0.004 * (1 if k else -1), 0, 0.006 * (1 if k else -1)))
    phone.keyframe_insert("location", frame=f)
phone.rotation_euler = (math.radians(35), 0, 0); phone.keyframe_insert("rotation_euler", frame=62)
show = hold + Vector((0, -0.16, -0.04))
phone.location = hold; phone.keyframe_insert("location", frame=62)
phone.location = show; phone.rotation_euler = (math.radians(-8), 0, math.pi); phone.keyframe_insert("location", frame=80); phone.keyframe_insert("rotation_euler", frame=80)
phone.keyframe_insert("location", frame=N); phone.keyframe_insert("rotation_euler", frame=N)
# where he looks: down at the screen, then up at us
look.location = hold + Vector((0, -0.05, 0)); look.keyframe_insert("location", frame=60)
look.location = Vector((0.3, -3.0, 1.5)); look.keyframe_insert("location", frame=82)
# ---------------------------------------------------------------- the set: purple studio, gold rim light, his arena behind
# deep space: a star field and a purple nebula in the world shader
world = bpy.data.worlds.new("space"); sc.world = world; world.use_nodes = True
wn = world.node_tree; wn.nodes.clear()
wo = wn.nodes.new("ShaderNodeOutputWorld"); bg = wn.nodes.new("ShaderNodeBackground")
tc = wn.nodes.new("ShaderNodeTexCoord")
# stars: tiny voronoi cells, kept only very near their centres
vor = wn.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 260
wn.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
st = wn.nodes.new("ShaderNodeMapRange"); st.inputs["From Min"].default_value = 0.0; st.inputs["From Max"].default_value = 0.14
st.inputs["To Min"].default_value = 9.0; st.inputs["To Max"].default_value = 0.0; st.clamp = True
wn.links.new(vor.outputs["Distance"], st.inputs["Value"])
# only some cells are stars
cellr = wn.nodes.new("ShaderNodeMath"); cellr.operation = "GREATER_THAN"; cellr.inputs[1].default_value = 0.7
sepc = wn.nodes.new("ShaderNodeSeparateColor"); wn.links.new(vor.outputs["Color"], sepc.inputs[0]); wn.links.new(sepc.outputs[0], cellr.inputs[0])
stars = wn.nodes.new("ShaderNodeMath"); stars.operation = "MULTIPLY"
wn.links.new(st.outputs[0], stars.inputs[0]); wn.links.new(cellr.outputs[0], stars.inputs[1])
# nebula: layered noise through a purple/magenta/blue ramp
noi = wn.nodes.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 2.2; noi.inputs["Detail"].default_value = 8; noi.inputs["Roughness"].default_value = 0.62
wn.links.new(tc.outputs["Generated"], noi.inputs["Vector"])
ramp = wn.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
cr.elements[0].position = 0.35; cr.elements[0].color = hexc("#05020F")
cr.elements[1].position = 0.78; cr.elements[1].color = hexc("#C03CFF")
e = cr.elements.new(0.55); e.color = hexc("#2A0F6E")
e = cr.elements.new(0.68); e.color = hexc("#3B6BFF")
wn.links.new(noi.outputs["Fac"], ramp.inputs[0])
neb = wn.nodes.new("ShaderNodeMixRGB"); neb.blend_type = "ADD"; neb.inputs[0].default_value = 1.0
wn.links.new(ramp.outputs["Color"], neb.inputs[1]); wn.links.new(stars.outputs[0], neb.inputs[2])
wn.links.new(neb.outputs[0], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.9
wn.links.new(bg.outputs[0], wo.inputs[0])
# a ringed planet behind him, and a soft glow on its edge
def emis(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = hexc(color); e.inputs["Strength"].default_value = strength; nt.links.new(e.outputs[0], o.inputs[0]); return m
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.9, location=(3.4, 13.0, 4.6), segments=96, ring_count=48)
planet = bpy.context.active_object; planet.data.shade_smooth()
pm = mat("planet", "#6B2BD9", rough=0.8); pn = pm.node_tree
pnoise = pn.nodes.new("ShaderNodeTexNoise"); pnoise.inputs["Scale"].default_value = 3.0; pnoise.inputs["Detail"].default_value = 6
pr = pn.nodes.new("ShaderNodeValToRGB"); pr.color_ramp.elements[0].color = hexc("#3A1690"); pr.color_ramp.elements[1].color = hexc("#E06BFF")
pn.links.new(pnoise.outputs["Fac"], pr.inputs[0]); pn.links.new(pr.outputs["Color"], pn.nodes["Principled BSDF"].inputs["Base Color"])
planet.data.materials.append(pm)
bpy.ops.mesh.primitive_torus_add(major_radius=2.9, minor_radius=0.18, location=(3.4, 13.0, 4.6), rotation=(math.radians(72), math.radians(18), 0))
ring = bpy.context.active_object; ring.scale = (1, 1, 0.08); ring.data.materials.append(emis("ring", "#FFC52E", 1.4))
sunL = bpy.data.objects.new("PlanetSun", bpy.data.lights.new("PlanetSun", "SUN")); sc.collection.objects.link(sunL)
sunL.data.energy = 2.5; sunL.data.color = (1.0, 0.85, 0.7); sunL.rotation_euler = (math.radians(60), math.radians(-40), math.radians(20))
# a slow drift of the planet through the shot
planet.keyframe_insert("location", frame=1); ring.keyframe_insert("location", frame=1)
planet.location.x -= 0.6; ring.location.x -= 0.6
planet.keyframe_insert("location", frame=N); ring.keyframe_insert("location", frame=N)
bpy.ops.mesh.primitive_cylinder_add(radius=1.6, depth=0.12, location=(0, 0, -0.06), vertices=96)
stage = bpy.context.active_object; stage.data.materials.append(mat("stage", "#3A1690", rough=0.45))
bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.035, location=(0, 0, 0.0))
rim = bpy.context.active_object; rim.data.materials.append(mat("rim", "#FFB423", rough=0.2, metal=0.9, emit=0.6))
def light(name, kind, loc, rot, energy, color=(1, 1, 1), size=1.0):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); sc.collection.objects.link(L)
    L.location = loc; L.rotation_euler = rot; L.data.energy = energy; L.data.color = color
    if kind == "AREA": L.data.size = size
    return L
light("key", "AREA", (-1.6, -2.2, 2.6), (math.radians(55), 0, math.radians(-35)), 260, (1.0, 0.95, 0.9), 2.0)
light("rimL", "AREA", (1.8, 1.5, 2.0), (math.radians(-60), math.radians(35), 0), 320, (1.0, 0.75, 0.25), 1.5)
light("rimR", "AREA", (-1.8, 1.5, 2.0), (math.radians(-60), math.radians(-35), 0), 280, (0.6, 0.35, 1.0), 1.5)

# ---------------------------------------------------------------- the camera: front, round over his shoulder, into the screen
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
tgt = bpy.data.objects.new("CamTarget", None); sc.collection.objects.link(tgt)
tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
sc.frame_set(N); bpy.context.view_layer.update()
sw = phone.matrix_world @ Vector((0, phone_d / 2, 0))
nrm = (phone.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
sc.frame_set(1)
keys = [  # frame, camera location, look-at
    (1, Vector((0.9, -3.4, 1.35)), Vector((0, 0, 1.05 * H / 1.69))),
    (70, Vector((0.25, -2.7, 1.40)), Vector((0, 0, 1.10 * H / 1.69))),
    (150, sw + nrm * 0.62, sw),
]
for f, loc, at in keys:
    cam.location = loc; cam.keyframe_insert("location", frame=f)
    tgt.location = at; tgt.keyframe_insert("location", frame=f)
for o in (cam, tgt):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"; k.easing = "EASE_IN_OUT"

# ---------------------------------------------------------------- render
r = sc.render
r.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A("--samples", 24, int); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; r.use_persistent_data = True
r.resolution_x = A("--w", 1280, int); r.resolution_y = A("--h", 720, int); r.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"
r.image_settings.file_format = "PNG"
if "--save" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(A("--save")))
if "--stills" in argv:
    fr = [int(x) for x in argv[argv.index("--stills") + 1].split(",")]; od = argv[argv.index("--stills") + 2]; os.makedirs(od, exist_ok=True)
    for f in fr:
        sc.frame_set(f); r.filepath = os.path.join(od, f"hero_{f:04d}.png"); bpy.ops.render.render(write_still=True)
if "--render" in argv:
    r.filepath = os.path.join(os.path.abspath(A("--render")), "f_"); bpy.ops.render.render(animation=True)
