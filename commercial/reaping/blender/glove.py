"""A white cartoon glove on a pinstripe sleeve (the Whale's hand for the bowl inserts), with knuckle pivots to curl."""
import bpy, math
from mathutils import Vector
from common import mat, sphere, cyl, link
def pinstripe():
    m = bpy.data.materials.new('pinstripe'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); w = N.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'; w.inputs['Scale'].default_value = 60; w.inputs['Distortion'].default_value = 0
    L.new(tc.outputs['Object'], w.inputs['Vector']); cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.9; cr.color_ramp.elements[1].position = 0.95
    cr.color_ramp.elements[0].color = (0.035, 0.05, 0.11, 1); cr.color_ramp.elements[1].color = (0.45, 0.47, 0.55, 1)
    L.new(w.outputs['Fac'], cr.inputs['Fac']); L.new(cr.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.7
    b.inputs['Sheen Weight'].default_value = 0.6; return m
def build(name='glove'):
    cotton = mat('glove_cotton', (0.92, 0.91, 0.88), 0.85, **{'Sheen Weight': 0.8, 'Sheen Roughness': 0.5, 'Subsurface Weight': 0.08})
    wrist = link(bpy.data.objects.new(name, None)); wrist.empty_display_size = 0.05; wrist.rotation_mode = 'XYZ'
    # local frame: fingers point -Z (down), palm faces +Y (toward the camera side)
    def part(o, parent):
        o.parent = parent; return o
    cuff = part(cyl(name + '_cuff', 0.052, 0.07, (0, 0, 0.03), cotton, r2=0.062), wrist)
    for i, z in enumerate((0.012, 0.03, 0.048)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.056 + i * 0.002, minor_radius=0.0025, location=(0, 0, z)); t = bpy.context.object; t.data.materials.append(cotton); part(t, wrist)
    sleeve = part(cyl(name + '_sleeve', 0.058, 0.6, (0, 0, 0.36), pinstripe()), wrist)
    palm = part(sphere(name + '_palm', 1.0, (0, 0, -0.06), cotton), wrist); palm.scale = (0.052, 0.03, 0.06)
    fingers = []
    for i, (x, L_) in enumerate(((-0.033, 0.07), (-0.011, 0.08), (0.011, 0.078), (0.032, 0.066))):
        piv = link(bpy.data.objects.new(f'{name}_k{i}', None)); piv.parent = wrist; piv.location = (x, 0.0, -0.105); piv.rotation_mode = 'XYZ'
        seg = cyl(f'{name}_f{i}', 0.0135, L_, (0, 0, -L_ / 2), cotton); seg.parent = piv
        tip = sphere(f'{name}_t{i}', 0.0135, (0, 0, -L_), cotton, seg=16); tip.parent = piv
        bpy.ops.object.select_all(action='DESELECT'); fingers.append(piv)
    tp = link(bpy.data.objects.new(f'{name}_thumb', None)); tp.parent = wrist; tp.location = (0.045, 0.012, -0.06); tp.rotation_mode = 'XYZ'; tp.rotation_euler = (0.3, 0, -0.6)
    ts = cyl(f'{name}_thumbseg', 0.014, 0.06, (0, 0, -0.03), cotton); ts.parent = tp; tt = sphere(f'{name}_thumbtip', 0.014, (0, 0, -0.06), cotton, seg=16); tt.parent = tp
    for o in [o for o in bpy.data.objects if o.name.startswith(name) and o.type == 'MESH']:
        sd = o.modifiers.new('sd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1
    return wrist, fingers, tp
def curl(fingers, thumb, f, amount):
    for i, k in enumerate(fingers):
        k.rotation_euler = (-amount * (1.2 + 0.1 * i), 0, 0); k.keyframe_insert('rotation_euler', frame=f)
    thumb.rotation_euler = (0.3 - amount * 0.5, 0, -0.6 + amount * 0.5); thumb.keyframe_insert('rotation_euler', frame=f)
