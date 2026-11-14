"""Stock-footage effects on a card: a video (explosion, smoke, muzzle flash) on a plane that faces the camera.

    import fxcard
    c = fxcard.card('/path/explosion.mp4', location=(0, 4, 2), height=5, cam=cam, start=20, strength=4)

Footage shot on black is used as emission with alpha from brightness, so it adds light without a black box.
Cheap (renders like a texture), art-directable, and how most film explosions are done. CC0 clips: cgheven.com.
"""
import bpy


def card(path, location=(0, 0, 0), height=4.0, cam=None, start=1, strength=3.0, alpha_gain=2.5, name='FX', light=0.0,
         light_color=(1.0, 0.55, 0.2)):
    img = bpy.data.images.load(path)
    w, h = img.size
    bpy.ops.mesh.primitive_plane_add(size=1, location=location)
    o = bpy.context.object; o.name = name
    o.scale = (height * w / h, height, 1)
    o.rotation_euler = (1.5708, 0, 0)
    mat = bpy.data.materials.new(name); mat.use_nodes = True; mat.blend_method = 'BLEND'
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.extension = 'CLIP'
    tex.image_user.frame_duration = max(1, img.frame_duration); tex.image_user.frame_start = start
    tex.image_user.use_auto_refresh = True; tex.image_user.use_cyclic = False
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    g = nt.nodes.new('ShaderNodeMath'); g.operation = 'MULTIPLY'; g.inputs[1].default_value = alpha_gain; g.use_clamp = True
    nt.links.new(tex.outputs['Color'], em.inputs['Color']); nt.links.new(tex.outputs['Color'], bw.inputs[0])
    nt.links.new(bw.outputs[0], g.inputs[0]); nt.links.new(g.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    o.data.materials.append(mat)
    o.visible_shadow = False
    if cam is not None:
        c = o.constraints.new('TRACK_TO'); c.target = cam; c.track_axis = 'TRACK_Z'; c.up_axis = 'UP_Y'
        o.rotation_euler = (0, 0, 0)
    if light:
        # a card emits almost no useful light; pair it with a point light so the scene reacts
        d = bpy.data.lights.new(name + '.light', 'POINT'); d.energy = light; d.color = light_color
        d.shadow_soft_size = height * 0.3
        L = bpy.data.objects.new(name + '.light', d); bpy.context.scene.collection.objects.link(L); L.location = location
        o['light'] = L.name
    return o
