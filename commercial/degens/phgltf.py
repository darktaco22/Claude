import json, os, sys, urllib.request
UA={'User-Agent':'scene-builder/1.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA)).read()
for aid in sys.argv[1:]:
    d=json.loads(get(f'https://api.polyhaven.com/files/{aid}')); g=d['gltf']['2k']['gltf']; out=f'ph/{aid}/gltf'; os.makedirs(out,exist_ok=True)
    open(f"{out}/{aid}.gltf",'wb').write(get(g['url']))
    for rel,inc in g.get('include',{}).items():
        p=f"{out}/{rel}"; os.makedirs(os.path.dirname(p),exist_ok=True); open(p,'wb').write(get(inc['url']))
    print('ok',aid)
