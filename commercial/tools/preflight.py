"""Checks to run before a long render, after Blender Studio's shot-delivery checklist.

    import preflight
    problems = preflight.check(scene, first, last, sample_frames=(1, 600, 1339))
    preflight.report(problems)      # prints; raises SystemExit(2) on errors so a batch job stops early

A 7-hour render that fails at hour 5 on a missing texture is the thing this exists to prevent.
"""
import os

import bpy


def check(scene: bpy.types.Scene, first: int = None, last: int = None, sample_frames=()) -> list:
    """Return a list of (level, message); level is 'ERROR' or 'WARN'."""
    problems = []
    first = scene.frame_start if first is None else first
    last = scene.frame_end if last is None else last

    if scene.camera is None:
        problems.append(('ERROR', 'scene has no active camera'))
    if last < first:
        problems.append(('ERROR', f'frame range {first}-{last} is empty'))

    for image in bpy.data.images:
        if image.source not in {'FILE', 'SEQUENCE', 'MOVIE'} or image.packed_file:
            continue
        if not os.path.exists(bpy.path.abspath(image.filepath)):
            problems.append(('ERROR', f'image missing on disk: {image.name} -> {image.filepath}'))

    for library in bpy.data.libraries:
        if not os.path.exists(bpy.path.abspath(library.filepath)):
            problems.append(('ERROR', f'linked library missing: {library.filepath}'))

    for volume in bpy.data.volumes:
        if volume.filepath and not os.path.exists(bpy.path.abspath(volume.filepath)):
            problems.append(('ERROR', f'volume file missing: {volume.filepath}'))

    for obj in scene.objects:
        if obj.type == 'MESH' and not obj.hide_render and obj.data.materials and None in list(obj.data.materials):
            problems.append(('WARN', f'{obj.name} has an empty material slot (renders pink or default)'))
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object is None:
                problems.append(('ERROR', f'{obj.name}: armature modifier has no armature'))
            if modifier.type == 'NODES' and modifier.node_group is None:
                problems.append(('WARN', f'{obj.name}: geometry-nodes modifier has no node group'))

    if scene.render.engine == 'CYCLES':
        if not scene.cycles.use_denoising and scene.cycles.samples < 64:
            problems.append(('WARN', f'{scene.cycles.samples} samples without denoising will be noisy'))
        if not scene.render.use_persistent_data:
            problems.append(('WARN', 'use_persistent_data is off: several seconds lost on every frame'))
        lights = [o for o in scene.objects if o.type == 'LIGHT' and not o.hide_render]
        if not lights and (scene.world is None or not scene.world.use_nodes):
            problems.append(('ERROR', 'no lights and no world: frames will be black'))

    out_dir = os.path.dirname(bpy.path.abspath(scene.render.filepath)) or '.'
    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as error:
            problems.append(('ERROR', f'cannot create output folder {out_dir}: {error}'))
    stat = os.statvfs(out_dir if os.path.isdir(out_dir) else '.')
    free_gb = stat.f_bavail * stat.f_frsize / 1e9
    if free_gb < 2.0:
        problems.append(('ERROR' if free_gb < 0.5 else 'WARN', f'only {free_gb:.1f} GB free for output'))

    camera = scene.camera
    keep = scene.frame_current
    for frame in sample_frames:
        scene.frame_set(frame)
        if camera is None:
            break
        dof = camera.data.dof
        if dof.use_dof and dof.focus_object is None and dof.focus_distance < 0.05:
            problems.append(('WARN', f'frame {frame}: focus distance is {dof.focus_distance:.3f} m'))
        location = camera.matrix_world.translation
        if any(abs(value) > 1e5 or value != value for value in location):
            problems.append(('ERROR', f'frame {frame}: camera position is invalid {tuple(location)}'))
    scene.frame_set(keep)
    return problems


def report(problems: list, stop_on_error: bool = True) -> bool:
    for level, message in problems:
        print(f'PREFLIGHT {level}: {message}')
    errors = [message for level, message in problems if level == 'ERROR']
    print(f'PREFLIGHT {len(errors)} errors, {len(problems) - len(errors)} warnings')
    if errors and stop_on_error:
        raise SystemExit(2)
    return not errors
