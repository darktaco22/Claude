"""The set: a 24-hour strip-mall pawn shop at 4 AM. Customer side (y < 0) and the pawnbroker's side (y > 0) split
by a counter with a bulletproof-glass partition (pass-through slot at counter height, a round speak grille).
Behind her: steel shelves of pawned things. Front: the shop window with the CASH 4 GOLD neon, the rainy lot
outside (for the opening shot). Blender axes: Z up; the counter runs along X at y = 0."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix
import assets
from room import pbr, plane, emissive, text_tex
import penthouse
from penthouse import flat, box

C = lambda: bpy.context.scene.collection
X0, X1 = -3.0, 3.0; BACK_Y = 2.2; FRONT_Y = -4.2; CEIL = 2.9
COUNTER_H = 0.97; COUNTER_D = 0.62          # counter top height, depth (y from -0.31 to 0.31)
GLASS_Z0, GLASS_Z1 = COUNTER_H + 0.07, 2.35   # the slot is the 7 cm gap under the glass
WIN = (-2.5, -0.4, 0.75, 2.45)               # shop window in the front wall (x0, x1, z0, z1)


def neon_img(path, lines, color, W=1600, H=520):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 150)
    y = 40
    for txt, sz in lines:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)
        d.text((W // 2, y + sz // 2), txt, font=f, fill=(*color, 255), anchor='mm', stroke_width=0); y += int(sz * 1.25)
    glow = im.filter(ImageFilter.GaussianBlur(14)); out = Image.alpha_composite(glow, im); out.save(path); return path


def build():
    tex = os.environ.get('DA_TEX', '/tmp')
    floor = pbr('pawn_floor', 'old_linoleum_flooring_01', scale=1.0, tint=(0.75, 0.7, 0.62), rough_add=0.1)
    wall = pbr('pawn_wall', 'painted_plaster_wall', scale=1.0, tint=(0.62, 0.6, 0.52))
    plane('floor', (X1 - X0, BACK_Y - FRONT_Y), ((X0 + X1) / 2, (BACK_Y + FRONT_Y) / 2, 0), (0, 0, 0), floor, uv_scale=0.5)
    ceil = pbr('pawn_ceiling', 'ceiling_interior', scale=1.0, tint=(0.7, 0.7, 0.68))
    plane('ceiling', (X1 - X0, BACK_Y - FRONT_Y), ((X0 + X1) / 2, (BACK_Y + FRONT_Y) / 2, CEIL), (math.pi, 0, 0), ceil, uv_scale=0.5)
    plane('back', (X1 - X0, CEIL), ((X0 + X1) / 2, BACK_Y, CEIL / 2), (math.pi / 2, 0, math.pi), wall, uv_scale=0.6)
    plane('left', (BACK_Y - FRONT_Y, CEIL), (X0, (BACK_Y + FRONT_Y) / 2, CEIL / 2), (math.pi / 2, 0, -math.pi / 2), wall, uv_scale=0.6)
    plane('right', (BACK_Y - FRONT_Y, CEIL), (X1, (BACK_Y + FRONT_Y) / 2, CEIL / 2), (math.pi / 2, 0, math.pi / 2), wall, uv_scale=0.6)
    # front wall with the shop window
    wx0, wx1, wz0, wz1 = WIN
    for (a, b, c, d) in ((X0, wx0, 0, CEIL), (wx1, X1, 0, CEIL), (wx0, wx1, 0, wz0), (wx0, wx1, wz1, CEIL)):
        plane('front', (b - a, d - c), ((a + b) / 2, FRONT_Y, (c + d) / 2), (math.pi / 2, 0, 0), wall)
    glass = bpy.data.materials['glass'] if 'glass' in bpy.data.materials else None
    # ---- the counter: laminate top, panelled front, kick plate
    top = flat('counter_top', (0.32, 0.27, 0.2), 0.35)
    body = pbr('counter_body', 'dark_brick_wall', scale=1.0, tint=(0.35, 0.33, 0.3)) if False else flat('counter_body', (0.18, 0.17, 0.16), 0.6)
    box('counter', (X0, -COUNTER_D / 2, 0), (X1, COUNTER_D / 2, COUNTER_H - 0.03), body)
    box('counter_top', (X0, -COUNTER_D / 2 - 0.03, COUNTER_H - 0.03), (X1, COUNTER_D / 2, COUNTER_H), top)
    # ---- bulletproof glass on aluminium posts, slot under it, round speak grilles at each window
    alu = flat('alu', (0.55, 0.56, 0.58), 0.3, 1.0)
    for x in (-1.4, 0.0, 1.4):
        box('post', (x - 0.025, -0.025, COUNTER_H), (x + 0.025, 0.025, GLASS_Z1 + 0.05), alu)
    box('glass_top_rail', (X0, -0.03, GLASS_Z1), (X1, 0.03, GLASS_Z1 + 0.06), alu)
    box('glass_bot_rail', (X0, -0.03, GLASS_Z0 - 0.015), (X1, 0.03, GLASS_Z0), alu)
    g = penthouse_glass()
    gl = plane('partition_glass', (X1 - X0, GLASS_Z1 - GLASS_Z0), ((X0 + X1) / 2, 0.0, (GLASS_Z0 + GLASS_Z1) / 2), (math.pi / 2, 0, 0), g)
    gl.visible_shadow = False
    for x in (-0.7, 0.7):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.012, location=(x, -0.006, 1.3), rotation=(math.pi / 2, 0, 0))
        o = bpy.context.active_object; o.name = 'grille'; o.data.materials.append(flat('grille', (0.4, 0.4, 0.42), 0.35, 1.0))
    # ---- the pawnbroker's side: shelves of pawned things, a back door, a desk lamp
    S = {}
    rr = random.Random(3)
    junk = ['portable_cassette_player', 'brass_vase_01', 'cardboard_box_01', 'binder_notebook', 'wine_bottles_01']
    for i, x in enumerate((-2.0, -0.85, 0.85, 2.0)):
        sh = assets.load('steel_frame_shelves_01')[0]; sh.location = (x, BACK_Y - 0.28, 0)
        for z in (0.35, 0.82, 1.3, 1.78):
            for k in range(2):
                aid = rr.choice(junk); r, _ = assets.load(aid); r.location = (x - 0.3 + k * 0.55 + rr.uniform(-0.05, 0.05), BACK_Y - 0.3, z)
                r.rotation_euler = (0, 0, rr.uniform(-0.4, 0.4))
    # TVs and a guitar case on the shelves would be nice; the boxes, players and vases read as pawned junk
    S['lamp'] = assets.load('desk_lamp_arm_01')[0]; S['lamp'].location = (1.1, 0.12, COUNTER_H); S['lamp'].scale = (0.6, 0.6, 0.6)
    for x in (-1.5, 0.0, 1.5):
        for y in (-2.4, 0.9):
            r, _ = assets.load('mounted_fluorescent_lights'); r.location = (x, y, CEIL - 0.005); r.rotation_euler = (math.pi, 0, 0)
    tc = assets.load('metal_trash_can')[0]; tc.location = (2.4, -3.6, 0); tc.scale = (0.5, 0.5, 0.5)
    # ---- the window: glass, neon CASH 4 GOLD / OPEN 24 HRS facing out (seen mirrored from inside: drawn mirrored)
    pg = penthouse_glass()
    wg = plane('shop_window', (wx1 - wx0, wz1 - wz0), ((wx0 + wx1) / 2, FRONT_Y, (wz0 + wz1) / 2), (math.pi / 2, 0, 0), pg); wg.visible_shadow = False
    n1 = neon_img(f'{tex}/neon_cash.png', [('CASH 4 GOLD', 190), ('WE BUY ANYTHING', 110)], (255, 196, 40))
    n2 = neon_img(f'{tex}/neon_open.png', [('OPEN 24 HRS', 150)], (255, 40, 60), W=1200, H=260)
    m1 = emissive('neon_cash', n1, 9.0, alpha=True); m2 = emissive('neon_open', n2, 9.0, alpha=True)
    S['neon1'] = plane('neon_cash', (1.5, 0.49), ((wx0 + wx1) / 2, FRONT_Y + 0.06, 2.0), (math.pi / 2, 0, math.pi), m1, flip=True)
    S['neon2'] = plane('neon_open', (0.9, 0.2), ((wx0 + wx1) / 2, FRONT_Y + 0.06, 1.35), (math.pi / 2, 0, math.pi), m2, flip=True)
    # outside: the same signs read correctly from the lot, a dark facade, wet asphalt, rain
    S['neon1o'] = plane('neon_cash_o', (1.5, 0.49), ((wx0 + wx1) / 2, FRONT_Y - 0.04, 2.0), (math.pi / 2, 0, 0), m1)
    S['neon2o'] = plane('neon_open_o', (0.9, 0.2), ((wx0 + wx1) / 2, FRONT_Y - 0.04, 1.35), (math.pi / 2, 0, 0), m2)
    fac = flat('facade', (0.08, 0.08, 0.09), 0.7)
    for (a, b, c, d) in ((X0 - 6, wx0, 0, 3.6), (wx1, X1 + 6, 0, 3.6), (wx0, wx1, 0, wz0), (wx0, wx1, wz1, 3.6)):
        plane('facade', (b - a, d - c), ((a + b) / 2, FRONT_Y - 0.03, (c + d) / 2), (math.pi / 2, 0, 0), fac)
    asph = pbr('lot', 'asphalt_02', scale=1.0, tint=(0.3, 0.3, 0.32), rough_mul=0.35)
    plane('lot', (20, 14), (0, FRONT_Y - 7.0, -0.01), (0, 0, 0), asph, uv_scale=0.4)
    rn = penthouse.rain_outside(1800)
    rr2 = random.Random(8); me = rn.data
    for f in range(0, len(me.vertices), 4):
        cx = rr2.uniform(-4.5, 3.0); cy = rr2.uniform(FRONT_Y - 5.5, FRONT_Y - 0.3)
        bx = me.vertices[f].co.x
        for k in range(4):
            v = me.vertices[f + k]; v.co.x = cx + (v.co.x - bx); v.co.y = cy
    w = bpy.data.worlds.new('night'); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.01, 0.012, 0.02, 1); bg.inputs['Strength'].default_value = 1.0
    return S


def penthouse_glass():
    """Thin-pane glass (see-through plus a Fresnel reflection), with a faint scuffed tint for the partition."""
    g = bpy.data.materials.new('pane'); g.use_nodes = True; nt = g.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (0.93, 0.97, 0.95, 1)
    gl_ = nt.nodes.new('ShaderNodeBsdfGlossy'); gl_.inputs['Roughness'].default_value = 0.06
    fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5; mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fr.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl_.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes['Material Output'].inputs[0])
    return g
