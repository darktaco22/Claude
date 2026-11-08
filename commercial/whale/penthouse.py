"""The set: the Whale's penthouse bedroom at 3 AM. Gothic four-poster, wainscot and jacquard wallpaper, a tall
rain-streaked window over the city, velvet drapes, a heart monitor on a stand, decanter and crystal on the
nightstand. Blender axes: Z up, the bed's head toward +Y, the camera mostly looks toward +Y."""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix, Euler
import assets
from room import pbr, plane, emissive, text_tex

PH = os.environ.get('PH', '')
C = lambda: bpy.context.scene.collection
BED = Vector((0.0, 0.2, 0.0))                 # bed origin (its head end is at +Y)
WALL_Y = 1.27; X0, X1 = -3.4, 3.4; FRONT_Y = -5.0; CEIL = 3.3
WIN = (-3.05, -1.35, 0.55, 2.9)               # window x0, x1, z0, z1 in the back wall


def flat(name, rgb, rough=0.5, metal=0.0, emit=None, alpha=None, transmission=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit[0], 1); b.inputs['Emission Strength'].default_value = emit[1]
    if alpha is not None: b.inputs['Alpha'].default_value = alpha
    if transmission: b.inputs['Transmission Weight'].default_value = transmission
    return m


def box(name, lo, hi, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[(a + b) / 2 for a, b in zip(lo, hi)])
    o = bpy.context.active_object; o.name = name; o.scale = [b - a for a, b in zip(lo, hi)]
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.cube_project(cube_size=1.0); bpy.ops.object.mode_set(mode='OBJECT')
    return o


def wall_with_hole(name, y, x0, x1, z0, z1, hole, m_paper, m_panel, rail_z=1.02):
    """The back wall: wallpaper above a wood wainscot, a rectangular hole for the window."""
    hx0, hx1, hz0, hz1 = hole
    pieces = [(x0, hx0, 0, z1), (hx1, x1, 0, z1), (hx0, hx1, 0, hz0), (hx0, hx1, hz1, z1)]
    for i, (a, b, c, d) in enumerate(pieces):
        for (lo, hi, m, off) in ((max(c, 0), min(d, rail_z), m_panel, 0.012), (max(c, rail_z), d, m_paper, 0.0)):
            if hi - lo < 1e-3: continue
            o = plane(f'{name}_{i}_{"p" if m is m_panel else "w"}', ((b - a), (hi - lo)), ((a + b) / 2, y - off, (lo + hi) / 2), (math.pi / 2, 0, math.pi), m, uv_scale=0.6)
    # chair rail
    box(f'{name}_rail', (x0, y - 0.04, rail_z - 0.03), (x1, y, rail_z + 0.03), m_panel)


def side_wall(name, x, y0, y1, m_paper, m_panel, sign, rail_z=1.02):
    rot = (math.pi / 2, 0, -sign * math.pi / 2)
    plane(f'{name}_w', (y1 - y0, CEIL - rail_z), (x, (y0 + y1) / 2, (CEIL + rail_z) / 2), rot, m_paper, uv_scale=0.6)
    plane(f'{name}_p', (y1 - y0, rail_z), (x + sign * 0.012, (y0 + y1) / 2, rail_z / 2), rot, m_panel, uv_scale=0.6)
    box(f'{name}_rail', (min(x, x + sign * 0.04), y0, rail_z - 0.03), (max(x, x + sign * 0.04), y1, rail_z + 0.03), m_panel)


def window():
    """Frame, mullions, glass with a faint film, and a backdrop: the night city (Poly Haven HDRI) is the world."""
    x0, x1, z0, z1 = WIN; wood = flat('win_wood', (0.05, 0.03, 0.02), 0.45)
    t = 0.07
    box('win_l', (x0 - t, WALL_Y - 0.05, z0 - t), (x0, WALL_Y + 0.12, z1 + t), wood)
    box('win_r', (x1, WALL_Y - 0.05, z0 - t), (x1 + t, WALL_Y + 0.12, z1 + t), wood)
    box('win_b', (x0 - t, WALL_Y - 0.12, z0 - t), (x1 + t, WALL_Y + 0.12, z0), wood)     # sill sticks out into the room
    box('win_t', (x0 - t, WALL_Y - 0.05, z1), (x1 + t, WALL_Y + 0.12, z1 + t), wood)
    xm = (x0 + x1) / 2
    box('win_mv', (xm - 0.025, WALL_Y + 0.02, z0), (xm + 0.025, WALL_Y + 0.08, z1), wood)
    for zz in (z0 + (z1 - z0) / 3, z0 + 2 * (z1 - z0) / 3):
        box('win_mh', (x0, WALL_Y + 0.02, zz - 0.02), (x1, WALL_Y + 0.08, zz + 0.02), wood)
    # thin pane: see-through plus a Fresnel reflection (a single refractive sheet renders as a slab)
    g = bpy.data.materials.new('glass'); g.use_nodes = True; nt = g.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); gl_ = nt.nodes.new('ShaderNodeBsdfGlossy'); gl_.inputs['Roughness'].default_value = 0.03
    fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5; mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fr.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl_.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes['Material Output'].inputs[0])
    gl = plane('win_glass', (x1 - x0, z1 - z0), (xm, WALL_Y + 0.1, (z0 + z1) / 2), (math.pi / 2, 0, 0), g)
    gl.visible_shadow = False
    return gl


def drapes(m):
    """Heavy velvet drapes either side of the window: a pleated sheet (sinusoidal folds), slightly swept back."""
    x0, x1, z0, z1 = WIN; out = []
    for side, xc in (('l', x0 - 0.18), ('r', x1 + 0.18)):
        bm = bmesh.new(); W = 0.62; H = CEIL - 0.1; nx, nz = 40, 30
        vs = [[bm.verts.new((xc - W / 2 + W * i / nx, WALL_Y - 0.14 - 0.045 * math.sin(i / nx * 2 * math.pi * 5.5), H * j / nz)) for i in range(nx + 1)] for j in range(nz + 1)]
        for j in range(nz):
            for i in range(nx): bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
        me = bpy.data.meshes.new('drape_' + side); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('drape_' + side, me); C().objects.link(o); me.materials.append(m)
        uv = me.uv_layers.new()
        for poly in me.polygons:
            for li in poly.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (v.x * 1.5, v.z * 1.5)
        s = o.modifiers.new('solid', 'SOLIDIFY'); s.thickness = 0.02
        sm = o.modifiers.new('sub', 'SUBSURF'); sm.levels = 1; sm.render_levels = 1
        for p in me.polygons: p.use_smooth = True
        out.append(o)
    rod = flat('rod', (0.55, 0.42, 0.18), 0.3, 1.0)
    box('drape_rod', (x0 - 0.55, WALL_Y - 0.2, CEIL - 0.13), (x1 + 0.55, WALL_Y - 0.17, CEIL - 0.1), rod)
    return out


def rain_outside(n=3500):
    """Rain falling past the window outside (same geometry-nodes fall as the Degens alley)."""
    import room
    x0, x1, z0, z1 = WIN
    o = room.rain(ox=0.0, n=n)
    # remap the streaks into a slab just outside the window
    rr = random.Random(5); me = o.data
    for f in range(0, len(me.vertices), 4):
        cx = rr.uniform(x0 - 1.0, x1 + 1.0); cy = rr.uniform(WALL_Y + 0.4, WALL_Y + 6.0)
        bx = me.vertices[f].co.x; by = me.vertices[f].co.y
        for k in range(4):
            v = me.vertices[f + k]; v.co.x = cx + (v.co.x - bx); v.co.y = cy
    return o


def droplets_on_glass(n=260):
    """Beads and runs of water on the pane: tiny refractive bumps, a few drawn into streaks."""
    x0, x1, z0, z1 = WIN; rr = random.Random(9)
    bm = bmesh.new()
    for i in range(n):
        x = rr.uniform(x0 + 0.03, x1 - 0.03); z = rr.uniform(z0 + 0.03, z1 - 0.03); r = rr.uniform(0.002, 0.006)
        L = r if rr.random() < 0.75 else rr.uniform(0.03, 0.14)
        res = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0)
        for v in res['verts']: v.co = Vector((x + v.co.x * r, WALL_Y + 0.085 + abs(v.co.y) * r * 0.6 * -1, z + v.co.z * (L if v.co.z < 0 else r)))
    me = bpy.data.meshes.new('drops'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('drops', me); C().objects.link(o)
    w = flat('water', (1, 1, 1), 0.02, transmission=1.0); w.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value = 1.33
    me.materials.append(w); o.visible_shadow = False
    for p in me.polygons: p.use_smooth = True
    return o


def place(aid, loc, rot_z=0.0, scale=1.0):
    r, ms = assets.load(aid); r.location = loc; r.rotation_euler = (0, 0, math.radians(rot_z)); r.scale = (scale,) * 3
    return r


def build():
    paper = pbr('wallpaper', 'quatrefoil_jacquard_fabric', scale=1.0, tint=(0.30, 0.42, 0.34), rough_add=0.15)
    panel = pbr('wainscot', 'dark_paneled_wood', scale=1.0, tint=(0.55, 0.42, 0.33))
    floor = pbr('parquet', 'herringbone_parquet', scale=1.0, tint=(0.62, 0.48, 0.38), rough_mul=1.0, rough_add=0.28)
    plane('floor', (X1 - X0, WALL_Y - FRONT_Y), ((X0 + X1) / 2, (WALL_Y + FRONT_Y) / 2, 0), (0, 0, 0), floor, uv_scale=0.45)
    ceil = flat('ceiling', (0.12, 0.11, 0.10), 0.85)
    plane('ceiling', (X1 - X0, WALL_Y - FRONT_Y), ((X0 + X1) / 2, (WALL_Y + FRONT_Y) / 2, CEIL), (math.pi, 0, 0), ceil)
    wall_with_hole('back', WALL_Y, X0, X1, 0, CEIL, WIN, paper, panel)
    side_wall('left', X0, FRONT_Y, WALL_Y, paper, panel, +1)
    side_wall('right', X1, FRONT_Y, WALL_Y, paper, panel, -1)
    plane('front', (X1 - X0, CEIL), ((X0 + X1) / 2, FRONT_Y, CEIL / 2), (math.pi / 2, 0, 0), paper, uv_scale=0.6)
    # crown moulding
    for (lo, hi) in (((X0, WALL_Y - 0.08, CEIL - 0.1), (X1, WALL_Y, CEIL)),):
        box('crown', lo, hi, panel)
    S = {}
    S['bed'] = place('GothicBed_01', BED)
    S['nightstand'] = place('ClassicNightstand_01', (-1.12, 0.92, 0), 0)
    S['clock'] = place('vintage_grandfather_clock_01', (2.75, 0.98, 0), 0)
    S['cabinet'] = place('GothicCabinet_01', (X0 + 0.5, -1.6, 0), -90)
    S['armchair'] = place('ArmChair_01', (2.1, -1.9, 0), 140)
    S['plant'] = place('potted_plant_01', (X1 - 0.45, -3.6, 0), 0)
    S['mirror'] = place('ornate_mirror_01', (1.75, WALL_Y - 0.01, 1.85), 0, 1.4)
    S['picture'] = place('fancy_picture_frame_01', (X0 + 0.02, 0.0, 1.85), 90, 1.6)
    S['drapes'] = drapes(pbr('velvet', 'velour_velvet', scale=2.0, tint=(0.42, 0.06, 0.08)))
    S['glass'] = window(); S['drops'] = droplets_on_glass(); S['rain'] = rain_outside()
    world()
    return S


def skyline_img(path, W=3072, Hh=1536, seed=3):
    """A night skyline seen from high up: towers across the street with lit windows, a hazy rainy sky."""
    from PIL import Image, ImageDraw, ImageFilter
    rr = random.Random(seed); im = Image.new('RGB', (W, Hh)); d = ImageDraw.Draw(im)
    for y in range(Hh):                                   # sky: deep blue-grey, lighter (city glow) near the horizon
        k = y / Hh; d.line([(0, y), (W, y)], fill=(int(10 + 28 * k ** 2), int(13 + 30 * k ** 2), int(22 + 40 * k ** 2)))
    for layer, (n, hmin, hmax, wmin, wmax, base, lit, win) in enumerate((
            (40, 0.25, 0.55, 60, 160, (14, 16, 22), 0.25, 9), (26, 0.35, 0.8, 110, 260, (9, 10, 14), 0.35, 14), (9, 0.55, 1.0, 260, 520, (5, 6, 9), 0.45, 22))):
        for i in range(n):
            bw = rr.randint(wmin, wmax); bx = rr.randint(-bw // 2, W - bw // 2); bh = int(Hh * rr.uniform(hmin, hmax)); top = Hh - bh
            d.rectangle([bx, top, bx + bw, Hh], fill=base)
            for wy in range(top + win, Hh, int(win * 1.6)):
                for wx in range(bx + win // 2, bx + bw - win // 2, int(win * 1.4)):
                    if rr.random() < lit:
                        c = rr.choice([(255, 196, 120), (255, 214, 160), (190, 210, 255), (255, 180, 90)]); f = rr.uniform(0.35, 1.0)
                        d.rectangle([wx, wy, wx + int(win * 0.7), wy + int(win * 0.9)], fill=tuple(int(x * f) for x in c))
            if rr.random() < 0.5: d.ellipse([bx + bw // 2 - 4, top - 4, bx + bw // 2 + 4, top + 4], fill=(255, 40, 30))   # aircraft beacon
    im = im.filter(ImageFilter.GaussianBlur(2.2)); im.save(path); return path


def world():
    """Very dim blue night ambience; the city itself is an emissive backdrop outside the window."""
    w = bpy.data.worlds.new('night'); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.012, 0.016, 0.03, 1); bg.inputs['Strength'].default_value = 1.0
    x0, x1, z0, z1 = WIN
    tex = os.environ.get('DA_TEX', '/tmp')
    img = skyline_img(f'{tex}/skyline.png')
    m = emissive('skyline', img, strength=1.6)
    o = plane('skyline', (34, 17), ((x0 + x1) / 2 + 2, WALL_Y + 22, 2.0), (math.pi / 2, 0, 0), m)
    o.visible_shadow = False; o.visible_diffuse = False; o.visible_glossy = True
    return w


def duvet(samples, x0=-0.7, x1=0.7, y0=-0.78, y1=0.30, base=0.47, n=(56, 64), clearance=0.035, top_z=None):
    """A thick duvet draped over the Whale: a height field above the highest point of his body under every
    grid cell over all sampled frames (so it can never cut into him), smoothed like cloth, hemmed with a skirt
    that falls over the bed's sides and foot. samples: Nx3 world points of his body over the clip schedule."""
    nx, ny = n; xs = np.linspace(x0, x1, nx); ys = np.linspace(y0, y1, ny)
    H = np.full((ny, nx), base)
    P = np.asarray(samples); P = P[P[:, 2] < (top_z if top_z else 9)]
    ix = np.clip(np.round((P[:, 0] - x0) / (x1 - x0) * (nx - 1)).astype(int), 0, nx - 1)
    iy = np.clip(np.round((P[:, 1] - y0) / (y1 - y0) * (ny - 1)).astype(int), 0, ny - 1)
    inside = (P[:, 0] > x0 - 0.02) & (P[:, 0] < x1 + 0.02) & (P[:, 1] > y0 - 0.02) & (P[:, 1] < y1 + 0.02)
    np.maximum.at(H, (iy[inside], ix[inside]), P[inside, 2] + clearance)
    # cloth: dilate (the duvet bridges over hollows) then a gentle blur, never dropping below the support
    from scipy.ndimage import grey_dilation, gaussian_filter
    sup = grey_dilation(H, size=(5, 5)); Hs = gaussian_filter(sup, 2.2); Hs = np.maximum(Hs, H)
    Hs = gaussian_filter(Hs, 1.0); Hs = np.maximum(Hs, H)
    bm = bmesh.new(); V = [[bm.verts.new((xs[i], ys[j], Hs[j, i])) for i in range(nx)] for j in range(ny)]
    for j in range(ny - 1):
        for i in range(nx - 1): bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    # skirt: the edge rows fall over the sides and the foot of the mattress, with a soft roll
    def skirt(edge, outward):
        prev = edge
        for k, (d, dz) in enumerate(((0.04, -0.04), (0.07, -0.1), (0.08, -0.2), (0.085, -0.3))):
            row = [bm.verts.new((v.co.x + outward[0] * d, v.co.y + outward[1] * d, min(v.co.z, base) + dz)) for v in edge]
            for a in range(len(row) - 1): bm.faces.new((prev[a], prev[a + 1], row[a + 1], row[a]))
            prev = row
    skirt([V[j][0] for j in range(ny)], (-1, 0)); skirt([V[j][nx - 1] for j in range(ny)], (1, 0)); skirt([V[0][i] for i in range(nx)], (0, -1))
    # a folded-back top hem across the chest
    me = bpy.data.meshes.new('duvet'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('duvet', me); C().objects.link(o)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (v.x * 1.2, v.y * 1.2 + v.z)
    s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.03; s.offset = -1
    m = pbr('duvet_velvet', 'velour_velvet', scale=3.0, tint=(0.36, 0.05, 0.07))
    me.materials.append(m)
    return o
