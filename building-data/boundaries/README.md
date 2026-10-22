# Barangay boundary evidence for Ermita

This folder contains candidate boundary data and a reproducible audit trail for assigning the pilot building records to barangays. The candidates are **not certified administrative assignments**.

## Files

- `ermita-geodata-barangay-candidates.geojson` — 85 City of Manila polygons returned by the GEODATA/Philippine Digital Atlas FeatureServer query for WGS84 bbox `[120.9700, 14.5720, 120.9945, 14.5985]`. Source: https://services7.arcgis.com/poQdgvLD6DHnbpsT/ArcGIS/rest/services/Philippine_Administrative_Boundaries/FeatureServer/3. Queried 2026-10-22. Geometry rounded to 6 decimal places. Publisher warns that features are derived from multiple sources and positional accuracy is not guaranteed.
- `ermita-barangay-candidates.geojson` — 63 candidate polygons extracted from the 42,026-feature PH Barangay Boundaries & PSGC GeoJSON snapshot. Source: https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/barangays.geojson. The publisher documents PSGC snapshot 2023-10-24 and NAMRIA shapefile version 2023-11-06, requests PSA/NAMRIA attribution, and notes coverage/matching gaps.
- `barangay-spatial-join-audit.csv` — centroid point-in-polygon results for the 30 pilot building records against the GEODATA candidate polygons.

## Pilot result

- 29 of 30 building centroids fell inside exactly one candidate polygon.
- 1 building centroid (`way/29282233`, Manila Ocean Park) did not fall inside any returned candidate polygon.
- No centroid matched multiple polygons in this sample.
- All single-polygon results are marked `candidate_single_polygon_match_review_required`; the unmatched building is `no_polygon_match_review_required`.

## Important limitations

1. A bounding-box query returns candidate polygons around the area, not an official boundary for Ermita itself.
2. The GEODATA publisher explicitly disclaims guaranteed positional accuracy. The PSGC/NAMRIA-derived dataset includes fuzzy matches and some repeated PSGC codes, so do not use PSGC code alone as a unique key.
3. Ermita is a Manila submunicipality; it is not itself a barangay. Do not infer its boundary by unioning a guessed set of barangays.
4. The audit uses each building polygon's computed centroid. A centroid may lie outside a concave building polygon; future production processing should compare centroid and representative point, test geometry validity, and record distance to boundaries.
5. Do not copy candidate names into the canonical building register as verified until cross-source checks and review are complete.

## Attribution

Boundary sources are described as derived from PSA/NAMRIA/Philippine Digital Atlas materials. Keep source URLs and the attribution/disclaimer with any downstream use. Check the source publisher's current license/redistribution terms before shipping the data in a public product.
