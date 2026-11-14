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
- **Fire/smoke.** Sphere puffs look like balls. `fire.py` bakes a real Mantaflow simulation to OpenVDB and renders
  (pipeline proven, ~1 min at res 96), but the default look is NOT good yet: it still reads as a glowing ball then a
  dark blob. To do before using it in a film: irregular emitter, higher initial velocity, noise upres, lit smoke.
  Downloaded CC0 VDBs (JangaFX) remain the better option if the host is allowed.
- **Camera.** Add recorded shake (`shakify.py`): INVESTIGATION at 0.3–0.6 for calm shots, THE_CLOSEUP for tension,
  HANDYCAM_RUN for chaos. Synthetic sine shake looks mechanical.
- **Finish (2D).** Bloom, light halation, vignette, grain, letterbox. Text needs a shadow and must avoid bright sky.

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
