import bpy, sys, math, os
from mathutils import Vector, Euler
sys.path.insert(0,'/home/user/Claude/commercial/degens'); import assets
ARGS=sys.argv[sys.argv.index('--')+1:]; tilt=float(ARGS[0]); out=ARGS[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
r,ms=assets.load('GothicBed_01')
bpy.ops.import_scene.gltf(filepath=os.environ['WHALE'])
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
rig=bpy.data.objects['whale_rig']; mesh=bpy.data.objects['whale']
rig.animation_data_create(); rig.animation_data.action=bpy.data.actions['idle_whale_rig']
rig.rotation_mode='XYZ'; rig.rotation_euler=Euler((math.radians(tilt),0,0))
sc.frame_set(1); bpy.context.view_layer.update()
def mz():
    dg=bpy.context.evaluated_depsgraph_get(); e=mesh.evaluated_get(dg); M=mesh.matrix_world
    return [M@v.co for v in e.data.vertices]
HIP=Vector((float(ARGS[2]),float(ARGS[3]),float(ARGS[4])))
pb=rig.pose.bones['mixamorig:Hips']; h=rig.matrix_world@pb.head; rig.location += HIP-h
bpy.context.view_layer.update()
for b in ['mixamorig:LeftFoot','mixamorig:Head','mixamorig:Spine2']: print('BONE',b,tuple(round(x,2) for x in rig.matrix_world@rig.pose.bones[b].head))
bpy.context.view_layer.update(); P=mz()
print('WHALE box', [round(min(p[i] for p in P),2) for i in range(3)], [round(max(p[i] for p in P),2) for i in range(3)], 'loc', tuple(round(x,2) for x in rig.location))
cam=bpy.data.objects.new('c',bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(1.3,-2.6,1.5); d=Vector((0,0.3,0.9))-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); cam.data.lens=30
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[1].default_value=0.6
L=bpy.data.objects.new('l',bpy.data.lights.new('l','AREA')); L.data.energy=300; L.data.size=2; L.location=(1.5,-1,3); sc.collection.objects.link(L)
L.rotation_euler=(Vector((0,0,0.6))-L.location).to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES'; sc.cycles.samples=16; sc.cycles.use_denoising=True; sc.render.resolution_x=360; sc.render.resolution_y=480; sc.render.filepath=out
bpy.ops.render.render(write_still=True)
