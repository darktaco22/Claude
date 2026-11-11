# ================================================================ dusk light: a low sun behind the red end, team colours, lightning
for o in ARENA:      # the court, wet: it mirrors the lights
    if o.name in bpy.data.objects.keys() and o.type == 'MESH' and o.dimensions.z < 0.2 and max(o.dimensions) > 10:
        for m in o.data.materials:
            bs = m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
            if bs and not bs.inputs['Roughness'].links: bs.inputs['Roughness'].default_value = 0.28
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); COL.objects.link(sun); sun.data.energy = 1.35; sun.data.angle = math.radians(2.5); sun.data.color = (1.0, 0.62, 0.36)
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
# ================================================================ the edit
# Each shot shows a stretch of the ANIMATION (starting at a0, played at `speed`) from its own camera: slow motion and
# overlapping angles of the same moment. render_edl.py renders film frames from edl.json.
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); COL.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36; cam.data.dof.use_dof = True; cam.data.clip_end = 2000
SHOTS = []; _t = [1.5]
def SH(dur, a0, speed, p0, p1, l0, l1, lens, fstop=2.8, shake=0.0, lens1=None):
    SHOTS.append(dict(t0=round(_t[0], 4), t1=round(_t[0] + dur, 4), a0=a0, speed=speed, p0=list(p0), p1=list(p1), l0=list(l0), l1=list(l1), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake)); _t[0] += dur
def pos(u): return u['pos']
bz, zc = pos(B['bonk']), pos(R['zcat']); ts, tp = pos(B['toshi']), pos(R['triplet']); sw_, ba = pos(B['swordcat']), pos(R['baton'])
SH(3.0, 1.5, 1, (9, -52, 27), (9, -45, 18), (9, -14, 5), (9, -14, 4), 24, 8)                                     # the stadium at dusk
SH(2.5, 4.5, 1, (1.3, -13.4, 1.0), (5.6, -13.4, 1.1), (2.6, -9.0, 1.7), (4.4, -9.0, 1.75), 28, 2.8, 0.1)          # red's line, low dolly
SH(2.2, 7.0, 1, (12.9, -13.4, 1.2), (13.2, -12.9, 1.3), (14.5, -9.6, 2.4), (14.5, -9.6, 2.5), 35, 2.4, 0.1)       # the champion taunts
SH(1.5, 8.0, 1, (5.2, -8.2, 4.6), (5.6, -7.6, 4.7), (9, -3.05, 5.9), (9, -3.05, 6.0), 70, 2.8)                    # the red king enjoys it
SH(2.8, 9.2, 1, (11.2, -18.6, 1.5), (11.6, -19.2, 1.7), (14.5, -22.6, 2.8), (14.5, -22.6, 3.0), 24, 3.2, 0.1, 28) # blue's right wing: the whale
SH(1.6, 12.0, 1, (3.9, -18.8, 1.7), (3.7, -19.3, 1.8), (3.5, -22.6, 2.3), (3.5, -22.6, 2.35), 32, 2.8, 0.1)       # the viking and his wing
SH(1.5, 13.0, 1, (11.3, -24.8, 7.0), (11.0, -25.3, 7.0), (9, -28.9, 5.05), (9, -28.9, 5.1), 52, 2.8, 0.1)         # the blue king, at his cannon
SH(1.4, 13.6, 1, (0.9, -16.0, 2.2), (1.2, -16.0, 2.3), (9.5, -16.0, 2.0), (9.5, -16.0, 2.0), 19, 5.6, 0.1)        # across the river: both lines; lightning
SH(1.0, 15.0, 1, (11.0, -25.2, 6.9), (10.8, -25.5, 6.9), (9, -28.9, 5.1), (9, -28.9, 5.15), 62, 2.8, 0.25)        # "FIGHT!"
# ---- the charge, from everywhere
SH(1.6, 15.05, 0.4, (3.5, -15.6, 0.6), (3.5, -15.5, 0.65), (3.5, -21.0, 1.7), (3.5, -18.8, 1.7), 28, 2.8, 0.35)   # blue's left wing, head on, slow
SH(1.6, 15.05, 0.4, (3.5, -16.4, 0.6), (3.5, -16.5, 0.65), (3.5, -11.0, 1.7), (3.5, -13.2, 1.7), 28, 2.8, 0.35)   # red's left wing, head on, slow
SH(1.4, 15.3, 0.5, (8.6, -22.4, 1.3), (8.8, -19.6, 1.4), (14.5, -21.2, 2.5), (14.5, -18.6, 2.5), 22, 2.8, 0.3)   # the whale, tracking from the side
SH(1.4, 15.3, 0.5, (14.9, -16.6, 0.7), (14.9, -16.7, 0.75), (14.5, -11.0, 2.4), (14.5, -13.9, 2.4), 32, 2.8, 0.35)  # the champion, straight at us
SH(1.4, 15.1, 1.0, (9, -16.4, 27), (9, -16.4, 22), (9, -16.0, 0), (9, -16.0, 0), 26, 8, 0.15)                     # from above: two lines close on two bridges
SH(1.0, 16.0, 0.3, (5.6, -16.0, 0.35), (5.5, -16.0, 0.4), (3.5, -16.0, 1.4), (3.5, -16.0, 1.45), 20, 4, 0.3)      # at ground level between them
SH(1.1, 16.25, 0.35, (1.3, -16.0, 1.5), (1.45, -16.0, 1.5), (3.5, -16.0, 1.7), (3.5, -16.0, 1.7), 24, 3.2, 0.6)   # impact, slow
# ---- the battle
SH(1.0, 16.6, 0.7, (6.9, -16.2, 1.3), (6.5, -16.0, 1.5), (3.4, -16.0, 1.7), (3.4, -16.0, 1.8), 28, 3.2, 0.7)      # left bridge
SH(1.2, 17.36, 0.35, (1.9, -21.2, 3.3), (2.0, -20.8, 3.1), (bz[0], -15.8, 1.6), (bz[0], -15.2, 1.9), 40, 3.2, 0.4)   # the bat connects, slow (over his shoulder)
SH(1.1, 17.2, 1, (12.0, -24.6, 2.9), (12.2, -24.2, 2.9), (14.6, -15.5, 1.8), (14.6, -15.5, 1.8), 30, 4, 0.3)      # over the wizard's shoulder
SH(1.4, 17.5, 1, (11.0, -12.0, 1.0), (11.2, -12.4, 1.1), (14.5, -16.2, 2.5), (14.5, -16.2, 2.6), 26, 4, 0.4)      # the giants trade blows (low, from red's side)
SH(1.4, 19.0, 1, (6.4, -12.6, 3.0), (6.0, -13.0, 2.6), (3.6, -16.4, 1.5), (3.8, -16.2, 1.6), 32, 3.2, 0.5)        # left bridge from red's side
SH(1.0, 18.9, 0.4, (17.0, -19.8, 1.2), (16.9, -19.5, 1.25), (ts[0], -16.0, 1.8), (ts[0], -15.7, 1.9), 28, 3.2, 0.4)    # the ninja's cut, slow (from behind him)
SH(1.2, 20.2, 1, (7.0, -16.7, 1.6), (6.8, -16.4, 1.6), (sw_[0], -16.0, 1.8), (sw_[0], -15.8, 1.9), 35, 3.2, 0.5)  # steel on steel
SH(1.4, 21.0, 1, (17.5, -20.8, 3.1), (17.4, -20.4, 2.9), (14.5, -16.2, 2.4), (14.5, -16.1, 2.5), 30, 4, 0.3)      # the giants again (high, from blue's corner)
SH(2.8, 22.4, 0.55, (12.6, -13.0, 0.7), (12.9, -13.3, 0.8), (14.5, -17.2, 3.0), (14.5, -17.0, 3.1), 21, 4, 0.5)   # the slam, from below, slow
SH(1.4, 23.9, 1, (10.9, -1.6, 8.4), (10.7, -1.4, 8.6), (14.5, -10.0, 4.5), (14.5, -6.8, 3.2), 26, 4, 0.9)         # the champion arrives in his tower
SH(1.2, 24.7, 1, (5.0, -8.6, 4.6), (5.2, -8.3, 4.65), (9, -3.05, 6.0), (9, -3.05, 6.0), 100, 2.8, 0.2)           # the red king, less amused
SH(1.6, 26.3, 1, (5.2, -8.2, 4.6), (5.5, -7.8, 4.7), (9, -3.05, 5.9), (9, -3.05, 6.0), 70, 2.8, 0.15)             # the red king calls his reserves
SH(2.6, 26.2, 1, (5.6, -26.6, 4.8), (5.9, -25.8, 5.2), (9.4, -11.0, 1.8), (9.4, -11.0, 2.0), 24, 4, 0.2)              # over the blue line: they drop in, one after another
SH(1.8, 27.6, 1, (0.9, -14.6, 0.9), (3.4, -14.6, 1.0), (2.6, -10.2, 1.8), (5.0, -10.2, 1.9), 28, 2.8, 0.1)        # the new red line, low dolly
SH(1.8, 28.6, 1, (5.6, -15.5, 1.3), (6.0, -16.1, 1.5), (8.6, -19.7, 2.4), (8.8, -19.7, 2.6), 22, 3.2, 0.1, 26)    # six heroes hold the river
SH(1.0, 29.6, 1, (0.9, -16.0, 2.2), (1.2, -16.0, 2.3), (9.5, -15.4, 2.0), (9.5, -15.4, 2.0), 19, 5.6, 0.1)        # across the river: six against fourteen
SH(1.5, 30.6, 0.3, (14.6, -15.5, 0.6), (14.6, -15.4, 0.65), (13.6, -19.4, 2.3), (13.8, -18.6, 2.4), 24, 2.8, 0.4) # they go again: blue, head on, slow
SH(1.6, 30.9, 0.3, (0.9, -16.0, 1.0), (1.1, -16.0, 1.1), (9.5, -16.0, 1.9), (9.5, -16.0, 1.9), 20, 4, 0.5)        # both lines, a breath before they meet; lightning; black
print('FILM 3D ends at', _t[0], 'frames', F(_t[0]) - 1)
json.dump(dict(fps=FPS, first=37, last=F(_t[0]) - 1, shots=SHOTS), open(os.path.join(HERE, 'edl.json'), 'w'), indent=0)
for o in bpy.data.objects:
    if o.type == 'LIGHT': o.visible_camera = False
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=False)
print('SAVED', OUT)
