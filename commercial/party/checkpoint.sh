#!/usr/bin/env bash
# Glitch checkpoint: build the scene, save party.blend, render scene stills, then isolated close-ups of every guest.
#   ./checkpoint.sh WORKDIR OUTDIR [stills frames]
set -u
W=${1:?work dir}; O=${2:?out dir}; FR=${3:-180,230,300,345,395,520,600,700,760,800}; mkdir -p "$O"; cd "$(dirname "$0")"
BL=${BLENDER:-blender}
"$BL" -b --factory-startup -P party.py -- --models "$W/models" --ph "$W/ph" --cmu "$W/cmu" --w 1280 --h 720 --samples 12 --save "$W/party.blend" --stills "$FR" "$O" > "$O/build.log" 2>&1
NAMES="useless,chillguy,jeanphil,lmao,chillhouse,mensa,troll,ket,zcat,cupsey,cate,triplet,baton,mitch,alon,whale,pepe,bonk,giga,swordcat,wojak,thisisfine,pnut,nyancat,dope,moodeng,popcat,floki,toshi,slerf,michi,pippin,pudgy,bome,apu,walter,goat,farter,neet,brett,npcwojak,pinkwojak,doge,wif,fwog"
"$BL" -b "$W/party.blend" -P qa.py -- --qa "$NAMES" --qf 150,450,750 --qo "$O" > "$O/qa.log" 2>&1
echo DONE > "$O/DONE"
