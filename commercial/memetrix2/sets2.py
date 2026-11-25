"""THE MEMETRIX II: the new sets (burning café, the Whale's white room) and the rooftop rain.
Builds on episode 1's helpers (../memetrix/mxsets.py) and keeps its conventions: one collection per set, lights in L_<SET>,
atmosphere objects tagged cine_ignore so the camera solver looks through them.
"""
import glob
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'memetrix'))
import mxsets  # noqa: E402
from mxsets import box, collection, cylinder, dust, haze, light, material, plane, screen, sphere  # noqa: E402

ORIGIN = dict(mxsets.ORIGIN, CAFE=Vector((600, 0, 0)), WHITE=Vector((800, 0, 0)))


def _drive(id_data, path, expr, index=-1):
    """A driver with a simple expression of `frame` (evaluated without Python, safe headless)."""
    fc = id_data.driver_add(path, index) if index >= 0 else id_data.driver_add(path)
    fc.driver.type = 'SCRIPTED'
    fc.driver.expression = expr
    return fc


def flame_material(name, seed=0.0):
    """Animated flame: a vertical gradient times moving 4D noise, emissive orange to yellow, transparent outside."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nt = mat.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 4.0
    noise.inputs['Detail'].default_value = 3.0
    _drive(noise.inputs['W'], 'default_value', f'frame / 9 + {seed}')
    nt.links.new(tc.outputs['Generated'], noise.inputs['Vector'])
    shape = nt.nodes.new('ShaderNodeMath')                      # 1 at the base fading to 0 at the top, minus the noise bite
    shape.operation = 'SUBTRACT'
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs['Y'], inv.inputs[1])                # (a plane's height on the card is its local Y)
    nt.links.new(inv.outputs[0], shape.inputs[0])
    bite = nt.nodes.new('ShaderNodeMath')
    bite.operation = 'MULTIPLY'
    bite.inputs[1].default_value = 0.9
    nt.links.new(noise.outputs['Fac'], bite.inputs[0])
    nt.links.new(bite.outputs[0], shape.inputs[1])
    side = nt.nodes.new('ShaderNodeMath')                       # narrower toward the edges of the card
    side.operation = 'PINGPONG'
    side.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs['X'], side.inputs[0])
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    nt.links.new(shape.outputs[0], mul.inputs[0])
    nt.links.new(side.outputs[0], mul.inputs[1])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (0.9, 0.06, 0.0, 1)              # edges deep orange, never brown
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (1.0, 0.62, 0.12, 1)
    mid = ramp.color_ramp.elements.new(0.3)
    mid.color = (1.0, 0.16, 0.01, 1)
    nt.links.new(mul.outputs[0], ramp.inputs[0])
    alpha = nt.nodes.new('ShaderNodeMath')
    alpha.operation = 'GREATER_THAN'
    alpha.inputs[1].default_value = 0.18
    nt.links.new(mul.outputs[0], alpha.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 9.0                       # (higher goes pink-white under AgX)
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(alpha.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def fire_material(name, seed=0.0):
    """Volumetric fire: climbing 4D noise, cut off with height and toward the edges, emitting orange to yellow by its heat.
    (Object coordinates of the unit cube; a first blackbody version came out almost black.)"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    tc = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])            # x, y, z in -0.5..0.5
    off = N('ShaderNodeVectorMath'); off.operation = 'ADD'
    _drive(off.inputs[1], 'default_value', '-frame * 0.07', index=2)                  # the flame climbs
    L(tc.outputs['Object'], off.inputs[0])
    noise = N('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 5.0; noise.inputs['Detail'].default_value = 8.0; noise.inputs['Roughness'].default_value = 0.7
    noise.inputs['Distortion'].default_value = 1.2                                     # licking, ragged tongues
    _drive(noise.inputs['W'], 'default_value', f'frame / 12 + {seed}')
    L(off.outputs[0], noise.inputs['Vector'])
    # falloff = (0.5 - z) * (1 - 2 * radius): 1 at the base centre, 0 at the top and the sides
    up = N('ShaderNodeMath'); up.operation = 'SUBTRACT'; up.inputs[0].default_value = 0.5; L(sep.outputs['Z'], up.inputs[1])
    xy = N('ShaderNodeCombineXYZ'); L(sep.outputs['X'], xy.inputs['X']); L(sep.outputs['Y'], xy.inputs['Y'])
    rad = N('ShaderNodeVectorMath'); rad.operation = 'LENGTH'; L(xy.outputs[0], rad.inputs[0])
    side = N('ShaderNodeMath'); side.operation = 'MULTIPLY_ADD'; side.use_clamp = True
    side.inputs[1].default_value = -2.0; side.inputs[2].default_value = 1.0; L(rad.outputs[1], side.inputs[0])
    fall = N('ShaderNodeMath'); fall.operation = 'MULTIPLY'; L(up.outputs[0], fall.inputs[0]); L(side.outputs[0], fall.inputs[1])
    # heat = noise * falloff, sharpened into tongues
    heat = N('ShaderNodeMath'); heat.operation = 'MULTIPLY'; L(noise.outputs['Fac'], heat.inputs[0]); L(fall.outputs[0], heat.inputs[1])
    tongue = N('ShaderNodeMapRange'); tongue.clamp = True
    tongue.inputs['From Min'].default_value = 0.14; tongue.inputs['From Max'].default_value = 0.34
    L(heat.outputs[0], tongue.inputs['Value'])
    ramp = N('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (0.55, 0.03, 0.0, 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (1.0, 0.75, 0.25, 1)
    mid = ramp.color_ramp.elements.new(0.45); mid.color = (1.0, 0.25, 0.02, 1)
    L(tongue.outputs['Result'], ramp.inputs['Fac'])
    strength = N('ShaderNodeMath'); strength.operation = 'MULTIPLY'; strength.inputs[1].default_value = 12.0
    L(tongue.outputs['Result'], strength.inputs[0])
    dens = N('ShaderNodeMath'); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 3.0
    L(tongue.outputs['Result'], dens.inputs[0])
    vol = N('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.08, 0.05, 0.03, 1)
    L(dens.outputs[0], vol.inputs['Density'])
    L(ramp.outputs['Color'], vol.inputs['Emission Color'])
    L(strength.outputs[0], vol.inputs['Emission Strength'])
    out = N('ShaderNodeOutputMaterial'); L(vol.outputs[0], out.inputs['Volume'])
    return mat


def smoke_material(name, seed=0.0, density=0.6):
    """Rising grey smoke: noise that climbs over time, thinning with height."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    off = nt.nodes.new('ShaderNodeVectorMath'); off.operation = 'ADD'
    _drive(off.inputs[1], 'default_value', '-frame * 0.012', index=2)
    nt.links.new(tc.outputs['Object'], off.inputs[0])
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 4.0
    _drive(noise.inputs['W'], 'default_value', f'frame / 40 + {seed}')
    nt.links.new(off.outputs[0], noise.inputs['Vector'])
    cut = nt.nodes.new('ShaderNodeMapRange')
    cut.inputs['From Min'].default_value = 0.45; cut.inputs['From Max'].default_value = 0.75
    cut.inputs['To Max'].default_value = density
    nt.links.new(noise.outputs['Fac'], cut.inputs['Value'])
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.12, 0.11, 0.1, 1)
    nt.links.new(cut.outputs['Result'], vol.inputs['Density'])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(vol.outputs[0], out.inputs['Volume'])
    return mat


def fire(name, loc, size, col, lit, energy=60.0, seed=0.0):
    """A fire: a volumetric flame (box, procedural shader), a smoke column above it, two flickering orange lights."""
    loc = Vector(loc)
    flame = box(name, (size * 0.9, size * 0.9, size * 1.8), loc + Vector((0, 0, size * 0.9)), fire_material(name + '_m', seed), col)
    flame.visible_shadow = False
    flame['cine_ignore'] = True
    smoke = box(name + '_smoke', (size * 1.3, size * 1.3, size * 2.0), loc + Vector((0, 0, size * 2.6)), smoke_material(name + '_sm', seed, 0.5),
                col)
    smoke.visible_shadow = False
    smoke['cine_ignore'] = True
    for k, (dz, e) in enumerate(((0.5, 1.0), (1.1, 0.55))):
        lamp = light(f'{name}_light{k}', 'POINT', loc + Vector((0, 0, size * dz)), energy * e, (1.0, 0.42, 0.1), lit, size=size * 0.35)
        _drive(lamp.data, 'energy', f'{energy * e} * (0.75 + 0.18 * sin(frame * 0.9 + {seed + k}) + 0.1 * sin(frame * 2.7 + {seed * 2 + k}))')
    return flame


def build_cafe():
    """Café FINE: a small diner where everything is quietly on fire. Warm orange light inside, the green Memetrix outside."""
    col = collection('CAFE')
    lit = collection('L_CAFE')
    o = ORIGIN['CAFE']
    tiles = bpy.data.materials.new('cafe_tiles')                   # black-and-white diner tiles
    tiles.use_nodes = True
    nt = tiles.node_tree
    chk = nt.nodes.new('ShaderNodeTexChecker')
    chk.inputs['Scale'].default_value = 24.0
    chk.inputs['Color1'].default_value = (0.85, 0.82, 0.76, 1)
    chk.inputs['Color2'].default_value = (0.06, 0.06, 0.07, 1)
    nt.links.new(chk.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.3
    plane('cafe_floor', 12, 10, o, tiles, col)
    wall_m = material('cafe_wall', (0.38, 0.24, 0.17), rough=0.85)
    mxsets.add_bump(wall_m, 30.0, 0.2)
    trim_m = material('cafe_trim', (0.6, 0.08, 0.06), rough=0.5)
    for name, size, off in (('cafe_back', (12, 0.3, 4.2), (0, 5, 2.1)), ('cafe_left', (0.3, 10, 4.2), (-6, 0, 2.1)),
                            ('cafe_right', (0.3, 10, 4.2), (6, 0, 2.1)), ('cafe_ceiling', (12, 10, 0.2), (0, 0, 4.25))):
        box(name, size, o + Vector(off), wall_m, col)
    box('cafe_stripe', (11.9, 0.05, 0.25), o + Vector((0, 4.83, 1.0)), trim_m, col)
    # the window in the back wall: a real opening onto the city at night (it was a code screen that rendered as black)
    back = bpy.data.objects['cafe_back']
    cutter = box('cafe_window_cut', (4.6, 1.0, 2.0), o + Vector((-2.2, 5.0, 2.2)), wall_m, col)
    cutter.hide_render = True
    cutter.hide_viewport = True
    cut = back.modifiers.new('window', 'BOOLEAN')
    cut.operation = 'DIFFERENCE'
    cut.object = cutter
    glass = material('cafe_glass', (0.8, 0.9, 0.85), rough=0.02)
    glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 1.0
    pane = plane('cafe_window_glass', 4.6, 2.0, o + Vector((-2.2, 4.95, 2.2)), glass, col, rot=(math.radians(90), 0, 0))
    pane.visible_shadow = False
    pane['cine_ignore'] = True
    # outside: the sidewalk, the street, and the other side of it: shops with lit signs, towers rising behind them
    rnd_c = random.Random(21)
    box('street_sidewalk', (40, 4, 0.15), o + Vector((0, 7.2, 0.07)), material('sidewalk', (0.18, 0.18, 0.19), rough=0.7), col)
    wet = material('street_asphalt', (0.03, 0.035, 0.035), rough=0.18)
    plane('street_road', 60, 12, o + Vector((0, 15.2, 0.0)), wet, col)
    for k in range(9):                                            # lane marks
        box(f'lane{k}', (1.6, 0.12, 0.01), o + Vector((-16 + k * 4.2, 15.2, 0.01)), material('lane', (0.9, 0.8, 0.3), rough=0.5), col)
    for k in range(10):                                           # the far side: towers, each a lit window grid
        w, d, h = rnd_c.uniform(5, 9), rnd_c.uniform(6, 10), rnd_c.uniform(14, 48)
        x = -24 + k * 5.6 + rnd_c.uniform(-0.8, 0.8)
        box(f'cafe_city{k}', (w, d, h), o + Vector((x, 25 + d / 2 + rnd_c.uniform(0, 8), h / 2)),
            mxsets.window_material(f'cafe_win{k}', 40 + k, (w, d, h)), col)
    for k, (x, txt, colour) in enumerate(((-6.5, 'PAWN', (1.0, 0.2, 0.15)), (-1.8, 'HODL 24H', (0.2, 1.0, 0.35)),
                                          (3.4, 'NOODLES', (1.0, 0.55, 0.1)))):
        bpy.ops.object.text_add(location=o + Vector((x, 23.4, 3.6)), rotation=(math.radians(90), 0, 0))   # reads from the café
        sign = bpy.context.active_object
        sign.name = f'neon_sign{k}'
        sign.data.body = txt
        sign.data.size = 1.0
        sign.data.align_x = 'CENTER'
        sign.data.materials.append(material(f'neon{k}', colour, emit=colour, strength=3.0))   # (8 washed out to white)
        for c_ in list(sign.users_collection):
            c_.objects.unlink(sign)
        col.objects.link(sign)
        nl = light(f'L_neon{k}', 'AREA', o + Vector((x, 22.6, 3.4)), 300, colour, lit, size=2.0, rot=(math.radians(-90), 0, 0))
        nl.visible_camera = False                                  # (seen through the window it was a white square)
    pole_m = material('street_pole', (0.08, 0.08, 0.09), rough=0.4, metal=0.6)
    lamp_m = material('street_lamp', (1.0, 0.8, 0.5), emit=(1.0, 0.78, 0.45), strength=12.0)
    for k, x in enumerate((-9.0, -1.0, 7.0)):                     # street lamps on the near sidewalk
        cylinder(f'street_pole{k}', 0.07, 5.0, o + Vector((x, 8.4, 2.5)), pole_m, col, verts=10)
        sphere(f'street_bulb{k}', 0.22, o + Vector((x, 8.4, 5.1)), lamp_m, col)
        light(f'L_street{k}', 'POINT', o + Vector((x, 8.4, 4.9)), 900, (1.0, 0.75, 0.45), lit, size=0.3).visible_camera = False
    sky = material('cafe_sky', (0.0, 0.0, 0.0), emit=(0.02, 0.05, 0.045), strength=1.0)
    plane('cafe_sky', 140, 70, o + Vector((0, 60, 30)), sky, col, rot=(math.radians(90), 0, 0))
    frame_m = material('cafe_window_frame', (0.15, 0.1, 0.08), rough=0.4)
    for name, size, off in (('win_top', (4.8, 0.12, 0.12), (-2.2, 4.8, 3.25)), ('win_bot', (4.8, 0.12, 0.12), (-2.2, 4.8, 1.15)),
                            ('win_mid', (0.08, 0.12, 2.1), (-2.2, 4.8, 2.2)), ('win_l', (0.12, 0.12, 2.2), (-4.6, 4.8, 2.2)),
                            ('win_r', (0.12, 0.12, 2.2), (0.2, 4.8, 2.2))):
        box(name, size, o + Vector(off), frame_m, col)
    # the counter, stools, booths and tables
    counter_m = material('cafe_counter', (0.75, 0.72, 0.66), rough=0.25, metal=0.1)
    chrome = material('cafe_chrome', (0.8, 0.8, 0.82), rough=0.15, metal=1.0)
    box('counter', (5.0, 0.8, 1.05), o + Vector((2.6, 2.6, 0.52)), material('cafe_counter_front', (0.55, 0.07, 0.06), rough=0.45), col)
    box('counter_top', (5.2, 0.95, 0.06), o + Vector((2.6, 2.6, 1.08)), counter_m, col, bevel=0.01)
    seat_m = material('cafe_seat', (0.7, 0.06, 0.05), rough=0.4)
    for k in range(5):
        x = 0.6 + k * 1.0
        cylinder(f'stool_post{k}', 0.04, 0.72, o + Vector((x, 1.75, 0.36)), chrome, col, verts=12)
        cylinder(f'stool_seat{k}', 0.2, 0.09, o + Vector((x, 1.75, 0.76)), seat_m, col, verts=20)
    for k, (x, y) in enumerate(((-3.6, 0.6), (-3.6, -2.2), (-0.8, -2.6))):
        cylinder(f'table_top{k}', 0.55, 0.05, o + Vector((x, y, 0.78)), counter_m, col, verts=28)
        cylinder(f'table_leg{k}', 0.05, 0.75, o + Vector((x, y, 0.38)), chrome, col, verts=10)
        for s in (-1, 1):
            box(f'booth{k}_{s}', (1.2, 0.5, 0.48), o + Vector((x, y + s * 0.85, 0.24)), seat_m, col, bevel=0.05)
            box(f'booth_back{k}_{s}', (1.2, 0.15, 0.7), o + Vector((x, y + s * 1.05, 0.7)), seat_m, col, bevel=0.04)
        cylinder(f'mug{k}', 0.045, 0.1, o + Vector((x + 0.2, y + 0.1, 0.86)), material('mug', (0.92, 0.9, 0.85), rough=0.3), col, verts=14)
    # the menu board over the counter and a coffee machine
    board_m = material('menu_board', (0.05, 0.06, 0.05), rough=0.8)
    box('menu_board', (3.2, 0.06, 1.0), o + Vector((2.6, 4.82, 3.0)), board_m, col)
    for k, txt in enumerate(('COFFEE ......... FINE', 'PIE ........... FINE', 'EXIT .............. ?')):
        bpy.ops.object.text_add(location=o + Vector((1.2, 4.78, 3.25 - k * 0.27)), rotation=(math.radians(90), 0, 0))
        t = bpy.context.active_object
        t.name = f'menu_text{k}'
        t.data.body = txt
        t.data.size = 0.17
        t.data.materials.append(material('chalk', (0.95, 0.95, 0.9), emit=(0.9, 0.9, 0.85), strength=0.4))
        for c in list(t.users_collection):
            c.objects.unlink(t)
        col.objects.link(t)
    box('coffee_machine', (0.6, 0.5, 0.7), o + Vector((4.4, 3.3, 1.45)), chrome, col, bevel=0.03)
    # pendant lamps (warm), and the fires: on tables, the counter, the menu board, the floor in a corner
    for k, x in enumerate((-3.6, -0.8, 2.0, 4.0)):
        cylinder(f'pendant_cord{k}', 0.008, 1.2, o + Vector((x, 1.0 if k > 1 else -0.8, 3.6)), board_m, col, verts=6)
        cone = cylinder(f'pendant{k}', 0.22, 0.18, o + Vector((x, 1.0 if k > 1 else -0.8, 2.95)), trim_m, col, verts=20)
        light(f'L_pendant{k}', 'POINT', o + Vector((x, 1.0 if k > 1 else -0.8, 2.8)), 12, (1.0, 0.75, 0.45), lit, size=0.15)
    rnd = random.Random(5)
    spots = [((-3.6, 0.6, 0.81), 0.8), ((-0.8, -2.6, 0.81), 0.65), ((1.4, 2.6, 1.11), 0.75), ((3.6, 2.6, 1.11), 0.9),
             ((3.6, 4.6, 2.5), 1.0), ((-5.4, 4.2, 0.0), 1.8), ((5.3, -3.8, 0.0), 2.0), ((-3.6, -2.2, 0.81), 0.6),
             ((5.6, 3.0, 0.0), 1.6), ((-5.6, -3.5, 0.0), 1.5), ((0.4, 4.6, 0.0), 1.3), ((-1.0, 4.6, 3.0), 0.9)]
    for k, (p, s) in enumerate(spots):
        fire(f'fire{k}', o + Vector(p), s * 1.25, col, lit, energy=25 + 50 * s, seed=rnd.uniform(0, 20))   # (darker room: the fire is the light)
    # flames climbing the walls (wide, flat fire boxes against them) and a burning curtain by the window
    for k, (p, sz) in enumerate((((-5.75, 2.0, 0.0), (0.4, 2.2, 3.0)), ((5.75, -1.5, 0.0), (0.4, 2.6, 3.2)),
                                 ((1.6, 4.75, 0.0), (2.4, 0.4, 2.6)), ((-4.9, 4.7, 1.1), (0.7, 0.35, 2.6)))):
        wf = box(f'wallfire{k}', sz, o + Vector(p) + Vector((0, 0, sz[2] / 2)), fire_material(f'wallfire_m{k}', 30 + k * 5), col)
        wf.visible_shadow = False
        wf['cine_ignore'] = True
        wl = light(f'L_wallfire{k}', 'AREA', o + Vector(p) + Vector((0, 0, sz[2] * 0.4)), 150, (1.0, 0.4, 0.08), lit, size=1.5)
        _drive(wl.data, 'energy', f'150 * (0.75 + 0.2 * sin(frame * 0.8 + {k * 3}) + 0.1 * sin(frame * 2.3 + {k}))')
    smoke_layer = box('cafe_smoke_layer', (11.6, 9.6, 1.1), o + Vector((0, 0, 3.6)), smoke_material('cafe_smoke_layer_m', 7, 1.4), col)
    smoke_layer.visible_shadow = False
    smoke_layer['cine_ignore'] = True
    soot = material('soot', (0.02, 0.018, 0.016), rough=0.95)
    for k, (p, rot, sz) in enumerate((((-5.83, 2.0, 2.6), (math.radians(90), 0, math.radians(90)), (3.0, 3.0)),
                                      ((5.83, -1.5, 2.6), (math.radians(90), 0, math.radians(-90)), (3.4, 3.2)),
                                      ((1.6, 4.84, 2.4), (math.radians(90), 0, math.radians(180)), (3.0, 2.6)))):
        sm_ = plane(f'scorch{k}', sz[0], sz[1], o + Vector(p), soot, col, rot=rot)       # blackened wall above each wall fire
        sm_.visible_shadow = False
    light('cafe_key', 'AREA', o + Vector((0, -3, 3.9)), 20, (1.0, 0.7, 0.45), lit, size=3.0, rot=(math.radians(20), 0, 0))
    light('cafe_window_light', 'AREA', o + Vector((-2.2, 4.4, 2.2)), 120, (0.4, 1.0, 0.55), lit, size=2.0,
          rot=(math.radians(-90), 0, 0))
    haze('haze_cafe', o + Vector((0, 0, 2.1)), (11.5, 9.5, 4.1), 0.012, (1.0, 0.7, 0.5), col)
    for l_ in lit.objects:                                         # lights light the set but never show as glowing quads
        if l_.type == 'LIGHT':
            l_.visible_camera = l_.visible_transmission = l_.visible_glossy = False   # (seen through the glass too)
    dust('embers_cafe', o + Vector((0, 0.5, 2.0)), (10, 8, 3.5), 350, (1.0, 0.5, 0.15), col, 9)
    return col


def build_white_room(stills=None):
    """The Whale's white room: no corners, a soft white light everywhere, a wall of old monitors showing other Anons."""
    col = collection('WHITE')
    lit = collection('L_WHITE')
    o = ORIGIN['WHITE']
    white = material('white_room', (0.92, 0.92, 0.93), rough=0.55)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=14, segments=48, ring_count=24, location=o + Vector((0, 0, 0)))
    dome = bpy.context.active_object
    dome.name = 'white_cyc'
    dome.scale = (1, 1, 0.6)
    for c in list(dome.users_collection):
        c.objects.unlink(dome)
    col.objects.link(dome)
    dome.data.materials.append(material('white_cyc', (0.95, 0.95, 0.96), rough=0.9, emit=(0.95, 0.96, 1.0), strength=0.55))
    for poly in dome.data.polygons:
        poly.use_smooth = True
    plane('white_floor', 30, 30, o + Vector((0, 0, 0.0)), material('white_floor', (0.95, 0.95, 0.96), rough=0.12), col)
    # the monitor wall: 8 x 6 old monitors, each showing a still of an Anon from episode 1
    case_m = material('monitor_case', (0.82, 0.8, 0.76), rough=0.5)
    stills = stills or []
    rnd = random.Random(11)
    k = 0
    for r in range(6):
        for c in range(8):
            x, z = -4.9 + c * 1.4, 0.55 + r * 1.0
            box(f'monitor{r}_{c}', (1.3, 0.8, 0.92), o + Vector((x, 7.2, z)), case_m, col, bevel=0.04)
            if stills:
                img = stills[k % len(stills)]
                k += 1
                scr_m = mxsets.image_material(f'monitor_img{r}_{c}', img, emit=1.4)
            else:
                scr_m = material(f'monitor_img{r}_{c}', (0.2, 0.3, 0.25), emit=(0.2, 0.5, 0.3), strength=1.0)
            s = plane(f'monitor_screen{r}_{c}', 1.08, 0.72, o + Vector((x, 6.79, z)), scr_m, col, rot=(math.radians(90), 0, 0))
            s.visible_shadow = False
            s['monitor'] = True
    # the two doors are made of falling code: SELL a doorway of red code, HOLD a doorway of green code, each word in its colour
    for name, x, word, tint in (('door_sell', -2.4, 'SELL', (1.0, 0.12, 0.08)), ('door_hold', 2.4, 'HOLD', (0.15, 1.0, 0.3))):
        d = screen(name, 1.25, 2.3, o + Vector((x, 3.0, 1.15)), (math.radians(90), 0, 0), col, 5.0, tint)
        nt = d.data.materials[0].node_tree                          # colour the code by its brightness (the rain frames are green:
        bw = nt.nodes.new('ShaderNodeRGBToBW')                      # tinting them red left almost nothing) over a faint glow
        nt.links.new(nt.nodes['rain'].outputs['Color'], bw.inputs[0])
        mix = next(n for n in nt.nodes if n.type == 'MIX_RGB')
        boost = nt.nodes.new('ShaderNodeMath')
        boost.operation = 'MULTIPLY_ADD'
        boost.inputs[1].default_value = 4.0
        boost.inputs[2].default_value = 0.025
        nt.links.new(bw.outputs[0], boost.inputs[0])
        nt.links.new(boost.outputs[0], mix.inputs[1])
        light(name + '_glow', 'AREA', o + Vector((x, 2.7, 1.2)), 140, tint, lit, size=1.2, rot=(math.radians(90), 0, 0))
        bpy.ops.object.text_add(location=o + Vector((x, 2.98, 2.55)), rotation=(math.radians(90), 0, 0))
        t = bpy.context.active_object
        t.name = name + '_word'
        t.data.body = word
        t.data.size = 0.5
        t.data.align_x = 'CENTER'
        t.data.extrude = 0.02
        t.data.materials.append(material(name + '_word_m', tint, emit=tint, strength=1.2))   # (brighter washed out to pastel)
        for c_ in list(t.users_collection):
            c_.objects.unlink(t)
        col.objects.link(t)
    light('white_key', 'AREA', o + Vector((0, -4, 7)), 900, (1, 1, 1), lit, size=8.0, rot=(math.radians(25), 0, 0))
    light('white_fill', 'AREA', o + Vector((0, 3, 6)), 400, (0.95, 0.97, 1.0), lit, size=10.0)
    haze('haze_white', o + Vector((0, 1, 3)), (16, 14, 6), 0.003, (1, 1, 1), col)
    return col


def episode1_stills(frames_dir, count=24):
    """Frames of Anon from episode 1 for the monitor wall (every Nth frame of the shots he is in)."""
    packed = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack', 'stills', 'f_*.jpg')))
    if len(packed) >= count:                                    # committed copies (episode 1's frames are not in git)
        return packed[:count]
    files = sorted(glob.glob(os.path.join(frames_dir, 'f_*.jpg')))
    return files[::max(1, len(files) // count)][:count]


def exhaust_material(name, col=(0.05, 1.0, 0.2), strength=5.0):
    """Rocket exhaust on a cone (local z -1..0, nozzle at the top): emission fading from the nozzle down, with a flickering
    noise core, mixed into transparency so the end of the flare dissolves instead of stopping in a hard edge."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    fade = nt.nodes.new('ShaderNodeMath')                           # 1 at the nozzle, 0 at the tail
    fade.operation = 'POWER'
    nt.links.new(sep.outputs['Z'], fade.inputs[0])
    fade.inputs[1].default_value = 4.0
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 6.0
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    _drive(noise.inputs['W'], 'default_value', 'frame / 3')
    flick = nt.nodes.new('ShaderNodeMapRange')
    flick.inputs['To Min'].default_value = 0.55
    flick.inputs['To Max'].default_value = 1.2
    nt.links.new(noise.outputs['Fac'], flick.inputs['Value'])
    fac = nt.nodes.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    fac.use_clamp = True
    nt.links.new(fade.outputs['Value'], fac.inputs[0])
    nt.links.new(flick.outputs['Result'], fac.inputs[1])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*col, 1.0)
    em.inputs['Strength'].default_value = strength
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fac.outputs['Value'], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def night_sky(mat):
    """The rooftop dome: city glow low on the horizon (warm-green) fading to a dark zenith, with soft clouds catching it.
    Replaces the flat near-black emission (the flight looks up into it for two seconds)."""
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    h = nt.nodes.new('ShaderNodeMapRange')                          # height on the dome: 0 at the horizon, 1 high up
    h.inputs['From Min'].default_value = -40.0
    h.inputs['From Max'].default_value = 700.0
    nt.links.new(sep.outputs['Z'], h.inputs['Value'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.11, 0.12, 0.07, 1)       # sodium-and-neon city glow
    els[1].position, els[1].color = 1.0, (0.012, 0.03, 0.024, 1)  # overhead: clouds still catch the city
    mid = els.new(0.3)
    mid.color = (0.04, 0.08, 0.06, 1)
    nt.links.new(h.outputs['Result'], ramp.inputs['Fac'])
    noise = nt.nodes.new('ShaderNodeTexNoise')                      # clouds
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 0.006
    noise.inputs['Detail'].default_value = 6.0
    noise.inputs['Roughness'].default_value = 0.6
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    _drive(noise.inputs['W'], 'default_value', 'frame / 900')
    cl = nt.nodes.new('ShaderNodeMapRange')
    cl.inputs['From Min'].default_value = 0.45
    cl.inputs['From Max'].default_value = 0.75
    cl.inputs['To Min'].default_value = 0.6
    cl.inputs['To Max'].default_value = 2.8
    nt.links.new(noise.outputs['Fac'], cl.inputs['Value'])
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(cl.outputs['Result'], em.inputs['Strength'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])


def wet_floor(mat, seed=0.0):
    """Rain on a flat roof: puddles (mirror-smooth, a shade darker) between wet gravel, the puddles shimmering with drops.
    World-position noise picks the puddles; animated 4D Voronoi bumps their normal (the drops), gravel stays matte-wet."""
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    if bsdf is None:
        return
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 0.35
    noise.inputs['Detail'].default_value = 3.0
    nt.links.new(geo.outputs['Position'], noise.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')                       # 1 = puddle, 0 = wet gravel
    ramp.color_ramp.elements[0].position = 0.46
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.52
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    rough = nt.nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = 0.42
    rough.inputs['To Max'].default_value = 0.03
    nt.links.new(ramp.outputs['Color'], rough.inputs['Value'])
    nt.links.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
    base = tuple(bsdf.inputs['Base Color'].default_value)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = base
    mix.inputs['B'].default_value = (base[0] * 0.55, base[1] * 0.55, base[2] * 0.55, 1.0)
    nt.links.new(ramp.outputs['Color'], mix.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    vor = nt.nodes.new('ShaderNodeTexVoronoi')                       # the drops: cells that re-form every few frames
    vor.voronoi_dimensions = '4D'
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 9.0
    nt.links.new(geo.outputs['Position'], vor.inputs['Vector'])
    _drive(vor.inputs['W'], 'default_value', f'frame / 5 + {seed}')
    amt = nt.nodes.new('ShaderNodeMath')
    amt.operation = 'MULTIPLY'
    nt.links.new(ramp.outputs['Color'], amt.inputs[0])
    amt.inputs[1].default_value = 0.25
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = 0.004
    nt.links.new(amt.outputs['Value'], bump.inputs['Strength'])
    nt.links.new(vor.outputs['Distance'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def rooftop_rain(col, centre, size=(30, 30), drops=2500, seed=3):
    """Falling rain: thin streaks vertex-instanced over a cloud that drops and wraps (driver on the cloud's z)."""
    rnd = random.Random(seed)
    mesh = bpy.data.meshes.new('rain_cloud')
    # the cloud falls 6 m and snaps back up. Every drop in the bottom 6 m has a twin 6 m above it, so the snap is invisible,
    # and the snap lands half-way between frames (frame + 0.5 on an 11-frame cycle), outside any motion-blur shutter
    half = [(rnd.uniform(-size[0] / 2, size[0] / 2), rnd.uniform(-size[1] / 2, size[1] / 2), rnd.uniform(0, 6)) for _ in range(drops // 2)]
    pts = half + [(x, y, z + 6) for x, y, z in half]
    mesh.from_pydata(pts, [], [])
    cloud = bpy.data.objects.new('rain_cloud', mesh)
    col.objects.link(cloud)
    cloud.location = centre
    _drive(cloud, 'location', f'{centre.z} - ((frame + 0.5) % 11) * {6 / 11}', index=2)
    streak_m = material('rain_streak', (0.75, 0.9, 0.85), rough=0.1, emit=(0.6, 0.85, 0.75), strength=0.45)
    streak_m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.4   # see-through: a drop beside the lens
    streak_m.blend_method = 'BLEND'                                                   # is a faint smear, not a white bar
    streak = cylinder('rain_streak', 0.0028, 0.35, (0, 0, 0), streak_m, col, verts=4)
    streak.parent = cloud
    streak.visible_shadow = False
    cloud.instance_type = 'VERTS'
    cloud['cine_ignore'] = True
    streak['cine_ignore'] = True
    for ob in (cloud, streak):                                # slow-motion shots sample fractional frames, so the snap can
        try:                                                  # still fall inside a shutter: the streaks are drawn long
            ob.cycles.use_motion_blur = False                 # already, so the rain carries no object blur at all
        except AttributeError:
            pass
    return cloud
