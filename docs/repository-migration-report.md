# Repository organization and verification report

Updated: 2026-10-20  
Branch: `main`

## Current canonical layout

- `README.md` — project entry point and data-preservation rules.
- `docs/` — the canonical home for repository structure, source catalog, data policy, data audit, and this migration report.
- `ermita/` — area-specific source data, derived data, QA, terrain, 3D assets, textures, and import/processing scripts.
- `ermita/scripts/` — active Ermita scripts, including the OpenFreeMap importer.
- `ermita/assets/textures/` — shared texture assets; `ermita/assets/README.md` documents their intended use and limitations.
- `ermita-malate-3d.html` — the active 3D preview page.
- `.github/workflows/deploy-pages.yml` — the sole tracked active workflow; it builds a minimal Pages artifact and creates the root redirect inside that artifact. A repository-root `index.html` is intentionally not tracked.
- `kartaview/` and `backup/` — retained in place and excluded from this cleanup.

## Changes consolidated

- Moved the five repository-level policy/audit/catalog/structure/migration documents into `docs/` and normalized their filenames.
- Moved the four Ermita import/preview scripts from the old root `scripts/` directory to `ermita/scripts/`; updated the Pages workflow and script root-path resolution.
- Consolidated shared surface textures under `ermita/assets/textures/` and the usage guide at `ermita/assets/README.md`.
- Updated the map, 3D, QA, inventory, and asset documentation to use current paths and describe the active preview and workflow accurately.
- Clarified that Microsoft satellite-derived footprints and Google Open Buildings are separate stored datasets, not automatically active preview layers.
- Clarified that `ermita/maps/generated/ermita-building-footprints.geojson` is Basemap/OpenMapTiles-derived according to the file-level audit and must not be treated as a pure OSM snapshot. The similarly named historical file under `backup/` is a different blob and must remain a separate preserved source.
- Made the OpenFreeMap importer derive its repository root from its own file location rather than the process working directory.

## Structural checks at this revision

The recursive Git tree for the checked revision reported 2,000 tracked files and `truncated: false`.

- No Python scripts remain under the old root `scripts/` path.
- The old root-level uppercase policy/report filenames are absent; their canonical copies live under `docs/`.
- The active preview exists at `ermita-malate-3d.html`; there is no tracked root `index.html` or non-archived `preview.html`.
- `.github/workflows/` contains one tracked active workflow: `deploy-pages.yml`.
- A Git-blob hash comparison found no byte-identical duplicate files outside `backup/` and `kartaview/`. This check deliberately excludes those preserved archives.
- The two same-named building-footprint files under `ermita/` and `backup/` have different blob hashes and must not be deleted as duplicates.
- The latest Pages workflow run for revision `af2d6f1c0a5ff5b291988be9c74890716d8abfbe` completed successfully.

## Source integrity and safety rules

1. Reuse valid committed source data first; import only missing or invalid assets.
2. Keep provider datasets separate. Do not silently merge or overwrite OSM, OpenFreeMap/OpenMapTiles, Microsoft, or Google geometries.
3. Keep original inputs, derived outputs, and import/QA reports traceable to their sources.
4. Treat a successful workflow as deployment evidence, not proof that every map layer is visually or geometrically correct.
5. Do not remove files from `backup/` or `kartaview/` as part of routine organization.
6. Keep work on `main`; do not create project branches for routine cleanup.

## Scope note

The structural checks above cover the tracked Git tree, exact duplicate blob hashes outside the excluded archives, the active workflow/page paths, and the named asset relocations. They do not claim that every building footprint is accurate, every external source is integrated into the preview, or every 3D feature has been visually verified against imagery.
