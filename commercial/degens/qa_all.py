"""Broad glitch sweep: blender -b scene.blend -P qa_all.py -- step_seconds
Reports interpenetrations by category with the times they occur."""
import bpy, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
STEP = float(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else 0.5
sc = bpy.context.scene
CAST = ['chad', 'earl', 'pam', 'linda']
# work on the true bodies (no clothing masks) so regions are closed and normals are consistent
for k in CAST:
    for m in bpy.data.objects[k + '.body'].modifiers:
        if m.type == 'MASK' and m.name != 'Hide helpers': m.show_viewport = False
    for m in bpy.data.objects[k + '.body'].modifiers:
        if m.type == 'SUBSURF': m.levels = 0
ARM = ('wrist', 'finger', 'metacarpal')
def region(o):
    names = {g.index: g.name for g in o.vertex_groups}; bones = set(b.name for b in o.parent.data.bones)
    reg = []
    for v in o.data.vertices:
        gs = [(names[g.group], g.weight) for g in v.groups if names.get(g.group) in bones]
        b = max(gs, key=lambda x: x[1])[0] if gs else ''
        side = b[-1] if b.endswith(('.L', '.R')) else 'M'
        reg.append(('arm' + side) if b.startswith(ARM) else ('limb' if b.startswith(('upperarm', 'lowerarm', 'shoulder', 'clavicle')) else 'core'))
    return reg
REG = {k: region(bpy.data.objects[k + '.body']) for k in CAST}
def mesh(o, dg):
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    V = [o.matrix_world @ v.co for v in me.vertices]; F = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear(); return V, F
def tree_of(objs, dg, face_filter=None):
    TV, TF = [], []
    for o in objs:
        for c in [o] + list(o.children_recursive):
            if c.type != 'MESH' or c.hide_render or (c.parent and c.parent.hide_render and c.parent.type == 'MESH'): continue
            V, F = mesh(c, dg); off = len(TV); TV += V
            TF += [tuple(i + off for i in f) for f in F if face_filter is None or face_filter(c, f)]
    return (BVHTree.FromPolygons(TV, TF), TV) if TF else (None, TV)
def inside(tree, p, rng=0.03):
    loc, nrm, i, d = tree.find_nearest(p, rng)
    return d if loc is not None and (p - loc).dot(nrm) < -0.002 else None
found = {}
def note(cat, t, n, depth):
    found.setdefault(cat, []).append((t, n, depth))
chairs = [o for o in bpy.data.objects if o.parent and o.parent.name.startswith('chair_pivot')]
others = [o for o in bpy.data.objects if o.name.startswith(('metal_office', 'door', 'oxy', 'wall_', 'cup', 'cardboard', 'korean', 'potted', 'Cube')) and o.type in ('MESH', 'EMPTY') and not o.name.endswith('_hinge')]
t = 3.3
while t < 48.4:
    f = int(round(t * 30)) + 1; sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    vis = {k: not bpy.data.objects[k + '.body'].hide_render for k in CAST}
    data = {}
    for k in CAST:
        if not vis[k]: continue
        b = bpy.data.objects[k + '.body']; V, F = mesh(b, dg); data[k] = (V, F)
    # 1. arms/hands through own body
    for k, (V, F) in data.items():
        R = REG[k]
        for s in 'LR':
            core = BVHTree.FromPolygons(V, [f_ for f_ in F if all(R[i] in ('core', 'arm' + ('R' if s == 'L' else 'L')) for i in f_)])
            ds = [d for i, p in enumerate(V) if R[i] == 'arm' + s for d in [inside(core, p)] if d]
            if len(ds) > 3: note(f'{k} {s}-hand into own body', t, len(ds), max(ds))
    # 2. person vs person (bodies + NEET)
    bodies = {k: BVHTree.FromPolygons(*data[k]) for k in data}
    nm = bpy.data.objects['neet']
    if not nm.hide_render:
        NV, NF = mesh(nm, dg)
    for a in data:
        for b2 in data:
            if a >= b2: continue
            ds = [d for p in data[a][0] for d in [inside(bodies[b2], p)] if d]
            if len(ds) > 3: note(f'{a} into {b2}', t, len(ds), max(ds))
        if not nm.hide_render:
            nt = BVHTree.FromPolygons(NV, NF)
            ds = [d for p in data[a][0] for d in [inside(nt, p)] if d]
            if len(ds) > 10: note(f'{a} into NEET', t, len(ds), max(ds))
    # 3. people vs other chairs / set pieces
    for a in data:
        for ch in chairs:
            tr, TV = tree_of([ch], dg)
            if tr is None: continue
            ds = [d for p in data[a][0] for d in [inside(tr, p)] if d and d > 0.005]
            if len(ds) > 3: note(f'{a} into {ch.name}', t, len(ds), max(ds))
        for ob in others:
            tr, TV = tree_of([ob], dg)
            if tr is None: continue
            ds = [d for p in data[a][0] for d in [inside(tr, p)] if d]
            if len(ds) > 3: note(f'{a} into {ob.name}', t, len(ds), max(ds))
    # 4. props / wardrobe vs heads (cannula, cap, glasses, sips, cigarette)
    for a in data:
        V, F = data[a]; R = REG[a]
        head = BVHTree.FromPolygons(V, F)
        for pn in ['cannula_face', 'cannula_line', 'chad_cap', 'pam_mug', 'linda_mug', 'linda_straw', 'wine_bottles_01_bordeaux', 'earl_cig', 'chad_can',
                   f'{a}.spamrakuen_tbm_glasses_frames_01', f'{a}.frankyaye_glasses_library_male', f'{a}_phone']:
            o = bpy.data.objects.get(pn)
            if o is None or o.hide_render: continue
            objs = [o] + [c for c in o.children_recursive if c.type in ('MESH', 'CURVE')]
            pts = []
            for c in objs:
                if c.type in ('MESH', 'CURVE'):
                    ev = c.evaluated_get(dg); me = ev.to_mesh(); pts += [c.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
            ds = [d for p in pts for d in [inside(head, p, 0.05)] if d]
            if pn == 'earl_cig' and a == 'earl': ds = [d for d in ds if d > 0.012]       # the filter sits between his lips
            if pn in ('linda_straw',) and a == 'linda': ds = [d for d in ds if d > 0.008]
            if len(ds) > 2: note(f'{pn} into {a}', t, len(ds), max(ds))
    # 5. feet through the floor
    for a, (V, F) in data.items():
        lo = min(p.z for p in V)
        if lo < -0.01: note(f'{a} below floor', t, 1, -lo)
    t += STEP
print('==== SWEEP RESULTS ====')
for cat, hits in sorted(found.items()):
    ts = [h[0] for h in hits]; deep = max(h[2] for h in hits)
    spans = []; s0 = ts[0]; prev = ts[0]
    for x in ts[1:]:
        if x - prev > STEP * 1.5: spans.append((s0, prev)); s0 = x
        prev = x
    spans.append((s0, prev))
    print(f'ISSUE {cat:45s} deepest {deep*100:5.1f} cm  at ' + ', '.join(f'{a:.1f}-{b:.1f}s' if b > a else f'{a:.1f}s' for a, b in spans))
print('==== END ====')
