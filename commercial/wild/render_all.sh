#!/bin/bash
# Build, render, finish and encode "A NATURAL HISTORY".  Run as a tracked background task (run_in_background, timeout 7200000);
# exit 3 / "RELAUNCH" means run it again (finished frames are kept).  W = work folder (default ~/wild_work); KOKORO = folder with the Kokoro model files.
set -e
T0=$(date +%s); BUDGET=${RENDER_BUDGET:-6600}; HERE=$(cd $(dirname $0) && pwd); BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}; export W=${W:-$HOME/wild_work}; cd $HERE; mkdir -p $W/frames
[ -f $W/tex/rug.png ] || python3 tex.py $W/tex
[ -f $W/vo/vo.json ] || python3 voices.py ${KOKORO:-$W/kokoro} $W/vo
if [ ! -f $W/scene.blend ] || [ scene.py -nt $W/scene.blend ]; then $BL -b --factory-startup -P scene.py -- --out $W/scene.blend --tex $W/tex --vo $W/vo > $W/build.log 2>&1; rm -f $W/all.txt.done; fi
N=$(python3 -c "import json;print(json.load(open('edl.json'))['last'])")
[ -f $W/all.txt ] || seq 1 $N | tr '\n' ' ' > $W/all.txt
export RENDER_BUDGET=$((BUDGET - $(date +%s) + T0)); rc=0
$BL -b $W/scene.blend -P render_edl.py -- $W/all.txt >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc)"; tail -20 $W/render.log; exit $rc; }
for f in $(seq 1 $N); do [ -f $W/frames/f_$(printf %04d $f).png ] || { echo "FRAME MISSING $f"; exit 1; }; done
rm -rf $W/fin; python3 finish.py $W/frames $W/fin $W/vo > $W/finish.log 2>&1
O=$HERE/../output/meme-royale-natural-history.mp4
ffmpeg -v error -y -framerate 24 -i $W/fin/c_%04d.png -i $W/fin/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $O
ls -la $O; echo ALL-DONE
