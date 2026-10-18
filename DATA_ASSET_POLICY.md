# Data and generated-asset retention policy

**Project objective:** build a highly accurate 3D Ermita, beginning with Malate. This is a study project, not a commercial product.

## Mandatory collection rules

1. Search the complete repository and inspect existing source files before downloading anything. Reuse existing files and download only missing data or genuinely newer/better coverage.
2. Do not ask the user about licenses, terms, contacting agencies, requesting APIs, or submitting data requests. Do not contact agencies or require the user to do so.
3. For any source with data directly downloadable without an account/API key/contact, download it with a workflow or direct script, clip it to the target AOI when appropriate, validate it, and save the actual data in this repository.
4. If a source is inaccessible or requires an API key, account approval, payment, or human contact, skip it and immediately test another downloadable source. Do not block the project waiting for a request.
5. Save each downloaded/imported/generated asset in the repository, not only as a temporary workflow artifact. Store a source URL, retrieval time, coverage/CRS, format, checksum when practical, and a concise QA report.
6. Work on main only. Workflows must be incremental/idempotent: inspect manifests and existing outputs, avoid repeated downloads, and import only missing or updated assets.
7. Keep source datasets separate until geometry and coverage have been compared. Never silently replace conflicts between OSM, Microsoft, DPWH, elevation, or imagery.
8. Prioritize streets, building footprints, real facades, roofs, building heights, windows, doors, signs and materials. Trees are lower priority.
9. Do not claim a source has been downloaded or visually verified unless the file exists in the repository and the check actually succeeded.

## Existing assets and important limits

- OSM roads/buildings and Microsoft building footprints already exist; inspect and reuse them.
- Copernicus DEM GLO-30 crop and its GLB terrain mesh already exist. This is regional DSM context, not a high-resolution building-roof survey.
- DPWH road/bridge layers already exist; inspect and reuse them.
- KartaView images and metadata already exist. Keep KartaView out of the live map renderer as previously requested; do not download duplicate image IDs.
- Procedural facade details are placeholders, not measured real facades. Keep this distinction explicit.

## Workflow acceptance checklist

- [ ] Existing repository data was inspected before download.
- [ ] Only missing/new data was fetched.
- [ ] Actual files are committed to the repository, not just artifacts.
- [ ] Source, date, extent, CRS/resolution and QA result are recorded.
- [ ] Data is checked for AOI coverage and alignment.
- [ ] The viewer/build uses the relevant committed asset when suitable.
- [ ] Workflow can run again without re-downloading or duplicating existing assets.
