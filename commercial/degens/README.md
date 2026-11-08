# Degens Anonymous (realistic remake)

Blender 4.2 + Cycles remake of the Degens Anonymous skit, with the original timing, dialogue, shots and sound cues.

- `director.py`: builds the scene and keys every frame (`blender -b -P director.py -- --out scene.blend`). Needs `env.sh` paths: `PH` (Poly Haven assets), `DA_TEX`, `DA_STUDIO` (original skit folder with `vo.json` and `models/neet.glb`).
- `humans.py`: the cast as original MakeHuman people (MPFB 2, CC0 assets), with clothing masks, recolours and lip-sync visemes.
- `rigctl.py`: IK/FK pose controller. Props are placed from the hand targets.
- `props.py`, `room.py`, `assets.py`: props, sets and Poly Haven (CC0) loading.
- `qa.py`, `sheet.py`: QA stills and contact sheets. `render_all.py`: resumable frame render.
- `overlay.html` + `overlays.js`: subtitles and phone UI as transparent frames. `assemble.sh`: upscale, overlay, mix, encode.
