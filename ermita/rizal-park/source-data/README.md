# NPDC tree inventory source-data imports

## Imported files

- `npdc-tree-inventory-2024-source-export.csv` — the CSV export retrieved from the public NPDC-linked Google Sheet on 2026-10-18. The export contains 30 data rows and 18 columns including blank columns.
- `npdc-tree-inventory-2024-coordinate-normalization.csv` — same 30 source rows with original tree number/name/taxonomy fields, raw source row preserved as JSON, original longitude/latitude DMS strings, and decimal-degree coordinate conversions where parseable.

Original public spreadsheet: https://docs.google.com/spreadsheets/d/1WfMFbHG9Tam6MtL6X1YYRAQ0zvMP2Upn/edit

## Important limitations

1. This is the visible tab/export returned by Google Sheets CSV export, not proof that the workbook contains all Rizal Park trees. It contains 30 rows only.
2. The sheet's header includes blank columns, and some data rows have non-empty values in trailing columns that do not align consistently with the named header fields. Therefore, this import preserves all original row values and labels uncertain columns `source_col_7`, `source_col_8`, and `source_col_9` rather than guessing measurement meaning.
3. Longitude/latitude values in the source are DMS strings such as `E 120 58 48.34` and `N 14 34 58.51`; decimal-degree values are calculated from those strings. They have not been independently checked against a basemap.
4. Do not treat the 30 records as a complete park inventory. The source appears to represent only a small section/subset. Obtain and reconcile the original workbook, its tabs, and the other NPDC downloadable inventories before producing park-wide counts.
5. The original XLSX download was tested successfully (HTTP 200, 533,032 bytes) but is not yet mirrored in this repository. The CSV export and coordinate-normalized table are the files actually imported.

## QA summary

- Source rows imported: 30
- Raw source columns: 18 (including blank columns)
- Coordinates: retained as source DMS plus calculated decimal degrees
- Individual tree IDs: source IDs preserved
- Species, DBH, height, health, defects and risk: preserve original values; do not silently correct shifted/ambiguous columns
- Outstanding: verify workbook tabs, column semantics, missing fields, coordinate range, duplicate tree IDs and coverage extent
