# City-wide GLB execution ledger

Last updated: 2026-10-26 UTC  
Repository: saeedhub101/Adam-City — branch main

## Current position

- [x] Documented city-wide geographic batches and the image verification gate.
- [x] Confirmed the previous source join failed because the saved thematic GeoJSON does not preserve original OSM object IDs. The first diagnostic sample had only the property entrance=main; all 231,208 polygon features in that export lacked a recognized source ID.
- [x] Added a workflow-only exporter that reads the repository's saved Jordan PBF and uses osmium export attributes to preserve the original OSM type/id in the temporary GeoJSON.
- [x] Updated the index workflow to install osmium-tool, regenerate the local ID-preserving source, run the matcher, restore the tracked GeoJSON, and commit diagnostics even when matching is blocked.
- [x] Added retry logic around Git rebase/push to handle concurrent main commits.
- [ ] Complete and verify a trustworthy source-to-GLB identity join.
- [ ] Save the full index to main and verify its counts and commit SHA.
- [ ] Produce and validate real facade/roof GLBs from approved photo/survey evidence. No new photorealistic GLB is claimed yet.

## Latest execution

- Current index run: [40275961180](https://github.com/saeedhub101/Adam-City/actions/runs/40275961180) — workflow now exports OSM IDs from the saved PBF before matching. It was in progress at the last check; output counts have not yet been verified.
- Previous diagnostic run: [40274057694](https://github.com/saeedhub101/Adam-City/actions/runs/40274057694) — found 89,231 named Building_ nodes across 490 existing GLBs, but zero source matches because the GeoJSON export had no explicit OSM IDs. Its commit step failed on unstaged changes/rebase.
- Earlier run [40273391055](https://github.com/saeedhub101/Adam-City/actions/runs/40273391055) also had zero matches and failed to push its index because main changed during execution.
- LiDAR importer run [40275828086](https://github.com/saeedhub101/Adam-City/actions/runs/40275828086) is running the revised geographic downloader rather than the former thousands-page global S3 catalog crawl. Verified payload totals are not yet available.

## Next steps — do not repeat completed work

1. Inspect run 40275961180 after the identity-preserving export; confirm the match count is nonzero and check for any way/relation ID encoding mismatch.
2. Verify the generated index exists on main and record its actual counts and commit SHA.
3. Continue local image/survey review in geographic batches. A nearby camera coordinate is not proof of which facade is shown.
4. Generate new GLBs only from approved evidence; preserve source geometry and coordinates, validate output files, and visually check against the exact building.
5. Do not claim photo-realistic output until a new GLB is committed, parses, remains aligned, and is verified against an approved image of the exact building.

## Photo evidence

The existing Tabarbour photo reviews reject both previously examined candidates for exact-building facade texturing. No exact-building image is approved there yet.
