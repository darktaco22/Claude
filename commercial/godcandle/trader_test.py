"""Dev check of the trader alone: blender -b --factory-startup -P trader_test.py -- OUT.png [t]   (pose, grip, tap, one still from over his shoulder)"""
import bpy, sys, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
A = sys.argv[sys.argv.index('--') + 1:]; OUT = A[0]; TT = float(A[1]) if len(A) > 1 else 1.0
import trader
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 544; sc.view_settings.view_transform = 'AgX'
T = trader.Trader((0, 0), face=math.pi, cast=trader.CAST_DEFAULT)
T.a.K.d = {}
W = T.pose(1, TT, lambda t: (0.0, -0.03, 0.002), pitch=0.5, yaw=0.45); T.a.K.flush(); sc.frame_set(1)
bpy.ops.mesh.primitive_cube_add(size=1); ph = bpy.context.object; ph.scale = (0.072, 0.150, 0.0082); ph.data.materials.append(bpy.data.materials.new('p')); ph.data.materials[0].diffuse_color = (0.02, 0.02, 0.03, 1)
bpy.ops.mesh.primitive_plane_add(size=0.0655, location=(0, 0, 0.0042)); sc_ = bpy.context.object; sc_.scale = (1, 2.2, 1); m = bpy.data.materials.new('s'); m.use_nodes = True
m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (0.2, 1.0, 0.4, 1); m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2.0; sc_.data.materials.append(m)
sc_.parent = ph
ph.matrix_world = W
bpy.ops.mesh.primitive_plane_add(size=10); bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0.1, 0.18)).__class__
bean = bpy.context.object; bean.scale = (1, 1, 0.55)
for loc, e, col in (((0.6, -1.8, 2.2), 600, (1, 0.9, 0.8)), ((-1.5, 1.5, 1.8), 300, (0.5, 0.6, 1.0))):
    ld = bpy.data.lights.new('l', 'AREA'); ld.energy = e; ld.size = 1.5; ld.color = col; o = bpy.data.objects.new('l', ld); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
sc.world = bpy.data.worlds.new('w'); sc.world.use_nodes = True; sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.15
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
pw = W.translation; cam.location = pw + Vector((0.42, -0.62, 0.30)); cam.data.lens = 60
cam.rotation_euler = (pw - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.dof.use_dof = False
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True); print('TEST-DONE', W.translation)
