#!/bin/bash
# Downloads the Meme Royale assets NO UTILITY uses, straight from the live game: unit models (with their clips),
# arena models, the "cold" arena's ground/backdrop, card art, UI art and sounds. Usage: ./fetch_game.sh GAME_DIR
set -e
G=$1; mkdir -p $G/units $G/arena $G/arenas/cold $G/cards $G/audio; cd $G
SITE=https://memeroyale.imaginestudio.fun/assets; UA="meme-royale-ad-builder/1.0"
get() { [ -s "$2" ] || curl -sSf -A "$UA" --retry 4 -o "$2" "$1"; }
for u in useless giga whale goat bonk cate walter; do get $SITE/units/$u.glb units/$u.glb; done
for a in tower_rig battlestation tower_rig_ruin battlestation_ruin bridge; do get $SITE/arena/$a.glb arena/$a.glb; done
for f in ground ground_n backdrop; do get $SITE/arenas/cold/$f.webp arenas/cold/$f.webp; done
for c in useless giga whale goat bonk cate walter troll chillguy; do get "$SITE/cards/$c.webp?v=2" cards/$c.webp; done
get $SITE/ui/bg_title_wide.webp bg_title_wide.webp
for s in amb_cold mus_battle_cold unit_die_1 punch_heavy_1 punch_light_1 punch_light_2 swing_1 swing_2 whale_slam card_pick deploy_drop \
  coin_jingle_1 coin_jingle_2 charge_rush countdown_tick victory vo_victory ui_swoosh bark_useless; do get $SITE/audio/$s.mp3 audio/$s.mp3; done
echo GAME-ASSETS-OK
