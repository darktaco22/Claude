import json, os, sys, urllib.request
UA={'User-Agent':'scene-builder/1.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA)).read()
def fetch(aid, res='2k', kind='blend'):
    d=json.loads(get(f'https://api.polyhaven.com/files/{aid}'))
    out=f'ph/{aid}'; os.makedirs(out,exist_ok=True)
    if kind=='tex':
        for m in ['Diffuse','diff','nor_gl','Rough','rough','Displacement','AO','arm']:
            if m in d and res in d[m]:
                f=d[m][res].get('jpg') or d[m][res].get('png'); p=f"{out}/{os.path.basename(f['url'])}"
                if not os.path.exists(p): open(p,'wb').write(get(f['url']))
        return
    if kind=='hdri':
        f=d['hdri'][res]['hdr']; open(f"{out}/{aid}.hdr",'wb').write(get(f['url'])); return
    b=d['blend'][res]['blend']; open(f"{out}/{aid}.blend",'wb').write(get(b['url']))
    for rel,inc in b.get('include',{}).items():
        p=f"{out}/{rel}"; os.makedirs(os.path.dirname(p),exist_ok=True)
        if not os.path.exists(p): open(p,'wb').write(get(inc['url']))
for a in sys.argv[1:]:
    aid,_,kind=a.partition(':'); 
    try: fetch(aid, kind=kind or 'blend'); print('ok',aid)
    except Exception as e: print('FAIL',aid,e)
