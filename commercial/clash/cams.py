# ================================================================ dusk light: a low sun behind the red end, team colours, lightning
for o in ARENA:      # the court, wet: it mirrors the lights
    if o.name in bpy.data.objects.keys() and o.type == 'MESH' and o.dimensions.z < 0.2 and max(o.dimensions) > 10:
        for m in o.data.materials:
            bs = m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
            if bs and not bs.inputs['Roughness'].links: bs.inputs['Roughness'].default_value = 0.28
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); COL.objects.link(sun); sun.data.energy = 1.9; sun.data.angle = math.radians(2.5); sun.data.color = (1.0, 0.62, 0.36)
sun.rotation_euler = (math.radians(74), 0, math.radians(float(arg('--sunrot', '205'))))
def keylight(name, loc, target, e, size=4.0, col=(1.0, 0.95, 0.85)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = e; ld.size = size; ld.color = col; o = bpy.data.objects.new(name, ld); COL.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
keylight('red_wash', (9, 3, 16), (9, -9, 0), 11000, 14, (1.0, 0.25, 0.15)); keylight('blue_wash', (9, -35, 16), (9, -23, 0), 11000, 14, (0.2, 0.45, 1.0))
keylight('pose_fill', (9, -22, 5), (9, -12, 2.4), 2600, 8, (0.75, 0.85, 1.0)); keylight('bridgeL', (3.5, -16, 9), (3.5, -16, 0), 1600, 5, (1.0, 0.9, 0.75)); keylight('bridgeR', (14.5, -16, 9), (14.5, -16, 0), 1600, 5, (1.0, 0.9, 0.75))
bolt_l = bpy.data.objects.new('lightning', bpy.data.lights.new('lightning', 'SUN')); COL.objects.link(bolt_l); bolt_l.data.color = (0.75, 0.82, 1.0); bolt_l.rotation_euler = (math.radians(35), 0, math.radians(40))
for f in range(1, LAST + 1):
    t = (f - 1) / FPS; e = sum(max(0.0, 1 - abs(t - th - d) / 0.05) * w_ for th in THUNDER for d, w_ in ((0.0, 1.0), (0.17, 0.5), (0.29, 0.8)))
    bolt_l.data.energy = 5.0 * e; bolt_l.data.keyframe_insert('energy', frame=f)
# ================================================================ camera
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); COL.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.dof.use_dof = True; cam.data.clip_end = 2000
V = Vector
def SH(t0, t1, p0, p1, l0, l1, lens, fstop=2.8, shake=0.0, lens1=None, focus=None):
    return dict(t0=t0, t1=t1, p0=V(p0), p1=V(p1), l0=V(l0), l1=V(l1), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake, focus=focus)
SHOTS = [
    SH(1.5, 4.5, (9, -52, 27), (9, -45, 18), (9, -14, 5), (9, -14, 4), 24, 8),                                    # the stadium at dusk
    SH(4.5, 7.0, (1.2, -12.6, 0.9), (6.5, -12.6, 1.0), (3.5, -9.0, 1.9), (8.5, -9.0, 1.9), 35, 2.4, 0.1),          # red's line, low dolly
    SH(7.0, 9.2, (12.9, -13.4, 1.2), (13.2, -12.9, 1.3), (14.5, -9.6, 2.4), (14.5, -9.6, 2.5), 35, 2.4, 0.1),       # the champion taunts
    SH(9.2, 12.0, (14.9, -18.3, 0.9), (14.7, -19.0, 1.1), (14.5, -22.4, 2.6), (14.5, -22.4, 2.8), 19, 3.2, 0.1, 23),   # blue's right wing: the whale
    SH(12.0, 13.6, (3.9, -18.8, 1.7), (3.7, -19.3, 1.8), (3.5, -22.6, 2.3), (3.5, -22.6, 2.35), 32, 2.8, 0.1),      # the viking and his wing
    SH(13.6, 15.0, (0.9, -16.0, 2.2), (1.2, -16.0, 2.3), (9.5, -16.0, 2.0), (9.5, -16.0, 2.0), 19, 5.6, 0.1),      # across the river: both lines; lightning
    SH(15.0, 16.4, (7.2, -21.5, 0.8), (7.0, -17.4, 0.9), (3.5, -21.8, 1.6), (3.6, -17.4, 1.6), 24, 4, 0.5),        # the charge
    SH(16.4, 17.9, (6.9, -16.2, 1.3), (6.5, -16.0, 1.5), (3.4, -16.0, 1.7), (3.4, -16.0, 1.8), 28, 3.2, 0.7),      # left bridge: impact
    SH(17.9, 19.0, (12.0, -24.6, 2.9), (12.2, -24.2, 2.9), (14.6, -15.5, 1.8), (14.6, -15.5, 1.8), 30, 4, 0.3),    # over the wizard's shoulder
    SH(19.0, 21.0, (6.4, -12.6, 3.0), (6.0, -13.0, 2.6), (3.6, -16.4, 1.5), (3.8, -16.2, 1.6), 32, 3.2, 0.5),      # left bridge from red's side
    SH(21.0, 22.4, (17.3, -16.6, 1.4), (17.2, -16.2, 1.5), (14.5, -16.4, 2.5), (14.5, -16.2, 2.6), 22, 4, 0.3),    # the giants, in profile
    SH(22.4, 24.0, (12.6, -13.0, 0.7), (12.9, -13.3, 0.8), (14.5, -17.2, 3.0), (14.5, -17.0, 3.1), 21, 4, 0.5),    # the slam, from below
    SH(24.0, 25.4, (10.9, -1.6, 8.4), (10.7, -1.4, 8.6), (14.5, -10.0, 4.5), (14.5, -6.8, 3.2), 26, 4, 0.9),        # the champion arrives in his tower (from the red king's side)
    SH(25.4, 27.4, (9, -25.5, 5.0), (9, -23.5, 4.2), (11.5, -9, 3.5), (10.0, -11, 3.0), 30, 4, 0.3),               # smoke; the heroes regroup
    SH(27.4, 31.0, (9.2, -18.2, 0.8), (9.2, -16.6, 1.0), (9.2, -11.8, 2.6), (9.2, -11.8, 2.9), 21, 4, 0.12, 25),   # the pose
]
