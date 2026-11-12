"""Dev check of the Rocketbox trader alone: blender -b --factory-startup -P rb_test.py -- OUT_PREFIX [t]   (three stills: over the shoulder, the phone close, from the side)"""
import bpy, sys, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
A = sys.argv[sys.argv.index('--') + 1:]; OUT = A[0]; TT = float(A[1]) if len(A) > 1 else 1.0
import rbtrader
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 544; sc.view_settings.view_transform = 'AgX'
T = rbtrader.RBTrader((0, 0), face=math.pi)
W = T.pose(1, TT, lambda t: (0.0, -0.03, 0.002)); sc.frame_set(1)
bpy.ops.mesh.primitive_cube_add(size=1); ph = bpy.context.object; ph.scale = (0.072, 0.150, 0.0082); bpy.ops.object.transform_apply(scale=True)
ph.data.transform(Matrix.Translation((0, 0, 0.0041))); m0 = bpy.data.materials.new('p'); m0.use_nodes = True; m0.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.02, 0.03, 1); ph.data.materials.append(m0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.0086)); sc_ = bpy.context.object; sc_.scale = (0.066, 0.143, 1); bpy.ops.object.transform_apply(scale=True); m = bpy.data.materials.new('s'); m.use_nodes = True
m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (0.2, 1.0, 0.4, 1); m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.5; sc_.data.materials.append(m)
sc_.parent = ph; ph.matrix_world = W
bpy.ops.mesh.primitive_plane_add(size=10); bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, -0.05, 0.2)); bpy.context.object.scale = (1, 1, 0.55)
for loc, e, col in (((0.8, -1.8, 2.2), 500, (1, 0.9, 0.8)), ((-1.5, 1.8, 1.8), 400, (0.6, 0.7, 1.0)), ((1.5, 1.5, 1.0), 200, (1, 1, 1))):
    ld = bpy.data.lights.new('l', 'AREA'); ld.energy = e; ld.size = 1.5; ld.color = col; o = bpy.data.objects.new('l', ld); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0.2, 1.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
sc.world = bpy.data.worlds.new('w'); sc.world.use_nodes = True; sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.2
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_start = 0.01
pw = W.translation; R = W.to_3x3(); n = R.col[2]; u = R.col[0]; v = R.col[1]
def look(loc, tgt, up):
    z = (Vector(loc) - Vector(tgt)).normalized(); x = Vector(up).cross(z).normalized(); y = z.cross(x); M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = loc; cam.matrix_world = M
for name, loc, lens, up in (('ots', pw + Vector((0.45, -0.75, 0.62)), 60, (0, 0, 1)), ('phone', pw + n * 0.34 + u * 0.12 + v * 0.03, 40, v), ('left', pw - u * 0.32 + n * 0.14 - v * 0.03, 40, v), ('side', pw + Vector((1.3, 0.1, 0.3)), 40, (0, 0, 1))):
    cam.data.lens = lens; look(loc, pw, up)
    sc.render.filepath = f'{OUT}_{name}.png'; bpy.ops.render.render(write_still=True)
print('TEST-DONE', pw)
