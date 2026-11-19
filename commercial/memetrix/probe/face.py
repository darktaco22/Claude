import bpy, sys, math
from mathutils import Vector
who = sys.argv[sys.argv.index('--')+1]; nums=[float(x) for x in sys.argv[sys.argv.index('--')+2:] if x[0].isdigit()]; eye,half=nums
sc=bpy.context.scene
for f in range(1,3): sc.frame_set(1)
rig=bpy.data.objects['RIG-'+who]
for c in rig.children_recursive:
    pass
# move every other rig away
for o in bpy.data.objects:
    if o.name.startswith('RIG-') and o!=rig:
        for c in o.children_recursive: c.hide_render=True
print('RIG', rig.location, rig.rotation_euler, [m.name for m in bpy.data.materials if 'eye' in m.name.lower()][:20])
cam=sc.camera
cam.animation_data_clear()
cam.data.type='ORTHO'; cam.data.ortho_scale=half*2; cam.data.dof.use_dof=False
base=rig.matrix_world.translation
SIDE='SIDE' in sys.argv
if SIDE:
    cam.location=base+Vector((4,-0.0,eye)); cam.rotation_mode='XYZ'; cam.rotation_euler=(math.pi/2,0,math.pi/2)
else:
    cam.location=base+Vector((0,-4,eye)); cam.rotation_mode='XYZ'; cam.rotation_euler=(math.pi/2,0,0)
sc.render.resolution_x=sc.render.resolution_y=800; sc.render.resolution_percentage=100
sc.cycles.samples=8; sc.render.use_motion_blur=False
for o in bpy.data.objects:
    if o.name.startswith('haze') or o.name.startswith('shades_') and 'NOSH' in sys.argv: o.hide_render=True
L=bpy.data.objects.new('probeL',bpy.data.lights.new('probeL','SUN')); sc.collection.objects.link(L); L.data.energy=4; L.rotation_euler=(math.radians(70),0,0)
bpy.data.objects['camfill'].data.energy=0
sc.render.filepath=f'/root/mx_probe/{who}_face20'+('_side' if SIDE else '')+('_nosh' if 'NOSH' in sys.argv else '')+'.png'
bpy.ops.render.render(write_still=True)
print('CENTER', base.x, base.z+eye, 'HALF', half)
