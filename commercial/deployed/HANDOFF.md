# DEPLOYED (Meme Royale, about 2:32)

A paratrooper comedy. The player's cards wait in a rattling drop ship above Arena 2 (Backyard BBQ) while "the Thumb", a
hopeless player, plays them one at a time. Sarge (Walter) briefs them; LMAO jumps and is bonked at once; the Airdrop
hits a rubber duck; the left tower falls while the Thumb sends WAGMI; Copium leaks at 10 and Chillhouse gets stuck in
the door, then bounces off the trampoline back past the ramp; the last card is Cupsey, an egg, who lands in front of
the whole enemy push, and wins because opponent `paperhands420` leaves the match. +28 Clout, new arena: a parking lot.

All game terms are real (checked in `meme-royale-research/client_src/data.js`): Copium bar, Clout, card costs, arena
names, the WAGMI emote, the bot name. Card art on the monitor and HUD is the game's own (`pack/cards`).

## Files
| File | Job |
|---|---|
| `voices.py` | 39 lines, 7 Kokoro stock voices (sarge am_onyx, egg am_puck, ket af_bella, chill am_liam, house am_santa, pilot am_eric, game bf_emma) -> `pack/vo` |
| `textures.py` | Monitor states, labels, WAGMI bubble, disconnect icon -> `pack/tex`; also draws the thumb used by the finish |
| `sets.py` | Drop ship (hold + exterior) and the Backyard BBQ arena, all from code |
| `scene.py` | Cast, animation, 76 shots, events -> `scene.blend` + `edl.json`. Builds in about 30 s |
| `render_edl.py` | Renders film frames from the EDL (per-shot hide list, camera fill light, motion blur flag) |
| `animatic.py` | One small frame per shot + labelled contact sheet. Use it after every staging change |
| `finish.py` | Grade, captions, the Thumb's HUD on top-down shots, banners, end card, sound mix |
| `setup.sh` | Makes a clean machine ready: Blender, character library, sky + grass from Poly Haven, scene build |
| `render_worker.sh A B` | Renders a frame range and pushes JPEGs to `frames_jpg/` |
| `finish_all.sh` | Checks every frame exists, finishes, mixes, encodes `commercial/output/meme-royale-deployed.mp4` |

## Render plan
- 3499 picture frames + a 6 s end card made in the finish. Settings: 67 % of 1080p, 6 samples (about 20 s a frame on 4 cores;
  haze and motion blur are on only for the shots listed in `HAZE_SHOTS` / `BLUR_SHOTS` in `scene.py`, they cost 12-15 s each).
- Split across this machine and worker sessions with `render_worker.sh`; ranges are in the progress log below.
- Then `git pull` and `./finish_all.sh`. Review with contact sheets and a dark-frame scan. The mix is unheard: say so.

## Rebuild from nothing
`W=~/dep_work ./setup.sh` (needs download.blender.org, api.polyhaven.com, dl.polyhaven.org). Voices and textures are
already in `pack/`; to re-record: `python3 voices.py KOKORO_DIR pack/vo`, to redraw: `python3 textures.py pack/cards pack/tex`.

## Progress log
- Full render started. Ranges: this machine 1-437; workers 438-875, 876-1312, 1313-1749, 1750-2187, 2188-2624, 2625-3062, 3063-3499.
  Each worker runs `./render_worker.sh A B` and pushes to `commercial/deployed/frames_jpg`. When all 3499 are in: `./finish_all.sh`.
