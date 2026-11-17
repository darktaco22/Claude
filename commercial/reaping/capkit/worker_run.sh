#!/bin/bash
# Resumable THE REAPING shot worker. Usage: worker_run.sh key [key...]. Captures each shot with the real game in headless
# Chromium, then commits commercial/reaping/shots/<key>.mp4 and pushes. Already-delivered shots are skipped.
set -u
KIT="$(cd "$(dirname "$0")" && pwd)"; REPO="$(git -C "$KIT" rev-parse --show-toplevel)"
cd "$REPO" && git fetch -q origin claude/last-line-final && git reset -q --hard FETCH_HEAD
OUT="$REPO/commercial/reaping/shots"; C=/root/road/rcap; export RSHOTS=/root/road/rshots
mkdir -p $RSHOTS "$OUT"; rm -rf $C; cp -r "$KIT" $C; cd $C
for k in "$@"; do python3 mk.py $k >/dev/null; done
pkill -9 -f "node drive" 2>/dev/null; pkill -9 -f chrom 2>/dev/null; sleep 2
rm -f ready cmd.js result.txt console.log
W=1080 H=1920 node drive.js > drive.out 2>&1 &
DRV=$!
for i in $(seq 1 120); do [ -f ready ] && break; sleep 5; done
[ -f ready ] || { echo "driver never became ready"; tail -5 drive.out; exit 2; }
echo "boot: $(./waitrun.sh "$(cat boot2.js)")"
rc=0
for a in "$@"; do
  if [ -f "$OUT/$a.mp4" ]; then echo "skip $a (already delivered)"; continue; fi
  rm -f $RSHOTS/$a.ok
  ./batch.sh $a </dev/null
  if [ ! -f $RSHOTS/$a.ok ]; then echo "capture failed for $a"; tail -5 console.log; rc=3; continue; fi
  cp $RSHOTS/$a.mp4 "$OUT/$a.mp4"; cp $RSHOTS/$a.json "$OUT/$a.json"
  cd "$REPO"; git add "commercial/reaping/shots/$a.mp4" "commercial/reaping/shots/$a.json"
  git commit -q -m "THE REAPING shot: $a"
  for t in 1 2 3 4 5; do git pull -q --rebase origin claude/last-line-final && git push -q origin HEAD:claude/last-line-final && break; sleep $((t*5)); done
  cd $C
done
kill $DRV 2>/dev/null
echo "WORKER-FINISHED rc=$rc"; exit $rc
