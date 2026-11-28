#!/usr/bin/env python3
"""Fetch the open-licensed assets used by THE MEMETRIX III into $W/ext3 (not committed; see ASSETS.md).

    python3 fetch_assets.py [set ...]        sets: farm maglev shrine docks exchange desert street bots sound hdri  (default: all)

Sources (all public, fetched over raw.githubusercontent.com / the Poly Haven API):
  - Polygonal Mind CC0 collections   github.com/ToxSam/cc0-models-Polygonal-Mind  (GLB)
  - Quaternius Modular Sci-Fi (CC0)  github.com/Malcolmnixon/Quaternius-Modular-Scifi-Pack  (.blend)
  - Poly Haven (CC0)                 api.polyhaven.com  (glTF 1k models, HDRIs)
  - Oculus Audio Pack 01 (CC BY 4.0) github.com/facebookincubator/Meta-open-sound  (OGG)
Already-downloaded files are skipped, so re-running is cheap.
"""
import json, os, sys, urllib.request, urllib.parse

W = os.environ.get('W', os.path.expanduser('~/mx_work'))
OUT = os.path.join(W, 'ext3')
RAW = 'https://raw.githubusercontent.com'
PM = RAW + '/ToxSam/cc0-models-Polygonal-Mind/main/projects/'
QT = RAW + '/Malcolmnixon/Quaternius-Modular-Scifi-Pack/main/addons/quaternius-modular-scifi-pack/blender/'
SND = RAW + '/facebookincubator/Meta-open-sound/main/corpora/oculus-audio-pack/ogg/'

# Polygonal Mind: folder -> model names (GLB)
PM_SETS = {
    'shrine': ('tomb-chaser-2', ['Ad01_Art', 'Ad02_Art', 'Ad03_Art', 'Ad04_Art', 'Ad05_Art', 'Ad06_Art', 'Column01_Art',
               'Column02_Art', 'Decoration01_Art', 'ElectricBox01_Art', 'ElectricPost01_Art', 'ElectricPost02_Art',
               'ElectricWire01_Art', 'ElectricWire02_Art', 'Floor01_Art', 'Floor02_Art', 'GlitchFloor_Art', 'GlitchRoof_Art',
               'Mist01_Art', 'Mist02_Art', 'Reed_Art', 'Rock01_Art', 'Rock02_Art', 'Shrine_Art', 'TempleBaseCorner_Art',
               'TempleBaseDetail01_Art', 'TempleBaseDetail02_Art', 'TempleBaseStaircase_Art', 'TempleBase_Art',
               'TempleBeam01_Art', 'TempleBeam02_Art', 'TempleColumn_Art', 'TempleRoof01Corner_Art', 'Cyber_Surroundings_01']),
    'maglev': ('transit', ['Tower_Station_01_Art', 'Tower_Station_Elevator_Art', 'Tower_Station_Fence_Art',
               'Tower_Station_Light_Art', 'Tower_Station_Sign_Art', 'Tower_Station_Telephone_Art', 'Iron_Structure_01_Art',
               'Train_Track_01', 'Track_01_Tap_Art', 'Platform_01_Art', 'Bench_01', 'Plant_01_Art', 'Plant_02_Art']),
    'docks': ('aero-system', ['Aero_Airship_01', 'Aero_Door_01', 'Aero_Ground_Hexagon_Art', 'Aero_Ground_Hexagons_01_Art',
              'Aero_Ground_Hexagons_02_Art', 'Aero_Lampost_01', 'Aero_Station_01_Art', 'Aero_Station_Mini_Platform_Art',
              'Aero_Station_PinkRing_Art', 'Aero_Station_Ring_Art', 'Aero_Station_YellowRing_Art', 'Floating_Island_01_Art',
              'Path_01_Art', 'Terrain_Art', 'Tree_01_Art']),
    'desert': ('crystal-crossroads', ['Arc', 'Column_Regular', 'Column_SmallBroken_01', 'Crystal_Base', 'Crystal_Cluster',
               'Crystal_ClusterSurrounded', 'Crystal_Small_01', 'Crystal_Small_02', 'Crystal_Small_03', 'Crystal_Small_04',
               'Dune_Sand', 'Floor_Sand_Large', 'Floor_Tiles_Large', 'Floor_Tiles_Medium', 'Platform_03',
               'Platform_StairsPlatform', 'Platform_Stairs_01', 'Platform_Stairs_02', 'Pattern_Cube', 'Pattern_Cylinder',
               'Pattern_Solar']),
    'bots': ('xyz', ['003_Hexabear_Art', '011_Rectashark_Art', '026_Tribird_Art', '020_Octozilla_Art', '002_Squaresquid_Art',
             '010_Rhombolion_Art', '030_Crabylon_Art', '016_Raptorous_Art']),
}

# Quaternius Modular Sci-Fi (.blend, CC0): the Exchange
QT_FILES = ['Column_1', 'Column_2', 'Column_3', 'Column_Slim', 'Staircase', 'Door_Double', 'FloorTile_Basic',
            'FloorTile_Basic2', 'FloorTile_Side', 'FloorTile_Corner', 'RoofTile_Pipes1', 'RoofTile_Vents', 'RoofTile_Details',
            'Props_Computer', 'Props_ComputerSmall', 'Props_Pod', 'Props_Teleporter_1', 'Props_Vessel_Tall', 'Props_Statue',
            'Props_ContainerFull', 'Props_Crate', 'Props_Shelf_Tall', 'Details/Details_Pipes_Long', 'Details/Details_Vent_4',
            'Details/Details_Plate_Details', 'Details/Details_Output', 'Details/Details_Hexagon', 'Walls/Wall_1', 'Walls/Wall_2',
            'Walls/Wall_3', 'Walls/Wall_4', 'Walls/Wall_5', 'Walls/Window_Wall_SideA']

# Poly Haven (CC0): glTF models at 1k textures
PH_SETS = {
    'farm': ['flood_lights', 'overhead_crane', 'portable_generator', 'tool_cart', 'steel_frame_shelves_01',
             'steel_frame_shelves_02', 'modular_airduct_rectangular_01', 'modular_airduct_circular_01', 'mounted_fluorescent_lights',
             'industrial_storage_cart', 'metal_office_desk', 'circuit_board', 'modular_electric_cables', 'hanging_industrial_lamp',
             'power_box_01', 'metal_tool_chest', 'plastic_crate_01', 'old_military_crate', 'propane_tank', 'industrial_pipe_lamp',
             'modular_industrial_pipes_01', 'security_camera_01', 'gaming_console', 'classic_laptop', 'folding_wooden_stool'],
    'street': ['street_lamp_01', 'street_lamp_02', 'fire_hydrant', 'korean_public_payphone_01', 'concrete_road_barrier',
               'trashbag', 'water_manhole_cover', 'modular_street_seating', 'metal_trash_can', 'utility_box_01',
               'utility_box_02', 'exterior_aircon_unit', 'rollershutter_door', 'rollershutter_window_01',
               'modular_urban_apartments_facade', 'modular_fire_escape', 'modular_electricity_poles', 'security_light',
               'street_rat', 'covered_car'],
}
HDRIS = {'hdri': ['kloppenheim_06', 'golden_bay', 'cobblestone_street_night', 'abandoned_factory_canteen_01',
                  'industrial_sunset_02_puresky', 'qwantani_dusk_2_puresky', 'goegap_road', 'dikhololo_night']}

# Oculus Audio Pack 01 (CC BY 4.0)
SOUNDS = ['FGHTImpt_Kick_OS_0%d' % i for i in range(1, 6)] + ['FGHTImpt_PunchHarder_OS_0%d' % i for i in range(1, 5)] + \
    ['FGHTImpt_PunchHardest_OS_01'] + ['FGHTImpt_PunchRegular_OS_0%d' % i for i in range(1, 7)] + \
    ['SWSH_Swoosh_OS_0%d' % i for i in range(1, 7)] + \
    ['GLASBrk_GlassBottleBreak_OS_01', 'GLASBrk_WindowPaneSmallBreak_OS_01', 'LASRGun_LaserShootUI_OS_01',
     'LASRGun_LaserShootUI_OS_02', 'TRNDoor_TrainDoorsClose_OS_01', 'TRNDoor_TrainDoorsOpen_OS_01', 'TRNElec_TrainPassby_OS_01',
     'TRNSbwy_SubwayPassbyEnter_OS_01', 'TRNSbwy_SubwayPassbyExit_OS_01', 'DSGNDron_DroneCreepy_OS_01', 'DSGNDron_DroneCreepy_OS_02',
     'DSGNImpt_ImpactCreepyReverb_OS_01', 'DSGNImpt_ImpactCreepyReverb_OS_02', 'DSGNImpt_ImpactCreepyReverb_OS_03',
     'CREAHmn_GiantLaugh_OS_01', 'CREAHmn_GiantLaugh_OS_02', 'CREAHmn_GiantEffort_OS_01',
     'METLImpt_MetalHitSurface_OS_01', 'METLImpt_MetalHitSurface_OS_02', 'METLImpt_MetalHitSurface_OS_03',
     'METLImpt_MetalObjDrop_OS_01', 'METLImpt_MetalObjDrop_OS_02', 'MECHLvr_LeverPull_OS_01', 'MECHLock_DoorUnlockKey_OS_01',
     'UIAlert_ScifiHightechError_OS_01', 'UIClick_ScifiHightechConfirm_OS_01', 'UIData_ScifiCountup_LOOP_01', 'UIMisc_Powerup_OS_01',
     'AMBInd_RoomToneMachineRoom_LOOP_01', 'AMBUrbn_CityAmerican_LOOP_01', 'CLOTHFlp_FlagFlapping_LOOP_01', 'CRWDConv_Restaurant_LOOP_01']


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'memetrix-asset-fetch'})
    with urllib.request.urlopen(req, timeout=120) as r, open(path + '.part', 'wb') as f:
        f.write(r.read())
    os.replace(path + '.part', path)
    return True


def ph_model(name):
    files = json.load(urllib.request.urlopen('https://api.polyhaven.com/files/' + name, timeout=60))
    g = files['gltf']['1k']['gltf']
    d = os.path.join(OUT, 'polyhaven', name)
    get(g['url'], os.path.join(d, os.path.basename(g['url'])))
    for rel, inc in g.get('include', {}).items():
        get(inc['url'], os.path.join(d, rel))


def ph_hdri(name):
    files = json.load(urllib.request.urlopen('https://api.polyhaven.com/files/' + name, timeout=60))
    h = files['hdri']['2k']['hdr']
    get(h['url'], os.path.join(OUT, 'hdri', name + '_2k.hdr'))


def main(sets):
    n = 0
    for s in sets:
        try:
            if s in PM_SETS:
                folder, names = PM_SETS[s]
                for nm in names:
                    n += get(PM + folder + '/' + urllib.parse.quote(nm) + '.glb', os.path.join(OUT, 'pm', folder, nm + '.glb'))
            elif s == 'exchange':
                for nm in QT_FILES:
                    n += get(QT + nm + '.blend', os.path.join(OUT, 'quaternius', nm.split('/')[-1] + '.blend'))
            elif s in PH_SETS:
                for nm in PH_SETS[s]:
                    ph_model(nm); n += 1
            elif s == 'hdri':
                for nm in HDRIS['hdri']:
                    ph_hdri(nm); n += 1
            elif s == 'sound':
                for nm in SOUNDS:
                    n += get(SND + nm + '.ogg', os.path.join(OUT, 'sound', nm + '.ogg'))
            print('OK', s, flush=True)
        except Exception as e:                     # keep going; report what failed
            print('FAIL', s, repr(e), flush=True)
    print('fetched', n, 'into', OUT)


if __name__ == '__main__':
    main(sys.argv[1:] or ['farm', 'maglev', 'shrine', 'docks', 'exchange', 'desert', 'street', 'bots', 'sound', 'hdri'])
