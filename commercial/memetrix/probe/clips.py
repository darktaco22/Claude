"""Pose sheet: each clip of a character at 4 moments, front and side views."""
import bpy, math, sys
from mathutils import Vector
who = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
rig = bpy.data.objects['RIG-' + who]
arm = next(o for o in rig.children_recursive if o.type == 'ARMATURE')
for o in bpy.data.objects:                                   # hide every other actor and all props
    if o.name.startswith('RIG-') and o != rig:
        for c in o.children_recursive: c.hide_render = True
for o in bpy.data.objects:
    if o.parent is None and o.type == 'MESH' and not o.name.startswith(('base_', 'floor')): pass
rig.animation_data_clear(); rig.location = (0, 0, -100); rig.rotation_euler = (0, 0, 0)
tilt = bpy.data.objects['TILT-' + who]; tilt.animation_data_clear(); tilt.rotation_euler = (0, 0, 0)
for t in arm.animation_data.nla_tracks: t.mute = True
for c in arm.pose.bones:
    for k in c.constraints: k.mute = True
arm.animation_data.action = None
L = bpy.data.objects.new('pL', bpy.data.lights.new('pL', 'SUN')); sc.collection.objects.link(L); L.data.energy = 4; L.rotation_euler = (math.radians(50), 0, math.radians(20))
w = bpy.data.worlds[0] if bpy.data.worlds else None
cam = sc.camera; cam.animation_data_clear(); cam.data.type = 'ORTHO'; cam.data.ortho_scale = {'slerf': 3.2, 'farter': 2.8, 'bome': 3.0}.get(who, 2.6); cam.data.dof.use_dof = False
for c in bpy.data.collections:
    if c.name.startswith('L_'): c.hide_render = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 360, 360, 100
sc.cycles.samples = 4; sc.render.use_motion_blur = False; sc.render.film_transparent = False
clips = [a for a in bpy.data.actions if a.name.startswith((CHAR := {'anon': 'zcat', 'slerf': 'slerf', 'bome': 'bome', 'farter': 'farter'}.get(who, who)) + ':')]
for a in clips:
    arm.animation_data.action = a
    f0, f1 = a.frame_range
    for j, u in enumerate((0.15, 0.4, 0.65, 0.95)):
        sc.frame_set(int(f0 + (f1 - f0) * u))
        for view, (loc, rot) in {'front': ((0, -6, -99.1), (math.pi / 2, 0, 0)), 'side': ((6, 0, -99.1), (math.pi / 2, 0, math.pi / 2))}.items():
            cam.location = loc; cam.rotation_euler = rot
            sc.render.filepath = f'/root/mx_probe/clips/{who}_{a.name.split(":")[1]}_{j}_{view}.png'
            bpy.ops.render.render(write_still=True)
    print('CLIP', a.name, f0, f1)
