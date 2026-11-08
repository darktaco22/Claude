import bpy, sys, math
from mathutils import Vector
sys.path.insert(0,'/home/user/Claude/commercial/degens'); import assets
bpy.ops.wm.read_factory_settings(use_empty=True)
r,ms=assets.load('GothicBed_01'); bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get(); sc=bpy.context.scene
# mattress / pillow height profile along the bed's centre line and across it
for y in [-0.9,-0.6,-0.3,0,0.3,0.6,0.8,0.95]:
    row=[]
    for x in [-0.6,-0.3,0,0.3,0.6]:
        hit,loc,*_=sc.ray_cast(dg,Vector((x,y,3)),Vector((0,0,-1))); row.append(round(loc.z,2) if hit else None)
    print('PROF y',y,row)
print([ (m.name, len(m.data.vertices), [s.material.name for s in m.material_slots if s.material]) for m in ms])
