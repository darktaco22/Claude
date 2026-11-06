"""Close-up QA with correct framing: blender -b scene.blend -P closeqa.py -- outdir"""
import bpy, sys, math
from mathutils import Vector
out = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene; sc.render.resolution_percentage = 40; sc.cycles.samples = 8
cam = sc.camera; cam.animation_data_clear(); cam.data.animation_data_clear(); cam.data.dof.use_dof = False
cam.rotation_mode = 'QUATERNION'
def shoot(name, t, rig, bone, dist, yaw, up=0.1, lens=50, off=Vector()):
    sc.frame_set(int(t * 30) + 1); bpy.context.view_layer.update()
    r = bpy.data.objects[rig]; tg = r.matrix_world @ r.pose.bones[bone].head + off
    fwd = r.matrix_world.to_3x3() @ Vector((0, -1, 0)); fwd.z = 0; fwd.normalize()
    side = Vector((fwd.y, -fwd.x, 0))
    p = tg + (fwd * math.cos(yaw) + side * math.sin(yaw)) * dist + Vector((0, 0, up))
    cam.location = p; cam.rotation_quaternion = (tg - p).to_track_quat('-Z', 'Y'); cam.data.lens = lens
    sc.render.filepath = f'{out}/qa_{name}.png'; bpy.ops.render.render(write_still=True)
import os
which = os.environ.get('CQ', 'all')
if which == 'set2':
    shoot('neet_side', 5, 'neet_rig', 'mixamorig:Hips', 2.2, 1.3, 0.1, 30)
    shoot('neet_front', 20, 'neet_rig', 'mixamorig:Hips', 2.4, 0.2, 0.4, 30)
    shoot('neet_fist', 29.3, 'neet_rig', 'mixamorig:Hips', 2.4, 0.5, 0.4, 30)
    shoot('earl_cig_rest', 10, 'earl', 'wrist.R', 0.5, -0.9, 0.15, 45)
    shoot('earl_cig_front', 10, 'earl', 'wrist.R', 0.55, 0.0, 0.25, 45)
    shoot('earl_drag', 25.6, 'earl', 'head', 0.6, -0.5, 0.0, 50)
    shoot('earl_mouth', 24.0, 'earl', 'head', 0.6, 0.2, 0.0, 50)
    shoot('pam_side', 10, 'pam', 'root', 1.8, 1.3, 0.1, 30, Vector((0, 0, -0.1)))
    shoot('chad_can', 10, 'chad', 'wrist.R', 0.5, -0.4, 0.2, 45)
    shoot('linda_phone', 36.0, 'linda', 'head', 0.7, 0.4, 0.0, 40)
    raise SystemExit
for k in ['chad', 'earl', 'pam', 'linda']:
    shoot(f'{k}_seat', 10, k, 'root', 1.6, 1.25, 0.05, 30, Vector((0, 0, -0.15)))
shoot('neet_seat', 10, 'neet_rig', 'mixamorig:Hips', 2.0, 1.2, 0.1, 28)
shoot('neet_front', 20, 'neet_rig', 'mixamorig:Hips', 2.2, 0.3, 0.3, 28)
shoot('earl_cig', 10, 'earl', 'wrist.R', 0.35, -0.6, 0.12, 50)
shoot('earl_drag', 25.6, 'earl', 'wrist.R', 0.45, -0.7, 0.05, 50)
shoot('pam_mug', 10, 'pam', 'wrist.L', 0.35, 0.7, 0.12, 50)
shoot('linda_mug', 10, 'linda', 'wrist.L', 0.35, 0.7, 0.12, 50)
shoot('chad_can', 10, 'chad', 'wrist.R', 0.35, -0.7, 0.12, 50)
shoot('linda_phone', 36.0, 'linda', 'wrist.R', 0.45, 0.3, 0.1, 50)
shoot('earl_phone', 36.0, 'earl', 'wrist.L', 0.45, 0.4, 0.1, 50)
