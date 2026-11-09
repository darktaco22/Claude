#!/bin/bash
# The gameplay clips on the phones, cut from the game's own engine footage (commercial/output/meme-royale-seeker-blender.mp4),
# cropped to 9:16 below the old captions, with the card name in the game's font. Usage: ./screens.sh OUTDIR
set -e; HERE=$(cd $(dirname $0) && pwd); V=$HERE/../output/meme-royale-seeker-blender.mp4; F=$HERE/../assets/lilita.ttf; O=$1
for c in "rug 6.0 2.6 RUG_PULL! 0xff4a6a" "battle 8.6 2.4 none 0" "candle 3.0 2.6 GOD_CANDLE! 0x66ff8a"; do set -- $c
  rm -rf $O/scr_$1; mkdir -p $O/scr_$1; T=$(echo $4 | tr _ ' '); DT=""
  [ "$4" != none ] && DT=",drawtext=fontfile=$F:text='$T':fontsize=54:fontcolor=$5:borderw=6:bordercolor=black:x=(w-tw)/2:y=46"
  ffmpeg -v error -y -ss $2 -t $3 -i $V -vf "fps=30,crop=ih*0.72*9/16:ih*0.72:(iw-ih*0.72*9/16)/2:ih*0.27,scale=360:640$DT" $O/scr_$1/%04d.png
done
