# Adam Royal

Adam Royal is the Windows 3D game prototype built with Godot 4.

## Included in the Windows build

- The central Manila district GLB, built from real OpenStreetMap road and building geometry and textured with procedural facade atlases.
- The existing 3D player character from `assets/saeed.glb`, staged as `assets/adam_royal_character.glb` during CI.
- Third-person camera, WASD movement, mouse look, jump, and an in-game city/source HUD.
- OpenStreetMap attribution: © OpenStreetMap contributors — https://www.openstreetmap.org/copyright

## Build and validation

The workflow `.github/workflows/build-godot-adam-royal.yml` reuses the committed Manila map GLB, report, facade atlases, and asphalt texture. It downloads OSM geometry only when the required cache is missing or incomplete, then commits the generated cache to `main`. It stages the cached GLB and actual player model, imports resources, runs the game headlessly, verifies that both GLBs load in the scene, exports `AdamRoyal.exe`, and uploads the executable and source assets as a workflow artifact.

Build logs are captured and printed on failure so Godot parser/import errors are visible instead of being replaced by a generic error.

## Controls

- WASD: move
- Mouse: look
- Space: jump
- Escape: release mouse; click to recapture

## Accuracy and current limits

The street layout and building footprints come from real mapped Manila geography. The current city GLB uses extruded building geometry, procedural facade atlases, and a procedural asphalt surface with approximate markings; it is **not** photogrammetry. Reference photographs are not yet projected onto their matching building meshes, so exact real-world facade and road appearance is not yet achieved. This build is a playable prototype, not a finished AAA-quality game. Cars, pedestrians, high-quality character animation, collision across the imported city, optimized LODs, and deeper gameplay systems still need implementation and testing.

The city source is OpenStreetMap under ODbL 1.0. Retain attribution and verify redistribution rights for any third-party character or image assets before commercial release.
