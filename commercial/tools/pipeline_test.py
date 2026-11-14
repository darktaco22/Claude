import bpy, sys, os, json, math
sys.path.insert(0, '/home/user/Claude/commercial/tools'); import pipeline
ok = lambda name, cond: print('TEST', name, 'PASS' if cond else 'FAIL')
T = '/root/tools/pipetest'; os.makedirs(T, exist_ok=True)
# --- library file with prefixed collections
bpy.ops.wm.read_factory_settings(use_empty=True)
for n in ('EN-rock_a', 'EN-rock_b', 'EN-plant_a'):
    c = bpy.data.collections.new(n); bpy.context.scene.collection.children.link(c)
    m = bpy.data.meshes.new(n); m.from_pydata([(0,0,0),(1,0,0),(0,1,0)], [], [(0,1,2)])
    c.objects.link(bpy.data.objects.new(n, m))
bpy.ops.wm.save_as_mainfile(filepath=T + '/lib.blend')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.save_as_mainfile(filepath=T + '/set.blend')
json.dump({'collections': {'rocks': {'link': [{'file': '//lib.blend', 'prefix': 'EN-rock_'}]},
                           'plants': {'link': [{'file': '//lib.blend', 'prefix': 'EN-plant_'}]}}}, open(T + '/set.json', 'w'))
sc = bpy.context.scene
r = pipeline.link_from_json(sc, '//set.json')
ok('link_from_json', len(r['rocks']) == 2 and len(r['plants']) == 1)
r2 = pipeline.link_from_json(sc, '//set.json')
ok('link twice adds nothing', len(r2['rocks']) == 0 and len(sc.collection.children['rocks'].objects) == 2)
ok('ensure_collection reuse', pipeline.ensure_collection(sc, 'rocks') == sc.collection.children['rocks'])
# --- real game character: bones, vertex groups, fcurves
bpy.ops.import_scene.gltf(filepath='/home/user/Claude/commercial/comeback/models/pepe.glb')
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == arm]
nb = len(arm.data.bones); vg0 = sorted(g.name for g in meshes[0].vertex_groups)
act = bpy.data.actions[0]; paths0 = [f.data_path for f in act.fcurves][:3]
n = pipeline.prefix_bones(arm, 'pepe_')
vg1 = sorted(g.name for g in meshes[0].vertex_groups)
ok('prefix_bones count', n == nb and all(b.name.startswith('pepe_') for b in arm.data.bones))
ok('vertex groups follow', all(g.startswith('pepe_') for g in vg1 if g[5:] in vg0) and len(vg1) == len(vg0))
ok('fcurve paths follow', all('pepe_' in f.data_path for f in act.fcurves if 'pose.bones' in f.data_path))
ok('prefix twice is no-op', pipeline.prefix_bones(arm, 'pepe_') == 0)
fc = next(pipeline.iter_fcurves(act, 'location', 2))
a0, a1 = act.frame_range; v0 = fc.evaluate(a0 + 3)
pipeline.offset_fcurve(fc, value=0.5)
ok('offset_fcurve', abs(fc.evaluate(a0 + 3) - (v0 + 0.5)) < 1e-4)
length0 = a1 - a0; pipeline.retime_action(act, 0.5, pivot=a0)
ok('retime_action', abs((act.frame_range[1] - act.frame_range[0]) - length0 * 0.5) < 0.51)
ok('sample_fcurve', len(pipeline.sample_fcurve(fc, range(5))) == 5)
ok('rename_objects', pipeline.rename_objects(meshes, {'Mesh': 'Body', 'mesh': 'body'}) >= 0)
pipeline.move_to_collection(arm, pipeline.ensure_collection(sc, 'chars'))
ok('move_to_collection', [c.name for c in arm.users_collection] == ['chars'])
# --- batch render with cleanup
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
cd = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -6, 1.2); cam.rotation_euler = (math.radians(88), 0, 0)
sun = bpy.data.objects.new('S', bpy.data.lights.new('S', 'SUN')); sc.collection.objects.link(sun); sun.rotation_euler = (0.9, 0, 0.5); sun.data.energy = 4
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = sc.render.resolution_y = 256
n0 = len(bpy.data.objects); m0 = len(bpy.data.meshes)
done = pipeline.batch_render_models(sc, '/home/user/Claude/commercial/comeback/models', T + '/thumbs', limit=6)
ok('batch rendered', len(done) == 6 and all(p.exists() for p in done))
ok('batch leaves no leftovers', len(bpy.data.objects) == n0 and len(bpy.data.meshes) == m0 and len(bpy.data.actions) == 0)
ok('batch resumes', len(pipeline.batch_render_models(sc, '/home/user/Claude/commercial/comeback/models', T + '/thumbs', limit=6)) == 0)
