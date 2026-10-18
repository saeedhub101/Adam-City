# Adam City — Malate & Ermita 3D Walk

A browser-based Three.js exploration game for **Malate and Ermita, Manila, Philippines**. The goal is to build a larger, explorable city using cached OpenStreetMap geometry, named streets, points of interest, and increasingly detailed 3D landmarks.

**Live game:** https://saeedhub101.github.io/Adam-City/

## Critical rule: imported data must be saved to GitHub

> **Never make the game depend on re-downloading map data on every build or every play session.**

Whenever we import, generate, enrich, or update map geometry, street names, points of interest, transport data, or other persistent game data:

1. Save the result into the repository (normally under `maps/`).
2. Validate the output and preserve the existing cache if the import fails or returns incomplete data.
3. Commit and push the updated files to the `main` branch.
4. Confirm the commit exists on GitHub and check the relevant GitHub Actions run.
5. Make the game read the committed local JSON files first. Online sources should be used for deliberate data-update workflows, not as a requirement to rebuild the world every time a player opens the game.

**A successful download is not a completed task until its useful output is saved and committed to GitHub.** Never replace a populated cache with an empty or failed response. Do not leave valuable generated data only in a temporary workflow runner or artifact.

### Map-data files

| File | Purpose |
| --- | --- |
| `maps/malate-map.json` | Cached OSM geometry used to build roads, buildings, railways, water and other map features. |
| `maps/malate-streets.json` | Cached named road segments and coordinates for street signs and street search. |
| `maps/malate-places.json` | Cached points of interest and business/place markers. |
| `.github/workflows/expand-ermita-map.yml` | Imports expanded Malate–Ermita geometry and should commit its results back to the repository. |
| `.github/workflows/cache-malate-map.yml` | Refreshes place/POI data while preserving the existing geometry and street cache. |

The map sources currently include **OpenStreetMap**. Keep appropriate attribution in the game and repository documentation. Generated facade textures are procedural game art; do not describe them as real photographs.

## Game structure

- **`index.html`** — the main game: page styling and HUD, Three.js scene, player movement/camera, road/building/rail rendering, street labels, search, markers and discovery objectives.
- **`maps/malate-map.json`** — cached physical map geometry.
- **`maps/malate-streets.json`** — street names and road coordinates.
- **`maps/malate-places.json`** — searchable landmarks and place markers.
- **`.github/workflows/`** — repeatable data import and build/deployment automation.
- **GitHub Pages** — publishes the static game from the repository. The game should continue to load its committed map data even when an external map API is temporarily unavailable.

The game is a static site and does not require npm/Vite for its basic deployment. Three.js is loaded from a CDN, so rendering still requires an internet connection unless that dependency is later bundled locally.

## Current direction and how we will continue

1. **Keep the game build healthy.** Check the latest GitHub Actions results after code or workflow changes and fix failures before adding more features.
2. **Persist and verify the expanded map.** Import Malate, Ermita and connecting streets; save geometry and street-name JSON to GitHub; confirm the commit and Pages deployment. Avoid concurrent workflow pushes overwriting one another.
3. **Render the whole cached region.** Ensure renderer bounds, rail/area filters, search and movement allow players to explore the expanded data rather than silently clipping it to the original block.
4. **Improve navigation.** Keep street-name boards readable and aligned, make street/business search reliable, and improve map feedback when no match is found.
5. **Improve landmarks and transport.** Refine mall, restaurant, hotel and shop facades; add distinctive signs and storefront layouts; improve LRT-1 track, stations, platforms and surrounding street details. Procedural/generated assets should be clearly distinguished from real photo references.
6. **Add richer city life.** Gradually add crossings, signals, sidewalks, street furniture, traffic and pedestrians while keeping performance reasonable on desktop and mobile.
7. **Test every milestone.** Verify the game build/screenshot workflow, GitHub Pages deployment, map JSON loading, search, movement and rendering after each meaningful change.

Work in small commits with clear messages. Prefer extending existing systems and cached data over replacing working features. If a workflow fails, inspect its logs, fix the underlying cause, rerun it, and verify the data commit and deployment.

## Controls

- **W / A / S / D** or **arrow keys** — move
- **Shift** — sprint
- **Drag the scene** — look around
- **On-screen directional pad** — move on touch devices
- **Search box** — find cached streets and places

## Map data and attribution

Map geometry is derived from OpenStreetMap data. Include attribution such as **© OpenStreetMap contributors** in the game UI or map-information area and keep the data source documented. Cached data can be incomplete or change over time; imported map geometry is a basis for the game world, not a guarantee of survey-grade accuracy.

## Development checklist

- [ ] Map and POI updates are committed to GitHub.
- [ ] Failed imports preserve existing valid data.
- [ ] Map-import workflow completes without a push race.
- [ ] Expanded Ermita geometry is actually rendered and walkable.
- [ ] Street names and place search work across the full map.
- [ ] Game build/screenshot workflow succeeds.
- [ ] GitHub Pages deployment succeeds.
