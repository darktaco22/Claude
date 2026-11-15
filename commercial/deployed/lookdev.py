"""Lighting test stills:  blender -b --factory-startup -P lookdev.py -- hold|yard OUT.png"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import assets
import sets

what, out = sys.argv[sys.argv.index('--') + 1:][:2]
W = os.environ.get('W', os.path.expanduser('~/dep_work'))
LIB = os.environ.get('LIB', os.path.expanduser('~/tools/chars.blend'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = int(os.environ.get('SAMPLES', '12'))
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 50
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
sc.render.threads_mode = 'FIXED'
sc.render.threads = 4
sets.world(os.path.expanduser('~/tools/assets/kloppenheim_06_puresky/kloppenheim_06_puresky_2k.exr'), strength=float(os.environ.get('SKY', '0.6')),
           rotation_deg=float(os.environ.get('SKYROT', '49.4')))

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.dof.use_dof = True

if what == 'hold':
    ship = sets.build_ship(W + '/tex')
    ship['hinge'].rotation_euler.x = math.radians(float(os.environ.get('RAMP', '-14')))
    for name in ('red', 'green'):
        mat, lamp = ship['lenses'][name]
        on = name == os.environ.get('JUMP', 'green')
        mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 8.0 if on else 0.0
        lamp.data.energy = 90.0 if on else 0.0
    cast = [('walter', (0.1, 1.2), 0), ('cupsey', (-1.3, 2.4), 90), ('ket', (1.3, 1.8), -90), ('chillguy', (1.3, 3.0), -90),
            ('lmao', (-1.3, 3.6), 90), ('chillhouse', (-1.2, 0.6), 90), ('dope', (1.3, 0.4), -90), ('pudgy', (-1.3, -0.8), 90)]
    chars = assets.load_many(LIB, [c[0] for c in cast], sc.collection)
    for char, (uid, (x, y), heading) in zip(chars, cast):
        for root in char['roots']:
            root.location = (x, y, 0)
            root.rotation_mode = 'XYZ'
            root.rotation_euler = (0, 0, math.radians(heading))
        arm = char['armature']
        arm.animation_data_create()
        arm.animation_data.action = char['clips']['idle']
    sets.sun(heading_deg=float(os.environ.get('SUN', '180')), elevation_deg=9, energy=5.0)
    if os.environ.get('NOHAZE'):
        ship['haze'].hide_render = True
    view = os.environ.get('VIEW', 'wide')
    if view == 'wide':
        cam.location = (0.0, -4.6, 1.5)
        target = Vector((0.0, 3.0, 1.3))
        cam.data.lens = 24
    elif view == 'sarge':
        cam.location = (-0.5, 3.6, 1.2)
        target = Vector((0.1, 1.2, 1.35))
        cam.data.lens = 50
    else:
        cam.location = (0.3, 4.0, 1.35)
        target = Vector((-1.3, 2.4, 1.0))
        cam.data.lens = 70
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.dof.focus_distance = (target - cam.location).length
    cam.data.dof.aperture_fstop = 2.8
    sc.frame_set(30)

sc.render.filepath = out
bpy.ops.render.render(write_still=True)
