# An inflatable flamingo pool float, built properly: a metaball body (chest, wing bulges, raised tail) turned into a smooth
# mesh, an S-curved tapering neck, a head with a bent flamingo beak (pale base, black tip), eyes, raised seams, and a glossy
# clear-coated vinyl. Self-contained so it can be test-rendered on its own: build_flamingo(location) returns the root empty.
import bpy, math
from mathutils import Vector

def _vinyl(name, color, rough=0.16, coat=1.0, sheen=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    c = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    b.inputs["Base Color"].default_value = (*[x ** 2.2 for x in c], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.05
    b.inputs["Subsurface Weight"].default_value = 0.08; b.inputs["Subsurface Radius"].default_value = (0.3, 0.1, 0.1)
    # a faint mottling so the plastic isn't a flat colour: a little noise into roughness and a soft bump
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough * 0.7; mr.inputs["To Max"].default_value = rough * 1.6
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.04
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def _link(o, coll):
    coll.objects.link(o); return o

def _smooth(o, levels=2):
    for p in o.data.polygons: p.use_smooth = True
    sd = o.modifiers.new("smooth", "SUBSURF"); sd.levels = 1; sd.render_levels = levels
    return o

def _curve(name, pts, radius, taper, mat_, coll, res=24):
    """A tube along a smooth bezier through pts, its radius scaled per point (taper)."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 8
    cu.resolution_u = res; cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(pts) - 1)
    for bp, p, t in zip(sp.bezier_points, pts, taper):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"; bp.radius = t
    o = _link(bpy.data.objects.new(name, cu), coll); o.data.materials.append(mat_)
    return o

def build_flamingo(loc, coll=None, scale=1.0):
    coll = coll or bpy.context.scene.collection
    PINK = _vinyl("fl_vinyl", "#FF5C9E"); PINK_DK = _vinyl("fl_vinyl_dk", "#E8407F", rough=0.2)
    WHITE = _vinyl("fl_white", "#F7F1EC"); BLACK = _vinyl("fl_black", "#141214", rough=0.1)
    root = _link(bpy.data.objects.new("flamingo", None), coll); root.location = loc; root.scale = (scale,) * 3

    # the body: a sphere sculpted into an inflated bird: long and flat-bottomed, the chest full, the rear narrowing and
    # sweeping up into a tail, a soft wing bulge on each side
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=72, ring_count=36, location=(0, 0, 0))
    body = bpy.context.active_object; body.name = "fl_body"
    for v in body.data.vertices:
        x, y, z = v.co
        back = max(0.0, -x); front = max(0.0, x)
        X = 0.6 * x - 0.12 * back ** 2
        Y = 0.4 * y * (1 - 0.5 * back ** 2) * (1 - 0.15 * front ** 3)
        Z = 0.24 * z * (0.55 if z < 0 else 1.0) + 0.3 * back ** 3 * (1.0 if z > -0.3 else 0.6) + 0.05 * front ** 2
        wing = math.exp(-((x + 0.1) / 0.45) ** 2) * max(0.0, abs(y) - 0.55) * max(0.0, z + 0.2)
        Y += math.copysign(0.07 * wing, y); Z += 0.05 * wing
        v.co = (X, Y, Z)
    body.data.materials.append(PINK); _smooth(body, 1); body.parent = root
    # the welded seam round the middle of the float
    bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.012, major_segments=96, minor_segments=8, location=(0, 0, -0.005))
    seam = bpy.context.active_object; seam.scale = (1.16, 0.775, 1); seam.data.materials.append(PINK_DK); seam.parent = root
    for p in seam.data.polygons: p.use_smooth = True
    # wing feather ridges: three soft tubes on each wing
    for sy in (1, -1):
        for k in range(3):
            y = sy * (0.2 + 0.035 * k)
            _curve("fl_feather", [Vector((0.2 - 0.04 * k, y, 0.17 - 0.015 * k)), Vector((-0.05, y * 1.12, 0.2 - 0.015 * k)), Vector((-0.32 + 0.03 * k, y * 1.05, 0.16 - 0.015 * k))],
                   0.018, (0.4, 1.0, 0.3), PINK_DK, coll).parent = root

    # the neck: an S-curve up from the chest, thicker at the base
    neck = _curve("fl_neck", [Vector((0.42, 0, 0.12)), Vector((0.56, 0, 0.42)), Vector((0.46, 0, 0.72)), Vector((0.5, 0, 0.92)), Vector((0.62, 0, 1.0))],
                  0.075, (1.35, 1.0, 0.92, 0.88, 0.9), PINK, coll)
    neck.parent = root
    # the head: an egg, tipped forward
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, segments=32, ring_count=16, location=(0.66, 0, 1.03))
    head = bpy.context.active_object; head.name = "fl_head"; head.scale = (1.25, 0.9, 0.95); head.rotation_euler = (0, math.radians(-12), 0)
    head.data.materials.append(PINK); _smooth(head, 1); head.parent = root
    # the beak: thick and pale where it meets the face, bending sharply down halfway, a black hooked tip
    _curve("fl_beak", [Vector((0.76, 0, 1.03)), Vector((0.86, 0, 1.02)), Vector((0.92, 0, 0.96))], 0.05, (0.95, 0.62, 0.38), WHITE, coll).parent = root
    _curve("fl_beak_tip", [Vector((0.915, 0, 0.97)), Vector((0.95, 0, 0.91)), Vector((0.94, 0, 0.86))], 0.05, (0.4, 0.27, 0.06), BLACK, coll).parent = root
    # eyes: a white disc, a black pupil, a highlight
    for sy in (1, -1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, segments=16, ring_count=8, location=(0.7, sy * 0.094, 1.06))
        e = bpy.context.active_object; e.scale = (1, 0.45, 1); e.data.materials.append(WHITE); e.parent = root
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.017, segments=16, ring_count=8, location=(0.712, sy * 0.106, 1.062))
        p_ = bpy.context.active_object; p_.scale = (1, 0.45, 1); p_.data.materials.append(BLACK); p_.parent = root
        for o in (e, p_):
            for pl in o.data.polygons: pl.use_smooth = True
    # the inflation valve on its back
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.03, vertices=24, location=(-0.2, 0.0, 0.215))
    v = bpy.context.active_object; v.data.materials.append(WHITE); v.parent = root
    return root

if __name__ == "__main__":   # test render: blender -b --factory-startup -P flamingo.py -- out.png
    import sys
    out = sys.argv[sys.argv.index("--") + 1]
    sc = bpy.context.scene
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    build_flamingo((0, 0, 0.25))
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0)); w = bpy.context.active_object
    wm = bpy.data.materials.new("water"); wm.use_nodes = True; wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.25, 0.45, 1)
    w.data.materials.append(wm)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (2.2, -2.4, 1.3); cam.rotation_euler = (Vector((0.15, 0, 0.55)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    for loc, e in (((3, -3, 4), 900), ((-3, 2, 3), 400)):
        L = bpy.data.objects.new("L", bpy.data.lights.new("L", "AREA")); L.data.energy = e; L.data.size = 2; L.location = loc
        L.rotation_euler = (Vector((0, 0, 0.4)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); sc.collection.objects.link(L)
    sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True; sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.3
    sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.render.resolution_x, sc.render.resolution_y = 640, 480
    sc.view_settings.view_transform = "AgX"; sc.render.filepath = out; bpy.ops.render.render(write_still=True)
