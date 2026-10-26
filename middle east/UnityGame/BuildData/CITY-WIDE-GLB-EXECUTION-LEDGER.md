# City-wide GLB execution ledger

Last updated: 2026-10-26  
Repository: `saeedhub101/Adam-City` — branch `main`

## Current position

- [x] City-wide geographic-batch plan documented.
- [x] Indexer updated to enumerate existing GLB building nodes even when OSM joins fail.
- [x] Updated indexer ran on GitHub Actions [40273391055](https://github.com/saeedhub101/Adam-City/actions/runs/40273391055).
- [x] Confirmed 1,477 manifest tiles, 490 existing GLB files scanned, and 89,231 exported `Building_` nodes.
- [ ] Fix OSM join: current run matched 0 nodes and could not recognize IDs on 231,208 polygon features. This is a schema/join issue, not evidence the buildings are missing.
- [ ] Persist index to `main`: index generation completed, but push was rejected because the branch advanced concurrently.
- [ ] Produce/validate real facade or roof GLBs from approved photo/survey evidence. No new photorealistic GLB is claimed yet.

## Workflow failure details

Run [40273391055](https://github.com/saeedhub101/Adam-City/actions/runs/40273391055):
- Index generation step: **success**, but zero OSM matches.
- Output had 89,231 building nodes retained and no source polygon parts joined.
- Commit step: **failure** — `git push origin HEAD:main` returned `[rejected] main -> main (fetch first)`. Another commit reached `main` while this run was working, so the generated index was not confirmed stored remotely.

Earlier runs:
- [40272094590](https://github.com/saeedhub101/Adam-City/actions/runs/40272094590): old indexer rejected an empty index.
- [40272105443](https://github.com/saeedhub101/Adam-City/actions/runs/40272105443): texture job was cancelled before a verified output.
- [40271467485](https://github.com/saeedhub101/Adam-City/actions/runs/40271467485): an earlier green workflow is not accepted as proof of valid textured GLBs because the Blender script had a Python failure.

## Next actions — do not repeat completed work

1. Print and inspect sample feature keys, nested tags, and GLB node-name patterns from existing files.
2. Correct ID parsing based on the observed source schema; never guess a join. Keep unmatched nodes marked unmatched.
3. Compact the index by omitting empty optional values.
4. Make the workflow pull/rebase latest `main` before committing generated outputs, then push.
5. Once the join is validated, process geographic batches for image/survey candidates, retaining photo review records and provenance.
6. Record each meaningful phase here: run ID, counts, exact output path, failure cause, and next step.

## Photo evidence

Two candidate images were opened and rejected for exact-building texture use. Their source, license status, visual review, and reasons are recorded in `TABARBOUR-PHOTO-REVIEWS.json`. No exact-building image is approved in that ledger yet.
