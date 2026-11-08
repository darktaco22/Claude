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
