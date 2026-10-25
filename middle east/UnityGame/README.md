# Middle East Open World — Unity project source

Unity game source for the Jordan and Palestine datasets stored under `middle east/`. No map API or external building service is used.

## Runtime implemented
- Third-person walk/run controller and follow camera.
- Jordan / Palestine region switching in the in-game overlay.
- Spatially chunked OSM building and street data, loaded around the player as they move.
- Building footprints extruded to recorded heights, mapped material hints, road classes, and street-name labels.
- Ear-clipped footprint triangulation for concave building polygons.
- Original compressed GeoJSON source archives remain untouched.

## Data source boundary
- `../Jordan/layers/`
- `../Palestine/layers/`

No data outside `middle east/` is used.

## Runtime data pipeline
The GitHub Actions workflow `.github/workflows/middle-east-world-data.yml` generates the chunked runtime data and publishes it as the `middle-east-unity-runtime-data` workflow artifact. The local generator is `tools/prepare_unity_data.py`; its outputs are `BuildData/Jordan/` and `BuildData/Palestine/`.

After runtime chunks are present in `BuildData/`, open this folder as a Unity project (Unity 2022.3 LTS or newer), then run:
1. `MiddleEastWorld > Install Generated Region Data`
2. `MiddleEastWorld > Create Playable Open World Scene`
3. Open `Assets/MiddleEastWorld/Scenes/MiddleEastOpenWorld.unity` and press Play.

Controls: WASD move, Left Shift run, hold right mouse button and move mouse to orbit camera. Use the on-screen buttons to switch region.

## Accuracy boundary
The available OSM data provides mapped footprints, some height/floor tags, roads, and names. It does not provide true photographic facades, exact windows, shop signage, or interior models for every building. The current renderer builds a playable geographic prototype from the available data; it is not yet a photorealistic reconstruction and this source repository does not contain a completed, tested Unity player build.
