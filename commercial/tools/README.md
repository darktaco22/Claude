# Render toolkit (free tools picked up from professional Blender workflows)

Everything here works headless in Blender 4.2 and was tested in this environment. Large downloads are not in git;
`polyhaven.py` fetches them again on demand (a few seconds each).

| File | What it gives | Source / licence |
|---|---|---|
| `shake_data.py`, `shakify.py` | Real recorded handheld camera shake (9 recordings). `shakify.apply(cam, 'INVESTIGATION', frame)` | Camera Shakify by Ian Hubert and Nathan Vegdahl; shake data is CC0. The add-on itself needs Blender 4.4, so `shakify.py` reads the data directly. |
| `polyhaven.py` | Download and load photo-scanned models, HDRI skies and ground materials. `pick()` filters the variants. | Poly Haven, all CC0 |
| `scatter.py` | Geometry-nodes scatter of instances over a surface (grass, flowers, rocks) | own code |
| `fire.py` | Mantaflow fire/smoke bake to OpenVDB. Pipeline works; look still needs tuning (see playbook) | Blender built-in |
| `vdb.py` | Loads downloaded fire/smoke/cloud volumes with a ready material. Tested with CGHeven CampFire 02: real flame shapes (`demo_fire.jpg`) | CGHeven free library and JangaFX packs, both CC0 |
| `lightrig.py` | Key / key-soft / fill / rim rig around a subject relative to the camera, shared colour sets per mood, eye catch-light | after Blender Studio's lighting guide |
| `fxcard.py` | Stock explosion/smoke footage on a camera-facing card, with an optional light so the scene reacts | clips: CGHeven (CC0) |
| `lab.py` | Integration test: game character + scanned field + sky + rig + explosion (`demo_lab.jpg`: sky only / rig / explosion) | |
| `pipeline.py`, `pipeline_test.py` | Pipeline automation: link sets from a JSON description, mass-rename objects, prefix bones + vertex groups, shift/retime/sample F-curves, batch-render a folder of models with cleanup and resume. 15 tests pass (`blender -b -P pipeline_test.py`) | after Blender Studio's Scripting for Artists course |
| `demo.py` | One-still proof: `blender -b -P demo.py -- ASSET_DIR out.png` | |

## Assets tested
`grass_bermuda_01`, `grass_medium_01`, `dandelion_01`, `searsia_lucida` (South African bush), `namaqualand_boulder_02`,
material `aerial_grass_rock`, HDRI `kloppenheim_06_puresky` (sunset, clear horizon). List more with
`python3 polyhaven.py DEST list models nature` or `list hdris sunrise-sunset`.

Notes: Poly Haven models are real-world scale (grass 5–30 cm), so scale them for the toy-sized arena. Each file holds
every variant and three detail levels; always go through `pick()`. Files named `*_geometry_nodes` are preview spheres.

## Reachable from this environment
github.com, api.polyhaven.com / dl.polyhaven.org, extensions.blender.org, download.blender.org, cgheven.com +
cdn.cgheven.com, jangafx.com, studio.blender.org, projects.blender.org, ambientcg.com.

## Volume downloads: mind the disk
- CGHeven: open `https://cgheven.com/assets/<name>`; the page source holds direct `cdn.cgheven.com` links. Free
  items say `"license":"CC0"`; links starting `cgh-protected://` are paid. VDB list: `/category/vdbs` (campfire,
  smoke shockwaves, hero clouds). `.rar` files: `apt-get install -y unar` then `unar file.rar`.
- CGHeven footage (explosions, smoke plumes): each asset page lists 1K/2K H.264 clips of a few MB on black. The
  1K aerial explosion is 4 MB, 120 frames at 60 fps. Smoke shockwave VDB is 5 GB: too big for this disk.
- **Sizes on the page are wrong.** CampFire_02_VDB.zip is 1.9 GB and unpacks to 9.4 GB (200 frames of ~47 MB). It
  filled the disk once. Check `Content-Length` first, extract only the frames needed (`unzip zip name_060.vdb`), and
  delete the zip.
- JangaFX packs (CC0, 59 MB to 6.6 GB) are hosted on MediaFire, whose download servers change name, so they cannot
  be reached with an exact-host allowlist.

## Looked at and not adopted
- Compify (Ian Hubert / Nathan Vegdahl): for compositing onto filmed footage; we have none.
- Most camera/lighting add-ons on extensions.blender.org are viewport UI helpers and add nothing to scripted renders.
