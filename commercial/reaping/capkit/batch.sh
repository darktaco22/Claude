#!/bin/bash
RSHOTS=${RSHOTS:-/root/road/rshots}
# THE REAPING shots: frames/<key> -> $RSHOTS/<key>.mp4. Usage: batch.sh key [key...]
cd /root/road/rcap; mkdir -p $RSHOTS
for a in "$@"; do
  [ -f $RSHOTS/$a.ok ] && continue
  echo "== $a $(date +%T)"
  ./waitrun.sh "if (await H.ev(()=>document.body.innerText.includes('TAP TO PLAY'))) { await p.mouse.click(540,1782); await H.sleep(3000);} return 1" >/dev/null </dev/null
  ./waitrun.sh "$(cat setup_$a.js)" </dev/null | cut -c1-200
  d=frames/$a; rm -rf $d
  if [ -f frames_$a.n ]; then ./waitrun.sh "$(sed "s#__OUT__#$d#; s#__N__#$(cat frames_$a.n)#" cap_frames.js)" </dev/null | cut -c1-300
  else ./waitrun.sh "$(sed "s#__OUT__#$d#" cap_tpl.js)" </dev/null | cut -c1-300; fi
  if [ -f $d/info.json ] && [ "$(ls $d/f_*.png 2>/dev/null | wc -l)" -gt 30 ]; then
    python3 fixblank.py $d
    ffmpeg -v error -y -framerate 30 -i $d/f_%04d.png -c:v libx264 -crf 14 -preset medium -pix_fmt yuv420p $RSHOTS/$a.mp4 </dev/null && cp $d/info.json $RSHOTS/$a.json && touch $RSHOTS/$a.ok && rm -rf $d
  fi
  echo "done $a $(date +%T)"
done
echo BATCH-FINISHED
