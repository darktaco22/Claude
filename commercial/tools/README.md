# Render toolkit (free tools picked up from professional Blender workflows)

Everything here works headless in Blender 4.2 and was tested in this environment. Large downloads are not in git;
`polyhaven.py` fetches them again on demand (a few seconds each).

| File | What it gives | Source / licence |
|---|---|---|
| `shake_data.py`, `shakify.py` | Real recorded handheld camera shake (9 recordings). `shakify.apply(cam, 'INVESTIGATION', frame)` | Camera Shakify by Ian Hubert and Nathan Vegdahl; shake data is CC0. The add-on itself needs Blender 4.4, so `shakify.py` reads the data directly. |
| `polyhaven.py` | Download and load photo-scanned models, HDRI skies and ground materials. `pick()` filters the variants. | Poly Haven, all CC0 |
| `scatter.py` | Geometry-nodes scatter of instances over a surface (grass, flowers, rocks) | own code |
| `demo.py` | One-still proof: `blender -b -P demo.py -- ASSET_DIR out.png` | |

## Assets tested
`grass_bermuda_01`, `grass_medium_01`, `dandelion_01`, `searsia_lucida` (South African bush), `namaqualand_boulder_02`,
material `aerial_grass_rock`, HDRI `kloppenheim_06_puresky` (sunset, clear horizon). List more with
`python3 polyhaven.py DEST list models nature` or `list hdris sunrise-sunset`.

Notes: Poly Haven models are real-world scale (grass 5–30 cm), so scale them for the toy-sized arena. Each file holds
every variant and three detail levels; always go through `pick()`. Files named `*_geometry_nodes` are preview spheres.

## Reachable from this environment
github.com, api.polyhaven.com / dl.polyhaven.org, extensions.blender.org, download.blender.org.

## Not reachable (would need the hosts allowed in the environment's network settings)
Free CC0 fire/smoke/explosion VDB volumes: jangafx.com (EmberGen free VDBs), cgheven.com. These are the proper fix
for ball-like fire puffs. Also studio.blender.org and projects.blender.org (Blender Studio film files and tools).

## Looked at and not adopted
- Compify (Ian Hubert / Nathan Vegdahl): for compositing onto filmed footage; we have none.
- Most camera/lighting add-ons on extensions.blender.org are viewport UI helpers and add nothing to scripted renders.
