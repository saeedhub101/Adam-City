# Adam City — Open-World 3D City Experiments

Adam City is a collection of browser and desktop 3D city-exploration prototypes. The repository contains a Manila street/map experience, a separate Vite-based 3D game with Tabarbour (Amman, Jordan) map/photo data, and a Helsinki photogrammetry asset pipeline.

- **GitHub Pages entry point:** https://saeedhub101.github.io/Adam-City/
- **Repository:** https://github.com/saeedhub101/Adam-City
- **Primary branch:** `main`

> Before changing code or data, inspect the existing files and workflows so updates extend the project rather than replacing working features or cached data.

## Project layout

| Path | Role |
| --- | --- |
| `index.html` | Root-level static Three.js game deployed through GitHub Pages; currently branded around A. Mabini Street / Malate, Manila. |
| `maps/` | Persistent Malate/Ermita map caches: geometry, named streets, and places. |
| `game/index.html` | Separate Vite-based 3D game entry point; currently presents a controllable third-person A. Mabini Street scene. |
| `game/src/main.js` | Vite game's main source, including photo catalogues, Google Street View integration, map/photo UI and scene initialization. |
| `game/src/helsinki.js` | Helsinki photogrammetry loading module. |
| `game/public/data/` | Static game data, including Tabarbour OSM snapshots and photo catalogues. |
| `game/public/data/tabarbour-custom.json` | Project-owned Tabarbour map overrides; OSM refreshes must not overwrite this file. |
| `game/public/models/helsinki/` | Helsinki mesh assets used by the desktop build/cache. |
| `scripts/` | Reusable map, photo-catalogue and mesh data scripts. |
| `1/assets/cities/` | Existing city model/material assets, including Tabarbour and San Francisco. |
| `.github/workflows/` | Automated map refreshes, photo collection, browser checks and Windows executable builds. |

There is more than one game/data path. Do not assume every feature belongs to the root `index.html`; inspect the relevant entry point and workflow before making changes.

## Persistent map and photo data

### Manila: Malate and Ermita

| File | Purpose |
| --- | --- |
| `maps/malate-map.json` | Cached OpenStreetMap geometry for roads, buildings, railways, water and other map features. |
| `maps/malate-streets.json` | Named road segments and coordinates for street labels/search. |
| `maps/malate-places.json` | Cached points of interest and place markers. |
| `.github/workflows/expand-ermita-map.yml` | Imports expanded Malate/Ermita geometry and refreshes named street data. |
| `.github/workflows/cache-malate-map.yml` | Enriches the POI cache while requiring existing map and street files to be present. |

### Tabarbour: Amman, Jordan

| File | Purpose |
| --- | --- |
| `game/public/data/tabarbour-osm.json` | Versioned OSM building/road snapshot loaded by the game before a live fallback. |
| `game/public/data/tabarbour-custom.json` | Project-owned edits/overrides; OSM refreshes must not overwrite it. |
| `game/public/data/tabarbour-photo-catalog.json` | Nearby Wikimedia Commons photo catalogue and metadata/licences. |
| `game/public/data/mapillary-photo-catalog.json` | Mapillary photo catalogue used when available. |
| `game/public/data/kartaview-photo-catalog.json` | KartaView photo catalogue used when available. |
| `game/public/data/bundled-photo-catalog.json` | Preferred bundled photo catalogue when present. |
| `.github/workflows/refresh-tabarbour-map.yml` | Scheduled/manual refresh of a bounded Tabarbour clip from Geofabrik's Jordan extract. |
| `.github/workflows/collect-tabarbour-photos.yml` | Collects photo metadata and licences. |
| `.github/workflows/collect-mapillary-photos.yml` | Mapillary street-photo collection. |
| `.github/workflows/build-tabarbour-facades.yml` | Builds facade assets from available street imagery. |

The Tabarbour workflow clips a small area from the Jordan PBF extract rather than committing a whole-country map. Keep datasets geographically scoped and split large regions/layers into manageable files.

### Helsinki and desktop build

- `game/src/helsinki.js` loads the Helsinki photogrammetry scene.
- `scripts/download_helsinki_mesh.py` prepares the source mesh.
- `.github/workflows/build-windows-exe.yml` builds a portable Windows executable and verifies the Helsinki mesh and textures are bundled.
- Artifacts are useful outputs, but reusable source/data must be committed or cached intentionally, not left only on a temporary runner.

## Non-negotiable data and Git rules

1. **Work on `main` only. Never create a branch.**
2. Read the current README, relevant source files, existing data, and workflow before changing anything.
3. Inspect the committed cache before importing and identify exactly what is missing or needs refreshing.
4. Save useful imported/generated data in repository files so future builds and sessions can reuse it. A successful download alone is not a finished task.
5. Prefer committed local JSON/assets at runtime. Network requests should normally belong to deliberate update workflows, not be required to reconstruct the world whenever the game starts.
6. Validate imports before replacing existing data: check schema, expected categories and counts; reject empty or clearly incomplete results. If a source fails or returns partial data, preserve the previous valid snapshot and merge only verified results.
7. Merge by stable source IDs (such as OSM element type + ID) to avoid duplicates and preserve useful existing fields. Keep project-owned overrides separate from upstream snapshots.
8. Split large datasets by region, layer, or purpose. Do not add a whole-country map or oversized single JSON when a regional extract is sufficient.
9. Commit directly to `main` with clear messages. Verify the commit and relevant Actions run, then verify Pages deployment or desktop artifact when applicable.
10. Workflows that write to `main` must handle concurrent updates safely. Use workflow-specific concurrency where appropriate, avoid overlapping writes, rebase data-only commits onto latest `origin/main` before pushing, and fail safely on conflicts. Never force-push over newer work.
11. Do not run overlapping data writers against the same files. If a push is rejected or rebase conflicts, inspect latest `main`, preserve both valid changes, and retry safely.
12. Preserve attribution and licences. OSM-derived data must be attributed as **© OpenStreetMap contributors**. Use real photos only with appropriate rights/credit; do not present procedural facade art as real photography.

## Workflows and verification

- `.github/workflows/game-screenshot.yml` runs a browser smoke test for the root Pages entry point: canvas initialization, Start button, HUD, movement input and screenshot capture.
- `.github/workflows/refresh-tabarbour-map.yml` refreshes the regional Tabarbour OSM snapshot on a schedule or manual dispatch.
- `.github/workflows/collect-tabarbour-photos.yml` refreshes licensed photo metadata.
- `.github/workflows/build-windows-exe.yml` builds and checks the Windows executable and bundled Helsinki mesh.
- Manila workflows import/merge map geometry, street names and POIs into `maps/`.

When a workflow fails:
1. Find the first real failing step and error in its logs.
2. Separate upstream API/source failures from code, validation, and Git push failures.
3. Fix the cause rather than hiding errors or weakening validation.
4. Rerun the relevant workflow.
5. Confirm it completed, reusable data is committed to `main`, and the expected site/build/artifact works.

A push race is a Git synchronization problem, not proof that map data is bad. Reconcile the workflow commit with latest `main`; do not discard another workflow's changes.

## Runtime and configuration

- The root GitHub Pages experience is static and loads Three.js from a CDN.
- The `game/` experience is a separate Vite/Three.js app and supports a Windows executable build.
- Google Street View in `game/src/main.js` reads `VITE_GOOGLE_MAPS_API_KEY` from the build environment. Configure it as an appropriate repository/environment secret; never hard-code API keys in committed source.
- External map/photo providers can be unavailable or have no coverage. Optional sources should fail gracefully while committed data remains usable.
- Map coordinates and photo-to-building associations can be incomplete. Associate a photo with a building only when evidence supports the match; never guess based only on proximity.

## Development priorities

- Keep both the root Pages game and separate `game/` app healthy; test the correct entry point for each change.
- Ensure Malate/Ermita geometry, street names and places cover the intended region and are rendered/searchable.
- Keep Tabarbour's regional snapshot, custom overrides and licensed photo catalogues persistent and distinct.
- Improve facades with licensed references when available, without inventing photo matches.
- Keep Helsinki mesh assets reproducible and verify they are included in desktop builds.
- Improve navigation, movement, performance, touch controls, and data fallbacks incrementally.

## Controls

For the root Malate/Ermita experience: **W/A/S/D** or arrow keys to move, **Shift** to sprint, drag to look around, touch directional pad on mobile, and search to find cached streets/places.

For the separate `game/` scene: use **WASD/arrow keys**, mouse drag to look, and on-screen controls on touch devices.

## Attribution

Map geometry is derived from OpenStreetMap data. Include **© OpenStreetMap contributors** in the game UI or map-information area and document the source. Photo catalogues should retain each image's source page, author/attribution, and licence. Cached data can be incomplete or change over time and is not survey-grade information.

## Checklist for every change

- [ ] Read the relevant existing files and understand their role.
- [ ] Work on `main` only; do not create branches.
- [ ] Preserve working code, existing map snapshots, and project-owned overrides.
- [ ] Validate and merge new data instead of destructively replacing good data.
- [ ] Keep datasets small, regional and/or layered.
- [ ] Commit reusable data and code to GitHub.
- [ ] Verify the commit and relevant GitHub Actions result.
- [ ] Verify the relevant browser/Pages or Windows build result.
