# Saeed Royale — standalone battle royale

This is a separate Unreal Engine game prototype, not a UEFN island and not part of the existing Fortnite Creative project.

## Initial implementation

- Unreal Engine C++ project/module skeleton.
- Restored a real 3D GLB district model for Manila at `Content/Maps/Manila-Central-District.glb` as the map source asset.
- Replicated third-person character foundation.
- Server-authoritative hitscan firing request.
- Replicated health and elimination state placeholders.
- Keyboard/mouse input mappings.
- Game mode foundation with a 100-player design target.

## Not implemented yet

- The Manila GLB is present as a source asset, but it has not yet been imported into Unreal `.uasset` assets or assembled into a playable `.umap` level. Playable terrain/buildings, loot, inventory, weapon assets, animation setup, UI, lobby, matchmaking, shrinking storm, bots, persistence, dedicated-server deployment, anti-cheat, audio, and optimization remain unfinished.
- Saeed GLB import/retargeting into the player character.
- Controller mappings and console certification work.

## Verification truth

GitHub Actions can check source files and package source artifacts, but cannot compile Unreal C++ without a matching Unreal Engine installation and build toolchain. This code has not yet been compiled in Unreal Editor. Treat it as a starting implementation until a real Unreal build and multiplayer PIE test pass.

## First local validation

1. Install Unreal Engine using Epic Games Launcher on Windows.
2. Open `SaeedRoyale.uproject` and import `Content/Maps/Manila-Central-District.glb` using the editor's GLTF/GLB import support.
3. Inspect the imported mesh hierarchy, scale, origin, and materials; split or optimize the city into streaming-friendly sections if required.
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
