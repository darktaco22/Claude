"""
Downloads the game's 3D models (.glb / .gltf) from the live site, for the runway.

    python3 fetch_models.py [--site https://memeroyale.imaginestudio.fun] [--out models]

Reads the page and the JavaScript it loads (following same-site script imports a few levels deep), collects every
path ending in .glb or .gltf, and downloads each one. Props come along too; runway_showcase.py skips anything
without a rig, so only the characters walk. If the game builds model paths at runtime (e.g. `models/${id}.glb`),
nothing literal is found: then open the site in a browser, watch the network tab for .glb requests, and put the files
in the folder by hand.
"""
import os, re, sys, urllib.parse, urllib.request

argv = sys.argv[1:]
A = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
SITE = A("--site", "https://memeroyale.imaginestudio.fun").rstrip("/") + "/"
OUT = os.path.abspath(A("--out", os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")))
HOST = urllib.parse.urlparse(SITE).netloc

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (runway-fetch)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

seen, queue, models = set(), [SITE], set()
model_re = re.compile(r"""["'`]([^"'`\s<>()]+?\.(?:glb|gltf))(?:\?[^"'`\s]*)?["'`]""", re.I)
script_re = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+\.m?js(?:\?[^"']*)?)["']|(?:import\s*\(?|from\s+)\s*["']([^"']+\.m?js)["']|["']([./\w-]+/[\w.-]+\.m?js)["']""")
while queue and len(seen) < 80:
    url = queue.pop(0)
    if url in seen: continue
    seen.add(url)
    try:
        text = get(url).decode("utf-8", "replace")
    except Exception as e:
        print(f"  ! {url}: {e}"); continue
    for m in model_re.finditer(text):
        models.add(urllib.parse.urljoin(url, m.group(1)))
    for m in script_re.finditer(text):
        js = next(g for g in m.groups() if g)
        nxt = urllib.parse.urljoin(url, js)
        if urllib.parse.urlparse(nxt).netloc == HOST and nxt not in seen:
            queue.append(nxt)
print(f"scanned {len(seen)} files, found {len(models)} model paths")
os.makedirs(OUT, exist_ok=True)
ok = 0
for u in sorted(models):
    name = os.path.basename(urllib.parse.urlparse(u).path)
    dst = os.path.join(OUT, name)
    if os.path.exists(dst):
        ok += 1; continue
    try:
        data = get(u)
        with open(dst, "wb") as f: f.write(data)
        ok += 1; print(f"  {name}  {len(data) / 1e6:.1f} MB")
    except Exception as e:
        print(f"  ! {u}: {e}")
print(f"{ok} models in {OUT}")
if not ok:
    sys.exit(1)
