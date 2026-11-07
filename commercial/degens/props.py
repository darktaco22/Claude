"""Hand props and wardrobe extras, modelled to real-world sizes with PBR materials.
Every prop's origin is its grip point (see GRIP), so the director places them from the palm."""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import assets

TEX = os.environ.get('DA_TEX', '/tmp')
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_S = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'


def coll():
    return bpy.context.scene.collection


def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0, image=None, alpha=None, trans=0.0, ior=1.45):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Coat Weight'].default_value = coat
    b.inputs['Transmission Weight'].default_value = trans; b.inputs['IOR'].default_value = ior
    if image:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(image); nt.links.new(t.outputs[0], b.inputs['Base Color'])
        if alpha: nt.links.new(t.outputs[1], b.inputs['Alpha'])
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = estr
    return m


def obj(name, me, m=None, parent=None):
    o = bpy.data.objects.new(name, me); coll().objects.link(o)
    if m: o.data.materials.append(m)
    if parent: o.parent = parent
    return o


def lathe(name, prof, segs=48, cap_bottom=True):
    """A surface of revolution about Z from a list of (r, z) points (open at the top)."""
    bm = bmesh.new(); rings = []
    for r, z in prof:
        ring = [bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in [i * 2 * math.pi / segs for i in range(segs)]]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
    if cap_bottom and prof[0][0] > 0:
        bm.faces.new(list(reversed(rings[0])))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    # cylindrical UVs (u around, v up)
    uv = me.uv_layers.new(); zs = [z for _, z in prof]; z0, z1 = min(zs), max(zs)
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            u = (math.atan2(v.y, v.x) / (2 * math.pi)) % 1.0
            uv.data[li].uv = (u, (v.z - z0) / max(1e-6, z1 - z0))
    # fix the seam
    for p in me.polygons:
        us = [uv.data[li].uv.x for li in p.loop_indices]
        if max(us) - min(us) > 0.5:
            for li in p.loop_indices:
                if uv.data[li].uv.x < 0.5: uv.data[li].uv.x += 1.0
    return me


def label(path, w, h, draw):
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im); draw(im, d, w, h); im.save(path); return path


# ------------------------------------------------------------------ mugs
def mug(name, color, text=None):
    """Ceramic mug, 8.4 cm wide, 9.6 cm tall. Origin: centre of the body (where the hand wraps)."""
    R, H, t = 0.042, 0.096, 0.0045
    prof = [(0.0, 0.0), (R - 0.006, 0.0), (R - 0.001, 0.002), (R, 0.008), (R, H - 0.003), (R - 0.0015, H), (R - t, H), (R - t, H - 0.004), (R - t, 0.012), (0.0, 0.010)]
    me = lathe(name, prof, 64, cap_bottom=False)
    if text:
        def dr(im, d, w, h):
            d.rectangle((0, 0, w, h), fill=(245, 242, 236))
            f = ImageFont.truetype(FONT_S, 92)
            for i, line in enumerate(text):
                tw = d.textlength(line, font=f); d.text((w * 0.25 - tw / 2, 170 + i * 120), line, fill=(196, 38, 92), font=f)
            for x, y in ((w * 0.25 - 300, 120), (w * 0.25 + 280, 430)):
                d.ellipse((x - 22, y - 22, x + 22, y + 22), fill=(196, 38, 92))
        img = label(f'{TEX}/{name}_decal.png', 2048, 640, dr)
        m = mat(name + '_ceramic', rough=0.18, coat=0.6, image=img)
    else:
        m = mat(name + '_ceramic', color, rough=0.2, coat=0.6)
    inner = mat(name + '_inside', (0.93, 0.92, 0.9), rough=0.15, coat=0.5)
    me.materials.append(m); me.materials.append(inner)
    for p in me.polygons:
        c = sum((me.vertices[v].co for v in p.vertices), Vector()) / len(p.vertices)
        if Vector((c.x, c.y)).length < R - t * 0.5 or c.z > H - 0.001: p.material_index = 1
    o = obj(name, me)
    o.modifiers.new('solid', 'SUBSURF').levels = 1
    # handle: a bent tube on the +X side
    bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.0055, major_segments=40, minor_segments=14, location=(R + 0.008, 0, H * 0.52), rotation=(math.pi / 2, 0, 0))
    hnd = bpy.context.active_object; hnd.name = name + '_handle'; hnd.scale = (0.75, 1.0, 1.0)
    bm = bmesh.new(); bm.from_mesh(hnd.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < -0.012], context='VERTS'); bm.to_mesh(hnd.data); bm.free()
    for p in hnd.data.polygons: p.use_smooth = True
    hnd.data.materials.append(m); hnd.parent = o
    for c in hnd.users_collection: c.objects.unlink(hnd)
    coll().objects.link(hnd)
    # origin: body centre
    o.data.transform(Matrix.Translation((0, 0, -H * 0.45))); hnd.location.z -= H * 0.45
    o['H'] = H; o['R'] = R
    return o


def can(name):
    """A 500 ml energy-drink can (6.6 cm x 16.8 cm), brushed aluminium with a printed sleeve."""
    R, H = 0.033, 0.168
    prof = [(0.0, 0.0), (0.024, 0.0), (0.03, 0.004), (R, 0.012), (R, H - 0.016), (0.029, H - 0.006), (0.0265, H - 0.002), (0.0265, H), (0.0, H - 0.003)]
    me = lathe(name, prof, 64)
    def dr(im, d, w, h):
        for y in range(h):
            g = int(18 + 10 * math.sin(y / h * math.pi)); d.line((0, y, w, y), fill=(g, g, g + 2))
        f = ImageFont.truetype(FONT_B, 210); fs = ImageFont.truetype(FONT_B, 70)
        for cx in (w * 0.22, w * 0.72):
            d.text((cx - 260, h * 0.30), 'VOLT', font=f, fill=(140, 255, 40))
            d.text((cx - 250, h * 0.62), 'MAX CHARGE', font=fs, fill=(235, 235, 235))
        for x in range(0, w, 60): d.line((x, h * 0.9, x + 40, h * 0.82), fill=(140, 255, 40), width=8)
    img = label(f'{TEX}/{name}_label.png', 2048, 1024, dr)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img)
    rr = nt.nodes.new('ShaderNodeMapRange'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); uvn = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(t.outputs[0], b.inputs['Base Color']); b.inputs['Metallic'].default_value = 0.85; b.inputs['Roughness'].default_value = 0.28
    b.inputs['Coat Weight'].default_value = 0.5
    me.materials.append(m)
    alu = mat(name + '_alu', (0.8, 0.8, 0.82), rough=0.22, metal=1.0); me.materials.append(alu)
    for p in me.polygons:
        c = sum((me.vertices[v].co for v in p.vertices), Vector()) / len(p.vertices)
        if c.z < 0.013 or c.z > H - 0.017: p.material_index = 1
    o = obj(name, me); o.data.transform(Matrix.Translation((0, 0, -H * 0.42)))
    o['H'] = H; o['R'] = R
    return o


def phone(name, screen_img):
    """A 7.2 x 15 x 0.8 cm phone. Origin: centre of the back. Screen faces +Z, top is +Y."""
    W, Hh, D = 0.072, 0.150, 0.0082
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.active_object; o.name = name
    o.scale = (W, Hh, D); bpy.ops.object.transform_apply(scale=True)
    o.data.transform(Matrix.Translation((0, 0, D / 2)))
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0075; bv.segments = 6; bv.limit_method = 'ANGLE'
    for p in o.data.polygons: p.use_smooth = True
    o.data.materials.append(mat(name + '_body', (0.02, 0.02, 0.025), rough=0.3, metal=0.6, coat=0.8))
    for c in o.users_collection: c.objects.unlink(o)
    coll().objects.link(o)
    # the screen: an emissive plane just above the glass
    bpy.ops.mesh.primitive_plane_add(size=1); s = bpy.context.active_object; s.name = name + '_screen'
    s.scale = (W - 0.006, Hh - 0.008, 1); bpy.ops.object.transform_apply(scale=True)
    s.location = (0, 0, D + 0.0004); s.parent = o
    sm = bpy.data.materials.new(name + '_screen'); sm.use_nodes = True; nt = sm.node_tree
    b = nt.nodes['Principled BSDF']; t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(screen_img)
    b.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1); b.inputs['Roughness'].default_value = 0.05; b.inputs['Coat Weight'].default_value = 1.0
    nt.links.new(t.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 0.0
    s.data.materials.append(sm)
    for c in s.users_collection: c.objects.unlink(s)
    coll().objects.link(s)
    # light the face from the screen
    ld = bpy.data.lights.new(name + '_glow', 'AREA'); ld.shape = 'RECTANGLE'; ld.size = W; ld.size_y = Hh; ld.color = (0.75, 0.85, 1.0); ld.energy = 0
    lo = bpy.data.objects.new(name + '_glow', ld); coll().objects.link(lo); lo.parent = o; lo.location = (0, 0, D + 0.01); lo.rotation_euler = (math.pi, 0, 0)
    o['screen_mat'] = sm.name; o['glow'] = lo.name
    return o


def cigarette(name, ph):
    """Poly Haven's cigarette (filter + paper), with a burnt tip: ash cone, glowing ember ring.
    Origin: middle of the filter (tan end). Lit, ashy paper end along +Z."""
    root, ms = assets.load('cigarette_pack')
    cig = [m for m in ms if m.name.endswith('_cigarette')][0]
    bpy.context.view_layer.update(); sc0 = cig.matrix_world.to_scale()
    keep = cig.copy(); keep.data = cig.data.copy(); coll().objects.link(keep)
    bpy.data.objects.remove(root)
    for m in ms: bpy.data.objects.remove(m)
    keep.name = name; keep.parent = None
    keep.data.transform(Matrix.Diagonal((*sc0, 1))); keep.matrix_world = Matrix()
    me0 = keep.data
    # which end is the filter? sample the cigarette's own texture near each end: the filter is tan
    img = next((n.image for m in me0.materials for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
    zs = [v.co.z for v in me0.vertices]; za, zb = min(zs), max(zs)
    def end_colour(near_low):
        if img is None: return 0.0
        w, h = img.size; px = img.pixels[:]; uv = me0.uv_layers.active.data; acc = []; 
        for poly in me0.polygons:
            for li in poly.loop_indices:
                z = me0.vertices[me0.loops[li].vertex_index].co.z
                if (z - za < 0.006) if near_low else (zb - z < 0.006):
                    u, v = uv[li].uv; x = min(w - 1, int((u % 1) * w)); y = min(h - 1, int((v % 1) * h)); k = (y * w + x) * 4
                    acc.append(px[k] - px[k + 2])          # red minus blue: high for tan/orange
        return sum(acc) / max(1, len(acc))
    low_tan, high_tan = end_colour(True), end_colour(False)
    if high_tan > low_tan:
        me0.transform(Matrix.Rotation(math.pi, 4, 'X'))          # put the filter at the low end
    print('CIGARETTE filter tint low/high end', round(low_tan, 3), round(high_tan, 3), '-> flipped' if high_tan > low_tan else '')
    bb = [v.co for v in me0.vertices]; z0 = min(v.z for v in bb); z1 = max(v.z for v in bb)
    cx = (min(v.x for v in bb) + max(v.x for v in bb)) / 2; cy = (min(v.y for v in bb) + max(v.y for v in bb)) / 2
    L = z1 - z0; r = (max(v.x for v in bb) - min(v.x for v in bb)) / 2
    me0.transform(Matrix.Translation((-cx, -cy, -z0 - 0.011)))    # filter middle at the origin, centred
    zt = L - 0.011
    ember = mat(name + '_ember', (0.05, 0.01, 0.0), rough=0.9, emit=(1.0, 0.25, 0.02), estr=6.0)
    ash = mat(name + '_ash', (0.32, 0.31, 0.3), rough=0.95)
    burn = mat(name + '_burnt', (0.08, 0.05, 0.03), rough=0.9)
    me = lathe(name + '_tip', [(r * 1.002, 0), (r * 1.004, 0.0015), (r * 0.96, 0.003), (r * 0.82, 0.0055), (r * 0.6, 0.0075), (0.0, 0.0085)], 32, False)
    me.materials.append(burn); me.materials.append(ember); me.materials.append(ash)
    for p in me.polygons:
        z = sum(me.vertices[v].co.z for v in p.vertices) / len(p.vertices)
        p.material_index = 0 if z < 0.0012 else (1 if z < 0.0035 else 2)
    tip = obj(name + '_tip', me, parent=keep); tip.location = (0, 0, zt - 0.001)
    keep['ember'] = ember.name; keep['tip_z'] = zt + 0.006
    return keep


def oxygen(name):
    """A green medical oxygen cylinder on a little two-wheel cart."""
    root = bpy.data.objects.new(name, None); coll().objects.link(root)
    green = mat(name + '_paint', (0.07, 0.26, 0.11), rough=0.35, coat=0.4)
    steel = mat(name + '_steel', (0.7, 0.7, 0.72), rough=0.25, metal=1.0)
    blk = mat(name + '_rubber', (0.02, 0.02, 0.02), rough=0.8)
    me = lathe(name + '_cyl', [(0.0, 0.05), (0.05, 0.05), (0.054, 0.06), (0.054, 0.56), (0.05, 0.6), (0.03, 0.625), (0.016, 0.63), (0.016, 0.65), (0.0, 0.65)], 48)
    me.materials.append(green); obj(name + '_cyl', me, parent=root)
    vm = lathe(name + '_valve', [(0.0, 0.65), (0.014, 0.65), (0.014, 0.69), (0.022, 0.69), (0.022, 0.7), (0.0, 0.7)], 24)
    vm.materials.append(steel); obj(name + '_valve', vm, parent=root)
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.025, location=(sx * 0.07, 0.03, 0.045), rotation=(0, math.pi / 2, 0))
        w = bpy.context.active_object; w.data.materials.append(blk); w.parent = root
    bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=0.62, location=(0, 0.07, 0.33)); fr = bpy.context.active_object; fr.data.materials.append(steel); fr.parent = root
    bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=0.18, location=(0, 0.04, 0.64), rotation=(math.pi / 2, 0, 0)); h = bpy.context.active_object; h.data.materials.append(steel); h.parent = root
    for o in root.children:
        for p in o.data.polygons: p.use_smooth = True
    return root


def tube_curve(name, pts, r=0.0022, m=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.resolution_u = 12
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu); coll().objects.link(o)
    if m: cu.materials.append(m)
    return o


def cap(name, color=(0.30, 0.02, 0.025)):
    """A ribbed knit beanie with a folded cuff. Origin: centre of the head opening."""
    root = bpy.data.objects.new(name, None); coll().objects.link(root)
    m = bpy.data.materials.new(name + '_knit'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = 0.95
    b.inputs['Sheen Weight'].default_value = 0.6; b.inputs['Sheen Roughness'].default_value = 0.6
    tc = nt.nodes.new('ShaderNodeTexCoord')
    # vertical ribs: bands around the head (angle in the XY plane), plus a fine knit noise
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
    at = nt.nodes.new('ShaderNodeMath'); at.operation = 'ARCTAN2'; nt.links.new(sep.outputs['Y'], at.inputs[0]); nt.links.new(sep.outputs['X'], at.inputs[1])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 60.0; nt.links.new(at.outputs[0], mul.inputs[0])
    sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'; nt.links.new(mul.outputs[0], sn.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900; nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.35
    nt.links.new(nz.outputs['Fac'], ad.inputs[0]); nt.links.new(sn.outputs[0], ad.inputs[2])
    bmp = nt.nodes.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.35; bmp.inputs['Distance'].default_value = 0.002
    nt.links.new(ad.outputs[0], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], b.inputs['Normal'])
    dk = nt.nodes.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.inputs['Factor'].default_value = 0.25
    dk.inputs[6].default_value = (*color, 1); dk.inputs[7].default_value = (color[0] * 0.5, color[1] * 0.5, color[2] * 0.5, 1)
    mr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(sn.outputs[0], mr.inputs['Value']); mr.inputs['From Min'].default_value = -1
    nt.links.new(mr.outputs[0], dk.inputs['Factor']); nt.links.new(dk.outputs[2], b.inputs['Base Color'])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1)
    cr = bpy.context.active_object; cr.name = name + '_crown'
    bm = bmesh.new(); bm.from_mesh(cr.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02], context='VERTS'); bm.to_mesh(cr.data); bm.free()
    cr.scale = (0.098, 0.112, 0.085); bpy.ops.object.transform_apply(scale=True)
    so = cr.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.005; so.offset = 1
    cr.modifiers.new('sub', 'SUBSURF').levels = 1
    cr.data.materials.append(m); cr.parent = root
    for p in cr.data.polygons: p.use_smooth = True
    # the folded cuff: a slightly thicker band round the rim
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=1, end_fill_type='NOTHING')
    cf = bpy.context.active_object; cf.name = name + '_cuff'
    cf.scale = (0.098 * 1.06, 0.112 * 1.06, 0.034); bpy.ops.object.transform_apply(scale=True)
    cf.location = (0, 0, 0.013)
    so = cf.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.006; so.offset = 0
    bv = cf.modifiers.new('bv', 'BEVEL'); bv.width = 0.002; bv.segments = 3
    cf.modifiers.new('sub', 'SUBSURF').levels = 1
    cf.data.materials.append(m); cf.parent = root
    for p in cf.data.polygons: p.use_smooth = True
    for o in [cr, cf]:
        for c in o.users_collection: c.objects.unlink(o)
        coll().objects.link(o)
    return root


def straw(name, length=0.24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.0035, depth=length, location=(0, 0, 0))
    s = bpy.context.active_object; s.name = name
    s.data.transform(Matrix.Translation((0, 0, length / 2)))   # origin at the bottom end
    so = s.modifiers.new('wall', 'SOLIDIFY'); so.thickness = 0.0006
    s.data.materials.append(mat(name, (1.0, 0.25, 0.55), rough=0.25, coat=0.6))
    for c in s.users_collection: c.objects.unlink(s)
    coll().objects.link(s)
    return s
