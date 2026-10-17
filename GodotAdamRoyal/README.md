# Adam Royal — Godot city build

This is the Godot 4 implementation being developed on branch `godot-city-conversion`. It does not overwrite the Unreal project on `main`.

## Real city source

The playable district is central Manila (Intramuros / Ermita / the southern Binondo edge), using real OpenStreetMap building footprints and road ways. The build workflow downloads current geometry and generates `assets/manila_city.json` before importing and exporting the game. No API key is required for the Overpass download, but public endpoints may throttle requests.

OpenStreetMap attribution: © OpenStreetMap contributors — https://www.openstreetmap.org/copyright

## Controls

- WASD: move
- Mouse: look
- Space: jump
- Escape: release mouse; click to recapture

## Build

GitHub Actions workflow: `.github/workflows/build-godot-adam-royal.yml`

It downloads Godot 4.4.1 and its Windows export templates, fetches the city dataset, validates that the dataset has at least 100 buildings and 30 road ways, runs a headless project startup check, exports `AdamRoyal.exe`, and uploads the output as a workflow artifact.

## Important realism boundary

The current city builder uses real map geometry but extrudes footprints into simplified building masses. It is a real-world street layout, not yet photogrammetric imagery or photorealistic facade capture. Realistic facade textures, vehicles, and human character assets remain production tasks and must be sourced with redistribution rights.
