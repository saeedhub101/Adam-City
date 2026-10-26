# Middle East Open World — Unity project source

Unity game source for the Jordan and Palestine datasets stored under `middle east/`. No map API or external building service is used.

## Runtime implemented
- Third-person walk/run controller and follow camera.
- The default start point is Tabarbour, Amman, at 31.997579, 35.940358 (near Cobra Pharmacy).
- The starter scene copies and loads the existing Amman GLB tiles around the start point from `../BuildGLB/amman/`; no new geographic datasets are downloaded.
- glTFast loads the existing GLB meshes copied from the repository into `StreamingAssets/AmmanGLB/`.
- Repository-local OSM street chunks can be rendered as line overlays. Procedurally extruded OSM building fallback is disabled so it cannot be mistaken for real architecture.
- Jordan / Palestine region switching in the in-game overlay.
- Spatially chunked OSM building and street data, loaded around the player as they move.
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
- The existing `BuildGLB/amman` GLBs are still loaded and displayed; they have not been disabled. However, they were generated from OSM footprints and contain extruded masses plus procedurally generated facade/window details, so they are not photogrammetry and should not be described as photo-realistic scanned buildings.
- The temporary safety floor is invisible and exists only to prevent the player falling while testing movement. It is not a terrain representation.
- The repository contains many local GLBs and reference photos, but the current Tabarbour inventory does not establish a georeferenced aerial orthophoto or photogrammetric city mesh suitable for applying real building textures there. Reference photos must not be projected onto unrelated buildings without a verified match and transform.
- Improving these GLBs to true photographic realism requires verified local source imagery / scan textures mapped to the correct buildings. Do not invent window patterns, facade colors, or building details to simulate that evidence.
- Only add a building/terrain mesh after verifying that its original source is a real scan/orthophoto, its license permits project use, and its geographic transform is documented.
- Movement: WASD; hold Left Shift to run; hold right mouse button and move mouse to orbit the camera.
- Build/runtime verification still requires opening the project in Unity 2022.3 LTS; Unity Editor and a player build have not been run here.
