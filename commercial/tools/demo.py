# blender -b -P demo.py -- ASSET_DIR OUT.png   (proves the toolkit works headless)
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polyhaven, scatter, shakify
A, OUT = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=30)
g = bpy.context.object
import random; random.seed(2)
for v in g.data.vertices: v.co.z = 0.5 * math.sin(v.co.x * 0.3) * math.cos(v.co.y * 0.25)
for l in g.data.uv_layers[0].data: l.uv = l.uv * 8
g.data.materials.append(polyhaven.append_material(A, 'aerial_grass_rock', '1k'))
def meshes(aid, lod='LOD1'): return polyhaven.pick(polyhaven.append_model(A, aid, '1k'), lod)
scatter.scatter(g, meshes('grass_bermuda_01') + meshes('grass_medium_01'), density=120, scale=(0.7, 1.6), name='Grass')
scatter.scatter(g, meshes('dandelion_01'), density=1.5, seed=5, name='Flowers')
t = [o for o in meshes('searsia_lucida') if '_a_' in o.name][0]; sc.collection.objects.link(t); t.location = (3, 6, 0.2); t.scale = (2, 2, 2)
for o in meshes('namaqualand_boulder_02'): sc.collection.objects.link(o); o.location = (-2.5, 2.5, 0.1)
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
e = w.node_tree.nodes.new('ShaderNodeTexEnvironment')
e.image = bpy.data.images.load(polyhaven.fetch(A, 'hdri', 'kloppenheim_06_puresky', '2k'))
mp = w.node_tree.nodes.new('ShaderNodeMapping'); tc = w.node_tree.nodes.new('ShaderNodeTexCoord')
mp.inputs['Rotation'].default_value[2] = math.radians(200)
w.node_tree.links.new(tc.outputs['Generated'], mp.inputs[0]); w.node_tree.links.new(mp.outputs[0], e.inputs[0])
w.node_tree.links.new(e.outputs[0], w.node_tree.nodes['Background'].inputs[0])
cd = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -6, 0.9); cam.rotation_euler = (math.radians(86), 0, 0); cd.lens = 35
cd.dof.use_dof = True; cd.dof.focus_distance = 8.5; cd.dof.aperture_fstop = 2.0
bpy.context.view_layer.update(); shakify.apply(cam, 'INVESTIGATION', 37)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 544
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
