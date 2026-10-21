# ADAM CITY

A source-traceable 3D city-data project focused on Ermita and Malate, Manila.

## Start here

- [Repository structure and naming rules](docs/repository-structure.md)
- [Data asset policy](docs/data-asset-policy.md)
- [Data source catalog](docs/data-source-catalog.md)
- [Data audit report](docs/data-audit-report.md)
- [MapLibre + Three.js GLB rendering and coordinate rules](docs/maplibre-threejs-glb-rendering.md)
- [3D preview page](ermita-malate-3d.html)

## Core rules

1. Reuse valid committed data before fetching anything. Download only missing or invalid source assets.
2. Keep source datasets separate; never silently replace OSM geometry with basemap or other-source geometry.
3. Keep source files, derived outputs, reports, and preview assets in the repository.
4. Validate both the saved data and deployed page; a successful workflow alone does not prove the map rendered correctly.
5. Work on main; do not create project branches without explicit instruction.

The repository contains historical snapshots and scripts that may use legacy paths. Consult the structure guide before moving or renaming any referenced asset.


## Repository map

- `docs/` — policy, source catalog, audit and organization records.
- `ermita/` — area data and generated assets.
- `kartaview/` — KartaView imagery and review index (legacy path currently referenced by metadata and scripts).
- `backup/` — historical snapshots and recovery copies.
- `ermita/scripts/` — Ermita-specific importers and processing scripts used by deployment.
- `ermita-malate-3d.html` — GitHub Pages preview entry point.
