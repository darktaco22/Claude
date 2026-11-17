"""Poly Haven fetcher: models as glTF (+bin/textures), textures as jpg maps. usage: phfetch.py name[:tex] ... (res via RES env)"""
import json, os, sys, urllib.request
UA = {'User-Agent': 'reaping-scene-builder/1.0'}; RES = os.environ.get('RES', '2k')
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
for a in sys.argv[1:]:
    aid, _, kind = a.partition(':'); out = f'ph/{aid}'; os.makedirs(out, exist_ok=True)
    try:
        d = json.loads(get(f'https://api.polyhaven.com/files/{aid}'))
        if kind == 'tex':
            for m in ['Diffuse', 'nor_gl', 'Rough', 'Displacement', 'arm', 'AO', 'Metal']:
                if m in d and RES in d[m]:
                    f = d[m][RES].get('jpg') or d[m][RES].get('png'); p = f"{out}/{os.path.basename(f['url'])}"
                    if not os.path.exists(p): open(p, 'wb').write(get(f['url']))
        else:
            g = d['gltf'][RES]['gltf']; p = f'{out}/{aid}.gltf'
            if not os.path.exists(p): open(p, 'wb').write(get(g['url']))
            for rel, inc in g.get('include', {}).items():
                q = f'{out}/{rel}'; os.makedirs(os.path.dirname(q), exist_ok=True)
                if not os.path.exists(q): open(q, 'wb').write(get(inc['url']))
        print('ok', aid)
    except Exception as e: print('FAIL', aid, e)
