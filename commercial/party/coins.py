# Meme-coin party decorations for party.py (run inside its namespace, after dressing.py and environment.py).
# Giant gold coins with tickers, coin pool floats and coin balloons, a pump chart on an LED wall behind the DJ, HODL /
# WEN LAMBO? / 1 $MEME = 1 $MEME neons, a TO THE MOON inflatable rocket on the lawn, and a BUY THE DIP sign at the pool.
LILITA = bpy.data.fonts.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "lilita.ttf")) \
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "lilita.ttf")) else None
GOLD = mat("coin_gold", "#F2B731", rough=0.22, metal=1.0)
GOLD_DK = mat("coin_gold_dk", "#9A6A12", rough=0.35, metal=1.0)

def label(text, size, m, extrude=0.01, font=LILITA):
    cu = bpy.data.curves.new("lbl", "FONT"); cu.body = text; cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = extrude
    if font: cu.font = font
    o = bpy.data.objects.new("lbl_" + text, cu); sc.collection.objects.link(o); o.data.materials.append(m); return o

def coin(ticker, loc, rot, r=0.5, depth=0.09):
    """A big gold coin, ticker embossed on both faces, a raised rim. Its face points along its local Z."""
    c = cyl("coin_" + ticker, (0, 0, 0), r, depth, GOLD, v=64)
    for sgn in (1, -1):
        bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.9, minor_radius=depth * 0.22, major_segments=64, minor_segments=8, location=(0, 0, sgn * depth / 2))
        rim = obj_mat(bpy.context.active_object, GOLD_DK); rim.data.shade_smooth(); rim.parent = c
        t = label(ticker, r * (0.62 if len(ticker) <= 5 else 0.42), GOLD_DK, extrude=depth * 0.12)
        t.location = (0, 0, sgn * (depth / 2 + 0.004)); t.rotation_euler = (0, 0 if sgn == 1 else math.pi, 0); t.parent = c
    c.location = loc; c.rotation_euler = rot
    return c

# leaning against the house front, facing the pool
for t, x, r in (("$DOGE", -5.7, 0.55), ("$PEPE", -4.5, 0.48), ("$BONK", 4.9, 0.5), ("$WIF", 6.05, 0.44)):
    coin(t, (x, 4.72, r * 0.97 + 0.02), (math.radians(76), 0, random.uniform(-0.15, 0.15)), r)
# a coin rolled onto the south deck, flat
coin("$POPCAT", (-7.4, -6.2, 0.05), (0, 0, 0.4), 0.42)
# coin pool floats, bobbing and turning
for t, x, y in (("$MEME", 1.9, -1.55), ("$BRETT", 5.0, -1.3)):
    f_ = coin(t, (x, y, WZ + 0.05), (0, 0, 0), 0.6, 0.14)
    for f in range(1, N + 1, 30):
        f_.location.z = WZ + 0.05 + 0.03 * math.sin(f / 11 + x); f_.rotation_euler = (0.04 * math.sin(f / 9 + x), 0.04 * math.cos(f / 13), f / 300)
        f_.keyframe_insert("location", frame=f); f_.keyframe_insert("rotation_euler", frame=f)
# gold coin balloons among the house-front balloons, slowly spinning on their strings
for i, t in enumerate(("$PNUT", "$GIGA", "$MEW", "$WIF", "$MOODENG", "$DOGE")):
    x, y, z = -5.0 + i * 2.0 + random.uniform(-0.3, 0.3), random.uniform(3.4, 4.1), random.uniform(2.4, 3.0)
    b = coin(t, (x, y, z), (math.pi / 2, 0, 0), 0.24, 0.05)
    cyl("string", (x, y, z - 0.75), 0.003, 1.0, mat("tp", "#FAFAF7", rough=0.9), v=6)
    for f in range(1, N + 1, 20):
        b.rotation_euler = (math.pi / 2, 0, 0.6 * math.sin(f / 25 + i)); b.location.z = z + 0.05 * math.sin(f / 17 + i)
        b.keyframe_insert("rotation_euler", frame=f); b.keyframe_insert("location", frame=f)

# the LED wall behind the DJ: a pump chart, green candles going straight up
box("led_wall", 8.55, 8.65, -6.2, -3.95, 1.6, 3.4, mat("led_back", "#05060A", rough=0.4), bevel=0.0)
UP, DN = mat("candle_up", "#21FF6B", emit=9.0), mat("candle_dn", "#FF2D4A", emit=9.0)
lvl = 1.9
for i in range(11):
    y = -4.05 - i * 0.2; red = i in (3, 8)   # read from the dance floor (looking east, north is on the left): rising to the right
    step = -0.06 if red else (0.05 + 0.01 * i)
    lo_, hi_ = (lvl + step, lvl) if red else (lvl, lvl + step)
    box("candle", 8.52, 8.55, y - 0.06, y + 0.06, lo_, hi_ + 0.01, DN if red else UP, bevel=0.0)
    box("wick", 8.525, 8.545, y - 0.008, y + 0.008, lo_ - 0.05, hi_ + 0.06, DN if red else UP, bevel=0.0)
    lvl += step
t = label("PUMP IT", 0.26, mat("neon_#21FF6B", "#21FF6B", emit=10.0), 0.02); t.location = (8.5, -4.75, 3.12); t.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
light("led_glow", "AREA", (8.2, -4.8, 2.5), 90, "#21FF6B", 2.0, rot=(0, -math.pi / 2, 0))

# neons
neon("HODL", (11.95, -0.9, 2.35), (math.pi / 2, 0, -math.pi / 2), 0.5, "#2BE0FF", 12.0)   # hung under the pergola, over the smokers
for dy in (-0.55, 0.55):
    cyl("wire", (11.95, -0.9 + dy, 2.65), 0.003, 0.32, mat("blackwire", "#111111"), v=6)
neon("WEN LAMBO?", (-5.2, GY1 - 0.3, 2.95), (math.pi / 2, 0, 0), 0.28, "#FFE02B", 10.0)    # over the TV
neon("1 $MEME = 1 $MEME", (3.2, GY1 - 0.31, 2.7), (math.pi / 2, 0, 0), 0.17, "#21FF6B", 10.0)  # over the kitchen cabinets

# TO THE MOON: an inflatable rocket on the lawn, tethered, swaying
gz = tz(-8.6, -12.2)
WHITE_V = mat("vinyl_w", "#F4F4F0", rough=0.35); RED_V = mat("vinyl_r", "#E8302A", rough=0.35)
rk = bpy.data.objects.new("rocket", None); sc.collection.objects.link(rk); rk.location = (-8.6, -12.2, gz)
parts = [cyl("rocket_body", (0, 0, 1.75), 0.48, 2.6, WHITE_V, v=40)]
bpy.ops.mesh.primitive_cone_add(radius1=0.48, radius2=0.0, depth=1.1, location=(0, 0, 3.6), vertices=40); parts.append(obj_mat(bpy.context.active_object, RED_V))
parts[-1].data.shade_smooth()
for a in range(3):
    th = a * math.tau / 3
    parts.append(box("fin", -0.04, 0.04, 0.35, 0.95, 0.45, 1.3, RED_V, bevel=0.02)); parts[-1].rotation_euler = (0, 0, th)
parts.append(cyl("window", (0, -0.47, 2.4), 0.17, 0.05, mat("rk_glass", "#3AA0FF", rough=0.05, metal=0.3, emit=1.5), rot=(math.pi / 2, 0, 0), v=32))
bpy.ops.mesh.primitive_cone_add(radius1=0.32, radius2=0.05, depth=0.7, location=(0, 0, 0.15), rotation=(math.pi, 0, 0), vertices=24)
parts.append(obj_mat(bpy.context.active_object, mat("flame", "#FF8A1A", emit=14.0)))
for p_ in parts: p_.parent = rk
for f in range(1, N + 1, 30):
    rk.rotation_euler = (0.04 * math.sin(f / 23), 0.05 * math.cos(f / 29), 0); rk.keyframe_insert("rotation_euler", frame=f)
t = label("TO THE MOON", 0.34, mat("neon_#FFFFFF", "#FFFFFF", emit=9.0), 0.02)
t.location = (-8.6, -12.75, gz + 0.55); t.rotation_euler = (math.pi / 2, 0, 0)
light("rocket_up", "SPOT", (-8.6, -14.5, gz + 0.3), 600, "#FFD7A0", 0.2, rot=(math.radians(62), 0, 0), spot=math.radians(40))

# BUY THE DIP: a sign at the pool edge, an arrow pointing into the water, next to Pink Wojak
SIGN = mat("sign_board", "#F7F3E8", rough=0.6)
box("sign_post", -3.68, -3.62, -3.05, -2.99, 0.0, 1.3, mat("oak", "#8A5A32"))
box("sign_board", -4.05, -3.25, -3.06, -3.02, 0.95, 1.45, SIGN)
t = label("BUY THE DIP", 0.13, mat("sign_ink", "#D41E2A", rough=0.5), 0.004); t.location = (-3.65, -3.065, 1.27); t.rotation_euler = (math.pi / 2, 0, 0)
bpy.ops.mesh.primitive_cone_add(radius1=0.09, radius2=0.0, depth=0.22, location=(-3.65, -2.9, 1.0), rotation=(-math.radians(110), 0, 0), vertices=4)
obj_mat(bpy.context.active_object, mat("sign_ink", "#D41E2A", rough=0.5))   # an arrow at the water
