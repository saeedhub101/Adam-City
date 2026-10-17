# Adam Royal — standalone 3D game

Adam Royal is a standalone Unreal Engine game project, separate from any UEFN island or Fortnite Creative project.

## Initial implementation

- Unreal Engine C++ project/module skeleton.
- Replicated third-person character foundation.
- Server-authoritative hitscan firing request.
- Replicated health and elimination state placeholders.
- Keyboard/mouse input mappings (WASD, mouse look, Space jump, left-click hitscan fire).
- C++ third-person camera boom/follow camera and baseline movement tuning.
- Game mode foundation with a 100-player design target.

## Not implemented yet

- The Manila district generator now produces a real-geography GLB from OpenStreetMap data and packages it with procedural facade atlases and Wikimedia Commons facade reference photos. This is source geometry, not yet a native Unreal .umap level, and the reference photos are not yet mapped onto building meshes.
- Loot, inventory, production weapon models/animations, HUD, lobby, matchmaking, shrinking storm, bots, persistence, dedicated-server deployment, anti-cheat, audio, and optimization remain unfinished.
- Saeed GLB import/retargeting into the player character.
- Controller mappings and console certification work.

## Verification truth

GitHub Actions can check source files and package source artifacts, but cannot compile Unreal C++ without a matching Unreal Engine installation and build toolchain. This code has not yet been compiled in Unreal Editor. Treat it as a starting implementation until a real Unreal build and multiplayer PIE test pass.

## First local validation

1. Install Unreal Engine using Epic Games Launcher on Windows.
2. Download a fresh, openly licensed city-area extract (not the old GLB) and save the source data in the repository.
3. Convert/import the new map data into Unreal assets and inspect scale, origin, roads, building geometry, and materials.
4. Save a real `.umap` level, add PlayerStarts and lighting, and set SaeedRoyaleGameMode as the map GameMode.
5. Compile the editor target and test Play-in-Editor before producing gameplay screenshots.
6. Use Play > Number of Players = 2 and run as a listen server to test replication and server-side damage.

## Platform plan

1. Windows prototype and repeatable multiplayer tests.
2. Battle-royale vertical slice: spawn flow, loot, inventory, weapons, storm, eliminations, win condition.
3. Dedicated-server and network/load tests.
4. PS5 only after approved PlayStation developer access and Sony SDK/tool access.

Official Unreal multiplayer guide: https://dev.epicgames.com/documentation/unreal-engine/multiplayer-programming-quick-start-for-unreal-engine

Official PS5 access requirements: https://dev.epicgames.com/documentation/unreal-engine/development-for-playstation-5-in-unreal-engine


## Real-world Manila district source

The map-generation workflow downloads current OpenStreetMap ways for a bounded central-Manila area, builds extruded building footprints and road geometry, and exports a GLB plus a provenance report into the workflow artifact `Adam-Royal-Manila-Central-District`. This is actual mapped geography, but buildings are procedural extrusions rather than photo-scanned assets. The workflow does not claim that Unreal has compiled or imported the GLB into a packaged game; the GLB is placed in the Unreal project's `Content/Maps` path in the generated artifact for editor import and review.

Map data © OpenStreetMap contributors, available under ODbL 1.0. See https://www.openstreetmap.org/copyright.

## City-data and texture workflow

The current automated pipeline is a **source-data generator and validation step**, not yet an Unreal gameplay build:

1. GitHub Actions checks out the repository and installs Python plus `requests`, `shapely`, `trimesh`, `mapbox-earcut`, `scipy`, `numpy`, and `pillow`.
2. `StandaloneBattleRoyale/Tools/build_manila_district.py` retrieves real mapped building footprints and road ways for the configured central-Manila bounding box from OpenStreetMap/Overpass, then creates 3D building extrusions and roads and exports `Manila-Central-District.glb` plus a JSON provenance/metrics report.
3. The generator creates procedural facade texture atlases (`Manila-Facade-Texture-*.jpg`) with Python Pillow. These add generic windows/concrete variation; they are **generated textures, not photographs of the actual buildings**.
4. `StandaloneBattleRoyale/Tools/fetch_manila_facade_photos.py` queries Wikimedia Commons for building-specific reference photos, downloads eligible files, and records source page, author and license details in `Content/Maps/Real-Facade-Photos/manifest.json`.
5. Quality checks verify that the GLB/report exist and contain a minimum number of buildings and roads, then upload the GLB, report, procedural texture atlases and reference-photo folder as the `Adam-Royal-Manila-Central-District` workflow artifact (retained for 30 days).

### Where the real-world data and images come from

- **Building footprints and roads:** OpenStreetMap via Overpass API. Attribution: © OpenStreetMap contributors; ODbL 1.0. https://www.openstreetmap.org/copyright
- **Building facade reference photographs:** Wikimedia Commons categories/pages for First United Building, Regina Building and Afable Building, accessed through the public Commons API. Each downloaded image must be checked against its own manifest entry for its source page, author and license; licenses and attribution requirements can differ by image. https://commons.wikimedia.org/
- **Procedural textures:** generated by the repository's Python/Pillow map-generation script; they are not downloaded photo textures and do not reproduce a specific facade.
- **No API key is intended to be required** for these OpenStreetMap/Overpass and Wikimedia Commons requests. External services can rate-limit or temporarily fail, so the workflow must be checked for a successful run and non-empty outputs.

### Important current limitation

The Wikimedia photos are currently **reference assets** packaged beside the GLB. They are not yet projected onto the corresponding 3D building meshes, and the generated facade atlases remain procedural. Therefore the current artifact does not yet guarantee authentic building signage, exact facade colors, or photogrammetric-level realism. Also, placing a GLB under `Content/Maps` does not by itself make it a native Unreal `.umap` level: import it in Unreal, inspect materials/collision/scale, configure lighting and gameplay actors, then test in Play-in-Editor before calling it playable. The GitHub workflow does not currently compile Unreal or capture actual gameplay screenshots.

