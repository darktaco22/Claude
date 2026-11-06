# "Chill Guy vs the -94% candle": Meme Royale short

`chillguy_meme_royale.mp4`: 1080×1920 (9:16), 43 s, H.264 + AAC, ready for X, TikTok, Reels and Shorts. `cover.jpg` is the thumbnail.

Everything in it comes from the live game: the 3D character models and animations, the Trading Floor arena, real spells and towers running in the game engine, the game's lofi track, and the characters' own voice lines ("I'm just a chill guy", "Sacré bleu!", Wojak's "Okay.").

## Beat sheet
| Time | Scene | Joke |
|---|---|---|
| 0–4.9 | 3:47 AM bedroom, chart crashing, phone notifications stacking (LIQUIDATED x100 / Dev: "gm frens, minor setback" / Mom: "did u sell the jpeg money??" / Landlord: "rent." / The Boys: "IT'S OVER") | relatable crypto pain hook |
| 4.9–8.6 | He turns to camera, shrugs: *"I'm just a chill guy"* | the meme's punchline |
| 8.6–15.6 | Group chat: Wojak running in panicked circles, NEET raging, Jean Phil "sacré bleu, je suis liquidated", Chill Guy walks in: "zoom out bro", Wojak: "okay." | contrast; deadpan voice line |
| 15.6–32 | "So he settled it like an adult: in Meme Royale." Panic Sell: the squad runs home, he keeps walking. Rug Pull: he doesn't notice. "Strategy? none. just vibes." Tower down, Battlestation down, "3 crowns, still chill." | shows his real card ability (can't be stunned or knocked back) |
| 32–39 | "5 minutes later: -93.8%" → "WE'RE SO BACK" (Wojak and Jean Phil celebrate) → him: "oh, did something happen?" | payoff and callback |
| 39–43 | End card: Chill Guy card, "can't be stunned / can't be knocked back / never panic sells", PLAY FREE + URL | call to action |

## Post copy (X)
> 3:47 AM. portfolio -94%.
>
> chill guy: 🤷
>
> can't be stunned. can't be knocked back. never panic sells.
> play free → memeroyale.imaginestudio.fun

Alternate hooks: "the group chat vs the one friend who never checks the chart" / "POV: you're the chill guy in a -94% market"

## Why it should outperform the account's current posts
Their best post (V2 trailer, 16:9) did 2.5K views; most get 250–800.
- **Vertical 9:16.** Built for phone feeds; only one of their 9 videos was vertical.
- **Hook in the first second.** On-screen text and notifications start at 0.9 s, and most people watch muted, so every joke is in captions.
- **A meme format people already know**, applied to the most relatable CT moment (a −94% bag), rather than a feature list.
- **It shows the game's actual mechanic as the joke** (Chill Guy really can't be stunned or knocked back), so it works as an ad without feeling like one.
- **Recurring cast** (NEET, Wojak, Jean Phil) continues their skit series, so it fits the account.
- **Distribution ideas:** post natively in the US evening, pin it, quote-tweet from @imaginegamelabs, reply with it under large CT "it's over" posts, and cross-post to TikTok, Reels and Shorts (where the trending "Hinoki Wood" Chill Guy sound can be added in-app under the platform's licence).

## Rights note
The Chill Guy character was created by artist **Phillip Banks**, who has publicly objected to its use by crypto projects (the $CHILLGUY coin) and stated that it is copyrighted. Meme Royale already ships the character, but a promotional video increases visibility, so the team should be comfortable with that risk (or have permission) before posting.

## Rebuilding
`source/skit.js` renders the 3D part from the live game (`node skit.js out.mp4`; `node skit.js dir preview` for a quick low-res check). `source/endcard.js` renders the end card. `source/mix.py` builds the soundtrack from the render's event log and the game's audio files (see the play-by-play log in the parent folder for how they were fetched).
