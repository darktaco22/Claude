"""Quick look: both sets with the units in place. blender -b -P lookdev.py -- OUTDIR"""
import bpy, sys, os, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'degens'), os.path.join(H, '..', 'whale')]
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30
import game, sets
OUT = sys.argv[-1]; os.makedirs(OUT, exist_ok=True)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16; sc.cycles.use_denoising = True
sc.render.resolution_x = 540; sc.render.resolution_y = 960
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.08, 0.16, 1)
T = sets.tunnel(); A = sets.arena()
U = {}
for i, (k, x, y) in enumerate((('giga', -1.2, 2.5), ('whale', 1.2, 3.5), ('bonk', -1.1, 0.0), ('useless', 0.6, -0.8))):
    u = game.Unit(k); u.ctrl.location = (sets.TX + x, y, 0); u.ctrl.rotation_euler.z = 0; u.play([(0, 'idle', 1, 10)]); U[k] = u
g = game.Unit('goat', 'goat'); g.ctrl.location = (-4, -5, 0); g.ctrl.rotation_euler.z = math.pi; g.play([(0, 'ready', 1, 10)])
u2 = game.Unit('useless', 'u2'); u2.ctrl.location = (-3, -9.5, 0); u2.ctrl.rotation_euler.z = 0; u2.play([(0, 'ready', 1, 10)])
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 2.0; sun.data.color = (0.75, 0.85, 1.0)
sun.rotation_euler = (math.radians(60), 0, math.radians(200)); sc.collection.objects.link(sun)
T['choose'].location = (sets.TX + 0.6, -0.8, sets.TH - 0.1); T['choose'].rotation_euler = (0, 0, 0); T['choose'].data.energy = 600
T['beam'].location = (sets.TX + 0.6, -0.8, sets.TH / 2); T['beam_mat'].node_tree.nodes['strength'].inputs[1].default_value = 1.5
cd = bpy.data.cameras.new('c'); cam = bpy.data.objects.new('c', cd); sc.collection.objects.link(cam); sc.camera = cam
cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
def shot(name, pos, tgt, lens, f=1):
    cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler(); cd.lens = lens
    sc.frame_set(f); sc.render.filepath = f'{OUT}/{name}.png'; bpy.ops.render.render(write_still=True)
shot('arena_hi', (0, -30, 16), (0, 0, 0), 22)
shot('arena', (-6.5, -15.5, 1.3), (-4, -3, 1.2), 22)
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/look.blend')
