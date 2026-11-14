"""Character library: every game character in one .blend, one collection each, with its facts stored on it.

Build once:   blender -b -P assets.py -- build MODELS_DIR UNITS_JSON LIB.blend
Use:          import assets;  char = assets.load(LIB, 'pepe', scene.collection)

Why (from Scripting for Artists, chapters 11 and 12): a prepared collection is uniform (smoothed, leftovers
removed, clips named `uid:clip`) and custom properties keep each asset's origin, height and clip lengths with it.
Measured: it is NOT faster than glTF import for a few characters, because every call reopens the 54 MB library
(6 characters: glTF 0.9 s, six `load` calls 2.7 s). Use `load_many` to open the library once.
Characters are appended (not linked) so their armatures can be animated freely.
"""
import json
import pathlib
import sys

import bpy

PREFIX = 'CH-'


def build(models_dir: str, units_json: str, lib_path: str) -> int:
    units = json.loads(pathlib.Path(units_json).read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    count = 0
    for uid, info in units.items():
        path = pathlib.Path(models_dir) / f'{uid}.glb'
        if not path.exists():
            continue
        before = set(bpy.data.objects)
        actions_before = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(path))
        imported = [obj for obj in bpy.data.objects if obj not in before]

        collection = bpy.data.collections.new(PREFIX + uid)
        scene.collection.children.link(collection)
        collection['source'] = path.name
        collection['height'] = info['height']
        collection['clips'] = json.dumps({name: clip['dur'] for name, clip in info['clips'].items()})

        for obj in imported:
            if obj.name.startswith('Icosphere'):       # exporter leftovers
                bpy.data.objects.remove(obj)
                continue
            for old in list(obj.users_collection):
                old.objects.unlink(obj)
            collection.objects.link(obj)
            if obj.type == 'MESH':
                for polygon in obj.data.polygons:
                    polygon.use_smooth = True
        for action in set(bpy.data.actions) - actions_before:
            action.use_fake_user = True
            action['unit'] = uid
            action.name = f'{uid}:{action.name.split("_")[0]}'
        count += 1
    bpy.ops.wm.save_as_mainfile(filepath=lib_path, compress=True)
    return count


def names(lib_path: str) -> list:
    with bpy.data.libraries.load(lib_path) as (data_from, _):
        return sorted(name[len(PREFIX):] for name in data_from.collections if name.startswith(PREFIX))


def load(lib_path: str, uid: str, parent: bpy.types.Collection, height: float = 0.0) -> dict:
    """Append one character. Returns its collection, armature, clips by name and native height.
    `height` rescales the character (0 keeps the game's size)."""
    return load_many(lib_path, [uid], parent, height)[0]


def load_many(lib_path: str, uids: list, parent: bpy.types.Collection, height: float = 0.0) -> list:
    """Append several characters with the library opened once. The same id may appear more than once."""
    with bpy.data.libraries.load(lib_path, link=False) as (data_from, data_to):
        missing = [uid for uid in uids if PREFIX + uid not in data_from.collections]
        if missing:
            raise KeyError(f'{missing} not in {lib_path}')
        data_to.collections = [PREFIX + uid for uid in uids]
        wanted = set(uids)
        data_to.actions = [name for name in data_from.actions if name.split(':')[0] in wanted]
    actions = [action for action in data_to.actions if action]
    return [_finish(uid, collection, actions, parent, height) for uid, collection in zip(uids, data_to.collections)]


def _finish(uid: str, collection, actions: list, parent, height: float) -> dict:
    parent.children.link(collection)
    data_to_actions = [action for action in actions if action.get('unit') == uid]

    armature = next(obj for obj in collection.objects if obj.type == 'ARMATURE')
    clips = {action.name.split(':')[1].split('.')[0]: action for action in data_to_actions}
    if armature.animation_data:
        armature.animation_data.action = None
    roots = [obj for obj in collection.objects if obj.parent is None]
    native = collection['height']
    if height:
        for root in roots:
            root.scale = root.scale * (height / native)
    return {'id': uid, 'collection': collection, 'armature': armature, 'clips': clips, 'height': height or native,
            'roots': roots}


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    if args[0] == 'build':
        print('BUILT', build(*args[1:4]), 'characters')
