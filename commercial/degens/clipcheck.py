"""Measure interpenetration: blender -b scene.blend -P clipcheck.py -- t1,t2,..
For each pair (A, B): vertices of A inside closed mesh B, and the deepest one (cm)."""
import bpy, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ts = [float(x) for x in sys.argv[sys.argv.index('--') + 1].split(',')]
sc = bpy.context.scene
def world_mesh(o, dg):
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    V = [o.matrix_world @ v.co for v in me.vertices]; F = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear(); return V, F
def inside(tree, p):
    # parity of ray hits along +Z and -X (two rays must agree)
    def hits(d):
        n, o = 0, p.copy()
        for _ in range(20):
            h = tree.ray_cast(o + d * 1e-5, d, 5.0)
            if h[0] is None: break
            n += 1; o = h[0]
        return n % 2 == 1
    return hits(Vector((0, 0, 1))) and hits(Vector((-1, 0.0001, 0)))
def objs(prefix): return [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefix) and not o.hide_render]
chairs = {}
for i, o in enumerate([o for o in bpy.data.objects if o.name.startswith('SchoolChair_01') and o.parent and o.parent.name.startswith('chair_pivot')]): chairs[i] = o
ORDER = ['chad', 'earl', 'pam', 'linda']
SEAT_OF = {'chad': 0, 'earl': 1, 'pam': 2, 'linda': 3}
PROPS = {'chad': ['chad_can', 'chad_phone'], 'earl': ['earl_cig', 'earl_phone'], 'pam': ['pam_mug', 'pam_phone'], 'linda': ['linda_mug', 'linda_phone', 'wine_bottles_01_bordeaux']}
for t in ts:
    sc.frame_set(int(round(t * 30)) + 1); dg = bpy.context.evaluated_depsgraph_get()
    for k in ORDER:
        bodyparts = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(k + '.') and not o.hide_render and 'high-poly' not in o.name and 'teeth' not in o.name and 'tongue' not in o.name and 'eyelash' not in o.name and 'eyebrow' not in o.name]
        targets = [('chair', chairs[SEAT_OF[k]])] + [(n, bpy.data.objects[n]) for n in PROPS[k] if n in bpy.data.objects and not bpy.data.objects[n].hide_render]
        for tn, tob in targets:
            TV, TF = world_mesh(tob, dg) if tob.type == "MESH" else ([], [])
            for c in tob.children_recursive:
                if c.type == 'MESH' and not c.hide_render:
                    v2, f2 = world_mesh(c, dg); off = len(TV); TV += v2; TF += [tuple(i + off for i in f) for f in f2]
            if not TF: continue
            tree = BVHTree.FromPolygons(TV, TF)
            lo = Vector([min(v[i] for v in TV) for i in range(3)]) - Vector((.01, .01, .01)); hi = Vector([max(v[i] for v in TV) for i in range(3)]) + Vector((.01, .01, .01))
            for bp in bodyparts:
                V, _ = world_mesh(bp, dg)
                cand = [p for p in V if all(lo[i] <= p[i] <= hi[i] for i in range(3))]
                bad = [p for p in cand if inside(tree, p)]
                if bad:
                    depth = max(tree.find_nearest(p)[3] for p in bad)
                    print(f'CLIP t={t:5.2f} {bp.name:38s} in {tn:26s} n={len(bad):4d} depth={depth*100:.1f}cm')
    print(f'CLIP t={t:5.2f} done')
