#!/bin/bash
# After all frames exist in $W/frames (.png) or frames_jpg/ (.jpg): finish, mix and encode DEPLOYED.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export W=${W:-$HOME/dep_work}; cd "$HERE"; EH=$(sha1sum edl.json | cut -c1-10); FR="$W/final_$EH"; rm -rf "$FR"; mkdir -p "$FR"
cp frames_jpg/$EH/*.jpg "$FR/" 2>/dev/null || true; cp "$W/frames_$EH"/*.png "$FR/" 2>/dev/null || true
N=$(python3 -c "import json;print(json.load(open('edl.json'))['last'])")
for f in $(seq 1 "$N"); do p=$(printf %04d "$f"); [ -f "$FR/f_$p.png" ] || [ -f "$FR/f_$p.jpg" ] || { echo "FRAME MISSING $f"; exit 1; }; done
rm -rf "$W/fin"; python3 finish.py "$FR" "$W/fin" pack/vo > "$W/finish.log" 2>&1
O="$HERE/../output/meme-royale-deployed.mp4"
ffmpeg -v error -y -framerate 24 -i "$W/fin/c_%04d.jpg" -i "$W/fin/mix.wav" -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 \
  -c:v libx264 -preset slow -b:v 4300k -maxrate 7000k -bufsize 12000k -pix_fmt yuv420p -c:a aac -b:a 160k -shortest -movflags +faststart "$O"
ls -la "$O"; tail -6 "$W/finish.log"; echo ALL-DONE
