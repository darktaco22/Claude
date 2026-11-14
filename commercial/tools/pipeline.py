"""Pipeline automation helpers, written after Blender Studio's "Scripting for Artists" course (Sybren Stüvel).

Free chapters were studied from their subtitles. The three "tech" chapters on F-curves, bone renaming and batch
rendering are subscriber-only, so those functions are my own implementations of the topics, not the course's code.

Style rules taken from the course and applied here:
- Use the context you are given; never reach for bpy.context inside a function that receives one.
- Keep the data-block a `new()` call returns; never look it up again by the name you asked for.
- Never change a collection while looping over it: loop over a copy.
- Guard clauses first (`if not x: return`), main work un-indented at the bottom.
- Catch the specific exception (KeyError, RuntimeError), never a bare `except`.
- Avoid operators (`bpy.ops`) where a data call exists: faster and independent of selection and mode.
"""
import json
import pathlib

import bpy


# ---------------------------------------------------------------------------- collections (chapters 6, 12)

def ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    """Return the scene's child collection called `name`, creating and linking it if needed."""
    try:
        return scene.collection.children[name]
    except KeyError:
        pass
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    """Unlink `obj` from every collection it is in and link it into `target`."""
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    target.objects.link(obj)


def link_collections(scene, blend_path: str, prefix: str, into: bpy.types.Collection, link: bool = True) -> list:
    """Link (or append) every collection in `blend_path` whose name starts with `prefix`, one instancing empty
    each. Running it twice adds only what is new."""
    with bpy.data.libraries.load(blend_path, link=link) as (data_from, data_to):
        data_to.collections = [name for name in data_from.collections if name.startswith(prefix)]

    empties = []
    for collection in data_to.collections:
        if collection is None or collection.name in into.objects:
            continue
        empty = bpy.data.objects.new(collection.name, None)
        empty.instance_type = 'COLLECTION'
        empty.instance_collection = collection
        into.objects.link(empty)
        empties.append(empty)
    return empties


def link_from_json(scene, json_path: str) -> dict:
    """Build a set from a description file:
    {"collections": {"rocks": {"link": [{"file": "//env/rocks.blend", "prefix": "EN-rock_"}]}}}"""
    with open(bpy.path.abspath(json_path)) as infile:
        link_info = json.load(infile)

    result = {}
    for collection_name, collection_info in link_info['collections'].items():
        into = ensure_collection(scene, collection_name)
        result[collection_name] = []
        for entry in collection_info['link']:
            result[collection_name] += link_collections(scene, bpy.path.abspath(entry['file']), entry['prefix'], into)
    return result


# ---------------------------------------------------------------------------- renaming

def rename_objects(objects, replacements: dict) -> int:
    """Mass-rename: replace each key of `replacements` found in an object's name. Returns how many changed."""
    changed = 0
    for obj in objects:
        new_name = obj.name
        for old, new in replacements.items():
            new_name = new_name.replace(old, new)
        if new_name == obj.name:
            continue
        obj.name = new_name
        changed += 1
    return changed


def prefix_bones(armature_obj: bpy.types.Object, prefix: str) -> int:
    """Prefix every bone of an armature and the matching vertex groups of the meshes it deforms, so two rigs can
    be joined without name clashes. Animation F-curves follow, because Blender fixes data paths on bone rename."""
    renamed = {}
    for bone in armature_obj.data.bones:
        if bone.name.startswith(prefix):
            continue
        old_name = bone.name
        bone.name = prefix + old_name
        renamed[old_name] = bone.name      # keep what Blender actually named it

    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.find_armature() != armature_obj:
            continue
        for group in obj.vertex_groups:
            if group.name in renamed:
                group.name = renamed[group.name]
    return len(renamed)


# ---------------------------------------------------------------------------- animation data

def iter_fcurves(action: bpy.types.Action, data_path_end: str = '', index: int = -1):
    """All F-curves of an action, optionally only those whose path ends with e.g. 'location' and/or one axis."""
    for fcurve in action.fcurves:
        if data_path_end and not fcurve.data_path.endswith(data_path_end):
            continue
        if index >= 0 and fcurve.array_index != index:
            continue
        yield fcurve


def offset_fcurve(fcurve: bpy.types.FCurve, value: float = 0.0, frames: float = 0.0) -> None:
    """Move a whole curve up/down and/or in time, handles included."""
    for key in fcurve.keyframe_points:
        key.co.x += frames
        key.co.y += value
        key.handle_left.x += frames
        key.handle_left.y += value
        key.handle_right.x += frames
        key.handle_right.y += value
    fcurve.update()


def retime_action(action: bpy.types.Action, factor: float, pivot: float = 1.0) -> None:
    """Speed an action up or down around `pivot` (factor 0.5 = twice as fast)."""
    for fcurve in action.fcurves:
        for key in fcurve.keyframe_points:
            for point in (key.co, key.handle_left, key.handle_right):
                point.x = pivot + (point.x - pivot) * factor
        fcurve.update()


def sample_fcurve(fcurve: bpy.types.FCurve, frames) -> list:
    """Values of a curve at any frames without moving the timeline (much faster than scene.frame_set)."""
    return [fcurve.evaluate(frame) for frame in frames]


# ---------------------------------------------------------------------------- batch processing

def purge_orphans() -> None:
    """Free everything that is no longer used. Needed between items of a long batch or memory keeps growing."""
    for _ in range(4):
        if not bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True):
            break


def batch_render_models(scene, folder: str, out_dir: str, pattern: str = '*.glb', importer=None, limit: int = 0):
    """Render every model file in `folder` to one image each: import, frame, render, remove, purge.
    Already rendered images are skipped, so an interrupted batch can simply be run again."""
    importer = importer or (lambda path: bpy.ops.import_scene.gltf(filepath=str(path)))
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    paths = sorted(pathlib.Path(folder).glob(pattern))
    for path in paths[:limit or None]:
        target = out_dir / (path.stem + '.png')
        if target.exists():
            continue
        before = set(bpy.data.objects)
        importer(path)
        imported = [obj for obj in bpy.data.objects if obj not in before]

        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        done.append(target)

        for obj in imported:
            bpy.data.objects.remove(obj)
        purge_orphans()
    return done
