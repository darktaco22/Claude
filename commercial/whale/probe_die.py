import bpy, sys, os, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'degens')]
from mathutils import Vector
import penthouse, whale
out = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; sc.render.fps = 30
r, ms = __import__('assets').load('GothicBed_01'); r.location = penthouse.BED
WR, WM = whale.load(os.environ['WHALE']); whale.place(WR)
for nm in ['die', 'lose', 'hit']:
    a = whale.clip(nm); WR.animation_data.action = a; f0, f1 = a.frame_range; print('CLIP', nm, f0, f1)
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (1.8, -2.6, 2.3); cam.rotation_euler = (Vector((0, 0.4, 0.9)) - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 28
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.color_type = 'TEXTURE'; sc.render.resolution_x = 240; sc.render.resolution_y = 300
WR.animation_data.action = whale.clip('die'); f0, f1 = WR.animation_data.action.frame_range
for i, fr in enumerate([f0 + (f1 - f0) * k / 7 for k in range(8)]):
    sc.frame_set(int(fr)); hp = WR.matrix_world @ WR.pose.bones['mixamorig:Hips'].head
    print('DIE', i, int(fr), 'hips', tuple(round(x, 2) for x in hp))
    sc.render.filepath = f'{out}/d{i}.png'; bpy.ops.render.render(write_still=True)
