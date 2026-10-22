# Ermita building GLB parts — permanent assets

These six GLBs are committed, manually editable assets. **They are not generated during deployment.** The generator script `ermita/scripts/export_ermita_buildings_glb_parts.py` has been deleted and the deployment workflow has no command that recreates these files.

| Model | Approximate coverage center | Source features | Polygon/mesh components | Inventory |
|---|---|---:|---:|---|
| [buildings_part1.glb](buildings_part1.glb) | Northwest — 120.970369, 14.608766 | 187 | 32,227 | [inventory](buildings_part1-inventory.json) |
| [buildings_part2.glb](buildings_part2.glb) | Southwest — 120.976819, 14.595345 | 187 | 2,321 | [inventory](buildings_part2-inventory.json) |
| [buildings_part3.glb](buildings_part3.glb) | South-central — 120.986357, 14.584853 | 187 | 1,798 | [inventory](buildings_part3-inventory.json) |
| [buildings_part4.glb](buildings_part4.glb) | North-central — 120.992787, 14.593576 | 187 | 30,850 | [inventory](buildings_part4-inventory.json) |
| [buildings_part5.glb](buildings_part5.glb) | East-central — 121.009509, 14.580671 | 187 | 70,246 | [inventory](buildings_part5-inventory.json) |
| [buildings_part6.glb](buildings_part6.glb) | Southeast — 121.019610, 14.567054 | 188 | 812 | [inventory](buildings_part6-inventory.json) |

Coverage descriptions are approximate and are not official neighborhood boundaries. Each model must use its own origin sidecar because the six models have different local origins. Inventory files list source feature IDs, source properties, heights, material information and polygon counts.

See [buildings_parts_index.json](buildings_parts_index.json) for the machine-readable mapping and [buildings_parts_report.json](buildings_parts_report.json) for validation totals.
