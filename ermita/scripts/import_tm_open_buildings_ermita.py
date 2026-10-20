#!/usr/bin/env python3
"""Coverage-aware TM Open Buildings importer for Adam City / Ermita.

TM Open Buildings is a free, separately licensed dataset, but its published
coverage is a set of selected 250 m tiles in 12 named Philippine cities. Manila
is not in that list. This script therefore records an explicit no-coverage
result for Ermita rather than downloading an unrelated national dataset or
inventing coverage. It is safe to run repeatedly and never overwrites other
providers' building geometry.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "ermita" / "maps" / "sources" / "tm-open-buildings"
REPORT = OUT_DIR / "tm-open-buildings-ermita-import-report.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_URL = "https://github.com/thinkingmachines/ph-open-buildings"
DATASET_URL = "https://www.kaggle.com/datasets/thinkdatasci/tm-open-buildings-philippines"
LICENSE = "Open Database License (ODbL); derivative database must comply with share-alike terms."
PUBLISHED_CITIES = [
    "Dagupan City",
    "Palayan City",
    "Navotas",
    "Mandaluyong",
    "Muntinlupa",
    "Legazpi City",
    "Tacloban City",
    "Iloilo City",
    "Mandaue City",
    "Cagayan de Oro City",
    "Zamboanga City",
    "Davao City",
]


def main() -> int:
    # Manila / Ermita is not among the source's published coverage cities.
    report = {
        "source": "TM Open Buildings - Philippines",
        "source_repository": SOURCE_URL,
        "dataset_download_page": DATASET_URL,
        "license": LICENSE,
        "area_of_interest": "Ermita / Rizal Park, Manila, Philippines",
        "published_coverage_cities": PUBLISHED_CITIES,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "status": "no_coverage_for_aoi",
        "downloaded": False,
        "feature_count": 0,
        "output_file": None,
        "reason": (
            "The published dataset covers selected 250 m tiles in 12 cities; Manila is not listed. "
            "No TM Open Buildings polygons can be claimed for Ermita from this release, so the "
            "importer intentionally does not download unrelated tiles or create synthetic features."
        ),
        "next_action": (
            "Revisit only if the provider publishes Manila/Ermita coverage. If TM data are later "
            "obtained for an area, preserve the original dataset separately and spatially match "
            "individual polygons to current building footprints before transferring attributes."
        ),
        "attributes_described_by_source": [
            "roof material for selected individual settlement buildings",
            "roof layout for selected individual settlement buildings",
            "roof area",
            "gated-community indicator",
            "coarse building-height category for non-settlement buildings",
        ],
        "matching_policy": (
            "No shared OSM ID is guaranteed by a standalone satellite-derived polygon. Any future "
            "matching must use polygon overlap, centroid distance, and shape checks; uncertain "
            "matches remain flagged for review."
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
