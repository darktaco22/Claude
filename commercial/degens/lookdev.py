import bpy, sys, time, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--')+1:]; out = a[0]; samples = int(a[1]) if len(a)>1 else 32
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920; sc.render.resolution_percentage = 50
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.05,0.06,0.05,1)
def area(name, loc, rot, size, e, col=(1,1,1)):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = e; l.size = size; l.color = col; o = bpy.data.objects.new(name, l); o.location = loc; o.rotation_euler = rot; sc.collection.objects.link(o)
area('key', (1.5,-3,3), (math.radians(55),0,math.radians(25)), 2, 600)
area('fill', (-3,-2,2), (math.radians(65),0,math.radians(-55)), 3, 200, (0.85,1,0.9))
area('top', (0,0,3.4), (0,0,0), 1.5, 300, (0.9,1,0.92))
bpy.ops.mesh.primitive_plane_add(size=20)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
tgt = Vector(tuple(map(float, a[2].split(',')))) if len(a)>2 else Vector((0,0,1.0)); pos = Vector(tuple(map(float, a[3].split(',')))) if len(a)>3 else Vector((0,-4.2,1.2))
cam.location = pos; cam.rotation_euler = (tgt-pos).to_track_quat('-Z','Y').to_euler(); cam.data.lens = float(a[4]) if len(a)>4 else 35
t = time.time(); sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('RENDER', round(time.time()-t,1), 's')
