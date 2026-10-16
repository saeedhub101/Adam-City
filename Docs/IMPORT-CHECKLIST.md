# UEFN Import and Validation Checklist

Use this checklist with the actual UEFN editor. Do not mark an item complete based on source-file inspection alone.

## 1. Source asset

- [ ] Confirm the exact GLB revision from `saeedhub101/Saeed-V2.0`.
- [ ] Keep an untouched copy of the original GLB.
- [ ] Record file size, SHA-256, node count, skin/joint count, animation names, and morph-target count.
- [ ] Inspect the model in a GLB viewer or Blender before importing.
- [ ] Check license/ownership and ensure the asset is permitted for the intended island.

## 2. Import into UEFN

- [ ] Import the GLB through the supported UEFN asset-import workflow.
- [ ] Confirm the mesh is visible and correctly oriented.
- [ ] Check scale, pivot, floor contact, and forward direction.
- [ ] Check materials, textures, eyes, teeth, tongue, and transparency.
- [ ] Confirm the skeleton is recognised and inspect bone hierarchy.
- [ ] Check which animations and morph targets the importer preserved. Do not assume all GLB features are supported.
- [ ] If import fails, capture the exact UEFN log/error before modifying the source asset.

## 3. NPC setup

- [ ] Create or configure a custom NPC Character Definition using the imported assets supported by the current UEFN version.
- [ ] Configure an NPC Spawner in a test island.
- [ ] Spawn one Saeed NPC in a controlled test area.
- [ ] Verify idle, facing direction, navigation, and collision.
- [ ] Bind only animation assets that UEFN actually imported and can play.
- [ ] Add Verse behavior only after the base NPC reliably spawns.

## 4. Functional tests

- [ ] Island launches successfully in UEFN session.
- [ ] NPC spawns exactly once at the expected location.
- [ ] Model and materials remain correct at gameplay camera distance.
- [ ] NPC does not float, sink into the floor, or face the wrong direction.
- [ ] Idle animation plays without visible rig breakage.
- [ ] Each selected animation is tested individually.
- [ ] NPC behavior remains stable after respawn and session restart.
- [ ] Record unsupported features and workarounds instead of silently omitting them.

## 5. Evidence required before declaring success

Record the UEFN version, import warnings, asset names created by UEFN, test outcome, and screenshots or logs for failures. A GitHub commit or green CI workflow alone does not prove in-editor functionality.
