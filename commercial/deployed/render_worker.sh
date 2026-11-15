#!/bin/bash
# Render frames A..B of DEPLOYED and push them as JPEGs to frames_jpg/ on the current branch.
# Usage: ./render_worker.sh A B     Run with Bash run_in_background and timeout 7200000. Exit 3 (RELAUNCH) = run it again.
set -e
A=$1; B=$2; T0=$(date +%s); BUDGET=${RENDER_BUDGET:-6300}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd); export W=${W:-$HOME/dep_work}
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
"$HERE/setup.sh"
cd "$HERE"; mkdir -p "$W/frames"
LIST="$W/part_${A}_${B}.txt"; [ -f "$LIST" ] || seq "$A" "$B" | tr '\n' ' ' > "$LIST"
export SCALE=${SCALE:-67} SAMPLES=${SAMPLES:-6} RENDER_BUDGET=$((BUDGET - $(date +%s) + T0)); rc=0
"$BL" -b "$W/scene.blend" -P render_edl.py -- "$LIST" >> "$W/render.log" 2>&1 || rc=$?
[ $rc = 0 ] || [ $rc = 3 ] || { echo "render failed ($rc)"; tail -20 "$W/render.log"; exit $rc; }
OUTJ="$HERE/frames_jpg"; mkdir -p "$OUTJ"
python3 - "$W/frames" "$OUTJ" <<'PY'
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
  cd "$REPO"; BR=$(git rev-parse --abbrev-ref HEAD); git add commercial/deployed/frames_jpg
  git commit -qm "Deployed: frames $A-$B (partial)" || true
  for i in 1 2 3 4 5; do git pull -q --rebase origin "$BR" && git push -q origin "HEAD:$BR" && break; sleep $((i * 5)); done
fi
if [ $rc = 3 ]; then echo "RELAUNCH: $(grep -o 'BUDGET-STOP [0-9]*' "$W/render.log" | tail -1) frames left"; exit 3; fi
echo "WORKER-DONE $A-$B"
