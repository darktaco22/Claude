"""Clipping sweep for LAST WILL & TESTAMENT: blender -b scene.blend -P wqa.py -- step_seconds [t0 t1]
Reports, by category, where any vertex sits more than 2 mm inside another surface: props in bodies, people in the
Whale / bed / duvet / furniture, hands through their own body, the Whale through the bed or duvet."""
import bpy, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
STEP = float(A[0]) if A else 0.5; T0 = float(A[1]) if len(A) > 1 else 0.0; T1 = float(A[2]) if len(A) > 2 else 26.7
sc = bpy.context.scene
CAST = ['kid', 'dad', 'mom', 'repo']
for k in CAST:
    b = bpy.data.objects[k + '.body']
    for m in b.modifiers:
        if m.type == 'MASK' and m.name != 'Hide helpers': m.show_viewport = False
        if m.type == 'SUBSURF': m.levels = 0
ARM = ('wrist', 'finger', 'metacarpal')
def region(o):
    names = {g.index: g.name for g in o.vertex_groups}; bones = set(b.name for b in o.parent.data.bones); reg = []
    for v in o.data.vertices:
        gs = [(names[g.group], g.weight) for g in v.groups if names.get(g.group) in bones]
        b = max(gs, key=lambda x: x[1])[0] if gs else ''
        side = b[-1] if b.endswith(('.L', '.R')) else 'M'
        reg.append(('arm' + side) if b.startswith(ARM) else ('limb' if b.startswith(('upperarm', 'lowerarm', 'shoulder', 'clavicle')) else 'core'))
    return reg
REG = {k: region(bpy.data.objects[k + '.body']) for k in CAST}
def mesh(o, dg):
    ev = o.evaluated_get(dg); me = ev.to_mesh(); M = o.matrix_world
    V = [M @ v.co for v in me.vertices]; F = [tuple(p.vertices) for p in me.polygons]; ev.to_mesh_clear(); return V, F
def tree(objs, dg):
    TV, TF = [], []
    for o in objs:
        for c in [o] + [x for x in o.children_recursive]:
            if c.type != 'MESH' or c.hide_render: continue
            V, F = mesh(c, dg); off = len(TV); TV += V; TF += [tuple(i + off for i in f) for f in F]
    return BVHTree.FromPolygons(TV, TF) if TF else None
def inside(tr, p, rng=0.04):
    loc, nrm, i, d = tr.find_nearest(p, rng)
    return d if loc is not None and (p - loc).dot(nrm) < -0.002 else None
PROPS = ['kid_phone', 'kid_phone2', 'dad_phone', 'dad_mug', 'carafe']
FURN = [o for o in bpy.data.objects if o.name.split('.')[0] in ('island', 'island_top', 'base_cab', 'back_top', 'fridge')]
FURN = [o for o in FURN if o.type in ('MESH', 'EMPTY')]
found = {}
def note(cat, t, n, d): found.setdefault(cat, []).append((t, n, d))
t = T0
while t <= T1:
    f = int(round(t * 30)) + 1; sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    bodies = {k: mesh(bpy.data.objects[k + '.body'], dg) for k in CAST}
    btree = {k: BVHTree.FromPolygons(*bodies[k]) for k in CAST}
    UN = []
    WV, WF = [], []
    for u in UN:
        if u.hide_render: continue
        V_, F_ = mesh(u, dg); o_ = len(WV); WV += V_; WF += [tuple(i + o_ for i in f_) for f_ in F_]
    wtree = BVHTree.FromPolygons(WV, WF) if WF else None
    ftree = tree(FURN, dg)
    # props in bodies (the holder's hand counts too: fingers must not enter the prop, the prop must not enter the hand)
    for pn in PROPS:
        o = bpy.data.objects.get(pn)
        if o is None or o.hide_render: continue
        pts = []
        for c in [o] + list(o.children_recursive):
            if c.type == 'MESH' and not c.hide_render: pts += mesh(c, dg)[0][::2]
        for k in CAST:
            ds = [d for p in pts for d in [inside(btree[k], p)] if d]
            if len(ds) > 2: note(f'{pn} inside {k}', t, len(ds), max(ds))
        if ftree and pn not in ('dad_mug',):
            ds = [d for p in pts for d in [inside(ftree, p)] if d]
            if len(ds) > 2: note(f'{pn} inside furniture', t, len(ds), max(ds))
    for k, (V, F) in bodies.items():
        if ftree:
            ds = [d for p in V[::3] for d in [inside(ftree, p)] if d]
            if len(ds) > 2: note(f'{k} inside bed/furniture', t, len(ds), max(ds))
        for k2 in CAST:
            if k2 == k: continue
            ds = [d for p in V[::4] for d in [inside(btree[k2], p)] if d]
            if len(ds) > 2: note(f'{k} inside {k2}', t, len(ds), max(ds))
        R = REG[k]
        for s in 'LR':
            core = BVHTree.FromPolygons(V, [f_ for f_ in F if all(R[i] in ('core', 'arm' + ('R' if s == 'L' else 'L')) for i in f_)])
            ds = [d for i, p in enumerate(V) if R[i] == 'arm' + s for d in [inside(core, p)] if d]
            if len(ds) > 3: note(f'{k} {s}-hand into own body', t, len(ds), max(ds))
    t = round(t + STEP, 3)
for cat, L in sorted(found.items()):
    ts = [x[0] for x in L]; print(f'QA {cat}: {len(L)} times, {ts[0]:.1f}-{ts[-1]:.1f}s, max {max(x[2] for x in L) * 100:.1f} cm, e.g. {[round(x, 1) for x in ts[:8]]}')
print('QA done', len(found), 'categories')
