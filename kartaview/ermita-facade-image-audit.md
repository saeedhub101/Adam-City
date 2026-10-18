# KartaView Existing Facade Image Audit

**Audit date:** 2026-10-18  
**Branch:** `main`  
**Scope:** repository tree, `kartaview/ermita-real-facade-images.csv`, and `kartaview/ermita-real-facade-report.json`. This is a file-index consistency audit, not a visual verification of facade matches.

## Findings

| Check | Result |
|---|---:|
| Facade match CSV data rows | 246 |
| Unique photo IDs in CSV | 246 |
| Duplicate photo IDs detected | 0 |
| Rows marked `downloaded` | 238 |
| Downloaded rows whose referenced local path exists in the Git tree | 238 |
| Image files currently present under `kartaview/images/` | 239 |
| Image file not referenced by the facade CSV by filename/photo ID | 1 |

The unreferenced image is:

- `kartaview/images/2562601769.jpg`

## Interpretation

- The 238 rows marked downloaded all have a matching local path in the repository tree.
- The directory contains one additional image, `2562601769.jpg`, which is not indexed in the facade CSV by photo ID. It may belong to another index or be an orphaned file; **do not delete it** until all repository references and its origin are checked.
- The CSV has 246 unique photo IDs, but uniqueness does not prove every image is correctly matched to a building.
- This audit does not inspect image pixels, EXIF metadata, URL reachability, exact facade identity, camera calibration, or license metadata embedded in derivatives.
- The related report records 740 unique API photos found, 246 matched to buildings, and 238 downloaded. Metadata discovery records are broader than the downloaded facade subset.

## Next validation

1. Re-run this audit using a real CSV parser (quoted fields can contain commas); verify all columns and paths rather than relying only on line counts.
2. Search the full repository for references to `2562601769.jpg`, inspect the image's source URL/metadata and determine whether it belongs in the facade CSV or another index.
3. Generate a review table with photo ID, OSM building ID/name, wall distance, heading difference, capture date, local path, and a human-review decision.
4. Keep the required attribution `© Grab and KartaView Contributors` and follow KartaView's CC BY-SA 4.0 terms: https://kartaview.org/terms
5. Do not download photos again just to rebuild the index. Fetch only a photo that is proven missing and is not already present by ID or local path.

## Related files

- `kartaview/ermita-real-facade-images.csv`
- `kartaview/ermita-real-facade-report.json`
- `kartaview/ermita-street-imagery-metadata-report.json`
- `ermita/research/next-data-acquisition-and-qa-plan.md`
