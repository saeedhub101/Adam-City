# Repository organization migration report

Date: 2026-10-20
Branch: `main`

## Completed in this pass

- Added a root `README.md` that explains the project entry points and core data-preservation rules.
- Added `docs/repository-structure.md` to define the purpose of the major directories and a consistent naming convention.
- Moved both historical preview snapshots from `checkpoints/` into `backup/checkpoints/` after verifying each destination file's contents:
  - `checkpoints/road-texture-before/index.html` → `backup/checkpoints/road-texture-before/index.html` (53,660 characters returned by the repository connector).
  - `checkpoints/terrain-alignment-before/index.html` → `backup/checkpoints/terrain-alignment-before/index.html` (51,162 characters returned by the repository connector).
- Removed the original checkpoint paths only after the destination copies were fetched and their lengths matched.
- Kept the active preview at the root path `ermita-malate-3d.html`, which is referenced by the Pages deployment arrangement.

## Why some existing directories were not renamed in this pass

The current tree contains 1,999 tracked files, including a large `kartaview/` archive, a `backup/` archive, the `ermita/` data tree, and root-level `scripts/`. Existing CSV records, processing scripts, reports, HTML, and workflows contain paths into these locations. Moving these trees without a repository-wide reference migration and data validation would risk breaking image lookups, import jobs, or the deployed page. The naming guide therefore records the canonical intent and explicitly flags these as path contracts until a complete reference rewrite can be tested.

## Data-preservation guarantees

- No source dataset was deleted as part of this pass.
- No data was re-downloaded as part of this pass.
- The only removed paths were the two old checkpoint paths, after copies were verified at their new archive paths.
- No claim is made that the 3D preview or GitHub Pages deployment was tested by this organizational change.

## Next validation boundary

A full path migration should be done as a single planned operation: build an old-to-new path map, rewrite references across scripts/workflows/HTML/CSV/JSON/GeoJSON/Markdown, parse structured datasets, check all local asset references, then run the import and Pages workflows and inspect their results. Until those checks pass, the existing data-source directories should retain their paths.


## Follow-up organization pass (2026-10-20)

- Moved the five repository-level policy, audit, catalog, structure, and migration documents into `docs/` and normalized their filenames to lowercase kebab-case.
- Kept `README.md`, the active preview HTML, and `.github/workflows/` in place because they are deployment entry points. Moved the four Ermita-specific root importers into `ermita/scripts/` and updated the Pages workflow to use the new path.
- Kept `ermita/`, `kartaview/`, and `backup/` at their current roots in this pass. They contain thousands of assets and references in scripts, CSV metadata, and HTML; moving them safely requires a repository-wide path migration and deployment/data-reference validation, not just moving directory entries. No data files were deleted as part of this documentation move.


## Latest verification (2026-10-20)

- Current branch head at this check: `60adc147730a7181bf13484cfa13024474e9f448`.
- Recursive tree inspection: 2,000 tracked files, `truncated: false`.
- Confirmed the five documentation files now exist under `docs/`, and the old root-level copies no longer exist.
- Confirmed both historical checkpoint HTML files are present under `backup/checkpoints/`.
- The remaining project/data directories were not wholesale moved because the active deployment workflow and source-indexing files depend on their current paths. The next safe phase is a reference-aware path migration with automated path checks, not a blind directory move.


## Importer relocation verification (2026-10-20)

- Moved `import_openfreemap_ermita.py`, `import_basemap_buildings.py`, `import_openaerialmap_ermita.py`, and `prepare_local_aerial_preview.py` from root `scripts/` to `ermita/scripts/`.
- Updated `.github/workflows/deploy-pages.yml` sparse-checkout and execution paths for the OpenFreeMap importer.
- Adjusted repository-root resolution in the moved basemap/OpenAerialMap/aerial-preview scripts.
- Verified that no `.py` files remain in the former root `scripts/` directory and all four destination paths exist. The recursive Git tree still reports 2,000 tracked files and is not truncated.
- This verifies path structure, not a completed GitHub Actions run or a visual browser test. The remaining `kartaview/`, `backup/`, and `ermita/` data hierarchy has not been relocated wholesale because its internal references require a larger migration and validation pass.


## Shared texture consolidation (2026-10-20)

Moved the asphalt, terrazzo sidewalk, painted masonry, and courtyard surface images from `ermita/buildings/` into `ermita/assets/textures/`. Updated `ermita/assets/README.md` and `ermita/3d/real-building-models.json`. Verified all four images exist at their new paths, none remain at the old paths, and the repository still contains 2,000 tracked files. Historical checkpoint pages under `backup/` were intentionally left untouched, as requested.


## Final layout cleanup (2026-10-20)

Moved the shared-asset usage guide from `ermita/buildings/ASSET_USAGE.md` to `ermita/assets/README.md`, corrected stale references to a non-existent `ermita/maps/preview.html`, and updated the Ermita overview and repository structure guide to reflect the active root preview page and current script locations. The `kartaview/` and `backup/` trees were intentionally excluded from this work as requested.


## Documentation reconciliation (2026-10-20)

- Corrected stale references to a missing root `index.html` and to removed deployment/export workflow filenames; the active Pages entry point is `ermita-malate-3d.html`, and the tracked workflow is `.github/workflows/deploy-pages.yml`.
- Reconciled the 3D/maps/QA documentation with the committed source layout: the live preview uses OpenFreeMap and local tile-derived fallback layers; the generated footprint GeoJSON is Basemap/OpenMapTiles-derived according to the file-level audit; Google Open Buildings and Microsoft satellite-derived footprints are stored separately and are not assumed to be active preview layers.
- Marked the initial layer inventory as historical planning guidance, not a current inventory.
- Updated the data policy to prohibit source conflation rather than incorrectly declaring the committed Microsoft satellite-footprint dataset absent.
- No changes were made to `kartaview/` or `backup/`.
