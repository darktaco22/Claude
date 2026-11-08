"""Look-dev still of the set: blender -b -P lookdev.py -- OUT.png [camx camy camz tx ty tz lens]"""
import bpy, sys, os, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'degens')]
from mathutils import Vector
import penthouse, whale
A = sys.argv[sys.argv.index('--') + 1:]; out = A[0]
cam_p = Vector([float(x) for x in A[1:4]]) if len(A) > 3 else Vector((0.35, -3.3, 1.55))
tgt = Vector([float(x) for x in A[4:7]]) if len(A) > 6 else Vector((-0.3, 0.6, 1.0)); lens = float(A[7]) if len(A) > 7 else 24
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
S = penthouse.build()
rig, mesh = whale.load(os.environ['WHALE']); whale.place(rig)
whale.schedule(rig, [(0, 'idle', 0, 1, 10)])
P = whale.body_points(mesh, range(1, 145, 12))
if not os.environ.get("NODUVET"): penthouse.duvet(P, top_z=whale.HIP.z + 0.2)
sc.frame_set(30)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = cam_p; cam.rotation_euler = (tgt - cam_p).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
def light(name, kind, loc, energy, color, size=0.3, tgt=None):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); L.data.energy = energy; L.data.color = color
    if kind == 'AREA': L.data.size = size
    elif kind == 'POINT': L.data.shadow_soft_size = size
    L.location = loc; sc.collection.objects.link(L)
    if tgt: L.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return L
light('lamp', 'POINT', (-1.15, 0.95, 1.05), 60, (1.0, 0.62, 0.32), 0.12)          # bedside lamp, warm
light('monitor', 'AREA', (1.0, 0.75, 1.25), 15, (0.3, 1.0, 0.55), 0.25, (0, 0.4, 1.0))
light('city', 'AREA', (-2.2, 2.2, 1.8), 120, (0.45, 0.55, 0.9), 1.6, (0, 0, 0.8))  # cool spill through the window
light('rim', 'AREA', (1.6, 1.6, 2.6), 60, (0.7, 0.75, 1.0), 1.0, (0, 0.3, 1.0))
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.3
sc.render.resolution_x = 540; sc.render.resolution_y = 960; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
