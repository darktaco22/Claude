# Long renders in cloud sessions: why they kept stopping, and how to run them

## Root cause

A Claude Code cloud session runs in a Firecracker microVM. **The VM is shut down roughly 10 minutes after a turn
ends unless the session is still busy**, and it boots fresh on the next message or scheduled check. The disk
survives (the scratchpad, `$HOME`, `/opt/blender`), but every process is gone.

The session only counts as busy while a turn is running, or while a background task that the tool runner tracks is
still running. Renders started with `setsid nohup … &` are detached on purpose, so the tool runner can't see them:
from its side the session is idle, the VM is stopped, and Blender dies with it.

Evidence from 2026-11-08:

| Job | How it was launched | Result |
|---|---|---|
| Local render 364–725 | `setsid nohup run_mid.sh &` | Died about 10 min after the turn ended at 14:31 (around 14:41), and again after the turn ended at 15:03 (around 15:12) |
| Six worker renders | `setsid nohup render_part.sh &` | About 10 frames per "15-minute cycle", then the container was recycled |
| RIFE 60 fps (61 min) | Bash `run_in_background` (tracked) | Ran 15:24–16:25 across three idle gaps between turns without a single stop |
| Nothing running | – | The turn ended 16:31; the VM booted again at 16:47:11 (`uptime`, PID 1 start time) |

Rescheduled checks only patched over this: each restart got about 10 minutes of work before the next shutdown.

## Rules

1. **Launch every long job as a tracked background task**: Bash with `run_in_background: true` and
   `timeout: 7200000`, the 2-hour maximum. Never use `setsid`, `nohup`, `&` or `disown` for work that must keep going.
2. **Jobs longer than 2 hours run in chunks.** `render_list.py` reads `RENDER_BUDGET` (seconds) and stops
   cleanly before it runs out, exiting with code 3 if frames are left. `render_part.sh` defaults to 6600 s. When the
   completion notification arrives with exit 3 or `RELAUNCH`, run the same command again. Finished frames are in
   `<list>.done` and are never rendered twice.
3. **No polling.** The completion notification wakes the session. A single long fallback check (60 minutes or
   more) is enough insurance.
4. **Setup and scene builds count too.** `setup_remote.sh` takes 5–20 minutes and `director.py` about 1.5 minutes,
   so run them tracked as well, or chain them in the same tracked command (`render_part.sh` builds the scene
   itself).
5. **Workers follow the same rules.** A worker prompt must say: run `render_part.sh` with `run_in_background`
   (timeout 7200000), and on exit 3 run it again.

## Example

```text
Bash(run_in_background=true, timeout=7200000):
  cd commercial/degens && W=$HOME/da_work ./render_part.sh 364 725 $HOME/part_0364_0725.mp4
# → notification: exit 3 "RELAUNCH: … frames left"  → run the same command again
# → notification: exit 0 and the mp4 is listed     → done
```

At about 22 s per frame on 4 cores, one 110-minute chunk covers about 300 frames, so the whole 1,452-frame film is
about 5 chunks in a single session. That's faster than the six workers, which were each killed every 10 minutes.
