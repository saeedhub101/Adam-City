# Middle East Open World — Unity project source

Unity game source for the Jordan and Palestine datasets stored under `middle east/`. No map API or external building service is used.

## Runtime implemented
- Third-person walk/run controller and follow camera.
- The default start point is Tabarbour, Amman, at 31.997579, 35.940358 (near Cobra Pharmacy).
- The starter scene copies and loads the existing Amman GLB tiles around the start point from `../BuildGLB/amman/`; no new geographic datasets are downloaded.
- glTFast loads the existing GLB meshes copied from the repository into `StreamingAssets/AmmanGLB/`.
- Repository-local OSM street chunks can be rendered as line overlays. Procedurally extruded OSM building fallback is disabled so it cannot be mistaken for real architecture.
- Jordan / Palestine region switching in the in-game overlay.
- Existing Amman GLB tiles load from local repository files around Tabarbour; their documented source origin is shifted to the game origin.
- A source-to-asset index workflow matches GLB building IDs and tile locations against original Jordan OSM records and records available source tags.
- Original compressed GeoJSON source archives remain untouched.

## Data source boundary
- `../Jordan/layers/`
- `../Palestine/layers/`

No data outside `middle east/` is used.

## Runtime data pipeline
The GitHub Actions workflow `.github/workflows/middle-east-world-data.yml` generates the chunked runtime data and publishes it as the `middle-east-unity-runtime-data` workflow artifact. The local generator is `tools/prepare_unity_data.py`; its outputs are `BuildData/Jordan/` and `BuildData/Palestine/`.

Open this folder as a Unity project (Unity 2022.3 LTS or newer). The editor bootstrap creates the Tabarbour starter scene and attempts to copy the existing nearby GLB tiles automatically. You can also run:
1. `MiddleEastWorld > Install Existing Tabarbour GLB Tiles`
2. `MiddleEastWorld > Install Generated Region Data` (only if the repository already contains `BuildData/`)
3. `MiddleEastWorld > Create Playable Open World Scene`
4. Open `Assets/MiddleEastWorld/Scenes/MiddleEastOpenWorld.unity` and press Play.

Controls: WASD move, Left Shift run, hold right mouse button and move mouse to orbit camera. Use the on-screen buttons to switch region.

## Accuracy and offline-only policy

- Unity gameplay must use files already committed in this repository. No runtime web map, hosted tile service, external API, or external model URL is permitted.
- The existing `BuildGLB/amman` GLBs are loaded and displayed from local files; they were not disabled. Their geometry was generated from OSM footprints and the exporter added synthetic facade/window details. They are not photogrammetry and must not be described as scanned/photo-realistic buildings.
- The temporary safety floor is invisible and exists only to prevent the player falling while testing movement. It is not a terrain representation.
- The repository contains many GLBs and imagery for other areas, but the checked Middle East asset tree contains no local georeferenced facade-photo set or city-scale photogrammetry texture package for Tabarbour. Manila/Ermita imagery must not be attached to Amman buildings. LiDAR catalog JSON pages are discovery metadata, not downloaded point-cloud files.
- `tools/build_glb_building_index.py` and `.github/workflows/index-amman-glb-buildings.yml` now generate a local source-matched index by OSM ID, tile, and coordinate, including original height/material/roof tags where present. This improves exact building matching; it does not itself change mesh appearance.
- True photographic realism cannot be fabricated from footprints or LiDAR catalogue records. Only apply image textures when a matching, locally stored, correctly georeferenced photo or scan is verified. Do not invent window patterns, facade colors, or building details.
- Only add a building/terrain mesh after verifying that its original source is a real scan/orthophoto, its license permits project use, and its geographic transform is documented.
- Movement: WASD; hold Left Shift to run; hold right mouse button and move mouse to orbit the camera.
- Build/runtime verification still requires opening the project in Unity 2022.3 LTS; Unity Editor and a player build have not been run here.
