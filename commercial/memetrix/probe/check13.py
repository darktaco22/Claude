import bpy, json
from mathutils import Vector
E = json.load(open('/home/user/dep/commercial/memetrix/edl.json'))
sc = bpy.context.scene; FPS = 24
def at(a):
    af = a * FPS + 1; sc.frame_set(int(af), subframe=af - int(af))
def shot(n): return next(x for x in E['shots'] if x['name'] == n)
S = {n: next(o for o in bpy.data.objects['RIG-' + n].children_recursive if o.type == 'ARMATURE') for n in ('slerf', 'anon')}
def bone_tail(n, b):
    A = S[n]; return A.matrix_world @ A.pose.bones[b].tail
def W(name): return bpy.data.objects[name].matrix_world.translation.copy()
s3 = shot('s03_1'); a = s3['a0'] + 1.0; at(a)
for side in ('Right', 'Left'):
    print(f'HOLD {side}: paw tip {tuple(round(v,2) for v in bone_tail("slerf", f"mixamorig:{side}Hand"))} target {tuple(round(v,2) for v in W(f"hold_slerf_{side}"))}')
tk = shot('take_red')['a0']
for d in (0.3, 0.45, 0.6):
    at(tk + d)
    wrist = bone_tail('anon', 'mixamorig:LeftForeArm')
    print(f'TAKE+{d}: anon wrist {tuple(round(v,2) for v in wrist)} target {tuple(round(v,2) for v in W("ik_anon_Left"))} red_s {tuple(round(v,2) for v in W("candle_red_s"))} red_a {tuple(round(v,2) for v in W("candle_red_a"))}')
sw = shot('swallow')['a0']
for d in (0.5, 0.7):
    at(sw + d); print(f'SWALLOW+{d}: candle {tuple(round(v,2) for v in W("candle_red_a"))} head {tuple(round(v,2) for v in S["anon"].matrix_world @ S["anon"].pose.bones["mixamorig:Head"].head)}')
body = next(o for o in bpy.data.objects['RIG-anon'].children_recursive if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
bt = shot('bullet_time')
worst = 9
for k in range(0, 30):
    a = bt['a0'] + k * 0.016; at(a)
    pts = [body.matrix_world @ v.co for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
    for j in range(7):
        c = W(f'proj{j}')
        if abs(c.y - 204.2 + 200) < 1.6 or True:
            d = min((p - c).length for p in pts[::3])
            if d < worst: worst = d
            if d < 0.2: print(f'CLOSE a+{k*0.016:.3f} proj{j} at y {c.y:.2f} z {c.z:.2f}: {d:.3f} m from Anon')
print('WORST clearance', round(worst, 3))
