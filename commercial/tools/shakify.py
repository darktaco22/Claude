"""Real recorded camera shake without the add-on (works in Blender 4.2 and in plain Python).

    from shakify import shake
    dloc, drot = shake('INVESTIGATION', t_seconds, influence=1.0, loc_scale=1.0)

dloc is metres in the camera's local axes, drot is XYZ euler radians to add to the camera's local rotation.
Shakes loop. In Blender: apply(cam, 'THE_CLOSEUP', frame, fps, influence) adds the offsets to an already-posed camera.
IDs: INVESTIGATION (calm handheld), THE_CLOSEUP (tight handheld), THE_WEDDING, WALK_TO_THE_STORE, HANDYCAM_RUN,
OUT_CAR_WINDOW, BIKE_ON_GRAVEL_2D, SPACESHIP_SHAKE_2D, THE_ZEEK_2D (the 2D ones are rotation only).
"""
import math
from shake_data import SHAKE_LIST


def _sample(keys, f):
    n = len(keys)
    f = f % (n - 1)
    i = int(math.floor(f))
    u = f - i
    return keys[i][1] * (1 - u) + keys[min(i + 1, n - 1)][1] * u


def shake(name, t, influence=1.0, loc_scale=1.0, offset=0.0):
    _, fps, ch = SHAKE_LIST[name]
    f = (t + offset) * fps
    loc, rot = [0.0] * 3, [0.0] * 3
    for (path, ax), keys in ch.items():
        v = _sample(keys, f) - keys[0][1] * 0  # data is already centred closely enough
        if path == 'location':
            loc[ax] = v * influence * loc_scale
        elif path == 'rotation_euler':
            rot[ax] = v * influence
    return loc, rot


def apply(cam, name, frame, fps=24.0, influence=1.0, loc_scale=1.0, offset=0.0):
    from mathutils import Euler, Vector
    dl, dr = shake(name, frame / fps, influence, loc_scale, offset)
    m = cam.matrix_world.copy()
    cam.matrix_world = m @ (Euler(dr, 'XYZ').to_matrix().to_4x4())
    cam.location = cam.location + m.to_3x3() @ Vector(dl)
