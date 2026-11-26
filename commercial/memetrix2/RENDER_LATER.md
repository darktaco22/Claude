# Render THE MEMETRIX II: LIQUIDATION later

Everything needed is committed on branch `claude/eager-brown-rlfja0`: scene code (`scene2.py`, `sets2.py`, episode 1's
`../memetrix/mxsets.py`, `../tools/cine.py`), voices (`pack/vo`), CRT images and the white room's monitor stills
(`pack/props`, `pack/stills`), titles, sound and finish (`finish.py`). `edl.json` is the edit to render; frames are filed under
the first 10 characters of its sha1 (`sha1sum edl.json | cut -c1-10`). **Re-check the hash before starting workers**: every
scene fix rewrites `edl.json`, and `render_worker.sh` prints the hash it is rendering (`EDIT <hash>`). As of this writing:
**59aee902f7**, 57 shots, 3406 frames of 3D (film frames 121-3526) + the opening and closing = about 2 min 40 s.

## Look (keep it): fog, lights, motion blur
`render_worker.sh` renders with everything on by default: volumetric haze (café smoke, rooftop rain fog, basement dust),
volumetric fire in the café, per-set lights, camera fill and rim light, motion blur, 67 % size at 6 samples (upscaled to 1080p
in the finish, which adds the grade, bloom, streaks, halation, grain and letterbox). **Do not set NOHAZE=1 or MB=0** for the real
render: those switches were only for quick check frames (`review/`), which is why those look cleaner and darker.
The rain has object motion blur switched off on purpose (it loops; the streaks are drawn long already).

## The café's fires are simulations
`setup.sh` bakes them on each worker before building the scene (`firesims.py`: seven fuels, about 15 minutes and 1.7 GB of
disk the first time; bakes are deterministic, so every worker gets the same fire). A worker needs about 4 GB free. If
`fire_sims` is missing, the scene falls back to the older procedural flames, so check the build log says
`CAFE fires 19 simulated 19` and `PLACE checked 76 problems 0`.
Fire volumes carry no motion blur on purpose (with it, Cycles padded them by the simulation's velocity and ran out of
memory). A café frame takes about 100 s at 67 % / 6 samples and peaks under 1 GB.

## How to render (12 cloud workers)
Café frames take about 100 s each at 67 % / 6 samples (the fire volumes), the other sets 25-40 s, so each worker needs
2-4 passes of the 2-hour cap: on exit 3 it is simply run again. Start one fresh worker session per range (create_session on this
repo, revision `claude/eager-brown-rlfja0`, each with its own outcome branch `claude/memetrix2-r1` ... `-r12`) with this
prompt (fill in A B N and the hash):

> You are a render worker for THE MEMETRIX II. Only job: render film frames A-B of edit HASH and push them, then stop.
> 1. git checkout -b claude/memetrix2-rN (push only there). 2. cd commercial/memetrix2; run `./render_worker.sh A B` with the
> Bash tool using run_in_background: true and timeout: 7200000 (never nohup/setsid/&). If it exits with code 3 (RELAUNCH),
> run exactly the same command again. 3. Its first lines must say "EDIT HASH"; if setup says the rebuilt edit differs, stop and
> report. 4. Frames go to commercial/memetrix2/frames_jpg/HASH/ and are pushed automatically. 5. When it prints WORKER-DONE,
> reply WORKER-DONE with the JPG count and send the same line to "@parent" with send_message.

Ranges (for 121-3526; recompute if `edl.json`'s `last` changed: `python3 -c "import json;print(json.load(open('edl.json'))['last'])"`):
- r1: `./render_worker.sh 121 404`
- r2: `./render_worker.sh 405 688`
- r3: `./render_worker.sh 689 972`
- r4: `./render_worker.sh 973 1255`
- r5: `./render_worker.sh 1256 1539`
- r6: `./render_worker.sh 1540 1823`
- r7: `./render_worker.sh 1824 2107`
- r8: `./render_worker.sh 2108 2391`
- r9: `./render_worker.sh 2392 2674`
- r10: `./render_worker.sh 2675 2958`
- r11: `./render_worker.sh 2959 3242`
- r12: `./render_worker.sh 3243 3526`

## Finish (one session, after all workers are done)
```
# from the repo root
for n in $(seq 1 12); do git fetch -q origin claude/memetrix2-r$n && \
  git archive origin/claude/memetrix2-r$n commercial/memetrix2/frames_jpg/HASH | tar -x; done
ls commercial/memetrix2/frames_jpg/HASH | wc -l      # must be 3406 (last - 120)
cd commercial/memetrix2 && W=~/mx_work ./finish_all.sh  # run_in_background, timeout 7200000 -> ../output/meme-royale-memetrix-2-liquidation.mp4
```
Then review at 3 frames a second (contact sheets) before sending, keep the MP4 under 100 MB (re-encode at 3000k if needed),
commit it.

## Quick checks without rendering everything
- `animatic.py`: three small frames per shot (`ANIM_OUT=dir ONLY=shot,shot SCALE=25 SAMPLES=4 MB=0 NOHAZE=1`).
- `render_edl.py -- list.txt` with `OUT=dir SCALE=40 SAMPLES=6`: real-look frames (fog and blur on).
- `finish.py FRAMES OUT o1,o2`: finished output frames (output frame = film frame + 144).

## After that (needs the user's OK)
Delete branches claude/memetrix2-r1..r12, archive the worker sessions.
