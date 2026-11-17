# Blender playbook (read this before starting any render job)

Claude does not remember earlier sessions. This file and the code beside it are the memory: add to it whenever a
render teaches something, so the next session starts from here.

## Look
- **Light from behind.** Key the subject from a low sun behind or to the side (rim light), then lift faces with a
  soft fill. Front-lit toy characters look flat. Key fill lights on only for the shots that need them; their pools
  show in wide shots.
- **Sky.** Nishita sky + sun lamp gives clean dawn/dusk; its sun direction is `(sin r, cos r)` so
  `sun_rotation = 180° − lamp heading`. For realism use a Poly Haven HDRI (`polyhaven.py`), "puresky" variants have a
  clear horizon.
- **Lenses.** 50–135 mm with f/1.8–2.8 for characters; wide lenses only for establishing shots. Oval bokeh:
  `cam.data.dof.aperture_ratio = 1.6`.
- **Depth.** Mist pass mixed with a warm colour at 0.3–0.4, never more (it turns beige). Floating dust motes near
  camera sell scale.
- **Emissives.** Keep glowing objects under strength ~1 and let the finish bloom them. Above that they clip to
  white and lose colour (seen in the eruption and timber shots of Natural History).
- **Ground.** Hand-made blade grass reads as plastic. Use scanned grass/flowers through `scatter.py`, mixed sizes,
  and exclude areas under props.
- **Fire/smoke.** Sphere puffs look like balls. Best: downloaded CC0 volumes through `vdb.py` (real flame shapes,
  ~25 s a frame at 960×540). `fire.py` (own Mantaflow simulation) runs but still looks like a glowing ball; it needs
  an irregular emitter, more velocity and noise before film use. Keep fire emission near 1; it clips to white fast.
- **Camera.** Add recorded shake (`shakify.py`): INVESTIGATION at 0.3–0.6 for calm shots, THE_CLOSEUP for tension,
  HANDYCAM_RUN for chaos. Synthetic sine shake looks mechanical.
- **Finish (2D).** Bloom, light halation, vignette, grain, letterbox. Text needs a shadow and must avoid bright sky.

## Learned from Blender Studio's production guides
- Light the **key shot** of a sequence first (usually the wide), then derive close-ups from it.
- Only four light types: key, key-soft, fill, rim. Keep one colour per type per sequence (`lightrig.MOODS`) so shots
  match. Keep light direction consistent across a scene; sketch it top-down for outdoor scenes.
- Eyes sell appeal: give every close-up a catch-light (`lightrig.eye_light`).
- Effects come after animation is final, and need at least rough lighting to judge. Prefer a procedural or card
  fake over a physics simulation when it gives more control.
- Effects that glow must also light the scene (sparks, fire): add a light with them.
- Parent switches cause motion-blur streaks; switch on constant keys and check subframes.

## Learned from the lab test (`demo_lab.jpg`)
- The toy characters sit well in a scanned field under an HDRI sky at 85 mm f/2. The HDRI alone already looks
  natural; the rig should only *shape* (default powers are deliberately low). An over-strong key flattens the face.
- A rim light does not read against a bright sky. Use it against dark backgrounds, or darken the background.
- Explosion card behind a character is convincing even out of focus. Pair it with a point light around 15 000 W at
  14 m; 60 000 W washed the field yellow.
- Poly Haven grass is real-world scale, which suits the characters (about 1.7 m tall) without rescaling.

## Learned from "Scripting for Artists" (Sybren Stüvel, Blender Studio)
Studied: the 11 free chapters (1, 6–15) from their subtitles. Not studied: chapters 2–5, 16 and the four tech
chapters (F-curves, 10,000 OBJ files, bone renaming, all angles), which are subscriber-only; `pipeline.py` covers
those topics with my own code.
- Use the `context` passed in, not `bpy.context`: an operator's context can differ (pinned tabs, overrides).
- `bpy.data.x.new(name)` may return a different name (`.001`). Keep the returned data-block; never re-look-up by name.
- Don't modify what you loop over: `for c in list(obj.users_collection)`.
- `try: scene.collection.children[name]` / `except KeyError:` create. Never a bare `except`.
- Link assets with `bpy.data.libraries.load(path, link=True)`; inside the `with`, `data_to.collections` is names,
  after it, real collections. Instance each with an empty (`instance_type='COLLECTION'`).
- Describe a set in a JSON file next to the blend (`//set.json`, resolve with `bpy.path.abspath`), keep code generic.
- Remember where imported data came from in a custom property, so it can be reloaded; copy `matrix_world` before
  deleting an object; remove a data-block only when `users == 0`.
- Prefer data calls over operators (set `obj.scale` instead of `bpy.ops.transform.resize`).
- Readability: guard clauses and early return, one job per function, real names (no `utils`/`misc`), `if items:`
  not `if len(items) != 0`, PEP 8, one statement per line. **My film scripts break this last rule** (semicolon
  chains in `scene.py`); new code follows it, as `pipeline.py` does.
- Operators: `bl_idname` `category.name`, class `CATEGORY_OT_name`, `bl_options {'REGISTER','UNDO'}` for the redo
  panel, `poll()` to limit context; modal operators return `RUNNING_MODAL` / `PASS_THROUGH`, timers via
  `wm.event_timer_add`. Useful if we ever build tools for a human at the keyboard; headless renders don't need them.
- Batch work: skip finished outputs so a run can resume; remove imported objects and purge orphans each item.

## Applying the course (measured)
- A library is not automatically faster: six separate appends from a 54 MB library took 2.7 s against 0.9 s for
  glTF import, because each call reopens the file. One `libraries.load` for all six took 0.5 s. Measure first.
- Run `preflight.check` before every render longer than a few minutes; it costs under a second.
- `casting_sheet.jpg` shows every character under the same light. Look at it when casting a film: `bome`, `mensa`,
  `pnut` and `useless` have unusual proportions that need their own camera framing.
- Start a new film from `assets.load_many` + `lightrig` + `preflight` instead of copying an old `scene.py`.

## Learned from "The Final" (in progress, see `commercial/final/HANDOFF.md`)
- Video on a card: Blender clamps the movie frame to the clip before applying `frame_offset`. To show clip frame k at
  scene frame f set `frame_start = f - k + 1`, `frame_offset = 0`, `use_auto_refresh = True`.
- Stock explosion cards need emission strength ~1.7 under AgX; 4+ washes to white. Sphere smoke over them hides them.
- Characters standing behind a tower's cannon are hidden from every low angle: stand them on top of it.
- Never put a camera in the lane of running characters, or inside a smoke plume; check with a run-through.
- Building on the clash stadium takes ~12 min per rebuild (2286 crowd instances); batch shot fixes per rebuild.
- `pgrep -f` uses extended regex: `a|b`, not `a\|b`.
- Draw broadcast graphics at 1080p in the finish, not in 3D; test them on run-through frames before the full render.

## Learned from "Deployed" (see `commercial/deployed/HANDOFF.md`)
- Build new sets from code (`deployed/sets.py`): the whole film rebuilds in 30 s, against 12 min for the stadium, so
  staging can be fixed many times. A per-shot contact sheet (`animatic.py`) finds most camera mistakes in one pass.
- Geometry-nodes scatter works in the surface object's local space: an object scale stretches every instance and thins
  the density. Give the surface a real-size mesh. Poly Haven grass clumps are 3-15 cm; scale 4-6.5 for toy characters.
- Appending the same collection twice in one `libraries.load` crashes Blender 4.2: `assets.load_many` now loads repeats
  in further passes.
- Close-ups: 35-50 mm at about 1.7 m. 70-90 mm at that distance shows one eye. Check that no other character stands
  between camera and subject, and that the camera is not inside a tower, a hull or another mesh (grey or black frame).
- A sky seen straight toward the sun is a blank white. Put the sun 30-40 degrees off the view axis and give camera rays
  a darker sky than lighting rays (`sets.world(camera_gain=0.45)`).
- A camera that follows an accelerating fall must be cut into short linear pieces, or the subject leaves the frame.
- Render cost here is light calculation, not scene setup: bounces made no difference; haze volume +15 s and motion blur
  +12 s a frame. Switch them on per shot. 67 % size with 6 samples and OIDN is clean for these characters.
- Objects created by different helpers can collide by name (`boom` tail boom vs `boom` explosion card): prefix effects.

- **Use the game's own assets and rules.** For a game film, download the real models/textures (`assets/arena/*.glb`,
  `assets/arenas/<id>/props/*.glb`, `layout.json`, ground/backdrop) and replay a match recorded from the game's own simulation
  (`deployed/sim/record.mjs`, Node, no browser). It makes the arena and the action recognisable to players. Check the rules
  first (hand of 4 / queue of 4, Copium cap 10, placement rules): a story that ignores them reads as wrong.
- Memory: Cycles memory grows with every subdivided mesh (~130 MB each here) and every duplicated texture. 100 characters
  without subdivision and with deduplicated textures render in about 3 GB; with both it exceeded 14 GB and was killed.
- Text between camera and subject: characters standing in a row block a front close-up of the row behind. Put the bench in a
  line along a wall and shoot it from the aisle.

## Edit and story
- Write the script first, record narration, then cut shots to the measured line durations.
- Speed ramps: 0.3–0.5× on impacts only. One joke per shot. Hold the last beat longer than feels natural.
- Render an animatic (every 6th frame at 25 %) and review all shots before the full render.
- Characters outside their scene must be hidden by keyed scale (`vis()`), not just out of frame.

## Speed and reliability
- `scene.render.use_persistent_data = True` cuts per-frame overhead from ~12 s to ~4.6 s.
- 10 samples + OIDN at 1280×544 is enough for stylised scenes; upscale in the finish.
- Never run two heavy renders at once (out of memory). Long jobs follow the root `CLAUDE.md` rules.
- `bmesh` grids need UVs created by hand. Scale helpers must not read animated (hidden) scales.
- Check every finished film with contact sheets and a dark-frame scan before sending.

## Sound
- Narration must sit ~6 dB over music; duck music and effects under speech. Claude cannot hear: report levels and
  say the mix is unlistened.
- No cloning of real people's voices. Kokoro stock voices: `bm_george` (British narrator), `am_onyx` (deep US).

## Toolbox
See `README.md` in this folder: camera shake, Poly Haven loader, scatter, fire simulation.


## "Deployed" rework 3: play the real game first (lessons)

- Before filming a game, PLAY it (Playwright + Chromium works: guest accounts, a throwaway password kept out of git) and look at real
  frames. A film built only from source code reads as made by someone who never played: wrong HUD, too many units, tap vs drag.
- Portrait game footage inside a 16:9 film: render the portrait view as its own shot (`res` per shot), draw the HUD at the
  phone's native size, then fit it as a phone over a blurred, darkened copy of itself.
- Close-ups blocked by crew in front of the speaker: hide everybody else for that shot (solo / `keep`), not new camera angles.
- A tall cartoon fall (20 m) can take 1.0 s; physical 2 s made the jump look like it happened before the tap.
- A recorded plan must replay exactly: round positions BEFORE the search plays them, and allow one tick of tolerance.

## Deployed rework 4: lessons (timing, rigs, workers)
- A rig with no animation clip at a frame drops to its bind pose (T-pose). Animate past the last shot (END_A) and never cut a one-shot clip (attack, emote) short: its first frames are the T-pose wind-up. `Actor.tidy_items` plays moves in full and merges flicker.
- Pin each line to the shot that carries it (`say_now`, film time). Looking a cue up by animation time picks the wrong shot when ranges overlap.
- Close-up cameras need per-character eye heights (the egg's face sits low) and the position where the actor stands once the shot is under way (`seat`).
- Ramp shot: view the open ramp head-on from outside the door; a camera inside the row only shows backs.
- Frames must be filed by edit hash (`frames_jpg/<hash>/`); a worker on a stale checkout otherwise mixes old frames in (this produced a giant Sarge on the phone screen).
- Containers restart without warning. render_worker.sh pushes every 15 min and loops by itself; relaunching the same command resumes.
- Workers will not take a range from a peer session without being told by the user; ask the user to nudge them if they sit idle.

## Real-game study (Deployed rework 5)
- Headless Chromium runs the game at about 1 fps, so mouse drags take ~30 s each. Play over the game's own websocket instead:
  wrap `window.WebSocket` with `addInitScript`, send `{"t":"play","slot":i,"x":..,"z":..,"card":id,"n":k}` (n counts messages after hello). Script: `commercial/deployed/reference/play_real_match.js`.
- Snapshots are deltas: `add` (new unit: card, team), `d.unit` rows `[id, mask, values for the set bits]` (bit0 x, bit1 z, bit3 state, bit5 hp), `ev` (play, tower_down, phase, end).
- Real rules seen: overdose x2 at 120 s, a tie at 180 s goes to OVERTIME until a tower falls, Copium x3 at 240 s. The server bot rushes a passive player (HQ down in about 52 s).
- Three real matches played with a defence-first controller (lost 0-1 twice on time, once in overtime): units on the field averaged 3.4-4.0 (peak 8-14, six or more for 17-26 % of the time; overtime floods the field). The game's own sim with both sides playing like its Bot gives the same numbers (mean 3.7-4.5). The first Deployed match (button masher, never defends) averaged 5.6 with a peak of 13: too crowded.
- Film match: `sim/search4.mjs` finds sparse matches (both sides play like the game's bot), `sim/record4.mjs` records one into pack/match.json.
