"""THE MEMETRIX II: the new sets (burning café, the Whale's white room) and the rooftop rain.
Builds on episode 1's helpers (../memetrix/mxsets.py) and keeps its conventions: one collection per set, lights in L_<SET>,
atmosphere objects tagged cine_ignore so the camera solver looks through them.
"""
import glob
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'memetrix'))
import mxsets  # noqa: E402
from mxsets import box, cylinder, dust, haze, light, material, plane, screen, sphere  # noqa: E402

_new_collection = mxsets.collection
SET_COLLECTIONS = ('FLOOR', 'BASEMENT', 'DOJO', 'ROOFTOP', 'CAFE', 'WHITE', 'PROPS')


def collection(name):
    """A set's (or a set's light) collection: the existing one if there is one. mxsets.collection always made a new one, so
    later dressing went into BASEMENT.001 and the like, and lights added later (the couch lamp, the lightning) landed in
    L_BASEMENT.001 / L_ROOFTOP.001, which the renderer never switches off with their set."""
    if name in SET_COLLECTIONS or name.startswith('L_'):
        c = bpy.data.collections.get(name)
        if c is not None:
            return c
    return _new_collection(name)


mxsets.collection = collection

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


def fire_material(name, seed=0.0, shape='flame'):
    """Volumetric fire: climbing 4D noise, cut off with height and toward the edges, emitting orange to yellow by its heat.
    (Object coordinates of the unit cube; a first blackbody version came out almost black.)"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    tc = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])            # x, y, z in -0.5..0.5
    off = N('ShaderNodeVectorMath'); off.operation = 'ADD'
    _drive(off.inputs[1], 'default_value', '-frame * 0.07', index=2)                  # the flame climbs
    L(tc.outputs['Object'], off.inputs[0])
    noise = N('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 8.0; noise.inputs['Detail'].default_value = 10.0; noise.inputs['Roughness'].default_value = 0.72
    noise.inputs['Distortion'].default_value = 1.4                                     # licking, ragged tongues
    _drive(noise.inputs['W'], 'default_value', f'frame / 10 + {seed}')
    stretch = N('ShaderNodeVectorMath'); stretch.operation = 'MULTIPLY'                 # flames are tall tongues, not blobs:
    stretch.inputs[1].default_value = (1.0, 1.0, 0.4) if shape != 'sheet' else (1.0, 1.0, 0.6)   # squash the noise in z
    L(off.outputs[0], stretch.inputs[0])
    L(stretch.outputs[0], noise.inputs['Vector'])
    # falloff: 1 low in the middle, 0 at the top and the sides. 'flame': a full body that narrows only near the top (the
    # first version, (0.5 - z) * (1 - 2r), was a narrow cone: small pointed tongues). 'sheet': fire spread over a surface
    # (walls, ceiling): fades only at the box's edges, so it reads as a burning surface, not a jet.
    def rng_(src, a, b):
        m = N('ShaderNodeMapRange'); m.clamp = True
        m.inputs['From Min'].default_value = a; m.inputs['From Max'].default_value = b
        L(src, m.inputs['Value'])
        return m.outputs['Result']

    def mul_(a, b):
        m = N('ShaderNodeMath'); m.operation = 'MULTIPLY'; L(a, m.inputs[0]); L(b, m.inputs[1])
        return m.outputs[0]
    ax = N('ShaderNodeMath'); ax.operation = 'ABSOLUTE'; L(sep.outputs['X'], ax.inputs[0])
    ay = N('ShaderNodeMath'); ay.operation = 'ABSOLUTE'; L(sep.outputs['Y'], ay.inputs[0])
    if shape == 'sheet':
        fall = mul_(mul_(rng_(ax.outputs[0], 0.5, 0.25), rng_(ay.outputs[0], 0.5, 0.25)),
                    mul_(rng_(sep.outputs['Z'], 0.5, 0.1), rng_(sep.outputs['Z'], -0.5, -0.3)))
    else:
        xy = N('ShaderNodeCombineXYZ'); L(sep.outputs['X'], xy.inputs['X']); L(sep.outputs['Y'], xy.inputs['Y'])
        rad = N('ShaderNodeVectorMath'); rad.operation = 'LENGTH'; L(xy.outputs[0], rad.inputs[0])
        width = N('ShaderNodeMath'); width.operation = 'MULTIPLY_ADD'                 # the body narrows with height:
        width.inputs[1].default_value = -0.3; width.inputs[2].default_value = 0.35       # 0.5 wide at the base, 0.2 at the top
        L(sep.outputs['Z'], width.inputs[0])
        rr = N('ShaderNodeMath'); rr.operation = 'DIVIDE'; L(rad.outputs[1], rr.inputs[0]); L(width.outputs[0], rr.inputs[1])
        side = rng_(rr.outputs[0], 1.0, 0.6)
        fall = mul_(side, rng_(sep.outputs['Z'], 0.5, 0.0))
    # heat = noise * falloff, sharpened into tongues
    con = N('ShaderNodeMapRange'); con.clamp = True                       # fractal noise hugs 0.5: stretch it, or the
    con.inputs['From Min'].default_value = 0.32; con.inputs['From Max'].default_value = 0.68   # flame is just the smooth falloff
    L(noise.outputs['Fac'], con.inputs['Value'])
    heat = N('ShaderNodeMath'); heat.operation = 'MULTIPLY'; L(con.outputs['Result'], heat.inputs[0]); L(fall, heat.inputs[1])
    tongue = N('ShaderNodeMapRange'); tongue.clamp = True
    lo_, hi_ = (0.4, 0.75) if shape == 'sheet' else (0.2, 0.6)        # (a sheet burns only on the noise peaks: tongues)
    tongue.inputs['From Min'].default_value = lo_; tongue.inputs['From Max'].default_value = hi_
    L(heat.outputs[0], tongue.inputs['Value'])
    ramp = N('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (0.35, 0.015, 0.0, 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (1.0, 0.6, 0.15, 1)
    mid = ramp.color_ramp.elements.new(0.5); mid.color = (1.0, 0.16, 0.0, 1)   # deep orange: bright emission goes pale under AgX
    L(tongue.outputs['Result'], ramp.inputs['Fac'])
    strength = N('ShaderNodeMath'); strength.operation = 'MULTIPLY'; strength.inputs[1].default_value = 6.5
    L(tongue.outputs['Result'], strength.inputs[0])
    dens = N('ShaderNodeMath'); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 5.0   # sooty edges
    L(tongue.outputs['Result'], dens.inputs[0])
    vol = N('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.08, 0.05, 0.03, 1)
    L(dens.outputs[0], vol.inputs['Density'])
    L(ramp.outputs['Color'], vol.inputs['Emission Color'])
    L(strength.outputs[0], vol.inputs['Emission Strength'])
    out = N('ShaderNodeOutputMaterial'); L(vol.outputs[0], out.inputs['Volume'])
    return mat


def smoke_material(name, seed=0.0, density=0.6, shape='column', col=(0.32, 0.29, 0.26)):   # grey: it catches the firelight
    """Rising smoke: climbing noise, shaped so the volume never shows the box it lives in (the first version had hard
    straight edges at the bottom of the ceiling layer and the sides of every column).
    shape 'column': fades in above the fire, thins to nothing at the top and toward the sides.
    shape 'layer': a ceiling layer, full at the top, feathering out over its lower 70 %."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    tc = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])
    off = N('ShaderNodeVectorMath'); off.operation = 'ADD'
    _drive(off.inputs[1], 'default_value', f'-frame * {0.012 if shape == "layer" else 0.02}', index=2)
    L(tc.outputs['Object'], off.inputs[0])
    noise = N('ShaderNodeTexNoise')
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 4.5
    noise.inputs['Detail'].default_value = 7.0
    noise.inputs['Roughness'].default_value = 0.62
    noise.inputs['Distortion'].default_value = 0.9                  # wisps and curls, not a soft blob
    _drive(noise.inputs['W'], 'default_value', f'frame / 40 + {seed}')
    st_ = N('ShaderNodeVectorMath'); st_.operation = 'MULTIPLY'
    st_.inputs[1].default_value = (1.0, 1.0, 0.55) if shape == 'column' else (0.6, 0.6, 1.0)   # rising columns / spreading layer
    L(off.outputs[0], st_.inputs[0])
    L(st_.outputs[0], noise.inputs['Vector'])
    cut = N('ShaderNodeMapRange')
    cut.inputs['From Min'].default_value = 0.42; cut.inputs['From Max'].default_value = 0.66
    cut.inputs['To Max'].default_value = density
    L(noise.outputs['Fac'], cut.inputs['Value'])

    def ramp_(src, a, b):                                   # 0 at a, 1 at b (clamped)
        m = N('ShaderNodeMapRange'); m.clamp = True
        m.inputs['From Min'].default_value = a; m.inputs['From Max'].default_value = b
        L(src, m.inputs['Value'])
        return m.outputs['Result']

    def mul_(a, b):
        m = N('ShaderNodeMath'); m.operation = 'MULTIPLY'
        L(a, m.inputs[0]); L(b, m.inputs[1])
        return m.outputs[0]
    if shape == 'layer':
        shp = ramp_(sep.outputs['Z'], -0.5, 0.2)
    else:
        xy = N('ShaderNodeCombineXYZ'); L(sep.outputs['X'], xy.inputs['X']); L(sep.outputs['Y'], xy.inputs['Y'])
        rad = N('ShaderNodeVectorMath'); rad.operation = 'LENGTH'; L(xy.outputs[0], rad.inputs[0])
        side = ramp_(rad.outputs[1], 0.5, 0.15)              # 1 in the middle, 0 at the walls of the box
        bottom = ramp_(sep.outputs['Z'], -0.5, -0.25)
        top = ramp_(sep.outputs['Z'], 0.5, 0.05)
        shp = mul_(mul_(side, bottom), top)
    vol = N('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (*col, 1)
    L(mul_(cut.outputs['Result'], shp), vol.inputs['Density'])
    out = N('ShaderNodeOutputMaterial')
    L(vol.outputs[0], out.inputs['Volume'])
    return mat


def embers(name, centre, size, count, col, seed=1, rise=3.2, period=96):
    """Rising embers: glowing orange sparks drifting up through the room and looping. Like the rain, every spark has a twin
    one loop below, the loop snaps half-way between frames, and the cloud has no object motion blur (slow-motion shots
    sample fractional frames), so the loop is never seen."""
    rnd = random.Random(seed)
    half = [(rnd.uniform(-size[0] / 2, size[0] / 2), rnd.uniform(-size[1] / 2, size[1] / 2), rnd.uniform(0, rise))
            for _ in range(count // 2)]
    pts = half + [(x, y, z - rise) for x, y, z in half]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(pts, [], [])
    cloud = bpy.data.objects.new(name, mesh)
    col.objects.link(cloud)
    cloud.location = centre
    _drive(cloud, 'location', f'{centre.z} + fmod(frame + 0.5, {period}) * {rise / period}', index=2)
    _drive(cloud, 'location', f'{centre.x} + 0.12 * sin(frame * 0.05 + {seed})', index=0)       # a slow sideways drift
    m = material(name + '_m', (1.0, 0.35, 0.06), emit=(1.0, 0.3, 0.04), strength=5.0)
    spark = bpy.data.objects.new(name + '_spark', bpy.data.meshes.new(name + '_spark'))
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.006)
    bmesh.ops.scale(bm, vec=(1.0, 1.0, 2.2), verts=bm.verts)      # a little stretched: they are moving
    bm.to_mesh(spark.data); bm.free()
    spark.data.materials.append(m)
    col.objects.link(spark)
    spark.parent = cloud
    cloud.instance_type = 'VERTS'
    for ob in (cloud, spark):
        ob['cine_ignore'] = True
        ob.visible_shadow = False
        try:
            ob.cycles.use_motion_blur = False
        except AttributeError:
            pass
    return cloud


def fire(name, loc, size, col, lit, energy=60.0, seed=0.0):
    """A fire: a volumetric flame (box, procedural shader), a smoke column above it, two flickering orange lights."""
    loc = Vector(loc)
    flame = box(name, (size * 0.9, size * 0.9, size * 1.8), loc + Vector((0, 0, size * 0.9)), fire_material(name + '_m', seed), col)
    flame.visible_shadow = False
    flame['cine_ignore'] = True
    # the plume: from the top of the flame (never below head height, so it never fogs the actors) to the ceiling,
    # no wider than 1.3 m (big floor fires had 4 m columns that filled the room)
    z0, z1 = max(loc.z + size * 1.3, 1.9), 4.3
    w = min(size * 1.2, 1.3)
    smoke = box(name + '_smoke', (w, w, z1 - z0), Vector((loc.x, loc.y, (z0 + z1) / 2)),
                smoke_material(name + '_sm', seed, 6.0, 'column'), col)        # a plume rolling up off each fire
    smoke.visible_shadow = False
    smoke['cine_ignore'] = True
    for k, (dz, e) in enumerate(((0.5, 1.0), (1.1, 0.55))):
        lamp = light(f'{name}_light{k}', 'POINT', loc + Vector((0, 0, size * dz)), energy * e, (1.0, 0.42, 0.1), lit, size=size * 0.35)
        _drive(lamp.data, 'energy', f'{energy * e} * (0.75 + 0.18 * sin(frame * 0.9 + {seed + k}) + 0.1 * sin(frame * 2.7 + {seed * 2 + k}))')
    return flame


FIRE_SIMS = os.environ.get('FIRE_SIMS') or os.path.join(os.environ.get('W', os.path.expanduser('~/mx_work')), 'fire_sims')
# per fuel: smoke colour, smoke density, flame colours (cool, mid, hot), flame brightness
FUEL_LOOK = {
    'table':   dict(smoke=(0.10, 0.09, 0.08), dens=1.6, ramp=((0.45, 0.03, 0.0), (1.0, 0.22, 0.01), (1.0, 0.62, 0.18)), glow=9.0),
    'booth':   dict(smoke=(0.04, 0.035, 0.03), dens=2.6, ramp=((0.40, 0.02, 0.0), (0.95, 0.16, 0.0), (1.0, 0.5, 0.12)), glow=7.0),
    'grease':  dict(smoke=(0.12, 0.11, 0.1), dens=1.2, ramp=((0.6, 0.06, 0.0), (1.0, 0.35, 0.03), (1.0, 0.8, 0.4)), glow=12.0),
    'paper':   dict(smoke=(0.2, 0.19, 0.18), dens=1.0, ramp=((0.55, 0.05, 0.0), (1.0, 0.3, 0.02), (1.0, 0.72, 0.3)), glow=10.0),
    'sheet':   dict(smoke=(0.08, 0.07, 0.06), dens=1.8, ramp=((0.45, 0.03, 0.0), (1.0, 0.2, 0.01), (1.0, 0.58, 0.16)), glow=8.0),
    'debris':  dict(smoke=(0.07, 0.06, 0.05), dens=2.0, ramp=((0.45, 0.03, 0.0), (1.0, 0.24, 0.01), (1.0, 0.6, 0.18)), glow=8.5),
    'machine': dict(smoke=(0.03, 0.03, 0.03), dens=2.8, ramp=((0.6, 0.1, 0.02), (1.0, 0.45, 0.1), (1.0, 0.9, 0.7)), glow=14.0),
}


DENS_K = float(os.environ.get('FIRE_DENS', '0.35'))   # (tuned on isolated fires: denser smoke fogged the room orange)
GLOW_K = float(os.environ.get('FIRE_GLOW', '0.6'))    # (brighter went white under AgX)


def sim_fire_material(recipe):
    """Shader for a baked fire (density, flame grids): smoke from density, emission from flame through the fuel's colours.
    Both are multiplied by the object's 'fade' property (the loop crossfade)."""
    name = 'simfire_' + recipe
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    lk = FUEL_LOOK[recipe]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    fade = N('ShaderNodeAttribute'); fade.attribute_type = 'OBJECT'; fade.attribute_name = 'fade'
    den = N('ShaderNodeAttribute'); den.attribute_name = 'density'
    fl = N('ShaderNodeAttribute'); fl.attribute_name = 'flame'
    d1 = N('ShaderNodeMath'); d1.operation = 'MULTIPLY'; L(den.outputs['Fac'], d1.inputs[0]); d1.inputs[1].default_value = lk['dens'] * DENS_K
    d2 = N('ShaderNodeMath'); d2.operation = 'MULTIPLY'; L(d1.outputs[0], d2.inputs[0]); L(fade.outputs['Fac'], d2.inputs[1])
    ramp = N('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*lk['ramp'][0], 1)
    els[1].position, els[1].color = 1.0, (*lk['ramp'][2], 1)
    mid = els.new(0.45); mid.color = (*lk['ramp'][1], 1)
    fk = N('ShaderNodeMapRange'); fk.clamp = True                 # only real flame glows (faint flame values spread through
    fk.inputs['From Min'].default_value = 0.18; fk.inputs['From Max'].default_value = 0.85   # the smoke lit it orange)
    L(fl.outputs['Fac'], fk.inputs['Value'])
    fp = N('ShaderNodeMath'); fp.operation = 'POWER'; L(fk.outputs['Result'], fp.inputs[0]); fp.inputs[1].default_value = 1.6
    L(fk.outputs['Result'], ramp.inputs['Fac'])
    st = N('ShaderNodeMath'); st.operation = 'MULTIPLY'; L(fp.outputs[0], st.inputs[0]); st.inputs[1].default_value = lk['glow'] * GLOW_K
    st2 = N('ShaderNodeMath'); st2.operation = 'MULTIPLY'; L(st.outputs[0], st2.inputs[0]); L(fade.outputs['Fac'], st2.inputs[1])
    vol = N('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (*lk['smoke'], 1)
    L(d2.outputs[0], vol.inputs['Density'])
    L(ramp.outputs['Color'], vol.inputs['Emission Color'])
    L(st2.outputs[0], vol.inputs['Emission Strength'])
    out = N('ShaderNodeOutputMaterial'); L(vol.outputs[0], out.inputs['Volume'])
    return mat


def sim_fire(name, recipe, loc, col, lit, scale=1.0, rot=0.0, start=0, energy=60.0, seed=0.0):
    """A baked fire placed on a burning object: two copies of the same simulation half a loop apart, crossfaded (each copy
    is faded out at the moment it jumps back to the start of its loop, so the loop never shows), plus two flickering lights.
    Returns None when the simulation has not been baked (the caller falls back to the procedural fire)."""
    meta_p = os.path.join(FIRE_SIMS, recipe, 'DONE.json')
    if not os.path.exists(meta_p):
        return None
    import json
    meta = json.load(open(meta_p))
    W_, L_ = meta['warm'], meta['loop']
    first = os.path.join(FIRE_SIMS, recipe, 'data', 'fluid_data_0001.vdb')
    mat = sim_fire_material(recipe)
    objs = []
    for k, shift in enumerate((0, L_ // 2)):
        vd = bpy.data.volumes.new(f'{name}_{"ab"[k]}')
        vd.filepath = first
        vd.is_sequence = True
        vd.frame_duration = L_
        vd.frame_offset = W_
        vd.frame_start = int(start) + shift
        vd.sequence_mode = 'REPEAT'
        vd.velocity_grid = ''                                      # no velocity motion blur: with it, Cycles padded the volume
        vd.velocity_scale = 0.0                                    # mesh by the (grid-unit) velocity and ran out of memory
        vd.materials.append(mat)
        ob = bpy.data.objects.new(vd.name, vd)
        col.objects.link(ob)
        org = Vector(meta.get('origin', (0, 0, 0))) * scale        # the grid's (0,0,0) is the domain's lower corner
        org.rotate(Matrix.Rotation(rot, 3, 'Z'))
        ob.location = Vector(loc) + org
        ob.rotation_euler = (0, 0, rot)
        ob.scale = (scale, scale, scale)
        ob['fade'] = 1.0
        fc = ob.driver_add('["fade"]')
        fc.driver.type = 'SCRIPTED'
        s0 = int(start) + shift
        fc.driver.expression = f'1 - abs(2 * fmod(frame - {s0} + {L_ * 1000}, {L_}) / {L_} - 1)'   # (fmod: a simple expression, no Python)
        ob['cine_ignore'] = True
        ob.visible_shadow = False
        ob.cycles.use_motion_blur = False
        objs.append(ob)
    for k, (dz, e) in enumerate(((0.35, 1.0), (0.9, 0.5))):
        lamp = light(f'{name}_light{k}', 'POINT', Vector(loc) + Vector((0, 0, dz * scale)), energy * e, (1.0, 0.42, 0.1), lit,
                     size=0.25 * scale)
        _drive(lamp.data, 'energy', f'{energy * e} * (0.75 + 0.18 * sin(frame * 0.9 + {seed + k}) + 0.1 * sin(frame * 2.7 + {seed * 2 + k}))')
    return objs


def char_material(name, base=(0.5, 0.1, 0.08), amount=0.8, embers=True, seed=0.0):
    """Burnt: the object's own colour survives in patches, the rest is blistered black char; with embers, glowing orange
    cracks (Voronoi edges masked by noise) pulse in the char. amount: 0 = scorched, 1 = burnt through."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    N, L = nt.nodes.new, nt.links.new
    tc = N('ShaderNodeNewGeometry')        # world position: the same char grain on a 5 m counter and a 10 cm bottle (object space stretched it)
    # Burning works in stages, so the colour does too: smoke-stained paint, then scorched brown, then black char. Two noise
    # scales (broad burn fronts, fine grain) and a wide, soft ramp: a hard cut between paint and black read as camouflage.
    nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 6.0
    nz.inputs['Roughness'].default_value = 0.55
    L(tc.outputs['Position'], nz.inputs['Vector'])
    fine = N('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 24.0; fine.inputs['Detail'].default_value = 8.0
    L(tc.outputs['Position'], fine.inputs['Vector'])
    fm = N('ShaderNodeMix'); fm.data_type = 'FLOAT'; fm.inputs['Factor'].default_value = 0.3
    L(nz.outputs['Fac'], fm.inputs['A']); L(fine.outputs['Fac'], fm.inputs['B'])
    spread = N('ShaderNodeMapRange')                                 # noise sits near 0.5: stretch it so fronts vary
    spread.inputs['From Min'].default_value = 0.32; spread.inputs['From Max'].default_value = 0.68
    L(fm.outputs['Result'], spread.inputs['Value'])
    burn = N('ShaderNodeMath'); burn.operation = 'ADD'; burn.use_clamp = True     # how far this spot has burnt (0..1)
    L(spread.outputs['Result'], burn.inputs[0]); burn.inputs[1].default_value = (amount - 0.55) * 1.2
    ramp = N('ShaderNodeValToRGB'); cr_ = ramp.color_ramp; cr_.interpolation = 'EASE'
    stained = tuple(c * (0.45 - 0.2 * amount) + 0.03 for c in base)            # soot-dulled paint
    cr_.elements[0].position = 0.18; cr_.elements[0].color = (*stained, 1)
    cr_.elements[1].position = 0.62; cr_.elements[1].color = (0.016, 0.013, 0.011, 1)
    mid = cr_.elements.new(0.4); mid.color = (0.075, 0.04, 0.02, 1)             # scorched, blistered brown
    L(burn.outputs['Value'], ramp.inputs['Fac'])
    L(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    cut = N('ShaderNodeMapRange'); cut.clamp = True                 # where the char has taken over
    cut.inputs['From Min'].default_value = 0.5; cut.inputs['From Max'].default_value = 0.72
    L(burn.outputs['Value'], cut.inputs['Value'])
    rough = N('ShaderNodeMapRange'); rough.inputs['To Min'].default_value = 0.45; rough.inputs['To Max'].default_value = 0.95
    L(cut.outputs['Result'], rough.inputs['Value'])
    L(rough.outputs['Result'], bsdf.inputs['Roughness'])
    bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.05 + 0.8 * amount * amount; bump.inputs['Distance'].default_value = 0.01
    blis = N('ShaderNodeTexVoronoi'); blis.inputs['Scale'].default_value = 28.0     # blistered, alligatored char
    L(tc.outputs['Position'], blis.inputs['Vector'])
    L(blis.outputs['Distance'], bump.inputs['Height'])
    L(bump.outputs['Normal'], bsdf.inputs['Normal'])
    if embers:
        warp = N('ShaderNodeTexNoise'); warp.inputs['Scale'].default_value = 2.5; warp.inputs['Detail'].default_value = 4.0
        L(tc.outputs['Position'], warp.inputs['Vector'])
        wv = N('ShaderNodeMix'); wv.data_type = 'VECTOR'; wv.inputs['Factor'].default_value = 0.35   # wandering cracks,
        L(tc.outputs['Position'], wv.inputs['A']); L(warp.outputs['Color'], wv.inputs['B'])                  # not tiles
        cr = N('ShaderNodeTexVoronoi'); cr.feature = 'DISTANCE_TO_EDGE'; cr.inputs['Scale'].default_value = 11.0
        cr.inputs['Randomness'].default_value = 1.0
        L(wv.outputs['Result'], cr.inputs['Vector'])
        edge = N('ShaderNodeMapRange'); edge.clamp = True
        edge.inputs['From Min'].default_value = 0.025; edge.inputs['From Max'].default_value = 0.0
        L(cr.outputs['Distance'], edge.inputs['Value'])
        pulse = N('ShaderNodeTexNoise'); pulse.noise_dimensions = '4D'; pulse.inputs['Scale'].default_value = 2.0
        L(tc.outputs['Position'], pulse.inputs['Vector'])
        _drive(pulse.inputs['W'], 'default_value', f'frame / 30 + {seed}')
        hot = N('ShaderNodeMapRange'); hot.clamp = True
        hot.inputs['From Min'].default_value = 0.56; hot.inputs['From Max'].default_value = 0.7   # glowing only in patches
        L(pulse.outputs['Fac'], hot.inputs['Value'])
        m1 = N('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L(edge.outputs['Result'], m1.inputs[0]); L(hot.outputs['Result'], m1.inputs[1])
        m2 = N('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L(m1.outputs[0], m2.inputs[0]); L(cut.outputs['Result'], m2.inputs[1])
        m3 = N('ShaderNodeMath'); m3.operation = 'MULTIPLY'; L(m2.outputs[0], m3.inputs[0]); m3.inputs[1].default_value = 6.0 * amount
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.28, 0.03, 1)
        L(m3.outputs[0], bsdf.inputs['Emission Strength'])
    return mat


def rest_on(obj, z_surface):
    """Drop an object (after its rotation) so its lowest point sits on a surface: never sunk in, never floating."""
    bpy.context.view_layer.update()
    low = min((obj.matrix_world @ Vector(c)).z for c in obj.bound_box)
    if obj.type == 'MESH' and obj.data.vertices:
        low = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    obj.location.z += z_surface - low + 0.001
    _TREES.pop(obj.name, None)
    bpy.context.view_layer.update()
    return obj


def burn_cafe(col, o):
    """Everything the fire has had: charred furniture where it burns, scorch and ash on the floor, soot on the ceiling,
    collapsed debris, a knocked-over stool, a burnt curtain at the window, sagging booth backs."""
    rnd = random.Random(21)
    # furniture that burns: char by distance to its fire
    burnt = {'booth0_1': 0.95, 'booth_back0_1': 1.0, 'booth2_-1': 0.9, 'booth_back2_-1': 1.0, 'table_top0': 0.85,
             'table_top2': 0.7, 'table_top1': 0.55, 'booth0_-1': 0.45, 'booth_back0_-1': 0.5, 'booth2_1': 0.4,
             'booth_back2_1': 0.45, 'booth1_-1': 0.25, 'booth_back1_-1': 0.3, 'counter_top': 0.5, 'counter': 0.45,
             'stool_seat3': 0.6, 'stool_seat4': 0.7, 'menu_board': 0.8, 'coffee_machine': 0.6}
    for k, (name, amt) in enumerate(burnt.items()):
        ob = bpy.data.objects.get(name)
        if ob is None or not ob.data.materials:
            continue
        m0 = ob.data.materials[0]
        bsdf = m0.node_tree.nodes.get('Principled BSDF') if m0.use_nodes else None
        base = tuple(bsdf.inputs['Base Color'].default_value)[:3] if bsdf else (0.4, 0.3, 0.2)
        ob.data.materials[0] = char_material(f'char_{name}', base, amt, embers=amt > 0.55, seed=k * 3.1)
    for name in ('booth_back0_1', 'booth_back2_-1'):                 # vinyl that has burnt sags over toward the seat
        ob = bpy.data.objects.get(name)
        if ob is not None:
            bpy.context.view_layer.objects.active = ob
            mod = ob.modifiers.new('sag', 'SIMPLE_DEFORM')
            mod.deform_method = 'BEND'
            mod.deform_axis = 'X'
            mod.angle = math.radians(18 if name.endswith('_1') else -18)
    # scorch and ash on the floor under every floor-level fire, soot on the ceiling above the big ones
    scorch = bpy.data.materials.new('floor_scorch')
    scorch.use_nodes = True
    nt = scorch.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.012, 0.01, 0.009, 1)
    bsdf.inputs['Roughness'].default_value = 0.95
    gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
    tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], gr.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.0; nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'
    nt.links.new(gr.outputs['Fac'], mm.inputs[0]); nt.links.new(nz.outputs['Fac'], mm.inputs[1])
    a_ = nt.nodes.new('ShaderNodeMapRange'); a_.clamp = True
    a_.inputs['From Min'].default_value = 0.05; a_.inputs['From Max'].default_value = 0.35
    nt.links.new(mm.outputs[0], a_.inputs['Value']); nt.links.new(a_.outputs['Result'], bsdf.inputs['Alpha'])
    scorch.blend_method = 'BLEND'
    floor_fires = [(-5.0, 4.0, 1.2), (5.0, -3.6, 1.3), (5.3, 3.8, 0.9), (-5.0, -3.4, 1.1), (0.4, 4.2, 0.85), (-2.2, -4.1, 0.75),
                   (-5.1, 0.0, 1.0), (3.0, -4.1, 0.9), (-5.42, 2.0, 1.0), (5.38, -1.5, 1.1), (1.6, 4.42, 1.0)]
    for k, (x, y, s_) in enumerate(floor_fires):
        pl = plane(f'scorch_floor{k}', 2.6 * s_, 2.6 * s_, o + Vector((x, y, 0.003 + 0.0004 * k)), scorch, col,
                   rot=(0, 0, rnd.uniform(0, 6.28)))
        pl.visible_shadow = False
        cl = plane(f'soot_ceiling{k}', 3.0 * s_, 3.0 * s_, o + Vector((x, y, 4.148 - 0.0004 * k)), scorch, col,
                   rot=(math.radians(180), 0, rnd.uniform(0, 6.28)))
        cl.visible_shadow = False
    # the whole floor under a film of soot and ash (smoke settles everywhere, not just under the fires)
    ash = bpy.data.materials.new('floor_ash')
    ash.use_nodes = True
    nt = ash.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.03, 0.028, 0.026, 1)
    bsdf.inputs['Roughness'].default_value = 0.97
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.9; nz.inputs['Detail'].default_value = 9.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    a_ = nt.nodes.new('ShaderNodeMapRange'); a_.clamp = True
    a_.inputs['From Min'].default_value = 0.3; a_.inputs['From Max'].default_value = 0.75
    a_.inputs['To Min'].default_value = 0.3; a_.inputs['To Max'].default_value = 0.88
    nt.links.new(nz.outputs['Fac'], a_.inputs['Value']); nt.links.new(a_.outputs['Result'], bsdf.inputs['Alpha'])
    ash.blend_method = 'BLEND'
    fl = plane('ash_floor', 11.5, 9.5, o + Vector((0, 0, 0.0015)), ash, col)
    fl.visible_shadow = False
    # debris under the floor fires: charred planks and broken ceiling tiles, every piece resting on the floor
    char_wood = char_material('char_debris', (0.3, 0.2, 0.12), 0.95, embers=True, seed=5)
    tile_m = char_material('char_tile', (0.55, 0.5, 0.45), 0.6, embers=False)
    for k, (x, y, s_) in enumerate(floor_fires[:8]):
        for j in range(5):
            ln = rnd.uniform(0.35, 0.9) * s_
            pc = box(f'debris{k}_{j}', (ln, rnd.uniform(0.06, 0.14), rnd.uniform(0.03, 0.07)),
                     o + Vector((x + rnd.uniform(-0.35, 0.35) * s_, y + rnd.uniform(-0.35, 0.35) * s_, 0.5)), char_wood, col,
                     rot=(rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(0, 3.14)))
            rest_on(pc, o.z + 0.004 * (j + 1))                       # stacked a little: none floats, none sinks
        tl = box(f'ceiling_tile{k}', (0.6, 0.6, 0.02), o + Vector((x + rnd.uniform(-0.5, 0.5), y + rnd.uniform(-0.5, 0.5), 0.3)),
                 tile_m, col, rot=(rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08), rnd.uniform(0, 3.14)))
        rest_on(tl, o.z + 0.002)
    # where the tiles fell from: dark holes in the ceiling over two of the fires
    hole_m = material('ceiling_hole', (0.004, 0.004, 0.004), rough=1.0)
    for k, (x, y) in enumerate(((-5.0, 4.0), (5.0, -3.6))):
        plane(f'ceiling_hole{k}', 0.6, 0.6, o + Vector((x + 0.3, y - 0.2, 4.146)), hole_m, col, rot=(math.radians(180), 0, 0.3))
    # a stool knocked over, lying on its side on the floor (seat and post as one piece, resting on the floor)
    chrome = bpy.data.materials.get('cafe_chrome')
    seat = char_material('char_stool', (0.7, 0.06, 0.05), 0.5, embers=False)
    post = cylinder('stool_fallen_post', 0.04, 0.72, o + Vector((-1.9, 1.2, 0.5)), chrome, col, verts=12)
    st = cylinder('stool_fallen_seat', 0.2, 0.09, o + Vector((-1.9, 1.2 + 0.36, 0.5)), seat, col, verts=20)
    for ob in (post, st):
        ob.rotation_euler = (math.radians(90), 0, 0)
    post.location.y = 1.2 - 0.0
    st.location.y = 1.2 + 0.405
    rest_on(post, o.z)
    st.location.z = post.location.z
    rest_on(st, o.z)
    # the curtain at the window, half burnt away: a hanging sheet, holes eaten through it from the bottom up
    cur = bpy.data.materials.new('curtain_burnt')
    cur.use_nodes = True
    nt = cur.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6.0; nz.inputs['Detail'].default_value = 6.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    h = nt.nodes.new('ShaderNodeMath'); h.operation = 'ADD'; nt.links.new(sep.outputs['Y'], h.inputs[0]); nt.links.new(nz.outputs['Fac'], h.inputs[1])
    keep = nt.nodes.new('ShaderNodeMapRange'); keep.clamp = True       # gone below the burn line, ragged
    keep.inputs['From Min'].default_value = 0.85; keep.inputs['From Max'].default_value = 0.9
    nt.links.new(h.outputs[0], keep.inputs['Value']); nt.links.new(keep.outputs['Result'], bsdf.inputs['Alpha'])
    edge = nt.nodes.new('ShaderNodeMapRange'); edge.clamp = True       # a charred, glowing edge just above the line
    edge.inputs['From Min'].default_value = 1.05; edge.inputs['From Max'].default_value = 0.88
    nt.links.new(h.outputs[0], edge.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (0.5, 0.06, 0.05, 1); mx.inputs['B'].default_value = (0.02, 0.015, 0.012, 1)
    nt.links.new(edge.outputs['Result'], mx.inputs['Factor']); nt.links.new(mx.outputs['Result'], bsdf.inputs['Base Color'])
    gl = nt.nodes.new('ShaderNodeMapRange'); gl.clamp = True
    gl.inputs['From Min'].default_value = 0.92; gl.inputs['From Max'].default_value = 0.88; gl.inputs['To Max'].default_value = 5.0
    nt.links.new(h.outputs[0], gl.inputs['Value'])
    bsdf.inputs['Emission Color'].default_value = (1.0, 0.3, 0.04, 1)
    nt.links.new(gl.outputs['Result'], bsdf.inputs['Emission Strength'])
    cur.blend_method = 'BLEND'
    bpy.ops.mesh.primitive_plane_add(size=1)
    cp = bpy.context.active_object
    cp.name = 'curtain'
    for c in list(cp.users_collection):
        c.objects.unlink(cp)
    col.objects.link(cp)
    cp.scale = (0.75, 2.2, 1)
    cp.rotation_euler = (math.radians(90), 0, 0)
    cp.location = o + Vector((-4.9, 4.7, 2.15))                     # from the curtain rail at 3.25 m down to 1.05 m
    sub = cp.modifiers.new('sub', 'SUBDIVIDE' if False else 'SUBSURF'); sub.levels = 0
    wave = cp.modifiers.new('folds', 'WAVE'); wave.use_x = True; wave.use_y = False; wave.height = 0.04; wave.width = 0.25
    wave.speed = 0.0
    cp.data.materials.append(cur)
    rail = cylinder('curtain_rail', 0.012, 1.0, o + Vector((-4.9, 4.72, 3.27)), chrome, col, rot=(0, math.radians(90), 0), verts=8)
    return col


def cafe_signs(col, lit, o):
    """What a real diner has on its glass and walls, still there while it burns: the name in gold leaf on the street
    window (painted on the inside of the glass to read from the street, so from in here it reads backward, as it does
    in any real shop), the hours on the door-side pane, a red neon OPEN sign hanging in the window, still lit, its N
    failing; a chalk menu with prices over the counter; a lit green EXIT sign, a FIRE EXTINGUISHER placard over the
    extinguisher nobody used, a NO SMOKING sign behind the counter, next to the fire."""
    out = (math.radians(90), 0, math.radians(180))            # reads from the street (+y)
    inn = (math.radians(90), 0, 0)                             # reads from inside the café (-y)
    gold = material('gold_leaf', (1.0, 0.72, 0.28), rough=0.22, metal=1.0, emit=(1.0, 0.65, 0.25), strength=0.35)
    vinyl = material('window_vinyl', (0.92, 0.9, 0.85), rough=0.5, emit=(0.9, 0.88, 0.8), strength=0.15)
    gy = 4.94                                                  # the glass is at y 4.95: lettering on its inner face
    # window: left pane x -4.5..-2.24, right pane -2.16..0.1, glass z 1.2..3.2
    for name, body, x, z, size, m in (('sign_name0', "FINE'S", -3.37, 2.62, 0.36, gold), ('sign_name1', 'DINER', -1.03, 2.62, 0.36, gold),
                                      ('sign_est', 'EST. 1987', -3.37, 2.38, 0.12, gold),
                                      ('sign_sub', 'COFFEE  ~  PIE  ~  BREAKFAST', -1.03, 2.4, 0.085, gold),
                                      ('sign_hours0', 'HOURS', -0.4, 1.68, 0.06, vinyl), ('sign_hours1', 'MON-FRI  6AM-10PM', -0.4, 1.58, 0.042, vinyl),
                                      ('sign_hours2', 'SAT-SUN  7AM-11PM', -0.4, 1.51, 0.042, vinyl)):
        t = _txt(name, body, o + Vector((x, gy, z)), out, size, m, col)
        if m is gold:
            t.data.extrude = 0.0015
        t['cine_ignore'] = True
    for k, dx in enumerate((-0.32, 0.32)):                     # a thin line under the name, like the sign painter's rule
        box(f'sign_rule{k}', (0.62, 0.002, 0.012), o + Vector((-2.2 + (-1.17 if k == 0 else 1.17), gy, 2.53)), gold, col)
    # the neon OPEN sign, hanging on two chains in the left pane, facing the street; the N is dying and flickers
    nx, ny, nz = -3.4, 4.74, 1.62
    steady = material('neon_open', (1.0, 0.1, 0.06), emit=(1.0, 0.12, 0.06), strength=6.0)
    dying = material('neon_open_n', (1.0, 0.1, 0.06), emit=(1.0, 0.12, 0.06), strength=6.0)
    _drive(steady.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'], 'default_value',
           '6.0 + 0.8 * sin(frame * 2.3) * sin(frame * 0.41)')
    _drive(dying.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'], 'default_value',
           '6.0 * floor(fmod(frame * 0.731 + 3.0 * sin(frame * 0.13), 1.9))')        # (on, off, on, off, irregularly)
    neon = _txt('neon_open', 'OPEN', o + Vector((nx, ny, nz)), out, 0.3, steady, col)
    neon.data.materials.append(dying)
    for i, ch in enumerate(neon.data.body_format):
        ch.material_index = 1 if i == 3 else 0
    neon.data.bevel_depth = 0.006                                    # tubes, not slabs
    neon.data.offset = -0.012
    neon.data.extrude = 0.004
    box('neon_open_rail', (1.0, 0.012, 0.012), o + Vector((nx, ny, nz + 0.29)), material('neon_rail', (0.05, 0.05, 0.05), rough=0.4,
        metal=0.6), col)                                              # the bar the tubes hang from (clear frame, no backing)
    chain = material('chain', (0.3, 0.3, 0.32), rough=0.3, metal=1.0)
    for k, dx in enumerate((-0.45, 0.45)):
        top_, bot_ = 3.19, nz + 0.296
        cylinder(f'neon_open_chain{k}', 0.004, top_ - bot_, o + Vector((nx + dx, ny, (top_ + bot_) / 2)), chain, col, verts=6)
    nl = light('L_neon_open', 'POINT', o + Vector((nx, ny - 0.25, nz + 0.12)), 6.0, (1.0, 0.12, 0.06), lit, size=0.3)
    _drive(nl.data, 'energy', '6.0 + 0.8 * sin(frame * 2.3) * sin(frame * 0.41)')
    # the chalk menu over the counter (board x 1.0..4.2, z 2.5..3.5, face at y 4.79)
    chalk = material('chalk', (0.88, 0.88, 0.84), rough=0.95, emit=(0.85, 0.85, 0.8), strength=0.12)
    my = 4.785
    _txt('menu_title', "FINE'S  MENU", o + Vector((2.6, my, 3.27)), inn, 0.14, chalk, col)
    items = (('COFFEE', '1.50'), ('TEA', '1.25'), ('PIE, SLICE', '3.25'), ('MILKSHAKE', '3.75'),
             ('EGGS & TOAST', '4.95'), ('PANCAKES', '5.50'), ('BURGER & FRIES', '7.95'), ('SOUP OF THE DAY', '3.95'))
    for k, (item, price) in enumerate(items):
        cx_ = 1.15 if k < 4 else 2.75
        z_ = 3.06 - (k % 4) * 0.15
        _txt(f'menu_item{k}', item, o + Vector((cx_, my, z_)), inn, 0.085, chalk, col, align='LEFT')
        _txt(f'menu_price{k}', price, o + Vector((cx_ + 1.3, my, z_)), inn, 0.085, chalk, col, align='RIGHT')
    # EXIT over the left wall's front end; a fire extinguisher placard; NO SMOKING behind the counter
    ex_m = material('exit_face', (0.1, 0.9, 0.3), emit=(0.15, 1.0, 0.35), strength=4.0)
    ex_case = box('exit_sign', (0.06, 0.38, 0.2), o + Vector((-5.819, -4.2, 3.0)), material('exit_case', (0.85, 0.85, 0.82), rough=0.4), col)
    _txt('exit_text', 'EXIT', o + Vector((-5.788, -4.2, 2.955)), (math.radians(90), 0, math.radians(90)), 0.11, ex_m, col)
    light('L_exit', 'POINT', o + Vector((-5.6, -4.2, 2.9)), 3.0, (0.15, 1.0, 0.35), lit, size=0.1)
    red = material('placard_red', (0.75, 0.04, 0.03), rough=0.5)
    white = material('placard_white', (0.95, 0.95, 0.92), rough=0.5)
    plane('ext_placard', 0.26, 0.17, o + Vector((-5.848, -0.8, 1.52)), red, col, rot=(math.radians(90), 0, math.radians(90)))
    for k, w in enumerate(('FIRE', 'EXTINGUISHER')):
        _txt(f'ext_placard_text{k}', w, o + Vector((-5.846, -0.8, 1.54 - k * 0.055)), (math.radians(90), 0, math.radians(90)),
             0.045 if k == 0 else 0.03, white, col)
    plane('nosmoking_sign', 0.32, 0.2, o + Vector((0.45, 4.848, 1.78)), white, col, rot=inn)
    _txt('nosmoking_text', 'NO SMOKING', o + Vector((0.45, 4.846, 1.765)), inn, 0.045, red, col)
    ring = bpy.data.curves.new('nosmoking_ring', 'CURVE')                # (the red circle above the words)
    ring.dimensions = '2D'; ring.bevel_depth = 0.004
    sp = ring.splines.new('POLY'); sp.points.add(23); sp.use_cyclic_u = True
    for i, p_ in enumerate(sp.points):
        a_ = i / 24 * 6.2832
        p_.co = (math.cos(a_) * 0.035, math.sin(a_) * 0.035, 0, 1)
    rob = bpy.data.objects.new('nosmoking_ring', ring); col.objects.link(rob); ring.materials.append(red)
    rob.location = o + Vector((0.45, 4.846, 1.84)); rob.rotation_euler = inn


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
    wall_m = material('cafe_wall', (0.38, 0.24, 0.17), rough=0.85)
    mxsets.add_bump(wall_m, 30.0, 0.2)
    trim_m = material('cafe_trim', (0.6, 0.08, 0.06), rough=0.5)
    for name, size, off in (('cafe_back', (12, 0.3, 4.2), (0, 5, 2.1)), ('cafe_left', (0.3, 10, 4.2), (-6, 0, 2.1)),
                            ('cafe_right', (0.3, 10, 4.2), (6, 0, 2.1)), ('cafe_ceiling', (12, 10, 0.2), (0, 0, 4.25))):
        box(name, size, o + Vector(off), wall_m, col)
    box('cafe_stripe', (11.9, 0.05, 0.25), o + Vector((0, 4.83, 1.0)), trim_m, col)
    # the window in the back wall: a real opening onto the city at night (it was a code screen that rendered as black)
    back = bpy.data.objects['cafe_back']
    cutter = box('cafe_window_cut', (4.6, 1.0, 2.0), o + Vector((-2.2, 5.0, 2.2)), wall_m, col)
    cutter.hide_render = True
    cutter.hide_viewport = True
    cut = back.modifiers.new('window', 'BOOLEAN')
    cut.operation = 'DIFFERENCE'
    cut.object = cutter
    # thin window glass: see-through with a faint reflection at grazing angles. (A one-sided plane with refraction at
    # IOR 1.5 bent the street like a lens and mirrored the room's lights onto it as a pale panel.)
    glass = bpy.data.materials.new('cafe_glass')
    glass.use_nodes = True
    gnt = glass.node_tree
    gnt.nodes.remove(gnt.nodes['Principled BSDF'])
    tr = gnt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (0.93, 0.97, 0.95, 1)
    gl = gnt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.03
    lw = gnt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.12
    fr = gnt.nodes.new('ShaderNodeMath'); fr.operation = 'MULTIPLY'; fr.inputs[1].default_value = 0.5
    gnt.links.new(lw.outputs['Fresnel'], fr.inputs[0])
    mx_ = gnt.nodes.new('ShaderNodeMixShader')
    gnt.links.new(fr.outputs[0], mx_.inputs['Fac']); gnt.links.new(tr.outputs[0], mx_.inputs[1]); gnt.links.new(gl.outputs[0], mx_.inputs[2])
    gnt.links.new(mx_.outputs[0], gnt.nodes['Material Output'].inputs['Surface'])
    pane = plane('cafe_window_glass', 4.6, 2.0, o + Vector((-2.2, 4.95, 2.2)), glass, col, rot=(math.radians(90), 0, 0))
    pane.visible_shadow = False
    pane['cine_ignore'] = True
    # outside: the sidewalk, the street, and the other side of it: shops with lit signs, towers rising behind them
    rnd_c = random.Random(21)
    box('street_sidewalk', (40, 4, 0.15), o + Vector((0, 7.2, 0.07)), material('sidewalk', (0.18, 0.18, 0.19), rough=0.7), col)
    wet = material('street_asphalt', (0.03, 0.035, 0.035), rough=0.18)
    plane('street_road', 60, 12, o + Vector((0, 15.2, 0.0)), wet, col)
    box('street_sidewalk_far', (60, 2.6, 0.15), o + Vector((0, 22.5, 0.07)), bpy.data.materials['sidewalk'], col)   # (under the shops)
    for k in range(9):                                            # lane marks
        box(f'lane{k}', (1.6, 0.12, 0.01), o + Vector((-16 + k * 4.2, 15.2, 0.01)), material('lane', (0.9, 0.8, 0.3), rough=0.5), col)
    for k in range(10):                                           # the far side: towers, each a lit window grid
        w, d, h = rnd_c.uniform(5, 9), rnd_c.uniform(6, 10), rnd_c.uniform(14, 48)
        x = -24 + k * 5.6 + rnd_c.uniform(-0.8, 0.8)
        box(f'cafe_city{k}', (w, d, h), o + Vector((x, 25 + d / 2 + rnd_c.uniform(0, 8), h / 2)),
            mxsets.window_material(f'cafe_win{k}', 40 + k, (w, d, h)), col)
    # the shops across the street: each name on a sign box fixed to its building, at the height of its own shopfront
    # (they were bare letters floating in the air, all at one height, lined up behind the café's window lettering)
    box_m = material('shop_sign_box', (0.03, 0.03, 0.035), rough=0.5, metal=0.4)
    for k, (x, txt, colour, z, size) in enumerate(((-6.9, 'PAWN & GOLD', (1.0, 0.2, 0.15), 4.6, 0.55), (-1.4, 'HODL 24H', (0.2, 1.0, 0.35), 3.0, 0.6),
                                                   (3.9, 'NOODLES', (1.0, 0.55, 0.1), 5.4, 0.7))):
        w_ = len(txt) * size * 0.68 + 0.5
        top = z + size * 1.35 + 0.8                                 # the shop: a low front building the sign is fixed to
        box(f'shopfront{k}', (max(w_ + 1.2, 5.0), 1.2, top), o + Vector((x, 23.7 + 0.6, top / 2)),
            material(f'shopfront_m{k}', (0.12, 0.11, 0.1), rough=0.8), col)
        win_tint = tuple(0.25 + 0.45 * c for c in colour)                # (at 0.6 they read as blank pastel slabs)
        ww = max(w_ + 1.2, 5.0) - 1.4
        plane(f'shop_window{k}', ww, 2.0, o + Vector((x, 23.69, 1.25)),
              material(f'shop_window_m{k}', (0.03, 0.03, 0.03), rough=0.05, emit=win_tint, strength=0.18), col, rot=(math.radians(90), 0, 0))
        for j in range(3):                                              # mullions and a door frame: glass, not a light box
            box(f'shop_mullion{k}_{j}', (0.06, 0.03, 2.0), o + Vector((x - ww / 2 + ww * (j + 1) / 4, 23.67, 1.25)), box_m, col)
        box(f'shop_transom{k}', (ww, 0.03, 0.06), o + Vector((x, 23.67, 1.75)), box_m, col)
        box(f'shop_sign{k}', (w_, 0.3, size * 1.35), o + Vector((x, 23.55, z + size * 0.35)), box_m, col)
        bpy.ops.object.text_add(location=o + Vector((x, 23.38, z)), rotation=(math.radians(90), 0, 0))   # reads from the café
        sign = bpy.context.active_object
        sign.name = f'neon_sign{k}'
        sign.data.body = txt
        sign.data.size = size
        sign.data.align_x = 'CENTER'
        sign.data.materials.append(material(f'neon{k}', colour, emit=colour, strength=3.0))   # (8 washed out to white)
        for c_ in list(sign.users_collection):
            c_.objects.unlink(sign)
        col.objects.link(sign)
        nl = light(f'L_neon{k}', 'AREA', o + Vector((x, 22.6, z - 0.2)), 220, colour, lit, size=1.6, rot=(math.radians(-90), 0, 0))
        nl.visible_camera = False                                  # (seen through the window it was a white square:
        nl.visible_transmission = False                            # through the glass too, a pale panel over the street)
        nl.visible_glossy = False
    pole_m = material('street_pole', (0.08, 0.08, 0.09), rough=0.4, metal=0.6)
    lamp_m = material('street_lamp', (1.0, 0.8, 0.5), emit=(1.0, 0.78, 0.45), strength=12.0)
    for k, x in enumerate((-9.0, -1.0, 7.0)):                     # street lamps on the near sidewalk
        cylinder(f'street_pole{k}', 0.07, 5.0, o + Vector((x, 8.4, 2.5)), pole_m, col, verts=10)
        sphere(f'street_bulb{k}', 0.22, o + Vector((x, 8.4, 5.1)), lamp_m, col)
        light(f'L_street{k}', 'POINT', o + Vector((x, 8.4, 4.9)), 900, (1.0, 0.75, 0.45), lit, size=0.3).visible_camera = False
    sky = material('cafe_sky', (0.0, 0.0, 0.0), emit=(0.02, 0.05, 0.045), strength=1.0)
    plane('cafe_sky', 140, 70, o + Vector((0, 60, 30)), sky, col, rot=(math.radians(90), 0, 0))
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
    cafe_signs(col, lit, o)
    box('coffee_machine', (0.6, 0.5, 0.7), o + Vector((4.4, 2.75, 1.46)), chrome, col, bevel=0.03)   # on the counter top
    # (it stood at y 3.3, behind the counter, 1.1 m off the floor with nothing under it)
    # pendant lamps (warm), and the fires: on tables, the counter, the menu board, the floor in a corner
    for k, x in enumerate((-3.6, -0.8, 2.0, 4.0)):
        cylinder(f'pendant_cord{k}', 0.008, 1.2, o + Vector((x, 1.0 if k > 1 else -0.8, 3.6)), board_m, col, verts=6)
        cone = cylinder(f'pendant{k}', 0.22, 0.18, o + Vector((x, 1.0 if k > 1 else -0.8, 2.95)), trim_m, col, verts=20)
        light(f'L_pendant{k}', 'POINT', o + Vector((x, 1.0 if k > 1 else -0.8, 2.8)), 12, (1.0, 0.75, 0.45), lit, size=0.15)
    # the fires, each on the thing that is burning and burning like it: baked simulations (firesims.py), one recipe per
    # fuel, every instance with its own size, turn and start time. Surfaces: table tops at 0.805 m, counter top 1.11 m,
    # booth seats 0.48 m (backs on the side away from the table), the walls' inner faces at x = +-5.85 and y = 4.85.
    rnd = random.Random(5)
    FIRES = [('table', (-3.6, 0.6, 0.805), 0.85, 20), ('paper', (-0.8, -2.6, 0.805), 1.0, 0),       # (napkins and a menu)
             ('table', (-3.6, -2.2, 0.805), 0.65, 140), ('grease', (2.3, 2.6, 1.11), 0.95, 0),
             ('machine', (4.4, 2.75, 1.81), 0.8, 0),
             ('booth', (-3.6, 1.45, 0.4), 1.0, 0), ('booth', (-3.6, -3.05, 0.4), 0.9, 180),
             ('sheet', (-5.42, 2.0, 0.0), 1.0, 90), ('sheet', (5.38, -1.5, 0.0), 1.1, -90),
             ('sheet', (1.6, 4.42, 0.0), 1.0, 0), ('sheet', (-4.9, 4.42, 1.0), 0.7, 0),             # (the last: the curtain)
             ('debris', (-5.0, 4.0, 0.0), 1.2, 30), ('debris', (5.0, -3.6, 0.0), 1.3, 200), ('debris', (5.3, 3.8, 0.0), 0.9, 75),
             ('debris', (-5.0, -3.4, 0.0), 1.1, 310), ('debris', (0.4, 4.2, 0.0), 0.85, 120), ('debris', (-2.2, -4.1, 0.0), 0.75, 250),
             ('debris', (-5.1, 0.0, 0.0), 1.0, 160), ('debris', (3.0, -4.1, 0.0), 0.9, 15)]
    simmed = 0
    for k, (rec, p, sc_, rz) in enumerate(FIRES):
        sc_ *= rnd.uniform(0.92, 1.08)
        got = sim_fire(f'fire{k}', rec, o + Vector(p), col, lit, scale=sc_, rot=math.radians(rz), start=rnd.randint(0, 191),
                       energy=12 + 24 * sc_, seed=rnd.uniform(0, 20))
        if got is None:                                            # not baked: the procedural flame (quick looks, no setup)
            fire(f'fire{k}', o + Vector(p), sc_, col, lit, energy=18 + 38 * sc_, seed=rnd.uniform(0, 20))
        else:
            simmed += 1
    print('CAFE fires', len(FIRES), 'simulated', simmed)
    burn_cafe(col, o)
    smoke_layer = box('cafe_smoke_layer', (11.6, 9.6, 1.3), o + Vector((0, 0, 3.6)), smoke_material('cafe_smoke_layer_m', 7, 3.5, 'layer'), col)
    smoke_layer.visible_shadow = False
    smoke_layer['cine_ignore'] = True
    soot = material('soot', (0.02, 0.018, 0.016), rough=0.95)
    for k, (p, rot, sz) in enumerate((((-5.83, 2.0, 2.6), (math.radians(90), 0, math.radians(90)), (3.0, 3.0)),
                                      ((5.83, -1.5, 2.6), (math.radians(90), 0, math.radians(-90)), (3.4, 3.2)),
                                      ((1.6, 4.84, 2.4), (math.radians(90), 0, math.radians(180)), (3.0, 2.6)))):
        sm_ = plane(f'scorch{k}', sz[0], sz[1], o + Vector(p), soot, col, rot=rot)       # blackened wall above each wall fire
        sm_.visible_shadow = False
    light('cafe_key', 'AREA', o + Vector((0, -3, 3.9)), 20, (1.0, 0.7, 0.45), lit, size=3.0, rot=(math.radians(20), 0, 0))
    wl = light('cafe_window_light', 'AREA', o + Vector((-2.2, 4.4, 2.2)), 120, (0.4, 1.0, 0.55), lit, size=2.0,
               rot=(math.radians(-90), 0, 0))
    wl.visible_camera = wl.visible_glossy = wl.visible_transmission = False   # (the glass reflected it: a pale panel on the street)
    haze('haze_cafe', o + Vector((0, 0, 2.1)), (11.5, 9.5, 4.1), 0.012, (1.0, 0.7, 0.5), col)
    for l_ in lit.objects:                                         # lights light the set but never show as glowing quads
        if l_.type == 'LIGHT':
            l_.visible_camera = l_.visible_transmission = l_.visible_glossy = False   # (seen through the glass too)
    embers('embers_cafe', o + Vector((0, 0.3, 0.2)), (11, 9, 0), 900, col, seed=9, rise=3.8, period=110)
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
    # the two doors are made of falling code: SELL a doorway of red code, HOLD a doorway of green code, each word in its colour
    for name, x, word, tint in (('door_sell', -2.4, 'SELL', (1.0, 0.12, 0.08)), ('door_hold', 2.4, 'HOLD', (0.15, 1.0, 0.3))):
        d = screen(name, 1.25, 2.3, o + Vector((x, 3.0, 1.15)), (math.radians(90), 0, 0), col, 5.0, tint)
        nt = d.data.materials[0].node_tree                          # colour the code by its brightness (the rain frames are green:
        bw = nt.nodes.new('ShaderNodeRGBToBW')                      # tinting them red left almost nothing) over a faint glow
        nt.links.new(nt.nodes['rain'].outputs['Color'], bw.inputs[0])
        mix = next(n for n in nt.nodes if n.type == 'MIX_RGB')
        boost = nt.nodes.new('ShaderNodeMath')
        boost.operation = 'MULTIPLY_ADD'
        boost.inputs[1].default_value = 4.0
        boost.inputs[2].default_value = 0.025
        nt.links.new(bw.outputs[0], boost.inputs[0])
        nt.links.new(boost.outputs[0], mix.inputs[1])
        light(name + '_glow', 'AREA', o + Vector((x, 2.7, 1.2)), 140, tint, lit, size=1.2, rot=(math.radians(90), 0, 0))
        bpy.ops.object.text_add(location=o + Vector((x, 2.98, 2.55)), rotation=(math.radians(90), 0, 0))
        t = bpy.context.active_object
        t.name = name + '_word'
        t.data.body = word
        t.data.size = 0.5
        t.data.align_x = 'CENTER'
        t.data.extrude = 0.02
        t.data.materials.append(material(name + '_word_m', tint, emit=tint, strength=1.2))   # (brighter washed out to pastel)
        for c_ in list(t.users_collection):
            c_.objects.unlink(t)
        col.objects.link(t)
    light('white_key', 'AREA', o + Vector((0, -4, 7)), 900, (1, 1, 1), lit, size=8.0, rot=(math.radians(25), 0, 0))
    light('white_fill', 'AREA', o + Vector((0, 3, 6)), 400, (0.95, 0.97, 1.0), lit, size=10.0)
    haze('haze_white', o + Vector((0, 1, 3)), (16, 14, 6), 0.003, (1, 1, 1), col)
    return col


def episode1_stills(frames_dir, count=24):
    """Frames of Anon from episode 1 for the monitor wall (every Nth frame of the shots he is in)."""
    packed = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack', 'stills', 'f_*.jpg')))
    if len(packed) >= count:                                    # committed copies (episode 1's frames are not in git)
        return packed[:count]
    files = sorted(glob.glob(os.path.join(frames_dir, 'f_*.jpg')))
    return files[::max(1, len(files) // count)][:count]


def exhaust_material(name, col=(0.05, 1.0, 0.2), strength=5.0):
    """Rocket exhaust on a cone (local z -1..0, nozzle at the top): emission fading from the nozzle down, with a flickering
    noise core, mixed into transparency so the end of the flare dissolves instead of stopping in a hard edge."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    fade = nt.nodes.new('ShaderNodeMath')                           # 1 at the nozzle, 0 at the tail
    fade.operation = 'POWER'
    nt.links.new(sep.outputs['Z'], fade.inputs[0])
    fade.inputs[1].default_value = 4.0
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 6.0
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    _drive(noise.inputs['W'], 'default_value', 'frame / 3')
    flick = nt.nodes.new('ShaderNodeMapRange')
    flick.inputs['To Min'].default_value = 0.55
    flick.inputs['To Max'].default_value = 1.2
    nt.links.new(noise.outputs['Fac'], flick.inputs['Value'])
    fac = nt.nodes.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    fac.use_clamp = True
    nt.links.new(fade.outputs['Value'], fac.inputs[0])
    nt.links.new(flick.outputs['Result'], fac.inputs[1])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*col, 1.0)
    em.inputs['Strength'].default_value = strength
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fac.outputs['Value'], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def night_sky(mat):
    """The rooftop dome: city glow low on the horizon (warm-green) fading to a dark zenith, with soft clouds catching it.
    Replaces the flat near-black emission (the flight looks up into it for two seconds)."""
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    h = nt.nodes.new('ShaderNodeMapRange')                          # height on the dome: 0 at the horizon, 1 high up
    h.inputs['From Min'].default_value = -40.0
    h.inputs['From Max'].default_value = 700.0
    nt.links.new(sep.outputs['Z'], h.inputs['Value'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.11, 0.12, 0.07, 1)       # sodium-and-neon city glow
    els[1].position, els[1].color = 1.0, (0.012, 0.03, 0.024, 1)  # overhead: clouds still catch the city
    mid = els.new(0.3)
    mid.color = (0.04, 0.08, 0.06, 1)
    nt.links.new(h.outputs['Result'], ramp.inputs['Fac'])
    noise = nt.nodes.new('ShaderNodeTexNoise')                      # clouds
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 0.006
    noise.inputs['Detail'].default_value = 6.0
    noise.inputs['Roughness'].default_value = 0.6
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    _drive(noise.inputs['W'], 'default_value', 'frame / 900')
    cl = nt.nodes.new('ShaderNodeMapRange')
    cl.inputs['From Min'].default_value = 0.45
    cl.inputs['From Max'].default_value = 0.75
    cl.inputs['To Min'].default_value = 0.6
    cl.inputs['To Max'].default_value = 2.8
    nt.links.new(noise.outputs['Fac'], cl.inputs['Value'])
    flash = nt.nodes.new('ShaderNodeMath')                          # lightning: the scene keys inputs[1] (0 = no flash)
    flash.name = 'sky_flash'
    flash.operation = 'MULTIPLY_ADD'
    nt.links.new(cl.outputs['Result'], flash.inputs[0])
    flash.inputs[1].default_value = 0.0
    nt.links.new(cl.outputs['Result'], flash.inputs[2])
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(flash.outputs[0], em.inputs['Strength'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])


def spark_burst(name, centre, col, count=90, radius=0.9, seed=1, up=0.35, colour=(1.0, 0.55, 0.15), strength=30.0, size=0.007):
    """A burst of sparks: glowing specks thrown out from one point and falling (shape key 'burst', 0 = all at the centre,
    1 = flown out and dropped). The scene keys the shape key and the spark's scale (0 = hidden)."""
    rnd = random.Random(seed)
    mesh = bpy.data.meshes.new(name)
    pts = [(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01)) for _ in range(count)]
    mesh.from_pydata(pts, [], [])
    cloud = bpy.data.objects.new(name, mesh)
    col.objects.link(cloud)
    cloud.location = centre
    cloud.shape_key_add(name='Basis')
    kb = cloud.shape_key_add(name='burst')
    for i, v in enumerate(kb.data):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1) + up)).normalized()
        r = radius * rnd.uniform(0.35, 1.0)
        v.co = Vector(pts[i]) + d * r + Vector((0, 0, -0.45 * r * rnd.uniform(0.5, 1.0)))   # out, then falling
    m = material(name + '_m', colour, emit=colour, strength=strength)
    spark = bpy.data.objects.new(name + '_spark', bpy.data.meshes.new(name + '_spark'))
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size)
    bm.to_mesh(spark.data); bm.free()
    spark.data.materials.append(m)
    col.objects.link(spark)
    spark.parent = cloud
    cloud.instance_type = 'VERTS'
    for ob in (cloud, spark):
        ob['cine_ignore'] = True
        ob.visible_shadow = False
    return cloud, spark


# ---------------------------------------------------------------- set dressing: placed on real surfaces, checked
DRESSED = []                                             # (object, kind) for the placement check after the build
SKIP_RAY = ('haze', 'rain', 'smoke', 'fire', 'dust', 'embers', 'scorch', 'soot', 'ash_', 'cafe_smoke', 'L_', 'shockwave', 'spark')


ASSEMBLY_PAIRS = []                                     # (name, name): parts of one thing that touch on purpose
ASSEMBLIES = (('couch',), ('lamp_',), ('mini_fridge', 'fridge_'), ('dartboard',), ('shelf_',), ('side_',), ('crust',), ('cup_stack',),
              ('pie',), ('till',), ('clock',), ('extinguisher',), ('skylight',), ('crate', 'pallet'), ('dish',), ('elec_box', 'conduit'),
              ('jukebox',), ('cafe_tv',), ('mstack',), ('whiteboard',), ('traffic_cone',), ('butt',), ('fchair',), ('pcdesk',), ('wbench',), ('dumbbell',), ('clotheshorse',), ('dehumidifier',))


def _group(name):
    return next((k for k, g in enumerate(ASSEMBLIES) if name.startswith(g)), None)


_TREES = {}                                              # object name -> (world-space BVH, bbox min, bbox max)


def _tree(ob):
    """World-space BVH of a mesh object (cached; dropped when the object is moved by put/rest_on)."""
    hit = _TREES.get(ob.name)
    if hit is not None:
        return hit
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ob.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    if not vs or not polys:
        _TREES[ob.name] = (None, None, None)
        return _TREES[ob.name]
    mn = Vector([min(v[i] for v in vs) for i in range(3)])
    mx = Vector([max(v[i] for v in vs) for i in range(3)])
    _TREES[ob.name] = (BVHTree.FromPolygons(vs, polys), mn, mx)
    return _TREES[ob.name]


def surface_below(x, y, z_from, ignore=(), want_object=False):
    """Height of the first solid surface under (x, y), looking down from z_from. Rays go against cached world-space BVHs of
    the meshes whose bounds contain (x, y) (no scene re-evaluation per ray: the café's 38 simulated fire sequences made that
    slow); volumes, rain, decals and the ignored objects are never candidates."""
    best, best_ob = None, None
    org = Vector((x, y, z_from))
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.hide_render or ob in ignore or ob.name.startswith(SKIP_RAY) or max(ob.dimensions) > 60:
            continue
        mw = ob.matrix_world
        bb = [mw @ Vector(c) for c in ob.bound_box]
        if not (min(c.x for c in bb) - 1e-4 <= x <= max(c.x for c in bb) + 1e-4 and
                min(c.y for c in bb) - 1e-4 <= y <= max(c.y for c in bb) + 1e-4 and min(c.z for c in bb) <= z_from):
            continue
        t, mn, mx = _tree(ob)
        if t is None:
            continue
        loc, nrm, idx, dist = t.ray_cast(org, Vector((0, 0, -1)), 200.0)
        if loc is not None and (best is None or loc.z > best):
            best, best_ob = loc.z, ob
    return (best, best_ob) if want_object else best


def put(obj, x=None, y=None, z_from=None, kind='rest'):
    """Rest an object on the surface below it: its lowest vertex 1 mm above that surface."""
    bpy.context.view_layer.update()
    x = obj.location.x if x is None else x
    y = obj.location.y if y is None else y
    obj.location.x, obj.location.y = x, y
    z0 = surface_below(x, y, z_from if z_from is not None else obj.location.z + 0.05, ignore=(obj,) + tuple(obj.children_recursive))
    if z0 is not None:
        rest_on(obj, z0)
    DRESSED.append((obj, kind))
    return obj


def check_dressing(bounds):
    """Placement check: every dressed object rests on something (a ray from just above its lowest point finds a surface
    within 2 cm below it), sits inside its room (bounds: name prefix -> (xmin, xmax, ymin, ymax, zmax)), and none of its
    corners is inside a wall. Prints PLACE lines; returns the number of problems."""
    bad = 0
    support = {}
    bpy.context.view_layer.update()
    for ob, kind in DRESSED:
        if ob.name not in bpy.data.objects:
            continue
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices] if ob.type == 'MESH' and ob.data.vertices else \
            [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = min(v.z for v in vs)
        cx = sum(v.x for v in vs) / len(vs)
        cy = sum(v.y for v in vs) / len(vs)
        support[ob.name] = None
        if kind == 'rest':
            z0, sup = surface_below(cx, cy, lo + 0.005, ignore=(ob,), want_object=True)
            support[ob.name] = sup
            if z0 is None or lo - z0 > 0.02 or z0 - lo > 0.01:
                print('PLACE floating/sunk', ob.name, 'low', round(lo, 3), 'surface', None if z0 is None else round(z0, 3))
                bad += 1
        for pre, (x0, x1, y0, y1, z1) in bounds.items():
            if ob.name.startswith(pre):
                out = [v for v in vs if not (x0 <= v.x <= x1 and y0 <= v.y <= y1 and v.z <= z1)]
                if out:
                    print('PLACE through a wall', ob.name, len(out), 'corners outside')
                    bad += 1
    # intersections with other solid objects (touching a support 1 mm below does not count)
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()

    def tree(o_):
        try:
            return BVHTree.FromObject(o_, dg)
        except Exception:
            return None
    solids = [o_ for o_ in bpy.data.objects if o_.type == 'MESH' and not o_.hide_render and not o_.name.startswith(SKIP_RAY)
              and o_.data.vertices and max(o_.dimensions) < 30]
    for ob, kind in DRESSED:
        if ob.name not in bpy.data.objects or ob.type != 'MESH':
            continue
        t_ = tree(ob)
        if t_ is None:
            continue
        mn = Vector([min((ob.matrix_world @ Vector(c))[i] for c in ob.bound_box) for i in range(3)])
        mx = Vector([max((ob.matrix_world @ Vector(c))[i] for c in ob.bound_box) for i in range(3)])
        if kind == 'decal':                                       # a rug lies under the furniture standing on it
            continue
        g_ = _group(ob.name)
        for other in solids:
            if other is ob or other.parent is ob or ob.parent is other or other is support.get(ob.name):
                continue
            if g_ is not None and _group(other.name) == g_:           # the parts of one piece of furniture
                continue
            if (ob.name, other.name) in ASSEMBLY_PAIRS or (other.name, ob.name) in ASSEMBLY_PAIRS:
                continue
            omn = Vector([min((other.matrix_world @ Vector(c))[i] for c in other.bound_box) for i in range(3)])
            omx = Vector([max((other.matrix_world @ Vector(c))[i] for c in other.bound_box) for i in range(3)])
            if any(mx[i] < omn[i] or omx[i] < mn[i] for i in range(3)):
                continue
            t2 = tree(other)
            if t2 is not None and t_.overlap(t2):
                print('PLACE intersects', ob.name, 'x', other.name)
                bad += 1
    print('PLACE checked', len(DRESSED), 'problems', bad)
    return bad


def _txt(name, body, loc, rot, size, mat, col, align='CENTER', extrude=0.0):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    t = bpy.context.active_object
    t.name = name
    t.data.body = body
    t.data.size = size
    t.data.align_x = align
    t.data.extrude = extrude
    t.data.materials.append(mat)
    for c in list(t.users_collection):
        c.objects.unlink(t)
    col.objects.link(t)
    return t


def dress_basement(o):
    """Mom's basement, lived in: a sagging couch against the left wall with a side table, a lamp and cans on it, a metal
    shelf of junk against the back wall, a mini fridge, posters flat on the walls, a rug under the crew, cables to the CRT,
    cords for the two bare bulbs (they hung from nothing), a dartboard, a mug and a plate of pizza crusts on the floor."""
    col = collection('BASEMENT')
    rnd = random.Random(31)
    WX, WY = 9.8, 8.8                                              # inner wall faces: x = +-9.8, y = +-8.8; ceiling 4.95
    fab = material('couch_fabric', (0.22, 0.24, 0.16), rough=0.95)
    mxsets.add_bump(fab, 140.0, 0.25)
    # the couch: base, seat cushions, back, arms; against the left wall, facing the room (+x)
    cx, cy = -WX + 0.47, -2.6
    base = box('couch_base', (0.9, 2.3, 0.32), o + Vector((cx, cy, 0.5)), fab, col, bevel=0.03); put(base, z_from=o.z + 1)
    for k in range(3):
        cu = box(f'couch_cushion{k}', (0.66, 0.7, 0.16), o + Vector((cx + 0.1, cy - 0.74 + k * 0.74, 1.0)), fab, col, bevel=0.05)
        cu.rotation_euler = (rnd.uniform(-0.03, 0.03), rnd.uniform(-0.04, 0.0), rnd.uniform(-0.04, 0.04))
        put(cu, z_from=o.z + 2)
    back = box('couch_back', (0.24, 2.3, 0.55), o + Vector((-WX + 0.2, cy, 0.6)), fab, col, bevel=0.05)
    back.rotation_euler = (0, math.radians(-6), 0)                 # leaning back toward the wall, clear of it
    put(back, z_from=o.z + 2)
    for s_ in (-1, 1):
        ar = box(f'couch_arm{s_}', (0.9, 0.2, 0.55), o + Vector((cx, cy + s_ * 1.2, 0.6)), fab, col, bevel=0.05)
        put(ar, z_from=o.z + 2)
    bl = box('couch_blanket', (0.7, 0.9, 0.03), o + Vector((cx + 0.05, cy + 0.55, 2)), material('blanket', (0.45, 0.1, 0.12), rough=0.9),
             col, bevel=0.012)
    bl.rotation_euler = (0.04, -0.06, 0.25)
    put(bl)
    # side table at the couch's end with a lamp, energy drink cans and a controller
    wood = material('side_table', (0.32, 0.2, 0.11), rough=0.6)
    tx, ty = -WX + 0.4, cy - 1.75
    top = box('side_table_top', (0.6, 0.6, 0.04), o + Vector((tx, ty, 0.6)), wood, col)
    for k, (dx, dy) in enumerate(((-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25))):
        lg = box(f'side_table_leg{k}', (0.04, 0.04, 0.58), o + Vector((tx + dx, ty + dy, 0.29)), wood, col)
        put(lg, z_from=o.z + 0.3)
    top.location.z = o.z + 0.58 + 0.02
    lamp_m = material('lamp_base', (0.15, 0.15, 0.16), rough=0.4, metal=0.6)
    lb = cylinder('lamp_base', 0.08, 0.04, o + Vector((tx - 0.1, ty + 0.12, 1.5)), lamp_m, col, verts=20); put(lb)
    lp = cylinder('lamp_pole', 0.012, 0.42, o + Vector((tx - 0.1, ty + 0.12, 1.5)), lamp_m, col, verts=8); put(lp)
    shade_m = material('lamp_shade', (0.9, 0.78, 0.55), rough=0.8, emit=(1.0, 0.75, 0.45), strength=1.5)
    sh = cylinder('lamp_shade', 0.14, 0.18, o + Vector((tx - 0.1, ty + 0.12, 0)), shade_m, col, verts=24)
    sh.location.z = lp.location.z + 0.21 + 0.06
    mxsets.light('L_couch_lamp', 'POINT', sh.location + Vector((0, 0, -0.02)), 25, (1.0, 0.72, 0.42), collection('L_BASEMENT'),
                 size=0.1)
    can_m = material('energy_can', (0.1, 0.75, 0.25), rough=0.25, metal=0.8)
    for k in range(3):
        cn = cylinder(f'side_can{k}', 0.033, 0.12, o + Vector((tx + 0.1 + k * 0.08, ty - 0.12 + rnd.uniform(-0.05, 0.05), 1.5)),
                      can_m, col, verts=16)
        if k == 2:
            cn.rotation_euler = (math.radians(90), 0, rnd.uniform(0, 3))     # one empty, on its side
        put(cn)
    ctl = box('controller', (0.15, 0.1, 0.04), o + Vector((tx + 0.12, ty + 0.15, 1.5)), material('controller', (0.05, 0.05, 0.06), rough=0.4),
              col, bevel=0.015)
    ctl.rotation_euler = (0, 0, 0.5)
    put(ctl)
    # metal shelf against the back wall with boxes, paint cans, a toolbox and a jar of coins
    steel = material('shelf_steel', (0.42, 0.43, 0.42), rough=0.45, metal=0.85)
    sx, sy = 4.4, WY - 0.24
    for k, zz in enumerate((0.02, 0.62, 1.22, 1.82)):
        box(f'shelf_board{k}', (1.6, 0.45, 0.025), o + Vector((sx, sy, zz + 0.0125)), steel, col)
    for k, (dx, dy) in enumerate(((-0.79, -0.21), (0.79, -0.21), (-0.79, 0.21), (0.79, 0.21))):
        box(f'shelf_post{k}', (0.03, 0.03, 1.86), o + Vector((sx + dx, sy + dy, 0.93)), steel, col)
    box_m = material('cardboard', (0.55, 0.4, 0.24), rough=0.9)
    paint_m = material('paint_can', (0.7, 0.7, 0.72), rough=0.3, metal=0.7)
    items = [('box', (0.5, 0.36, 0.3), (-0.45, 0, 1)), ('box', (0.38, 0.3, 0.24), (0.3, 0.02, 1)), ('paint', None, (0.65, -0.05, 1)),
             ('paint', None, (-0.15, 0.0, 2)), ('paint', None, (0.05, 0.05, 2)), ('box', (0.6, 0.38, 0.4), (0.4, 0, 2)),
             ('tool', (0.45, 0.2, 0.2), (-0.4, 0, 3)), ('box', (0.42, 0.34, 0.28), (0.35, 0.0, 3)), ('jar', None, (-0.6, 0.05, 0)),
             ('box', (0.55, 0.38, 0.45), (0.3, 0.0, 0)), ('box', (0.4, 0.32, 0.3), (-0.2, 0.02, 0))]
    shelf_z = (0.02 + 0.025, 0.62 + 0.025, 1.22 + 0.025, 1.82 + 0.025)
    for k, (kind, size, (dx, dy, lev)) in enumerate(items):
        p_ = o + Vector((sx + dx, sy + dy, shelf_z[lev] + 0.4))
        if kind == 'box':
            it = box(f'shelf_box{k}', size, p_, box_m, col, bevel=0.005)
            it.rotation_euler = (0, 0, rnd.uniform(-0.08, 0.08))
        elif kind == 'paint':
            it = cylinder(f'shelf_paint{k}', 0.085, 0.19, p_, paint_m, col, verts=20)
        elif kind == 'tool':
            it = box(f'shelf_toolbox{k}', size, p_, material('toolbox', (0.7, 0.08, 0.06), rough=0.4, metal=0.4), col, bevel=0.01)
        else:
            it = cylinder(f'shelf_jar{k}', 0.07, 0.18, p_, material('jar', (0.75, 0.8, 0.75), rough=0.05), col, verts=20)
        h_ = size[2] if size else (0.19 if kind == 'paint' else 0.18)    # (dimensions are not updated yet here)
        it.location.z = o.z + shelf_z[lev] + 0.001 + h_ / 2
        DRESSED.append((it, 'rest'))
    # a mini fridge in the back-left, by the boxes, against the wall
    fr = box('mini_fridge', (0.55, 0.55, 0.85), o + Vector((-1.6, WY - 0.3, 0.5)), material('fridge', (0.85, 0.85, 0.82), rough=0.3),
             col, bevel=0.02); put(fr)
    hd = box('fridge_handle', (0.03, 0.03, 0.3), o + Vector((-1.4, WY - 0.592, 0.6)), steel, col)
    hd.location.z = fr.location.z + 0.15
    st_ = box('fridge_sticker', (0.18, 0.005, 0.12), o + Vector((-1.7, WY - 0.578, 0)), material('sticker', (0.95, 0.65, 0.1), rough=0.5),
              col)
    st_.location.z = fr.location.z + 0.1
    # posters, flat on the walls (1 cm off the concrete), and a dartboard
    paper = material('poster_paper', (0.92, 0.9, 0.84), rough=0.8)
    ink = material('poster_ink', (0.05, 0.6, 0.2), rough=0.6, emit=(0.05, 0.6, 0.2), strength=0.1)
    red = material('poster_red', (0.75, 0.06, 0.05), rough=0.6)
    # rotations: back wall (y = +8.8) faces -y: (90, 0, 0); right wall (x = +9.8) faces -x: (90, 0, -90). With these the
    # print's +x runs left-to-right for someone in the room (the first version flipped them 180 degrees: mirrored text)
    posters = [('HODL', (1.4, WY - 0.01, 2.6), (math.radians(90), 0, 0), ink),
               ('WAGMI', (-4.2, WY - 0.01, 2.4), (math.radians(90), 0, 0), red),
               ('TO THE MOON', (WX - 0.01, -1.5, 2.5), (math.radians(90), 0, math.radians(-90)), ink)]
    for k, (txt, p_, rot, m_) in enumerate(posters):
        pl = plane(f'poster{k}', 1.4 if len(txt) > 6 else 1.0, 0.75 if len(txt) > 6 else 1.3, o + Vector(p_), paper, col, rot=rot)
        bpy.context.view_layer.update()
        nrm = (pl.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
        t = _txt(f'poster_text{k}', txt, pl.location + nrm * 0.004, pl.rotation_euler, 0.2 if len(txt) > 6 else 0.3, m_, col)
        t.location.z -= 0.1 if len(txt) <= 6 else 0.07                 # (text sits on its baseline: centre it on the sheet)
        DRESSED.append((pl, 'wall'))
    dart_m = material('dartboard', (0.08, 0.08, 0.07), rough=0.8)
    db = cylinder('dartboard', 0.23, 0.04, o + Vector((WX - 0.02, 2.6, 1.75)), dart_m, col, rot=(0, math.radians(90), 0), verts=40)
    ring = cylinder('dartboard_ring', 0.1, 0.045, o + Vector((WX - 0.02, 2.6, 1.75)), red, col, rot=(0, math.radians(90), 0), verts=32)
    DRESSED.append((db, 'wall'))
    # a rug under the crew, cables from the CRT across the floor, crusts on a plate, a mug
    rug_m = material('rug', (0.2, 0.07, 0.05), rough=0.95)                  # worn dark red (it read pink under the bulbs)
    mxsets.add_bump(rug_m, 60.0, 0.2)
    rug = box('rug', (4.2, 3.0, 0.008), o + Vector((0.2, 0.0, 0.5)), rug_m, col)
    rug.rotation_euler = (0, 0, math.radians(8))
    put(rug, z_from=o.z + 1)
    DRESSED[-1] = (rug, 'decal')
    cab_m = material('cable', (0.03, 0.03, 0.03), rough=0.5)
    pts = [Vector((3.0, 2.0, 0)), Vector((2.2, 1.6, 0)), Vector((1.4, 1.9, 0)), Vector((0.6, 1.5, 0)), Vector((0.35, 2.1, 0))]
    cd = bpy.data.curves.new('crt_cable', 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = 0.008
    sp = cd.splines.new('NURBS'); sp.points.add(len(pts) - 1); sp.use_endpoint_u = True; sp.order_u = 3
    for p_, q_ in zip(sp.points, pts):
        z_ = surface_below(o.x + q_.x, o.y + q_.y, o.z + 1.0) or o.z
        p_.co = (o.x + q_.x, o.y + q_.y, z_ + 0.009, 1)
    cb = bpy.data.objects.new('crt_cable', cd); col.objects.link(cb); cd.materials.append(cab_m)
    plate = cylinder('crust_plate', 0.12, 0.012, o + Vector((-2.4, 1.6, 0.5)), material('plate', (0.92, 0.92, 0.9), rough=0.2), col, verts=28)
    put(plate)
    crust_m = material('crust', (0.62, 0.38, 0.14), rough=0.8)
    for k in range(3):
        cr = box(f'crust{k}', (0.09, 0.025, 0.02), o + Vector((-2.4 - 0.05 + k * 0.05, 1.6 + (0.03 if k == 1 else -0.02), 1)), crust_m,
                 col, bevel=0.008)
        cr.rotation_euler = (0, 0, 1.3 + k * 0.25)                    # side by side on the plate, not through each other
        put(cr)
    mug = cylinder('floor_mug', 0.045, 0.1, o + Vector((-2.1, 1.85, 1)), material('mug_b', (0.2, 0.35, 0.6), rough=0.3), col, verts=16)
    put(mug)
    # cords for the two bare bulbs: from the ceiling (4.95 m) down to each bulb's socket (they hung from nothing)
    cord_m = material('bulb_cord', (0.02, 0.02, 0.02), rough=0.6)
    for name in ('bulb_a', 'bulb_b'):
        b_ = bpy.data.objects.get(name)
        if b_ is None:
            continue
        top_, bot_ = o.z + 4.95, b_.location.z + 0.07
        cylinder(name + '_cord', 0.006, top_ - bot_, Vector((b_.location.x, b_.location.y, (top_ + bot_) / 2)), cord_m, col, verts=6)
        cylinder(name + '_socket', 0.025, 0.05, Vector((b_.location.x, b_.location.y, bot_ + 0.005)), cord_m, col, verts=12)
    return col


def dress_cafe(o):
    """The café's things, and what the fire did to them: on every table a plate, sauce bottles, a napkin holder (charred and
    slumped where the table burns); on the counter a till, a pie dome, a stack of cups; a stopped clock and an unused fire
    extinguisher on the walls; broken plates on the floor."""
    col = collection('CAFE')
    rnd = random.Random(41)
    burning_tables = {0: 1.0, 2: 0.85, 1: 0.5}                     # table index: how burnt (fire on tables 0 and 2, paper on 1)
    china = material('china', (0.93, 0.92, 0.88), rough=0.2)
    red = material('ketchup', (0.65, 0.04, 0.03), rough=0.25)
    yel = material('mustard', (0.85, 0.65, 0.05), rough=0.25)
    steel = bpy.data.materials.get('cafe_chrome')
    for k, (x, y) in enumerate(((-3.6, 0.6), (-3.6, -2.2), (-0.8, -2.6))):
        tk = {0: 0, 1: 2, 2: 1}[k]
        amt = burning_tables[tk]
        def m_(base, name):
            return char_material(f'char_{name}{k}', base, amt, embers=amt > 0.8, seed=k * 2.3) if amt > 0.4 else None
        pl = cylinder(f'plate{k}', 0.11, 0.012, o + Vector((x - 0.22, y - 0.12, 1.2)), m_((0.93, 0.92, 0.88), 'plate') or china, col, verts=28)
        put(pl)
        for j, (mat_, dx) in enumerate(((red, 0.18), (yel, 0.26))):
            b_ = cylinder(f'sauce{k}_{j}', 0.03, 0.17, o + Vector((x + dx, y + 0.22, 1.3)), m_(mat_.diffuse_color[:3], f'sauce{j}_') or mat_,
                          col, verts=14)
            if amt > 0.8:                                          # plastic bottles in the fire sag and lean
                b_.scale.z = rnd.uniform(0.6, 0.75)
                b_.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0)
            put(b_)
        nh = box(f'napkins{k}', (0.12, 0.07, 0.1), o + Vector((x - 0.05, y + 0.28, 1.3)), m_((0.8, 0.8, 0.82), 'napkins') or steel, col)
        put(nh)
    # the counter: a till, a pie under a glass dome, a stack of cups, a sugar pourer (counter top at 1.11 m)
    till = box('till', (0.42, 0.36, 0.22), o + Vector((0.8, 2.55, 1.5)), material('till', (0.18, 0.18, 0.2), rough=0.4, metal=0.3), col,
               bevel=0.02)
    put(till)
    disp = box('till_display', (0.2, 0.03, 0.12), o + Vector((0.8, 2.45, 1.5)), material('till_screen', (0.1, 0.5, 0.2),
               emit=(0.1, 0.8, 0.3), strength=1.5), col)
    disp.rotation_euler = (math.radians(-20), 0, 0)
    disp.location.z = till.location.z + 0.17
    stand = cylinder('pie_stand', 0.16, 0.02, o + Vector((3.4, 2.65, 1.5)), char_material('char_stand', (0.9, 0.9, 0.9), 0.4, False), col,
                     verts=28)
    put(stand)
    pie = cylinder('pie', 0.13, 0.04, o + Vector((3.4, 2.65, 1.5)), char_material('char_pie', (0.7, 0.45, 0.2), 0.75, True, 4), col, verts=28)
    put(pie)
    glass_m = material('dome_glass', (0.9, 0.9, 0.9), rough=0.05)
    glass_m.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.9
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.17, location=o + Vector((3.4, 2.65, 1.5)), segments=24, ring_count=12)
    dome = bpy.context.active_object
    dome.name = 'pie_dome'
    for c in list(dome.users_collection):
        c.objects.unlink(dome)
    col.objects.link(dome)
    bm = bmesh.new(); bm.from_mesh(dome.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.001], context='VERTS')   # a half dome
    bm.to_mesh(dome.data); bm.free()
    dome.data.materials.append(glass_m)
    dome.location.z = stand.location.z + 0.011
    for j in range(4):
        cp = cylinder(f'cup_stack{j}', 0.045, 0.09, o + Vector((1.5, 2.85, 1.5)), china, col, verts=16)
        cp.location.z = o.z + 1.11 + 0.001 + 0.045 + j * 0.06          # nested cups, each 6 cm above the last
    sg = cylinder('sugar', 0.04, 0.12, o + Vector((1.9, 2.4, 1.5)), glass_m, col, verts=16); put(sg)
    # walls: a stopped clock (right wall, inner face x = 5.85), a fire extinguisher on its bracket (left wall, x = -5.85)
    clock = cylinder('clock', 0.22, 0.04, o + Vector((5.83, 1.2, 2.9)), char_material('char_clock', (0.92, 0.9, 0.85), 0.55, False), col,
                     rot=(0, math.radians(90), 0), verts=36)
    for j, (ang, ln) in enumerate(((math.radians(-60), 0.12), (math.radians(160), 0.17))):   # stopped at the moment it started
        hd = box(f'clock_hand{j}', (0.005, 0.012, ln), o + Vector((5.805, 1.2, 2.9)), material('clock_hand', (0.02, 0.02, 0.02)), col)
        hd.rotation_euler = (ang, 0, 0)
        hd.location += Vector((0, -math.sin(ang) * ln / 2, math.cos(ang) * ln / 2))
    DRESSED.append((clock, 'wall'))
    ext_m = material('extinguisher', (0.75, 0.05, 0.04), rough=0.3, metal=0.2)
    ex = cylinder('extinguisher', 0.075, 0.5, o + Vector((-5.73, -0.8, 0.95)), ext_m, col, verts=20)   # (5 mm off its bracket)
    brk = box('extinguisher_bracket', (0.04, 0.12, 0.06), o + Vector((-5.83, -0.8, 1.05)), steel, col)
    DRESSED.append((ex, 'wall'))
    # broken plates on the floor (each shard flat on the tiles)
    for j in range(7):                                             # (on a jittered grid: random spots overlapped)
        sh = box(f'shard{j}', (rnd.uniform(0.04, 0.09), rnd.uniform(0.03, 0.06), 0.01),
                 o + Vector((-2.6 + (j % 4) * 0.32 + rnd.uniform(-0.06, 0.06), -1.5 + (j // 4) * 0.4 + rnd.uniform(-0.06, 0.06), 0.3)),
                 china, col)
        sh.rotation_euler = (0, 0, rnd.uniform(0, 3.1))
        put(sh)
    return col


def dress_rooftop(o):
    """The roof, at the edges (the action is within 7 m of the centre): a pallet of crates by the stair house, a satellite
    dish on its stand, an electrical box with conduit along the parapet, two skylights and a roof hatch."""
    col = collection('ROOFTOP')
    rnd = random.Random(51)
    metal = bpy.data.materials.get('roof_metal') or material('roof_metal2', (0.5, 0.52, 0.5), rough=0.45, metal=0.8)
    wood = material('pallet_wood', (0.45, 0.33, 0.2), rough=0.85)
    crate = material('crate', (0.3, 0.32, 0.26), rough=0.8)
    px, py = -7.6, -12.2
    pal = box('pallet', (1.2, 1.0, 0.14), o + Vector((px, py, 1.0)), wood, col); put(pal, z_from=o.z + 2)
    for j, (dx, dy, sz) in enumerate(((-0.28, -0.2, 0.5), (0.3, -0.18, 0.5), (0.0, 0.25, 0.45))):
        cr = box(f'crate{j}', (sz, sz, sz), o + Vector((px + dx, py + dy, 2)), crate, col, bevel=0.01)
        cr.rotation_euler = (0, 0, rnd.uniform(-0.15, 0.15))
        put(cr, z_from=o.z + 3)
    top = box('crate_top', (0.45, 0.45, 0.45), o + Vector((px - 0.1, py - 0.2, 3)), crate, col, bevel=0.01)
    top.rotation_euler = (0, 0, 0.3)
    put(top, z_from=o.z + 4)
    # satellite dish
    dx_, dy_ = 6.5, 13.2
    pole = cylinder('dish_pole', 0.05, 1.4, o + Vector((dx_, dy_, 2)), metal, col, verts=10); put(pole, z_from=o.z + 3)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(0, 0, 0), segments=24, ring_count=12)
    dish = bpy.context.active_object
    dish.name = 'dish'
    for c in list(dish.users_collection):
        c.objects.unlink(dish)
    col.objects.link(dish)
    bm = bmesh.new(); bm.from_mesh(dish.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > -0.3], context='VERTS')
    bm.to_mesh(dish.data); bm.free()
    dish.data.materials.append(metal)
    dish.rotation_euler = (math.radians(120), 0, math.radians(200))
    bpy.context.view_layer.update()
    rq = dish.rotation_euler.to_matrix()
    cap = Vector((0, 0, -0.5))                                      # the bowl's centre, in its own space (a cap of a sphere)
    top = Vector((o.x + dx_, o.y + dy_, pole.location.z + 0.7))   # the pole's top
    dish.location = top - rq @ cap + (rq @ Vector((0, 0, -1))) * 0.04   # bowl on the pole (it floated 45 cm off it)
    axis = (rq @ Vector((0, 0, 1))).normalized()                    # the feed arm, out of the bowl along its axis
    arm = cylinder('dish_arm', 0.012, 0.5, top + axis * 0.25, metal, col, verts=8)
    arm.rotation_mode = 'QUATERNION'
    arm.rotation_quaternion = axis.to_track_quat('Z', 'Y')
    # electrical box on the east parapet (inner face x = 16.5) and a conduit running down and along the roof
    eb = box('elec_box', (0.25, 0.6, 0.8), o + Vector((16.5 - 0.127, -6.0, 0.6)), material('elec', (0.55, 0.58, 0.5), rough=0.6), col)
    put(eb, z_from=o.z + 2)
    cd = cylinder('conduit', 0.03, 5.0, o + Vector((16.2, -6.0 - 2.8, 0)), metal, col, rot=(math.radians(90), 0, 0), verts=10)
    put(cd, z_from=o.z + 1)
    # skylights (glass on a curb) and a roof hatch
    glass = material('skylight', (0.15, 0.25, 0.22), rough=0.05, metal=0.2)
    for j, (x, y) in enumerate(((8.5, 3.5), (-9.5, 2.5))):
        curb = box(f'skylight_curb{j}', (1.6, 1.2, 0.3), o + Vector((x, y, 1)), material('curb', (0.3, 0.3, 0.28), rough=0.8), col)
        put(curb, z_from=o.z + 2)
        gl = box(f'skylight_glass{j}', (1.5, 1.1, 0.02), o + Vector((x, y, 0)), glass, col)
        gl.location.z = curb.location.z + 0.16
    hatch = box('roof_hatch', (0.9, 0.9, 0.35), o + Vector((-3.0, 12.5, 1)), material('hatch', (0.25, 0.27, 0.25), rough=0.6, metal=0.4),
                col, bevel=0.02)
    put(hatch, z_from=o.z + 2)
    return col


def wet_floor(mat, seed=0.0):
    """Rain on a flat roof: puddles (mirror-smooth, a shade darker) between wet gravel, the puddles shimmering with drops.
    World-position noise picks the puddles; animated 4D Voronoi bumps their normal (the drops), gravel stays matte-wet."""
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    if bsdf is None:
        return
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 0.35
    noise.inputs['Detail'].default_value = 3.0
    nt.links.new(geo.outputs['Position'], noise.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')                       # 1 = puddle, 0 = wet gravel
    ramp.color_ramp.elements[0].position = 0.46
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.52
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    rough = nt.nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = 0.42
    rough.inputs['To Max'].default_value = 0.03
    nt.links.new(ramp.outputs['Color'], rough.inputs['Value'])
    nt.links.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
    base = tuple(bsdf.inputs['Base Color'].default_value)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = base
    mix.inputs['B'].default_value = (base[0] * 0.55, base[1] * 0.55, base[2] * 0.55, 1.0)
    nt.links.new(ramp.outputs['Color'], mix.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    vor = nt.nodes.new('ShaderNodeTexVoronoi')                       # the drops: cells that re-form every few frames
    vor.voronoi_dimensions = '4D'
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 9.0
    nt.links.new(geo.outputs['Position'], vor.inputs['Vector'])
    _drive(vor.inputs['W'], 'default_value', f'frame / 5 + {seed}')
    amt = nt.nodes.new('ShaderNodeMath')
    amt.operation = 'MULTIPLY'
    nt.links.new(ramp.outputs['Color'], amt.inputs[0])
    amt.inputs[1].default_value = 0.25
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = 0.004
    nt.links.new(amt.outputs['Value'], bump.inputs['Strength'])
    nt.links.new(vor.outputs['Distance'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def rooftop_rain(col, centre, size=(30, 30), drops=2500, seed=3):
    """Falling rain: thin streaks vertex-instanced over a cloud that drops and wraps (driver on the cloud's z)."""
    rnd = random.Random(seed)
    mesh = bpy.data.meshes.new('rain_cloud')
    # the cloud falls 6 m and snaps back up. Every drop in the bottom 6 m has a twin 6 m above it, so the snap is invisible,
    # and the snap lands half-way between frames (frame + 0.5 on an 11-frame cycle), outside any motion-blur shutter
    half = [(rnd.uniform(-size[0] / 2, size[0] / 2), rnd.uniform(-size[1] / 2, size[1] / 2), rnd.uniform(0, 6)) for _ in range(drops // 2)]
    pts = half + [(x, y, z + 6) for x, y, z in half]
    mesh.from_pydata(pts, [], [])
    cloud = bpy.data.objects.new('rain_cloud', mesh)
    col.objects.link(cloud)
    cloud.location = centre
    _drive(cloud, 'location', f'{centre.z} - fmod(frame + 0.5, 11) * {6 / 11}', index=2)
    streak_m = material('rain_streak', (0.75, 0.9, 0.85), rough=0.1, emit=(0.6, 0.85, 0.75), strength=0.45)
    streak_m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.4   # see-through: a drop beside the lens
    streak_m.blend_method = 'BLEND'                                                   # is a faint smear, not a white bar
    streak = cylinder('rain_streak', 0.0028, 0.35, (0, 0, 0), streak_m, col, verts=4)
    streak.parent = cloud
    streak.visible_shadow = False
    cloud.instance_type = 'VERTS'
    cloud['cine_ignore'] = True
    streak['cine_ignore'] = True
    for ob in (cloud, streak):                                # slow-motion shots sample fractional frames, so the snap can
        try:                                                  # still fall inside a shutter: the streaks are drawn long
            ob.cycles.use_motion_blur = False                 # already, so the rain carries no object blur at all
        except AttributeError:
            pass
    return cloud


# ------------------------------------------------------------------------------------------------ second dressing pass
def _blob(name, radius, scale, loc, mat, col, seed=0, lumpy=0.12):
    """A soft, slumped shape (bean bag, bin bag, hoodie): a squashed sphere with a little noise in its surface."""
    ob = sphere(name, radius, loc, mat, col, scale=scale)
    rnd = random.Random(seed)
    for v in ob.data.vertices:
        v.co *= 1.0 + rnd.uniform(-lumpy, lumpy) * 0.5
        if v.co.z < -radius * 0.55:                                  # a flat bottom where it rests
            v.co.z = -radius * 0.55
    return ob


def _curve(name, pts, radius, mat, col, order=3):
    cd = bpy.data.curves.new(name, 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = radius; cd.bevel_resolution = 2
    sp = cd.splines.new('NURBS'); sp.points.add(len(pts) - 1); sp.use_endpoint_u = True; sp.order_u = min(order, len(pts))
    for p_, q_ in zip(sp.points, pts):
        p_.co = (q_[0], q_[1], q_[2], 1)
    ob = bpy.data.objects.new(name, cd); col.objects.link(ob); cd.materials.append(mat)
    return ob


def _floor_cable(name, o, pts, radius, mat, col):
    """A cable lying on whatever is under it (each control point dropped onto the surface below)."""
    out = []
    for x, y in pts:
        z_ = surface_below(o.x + x, o.y + y, o.z + 0.5)
        out.append((o.x + x, o.y + y, (z_ if z_ is not None else o.z) + radius + 0.001))
    return _curve(name, out, radius, mat, col)


def dress_basement_more(o):
    """Mom's basement, second pass: the ceiling's joists, a duct and pipes (a basement ceiling is never flat plaster), two
    high windows with streetlight in them, a whiteboard with the 'plan' and its chart, a bean bag, storage totes in the
    corner, a hoodie on the couch arm, sneakers by the couch, a bag of chips, a bin bag by the stairs."""
    col = collection('BASEMENT')
    rnd = random.Random(33)
    WX, WY, CZ = 9.8, 8.8, 4.95
    wood = material('joist_wood', (0.42, 0.3, 0.18), rough=0.85)
    mxsets.add_bump(wood, 30.0, 0.2)
    for k in range(14):                                            # joists along x, every 1.2 m (clear of the bulb cords)
        y = -8.2 + k * 1.2
        j = box(f'joist{k}', (2 * WX - 0.02, 0.06, 0.22), o + Vector((0, y, CZ - 0.111)), wood, col)
        DRESSED.append((j, 'wall'))
    duct_m = material('duct', (0.55, 0.56, 0.56), rough=0.35, metal=0.9)
    du = box('duct_main', (0.5, 14.0, 0.28), o + Vector((-6.5, -1.0, CZ - 0.22 - 0.144)), duct_m, col)   # across the joists, under them
    DRESSED.append((du, 'wall'))
    steel_m = material('board_frame', (0.7, 0.7, 0.72), rough=0.3, metal=0.8)
    copper = material('copper_pipe', (0.72, 0.38, 0.2), rough=0.3, metal=1.0)
    for k, (x, r) in enumerate(((3.5, 0.022), (3.65, 0.016))):     # wall to wall (they stopped in mid-air)
        pp = cylinder(f'ceiling_pipe{k}', r, 2 * WY - 0.02, o + Vector((x, 0.0, CZ - 0.22 - r - 0.002)), copper, col,
                      rot=(math.radians(90), 0, 0), verts=12)
        DRESSED.append((pp, 'wall'))
    # two high windows in the back wall, above the washers and above the shelf: streetlight comes in cold and blue
    frame_m = material('window_frame', (0.6, 0.6, 0.58), rough=0.6)
    for k, x in enumerate((-5.8, 5.6)):
        fr = box(f'base_window_frame{k}', (1.2, 0.06, 0.5), o + Vector((x, WY - 0.032, 4.35)), frame_m, col)
        gl = plane(f'base_window_glass{k}', 1.08, 0.38, o + Vector((x, WY - 0.064, 4.35)),
                   material(f'base_window_night{k}', (0.1, 0.15, 0.25), rough=0.1, emit=(0.35, 0.5, 0.8), strength=0.8), col,
                   rot=(math.radians(90), 0, 0))
        gl.visible_shadow = False
        mxsets.light(f'L_base_window{k}', 'AREA', o + Vector((x, WY - 0.15, 4.3)), 30, (0.55, 0.7, 1.0), collection('L_BASEMENT'),
                     size=1.0, rot=(math.radians(-70), 0, 0))
        DRESSED.append((fr, 'wall'))
    # the whiteboard on the right wall: THE PLAN, a chart that goes up and then very much down
    board = plane('whiteboard', 1.6, 1.0, o + Vector((WX - 0.014, -4.8, 1.9)), material('whiteboard', (0.9, 0.9, 0.88), rough=0.25), col,
                  rot=(math.radians(90), 0, math.radians(-90)))
    frm = box('whiteboard_frame', (0.012, 1.66, 1.06), o + Vector((WX - 0.007, -4.8, 1.9)), steel_m, col)
    DRESSED.append((frm, 'wall'))
    tray = box('whiteboard_tray', (0.06, 1.2, 0.02), o + Vector((WX - 0.031, -4.8, 1.36)), steel_m, col)
    marker_r = material('marker_red', (0.8, 0.05, 0.04), rough=0.5)
    marker_b = material('marker_blue', (0.05, 0.15, 0.7), rough=0.5)
    xw = o.x + WX - 0.02
    up = [(-0.7, -0.35), (-0.45, -0.2), (-0.3, -0.25), (-0.1, 0.05), (0.05, 0.0), (0.2, 0.3), (0.3, 0.33), (0.42, -0.38)]
    _curve('whiteboard_chart', [(xw, o.y - 4.8 - u, o.z + 1.9 + v) for u, v in up], 0.005, marker_r, col, order=2)
    _txt('whiteboard_title', 'THE PLAN', Vector((xw, o.y - 4.8 + 0.1, o.z + 2.22)), (math.radians(90), 0, math.radians(-90)), 0.14,
         marker_b, col)
    _txt('whiteboard_note', 'buy high', Vector((xw, o.y - 4.8 - 0.25, o.z + 1.52)), (math.radians(90), 0, math.radians(-90)), 0.08,
         marker_b, col)
    for k, m_ in enumerate((marker_r, marker_b)):
        mk = cylinder(f'whiteboard_marker{k}', 0.009, 0.12, o + Vector((WX - 0.03, -4.6 + k * 0.1, 1.5)), m_, col,
                      rot=(math.radians(90), 0, 0), verts=8)
        put(mk)
    # a bean bag by the right wall, a hoodie on the couch arm, sneakers by the couch, chips on a cushion
    bean = _blob('beanbag', 0.5, (1.0, 1.1, 0.7), o + Vector((WX - 1.3, -2.9, 1.0)), material('beanbag', (0.1, 0.12, 0.3), rough=0.8), col,
                 seed=3)
    put(bean, z_from=o.z + 2)
    arm = bpy.data.objects.get('couch_arm1')
    if arm is not None:
        hd = _blob('hoodie', 0.25, (1.0, 0.42, 0.28), o + Vector((-WX + 0.75, -2.6 + 1.2, 2.0)), material('hoodie', (0.3, 0.3, 0.32), rough=0.95),
                   col, seed=5, lumpy=0.2)
        hd.rotation_euler = (0, 0.1, 0.05)
        put(hd, z_from=o.z + 2)
    shoe_m = material('sneaker', (0.85, 0.85, 0.85), rough=0.6)
    for k in range(2):
        sn = box(f'sneaker{k}', (0.3, 0.11, 0.1), o + Vector((-WX + 1.25 + k * 0.04, -3.95 - k * 0.36, 0.5)), shoe_m, col, bevel=0.03)
        sn.rotation_euler = (0, 0, 0.3 + k * 0.25)
        put(sn)
    cushion = bpy.data.objects.get('couch_cushion0')
    if cushion is not None:
        ch = _blob('chips_bag', 0.11, (1.0, 0.75, 0.3), cushion.location + Vector((0.05, 0.05, 0.4)),
                   material('chips', (0.85, 0.15, 0.08), rough=0.3, metal=0.4), col, seed=9, lumpy=0.25)
        ch.rotation_euler = (0, 0, 0.6)
        put(ch, z_from=cushion.location.z + 0.5)
    # storage totes stacked in the front-left corner, a bin bag by the stairs
    tote_m = material('tote', (0.2, 0.35, 0.45), rough=0.4)
    lid_m = material('tote_lid', (0.08, 0.1, 0.12), rough=0.4)
    for k, (x, y) in enumerate(((-WX + 0.45, -WY + 0.4), (-WX + 1.25, -WY + 0.4), (-WX + 0.5, -WY + 0.42))):
        t_ = box(f'tote{k}', (0.62, 0.44, 0.36), o + Vector((x, y, 2.0 + k)), tote_m, col, bevel=0.02)
        t_.rotation_euler = (0, 0, rnd.uniform(-0.05, 0.05))
        put(t_, z_from=o.z + 3)
        ld = box(f'tote_lid{k}', (0.66, 0.48, 0.03), o + Vector((x, y, 0)), lid_m, col, bevel=0.01)
        ld.rotation_euler = t_.rotation_euler
        bpy.context.view_layer.update()
        ld.location.z = t_.location.z + 0.18 + 0.016
        ASSEMBLY_PAIRS.append((t_.name, ld.name))
    # the front of the room (it was bare floor): an old PC desk against the front wall, a weight bench nobody uses with
    # dumbbells and a kettlebell, a dehumidifier in the corner, a clothes horse with laundry drying on it
    dk = material('desk_laminate', (0.5, 0.42, 0.32), rough=0.55)
    dx_, dy_ = 3.4, -WY + 0.42
    dtop = box('pcdesk_top', (1.5, 0.72, 0.035), o + Vector((dx_, dy_, 0.74)), dk, col)
    for k, (ex, ey) in enumerate(((-0.72, -0.33), (0.72, -0.33), (-0.72, 0.33), (0.72, 0.33))):
        box(f'pcdesk_leg{k}', (0.04, 0.04, 0.722), o + Vector((dx_ + ex, dy_ + ey, 0.361)), dk, col)
    dtop.location.z = o.z + 0.722 + 0.0175 + 0.001
    pcm = material('pc_beige', (0.75, 0.72, 0.62), rough=0.5)
    mon = box('pcdesk_monitor', (0.42, 0.4, 0.36), o + Vector((dx_ - 0.15, dy_ - 0.08, 1.5)), pcm, col, bevel=0.02)
    put(mon)
    scr = plane('pcdesk_screen', 0.32, 0.25, o + Vector((dx_ - 0.15, dy_ + 0.121, 0)),
                material('pc_screen', (0.02, 0.1, 0.05), emit=(0.1, 0.9, 0.35), strength=0.6), col, rot=(math.radians(90), 0, math.radians(180)))
    scr.location.z = mon.location.z + 0.02
    kb = box('pcdesk_keyboard', (0.44, 0.15, 0.025), o + Vector((dx_ - 0.1, dy_ + 0.22, 1.5)), pcm, col, bevel=0.005); put(kb)
    ms = box('pcdesk_mouse', (0.06, 0.1, 0.03), o + Vector((dx_ + 0.25, dy_ + 0.22, 1.5)), pcm, col, bevel=0.012); put(ms)
    tw = box('pcdesk_tower', (0.2, 0.45, 0.42), o + Vector((dx_ + 0.5, dy_ - 0.05, 0.5)), pcm, col, bevel=0.01); put(tw, z_from=o.z + 0.6)
    cn_ = cylinder('pcdesk_can', 0.033, 0.12, o + Vector((dx_ + 0.55, dy_ + 0.05, 1.5)), bpy.data.materials.get('energy_can'), col, verts=16)
    put(cn_)
    oc = box('pcdesk_chair_seat', (0.5, 0.5, 0.08), o + Vector((dx_ - 0.1, dy_ + 0.75, 0.5)), material('office_chair', (0.08, 0.08, 0.09),
             rough=0.7), col, bevel=0.03)
    ocp = cylinder('pcdesk_chair_post', 0.03, 0.42, o + Vector((dx_ - 0.1, dy_ + 0.75, 0.21)), steel_m, col, verts=10)
    ocb = cylinder('pcdesk_chair_base', 0.28, 0.03, o + Vector((dx_ - 0.1, dy_ + 0.75, 0.015)), steel_m, col, verts=5)
    ocp.location.z = o.z + 0.03 + 0.21 + 0.001
    oc.location.z = ocp.location.z + 0.21 + 0.04 + 0.001
    ocback = box('pcdesk_chair_back', (0.46, 0.06, 0.5), o + Vector((dx_ - 0.1, dy_ + 0.98, 0)), oc.data.materials[0], col, bevel=0.03)
    ocback.rotation_euler = (math.radians(-8), 0, 0)
    ocback.location.z = oc.location.z + 0.04 + 0.25
    # weight bench and weights, out in the room's front-right
    bx_, by_ = 6.2, -6.0
    pad = box('wbench_pad', (0.3, 1.2, 0.08), o + Vector((bx_, by_, 0.46)), material('bench_vinyl', (0.06, 0.06, 0.07), rough=0.4), col,
              bevel=0.02)
    for k, ey in enumerate((-0.5, 0.5)):
        box(f'wbench_leg{k}', (0.36, 0.05, 0.42), o + Vector((bx_, by_ + ey, 0.21)), steel_m, col)
    pad.location.z = o.z + 0.42 + 0.04 + 0.001
    iron = material('iron', (0.12, 0.12, 0.13), rough=0.45, metal=0.9)
    for k, (x, y, rz) in enumerate(((bx_ + 0.6, by_ - 0.3, 0.2), (bx_ + 0.75, by_ + 0.05, -0.3))):
        bar = cylinder(f'dumbbell_bar{k}', 0.016, 0.36, o + Vector((x, y, 0.08)), steel_m, col, rot=(0, math.radians(90), rz), verts=8)
        bar.location.z = o.z + 0.075
        for j, s_ in enumerate((-1, 1)):
            w_ = cylinder(f'dumbbell_plate{k}_{j}', 0.075, 0.05, o + Vector((x, y, 0.0751)), iron, col, rot=(0, math.radians(90), rz), verts=16)
            w_.location.x += math.cos(rz) * 0.14 * s_
            w_.location.y += math.sin(rz) * 0.14 * s_
        DRESSED.append((bar, 'wall'))
    kb_ = sphere('kettlebell', 0.11, o + Vector((bx_ - 0.5, by_ + 0.7, 1.0)), iron, col); put(kb_)
    # a dehumidifier in the front-right corner, its little blue light on
    dh = box('dehumidifier', (0.38, 0.28, 0.6), o + Vector((WX - 0.3, -WY + 0.3, 0.5)), material('dehum', (0.9, 0.9, 0.88), rough=0.4), col,
             bevel=0.02)
    put(dh)
    led = sphere('dehumidifier_led', 0.008, dh.location + Vector((-0.1, 0.141, 0.22)), material('dehum_led', (0.1, 0.4, 1.0),
                 emit=(0.1, 0.4, 1.0), strength=8.0), col)
    # a clothes horse with laundry on it, between the couch and the totes
    hx, hy = -WX + 1.6, -6.6
    for k, ex in enumerate((-0.4, 0.4)):
        for j, tilt in enumerate((-0.18, 0.18)):
            cylinder(f'clotheshorse_leg{k}_{j}', 0.01, 1.15, o + Vector((hx + ex, hy + math.sin(tilt) * 0.55, 0.57)), steel_m, col,
                     rot=(tilt, 0, 0), verts=6)
    for j, (zz, dy) in enumerate(((1.05, 0.0), (0.75, 0.0))):
        cylinder(f'clotheshorse_rail{j}', 0.008, 0.82, o + Vector((hx, hy + dy, zz)), steel_m, col, rot=(0, math.radians(90), 0), verts=6)
    for j, (zz, tint, w) in enumerate(((1.05, (0.7, 0.1, 0.12), 0.32), (1.05, (0.15, 0.3, 0.6), 0.26), (0.75, (0.85, 0.85, 0.8), 0.3))):
        cl = box(f'clotheshorse_cloth{j}', (w, 0.012, 0.34), o + Vector((hx + (-0.2, 0.1, -0.1)[j], hy + (0.012 if j < 2 else -0.012),
                                                                          zz - 0.17 - 0.009)),
                 material(f'laundry{j}', tint, rough=0.95), col)
    bag = _blob('bin_bag', 0.35, (1.0, 0.9, 1.1), o + Vector((-6.8, 4.3, 1.5)), material('bin_bag', (0.02, 0.02, 0.025), rough=0.15), col,
                seed=12, lumpy=0.25)
    put(bag, z_from=o.z + 2)
    return col


def dress_cafe_more(o):
    """The café, second pass: a charred jukebox by the right wall, a burnt TV on its bracket in the corner, scorched
    pictures on the walls (one fallen on its face), a ceiling fan with a blade sagging from the heat, cutlery by the
    plates, a bin at the end of the counter."""
    col = collection('CAFE')
    rnd = random.Random(43)
    # jukebox: body, rounded top, a dead glass front
    jb = box('jukebox', (0.65, 0.8, 1.2), o + Vector((5.47, 0.4, 0.6)), char_material('char_jukebox', (0.6, 0.12, 0.08), 0.6, False, 7), col,
             bevel=0.03)
    put(jb)
    jt = cylinder('jukebox_top', 0.4, 0.65, o + Vector((5.47, 0.4, 0)), char_material('char_jukebox_top', (0.75, 0.55, 0.2), 0.7, True, 8), col,
                  rot=(0, math.radians(90), 0), verts=28)
    bpy.context.view_layer.update()
    jt.location.z = jb.location.z + 0.6 - 0.02
    jg = box('jukebox_glass', (0.01, 0.6, 0.5), o + Vector((5.47 - 0.33, 0.4, 0)), material('juke_glass', (0.05, 0.03, 0.02), rough=0.1), col)
    jg.location.z = jb.location.z + 0.18
    # the TV on its bracket in the right wall's corner above the counter end: case charred, screen cracked and dead
    tv = box('cafe_tv', (0.12, 0.9, 0.55), o + Vector((5.72, 2.4, 3.15)), char_material('char_tv', (0.12, 0.12, 0.13), 0.7, False, 9), col,
             bevel=0.01)
    tvs = plane('cafe_tv_screen', 0.84, 0.49, o + Vector((5.659, 2.4, 3.15)), material('tv_dead', (0.01, 0.01, 0.012), rough=0.05), col,
                rot=(math.radians(90), 0, math.radians(-90)))
    mxsets.add_bump(tvs.data.materials[0], 9.0, 0.8)                 # (a crazed, cracked screen)
    brk = box('cafe_tv_bracket', (0.07, 0.12, 0.12), o + Vector((5.815, 2.4, 3.15)), bpy.data.materials.get('cafe_chrome'), col)
    DRESSED.append((tv, 'wall'))
    # pictures on the walls, scorched; one has fallen on its face
    for k, (x, y, z, w, h, rz) in enumerate(((-5.834, -2.4, 2.2, 0.55, 0.42, 90), (-5.834, -1.3, 2.35, 0.4, 0.5, 90),
                                             (5.834, 3.4, 2.4, 0.6, 0.45, -90))):
        pf = box(f'cafe_picture{k}', (0.6, 0.03, 0.45), o + Vector((x, y, z)),
                 char_material(f'char_picture{k}', (0.85, 0.75, 0.55), 0.45 + 0.2 * k, k == 2, 10 + k), col)
        pf.scale = (w, 0.03, h)
        pf.rotation_euler = (0, 0, math.radians(rz))
        DRESSED.append((pf, 'wall'))
    fallen = box('cafe_picture_fallen', (0.5, 0.4, 0.03), o + Vector((-5.3, -1.75, 0.5)),
                 char_material('char_picture_fallen', (0.85, 0.75, 0.55), 0.6, False, 14), col)
    fallen.rotation_euler = (0, 0, 0.35)
    put(fallen)
    # ceiling fan: downrod from the ceiling, motor, four blades, one drooping (the heat softened it)
    fan_m = char_material('char_fan', (0.35, 0.25, 0.15), 0.55, False, 15)
    fx_, fy_ = 1.6, -2.0
    rod = cylinder('fan_rod', 0.015, 0.5, o + Vector((fx_, fy_, 4.15 - 0.25)), bpy.data.materials.get('cafe_chrome'), col, verts=8)
    mot = cylinder('fan_motor', 0.13, 0.14, o + Vector((fx_, fy_, 4.15 - 0.5 - 0.07)), fan_m, col, verts=20)
    for k in range(4):
        a_ = math.radians(20 + k * 90)
        bl = box(f'fan_blade{k}', (0.6, 0.14, 0.012), o + Vector((fx_ + math.cos(a_) * 0.43, fy_ + math.sin(a_) * 0.43, 4.15 - 0.53)), fan_m, col)
        droop = 0.45 if k == 1 else 0.06
        bl.rotation_euler = (0, 0, a_)
        bl.rotation_euler.rotate_axis('Y', droop)
        bl.location.z -= math.sin(droop) * 0.3
    # cutlery beside each plate, a bin at the end of the counter
    cut_m = char_material('char_cutlery', (0.6, 0.6, 0.62), 0.5, False, 16)
    for k, (x, y) in enumerate(((-3.6, 0.6), (-3.6, -2.2), (-0.8, -2.6))):
        for j, dx in enumerate((-0.37, -0.06)):
            c_ = box(f'cutlery{k}_{j}', (0.016, 0.19, 0.005), o + Vector((x + dx, y - 0.12 + rnd.uniform(-0.02, 0.02), 1.3)), cut_m, col)
            c_.rotation_euler = (0, 0, rnd.uniform(-0.12, 0.12))
            put(c_)
    bin_ = cylinder('cafe_bin', 0.2, 0.62, o + Vector((-0.35, 2.6, 0.5)), char_material('char_bin', (0.3, 0.3, 0.3), 0.4, False, 17), col, verts=20)
    put(bin_)
    return col


def dress_rooftop_more(o):
    """The roof, second pass: coping on the parapet, a pipe run on wooden sleepers along the north edge, a lamp over the
    stair door, someone's smoking spot (a folding chair, a bucket of butts), a ladder up the water tank, a traffic cone."""
    col = collection('ROOFTOP')
    rnd = random.Random(53)
    conc = material('coping', (0.38, 0.38, 0.36), rough=0.7)
    for k, (cx, cy, sx, sy) in enumerate(((0, 16.75, 34.1, 0.62), (0, -16.75, 34.1, 0.62), (16.75, 0, 0.62, 32.86), (-16.75, 0, 0.62, 32.86))):
        box(f'coping{k}', (sx, sy, 0.06), o + Vector((cx, cy, 1.1 + 0.031)), conc, col)
    # the pipe run: sleepers every 2 m, two pipes lying on them
    sl_m = material('sleeper', (0.25, 0.2, 0.14), rough=0.9)
    pipe_m = material('roof_pipe', (0.45, 0.47, 0.45), rough=0.5, metal=0.7)
    xs = [-8.0 + 2.0 * k for k in range(9)]
    top = 0
    for k, x in enumerate(xs):
        s_ = box(f'sleeper{k}', (0.15, 0.6, 0.12), o + Vector((x, 15.6, 1.0)), sl_m, col)
        put(s_, z_from=o.z + 1)
        top = s_.location.z + 0.06
    for j, (dy, r) in enumerate(((-0.13, 0.07), (0.15, 0.05))):
        pp = cylinder(f'roof_pipe{j}', r, 17.0, o + Vector((0.0, 15.6 + dy, 0)), pipe_m, col, rot=(0, math.radians(90), 0), verts=16)
        pp.location.z = top + r + 0.001
        DRESSED.append((pp, 'rest'))
    # a bulkhead lamp over the stair door (door at x -10.2, face y = -9.5) and its warm light on the wet roof
    lamp = cylinder('stair_lamp', 0.1, 0.09, o + Vector((-10.2, -9.5 + 0.047, 2.45)), material('stair_lamp_m', (1.0, 0.8, 0.5),
                    emit=(1.0, 0.75, 0.4), strength=6.0), col, rot=(math.radians(90), 0, 0), verts=16)
    DRESSED.append((lamp, 'wall'))
    mxsets.light('L_stair_lamp', 'POINT', o + Vector((-10.2, -9.2, 2.4)), 60, (1.0, 0.72, 0.4), collection('L_ROOFTOP'), size=0.12)
    # the smoking spot: a folding chair beside the door, a bucket of sand and butts next to it
    chm = material('folding_chair', (0.18, 0.22, 0.2), rough=0.5, metal=0.6)
    cx, cy = -8.4, -8.6
    seat = box('fchair_seat', (0.42, 0.4, 0.03), o + Vector((cx, cy, 0.46)), chm, col)
    for k, (dx, dy) in enumerate(((-0.19, -0.17), (0.19, -0.17), (-0.19, 0.17), (0.19, 0.17))):
        lg = cylinder(f'fchair_leg{k}', 0.012, 0.445, o + Vector((cx + dx, cy + dy, 0.2225)), chm, col, verts=8)
        put(lg, z_from=o.z + 0.5)
    seat.location.z = o.z + 0.445 + 0.016 + 0.001
    for k, dx in enumerate((-0.19, 0.19)):                          # the back's two uprights (the rear legs carry on up)
        cylinder(f'fchair_upright{k}', 0.012, 0.8, o + Vector((cx + dx, cy - 0.215, 0.4)), chm, col, verts=8)
    bk = box('fchair_back', (0.42, 0.03, 0.32), o + Vector((cx, cy - 0.2, 0.46 + 0.016 + 0.17)), chm, col)
    bucket = cylinder('butt_bucket', 0.13, 0.26, o + Vector((cx + 0.55, cy + 0.15, 1.0)), material('bucket', (0.55, 0.12, 0.08), rough=0.4,
                      metal=0.5), col, verts=18)
    put(bucket)
    sand = cylinder('butt_sand', 0.12, 0.01, bucket.location + Vector((0, 0, 0.13 + 0.006)), material('sand', (0.6, 0.55, 0.45), rough=1.0), col,
                    verts=18)
    butt_m = material('butt', (0.9, 0.85, 0.75), rough=0.8)
    for k in range(5):
        a_ = rnd.uniform(0, 6.28); r_ = rnd.uniform(0.02, 0.08)
        bt = cylinder(f'butt{k}', 0.004, 0.03, sand.location + Vector((math.cos(a_) * r_, math.sin(a_) * r_, 0.012)), butt_m, col,
                      rot=(rnd.uniform(0.3, 1.0), 0, a_), verts=6)
    # ladder up the water tank's west side (tank x 9.3..12.7, y 9.8..13.2, from 4 m to 7 m)
    lad = material('ladder', (0.4, 0.42, 0.4), rough=0.5, metal=0.8)
    lx = 9.3 - 0.08
    for k, y in enumerate((11.2, 11.7)):
        cylinder(f'tank_ladder_rail{k}', 0.02, 6.95, o + Vector((lx, y, 3.475)), lad, col, verts=8)   # (stops under the tank's roof)
    for k in range(22):
        cylinder(f'tank_ladder_rung{k}', 0.013, 0.5, o + Vector((lx, 11.45, 0.3 + k * 0.3)), lad, col, rot=(math.radians(90), 0, 0), verts=8)
    # a traffic cone left by the electrical box
    cone_m = material('cone', (1.0, 0.3, 0.02), rough=0.5)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.16, radius2=0.03, depth=0.6, location=o + Vector((15.2, -3.6, 1.0)))
    cn = bpy.context.active_object
    cn.name = 'traffic_cone'
    for c_ in list(cn.users_collection):
        c_.objects.unlink(cn)
    col.objects.link(cn)
    cn.data.materials.append(cone_m)
    cn.location.z += 3.0                                           # (out of the way while its base is put down)
    cb = box('traffic_cone_base', (0.38, 0.38, 0.03), o + Vector((15.2, -3.6, 1.0)), cone_m, col)
    put(cb)
    put(cn, z_from=cb.location.z + 0.5)                            # the cone stands on its base
    return col


def dress_white_more(o, stills=None):
    """The white room, second pass: old monitors stacked on the floor at both ends of the wall, turned toward the room,
    a few dead, and their cables running across the white floor to the wall."""
    col = collection('WHITE')
    rnd = random.Random(13)
    case_m = bpy.data.materials.get('monitor_case') or material('monitor_case2', (0.82, 0.8, 0.76), rough=0.5)
    dead = material('monitor_dead', (0.03, 0.035, 0.035), rough=0.1)
    stills = stills or []
    k = 0
    for side in (-1, 1):
        x0, ang = side * 7.1, math.radians(side * -28)
        rq = Matrix.Rotation(ang, 3, 'Z')
        slots = [(-0.7, 0, 0), (0.7, 0, 0), (0.0, 0, 1)]              # two on the floor, one on top between them
        for j, (u, _, lev) in enumerate(slots):
            p_ = o + Vector((x0, 5.9, 0)) + rq @ Vector((u, 0, 0))
            m = box(f'mstack{side}_{j}', (1.3, 0.8, 0.92), p_ + Vector((0, 0, 0.6 + lev * 1.5)), case_m, col, bevel=0.04)
            m.rotation_euler = (0, 0, ang + rnd.uniform(-0.03, 0.03))
            put(m, z_from=o.z + 0.6 + lev * 1.5 + 0.8)
            bpy.context.view_layer.update()
            if stills and (j + side) % 3:
                scr_m = mxsets.image_material(f'mstack_img{side}_{j}', stills[(k * 5 + 3) % len(stills)], emit=1.2)
            else:
                scr_m = dead
            k += 1
            fw = m.matrix_world.to_quaternion() @ Vector((0, -1, 0))
            s = plane(f'mstack_screen{side}_{j}', 1.08, 0.72, m.location + fw * 0.405, scr_m, col,
                      rot=(math.radians(90), 0, m.rotation_euler.z))
            s.visible_shadow = False
            s['monitor'] = True
    cab = material('white_cable', (0.04, 0.04, 0.045), rough=0.45)
    for k, pts in enumerate(([(-4.6, 6.75), (-5.0, 6.1), (-5.6, 5.75), (-6.4, 5.6)], [(4.6, 6.75), (5.0, 6.1), (5.6, 5.75), (6.4, 5.6)],
                             [(-1.0, 6.75), (-1.6, 5.2), (-2.2, 3.6), (-2.4, 3.08)], [(1.0, 6.75), (1.7, 5.3), (2.2, 3.7), (2.4, 3.08)])):
        _floor_cable(f'white_cable{k}', o, pts, 0.018, cab, col)
    return col
