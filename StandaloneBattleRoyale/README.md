# Saeed Royale — standalone battle royale

This is a separate Unreal Engine game prototype, not a UEFN island and not part of the existing Fortnite Creative project.

## Initial implementation

- Unreal Engine C++ project/module skeleton.
- Replicated third-person character foundation.
- Server-authoritative hitscan firing request.
- Replicated health and elimination state placeholders.
- Keyboard/mouse input mappings.
- Game mode foundation with a 100-player design target.

## Not implemented yet

- No new city map has been downloaded or imported yet. The old Manila GLB was mistakenly restored and has been removed again; do not treat it as a new map. Playable terrain/buildings, loot, inventory, weapon assets, animation setup, UI, lobby, matchmaking, shrinking storm, bots, persistence, dedicated-server deployment, anti-cheat, audio, and optimization remain unfinished.
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
