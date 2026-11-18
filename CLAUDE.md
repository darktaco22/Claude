# Notes for Claude sessions in this repo

## Long-running jobs (renders, RIFE, setup): never launch them detached

Cloud sessions run in a VM that **shuts down about 10 minutes after a turn ends unless a tracked background task is
running**. Anything started with `setsid`, `nohup`, `&` or `disown` is invisible to the tool runner and dies when the VM
stops. That is why renders kept "stopping"; nothing crashed. Full evidence: `commercial/degens/RENDERING.md`.

- Launch every job that outlives a turn with Bash `run_in_background: true` and `timeout: 7200000` (the 2-hour maximum).
- Jobs longer than 2 hours run in chunks. `render_part.sh` / `render_list.py` stop cleanly before the cap
  (`RENDER_BUDGET`, default 6600 s) and exit **3** with `RELAUNCH`. When the completion notification arrives with exit
  3, run the same command again; finished frames are never rendered twice.
- Don't poll with 15-minute checks. The completion notification wakes the session. One fallback check of an hour or
  more is enough.
- Give each job its own work folder or a freshly built `scene.blend`. Progress marks (`part_A_B.txt.done`) older than
  the scene are dropped automatically.
- Workers (other sessions) follow the same rules. Put "launch with run_in_background, timeout 7200000; on exit 3 run it
  again" in every worker prompt.

## Blender work: read the playbook first

Before any Blender scene or render task, read `commercial/tools/PLAYBOOK.md` and `commercial/tools/README.md`. They hold
the lessons and reusable tools from earlier renders (lighting, lenses, camera shake, scanned assets, fire). When a
render teaches something new, add it there in the same commit.

## Cameras: cinematic shots, Blender only

The user wants Blender kept (no Unreal Engine) and better cinematography in every future render. Plan shots with
`commercial/tools/cine.py` (shot sizes, angles, moves, thirds, over-the-shoulder, rack focus) and run `cine.solve()` on
each shot. Follow "Camera language" in the playbook: varied sizes and angles, no jump cuts, 180-degree rule, motivated
moves (push on big moments, arc for depth, low angle for heroes).

## Work in progress

"The Final" (2-minute film): state, render plan and next steps are in `commercial/final/HANDOFF.md`. Read it before
continuing that film.

"Deployed" (2.5-minute drop ship comedy): state and render plan are in `commercial/deployed/HANDOFF.md`.
