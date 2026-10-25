# Unity Middle East World — runtime foundation

This folder is the Unity game implementation source for the repository's existing **middle east** data only. It does not pull from other repository areas and does not require an API key.

## Data boundary
- Jordan inputs: `../Jordan/layers/`
- Palestine inputs: `../Palestine/layers/`
- Source data stays in those folders and is never overwritten.
- Generated runtime data belongs under `BuildData/Jordan/` and `BuildData/Palestine/`.
- Keep each region separate; do not merge source records across regions.

## What is implemented here
- Unity runtime scene bootstrap and third-person character controller.
- Local JSON/GZip feature reader for the prepared per-region data.
- Procedural building footprints with height/floor fallback, street ribbons and labels.
- Deterministic local-coordinate projection from WGS84 lon/lat to Unity metres.
- A preprocessing script that reads the repository's existing compressed GeoJSON layers and creates Unity-friendly region JSON without external packages.

## Reality and data quality
The repository contains extensive OSM-derived geometry and some height/floor metadata, but OSM does **not** contain true façade photographs, exact window layouts, shop-sign photographs or interior geometry for every building. The runtime therefore uses mapped footprints, recorded heights and region-appropriate materials where available; it must not pretend procedural façades are literal photographic reconstructions. Photogrammetry / legally usable façade imagery must be added per landmark when verified.

## Build steps
1. Run `python tools/prepare_unity_data.py` from this directory with Python 3.9+.
2. Copy this folder into a Unity 2022.3 LTS or newer project as `Assets/MiddleEastWorld`.
3. Open the included scene-setup instructions and run `MiddleEastWorld > Create Demo Scene` in the Unity Editor.
4. Select Jordan or Palestine from the runtime region selector.

No Unity editor is available in this repository action, so an actual Unity player build cannot be claimed until Unity's editor/build runner executes the project.
