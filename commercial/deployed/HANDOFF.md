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

## Rework 3 (after playing the live game) - findings and plan

Played a real match on memeroyale.imaginestudio.fun with Playwright (guest account, throwaway password never committed;
`reference/play_match.js`; the lobby needs a tap on the splash `#boot` every page load; cards are DRAGGED onto your half;
a new account's arena is Mom's Basement; the user's screenshot `reference/user_screenshot_moon.png` is the Moon arena).

What real play looks like (what v2 got wrong):
- Camera: steep top-down view of the whole board, portrait phone screen. Field is SPARSE: 1-4 units per side at a time
  (v2 replay: enemy average 2.6, p90 7, max 11 because the enemy deck had swarm cards useless/fud/firesale).
- HUD: top-left dark pill (name in team colour, trophy + number), top-right "TIME LEFT m:ss" pill, W score badges
  (red top, green below, at the right river bank), emote button bottom-left, tower HP as red/green pills with numbers,
  names pop up over units when a card is played, banners FIGHT!, TAKE THE L, DEFEAT screen.
- Tray: dark panel with a GREEN border; NEXT label + small card with a hex purple cost badge on the left; four cards with
  hex cost badges top-left and the card NAME under the art; selected card has a coloured (cyan) frame; below, a purple
  Copium potion icon with the number and a 10-segment purple bar. (v2's tray drew round badges and no names.)

Fixes so far: enemy deck without swarm cards (`sim/search3.mjs` deck1 = troll dope bonk neet zcat apu farter popcat) keeps
the enemy at <=4 units. `node search3.mjs 3000 0.3 0.4` finds winning masher matches (e.g. seed 2811: illegal tap 16.5,
enemy rig 59.7, ours 155, enemy 161.3, win 2-1 at 180). Scene segments C-G in scene.py are hard-wired to the old match's
times (40.97, 43.6, 88.8, 95.83, 120, 164.5, 166.57) and need re-timing to the new recording.

To do: re-record + re-time the story, redraw the tray/HUD exactly like the real one, declutter the ship (no characters
overlapping/clipping: one bay each), re-render (about 3 h with 8 machines), finish.
