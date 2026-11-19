import bpy, json
from mathutils import Vector
E = json.load(open('/home/user/dep/commercial/memetrix/edl.json')); sc = bpy.context.scene
body = next(o for o in bpy.data.objects['RIG-anon'].children_recursive if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
rest = [v.co.copy() for v in body.data.vertices]
# tail: behind the body (rest pose faces -Y in the mesh's own space) and low
ys = sorted(c.y for c in rest)
tail = {i for i, c in enumerate(rest) if c.y > 0.18 and c.z < 0.75}
print('LY tail verts', len(tail), 'of', len(rest), 'rest y range', round(ys[0], 2), round(ys[-1], 2))
fall = E['events']['fall']
def anim_of(t):
    s = next(x for x in E['shots'] if x['t0'] <= t < x['t1']); return s['a0'] + (t - s['t0']) * s['s0']
for dt in (0.5, 1.0, 2.0, 3.0, 5.0):
    a = anim_of(fall + dt); af = a * 24 + 1; sc.frame_set(int(af), subframe=af % 1)
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    P = [body.matrix_world @ v.co for v in ev.data.vertices]
    floor = bpy.data.objects['RIG-anon'].matrix_world.translation.z
    bmin = min(p.z for i, p in enumerate(P) if i not in tail); tmin = min(p.z for i, p in enumerate(P) if i in tail)
    print(f'LY fall+{dt}: rig z {floor:.3f} body lowest z {bmin:+.3f} tail lowest z {tmin:+.3f}')
import math
a = anim_of(fall + 2.0); sc.frame_set(int(a * 24 + 1))
rig = bpy.data.objects['RIG-anon']; c = rig.matrix_world.translation
cam = sc.camera; cam.animation_data_clear(); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.2; cam.data.dof.use_dof = False
for c_ in bpy.data.collections:
    if c_.name.startswith('L_'): c_.hide_render = c_.name != 'L_DOJO'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 900, 500, 100
sc.cycles.samples = 6; sc.render.use_motion_blur = False
bpy.data.objects['camfill'].data.energy = 40
for name, off, rot in (('side', Vector((0, -6, 0.6)), (math.pi / 2, 0, 0)), ('end', Vector((6, 0, 0.6)), (math.pi / 2, 0, math.pi / 2))):
    cam.location = c + off; cam.rotation_euler = rot
    sc.render.filepath = f'/root/mx_probe/lying18_{name}.png'; bpy.ops.render.render(write_still=True)
