"""Real simulated fire and smoke (Blender's built-in Mantaflow), no downloads needed.

    import fire
    dom = fire.burst(location=(0, 0, 0), size=6, start=1, end=60, cache='/root/work/fire1', res=64,
                     kind='BOTH', burst_frames=6)   # short emission = explosion puff; long = bonfire
    fire.bake(dom)                                   # writes an OpenVDB cache, reusable across renders

Test:  blender -b -P fire.py -- CACHE_DIR out.png
"""
import bpy


def burst(location=(0, 0, 0), size=6.0, start=1, end=60, cache='/tmp/fire', res=64, kind='BOTH',
          burst_frames=8, emitter_radius=0.5, velocity=6.0, name='Fire'):
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_cube_add(size=size, location=(location[0], location[1], location[2] + size / 2))
    dom = bpy.context.object; dom.name = name + 'Domain'
    m = dom.modifiers.new('Fluid', 'FLUID'); m.fluid_type = 'DOMAIN'
    d = m.domain_settings
    d.domain_type = 'GAS'; d.resolution_max = res
    d.cache_type = 'ALL'; d.cache_data_format = 'OPENVDB'; d.cache_directory = cache
    d.cache_frame_start, d.cache_frame_end = start, end
    d.use_adaptive_domain = False; d.vorticity = 0.6; d.burning_rate = 0.9; d.flame_vorticity = 0.6
    d.use_noise = False
    bpy.ops.mesh.primitive_ico_sphere_add(radius=emitter_radius, location=(location[0], location[1], location[2] + emitter_radius))
    em = bpy.context.object; em.name = name + 'Emitter'; em.hide_render = True
    fm = em.modifiers.new('Fluid', 'FLUID'); fm.fluid_type = 'FLOW'
    f = fm.flow_settings
    f.flow_type = kind; f.flow_behavior = 'INFLOW'; f.fuel_amount = 1.5; f.density = 1.0
    f.use_initial_velocity = True; f.velocity_normal = velocity
    f.use_inflow = True; f.keyframe_insert('use_inflow', frame=start)
    f.use_inflow = False; f.keyframe_insert('use_inflow', frame=start + burst_frames)
    # material: Principled Volume reads the density / flame / temperature grids
    mat = bpy.data.materials.new(name + 'Vol'); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs["Density"].default_value = 2.5
    pv.inputs['Color'].default_value = (0.5, 0.47, 0.44, 1)
    pv.inputs["Blackbody Intensity"].default_value = 0.0
    pv.inputs['Temperature'].default_value = 1500
    fl = nt.nodes.new('ShaderNodeAttribute'); fl.attribute_name = 'flame'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.05; ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.6; ramp.color_ramp.elements[1].color = (1.0, 0.45, 0.08, 1)
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 5.0
    nt.links.new(fl.outputs['Fac'], ramp.inputs[0]); nt.links.new(fl.outputs['Fac'], mul.inputs[0])
    nt.links.new(ramp.outputs[0], pv.inputs['Emission Color']); nt.links.new(mul.outputs[0], pv.inputs['Emission Strength'])
    nt.links.new(pv.outputs[0], out.inputs['Volume'])
    dom.data.materials.append(mat)
    return dom


def bake(dom):
    bpy.context.view_layer.objects.active = dom
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        bpy.ops.fluid.bake_all()


if __name__ == '__main__':
    import sys, math
    cache, out = sys.argv[sys.argv.index('--') + 1:][:2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, 40
    bpy.ops.mesh.primitive_plane_add(size=40)
    dom = burst(cache=cache, end=40, res=96); bake(dom)
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.07, 0.12, 1)
    cd = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, -13, 2.5); cam.rotation_euler = (math.radians(88), 0, 0)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    for fr in (8, 16):
        sc.frame_set(fr); sc.render.filepath = out.replace('.png', f'_{fr}.png'); bpy.ops.render.render(write_still=True)
