# City-wide GLB execution ledger

Last updated: 2026-10-26 UTC  
Repository: saeedhub101/Adam-City — branch main

## Current position

- [x] Found why the previous identity join returned zero: the source GeoJSON had lost its OSM IDs, and existing GLB node names are literally Building_, Building_.001, etc. They contain no building ID.
- [x] Added an exporter that regenerates the local Jordan building GeoJSON from the repository's saved PBF using osmium attributes to preserve original OSM IDs.
- [x] Updated the Amman GLB builder to read the preserved @id value and support a force rebuild that updates existing manifest entries rather than skipping old GLBs.
- [x] Updated the Amman index workflow to use sparse checkout, install Blender/osmium, rebuild existing tiles with stable IDs, then index them and save diagnostics.
- [x] Added diagnostic samples for GLB file presence, GLB header validity, and actual node names. The previous diagnostic confirmed 1,477 manifest files exist and have valid GLB headers; the names are empty IDs, not missing files.
- [ ] Verify rebuilt Amman GLB node IDs, geometry alignment, full source match count, and the committed index SHA.
- [ ] Continue local photo/survey review and create new photorealistic facade assets only when an exact building image is approved.

## Active run

- [Amman GLB ID rebuild and index](https://github.com/saeedhub101/Adam-City/actions/runs/40276645698) — in progress at last check. It now exports the saved PBF with IDs, rebuilds the existing Amman tiles, and then runs the identity matcher. No new matched index has been verified yet.
- [SlideRule satellite laser import](https://github.com/saeedhub101/Adam-City/actions/runs/40276478392) — in progress at last check. Direct CMR granule URLs produced 7,728 HTTP 401 skips and zero raw files; OpenAltimetry API returned 200 errors. The importer now tries the public SlideRule service to retrieve actual sampled ATL03 observations into the repository. No observations are counted until a nonempty GeoJSON is saved and validated.
- [Older regional GLB generation](https://github.com/saeedhub101/Adam-City/actions/runs/40276627962) — also triggered by the builder change; its default mode skips existing GLBs and does not perform the forced Amman rebuild.

## Data quality rules

- OSM geometry, IDs, and the current tile origin must stay aligned. No nearest-centroid-only joins.
- The Amman GLB regeneration uses the same saved OSM geometry and local-coordinate origin; it is intended to repair identity metadata and node names, not invent a new facade design.
- Satellite laser observations are sparse spaceborne measurements, not dense airborne city LiDAR and not proof of a building's facade appearance.
- The procedural limestone texture experiment is not an exact-building photograph and must not be described as photorealistic evidence.
- Do not report a task as complete until a GLB is committed, parses, preserves alignment, and its identity join is verified.

## Next steps

1. Inspect run 40276645698 output and the committed AMMAN-GLB-INDEX-DIAGNOSTICS.json.
2. If IDs now match, record matched/unmatched counts and the exact commit SHA.
3. Continue photo matching against repository-local images. The existing Tabarbour review rejects the two previously considered photo candidates; no exact-building photo is approved there yet.
4. Review SlideRule output separately and report whether any actual observation rows were imported. Do not label satellite samples as airborne LiDAR.
