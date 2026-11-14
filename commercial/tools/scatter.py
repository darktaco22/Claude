"""Geometry-nodes scatter: instance a set of objects over a surface (grass, rocks, flowers).

    import scatter
    scatter.scatter(ground_obj, [grass_a, grass_b], density=40, scale=(0.7, 1.3), seed=1, name='Grass')

Instances cost almost no memory, so density can be high. Works in Blender 4.2.
"""
import bpy


def scatter(surface, objs, density=20.0, scale=(0.8, 1.2), seed=0, name='Scatter', align=True):
    col = bpy.data.collections.new(name + '_src')
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi, go = N.new('NodeGroupInput'), N.new('NodeGroupOutput')
    pts = N.new('GeometryNodeDistributePointsOnFaces')
    pts.inputs['Density'].default_value = density
    pts.inputs['Seed'].default_value = seed
    ci = N.new('GeometryNodeCollectionInfo')
    ci.inputs['Collection'].default_value = col
    ci.inputs['Separate Children'].default_value = True
    ci.inputs['Reset Children'].default_value = True
    inst = N.new('GeometryNodeInstanceOnPoints')
    inst.inputs['Pick Instance'].default_value = True
    rs = N.new('FunctionNodeRandomValue'); rs.data_type = 'FLOAT'
    rs.inputs[2].default_value, rs.inputs[3].default_value = scale
    rr = N.new('FunctionNodeRandomValue'); rr.data_type = 'FLOAT_VECTOR'
    rr.inputs[0].default_value = (0, 0, 0); rr.inputs[1].default_value = (0.12, 0.12, 6.283)
    join = N.new('GeometryNodeJoinGeometry')
    L.new(gi.outputs[0], pts.inputs['Mesh'])
    L.new(pts.outputs['Points'], inst.inputs['Points'])
    L.new(ci.outputs[0], inst.inputs['Instance'])
    L.new(rs.outputs[1], inst.inputs['Scale'])
    L.new(rr.outputs[0], inst.inputs['Rotation'])
    L.new(gi.outputs[0], join.inputs[0]); L.new(inst.outputs[0], join.inputs[0])
    L.new(join.outputs[0], go.inputs[0])
    m = surface.modifiers.new(name, 'NODES'); m.node_group = ng
    col.hide_render = False
    return m
