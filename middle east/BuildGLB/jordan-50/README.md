# Jordan-wide OSM GLB set

This directory is the consolidated regional output target for the Jordan map. The build workflow is designed to create no more than 50 large GLB files for the country, rather than thousands of 0.01-degree tiles.

## Current pipeline contents

The exporter combines the locally stored Jordan OSM layers for buildings, building details, roads, street names, addresses, boundaries, landcover, places, and water. The workflow also filters the saved Jordan PBF for mapped infrastructure such as railways, waterways, power lines, trees, traffic signals, public-transport features, bridges, tunnels, barriers, and related objects.

Each building and infrastructure object retains its OSM identity and relevant tags as GLB custom properties where the source data exposes them. The manifest records feature counts and the shared geographic origin. OSM-tagged building/roof colors and materials are used when present; missing values are not presented as surveyed facts.

## Accuracy and offline use

The GLBs are self-contained geometry/material assets. They do not require a live map service or external asset URLs at runtime.

OSM data does not supply measured facade photos, exact window positions, roof texture photographs, or accurate heights for every building. The generator marks default heights and procedural windows as such. They are not survey data.

The current repository inventory does not yet contain a Jordan-specific DEM or local orthophotos. Terrain elevation, satellite/orthophoto textures, and verified photogrammetric models are separate follow-up data-import tasks; this folder must not be described as a fully textured photogrammetric city until those assets are actually integrated.

## Incremental persistence and resume (required)

The build must save each completed GLB and update `manifest.json` to `main` during the build, not wait for the final validation/commit step. The exporter is invoked with `--repo_commit true --force false`: after each tile it commits and pushes that GLB plus the manifest, and a later run reuses valid existing GLBs instead of rebuilding them. If the run is cancelled, times out, or fails on a later tile, previously checkpointed files remain in the repository. Validation at the end is an additional check, not the first persistence point. Keep the output to at most 50 regional GLBs rather than creating thousands of tiny files.

## Validation

The workflow must:
- generate 1–50 GLBs,
- verify each file's GLB header,
- ensure every generated GLB is listed in manifest.json,
- save feature counts and georeference origin,
- commit the validated output to main.

The legacy workflow that generated many tiny grid tiles is retired.
