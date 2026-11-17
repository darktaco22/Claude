"""Real tears for Wojak: two wet streaks from the eyes down the cheeks plus falling drops, riding the head bone."""
import bpy, math, random
from mathutils import Vector, Matrix
from common import link
def water():
    m = bpy.data.materials.new('tear'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.9, 0.97, 1.0, 1); b.inputs['Roughness'].default_value = 0.02; b.inputs['IOR'].default_value = 1.33
    b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['Coat Weight'].default_value = 1.0
    b.inputs['Emission Color'].default_value = (0.3, 0.95, 0.9, 1); b.inputs['Emission Strength'].default_value = 0.22   # the game's teal tear glow
    return m
def build(c, f0, f1, period=24, seed=2):
    rig = c.rig; mesh = next(o for o in rig.children if o.type == 'MESH')
    arm = next(md for md in mesh.modifiers if md.type == 'ARMATURE'); arm.show_viewport = False
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
    mw = mesh.matrix_world; inv = mw.inverted()
    vs = [mw @ v.co for v in ev.data.vertices]
    head = rig.matrix_world @ rig.data.bones['mixamorig:Head'].head_local
    hv = [v for v in vs if v.z > head.z - 0.02]; top = max(v.z for v in hv); front = min(v.y for v in hv)  # rest faces -Y... after ctrl rotation use the facing vector
    fwd = (rig.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized(); right = fwd.cross(Vector((0, 0, 1))).normalized()
    cx = sum((v for v in hv), Vector()) / len(hv)
    eye_z = head.z + 0.50 * (top - head.z)
    def surf(lat, z):
        o = cx + right * lat; o.z = z; o = o + fwd * 0.5
        hit, loc, nor, idx = mesh.ray_cast(inv @ o, inv.to_3x3() @ (-fwd))
        return (mw @ loc, (mw.to_3x3() @ nor).normalized()) if hit else (None, None)
    tm = water(); objs = []
    for side in (-1, 1):
        pts = []
        for i in range(10):
            z = eye_z - 0.012 - i * 0.0072; p, n = surf(side * (0.041 + 0.003 * math.sin(i * 0.7)), z)
            if p: pts.append(p + n * 0.0016)
        if len(pts) < 4: continue
        cu = bpy.data.curves.new('tear', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0018; cu.bevel_resolution = 3
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (*p, 1); sp.points[i].radius = 0.6 + 0.5 * (i / len(pts))
        o = link(bpy.data.objects.new('tear_streak', cu)); o.data.materials.append(tm); objs.append(o)
        # drops: form at the end of the streak, fall, vanish (keyed), staggered
        rnd = random.Random(seed + side); start = pts[-1]
        for k in range(int((f1 - f0) / period) + 1):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.0032, location=start); d = bpy.context.object; d.name = 'tear_drop'; d.data.materials.append(tm)
            d.scale = (1, 1, 1.25); objs.append(d)
            a = f0 + k * period + rnd.randint(0, 10)
            for f, z, s in ((a - 1, 0, 0.0), (a, 0, 0.4), (a + 8, -0.004, 1.0), (a + 12, -0.06, 1.0), (a + 16, -0.22, 0.8), (a + 17, -0.25, 0.0)):
                d.location = start + Vector((0, 0, z)); d.keyframe_insert('location', frame=f); d.scale = (s, s, s * 1.3); d.keyframe_insert('scale', frame=f)
    arm.show_viewport = True; bpy.context.view_layer.update()
    pm = rig.matrix_world @ rig.data.bones['mixamorig:Head'].matrix_local   # rest: the geometry above was built on the rest mesh
    for o in objs:
        cn = o.constraints.new('CHILD_OF'); cn.target = rig; cn.subtarget = 'mixamorig:Head'; cn.inverse_matrix = pm.inverted()
    return objs
