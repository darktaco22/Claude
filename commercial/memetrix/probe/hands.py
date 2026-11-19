import bpy, sys
who, char = sys.argv[sys.argv.index('--') + 1:][:2]
sc = bpy.context.scene
rig = bpy.data.objects['RIG-' + who]; arm = next(o for o in rig.children_recursive if o.type == 'ARMATURE')
body = next(o for o in rig.children_recursive if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
for t in arm.animation_data.nla_tracks: t.mute = True
for pb in arm.pose.bones:
    for c in pb.constraints: c.mute = True
rig.animation_data_clear(); rig.location = (0, 0, -100); rig.rotation_euler = (0, 0, 0)
tl = bpy.data.objects['TILT-' + who]; tl.animation_data_clear(); tl.rotation_euler = (0, 0, 0)
gi = {g.name: g.index for g in body.vertex_groups}
print('H groups', [n for n in gi if 'Hand' in n and 'Index' not in n and 'Thumb' not in n])
def vs(name): return [v.index for v in body.data.vertices if any(g.group == gi[name] and g.weight >= 0.4 for g in v.groups)]
R, L = vs('mixamorig:RightHand'), vs('mixamorig:LeftHand')
for c in ('idle', 'ready', 'emote', 'attack1', 'attack2', 'win', 'lose'):
    act = bpy.data.actions.get(f'{char}:{c}')
    if not act: continue
    arm.animation_data.action = act; a0, a1 = act.frame_range
    for fr in (0.1, 0.3, 0.5, 0.7):
        sc.frame_set(int(a0 + (a1 - a0) * fr)); ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        def c_(ix):
            ps = [body.matrix_world @ ev.data.vertices[i].co - rig.location for i in ix]
            m = sum(ps, ps[0] * 0) / len(ps); return f'({m.x:+.2f},{m.y:+.2f},{m.z:.2f})'
        print(f'H {c}@{fr}: R {c_(R)} L {c_(L)}')
