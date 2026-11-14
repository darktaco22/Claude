import bpy, sys, time, os
sys.path.insert(0, '/home/user/Claude/commercial/tools'); import assets, preflight
M = '/home/user/Claude/commercial/comeback/models'; LIB = '/root/tools/chars.blend'
ok = lambda name, cond: print('TEST', name, 'PASS' if cond else 'FAIL')
ids = ['pepe', 'troll', 'whale', 'giga', 'wojak', 'popcat']
bpy.ops.wm.read_factory_settings(use_empty=True); t = time.time()
for uid in ids: bpy.ops.import_scene.gltf(filepath=f'{M}/{uid}.glb')
t_glb = time.time() - t
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; t = time.time()
chars = assets.load_many(LIB, ids, sc.collection, height=2.0)
t_lib = time.time() - t
print(f'TIME glb {t_glb:.2f}s  library {t_lib:.2f}s for {len(ids)} characters; library holds {len(assets.names(LIB))}; file {os.path.getsize(LIB)/1e6:.0f} MB')
c = chars[0]
ok('all six distinct', len({c['armature'] for c in chars}) == 6 and all('idle' in c['clips'] for c in chars))
ok('clips loaded', 'idle' in c['clips'] and 'run' in c['clips'])
ok('props kept', c['collection']['source'] == 'pepe.glb' and c['collection']['height'] > 0)
ok('two copies independent', assets.load(LIB, 'pepe', sc.collection)['armature'] != c['armature'])
try: assets.load(LIB, 'nobody', sc.collection); ok('unknown id raises', False)
except KeyError: ok('unknown id raises', True)
p = preflight.check(sc)
ok('preflight: no camera', any('camera' in m for l, m in p if l == 'ERROR'))
cam = bpy.data.objects.new('C', bpy.data.cameras.new('C')); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'CYCLES'; sc.render.filepath = '/root/tools/pf/out_'
img = bpy.data.images.new('x', 4, 4); img.source = 'FILE'; img.filepath = '/nonexistent/tex.png'
p = preflight.check(sc, 1, 10, sample_frames=(1, 5))
ok('preflight: missing image', any('image missing' in m for l, m in p))
ok('preflight: black frames', any('black' in m for l, m in p))
ok('preflight: persistent data', any('persistent' in m for l, m in p))
bpy.data.images.remove(img); sc.render.use_persistent_data = True
sc.collection.objects.link(bpy.data.objects.new('S', bpy.data.lights.new('S', 'SUN')))
ok('preflight: clean scene passes', not [m for l, m in preflight.check(sc, 1, 10, (1, 5)) if l == 'ERROR'])
