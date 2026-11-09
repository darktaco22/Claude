"""The set: a suburban family kitchen, seen at 11:47 PM and again at 7:15 AM. An island across the room (y = 0), counters,
stove and fridge along the back wall under a window, a doorway in the right wall (where the repo man appears).
Blender axes: Z up; the camera mostly looks toward +Y."""
import bpy, math, os
from mathutils import Vector
import assets
from room import pbr, plane
from penthouse import flat, box

X0, X1 = -3.0, 3.0; BACK_Y = 2.4; FRONT_Y = -3.6; CEIL = 2.7
ISL_H = 0.92; ISL = (-1.0, 1.0, -0.4, 0.4)        # island x0, x1, y0, y1
WIN = (-1.6, 0.2, 1.15, 2.15)                      # window over the sink (x0, x1, z0, z1) in the back wall
DOOR = (-1.9, -0.9, 2.1)                           # doorway in the right wall: y0, y1, height


def place(aid, loc, rz=0.0, s=1.0):
    r, ms = assets.load(aid); r.location = loc; r.rotation_euler = (0, 0, math.radians(rz)); r.scale = (s, s, s); return r


def build():
    floor = pbr('k_floor', 'wood_floor', scale=1.0, tint=(0.85, 0.75, 0.62), rough_add=0.15)
    wall = pbr('k_wall', 'white_plaster_02', scale=1.0, tint=(0.93, 0.88, 0.78))
    plane('floor', (X1 - X0, BACK_Y - FRONT_Y), ((X0 + X1) / 2, (BACK_Y + FRONT_Y) / 2, 0), (0, 0, 0), floor, uv_scale=0.6)
    plane('ceiling', (X1 - X0, BACK_Y - FRONT_Y), ((X0 + X1) / 2, (BACK_Y + FRONT_Y) / 2, CEIL), (math.pi, 0, 0), flat('k_ceil', (0.9, 0.88, 0.84), 0.9))
    wx0, wx1, wz0, wz1 = WIN
    for (a, b, c, d) in ((X0, wx0, 0, CEIL), (wx1, X1, 0, CEIL), (wx0, wx1, 0, wz0), (wx0, wx1, wz1, CEIL)):
        plane('back', (b - a, d - c), ((a + b) / 2, BACK_Y, (c + d) / 2), (math.pi / 2, 0, math.pi), wall, uv_scale=0.6)
    plane('left', (BACK_Y - FRONT_Y, CEIL), (X0, (BACK_Y + FRONT_Y) / 2, CEIL / 2), (math.pi / 2, 0, -math.pi / 2), wall, uv_scale=0.6)
    dy0, dy1, dh = DOOR
    for (a, b, c, d) in ((FRONT_Y, dy0, 0, CEIL), (dy1, BACK_Y, 0, CEIL), (dy0, dy1, dh, CEIL)):
        plane('right', (b - a, d - c), (X1, (a + b) / 2, (c + d) / 2), (math.pi / 2, 0, math.pi / 2), wall, uv_scale=0.6)
    plane('front', (X1 - X0, CEIL), ((X0 + X1) / 2, FRONT_Y, CEIL / 2), (math.pi / 2, 0, 0), wall, uv_scale=0.6)
    plane('hall_floor', (2.0, 1.4), (X1 + 1.0, (dy0 + dy1) / 2, 0), (0, 0, 0), floor, uv_scale=0.6)
    plane('hall_wall', (1.4, CEIL), (X1 + 1.9, (dy0 + dy1) / 2, CEIL / 2), (math.pi / 2, 0, math.pi / 2), wall)
    trim = flat('k_trim', (0.95, 0.94, 0.9), 0.5)
    for y in (dy0, dy1): box('door_jamb', (X1 - 0.02, y - 0.04, 0), (X1 + 0.12, y + 0.04 if y == dy0 else y + 0.04, dh), trim)
    # counters along the back wall: white shaker cabinets, a marble top, upper cabinets either side of the window
    cab = flat('k_cab', (0.82, 0.84, 0.8), 0.45); top = pbr('k_marble', 'marble_01', scale=1.0, rough_add=0.05)
    box('base_cab', (X0, BACK_Y - 0.62, 0), (X1 - 0.6, BACK_Y, 0.88), cab)
    box('back_top', (X0, BACK_Y - 0.64, 0.88), (X1 - 0.6, BACK_Y, 0.92), top)
    for (a, b) in ((X0, wx0 - 0.15), (wx1 + 0.15, X1 - 1.4)):
        box('upper_cab', (a, BACK_Y - 0.35, 1.5), (b, BACK_Y, 2.25), cab)
    for x in [X0 + 0.3 + 0.6 * i for i in range(9)]:
        if x < X1 - 0.7: box('handle', (x - 0.06, BACK_Y - 0.64, 0.74), (x + 0.06, BACK_Y - 0.62, 0.755), flat('k_steel', (0.7, 0.7, 0.72), 0.25, 1.0))
    # the fridge in the corner
    steel = flat('k_fridge', (0.72, 0.73, 0.75), 0.3, 0.9)
    box('fridge', (X1 - 0.95, BACK_Y - 0.72, 0), (X1 - 0.05, BACK_Y - 0.02, 1.95), steel)
    box('fridge_gap', (X1 - 0.51, BACK_Y - 0.725, 0.02), (X1 - 0.49, BACK_Y - 0.72, 1.93), flat('k_gap', (0.05, 0.05, 0.05), 0.6))
    for x in (X1 - 0.56, X1 - 0.44): box('fridge_h', (x - 0.012, BACK_Y - 0.78, 0.9), (x + 0.012, BACK_Y - 0.74, 1.5), flat('k_steel', (0.7, 0.7, 0.72), 0.25, 1.0))
    # sink window: frame, glass (the night/morning sky is the world behind it)
    from penthouse import WALL_Y as _w  # noqa (keeps the penthouse module's glass helpers importable)
    g = bpy.data.materials.new('k_glass'); g.use_nodes = True; nt = g.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); nt.links.new(tr.outputs[0], nt.nodes['Material Output'].inputs[0])
    plane('k_window', (wx1 - wx0, wz1 - wz0), ((wx0 + wx1) / 2, BACK_Y + 0.02, (wz0 + wz1) / 2), (math.pi / 2, 0, 0), g).visible_shadow = False
    for (a, b, c, d) in ((wx0 - 0.05, wx0, wz0, wz1), (wx1, wx1 + 0.05, wz0, wz1), (wx0 - 0.05, wx1 + 0.05, wz0 - 0.05, wz0), (wx0 - 0.05, wx1 + 0.05, wz1, wz1 + 0.05)):
        box('win_frame', (a, BACK_Y - 0.03, c), (b, BACK_Y + 0.05, d), trim)
    box('mullion', ((wx0 + wx1) / 2 - 0.02, BACK_Y - 0.02, wz0), ((wx0 + wx1) / 2 + 0.02, BACK_Y + 0.04, wz1), trim)
    # the island: navy base, butcher-block top
    box('island', (ISL[0], ISL[2], 0), (ISL[1], ISL[3], ISL_H - 0.04), flat('k_island', (0.12, 0.18, 0.3), 0.5))
    box('island_top', (ISL[0] - 0.04, ISL[2] - 0.05, ISL_H - 0.04), (ISL[1] + 0.04, ISL[3] + 0.05, ISL_H), flat('k_block', (0.55, 0.38, 0.22), 0.45))
    # dressing
    place('electric_stove', (0.9, BACK_Y - 0.4, 0), 180, 0.72)
    place('vintage_microwave', (-2.5, BACK_Y - 0.32, 0.92), 180, 0.5)
    place('vintage_electric_kettle', (0.2 + 0.35, BACK_Y - 0.33, 0.92), 200, 0.8)
    place('bananas', (0.55, 0.1, ISL_H), 30, 0.9)
    place('food_apple_01', (0.75, -0.12, ISL_H), 0); place('food_apple_01', (0.68, -0.05, ISL_H), 70)
    place('wall_clock', (-2.98, 0.4, 1.95), 90, 1.2)
    place('potted_plant_02', (X0 + 0.45, -2.8, 0), 0)
    sky = bpy.data.worlds.new('sky'); bpy.context.scene.world = sky; sky.use_nodes = True
    bg = sky.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.02, 0.03, 0.06, 1); bg.inputs['Strength'].default_value = 1.0
    return {}
