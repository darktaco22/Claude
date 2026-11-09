"""A mouth for NEET (the game's model has its lips painted on, and too few face vertices to open them): a small mouth
decal (dark inside, upper teeth, tongue, lip rim) conformed to his face at the lips and skinned to his Head bone, with an
'open' shape key the lip-sync drives (0 = a closed line, 1 = wide open)."""
import bpy, math
from mathutils import Vector

LIPS = Vector((0.0, -0.197, 1.402))     # rest pose, world space of the fresh import: the painted lip line (measured off the mesh profile)
W_, H_ = 0.056, 0.030                   # the mouth fully open

def add_mouth(rig, me, tex):
    rig.data.pose_position = 'REST'; bpy.context.view_layer.update()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=18, y_subdivisions=10, size=1)
    mo = bpy.context.object; mo.name = 'neet_mouth'
    # build it in world space in front of the lips, facing -Y, then conform it to the face (rest pose) and bake that
    # LIPS are world coordinates of the freshly imported model; in a scene the model sits under a placed, scaled root
    Mw = rig.parent.matrix_world.copy() if rig.parent else __import__('mathutils').Matrix()
    for v in mo.data.vertices:
        x, y = v.co.x, v.co.y
        v.co = Mw @ Vector((LIPS.x + x * W_, LIPS.y - 0.04, LIPS.z + y * H_))
    sw = mo.modifiers.new('sw', 'SHRINKWRAP'); sw.target = me; sw.wrap_method = 'PROJECT'
    sw.use_project_y = True; sw.use_negative_direction = True; sw.use_positive_direction = True; sw.offset = 0.0018
    bpy.context.view_layer.objects.active = mo; bpy.ops.object.modifier_apply(modifier='sw')
    full = [v.co.copy() for v in mo.data.vertices]
    # closed: squashed onto the lip line (a thin dark seam)
    Mi = Mw.inverted()
    for v in mo.data.vertices:
        lc = Mi @ v.co; lc.z = LIPS.z + (lc.z - LIPS.z) * 0.06; v.co = Mw @ lc
    mo.shape_key_add(name='Basis'); k = mo.shape_key_add(name='open')
    for i, p in enumerate(full): k.data[i].co = p
    # into the mesh's own space, skinned to the Head bone like the face around it
    M = me.matrix_world.copy()
    Minv = M.inverted(); B = mo.data.shape_keys.key_blocks['Basis']
    for kb in (B, k):
        for v in kb.data: v.co = Minv @ v.co
    for i, v in enumerate(mo.data.vertices): v.co = B.data[i].co
    mo.parent = me.parent; mo.matrix_parent_inverse = me.matrix_parent_inverse.copy(); mo.matrix_basis = me.matrix_basis.copy()
    vg = mo.vertex_groups.new(name='mixamorig:Head'); vg.add(list(range(len(mo.data.vertices))), 1.0, 'REPLACE')
    am = mo.modifiers.new('arm', 'ARMATURE'); am.object = rig
    m = bpy.data.materials.new('neet_mouth'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(tex)
    nt.links.new(ti.outputs[0], b.inputs['Base Color']); nt.links.new(ti.outputs[1], b.inputs['Alpha']); b.inputs['Roughness'].default_value = 0.4
    mo.data.materials.append(m)
    for p in mo.data.polygons: p.use_smooth = True
    rig.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    return mo
