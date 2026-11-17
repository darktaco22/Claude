#!/bin/bash
# hero captures: frames2/NN_arena -> /root/road/hero/arena.mp4 (frames deleted after encode)
cd /root/road/cap; mkdir -p /root/road/hero
python3 - "$@" <<'P' > hero.txt
import json,sys
h=json.load(open('hero.json')); sel=sys.argv[1:] or h
for a in sel: print(h.index(a)+1,a)
P
while read i a; do
  d=$(printf "frames2/%02d_%s" $i $a)
  [ -f /root/road/hero/$a.ok ] && continue
  echo "== $a $(date +%T)"
  ./waitrun.sh "if (await H.ev(()=>document.body.innerText.includes('TAP TO PLAY'))) { await p.mouse.click(540,1782); await H.sleep(3000);} return 1" >/dev/null </dev/null
  ./waitrun.sh "$(cat setup3_$a.js)" </dev/null | cut -c1-200
  ./waitrun.sh "$(sed "s#__OUT__#$d#" cap2_tpl.js)" </dev/null | cut -c1-400
  if [ -f $d/sfx.json ]; then
    ffmpeg -v error -y -framerate 30 -i $d/f_%04d.png -c:v libx264 -crf 12 -preset fast -pix_fmt yuv420p /root/road/hero/$a.mp4 </dev/null && cp $d/sfx.json /root/road/hero/$a.json && rm -f $d/f_*.png && touch /root/road/hero/$a.ok
  fi
  echo "done $a $(date +%T)"
done < hero.txt
echo BATCH2-FINISHED
