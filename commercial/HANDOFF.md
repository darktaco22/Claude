# Meme Royale videos: handoff for a new session

Read this first. It replaces the long conversation these videos were made in.

## What exists (all in `commercial/`, finished files in `commercial/output/`)
| Video | Folder | Output |
|---|---|---|
| NOOB vs PRO tip (vertical) | `noobpro/` | `meme-royale-noob-vs-pro.mp4`, `meme-royale-tip2-splash.mp4` |
| "Wait, they're coins" skit (vertical) | `coins/` | `meme-royale-wait-theyre-coins.mp4` |
| "I WILL FIND YOU" (vertical) | `findyou/` | `meme-royale-i-will-find-you.mp4` |
| Stadium commercial "It's not over until it's over" (16:9, 62 s) | `comeback/` | `meme-royale-epic-comeback.mp4` |
| "Clash at the Bridge" battle cinematic (16:9, 59.5 s) | `clash/` | `meme-royale-clash-at-the-bridge.mp4` |

The user liked the stadium/battle style most (especially both sides rushing the centre, many angles, slow motion).
They want game-accurate action: the king tower's cannon cannot shoot towers; towers fall to troops or spells.
Don't repeat an ending from an earlier video (the whale smashing a tower was used in `comeback`).

## Assets
- Game site: memeroyale.imaginestudio.fun. All 39 unit models: `comeback/models/*.glb` (clips: idle, ready, walk, run,
  attack1-3, hit, die, win, lose, emote; `neet` also has sit* clips). Unit list and clip data: `noobpro/models/units.json`.
- Arena exported from the live game: `comeback/models/arena_basement.glb`. Its two king towers face outward: rotate them
  180 degrees (done in `comeback/scene.py`).
- Game audio (music, announcer `vo_*`, crowd, effects): `comeback/audio/`. Fonts, logo, title art: `assets/`.
- Skies and textures: `comeback/tex/` (`sky.hdr` day, `dusk.hdr` sunset). More from Poly Haven with `degens/phget.py`.
- Units face -Y at rotation 0. Court: X 0..18, Y 0 (red end) .. -32 (blue end); bridges at x 3.5 and 14.5, river at y -16.

## Pipeline (stadium films)
- `comeback/scene.py` builds everything (stadium, 2,300-fan instanced crowd, FX helpers `explode`, `fling`, `run_to`,
  `clip`, `sched`). `clash/gen.py` assembles `clash/scene.py` from that head plus `clash/tail.py` (battle) and
  `clash/cams.py` (lights and the edit). Edit `tail.py` / `cams.py`, run `python3 gen.py`.
- The edit is a shot list (`SH(duration, anim_start, speed, cam...)` in `cams.py` -> `edl.json`): each shot shows a stretch
  of the animation at its own speed (slow motion, overlapping angles). `render_edl.py` renders film frames from it.
- `render_part.sh FIRST LAST` renders a frame range to `parts/part_A_B.mp4` + `.frames.txt` (resumable; exits 3 = run again).
- `finish.py FRAMES_DIR OUT_DIR` does grade, bloom, title and end cards and the whole soundtrack; then 2-pass x264
  (~11 Mbps keeps a minute under GitHub's 100 MB limit).
- Blender 4.2.3 at `/opt/blender/...` (`noobpro/setup.sh` installs it). Cycles CPU, 1280x720, 8-10 samples + denoise,
  upscaled to 1080p in `finish.py`. A scene build takes ~10 min; a frame ~35-45 s on a 4-core machine.

## Lessons (each cost a re-render)
- Test before a full render: one low-res frame per shot (`te.py` pattern: samples 6, 50 %), look at a contact sheet.
- Cameras end up inside things: fighters next to the lens, tower glow shells, smoke, bridges, the fence (x<0, x>18), stands.
- Keep euler angles continuous (camera and units): a +180/-180 wrap between keys becomes a full spin, and motion blur
  smears it. `run_near` in `clash/tail.py` and the `PREV_ROT` handling in `comeback/scene.py` do this.
- `run_to` keys rotation only at its start, so a unit slowly turns between two runs: key the facing just before.
- Never use Python's `hash()` for variation (differs per machine). Anything that consumes the shared `rnd` before `crowd()`
  changes the crowd: keep the call count stable if old frames are being reused.
- Big transparent smoke spheres: keep them small and short-lived, `visible_shadow = False`.
- Memory: this scene peaks near 11 GB of a 15 GB machine. Subdivide only the hero units.
- Scratch disk is limited: delete old frame folders before a new build ("Error: Success" on save = disk full).
- The reference-video host (googlevideo) is blocked; YouTube storyboards via `yt-dlp -f sb0` work (i.ytimg.com).

## USAGE RULES (the account hit its 5-hour limit repeatedly)
1. One video per conversation. A long conversation re-reads its whole history on every wake-up; that was the main cost.
2. Render workers (`create_session`, model claude-sonnet-5-5): no check-ins, no "done" messages to the orchestrator.
   They launch `render_part.sh` as a tracked background task, push their part to their own branch, and stop.
3. Do not schedule wake-ups in the orchestrator. Let a fresh small session wait for the branches with a shell loop
   (`until [ "$(git ls-remote --heads origin 'claude/NAME-*' | wc -l)" -ge N ]; do sleep 60; done`, zero tokens), then
   assemble from the repo and push the video. See the "Clash final assembly" prompt pattern: one script, one background run.
4. Launch workers in small batches (6-8), not 16-18 at once, and only after test frames pass.
5. Small fixes (under ~100 frames): render them in the orchestrator's own machine as one background task instead of workers.
6. Archive worker sessions sparingly: each archive call returns a large record into the conversation.
