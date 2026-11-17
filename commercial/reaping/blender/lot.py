"""THE REAPING - the reaping square, staged in a real parking lot (Poly Haven 'Mall Parking Lot' HDRI, CC0).
Stage faces -Y; the crowd stands at y<3 facing +Y. The mall (and the low sun) sit behind the stage."""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from mathutils import Vector
sc = reset(); TEX = os.path.join(A, 'tex'); random.seed(3)
HDRI_ROT = arg('--hrot', -34.0, float)
world_hdri(os.path.join(PH, 'mall_meme_16k.hdr'), strength=1.0, rot_deg=HDRI_ROT)

# ---------------------------------------------------------------- ground: real asphalt that dissolves into the photo
gm = pbr('asphalt', os.path.join(PH, 'asphalt_02'), scale=9.0, tint=(0.82, 0.82, 0.84))
nt = gm.node_tree; N, L = nt.nodes, nt.links; b = N['Principled BSDF']
geo = N.new('ShaderNodeNewGeometry'); vl = N.new('ShaderNodeVectorMath'); vl.operation = 'LENGTH'
sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs[0]); cmb = N.new('ShaderNodeCombineXYZ'); L.new(sep.outputs[0], cmb.inputs[0]); L.new(sep.outputs[1], cmb.inputs[1])
L.new(cmb.outputs[0], vl.inputs[0]); mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 16; mr.inputs['From Max'].default_value = 30
L.new(vl.outputs['Value'], mr.inputs['Value']); tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
L.new(mr.outputs['Result'], mx.inputs[0]); L.new(b.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], N['Material Output'].inputs['Surface'])
ground = plane('ground', 70, 70, (0, 0, 0), m=gm)
paint = mat('paint', (0.86, 0.86, 0.82), 0.7)
for i in range(-6, 7):   # parking stall lines (2.6 m bays) both sides of the square
    for y0 in (-11.0, 13.5):
        if abs(i) < 1 and y0 > 0: continue
        plane(f'stall_{i}_{y0}', 0.12, 5.0, (i * 2.6, y0, 0.004), m=paint)
for x in (-8.5, 8.5): plane(f'lane_{x}', 0.12, 22, (x, 1.0, 0.004), m=paint)

# ---------------------------------------------------------------- the stage
wood = pbr('stagewood', os.path.join(PH, 'dark_wooden_planks'), scale=2.5)
black = mat('black_cloth', (0.012, 0.012, 0.014), 0.9)
gold = mat('gold', (0.83, 0.62, 0.25), 0.28, 1.0)
velvet = mat('velvet', (0.11, 0.004, 0.008), 0.7, 0.0, **{'Sheen Weight': 0.6, 'Sheen Roughness': 0.3, 'Sheen Tint': (1.0, 0.35, 0.35, 1)})
SY = 6.4; SW, SD, SH = 8.0, 4.0, 0.55
box('stage_deck', (SW, SD, 0.08), (0, SY, SH - 0.04), wood, bevel=0.01)
box('stage_skirt', (SW + 0.02, SD + 0.02, SH - 0.08), (0, SY, (SH - 0.08) / 2), black)
for i in range(3): box(f'step_{i}', (2.4, 0.34, (i + 1) * SH / 4), (0, SY - SD / 2 - 0.17 - (2 - i) * 0.34, (i + 1) * SH / 8), wood, bevel=0.008)
box('carpet_stage', (2.2, SD - 0.3, 0.012), (0, SY - 0.1, SH + 0.006), velvet)
box('carpet_aisle', (2.0, 6.0, 0.01), (0, SY - SD / 2 - 1.2 - 3.0, 0.005), velvet)
box('trim_front', (SW, 0.05, 0.06), (0, SY - SD / 2, SH - 0.02), gold)
# the bowl of names on a slim pedestal at the host's right hand (his fins are short), and a lectern for show
WX, WY = 0.0, SY - 0.15                    # the Whale's spot
BX, BY = WX - 0.84, WY - 0.24; BS = 0.74; BZ = SH + 0.80
cyl('ped_col', 0.13, BZ - SH - 0.06, (BX, BY, SH + (BZ - SH - 0.06) / 2), wood, verts=40)
cyl('ped_base', 0.24, 0.05, (BX, BY, SH + 0.025), gold); cyl('ped_top', 0.2, 0.04, (BX, BY, BZ - 0.02), gold)
lec = box('lectern', (0.62, 0.46, 1.12), (WX + 1.25, WY - 0.6, SH + 0.56), wood, bevel=0.015)
box('lectern_cap', (0.72, 0.54, 0.05), (WX + 1.25, WY - 0.6, SH + 1.135), gold, bevel=0.01)
plaque = plane('plaque', 0.42, 0.42, (WX + 1.25, WY - 0.6 - 0.235, SH + 0.62), rot=(math.pi / 2, 0, 0), m=image_mat('plaque', os.path.join(TEX, 'plaque.jpg'), rough=0.35))
prof = [(r * BS, z * BS) for r, z in [(0.06, 0.0), (0.16, 0.004), (0.24, 0.03), (0.30, 0.09), (0.33, 0.17), (0.32, 0.25), (0.28, 0.31), (0.25, 0.335)]]
bowl = lathe('bowl', prof, (BX, BY, BZ), glass(), thick=0.006)
lathe('bowl_rim', [(0.252 * BS, 0.334 * BS), (0.258 * BS, 0.338 * BS), (0.252 * BS, 0.342 * BS)], (BX, BY, BZ), glass(rough=0.0))
paper = mat('paper', (0.62, 0.59, 0.52), 0.8, **{'Subsurface Weight': 0.15, 'Subsurface Radius': (0.3, 0.3, 0.25)})
slips = []
for i in range(70):   # folded name slips piled inside
    r = 0.2 * math.sqrt(random.random()); a = random.random() * math.tau; z = BZ + 0.025 + random.random() * 0.09 + (0.2 - r) * 0.2
    s = box(f'slip_{i}', (0.075, 0.042, 0.0015), (BX + math.cos(a) * r, BY + math.sin(a) * r, z), paper, rot=(random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), random.random() * 6.3))
    slips.append(s)
# banner on a gold-capped frame + hanging flags + jumbotron
banner = plane('banner', 6.6, 2.2, (0, SY + 1.6, SH + 3.15), rot=(math.pi / 2, 0, 0), m=image_mat('banner', os.path.join(TEX, 'banner.jpg'), rough=0.75))
for x in (-3.42, 3.42):
    cyl(f'pole_{x}', 0.07, 4.9, (x, SY + 1.62, SH + 2.45), black); sphere(f'finial_{x}', 0.13, (x, SY + 1.62, SH + 4.95), gold)
fm = image_mat('flag', os.path.join(TEX, 'flag.png'), rough=0.7); fm.blend_method = 'CLIP' if hasattr(fm, 'blend_method') else None
for i, x in enumerate((-5.3, -4.3, 4.3, 5.3)):
    fl = plane(f'flag_{i}', 0.9, 3.6, (x, SY + 1.5, SH + 2.4), rot=(math.pi / 2, 0, 0), m=fm)
    cyl(f'flagbar_{i}', 0.03, 1.05, (x, SY + 1.5, SH + 4.22), gold, rot=(0, math.pi / 2, 0))
    cl = fl.modifiers.new('wave', 'WAVE'); cl.height = 0.035; cl.width = 1.2; cl.speed = 0.04; cl.use_normal = True; cl.use_x = False
scr = box('jumbotron', (4.2, 0.25, 2.4), (8.2, SY + 0.4, 4.6), black, rot=(0, 0, math.radians(-22)))
plane('jumbo_led', 4.0, 2.25, (8.2 - 0.13 * math.sin(math.radians(22)), SY + 0.4 - 0.13 * math.cos(math.radians(22)), 4.6), rot=(math.pi / 2, 0, math.radians(-22)), m=image_mat('screen', os.path.join(TEX, 'screen.jpg'), emit=2.2, rough=0.3))
for dx in (-1.6, 1.6): cyl(f'jumbo_leg_{dx}', 0.09, 3.4, (8.2 + dx * math.cos(math.radians(22)), SY + 0.4 + dx * math.sin(math.radians(22)) * -1, 1.7), black)

# ---------------------------------------------------------------- crowd pens (gold stanchions + velvet rope)
def stanchion(x, y): cyl('st', 0.025, 0.95, (x, y, 0.475), gold); cyl('stb', 0.17, 0.035, (x, y, 0.017), gold); sphere('stt', 0.045, (x, y, 0.97), gold)
def rope(p, q):
    p, q = Vector(p), Vector(q); mid = (p + q) / 2; mid.z -= 0.14
    cu = bpy.data.curves.new('rope', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.022; cu.bevel_resolution = 4
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
    for bp, v in zip(sp.bezier_points, (p, mid, q)): bp.co = v; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = link(bpy.data.objects.new('rope', cu)); o.data.materials.append(velvet)
pts = [(-5.0, -5.5), (-5.0, -2.5), (-5.0, 0.5), (-5.0, 2.6), (-1.6, 2.6)]
for side in (-1, 1):
    P = [(side * abs(x) if x != -1.6 else side * 1.6, y) for x, y in pts]
    for x, y in P: stanchion(x, y + 0)
    for a, b2 in zip(P, P[1:]): rope((a[0], a[1], 0.9), (b2[0], b2[1], 0.9))
# lights: flood towers + stage wash (the HDRI sun backlights the stage)
for x in (-6.5, 6.5):
    g = ph('flood_lights', (x, 2.0, 0), face(-x, 3), 1.6)
lamp('key_stage', 'AREA', (-2.6, SY - 4.8, 3.6), (WX, WY, 2.4), energy=2600, color=(1.0, 0.9, 0.78), size=2.0)
lamp('fill_stage', 'AREA', (4.0, SY - 5.5, 3.2), (0, SY, 1.5), energy=500, color=(0.85, 0.9, 1.0), size=3.0)
lamp('crowd_key', 'AREA', (0, SY - 1.5, 5.0), (0, 0.5, 1.0), energy=320, color=(1.0, 0.95, 0.88), size=3.0)
ph('street_lamp_01', (-9.5, 9.5, 0), 0, 1.0); ph('street_lamp_01', (9.8, -6.5, 0), math.pi, 1.0)
ph('concrete_road_barrier', (-7.2, 9.0, 0), 0.2, 1.0); ph('concrete_road_barrier', (7.4, 9.4, 0), -0.15, 1.0)
ph('WetFloorSign_01', (3.6, 3.2, 0), 0.6, 1.0); ph('metal_trash_can', (-6.8, -3.5, 0), 0.3, 1.0); ph('fire_hydrant', (6.6, -1.2, 0), 1.0, 1.0)
ph('security_camera_01', (-3.42, SY + 1.5, SH + 4.3), math.pi, 1.0)
plane('sign', 1.6, 0.6, (-6.0, 3.0, 1.35), rot=(math.pi / 2, 0, math.radians(30)), m=image_mat('sign', os.path.join(TEX, 'sign.jpg'), rough=0.6))
cyl('sign_post', 0.035, 1.1, (-6.0, 3.03, 0.55), black)

# ---------------------------------------------------------------- the cast
import glove as GL, tears as TR
CAST = {}
CAST['whale'] = load('whale', (WX, WY, SH), face(-0.12, -1), 1.32)
CAST['wojak'] = load('wojak', (0.0, 1.2, 0), face(0, 1), 1.0, subd=False)
ROW = [('giga', -3.4, 1.12), ('pepe', -2.05, 1.0), ('bonk', -0.7, 1.0), ('troll', 0.7, 1.0), ('chillguy', 2.05, 1.0)]
for cid, x, s in ROW: CAST[cid] = load(cid, (x, -0.7, 0), face(0, 1), s)
EXTRA = [('goat', -3.3, -2.2), ('floki', -1.95, -2.3), ('cate', -0.65, -2.2), ('toshi', 0.65, -2.3), ('pnut', 1.95, -2.2), ('walter', 3.3, -2.3),
         ('slerf', -2.6, -3.5), ('nyancat', -1.3, -3.6), ('swordcat', 0.0, -3.5), ('floki', 1.3, -3.6), ('goat', 2.6, -3.5)]
for i, (cid, x, y) in enumerate(EXTRA):
    if os.path.exists(os.path.join(UNITS, cid + '.glb')): CAST[f'{cid}_{i}'] = load(cid, (x + random.uniform(-0.12, 0.12), y, 0), face(random.uniform(-0.12, 0.12), 1), random.uniform(0.94, 1.04))
TOTAL = arg('--frames', 700, int); sc.frame_start, sc.frame_end = 1, TOTAL
for cid, c in CAST.items():
    if cid in ('whale', 'wojak'): continue
    clip(c, 'idle', 1 - random.randint(0, 40), TOTAL + 10, speed=random.uniform(0.9, 1.1))
W, WJ, PP = CAST['whale'], CAST['wojak'], CAST['pepe']
print('TEARS', len(TR.build(WJ, 150, 720)))
clip(W, 'idle', -20, TOTAL + 10); clip(W, 'ready', 302, 358, speed=0.8, blend=8); 
clip(WJ, 'lose', -30, TOTAL + 10, speed=0.85); clip(WJ, 'hit', 413, 428, blend=3)
for ms in [o for o in WJ.rig.children if o.type == 'MESH']:   # the game's Wojak is mid-gray, not chalk white
    for m in ms.data.materials:
        nt = m.node_tree; b = nt.nodes.get('Principled BSDF'); lk = b.inputs['Base Color'].links if b else []
        if lk:
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0; mx.inputs['B'].default_value = (0.36, 0.37, 0.4, 1); b.inputs['Roughness'].default_value = 0.65; b.inputs['Specular IOR Level'].default_value = 0.3
            nt.links.new(lk[0].from_socket, mx.inputs['A']); nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
# ---- E: everybody (but Wojak) hops one step back, in sync, at f411
HOP = 411
for cid, c in CAST.items():
    if cid in ('whale', 'wojak'): continue
    p = c.ctrl.location.copy(); sd = random.uniform(-1.2, 1.2)
    for f, dy, dz, sz in ((HOP - 6, 0, 0, 1.0), (HOP - 2, 0, 0, 0.9), (HOP + 1, -0.35, 0.12, 1.06), (HOP + 4, -0.8, 0.16, 1.03), (HOP + 7, -1.0, 0.0, 0.93), (HOP + 11, -1.0, 0.0, 1.0)):
        f = int(f + sd * 0); c.ctrl.location = (p.x, p.y + dy, p.z + dz); c.ctrl.keyframe_insert('location', frame=f)
        c.ctrl.scale = (c.ctrl.scale.x, c.ctrl.scale.y, c.ctrl.scale.x * sz); c.ctrl.keyframe_insert('scale', frame=f)
# ---- F: Pepe raises his hand (f520), then points at Wojak (f593)
ik = PP.rig.pose.bones['mixamorig:RightForeArm'].constraints['IK']
for f, inf in ((1, 0.0), (514, 0.0), (521, 1.0), (700, 1.0)): ik.mute = False; ik.influence = inf; ik.keyframe_insert('influence', frame=f)
T = PP.T['hand_R']
for f, v in ((514, PP.arm_at('R', 0.05, 0.12, -0.9)), (521, PP.arm_at('R', 0.1, 0.42, 1.05)), (540, PP.arm_at('R', 0.12, 0.48, 1.02)), (560, PP.arm_at('R', 0.08, 0.40, 1.06)),
             (586, PP.arm_at('R', 0.1, 0.44, 1.04)), (594, PP.arm_at('R', 0.95, 0.38, 0.28)), (700, PP.arm_at('R', 0.97, 0.36, 0.26))):
    T.location = v; T.keyframe_insert('location', frame=f)
pole = PP.T['pole_R']; pole.location = PP.shoulderR + Vector((-0.4, 0.4, -0.5)); pole.keyframe_insert('location', frame=1)
# ---- A: the Whale's gloved fin draws a name (IK solved, baked to FK on its own NLA track)
import reach as RC
BOWL = Vector((BX, BY, BZ))
RC.glove_fins(W, ('Right', 'Left'))
SH_R = W.rig.matrix_world @ W.rig.data.bones['mixamorig:RightArm'].head_local
print('WHALE shoulder', SH_R)
pole = SH_R + Vector((0.1, 0.6, -0.5)); TOPB = Vector((BX, BY, BZ + 0.25 * BS))
keys = [(1, SH_R + Vector((-0.05, -0.05, -0.42)), pole), (10, SH_R + Vector((-0.2, -0.1, -0.2)), pole), (20, TOPB + Vector((0.08, 0.02, -0.02)), pole), (25, TOPB + Vector((0.06, 0.05, -0.05)), pole),
        (30, TOPB + Vector((0.09, -0.02, -0.04)), pole), (36, TOPB + Vector((0.07, 0.01, -0.03)), pole), (56, SH_R + Vector((-0.3, -0.32, 0.02)), pole), (90, SH_R + Vector((-0.3, -0.33, 0.04)), pole)]
RC.bake(W, 'Right', keys, 1, 98, blend=4, name='whale_reach')
tip = W.rig.pose.bones['mixamorig:RightForeArm']
anchor = link(bpy.data.objects.new('slip_anchor', None)); cn = anchor.constraints.new('COPY_LOCATION'); cn.target = W.rig; cn.subtarget = 'mixamorig:RightForeArm'; cn.head_tail = 1.0
slip = plane('slip_drawn', 0.15, 0.075, (0, 0, 0), rot=(math.pi / 2, 0, 0), m=image_mat('slipw', os.path.join(TEX, 'slip_wojak.jpg'), rough=0.8)); slip.parent = anchor; slip.location = (-0.03, -0.1, -0.09)
slip.hide_render = True; slip.keyframe_insert('hide_render', frame=1); slip.hide_render = False; slip.keyframe_insert('hide_render', frame=36); slip.hide_render = True; slip.keyframe_insert('hide_render', frame=95)
# ---- cameras (one per shot, bound by markers)
cams = {}
def shot(name, f, cam): cams[name] = cam; bind(cam, f); return cam
c = shot('A_hand', 1, camera('A_hand', (BX - 0.35, BY - 0.95, BZ + 0.42), (BX, BY, BZ + 0.2), lens=55, fstop=2.2))
SLIPEND = SH_R + Vector((-0.32, -0.42, -0.06))
key_cam(c, 1, focus=TOPB); key_cam(c, 38, focus=TOPB); key_cam(c, 56, focus=SLIPEND)
key_cam(c, 1, loc=(BX - 0.35, BY - 0.95, BZ + 0.42), look=TOPB); key_cam(c, 38, loc=(BX - 0.35, BY - 0.95, BZ + 0.42), look=TOPB); key_cam(c, 62, focus=SLIPEND); key_cam(c, 40, lens=55); key_cam(c, 80, loc=SLIPEND + Vector((-0.12, -0.62, 0.03)), look=SLIPEND, lens=62)
handheld(c, 0.0025, 0.0015, seed=1)
WH = Vector((WX, WY, SH + 2.1))
c = shot('B_whale', 101, camera('B_whale', (0.35, SY - 2.9, 2.25), WH + Vector((0, 0, 0.35)), lens=50, fstop=2.2)); key_cam(c, 101, loc=(0.35, SY - 2.9, 2.25)); key_cam(c, 150, loc=(0.32, SY - 2.65, 2.28)); handheld(c, seed=2)
WJH = Vector((0.0, 1.2, 1.18))
c = shot('C_wojak', 161, camera('C_wojak', (0.18, 2.62, 1.3), WJH, lens=85, fstop=1.8)); key_cam(c, 161, loc=(0.18, 2.62, 1.3)); key_cam(c, 290, loc=(0.14, 2.42, 1.27)); handheld(c, seed=3)
c = shot('D_whale', 301, camera('D_whale', (-2.1, SY - 4.6, 1.75), (WX - 0.2, WY - 0.3, 1.95), lens=38, fstop=4)); key_cam(c, 301, loc=(-1.9, SY - 4.6, 1.75)); key_cam(c, 360, loc=(-1.75, SY - 4.3, 1.8)); handheld(c, seed=4)
c = shot('E_crowd', 371, camera('E_crowd', (0.4, SY - 2.6, 2.2), (0.0, -0.9, 1.0), lens=34, fstop=5.6)); key_cam(c, 371, loc=(0.4, SY - 2.6, 2.2)); key_cam(c, 500, loc=(0.36, SY - 2.85, 2.1)); handheld(c, 0.003, 0.0018, seed=5)
PH_ = Vector((-2.05, -1.7, 1.42))
c = shot('F_pepe', 511, camera('F_pepe', (-1.72, 0.75, 1.5), PH_, lens=50, fstop=2.0)); key_cam(c, 511, loc=(-1.72, 0.75, 1.5), lens=50); key_cam(c, 545, loc=(-1.72, 0.75, 1.5), lens=50)
key_cam(c, 588, loc=(-1.8, 0.2, 1.5), lens=54); key_cam(c, 630, loc=(-1.8, 0.15, 1.5), lens=54); handheld(c, seed=6)
c = shot('G_wojak', 641, camera('G_wojak', (-0.15, 2.75, 1.32), WJH + Vector((0, 0, 0.1)), lens=85, fstop=1.8)); key_cam(c, 641, loc=(-0.15, 2.75, 1.32)); key_cam(c, 700, loc=(-0.12, 2.55, 1.3)); handheld(c, seed=7)
cams['dbg_slip'] = camera('dbg_slip', (BX - 1.0, BY - 1.9, BZ + 1.2), (BX + 0.3, BY, BZ + 0.6), lens=35, fstop=8)
cams['dbg_face'] = camera('dbg_face', (0.05, 2.25, 1.3), (0.0, 1.2, 1.25), lens=135, fstop=5.6)
cams['wide_stage'] = camera('wide_stage', (2.2, -8.5, 4.2), (0, SY - 1, 1.6), lens=24, fstop=8)
sc.camera = cams['A_hand']
if '--cams' in argv:   # look-dev: named camera at a frame, e.g. --cams A_hand@60,C_wojak@200
    out = arg('--out', '/tmp/stills'); os.makedirs(out, exist_ok=True); ms = list(sc.timeline_markers)
    for m in ms: sc.timeline_markers.remove(m)
    for spec in arg('--cams').split(','):
        cn, f = spec.split('@'); sc.camera = cams[cn]; sc.frame_set(int(f)); sc.render.filepath = os.path.join(out, f'{cn}_{int(f):04d}.png'); bpy.ops.render.render(write_still=True)
finish()
