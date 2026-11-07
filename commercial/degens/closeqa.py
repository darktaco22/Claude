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
if which == 'cighand':
    shoot('h_front', 10, 'earl', 'wrist.R', 0.35, 0.0, 0.15, 45, Vector((0.05, -0.06, 0)))
    shoot('h_side', 10, 'earl', 'wrist.R', 0.35, -1.4, 0.15, 45, Vector((0.05, -0.06, 0)))
    shoot('h_top', 10, 'earl', 'wrist.R', 0.15, -0.6, 0.35, 45, Vector((0.05, -0.06, 0)))
    raise SystemExit
if which == 'cloth':
    shoot('pam_chest', 14, 'pam', 'spine02', 0.7, 0.1, 0.05, 40)
    shoot('linda_chest', 20.4, 'linda', 'spine02', 0.7, -0.2, 0.05, 40)
    shoot('earl_cuff', 10, 'earl', 'wrist.R', 0.4, -1.2, 0.1, 45)
    shoot('pam_cuff', 14, 'pam', 'wrist.L', 0.4, 1.2, 0.1, 45)
    raise SystemExit
if which == 'lips':
    shoot('drag_front', 25.6, 'earl', 'head', 0.42, -0.25, -0.1, 55, Vector((0, -0.08, -0.05)))
    shoot('drag_side', 25.6, 'earl', 'head', 0.42, -1.3, -0.1, 55, Vector((0, -0.08, -0.05)))
    shoot('mouth_front', 24.0, 'earl', 'head', 0.42, -0.2, -0.1, 55, Vector((0, -0.08, -0.05)))
    shoot('mouth_side', 24.0, 'earl', 'head', 0.42, -1.3, -0.1, 55, Vector((0, -0.08, -0.05)))
    raise SystemExit
if which == 'cig':
    shoot('drag_side', 25.6, 'earl', 'head', 0.4, -1.2, -0.08, 55)
    shoot('drag_front', 25.6, 'earl', 'head', 0.45, -0.3, -0.08, 55)
    shoot('mouth_side', 24.0, 'earl', 'head', 0.4, -1.2, -0.08, 55)
    shoot('rest_cig', 10, 'earl', 'wrist.R', 0.45, -0.5, 0.2, 50)
    shoot('earl_body', 20, 'earl', 'spine02', 1.4, 0.3, 0.1, 35)
    raise SystemExit
if which == 'ears':
    shoot('earl_earR', 10, 'earl', 'head', 0.4, -1.5, 0.0, 50)
    shoot('earl_earL', 10, 'earl', 'head', 0.4, 1.5, 0.0, 50)
    shoot('earl_chin', 24, 'earl', 'head', 0.45, 0.2, -0.15, 50)
    raise SystemExit
if which == 'iss':
    shoot('earl_ear_back', 10, 'earl', 'head', 0.45, 2.4, 0.0, 50)
    shoot('earl_line', 20, 'earl', 'spine02', 1.0, -0.6, 0.1, 40)
    shoot('linda_phone', 36, 'linda', 'wrist.R', 0.6, 0.6, 0.15, 40)
    shoot('linda_neet_feet', 10, 'linda', 'foot.L', 0.9, 0.5, 0.35, 35)
    shoot('clap', 16.3, 'pam', 'wrist.L', 0.5, 0.5, 0.15, 45)
    raise SystemExit
if which == 'hands2':
    shoot('chad_L', 10, 'chad', 'wrist.L', 0.6, 1.4, 0.05, 35)
    shoot('chad_R', 10, 'chad', 'wrist.R', 0.6, -1.4, 0.05, 35)
    shoot('pam_L', 10, 'pam', 'wrist.L', 0.6, 1.4, 0.05, 35)
    shoot('linda_L', 10, 'linda', 'wrist.L', 0.6, 1.4, 0.05, 35)
    shoot('chad_front', 10, 'chad', 'root', 1.4, 0.2, 0.3, 35, Vector((0, 0, -0.1)))
    raise SystemExit
if which == 'hands':
    shoot('chad_L', 10, 'chad', 'wrist.L', 0.5, 1.2, 0.25, 40)
    shoot('chad_R', 10, 'chad', 'wrist.R', 0.5, -1.2, 0.25, 40)
    shoot('pam_L', 10, 'pam', 'wrist.L', 0.5, 1.2, 0.25, 40)
    shoot('earl_face', 24, 'earl', 'head', 0.7, 0.5, 0.0, 45)
    shoot('earl_face2', 24, 'earl', 'head', 0.7, -0.6, -0.1, 45)
    raise SystemExit
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
