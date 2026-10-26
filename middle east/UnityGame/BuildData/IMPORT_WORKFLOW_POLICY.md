# Mandatory import workflow policy

Applies to every data-import workflow in saeedhub101/Adam-City, including OSM, GLB, GIS, imagery, terrain, infrastructure and LiDAR. This policy is mandatory for future import work.

## 1. Inspect before downloading
- Inventory existing files, manifests, checksums, metadata, and completed checkpoints before starting an import.
- Build a source inventory and missing-items list. Import only assets or geographic coverage that are genuinely missing.
- Use stable source IDs, OSM type + ID, URLs, checksums, or source-specific identifiers to avoid duplicates.
- Do not re-import the same assets on every run simply because the workflow restarted.

## 2. Save during the workflow
- Persist successful outputs and progress checkpoints while the workflow is running; do not wait until the final step to save everything.
- Commit useful batches incrementally to main, with a manifest/checkpoint describing what was saved and what remains.
- A failed later stage must not discard already imported and committed outputs.
- Keep progress logs concise and machine-readable so a restarted workflow can identify completed work.

## 3. Sensible file sizes; no file explosion
- Avoid one file per feature or tiny geographic tile when a larger regional dataset is appropriate.
- Combine related features into manageable regional files. For Jordan GLBs, the country-wide output limit is 50 GLB files maximum.
- Split a file only when required by practical repository, reader, or processing limits. Chunks must be reasonably large and limited in number, not millions of tiny files.
- Use deterministic chunk naming and a manifest with original filename, chunk order, total bytes, checksum, and reconstruction instructions where chunking is unavoidable.
- Keep JSON/GeoJSON reports and manifests readable and bounded; use compressed GeoJSON or regional files when suitable.

## 4. Failure isolation and stage continuation
- Structure workflows as independent stages. A failed source, region, or conversion should be recorded without preventing unrelated remaining regions/sources/stages from running.
- Use per-stage and per-region error handling, bounded retries, and a final summary of successes, skips, failures, and missing coverage.
- Optional source failures should not erase successes or block independent work.

## 5. Resume, do not restart from zero
- Before each task, read the saved progress manifest and inspect existing output files.
- Mark an item complete only after validating the actual payload, not just a catalog entry or HTTP 200 response.
- Resume partial downloads with HTTP Range when supported; otherwise retain validated chunks and continue from the next missing chunk.
- Skip verified outputs whose checksum/size/source identity still matches. Revalidate incomplete or suspect files.
- Use atomic temporary-file writes and checkpoint after each successful asset or small batch.

## 6. Data integrity and truthful reporting
- Record source, license, geographic bounds/CRS, timestamps, size, checksum, and validation result when available.
- Distinguish metadata/catalog discovery from actual downloaded payloads.
- For GLBs, validate file headers, parseability, feature counts, source IDs, georeferencing and manifest coverage.
- Never claim success based only on workflow startup, metadata, catalog pages, or placeholder geometry.
- Preserve original IDs and tags; never invent measured heights, material, facade imagery, or other factual attributes.

## 7. Repository size and safe commits
- Avoid creating huge Git histories by repeatedly committing the same large raw assets. Commit incremental batches, not every tiny record.
- Check repository size and GitHub file-size limits before committing large binary payloads. If a payload exceeds practical Git limits, use an approved storage mechanism and keep a stable manifest/reference in the repository; do not silently replace requested assets with metadata.
- Never delete pre-existing data unless explicitly authorized and confirmed obsolete.

## 8. Required final report
Every import workflow must report items discovered, already present, newly imported, duplicate-skipped, and failed; actual payload files and bytes; paths and checksums; geographic coverage and source/licensing notes; per-stage results and errors; checkpoint/resume location and next steps.

## Current run exception
If a workflow is already running when this policy is adopted, do not modify its workflow/script or cancel it while it is still running. Monitor it to completion. If it fails, cancel only if it is still running, then apply this policy to the next run and resume from committed checkpoints rather than starting over.