#!/bin/bash
# Render frames FIRST..LAST of the Degens remake on this machine and encode them as one near-lossless
# video for transfer. Usage: W=~/da_work ./render_part.sh FIRST LAST OUT.mkv
set -e
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/da_work}; export DA_STUDIO=$HERE/studio; . $HERE/env.sh; export W DA_STUDIO PH=$W/ph DA_TEX=$W/tex
cd $HERE; mkdir -p $W/frames
[ -f $W/scene.blend ] || $BL -b -P director.py -- --out $W/scene.blend > $W/build.log 2>&1
seq $1 $2 | tr '\n' ' ' > $W/part.txt
$BL -b $W/scene.blend -P render_list.py -- $W/part.txt > $W/render.log 2>&1
ffmpeg -v error -y -start_number $1 -framerate 30 -i $W/frames/f_%04d.png -frames:v $(( $2 - $1 + 1 )) -c:v libx264 -preset slow -crf 9 -pix_fmt yuv444p $3
ls -la $3
