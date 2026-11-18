"""Tests for cine.py: subjects land where the shot asks, sizes fit, moves move. Run: blender -b -P cine_test.py"""
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cine  # noqa: E402

sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam

PLACES = {'a': ((0.0, 0.0, 0.0), 180.0), 'b': ((0.0, -2.0, 0.0), 0.0)}


def where(name, t):
    if name == 'runner':                                   # runs along +x at 3 m/s
        return (3.0 * t, 5.0, 0.0), 90.0
    return PLACES[name]


def screen(point):
    bpy.context.view_layer.update()
    v = world_to_camera_view(sc, cam, Vector(point))
    return (v.x * 2 - 1, v.y * 2 - 1, v.z)


def eye_of(name, t, height=1.7):
    feet, _ = where(name, t)
    return Vector(feet) + Vector((0, 0, 0.92 * height))


failures = []


def expect(ok, message):
    if not ok:
        failures.append(message)


# 1. every move frames the subject's eyes where the shot asks, at start, middle and end
moves = ['static', 'push', 'pull', 'arc', 'crane', 'dolly_zoom', 'pedestal']
for move in moves:
    for frame in ('left', 'right', 'center', (0.2, -0.1)):
        for angle in ('eye', 'low', 'high', 10):
            for dutch in (0, 8):
                shot = dict(subject='a', size='MS', move=move, frame=frame, angle=angle, dutch=dutch, bearing=35, lens=50)
                for u in (0.0, 0.5, 1.0):
                    cine.place(cam, shot, u, 0.0, where, sc)
                    eye = eye_of('a', 0.0)
                    if move == 'pedestal':
                        eye = eye + Vector((0, 0, 0.5 * (cine.ease(u) - 0.5)))
                    x, y, z = screen(eye)
                    want = cine.frame_point(frame)
                    # a dutch angle must not move the subject off its frame point
                    err = math.hypot(x - want[0], y - want[1])
                    expect(z > 0 and err < 0.02, f'{move} {frame} {angle} dutch={dutch} u={u}: eyes at ({x:.3f},{y:.3f}) want {want}')

# 2. shot sizes: a medium shot shows the waist, a close-up does not show the chest; a wide shot shows the feet
for size, must_see, must_not in (('WS', [0.0, 1.7], []), ('MS', [0.9], [0.2]), ('CU', [1.7], [1.1])):
    shot = dict(subject='a', size=size, frame='center', lens=50, bearing=0)
    cine.place(cam, shot, 0.0, 0.0, where, sc)
    for h in must_see:
        expect(-1.0 <= screen((0, 0, h))[1] <= 1.0, f'{size}: height {h} should be in frame (y={screen((0, 0, h))[1]:.2f})')
    for h in must_not:
        expect(not -1.0 <= screen((0, 0, h))[1] <= 1.0, f'{size}: height {h} should be out of frame')

# 3. moves really move: push gets closer, arc changes bearing, crane rises, dolly zoom keeps the face size
def cam_at(shot, u):
    pos = cine.place(cam, shot, u, 0.0, where, sc)
    return pos.copy(), cam.data.lens


eye = eye_of('a', 0.0)
p0, _ = cam_at(dict(subject='a', move='push', size='MS'), 0)
p1, _ = cam_at(dict(subject='a', move='push', size='MS'), 1)
expect((p1 - eye).length < (p0 - eye).length * 0.8, 'push should end 20 %+ closer')
p0, _ = cam_at(dict(subject='a', move='crane', amount=30, size='MS'), 0)
p1, _ = cam_at(dict(subject='a', move='crane', amount=30, size='MS'), 1)
expect(p1.z > p0.z + 0.5, 'crane should rise')
p0, _ = cam_at(dict(subject='a', move='arc', amount=60, size='MS'), 0)
p1, _ = cam_at(dict(subject='a', move='arc', amount=60, size='MS'), 1)
expect(abs((p0 - eye).angle(p1 - eye) - math.radians(60)) < 0.05, 'arc should sweep 60 degrees')


def face_span(shot, u):
    cine.place(cam, shot, u, 0.0, where, sc)
    return screen(eye + Vector((0, 0, 0.12)))[1] - screen(eye - Vector((0, 0, 0.12)))[1]


dz = dict(subject='a', move='dolly_zoom', amount=-0.45, size='MCU', frame='center', lens=35)
expect(abs(face_span(dz, 0) - face_span(dz, 1)) < 0.02, 'dolly zoom should keep the face the same size')

# 4. tracking a runner keeps it framed with lead room (runner sits on the side it runs away from)
shot = dict(subject='runner', size='MLS', move='track', bearing=90, frame='left', lens=35)
for t in (0.0, 1.0, 2.0):
    cine.place(cam, shot, t / 2, t, where, sc)
    x, y, z = screen(eye_of('runner', t))
    ahead_x = screen(eye_of('runner', t + 0.5))[0]
    expect(abs(x) > 0.25 and (ahead_x - x) * x < 0, f'track t={t}: runner at x={x:.2f} should have room ahead (moving to {ahead_x:.2f})')

# 5. rack focus moves the focus distance from one subject to the other
shot = dict(subject='a', size='MS', bearing=0, focus=['rack', 'a', 'b', 0.3, 0.7])
cine.place(cam, shot, 0.0, 0.0, where, sc)
f0 = cam.data.dof.focus_distance
cine.place(cam, shot, 1.0, 0.0, where, sc)
f1 = cam.data.dof.focus_distance
expect(abs(f1 - f0) > 1.5, f'rack focus should change focus distance ({f0:.2f} -> {f1:.2f})')

# 6. presets and coverage all place without error, and the rules checker catches a jump cut
for shot in list(cine.dialogue('a', 'b').values()) + [cine.hero('a'), cine.reaction('a'), cine.establish('a'), cine.vertigo('a')]:
    for u in (0, 0.5, 1):
        cine.place(cam, shot, u, 0.0, where, sc)
        expect(screen(eye_of(shot['subject'], 0))[2] > 0, f'preset {shot} lost its subject')
expect(cine.check_rules([dict(subject='a', size='MS', bearing=30), dict(subject='a', size='MS', bearing=40)]), 'jump cut not caught')
expect(not cine.check_rules([dict(subject='a', size='WS', bearing=30), dict(subject='a', size='CU', bearing=-30)]), 'false alarm')
expect(abs(cine.ease(1.0, 'settle') - 1) < 1e-9 and max(cine.ease(u / 100, 'settle') for u in range(101)) > 1.0, 'settle should overshoot then land')

# 7. over-the-shoulder: camera behind B, the subject A on its third, B's head on the other side of frame
for fx in (-1 / 3, 1 / 3):
    shot = dict(subject='a', over='b', frame=(fx, 1 / 3), lens=50)
    pos = cine.place(cam, shot, 0.0, 0.0, where, sc)
    x, y, _ = screen(eye_of('a', 0))
    bx, _, bz = screen(eye_of('b', 0))
    expect(abs(x - fx) < 0.02 and pos.y < -2.0, f'ots {fx}: subject at {x:.2f}, camera y {pos.y:.2f} should be behind B')
    expect(bz > 0 and bx * fx < 0, f'ots {fx}: over-shoulder character should sit on the other side (x={bx:.2f})')

# 8. surface focus and the obstruction solver, with real geometry: a head sphere and a wall in front of it
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.24, location=(0, 0, 0.92 * 1.7))
shot = dict(subject='a', size='CU', bearing=0, frame='center', lens=85)
pos = cine.place(cam, shot, 0.0, 0.0, where, sc)
expected = (pos - eye_of('a', 0)).length - 0.24
expect(abs(cam.data.dof.focus_distance - expected) < 0.01, f'focus {cam.data.dof.focus_distance:.3f} should be on the head surface {expected:.3f}')
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -1.2, 1.5))
bpy.context.object.scale = (0.8, 0.1, 1.2)
wall = bpy.context.object.name
blocked = dict(subject='a', size='MS', bearing=0, frame='center', lens=35)
fixed, note = cine.solve(blocked, where, sc)
expect('blocked' in note and fixed['bearing'] != 0, f'solver should swing around the wall: {note}')
pos, look, *_ = cine.rig(fixed, 0.5, 0.0, where, cine.aspect_of(sc))
expect(cine.blocker(sc, pos, look) is None, 'solved shot still blocked')
_, note = cine.solve(dict(subject='a', size='MS', bearing=90, lens=35), where, sc)
expect(note == 'clear', f'clear shot reported as {note}')

print('\n'.join(failures[:20]))
print(f'cine_test: {len(failures)} failures')
sys.exit(1 if failures else 0)
