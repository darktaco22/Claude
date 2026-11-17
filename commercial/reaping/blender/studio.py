"""THE REAPING - 'THE POPCAT HOUR', the pre-Games talk show. A built TV studio: glossy floor, round marble riser with LED rim,
curved LED wall (night skyline), neon sign, anchor desk, guest armchair (Poly Haven), coffee table + tissues, plants,
coloured rim lights and an audience in the dark. Popcat hosts; Wojak sits, crying."""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from mathutils import Vector
import bmesh
sc = reset(); TEX = os.path.join(A, 'tex'); random.seed(5)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.01, 0.01, 0.014, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
sc.view_settings.look = 'AgX - Punchy'

def emis(name, col, s): return mat(name, (0, 0, 0), 0.5, emit=col, estr=s)
floor = pbr('floor', os.path.join(PH, 'dark_wooden_planks'), scale=6.0, rough_mul=0.35, tint=(0.55, 0.45, 0.4))
plane('floor', 40, 40, (0, 0, 0), m=floor)
marble = pbr('marble', os.path.join(PH, 'marble_01'), scale=2.0, rough_mul=0.4)
cyl('riser', 4.2, 0.22, (0, 1.0, 0.11), marble, verts=128)
bpy.ops.mesh.primitive_torus_add(major_radius=4.21, minor_radius=0.025, major_segments=192, location=(0, 1.0, 0.2)); led = bpy.context.object; led.data.materials.append(emis('ledrim', (0.2, 0.75, 1.0), 6.0))
FZ = 0.22
# ---- curved LED wall (night skyline) with panel seams
def arc_wall(name, R, a0, a1, h, z0, cy, m, seg=96):
    bm = bmesh.new(); rows = []
    for j in (0, 1):
        rows.append([bm.verts.new((R * math.sin(a), cy + R * math.cos(a), z0 + j * h)) for a in [a0 + (a1 - a0) * i / seg for i in range(seg + 1)]])
    uv = None; faces = []
    for i in range(seg): faces.append(bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i])))
    uvl = bm.loops.layers.uv.new()
    for i, f in enumerate(faces):
        for l in f.loops:
            v = l.vert; k = next(ii for ii in range(seg + 1) if rows[0][ii] == v or rows[1][ii] == v); l[uvl].uv = (k / seg, 0.0 if v in rows[0] else 1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    return o
wallm = bpy.data.materials.new('ledwall'); wallm.use_nodes = True; N, L = wallm.node_tree.nodes, wallm.node_tree.links; b = N['Principled BSDF']
tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(TEX, 'skyline.png')); uvn = N.new('ShaderNodeUVMap'); mp = N.new('ShaderNodeMapping')
mp.inputs['Scale'].default_value = (1, 0.8, 1); mp.inputs['Location'].default_value = (0, 0.2, 0); L.new(uvn.outputs['UV'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], tx.inputs['Vector'])
grid = N.new('ShaderNodeTexBrick'); grid.inputs['Scale'].default_value = 1.0; grid.offset = 0; grid.inputs['Mortar Size'].default_value = 0.0025; grid.inputs['Brick Width'].default_value = 0.04; grid.inputs['Row Height'].default_value = 0.12
grid.inputs['Color1'].default_value = (1, 1, 1, 1); grid.inputs['Color2'].default_value = (1, 1, 1, 1); grid.inputs['Mortar'].default_value = (0.15, 0.15, 0.15, 1); L.new(uvn.outputs['UV'], grid.inputs['Vector'])
mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0; L.new(tx.outputs['Color'], mx.inputs['A']); L.new(grid.outputs['Color'], mx.inputs['B'])
L.new(mx.outputs['Result'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.05; b.inputs['Base Color'].default_value = (0.01, 0.01, 0.01, 1); b.inputs['Roughness'].default_value = 0.25
arc_wall('ledwall', 8.5, -0.95, 0.95, 4.6, 0.0, -2.5, wallm)
# ---- neon sign: THE POPCAT HOUR
def neon_text(text, size, loc, col, strength=18, extrude=0.02, bevel=0.012, rotx=math.pi / 2):
    cu = bpy.data.curves.new('neon', 'FONT'); cu.body = text; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = extrude; cu.bevel_depth = bevel
    try: cu.font = bpy.data.fonts.load('/usr/share/fonts/opentype/inter/Inter-Black.otf')
    except Exception: pass
    o = link(bpy.data.objects.new('neon_' + text[:6], cu)); o.location = loc; o.rotation_euler = (rotx, 0, 0); o.data.materials.append(emis('neon_' + text[:4], col, strength)); return o
box('sign_plate', (5.6, 0.08, 1.7), (0, 4.85, 4.15), mat('plate', (0.012, 0.012, 0.016), 0.35, 0.4))
neon_text('THE', 0.42, (0, 4.79, 4.62), (1.0, 0.85, 0.2), 14)
neon_text('POPCAT HOUR', 0.78, (0, 4.79, 3.95), (1.0, 0.18, 0.62), 22)
for x in (-2.55, 2.55): cyl('sign_cable', 0.008, 2.2, (x, 4.85, 6.1), mat('cable', (0.02, 0.02, 0.02), 0.5))
# ---- anchor desk (curved, walnut front, glossy top, underglow)
walnut = pbr('walnut', os.path.join(PH, 'dark_wooden_planks'), scale=3.0, tint=(0.75, 0.5, 0.35), rough_mul=0.6)
def arc_box(name, R0, R1, a0, a1, z0, z1, cx, cy, m, seg=64):
    bm = bmesh.new()
    def ring(R, z): return [bm.verts.new((cx + R * math.sin(a), cy - R * math.cos(a), z)) for a in [a0 + (a1 - a0) * i / seg for i in range(seg + 1)]]
    A_, B_, C_, D_ = ring(R0, z0), ring(R1, z0), ring(R1, z1), ring(R0, z1)
    for i in range(seg):
        for P, Q in ((A_, B_), (B_, C_), (C_, D_), (D_, A_)): bm.faces.new((P[i], P[i + 1], Q[i + 1], Q[i]))
    for P, Q, R_, S_ in ((A_, B_, C_, D_),): bm.faces.new((P[0], Q[0], R_[0], S_[0])); bm.faces.new((S_[-1], R_[-1], Q[-1], P[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); me.materials.append(m)
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.01; bv.segments = 2; bv.limit_method = 'ANGLE'; return o
DX, DY = -1.7, 1.9
arc_box('desk_body', 0.55, 0.95, -0.9, 0.9, FZ + 0.06, FZ + 1.0, DX, DY, walnut)
arc_box('desk_top', 0.5, 1.02, -0.92, 0.92, FZ + 1.0, FZ + 1.05, DX, DY, mat('desktop', (0.02, 0.02, 0.025), 0.12, 0.3))
arc_box('desk_glow', 0.96, 0.975, -0.88, 0.88, FZ + 0.03, FZ + 0.06, DX, DY, emis('deskglow', (1.0, 0.2, 0.6), 12))
plane('desk_logo', 0.9, 0.9, (DX, DY - 0.965, FZ + 0.55), rot=(math.pi / 2, 0, 0), m=image_mat('deskplaque', os.path.join(TEX, 'pophour.png'), emit=0.6, rough=0.4))
cyl('mug_host', 0.045, 0.1, (DX + 0.45, DY - 0.55, FZ + 1.1), mat('mug', (0.85, 0.85, 0.85), 0.25))
# ---- guest: armchair, coffee table, tissues, plants
GX, GY = 1.35, 1.35
ph('modern_arm_chair_01', (GX, GY, FZ), face(-0.85, -1), 0.82)
SEATZ = seat_top(GX, GY)
ph('modern_coffee_table_01', (0.0, 0.55, FZ), 0, 1.0)
box('tissue_box', (0.24, 0.12, 0.1), (0.35, 0.5, FZ + 0.47), mat('tbox', (0.35, 0.75, 0.85), 0.5))
for i in range(3): box(f'tissue_{i}', (0.08, 0.06, 0.002), (0.35 + i * 0.01 - 0.01, 0.5, FZ + 0.54 + i * 0.012), mat('tis', (0.95, 0.95, 0.95), 0.9), rot=(0.4, 0.3 * i, 0.2))
cyl('mug_guest', 0.045, 0.1, (-0.25, 0.6, FZ + 0.47), mat('mug2', (0.8, 0.8, 0.82), 0.25))
ph('pachira_aquatica_01', (3.6, 2.6, FZ), 0.3, 1.2); ph('calathea_orbifolia_01', (-3.7, 2.9, FZ), 1.0, 1.4); ph('potted_plant_02', (2.6, 3.4, FZ), 0.0, 1.3)
# ---- audience (in the dark, backs to camera) + rails
seatm = mat('seat', (0.03, 0.03, 0.035), 0.6)
for r, y in enumerate((-4.2, -5.4)):
    box(f'rail_{r}', (9.0, 0.06, 0.06), (0, y + 0.45, 0.85 + r * 0.3), mat('rail', (0.2, 0.2, 0.22), 0.3, 1.0))
AUD = ['goat', 'floki', 'cate', 'toshi', 'pnut', 'walter', 'slerf', 'nyancat', 'swordcat', 'chillguy']
CAST = {}
for i, cid in enumerate(AUD):
    if not os.path.exists(os.path.join(UNITS, cid + '.glb')): continue
    r = i // 5; x = -3.2 + (i % 5) * 1.6 + random.uniform(-0.2, 0.2); y = -4.4 - r * 1.2
    c = load(cid, (x, y, 0.0 + r * 0.3), face(-x * 0.05, 1), 0.95); CAST[f'aud{i}'] = c
# ---- the cast
POP = load('popcat', (DX, DY + 0.45, FZ), face(0.35, -1), 0.95); CAST['popcat'] = POP
WJ = load('wojak', (GX, GY + 0.05, FZ), face(-0.85, -1), 1.0, subd=False); CAST['wojak'] = WJ
import tears as TR
print('TEARS', len(TR.build(WJ, 1, 400, period=20)))
TOTAL = arg('--frames', 360, int); sc.frame_start, sc.frame_end = 1, TOTAL
for k, c in CAST.items():
    if k in ('popcat', 'wojak'): continue
    clip(c, 'idle', 1 - random.randint(0, 30), TOTAL + 10, speed=random.uniform(0.85, 1.05))
clip(POP, 'idle', -10, TOTAL + 10)
for f0, f1 in ((86, 104), (112, 128), (300, 320)): clip(POP, 'attack1', f0, f1, speed=1.3, blend=3)   # the 'pop' mouth while talking
# Wojak sits, slumped, sobbing: FK seated legs on the measured cushion, IK arms (hands on knees)
off, kL, kR = sit_fk(WJ, SEATZ, front_y=-0.31, flesh=0.07, slope=float(arg('--slope', 26)))
for f in range(1, TOTAL + 1, 3):
    sob = 0.5 + 0.5 * math.sin(f * 0.55); sob2 = math.sin(f * 1.1)
    WJ.key(f, {'hips': off, 'spine': 0.3 + 0.04 * sob, 'lean': 0.02 * sob2,
               'hand_L': kL + Vector((0.0, 0.06, 0.09 + 0.01 * sob)), 'hand_R': kR + Vector((0.0, 0.06, 0.09 + 0.01 * sob)),
               'look': WJ.headp + Vector((0.0, -2.0, -0.9 + 0.12 * sob2)), 'nosafe': True})
# ---- lights
lamp('key_host', 'AREA', (DX - 1.6, DY - 3.0, 2.8), (DX, DY + 0.4, 1.6), energy=420, color=(1.0, 0.93, 0.85), size=1.6)
lamp('key_guest', 'AREA', (GX + 1.8, GY - 2.8, 2.6), (GX, GY, 1.0), energy=380, color=(1.0, 0.93, 0.86), size=1.6)
lamp('fill', 'AREA', (0, -3.5, 2.2), (0, 1.5, 1.0), energy=260, color=(0.8, 0.85, 1.0), size=4.0)
lamp('rim_m', 'SPOT', (-3.5, 4.0, 4.2), (DX, DY, 1.4), energy=900, color=(1.0, 0.25, 0.7), size=0.2, spot=35)
lamp('rim_c', 'SPOT', (3.8, 3.8, 4.2), (GX, GY, 1.0), energy=800, color=(0.25, 0.75, 1.0), size=0.2, spot=35)
for x in (-3.0, 0.0, 3.0): lamp(f'pool_{x}', 'SPOT', (x, 1.0, 6.0), (x * 0.7, 1.2, 0.0), energy=600, color=(1.0, 0.9, 0.8), size=0.1, spot=28, blend=0.5)
lamp('aud_back', 'AREA', (0, -8.0, 3.0), (0, -4.5, 1.0), energy=40, color=(0.5, 0.6, 1.0), size=6.0)
# ---- cameras
cams = {}
def shot(name, f, cam): cams[name] = cam; bind(cam, f); return cam
c = shot('T1_wide', 1, camera('T1_wide', (0.6, -7.4, 3.2), (0, 2.0, 1.6), lens=30, fstop=5.6)); key_cam(c, 1, loc=(0.6, -7.4, 3.2), look=(0, 2.0, 1.75)); key_cam(c, 70, loc=(0.4, -6.2, 2.2), look=(0, 2.0, 1.45)); handheld(c, 0.003, 0.0015, seed=11)
PH_ = Vector((DX, DY + 0.45, FZ + 1.25)); c = shot('T2_pop', 81, camera('T2_pop', (0.1, -1.9, 1.85), (-1.05, 2.8, 2.3), lens=38, fstop=3.2)); key_cam(c, 81, loc=(0.1, -1.9, 1.85)); key_cam(c, 150, loc=(0.0, -1.6, 1.85)); handheld(c, seed=12)
WH_ = Vector((GX, GY - 0.2, FZ + 0.95)); c = shot('T3_wojak', 161, camera('T3_wojak', (GX - 1.6, GY - 1.9, FZ + 1.05), WH_, lens=60, fstop=2.0)); key_cam(c, 161, loc=(GX - 1.6, GY - 1.9, FZ + 1.05)); key_cam(c, 220, loc=(GX - 1.5, GY - 1.75, FZ + 1.04)); handheld(c, seed=13)
c = shot('T4_two', 231, camera('T4_two', (0.3, -3.3, 1.6), (0, 1.6, 1.1), lens=32, fstop=4)); key_cam(c, 231, loc=(0.3, -3.3, 1.6)); key_cam(c, 290, loc=(0.25, -3.0, 1.55)); handheld(c, seed=14)
c = shot('T5_pop', 301, camera('T5_pop', (DX + 0.55, DY - 1.9, FZ + 1.95), PH_ + Vector((0, 0, 0.05)), lens=55, fstop=2.0)); key_cam(c, 301, loc=(DX + 0.55, DY - 1.9, FZ + 1.95)); key_cam(c, 350, loc=(DX + 0.5, DY - 1.7, FZ + 1.9)); handheld(c, seed=15)
cams['dbg_side'] = camera('dbg_side', (GX + 2.2, GY - 0.2, FZ + 0.9), (GX, GY, FZ + 0.6), lens=40, fstop=8)
cams['dbg_34'] = camera('dbg_34', (GX + 0.6, GY - 2.2, FZ + 1.0), (GX, GY, FZ + 0.6), lens=40, fstop=8)
cams['dbg_front'] = camera('dbg_front', (GX - 1.5, GY - 1.2, FZ + 0.75), (GX, GY, FZ + 0.6), lens=40, fstop=8)
sc.camera = cams['T1_wide']
if '--cams' in argv:
    out = arg('--out', '/tmp/stills'); os.makedirs(out, exist_ok=True)
    for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
    for spec in arg('--cams').split(','):
        cn, f = spec.split('@'); sc.camera = cams[cn]; sc.frame_set(int(f)); sc.render.filepath = os.path.join(out, f'{cn}_{int(f):04d}.png'); bpy.ops.render.render(write_still=True)
finish()
