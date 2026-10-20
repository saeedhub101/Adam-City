# Data and asset policy

1. Inspect repository data before downloading anything; preserve accepted files and use incremental/idempotent workflows.
2. Save imported or generated assets and provenance reports in repository files, not only as workflow artifacts.
3. Work on `main` only; do not create branches for this project.
4. Distinguish source located, link tested, downloaded, committed, validated, geospatially aligned and licence verified.
5. Keep source datasets separate until geometry and coverage have been checked; never silently replace conflicts.
6. Keep building providers in separate datasets. A Microsoft satellite-derived footprint dataset and a Google Open Buildings dataset are now committed under `ermita/maps/sources/`; neither is automatically the active preview layer, and their presence does not establish accuracy.
7. The current live preview is OpenFreeMap-based. The generated `ermita/maps/generated/ermita-building-footprints.geojson` is Basemap/OpenMapTiles-derived according to the file-level audit, not a pure OSM dataset. Preserve source identities and never label or overwrite one provider as another. OSM data must retain IDs/tags and comply with ODbL attribution/share-alike obligations.
8. Prioritize streets, building footprints, real facades, roofs, building heights, windows, doors, signs and materials. Trees are lower priority.
9. Do not claim an asset was downloaded, visually verified or accurately aligned unless the file exists and the check actually succeeded.
10. For facade photos, verify building identity, camera direction, visible facade, street-facing wall, source URL and reuse terms before applying the image to a model.

11. On every deployment, inspect the repository's saved source tiles, generated datasets, and reports before downloading or generating anything.
12. Reuse valid committed assets first. Download only source tiles that are missing or invalid; never redownload valid tiles just because a deployment runs again.
13. Persist all newly imported source tiles, decoded layer records, generated fallback datasets, and their provenance/QA reports to `main` in the same deployment workflow. Do not leave generated data only in a temporary runner or Pages artifact.
14. Rebuild derived fallback datasets only when they are missing or when new source tiles have been added. Reuse existing fallbacks unchanged when the source set has not changed.
15. Validate generated GeoJSON counts and non-empty files before publishing. A successful deployment must not be treated as proof that the map rendered correctly; report the actual checks performed.
