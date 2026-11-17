#!/bin/bash
# Resumable hero-capture worker. Usage: worker_run.sh arena [arena...]
# Safe to re-run after a container restart: arenas already delivered to the repo are skipped.
KIT="$(cd "$(dirname "$0")" && pwd)"; REPO="$(git -C "$KIT" rev-parse --show-toplevel)"
OUT="$REPO/commercial/trophy-road/hero"; R=/root/road
mkdir -p $R/hero "$OUT"; rm -rf $R/cap; cp -r "$KIT" $R/cap; cd $R/cap
python3 gen2.py                                   # regenerates script2_*/setup3_* for this kit
pkill -9 -f "node drive" 2>/dev/null; pkill -9 -f chrom 2>/dev/null; sleep 2
rm -f ready cmd.js result.txt console.log
W=1080 H=1920 node drive.js > drive.out 2>&1 &
DRV=$!
for i in $(seq 1 120); do [ -f ready ] && break; sleep 5; done
[ -f ready ] || { echo "driver never became ready"; tail -5 drive.out; exit 2; }
rc=0
for a in "$@"; do
  if [ -f "$OUT/$a.mp4" ] && [ -f "$OUT/$a.json" ]; then echo "skip $a (already delivered)"; continue; fi
  rm -f $R/hero/$a.ok; rm -rf frames2
  ./batch2.sh $a </dev/null
  if [ ! -f $R/hero/$a.ok ]; then echo "capture failed for $a"; rc=3; continue; fi
  ffmpeg -v error -y -i $R/hero/$a.mp4 -c:v libx264 -crf 17 -preset medium -pix_fmt yuv420p "$OUT/$a.mp4" </dev/null
  cp $R/hero/$a.json "$OUT/$a.json"
  cd "$REPO"; git add "commercial/trophy-road/hero/$a.mp4" "commercial/trophy-road/hero/$a.json"
  git commit -q -m "Trophy Road hero capture: $a

Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
  for t in 1 2 3 4 5; do git pull -q --rebase origin claude/last-line-final && git push -q origin HEAD:claude/last-line-final && break; sleep $((t*5)); done
  cd $R/cap
done
kill $DRV 2>/dev/null
echo "WORKER-FINISHED rc=$rc"; exit $rc
