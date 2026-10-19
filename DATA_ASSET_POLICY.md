# Data and asset policy

1. Inspect repository data before downloading anything; preserve accepted files and use incremental/idempotent workflows.
2. Save imported or generated assets and provenance reports in repository files, not only as workflow artifacts.
3. Work on `main` only; do not create branches for this project.
4. Distinguish source located, link tested, downloaded, committed, validated, geospatially aligned and licence verified.
5. Keep source datasets separate until geometry and coverage have been checked; never silently replace conflicts.
6. **Microsoft/Bing building footprints are rejected for the current Ermita project.** Their inaccurate outlines were removed. Do not re-import them or revive their workflows unless the project owner explicitly reverses this decision.
7. Use OSM as the active building-footprint source; preserve OSM IDs/tags and comply with ODbL attribution/share-alike obligations.
8. Prioritize streets, building footprints, real facades, roofs, building heights, windows, doors, signs and materials. Trees are lower priority.
9. Do not claim an asset was downloaded, visually verified or accurately aligned unless the file exists and the check actually succeeded.
10. For facade photos, verify building identity, camera direction, visible facade, street-facing wall, source URL and reuse terms before applying the image to a model.
