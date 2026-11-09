"""Cast lineup still: blender -b -P lineup.py -- OUT.png"""
import bpy, sys, os, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'whale'), os.path.join(H, '..', 'degens')]
from mathutils import Vector
import cast
out = sys.argv[sys.argv.index('--') + 1]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
for i, k in enumerate(cast.KEYS):
    rig, body, parts = cast.build(k); rig.location.x = (i - 2) * 0.85
for j, (n, sc_) in enumerate([('useless', 0.34), ('slerf', 0.95)]):
    r, m = cast.load_unit(os.path.join(os.environ['GD'], n + '.glb'), n); r.location = (0.55 + j * 0.9, 0, 0); r.scale = (sc_,) * 3
    print('UNIT', n, sorted(a.name + ':' + str(int(a.frame_range[1])) for a in bpy.data.actions if a.name.endswith(n + '_rig')))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -5.2, 1.1); cam.rotation_euler = (math.radians(90), 0, 0); cam.data.lens = 40
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 0.5
L = bpy.data.objects.new('k', bpy.data.lights.new('k', 'AREA')); L.data.energy = 400; L.data.size = 3; L.location = (1.5, -3, 3); sc.collection.objects.link(L)
L.rotation_euler = (Vector((0, 0, 1)) - L.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x = 1200; sc.render.resolution_y = 800; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
