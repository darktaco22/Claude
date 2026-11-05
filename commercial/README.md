# MEME ROYALE: Solana dApp Store / Seeker commercials

Two commercials for [memeroyale.imaginestudio.fun](https://memeroyale.imaginestudio.fun), announcing the game is coming
to the Solana dApp Store and playable on Seeker. Everything on screen is the real game: footage rendered by the game's own
engine, the game's own 3D characters, card art, logo, font, music and sound effects.

| File | What it is |
|---|---|
| `output/meme-royale-seeker-blender.mp4` | **16:9, 29 s.** Engine cinematics of a real battle, PEPE playing the game on a phone in space (Blender), the portrait game in a phone, end card. Cut in Blender's sequencer. |
| `output/meme-royale-seeker-raea.mp4` | **9:16, 20 s.** Vertical spot for mobile feeds, made with raea: cropped engine shots, the characters in 3D, the game on a phone, card fan end card. |
| `output/raea-showcase.mp4` | raea demo: the game's GIGA, PEPE and MOO DENG models with their own animation clips. |

Both final exports pass `raea check`: -14 LUFS (±0.5), true peak under -1 dBTP, text inside the platform safe areas,
contrast and reading time OK, no dark-area blocking.

## Storyboard (Blender cut)

| Time | Shot | On screen |
|---|---|---|
| 0:00 | GIGA wrestles MOO DENG on the bridge (engine close-up) | REAL-TIME / MEME CARD BATTLES |
| 0:03 | God Candle smashes a tower | GOD CANDLE! |
| 0:06 | The rug pull, coins flying | RUG PULL! |
| 0:08 | POPCAT under PUMP IT | 74 MEME CARDS |
| 0:11 | Sweep over the full brawl | 17 ARENAS |
| 0:14 | The king tower falls | VICTORY! |
| 0:17 | PEPE in deep space plays on his phone, turns it to us, the camera pushes into the screen | COMING TO THE SOLANA dAPP STORE · PLAY IT ON SEEKER |
| 0:22 | The game in its phone layout | PLAYABLE ON SEEKER · THE FULL GAME ON MOBILE |
| 0:25 | Logo over the key art | COMING SOON TO THE SOLANA dAPP STORE · PLAYABLE ON SEEKER · URL |

The card count (74) and arena count (17) come from the game's own `data.js`.

## How it was made

1. **Footage from the game's engine** (`engine/capture/`). The live site runs in headless Chromium. `vclock.js`
   replaces the page's clock (requestAnimationFrame, `performance.now`, timers, CSS animations) with a virtual one, so the
   three.js engine is stepped exactly 1/30 s per frame and every frame is captured, however slow the software GPU is.
   `director.js` scripts an offline match against the game's own `Battle` (who plays which card, where, when) and drives
   the engine's camera for cinematic shots; `script_basement.js` is the choreography. Every sound the game plays is logged
   with its frame, so the edit can place the game's real sound effects on the picture. Two passes: a 1280×720 cinematic
   pass with the HUD hidden, and a 540×960 pass in the game's phone layout with its real HUD.
2. **Hero shot** (`engine/hero_seeker.py`, Blender, Cycles). The game's PEPE model and his idle animation, his hands on
   the phone by IK and his head turned to the screen; the screen plays the phone-layout capture frame for frame. A space
   set: a star field and nebula in the world shader, and a ringed planet.
3. **Edit** (`engine/edit_commercial.py`, Blender's sequencer). Reads `engine/edit.json`: the cuts, titles in the game's
   Lilita One font, the phone mock-up (`make_edit_assets.py`), the game's battle music, and the logged sound effects
   (285 strips). Rendered to PNG frames and a WAV mixdown, then encoded with x264 and loudness-normalized.
4. **raea spot** (`raea/seeker-ad.tsx`). A raea composition in React and TypeScript, rendered with `raea render`.

## Re-render

Needs Blender 4.2+, ffmpeg, Node with Playwright and Chromium, and [raea](https://raea.io/install). On a machine without a GPU,
raea needs Mesa's Vulkan driver (`mesa-vulkan-drivers`) and `WGPU_BACKEND=vulkan`.

```bash
# the hero shot (screen = the phone-layout capture)
blender -b --factory-startup -P engine/hero_seeker.py -- --model pepe.glb --screen cap_phone --first 88 \
  --backdrop backdrop_blur.png --w 1280 --h 720 --samples 8 --render hero_frames
# the edit (paths in edit.json are relative to it)
blender -b --factory-startup -P engine/edit_commercial.py -- edit.json out.mp4 --frames final_frames
# the raea spot (media/ beside the .tsx: cinematic.mp4, gameplay.mp4, the .glb models, cards/, sounds)
raea render raea/seeker-ad.tsx -o meme-royale-seeker-raea.mp4 --quality master && raea check meme-royale-seeker-raea.mp4 --shape 9:16
```

The large intermediates (captured frames, models, sounds) are re-created by the capture scripts and are not committed.

## Notes

- The phone is a generic dark handset; no Solana Mobile logos or product design were recreated. Swap in official
  Seeker / dApp Store badge artwork if you have it.
- The first version (an original Blender scene, before the real game was used) is kept in `v1/`.
