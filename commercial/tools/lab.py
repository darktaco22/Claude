# blender -b -P lab.py -- ASSET_DIR OUT_PREFIX [explosion.mp4]
# Integration test: game character on scanned ground, sky HDRI, light rig on/off, explosion card, camera shake.
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import polyhaven, scatter, shakify, lightrig, fxcard
args = sys.argv[sys.argv.index('--') + 1:]; A, OUT = args[:2]; EXP = args[2] if len(args) > 2 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 24
bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=40, size=40); g = bpy.context.object
for l in g.data.uv_layers[0].data: l.uv = l.uv * 10
g.data.materials.append(polyhaven.append_material(A, 'aerial_grass_rock', '1k'))
P = lambda aid: polyhaven.pick(polyhaven.append_model(A, aid, '1k'))
scatter.scatter(g, P('grass_bermuda_01') + P('grass_medium_01'), density=90, scale=(0.8, 1.8), name='Grass')
scatter.scatter(g, P('dandelion_01'), density=0.8, seed=5, name='Flowers')
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, '..', 'comeback', 'models', 'pepe.glb'))
arm = [o for o in bpy.context.selected_objects if o.type == 'ARMATURE'][0]
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
idle = [a for a in bpy.data.actions if a.name.startswith('idle')]
if idle: arm.animation_data_create(); arm.animation_data.action = idle[0]
for o in bpy.data.objects:
    if o.type == 'MESH' and o.find_armature() == arm:
        for p in o.data.polygons: p.use_smooth = True
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; nt = w.node_tree
e = nt.nodes.new('ShaderNodeTexEnvironment'); e.image = bpy.data.images.load(polyhaven.fetch(A, 'hdri', 'kloppenheim_06_puresky', '2k'))
mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord'); mp.inputs['Rotation'].default_value[2] = math.radians(200)
nt.links.new(tc.outputs['Generated'], mp.inputs[0]); nt.links.new(mp.outputs[0], e.inputs[0]); nt.links.new(e.outputs[0], nt.nodes['Background'].inputs[0])
nt.nodes['Background'].inputs[1].default_value = 1.6
cd = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (1.2, -5.2, 1.25); cd.lens = 85
cam.rotation_euler = ((__import__('mathutils').Vector((0, 0, 1.3)) - cam.location).to_track_quat('-Z', 'Y')).to_euler()
cd.dof.use_dof = True; cd.dof.focus_distance = 5.3; cd.dof.aperture_fstop = 2.0; cd.dof.aperture_ratio = 1.6
sc.frame_set(20); bpy.context.view_layer.update(); shakify.apply(cam, 'THE_CLOSEUP', 20, influence=0.5)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 544
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
lightrig.rig((0, 0, 0), cam, height=1.7, key_side=-1, mood='dawn'); lightrig.eye_light(cam, (0, 0, 0), 1.7)
sc.render.filepath = OUT + '_b_rig.png'; bpy.ops.render.render(write_still=True)
if EXP:
    fxcard.card(EXP, location=(-3.5, 14, 4.2), height=9, cam=cam, start=20 - 28, strength=5, light=60000)
    sc.render.filepath = OUT + '_c_fx.png'; bpy.ops.render.render(write_still=True)
