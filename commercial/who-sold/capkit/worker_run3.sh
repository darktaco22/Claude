#!/bin/bash
# Resumable WHO SOLD? shot worker. Usage: worker_run3.sh key [key...]. Safe to re-run: delivered shots are skipped.
KIT="$(cd "$(dirname "$0")" && pwd)"; REPO="$(git -C "$KIT" rev-parse --show-toplevel)"
OUT="$REPO/commercial/who-sold/shots"; R=/root/road
mkdir -p $R/shots "$OUT"; rm -rf $R/cap; cp -r "$KIT" $R/cap; cd $R/cap; python3 gen3.py
pkill -9 -f "node drive" 2>/dev/null; pkill -9 -f chrom 2>/dev/null; sleep 2
rm -f ready cmd.js result.txt console.log
W=1080 H=1920 node drive.js > drive.out 2>&1 &
DRV=$!
for i in $(seq 1 120); do [ -f ready ] && break; sleep 5; done
[ -f ready ] || { echo "driver never became ready"; tail -5 drive.out; exit 2; }
rc=0
for a in "$@"; do
  if [ -f "$OUT/$a.mp4" ] && [ -f "$OUT/$a.json" ]; then echo "skip $a (already delivered)"; continue; fi
  rm -f $R/shots/$a.ok
  ./batch3.sh $a </dev/null
  if [ ! -f $R/shots/$a.ok ]; then echo "capture failed for $a"; rc=3; continue; fi
  cp $R/shots/$a.mp4 "$OUT/$a.mp4"; cp $R/shots/$a.json "$OUT/$a.json"
  cd "$REPO"; git add "commercial/who-sold/shots/$a.mp4" "commercial/who-sold/shots/$a.json"
  git commit -q -m "WHO SOLD? shot: $a

Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
  for t in 1 2 3 4 5; do git pull -q --rebase origin claude/last-line-final && git push -q origin HEAD:claude/last-line-final && break; sleep $((t*5)); done
  cd $R/cap
done
kill $DRV 2>/dev/null
echo "WORKER-FINISHED rc=$rc"; exit $rc
