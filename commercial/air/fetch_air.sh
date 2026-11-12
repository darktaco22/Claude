#!/bin/bash
# Downloads the Meme Royale assets LAST LINE uses, straight from the live game. Usage: ./fetch_war.sh GAME_DIR
set -e
G=$1; mkdir -p $G/units $G/arena $G/arenas/dump; cd $G
SITE=https://memeroyale.imaginestudio.fun/assets; UA="meme-royale-ad-builder/1.0"
get() { [ -s "$2" ] || curl -sSf -A "$UA" --retry 4 -o "$2" "$1"; }
for u in swordcat floki toshi walter goat slerf pepe bonk cate giga troll chillguy wojak pnut; do get $SITE/units/$u.glb units/$u.glb; done
mkdir -p $G/arenas/cemetery; for f in ground ground_n backdrop; do get $SITE/arenas/cemetery/$f.webp arenas/cemetery/$f.webp; done
for a in tower_rig battlestation tower_rig_ruin battlestation_ruin bridge; do get $SITE/arena/$a.glb arena/$a.glb; done
for f in ground ground_n backdrop; do get $SITE/arenas/dump/$f.webp arenas/dump/$f.webp; done
[ -z "$(find $G/units $G/arena $G/arenas/dump -size 0)" ] && echo WAR-ASSETS-OK
