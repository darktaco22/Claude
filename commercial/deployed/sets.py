"""Sets for "DEPLOYED": the drop ship (cargo hold + exterior) and the Backyard BBQ arena.

    import sets
    ship = sets.build_ship(tex_dir)          # dict: root empty, ramp hinge, lights, screens ...
    yard = sets.build_yard(asset_dir, tex_dir)

Everything is built from code so a worker can rebuild it from the repo alone. Ship parts are parented to
`ship['root']` (move that to put the ship at altitude). Units are metres; characters are about 1.7 m.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Vector

HALF_W = 2.2          # hold half width
HEIGHT = 3.05         # hold height
Y0, Y1 = -6.0, 6.0    # front bulkhead, rear (ramp) end
DOOR_W, DOOR_H = 2.9, 2.55


# ------------------------------------------------------------------ small helpers
def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def material(name, color, rough=0.6, metal=0.0, emit=None, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        bsdf.inputs['Emission Color'].default_value = (*emit, 1)
        bsdf.inputs['Emission Strength'].default_value = strength
    return mat


def add_bump(mat, scale=40.0, strength=0.25, kind='noise'):
    """Procedural surface wear so flat-coloured metal is not plastic."""
    tree = mat.node_tree
    bsdf = tree.nodes['Principled BSDF']
    coord = tree.nodes.new('ShaderNodeTexCoord')
    if kind == 'tread':
        tex = tree.nodes.new('ShaderNodeTexBrick')
        tex.inputs['Scale'].default_value = scale
        tex.inputs['Mortar Size'].default_value = 0.08
        out = tex.outputs['Fac']
    else:
        tex = tree.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = scale
        tex.inputs['Detail'].default_value = 6
        out = tex.outputs['Fac']
        ramp = tree.nodes.new('ShaderNodeMapRange')
        ramp.inputs['From Min'].default_value = 0.35
        ramp.inputs['From Max'].default_value = 0.75
        ramp.inputs['To Min'].default_value = bsdf.inputs['Roughness'].default_value * 0.6
        ramp.inputs['To Max'].default_value = min(1.0, bsdf.inputs['Roughness'].default_value * 1.5)
        tree.links.new(out, ramp.inputs['Value'])
        tree.links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])
    tree.links.new(coord.outputs['Object'], tex.inputs['Vector'])
    bump = tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = strength
    tree.links.new(out, bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def image_material(name, path, emit=0.0, alpha=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes['Principled BSDF']
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(path)
    tex.name = 'img'
    tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.5
    if emit:
        tree.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = emit
    if alpha:
        tree.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
        mat.blend_method = 'HASHED'
    return mat


def box(name, size, loc, mat, col, parent=None, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.location = loc
    obj.rotation_euler = rot
    _adopt(obj, mat, col, parent)
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return obj


def cylinder(name, radius, depth, loc, mat, col, parent=None, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts)
    obj = bpy.context.active_object
    obj.name = name
    obj.location = loc
    obj.rotation_euler = rot
    _adopt(obj, mat, col, parent)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def sphere(name, radius, loc, mat, col, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=24, ring_count=12)
    obj = bpy.context.active_object
    obj.name = name
    obj.location = loc
    obj.scale = scale
    _adopt(obj, mat, col, parent)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def plane(name, size_x, size_y, loc, mat, col, parent=None, rot=(0, 0, 0)):
    """Plane with UVs filling 0..1 (for labels and screens)."""
    bpy.ops.mesh.primitive_plane_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size_x, size_y, 1)
    obj.location = loc
    obj.rotation_euler = rot
    _adopt(obj, mat, col, parent)
    return obj


def _adopt(obj, mat, col, parent):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent


def light(name, kind, loc, energy, color, col, parent=None, size=0.3, rot=(0, 0, 0), spot=None):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == 'AREA':
        data.size = size
    elif kind == 'SPOT':
        data.spot_size = spot or math.radians(50)
        data.spot_blend = 0.4
        data.shadow_soft_size = size
    elif kind == 'POINT':
        data.shadow_soft_size = size
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    if parent:
        obj.parent = parent
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - Vector(obj.location)).to_track_quat('-Z', 'Y').to_euler()


# ------------------------------------------------------------------ hull profile
def profile(scale=1.0, steps=28, power=3.2):
    """Boxy arch (superellipse) from the right floor corner over the roof to the left floor corner."""
    points = []
    for index in range(steps + 1):
        angle = math.pi * index / steps
        cos, sin = math.cos(angle), math.sin(angle)
        x = HALF_W * scale * math.copysign(abs(cos) ** (2 / power), cos)
        z = HEIGHT * scale * abs(sin) ** (2 / power)
        points.append((x, z))
    return points


def arch_mesh(name, y_values, outer=1.0, inner=None, mat=None, col=None, parent=None, flip=False):
    """Sweep the profile along y. With `inner`, makes a solid ring (rib); without, a shell seen from inside."""
    mesh = bmesh.new()
    rows = []
    for y in y_values:
        rows.append([mesh.verts.new((x, y, z)) for x, z in profile(outer)])
    for a, b in zip(rows, rows[1:]):
        for i in range(len(a) - 1):
            face = (a[i], a[i + 1], b[i + 1], b[i]) if not flip else (a[i], b[i], b[i + 1], a[i + 1])
            mesh.faces.new(face)
    if inner:
        inner_rows = []
        for y in y_values:
            inner_rows.append([mesh.verts.new((x, y, z)) for x, z in profile(inner)])
        for a, b in zip(inner_rows, inner_rows[1:]):
            for i in range(len(a) - 1):
                mesh.faces.new((a[i], b[i], b[i + 1], a[i + 1]))
        for row, inner_row in ((rows[0], inner_rows[0]), (rows[-1], inner_rows[-1])):
            for i in range(len(row) - 1):
                mesh.faces.new((row[i], inner_row[i], inner_row[i + 1], row[i + 1]))
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
    data = bpy.data.meshes.new(name)
    mesh.to_mesh(data)
    mesh.free()
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    for poly in data.polygons:
        poly.use_smooth = True
    if mat:
        data.materials.append(mat)
    if parent:
        obj.parent = parent
    return obj


# ------------------------------------------------------------------ the ship
def build_ship(tex_dir):
    col = collection('SHIP')
    root = bpy.data.objects.new('SHIP', None)
    col.objects.link(root)

    hull_mat = add_bump(material('hull', (0.25, 0.29, 0.25), rough=0.5, metal=0.7), 3.0, 0.08)
    rib_mat = add_bump(material('rib', (0.16, 0.19, 0.16), rough=0.5, metal=0.7), 30.0, 0.15)
    floor_mat = add_bump(material('floor', (0.09, 0.095, 0.1), rough=0.45, metal=0.8), 7.0, 0.6, kind='tread')
    dark = material('dark', (0.03, 0.03, 0.035), rough=0.5, metal=0.5)
    strap = material('strap', (0.55, 0.12, 0.08), rough=0.85)
    canvas = material('canvas', (0.32, 0.3, 0.2), rough=0.95)
    yellow = material('hazard', (0.9, 0.62, 0.05), rough=0.6)
    wood = add_bump(material('crate', (0.42, 0.29, 0.16), rough=0.8), 14.0, 0.5)

    arch_mesh('hull', [Y0 - 0.05, Y1 + 0.05], 1.0, None, hull_mat, col, root)
    for index, y in enumerate([Y0 + 0.6 + 1.2 * k for k in range(10)]):
        arch_mesh(f'rib{index}', [y - 0.06, y + 0.06], 0.995, 0.94, rib_mat, col, root)
    for side in (-1, 1):                                         # stringers and bench
        for z, depth in ((1.05, 0.05), (2.2, 0.05)):
            box('stringer', (0.06, Y1 - Y0, depth), (side * 2.12, 0, z), rib_mat, col, root)
        box('bench', (0.42, 9.4, 0.05), (side * 1.86, -0.9, 0.46), canvas, col, root)
        for y in [Y0 + 0.7 + 1.2 * k for k in range(9)]:
            box('benchleg', (0.04, 0.04, 0.46), (side * 1.68, y, 0.23), rib_mat, col, root)
            box('web', (0.03, 0.05, 1.5), (side * 2.02, y + 0.6, 1.3), strap, col, root, rot=(0, side * 0.12, 0))
        cylinder('cable', 0.015, Y1 - Y0 - 0.4, (side * 0.85, 0, 2.72), dark, col, root, rot=(math.pi / 2, 0, 0), verts=8)
        for k in range(14):                                       # hand straps on the static line
            y = Y0 + 0.8 + k * 0.8
            box('handstrap', (0.035, 0.012, 0.42), (side * 0.85, y, 2.5), yellow, col, root)
            box('handloop', (0.12, 0.012, 0.035), (side * 0.85, y, 2.28), yellow, col, root)
    box('floor', (HALF_W * 2, Y1 - Y0, 0.06), (0, 0, -0.03), floor_mat, col, root)
    for k in range(7):                                            # hazard stripes at the ramp edge
        box('stripe', (0.2, 0.5, 0.004), (-1.2 + k * 0.4, Y1 - 0.4, 0.004), yellow, col, root, rot=(0, 0, 0.6))
    for x in (-0.55, 0.55):                                       # floor rails
        box('rail', (0.06, Y1 - Y0 - 0.6, 0.03), (x, -0.2, 0.012), rib_mat, col, root)

    # front bulkhead with cockpit door, monitor and copium tank
    box('bulkhead', (HALF_W * 2, 0.1, HEIGHT), (0, Y0, HEIGHT / 2), hull_mat, col, root)
    box('cockpit_door', (0.95, 0.06, 2.0), (-1.05, Y0 + 0.07, 1.0), rib_mat, col, root, bevel=0.02)
    cylinder('door_window', 0.2, 0.03, (-1.05, Y0 + 0.11, 1.55), material('glass_warm', (1, 0.7, 0.4), emit=(1, 0.62, 0.3), strength=2.0),
             col, root, rot=(math.pi / 2, 0, 0))
    box('monitor_frame', (1.9, 0.1, 1.2), (0.75, Y0 + 0.1, 1.85), dark, col, root, bevel=0.03)
    tank_glass = material('copium', (0.45, 0.1, 0.9), rough=0.15, emit=(0.7, 0.31, 0.96), strength=1.6)
    cylinder('tank', 0.2, 1.3, (-1.9, Y0 + 0.4, 1.5), tank_glass, col, root)
    for z in (0.82, 2.18):
        cylinder('tank_cap', 0.23, 0.08, (-1.9, Y0 + 0.4, z), rib_mat, col, root)
    cylinder('pipe', 0.05, 11.0, (-1.55, -0.4, 2.86), rib_mat, col, root, rot=(math.pi / 2, 0, 0), verts=12)
    cylinder('pipe_up', 0.05, 0.75, (-1.9, Y0 + 0.4, 2.55), rib_mat, col, root, verts=12)

    # rear frame around the door opening, and the ramp on a hinge
    side_w = HALF_W - DOOR_W / 2
    for side in (-1, 1):
        box('rear_side', (side_w + 0.3, 0.16, HEIGHT), (side * (DOOR_W / 2 + side_w / 2 + 0.15), Y1, HEIGHT / 2), hull_mat, col, root)
        box('jump_box', (0.2, 0.1, 0.46), (side * (DOOR_W / 2 + 0.22), Y1 - 0.12, 2.0), dark, col, root, bevel=0.015)
    box('rear_top', (DOOR_W + 0.1, 0.16, HEIGHT - DOOR_H), (0, Y1, DOOR_H + (HEIGHT - DOOR_H) / 2), hull_mat, col, root)
    hinge = bpy.data.objects.new('ramp_hinge', None)
    col.objects.link(hinge)
    hinge.parent = root
    hinge.location = (0, Y1 + 0.02, 0.0)
    ramp_len = DOOR_H + 0.25
    box('ramp', (DOOR_W, ramp_len, 0.1), (0, ramp_len / 2, -0.05), floor_mat, col, hinge)
    for x in (-DOOR_W / 2 + 0.05, DOOR_W / 2 - 0.05):
        box('ramp_edge', (0.08, ramp_len, 0.05), (x, ramp_len / 2, 0.02), yellow, col, hinge)
    hinge.rotation_euler = (math.radians(90), 0, 0)               # closed (upright); open is about -14 degrees

    # jump lights: red and green lens on each side box, with a real light
    lenses = {}
    for name, color, z in (('red', (1.0, 0.05, 0.03), 2.1), ('green', (0.1, 1.0, 0.2), 1.9)):
        mat = material('lens_' + name, color, rough=0.2, emit=color, strength=0.0)
        for side in (-1, 1):
            cylinder('lens_' + name, 0.065, 0.04, (side * (DOOR_W / 2 + 0.22), Y1 - 0.18, z), mat, col, root, rot=(math.pi / 2, 0, 0))
        lamp = light('jump_' + name, 'POINT', (0, Y1 - 0.7, 2.75), 0.0, color, col, root, size=0.5)
        lenses[name] = (mat, lamp)

    # ceiling lamps (caged), dim warm; they flicker on impacts
    lamp_mat = material('lamp', (1, 0.75, 0.5), emit=(1.0, 0.66, 0.36), strength=3.0)
    ceiling = []
    for k in range(5):
        y = Y0 + 1.4 + k * 2.3
        sphere('bulb', 0.07, (0, y, 2.9), lamp_mat, col, root, scale=(1, 1.6, 0.7))
        box('cage', (0.2, 0.34, 0.02), (0, y, 2.8), dark, col, root)
        ceiling.append(light(f'ceiling{k}', 'POINT', (0, y, 2.72), 55.0, (1.0, 0.7, 0.42), col, root, size=0.12))

    # portholes: glowing discs plus a warm spot from outside for each, making shafts in the haze
    port_mat = material('porthole', (1, 0.8, 0.6), emit=(1.0, 0.72, 0.45), strength=4.0)
    shafts = []
    for side in (-1, 1):
        for k in range(4):
            y = Y0 + 1.8 + k * 2.6
            cylinder('porthole', 0.19, 0.03, (side * 2.13, y, 1.95), port_mat, col, root, rot=(0, math.pi / 2, 0))
            cylinder('port_ring', 0.24, 0.02, (side * 2.15, y, 1.95), rib_mat, col, root, rot=(0, math.pi / 2, 0))
            if side == 1:
                spot = light(f'shaft{k}', 'SPOT', (side * 2.05, y, 1.95), 900.0, (1.0, 0.68, 0.38), col, root, size=0.05,
                             spot=math.radians(24))
                aim(spot, (-1.2, y - 1.0, 0.0))
                shafts.append(spot)

    # cargo: crates, the AIRDROP crate by the ramp, nets
    random.seed(4)
    for x, y, s in ((-1.75, -5.2, 0.7), (-1.72, -4.35, 0.55), (1.7, 4.9, 0.6)):
        box('crate', (s, s, s), (x, y, s / 2), wood, col, root, rot=(0, 0, random.uniform(-0.15, 0.15)), bevel=0.02)
        box('crate_strap', (s + 0.01, 0.07, s + 0.01), (x, y, s / 2), strap, col, root)
    airdrop = box('AIRDROP', (0.8, 0.8, 0.8), (1.05, 4.6, 0.4), wood, col, root, bevel=0.03)
    label = image_material('airdrop_label', os.path.join(tex_dir, 'airdrop.png'))
    for dx, dy, rot in ((0, -0.51, (math.pi / 2, 0, 0)), (0, 0.51, (math.pi / 2, 0, math.pi)), (-0.51, 0, (math.pi / 2, 0, -math.pi / 2)),
                        (0.51, 0, (math.pi / 2, 0, math.pi / 2))):
        plane('airdrop_label', 0.9, 0.9, (dx, dy, 0), label, col, airdrop, rot=rot)
    deck_label = image_material('deck_label', os.path.join(tex_dir, 'deck_one.png'), alpha=True)
    plane('deck_label', 2.4, 0.6, (-2.02, 1.2, 1.62), deck_label, col, root, rot=(math.pi / 2, 0, -math.pi / 2 - 0.1))
    plane('tank_label', 0.5, 0.16, (-1.9, Y0 + 0.62, 0.7), image_material('copium_label', os.path.join(tex_dir, 'copium.png'), alpha=True),
          col, root, rot=(math.pi / 2, 0, 0))

    # haze so the light shafts read
    haze = box('haze', (HALF_W * 2 - 0.1, Y1 - Y0 + 4.0, HEIGHT - 0.1), (0, 2.0, HEIGHT / 2), None, col, root)
    haze_mat = bpy.data.materials.new('haze')
    haze_mat.use_nodes = True
    tree = haze_mat.node_tree
    tree.nodes.remove(tree.nodes['Principled BSDF'])
    volume = tree.nodes.new('ShaderNodeVolumeScatter')
    volume.inputs['Density'].default_value = 0.035
    volume.inputs['Anisotropy'].default_value = 0.35
    tree.links.new(volume.outputs['Volume'], tree.nodes['Material Output'].inputs['Volume'])
    haze.data.materials.append(haze_mat)

    return {'root': root, 'col': col, 'hinge': hinge, 'lenses': lenses, 'ceiling': ceiling, 'shafts': shafts,
            'airdrop': airdrop, 'haze': haze, 'screen_at': (0.75, Y0 + 0.16, 1.85), 'screen_size': (1.76, 1.06),
            'lamp_mat': lamp_mat}


# ------------------------------------------------------------------ sky and sun
def world(hdri_path, strength=1.0, rotation_deg=0.0, camera_gain=0.45):
    wld = bpy.data.worlds.new('sky')
    bpy.context.scene.world = wld
    wld.use_nodes = True
    tree = wld.node_tree
    env = tree.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(hdri_path)
    mapping = tree.nodes.new('ShaderNodeMapping')
    coord = tree.nodes.new('ShaderNodeTexCoord')
    mapping.inputs['Rotation'].default_value = (0, 0, math.radians(rotation_deg))
    tree.links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
    tree.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
    background = tree.nodes['Background']
    tree.links.new(env.outputs['Color'], background.inputs['Color'])
    # the camera sees a darker sky than the one that lights the scene, so it keeps its colour instead of clipping
    path = tree.nodes.new('ShaderNodeLightPath')
    mix = tree.nodes.new('ShaderNodeMix')
    mix.inputs['A'].default_value = strength
    mix.inputs['B'].default_value = strength * camera_gain
    tree.links.new(path.outputs['Is Camera Ray'], mix.inputs['Factor'])
    tree.links.new(mix.outputs['Result'], background.inputs['Strength'])
    return wld


def sun(heading_deg=180.0, elevation_deg=14.0, energy=4.0, color=(1.0, 0.72, 0.45)):
    """Sun lamp. heading = compass direction the light travels toward (180 = toward -Y)."""
    data = bpy.data.lights.new('sun', 'SUN')
    data.energy = energy
    data.color = color
    data.angle = math.radians(2.0)
    obj = bpy.data.objects.new('sun', data)
    bpy.context.scene.collection.objects.link(obj)
    h, e = math.radians(heading_deg), math.radians(elevation_deg)
    direction = Vector((math.sin(h) * math.cos(e), math.cos(h) * math.cos(e), -math.sin(e)))
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return obj


# ------------------------------------------------------------------ the Backyard BBQ arena
# The units are toys in a real backyard: props are about six times life size. Our side is y < 0 (blue), the
# opponent's y > 0 (red). The paddling pool is the river, with a plank bridge on each lane (x = -5.5 and 5.5).
LANE = 5.5
TOWERS = {'our_left': (-LANE, -9.0), 'our_right': (LANE, -9.0), 'our_king': (0.0, -13.5),
          'their_left': (-LANE, 9.0), 'their_right': (LANE, 9.0), 'their_king': (0.0, 13.5)}


def lawn_material():
    mat = bpy.data.materials.new('lawn')
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes['Principled BSDF']
    coord = tree.nodes.new('ShaderNodeTexCoord')
    wave = tree.nodes.new('ShaderNodeTexWave')                  # mown stripes
    wave.inputs['Scale'].default_value = 0.42
    wave.inputs['Distortion'].default_value = 0.6
    wave.inputs['Detail'].default_value = 1.0
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 2.2
    noise.inputs['Detail'].default_value = 8
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.085, 0.2, 0.03, 1)
    ramp.color_ramp.elements[1].color = (0.2, 0.36, 0.06, 1)
    mix = tree.nodes.new('ShaderNodeMath')
    mix.operation = 'ADD'
    scale = tree.nodes.new('ShaderNodeMath')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = 0.45
    tree.links.new(coord.outputs['Object'], wave.inputs['Vector'])
    tree.links.new(coord.outputs['Object'], noise.inputs['Vector'])
    tree.links.new(noise.outputs['Fac'], scale.inputs[0])
    tree.links.new(wave.outputs['Fac'], mix.inputs[0])
    tree.links.new(scale.outputs[0], mix.inputs[1])
    tree.links.new(mix.outputs[0], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.9
    return mat


def tower(name, x, y, team, col, king=False):
    """Toy tower: stone body, team-coloured cap with battlements, a cannon on top. Returns its parts for wrecking."""
    stone = _shared('stone', lambda: add_bump(material('stone', (0.5, 0.48, 0.45), rough=0.85), 2.5, 0.5))
    color = (0.1, 0.3, 0.95) if team == 'blue' else (0.9, 0.12, 0.1)
    team_mat = _shared('team_' + team, lambda: material('team_' + team, color, rough=0.45))
    gold = _shared('gold', lambda: material('gold', (1.0, 0.72, 0.2), rough=0.3, metal=1.0))
    dark = _shared('gun', lambda: material('gun', (0.05, 0.05, 0.06), rough=0.4, metal=0.8))
    width, height = (3.2, 4.2) if king else (2.3, 3.0)
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.location = (x, y, 0)
    parts = [box(name + '_body', (width, width, height), (0, 0, height / 2), stone, col, root, bevel=0.08),
             box(name + '_band', (width + 0.12, width + 0.12, 0.35), (0, 0, height * 0.55), team_mat, col, root, bevel=0.04),
             box(name + '_cap', (width + 0.4, width + 0.4, 0.4), (0, 0, height + 0.2), team_mat, col, root, bevel=0.06)]
    count = 4 if king else 3
    for i in range(count):
        for j in range(count):
            if 0 < i < count - 1 and 0 < j < count - 1:
                continue
            step = (width + 0.4 - 0.5) / (count - 1)
            parts.append(box(name + '_merlon', (0.5, 0.5, 0.5), (-(width + 0.4) / 2 + 0.25 + i * step, -(width + 0.4) / 2 + 0.25 + j * step,
                                                              height + 0.65), stone, col, root, bevel=0.04))
    facing = 1 if team == 'blue' else -1
    parts.append(sphere(name + '_gun', 0.55 if king else 0.42, (0, 0, height + 0.75), dark, col, root))
    parts.append(cylinder(name + '_barrel', 0.2 if king else 0.15, 1.2, (0, facing * 0.6, height + 0.85), dark, col, root,
                          rot=(math.radians(80), 0, 0), verts=16))
    if king:
        for k in range(5):
            angle = k * math.tau / 5
            parts.append(box(name + '_crown', (0.22, 0.22, 0.7), (math.cos(angle) * 0.75, math.sin(angle) * 0.75 - facing * 0.9, height + 0.75),
                             gold, col, root, rot=(0, 0, angle)))
    return {'root': root, 'parts': parts, 'height': height, 'team': team, 'king': king}


_SHARED = {}


def _shared(key, make):
    if key not in _SHARED or _SHARED[key].name not in bpy.data.materials:
        _SHARED[key] = make()
    return _SHARED[key]


def duck(col, loc, size=1.0):
    yellow = material('duck', (1.0, 0.78, 0.05), rough=0.25)
    orange = material('duck_beak', (1.0, 0.35, 0.02), rough=0.3)
    black = material('duck_eye', (0.01, 0.01, 0.01), rough=0.1)
    root = bpy.data.objects.new('DUCK', None)
    col.objects.link(root)
    root.location = loc
    root.scale = (size, size, size)
    sphere('duck_body', 0.6, (0, 0, 0.35), yellow, col, root, scale=(1.0, 1.35, 0.8))
    sphere('duck_tail', 0.25, (0, -0.75, 0.6), yellow, col, root, scale=(0.8, 1.0, 0.8))
    sphere('duck_head', 0.4, (0, 0.55, 1.05), yellow, col, root)
    sphere('duck_beak', 0.2, (0, 0.95, 0.98), orange, col, root, scale=(1.1, 1.3, 0.45))
    for side in (-1, 1):
        sphere('duck_eye', 0.07, (side * 0.2, 0.86, 1.2), black, col, root)
        sphere('duck_wing', 0.3, (side * 0.55, -0.05, 0.45), yellow, col, root, scale=(0.35, 1.2, 0.7))
    return root


def build_yard(tex_dir, asset_dir=None, grass=True):
    col = collection('YARD')
    lawn = plane('lawn', 90, 100, (0, 0, 0), lawn_material(), col)
    wood = add_bump(material('plank', (0.5, 0.33, 0.17), rough=0.75), 6.0, 0.5)
    white = material('white_paint', (0.85, 0.83, 0.78), rough=0.6)
    pool_blue = material('pool_blue', (0.05, 0.35, 0.9), rough=0.25)
    pool_white = material('pool_white', (0.9, 0.92, 0.95), rough=0.25)
    water = material('water', (0.02, 0.35, 0.6), rough=0.04)
    water.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.5
    add_bump(water, 1.4, 0.12)
    dark = material('yard_dark', (0.03, 0.03, 0.035), rough=0.4, metal=0.6)
    red = material('yard_red', (0.8, 0.08, 0.06), rough=0.4)

    # paddling pool river: three stacked tubes on each bank, water between, round ends
    half = 12.5
    for side in (-1, 1):
        for k, mat in enumerate((pool_blue, pool_white, pool_blue)):
            cylinder('pool_tube', 0.28, half * 2, (0, side * 1.75, 0.26 + k * 0.42), mat, col, rot=(0, math.pi / 2, 0))
            cylinder('pool_end', 0.28, 3.5, (side * half, 0, 0.26 + k * 0.42), mat, col, rot=(math.pi / 2, 0, 0))
    plane('water', half * 2, 3.3, (0, 0, 0.95), water, col)
    bridges = []
    for x in (-LANE, LANE):
        for k in range(9):                                       # arched plank bridge over the pool wall
            y = -2.6 + k * 0.65
            z = 1.5 - 0.11 * (k - 4) ** 2 * 0.55
            bridges.append(box('bridge_plank', (2.3, 0.58, 0.14), (x, y, z), wood, col, rot=(-(k - 4) * 0.12, 0, 0), bevel=0.02))
        for side in (-1, 1):
            box('bridge_ramp', (2.3, 1.6, 0.12), (x, side * 3.5, 0.55), wood, col, rot=(side * -0.62, 0, 0))

    towers = {name: tower(name, x, y, 'blue' if name.startswith('our') else 'red', col, king='king' in name)
              for name, (x, y) in TOWERS.items()}
    the_duck = duck(col, (9.3, 0.1, 0.72), 1.0)

    # picket fence (giant): rails and pickets on three sides
    random.seed(7)
    for x in (-15.0, 15.0):
        for k in range(46):
            y = -23 + k * 1.02
            box('picket', (0.14, 0.9, 7.0 + (0.5 if k % 2 else 0)), (x, y, 3.5), white, col, rot=(0, 0, random.uniform(-0.03, 0.03)))
        for z in (1.6, 5.2):
            box('fence_rail', (0.2, 47.0, 0.5), (x - math.copysign(0.2, x), 0, z), white, col)
    for k in range(30):
        box('picket', (0.9, 0.14, 7.0 + (0.5 if k % 2 else 0)), (-14.8 + k * 1.02, 24.0, 3.5), white, col)

    # the kettle grill behind the opponent's king tower, with glowing coals
    cylinder('grill_bowl', 4.2, 2.2, (0, 20.0, 7.4), dark, col, verts=48)
    sphere('grill_lid', 4.25, (0, 20.0, 8.6), dark, col, scale=(1, 1, 0.55))
    for k in range(3):
        angle = k * math.tau / 3 + 0.5
        leg = cylinder('grill_leg', 0.16, 7.4, (math.cos(angle) * 3.0, 20.0 + math.sin(angle) * 3.0, 3.6), _shared('gun', lambda: dark), col,
                       rot=(math.sin(angle) * 0.22, -math.cos(angle) * 0.22, 0))
    coals = material('coals', (1, 0.3, 0.05), emit=(1.0, 0.25, 0.04), strength=6.0)
    cylinder('grill_glow', 4.0, 0.1, (0, 20.0, 6.25), coals, col, verts=48)
    light('grill_light', 'POINT', (0, 18.0, 5.6), 9000.0, (1.0, 0.35, 0.1), col, size=2.0)

    # trampoline on our right
    tramp = bpy.data.objects.new('TRAMPOLINE', None)
    col.objects.link(tramp)
    tramp.location = (9.5, -5.0, 0)
    mat_black = material('tramp_mat', (0.02, 0.02, 0.025), rough=0.7)
    cylinder('tramp_mat', 2.3, 0.06, (0, 0, 1.3), mat_black, col, tramp, verts=48)
    bpy.ops.mesh.primitive_torus_add(major_radius=2.5, minor_radius=0.22, major_segments=48, minor_segments=10)
    pad = bpy.context.active_object
    pad.location = (0, 0, 1.32)
    _adopt(pad, pool_blue, col, tramp)
    for poly in pad.data.polygons:
        poly.use_smooth = True
    for k in range(6):
        angle = k * math.tau / 6
        cylinder('tramp_leg', 0.07, 1.3, (math.cos(angle) * 2.5, math.sin(angle) * 2.5, 0.65), dark, col, tramp, verts=10)

    # cooler, string lights on poles, tiki torches
    box('cooler', (4.6, 3.0, 2.6), (-11.0, 4.5, 1.3), red, col, rot=(0, 0, 0.25), bevel=0.15)
    box('cooler_lid', (4.7, 3.1, 0.6), (-11.0, 4.5, 2.9), pool_white, col, rot=(0, 0, 0.25), bevel=0.15)
    bulb_mat = material('bulb', (1, 0.8, 0.5), emit=(1.0, 0.7, 0.35), strength=9.0)
    poles = [(-13.5, -21.0), (13.5, -8.0), (-13.5, 6.0), (13.5, 21.0)]
    for x, y in poles:
        cylinder('pole', 0.14, 11.0, (x, y, 5.5), wood, col, verts=10)
    for (x0, y0), (x1, y1) in zip(poles, poles[1:]):
        for k in range(1, 22):
            u = k / 22
            sag = 2.2 * 4 * u * (1 - u)
            sphere('string_bulb', 0.16, (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, 10.8 - sag), bulb_mat, col)
    flame = material('flame', (1, 0.5, 0.1), emit=(1.0, 0.45, 0.08), strength=7.0)
    torches = []
    for x, y in ((-12.5, -12.0), (12.5, 12.0), (-12.5, 14.0), (12.5, -17.0)):
        cylinder('tiki', 0.12, 5.0, (x, y, 2.5), wood, col, verts=10)
        cylinder('tiki_head', 0.34, 0.8, (x, y, 5.2), wood, col, verts=12)
        bpy.ops.mesh.primitive_cone_add(radius1=0.26, depth=0.9, vertices=12)
        cone = bpy.context.active_object
        cone.location = (x, y, 6.0)
        _adopt(cone, flame, col, None)
        torches.append(light('tiki_light', 'POINT', (x, y, 6.2), 2500.0, (1.0, 0.5, 0.15), col, size=0.4))

    scattered = None
    if grass and asset_dir:
        scattered = _grass(lawn, asset_dir, col)
    return {'col': col, 'lawn': lawn, 'towers': towers, 'duck': the_duck, 'trampoline': tramp, 'grass': scattered}


def _grass(lawn, asset_dir, col):
    """Scanned grass clumps (Poly Haven, CC0) over the playing field only, scaled up for the toy-sized units."""
    import polyhaven
    import scatter
    objs = polyhaven.pick(polyhaven.append_model(asset_dir, 'grass_bermuda_01', '1k'))
    objs = [obj for obj in objs if not any(word in obj.name for word in ('dead', 'single', 'seedling', 'medium'))]
    for obj in objs:                                             # bake each object's own scale into its mesh:
        obj.data.transform(obj.matrix_basis)                     # the scatter resets instance transforms
        obj.matrix_basis.identity()
        print('GRASS', obj.name, tuple(round(v, 3) for v in obj.dimensions))
    field = plane('grass_field', 29, 44, (0, 0, 0.005), None, col)
    for vertex in field.data.vertices:                           # real-size mesh: geometry nodes work in local space,
        vertex.co.x *= 29                                        # so an object scale would stretch every instance
        vertex.co.y *= 44
    field.scale = (1, 1, 1)
    field.data.materials.append(lawn.data.materials[0])
    return scatter.scatter(field, objs, density=34.0, scale=(4.0, 6.5), seed=3, name='yard_grass')


def build_exterior(ship):
    """Outside of the drop ship for the opening shot: nose, wings, four engines with prop discs, tail."""
    col, root = ship['col'], ship['root']
    skin = add_bump(material('skin', (0.2, 0.24, 0.2), rough=0.5, metal=0.6), 2.0, 0.1)
    dark = material('skin_dark', (0.05, 0.055, 0.06), rough=0.4, metal=0.7)
    glass = material('canopy', (0.3, 0.2, 0.1), rough=0.1, emit=(1.0, 0.6, 0.25), strength=1.5)
    prop = material('prop_disc', (0.1, 0.1, 0.1), rough=0.3)
    prop.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.22
    prop.blend_method = 'BLEND'
    belly = box('belly', (HALF_W * 2 + 0.1, Y1 - Y0 + 0.2, 0.5), (0, 0, -0.3), skin, col, root, bevel=0.12)
    nose_col = collection('NOSE')                                 # separate so interior shots can hide it (it reaches into the hold)
    nose = sphere('nose', 1.0, (0, Y0 - 0.3, 1.45), skin, nose_col, root, scale=(HALF_W * 1.02, 3.4, 1.62))
    sphere('canopy', 1.0, (0, Y0 - 1.9, 2.1), glass, nose_col, root, scale=(1.5, 1.4, 0.75))
    box('wing', (27.0, 3.4, 0.38), (0, -1.2, HEIGHT + 0.1), skin, col, root, bevel=0.15)
    for x in (-9.0, -4.6, 4.6, 9.0):
        cylinder('engine', 0.62, 3.2, (x, -2.4, HEIGHT - 0.25), dark, col, root, rot=(math.pi / 2, 0, 0))
        cylinder('spinner', 0.2, 0.7, (x, -4.3, HEIGHT - 0.25), skin, col, root, rot=(math.pi / 2, 0, 0), verts=12)
        cylinder('prop', 1.9, 0.03, (x, -4.25, HEIGHT - 0.25), prop, col, root, rot=(math.pi / 2, 0, 0), verts=32)
    box('boom', (1.3, 6.5, 1.2), (0, Y1 + 2.6, HEIGHT + 0.6), skin, col, root, rot=(math.radians(14), 0, 0), bevel=0.2)
    box('fin', (0.3, 3.2, 4.2), (0, Y1 + 5.2, HEIGHT + 3.2), skin, col, root, rot=(math.radians(-22), 0, 0), bevel=0.1)
    box('tailplane', (9.5, 2.0, 0.26), (0, Y1 + 5.6, HEIGHT + 1.9), skin, col, root, bevel=0.1)
    return [belly, nose]
