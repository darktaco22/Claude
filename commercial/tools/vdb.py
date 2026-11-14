"""Load downloaded OpenVDB fire/smoke/cloud volumes (e.g. CGHeven, JangaFX; both CC0) with a ready material.

    import vdb
    v = vdb.load('/path/frame_060.vdb', height=3.0, location=(0, 0, 0))     # one frame
    v = vdb.load('/path/CampFire_02_VDB_000.vdb', sequence=(200, 1, 0))     # frames, start frame, file offset

EmberGen exports are in voxel units (about 1000 wide), so `height` rescales them. Grid names vary
(density / flames / temperature); the material uses whichever exist.

Test:  blender -b -P vdb.py -- FILE.vdb out.png
"""
import bpy
from mathutils import Vector


def load(path, height=3.0, location=(0, 0, 0), sequence=None, density=1.0, fire=1.0,
         smoke_color=(0.45, 0.42, 0.4), fire_color=(1.0, 0.42, 0.08)):
    bpy.ops.object.volume_import(filepath=path)
    v = bpy.context.object
    if sequence:
        v.data.is_sequence = True
        v.data.frame_duration, v.data.frame_start, v.data.frame_offset = sequence
        v.data.sequence_mode = 'CLIP'
    v.data.grids.load()
    names = [g.name for g in v.data.grids]
    zs = [c[2] for c in v.bound_box]; xs = [c[0] for c in v.bound_box]; ys = [c[1] for c in v.bound_box]
    k = height / max(1e-6, max(zs) - min(zs))
    v.scale = (k, k, k)
    v.location = Vector(location) - Vector(((min(xs) + max(xs)) / 2 * k, (min(ys) + max(ys)) / 2 * k, min(zs) * k))
    mat = bpy.data.materials.new('VDB'); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Color'].default_value = (*smoke_color, 1)
    pv.inputs['Blackbody Intensity'].default_value = 0.0
    # densities are per voxel unit, so compensate for the rescale
    dn = next((n for n in names if n.lower() in ('density', 'smoke', 'soot')), None)
    if dn:
        a = nt.nodes.new('ShaderNodeAttribute'); a.attribute_name = dn
        m = nt.nodes.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; m.inputs[1].default_value = density * 4.0
        nt.links.new(a.outputs['Fac'], m.inputs[0]); nt.links.new(m.outputs[0], pv.inputs['Density'])
    else:
        pv.inputs['Density'].default_value = 0.0
    fn = next((n for n in names if n.lower() in ('flames', 'flame', 'temperature', 'heat', 'fire')), None)
    if fn:
        a = nt.nodes.new('ShaderNodeAttribute'); a.attribute_name = fn
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        e = ramp.color_ramp.elements
        e[0].position = 0.0; e[0].color = (0.6, 0.05, 0.0, 1)
        e[1].position = 1.0; e[1].color = (1.0, 0.85, 0.5, 1)
        mid = e.new(0.4); mid.color = (*fire_color, 1)
        m = nt.nodes.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; m.inputs[1].default_value = fire
        nt.links.new(a.outputs['Fac'], ramp.inputs[0]); nt.links.new(a.outputs['Fac'], m.inputs[0])
        nt.links.new(ramp.outputs[0], pv.inputs['Emission Color']); nt.links.new(m.outputs[0], pv.inputs['Emission Strength'])
    nt.links.new(pv.outputs[0], out.inputs['Volume'])
    v.data.materials.append(mat)
    v['grids'] = ','.join(names)
    return v


if __name__ == '__main__':
    import sys, math
    f, outp = sys.argv[sys.argv.index('--') + 1:][:2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=40)
    v = load(f, height=3.0)
    print('GRIDS', v['grids'], [(g.name, g.data_type) for g in v.data.grids])
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.03, 0.04, 0.07, 1)
    cd = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, -8, 1.6); cam.rotation_euler = (math.radians(89), 0, 0)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = True
    sc.cycles.volume_step_rate = 1.0; sc.cycles.volume_max_steps = 256
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.filepath = outp; bpy.ops.render.render(write_still=True)
