#!/usr/bin/env bash
# Re-creates everything the party build reads from outside the repo (a fresh container has none of it).
#   ./setup_assets.sh WORKDIR        (e.g. /tmp/party-work)   -> WORKDIR/{models,ph,cmu,music,audio,cards}
set -euo pipefail
W=${1:?work dir}; mkdir -p "$W"/{models,ph/tex,music,audio,cards}; cd "$W"
UA="party-scene-builder/1.0"; SITE=https://memeroyale.imaginestudio.fun
# 1. the game's 39 character models (and logo) from the live site
for id in useless chillguy jeanphil lmao chillhouse mensa troll ket zcat cupsey cate triplet baton mitch alon whale neet bonk dope swordcat popcat wojak pnut pepe moodeng giga thisisfine nyancat floki toshi slerf michi pippin pudgy bome apu walter goat farter; do
  [ -s models/$id.glb ] || curl -sSf -A "$UA" -o models/$id.glb "$SITE/assets/units/$id.glb"
  [ -s cards/$id.png ] || { curl -sSf -A "$UA" -o cards/$id.webp "$SITE/assets/cards/$id.webp?v=2" && ffmpeg -nostdin -loglevel error -y -i cards/$id.webp cards/$id.png && rm cards/$id.webp; }
done
cp "$(dirname "$0")/../assets/logo.png" logo.png
# 2. Poly Haven (CC0): night sky, city HDRI, furniture, plants, trees, PBR textures
python3 - <<'PY'
import json, urllib.request, os
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'party-scene-builder/1.0'}), timeout=180) as r: return r.read()
for h, res in (('kloppenheim_02_puresky', '2k'), ('shanghai_bund', '4k')):
    p = f'ph/{h}_{res}.hdr'
    if not os.path.exists(p): open(p, 'wb').write(get(json.loads(get(f'https://api.polyhaven.com/files/{h}'))['hdri'][res]['hdr']['url']))
for i in ['sofa_03','modern_coffee_table_01','mid_century_lounge_chair','bar_chair_round_01','potted_plant_01','potted_plant_02','modern_ceiling_lamp_01',
          'jacaranda_tree','quiver_tree_02','shrub_02','shrub_03','shrub_04','fern_02','potted_plant_04','wine_bottles_01','street_lamp_02','planter_box_02']:
    if os.path.exists(f'ph/{i}/{i}.gltf'): continue
    g = json.loads(get(f'https://api.polyhaven.com/files/{i}'))['gltf']['1k']['gltf']; os.makedirs(f'ph/{i}', exist_ok=True)
    open(f'ph/{i}/{i}.gltf', 'wb').write(get(g['url']))
    for rel, info in g.get('include', {}).items():
        q = os.path.join('ph', i, rel); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(get(info['url']))
tex = {'rectangular_paving':'2k','blue_floor_tiles_01':'1k','leafy_grass':'2k','plastered_wall_04':'2k','painted_plaster_wall':'1k','rustic_stone_wall_02':'2k',
       'herringbone_parquet':'2k','marble_01':'1k','oak_veneer_01':'1k','bark_brown_02':'1k','palm_tree_bark':'1k','gravel_floor_02':'1k','black_oak_veneer':'1k',
       'quatrefoil_jacquard_fabric':'1k','concrete_floor_02':'1k','metal_plate':'1k'}
for t, res in tex.items():
    if os.path.isdir(f'ph/tex/{t}'): continue
    f = json.loads(get(f'https://api.polyhaven.com/files/{t}')); os.makedirs(f'ph/tex/{t}', exist_ok=True)
    for key, out in (('Diffuse', 'diff'), ('nor_gl', 'nor'), ('Rough', 'rough')):
        if key in f: open(f'ph/tex/{t}/{out}.jpg', 'wb').write(get(f[key][res]['jpg']['url']))
PY
# 3. CMU motion capture (cgspeed's BVH conversion, free for any use), only the clips the party uses
if [ ! -d cmu ]; then GIT_LFS_SKIP_SMUDGE=1 git clone -q --filter=blob:none --no-checkout --depth 1 https://github.com/una-dinosauria/cmu-mocap cmu; fi
( cd cmu; P=""; for c in 113_04 111_05 60_01 18_15 93_08 90_32 120_21 85_14 90_30 55_02 79_33 80_29 13_09 13_14 91_09 141_12 120_05; do s=${c%_*}; P="$P data/$(printf %03d $((10#$s)))/$c.bvh"; done; git checkout -q HEAD -- $P )
# 4. music (Kevin MacLeod, incompetech.com, CC BY 4.0) and the game's sound effects
[ -s "music/Cut and Run.mp3" ] || curl -sSf -A "$UA" -o "music/Cut and Run.mp3" "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Cut%20and%20Run.mp3"
python3 - <<'PY'
import json, urllib.request, os
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'party-scene-builder/1.0'}), timeout=60).read()
m = json.loads(get('https://memeroyale.imaginestudio.fun/assets/audio/manifest.json'))
for k in ['amb_beach','crowd_cheer','crowd_laugh','crowd_ooh','laugh_blast','coins','coin_jingle','fart_cast','fart_cloud']:
    for f in (m[k].get('variants') or [m[k]['file']])[:2]:
        if not os.path.exists('audio/' + f): open('audio/' + f, 'wb').write(get('https://memeroyale.imaginestudio.fun/assets/audio/' + f))
PY
echo "assets ready in $W"
