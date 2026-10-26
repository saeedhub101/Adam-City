# Middle East Open World — Unity project source

Unity game source for the Jordan and Palestine datasets stored under `middle east/`. No map API or external building service is used.

## Runtime implemented
- Third-person walk/run controller and follow camera.
- The default start point is Tabarbour, Amman, at 31.997579, 35.940358 (near Cobra Pharmacy).
- The starter scene copies and loads the existing Amman GLB tiles around the start point from `../BuildGLB/amman/`; no new geographic datasets are downloaded.
- glTFast loads those existing GLB meshes, and the OSM runtime renderer supplies streets and distant fallback buildings where chunk data is installed.
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

## Accuracy boundary
The existing Amman GLBs contain detailed generated meshes, facade/window geometry and streets, but the GLB generation script constructs these from OSM footprints and tags. They are not photogrammetry scans, and should not be described as fully real photographed buildings. The nearby GLB mesh is now the preferred geometry around the Tabarbour start point; the broader Jordan/Palestine coverage still needs existing GLB tile sets and runtime data installed/connected. A Unity Editor compile, Play-mode test and standalone player build have not yet been run in this environment, so a finished tested game build is not claimed.
