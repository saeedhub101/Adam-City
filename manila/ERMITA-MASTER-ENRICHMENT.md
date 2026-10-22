# Ermita master-data enrichment — workflow and audit log

## Purpose and current status

This document is the working procedure for enriching the Ermita building master data. The aim is to fill missing building-specific metadata from sources already stored in this repository first, then research only the remaining gaps. The master dataset currently contains 24,102 CSV rows across 193 columns and 22,977 GeoJSON features split into two parts. These counts describe records/features, not necessarily unique physical buildings.

**Important status:** the exact-ID enrichment script and its workflow integration are committed, but the data pass must not be described as completed until the GitHub Actions run succeeds and the generated report is inspected. The first-30 audit is a baseline completeness check, not proof that those buildings have no useful external imagery.

## Workflow stages

### 1. Preserve and inventory the source data

Master files:
- `manila/manila/ermita-buildings-master.csv`
- `manila/manila/ermita-buildings-master.parts/part-001.geojson`
- `manila/manila/ermita-buildings-master.parts/part-002.geojson`
- `manila/manila/ermita-buildings-master-manifest.json`

The manifest records the source-file inventory and SHA-256 values. Keep all rows and features, including possible duplicates across sources. Do not use deduplication as a shortcut to decide that two footprints are the same building.

### 2. Run the conservative internal exact-ID pass

Run from the repository root:

```bash
python3 manila/enrich_ermita_master_data.py
```

Current inputs used by this script:
- `complete_data/OSM/data/buildings/Ermita/osm-building-details.csv`
- `complete_data/OSM/quality/building-height-evidence.csv`
- `ermita/3d/building-match-audit.csv`

The wider repository inventory in the manifest contains other candidate sources, but **this script does not yet ingest all 19 CSV sources**. The remaining files are inputs for later crosswalk, review, and verification stages; they must not be represented as already merged.

The script adds these fields to the master CSV rows and GeoJSON feature properties:
- `enriched_name`, `enriched_official_name`, `enriched_building_type`
- `enriched_height_m`, `enriched_levels`, `enriched_roof_shape`
- `enriched_house_number`, `enriched_street`, `enriched_postcode`, `enriched_city`
- `enriched_material`, `enriched_facade_colour`, `enriched_roof_material`, `enriched_roof_colour`
- `enrichment_sources`, `enrichment_status`

Values are copied only when a valid explicit OSM ID matches. If source files provide conflicting values for the same field, that field is left blank in the enriched output and the conflict is recorded in the report. Existing source columns are not intentionally overwritten.

Statuses:
- `exact_osm_id_enriched`: at least one non-conflicting field was supported by an exact-ID source match.
- `conflict_review`: at least one field has conflicting source values. Other unconflicted fields may still be filled.
- `no_exact_id_evidence`: no usable evidence was found through the exact-ID pass.

Generated report:
- `manila/manila/ermita-master-enrichment-report.json`

The report must be reviewed for row/feature counts, populated fields, conflicts, and status counts before this stage is accepted.

### 3. Run it through the existing GitHub Actions workflow

The enrichment is part of the existing `.github/workflows/deploy-pages.yml`; no separate workflow was created.

The enrichment step runs when either:
- the workflow is started manually with **workflow_dispatch**, or
- a push commit message contains the exact phrase `Run Ermita master enrichment`.

It is not designed to rewrite the large master files on every ordinary push. The workflow checks out the committed data and script, runs the script, then commits the modified master CSV, both GeoJSON parts, and JSON report if they changed. The workflow subsequently assembles and deploys the existing site assets.

Workflow run to inspect:
https://github.com/saeedhub101/Adam-City/actions

A successful Pages deployment alone is not sufficient evidence that enrichment ran: check the enrichment step logs and confirm that the report exists and matches the processed files.

### 4. Build a conservative crosswalk for unmatched records

After reviewing the exact-ID report, inspect other repository sources, including:
- `complete_data/OSM/data/buildings/Ermita/building-source-link-audit.csv`
- `complete_data/OSM/data/buildings/Ermita/building-visual-research-queue.csv`
- `complete_data/OSM/data/buildings/Ermita/building-image-candidates.csv`
- `ermita/maps/qa/consolidated-building-register.csv`
- `ermita/maps/qa/non-osm-building-footprint-crosswalk.csv`
- `ermita/3d/facade-photo-review.csv`
- `kartaview/ermita-real-facade-images.csv` and the facade-crops manifests

These sources have different IDs and levels of verification. Do not treat a candidate or proximity match as confirmed. Use source IDs first. Any spatial match must pass geometry/overlap checks and be reviewed where ambiguity remains; preserve unresolved records in a review queue.

### 5. Verify imagery before adding visual details

For each proposed photo:
1. Open and inspect the actual image.
2. Verify that it depicts the specific building and the correct facade/roof.
3. Check the image location, viewing direction, capture date where available, and footprint alignment.
4. Record the image/source URL, access date, match method, and confidence.
5. Only then record observed facade colour/material, windows, doors, balconies, signage, or roof details.

A filename, business name, nearby coordinate, or candidate-list entry alone is not proof that the image belongs to a footprint. Never invent architectural measurements or assign an unverified image as a texture.

### 6. Research external sources only for remaining important gaps

Once internal sources and images have been reviewed, use authoritative sources where available (official building/institution websites, government records, reliable mapping/photo records, or well-sourced reference pages). Record per-field provenance, URL, access date, confidence, and conflicting claims. Keep uncertain fields blank or explicitly flagged instead of silently choosing a value.

### 7. Quality checks before accepting a pass

- Compare input and output CSV row counts and GeoJSON feature counts.
- Confirm that geometry, coordinates, feature IDs, source IDs, existing attributes, and render-height values did not change.
- Review all conflict fields and representative joined records.
- Confirm that no source rows/features were deleted or merged.
- Confirm that the report is committed and that the action log shows the enrichment step succeeded.
- Keep visual reconstruction completeness separate from metadata completeness.

## Safety invariants

- Metadata enrichment only: do not alter geometry, coordinates, source IDs, feature IDs, or rendering heights.
- Do not delete or merge rows/features just because they may refer to the same physical building.
- Do not infer exact height from floor count or OpenFreeMap render height.
- Do not treat candidate imagery as verified facade evidence.
- Do not invent names, addresses, materials, colours, roof forms, windows, or dimensions.
- Record provenance and conflicts; keep ambiguous matches for review.

## Baseline: first 30 building audit

See [the first-30 building audit](manila/ermita-buildings-master.parts/part-001-first30-building-audit.md) and its row-level CSV. It found 0 of 30 records complete for realistic building-specific reconstruction under the audit criteria. That means more evidence is needed, not that no external photos exist.

## Change log

- Added the conservative exact-OSM-ID enrichment script and wired it into the existing Pages workflow.
- Documented above the exact script inputs, generated fields/report, trigger conditions, safety constraints, and follow-up stages.
- Do not mark the enrichment data pass complete until a successful action run and report review are recorded.
