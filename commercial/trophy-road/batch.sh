#!/bin/bash
# captures each arena once; a finished arena has frames/NN_arena/DONE
cd /root/road/cap
python3 - <<'P' > arenas.txt
import json
for i,a in enumerate(json.load(open('arenas.json'))): print(i+1,a)
P
while read i a; do
  d=$(printf "frames/%02d_%s" $i $a)
  [ -f $d/DONE ] && continue
  echo "== $a $(date +%T)"
  ./waitrun.sh "if (await H.ev(()=>document.body.innerText.includes('TAP TO PLAY')||!!document.querySelector('[class*=splash],[id*=splash]'))) { await p.mouse.click(540,1782); await H.sleep(3000);} return 1" >/dev/null
  ./waitrun.sh "$(cat setup_$a.js)" | cut -c1-200
  ./waitrun.sh "$(sed "s#__OUT__#$d#" cap_tpl.js)" | cut -c1-200
  [ -f $d/sfx.json ] && touch $d/DONE
  [ -f $d/DONE ] && (cd /root/road && rm -f seg/s_$a.mp4 && python3 assemble.py $a </dev/null >/dev/null 2>&1 && rm -f cap/$d/f_*.png)
  echo "done $a $(date +%T) $(ls $d | wc -l) files"
done < arenas.txt
echo BATCH-FINISHED
