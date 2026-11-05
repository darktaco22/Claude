# MEME ROYALE: the runway

This folder holds two versions: the raea one described here (`runway.tsx`, `cast.ts`, rendered to
`../output/meme-royale-runway.mp4`), and a Blender one added separately (`runway_showcase.py`, `fetch_models.py`,
`render_runway.sh`; see `../README.md`).

`../output/meme-royale-runway.mp4`: 2 min 54 s, 1280×720, 30 fps. Every character in the game (all 39 unit models) walks
the runway one by one, commons first and the legendaries last: in from the left, a turn to the camera, its own pose clip
(its emote, or its victory loop when the emote is short) with its own voice line and a name/rarity card, a turn back, and
off to the right as the next one arrives. The camera never moves. The backdrop is each character's own card art,
washed out, cross-fading over 1.5 s as each new one reaches the mark. The game's menu music plays underneath.

Made with raea (`runway.tsx`, cast and clip lengths in `cast.ts`), from the game's own models, clips, card art, voice lines and
music. It passes `raea check`: -14.1 LUFS, nothing clipped, contrast and reading time OK.

To re-render, put the game's files in `media/` beside `runway.tsx` (`models/<id>.glb`, `bg/<id>.png` from `cards/<id>.png`,
`sfx/bark_*.mp3`, `sfx/mus_menu.mp3`, `logo.png`, `lilita.ttf`), then run
`RAEA_READBACK=rgba raea render runway.tsx -o frames/` and encode the frames with x264 (crf 15), taking the sound from a normal
`raea render runway.tsx -o runway.mp4`.
