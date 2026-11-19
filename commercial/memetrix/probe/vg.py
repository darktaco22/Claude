import bpy
from collections import Counter
from mathutils import Vector
sc = bpy.context.scene
rig = bpy.data.objects['RIG-anon']; arm = next(o for o in rig.children_recursive if o.type == 'ARMATURE')
body = next(o for o in rig.children_recursive if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
for t in arm.animation_data.nla_tracks: t.mute = True
for pb in arm.pose.bones:
    for c in pb.constraints: c.mute = True
rig.animation_data_clear(); rig.location = (0, 0, -100); rig.rotation_euler = (0, 0, 0)
tl = bpy.data.objects['TILT-anon']; tl.animation_data_clear(); tl.rotation_euler = (0, 0, 0)
act = bpy.data.actions['zcat:attack1']; arm.animation_data.action = act; sc.frame_set(2)
ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
names = {g.index: g.name for g in body.vertex_groups}
P = [(v.index, body.matrix_world @ ev.data.vertices[v.index].co - rig.location) for v in body.data.vertices]
tip = min((p for p in P if p[1].z < 1.3 and p[1].x < -0.3), key=lambda q: q[1].y)
print('VG tip', tip[0], tuple(round(c, 2) for c in tip[1]))
near = [i for i, p in P if (p - tip[1]).length < 0.08]
cnt = Counter()
for i in near:
    for g in body.data.vertices[i].groups:
        cnt[(names[g.group], round(g.weight, 1))] += 1
print('VG groups near tip', cnt.most_common(12))
print('VG all groups', list(names.values()))
gi = {g.name: g.index for g in body.vertex_groups}
def arm_verts(name, w=0.3):
    return [v.index for v in body.data.vertices if any(g.group == gi[name] and g.weight >= w for g in v.groups)]
RF = arm_verts('mixamorig:RightForeArm'); LF = arm_verts('mixamorig:LeftForeArm')
for c in ('attack1', 'attack2', 'attack3', 'emote', 'win', 'idle', 'ready', 'lose'):
    act = bpy.data.actions['zcat:' + c]; arm.animation_data.action = act; a0, a1 = act.frame_range
    for fr in (0.1, 0.25, 0.4, 0.55, 0.7):
        sc.frame_set(int(a0 + (a1 - a0) * fr))
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        def ext(ix):
            ps = [body.matrix_world @ ev.data.vertices[i].co - rig.location for i in ix]
            f = min(ps, key=lambda p: p.y); t = max(ps, key=lambda p: p.z)
            return f'fwd({f.x:+.2f},{f.y:+.2f},{f.z:.2f}) top({t.x:+.2f},{t.y:+.2f},{t.z:.2f})'
        print(f'PW {c}@{fr}: R {ext(RF)} | L {ext(LF)}')
