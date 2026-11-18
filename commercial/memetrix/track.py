"""Where each character is at an animation time, shared by scene.py (build, shot solving) and render_edl.py (camera).

A track is a list of keys [a, x, y, z, H, step]: animation time (s), feet position, heading H in degrees in the camera
toolkit's convention (facing direction (sin H, cos H); characters' own rigs face -Y, so rig rotation = 180 - H), and
step=1 for a cut (jump) key. Between keys: linear. Before the first key: the first key.
"""
import math


def sample(keys, a):
    if not keys:
        return (0.0, 0.0, -100.0), 0.0
    if a <= keys[0][0]:
        k = keys[0]
        return (k[1], k[2], k[3]), k[4]
    for i in range(1, len(keys)):
        k0, k1 = keys[i - 1], keys[i]
        if a < k1[0] - 1e-4:
            if k1[5]:
                return (k0[1], k0[2], k0[3]), k0[4]
            u = (a - k0[0]) / max(1e-9, k1[0] - k0[0])
            h = k0[4] + (_wrap(k1[4] - k0[4])) * u
            return tuple(k0[j] + (k1[j] - k0[j]) * u for j in (1, 2, 3)), h
    k = keys[-1]
    return (k[1], k[2], k[3]), k[4]


def _wrap(d):
    while d > 180:
        d -= 360
    while d < -180:
        d += 360
    return d


def make_where(tracks):
    def where(name, a):
        return sample(tracks[name], a)
    return where


def heading_to(src, dst):
    """Heading H that looks from src toward dst (2D)."""
    return math.degrees(math.atan2(dst[0] - src[0], dst[1] - src[1]))
