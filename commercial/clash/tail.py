# ================================================================ CLASH AT THE BRIDGE: the battle
T_FIGHT, T_MEET, T_SLAM, T_CRASH, T_FIRE, T_TOWER, T_WIN = 15.0, 16.3, 23.6, 24.6, 25.4, 26.9, 29.9      # animation time (the film re-times it: cams.py)
THUNDER = [2.6, 14.4, 23.6, 31.1]
def smooth(u):
    """The game's low-poly models: welded, smooth-shaded and subdivided at render time for the close-ups."""
    import bmesh
    for o in u['objs']:
        if o.type != 'MESH' or o.name.startswith('prop_') or len(o.data.vertices) < 500: continue
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002); bm.to_mesh(o.data); bm.free()
        for p in o.data.polygons: p.use_smooth = True
        sd = o.modifiers.new('subd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1; sd.uv_smooth = 'PRESERVE_BOUNDARIES'
        for m in o.data.materials:
            bs = m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
            if bs:
                for l in list(bs.inputs['Metallic'].links): m.node_tree.links.remove(l)
                bs.inputs['Metallic'].default_value = 0.0; bs.inputs['Roughness'].default_value = 0.55 if not bs.inputs['Roughness'].links else bs.inputs['Roughness'].default_value
def fighter(uid, h, team): u = unit(uid, h); ring(u, team); smooth(u); return u
SPARK = mat('spark', (1, 0.8, 0.3), 0.4, emit=(1.0, 0.72, 0.25), estr=45)
def sparks(c, t, n=16, seed=1, speed=7.0):
    r_ = random.Random(seed); f0 = F(t); c = Vector(c)
    ld = bpy.data.lights.new('sparkL', 'POINT'); ld.color = (1.0, 0.8, 0.5); ld.shadow_soft_size = 0.3; lo = bpy.data.objects.new('sparkL', ld); COL.objects.link(lo); lo.location = c
    for f, e in ((f0 - 1, 0), (f0, 9000), (f0 + 3, 3000), (f0 + 7, 0)): ld.energy = e; ld.keyframe_insert('energy', frame=f)
    for i in range(n):
        v = Vector((r_.uniform(-1, 1), r_.uniform(-1, 1), r_.uniform(0.1, 1.2))).normalized() * r_.uniform(0.4, 1.0) * speed
        o = box('spk', (0.035, 0.035, 0.22), c, SPARK); o.rotation_euler = v.to_track_quat('Z', 'Y').to_euler(); o.visible_shadow = False
        o.scale = (0.001,) * 3; key(o, 'scale', f0 - 1); o.scale = (1, 1, 1); key(o, 'scale', f0)
        for k_ in range(0, 13, 2):
            tt = k_ / FPS; o.location = c + v * tt + Vector((0, 0, -0.5 * 14 * tt * tt)); key(o, 'location', f0 + k_)
        o.scale = (0.001,) * 3; key(o, 'scale', f0 + 13); const(o)
def dust(c, t, R=1.0, seed=2, n=5):
    r_ = random.Random(seed); f0 = F(t); c = Vector(c)
    for i in range(n):
        off = Vector((r_.uniform(-1, 1), r_.uniform(-1, 1), r_.uniform(0.1, 0.5))) * R * 0.7; rr = R * r_.uniform(0.5, 0.9)
        o = ico('dust', 1.0, c + off, DUST); o.visible_shadow = False
        for f, s, dz in ((f0, 0.001, 0), (f0 + 6, rr * 0.7, 0.2), (f0 + 26, rr * 1.2, 0.9), (f0 + 50, 0.001, 1.6)):
            o.scale = (s,) * 3; key(o, 'scale', f); o.location = c + off * (1 + 0.02 * (f - f0)) + Vector((0, 0, dz)); key(o, 'location', f)
def stand(u, x, y, hd, t0, t1, c='ready', sp=1.0):
    place(u, (x, y, 0), hd, F(t0)); clip(u, c, F(t0), F(t1), sp)
def fight(u, t0, t1, sp=1.1, phase=0):
    f = F(t0) + phase; names = [n for n in ('attack1', 'attack2', 'attack3') if n in u['clips']]; i = phase
    while f < F(t1):
        a = u['clips'][names[i % len(names)]]; L = max(10, int((a.frame_range[1] - a.frame_range[0]) * 0.8 / sp)); clip(u, names[i % len(names)], f, min(f + L, F(t1)), sp); f += L; i += 1
N_, S_ = heading(0, 1), heading(0, -1)        # facing the red end / the blue end
BLUE = {}; REDU = {}
# x, y at the line-up; lane (bridge x); slot offset at the bridge
for uid, h, x, y, lane, dx in (('floki', 3.0, 3.5, -22.6, 3.5, 0.0), ('bonk', 2.6, 2.1, -23.4, 3.5, -1.1), ('swordcat', 2.7, 4.9, -23.4, 3.5, 1.1),
                               ('whale', 4.6, 14.5, -22.4, 14.5, 0.0), ('toshi', 2.7, 16.1, -23.5, 14.5, 1.3), ('pepe', 2.6, 12.7, -24.3, 14.5, -1.8)):
    u = fighter(uid, h, 'b'); BLUE[uid] = u; u['lane'] = lane; u['dx'] = dx
    stand(u, x, y, N_, 0, T_FIGHT, 'ready' if uid != 'whale' else 'idle')
    ymeet = -17.0 - (0.3 if dx else 0) - (0.5 if uid == 'whale' else 0)
    if uid == 'pepe': ymeet = -21.5
    u['t_arr'] = run_to(u, [(x, y), (lane + dx, ymeet)], T_FIGHT + 0.05 * abs(dx), 4.6 if uid != 'whale' else 3.9, 'run', 1.15); u['pos'] = (lane + dx, ymeet)
for uid, h, x, y, lane, dx in (('troll', 2.8, 3.5, -9.4, 3.5, 0.0), ('zcat', 2.5, 2.1, -8.6, 3.5, -1.1), ('baton', 2.7, 4.9, -8.6, 3.5, 1.1),
                               ('giga', 3.4, 14.5, -9.6, 14.5, 0.0), ('triplet', 2.7, 16.1, -8.5, 14.5, 1.3), ('ket', 2.5, 12.9, -8.5, 14.5, -1.3)):
    u = fighter(uid, h, 'r'); REDU[uid] = u; u['lane'] = lane; u['dx'] = dx
    if uid == 'giga': stand(u, x, y, S_, 0, 6.6, 'ready'); clip(u, 'emote', F(6.6), F(9.6)); clip(u, 'ready', F(9.6), F(T_FIGHT))
    else: stand(u, x, y, S_, 0, T_FIGHT, 'ready')
    ymeet = -15.0 + (0.3 if dx else 0) + (0.4 if uid == 'giga' else 0)
    u['t_arr'] = run_to(u, [(x, y), (lane + dx, ymeet)], T_FIGHT + 0.05 * abs(dx), 4.6, 'run', 1.15); u['pos'] = (lane + dx, ymeet)
B, R = BLUE, REDU
def mid(a, b_, z=1.8): return Vector(((a['pos'][0] + b_['pos'][0]) / 2, (a['pos'][1] + b_['pos'][1]) / 2, z))
def ko(u, t, away, **kw):     # fights until t, then is sent flying
    fight(u, u['t_arr'], t, 1.1, sum(map(ord, u['id'])) % 3); fling(u, t, away, **kw)
# --- the left bridge
ko(R['zcat'], 17.5, (-1.0, 0.8), up=9, dist=9, dur=1.3); sparks(mid(B['bonk'], R['zcat']), 17.5, 18, 3); dust(mid(B['bonk'], R['zcat'], 0.3), 17.5, 0.9, 3)
for i, t in enumerate((16.7, 17.6, 18.5, 19.4, 20.2)): sparks(mid(B['swordcat'], R['baton'], 2.0), t, 12, 10 + i, 5.0)
ko(R['troll'], 19.3, (0.3, 1.0), up=11, dist=11, dur=1.4); sparks(mid(B['floki'], R['troll']), 19.3, 20, 4); dust(mid(B['floki'], R['troll'], 0.3), 19.3, 1.0, 4)
ko(R['baton'], 20.9, (1.0, 0.7), up=10, dist=10, dur=1.3); sparks(mid(B['swordcat'], R['baton']), 20.9, 20, 5)
fight(B['floki'], B['floki']['t_arr'], 18.2, 1.1); clip(B['floki'], 'hit', F(18.2), F(18.9), 1.0); fight(B['floki'], 18.9, 19.6, 1.2); clip(B['floki'], 'win', F(19.6), F(T_TOWER + 2.2))
fight(B['bonk'], B['bonk']['t_arr'], 17.9, 1.2, 1); clip(B['bonk'], 'win', F(17.9), F(T_TOWER + 2.2))
fight(B['swordcat'], B['swordcat']['t_arr'], 21.2, 1.2, 2); clip(B['swordcat'], 'win', F(21.2), F(T_TOWER + 2.2))
# --- the right bridge: the wizard's bolt, the ninja, and the two giants
PZ = B['pepe']; clip(PZ, 'ready', F(PZ['t_arr']), F(16.9)); clip(PZ, 'attack1', F(16.9), F(17.7), 0.9); clip(PZ, 'ready', F(17.7), F(19.6)); clip(PZ, 'attack1', F(19.6), F(20.4), 0.9); clip(PZ, 'win', F(20.4), F(T_TOWER + 2.2))
BOLT = mat('bolt', (0.3, 1, 0.4), 0.3, emit=(0.25, 1.0, 0.35), estr=40)
def bolt(a, tgt, t0, t1):
    o = ico('bolt', 0.28, a, BOLT, 2); o.visible_shadow = False; ld = bpy.data.lights.new('boltL', 'POINT'); ld.color = (0.3, 1.0, 0.4); ld.energy = 6000; ld.shadow_soft_size = 0.4
    lo = bpy.data.objects.new('boltL', ld); COL.objects.link(lo); lo.parent = o
    o.scale = (0.001,) * 3; key(o, 'scale', F(t0) - 1); o.scale = (1, 1, 1); key(o, 'scale', F(t0)); o.location = a; key(o, 'location', F(t0)); o.location = tgt; key(o, 'location', F(t1))
    o.scale = (0.001,) * 3; key(o, 'scale', F(t1) + 1); const(o); linear(o)
    for f, e in ((F(t0) - 1, 0), (F(t0), 6000), (F(t1), 6000), (F(t1) + 1, 0)): ld.energy = e; ld.keyframe_insert('energy', frame=f)
kp = Vector((R['ket']['pos'][0], R['ket']['pos'][1], 1.5)); pp = Vector((PZ['pos'][0] + 0.3, PZ['pos'][1] + 0.8, 2.3))
bolt(pp, kp, 17.25, 17.6); explode(kp, 17.6, 1.5, FIREGRN, 0, 51, SMOKEG, light=(0.3, 1.0, 0.3)); ko(R['ket'], 17.6, (-1.0, 0.6), up=10, dist=9, dur=1.3)
ko(R['triplet'], 19.1, (1.0, 0.9), up=9, dist=10, dur=1.3); sparks(mid(B['toshi'], R['triplet']), 19.1, 20, 6)
for i, t in enumerate((16.6, 17.4, 18.2)): sparks(mid(B['toshi'], R['triplet'], 1.9), t, 10, 20 + i, 5.0)
fight(B['toshi'], B['toshi']['t_arr'], 19.4, 1.3, 1); clip(B['toshi'], 'win', F(19.4), F(T_TOWER + 2.2))
WH, GG = B['whale'], R['giga']
fight(GG, GG['t_arr'], T_SLAM, 1.0)
fight(WH, WH['t_arr'], 17.7, 0.9); clip(WH, 'hit', F(17.7), F(18.5), 0.9); fight(WH, 18.5, 19.8, 0.9); clip(WH, 'hit', F(19.8), F(20.6), 0.9); clip(WH, 'ready', F(20.6), F(22.2))
for t, back in ((17.7, 0.7), (19.8, 0.8)):      # the champion's punches drive the whale back
    key(WH['root'], 'location', F(t)); WH['root'].location.y -= back; key(WH['root'], 'location', F(t) + 7); sparks(mid(WH, GG, 2.6), t, 14, int(t * 10), 6.0); dust(Vector((14.5, WH['root'].location.y, 0.3)), t, 0.9, int(t))
bolt(pp, Vector((GG['pos'][0], GG['pos'][1], 2.4)), 19.95, 20.3); explode(Vector((GG['pos'][0], GG['pos'][1], 2.2)), 20.3, 1.2, FIREGRN, 0, 52, SMOKEG, light=(0.3, 1.0, 0.3))
bpy.context.view_layer.update()
aw = WH['clips']['attack1']; slam_len = (aw.frame_range[1] - aw.frame_range[0]) * 0.8 / 0.45; hit_frac = (UJ['whale']['clips']['attack1']['hit'] or 0.4) / UJ['whale']['clips']['attack1']['dur']
f_sl = F(T_SLAM) - int(slam_len * hit_frac); clip(WH, 'attack1', f_sl, f_sl + int(slam_len), 0.45, 4); clip(WH, 'win', f_sl + int(slam_len), F(T_TOWER + 2.2))
gy = GG['pos'][1]; sw2 = bpy.data.objects.new('shock2', None); COL.objects.link(sw2); sw2.location = (14.5, gy - 0.8, 0.25)
bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.07, major_segments=64, location=(0, 0, 0)); tor = bpy.context.object; tor.data.materials.append(mat('shock2m', (0.4, 0.7, 1), 0.3, emit=(0.4, 0.7, 1.0), estr=30)); tor.parent = sw2
for f, s in ((F(T_SLAM) - 1, 0.001), (F(T_SLAM), 1.0), (F(T_SLAM) + 16, 16.0), (F(T_SLAM) + 17, 0.001)): sw2.scale = (s, s, min(s, 1.0)); key(sw2, 'scale', f)
linear(sw2); dust(Vector((14.5, gy - 0.8, 0.3)), T_SLAM, 1.7, 9, 7); sparks(Vector((14.5, gy - 0.5, 2.2)), T_SLAM, 30, 77, 9.0)
# the champion leaves the bridge and arrives in his own tower
r = GG['root']; sc.frame_set(F(T_SLAM)); p0 = r.matrix_world.translation.copy(); p1 = Vector((14.5, -6.6, 3.6)); n = F(T_CRASH) - F(T_SLAM)
for i in range(n + 1):
    u_ = i / n; p = p0.lerp(p1, u_) + Vector((0, 0, 5.5 * 4 * u_ * (1 - u_))); r.location = p; key(r, 'location', F(T_SLAM) + i); r.rotation_euler = (-u_ * 9.0, 0, r.rotation_euler.z); key(r, 'rotation_euler', F(T_SLAM) + i)
clip(GG, 'die', F(T_SLAM), F(T_CRASH) + 1, 0.8, 0); sx = r.scale.copy(); key(r, 'scale', F(T_CRASH)); r.scale = sx * 0.0001; key(r, 'scale', F(T_CRASH) + 1); const(r)
CREW = {}
for k in ('rL', 'rR'):
    u = unit('chillguy', 1.87); place(u, (*TPOS[k], 3.86), 0.0); sched(u, [(0, 'idle', 1), (T_MEET, 'ready', 1), (T_CRASH, 'hit', 0.6), (T_CRASH + 1.2, 'lose', 1.5)] if k == 'rR' else [(0, 'idle', 1), (T_TOWER + 0.3, 'hit', 0.5), (T_TOWER + 1.6, 'lose', 1)]); CREW[k] = u
for k in ('bL', 'bR'):
    u = unit('chillguy', 1.87); place(u, (*TPOS[k], 3.86), math.pi); sched(u, [(0, 'idle', 1), (T_MEET, 'ready', 1), (T_TOWER + 0.4, 'win', 1)])
KB = unit('neet', 2.2); place(KB, (9, -29.5 + 0.55, 3.75), math.pi); sched(KB, [(0, 'sit', 1), (T_FIGHT, 'sityell', 1), (T_MEET + 1.5, 'sitcheer', 1), (T_SLAM, 'sitfistpump', 1), (T_FIRE - 0.5, 'sityell', 1), (T_TOWER, 'sitfistpump', 1), (T_TOWER + 2.5, 'sitclap', 1)])
KR = unit('pudgy', 2.5); place(KR, (9, -3.05, 4.3), 0.0); sched(KR, [(0, 'idle', 1), (6.6, 'emote', 1.0), (9.8, 'win', 0.8), (T_MEET + 1.4, 'ready', 1), (T_CRASH + 0.1, 'hit', 0.45), (T_CRASH + 1.7, 'lose', 1.6), (T_TOWER + 0.1, 'hit', 0.45), (T_TOWER + 1.7, 'lose', 1.3)])
# the crash: the tower shakes and coughs dust but holds
e = TW['rR']; cx = TPOS['rR'][0]
for i, dx in enumerate((0.0, 0.22, -0.2, 0.14, -0.1, 0.05, 0.0)): e.location.x = cx + dx; key(e, 'location', F(T_CRASH) + i * 2)
e.location.x = cx; dust(Vector((14.5, -6.8, 3.6)), T_CRASH, 2.2, 31, 8); sparks(Vector((14.5, -7.2, 3.8)), T_CRASH, 26, 32, 8.0); explode(Vector((14.5, -7.4, 3.2)), T_CRASH, 1.3, FIRE, 14, 33, DUST)
# the blue king's cannon answers
MUZ = Vector((9, -26.6, 5.25)); TGT = Vector((14.5, -6.6, 3.4)); T_BALL = T_TOWER - T_FIRE
ball = sphere('cannonball', 0.6, MUZ, mat('ballm', (0.05, 0.03, 0.02), 0.4, emit=(1.0, 0.35, 0.05), estr=5.0))
bl_ = bpy.data.lights.new('ballL', 'POINT'); bl_.color = (1.0, 0.5, 0.2); bl_.energy = 0; bl_.shadow_soft_size = 0.6; blo = bpy.data.objects.new('ballL', bl_); COL.objects.link(blo); blo.parent = ball
for f_, e_ in ((F(T_FIRE) - 1, 0), (F(T_FIRE), 12000), (F(T_TOWER), 12000), (F(T_TOWER) + 1, 0)): bl_.energy = e_; bl_.keyframe_insert('energy', frame=f_); ball.scale = (0.001,) * 3; key(ball, 'scale', F(T_FIRE) - 1); ball.scale = (1, 1, 1); key(ball, 'scale', F(T_FIRE))
nb = F(T_TOWER) - F(T_FIRE)
for i in range(nb + 1):
    u_ = i / nb; ball.location = MUZ.lerp(TGT, u_) + Vector((0, 0, 4.0 * 4 * u_ * (1 - u_))); key(ball, 'location', F(T_FIRE) + i)
ball.scale = (0.001,) * 3; key(ball, 'scale', F(T_TOWER) + 1); const(ball); linear(ball)
explode(MUZ + Vector((0, 0.6, 0)), T_FIRE, 1.1, FIRE, 0, 34, DUST, light=(1.0, 0.7, 0.3)); sparks(MUZ + Vector((0, 0.8, 0)), T_FIRE, 24, 35, 10.0)
kill_tower('rR', T_TOWER, 61, [CREW['rR']])
# the heroes regroup and pose
for i, (uid, x, y) in enumerate((('floki', 5.2, -12.2), ('bonk', 3.6, -12.8), ('swordcat', 6.9, -12.6), ('whale', 9.6, -10.6), ('toshi', 12.3, -12.5), ('pepe', 14.0, -12.9))):
    u = B[uid]; t0 = T_TOWER + 0.5 + 0.1 * i + (0.5 if uid == 'whale' else 0); sc.frame_set(F(t0)); p = u['root'].matrix_world.translation
    via = [(p.x, p.y), (u['lane'], -14.2), (x, y)] if uid != 'pepe' else [(p.x, p.y), (14.5, -18.2), (14.5, -14.2), (x, y)]
    ta = run_to(u, via, t0, 5.2 if uid != 'whale' else 4.4, 'run', 1.2); place(u, (x, y, 0), S_, F(ta) + 5); clip(u, 'ready', F(ta), F(T_WIN + 0.15 * i)); clip(u, 'win' if i % 2 else 'emote', F(T_WIN + 0.15 * i), LAST + 2)
