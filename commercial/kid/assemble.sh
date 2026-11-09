#!/bin/bash
# assemble.sh FRAMES OVERLAYS AUDIO OUT.mp4 — upscale Cycles frames to 1080x1920, lay the HTML overlays on top, add the mix.
set -e
F=$1; O=$2; A=$3; OUT=$4
ffmpeg -v error -y -framerate 30 -i "$F/f_%04d.png" -framerate 30 -i "$O/o_%04d.png" -i "$A" \
  -filter_complex "[0:v]scale=1080:1920:flags=lanczos,unsharp=5:5:0.45:5:5:0,format=rgba[bg];[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v];[2:a]atrim=0:30.8[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -t 30.8 "$OUT"
ffprobe -v error -show_entries stream=codec_type,width,height,nb_frames -show_entries format=duration,size -of compact "$OUT"
