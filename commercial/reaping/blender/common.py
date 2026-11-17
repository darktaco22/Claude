"""THE REAPING (Blender side): shared scene tools. Cycles + AgX, game characters (Mixamo rigs) with the party IK controller,
Poly Haven assets, cinematic cameras (DOF, handheld noise), and a CLI for stills / saving / rendering."""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Euler, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'party'))
import moves as M

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None, cast=str):
    return cast(argv[argv.index(name) + 1]) if name in argv else default
A = arg('--assets', '/root/reap3d')            # units/, ph/, tex/
UNITS, PH = os.path.join(A, 'units'), os.path.join(A, 'ph')
FPS = 30

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.fps = FPS
    sc.render.engine = 'CYCLES'; cy = sc.cycles; cy.device = 'CPU'
    cy.samples = arg('--samples', 32, int); cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; cy.denoising_prefilter = 'ACCURATE'
    cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.035; cy.adaptive_min_samples = 8
    cy.max_bounces = 5; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.transmission_bounces = 6; cy.transparent_max_bounces = 6; cy.volume_bounces = 0
    cy.light_sampling_threshold = 0.02; sc.render.use_persistent_data = True
    cy.texture_limit_render = '4096'
    cy.sample_clamp_indirect = 8.0; cy.caustics_reflective = False; cy.caustics_refractive = False
    sc.render.resolution_x = arg('--w', 1080, int); sc.render.resolution_y = arg('--h', 1920, int); sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.use_motion_blur = arg('--mblur', 0, int) == 1; sc.render.motion_blur_shutter = 0.5
    sc.render.image_settings.file_format = 'PNG'; sc.render.film_transparent = False
    return sc

# ------------------------------------------------------------------ materials
def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emit=None, estr=0.0, **extra):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = estr
    for k, v in extra.items(): b.inputs[k].default_value = v
    return m
def pbr(name, folder, scale=1.0, tint=None, rough_mul=1.0, disp=0.0):
    """Poly Haven texture set (diff / nor_gl / rough or arm) with box-free UV scaling"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['Principled BSDF']
    files = os.listdir(folder); find = lambda *ks: next((os.path.join(folder, f) for f in files if any(k in f for k in ks)), None)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale); L.new(tc.outputs['UV'], mp.inputs['Vector'])
    def tex(p, non_color=False):
        t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(p); L.new(mp.outputs['Vector'], t.inputs['Vector'])
        if non_color: t.image.colorspace_settings.name = 'Non-Color'
        return t
    d = find('diff', 'Diffuse')
    if d:
        t = tex(d); out = t.outputs['Color']
        if tint:
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            L.new(out, mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1); out = mx.outputs['Result']
        L.new(out, b.inputs['Base Color'])
    n = find('nor_gl')
    if n: t = tex(n, True); nm = N.new('ShaderNodeNormalMap'); L.new(t.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    r = find('rough', 'Rough'); arm = find('_arm')
    if r: t = tex(r, True); mt = N.new('ShaderNodeMath'); mt.operation = 'MULTIPLY'; mt.inputs[1].default_value = rough_mul; L.new(t.outputs['Color'], mt.inputs[0]); L.new(mt.outputs[0], b.inputs['Roughness'])
    elif arm:
        t = tex(arm, True); sp = N.new('ShaderNodeSeparateColor'); L.new(t.outputs['Color'], sp.inputs['Color']); L.new(sp.outputs['Green'], b.inputs['Roughness']); L.new(sp.outputs['Blue'], b.inputs['Metallic'])
    return m
def glass(name='glass', color=(0.92, 0.97, 1.0), rough=0.01, ior=1.47):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N['Principled BSDF']); g = N.new('ShaderNodeBsdfGlass'); g.inputs['Color'].default_value = (*color, 1); g.inputs['Roughness'].default_value = rough; g.inputs['IOR'].default_value = ior
    L.new(g.outputs[0], N['Material Output'].inputs['Surface']); return m
def image_mat(name, path, emit=0.0, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path); L.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    if emit: L.new(t.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    if t.image.depth == 32 or path.endswith('.png'): L.new(t.outputs['Alpha'], b.inputs['Alpha'])
    return m

# ------------------------------------------------------------------ geometry helpers
def link(o, coll=None): (coll or bpy.context.scene.collection).objects.link(o); return o
def box(name, size, loc, m=None, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot); o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel: bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'
    if m: o.data.materials.append(m)
    return o
def cyl(name, r, h, loc, m=None, verts=48, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    if m: o.data.materials.append(m)
    bpy.ops.object.shade_smooth(); return o
def sphere(name, r, loc, m=None, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc); o = bpy.context.object; o.name = name
    if m: o.data.materials.append(m)
    bpy.ops.object.shade_smooth(); return o
def plane(name, w, h, loc, rot=(0, 0, 0), m=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot); o = bpy.context.object; o.name = name; o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(scale=True)
    if m: o.data.materials.append(m)
    return o
def lathe(name, profile, loc, m=None, steps=96, thick=0.0):
    """profile: [(r, z), ...] revolved around Z"""
    bm = bmesh.new(); vs = [bm.verts.new((r, 0, z)) for r, z in profile]
    for a, b in zip(vs, vs[1:]): bm.edges.new((a, b))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=steps, use_merge=True)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); o.location = loc
    for p in me.polygons: p.use_smooth = True
    if thick: s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = thick; s.offset = 0
    if m: me.materials.append(m)
    return o
def import_gltf(path, loc=(0, 0, 0), rz=0.0, scale=1.0):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path); new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]; g = bpy.data.objects.new(os.path.basename(path) + '_root', None); link(g)
    for r in roots: r.parent = g
    g.location = loc; g.rotation_euler = (0, 0, rz); g.scale = (scale, scale, scale); return g
def ph(name, loc=(0, 0, 0), rz=0.0, scale=1.0):
    return import_gltf(os.path.join(PH, name, name + '.gltf'), loc, rz, scale)

# ------------------------------------------------------------------ characters
def face(dx, dy): return math.atan2(dx, -dy)            # ctrl z-rotation that faces (dx, dy)
def load(cid, loc, rot, scale=1.0, subd=True):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(UNITS, cid + '.glb'))
    new = [o for o in bpy.data.objects if o not in before]; rig = next(o for o in new if o.type == 'ARMATURE')
    drop = [o for o in new if o.type == 'MESH' and o.parent is None]; keep = [o for o in new if o not in drop]
    for o in drop: bpy.data.objects.remove(o)
    for o in [o for o in keep if o.type == 'MESH']:
        if subd: sd = o.modifiers.new('smooth', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1; sd.quality = 1; sd.use_limit_surface = False
    if rig.animation_data:
        for tr in rig.animation_data.nla_tracks: tr.mute = True   # the importer stashes every clip as a live NLA track
    c = M.Char(rig, cid); c.ctrl.location = loc; c.ctrl.rotation_euler = (0, 0, rot); c.ctrl.scale = (scale,) * 3
    return c
def clip(c, name, f0, f1, speed=1.0, blend=4):
    """the game's own clip on the NLA from f0 to f1 (IK muted)"""
    for pbn in c.rig.pose.bones:
        for cn in pbn.constraints: cn.mute = True
    act = c.clip_actions.get(name) or c.clip_actions['idle']; ad = c.rig.animation_data
    tr = ad.nla_tracks.new(); st = tr.strips.new(f'{name}_{f0}', f0, act); L = act.frame_range[1] - act.frame_range[0]
    st.scale = 1.0 / speed; st.repeat = max(1.0, (f1 - f0) / max(1.0, L / speed)); st.frame_end = f1
    st.blend_in = st.blend_out = min(blend, (f1 - f0) / 3); st.extrapolation = 'NOTHING'; ad.action = None
    return st

# ------------------------------------------------------------------ cameras
def camera(name, loc, look, lens=50, fstop=2.8, focus=None, sensor=36):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = sensor; cd.sensor_fit = 'HORIZONTAL'
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop; cd.dof.aperture_blades = 7
    o = link(bpy.data.objects.new(name, cd)); o.location = loc
    tgt = link(bpy.data.objects.new(name + '_look', None)); tgt.location = look
    tc = o.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    f = link(bpy.data.objects.new(name + '_focus', None)); f.location = focus or look; cd.dof.focus_object = f
    o['tgt'], o['foc'] = tgt.name, f.name
    return o
def key_cam(o, f, loc=None, look=None, focus=None, lens=None):
    T = bpy.data.objects[o['tgt']]; F = bpy.data.objects[o['foc']]
    if loc is not None: o.location = loc; o.keyframe_insert('location', frame=f)
    if look is not None: T.location = look; T.keyframe_insert('location', frame=f)
    if focus is not None: F.location = focus; F.keyframe_insert('location', frame=f)
    if lens is not None: o.data.lens = lens; o.data.keyframe_insert('lens', frame=f)
def handheld(o, amp=0.004, rot=0.0025, speed=1.0, seed=1):
    """subtle operator shake (noise on location / rotation offsets via a parent empty)"""
    p = link(bpy.data.objects.new(o.name + '_shake', None)); o.parent = p
    p.animation_data_create(); p.animation_data.action = bpy.data.actions.new(o.name + '_shake')
    for path, n, a in (('location', 3, amp), ('rotation_euler', 3, rot)):
        for i in range(n):
            fc = p.animation_data.action.fcurves.new(path, index=i); fc.keyframe_points.insert(1, 0.0)
            md = fc.modifiers.new('NOISE'); md.scale = 22 / speed; md.strength = a * 2; md.phase = seed * 13.7 + i * 5.1 + (0 if path == 'location' else 40)
    return p
def bind(cam, f):
    sc = bpy.context.scene; m = sc.timeline_markers.new(cam.name + str(f), frame=f); m.camera = cam
def lamp(name, kind, loc, look=None, energy=100, color=(1, 1, 1), size=0.5, spot=None, blend=0.3):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind in ('AREA',): ld.size = size; ld.shape = 'DISK'
    if kind in ('POINT', 'SPOT'): ld.shadow_soft_size = size
    if kind == 'SPOT': ld.spot_size = math.radians(spot or 40); ld.spot_blend = blend
    o = link(bpy.data.objects.new(name, ld)); o.location = loc
    if look:
        t = link(bpy.data.objects.new(name + '_aim', None)); t.location = look
        c = o.constraints.new('TRACK_TO'); c.target = t; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    return o
def world_hdri(path, strength=1.0, rot_deg=0.0, bg_strength=None):
    w = bpy.data.worlds.new('world'); bpy.context.scene.world = w; w.use_nodes = True; N, L = w.node_tree.nodes, w.node_tree.links
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot_deg))
    env = N.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path)
    L.new(tc.outputs['Generated'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], env.inputs['Vector'])
    bg = N['Background']; L.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    if bg_strength is not None:   # camera sees the plate at a different strength than the lighting
        bg2 = N.new('ShaderNodeBackground'); L.new(env.outputs['Color'], bg2.inputs['Color']); bg2.inputs['Strength'].default_value = bg_strength
        lp = N.new('ShaderNodeLightPath'); mx = N.new('ShaderNodeMixShader'); L.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
        L.new(bg.outputs[0], mx.inputs[1]); L.new(bg2.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], N['World Output'].inputs['Surface'])
    return w

# ------------------------------------------------------------------ CLI: stills / save / render range
def finish(default_stills=()):
    sc = bpy.context.scene
    if '--save' in argv: bpy.ops.wm.save_as_mainfile(filepath=arg('--save'))
    if '--stills' in argv:
        frames = [int(x) for x in arg('--stills').split(',')]; out = arg('--out', '/tmp/stills')
        os.makedirs(out, exist_ok=True)
        for f in frames:
            sc.frame_set(f); sc.render.filepath = os.path.join(out, f'still_{f:04d}.png'); bpy.ops.render.render(write_still=True)
    if '--range' in argv:
        a, b = [int(x) for x in arg('--range').split('-')]; sc.frame_start, sc.frame_end = a, b
        out = arg('--out', '/tmp/frames'); os.makedirs(out, exist_ok=True)
        for fn in os.listdir(out):   # a frame cut off mid-write would otherwise be skipped forever
            p = os.path.join(out, fn)
            if os.path.getsize(p) == 0: os.remove(p)
        sc.render.filepath = os.path.join(out, 'f_'); sc.render.use_overwrite = False; sc.render.use_placeholder = False
        bpy.ops.render.render(animation=True)

# ------------------------------------------------------------------ sitting
def seat_top(x, y, z0=2.5):
    """world height of the first surface below (x, y): the chair's cushion (call before characters are loaded)"""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nor, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector((x, y, z0)), Vector((0, 0, -1)))
    print('SEAT', round(loc.z, 3) if hit else None, ob.name if hit else None); return loc.z if hit else 0.45
def sit_pose(c, seat_z, back=0.08, spread=0.06, slump=0.0, flesh=0.06):
    """A seated pose in the character's own space: hip joints on the cushion, thighs level and forward, knees bent,
    shins down, feet planted (or dangling if the legs are short). Returns the pose dict and the knee points."""
    B = c.B; s = c.ctrl.scale.x; seat = (seat_z - c.ctrl.location.z) / s
    hl = lambda n: Vector(B[n].head_local)
    up_l, up_r, kn_l, ft_l = hl('mixamorig:LeftUpLeg' if 'mixamorig:LeftUpLeg' in B else 'LeftUpLeg'), hl('mixamorig:RightUpLeg' if 'mixamorig:RightUpLeg' in B else 'RightUpLeg'), c.footL, c.footL
    LL = Vector(B['LeftLeg'].head_local) if 'LeftLeg' in B else Vector(B['mixamorig:LeftLeg'].head_local)
    up_l = Vector(B['LeftUpLeg'].head_local) if 'LeftUpLeg' in B else up_l; up_r = Vector(B['RightUpLeg'].head_local) if 'RightUpLeg' in B else up_r
    thigh = (LL - up_l).length; shin = (c.footL - LL).length
    hz = seat + flesh - up_l.z                       # lift/drop of the whole hips
    hip_off = Vector((0, back, hz))
    joint_z = up_l.z + hz; floor = c.footL.z
    drop = joint_z - floor
    if drop <= shin: fz = floor; fwd = math.sqrt(max(0.0, shin ** 2 - drop ** 2)) * 0.7   # feet planted, shins angled a little forward
    else: fz = joint_z - shin; fwd = 0.0                                                   # short legs: they dangle
    kL = Vector((up_l.x + spread, back - thigh, joint_z)); kR = Vector((up_r.x - spread, back - thigh, joint_z))
    pose = {'hips': hip_off, 'spine': slump,
            'foot_L': Vector((kL.x + 0.02, kL.y - fwd, fz)), 'foot_R': Vector((kR.x - 0.02, kR.y - fwd, fz)), 'nosafe': True}
    return pose, kL, kR
def sit_knees(c, kL, kR):
    for n, k in (('knee_L', kL), ('knee_R', kR)):
        t = c.T[n]; t.location = k + Vector((0, -0.6, 0.15)); t.keyframe_insert('location', frame=1)
