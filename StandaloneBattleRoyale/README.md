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

- Playable map, terrain, buildings, loot, inventory, weapon assets, animation setup, UI, lobby, matchmaking, shrinking storm, bots, persistence, dedicated-server deployment, anti-cheat, audio, and optimization.
- Saeed GLB import/retargeting into the player character.
- Controller mappings and console certification work.

## Verification truth

GitHub Actions can check source files and package source artifacts, but cannot compile Unreal C++ without a matching Unreal Engine installation and build toolchain. This code has not yet been compiled in Unreal Editor. Treat it as a starting implementation until a real Unreal build and multiplayer PIE test pass.

## First local validation

1. Install Unreal Engine using Epic Games Launcher on Windows.
2. Open SaeedRoyale.uproject and let Unreal generate project files.
3. Compile the editor target.
4. Create a test map, place PlayerStarts, and set SaeedRoyaleGameMode as the map GameMode.
5. Use Play > Number of Players = 2 and run as a listen server to test replication and server-side damage.
6. Fix all compile/runtime errors before adding the storm and loot systems.

## Platform plan

1. Windows prototype and repeatable multiplayer tests.
2. Battle-royale vertical slice: spawn flow, loot, inventory, weapons, storm, eliminations, win condition.
3. Dedicated-server and network/load tests.
4. PS5 only after approved PlayStation developer access and Sony SDK/tool access.

Official Unreal multiplayer guide: https://dev.epicgames.com/documentation/unreal-engine/multiplayer-programming-quick-start-for-unreal-engine

Official PS5 access requirements: https://dev.epicgames.com/documentation/unreal-engine/development-for-playstation-5-in-unreal-engine
