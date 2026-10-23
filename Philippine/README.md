# Philippine consolidation
The workflow scans repository-wide .geojson, GeoJSON-named .json, and .csv sources. It merges records by coordinates rounded to six decimal places or a stable ID, retains source filenames, fills missing fields, and records conflicting values for review rather than stopping.

- `CSV/Philippine01.csv`, `Philippine02.csv`, …
- `GeoJSON/Philippine01.geojson`, `Philippine02.geojson`, … (one Feature JSON object per line / JSONL)
- `error/` contains malformed records, missing-key records, geometry disagreements, and attribute conflicts.
- `progress.json` updates as each source file is processed; `report.json` summarizes the run.

Chunk target is approximately 1.8 MB. Workflow timeout is six hours, newer runs do not cancel it, and the script pushes checkpoint commits while processing.
