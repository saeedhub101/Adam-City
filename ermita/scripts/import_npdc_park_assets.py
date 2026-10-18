#!/usr/bin/env python3
"""Download official NPDC reference assets with hashes and provenance.

Existing park-tree CSV datasets are deliberately not re-imported. Public access
does not itself establish an open redistribution licence; see the report.
"""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ermita/rizal-park/source-data/npdc-assets"
ASSETS = [
    {
        "filename": "rizal-park-technical-map-2024.jpg",
        "url": "https://npdc.gov.ph/wp-content/uploads/2024/05/Rizal-Park-Technical-Map-scaled.jpg",
        "description": "NPDC-published Rizal Park technical map",
        "expected": "image/jpeg",
    },
    {
        "filename": "rizal-park-brochure-2021.pdf",
        "url": "https://npdc.gov.ph/wp-content/uploads/2021/06/Rizal-Park-Brochures.pdf",
        "description": "NPDC-published Rizal Park brochure",
        "expected": "application/pdf",
    },
    {
        "filename": "distribution-and-thematic-mapping-report-2025.pdf",
        "url": "https://npdc.gov.ph/wp-content/uploads/2025/02/GIS-Group_Distribution-and-Thematic-Mapping-Report.pdf",
        "description": "NPDC GIS Group distribution and thematic mapping report",
        "expected": "application/pdf",
    },
    {
        "filename": "western-section-development-project-public-2026.pdf",
        "url": "https://npdc.gov.ph/wp-content/uploads/2026/08/NPDC-Western-Section-Development-Project-PUBLIC.pdf",
        "description": "NPDC public Western Section Development Project document",
        "expected": "application/pdf",
    },
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for item in ASSETS:
        target = OUT / item["filename"]
        request = urllib.request.Request(
            item["url"],
            headers={"User-Agent": "Adam-City-NPDC-reference-import/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(40 * 1024 * 1024 + 1)
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if len(data) > 40 * 1024 * 1024:
            raise RuntimeError(f"Refusing unexpectedly large asset (>40 MiB): {item['url']}")
        if item["expected"] == "application/pdf" and not data.startswith(b"%PDF-"):
            raise RuntimeError(f"Response is not a PDF: {item['url']} (Content-Type: {content_type})")
        if item["expected"] == "image/jpeg" and not data.startswith(b"\xff\xd8\xff"):
            raise RuntimeError(f"Response is not a JPEG: {item['url']} (Content-Type: {content_type})")
        digest = hashlib.sha256(data).hexdigest()
        changed = not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        if changed:
            target.write_bytes(data)
        entries.append({
            **item,
            "local_path": str(target.relative_to(ROOT)),
            "downloaded_bytes": len(data),
            "sha256": digest,
            "http_content_type": content_type,
            "updated_local_file": changed,
            "redistribution_license": "NPDC Downloads page states: All content is public domain unless otherwise stated. Check each downloaded document for a specific contrary notice before reuse.",
            "use_note": "Reference/source evidence only. Map georeferencing and digitization require a separate documented QA step.",
        })
        print(f"{item['filename']}: {len(data):,} bytes sha256={digest}")
    report = {
        "status": "success",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_catalog": "https://npdc.gov.ph/downloads/",
        "assets": entries,
        "not_imported_again": [
            "The existing NPDC 2024 tree inventory source-export CSV and coordinate-normalization CSV were left unchanged to avoid duplicate imports.",
            "Tree thematic-map PDFs and additional inventory maps are not downloaded in this batch; the initial batch focuses on the park map and planning references.",
        ],
        "limitations": [
            "The NPDC Downloads page states that all content is public domain unless otherwise stated; asset-specific contrary notices still need checking.",
            "The technical map is an image document, not a ready-made GIS layer.",
            "No spatial coordinates were assigned to image features in this import step.",
        ],
    }
    (OUT / "import-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "success", "asset_count": len(entries), "output_dir": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
