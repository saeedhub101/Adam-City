# City-wide GLB execution ledger

Last updated: 2026-10-26  
Repository: `saeedhub101/Adam-City` — branch `main`

## Current position

- [x] Documented city-wide geographic batches and the image verification gate.
- [x] Updated the indexer to inventory existing exported `Building_` nodes even when source matching fails.
- [x] Diagnosed the prior workflow failure from its actual logs.
- [x] Fixed the index workflow to fetch/rebase the latest `main` before committing generated output.
- [x] Added runtime diagnostics that print the actual first OSM GeoJSON feature schema so the ID mismatch can be fixed from observed data, not guessed field names.
- [ ] Complete a trustworthy source-to-GLB identity join.
- [ ] Save the full index to `main` and verify it was committed.
- [ ] Produce and validate real facade/roof GLBs from approved photo/survey evidence. No new photorealistic GLB is claimed yet.

## Latest execution

- Current run: [40274057694](https://github.com/saeedhub101/Adam-City/actions/runs/40274057694) — running the updated indexer with source-schema diagnostics.
- Previous run: [40273391055](https://github.com/saeedhub101/Adam-City/actions/runs/40273391055) — scanned 1,477 manifest tiles, 490 present GLB files and 89,231 exported building nodes; matched 0 OSM records; identified 231,208 polygon features without recognized explicit IDs.
- In run 40273391055 the index-generation step completed, but the commit/push step failed with `[rejected] main -> main (fetch first)` because another commit updated `main` while the workflow was running. The workflow now rebases before committing.
- Earlier [40272094590](https://github.com/saeedhub101/Adam-City/actions/runs/40272094590) failed the old empty-index guard. [40272105443](https://github.com/saeedhub101/Adam-City/actions/runs/40272105443) was cancelled before verified texture outputs. Earlier green run [40271467485](https://github.com/saeedhub101/Adam-City/actions/runs/40271467485) is not proof of a valid textured GLB because Blender had reported a Python failure.

## Next steps — avoid repeating completed work

1. Read the schema diagnostics from run 40274057694 and adapt the ID parser to the actual local data format.
2. Rerun the index only after fixing the schema mismatch; retain unmatched assets and never guess identity by proximity.
3. Verify the generated index exists in the remote repository and record counts/commit SHA here.
4. Process image and survey candidates in geographic batches, inspecting actual images and recording license, exact-building identity, facade coverage, and accept/reject reasons.
5. Generate new GLBs only from approved evidence, preserve source assets/coordinates, validate output files and visual appearance, then continue automatically through further batches.
6. Update this ledger at each meaningful phase with run IDs, output paths, failure causes, and the exact next action.

## Photo evidence

Two candidates have been opened and rejected for exact-building texturing. Source, license status, visual review and reasons are recorded in `TABARBOUR-PHOTO-REVIEWS.json`. No exact-building image is approved there yet.
