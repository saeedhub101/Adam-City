# Saeed Royale — Windows 3D survival shooter

A standalone third-person 3D survival shooter made with Godot 4.4.1. This project is separate from the UEFN island and the earlier Unreal prototype. The arena, cover, trees, player, AI rivals, weapon visuals, storm ring and HUD are generated at runtime, so the game does not depend on external asset downloads.

## Controls

- WASD or arrow keys: move
- Mouse: aim/look
- Left mouse button: fire
- R: reload
- Space: jump
- Shift: sprint
- Esc: release or recapture the mouse
- Enter: restart after defeat or victory

## Gameplay in this build

- Third-person movement in a 3D arena
- 14 AI rivals
- Rifle fire, ammunition, reloading and hit detection
- Health and ammunition pickups
- A shrinking safe zone that damages players outside it
- HUD, survival timer, victory/defeat and restart

## Download

The GitHub Actions workflow named **Build Saeed Royale for Windows** exports a Windows x64 executable and uploads it as the artifact **SaeedRoyale-Windows-x64**. Download the artifact ZIP from a successful workflow run. Extract it and launch SaeedRoyale.exe.

This version is a playable single-player prototype against computer-controlled opponents. Online multiplayer, matchmaking and dedicated servers are not implemented and are not advertised as available.

## Automated checks

GitHub Actions validates the project files, launches Godot headlessly to catch script/runtime errors, exports the Windows executable, and uploads the artifact only if those steps succeed.
