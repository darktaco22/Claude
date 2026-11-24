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


def fire(name, loc, size, col, lit, energy=60.0, seed=0.0):
    """A fire: three crossed flame cards, a flickering orange point light and a little smoke."""
    holder = bpy.data.objects.new(name, None)
    col.objects.link(holder)
    holder.location = loc
    for k in range(3):
        card = plane(f'{name}_card{k}', size * 0.9, size * 1.6, (0, 0, size * 0.8), flame_material(f'{name}_m{k}', seed + k * 3.1),
                     col, parent=holder, rot=(math.radians(90), 0, math.radians(60 * k)))
        card.visible_shadow = False
        card['cine_ignore'] = True
    lamp = light(name + '_light', 'POINT', Vector(loc) + Vector((0, 0, size * 0.7)), energy, (1.0, 0.45, 0.12), lit, size=size * 0.4)
    _drive(lamp.data, 'energy', f'{energy} * (0.8 + 0.15 * sin(frame * 0.9 + {seed}) + 0.08 * sin(frame * 2.3 + {seed * 2}))')
    return holder


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
    wall_m = material('cafe_wall', (0.55, 0.38, 0.28), rough=0.85)
    mxsets.add_bump(wall_m, 30.0, 0.2)
    trim_m = material('cafe_trim', (0.6, 0.08, 0.06), rough=0.5)
    for name, size, off in (('cafe_back', (12, 0.3, 4.2), (0, 5, 2.1)), ('cafe_left', (0.3, 10, 4.2), (-6, 0, 2.1)),
                            ('cafe_right', (0.3, 10, 4.2), (6, 0, 2.1)), ('cafe_ceiling', (12, 10, 0.2), (0, 0, 4.25))):
        box(name, size, o + Vector(off), wall_m, col)
    box('cafe_stripe', (11.9, 0.05, 0.25), o + Vector((0, 4.83, 1.0)), trim_m, col)
    # the window in the back wall: the Memetrix outside (green code rain), a frame and mullions
    screen('cafe_window_view', 4.6, 2.0, o + Vector((-2.2, 4.84, 2.2)), (math.radians(90), 0, math.radians(180)), col, 1.6, (0.6, 1.0, 0.7))
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
        light(f'L_pendant{k}', 'POINT', o + Vector((x, 1.0 if k > 1 else -0.8, 2.8)), 45, (1.0, 0.75, 0.45), lit, size=0.15)
    rnd = random.Random(5)
    spots = [((-3.6, 0.6, 0.81), 0.8), ((-0.8, -2.6, 0.81), 0.65), ((1.4, 2.6, 1.11), 0.75), ((3.6, 2.6, 1.11), 0.9),
             ((3.6, 4.6, 2.5), 1.0), ((-5.4, 4.2, 0.0), 1.8), ((5.3, -3.8, 0.0), 2.0), ((-3.6, -2.2, 0.81), 0.6),
             ((5.6, 3.0, 0.0), 1.6), ((-5.6, -3.5, 0.0), 1.5), ((0.4, 4.6, 0.0), 1.3), ((-1.0, 4.6, 3.0), 0.9)]
    for k, (p, s) in enumerate(spots):
        fire(f'fire{k}', o + Vector(p), s, col, lit, energy=35 + 70 * s, seed=rnd.uniform(0, 20))
    light('cafe_key', 'AREA', o + Vector((0, -3, 3.9)), 90, (1.0, 0.7, 0.45), lit, size=3.0, rot=(math.radians(20), 0, 0))
    light('cafe_window_light', 'AREA', o + Vector((-2.2, 4.4, 2.2)), 120, (0.4, 1.0, 0.55), lit, size=2.0,
          rot=(math.radians(-90), 0, 0))
    haze('haze_cafe', o + Vector((0, 0, 2.1)), (11.5, 9.5, 4.1), 0.012, (1.0, 0.75, 0.55), col)
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
    # the two doors (outlined in light) and their words, closed until the Whale opens them
    edge = material('door_edge', (1, 1, 1), emit=(1.0, 0.98, 0.92), strength=9.0)
    for name, x, word in (('door_sell', -2.4, 'SELL'), ('door_hold', 2.4, 'HOLD')):
        for part, size, off in (('l', (0.05, 0.05, 2.3), (-0.6, 0, 1.15)), ('r', (0.05, 0.05, 2.3), (0.6, 0, 1.15)),
                                ('t', (1.25, 0.05, 0.05), (0, 0, 2.3))):
            box(f'{name}_{part}', size, o + Vector((x, 3.0, 0)) + Vector(off), edge, col)
        bpy.ops.object.text_add(location=o + Vector((x, 2.98, 2.55)), rotation=(math.radians(90), 0, 0))
        t = bpy.context.active_object
        t.name = name + '_word'
        t.data.body = word
        t.data.size = 0.5
        t.data.align_x = 'CENTER'
        t.data.extrude = 0.02
        t.data.materials.append(material(name + '_word_m', (0.02, 0.02, 0.02), rough=0.3))
        for c_ in list(t.users_collection):
            c_.objects.unlink(t)
        col.objects.link(t)
    light('white_key', 'AREA', o + Vector((0, -4, 7)), 900, (1, 1, 1), lit, size=8.0, rot=(math.radians(25), 0, 0))
    light('white_fill', 'AREA', o + Vector((0, 3, 6)), 400, (0.95, 0.97, 1.0), lit, size=10.0)
    haze('haze_white', o + Vector((0, 1, 3)), (16, 14, 6), 0.003, (1, 1, 1), col)
    return col


def episode1_stills(frames_dir, count=24):
    """Frames of Anon from episode 1 for the monitor wall (every Nth frame of the shots he is in)."""
    files = sorted(glob.glob(os.path.join(frames_dir, 'f_*.jpg')))
    return files[::max(1, len(files) // count)][:count]


def rooftop_rain(col, centre, size=(30, 30), drops=2500, seed=3):
    """Falling rain: thin streaks vertex-instanced over a cloud that drops and wraps (driver on the cloud's z)."""
    rnd = random.Random(seed)
    mesh = bpy.data.meshes.new('rain_cloud')
    pts = [(rnd.uniform(-size[0] / 2, size[0] / 2), rnd.uniform(-size[1] / 2, size[1] / 2), rnd.uniform(0, 12)) for _ in range(drops)]
    mesh.from_pydata(pts, [], [])
    cloud = bpy.data.objects.new('rain_cloud', mesh)
    col.objects.link(cloud)
    cloud.location = centre
    _drive(cloud, 'location', f'{centre.z} - (frame * 0.55) % 6', index=2)
    streak_m = material('rain_streak', (0.75, 0.9, 0.85), rough=0.1, emit=(0.6, 0.85, 0.75), strength=0.6)
    streak = cylinder('rain_streak', 0.004, 0.35, (0, 0, 0), streak_m, col, verts=4)
    streak.parent = cloud
    streak.visible_shadow = False
    cloud.instance_type = 'VERTS'
    cloud['cine_ignore'] = True
    streak['cine_ignore'] = True
    return cloud
