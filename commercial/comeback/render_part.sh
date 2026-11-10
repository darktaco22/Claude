#!/bin/bash
# Render frames FIRST..LAST of the Meme Royale stadium commercial and encode them as one near-lossless part video.
# Usage: ./render_part.sh FIRST LAST   (3D frames are 49..1392; writes parts/part_FIRST_LAST.mp4 + .frames.txt)
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never setsid/nohup/&.
# Stops before the 2 h cap (RENDER_BUDGET, default 6000 s) and exits 3 with "RELAUNCH"; then run it again.
set -e
export RENDER_BUDGET=${RENDER_BUDGET:-6000}
HERE=$(cd $(dirname $0) && pwd); DG=$HERE/../degens; BL=/opt/blender/blender-4.2.3-linux-x64/blender
export W=${W:-$HOME/cb_work}; mkdir -p $W/frames $HERE/parts
[ -x $BL ] || bash $HERE/../noobpro/setup.sh > $W/setup.log 2>&1
[ -f $W/scene.blend ] || { rm -f $W/part_*.txt.done; $BL -b --factory-startup -P $HERE/scene.py -- --out $W/scene.blend > $W/build.log 2>&1; }
L=$W/part_$1_$2.txt; seq $1 $2 | tr '\n' ' ' > $L
[ -f $L.done ] && [ $W/scene.blend -nt $L.done ] && rm -f $L.done
rc=0; $BL -b $W/scene.blend -P $DG/render_list.py -- $L >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc), see $W/render.log"; tail -20 $W/render.log; exit $rc; }
O=$HERE/parts/part_$(printf %04d $1)_$(printf %04d $2)
mkdir -p $W/pk_$1 && i=0 && for f in $(cat $L); do i=$((i+1)); ln -sf $W/frames/f_$(printf %04d $f).png $W/pk_$1/p_$(printf %04d $i).png; done
ffmpeg -v error -y -framerate 24 -i $W/pk_$1/p_%04d.png -c:v libx264 -preset slow -crf 12 -pix_fmt yuv444p $O.mp4; cp $L $O.frames.txt
ls -la $O.mp4; echo PART-DONE $O.mp4
