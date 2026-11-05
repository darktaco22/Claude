"""
MEME ROYALE commercial: the edit, done in Blender's Video Sequence Editor.

The footage is rendered by the game's own three.js engine (see capture/), frame by frame; this script cuts it
together with titles, the phone mock-up, the game's music and every sound the game played during the capture.

    blender -b --factory-startup -P edit_commercial.py -- edit.json out.mp4 [--save edit.blend] [--stills 30,200 dir]
"""
import bpy, json, os, sys, math

argv = sys.argv[sys.argv.index("--") + 1:]
CFG = json.load(open(argv[0]))
OUT = os.path.abspath(argv[1])
BASE = os.path.dirname(os.path.abspath(argv[0]))
P = lambda p: p if os.path.isabs(p) else os.path.join(BASE, p)

FPS = 30
W, H = 1280, 720
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.fps = FPS
se = sc.sequence_editor_create()
FONT = bpy.data.fonts.load(P(CFG["font"]))

def hexc(h, a=1.0):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)

def frames_strip(name, folder, first, count, ch, at, fit="FIT"):
    files = [f"f_{i:04d}.png" for i in range(first, first + count)]
    s = se.sequences.new_image(name, os.path.join(P(folder), files[0]), ch, at, fit_method=fit)
    for f in files[1:]:
        s.elements.append(f)
    s.frame_final_duration = count
    return s

def still(name, path, ch, at, dur, fit="FIT"):
    s = se.sequences.new_image(name, P(path), ch, at, fit_method=fit)
    s.frame_final_duration = dur
    return s

def key(obj, path, frame, value, interp="BEZIER"):
    target, attr = obj, path
    if "." in path:
        head, attr = path.rsplit(".", 1)
        for part in head.split("."):
            target = getattr(target, part)
    setattr(target, attr, value)
    target.keyframe_insert(attr, frame=frame)

def text(body, at, dur, x, y, size, color="#FFFFFF", ch=20, outline="#1A0846", pop=True, anchor="CENTER"):
    t = se.sequences.new_effect(name="T_" + body[:12], type="TEXT", channel=ch, frame_start=at, frame_end=at + dur)
    t.text = body
    t.font = FONT
    t.font_size = size
    t.color = hexc(color)
    t.use_outline = True
    t.outline_color = hexc(outline)
    t.outline_width = 0.14
    t.use_shadow = True
    t.shadow_color = (0, 0, 0, 0.55)
    t.location = (x, y)
    t.anchor_x = anchor
    t.anchor_y = "CENTER"
    t.blend_type = "ALPHA_OVER"
    if pop:
        # the game's pop: in big, settle, out fast
        key(t, "font_size", at, size * 0.2)
        key(t, "font_size", at + 5, size * 1.15)
        key(t, "font_size", at + 9, size)
        key(t, "font_size", at + dur - 4, size)
        key(t, "font_size", at + dur, size * 0.2)
    return t

def flash(at, ch=30, dur=5, color="#FFFFFF", peak=0.9):
    c = se.sequences.new_effect(name="flash", type="COLOR", channel=ch, frame_start=at, frame_end=at + dur)
    c.color = hexc(color)[:3]
    c.blend_type = "ALPHA_OVER"
    key(c, "blend_alpha", at, peak)
    key(c, "blend_alpha", at + dur, 0.0)

def push(s, at, dur, s0=1.0, s1=1.08):
    """slow push-in on a strip (camera feel on stills)"""
    key(s, "transform.scale_x", at, s0); key(s, "transform.scale_y", at, s0)
    key(s, "transform.scale_x", at + dur, s1); key(s, "transform.scale_y", at + dur, s1)

# ---------------------------------------------------------------- picture
t = 0
sound_events = []
for seg in CFG["segments"]:
    kind, dur = seg["kind"], seg["dur"]
    if kind == "still":
        s = still(seg["name"], seg["path"], 1, t, dur)
        if seg.get("push"):
            push(s, t, dur, *seg["push"])
    elif kind == "full":
        s = frames_strip(seg["name"], seg["dir"], seg["from"], dur, 1, t)
        if seg.get("log"):
            sound_events.append((seg["log"], seg.get("snd_from", seg["from"]), dur, t, seg.get("snd_gain", 1.0)))
    elif kind == "phone":
        bg = still(seg["name"] + "_bg", CFG["backdrop"], 1, t, dur)
        push(bg, t, dur, 1.02, 1.1)
        s = frames_strip(seg["name"], seg["dir"], seg["from"], dur, 2, t, fit="ORIGINAL")
        s.blend_type = "ALPHA_OVER"
        fr = still(seg["name"] + "_frame", CFG["phone_frame"], 3, t, dur, fit="ORIGINAL")
        fr.blend_type = "ALPHA_OVER"
        for strip in (s, fr):
            strip.transform.offset_x = seg.get("phone_x", 0)
        sound_events.append((seg["log"], seg.get("snd_from", seg["from"]), dur, t, seg.get("snd_gain", 1.0)))
    elif kind == "endcard":
        bg = still("end_bg", CFG["endcard_bg"], 1, t, dur)
        push(bg, t, dur, 1.0, 1.06)
        logo = still("logo", CFG["logo"], 2, t, dur, fit="ORIGINAL")
        logo.blend_type = "ALPHA_OVER"
        k = 0.36
        logo.transform.offset_y = 70
        key(logo, "transform.scale_x", t, 0.05); key(logo, "transform.scale_y", t, 0.05)
        key(logo, "transform.scale_x", t + 8, k * 1.15); key(logo, "transform.scale_y", t + 8, k * 1.15)
        key(logo, "transform.scale_x", t + 13, k); key(logo, "transform.scale_y", t + 13, k)
        key(logo, "transform.scale_x", t + dur, k * 1.04); key(logo, "transform.scale_y", t + dur, k * 1.04)
    for tx in seg.get("texts", []):
        text(tx["body"], t + tx.get("at", 0), tx.get("dur", dur - tx.get("at", 0)), tx["x"], tx["y"], tx["size"], tx.get("color", "#FFFFFF"),
             ch=20 + seg["texts"].index(tx), pop=tx.get("pop", True))
    if seg.get("flash"):
        flash(t)
    t += dur
END = t
sc.frame_start, sc.frame_end = 0, END - 1

# ---------------------------------------------------------------- sound: the game's own
AUD = P(CFG["audio_dir"])
def snd(path, at, vol=1.0, pan=0.0, ch=40, dur=None):
    if not os.path.exists(path) or at >= END:
        return None
    s = se.sequences.new_sound(os.path.basename(path), path, ch, at)
    s.volume = vol
    try:
        s.pan = max(-1, min(1, pan))
    except Exception:
        pass
    if dur:
        s.frame_final_duration = dur
    if s.frame_final_end > END:
        s.frame_final_end = END
    return s

mus = CFG["music"]
m = snd(os.path.join(AUD, mus["file"]), 0, mus.get("vol", 0.5), ch=60)
if m:
    m.frame_final_end = END
    key(m, "volume", 0, 0.0)
    key(m, "volume", 10, mus.get("vol", 0.5))
    key(m, "volume", END - 40, mus.get("vol", 0.5))
    key(m, "volume", END - 1, 0.0)

logs = {}
used = 0
chan = [0] * 32   # a free-at frame per channel, so one-shots don't overlap within a channel
for (logname, src0, dur, at, gain) in sound_events:
    if logname not in logs:
        logs[logname] = json.load(open(P(logname)))
    L = logs[logname]
    for e in L["sfx"]:
        if e.get("music") or e.get("amb") or not e.get("file"):
            continue
        idx = round((e["t"] - L["start"]) / (1000 / 30)) - 1
        if not (src0 <= idx < src0 + dur):
            continue
        f = at + (idx - src0)
        path = os.path.join(AUD, e["file"])
        vol = (e.get("vol") or 0.8) * (e["o"].get("vol", 1.0) if e.get("o") else 1.0) * CFG.get("sfx_gain", 1.0) * gain
        for c in range(32):
            if chan[c] <= f:
                s = snd(path, f, vol, (e.get("o") or {}).get("pan", 0.0), ch=70 + c)
                if s:
                    chan[c] = s.frame_final_end
                    used += 1
                break
for ev in CFG.get("extra_sounds", []):
    snd(os.path.join(AUD, ev["file"]), ev["at"], ev.get("vol", 0.8), ch=66)
print("sound strips:", used)

# ---------------------------------------------------------------- output
r = sc.render
r.image_settings.file_format = "FFMPEG"
r.ffmpeg.format = "MPEG4"
r.ffmpeg.codec = "H264"
r.ffmpeg.constant_rate_factor = "HIGH"
r.ffmpeg.ffmpeg_preset = "GOOD"
r.ffmpeg.audio_codec = "AAC"
r.ffmpeg.audio_bitrate = 192
r.ffmpeg.audio_channels = "STEREO"
r.filepath = OUT
sc.render.use_sequencer = True

if "--save" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[argv.index("--save") + 1]))
if "--stills" in argv:
    fr = [int(x) for x in argv[argv.index("--stills") + 1].split(",")]
    od = argv[argv.index("--stills") + 2]
    os.makedirs(od, exist_ok=True)
    r.image_settings.file_format = "PNG"
    for f in fr:
        sc.frame_set(f)
        r.filepath = os.path.join(od, f"edit_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
    print("wrote", OUT)
