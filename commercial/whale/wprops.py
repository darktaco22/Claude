"""Props for LAST WILL & TESTAMENT: martini, crystal decanter and tumbler, cigar, vape, hip flask, the will,
phones with their screens, the heart monitor (a scrolling ECG drawn from the story's heartbeat), a clerical
collar tab and a mourning veil. Origins are chosen for gripping: cylinders at their grip centre, axis +Z."""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from props import mat, obj, coll
import props as _p


def lathe(name, prof, segs=48, cap_bottom=True):
    return obj(name, _p.lathe(name, prof, segs, cap_bottom))

TEX = lambda: os.environ.get('DA_TEX', '/tmp')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'


def glass_mat(name, tint=(0.95, 0.97, 1.0)):
    return mat(name, tint, rough=0.02, trans=1.0, ior=1.5)


def liquid_mat(name, col, ior=1.34):
    m = mat(name, col, rough=0.05, trans=0.92, ior=ior)
    m.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.9
    return m


def martini(name):
    """Coupe-style martini glass, held by the stem. Origin at the middle of the stem."""
    prof = [(0.0, -0.065), (0.036, -0.065), (0.036, -0.061), (0.006, -0.058), (0.0035, -0.05), (0.0035, 0.04),
            (0.006, 0.048), (0.056, 0.105), (0.057, 0.107), (0.0, 0.107)]
    g = lathe(name, prof, segs=48); g.data.materials.append(glass_mat(name + '_glass'))
    # the drink: a shallow cone of gin, and an olive on a pick
    liq = lathe(name + '_gin', [(0.0, 0.052), (0.0045, 0.052), (0.049, 0.097), (0.0, 0.097)], segs=40)
    liq.data.materials.append(liquid_mat(name + '_ginm', (0.96, 0.97, 0.9))); liq.parent = g
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.009, location=(0.012, 0, 0.083)); ol = bpy.context.active_object
    ol.name = name + '_olive'; ol.scale = (1, 1, 1.25); ol.data.materials.append(mat(name + '_olivem', (0.18, 0.28, 0.04), rough=0.35)); ol.parent = g
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0012, depth=0.09, location=(0.02, 0, 0.1), rotation=(0, math.radians(-25), 0)); pk = bpy.context.active_object
    pk.name = name + '_pick'; pk.data.materials.append(mat(name + '_pickm', (0.7, 0.05, 0.05), rough=0.4)); pk.parent = g
    for o in (g, liq, ol, pk):
        for p in o.data.polygons: p.use_smooth = True
    g['R'] = 0.0035; g['z0'] = -0.03; g['z1'] = 0.03; g['rim'] = 0.107; g['rim_r'] = 0.056
    return g


def decanter(name):
    """A square-shouldered crystal decanter of scotch, stopper out, held by the neck."""
    prof = [(0.0, -0.25), (0.062, -0.25), (0.068, -0.24), (0.07, -0.12), (0.06, -0.085), (0.022, -0.05), (0.016, -0.035),
            (0.016, 0.07), (0.021, 0.075), (0.021, 0.081), (0.013, 0.081), (0.013, -0.04), (0.06, -0.1), (0.06, -0.24), (0.0, -0.24)]
    d = lathe(name, prof, segs=8); d.data.materials.append(glass_mat(name + '_glass'))      # 8 sides: cut crystal
    liq = lathe(name + '_scotch', [(0.0, -0.238), (0.058, -0.238), (0.058, -0.145), (0.0, -0.145)], segs=8)
    liq.data.materials.append(liquid_mat(name + '_scotchm', (0.62, 0.28, 0.05))); liq.parent = d
    d['R'] = 0.017; d['z0'] = 0.005; d['z1'] = 0.055; d['lip'] = 0.081
    return d


def tumbler(name, fill=0.4):
    t = lathe(name, [(0.0, 0.0), (0.04, 0.0), (0.042, 0.095), (0.039, 0.095), (0.037, 0.012), (0.0, 0.012)], segs=8)
    t.data.materials.append(glass_mat(name + '_glass'))
    l = lathe(name + '_liq', [(0.0, 0.013), (0.036, 0.013), (0.037, 0.013 + 0.08 * fill), (0.0, 0.013 + 0.08 * fill)], segs=8)
    l.data.materials.append(liquid_mat(name + '_liqm', (0.62, 0.28, 0.05))); l.parent = t
    return t


def leaf_mat(name):
    """Cigar wrapper leaf: brown, veined (noise), slightly oily."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 60; n.inputs['Detail'].default_value = 8
    w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = 25; w.wave_type = 'BANDS'; w.inputs['Distortion'].default_value = 6
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.11, 0.05, 0.022, 1); cr.color_ramp.elements[1].color = (0.27, 0.13, 0.055, 1)
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'
    nt.links.new(n.outputs['Fac'], mx.inputs[0]); nt.links.new(w.outputs['Fac'], mx.inputs[1]); nt.links.new(mx.outputs[0], cr.inputs[0])
    nt.links.new(cr.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.55
    bm = nt.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = 0.25; nt.links.new(mx.outputs[0], bm.inputs['Height']); nt.links.new(bm.outputs[0], b.inputs['Normal'])
    return m


def cigar(name):
    """A Churchill cigar: 15 cm, 18 mm thick. Origin at the mouth end, +Z toward the lit end.
    Gold band near the mouth, grey ash and a glowing ember at the tip."""
    L, r = 0.15, 0.0088
    body = lathe(name, [(0.0, 0.0), (r * 0.82, 0.0), (r, 0.012), (r, L - 0.012), (r * 0.97, L - 0.004), (0.0, L - 0.004)], segs=24)
    body.data.materials.append(leaf_mat(name + '_leaf'))
    band = lathe(name + '_band', [(r + 0.0004, 0.022), (r + 0.0004, 0.036)], segs=24, cap_bottom=False)
    band.data.materials.append(mat(name + '_bandm', (0.75, 0.55, 0.12), rough=0.25, metal=0.8)); band.parent = body
    ash = lathe(name + '_ash', [(0.0, L - 0.005), (r * 0.98, L - 0.005), (r * 0.9, L + 0.012), (0.0, L + 0.014)], segs=24)
    ash.data.materials.append(mat(name + '_ashm', (0.42, 0.41, 0.4), rough=0.95)); ash.parent = body
    em = lathe(name + '_ember', [(0.0, L - 0.0065), (r * 0.99, L - 0.0065), (r * 0.99, L - 0.0035), (0.0, L - 0.0035)], segs=24)
    emm = mat(name + '_emberm', (0.9, 0.25, 0.04), rough=0.6, emit=(1.0, 0.32, 0.05), estr=3.0); em.data.materials.append(emm); em.parent = body
    for o in (body, band, ash, em):
        for p in o.data.polygons: p.use_smooth = True
    body['R'] = r; body['L'] = L; body['ember'] = emm.name
    return body


def vape(name):
    """A slim pod vape: matte black body, smoked mouthpiece, an LED. Origin mid-body, +Z toward the mouthpiece."""
    v = lathe(name, [(0.0, -0.05), (0.0075, -0.05), (0.0078, -0.045), (0.0078, 0.04), (0.005, 0.05), (0.0035, 0.062), (0.0, 0.062)], segs=24)
    v.data.materials.append(mat(name + '_m', (0.02, 0.02, 0.025), rough=0.35, metal=0.6))
    led = lathe(name + '_led', [(0.0079, -0.03), (0.0079, -0.026)], segs=24, cap_bottom=False)
    lm = mat(name + '_ledm', (0.1, 0.4, 1.0), emit=(0.2, 0.5, 1.0), estr=0.0); led.data.materials.append(lm); led.parent = v
    v['R'] = 0.0078; v['tip'] = 0.062; v['led'] = lm.name
    return v


def flask(name):
    """A curved steel hip flask (11 x 9 x 2.2 cm), held flat like a phone. Origin at its centre, +Y toward the cap."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.09, v.co.y * 0.115, v.co.z * 0.022))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = obj(name, me, mat(name + '_steel', (0.75, 0.75, 0.77), rough=0.18, metal=1.0))
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.009; bv.segments = 6
    sd = o.modifiers.new('sub', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
    cap = lathe(name + '_cap', [(0.0, 0.0), (0.011, 0.0), (0.011, 0.016), (0.0, 0.016)], segs=24)
    cap.data.materials.append(o.data.materials[0]); cap.parent = o; cap.rotation_euler = (-math.pi / 2, 0, 0); cap.location = (0, 0.0575, 0)
    for p in o.data.polygons: p.use_smooth = True
    o['W'], o['L'], o['D'] = 0.09, 0.115, 0.022
    return o


def will_paper(name):
    """The will: a few stapled pages in a blue legal back, printed LAST WILL AND TESTAMENT. Origin at its centre."""
    W, Hh = 0.216, 0.279
    path = f'{TEX()}/{name}.png'; im = Image.new('RGB', (864, 1116), (236, 232, 222)); d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(SERIF, 46); f2 = ImageFont.truetype(FONT_R, 20)
    d.text((432, 110), 'LAST WILL', font=f1, fill=(20, 20, 20), anchor='mm'); d.text((432, 165), 'AND TESTAMENT', font=f1, fill=(20, 20, 20), anchor='mm')
    rr = random.Random(2)
    for y in range(250, 1050, 30):
        x = 90
        while x < 770:
            wl = rr.randint(25, 95); d.rectangle([x, y, min(x + wl, 774), y + 9], fill=(70, 70, 70)); x += wl + 12
    d.line([(520, 1000), (760, 1000)], fill=(30, 30, 30), width=2); im.save(path)
    m = bpy.data.materials.new(name + '_print'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(path); nt.links.new(tx.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.85
    b.inputs['Subsurface Weight'].default_value = 0.1
    bpy.ops.mesh.primitive_plane_add(size=1); p = bpy.context.active_object; p.name = name; p.scale = (W, Hh, 1); bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(m)
    sl = p.modifiers.new('solid', 'SOLIDIFY'); sl.thickness = 0.002
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.004, -0.0025)); bk = bpy.context.active_object; bk.name = name + '_back'
    bk.scale = (W + 0.004, Hh + 0.012, 1); bpy.ops.object.transform_apply(scale=True, location=False)
    bk.data.materials.append(mat(name + '_blue', (0.12, 0.2, 0.45), rough=0.7)); bk.parent = p
    p['W'], p['H'] = W, Hh
    return p


def collar(name):
    """The white tab of a clerical collar, set in the black shirt's neckband."""
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.active_object; o.name = name
    o.scale = (0.022, 0.003, 0.016); bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat(name + '_m', (0.92, 0.92, 0.9), rough=0.45))
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = 0.0012; bv.segments = 2
    return o


def veil(name):
    """A black pillbox hat with a short birdcage net veil (sheer, so the eyes read through it)."""
    hat = lathe(name, [(0.0, 0.0), (0.045, 0.0), (0.047, 0.004), (0.047, 0.034), (0.044, 0.038), (0.0, 0.038)], segs=40)
    hat.data.materials.append(mat(name + '_felt', (0.012, 0.012, 0.014), rough=0.75))
    # net: a curved sheet of a fine diamond mesh texture, alpha-masked
    path = f'{TEX()}/{name}_net.png'; im = Image.new('RGBA', (512, 512), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(-512, 1024, 18):
        d.line([(i, 0), (i + 512, 512)], fill=(10, 10, 10, 255), width=2); d.line([(i, 512), (i + 512, 0)], fill=(10, 10, 10, 255), width=2)
    im.save(path)
    m = bpy.data.materials.new(name + '_netm'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(path)
    nt.links.new(tx.outputs[0], b.inputs['Base Color']); nt.links.new(tx.outputs[1], b.inputs['Alpha']); b.inputs['Roughness'].default_value = 0.8
    m.blend_method = 'HASHED' if hasattr(m, 'blend_method') else None
    bm = bmesh.new(); nu, nv = 24, 10; R = 0.13
    V = [[bm.verts.new((R * math.sin(a), -R * math.cos(a) * 0.95 + 0.02, -0.11 * j / nv)) for a in np.linspace(-1.25, 1.25, nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu): bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    me = bpy.data.meshes.new(name + '_net'); bm.to_mesh(me); bm.free()
    net = obj(name + '_net', me, m); net.parent = hat; net.hide_render = True    # the hat alone reads better
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (math.atan2(v.x, -v.y) * 2.0, v.z * 6.0)
    net.visible_shadow = False
    return hat


def screen_img(path, kind):
    """Phone screens: the Whale's exchange app (SELL ALL), and everyone else's dump alert."""
    W, Hh = 540, 1140; im = Image.new('RGB', (W, Hh), (8, 10, 14)); d = ImageDraw.Draw(im)
    fb = lambda s: ImageFont.truetype(FONT, s); fr = lambda s: ImageFont.truetype(FONT_R, s)
    if kind == 'sell':
        d.text((40, 70), '$WHALE', font=fb(56), fill=(240, 240, 240)); d.text((40, 140), 'Your position: 81% of supply', font=fr(26), fill=(150, 160, 175))
        pts = []; rr = random.Random(4); y = 640.0
        for i in range(60):
            y -= rr.uniform(-6, 9); pts.append((40 + i * 7.7, y))
        d.line(pts, fill=(40, 220, 120), width=5)
        d.text((40, 220), '+4,180%', font=fb(64), fill=(40, 220, 120))
        d.rounded_rectangle([40, 860, 500, 1000], radius=26, fill=(225, 40, 50)); d.text((270, 930), 'SELL ALL', font=fb(64), fill=(255, 255, 255), anchor='mm')
    else:
        d.rounded_rectangle([24, 120, 516, 470], radius=28, fill=(26, 28, 34))
        d.text((52, 150), 'WHALE ALERT', font=fb(32), fill=(255, 80, 80)); d.text((52, 205), '$WHALE  -99.7%', font=fb(48), fill=(255, 255, 255))
        d.text((52, 280), 'Dev wallet sold 81% of supply', font=fr(26), fill=(190, 195, 205)); d.text((52, 320), 'Liquidity removed. 3:07 AM', font=fr(26), fill=(190, 195, 205))
        pts = [(52 + i * 7.5, 440 - (30 if i < 40 else 30 - (i - 40) * 4.5)) for i in range(60)]
        d.line([(x, max(y, 360)) for x, y in pts], fill=(255, 70, 70), width=4)
        d.text((270, 40), '3:07', font=fb(60), fill=(230, 230, 235), anchor='mm')
    im.save(path); return path


def ecg_strip(path, beats, total, px_per_s=180, H=200):
    """The whole night's heartbeat as one long trace (x = time): beats is a list of beat times; after the last
    beat of `beats` before `flat_from` the line is flat. Scrolled on the monitor by a mapping offset."""
    W = int(total * px_per_s) + 4; im = Image.new('RGB', (W, H), (0, 0, 0)); d = ImageDraw.Draw(im)
    def qrs(u):          # one beat's shape over u in [0, 0.6] s
        return (0.12 * math.exp(-((u - 0.08) / 0.03) ** 2) - 0.15 * math.exp(-((u - 0.17) / 0.008) ** 2)
                + 1.0 * math.exp(-((u - 0.2) / 0.011) ** 2) - 0.25 * math.exp(-((u - 0.225) / 0.01) ** 2) + 0.25 * math.exp(-((u - 0.42) / 0.05) ** 2))
    ys = []
    bt = sorted(beats)
    for x in range(W):
        t = x / px_per_s; v = 0.0
        for b in bt:
            if b - 0.25 <= t <= b + 0.45: v += qrs(t - b + 0.2)
        ys.append(H * 0.62 - v * H * 0.42)
    d.line([(x, y) for x, y in enumerate(ys)], fill=(60, 255, 120), width=3)
    im = im.filter(ImageFilter.GaussianBlur(0.8)); im.save(path); return path


def monitor(name, strip, total, px_per_s=180):
    """A bedside patient monitor on a rolling pole. Its screen shows a 3 s window of the ECG strip, scrolled by
    the material's mapping (keyed per frame). Origin at the floor under the pole."""
    root = bpy.data.objects.new(name, None); coll().objects.link(root)
    metal = mat(name + '_metal', (0.6, 0.6, 0.62), rough=0.3, metal=1.0); plastic = mat(name + '_plastic', (0.82, 0.82, 0.8), rough=0.4)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=1.25, location=(0, 0, 0.66)); pole = bpy.context.active_object; pole.name = name + '_pole'; pole.data.materials.append(metal); pole.parent = root
    for a in range(5):
        ang = a * 2 * math.pi / 5
        bpy.ops.mesh.primitive_cube_add(size=1, location=(math.cos(ang) * 0.15, math.sin(ang) * 0.15, 0.05), rotation=(0, 0, ang))
        leg = bpy.context.active_object; leg.scale = (0.3, 0.025, 0.02); leg.data.materials.append(metal); leg.parent = root
        bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.018, location=(math.cos(ang) * 0.29, math.sin(ang) * 0.29, 0.02), rotation=(math.pi / 2, 0, ang))
        w = bpy.context.active_object; w.data.materials.append(mat(name + '_wheel', (0.05, 0.05, 0.05), rough=0.6)); w.parent = root
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.36)); body = bpy.context.active_object; body.name = name + '_body'
    body.scale = (0.32, 0.12, 0.24); bpy.ops.object.transform_apply(scale=True); body.data.materials.append(plastic); body.parent = root
    bv = body.modifiers.new('b', 'BEVEL'); bv.width = 0.012; bv.segments = 3
    # screen: emissive, the strip scrolled through a mapping node (location x keyed)
    m = bpy.data.materials.new(name + '_screen'); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.name = 'scroll'
    win_s = 3.0; mp.inputs['Scale'].default_value = (win_s / total, 1, 1)
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(strip); tx.extension = 'CLIP'; tx.interpolation = 'Cubic'
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], tx.inputs['Vector'])
    # a faint grid and a dark-green panel behind the trace
    gr = nt.nodes.new('ShaderNodeTexBrick'); gr.inputs['Scale'].default_value = 1.0
    em = nt.nodes.new('ShaderNodeEmission'); em.name = 'em'; em.inputs['Strength'].default_value = 2.5
    add = nt.nodes.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'; add.inputs['Factor'].default_value = 1.0
    add.inputs[6].default_value = (0.004, 0.02, 0.012, 1); nt.links.new(tx.outputs[0], add.inputs[7])
    nt.links.new(add.outputs[2], em.inputs['Color']); nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.0605, 1.375), rotation=(math.pi / 2, 0, 0)); scr = bpy.context.active_object
    scr.name = name + '_scr'; scr.scale = (0.26, 0.15, 1); bpy.ops.object.transform_apply(scale=True); scr.data.materials.append(m); scr.parent = root
    # heart-rate digits as a separate small emissive plane (texture swapped by keyed mix)
    root['screen_mat'] = m.name; root['win_s'] = win_s
    return root
