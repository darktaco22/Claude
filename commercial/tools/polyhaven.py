"""Download CC0 assets from Poly Haven (models, HDRIs, textures) and load them in Blender.

    python3 polyhaven.py DEST model grass_bermuda_01 1k
    python3 polyhaven.py DEST hdri  kloofendal_48d_partly_cloudy_puresky 2k
    python3 polyhaven.py DEST tex   aerial_grass_rock 2k
    python3 polyhaven.py DEST list  models nature        # ids by popularity

In Blender:  objs = polyhaven.append_model('DEST', 'grass_bermuda_01', '1k')
"""
import json, os, sys, urllib.request

API = 'https://api.polyhaven.com'
UA = {'User-Agent': 'asset-fetch'}


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def _save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _get(url)
    with open(path + '.part', 'wb') as f:
        f.write(data)
    os.replace(path + '.part', path)
    return path


def fetch(dest, kind, aid, res='1k'):
    files = json.loads(_get(f'{API}/files/{aid}'))
    d = os.path.join(dest, aid)
    if kind == 'hdri':
        x = files['hdri'][res]['exr']
        return _save(x['url'], os.path.join(d, f'{aid}_{res}.exr'))
    x = files['blend'][res]['blend']
    p = _save(x['url'], os.path.join(d, f'{aid}_{res}.blend'))
    for rel, inc in x.get('include', {}).items():
        _save(inc['url'], os.path.join(d, rel))
    return p


def listing(typ='models', cat=None):
    q = f'{API}/assets?t={typ}' + (f'&c={cat}' if cat else '')
    d = json.loads(_get(q))
    return sorted(d.items(), key=lambda kv: -kv[1].get('download_count', 0))


def append_model(dest, aid, res='1k'):
    import bpy
    p = fetch(dest, 'model', aid, res)
    with bpy.data.libraries.load(p, link=False) as (src, dst):
        dst.objects = list(src.objects)
    return [o for o in dst.objects if o is not None]


def pick(objs, lod='LOD1', skip=('geometry', 'geonodes', 'leaf_UV')):
    """Usable meshes only: one detail level, no helper objects (Poly Haven files ship every variant and LOD)."""
    out = [o for o in objs if o.type == 'MESH' and not any(k in o.name for k in skip)]
    with_lod = [o for o in out if o.name.endswith(lod)]
    if with_lod:
        out = with_lod
    for o in out:
        o.location = (0, 0, 0)
    return out


def append_material(dest, aid, res='2k'):
    import bpy
    p = fetch(dest, 'tex', aid, res)
    with bpy.data.libraries.load(p, link=False) as (src, dst):
        dst.materials = list(src.materials)
    return dst.materials[0]


if __name__ == '__main__':
    dest, kind = sys.argv[1], sys.argv[2]
    if kind == 'list':
        for k, v in listing(sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)[:80]:
            print(k, v.get('polycount', ''), ','.join(v['categories'][:4]))
    else:
        print(fetch(dest, kind, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '1k'))
