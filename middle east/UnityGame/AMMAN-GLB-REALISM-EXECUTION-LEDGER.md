# Amman GLB Realism Pipeline — Execution Ledger

Last updated: 2026-10-26 UTC
Repository: saeedhub101/Adam-City
Branch: main

## Verified progress
- City-wide batch plan is documented in TABARBOUR-REAL-BUILDING-EXECUTION-PLAN.md.
- Amman manifest lists 1,477 tiles.
- Run 40273391055 scanned 490 existing GLBs and found 89,231 named Building_ nodes, but extracted zero source OSM IDs. Its generated index was not valid and the push failed because main changed during the run.
- The texture workflow run 40272105443 was cancelled. No new photorealistic GLB has been verified.
- Two previously inspected Tabarbour image candidates were rejected for exact-building facade texturing.
- The indexer was updated to inspect common flat/nested OSM identity fields, emit diagnostic samples to middle east/UnityGame/BuildData/AMMAN-GLB-INDEX-DIAGNOSTICS.json, and refuse to publish an index with zero matches.

## Current blocker
The saved Jordan buildings GeoJSON contains polygon features, but the previous run could not find an OSM identity field in any feature. The next run's diagnostic sample must be inspected to learn the real schema. Do not guess IDs, join by nearest location alone, or create facade textures before identity matching works.

## Next actions — resume here, do not repeat completed steps
1. Run the updated indexer and inspect AMMAN-GLB-INDEX-DIAGNOSTICS.json (or the diagnostic printed in the workflow logs).
2. Fix ID extraction using the actual keys observed in the diagnostic, then rerun until stable OSM IDs match GLB nodes and tile locations.
3. Make the workflow preserve diagnostics on failure and retry non-fast-forward pushes; its previous push failed during concurrent main updates.
4. Produce a resumable per-tile/per-building batch manifest and process whole geographic batches, not one building at a time.
5. Search local imagery and real point-cloud payloads first; only use external sources for missing evidence.
6. Generate separate GLBs only where exact-building image/survey evidence exists; preserve original GLBs and coordinates.
7. Validate each output and continue automatically to the next batch.

## Integrity rule
An inventory, source join, or green workflow status is not proof of a realistic building. Claim photo-realistic output only after the new GLB exists, parses, stays aligned with the source, and has been visually checked against an approved image of the exact building.
