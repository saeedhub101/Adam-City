# ADAM CITY

A source-traceable 3D city-data project focused on Ermita and Malate, Manila.

## Start here

- [Repository structure and naming rules](REPOSITORY_STRUCTURE.md)
- [Data asset policy](DATA_ASSET_POLICY.md)
- [Data source catalog](DATA_SOURCE_CATALOG.md)
- [Data audit report](DATA_AUDIT_REPORT.md)
- [3D preview page](ermita-malate-3d.html)

## Core rules

1. Reuse valid committed data before fetching anything. Download only missing or invalid source assets.
2. Keep source datasets separate; never silently replace OSM geometry with basemap or other-source geometry.
3. Keep source files, derived outputs, reports, and preview assets in the repository.
4. Validate both the saved data and deployed page; a successful workflow alone does not prove the map rendered correctly.
5. Work on main; do not create project branches without explicit instruction.

The repository contains historical snapshots and scripts that may use legacy paths. Consult the structure guide before moving or renaming any referenced asset.
