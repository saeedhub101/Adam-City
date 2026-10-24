#!/usr/bin/env python3
"""Audit persisted Middle East OSM PBF tiles for integrity and actual OSM objects."""
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("middle east")
TILE_DIR = ROOT / "Palestine/osm/tiles"
PROGRESS = TILE_DIR / "tile-progress.json"
REPORT = ROOT / "Palestine/reports/tile-integrity-report.json"

def count_objects(path: Path) -> int:
    # fileinfo validates the PBF container; OPL stream count distinguishes a valid
    # but empty spatial extract from a tile containing actual OSM objects.
    subprocess.run(["osmium", "fileinfo", str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    proc = subprocess.Popen(["osmium", "cat", str(path), "-f", "opl"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    count = sum(1 for line in proc.stdout if line.strip())
    stderr = proc.stderr.read() if proc.stderr else ""
    code = proc.wait()
    if code:
        raise RuntimeError(f"osmium cat failed for {path}: {stderr[-2000:]}")
    return count

def main():
    if not PROGRESS.is_file():
        raise SystemExit(f"Missing tile progress manifest: {PROGRESS}")
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    records = []
    errors = []
    for name, meta in sorted(progress.items()):
        path = TILE_DIR / f"{name}.osm.pbf"
        if not path.is_file():
            errors.append({"tile": name, "error": "file missing"})
            continue
        size = path.stat().st_size
        if size != meta.get("bytes"):
            errors.append({"tile": name, "error": "size does not match progress manifest",
                           "file_bytes": size, "manifest_bytes": meta.get("bytes")})
            continue
        try:
            count = count_objects(path)
            records.append({"tile": name, "bbox": meta.get("bbox"), "bytes": size,
                            "osm_object_count": count,
                            "classification": "empty_valid_tile" if count == 0 else "contains_osm_objects"})
        except Exception as exc:
            errors.append({"tile": name, "error": str(exc)})
    expected = 70
    report = {
        "schema": "adam-city-osm-tile-integrity-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Geofabrik Israel and Palestine combined extract",
        "expected_tile_count": expected,
        "manifest_tile_count": len(progress),
        "checked_tile_count": len(records),
        "tiles_with_osm_objects": sum(x["osm_object_count"] > 0 for x in records),
        "valid_empty_tiles": [x for x in records if x["osm_object_count"] == 0],
        "tiles_with_objects_summary": {
            "object_count_total": sum(x["osm_object_count"] for x in records),
            "nonempty_tile_names": [x["tile"] for x in records if x["osm_object_count"] > 0]
        },
        "errors": errors,
        "status": "complete" if len(records) == len(progress) == expected and not errors else "needs_attention",
        "note": "A valid empty PBF tile is not automatically a coverage gap; use its bbox and source extent to assess whether land data should exist there."
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "manifest_tile_count", "checked_tile_count",
          "tiles_with_osm_objects", "valid_empty_tiles", "errors"]}, ensure_ascii=False, indent=2))
    if errors or len(records) != expected:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
