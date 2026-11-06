# Automatic glitch scan on a saved party.blend:
#  1. INSIDE: guests whose (posed) mesh intersects a prop or another guest, at several frames.
#  2. BLOCKED: at each featured moment, the guests the shot is about, and how much of each the camera actually sees
#     (rays from the camera to points over the body; a ray stopped first by a non-guest object counts as blocked).
#   blender -b party.blend -P scan.py -- [--frames 1,150,...]
import bpy, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FR = [int(x) for x in argv[argv.index("--frames") + 1].split(",")] if "--frames" in argv else [1, 120, 240, 360, 480, 600, 720, 840]
sc = bpy.context.scene
rigs = {o.name.split("_ctrl")[0]: o for o in bpy.data.objects if o.name.endswith("_ctrl")}
gmesh = {n: [m for r in c.children if r.type == "ARMATURE" for m in r.children if m.type == "MESH"] for n, c in rigs.items()}
mine = {m: n for n, ms in gmesh.items() for m in ms}
# things a guest is allowed to touch: floors, ground, water, the seats they sit on, their own props
SKIP = ("deck", "lawn", "terrain", "ground", "floor", "rug", "water", "pool", "tile", "coping", "grass", "beanbag", "crate",
        "puff", "cloud", "gas", "smoke", "confetti", "bill", "drop", "splash", "laser", "chamber", "string", "balcony", "hair", "dress",
        "bodice", "skirt", "beanie", "pompom", "band", "cig", "ember", "note", "cup", "cash", "bow", "parquet", "step", "plane",
        "doge_", "lbl", "line", "powder", "bubble", "fl_", "flamingo", "slab", "terr", "stone_floor", "path", "gravel")
def skip(o): return any(k in o.name.lower() for k in SKIP)
dg = bpy.context.evaluated_depsgraph_get()
def bvh_of(o):
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    verts = [mw @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    oe.to_mesh_clear()
    if not polys: return None, None
    lo = Vector(map(min, *verts)) if len(verts) > 1 else verts[0]; hi = Vector(map(max, *verts)) if len(verts) > 1 else verts[0]
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), (lo, hi)
def boxes_overlap(a, b, pad=0.0):
    return all(a[0][i] - pad <= b[1][i] and b[0][i] - pad <= a[1][i] for i in range(3))

static = [o for o in bpy.data.objects if o.type == "MESH" and o not in mine and not skip(o) and o.visible_get() and not o.hide_render]
print(f"SCAN {len(rigs)} guests, {len(static)} props")
sbvh = {}
def prop_bvh(o):
    if o.animation_data or (o.parent and o.parent.animation_data):   # moving props: rebuild every frame
        return bvh_of(o)
    if o not in sbvh: sbvh[o] = bvh_of(o)
    return sbvh[o]
found = {}
for f in FR:
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    G = {}
    for n, ms in gmesh.items():
        parts = [bvh_of(m) for m in ms]
        parts = [p for p in parts if p[0]]
        if parts: G[n] = parts
    names = list(G)
    for n in names:
        for (bv, bb) in G[n]:
            for o in static:
                b2 = o.bound_box; mw = o.matrix_world; pts = [mw @ Vector(p) for p in b2]
                ob = (Vector(map(min, *pts)), Vector(map(max, *pts)))
                if not boxes_overlap(bb, ob): continue
                pb, _ = prop_bvh(o)
                if pb and bv.overlap(pb):
                    found.setdefault((n, o.name), []).append(f)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for (ba, xa) in G[a]:
                for (bb_, xb) in G[b]:
                    if boxes_overlap(xa, xb) and ba.overlap(bb_):
                        found.setdefault((a, "GUEST " + b), []).append(f)
for (n, o), fs in sorted(found.items()):
    print(f"INSIDE {n:12s} x {o:40s} frames {sorted(set(fs))}")

# featured moments: (frames, guests the shot is about)
FEAT = [((170, 200, 230), ("moodeng", "zcat", "pudgy", "fwog", "popcat")), ((300, 330, 345), ("triplet", "giga", "pepe", "brett", "slerf")),
        ((380, 400, 420), ("whale", "wojakgirl", "doomergirl", "swordcat")), ((480, 510, 540), ("farter", "lmao", "troll", "michi")),
        ((590, 605, 620), ("ket", "cate")), ((690, 705), ("walter", "floki", "toshi")), ((740, 755, 770), ("wojak", "apu")),
        ((800, 815, 830), ("useless", "wif", "bonk", "pnut", "chillhouse"))]
cam = sc.camera
for frs, who in FEAT:
    for f in frs:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); cp = cam.matrix_world.translation
        for n in who:
            if n not in rigs: continue
            rig = next((r for r in rigs[n].children if r.type == "ARMATURE"), None)
            pts = []
            for bn in ("mixamorig:Head", "mixamorig:Spine1", "mixamorig:Hips", "mixamorig:LeftHand", "mixamorig:RightHand"):
                pb = rig.pose.bones.get(bn)
                if pb: pts.append(rig.matrix_world @ pb.head)
            if not pts: pts = [rigs[n].matrix_world.translation + Vector((0, 0, 0.6))]
            blocked = []
            for p in pts:
                d = p - cp; L = d.length; d.normalize(); o_ = cp.copy(); t = 0.0; hit_by = None
                while t < L - 0.15:
                    hit, loc, _, _, ob, _ = sc.ray_cast(dg, o_ + d * (t + 0.01), d, distance=L - t)
                    if not hit: break
                    if ob in mine:
                        if mine[ob] == n: break
                        t = (loc - o_).length + 0.02; continue   # another guest in front is fine (it's a party)
                    if any(k in ob.name.lower() for k in ("puff", "cloud", "smoke", "gas", "bill", "confetti", "laser", "glass", "string")):
                        t = (loc - o_).length + 0.02; continue
                    hit_by = ob.name; break
                if hit_by: blocked.append(hit_by)
            if len(blocked) >= max(2, len(pts) // 2):
                print(f"BLOCKED f{f:4d} {n:12s} {len(blocked)}/{len(pts)} by {sorted(set(blocked))}")
print("SCAN DONE")
