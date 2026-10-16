# SaeedIsland — UEFN starter

This folder describes the intended island setup. It is not a native UEFN island project: native project metadata and map files must be created and saved by UEFN itself.

## Create the island

1. In UEFN, create a **Blank** island project named **SaeedIsland**.
2. Open it once and use Verse Explorer to create a Verse file, then close UEFN.
3. From this repository on Windows, run:

   ```powershell
   .\Tools\Initialize-SaeedIsland.ps1 -ProjectPath "C:\Path\To\SaeedIsland"
   ```

4. Reopen the project. Import the file at Plugins\SaeedIsland\Content\Imports\Saeed\saeed.glb through the Content Browser if the installed UEFN version accepts the format. If not, convert the model in Blender to a supported FBX and verify skeleton, materials, scale, and orientation.
5. Configure a supported NPC Character Definition and NPC Spawner. Attach the Verse behavior only after the file compiles.
6. Build Verse, launch a private session, and verify spawn, navigation, collision, animation, and despawn behavior.

## Acceptance gate

Do not call the island complete until:
- UEFN opens the saved project without errors.
- Character assets import without missing materials or skeleton errors.
- Verse compiles in the installed UEFN version.
- The NPC spawns and navigates in a private play session.
- No third-party island/map assets are copied without a verified license.

## Licensing

The island base should be created from Epic's Blank template. Epic-provided content remains subject to Epic's terms; the Saeed model is the user's supplied project asset. This repository does not claim that Fortnite, UEFN, or the source model is public domain.
