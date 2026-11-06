"""Loads Poly Haven (CC0) props: .blend where Blender 4.2 can read it, otherwise the glTF."""
import bpy, os
PH = os.environ.get('PH', '')
def load(aid, coll=None):
    """Returns a new parent empty holding the asset's meshes, origin at the asset's origin."""
    coll = coll or bpy.context.scene.collection
    before = set(bpy.data.objects)
    b = f'{PH}/{aid}/{aid}.blend'; g = f'{PH}/{aid}/gltf/{aid}.gltf'
    ok = False
    if os.path.exists(b):
        try:
            with bpy.data.libraries.load(b) as (src, dst): dst.objects = src.objects
            for o in dst.objects:
                if o is not None: coll.objects.link(o)
            ok = True
        except OSError: pass
    if not ok:
        bpy.ops.import_scene.gltf(filepath=g)
        for o in bpy.context.selected_objects:
            for c in o.users_collection: c.objects.unlink(o)
            coll.objects.link(o)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(aid, None); coll.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    return root, [o for o in new if o.type == 'MESH']
def dims(root):
    from mathutils import Vector
    import itertools
    pts = [o.matrix_world @ Vector(c) for o in root.children_recursive if o.type == 'MESH' for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)]); return lo, hi
