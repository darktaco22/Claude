#!/bin/bash
# WHO SOLD? shots: frames3/<key> -> /root/road/shots/<key>.mp4 (+ .json, .ok). Usage: batch3.sh key [key...]
cd /root/road/cap; mkdir -p /root/road/shots
for a in "$@"; do
  d=frames3/$a
  [ -f /root/road/shots/$a.ok ] && continue
  echo "== $a $(date +%T)"
  ./waitrun.sh "if (await H.ev(()=>document.body.innerText.includes('TAP TO PLAY'))) { await p.mouse.click(540,1782); await H.sleep(3000);} return 1" >/dev/null </dev/null
  ./waitrun.sh "$(cat setup4_$a.js)" </dev/null | cut -c1-200
  rm -rf $d
  ./waitrun.sh "$(sed "s#__OUT__#$d#; s#__EVERY__#1#" cap3_tpl.js)" </dev/null | cut -c1-300
  if [ -f $d/info.json ] && [ "$(ls $d/f_*.png 2>/dev/null | wc -l)" -gt 60 ]; then
    ffmpeg -v error -y -framerate 30 -i $d/f_%04d.png -c:v libx264 -crf 14 -preset medium -pix_fmt yuv420p /root/road/shots/$a.mp4 </dev/null && cp $d/info.json /root/road/shots/$a.json && rm -rf $d && touch /root/road/shots/$a.ok
  fi
  echo "done $a $(date +%T)"
done
echo BATCH3-FINISHED
