# "THE FARTCOIN INVESTOR": Meme Royale mockumentary short (skit #2)

`fartcoin_investor.mp4`: 1080×1920, 45 s, H.264 + AAC, 21 MB. `cover.jpg` is the thumbnail (the "Why would I deceive you?" close-up).

## Why this character and format (research, Nov 6 2026)
- **Fartcoin** is one of the most actively traded memecoins this month (alongside DOGE, PEPE and PENGU), and the game has a FARTER card, a FART spell and a GAS FEES spell.
- **"Why would I deceive you?"** (from the Elizabeth Holmes / Nathan Fielder documentary teaser, Sept 2026) is a trending deadpan "caught in an obvious lie" reaction format. It fits a guy who obviously farted.
- **Mockumentary / talking-head** deadpan is a proven skit format; narrative comedy shorts are trending toward 30–60 s, which leaves room for setup and callbacks.
- **Low rights risk:** FARTER is the game's own character design (unlike Chill Guy or Pepe, whose creators have objected to crypto use).

## Beat sheet
| Time | Scene | Joke |
|---|---|---|
| 0–4.4 | Elevator, "someone in this elevator holds $FARTCOIN"; green cloud; everyone turns; close-up: **"Why would I deceive you?"** + snap zoom + boom | cold-open hook on a trending format |
| 4.4–5.9 | Title slam: THE FARTCOIN INVESTOR, *a documentary* | genre switch |
| 5.9–18.8 | Interview: "What does Fartcoin actually do?" / "It's a utility token." / "What's the utility?" / **"Gas fees."** (puff, laugh) / "Some people say it stinks." / "That's how you know it's working." | crypto pun, rule of three |
| 18.8–26.4 | The elevator, 9:01 AM: Jean Phil "Sacré bleu!" faints, Wojak "Okay.", Giga "Hmm.", Chill Guy cameo shrug ("I'm just a chill guy"), FARTER: "That is called… proof of stink." | ensemble reactions; callback to skit #1; Proof-of-Stake pun |
| 26.4–36.5 | Meme Royale: "step 1: gas the whale" (The Whale: "Make way."), "step 2: let it drift" (FART spell melts the tower), "step 3: deny everything": "Did you just win… by farting?" / "It's called a strategy." | real game mechanics as the joke |
| 36.5–41.3 | "Any advice for new investors?" / **"Hold your breath."** (punch-in, puff, laugh) | button joke |
| 41.3–45.3 | End card: FARTER card, PLAY FREE | call to action |

## What improved over skit #1 (Chill Guy)
**Script**
- Real spoken dialogue (two TTS voices: a neutral interviewer, and a posh British deadpan for FARTER), not just captions.
- Cold open on the punchline, then a title card (a proven hook structure).
- More jokes per second, a rule-of-three build, a callback to skit #1 (Chill Guy cameo), and a final "button" line.
- Every line checked for intelligibility with Whisper; "Gas." was misheard as "Ass." in the mix, so it became "Gas fees." (clearer, and a better crypto pun).

**Rendering and editing**
- Depth of field (three.js BokehPass, loaded as a blob module to satisfy the game's CSP) on all skit shots.
- Handheld documentary camera noise, snap punch-in zooms synced to booms.
- Particle gas clouds (soft sprites that billow, drift and fade near the camera).
- New sets: a brushed-steel elevator with a floor display, and a night office with a procedural skyline, a framed $FART chart and the game's own candle and rocket props.
- Word-by-word subtitles synced to the speech, a documentary lower third, an animated title card.
- Film grade in post: contrast and saturation, vignette, light grain.
- Music ducks under dialogue; laugh track; the game's fart, stink and impact sounds.

**QA (new)**
- Preview contact sheets for each pass, plus a 2-fps frame scan of the final.
- Caught and fixed: the subject off-frame in the elevator wide shot, gas flooding the close-ups, a blown-out elevator wall, FARTER facing away during the arena dialogue, and the camera clipping into tower rubble. That shot was re-rendered on its own and spliced back in.
- A full-mix Whisper transcript confirms every line reads.

## Post copy (X)
> Fartcoin holders when you ask about the fundamentals 💨
>
> "it's a utility token"
>
> 🎮 play free → memeroyale.imaginestudio.fun

Alt hooks: "someone in this elevator holds $FARTCOIN" / "proof of stink is the future of consensus"

## Distribution notes
- Post natively, vertical. Reply with it under Fartcoin and memecoin discussions (it's one of the most traded memecoins right now).
- Quote-tweet from @imaginegamelabs.
- On TikTok, Reels and Shorts, the cold-open line works as the on-screen hook in the first second.

## Rebuilding
- Voices: Piper TTS (`pip install piper-tts`; voices `en_US-lessac-medium` and `en_GB-alan-medium` from huggingface.co/rhasspy/piper-voices). Lines are in `source/tts_lines.tsv`.
- Render: `node source/skit2.js out.mp4` (`SEG0`/`SEG1` re-render a single shot quickly; the simulation fast-forwards without drawing).
- Sound: `python3 source/mix.py out_events.json 45.3 mix.m4a nofixed`.
- End card: `node source/endcard.js end.mp4 4 end2.html`.
