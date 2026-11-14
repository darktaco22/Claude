"""Casting sheet: one lit portrait of every character in the library, then one labelled contact sheet.

    blender -b -P casting.py -- LIB.blend ASSET_DIR OUT_DIR

Uses the toolkit end to end: character library, sky HDRI, light rig, pre-flight check, resumable batch loop.
"""
import math
import os
import pathlib
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets
import lightrig
import pipeline
import polyhaven
import preflight


def setup_scene(asset_dir: str) -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.use_persistent_data = False        # scene content changes every item
    scene.render.resolution_x, scene.render.resolution_y = 360, 450
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Punchy'

    world = bpy.data.worlds.new('World')
    scene.world = world
    world.use_nodes = True
    environment = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    environment.image = bpy.data.images.load(polyhaven.fetch(asset_dir, 'hdri', 'kloppenheim_06_puresky', '2k'))
    background = world.node_tree.nodes['Background']
    world.node_tree.links.new(environment.outputs[0], background.inputs[0])
    background.inputs[1].default_value = 0.5
    scene.render.film_transparent = True

    bpy.ops.mesh.primitive_plane_add(size=60)
    floor = bpy.context.object
    floor.is_shadow_catcher = True

    camera = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 85
    return scene


def frame_character(camera, height: float) -> None:
    distance = height * 3.9
    camera.location = Vector((distance * 0.35, -distance, height * 0.62))
    target = Vector((0, 0, height * 0.52))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()


def render_all(lib_path: str, asset_dir: str, out_dir: str) -> list:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(asset_dir)
    rendered = []
    for uid in assets.names(lib_path):
        target = out / f'{uid}.png'
        if target.exists():
            continue
        character = assets.load(lib_path, uid, scene.collection)
        height = character['height']
        if 'idle' in character['clips']:
            character['armature'].animation_data_create()
            character['armature'].animation_data.action = character['clips']['idle']
        scene.frame_set(12)
        frame_character(scene.camera, height)
        rig = lightrig.rig((0, 0, 0), scene.camera, height=height, mood='day', name='cast')
        if not rendered:
            scene.render.filepath = str(target)
            preflight.report(preflight.check(scene, 12, 12, sample_frames=(12,)))

        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        rendered.append(uid)

        for light in rig.values():
            bpy.data.objects.remove(light)
        for obj in list(character['collection'].objects):
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(character['collection'])
        pipeline.purge_orphans()
    return rendered


if __name__ == '__main__':
    lib, asset_dir, out_dir = sys.argv[sys.argv.index('--') + 1:][:3]
    print('CAST rendered', len(render_all(lib, asset_dir, out_dir)))
