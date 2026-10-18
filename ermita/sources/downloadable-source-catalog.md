# Downloadable source catalog — Ermita and Rizal Park

**Source checked:** 2026-10-18. This is a link-and-ingestion register for publicly reachable source files. Files are not claimed to be mirrored into this repository unless a repository path is explicitly shown. NPDC's downloads page states government content is public domain unless otherwise stated; verify any third-party or separately licensed material before mirroring it.

## NPDC official downloadable sources

| Asset | Direct source / download | Recommended repository destination | Ingestion status |
|---|---|---|---|
| Rizal Park technical map (JPG) | https://npdc.gov.ph/wp-content/uploads/2024/05/Rizal-Park-Technical-Map-scaled.jpg | `ermita/rizal-park/source-assets/Rizal-Park-Technical-Map-scaled.jpg` | Direct image verified; map labels transcribed to `park-map-feature-index.csv`; binary not mirrored by current text-file upload workflow |
| Rizal Park brochure (PDF) | https://npdc.gov.ph/wp-content/uploads/2021/06/Rizal-Park-Brochures.pdf | `ermita/rizal-park/source-assets/Rizal-Park-Brochures.pdf` | Direct PDF verified; not mirrored here |
| Rizal Park Luneta tree inventory 2024 (Google Sheet / XLSX source) | https://docs.google.com/spreadsheets/d/1WfMFbHG9Tam6MtL6X1YYRAQ0zvMP2Upn/edit?ouid=115574783122774806529&rtpof=true&sd=true&usp=drive_link | `ermita/rizal-park/source-assets/NPDC-Inventory-2024.xlsx` | Sheet opens publicly and displays columns/records; full XLSX export not ingested in this commit |
| Bachelor’s Garden Tree Inventory (PDF) | https://drive.google.com/file/d/1P_bhaFVcAoJ-k1L0TiuixBLBhyzfz2Iw/view?usp=drive_link | `ermita/rizal-park/source-assets/Bachelors-Garden-Tree-Inventory.pdf` | Public source link verified; not mirrored here |
| Kanlungan ng Sining Tree Inventory (PDF) | https://drive.google.com/file/d/1Yjrpi3yGYj7BPu4la60eEK-LI3UFEiOA/view?usp=drive_link | `ermita/rizal-park/source-assets/Kanlungan-ng-Sining-Tree-Inventory.pdf` | Public source link verified; not mirrored here |
| Noli Me Tangere Garden Tree Inventory (PDF) | https://drive.google.com/file/d/1xeSX2Z_miYu9l8uJNMuu1dyzFJJ4Bzvv/view?usp=drive_link | `ermita/rizal-park/source-assets/Noli-Me-Tangere-Garden-Tree-Inventory.pdf` | Public source link verified; not mirrored here |
| Western Section Tree Inventory (PDF) | https://drive.google.com/file/d/1K-fNRdlv4nrk-bjbRXVazyAjpWNd7tZt/view?usp=drive_link | `ermita/rizal-park/source-assets/Western-Section-Tree-Inventory.pdf` | Public source link verified; not mirrored here |
| Distribution Maps of Exotic Trees (Drive folder) | https://drive.google.com/drive/folders/1YPhKrub5hjoTjAINzZ_I1q1YJXPHUT5H?usp=drive_link | `ermita/rizal-park/source-assets/exotic-tree-maps/` | Folder link verified; individual contents not yet enumerated |
| Distribution Maps of Fruit-bearing Trees (Drive folder) | https://drive.google.com/drive/folders/1eQeodceuDWAm96CFabacgd4EeZLkZ2Hb?usp=drive_link | `ermita/rizal-park/source-assets/fruit-bearing-tree-maps/` | Folder link verified; individual contents not yet enumerated |
| Distribution Maps of Native Trees (Drive folder) | https://drive.google.com/drive/folders/10OysVTU9LdMsVGfjvVY6WfAqTUABMlw7?usp=drive_link | `ermita/rizal-park/source-assets/native-tree-maps/` | Folder link verified; individual contents not yet enumerated |
| Tree Thematic Maps (Drive folder) | https://drive.google.com/drive/folders/1NEwRpiiRsBzszpWS7wkoXc2xXY7HPn2J?usp=drive_link | `ermita/rizal-park/source-assets/tree-thematic-maps/` | Folder link verified; individual contents not yet enumerated |
| Tree Inventory Maps (Drive folder) | https://drive.google.com/drive/folders/1aDpL7a7yBdfp82j59mQkIuSXoeZUQe_h?usp=drive_link | `ermita/rizal-park/source-assets/tree-inventory-maps/` | Folder link verified; individual contents not yet enumerated |
| Tree distribution and thematic mapping report (PDF) | https://npdc.gov.ph/wp-content/uploads/2025/02/GIS-Group_Distribution-and-Thematic-Mapping-Report.pdf | `ermita/rizal-park/source-assets/GIS-Group_Distribution-and-Thematic-Mapping-Report.pdf` | Official PDF source known; analysis notes already in repository |
| 2024 native tree distribution map (PDF) | https://npdc.gov.ph/wp-content/uploads/2025/02/Inventory-Of-Trees.pdf | `ermita/rizal-park/source-assets/Inventory-Of-Trees.pdf` | Official PDF source known; reported summary in research notes |
| Rizal Park Complex Western Section Development Plan (PDF) | https://npdc.gov.ph/wp-content/uploads/2026/08/NPDC-Western-Section-Development-Project-PUBLIC.pdf | `ermita/rizal-park/source-assets/NPDC-Western-Section-Development-Project-PUBLIC.pdf` | Official 34-page PDF opened; not mirrored here |

Official source index: https://npdc.gov.ph/downloads/

## Tree spreadsheet columns observed

The public 2024 Google Sheet visibly labels these fields: Tree number, Common Name, Scientific name, Family Name, Tree Classification, Fruit-bearing, DBH, Height, Longitude, Latitude, Tree defects, Health, Structural integrity, Overall risk rating, Remarks. Some rows have blanks and some coordinate/field alignment appears inconsistent in the web-rendered preview. When importing the original workbook, preserve its raw values in a source table before cleaning or interpreting them; validate coordinates and the exact column order from the downloaded workbook rather than relying only on the web preview.

## Permission and ingestion policy

- The NPDC downloads page says government content is public domain unless otherwise stated. Prioritize mirroring official NPDC public-domain files with attribution.
- The fact that a file can be downloaded does not automatically grant permission to rehost third-party copyrighted material. For non-government files, keep the original download link and metadata unless a licence or permission supports mirroring.
- For OpenStreetMap, preserve attribution and follow ODbL obligations.
- Google Maps/Street View are kept as references; do not bulk-copy their imagery or map tiles.
- A link in this file means the source was found, not that the file has been copied into this repository.


## Import completed on 2026-10-18

The public Google Sheet's CSV export was downloaded successfully and committed as:
- `ermita/rizal-park/source-data/npdc-tree-inventory-2024-source-export.csv` (30 source rows)
- `ermita/rizal-park/source-data/npdc-tree-inventory-2024-coordinate-normalization.csv` (same 30 rows with DMS-to-decimal coordinates and original row JSON preserved)
- QA notes: `ermita/rizal-park/source-data/README.md`

The full XLSX export was also successfully downloaded for inspection (533,032 bytes), but is not yet mirrored into GitHub. The CSV endpoint returns 30 data rows, so this is a partial sheet export and must not be represented as the complete park-wide inventory.
