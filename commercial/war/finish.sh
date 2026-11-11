#!/bin/bash
# finish.sh [WORK]: collects every pushed LAST LINE part from the worker branches, checks that all 1446 frames are there and,
# if they are, assembles the film (frames + overlay.webm + mix.m4a) into commercial/output/meme-royale-last-line.mp4.
# Exit 4 = frames still missing (it prints which). Needs only git, ffmpeg and python3.
set -e
W=${1:-$HOME/war_fin}; R=$(git rev-parse --show-toplevel); H=$R/commercial/war; mkdir -p $W/frames $W/parts; cd $R; git fetch -q origin
OK="0001_0080 0081_0160 0161_0321 0322_0482 0483_0643 0644_0723 0724_0804 0644_0804 0805_0884 0885_0965 0805_0965 0966_1046 1047_1126 0966_1126 1127_1207 1208_1287 1127_1287 1288_1366 1367_1446 1288_1446"
for b in $(git branch -r | grep -E 'origin/claude/' | grep -v HEAD); do
  for r in $OK; do f=commercial/renders/wpart_$r.mp4
    if [ ! -s $W/parts/wpart_$r.mp4 ] && git cat-file -e $b:$f 2>/dev/null; then git show $b:$f > $W/parts/wpart_$r.mp4
      ffmpeg -v error -y -i $W/parts/wpart_$r.mp4 -start_number $((10#${r:0:4})) $W/frames/f_%04d.png; echo "got wpart_$r from $b"; fi
  done
done
M=$(python3 -c "
import os
m=[f for f in range(1,1447) if not os.path.exists('$W/frames/f_%04d.png'%f)]
r=[]
for x in m:
    if r and x==r[-1][1]+1: r[-1][1]=x
    else: r.append([x,x])
print(' '.join('%d-%d'%(a,b) for a,b in r))")
[ -z "$M" ] || { echo "MISSING frames: $M"; exit 4; }
python3 $R/commercial/useless/edit.py $H/timeline.json $W/frames $W/ff; N=$(ls $W/ff | wc -l); D=$(python3 -c "print($N/30)"); mkdir -p $R/commercial/output
ffmpeg -v error -y -framerate 30 -i $W/ff/f_%04d.png -c:v libvpx-vp9 -i $H/overlay.webm -i $H/mix.m4a \
  -filter_complex "[0:v]noise=alls=3:allf=t,format=rgba[bg];[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v];[2:a]atrim=0:$D[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 17 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -t $D $R/commercial/output/meme-royale-last-line.mp4
ffprobe -v error -show_entries stream=codec_type,width,height,nb_frames -show_entries format=duration,size -of compact $R/commercial/output/meme-royale-last-line.mp4; echo FILM-DONE
