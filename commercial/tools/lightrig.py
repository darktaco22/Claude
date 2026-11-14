"""Character lighting rig after Blender Studio's four light types: key, key-soft, fill, rim (+ eye highlight).

    import lightrig
    rig = lightrig.rig(subject_location, camera, height=1.7, key_side=-1, mood='dawn')
    lightrig.eye_light(camera, subject_location, height=1.7)     # small catch-light near the lens

Colours live in MOODS so every shot of a sequence shares them (Blender Studio keeps them in one library file).
Angles are measured around the subject relative to the camera: 0 = at camera, 180 = behind subject.
"""
import bpy, math
from mathutils import Vector

MOODS = {
    #            key              key_soft           fill               rim
    'dawn':  ((1.0, 0.78, 0.55), (1.0, 0.85, 0.7), (0.55, 0.68, 1.0), (1.0, 0.72, 0.45)),
    'day':   ((1.0, 0.96, 0.9),  (1.0, 0.97, 0.94), (0.7, 0.82, 1.0),  (1.0, 0.98, 0.95)),
    'night': ((0.6, 0.72, 1.0),  (0.65, 0.75, 1.0), (0.25, 0.3, 0.5),  (0.75, 0.85, 1.0)),
    'fire':  ((1.0, 0.5, 0.18),  (1.0, 0.6, 0.3),  (0.3, 0.35, 0.6),  (1.0, 0.4, 0.1)),
}


def _area(name, loc, target, size, power, color, col):
    d = bpy.data.lights.new(name, 'AREA'); d.shape = 'DISK'; d.size = size; d.energy = power; d.color = color
    o = bpy.data.objects.new(name, d); col.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def rig(subject, cam, height=1.7, key_side=-1, mood='dawn', power=1.0, name='rig', rim=True):
    """Lights scale with the subject height, so the same call works for a 1.7 m hero or a 6 m giant."""
    col = bpy.data.collections.get(name + '.lighting') or bpy.data.collections.new(name + '.lighting')
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    s = Vector(subject); h = height
    tgt = s + Vector((0, 0, h * 0.7))
    v = Vector((cam.location.x - s.x, cam.location.y - s.y, 0)).normalized()
    def at(angle_deg, elev_deg, dist):
        a = math.radians(angle_deg); e = math.radians(elev_deg)
        d = Vector((v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a), 0))
        return tgt + d * dist * h * math.cos(e) + Vector((0, 0, dist * h * math.sin(e)))
    kc, ksc, fc, rc = MOODS[mood]
    w = power * h * h   # watts scale with area lit
    out = {
        'key':      _area(name + '.key', at(45 * key_side, 35, 3.0), tgt, 0.6 * h, 110 * w, kc, col),
        'key_soft': _area(name + '.key_soft', at(25 * key_side, 20, 3.0), tgt, 2.2 * h, 35 * w, ksc, col),
        'fill':     _area(name + '.fill', at(-50 * key_side, 5, 3.2), tgt, 3.0 * h, 8 * w, fc, col),
    }
    if rim:
        out['rim'] = _area(name + '.rim', at(-155 * key_side, 35, 3.0), tgt, 0.5 * h, 1100 * w, rc, col)
        out['rim2'] = _area(name + '.rim2', at(155 * key_side, 15, 3.0), tgt, 0.5 * h, 500 * w, rc, col)
    return out


def eye_light(cam, subject, height=1.7, power=6.0, name='eye'):
    """Tiny bright disc just above the lens: gives eyes a catch-light without changing the lighting."""
    s = Vector(subject) + Vector((0, 0, height * 0.9))
    d = (cam.location - s); dist = d.length; d.normalize()
    loc = s + d * min(dist * 0.9, 4.0 * height) + Vector((0, 0, 0.25 * height))
    o = _area(name + '.highlight', loc, s, 0.12 * height, power * height * height, (1, 1, 1), bpy.context.scene.collection)
    o.data.use_shadow = False
    try:
        o.visible_diffuse = False   # reflections only
    except Exception:
        pass
    return o
