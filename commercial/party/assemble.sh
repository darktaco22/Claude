#!/usr/bin/env bash
# frames (960x540 PNG) + party_mix.wav -> the final 1280x720 MP4 with the closing logo card
set -euo pipefail
FR=${1:?frames dir}; MIX=${2:?mix wav}; LOGO=${3:?logo png}; FONT=${4:?font ttf}; OUT=${5:?out mp4}
T0=27.2   # the card comes in here (s)
ffmpeg -nostdin -loglevel error -y -framerate 30 -i "$FR/f_%04d.png" -loop 1 -i "$LOGO" -i "$MIX" -filter_complex "
[0:v]scale=1280:720:flags=lanczos,format=yuv420p[v];
[v]drawbox=x=0:y=0:w=iw:h=ih:color=0x1A0846@0.55:t=fill:enable='gte(t,$T0)'[d];
[1:v]scale=520:-1,format=rgba,fade=t=in:st=$T0:d=0.35:alpha=1[l];
[d][l]overlay=x=(W-w)/2:y=70:enable='gte(t,$T0)'[o];
[o]drawtext=fontfile=$FONT:text='COMING SOON TO THE SOLANA dAPP STORE':fontsize=46:fontcolor=0xFFC52E:borderw=4:bordercolor=0x1A0846:x=(w-tw)/2:y=600:enable='gte(t,$T0+0.3)'[t1];
[t1]drawtext=fontfile=$FONT:text='memeroyale.imaginestudio.fun':fontsize=28:fontcolor=0xF1E8FF:borderw=3:bordercolor=0x1A0846:x=(w-tw)/2:y=660:enable='gte(t,$T0+0.6)'[t2];
[t2]drawtext=fontfile=$FONT:text='Music\: Cut and Run by Kevin MacLeod (incompetech.com), CC BY 4.0':fontsize=15:fontcolor=0xD8D0F0:x=(w-tw)/2:y=700:enable='gte(t,$T0+0.6)'[out]" \
  -map "[out]" -map 2:a -c:v libx264 -preset slow -crf 16 -tune animation -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -shortest "$OUT"
echo "wrote $OUT"
