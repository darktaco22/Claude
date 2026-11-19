import bpy
from mathutils import Vector
sc = bpy.context.scene
def setup(who):
    rig = bpy.data.objects['RIG-' + who]; arm = next(o for o in rig.children_recursive if o.type == 'ARMATURE')
    body = next(o for o in rig.children_recursive if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
    rig.animation_data_clear(); rig.location = (0, 0, -100); rig.rotation_euler = (0, 0, 0)
    t = bpy.data.objects['TILT-' + who]; t.animation_data_clear(); t.rotation_euler = (0, 0, 0)
    for tr in arm.animation_data.nla_tracks: tr.mute = True
    for pb in arm.pose.bones:
        for c in pb.constraints: c.mute = True
    return rig, arm, body
def pts(rig, arm, body, act, frac):
    arm.animation_data.action = act; a0, a1 = act.frame_range; sc.frame_set(int(a0 + (a1 - a0) * frac))
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [body.matrix_world @ v.co - rig.location for v in ev.data.vertices]
for who, char, clips, fr in (('slerf', 'slerf', ('win', 'emote', 'attack1'), (0.05, 0.1, 0.15, 0.2, 0.3)), ('anon', 'zcat', ('attack1', 'attack2', 'win', 'emote', 'attack3'), (0.1, 0.25, 0.4, 0.55))):
    rig, arm, body = setup(who)
    for c in clips:
        act = bpy.data.actions[f'{char}:{c}']
        for f in fr:
            P = pts(rig, arm, body, act, f)
            low = [p for p in P if p.z < (0.92 if who == 'anon' else 1.2)]
            fwd = min(low, key=lambda p: p.y)
            rgt = min(P, key=lambda p: p.x); lft = max(P, key=lambda p: p.x)
            print(f'P {who} {c}@{f}: fwd {tuple(round(v,2) for v in fwd)} right {tuple(round(v,2) for v in rgt)} left {tuple(round(v,2) for v in lft)}')
