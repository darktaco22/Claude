"""The sets: a church-basement meeting room at 3 AM (cinder block, checker linoleum, drop ceiling,
flickering fluorescents) and, for the opening, the rainy alley door with its neon sign.
Blender axes: Z up; the camera looks toward +Y; the cast faces -Y."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import assets, props

PH = os.environ.get('PH', '')
TEX = os.environ.get('DA_TEX', '/tmp')
C = lambda: bpy.context.scene.collection
R = random.Random(7)


def pbr(name, tex, scale=1.0, tint=None, rough_mul=1.0, rough_add=0.0, disp=0.0, coords='UV', normal_str=1.0, checker=None, paint=None):
    """A Poly Haven PBR texture set as a material. coords='BOX' uses object-space box projection."""
    d = f'{PH}/{tex}'; files = os.listdir(d)
    pick = lambda key: next((f'{d}/{f}' for f in files if key in f), None)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['UV' if coords == 'UV' else 'Object'], mp.inputs['Vector'])
    def img(path, non_color=False):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
        if non_color: t.image.colorspace_settings.name = 'Non-Color'
        if coords == 'BOX': t.projection = 'BOX'; t.projection_blend = 0.2
        nt.links.new(mp.outputs[0], t.inputs['Vector']); return t
    col = img(pick('_diff')).outputs[0]
    if tint is not None and paint is not None:
        bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(col, bw.inputs[0])
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.45
        mr.inputs['To Min'].default_value = 0.62; mr.inputs['To Max'].default_value = 1.05; nt.links.new(bw.outputs[0], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        mx.inputs[6].default_value = (*tint, 1); nt.links.new(mr.outputs[0], mx.inputs[7]); col = mx.outputs[2]
    elif tint is not None:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        mx.inputs[7].default_value = (*tint, 1); nt.links.new(col, mx.inputs[6]); col = mx.outputs[2]
    if checker is not None:
        # a two-colour tile pattern multiplied over the texture's grime
        ck = nt.nodes.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = checker[0]
        ck.inputs['Color1'].default_value = (*checker[1], 1); ck.inputs['Color2'].default_value = (*checker[2], 1)
        tc2 = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc2.outputs['Object'], ck.inputs['Vector'])
        bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(col, bw.inputs[0])
        ga = nt.nodes.new('ShaderNodeMapRange'); ga.inputs['From Min'].default_value = 0.0; ga.inputs['From Max'].default_value = 0.6
        ga.inputs['To Min'].default_value = 0.55; ga.inputs['To Max'].default_value = 1.05; nt.links.new(bw.outputs[0], ga.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        nt.links.new(ck.outputs['Color'], mx.inputs[6]); nt.links.new(ga.outputs[0], mx.inputs[7]); col = mx.outputs[2]
    nt.links.new(col, b.inputs['Base Color'])
    rp = pick('_rough') or None
    if rp:
        r = img(rp, True); mr = nt.nodes.new('ShaderNodeMath'); mr.operation = 'MULTIPLY_ADD'
        mr.inputs[1].default_value = rough_mul; mr.inputs[2].default_value = rough_add
        nt.links.new(r.outputs[0], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs['Roughness'])
    np_ = pick('_nor_gl')
    if np_:
        n = img(np_, True); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_str
        nt.links.new(n.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    return m


def plane(name, size, loc, rot, m, uv_scale=None, flip=False):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = (size[0], size[1], 1); bpy.ops.object.transform_apply(scale=True)
    if flip:
        for l in o.data.uv_layers[0].data: l.uv = (1.0 - l.uv.x, l.uv.y)
    if uv_scale:
        for l in o.data.uv_layers[0].data: l.uv = (l.uv.x * size[0] * uv_scale, l.uv.y * size[1] * uv_scale)
    o.data.materials.append(m)
    return o


def text_tex(path, w, h, draw):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); draw(im, d, w, h); im.save(path); return path


def emissive(name, img, strength=4.0, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    out = nt.nodes['Material Output']; t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img)
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength; nt.links.new(t.outputs[0], em.inputs['Color'])
    if alpha:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(t.outputs[1], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    else:
        nt.links.new(em.outputs[0], out.inputs[0])
    return m


def printed(name, img, rough=0.75):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img); nt.links.new(t.outputs[0], b.inputs['Base Color'])
    nt.links.new(t.outputs[1], b.inputs['Alpha']); b.inputs['Roughness'].default_value = rough
    return m


SEAT_ANGLES = [-56, -28, 0, 28, 56]
CHAIR_S = 0.92            # a slightly smaller school chair: seat at 46 cm
SEAT_H = 0.5 * CHAIR_S
def seats():
    out = []
    for d in SEAT_ANGLES:
        a = math.radians(d); x = math.sin(a) * 1.45; y = math.cos(a) * 1.45 - 0.2
        out.append(dict(x=x, y=y, face=math.atan2(-x, 0.8 + y)))
    return out


def basement():
    S = {}
    wall = pbr('cinderblock', 'concrete_block_wall', scale=0.55, tint=(0.40, 0.47, 0.34), rough_add=0.05, coords='UV', paint=True, normal_str=0.8)
    lowwall = pbr('cinderblock_low', 'concrete_block_wall', scale=0.55, tint=(0.22, 0.29, 0.21), coords='UV', paint=True, normal_str=0.8)
    floor = pbr('linoleum', 'old_linoleum_flooring_01', scale=0.6, rough_mul=0.7, rough_add=0.05, checker=(1 / 0.6 * 2, (0.78, 0.76, 0.64), (0.36, 0.38, 0.30)), normal_str=0.4)
    ceil = pbr('ceiling', 'ceiling_interior', scale=0.5, tint=(0.75, 0.75, 0.7))
    plane('floor', (8.4, 10.2), (0, -2.0, 0), (0, 0, 0), floor, 0.5)
    plane('ceiling', (8.4, 10.2), (0, -2.0, 3.6), (math.pi, 0, 0), ceil, 1.0)
    # walls: painted block, darker band below a chair rail
    for name, size, loc, rot in (('wall_back', (8.4, 3.6), (0, 2.9, 1.8), (math.pi / 2, 0, math.pi)),
                                 ('wall_left', (10.2, 3.6), (-4.2, -2.0, 1.8), (math.pi / 2, 0, -math.pi / 2)),
                                 ('wall_right_front', (5.4, 3.6), (4.2, -4.4, 1.8), (math.pi / 2, 0, math.pi / 2)),
                                 ('wall_right_back', (3.6, 3.6), (4.2, 1.1, 1.8), (math.pi / 2, 0, math.pi / 2)),
                                 ('wall_front', (8.4, 3.6), (0, -7.1, 1.8), (math.pi / 2, 0, 0))):
        o = plane(name, size, loc, rot, wall, 0.5)
        lo = plane(name + '_low', (size[0], 1.0), (loc[0], loc[1], 0.5), rot, lowwall, 0.5)
        n = o.matrix_world.to_3x3() @ Vector((0, 0, 1)); lo.location += n * 0.004
        # chair rail
        bpy.ops.mesh.primitive_cube_add(size=1, location=Vector((loc[0], loc[1], 1.0)) + n * 0.015)
        rl = bpy.context.active_object; rl.name = name + '_rail'
        rl.scale = (size[0] if abs(n.y) > 0.5 else 0.03, size[0] if abs(n.x) > 0.5 else 0.03, 0.06)
        rl.data.materials.append(props.mat('rail', (0.36, 0.25, 0.16), rough=0.45, coat=0.3))
    # over the doorway (the wall has a real opening for the exit door)
    plane('wall_right_lintel', (1.0, 1.5), (4.2, -1.2, 2.85), (math.pi / 2, 0, math.pi / 2), wall, 0.5)
    # a dim corridor beyond the door
    hall = props.mat('hall', (0.22, 0.24, 0.2), rough=0.8)
    for nm_, sz, lc, rt in (('hall_floor', (2.2, 1.6), (5.3, -1.2, 0.0), (0, 0, 0)), ('hall_ceil', (2.2, 1.6), (5.3, -1.2, 2.4), (math.pi, 0, 0)),
                            ('hall_side1', (2.2, 2.4), (5.3, -0.4, 1.2), (math.pi / 2, 0, math.pi)), ('hall_side2', (2.2, 2.4), (5.3, -2.0, 1.2), (math.pi / 2, 0, 0)),
                            ('hall_end', (1.6, 2.4), (6.4, -1.2, 1.2), (math.pi / 2, 0, math.pi / 2))):
        plane(nm_, sz, lc, rt, hall)
    hl = bpy.data.lights.new('hall_light', 'POINT'); hl.energy = 12; hl.color = (1.0, 0.85, 0.6); hl.shadow_soft_size = 0.2
    hlo = bpy.data.objects.new('hall_light', hl); C().objects.link(hlo); hlo.location = (5.6, -1.2, 2.2)
    # fluorescent fixtures: Poly Haven's mounted panel + a real area light under each
    S['tubes'] = []
    for i, (x, y) in enumerate(((-1.4, 0.6), (1.4, 0.6), (0.0, -1.6))):
        root, ms = assets.load('mounted_fluorescent_lights')
        root.location = (x, y, 3.6); root.rotation_euler = (0, 0, math.pi / 2); root.scale = (1.4, 1.4, 1.4)
        # its tube material glows
        em = props.mat(f'tube_glow{i}', (1, 1, 1), emit=(0.88, 1.0, 0.92), estr=14.0)
        for m in ms:
            if any(k in (m.active_material.name.lower() if m.active_material else '') for k in ('tube', 'light', 'emis', 'bulb', 'diffuser', 'glass')):
                m.data.materials.clear(); m.data.materials.append(em)
        ld = bpy.data.lights.new(f'tube{i}', 'AREA'); ld.shape = 'RECTANGLE'; ld.size = 1.2; ld.size_y = 0.5
        ld.energy = 150; ld.color = (0.84, 1.0, 0.86)
        lo = bpy.data.objects.new(f'tube{i}', ld); C().objects.link(lo); lo.location = (x, y, 3.53)
        S['tubes'].append(dict(light=lo, mat=em, base=150, ebase=10.0))
    # bounce/fill so shadows aren't black (the room is small and pale)
    fd = bpy.data.lights.new('fill', 'AREA'); fd.size = 6; fd.energy = 45; fd.color = (0.8, 0.95, 0.85)
    fo = bpy.data.objects.new('fill', fd); C().objects.link(fo); fo.location = (0, -4.5, 2.6); fo.rotation_euler = (math.radians(70), 0, 0)
    S['fill'] = fo
    # banner and the 12 steps poster
    def banner(im, d, w, h):
        d.rectangle((0, 0, w, h), fill=(242, 238, 226, 255)); d.rectangle((10, 10, w - 10, h - 10), outline=(190, 45, 45, 255), width=10)
        f = ImageFont.truetype(props.FONT_S, 120); s = 'ONE CANDLE AT A TIME'; tw = d.textlength(s, font=f)
        d.text(((w - tw) / 2, 58), s, font=f, fill=(30, 58, 140, 255))
    bm = printed('banner', text_tex(f'{TEX}/banner.png', 2048, 280, banner), 0.85)
    b = plane('banner', (2.6, 0.36), (0, 2.885, 2.72), (math.pi / 2, 0, math.pi), bm, flip=True); b.rotation_euler.y = 0.02
    def steps(im, d, w, h):
        d.rectangle((0, 0, w, h), fill=(240, 234, 216, 255))
        d.text((90, 50), 'THE 12 STEPS', font=ImageFont.truetype(props.FONT_S, 64), fill=(20, 20, 20, 255))
        f = ImageFont.truetype(props.FONT_S, 30)
        L = ['1. We admitted we were powerless', '    over memecoins.', '2. Came to believe a chart', '    could restore us to sanity.', '3. Turned off notifications.', '4. Turned them back on.',
             '5. Admitted it was a rug.', '6. Bought the rug.', '7. Humbly asked the dev', '    to stop selling.', '8. ...', '9. Never sold.', '10. Sold the bottom.', '11. Prayed.', '12. Aped.']
        for i, s in enumerate(L): d.text((48, 170 + i * 52), s, font=f, fill=(25, 25, 25, 255))
    plane('steps', (0.75, 1.03), (2.3, 2.885, 1.85), (math.pi / 2, 0, math.pi), printed('steps', text_tex(f'{TEX}/steps.png', 700, 960, steps)), flip=True)
    # window high on the left wall: night rain beyond
    def rainwin(im, d, w, h):
        d.rectangle((0, 0, w, h), fill=(8, 14, 26, 255))
        for i in range(160):
            x = R.uniform(0, w); y = R.uniform(-60, h); d.line((x, y, x - 4, y + R.uniform(30, 70)), fill=(120, 150, 190, 150), width=2)
        for i in range(40):
            x, y, r = R.uniform(0, w), R.uniform(0, h), R.uniform(3, 9); d.ellipse((x - r, y - r, x + r, y + r), fill=(140, 170, 210, 120))
    wm = emissive('window', text_tex(f'{TEX}/window.png', 512, 256, rainwin), 0.6)
    win = plane('window', (1.4, 0.7), (-4.19, 1.2, 2.85), (math.pi / 2, 0, -math.pi / 2), wm)
    S['window_map'] = wm
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-4.17, 1.2, 2.85)); wf = bpy.context.active_object; wf.scale = (0.06, 1.5, 0.8)
    so = wf.modifiers.new('hole', 'SOLIDIFY'); wf.data.materials.append(props.mat('wframe', (0.4, 0.42, 0.38), rough=0.5))
    bm2 = bmesh.new(); bm2.from_mesh(wf.data); bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if abs(f.normal.x) > 0.9], context='FACES'); bm2.to_mesh(wf.data); bm2.free()
    # the exit door (the stampede goes out of it), hinged at its back edge
    door_m = props.mat('door', (0.32, 0.2, 0.12), rough=0.42, coat=0.35)
    hinge = bpy.data.objects.new('door_hinge', None); C().objects.link(hinge); hinge.location = (4.17, -0.7, 0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.5, 1.05)); dr = bpy.context.active_object; dr.name = 'door'
    dr.scale = (0.05, 1.0, 2.1); dr.data.materials.append(door_m); dr.parent = hinge
    bv = dr.modifiers.new('bv', 'BEVEL'); bv.width = 0.008; bv.segments = 2
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.06, -0.85, 1.0)); bar = bpy.context.active_object; bar.scale = (0.04, 0.12, 0.03)
    bar.data.materials.append(props.mat('steel', (0.75, 0.75, 0.75), rough=0.2, metal=1.0)); bar.parent = hinge
    fm = props.mat('doorframe', (0.18, 0.16, 0.14), rough=0.5)
    for lc, sc_ in (((4.19, -0.66, 1.08), (0.08, 0.06, 2.16)), ((4.19, -1.74, 1.08), (0.08, 0.06, 2.16)), ((4.19, -1.2, 2.13), (0.08, 1.14, 0.06))):
        bpy.ops.mesh.primitive_cube_add(size=1, location=lc); fr = bpy.context.active_object; fr.scale = sc_; fr.data.materials.append(fm)
    # dark opening behind the door
    S['door'] = hinge
    def exit_sign(im, d, w, h):
        d.rectangle((0, 0, w, h), fill=(30, 8, 8, 255)); f = ImageFont.truetype(props.FONT_B, 150); tw = d.textlength('EXIT', font=f)
        d.text(((w - tw) / 2, 18), 'EXIT', font=f, fill=(255, 40, 40, 255))
    plane('exit_sign', (0.42, 0.16), (4.16, -1.2, 2.45), (math.pi / 2, 0, math.pi / 2), emissive('exit', text_tex(f'{TEX}/exit.png', 512, 200, exit_sign), 6.0), flip=True)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(4.18, -1.2, 2.45)); eb = bpy.context.active_object; eb.scale = (0.04, 0.46, 0.2); eb.data.materials.append(props.mat('signbox', (0.85, 0.85, 0.82), rough=0.4))
    el = bpy.data.lights.new('exit_glow', 'POINT'); el.energy = 6; el.color = (1, 0.1, 0.08); el.shadow_soft_size = 0.1
    elo = bpy.data.objects.new('exit_glow', el); C().objects.link(elo); elo.location = (4.0, -1.2, 2.35)
    # refreshment table: folding table, urn, donut box, foam cups, croissants
    top = props.mat('laminate', (0.82, 0.8, 0.74), rough=0.35, coat=0.2); steel = props.mat('tablesteel', (0.3, 0.3, 0.3), rough=0.35, metal=1.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.6, 2.35, 0.74)); tb = bpy.context.active_object; tb.scale = (1.8, 0.75, 0.035)
    tb.data.materials.append(top); tb.modifiers.new('bv', 'BEVEL').width = 0.01
    for dx in (-0.82, 0.82):
        for dy in (-0.3, 0.3):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.014, depth=0.72, location=(-2.6 + dx, 2.35 + dy, 0.36)); bpy.context.active_object.data.materials.append(steel)
    urn, _ = assets.load('modified_thermos'); urn.location = (-3.2, 2.45, 0.76); urn.scale = (1.9, 1.9, 1.9); urn.rotation_euler.z = 2.5
    jug, _ = assets.load('plastic_thermos'); jug.location = (-2.95, 2.25, 0.76); jug.rotation_euler.z = 0.6
    box, _ = assets.load('cardboard_box_01'); box.location = (-2.35, 2.42, 0.76); box.scale = (0.9, 0.62, 0.22); box.rotation_euler.z = 0.1
    dough = props.mat('dough', (0.55, 0.3, 0.12), rough=0.7); icing = props.mat('icing', (0.95, 0.5, 0.65), rough=0.25, coat=0.6)
    for i, (dx, dy, ic) in enumerate(((-0.08, -0.06, True), (0.06, 0.04, False), (0.0, 0.1, True))):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.022, location=(-2.35 + dx, 2.4 + dy, 0.845))
        dn = bpy.context.active_object; dn.data.materials.append(icing if ic else dough); dn.scale.z = 0.75
        for p in dn.data.polygons: p.use_smooth = True
    foam = props.mat('foam', (0.95, 0.95, 0.93), rough=0.6)
    for i in range(6):
        me = props.lathe(f'cup{i}', [(0.0, 0.0), (0.028, 0.0), (0.04, 0.1), (0.041, 0.104)], 32)
        me.materials.append(foam); cu = props.obj(f'cup{i}', me); cu.location = (-1.95 - (i % 3) * 0.1, 2.25 + (i // 3) * 0.1, 0.76 + (0.0 if i < 5 else 0.02))
    cro, _ = assets.load('croissant'); cro.location = (-2.15, 2.18, 0.765); cro.rotation_euler.z = 0.7
    # clock, fire extinguisher, plant, extra stacked chairs
    clk, cms = assets.load('wall_clock'); clk.location = (-1.9, 2.895, 2.45); clk.rotation_euler = (0, 0, 0)
    for m in cms:
        if 'hours' in m.name: m.rotation_euler.y += math.radians(90)
    ext, _ = assets.load('korean_fire_extinguisher_01'); ext.location = (4.0, 0.25, 0.0); ext.rotation_euler.z = math.pi / 2
    pl, _ = assets.load('potted_plant_02'); pl.location = (-3.7, -0.9, 0.0); pl.rotation_euler.z = 1.0
    alarm, _ = assets.load('fire_alarm'); alarm.location = (4.19, -0.2, 1.4); alarm.rotation_euler.z = -math.pi / 2
    for i in range(3):
        ch, _ = assets.load('SchoolChair_01'); ch.location = (3.3, 2.45, i * 0.12); ch.rotation_euler.z = math.pi + 0.05 * i
    # the circle of chairs
    S['seats'] = seats(); S['chairs'] = []
    for s in S['seats']:
        if len(S['chairs']) == 4:       # NEET's seat: a low wooden stool, fitted to his own sitting pose later
            ch, _ = assets.load('wooden_stool_01')
        else:
            ch, _ = assets.load('SchoolChair_01'); ch.scale = (CHAIR_S, CHAIR_S, CHAIR_S)
        piv = bpy.data.objects.new('chair_pivot', None); C().objects.link(piv)
        piv.location = (s['x'], s['y'], 0); piv.rotation_euler.z = s['face']; ch.parent = piv
        S['chairs'].append(dict(pivot=piv, chair=ch))
    return S


def exterior(ox=60.0):
    """The alley door, wet ground, neon sign, warm street light; rain is added by the director."""
    S = {}
    brick = pbr('brick', 'dark_brick_wall', scale=0.5, rough_add=0.0)
    wet = pbr('wet_asphalt', 'asphalt_02', scale=0.35, rough_mul=0.25, rough_add=0.02, tint=(0.5, 0.5, 0.52))
    plane('alley_wall', (12, 7), (ox, 1.0, 3.5), (math.pi / 2, 0, math.pi), brick, 0.5)
    plane('alley_ground', (12, 12), (ox, -4.0, 0), (0, 0, 0), wet, 0.5)
    plane('alley_side', (12, 7), (ox - 3.2, -3.0, 3.5), (math.pi / 2, 0, -math.pi / 2), brick, 0.5)
    dm = pbr('alley_door', 'rusty_painted_metal', scale=1.0, tint=(0.55, 0.6, 0.65))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox, 0.96, 1.1)); d = bpy.context.active_object; d.scale = (1.1, 0.07, 2.2); d.data.materials.append(dm)
    d.modifiers.new('bv', 'BEVEL').width = 0.01
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox, 0.99, 1.1)); fr = bpy.context.active_object; fr.scale = (1.24, 0.06, 2.3); fr.data.materials.append(props.mat('dframe', (0.12, 0.12, 0.13), rough=0.4, metal=0.6))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.14, location=(ox + 0.42, 0.9, 1.05), rotation=(0, math.pi / 2, 0))
    bpy.context.active_object.data.materials.append(props.mat('handle', (0.7, 0.7, 0.7), rough=0.2, metal=1.0))
    # neon sign: glowing glass tubes drawn as text, on a dark backing
    def neon(im, d, w, h):
        layer = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
        f1 = ImageFont.truetype(props.FONT_S, 190); f2 = ImageFont.truetype(props.FONT_B, 150); f3 = ImageFont.truetype(props.FONT_B, 64)
        for s, f, y, c in (('Degens', f1, 20, (255, 90, 200)), ('ANONYMOUS', f2, 250, (90, 235, 255)), ('MEETS NIGHTLY · 3 AM', f3, 450, (255, 90, 200))):
            tw = dl.textlength(s, font=f); dl.text(((w - tw) / 2, y), s, font=f, fill=(*c, 255))
        glow = layer.filter(ImageFilter.GaussianBlur(18)); im.alpha_composite(glow); im.alpha_composite(glow)
        core = layer.copy(); px = core.load()
        im.alpha_composite(layer)
    nm = emissive('neon', text_tex(f'{TEX}/neon.png', 1600, 560, neon), 9.0, alpha=True)
    plane('neon', (2.6, 0.91), (ox, 0.9, 2.9), (math.pi / 2, 0, math.pi), nm, flip=True)
    S['neon_mat'] = nm
    nl = bpy.data.lights.new('neon_light', 'AREA'); nl.size = 2.4; nl.size_y = 0.8; nl.shape = 'RECTANGLE'; nl.energy = 160; nl.color = (1.0, 0.45, 0.85)
    nlo = bpy.data.objects.new('neon_light', nl); C().objects.link(nlo); nlo.location = (ox, 0.75, 2.9); nlo.rotation_euler = (math.radians(-90), 0, 0)
    S['neon_light'] = nlo
    sl = bpy.data.lights.new('street', 'SPOT'); sl.energy = 1400; sl.color = (1.0, 0.66, 0.36); sl.spot_size = math.radians(70); sl.spot_blend = 0.6; sl.shadow_soft_size = 0.2
    slo = bpy.data.objects.new('street', sl); C().objects.link(slo); slo.location = (ox - 2.6, -3.0, 5.2)
    slo.rotation_euler = (Vector((ox, 0.0, 0.0)) - slo.location).to_track_quat('-Z', 'Y').to_euler()
    bl = bpy.data.lights.new('moon', 'AREA'); bl.size = 8; bl.energy = 120; bl.color = (0.45, 0.6, 1.0)
    blo = bpy.data.objects.new('moon', bl); C().objects.link(blo); blo.location = (ox + 3, -6, 6); blo.rotation_euler = (Vector((ox, 0, 0)) - blo.location).to_track_quat('-Z', 'Y').to_euler()
    return S


def rain(ox=60.0, n=2200):
    """Rain streaks: one mesh of thin quads, moved per frame by a geometry-nodes offset on scene time."""
    bm = bmesh.new(); rr = random.Random(11)
    for i in range(n):
        x = ox + rr.uniform(-3.0, 3.5); y = rr.uniform(-3.4, 0.9); z = rr.uniform(0, 6.0); L = rr.uniform(0.18, 0.32)
        a = bm.verts.new((x, y, z)); b = bm.verts.new((x + 0.004, y, z)); c = bm.verts.new((x + 0.004 - 0.03, y, z + L)); d = bm.verts.new((x - 0.03, y, z + L))
        bm.faces.new((a, b, c, d))
    me = bpy.data.meshes.new('rain'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('rain', me); C().objects.link(o)
    m = bpy.data.materials.new('rain'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.75, 0.82, 0.95, 1); b.inputs['Roughness'].default_value = 0.05
    b.inputs['Transmission Weight'].default_value = 0.6; b.inputs['Alpha'].default_value = 0.12
    b.inputs['Emission Color'].default_value = (0.6, 0.7, 0.9, 1); b.inputs['Emission Strength'].default_value = 0.08
    me.materials.append(m)
    # geometry nodes: z = ((z0 - t*9) mod 6)
    gn = o.modifiers.new('fall', 'NODES'); ng = bpy.data.node_groups.new('rainfall', 'GeometryNodeTree'); gn.node_group = ng
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry'); ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; L = ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput'); st = N.new('GeometryNodeSetPosition')
    pos = N.new('GeometryNodeInputPosition'); sep = N.new('ShaderNodeSeparateXYZ'); comb = N.new('ShaderNodeCombineXYZ')
    tm = N.new('GeometryNodeInputSceneTime'); mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 9.0
    # the whole streak (4 verts) must wrap together: wrap by the face's index-based phase instead of per-vertex z
    idx = N.new('GeometryNodeInputIndex'); div = N.new('ShaderNodeMath'); div.operation = 'FLOOR'; d4 = N.new('ShaderNodeMath'); d4.operation = 'DIVIDE'; d4.inputs[1].default_value = 4.0
    hsh = N.new('FunctionNodeRandomValue'); hsh.data_type = 'FLOAT'; hsh.inputs[2].default_value = 0.0; hsh.inputs[3].default_value = 6.0
    sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'
    md = N.new('ShaderNodeMath'); md.operation = 'FLOORED_MODULO'; md.inputs[1].default_value = 6.0
    base = N.new('ShaderNodeMath'); base.operation = 'SUBTRACT'
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'
    L.new(gi.outputs[0], st.inputs['Geometry']); L.new(st.outputs[0], go.inputs[0])
    L.new(idx.outputs[0], d4.inputs[0]); L.new(d4.outputs[0], div.inputs[0]); L.new(div.outputs[0], hsh.inputs['ID'])
    L.new(tm.outputs['Seconds'], mul.inputs[0])
    L.new(hsh.outputs[1], sub.inputs[0]); L.new(mul.outputs[0], sub.inputs[1]); L.new(sub.outputs[0], md.inputs[0])   # new bottom z of the streak
    L.new(pos.outputs[0], sep.inputs[0])
    # offset each vertex by (new_bottom - its own streak's original bottom); streak verts keep their shape relative to z0
    # (original bottoms are random in [0,6], so use z - floor-free trick: keep relative height = z - bottom_estimate)
    rel = N.new('ShaderNodeMath'); rel.operation = 'FLOORED_MODULO'; rel.inputs[1].default_value = 6.0
    L.new(sep.outputs['Z'], rel.inputs[0])
    L.new(sep.outputs['X'], comb.inputs['X']); L.new(sep.outputs['Y'], comb.inputs['Y'])
    # vertex height above its streak bottom: verts 2,3 are L above 0,1; approximate with (index mod 4 >= 2) * 0.25
    m4 = N.new('ShaderNodeMath'); m4.operation = 'FLOORED_MODULO'; m4.inputs[1].default_value = 4.0; L.new(idx.outputs[0], m4.inputs[0])
    ge = N.new('ShaderNodeMath'); ge.operation = 'GREATER_THAN'; ge.inputs[1].default_value = 1.5; L.new(m4.outputs[0], ge.inputs[0])
    h = N.new('ShaderNodeMath'); h.operation = 'MULTIPLY'; h.inputs[1].default_value = 0.26; L.new(ge.outputs[0], h.inputs[0])
    L.new(md.outputs[0], add.inputs[0]); L.new(h.outputs[0], add.inputs[1]); L.new(add.outputs[0], comb.inputs['Z'])
    L.new(comb.outputs[0], st.inputs['Position'])
    o.visible_shadow = False
    return o
