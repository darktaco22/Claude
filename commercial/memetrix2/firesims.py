"""Simulated fires for the café (Blender's Mantaflow gas solver), one per kind of fuel, baked to OpenVDB.

    blender -b --factory-startup -P firesims.py -- OUT_DIR [NAME ...]     (idempotent: a finished bake is kept)

Real fires look different because they burn different things: a vinyl booth smoulders with a lazy, sooty flame, grease on
a counter throws tall bright tongues, paper flickers fast and small, a curtain burns as a sheet climbing the wall, a pile
of debris burns as many separate tongues. Each recipe here is a different fuel source (the shape that emits fuel, how much,
how hot) and different combustion settings (burn rate, flame vorticity, smoke). The scene places several instances of
these on the burning objects, each scaled, turned and started at its own time, so no two fires in the room are alike.

Each recipe is simulated in its own small domain with its source at the origin, standing on z = 0.
Bake time: about 2 min per recipe on one machine; bakes are deterministic (only file metadata differs between runs).
"""
import json
import os
import sys
import time

import bpy

WARM = 40                                        # frames before the loop starts (the fire builds up from nothing)
LOOP = 192                                       # 8 s loop; the scene crossfades two copies half a loop apart (seamless)
FRAMES = int(os.environ.get('FIRE_FRAMES', WARM + LOOP))
RES = 64

# name: domain size (x, y, z), domain centre z, source shapes [(kind, size, location, rotation)], settings
RECIPES = {
    # a wooden table top burning: a broad, steady fire
    'table': dict(dom=(1.8, 1.8, 2.6), src=[('cyl', (0.5, 0.5, 0.05), (0, 0, 0.05), (0, 0, 0))],
                  fuel=1.0, temp=1.2, burn=0.75, vort=0.35, fvort=0.5, smoke=1.0, alpha=1.0, beta=1.0),
    # a vinyl booth (seat and back): slow, rolling, sooty
    'booth': dict(dom=(2.0, 1.6, 2.6), src=[('box', (1.1, 0.45, 0.08), (0, 0, 0.1), (0, 0, 0)),
                                            ('box', (1.1, 0.1, 0.5), (0, 0.25, 0.45), (0, 0, 0))],
                  fuel=1.4, temp=0.9, burn=0.5, vort=0.5, fvort=0.35, smoke=2.2, alpha=1.2, beta=0.8),
    # spilled grease along the counter: tall, bright, fast tongues
    'grease': dict(dom=(2.6, 1.2, 2.6), src=[('box', (2.0, 0.18, 0.04), (0, 0, 0.03), (0, 0, 0))],
                   fuel=1.0, temp=2.2, burn=0.95, vort=0.2, fvort=0.8, smoke=0.6, alpha=0.8, beta=1.6),
    # paper (napkins, a menu): small, quick flicker
    'paper': dict(dom=(0.9, 0.9, 1.4), src=[('box', (0.22, 0.16, 0.02), (0, 0, 0.02), (0, 0, 0.3))],
                  fuel=0.7, temp=1.4, burn=1.0, vort=0.6, fvort=1.0, smoke=0.5, alpha=1.0, beta=1.2),
    # a curtain / wallpaper sheet: fire climbing a vertical surface
    'sheet': dict(dom=(2.0, 1.2, 3.4), src=[('box', (1.4, 0.04, 2.2), (0, 0.4, 1.15), (0, 0, 0))],
                  fuel=0.9, temp=1.3, burn=0.8, vort=0.3, fvort=0.6, smoke=1.4, alpha=1.0, beta=1.0),
    # a pile of debris on the floor: several separate sources, many tongues
    'debris': dict(dom=(2.2, 2.2, 2.8), src=[('box', (0.35, 0.25, 0.15), (-0.35, -0.2, 0.08), (0, 0, 0.4)),
                                             ('box', (0.25, 0.4, 0.1), (0.3, 0.15, 0.05), (0, 0, -0.3)),
                                             ('cyl', (0.12, 0.12, 0.3), (0.05, -0.35, 0.15), (0, 1.2, 0)),
                                             ('box', (0.2, 0.2, 0.25), (-0.1, 0.4, 0.12), (0, 0, 0.8))],
                   fuel=1.1, temp=1.3, burn=0.7, vort=0.45, fvort=0.6, smoke=1.6, alpha=1.0, beta=1.0),
    # the coffee machine: a small, very hot electrical fire
    'machine': dict(dom=(1.0, 1.0, 1.8), src=[('box', (0.3, 0.25, 0.05), (0, 0, 0.03), (0, 0, 0))],
                    fuel=0.6, temp=2.6, burn=1.0, vort=0.25, fvort=0.9, smoke=1.8, alpha=0.8, beta=1.8),
}


def bake(name, r, out):
    path = os.path.join(out, name)
    done = os.path.join(path, 'DONE.json')
    if os.path.exists(done):
        print('KEEP', name)
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 24
    sc.frame_start, sc.frame_end = 1, FRAMES
    dx, dy, dz = r['dom']
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, dz / 2 - 0.02))
    dom = bpy.context.active_object
    dom.name = 'domain'
    dom.scale = (dx, dy, dz)                          # (left as object scale: with it applied, the adaptive domain crashed)
    pieces = []
    for kind, size, loc, rot in r['src']:
        if kind == 'cyl':
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=1.0, location=loc, rotation=rot)
        else:
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        o = bpy.context.active_object
        o.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        pieces.append(o)
    bpy.ops.object.select_all(action='DESELECT')            # one flow object (several flow objects crashed the solver)
    for o in pieces:
        o.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    if len(pieces) > 1:
        bpy.ops.object.join()
    src = bpy.context.active_object
    f = src.modifiers.new('fluid', 'FLUID')
    f.fluid_type = 'FLOW'
    fs = f.flow_settings
    fs.flow_type = 'FIRE'
    fs.flow_behavior = 'INFLOW'
    fs.flow_source = 'MESH'
    fs.surface_distance = 0.6
    fs.fuel_amount = r['fuel']
    fs.temperature = r['temp']
    fs.subframes = 1
    src.hide_render = True
    # (the domain is set up after its fire source: set up first, it sometimes initialised without the fire grids and the
    # solver crashed on a missing grid)
    mod = dom.modifiers.new('fluid', 'FLUID')
    mod.fluid_type = 'DOMAIN'
    d = mod.domain_settings
    d.domain_type = 'GAS'
    d.resolution_max = RES
    d.cache_type = 'ALL'
    d.cache_directory = path
    d.cache_data_format = 'OPENVDB'
    d.openvdb_cache_compress_type = 'BLOSC'
    d.openvdb_data_depth = '16'
    d.cache_frame_start, d.cache_frame_end = 1, FRAMES
    d.use_adaptive_domain = os.environ.get('FIRE_ADAPT', '0') == '1'   # (an adaptive grid's offset is not in the VDB: placement lost)
    d.vorticity = r['vort']
    d.flame_vorticity = r['fvort']
    d.burning_rate = r['burn']
    d.flame_smoke = r['smoke']
    d.flame_ignition = 1.25
    d.flame_max_temp = 1.75
    d.alpha, d.beta = r['alpha'], r['beta']
    d.use_dissolve_smoke = True                       # smoke thins out on its way up (the room's own smoke does the rest)
    d.dissolve_speed = 40
    d.use_dissolve_smoke_log = True
    t0 = time.time()
    bpy.context.view_layer.objects.active = dom
    with bpy.context.temp_override(object=dom, active_object=dom):
        bpy.ops.fluid.bake_all()
    files = sorted(f for f in os.listdir(os.path.join(path, 'data')) if f.endswith('.vdb'))
    meta = dict(name=name, frames=FRAMES, warm=WARM, loop=LOOP, res=RES, files=len(files), secs=round(time.time() - t0, 1),
                pattern='data/fluid_data_####.vdb', dom=r['dom'],
                origin=(-dx / 2, -dy / 2, -0.02))      # the VDB's (0,0,0) is the domain's lower corner (fixed grid)
    with open(done, 'w') as fh:
        json.dump(meta, fh)
    print('BAKED', meta, flush=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = args[0] if args else os.path.join(os.environ.get('W', '/tmp'), 'fire_sims')
    names = args[1:] or list(RECIPES)
    os.makedirs(out, exist_ok=True)
    for n in names:
        bake(n, RECIPES[n], out)
    print('FIRESIMS-DONE')
