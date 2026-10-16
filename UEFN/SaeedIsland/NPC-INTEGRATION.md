# Saeed NPC integration checklist for the bundled ForTemple UEFN project

## What the GitHub package workflow prepares

- The existing ForTemple UEFN project, including its `.uefnproject` and `.umap` map.
- Saeed's original `Saeed-Assets/saeed.glb`.
- A converted `Saeed-Assets/saeed.fbx`, produced by Blender in GitHub Actions.
- The starter Verse roaming behavior source.

The workflow checks that the original project/map exist, then converts the GLB through Blender and re-imports the FBX in a clean Blender scene. It fails if it cannot find a mesh, armature, or skinned mesh after the round-trip. This validates the model conversion, **not** UEFN import or Fortnite gameplay.

## Finish the NPC inside UEFN

1. Download the `SaeedIsland-UEFN-Base` artifact from the latest successful run of the repository's **Package SaeedIsland UEFN base** workflow, then extract the ZIP.
2. Open `ForTemple/ForTemple.uefnproject` in UEFN and allow any project migration to complete. Make a backup before accepting major migrations.
3. In the Content Browser, import `Saeed-Assets/saeed.fbx` first. In the import options, enable **Skeletal Mesh** and import the skeleton/mesh and animations as appropriate. Confirm the result is a usable skeletal mesh with a skeleton, not just a static mesh. The original `saeed.glb` is included as a fallback; UEFN also documents GLB as a supported 3D-model format.
4. Check the imported character's scale, orientation, materials, skin weights, facial shape keys, and animation clips in UEFN. A Blender round-trip does not guarantee that every material, facial morph, or animation will behave identically in UEFN.
5. Create an Actor Blueprint with a Skeletal Mesh component and assign the imported Saeed skeletal mesh.
6. Create an NPC Character Definition. Configure Character Type = Custom and Character Look = Custom Character, then select the Actor Blueprint according to the current UEFN NPC Character Definition UI.
7. Place an NPC Spawner in the map and assign the Saeed NPC Character Definition.
8. Add `saeed_npc_behavior.verse` to the project's Verse source area. Attach it as the NPC's Verse Behavior if supported by the current UEFN version, then compile and fix any API/version errors.
9. Launch a UEFN session and verify that the NPC spawns, is visible, can navigate, and does not interfere with the existing map objectives. Save the project.
10. To let others play, publish through Epic's Creator Portal. A GitHub ZIP is not a published Fortnite island.

## What GitHub cannot verify by itself

GitHub Actions can stage files and convert/validate the model, but it does not run the UEFN editor, create editor-owned native assets/definitions/spawners, compile Verse against the installed UEFN version, or launch a Fortnite playtest. Do not treat a green packaging workflow as proof that Saeed is already an in-game NPC.

## Source project permissions

The upstream ForTemple repository does not appear to include a clear license file. Use this as a personal working base unless you verify permission to redistribute its assets or publish a derivative island.
