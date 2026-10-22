# Ermita buildings — split GLB exports

Six GLB files generated from the complete ermita-building-footprints.geojson source. Every source feature is assigned to exactly one part; every polygon component is exported, without corridor filtering or minimum-area filtering. Each GLB has an -origin.json placement sidecar and an -inventory.json listing source properties and IDs. The report records source/export counts and fails generation if coverage is incomplete.

Use the part-specific origin metadata when positioning each GLB; the six files use different local origins to maintain mesh precision.
