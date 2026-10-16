# Saeed UEFN project scaffold

This folder contains the source files and preparation helper for a real UEFN island project. UEFN must create the native island project on a Windows machine with UEFN installed; this repository cannot generate the editor's saved island, imported Unreal assets, or validate them remotely.

## Create the native island once

1. Install and launch Unreal Editor for Fortnite (UEFN).
2. In Project Browser choose **Island Templates → Blank**.
3. Set project name to `SaeedIsland` (letters/numbers/underscores only) and create it.
4. Close UEFN before copying source files.
5. In this repository, run PowerShell from the repository root:

   ```powershell
   .\Tools\Prepare-UEFNProject.ps1 -ProjectPath "C:\Users\YOUR_USER\Documents\Fortnite Projects\SaeedIsland"
   ```

   Set `ProjectPath` to the actual folder UEFN created. The helper checks for a `.uefnproject` file and a project `Plugins\<ProjectName>\Content` folder before copying the Verse source. It does not fabricate missing UEFN project files.

6. Reopen the project in UEFN, open Verse Explorer, then run **Verse → Build Verse Code**.
7. In the editor, create/configure an NPC Character Definition and NPC Spawner using options supported by the installed UEFN version. Assign the behavior script in the editor, compile, launch a session, and record results.

## Character asset

The source GLB is `../assets/saeed.glb`. UEFN's supported import pipeline and NPC appearance restrictions must be checked in the editor. If the asset must be converted, use Blender to create a separate FBX working copy; never overwrite the original GLB. A successful asset import does not itself mean Fortnite's NPC system accepts that custom mesh.

## Honest completion criteria

This is a **source scaffold**, not a finished native island. The island is only complete after UEFN opens the project, imports a compatible character asset, builds Verse successfully, and a playtest confirms the NPC appears and behaves correctly.