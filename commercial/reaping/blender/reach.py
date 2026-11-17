"""IK -> FK baking for rigs without hand bones (the Whale): solve a 2-bone IK toward keyed targets, read the solved local
rotations, key them in an action and lay it on its own NLA track over the clips."""
import bpy
from common import link
def bake(c, side, keys, f0, f1, blend=6, name='reach'):
    rig = c.rig; ad = rig.animation_data; pb = rig.pose.bones
    up, lo = pb[f'mixamorig:{side}Arm'], pb[f'mixamorig:{side}ForeArm']
    tgt = link(bpy.data.objects.new(name + '_tgt', None)); pole = link(bpy.data.objects.new(name + '_pole', None))
    ik = lo.constraints.new('IK'); ik.target = tgt; ik.chain_count = 2; ik.pole_target = pole; ik.pole_angle = -1.5708
    sc = bpy.context.scene; out = []
    for f, p, pl in keys:
        tgt.location = p; pole.location = pl; sc.frame_set(f); bpy.context.view_layer.update()
        q = [rig.convert_space(pose_bone=b, matrix=b.matrix, from_space='POSE', to_space='LOCAL').to_quaternion() for b in (up, lo)]
        out.append((f, q))
    lo.constraints.remove(ik); bpy.data.objects.remove(tgt); bpy.data.objects.remove(pole)
    act = bpy.data.actions.new(name); keep = ad.action; ad.action = act
    for b in (up, lo): b.rotation_mode = 'QUATERNION'
    for f, (qa, qb) in out:
        up.rotation_quaternion = qa; up.keyframe_insert('rotation_quaternion', frame=f); lo.rotation_quaternion = qb; lo.keyframe_insert('rotation_quaternion', frame=f)
    ad.action = keep
    tr = ad.nla_tracks.new(); st = tr.strips.new(name, f0, act); st.frame_start = f0; st.frame_end = f1
    st.blend_in = st.blend_out = blend; st.extrapolation = 'NOTHING'; st.use_sync_length = False
    return act
def glove_fins(c, sides=('Right',), frac=0.55):
    """white satin glove on the fin: faces mostly weighted to the forearm, past `frac` of its length"""
    rig = c.rig; mesh = next(o for o in rig.children if o.type == 'MESH'); me = mesh.data
    m = bpy.data.materials.new('satin_glove'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.9, 0.89, 0.86, 1); b.inputs['Roughness'].default_value = 0.42; b.inputs['Sheen Weight'].default_value = 1.0
    b.inputs['Sheen Roughness'].default_value = 0.25; b.inputs['Coat Weight'].default_value = 0.15
    me.materials.append(m); idx = len(me.materials) - 1
    inv = mesh.matrix_world.inverted() @ rig.matrix_world
    n = 0
    for side in sides:
        bn = rig.data.bones[f'mixamorig:{side}ForeArm']; gi = mesh.vertex_groups.get(bn.name)
        if gi is None: continue
        h, t = inv @ bn.head_local, inv @ bn.tail_local; L = (t - h).length; d = (t - h).normalized()
        vin = set()
        for v in me.vertices:
            w = {mesh.vertex_groups[g.group].name: g.weight for g in v.groups}
            if w.get(bn.name, 0) > 0.5 and (v.co - h).dot(d) > frac * L: vin.add(v.index)
        for p in me.polygons:
            if sum(i in vin for i in p.vertices) >= len(p.vertices) - 1: p.material_index = idx; n += 1
    print('GLOVE faces', n)
    return m
