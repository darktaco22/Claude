# THE MEMETRIX II: build plan and state

Script: `SCRIPT.md` (approved: "Go ahead"). Same pipeline as episode 1 (`../memetrix/`): voices -> sets -> scene.py (staging and
shots as cine data, solved) -> check frames + before/after sheets for the user -> workers render -> finish.py (titles, grade,
mix) -> review at 3 fps + pop detector -> send.

## Done
- **Voices:** `voices.py` -> `pack/vo` (34 lines, 87.9 s). New voices: whale bm_lewis 0.8, swordcat af_kore, This-Is-Fine
  am_puck, Toshi af_sky; `jean12` = one take layered 12x with 8-90 ms delays (the copied agent). Slerf's fast line at 2.3x.
- **New characters measured** (idle pose, front + side height grids; `/root/mx_probe/measure.py`): all ~1.68 m tall.
  Eye heights: whale 1.37 (eyes on the sides of the head), swordcat 1.30 (armoured kitten knight with a sword),
  thisisfine 1.28 (cartoon dog, bowler hat), toshi 1.21 (blue ninja cat with two katanas: the Keyholder).
- **Sets** (`sets2.py`, look test `look_sets_v1.jpg`): the burning café FINE at (600,0,0) (diner tiles, red booths, chrome
  stools, counter, chalk menu "EXIT ... ?", code rain outside the window, 12 animated flame clusters with flickering
  lights, warm haze and embers); the white room at (800,0,0) (white cyclorama, 8 x 6 monitor wall playing episode 1 frames,
  SELL / HOLD doors outlined in light); rooftop rain (instanced streaks, driver-animated). Flame emission lowered to 9
  after the last look test (pink-white at 14): re-check.

## State (2026-11-25)
- scene2.py builds (W/scene2_v2.blend): 56 shots, 145.8 s. Full preview reviewed (anim2_v1), first fix pass rendered (anim2_v2).
- Doors: red / green falling code (user request), done.
- Fixed in pass 1: basement wide (camera was above the ceiling), Mensa's second shot, café establishing shot (camera was outside
  the walls), Jeanphil "Me. Too." wide (a clone's fist filled the frame), Michi's rooftop line, the door wide, the save.
- Still to fix: Swordcat's "He holds." and Toshi's / This-Is-Fine's lines after the duel (the other café characters block
  them: restage the three after the duel); the duel catch (Swordcat too far from Anon in the catch shot: check headings);
  the Whale's close-ups look down onto his hat (use MS/MCU from eye level, not CU); the cracked bull (no crack yet);
  the rocket candle reads as a green bar beside Anon; then the 2D work in finish.py (crash opening, LIQUIDATION stamp,
  liquidation bar over Michi, closing).

## State (2026-11-25, later)
- Duel: blade catch measured on Swordcat's sword prop (`prop_blade`, parented to his right hand: attack1 at 60 % holds it level
  at 1.31 m pointing ahead); Anon steps in so his raised paws close on it. Side-on duel cameras from the open side of the café.
- Bull crack (ray-placed glowing fissure + falling chunk), rocket candle (size 2.6) with a tapered green exhaust streak.
- finish.py for episode 2: crash opening (code turns red column by column and falls; news ticker), typed messages,
  THE MEMETRIX II + red LIQUIDATION stamp with a crack, café and white-room grades, clone glitches, shockwave/save flashes,
  liquidation bar over the film with the world draining of colour (MARGIN RESTORED after the save), "To be continued...",
  new cast cards, taglines NOBODY HOLDS FOREVER. / WATCH ME., new sound (fire, white-room drone, battle music in the brawl,
  duel steel, clone zaps, shockwave, rocket launch, margin call riser, the save). Test sheets in review/.

## State (2026-11-25, evening)
- Café: real 3D city through a Boolean-cut window (towers with lit windows, wet street, neon PAWN / HODL 24H / NOODLES,
  street lamps); volumetric fire (12 fire volumes + wall/curtain fire, smoke layer under the ceiling, scorch marks); all café
  lights hidden from camera/glass/gloss rays. Café frames are ~3x slower than episode 1's: use more workers.
- CRT insert (n11_1): one Jeanphil, then four, then sixteen on the screen as the camera pulls back from inside Mensa;
  TV model's sticky notes removed from the glass. cine.py gained `look_at` (absolute look point for prop inserts).
- n11_0 holds a fixed heading while Mensa spins; f10 re-angled; key ring dimmer.

- Full preview anim2_full3 reviewed; fixed since: bull laser eyes die on the crack (crack stays on the bull), Mensa / Michi /
  Slerf basement angles, seamless rain (no pop, no blur smear), wet puddled roof, see-through rain near the lens, rocket
  exhaust fading from the nozzle, the save from the far side (Toshi's katana), Anon straightens after the save and the two turn
  to each other on "Bought the dip.", the door shot (Whale between big SELL / HOLD doors), slow-motion catch insert measured on
  the blade. Real-look frames (fog + blur, 40 %) checked: review/look_v35.jpg. Finish checked on them.
- RENDER_LATER.md + setup.sh / render_worker.sh / finish_all.sh: the render package (12 workers).

## State (2026-11-26)
- Fires are simulations now (firesims.py, Mantaflow, baked per machine by setup.sh): seven fuels with their own source shapes
  and combustion (table wood, vinyl booth, counter grease, paper, a wall/curtain sheet, a debris pile, the coffee machine).
  19 placed fires on the things that burn, each scaled, turned and started differently; each is two copies of its 8 s loop
  half a loop apart, crossfaded (seamless). VDBs come from a fixed (non-adaptive) grid: an adaptive grid's offset is not in the
  file. Bakes are deterministic (only metadata differs).
- The café burns: charred materials (own colour in patches, blistered char, glowing cracks), sagging booth backs, scorch and
  ash on the floor, soot on the ceiling, fallen ceiling tiles, charred debris under the floor fires, a knocked-over stool, a
  half-burnt curtain on a rail, charred/melted table things, a till, a pie dome, a stopped clock, an extinguisher.
  Fixed: the coffee machine floated behind the counter; a fire hung on the wall at 2.5 m.
- Basement dressed (couch, side table with lamp and cans, shelf of junk, mini fridge, posters, dartboard, rug, CRT cable,
  plate and mug); the bare bulbs got cords (they hung from nothing). Rooftop: crates on a pallet, satellite dish, electrical
  box and conduit, skylights, hatch.
- sets2.check_dressing: every dressed object must rest on a surface (ray), stay inside its room and not intersect anything
  (BVH); the build prints PLACE lines.
- Pop check (per film frame: camera and every head): fixed f13 (camera swung 1.8 m in a frame as Swordcat turned into his walk)
  and a18 (camera whipped as Anon turned).

## State (2026-11-26, afternoon)
- Café fires are Mantaflow simulations, one per fuel (table, booth, grease, paper, sheet/curtain, debris, coffee machine),
  19 placed instances, each scaled, turned and started at its own point in the loop (`firesims.py`, baked by `setup.sh`).
- Burnt café: char burns in stages (soot-dulled paint, scorched brown, black blistered char, glowing cracks where hot),
  world-space grain; soot/ash film over the whole floor, scorch under each fire, soot on the ceiling, debris, sagging booths.
- Dressing in the basement, café and rooftop goes through `put`/`rest_on` (everything rests on a real surface) and
  `check_dressing`: build log must say `PLACE checked 76 problems 0`.
- Scene build exits right after saving (Blender hung on quit until the 2-hour cap).
- Full animatic (v48) and real-look café/duel/catch frames checked: no pops, clipping or floating props found.
- Edit 59aee902f7 is ready; the full render waits for the user's go.

## Next
1. Render on the user's go (RENDER_LATER.md).
2. Detail passes: rooftop rain and wet reflections, white room, brawl choreography, the Whale.
3. RENDER_LATER-style package for episode 2 (workers, 67 % / 6 samples, fog + motion blur ON).

## Earlier plan (kept for reference)
1. scene.py for episode 2 (copy ../memetrix/scene.py; keep Actor, glue, posed/fist_top/place, held poses, custom poses,
   IK-with-pole, cam_at, swallow-style measured targets). New: Swordcat duel (blocks, slow-motion lean, blade catch:
   glue Anon's paws to the blade), 12 Jeanphil clones (instances of the jeanphil character, shades fitted once and glued),
   green shockwave (expanding emissive torus + displaced floor), rocket candle flight (Anon on a path, sparks), Michi's
   liquidation (2D bar in the finish + grey-out material swap), the Whale floating (bob like Bome).
2. Rooftop: wet floor (lower roughness, puddle decals) + rain_cloud, night grade.
3. finish.py: the crash opening (green candles turn red and fall), red LIQUIDATION stamp with a crack, news ticker, closing
   tagline "NOBODY HOLDS FOREVER." / "WATCH ME.", cast cards for the 4 new characters.
4. Check frames per shot, before/after sheets to the user, then render with workers (see ../memetrix/RENDER_LATER.md).


## Done (2026-11-27)
Rendered all 3406 frames of edit 59aee902f7 (12 workers) and finished them: `output/meme-royale-memetrix-2-liquidation.mp4`, 169.4 s, 4066 frames, 97.3 MB. Reviewed at 3 frames a second, no glitches. Fixed in finish.py: the liquidation bar crashed on a negative width 0.2 s before it starts.

## Ending and fight sounds (edit 6ab963c055, 2026-11-27)
- The ending no longer reads as a death. Michi flinches and steps in. A new close-up ("still_here") shows Anon's paw lifting
  toward her and his tail twitching. A new wide shot ("city_green") shows every window in the city turning green in a wave
  (SCRIPT §5). Shots before the collapse are unchanged, so only frames 3426-3646 were re-rendered; 121-3425 are hard links to edit 59aee902f7.
- Fight sounds come from the animation itself. scene2.py logs every attack, hit and fall (EVENTS['fight']). finish.py
  turns each one into a swish, punch or body fall, with blade rings on the sword clash and catch. The ending gets a
  heartbeat, a breath and a swell.
- Output: 174.4 s, 4186 frames, 4200k video. If the disk fills during finish.py, resume with its ONLY list, then run
  with SOUND_ONLY=1.
