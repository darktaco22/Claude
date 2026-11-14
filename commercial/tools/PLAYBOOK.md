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
