"""Sets and props for THE MEMETRIX, built from code and the game's own arena kits (pack/arenas/<id>/props/*.glb).

Three sets far apart in one scene (the camera never sees two at once):
    FLOOR     (0, 0)     The Trading Floor at night, inside the Memetrix: desks, chart boards, the bull, walls of green code.
    BASEMENT  (200, 0)   Mom's Basement, the real world: gaming chair, CRT console, laundry, pizza, washer, bare bulbs.
    DOJO      (400, 0)   The Metaverse training program: pink grid floor, arches, columns, visor busts, palms.
    ROOFTOP   (2000, 0)  A skyscraper roof at night inside the Memetrix, built from code (no arena props): the bullet-time dodge.
Each set's lights live in its own collection; the renderer switches them with the shot (lights of other sets cost time).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'deployed'))
from sets import (add_bump, box, collection, cylinder, duplicate, image_material, import_glb, light, material, plane, sphere,  # noqa: E402
                  textured_plane)

PACK = os.path.join(HERE, 'pack')
ORIGIN = {'FLOOR': Vector((0, 0, 0)), 'BASEMENT': Vector((200, 0, 0)), 'DOJO': Vector((400, 0, 0)), 'ROOFTOP': Vector((2000, 0, 0))}
_CACHE = {}


def prop(arena, name, col, loc, rot_deg=0.0, scale=1.0):
    """Place a copy of an arena prop (loaded once, kept hidden) standing on the floor at loc."""
    key = (arena, name)
    if key not in _CACHE:
        src = collection('SRC')
        src.hide_render = True
        src.hide_viewport = True
        _CACHE[key] = import_glb(os.path.join(PACK, 'arenas', arena, 'props', name + '.glb'), src)
    holder = bpy.data.objects.new(f'{arena}_{name}', None)
    col.objects.link(holder)
    for copy in duplicate(_CACHE[key], col):
        copy.parent = holder
    holder.location = Vector(loc)
    holder.rotation_euler = (0, 0, math.radians(rot_deg))
    holder.scale = (scale, scale, scale)
    return holder


def rain_material(name, strength=2.2, tint=(1, 1, 1)):
    """Emissive screen showing the looping code rain (pack/rain/r_0001.png ...). The renderer sets the frame."""
    path = os.path.join(PACK, 'rain', 'r_0001.png')
    img = bpy.data.images.load(path, check_existing=True)
    img.source = 'SEQUENCE'
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.name = 'rain'
    tex.image = img
    tex.image_user.frame_duration = 48
    tex.image_user.use_cyclic = True
    tex.image_user.use_auto_refresh = True
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    mix.inputs[2].default_value = (*tint, 1)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tex.outputs['Color'], mix.inputs[1])
    nt.links.new(mix.outputs[0], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return mat


def screen(name, w, h, loc, rot, col, strength=2.2, tint=(1, 1, 1)):
    obj = plane(name, w, h, loc, rain_material(name + '_m', strength, tint), col, rot=rot)
    obj.visible_shadow = False
    return obj


def _ground(name, arena, size, centre, col, repeat, tint, rough=0.35):
    obj, _ = textured_plane(name, size, size, centre, os.path.join(PACK, 'arenas', arena, 'ground.webp'), col,
                            repeat=(repeat, repeat), tint=tint)
    bsdf = obj.data.materials[0].node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Roughness'].default_value = rough
    return obj


# ---------------------------------------------------------------- the trading floor (inside the Memetrix)
def build_floor():
    col = collection('FLOOR')
    lit = collection('L_FLOOR')
    o = ORIGIN['FLOOR']
    _ground('floor_ground', 'exchange', 60, o, col, 14, (0.35, 0.42, 0.36), rough=0.18)
    wall = material('floor_wall', (0.02, 0.035, 0.03), rough=0.7)
    box('floor_back', (40, 0.4, 9), o + Vector((0, 16, 4.5)), wall, col)
    box('floor_left', (0.4, 34, 9), o + Vector((-14, 0, 4.5)), wall, col)
    box('floor_right', (0.4, 34, 9), o + Vector((14, 0, 4.5)), wall, col)
    box('floor_front', (40, 0.4, 9), o + Vector((0, -14, 4.5)), wall, col)
    box('floor_ceiling', (40, 34, 0.4), o + Vector((0, 1, 9.2)), wall, col)
    # walls of code: the back wall, both sides; a strip of code on the ceiling
    screen('rain_back', 22, 7, o + Vector((0, 15.7, 4.4)), (math.pi / 2, 0, math.pi), col, 2.4)
    screen('rain_left', 24, 7, o + Vector((-13.7, 1, 4.4)), (math.pi / 2, 0, -math.pi / 2), col, 1.6)
    screen('rain_right', 24, 7, o + Vector((13.7, 1, 4.4)), (math.pi / 2, 0, math.pi / 2), col, 1.6)
    screen('rain_front', 22, 7, o + Vector((0, -13.7, 4.4)), (math.pi / 2, 0, 0), col, 1.4)
    # desks in rows, each with its own small rain monitor (Anon's desk is the front centre one)
    for i, x in enumerate((-7.5, -2.5, 2.5, 7.5)):
        for j, y in enumerate((-5.5, 0.0, 5.0)):
            if (x, y) in ((-2.5, 5.0), (2.5, 5.0)):
                continue                                                    # leave the aisle to the bull clear
            prop('exchange', 'ex_desk', col, o + Vector((x, y, 0)), 180, 0.75)
    prop('exchange', 'ex_bull', col, o + Vector((0, 11.0, 0)), 180, 0.9)
    prop('exchange', 'ex_bear', col, o + Vector((9.5, 11.5, 0)), 200, 0.8)
    prop('exchange', 'ex_bell', col, o + Vector((-9.5, 11.5, 0)), 160, 0.9)
    for x, y in ((-12, 13.5), (12, 13.5), (-12, -11), (12, -11)):
        prop('exchange', 'ex_ticker', col, o + Vector((x, y, 0)), 0, 1.0)
    for x, y in ((-5, 9.5), (5, 9.5)):
        prop('exchange', 'ex_board', col, o + Vector((x, y, 0)), 180, 0.9)
    for x, y in ((-11.5, 5), (11.5, -3)):
        prop('exchange', 'ex_plant', col, o + Vector((x, y, 0)), 0, 0.9)
    prop('exchange', 'ex_papers', col, o + Vector((4.5, -2.6, 0)), 30, 0.7)
    prop('exchange', 'ex_papers', col, o + Vector((-6, 2.8, 0)), -60, 0.7)
    # Anon's own monitor: a big rain screen on his desk, facing him (he stands south of it)
    screen('rain_anon', 1.3, 0.75, o + Vector((0, -0.95, 1.55)), (math.radians(80), 0, 0), col, 2.8)
    # lights: green from the code, a cold top light, a soft key that follows the story beats
    light('floor_top', 'AREA', o + Vector((0, 2, 8.6)), 900, (0.75, 1.0, 0.8), lit, size=10)
    light('floor_glow_back', 'AREA', o + Vector((0, 13.5, 3.5)), 1600, (0.25, 1.0, 0.35), lit, size=12, rot=(math.radians(-90), 0, 0))
    light('floor_glow_anon', 'AREA', o + Vector((0, 0.1, 1.9)), 60, (0.35, 1.0, 0.45), lit, size=1.2, rot=(math.radians(-80), 0, 0))
    light('floor_bull', 'SPOT', o + Vector((0, 6, 7.5)), 2500, (0.85, 1.0, 0.8), lit, rot=(math.radians(-35), 0, 0), spot=math.radians(35))
    return col


# ---------------------------------------------------------------- Mom's basement (the real world)
def build_basement():
    col = collection('BASEMENT')
    lit = collection('L_BASEMENT')
    o = ORIGIN['BASEMENT']
    _ground('base_ground', 'basement', 40, o, col, 8, (0.8, 0.75, 0.65), rough=0.8)
    concrete = material('base_wall', (0.30, 0.28, 0.25), rough=0.95)
    for name, size, off in (('base_back', (24, 0.4, 5), (0, 9, 2.5)), ('base_left', (0.4, 20, 5), (-10, 0, 2.5)),
                            ('base_right', (0.4, 20, 5), (10, 0, 2.5)), ('base_front', (24, 0.4, 5), (0, -9, 2.5)),
                            ('base_ceiling', (24, 20, 0.3), (0, 0, 5.1))):
        box(name, size, o + Vector(off), concrete, col)
    stairs = material('stairs', (0.35, 0.22, 0.12), rough=0.8)
    for k in range(8):                                                       # the stairs up to Mom (light spills down them)
        box(f'stair{k}', (1.6, 0.45, 0.3), o + Vector((-8.6, 6.8 - k * 0.45, 0.15 + k * 0.3)), stairs, col)
    prop('basement', 'gaming_chair', col, o + Vector((0, 0, 0)), 180, 1.0)            # Anon wakes up here
    prop('basement', 'crt_tv', col, o + Vector((3.2, 2.2, 0)), 200, 1.0)              # Mensa's console
    screen('rain_crt', 0.62, 0.48, o + Vector((3.05, 1.72, 1.32)), (math.radians(90), 0, math.radians(200)), col, 3.0)
    prop('basement', 'pizza_stack', col, o + Vector((4.6, 3.0, 0)), 0, 1.0)
    prop('basement', 'can_pyramid', col, o + Vector((5.6, 3.6, 0)), 10, 1.0)
    prop('basement', 'laundry_pile', col, o + Vector((-3.5, 3.5, 0)), 0, 1.0)
    prop('basement', 'washer', col, o + Vector((-6.5, 6.5, 0)), 180, 1.1)             # the Oracle's corner
    prop('basement', 'washer', col, o + Vector((-5.3, 6.5, 0)), 180, 1.1)
    prop('basement', 'box_stack', col, o + Vector((-3.0, 7.2, 0)), 170, 0.9)          # Alon sits by it
    prop('basement', 'water_heater', col, o + Vector((7.5, 7.5, 0)), 180, 1.0)
    prop('basement', 'desk_fan', col, o + Vector((2.0, 3.0, 0)), 200, 1.0)
    prop('basement', 'pipe_lights', col, o + Vector((0, 8.5, 2.0)), 180, 1.2)
    # lights: two bare bulbs (warm), the CRT's green, cold daylight from a window well, and the stair light
    bulb = material('bulb', (1.0, 0.8, 0.5), emit=(1.0, 0.75, 0.4), strength=8.0)
    for name, off in (('bulb_a', (0.5, 1.5, 4.4)), ('bulb_b', (-5.5, 6.0, 4.4))):
        sphere(name, 0.08, o + Vector(off), bulb, col)
        light('L_' + name, 'POINT', o + Vector(off) - Vector((0, 0, 0.12)), 260, (1.0, 0.72, 0.42), lit, size=0.08)
    light('base_crt', 'AREA', o + Vector((2.9, 1.4, 1.3)), 40, (0.3, 1.0, 0.45), lit, size=0.6, rot=(math.radians(90), 0, math.radians(200)))
    light('base_window', 'AREA', o + Vector((6, -8.5, 4.2)), 300, (0.6, 0.75, 1.0), lit, size=2.0, rot=(math.radians(60), 0, 0))
    light('base_stairs', 'SPOT', o + Vector((-8.6, 9.5, 4.8)), 900, (1.0, 0.85, 0.65), lit, rot=(math.radians(-60), 0, 0), spot=math.radians(50))
    return col


# ---------------------------------------------------------------- the Metaverse dojo (training program)
def build_dojo():
    col = collection('DOJO')
    lit = collection('L_DOJO')
    o = ORIGIN['DOJO']
    _ground('dojo_ground', 'metaverse', 80, o, col, 16, (1.0, 0.9, 1.0), rough=0.25)
    prop('metaverse', 'me_arch', col, o + Vector((0, 9, 0)), 0, 1.0)
    for x in (-6, 6):
        prop('metaverse', 'me_column', col, o + Vector((x, 6, 0)), 0, 1.0)
        prop('metaverse', 'me_column', col, o + Vector((x, -4, 0)), 0, 1.0)
    prop('metaverse', 'me_bust', col, o + Vector((-14, 26, -1)), 15, 1.2)
    prop('metaverse', 'me_bust_s', col, o + Vector((15, 22, -1)), -20, 1.0)
    for x, y in ((-11, 4), (11, 2), (-9, -9), (10, -10)):
        prop('metaverse', 'me_palm', col, o + Vector((x, y, 0)), x * 7, 0.9)
    prop('metaverse', 'me_crt', col, o + Vector((4, 12, 0)), 160, 1.0)
    prop('metaverse', 'me_cube_c', col, o + Vector((-4.5, 13, 0)), 20, 1.0)
    prop('metaverse', 'me_ruin', col, o + Vector((8, 13, 0)), 0, 1.0)
    mat_m = material('dojo_mat', (0.08, 0.05, 0.12), rough=0.6)                          # the sparring mat: dark, neon edge
    box('dojo_mat', (6.0, 6.0, 0.06), o + Vector((0, 0, 0.03)), mat_m, col)
    edge = material('dojo_edge', (1.0, 0.3, 0.8), emit=(1.0, 0.3, 0.8), strength=2.0)
    for name, size, off in (('edge_n', (6.1, 0.08, 0.08), (0, 3.0, 0.06)), ('edge_s', (6.1, 0.08, 0.08), (0, -3.0, 0.06)),
                            ('edge_e', (0.08, 6.1, 0.08), (3.0, 0, 0.06)), ('edge_w', (0.08, 6.1, 0.08), (-3.0, 0, 0.06))):
        box(name, size, o + Vector(off), edge, col)
    back, _ = textured_plane('dojo_backdrop', 160, 80, o + Vector((0, 60, 18)), os.path.join(PACK, 'arenas', 'metaverse', 'backdrop.webp'),
                             col, emit=1.0, rot=(math.pi / 2, 0, 0))
    back.visible_shadow = False
    light('dojo_sun', 'SUN', o + Vector((0, 0, 20)), 4.5, (1.0, 0.75, 0.95), lit, rot=(math.radians(50), 0, math.radians(200)))
    light('dojo_rim', 'AREA', o + Vector((0, 8, 4)), 800, (0.4, 0.9, 1.0), lit, size=6, rot=(math.radians(-110), 0, 0))
    return col


def world():
    """Dark world: the sets carry their own light. The dojo's sun and sky card do the bright look."""
    w = bpy.data.worlds.new('mx_world')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.01, 0.012, 0.016, 1)
    bg.inputs[1].default_value = 1.0
    return bg


# ---------------------------------------------------------------- hand props
def candle(name, colour, col, size=1.0):
    """A chart candle: body plus wick, faintly glowing. Origin at the body's centre."""
    glow = (0.95, 0.12, 0.1) if colour == 'red' else (0.1, 0.95, 0.25)
    body_m = material(f'candle_{colour}', glow, rough=0.25, emit=glow, strength=0.6)
    wick_m = material(f'wick_{colour}', tuple(c * 0.6 for c in glow), rough=0.4)
    holder = bpy.data.objects.new(name, None)
    col.objects.link(holder)
    body = box(name + '_body', (0.07 * size, 0.07 * size, 0.17 * size), (0, 0, 0), body_m, col, parent=holder, bevel=0.008 * size)
    wick = cylinder(name + '_wick', 0.006 * size, 0.32 * size, (0, 0, 0), wick_m, col, parent=holder, verts=8)
    for part in (body, wick):
        part.visible_shadow = False
    return holder


def sunglasses(name, col, width=0.2):
    """Small oval black shades (the agents' and the mentor's)."""
    lens = material('shades', (0.01, 0.01, 0.012), rough=0.05, metal=0.3)
    holder = bpy.data.objects.new(name, None)
    col.objects.link(holder)
    for s in (-1, 1):
        sphere(f'{name}_l{s}', 1.0, (s * width * 0.26, 0, 0), lens, col, parent=holder, scale=(width * 0.22, width * 0.06, width * 0.15))
    box(f'{name}_bridge', (width * 0.18, width * 0.04, width * 0.03), (0, 0, width * 0.05), lens, col, parent=holder)
    return holder


def cookie(name, col):
    m = material('cookie', (0.55, 0.33, 0.14), rough=0.8)
    chip = material('chip', (0.12, 0.06, 0.03), rough=0.6)
    holder = bpy.data.objects.new(name, None)
    col.objects.link(holder)
    cylinder(name + '_b', 0.07, 0.02, (0, 0, 0), m, col, parent=holder, verts=24)
    for k in range(5):
        a = k * 2.4
        sphere(f'{name}_c{k}', 0.011, (0.04 * math.cos(a), 0.04 * math.sin(a), 0.01), chip, col, parent=holder)
    return holder


def bent_card(name, col, art=None):
    """A game card bent in a curve (the kid's 'there is no chart' card)."""
    path = art or os.path.join(HERE, '..', 'deployed', 'pack', 'cards', 'cupsey.png')
    mat = image_material(name + '_m', path) if os.path.exists(path) else material(name + '_m', (0.9, 0.85, 0.6))
    obj = plane(name, 0.16, 0.22, (0, 0, 0), mat, col)
    bpy.context.view_layer.objects.active = obj
    sub = obj.modifiers.new('sub', 'SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = sub.render_levels = 3
    bend = obj.modifiers.new('bend', 'SIMPLE_DEFORM')
    bend.deform_method = 'BEND'
    bend.deform_axis = 'Y'
    bend.angle = 0.0
    obj.rotation_euler = (math.pi / 2, 0, 0)
    return obj


def attach(obj, armature, bone, world_point, world_rot=None):
    """Parent obj to a bone, keeping it at world_point now (bind pose)."""
    bpy.context.view_layer.update()
    obj.location = world_point
    if world_rot is not None:
        obj.rotation_euler = world_rot
    bpy.context.view_layer.update()
    mw = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = mw


# ---------------------------------------------------------------- the rooftop (inside the Memetrix, night)
def window_material(name, seed):
    """Office tower facade: a grid of windows, some lit warm, some cold, most dark."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.02, 0.025, 0.025, 1)
    bsdf.inputs['Roughness'].default_value = 0.4
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Location'].default_value = (seed * 3.7, seed * 1.3, 0)
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.offset = 0.0
    brick.squash = 1.0
    brick.inputs['Scale'].default_value = 0.6
    brick.inputs['Mortar Size'].default_value = 0.35
    brick.inputs['Bias'].default_value = 0.55
    brick.inputs['Color1'].default_value = (1.0, 0.82, 0.55, 1)
    brick.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1)
    brick.inputs['Mortar'].default_value = (0.0, 0.0, 0.0, 1)
    brick.inputs['Brick Width'].default_value = 1.0
    brick.inputs['Row Height'].default_value = 1.4
    nt.links.new(coord.outputs['Object'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], brick.inputs['Vector'])
    nt.links.new(brick.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 2.2
    return mat


def build_rooftop():
    import random
    rnd = random.Random(5)
    col = collection('ROOFTOP')
    lit = collection('L_ROOFTOP')
    o = ORIGIN['ROOFTOP']
    roof = material('roof_gravel', (0.16, 0.17, 0.16), rough=0.95)
    add_bump(roof, 60.0, 0.35)
    box('roof', (34, 34, 1.0), o + Vector((0, 0, -0.5)), roof, col)
    walls = material('tower_wall', (0.05, 0.06, 0.06), rough=0.6)
    box('tower', (34, 34, 160), o + Vector((0, 0, -81)), window_material('tower_win', 0), col)
    parapet = material('parapet', (0.32, 0.32, 0.30), rough=0.9)
    for name, size, off in (('par_n', (34, 0.5, 1.1), (0, 16.75, 0.55)), ('par_s', (34, 0.5, 1.1), (0, -16.75, 0.55)),
                            ('par_e', (0.5, 34, 1.1), (16.75, 0, 0.55)), ('par_w', (0.5, 34, 1.1), (-16.75, 0, 0.55))):
        box(name, size, o + Vector(off), parapet, col)
    metal = material('roof_metal', (0.5, 0.52, 0.5), rough=0.45, metal=0.8)
    dark = material('roof_dark', (0.05, 0.05, 0.05), rough=0.6)
    for k, (x, y) in enumerate(((-10, 9), (-12.5, 9), (10, -10), (12.5, -10), (11, 8))):        # AC units with fans
        box(f'ac{k}', (2.0, 1.6, 1.4), o + Vector((x, y, 0.7)), metal, col, bevel=0.04)
        cylinder(f'acfan{k}', 0.6, 0.06, o + Vector((x, y, 1.42)), dark, col, verts=24)
    for k, (x, y) in enumerate(((-6, -11), (7, 12), (-13, -4), (13.5, 2))):                   # vent stacks
        cylinder(f'vent{k}', 0.25, 1.8, o + Vector((x, y, 0.9)), metal, col, verts=16)
        cylinder(f'ventcap{k}', 0.4, 0.12, o + Vector((x, y, 1.86)), metal, col, verts=16)
    box('stair_house', (3.5, 3.0, 3.0), o + Vector((-11, -11, 1.5)), parapet, col)          # the door Michi comes out of
    box('stair_door', (1.0, 0.08, 2.1), o + Vector((-10.2, -9.46, 1.05)), material('door', (0.35, 0.12, 0.08), rough=0.6), col)
    wood = material('tower_wood', (0.35, 0.22, 0.12), rough=0.85)
    tw = o + Vector((11, 11.5, 0))                                                              # water tower on legs
    for dx, dy in ((-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)):
        cylinder(f'leg{dx}{dy}', 0.08, 4.0, tw + Vector((dx, dy, 2.0)), dark, col, verts=8)
    cylinder('tank', 1.7, 3.0, tw + Vector((0, 0, 5.5)), wood, col, verts=32)
    bpy.ops.mesh.primitive_cone_add(radius1=1.85, depth=1.1, location=tw + Vector((0, 0, 7.55)), vertices=32)
    cone = bpy.context.active_object
    cone.name = 'tank_roof'
    for c in list(cone.users_collection):
        c.objects.unlink(cone)
    col.objects.link(cone)
    cone.data.materials.append(dark)
    cylinder('mast', 0.06, 9.0, o + Vector((-13, 13, 4.5)), metal, col, verts=8)              # antenna with a red light
    beacon = material('beacon', (1, 0.05, 0.03), emit=(1, 0.05, 0.03), strength=6.0)
    sphere('beacon', 0.12, o + Vector((-13, 13, 9.05)), beacon, col)
    pad = material('helipad', (0.85, 0.8, 0.2), rough=0.7)                                     # helipad ring and H, painted
    bpy.ops.mesh.primitive_torus_add(major_radius=4.2, minor_radius=0.12, location=o + Vector((0, 0, 0.005)), major_segments=64, minor_segments=4)
    ring = bpy.context.active_object
    ring.scale = (1, 1, 0.05)
    for c in list(ring.users_collection):
        c.objects.unlink(ring)
    col.objects.link(ring)
    ring.data.materials.append(pad)
    for name, size, off in (('h_l', (0.35, 3.2, 0.01), (-1.0, 0, 0.005)), ('h_r', (0.35, 3.2, 0.01), (1.0, 0, 0.005)), ('h_m', (2.0, 0.35, 0.01), (0, 0, 0.005))):
        box(name, size, o + Vector(off), pad, col)
    # the city: towers all round, tops between 25 m below and 40 m above the roof; streets glow far below
    for k in range(70):
        ang = rnd.uniform(0, math.tau)
        dist = rnd.uniform(45, 260)
        w, d = rnd.uniform(14, 34), rnd.uniform(14, 34)
        top = rnd.uniform(-25, 40) * (1.0 if dist > 70 else 0.5)
        centre = o + Vector((math.cos(ang) * dist, math.sin(ang) * dist, (top - 200) / 2))
        b = box(f'city{k}', (w, d, top + 200), centre, window_material(f'win{k}', k + 1), col)
        b.rotation_euler = (0, 0, rnd.uniform(0, math.pi))
        if rnd.random() < 0.3:
            sphere(f'cbeacon{k}', 0.4, centre + Vector((0, 0, (top + 200) / 2 + 0.6)), beacon, col)
    street = material('street_glow', (1.0, 0.6, 0.3), emit=(1.0, 0.55, 0.25), strength=1.2)
    plane('streets', 900, 900, o + Vector((0, 0, -200)), street, col)
    sky = material('rooftop_sky', (0.0, 0.0, 0.0), emit=(0.06, 0.12, 0.09), strength=1.0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=700, location=o, segments=32, ring_count=16)
    dome = bpy.context.active_object
    dome.name = 'rooftop_dome'
    for c in list(dome.users_collection):
        c.objects.unlink(dome)
    col.objects.link(dome)
    dome.data.materials.append(sky)
    dome.visible_shadow = False
    # light: cold moon from behind the agents, warm city bounce from below the parapet, a soft top so faces read
    light('moon', 'SUN', o + Vector((0, 0, 50)), 1.2, (0.7, 0.95, 0.85), lit, rot=(math.radians(55), 0, math.radians(160)))
    light('city_bounce', 'AREA', o + Vector((0, -20, -2)), 6000, (1.0, 0.7, 0.45), lit, size=30, rot=(math.radians(-70), 0, 0))
    light('roof_top', 'AREA', o + Vector((0, 2, 9)), 1400, (0.7, 1.0, 0.8), lit, size=12)
    light('roof_rim', 'AREA', o + Vector((0, 14, 4)), 2500, (0.5, 1.0, 0.7), lit, size=8, rot=(math.radians(-100), 0, 0))
    return col
