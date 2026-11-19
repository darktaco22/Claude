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
from mathutils import Matrix, Vector

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
    haze('haze_floor', o + Vector((0, 1, 4.5)), (27, 29, 8.8), 0.006, (0.8, 1.0, 0.85), col)
    dust('dust_floor', o + Vector((0, 2, 1.6)), (8, 12, 2.4), 500, (0.7, 1.0, 0.75), col, 2)
    light('floor_bull', 'SPOT', o + Vector((0, 6, 7.5)), 2500, (0.85, 1.0, 0.8), lit, rot=(math.radians(-35), 0, 0), spot=math.radians(35))
    return col


# ---------------------------------------------------------------- Mom's basement (the real world)
CRT_SCREEN = {}


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
    # the stairs up to Mom: treads with a nosing, painted risers, a worn carpet runner, a closed-in underside, a handrail on
    # balusters with a newel post, a landing with a rail, a family photo and a light switch on the wall
    tread_m = material('stair_tread', (0.42, 0.27, 0.15), rough=0.55)
    add_bump(tread_m, 30.0, 0.15)
    riser_m = material('stair_riser', (0.82, 0.79, 0.72), rough=0.7)
    runner_m = material('stair_runner', (0.32, 0.07, 0.06), rough=0.95)
    add_bump(runner_m, 120.0, 0.3)
    panel_m = material('stair_panel', (0.78, 0.75, 0.68), rough=0.75)
    add_bump(panel_m, 6.0, 0.08)
    rail_m = material('stair_rail', (0.30, 0.18, 0.10), rough=0.4)
    for k in range(8):
        yc, zt = 6.8 - k * 0.45, 0.3 + k * 0.3                                # step centre (y), top of the tread (z)
        box(f'stair{k}', (1.6, 0.45, 0.26), o + Vector((-8.6, yc, zt - 0.17)), riser_m, col)                       # the body
        box(f'tread{k}', (1.64, 0.49, 0.04), o + Vector((-8.6, yc + 0.02, zt - 0.02)), tread_m, col, bevel=0.008)   # nosing
        box(f'runner{k}', (0.8, 0.47, 0.012), o + Vector((-8.65, yc + 0.01, zt + 0.006)), runner_m, col)
        box(f'runner_r{k}', (0.8, 0.012, 0.26), o + Vector((-8.65, yc + 0.236, zt - 0.17)), runner_m, col)
    box('stair_landing', (1.6, 1.4, 0.3), o + Vector((-8.6, 2.95, 2.25)), riser_m, col)
    box('landing_top', (1.64, 1.44, 0.04), o + Vector((-8.6, 2.95, 2.38)), tread_m, col, bevel=0.008)
    import bmesh
    me = bpy.data.meshes.new('under_stairs')                                  # the side panel closing in the space under them
    bm = bmesh.new()
    vs = [bm.verts.new((o.x - 7.79, o.y + yy_, zz_)) for yy_, zz_ in ((7.025, 0.0), (2.25, 0.0), (2.25, 2.1), (3.875, 2.1))]
    bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()
    under = bpy.data.objects.new('under_stairs', me)
    col.objects.link(under)
    me.materials.append(panel_m)
    sol = under.modifiers.new('thick', 'SOLIDIFY')
    sol.thickness = 0.03
    for k in range(8):                                                       # balusters from each tread up to the rail
        yc, zt = 6.8 - k * 0.45, 0.3 + k * 0.3
        cylinder(f'baluster{k}', 0.018, 0.88, o + Vector((-7.88, yc, zt + 0.44)), rail_m, col, verts=8)
    box('newel', (0.1, 0.1, 1.3), o + Vector((-7.88, 7.05, 0.65)), rail_m, col, bevel=0.01)
    sphere('newel_cap', 0.07, o + Vector((-7.88, 7.05, 1.33)), rail_m, col)
    p0, p1 = Vector((-7.88, 7.05, 1.2)), Vector((-7.88, 3.65, 2.1 + 1.18))   # the handrail along the slope, top of the posts
    rail = cylinder('handrail', 0.03, (p1 - p0).length, o + (p0 + p1) / 2, rail_m, col, verts=12)
    rail.rotation_mode = 'QUATERNION'
    rail.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
    for k, yy_ in enumerate((3.55, 2.95, 2.35)):                              # the landing rail
        cylinder(f'landing_post{k}', 0.02, 0.9, o + Vector((-7.88, yy_, 2.85)), rail_m, col, verts=8)
    box('landing_rail', (0.06, 1.35, 0.06), o + Vector((-7.88, 2.95, 3.3)), rail_m, col)
    frame_m = material('photo_frame', (0.15, 0.1, 0.07), rough=0.4)
    photo_m = material('photo', (0.55, 0.45, 0.35), rough=0.6, emit=(0.25, 0.2, 0.15), strength=0.3)
    for k, (yy_, zz_, w_, h_) in enumerate(((5.2, 2.1, 0.45, 0.35), (4.4, 2.6, 0.3, 0.4), (6.0, 1.7, 0.3, 0.3))):   # family photos
        box(f'photo_frame{k}', (0.03, w_, h_), o + Vector((-9.78, yy_, zz_)), frame_m, col)
        box(f'photo{k}', (0.01, w_ - 0.06, h_ - 0.06), o + Vector((-9.76, yy_, zz_)), photo_m, col)
    plate_m = material('switch_plate', (0.9, 0.88, 0.82), rough=0.4)
    box('light_switch', (0.015, 0.08, 0.12), o + Vector((-9.79, 3.65, 3.55)), plate_m, col)
    basket_m = material('basket', (0.75, 0.72, 0.6), rough=0.8)
    cylinder('laundry_basket', 0.22, 0.28, o + Vector((-8.95, 6.8 - 2 * 0.45, 0.9 + 0.14)), basket_m, col, verts=20)
    shoe_m = material('shoe', (0.12, 0.12, 0.14), rough=0.6)
    for k, dx in enumerate((-0.1, 0.1)):
        box(f'shoe{k}', (0.1, 0.26, 0.09), o + Vector((-8.2 + dx, 7.35, 0.045)), shoe_m, col, rot=(0, 0, math.radians(8 * (k * 2 - 1))))
    trim = material('door_trim', (0.85, 0.82, 0.74), rough=0.6)
    for name, size, off in (('door_jamb_a', (0.12, 0.1, 2.1), (-9.74, 2.45, 3.45)), ('door_jamb_b', (0.12, 0.1, 2.1), (-9.74, 3.45, 3.45)),
                            ('door_head', (0.12, 1.1, 0.1), (-9.74, 2.95, 4.5))):
        box(name, size, o + Vector(off), trim, col)
    warm = material('door_glow', (1.0, 0.85, 0.6), emit=(1.0, 0.78, 0.5), strength=6.0)
    box('door_gap', (0.02, 0.9, 2.0), o + Vector((-9.79, 2.95, 3.4)), warm, col)          # light from Mom's kitchen
    door = material('door', (0.55, 0.42, 0.3), rough=0.7)
    box('door_leaf', (0.05, 0.9, 2.0), o + Vector((-9.45, 2.65, 3.4)), door, col, rot=(0, 0, math.radians(-55)))   # ajar
    light('L_door', 'AREA', o + Vector((-9.6, 2.95, 3.6)), 220, (1.0, 0.8, 0.55), lit, size=0.9, rot=(0, math.radians(-90), 0))
    prop('basement', 'gaming_chair', col, o + Vector((0.3, 2.3, 0)), 160, 1.0)        # behind Slerf (at 0,0 it blocked his shots)
    tv = prop('basement', 'crt_tv', col, o + Vector((3.2, 2.2, 0)), 20, 1.0)          # Mensa's console, screen toward him
    bpy.context.view_layer.update()                                                    # (at 200 degrees the screen faced the wall)
    glass = next(c for c in tv.children_recursive if 'screen' in c.name)
    body = next(c for c in tv.children_recursive if c.type == 'MESH' and c is not glass)
    gb = [glass.matrix_world @ Vector(v) for v in glass.bound_box]
    bb = [body.matrix_world @ Vector(v) for v in body.bound_box]
    gc = sum(gb, Vector()) / 8
    out = gc - sum(bb, Vector()) / 8
    out.z = 0
    out.normalize()                                                                    # the screen's outward normal
    gw = max((v - gc).dot(Vector((-out.y, out.x, 0))) for v in gb) * 2
    gh = max(v.z for v in gb) - min(v.z for v in gb)
    yaw = math.atan2(out.y, out.x) - math.pi / 2
    screen('rain_crt', gw * 0.92, gh * 0.9, gc + out * 0.03, (math.radians(90), 0, yaw + math.pi), col, 3.0)
    CRT_SCREEN.update(centre=gc + out * 0.03, normal=out)
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
    dust('dust_base', o + Vector((0, 2.5, 1.5)), (12, 9, 3.0), 500, (1.0, 0.85, 0.6), col, 3)
    haze('haze_base', o + Vector((0, 0, 2.5)), (19.5, 17.5, 4.9), 0.004, (1.0, 0.9, 0.8), col)
    crt_light = light('base_crt', 'AREA', CRT_SCREEN['centre'] + CRT_SCREEN['normal'] * 0.25, 60, (0.3, 1.0, 0.45), lit, size=0.6)
    crt_light.rotation_mode = 'QUATERNION'
    crt_light.rotation_quaternion = CRT_SCREEN['normal'].to_track_quat('-Z', 'Y')
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


def haze(name, centre, size, density, colour, col):
    """A box of thin fog so lights draw beams. Renderer can drop it (NOHAZE=1)."""
    mat = bpy.data.materials.new(name + '_m')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Density'].default_value = density
    vol.inputs['Color'].default_value = (*colour, 1)
    vol.inputs['Anisotropy'].default_value = 0.45
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(vol.outputs[0], out.inputs['Volume'])
    obj = box(name, size, centre, mat, col)
    obj.visible_shadow = False
    obj['cine_ignore'] = True
    return obj


def dust(name, centre, size, count, colour, col, seed=1):
    """Floating motes near the lens: tiny faintly glowing specks (bokeh with shallow focus). One mesh, vertex-instanced."""
    import random
    rnd = random.Random(seed)
    mesh = bpy.data.meshes.new(name)
    pts = [tuple(centre[i] + rnd.uniform(-size[i] / 2, size[i] / 2) for i in range(3)) for _ in range(count)]
    mesh.from_pydata(pts, [], [])
    cloud = bpy.data.objects.new(name, mesh)
    col.objects.link(cloud)
    speck_m = material(name + '_m', colour, rough=0.5, emit=colour, strength=0.25)
    speck = sphere(name + '_speck', 0.0022, (0, 0, 0), speck_m, col)
    speck.parent = cloud
    cloud.instance_type = 'VERTS'
    cloud['cine_ignore'] = True
    speck['cine_ignore'] = True
    speck.visible_shadow = False
    return cloud


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
def candle(name, colour, col, size=1.0, trail=0.0, rings=False):
    """A chart candle: body plus wick, faintly glowing. Origin at the body's centre. `trail` (m) adds a fading glow streak
    behind it along local -Y (projectiles fly along +Y of their own frame once rotated)."""
    glow = (0.95, 0.12, 0.1) if colour == 'red' else (0.1, 0.95, 0.25)
    body_m = material(f'candle_{colour}', glow, rough=0.25, emit=glow, strength=0.6)
    wick_m = material(f'wick_{colour}', tuple(c * 0.6 for c in glow), rough=0.4)
    holder = bpy.data.objects.new(name, None)
    col.objects.link(holder)
    body = box(name + '_body', (0.07 * size, 0.07 * size, 0.17 * size), (0, 0, 0), body_m, col, parent=holder, bevel=0.008 * size)
    wick = cylinder(name + '_wick', 0.006 * size, 0.32 * size, (0, 0, 0), wick_m, col, parent=holder, verts=8)
    for part in (body, wick):
        part.visible_shadow = False
    if trail:
        streak_m = material(f'streak_{colour}', glow, rough=0.5, emit=glow, strength=3.0)
        streak = cylinder(name + '_trail', 0.02 * size, trail, (0, 0, -trail / 2 - 0.09 * size), streak_m, col, parent=holder, verts=8)
        streak.data.transform(Matrix.Translation((0, 0, -trail / 2)))      # origin at the candle end: scale z grows it backwards
        streak.location.z = -0.09 * size
        streak.visible_shadow = False
    if rings:                                                  # bullet-time shock rings trailing the candle, fainter further back
        for j, (back, r) in enumerate(((0.3, 0.045), (0.6, 0.065), (0.95, 0.085))):
            ring_m = material(f'ring_{colour}_{j}', glow, rough=0.3, emit=glow, strength=1.6 - 0.45 * j)
            bpy.ops.mesh.primitive_torus_add(major_radius=r * size, minor_radius=0.006 * size, location=(0, 0, 0),
                                             major_segments=32, minor_segments=6)
            ring = bpy.context.active_object
            ring.name = f'{name}_ring{j}'
            for c_ in list(ring.users_collection):
                c_.objects.unlink(ring)
            col.objects.link(ring)
            ring.data.materials.append(ring_m)
            ring.parent = holder
            ring.location = (0, 0, -back * size)
            ring.visible_shadow = False
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
    pivot = bpy.data.objects.new(name + '_bend_pivot', None)   # a Y bend bends along the pivot's X: turn the pivot 90 degrees
    col.objects.link(pivot)                                     # so the card curls along its length (across its width barely
    pivot.parent = obj                                          # reads from the front, and X/Z bends do nothing to a flat card)
    pivot.rotation_euler = (0, 0, math.pi / 2)
    bend.origin = pivot
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
def window_material(name, seed, dims=(1, 1, 1)):
    """Office tower facade: a grid of windows, some lit warm, some cold, most dark."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.02, 0.025, 0.025, 1)
    bsdf.inputs['Roughness'].default_value = 0.4
    coord = nt.nodes.new('ShaderNodeTexCoord')
    metric = nt.nodes.new('ShaderNodeVectorMath')                  # object coords (-1..1) to metres on this tower
    metric.operation = 'MULTIPLY'
    metric.inputs[1].default_value = tuple(dims)                    # the box helper is a unit cube (-0.5..0.5) scaled to size
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    across = nt.nodes.new('ShaderNodeMath')                        # across the face (x on one pair of faces, y on the other)
    across.operation = 'ADD'
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Location'].default_value = (seed * 3.7, seed * 1.3, 0)
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.offset = 0.0
    brick.squash = 1.0
    brick.inputs['Scale'].default_value = 0.9
    brick.inputs['Mortar Size'].default_value = 0.12
    brick.inputs['Bias'].default_value = 0.55
    brick.inputs['Color1'].default_value = (1.0, 0.82, 0.55, 1)
    brick.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1)
    brick.inputs['Mortar'].default_value = (0.0, 0.0, 0.0, 1)
    brick.inputs['Brick Width'].default_value = 1.0
    brick.inputs['Row Height'].default_value = 1.4
    nt.links.new(coord.outputs['Object'], metric.inputs[0])
    nt.links.new(metric.outputs[0], sep.inputs[0])
    nt.links.new(sep.outputs['X'], across.inputs[0])
    nt.links.new(sep.outputs['Y'], across.inputs[1])
    nt.links.new(across.outputs[0], comb.inputs['X'])
    nt.links.new(sep.outputs['Z'], comb.inputs['Y'])
    nt.links.new(comb.outputs[0], mapping.inputs['Vector'])
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
    roof = material('roof_gravel', (0.07, 0.075, 0.07), rough=0.95)
    add_bump(roof, 60.0, 0.35)
    box('roof', (34, 34, 1.0), o + Vector((0, 0, -0.5)), roof, col)
    walls = material('tower_wall', (0.05, 0.06, 0.06), rough=0.6)
    box('tower', (34, 34, 160), o + Vector((0, 0, -81)), window_material('tower_win', 0, (34, 34, 160)), col)
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
    for name, size, off in (('h_l', (0.35, 3.2, 0.01), (-1.0, 0, 0.005)), ('h_r', (0.35, 3.2, 0.01), (1.0, 0, 0.005)), ('h_m', (1.65, 0.35, 0.01), (0, 0, 0.005))):
        box(name, size, o + Vector(off), pad, col)
    # the city: towers all round, tops between 25 m below and 40 m above the roof; streets glow far below
    for k in range(140):
        ang = rnd.uniform(0, math.tau)
        dist = rnd.uniform(70, 420)
        w, d = rnd.uniform(14, 30), rnd.uniform(14, 30)
        top = rnd.uniform(-70, 8) if dist < 200 else rnd.uniform(-40, 60)       # near: below us; far: a few taller towers
        centre = o + Vector((math.cos(ang) * dist, math.sin(ang) * dist, (top - 200) / 2))
        b = box(f'city{k}', (w, d, top + 200), centre, window_material(f'win{k}', k + 1, (w, d, top + 200)), col)
        b.rotation_euler = (0, 0, rnd.uniform(0, math.pi))
        if rnd.random() < 0.3:
            sphere(f'cbeacon{k}', 0.4, centre + Vector((0, 0, (top + 200) / 2 + 0.6)), beacon, col)
    street = material('street_glow', (1.0, 0.6, 0.3), emit=(1.0, 0.55, 0.25), strength=1.2)
    plane('streets', 900, 900, o + Vector((0, 0, -200)), street, col)
    sky = material('rooftop_sky', (0.0, 0.0, 0.0), emit=(0.015, 0.04, 0.03), strength=1.0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=700, location=o, segments=32, ring_count=16)
    dome = bpy.context.active_object
    dome.name = 'rooftop_dome'
    for c in list(dome.users_collection):
        c.objects.unlink(dome)
    col.objects.link(dome)
    dome.data.materials.append(sky)
    dome.visible_shadow = False
    haze('haze_roof', o + Vector((0, 0, 6)), (80, 80, 14), 0.004, (0.75, 1.0, 0.85), col)
    # light: cold moon from behind the agents, warm city bounce from below the parapet, a soft top so faces read
    light('moon', 'SUN', o + Vector((0, 0, 50)), 1.2, (0.7, 0.95, 0.85), lit, rot=(math.radians(55), 0, math.radians(160)))
    light('city_bounce', 'AREA', o + Vector((0, -20, -2)), 6000, (1.0, 0.7, 0.45), lit, size=30, rot=(math.radians(-70), 0, 0))
    light('roof_top', 'AREA', o + Vector((0, 2, 9)), 600, (0.7, 1.0, 0.8), lit, size=12)
    light('roof_rim', 'AREA', o + Vector((0, 14, 4)), 2500, (0.5, 1.0, 0.7), lit, size=8, rot=(math.radians(-100), 0, 0))
    return col
