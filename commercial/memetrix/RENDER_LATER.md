# Render THE MEMETRIX later (polish 3, edit 37a9155c53)

Everything needed is committed on branch `claude/eager-brown-rlfja0`. The scene code, voices (incl. the fixed "leverage"),
titles and finish are final as of this commit; `edl.json` (hash **37a9155c53**) is the edit to render.
Film: 137.8 s of 3D (3187 frames, 121-3307) + 11 s opening + 14 s closing = about 158 s.

## What changed since v2 (all approved on before/after sheets in `commercial/output/review/`)
Slerf presents both candles on his fists (custom pose) with red/green glow on his face; Anon takes the red one from the side
and swallows it (close-up on the mouth hole); fitted shades on Slerf, Jeanphil and the plank agents; Farter reads his phone
("+6,942%" close-up); Bome offers the cookie on his glove and Anon takes it; detailed staircase and Mom's lit door; CRT faces
Mensa; Anon lies flat on the mat after the fall (tail swung flat); training fight blocks and push; side-on bullet-time orbit with
glowing staggered candles; diamonds in Anon's raised paws; muzzle flash; many camera fixes (none inside characters).

## Known small issues (optional to fix before rendering)
- End of the cookie shot: Anon lowers the paw with the cookie behind his body (could lift it toward the bag).
- Bullet candles still look a little like flat sticks up close.

## How to render (8 cloud workers, about 2.5-3 hours)
Start one fresh worker session per range (create_session on this repo, revision `claude/eager-brown-rlfja0`, each with its own
outcome branch `claude/memetrix-r1` ... `-r8`) with this prompt (fill in A B and N):

> You are a render worker for THE MEMETRIX. Only job: render film frames A-B of edit 37a9155c53 and push them, then stop.
> 1. git checkout -b claude/memetrix-rN (push only there). 2. cd commercial/memetrix; run `./render_worker.sh A B` with the
> Bash tool using run_in_background: true and timeout: 7200000 (never nohup/setsid/&). If it exits with code 3 (RELAUNCH),
> run exactly the same command again. 3. Its first lines must say "EDIT 37a9155c53"; if setup says the rebuilt edit differs, stop and
> report. 4. Frames go to commercial/memetrix/frames_jpg/37a9155c53/ and are pushed automatically. 5. When it prints WORKER-DONE,
> reply WORKER-DONE with the JPG count and send the same line to "@parent" with send_message.

Ranges:
- r1: `./render_worker.sh 121 518`
- r2: `./render_worker.sh 519 917`
- r3: `./render_worker.sh 918 1315`
- r4: `./render_worker.sh 1316 1714`
- r5: `./render_worker.sh 1715 2112`
- r6: `./render_worker.sh 2113 2510`
- r7: `./render_worker.sh 2511 2909`
- r8: `./render_worker.sh 2910 3307`

(One machine alone also works: `./render_worker.sh 121 3307` relaunched on every exit 3, about 25-30 hours.)

## Finish (one session, after all workers are done)
```
# from the repo root
for n in 1 2 3 4 5 6 7 8; do git fetch -q origin claude/memetrix-r$n && \
  git archive origin/claude/memetrix-r$n commercial/memetrix/frames_jpg/37a9155c53 | tar -x; done
ls commercial/memetrix/frames_jpg/37a9155c53 | wc -l      # must be 3187
cd commercial/memetrix && W=~/mx_work ./finish_all.sh     # run_in_background, timeout 7200000 -> ../output/meme-royale-memetrix.mp4
```
Then review at 3 frames a second (contact sheets) and run the pop detector in `probe/` before sending, keep the MP4
under 100 MB (re-encode at 3000k if needed), commit it.

## After that (needs the user's OK)
Delete branches claude/memetrix-w1..w10 and -r1..r8, archive the worker sessions (tags memetrix-render).
