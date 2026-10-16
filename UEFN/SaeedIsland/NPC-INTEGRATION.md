# Saeed NPC integration checklist for the bundled ForTemple UEFN project

## What this package contains
- The existing ForTemple UEFN project, including its .uefnproject and .umap.
- Saeed's original GLB model.
- A starter Verse behavior source for a roaming NPC.

## Finish the NPC inside UEFN
UEFN must generate and save native assets for the custom NPC; GitHub cannot safely manufacture those editor-owned assets from text files alone.

1. Open `ForTemple/ForTemple.uefnproject` in UEFN and allow it to update/migrate the project if prompted. Make a copy before accepting major migrations.
2. Import `Saeed-Assets/saeed.glb` into the project Content Browser. Confirm the import creates a usable skeletal mesh and skeleton, not just a static mesh. If it is static-only or the skeleton is unsuitable, fix/export it in Blender first.
3. Create an Actor Blueprint with a Skeletal Mesh component and assign the imported Saeed skeletal mesh.
4. Create an NPC Character Definition. Configure Character Type = Custom, Character Look = Custom Character, and select the Actor Blueprint, following Epic's current NPC Character Definition and Animation Preset documentation.
5. Place an NPC Spawner in the map and assign the Saeed NPC Character Definition.
6. Add `saeed_npc_behavior.verse` to the project's Verse source area. Attach it as the NPC's Verse Behavior in the definition/device UI if the current UEFN version exposes that configuration. Compile; fix any API/version errors before playtesting.
7. Launch a UEFN session and verify the NPC spawns, is visible, can navigate, and does not block the existing Stronghold objectives.
8. Save the project. Use UEFN's Launch Session/playtest to see it in Fortnite. To let other people play it, publish through Epic's Creator Portal; a GitHub ZIP alone is not a published Fortnite island.

## Important
The ZIP is a prepared working base, not a claim that the custom NPC has already been inserted, compiled, or playtested. Those last editor-owned steps require UEFN. The upstream author describes the project as open-sourced but the repository has no clear LICENSE file, so do not redistribute its original assets or publish a derivative until you have verified the applicable permissions.
