#!/bin/bash
# Render frames A..B of "THE FINAL" on a worker machine and push them as JPEGs.
# Usage: ./render_worker.sh A B   (run with Bash run_in_background, timeout 7200000; exit 3 = run the same command again)
# Needs only this repo (game models are in commercial/comeback) plus pack/vo and pack/fx. Blender 4.2.3 is fetched if missing.
set -e
A=$1; B=$2; T0=$(date +%s); BUDGET=${RENDER_BUDGET:-6300}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
export W=${W:-$HOME/final_work}; mkdir -p "$W/frames"
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
if [ ! -x "$BL" ]; then
  mkdir -p /opt/blender && cd /opt/blender
  curl -sSL -o b.tar.xz https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf b.tar.xz && rm b.tar.xz
  cd "$HERE"
fi
cd "$HERE"
if [ ! -f "$W/scene.blend" ]; then
  "$BL" -b --factory-startup -P scene.py -- --out "$W/scene.blend" --vo "$HERE/pack/vo" --fx "$HERE/pack/fx" > "$W/build.log" 2>&1
fi
LIST="$W/part_${A}_${B}.txt"; [ -f "$LIST" ] || seq "$A" "$B" | tr '\n' ' ' > "$LIST"
export SCALE=75 SAMPLES=7 RENDER_BUDGET=$((BUDGET - $(date +%s) + T0)); rc=0
"$BL" -b "$W/scene.blend" -P render_edl.py -- "$LIST" >> "$W/render.log" 2>&1 || rc=$?
[ $rc = 0 ] || [ $rc = 3 ] || { echo "render failed ($rc)"; tail -20 "$W/render.log"; exit $rc; }
# pack finished frames as JPEG (q95) into the repo and push
OUTJ="$HERE/frames_jpg"; mkdir -p "$OUTJ"
python3 - "$W/frames" "$OUTJ" <<'PY'
import sys, os
from PIL import Image
src, dst = sys.argv[1:]
for n in sorted(os.listdir(src)):
    if n.startswith('f_') and n.endswith('.png'):
        d = os.path.join(dst, n[:-4] + '.jpg')
        if not os.path.exists(d):
            Image.open(os.path.join(src, n)).convert('RGB').save(d, quality=95, subsampling=0)
PY
cd "$REPO"; git add commercial/final/frames_jpg; git commit -qm "The Final: frames $A-$B (partial)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PjJBqpRZSpPSQmrBC3LjLD" || true
for i in 1 2 3 4 5; do git pull -q --rebase origin claude/clash-final && git push -q origin HEAD:claude/clash-final && break; sleep $((i*5)); done
if [ $rc = 3 ]; then echo "RELAUNCH: $(grep -o 'BUDGET-STOP [0-9]*' "$W/render.log" | tail -1) frames left"; exit 3; fi
echo "WORKER-DONE $A-$B"
