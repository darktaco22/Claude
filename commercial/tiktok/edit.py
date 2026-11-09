# The TikTok cut: "Day 1 of trying to break MEME ROYALE". Real gameplay captured from the live game (1080x1920 frames from
# the engine, phone layout), cut into a hook + three speed sections, with captions, a live USELESS counter, the game's own
# battle music and the game's own sound effects placed from the engine's sound log.
#   python3 edit.py CAP_DIR OVERLAY_DIR AUDIO_DIR FONT OUT.mp4
import sys, os, json, math, subprocess, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
CAP, OV, AUD, FONT, OUT = sys.argv[1:6]
WORK = os.path.join(os.path.dirname(os.path.abspath(OUT)), "tt_edit_work"); os.makedirs(WORK + "/fr", exist_ok=True)
FPS = 30
OLD, NEW = os.path.join(CAP, "frames"), os.path.join(CAP, "frames2")
F_FIGHT = 80          # the frame "FIGHT!" plays (battle time 0)

# ---------------------------------------------------------------------- the timeline: (source dir, source frame) per output frame
segs = []   # (name, dir, a, b, step)
segs.append(("hook", OLD, 1040, 1080, 1.0))      # 1.3 s of the flood first: the hook
segs.append(("start", OLD, 62, 400, 2.0))        # the names, FIGHT, the first armies and forks, at 2x
segs.append(("grow", OLD, 400, 1095, 1.3))       # the swarm takes over, a little fast
segs.append(("finale", NEW, 1095, 1330, 1.0))    # the towers fall, VICTORY
segs.append(("end", NEW, 1330, 1395, 1.0))       # the rewards, the call to action
tl = []
for name, d, a, b, st in segs:
    x = a
    while x < b:
        tl.append((name, d, int(x))); x += st
N = len(tl)
first = {}
for i, (n, d, f) in enumerate(tl): first.setdefault(n, i)
def out_at(seg, src):   # the output frame showing source frame src in segment seg
    best = None
    for i, (n, d, f) in enumerate(tl):
        if n == seg and f >= src: return i
    return best

# ---------------------------------------------------------------------- captions (output frame ranges)
def rng(a, b): return (a, b)
CAPS = [("c_wait", rng(0, first["start"]))]
s = first["start"]
CAPS += [("c_plan", rng(s + 12, out_at("start", 190))),
         ("c_fork", rng(out_at("start", 190), first["grow"] + 20)),
         ("c_mult", rng(first["grow"] + 45, out_at("grow", 700))),
         ("c_hot", rng(out_at("grow", 730), out_at("grow", 930))),
         ("c_1000", rng(out_at("grow", 950), first["finale"] + 10)),
         ("c_works", rng(out_at("finale", 1240), first["end"] + 10)),
         ("c_day2", rng(first["end"] + 12, N))]
OVL = {n: Image.open(os.path.join(OV, n + ".png")).convert("RGBA") for n, _ in CAPS + [("title", 0)]}

# ---------------------------------------------------------------------- the counter (measured in test runs of the same script)
KEYS = [(-9, 0), (2.2, 0), (2.4, 15), (3.6, 30), (6, 75), (12, 120), (18, 220), (22, 385), (26, 530), (30, 710), (32, 856),
        (35, 975), (37, 1050), (39, 1110), (40.5, 1146), (99, 1146)]
def count_at(src):
    t = (src - F_FIGHT) / FPS
    for (t0, c0), (t1, c1) in zip(KEYS, KEYS[1:]):
        if t0 <= t < t1: return int(c0 + (c1 - c0) * (t - t0) / (t1 - t0))
    return 0
fnt = ImageFont.truetype(FONT, 64)
def counter(img, n):
    if n <= 0: return
    d = ImageDraw.Draw(img); txt = f"USELESS ON MAP: {n:,}"
    w = d.textbbox((0, 0), txt, font=fnt, stroke_width=7)[2]
    x = (1080 - w) // 2; y = 372
    d.rounded_rectangle((x - 30, y - 10, x + w + 30, y + 84), 30, fill=(20, 10, 50, 190))
    d.text((x, y), txt, font=fnt, fill=(255, 226, 74), stroke_width=7, stroke_fill=(0, 0, 0))

# ---------------------------------------------------------------------- frames
for i, (seg, d, f) in enumerate(tl):
    p = os.path.join(WORK, "fr", f"o_{i:04d}.png")
    if os.path.exists(p): continue
    im = Image.open(os.path.join(d, f"f_{f:04d}.png")).convert("RGBA")
    if im.size != (1080, 1920): im = im.resize((1080, 1920), Image.LANCZOS)
    if seg == "hook":   # a slow push in on the flood
        k = 1.0 + 0.08 * (i / max(1, first["start"]))
        w, h = int(1080 / k), int(1920 / k)
        im = im.crop(((1080 - w) // 2, (1920 - h) // 2 - 120, (1080 - w) // 2 + w, (1920 - h) // 2 - 120 + h)).resize((1080, 1920), Image.LANCZOS)
    for cut in (first["start"], first["finale"]):   # a short white flash on the big cuts
        if cut <= i < cut + 3:
            im = Image.blend(im, Image.new("RGBA", im.size, (255, 255, 255, 255)), 0.6 - 0.2 * (i - cut))
    im = Image.alpha_composite(im, OVL["title"])
    counter(im, count_at(f) if seg != "hook" else 1146)
    for n, (a, b) in CAPS:
        if a is not None and b is not None and a <= i < b:
            cap = OVL[n]
            age = i - a
            if age < 5:   # a pop in
                k = 0.7 + 0.3 * (age / 5) + 0.08 * math.sin(age / 5 * math.pi)
                cap = cap.resize((int(1080 * k), int(1920 * k)), Image.LANCZOS)
                big = Image.new("RGBA", (1080, 1920)); big.paste(cap, ((1080 - cap.width) // 2, int(1240 - 1240 * k)), cap); cap = big
            im = Image.alpha_composite(im, cap)
    im.convert("RGB").save(p, optimize=False, compress_level=1)
print("frames", N, "=", round(N / FPS, 2), "s")

# ---------------------------------------------------------------------- sound: the game's music + its own effects from the engine log
man = json.load(open(os.path.join(AUD, "manifest.json")))
L = json.load(open(os.path.join(NEW, "sfx.json"))); st = L["start"]
evs = [(round((e["t"] - st) / (1000 / FPS)), e["id"], e.get("file")) for e in L["sfx"] if e.get("id") and e.get("file") and not e.get("music") and not e.get("amb")]
by_src = {}
for f, id_, file in evs: by_src.setdefault(f, []).append((id_, file))
SWARM = {"atk_useless", "coin_jingle", "tower_hit", "swing", "die_useless", "bark_useless"}
place, last = [], {}
for i, (seg, d, f) in enumerate(tl):
    for id_, file in by_src.get(f, []):
        t = i / FPS
        gap = 0.09 if id_ in SWARM else 0.05
        if t - last.get(id_, -9) < gap: continue
        last[id_] = t
        vol = man.get(id_, {}).get("vol", 1.0) * (0.5 if id_ in SWARM else 1.0)
        place.append((t, os.path.join(AUD, file), vol))
# the hook has no log of its own: a bed of the swarm's coins
for k in range(14):
    place.append((k * 0.09, os.path.join(AUD, man["coin_jingle"]["file"]), 0.4))
place.append((first["start"] / FPS, os.path.join(AUD, man["spell_hardfork"]["file"]), 0.9))
dur = N / FPS
print("sounds", len(place))
# mix in chunks of 60 inputs (ffmpeg's amix), then together with the music
chunks = [place[i:i + 60] for i in range(0, len(place), 60)]
parts = []
for ci, ch in enumerate(chunks):
    out = os.path.join(WORK, f"sfx_{ci:03d}.wav"); parts.append(out)
    if os.path.exists(out): continue
    args = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y"]
    for t, path, v in ch: args += ["-i", path]
    fc = ";".join(f"[{j}:a]aresample=48000,aformat=channel_layouts=stereo,volume={v:.3f},adelay={int(t * 1000)}|{int(t * 1000)}[a{j}]" for j, (t, path, v) in enumerate(ch))
    fc += ";" + "".join(f"[a{j}]" for j in range(len(ch))) + f"amix=inputs={len(ch)}:normalize=0:duration=longest,apad,atrim=0:{dur:.3f}[o]"
    subprocess.run(args + ["-filter_complex", fc, "-map", "[o]", out], check=True)
sfx = os.path.join(WORK, "sfx.wav")
args = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y"]
for p in parts: args += ["-i", p]
subprocess.run(args + ["-filter_complex", "".join(f"[{j}:a]" for j in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0,atrim=0:{dur:.3f}[o]", "-map", "[o]", sfx], check=True)
mus = os.path.join(AUD, man["mus_battle_cemetery"]["file"])
mix = os.path.join(WORK, "mix.wav")
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", mus, "-i", sfx, "-filter_complex",
                f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.55,atrim=0:{dur:.3f},afade=t=out:st={dur - 1.2:.3f}:d=1.2[m];"
                f"[1:a]volume=1.0[s];[m][s]amix=inputs=2:normalize=0,alimiter=limit=0.89,loudnorm=I=-14:TP=-2:LRA=11[o]",
                "-map", "[o]", "-ar", "48000", mix], check=True)
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(WORK, "fr", "o_%04d.png"),
                "-i", mix, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT], check=True)
print("wrote", OUT)
