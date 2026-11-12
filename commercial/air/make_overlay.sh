#!/bin/bash
# Renders overlay.html (subtitles, flashes, tagline, end card) for every frame and encodes overlay.webm. Usage: make_overlay.sh TIMELINE.json OUT_WEBM
set -e
H=$(cd $(dirname $0) && pwd); TL=$1; OUT=$2; D=$(mktemp -d); export GAME=${GAME:-$HOME/war_work/game}
cd $H && NODE_PATH=$(npm root -g 2>/dev/null) node overlays.js $TL $D
ffmpeg -v error -y -framerate 30 -i $D/o_%04d.png -vf scale=540:960 -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 -auto-alt-ref 0 $OUT; rm -rf $D; ls -la $OUT
