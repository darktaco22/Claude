"""Visual proof of cine.py: two stand-in figures in a small yard, each preset shot at start / middle / end.
Run: blender -b -P cine_demo.py -- OUT_DIR   (about 2 min on 4 cores; writes cine_demo.jpg in this folder)"""
import os
import subprocess
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cine  # noqa: E402

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp/cine_demo'
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 12
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 640, 360
sc.view_settings.view_transform = 'AgX'


def material(name, rgb, rough=0.6, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*rgb, 1)
        b.inputs['Emission Strength'].default_value = emit
    return m


def add(prim, loc, scale, mat, **kw):
    getattr(bpy.ops.mesh, prim)(location=loc, **kw)
    o = bpy.context.object
    o.scale = scale
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def figure(x, y, heading, colour):
    """A 1.7 m stand-in: body, head, two eyes and a nose that show where it faces."""
    import math
    body = material('body' + str(x), colour)
    white = material('eye', (0.9, 0.9, 0.9), 0.3)
    dark = material('pupil', (0.02, 0.02, 0.02), 0.2)
    add('primitive_cylinder_add', (x, y, 0.6), (0.28, 0.22, 0.6), body, vertices=32)
    add('primitive_uv_sphere_add', (x, y, 1.5), (0.24, 0.24, 0.26), body)
    h = math.radians(heading)
    fwd = Vector((math.sin(h), math.cos(h), 0))
    side = Vector((math.cos(h), -math.sin(h), 0))
    for s in (-1, 1):
        p = Vector((x, y, 1.56)) + fwd * 0.2 + side * 0.09 * s
        add('primitive_uv_sphere_add', p, (0.05, 0.05, 0.05), white)
        add('primitive_uv_sphere_add', p + fwd * 0.04, (0.025, 0.025, 0.025), dark)
    add('primitive_uv_sphere_add', Vector((x, y, 1.47)) + fwd * 0.24, (0.04, 0.04, 0.05), body)


add('primitive_plane_add', (0, 0, 0), (40, 40, 1), material('ground', (0.16, 0.3, 0.12), 0.9))
post = material('post', (0.55, 0.42, 0.3))
for i in range(-12, 13):                                   # a fence and a row of posts give parallax
    add('primitive_cube_add', (i * 1.2, 6.0, 0.5), (0.06, 0.06, 0.5), post)
for i, (x, y) in enumerate([(-5, -4), (4.5, -5), (-7, 3), (7, 2.5), (2.5, 9), (-3, 10)]):
    add('primitive_cylinder_add', (x, y, 1.2), (0.15, 0.15, 1.2), post)
    add('primitive_uv_sphere_add', (x, y, 2.8), (1.1, 1.1, 1.0), material('leaf' + str(i), (0.12, 0.35, 0.1)))
add('primitive_cube_add', (-2.5, 4.0, 1.0), (1.2, 0.6, 1.0), material('shed', (0.6, 0.2, 0.15)))
add('primitive_uv_sphere_add', (1.6, 3.5, 0.6), (0.3, 0.3, 0.3), material('lamp', (1.0, 0.7, 0.3), emit=3.0))

figure(0.0, 0.0, 180.0, (0.85, 0.75, 0.2))                 # A faces -y, toward B
figure(0.0, -2.0, 0.0, (0.25, 0.45, 0.85))                 # B faces +y, toward A

world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
sky = world.node_tree.nodes.new('ShaderNodeTexSky')
sky.sun_elevation = 0.35
sky.sun_rotation = 2.3
world.node_tree.links.new(sky.outputs[0], world.node_tree.nodes['Background'].inputs[0])
world.node_tree.nodes['Background'].inputs[1].default_value = 0.35
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (0.9, 0.0, 2.6)
sc.collection.objects.link(sun)

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
WHERE = {'a': ((0.0, 0.0, 0.0), 180.0), 'b': ((0.0, -2.0, 0.0), 0.0)}


def where(name, t):
    return WHERE[name]


cov = cine.dialogue('a', 'b')
SHOTS = [
    ('establish (crane down)', cine.establish('a')),
    ('two-shot', cov['two']),
    ('OTS on A', cov['ots_a']),
    ('OTS on B', cov['ots_b']),
    ('CU A', cov['cu_a']),
    ('hero (low push)', cine.hero('a')),
    ('arc 70 deg', dict(subject='a', size='MS', move='arc', amount=70, bearing=20, lens=45, frame='left', fstop=2.4)),
    ('dolly zoom', cine.vertigo('a')),
    ('dutch + rack focus A->B', dict(subject='a', size='MCU', bearing=-150, lens=70, dutch=10, frame='right', fstop=1.6,
                                     focus=['rack', 'b', 'a', 0.2, 0.8])),
]
tiles = []
for i, (label, shot) in enumerate(SHOTS):
    shot, note = cine.solve(shot, where, sc)
    print(f'solve {label}: {note}')
    for j, u in enumerate((0.0, 0.5, 1.0)):
        cine.place(cam, shot, u, 0.0, where, sc)
        path = os.path.join(OUT, f's{i}_{j}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        tiles.append((path, f'{label}  u={u}'))

# labelled 3-wide sheet (one row per shot) with ffmpeg
inputs = []
for path, label in tiles:
    inputs += ['-i', path]
filters = ''.join(
    f"[{k}:v]drawtext=text='{label}':x=10:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55[t{k}];"
    for k, (_, label) in enumerate(tiles))
layout = '|'.join(f'{(k % 3) * 640}_{(k // 3) * 360}' for k in range(len(tiles)))
filters += ''.join(f'[t{k}]' for k in range(len(tiles))) + f'xstack=inputs={len(tiles)}:layout={layout}'
sheet = os.path.join(HERE, 'cine_demo.jpg')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', filters, '-q:v', '4', sheet], check=True)
print('sheet', sheet)
