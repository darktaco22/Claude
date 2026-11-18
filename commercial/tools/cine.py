"""Cinematic camera toolkit: shot sizes, angles, moves, composition and focus, described as data.

A shot is a plain dict (JSON-safe, so it can live in an EDL). `place(cam, shot, u, t, where)` puts a Blender camera
for progress `u` (0..1 through the shot) at film time `t`. `where(name, t)` returns a subject's world position
(feet) and heading in degrees; the toolkit never looks objects up itself, so it works with any scene.

Vocabulary (see PLAYBOOK.md, "Camera language"):

    size      ECU CU MCU MS MLS WS EWS  -> distance from lens and how much of the subject fills the frame
    angle     eye, low, high, worm, bird, or a number (degrees of camera elevation; negative looks up)
    bearing   degrees around the subject from its face (0 front, +-45 three-quarter, 90 profile, 180 behind)
    move      static, push, pull, arc, crane, track, dolly_zoom, pedestal, reveal
    frame     where the subject's eyes sit on screen, (x, y) in -1..1; default left/right third and upper third
    dutch     roll in degrees (unease, chaos); keep under 15
    focus     subject name, or ("rack", from, to, u0, u1) for a rack focus
    ease      smooth (default), in, out, linear, settle (lands with a small overshoot, for handheld-like stops)

Example:

    {"subject": "sarge", "size": "MCU", "angle": "low", "bearing": 35, "move": "push", "amount": 0.25,
     "frame": "left", "lens": 65, "fstop": 2.0}
"""
import math

from mathutils import Euler, Quaternion, Vector

SENSOR_W = 36.0                                          # mm, Blender default (sensor_fit AUTO uses the wider side)

# fraction of the subject's height visible in frame, measured from the eyes: (above eyes, below eyes) in subject heights
SIZES = {
    'ECU': (0.06, 0.06),                                 # eyes only
    'CU': (0.12, 0.16),                                  # head and neck
    'MCU': (0.14, 0.32),                                 # head and shoulders, chest
    'MS': (0.16, 0.55),                                  # waist up
    'MLS': (0.18, 0.85),                                 # knees up (cowboy)
    'WS': (0.35, 1.15),                                  # whole body with room
    'EWS': (1.6, 2.6),                                   # body small in the place
}
ANGLES = {'eye': 0.0, 'low': -15.0, 'worm': -45.0, 'high': 25.0, 'bird': 80.0}
EYES = {}                                                # character name -> eye height in metres (else 0.92 x height)
EYE_FWD = {}                                             # character name -> how far the face sits in front of the feet (m)
FRAME_SCALE = 1.0                                        # >1 frames every size wider (cartoon casts with big heads)


def eye_point(name, feet, heading, height=1.7):
    """Where a character's eyes are: above the feet, and forward along its facing for long-bodied characters."""
    h = math.radians(heading)
    fwd = EYE_FWD.get(name, 0.0)
    return Vector(feet) + Vector((math.sin(h) * fwd, math.cos(h) * fwd, EYES.get(name, 0.92 * height)))
THIRDS = {'left': (-1 / 3, 1 / 3), 'right': (1 / 3, 1 / 3), 'center': (0.0, 1 / 3), 'low_left': (-1 / 3, 0.0),
          'low_right': (1 / 3, 0.0)}


# ---------------------------------------------------------------- easing
def ease(u, kind='smooth'):
    u = min(1.0, max(0.0, u))
    if kind == 'linear':
        return u
    if kind == 'in':
        return u * u * u
    if kind == 'out':
        return 1 - (1 - u) ** 3
    if kind == 'settle':                                  # fast start, overshoots about 1 %, settles at the end
        return (1 - math.exp(-7 * u) * math.cos(5 * u)) / (1 - math.exp(-7) * math.cos(5))
    return u * u * u * (u * (u * 6 - 15) + 10)            # smootherstep: no velocity or acceleration jump


# ---------------------------------------------------------------- framing maths
def aspect_of(scene):
    r = scene.render
    return (r.resolution_x * r.pixel_aspect_x) / max(1, r.resolution_y * r.pixel_aspect_y)


def fovs(lens, aspect):
    """Horizontal and vertical field of view (radians) for a lens in mm (sensor fit AUTO)."""
    if aspect >= 1:
        half_w = math.atan(SENSOR_W / 2 / lens)
        half_h = math.atan(math.tan(half_w) / aspect)
    else:
        half_h = math.atan(SENSOR_W / 2 / lens)
        half_w = math.atan(math.tan(half_h) * aspect)
    return 2 * half_w, 2 * half_h


def distance_for(size, height, lens, aspect, frame_y=1 / 3):
    """Camera distance that fits the slice of the subject named by `size` in the frame height, with the eyes at `frame_y`."""
    above, below = SIZES[size] if isinstance(size, str) else size
    span = (above + below) * height
    _, fov_v = fovs(lens, aspect)
    return span / (2 * math.tan(fov_v / 2)) * (1 + 0.15 * abs(frame_y))


def frame_point(frame):
    if frame is None:
        return THIRDS['center']
    if isinstance(frame, str):
        return THIRDS[frame]
    return tuple(frame)


def elevation_of(angle):
    return ANGLES[angle] if isinstance(angle, str) else float(angle)


# ---------------------------------------------------------------- moves
def _orbit(eye, heading, bearing, elevation, distance):
    """Camera position around an eye point: bearing from the subject's facing, elevation above the horizon."""
    b = math.radians(heading + bearing)
    e = math.radians(elevation)
    flat = distance * math.cos(e)
    return eye + Vector((math.sin(b) * flat, math.cos(b) * flat, distance * math.sin(e)))


def rig(shot, u, t, where, aspect):
    """Camera position, the point to frame, lens and roll for a shot at progress u. Pure maths; no Blender objects."""
    k = ease(u, shot.get('ease', 'smooth'))
    name = shot['subject']
    feet, heading = where(name, t)
    height = shot.get('height', 1.7)
    eye = eye_point(name, feet, heading, height)
    if 'eye' in shot:
        eye.z = Vector(feet).z + shot['eye']
    if 'look_offset' in shot:
        eye += Vector(shot['look_offset'])
    if shot.get('fixed_heading') is not None:
        heading = shot['fixed_heading']
    lens0 = shot.get('lens', 50.0)
    lens = lens0
    frame = frame_point(shot.get('frame'))
    dist0 = shot.get('distance') or distance_for(shot.get('size', 'MS'), height, lens0, aspect, frame[1]) * shot.get('scale', FRAME_SCALE)
    bearing = shot.get('bearing', 30.0)
    elevation = elevation_of(shot.get('angle', 'eye'))
    roll = shot.get('dutch', 0.0)
    move = shot.get('move', 'static')
    amount = shot.get('amount', 0.0)
    dist = dist0

    if move == 'push':                                    # dolly in: amount = fraction of the distance travelled
        dist = dist0 * (1 - (amount or 0.25) * k)
    elif move == 'pull':
        dist = dist0 * (1 + (amount or 0.35) * k)
    elif move == 'arc':                                   # orbit: amount = degrees swept (parallax, reveals depth)
        bearing += (amount or 40.0) * (k - 0.5)
    elif move == 'crane':                                 # rise or fall: amount = elevation change in degrees
        elevation += (amount or 30.0) * k
    elif move == 'pedestal':                              # straight up or down (metres), the look point rises with it
        eye += Vector((0, 0, (amount or 0.5) * (k - 0.5)))
    elif move == 'dolly_zoom':                            # vertigo: distance changes, lens keeps the subject's size
        dist = dist0 * (1 + (amount or -0.45) * k)
        lens = lens0 * dist / dist0
    elif move == 'reveal':                                # start on a foreground point, pan onto the subject
        start = Vector(shot['from'])
        pos = _orbit(eye, heading, bearing, elevation, dist)
        look = start.lerp(eye, k)
        return pos, look, lens, roll, frame if k > 0.999 else (0.0, 0.0), dist
    elif move == 'track':                                 # keep the bearing to a moving subject; lead room on its motion
        if shot.get('lead', True):
            ahead, _ = where(name, t + 0.4)
            velocity = Vector(ahead) - Vector(feet)
            if velocity.length > 0.05:
                pos = _orbit(eye, heading, bearing, elevation, dist)
                side = (eye - pos).cross(Vector((0, 0, 1)))
                screen_dir = -1.0 if velocity.dot(side) > 0 else 1.0
                frame = (screen_dir * abs(frame[0] or 1 / 3), frame[1])
    if 'lens1' in shot and move != 'dolly_zoom':           # a zoom on top of the move (snap zooms, slow creeps)
        lens = lens0 + (shot['lens1'] - lens0) * k
    if 'dutch1' in shot:
        roll = roll + (shot['dutch1'] - roll) * k
    if shot.get('over'):                                 # over-the-shoulder: long lens from well behind the other character
        o_feet, o_head = where(shot['over'], t)
        o_eye = eye_point(shot['over'], o_feet, o_head, shot.get('over_height', height))
        back = o_eye - eye
        gap = back.length
        back.z = 0
        back.normalize()
        # far enough back that the near head is a soft shape, not a wall; the lens keeps the subject at its size
        d = gap + shot.get('over_back', 2.4) * (1 - (amount if move == 'push' else 0.0) * k)
        lens = lens0 * d / (distance_for(shot.get('size', 'MCU'), height, lens0, aspect, frame[1]) * shot.get('scale', FRAME_SCALE))
        side = back.cross(Vector((0, 0, 1))) * (1 if frame[0] <= 0 else -1)
        want = shot.get('over_x', 0.92) * (1 if frame[0] <= 0 else -1)      # near head centre close to the far edge
        best = None
        for i in range(1, 40):
            offset = i * 0.04
            pos = eye + back * d + side * offset + Vector((0, 0, shot.get('over_up', 0.1)))
            q = aim(pos, eye, lens, roll, frame, aspect)
            x = project(pos, q, o_eye, lens, aspect)[0]
            if best is None or abs(x - want) < best[0]:
                best = (abs(x - want), pos)
        return best[1], eye, lens, roll, frame, (eye - best[1]).length
    pos = _orbit(eye, heading, bearing, elevation, dist)
    return pos, eye, lens, roll, frame, dist


def aim(pos, look, lens, roll, frame, aspect):
    """Rotation that puts `look` at screen position `frame` (x right, y up, -1..1) with a roll."""
    q = (look - pos).to_track_quat('-Z', 'Y')
    fov_h, fov_v = fovs(lens, aspect)
    yaw = math.atan(frame[0] * math.tan(fov_h / 2))
    pitch = math.atan(frame[1] * math.tan(fov_v / 2))
    # turning the camera right moves the subject left on screen, so rotate against the wanted offset
    # roll about the line of sight first, so the subject stays on its frame point whatever the dutch angle
    q = q @ Quaternion((0, 0, 1), math.radians(roll))
    return q @ Euler((-pitch, yaw, 0.0), 'XYZ').to_quaternion()


def surface_distance(scene, pos, point, slack=0.45):
    """Distance from pos to the first surface on the way to point, if it lies within `slack` of the point (the face);
    the centre of a head is ~0.2 m behind what the lens sees, which at f/2 and 85 mm is visibly soft."""
    direction = point - pos
    length = direction.length
    hit, location, *_ = scene.ray_cast(_depsgraph(), pos, direction.normalized(), distance=length + slack)
    if hit and (location - pos).length > length - slack:
        return (location - pos).length
    return length - 0.12


def _depsgraph():
    import bpy
    return bpy.context.evaluated_depsgraph_get()


def owner(obj):
    """The character an object belongs to: the 'actor' custom property on it or a parent (set by the scene builder)."""
    while obj is not None:
        if 'actor' in obj:
            return obj['actor']
        obj = obj.parent
    return None


def blocker(scene, pos, point, slack=0.45, skip=()):
    """The object between the camera and a subject's eyes, or None. Anything closer than `slack` to the eyes is the subject;
    objects owned by a name in `skip` (the subject itself, its props) are looked through."""
    direction = point - pos
    length = direction.length
    direction.normalize()
    start = pos.copy()
    for _ in range(8):
        hit, location, _, _, obj, _ = scene.ray_cast(_depsgraph(), start, direction, distance=length - (start - pos).length)
        if not hit or (point - location).length <= slack:
            return None
        if owner(obj) not in skip:
            return obj
        start = location + direction * 0.01
    return None


def project(pos, q, point, lens, aspect):
    """Screen position (x, y in -1..1, depth) of a world point for a camera at pos with rotation q."""
    local = q.inverted() @ (Vector(point) - pos)
    if local.z >= -1e-6:
        return (9.0, 9.0, local.z)
    fov_h, fov_v = fovs(lens, aspect)
    return (local.x / -local.z / math.tan(fov_h / 2), local.y / -local.z / math.tan(fov_v / 2), -local.z)


def clutter(scene, pos, q, lens, aspect, subject_distance, floor_z=0.0, cols=16, rows=9, skip=()):
    """Fraction of the frame covered by things much nearer than the subject (trees, heads, posts in the lens).
    The ground under everyone is ignored."""
    fov_h, fov_v = fovs(lens, aspect)
    near = subject_distance * 0.55
    hits = 0
    dg = _depsgraph()
    for i in range(cols):
        for j in range(rows):
            x = (i + 0.5) / cols * 2 - 1
            y = (j + 0.5) / rows * 2 - 1
            ray = q @ Vector((x * math.tan(fov_h / 2), y * math.tan(fov_v / 2), -1.0))
            hit, loc, normal, _, obj, _ = scene.ray_cast(dg, pos, ray.normalized(), distance=near)
            if hit and not (normal.z > 0.9 and loc.z < floor_z + 0.05) and owner(obj) not in skip:
                hits += 1
    return hits / (cols * rows)


def focus_distance(shot, u, t, where, pos, scene=None):
    focus = shot.get('focus', shot['subject'])
    height = shot.get('height', 1.7)

    def dist_to(name):
        feet, head = where(name, t)
        point = eye_point(name, feet, head, height)
        if scene is None:
            return (point - pos).length - 0.12
        return surface_distance(scene, pos, point)

    if isinstance(focus, (list, tuple)) and focus and focus[0] == 'rack':
        _, a, b, u0, u1 = focus
        w = ease((u - u0) / max(1e-6, u1 - u0))
        return dist_to(a) * (1 - w) + dist_to(b) * w
    if isinstance(focus, (int, float)):
        return float(focus)
    return dist_to(focus)


def place(cam, shot, u, t, where, scene):
    """Set a camera object for the shot at progress u (0..1) and film time t. Returns the camera position."""
    aspect = aspect_of(scene)
    pos, look, lens, roll, frame, _ = rig(shot, u, t, where, aspect)
    cam.location = pos
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = aim(pos, look, lens, roll, frame, aspect)
    cam.data.sensor_fit = 'AUTO'
    cam.data.sensor_width = SENSOR_W
    cam.data.lens = lens
    cam.data.dof.use_dof = shot.get('fstop', 2.8) < 16
    cam.data.dof.aperture_fstop = shot.get('fstop', 2.8)
    cam.data.dof.focus_distance = max(0.2, focus_distance(shot, u, t, where, pos, scene))
    return pos


def solve(shot, where, scene, t0=0.0, t1=1.0, samples=7, ignore=()):
    """Check a shot for anything between camera and subject (trees, walls, other characters). If blocked, try bearings
    10-60 degrees either side, then higher angles, and return the first clear version (a copy) plus a note.
    Run once per shot when building the EDL, never per frame (the camera would jump)."""
    aspect = aspect_of(scene)

    limit = shot.get('clutter_max', 0.08)
    skip = tuple(n for n in (shot['subject'], shot.get('over')) if n)

    def clear(candidate):
        for i in range(samples):
            u = i / (samples - 1)
            t = t0 + (t1 - t0) * u
            pos, look, lens, roll, frame, dist = rig(candidate, u, t, where, aspect)
            obj = blocker(scene, pos, look, skip=(candidate['subject'],))
            if obj is not None and obj.name not in ignore:
                return obj.name
            covered = clutter(scene, pos, aim(pos, look, lens, roll, frame, aspect), lens, aspect, dist, where(candidate['subject'], t)[0][2],
                              skip=skip)
            if covered > limit:
                return f'foreground clutter ({covered:.0%} of frame)'
        return None

    first = clear(shot)
    if first is None:
        return dict(shot), 'clear'
    if shot.get('over'):                                   # over-the-shoulder: move further off the near character's head
        for over_x in (1.05, 1.2, 1.4, 1.65, 1.9, 2.2):
            for up in (0.1, 0.3):
                candidate = dict(shot, over_x=over_x, over_up=up)
                if clear(candidate) is None:
                    return candidate, f'{first} blocked the view; near head moved to x={over_x}, camera up {up} m'
        return dict(shot), f'BLOCKED by {first} at every tried offset: restage or hide it'
    base_b = shot.get('bearing', 30.0)
    base_e = elevation_of(shot.get('angle', 'eye'))
    for lift in (0, 10, 20):
        for step in (10, -10, 20, -20, 30, -30, 45, -45, 60, -60):
            candidate = dict(shot, bearing=base_b + step, angle=base_e + lift)
            if clear(candidate) is None:
                return candidate, f'{first} blocked the view; moved bearing {step:+d}, angle {lift:+d}'
    return dict(shot), f'BLOCKED by {first} at every tried angle: restage or hide it'


# ---------------------------------------------------------------- coverage
def dialogue(a, b, lens_close=65, lens_wide=32, side=1):
    """Standard coverage for two characters talking, all on one side of the 180-degree line between them.

    Returns shots: two-shot wide, over-the-shoulder on each, clean close-up on each. `side` picks the side of the line.
    Bearings are relative to each speaker's facing (they face each other), so +side*35 stays on the same side for both."""
    s = side
    return {
        'two': dict(subject=a, size='WS', bearing=s * 80, lens=lens_wide, frame='left', angle='eye', fstop=4.0),
        'ots_a': dict(subject=a, over=b, lens=lens_close - 15, frame=(s * 1 / 3, 1 / 3), fstop=2.8),
        'ots_b': dict(subject=b, over=a, lens=lens_close - 15, frame=(-s * 1 / 3, 1 / 3), fstop=2.8),
        'cu_a': dict(subject=a, size='CU', bearing=-s * 35, lens=lens_close + 20, frame='right', fstop=1.8),
        'cu_b': dict(subject=b, size='CU', bearing=s * 35, lens=lens_close + 20, frame='left', fstop=1.8),
    }


def hero(subject, lens=40):
    """Low-angle push on a character's big moment."""
    return dict(subject=subject, size='MS', angle='low', bearing=25, move='push', amount=0.2, lens=lens, frame='center', fstop=2.2)


def reaction(subject, lens=85):
    """Snap of a reaction: tight, slight creep in, settles."""
    return dict(subject=subject, size='CU', bearing=-20, move='push', amount=0.08, lens=lens, frame='right', ease='settle', fstop=1.8)


def establish(subject, lens=24):
    """Opening of a place: high, wide, slow crane down onto the subject."""
    return dict(subject=subject, size='EWS', angle=35, bearing=40, move='crane', amount=-25, lens=lens, frame='center', fstop=8.0)


def chaos(subject, lens=28):
    """Action beat: wide lens, close, tilted, tracking with lead room."""
    return dict(subject=subject, size='MLS', angle='low', bearing=60, move='track', lens=lens, dutch=8, frame='left', fstop=4.0)


def vertigo(subject, lens=35):
    """Realisation beat: dolly zoom, background stretches while the face holds."""
    return dict(subject=subject, size='MCU', bearing=0, move='dolly_zoom', amount=-0.45, lens=lens, frame='center', fstop=2.8)


# ---------------------------------------------------------------- checks
def check_rules(shots):
    """Warn about common mistakes in a list of consecutive shots (dicts with 'subject', 'size', 'bearing', 'line')."""
    notes = []
    order = list(SIZES)
    for i in range(1, len(shots)):
        p, c = shots[i - 1], shots[i]
        if p.get('over') or c.get('over'):
            continue                                       # an over-the-shoulder is its own setup (camera behind the other)
        if p.get('subject') == c.get('subject') and p.get('size') == c.get('size') and abs(p.get('bearing', 30) - c.get('bearing', 30)) < 30:
            notes.append(f'shot {i}: jump cut - same subject and size from within 30 degrees; change size two steps or move 30+ degrees')
        if p.get('subject') == c.get('subject') and p.get('size') in order and c.get('size') in order:
            if abs(order.index(p['size']) - order.index(c['size'])) == 1 and abs(p.get('bearing', 30) - c.get('bearing', 30)) < 30:
                notes.append(f'shot {i}: size change of one step on the same axis reads as a glitch; skip a size or change angle')
        if 'line' in p and 'line' in c and p['line'] != c['line']:
            notes.append(f'shot {i}: crosses the 180-degree line; show the move (an arc or a neutral shot) between them')
    return notes
