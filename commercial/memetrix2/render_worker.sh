#!/bin/bash
# Render frames A..B of THE MEMETRIX II, filed under the edit's hash, and push them as JPEGs to frames_jpg/<hash>/ on the current branch.
# Usage: ./render_worker.sh A B     Run with Bash run_in_background and timeout 7200000.
# Renders in slices (SLICE seconds, default 900): after every slice the new frames are converted, committed and pushed, so a
# container restart costs at most one slice. Loops by itself; exit 3 (RELAUNCH) only when the 2 h cap is reached; run it again then.
set -e
A=$1; B=$2; T0=$(date +%s); BUDGET=${RENDER_BUDGET:-6600}; SLICE=${SLICE:-900}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd); export W=${W:-$HOME/mx_work}
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
"$HERE/setup.sh"
cd "$HERE"
EH=$(sha1sum edl.json | cut -c1-10)             # frames are filed under the edit they were rendered for, so frames of another version can never be mixed in
export OUT="$W/frames2_$EH"; mkdir -p "$OUT"
echo "EDIT $EH (frames go to frames_jpg/$EH)"
LIST="$W/part2_${A}_${B}_$EH.txt"
if [ ! -f "$LIST" ]; then                       # frames listed in reuse_<hash>.txt are kept from an earlier render: skip them
  if [ -f "reuse_$EH.txt" ]; then seq "$A" "$B" | grep -vxF -f <(tr ' ' '\n' < "reuse_$EH.txt" | grep .) | tr '\n' ' ' > "$LIST"
  else seq "$A" "$B" | tr '\n' ' ' > "$LIST"; fi
fi
export SCALE=${SCALE:-67} SAMPLES=${SAMPLES:-6}
OUTJ="$HERE/frames_jpg/$EH"; mkdir -p "$OUTJ"

convert_and_push() {
  python3 - "$OUT" "$OUTJ" <<'PY'
import os, sys
from PIL import Image
src, dst = sys.argv[1:]
for name in sorted(os.listdir(src)):
    if name.startswith('f_') and name.endswith('.png'):
        out = os.path.join(dst, name[:-4] + '.jpg')
        if not os.path.exists(out):
            Image.open(os.path.join(src, name)).convert('RGB').save(out, quality=95, subsampling=0)
PY
  if [ -z "$NOPUSH" ]; then
    (cd "$REPO"; BR=$(git rev-parse --abbrev-ref HEAD); git add commercial/memetrix2/frames_jpg/$EH
     git commit -qm "Memetrix II: frames $A-$B (partial)" || true
     for i in 1 2 3 4 5; do { ! git ls-remote --exit-code -q origin "refs/heads/$BR" >/dev/null || git pull -q --rebase origin "$BR"; } && git push -q origin "HEAD:$BR" && break; sleep $((i * 5)); done) || true
  fi
}

while true; do
  LEFT=$((BUDGET - $(date +%s) + T0))
  [ "$LEFT" -gt 120 ] || { convert_and_push; echo "RELAUNCH: time cap reached"; exit 3; }
  [ "$LEFT" -lt "$SLICE" ] && S=$LEFT || S=$SLICE
  rc=0
  RENDER_BUDGET=$S "$BL" -b "$W/scene2.blend" -P render_edl.py -- "$LIST" >> "$W/render2.log" 2>&1 || rc=$?
  [ $rc = 0 ] || [ $rc = 3 ] || { echo "render failed ($rc)"; tail -20 "$W/render2.log"; exit $rc; }
  convert_and_push
  [ $rc = 0 ] && break
done
echo "WORKER-DONE $A-$B"
