"""Volumetric puffs of exhaled smoke (shared with the Whale skit)."""
import bpy, random
from mathutils import Vector
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))


def make(name, n, t0, life=3.0, seed=5, color=(0.82, 0.82, 0.85)):
    m = bpy.data.materials.get('smoke') or _smoke_mat()
    rr = random.Random(seed); puffs = []
    for i in range(n):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
        o = bpy.context.active_object; o.name = f'{name}{i}'; o.data.materials.append(m); o.visible_shadow = False
        puffs.append(dict(o=o, b=t0 + i * 0.045, vx=rr.uniform(-0.06, 0.1), vy=rr.uniform(0.08, 0.18), vz=rr.uniform(0.1, 0.2), s=rr.uniform(0.7, 1.2), life=life))
    return puffs


def _smoke_mat():
    m = bpy.data.materials.new('smoke'); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    out = nt.nodes['Material Output']
    vol = nt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Color'].default_value = (0.82, 0.82, 0.85, 1)
    oi = nt.nodes.new('ShaderNodeObjectInfo'); noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 9; noise.inputs['Detail'].default_value = 6
    tc = nt.nodes.new('ShaderNodeTexCoord'); grad = nt.nodes.new('ShaderNodeTexGradient'); grad.gradient_type = 'SPHERICAL'
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul2 = nt.nodes.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'
    cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.45; cr.inputs['From Max'].default_value = 0.75
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(tc.outputs['Object'], grad.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], cr.inputs['Value']); nt.links.new(cr.outputs[0], mul.inputs[0]); nt.links.new(grad.outputs['Fac'], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0]); nt.links.new(oi.outputs['Alpha'], mul2.inputs[1])
    sc = nt.nodes.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 12.0
    nt.links.new(mul2.outputs[0], sc.inputs[0]); nt.links.new(sc.outputs[0], vol.inputs['Density'])
    nt.links.new(vol.outputs[0], out.inputs['Volume'])
    return m


def frame(puffs, src, t, f, K):
    for p in puffs:
        o = p['o']; age = t - p['b']; L = p['life']
        if age < 0 or age > L or src is None:
            K.add(o, 'hide_render', 0, f, 1); K.add(o, 'color', 3, f, 0.0)
            for i in range(3): K.add(o, 'scale', i, f, 0.01)
            continue
        K.add(o, 'hide_render', 0, f, 0)
        o0, fw = src; side = fw.cross(Vector((0, 0, 1))).normalized()
        pos = o0 + fw * (0.04 + p['vy'] * age) + side * (p['vx'] * age) + Vector((0, 0, p['vz'] * age * 0.9 - 0.02))
        sz = (0.022 + age * 0.085) * p['s']
        for i in range(3): K.add(o, 'location', i, f, pos[i]); K.add(o, 'scale', i, f, sz)
        K.add(o, 'color', 3, f, (1 - age / L) ** 1.5 * 0.85 * clamp(age / 0.1))


