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

## REWORK after the first review (user feedback, Nov 15) - read this first
The first cut was wrong about the game: cards are NOT lost after playing. A deck is 8 cards; 4 are in the hand and the rest
wait in a queue; a played card goes to the back of the queue and the next one steps in. There is no "last card". The
arena also looked nothing like the game's Backyard BBQ. Fixes:
1. **Real rules.** `sim/record.mjs` plays a real match with the game's own `sim.js` + `ai.js` (Node, no browser) and records
   every unit 10 times a second plus events -> `pack/match.json` (seed 137: Thumb wins 2-1 on time; our right tower falls
   at 0:41, enemy right tower 1:36, COPIUM OVERDOSE at 2:00, enemy left tower 2:47). The Thumb is a button masher who taps
   cards at random: with about 25 plays he beats the weak bot about 1 time in 4 (`sim/search3.mjs` found it); a passive
   Thumb always loses. One tap is on the enemy half and is refused ("enemy side"), the real rule.
2. **Real arena.** `pack/game/` holds the game's own tower_rig, battlestation, bridge, edge pieces and every Backyard prop
   (GLB) with its `layout.json`, plus ground/backdrop textures, downloaded from memeroyale.imaginestudio.fun/assets.
   Game coordinates: court 18 x 32 (x, z), bridges at x 3.5 and 14.5 on z 16, rigs at (3.5|14.5, 25.5|6.5), king base at
   (9, 29.5|2.5). Team 0 (ours) is z high. Characters are about 1.7 tall, towers 4.9: the same scale as the game.
3. **Story.** The ship carries the deck: 4 characters at the ramp (the hand) and 4 on the bench (the queue). Each real
   play makes the next character jump to the tapped spot; the queue shifts; the jumper pops back in at the end of the line.

## Status after the rework (Nov 15)
Built: real arena (`sets.build_game_arena`), replay of `pack/match.json` (`scene.py`), 102 shots / 145.5 s (139.5 s + 6 s end card),
new voices (`voices.py`, 52 clips with the game's own announcer), HUD from real data (`monitor.py`), finish with HUD + tower
health bars (`finish.py`). `DRY=1` rebuilds only `edl.json` in 30 s (use it while editing shots); the full build takes about 3 min.
Render: 67 % size, 6 samples, about 19 s a frame (3349 frames). Ranges: local 1-419; workers 420-838, 839-1257, 1258-1676,
1677-2095, 2096-2514, 2515-2933, 2934-3349. Then `./finish_all.sh` (writes `commercial/output/meme-royale-deployed.mp4`).
Lessons (also in the playbook): subdivision costs ~130 MB per mesh, so only the ship's cast has it; library passes duplicate
textures (dedupe by content, never by name: different characters share names like `base_0`).

## Rework 3 (after playing the live game): what the film is now

Played a real match on memeroyale.imaginestudio.fun with Playwright (guest account; the lobby needs a tap on the splash `#boot`
after each page load; cards are DRAGGED onto your half; a new account's arena is Mom's Basement; `reference/` holds the user's
Moon-arena screenshot, real-match frames and the Playwright script). Real play: steep top-down portrait camera, SPARSE field
(1-4 units a side), name pill + TIME LEFT pill, W badges on the river bank, tower HP pills, green-bordered tray with NEXT,
four cards with hex cost badges and names, Copium bottle + 10-segment bar.

What changed:
- Match: `sim/plan14444.json` (`node search3.mjs 15000 0.3 0.4` finds winning button-masher matches against a SINGLE-UNIT enemy deck:
  troll dope bonk neet zcat apu farter popcat; a rejected drag costs the Thumb 1.7 s). Illegal drag 17.97, our left tower 43.1,
  enemy right tower 83.4, enemy left tower 91.2, overdose 120, win 2-1 at 180. Enemy averages 2.7 units (max 7).
- `hud.py`: the real HUD drawn from the screenshot (tray, pills, W badges, HP pills, emote button). Used by the monitor, the phone
  shots and the cinematic arena shots.
- Phone shots (`phone=True`, `res=[806,1746]` in edl.json): the game's own static top-down camera (`PHONE_CAM` in scene.py, ship and
  the crew still inside it hidden by render_edl.py), composed by finish.py into a phone on a blurred backdrop with the HUD, the drag
  (card follows the finger from its slot, ring at the target), the drop ring, the card name popping up, "Can't drop here",
  FIGHT!, tower/overdose/victory banners. Each play: phone drag (0.85 s) -> ramp shot -> fall (FALL = 1.0 s) -> short chase.
- Ship close-ups are SOLO (`keep=[card]` / `keep=['sarge']`, actors tagged `rig['hold']`): nobody blocks or clips into the speaker.
- Dialogue: "drag" not "tap", no "last card"; lines placed at match times; `VOICE PUSH` prints show lines shifted off overlaps.
- Film: 3224 frames (134 s + 6 s end card).

Render: ranges of about 403 frames for 8 machines (see the table in the worker prompts / git log). Phone frames render in about 9 s,
ship and arena frames 15-25 s.
