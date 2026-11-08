#!/bin/bash
# Render frames FIRST..LAST of LAST WILL & TESTAMENT and encode them for transfer.
# Usage: W=~/wh_work ./render_part.sh FIRST LAST OUT.mp4
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never with setsid/nohup.
# It stops itself before the 2 h cap (RENDER_BUDGET, default 6600 s) and exits 3 ("RELAUNCH") with frames left:
# then run the same command again. Finished frames are never re-rendered.
set -e
export RENDER_BUDGET=${RENDER_BUDGET:-6600}
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/wh_work} PH=$W/ph DA_TEX=$W/tex WHALE=${WHALE:-$W/whale.glb} VO=$HERE/vo
BL=/opt/blender/blender-4.2.3-linux-x64/blender
cd $HERE/../degens; mkdir -p $W/frames
[ -f $W/scene.blend ] || { rm -f $W/part_*.txt.done; $BL -b -P $HERE/director.py -- --out $W/scene.blend > $W/build.log 2>&1; }
L=$W/part_$1_$2.txt; seq $1 $2 | tr '\n' ' ' > $L
[ -f $L.done ] && [ $W/scene.blend -nt $L.done ] && rm -f $L.done
rc=0; $BL -b $W/scene.blend -P render_list.py -- $L >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc), see $W/render.log"; exit $rc; }
ffmpeg -v error -y -start_number $1 -framerate 30 -i $W/frames/f_%04d.png -frames:v $(( $2 - $1 + 1 )) -c:v libx264 -preset slow -crf 9 -pix_fmt yuv444p $3
ls -la $3
