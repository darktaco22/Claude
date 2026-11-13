#!/bin/bash
# finish.sh [WORK]: collects every pushed DAWN PATROL part (commercial/renders/ppart_AAAA_BBBB.mp4) from the worker branches, checks that
# all frames of timeline.json are there and, if they are, assembles the film (frames + overlay.webm + mix.m4a) into
# commercial/output/meme-royale-dawn-patrol.mp4. Exit 4 = frames still missing (it prints which). Needs only git, ffmpeg and python3.
set -e
W=${1:-$HOME/air_fin}; R=$(git rev-parse --show-toplevel); H=$R/commercial/air; mkdir -p $W/frames $W/parts; cd $R; git fetch -q origin
NF=$(python3 -c "import json;print(round(json.load(open('$H/timeline.json'))['end']*30))")
for b in $(git branch -r | grep -E 'origin/claude/(air-[a-z]*[0-9]+|last-line-final)$' | grep -v HEAD); do
  for f in $(git ls-tree --name-only $b commercial/renders/ 2>/dev/null | grep -E 'ppart_[0-9]{4}_[0-9]{4}\.mp4$'); do
    r=$(basename $f .mp4); r=${r#ppart_}
    if [ ! -s $W/parts/ppart_$r.mp4 ]; then git show $b:$f > $W/parts/ppart_$r.mp4
      ffmpeg -v error -y -i $W/parts/ppart_$r.mp4 -start_number $((10#${r:0:4})) $W/frames/f_%04d.png; echo "got ppart_$r from $b"; fi
  done
done
M=$(python3 -c "
import os
m=[f for f in range(1,$NF+1) if not os.path.exists('$W/frames/f_%04d.png'%f)]
r=[]
for x in m:
    if r and x==r[-1][1]+1: r[-1][1]=x
    else: r.append([x,x])
print(' '.join('%d-%d'%(a,b) for a,b in r))")
[ -z "$M" ] || { echo "MISSING frames: $M"; exit 4; }
python3 $R/commercial/useless/edit.py $H/timeline.json $W/frames $W/ff; N=$(ls $W/ff | wc -l); D=$(python3 -c "print($N/30)"); mkdir -p $R/commercial/output
ffmpeg -v error -y -framerate 30 -i $W/ff/f_%04d.png -c:v libvpx-vp9 -i $H/overlay.webm -i $H/mix.m4a \
  -filter_complex "[0:v]noise=alls=3:allf=t,format=rgba[bg];[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v];[2:a]atrim=0:$D[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 17 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -t $D $R/commercial/output/meme-royale-dawn-patrol.mp4
ffprobe -v error -show_entries stream=codec_type,width,height,nb_frames -show_entries format=duration,size -of compact $R/commercial/output/meme-royale-dawn-patrol.mp4; echo FILM-DONE
