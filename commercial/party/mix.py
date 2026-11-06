"""The party's soundtrack: the game's summer battle track, its crowd and character sounds, Chatterbox shouts,
and synthesized splashes, placed on the frames where the action happens (30 fps)."""
import subprocess, os
FPS = 30; DUR = 30.0
A = "audio/"; V = "vo/"
# synthesized splash: filtered noise with a fast attack and a short tail
if not os.path.exists("splash.wav"):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=1.4:c=pink:a=0.9",
                    "-af", "highpass=f=300,lowpass=f=6000,afade=t=in:d=0.02,afade=t=out:st=0.15:d=1.2,volume=2.0", "splash.wav"], check=True)
events = [  # (file, frame, gain dB): crowd and effects only, no voices
    (A + "amb_beach.mp3", 0, -22), (A + "crowd_cheer.mp3", 8, -14),
    ("splash.wav", 222, -2), (A + "crowd_ooh.mp3", 226, -10), (A + "crowd_laugh.mp3", 250, -14),
    (A + "coins.mp3", 360, -9), (A + "coin_jingle_1.mp3", 395, -10),
    ("splash.wav", 410, -1), (A + "crowd_cheer.mp3", 412, -8), (A + "coins.mp3", 445, -11),
    (A + "fart_cast.mp3", 500, -4), (A + "fart_cloud.mp3", 508, -8), (A + "laugh_blast.mp3", 530, -8),
    (A + "crowd_laugh.mp3", 610, -12), (A + "crowd_ooh.mp3", 700, -11), (A + "laugh_blast.mp3", 760, -12),
    (A + "crowd_cheer.mp3", 860, -8),
]
# the club track: Kevin MacLeod, "Cut and Run" (incompetech.com, CC BY 4.0): the bassiest of the candidates (74% of its energy
# under 150 Hz), its strongest 30 s from a beat at 101.05 s; a low shelf pushes the kick and sub a little further
inputs = ["-ss", "101.053", "-i", "music/Cut and Run.mp3"]; filters = [f"[0:a]atrim=0:{DUR},asetpts=PTS-STARTPTS,bass=g=4:f=90:w=0.6,volume=-9dB,afade=t=in:d=0.2,afade=t=out:st={DUR - 2.5}:d=2.5[m]"]
labels = ["[m]"]
for i, (f, fr, g) in enumerate(events, start=1):
    if not os.path.exists(f): print("missing", f); continue
    inputs += ["-i", f]; ms = int(fr / FPS * 1000)
    filters.append(f"[{i}:a]aresample=48000,volume={g}dB,adelay={ms}|{ms}[e{i}]"); labels.append(f"[e{i}]")
filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,atrim=0:{DUR},alimiter=limit=0.6:level=false,loudnorm=I=-14:TP=-3:LRA=11[out]")
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2", "party_mix.wav"], check=True)
print("ok")
