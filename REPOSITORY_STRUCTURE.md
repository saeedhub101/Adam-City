# Repository structure and naming guide

This guide records the intended organization while preserving paths referenced by scripts, reports, and the Pages deployment.

## Main locations

| Location | Purpose | Handling rule |
|---|---|---|
| `.github/workflows/` | Active GitHub Actions workflows | Keep workflow filenames stable unless all references are updated. |
| `ermita/maps/sources/` | Provider-specific map data, including OpenFreeMap/OpenMapTiles, Google Open Buildings, and Microsoft source archives | Keep providers separate; do not merge their geometry into the OSM dataset. |
| `ermita/maps/generated/` | Generated map datasets | Record source and generation method; verify provenance before overwriting. |
| `ermita/maps/external/` | External/reference datasets such as DPWH data | Preserve provider, date/version, licence, and import report. |
| `ermita/maps/qa/` and `ermita/quality/` | Validation results, comparisons, and evidence | Reports should identify exact input path and feature count; include input hash where practical. |
| `ermita/3d/terrain/` | DEM and terrain assets | Preserve source resolution, vertical units, and whether a surface is DSM or bare-earth DTM. |
| `ermita/3d/generated/` and `ermita/3d/exports/` | Generated models and preview exports | Keep derived assets distinct from original source data. |
| `ermita/scripts/` | Ermita-specific processing scripts | Use descriptive `verb_subject.py` names and repository-relative paths. |
| `scripts/` | Root-level importers required by the active deployment workflow | Do not move until workflow references and importer paths are updated together. |
| `kartaview/` | KartaView imagery, metadata, indexes, and facade-review artifacts | Retain this path until CSV records and scripts that use root-relative `kartaview/...` paths are migrated together. |
| `backup/` | Historical/original snapshots and recoverable copies | Treat as read-only except for explicit restoration/migration. A backup is not automatically the active dataset. |
| `checkpoints/` | Historical page snapshots saved before earlier changes | Reference-only; not the active deployed page. |
| `ermita-malate-3d.html` | Current 3D preview entry point used by the Pages workflow | Keep at repository root while the deployment workflow expects this path. |

## Naming convention

- Use lowercase kebab-case for folders and new data filenames.
- Include the area (`ermita`, `malate`, or `ermita-malate`) where needed to avoid ambiguity.
- Include the provider when multiple sources produce the same data type, for example `openfreemap-building-footprints.geojson`.
- Use `-raw` for source snapshots, `-processed` for normalized data, `-report.json` for machine-readable QA/import reports, and `-audit.md` for human-readable audit reports.
- Preserve source IDs, attribution, and provenance inside metadata; filenames alone are not provenance.
- Avoid duplicate copies of large binary data. Keep one canonical asset path and update every consumer if it changes.

## Migration safeguards

Before moving or renaming a path:
1. Search the complete repository for references in Python, YAML, HTML, CSV, GeoJSON, JSON, and Markdown.
2. Update producers, consumers, workflows, and documentation in the same migration.
3. Confirm moved assets remain present and no valid source data was redownloaded or discarded.
4. Validate JSON/GeoJSON parsing, image/model file presence, and deployment paths.
5. Record the old-to-new path mapping in the migration report.

## Status

This is the initial normalization guide, not a claim that every legacy filename has already been renamed. Some paths are workflow/API contracts and must be migrated atomically rather than renamed in isolation.
