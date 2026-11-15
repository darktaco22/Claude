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
def world(hdri_path, strength=1.0, rotation_deg=0.0):
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
    background.inputs['Strength'].default_value = strength
    tree.links.new(env.outputs['Color'], background.inputs['Color'])
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
