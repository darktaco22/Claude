#!/bin/bash
# Render frames FIRST..LAST of "I WILL FIND YOU" (frames 991-1080 are the full-screen gameplay insert: skipped)
# and encode them as one near-lossless part video.  Usage: ./render_part.sh FIRST LAST  (writes parts/part_FIRST_LAST.mp4)
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never setsid/nohup/&.
# Stops before the 2 h cap (RENDER_BUDGET, default 6600 s) and exits 3 with "RELAUNCH"; then run it again.
set -e
export RENDER_BUDGET=${RENDER_BUDGET:-6600}
HERE=$(cd $(dirname $0) && pwd); DG=$HERE/../degens; BL=/opt/blender/blender-4.2.3-linux-x64/blender
export W=${W:-$HOME/fy_work}; export PH=$W/ph DA_TEX=$W/tex FY_LOSS=$W/seq/loss FY_GRAN=$W/seq/gran
mkdir -p $W/frames $HERE/parts
[ -f $W/.setup_done ] || { bash $DG/setup_remote.sh > $W/setup.log 2>&1; (cd $W && python3 $DG/phget.py ArmChair_01 side_table_01 throw_pillows_01 wooden_floor_02:tex beige_wall_001:tex) >> $W/setup.log 2>&1; touch $W/.setup_done; }
if [ ! -f $W/seq/gran/g_1128.png ]; then
  mkdir -p $W/cap_loss $W/cap_gran
  ffmpeg -v error -y -i $HERE/cap_loss_0156.mp4 -start_number 156 $W/cap_loss/f_%04d.png
  ffmpeg -v error -y -i $HERE/cap_gran_0123.mp4 -start_number 123 $W/cap_gran/f_%04d.png
  python3 $HERE/link_seq.py $W/cap_loss $W/cap_gran $W/seq
fi
[ -f $W/scene.blend ] || { rm -f $W/part_*.txt.done; $BL -b -P $HERE/scene.py -- --out $W/scene.blend > $W/build.log 2>&1; }
L=$W/part_$1_$2.txt; seq $1 $2 | awk '$1 < 991 || $1 > 1080' | tr '\n' ' ' > $L
[ -f $L.done ] && [ $W/scene.blend -nt $L.done ] && rm -f $L.done
rc=0; $BL -b $W/scene.blend -P $DG/render_list.py -- $L >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc), see $W/render.log"; tail -20 $W/render.log; exit $rc; }
# the part as a video: its frames in order (an insert gap is simply left out; finish.py re-reads the numbers from frames.txt)
O=$HERE/parts/part_$(printf %04d $1)_$(printf %04d $2)
mkdir -p $W/pk_$1 && i=0 && for f in $(cat $L); do i=$((i+1)); ln -sf $W/frames/f_$(printf %04d $f).png $W/pk_$1/p_$(printf %04d $i).png; done
ffmpeg -v error -y -framerate 30 -i $W/pk_$1/p_%04d.png -c:v libx264 -preset slow -crf 10 -pix_fmt yuv444p $O.mp4; cp $L $O.frames.txt
ls -la $O.mp4; echo PART-DONE $O.mp4
