#!/usr/bin/env python3
"""Sort building features from Manila vector-tile PBFs by the supplied 51 boundary records.

Only the boundary.geojsonl file is used as boundary input. Building CSV files are never read.
Original PBF tiles are read-only. Progress is committed to main every 10 tiles and can resume.
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import mapbox_vector_tile
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[2]
TILES_ROOT = REPO / "Manila" / "vector-tiles"
BOUNDARY_PATH = REPO / "complete_data" / "open free tile" / "layers" / "boundary.geojsonl"
OUT_ROOT = REPO / "Manila" / "New_Manila"
PROGRESS_PATH = REPO / "Manila" / "New_Manila-progress.jsonl"
CHECKPOINT_EVERY = 10
EARTH_R = 6371008.8
RAD = math.pi / 180.0
REF_LAT = 14.45
USER_NAME = "github-actions[bot]"
USER_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=check)


def checkpoint(label: str) -> None:
    git("add", "--", str(PROGRESS_PATH.relative_to(REPO)))
    staged = git("diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return
    git("config", "user.name", USER_NAME)
    git("config", "user.email", USER_EMAIL)
    git("commit", "-m", f"Checkpoint PBF boundary sorting: {label}")
    pushed = git("push", "origin", "HEAD:main", check=False)
    if pushed.returncode:
        print(pushed.stdout, file=sys.stderr, flush=True)
        raise RuntimeError("Could not push checkpoint to main; stopping safely.")


def project(lon: float, lat: float) -> tuple[float, float]:
    return (EARTH_R * lon * RAD * math.cos(REF_LAT * RAD), EARTH_R * lat * RAD)


def read_boundaries() -> list[dict[str, Any]]:
    if not BOUNDARY_PATH.is_file():
        raise FileNotFoundError(f"Boundary file not found: {BOUNDARY_PATH}")
    result = []
    for index, line in enumerate(BOUNDARY_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        feat = json.loads(line)
        geom = feat.get("geometry") or {}
        if geom.get("type") == "LineString":
            raw_lines = [geom.get("coordinates", [])]
        elif geom.get("type") == "MultiLineString":
            raw_lines = geom.get("coordinates", [])
        else:
            raise ValueError(f"Unexpected geometry at boundary record {index}: {geom.get('type')}")
        projected = []
        for coords in raw_lines:
            points = [project(float(c[0]), float(c[1])) for c in coords if len(c) >= 2]
            if len(points) >= 2:
                projected.append(LineString(points))
        if not projected:
            raise ValueError(f"Boundary record {index} has no usable line segments")
        result.append({"record": index, "feature_id": feat.get("id", ""),
                       "properties": feat.get("properties") or {},
                       "geometry": unary_union(projected)})
    if len(result) != 51:
        raise ValueError(f"Expected 51 boundary records, found {len(result)}")
    return result


def tile_lonlat(path: Path, extent: int, x: float, y: float) -> tuple[float, float]:
    z, tx, ty = map(int, path.relative_to(TILES_ROOT).with_suffix("").parts[-3:])
    n = 2 ** z
    lon = ((tx + x / extent) / n) * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + y / extent) / n))))
    return lon, lat


def center_of_feature(path: Path, feature: dict[str, Any], extent: int) -> tuple[float, float] | None:
    geom_data = feature.get("geometry")
    if not geom_data or not geom_data.get("coordinates"):
        return None
    try:
        centroid = shape(geom_data).centroid
        return tile_lonlat(path, extent, float(centroid.x), float(centroid.y))
    except Exception:
        coords: list[tuple[float, float]] = []
        def walk(value: Any) -> None:
            if isinstance(value, (list, tuple)):
                if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                    coords.append((float(value[0]), float(value[1])))
                else:
                    for child in value:
                        walk(child)
        walk(geom_data.get("coordinates"))
        if not coords:
            return None
        unique = list(dict.fromkeys(coords))
        return tile_lonlat(path, extent, sum(p[0] for p in unique) / len(unique),
                           sum(p[1] for p in unique) / len(unique))


def boundary_for(lon: float, lat: float, boundaries: list[dict[str, Any]]) -> tuple[dict[str, Any], float]:
    point = Point(*project(lon, lat))
    distance, _, chosen = min(
        (float(item["geometry"].distance(point)), item["record"], item) for item in boundaries
    )
    return chosen, distance


def load_progress() -> tuple[set[str], list[dict[str, Any]]]:
    processed: set[str] = set()
    rows: list[dict[str, Any]] = []
    if PROGRESS_PATH.exists():
        with PROGRESS_PATH.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                processed.add(row["tile_path"])
                if row.get("row_type") != "tile_marker":
                    rows.append(row)
    return processed, rows


def process_tile(path: Path, boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
    z, tx, ty = map(int, path.relative_to(TILES_ROOT).with_suffix("").parts[-3:])
    rows: list[dict[str, Any]] = []
    for layer_name, layer in decoded.items():
        if str(layer_name).lower() not in ("building", "buildings"):
            continue
        extent = int(layer.get("extent", 4096))
        for index, feature in enumerate(layer.get("features", [])):
            props = feature.get("properties") or {}
            center = center_of_feature(path, feature, extent)
            if center is None:
                continue
            lon, lat = center
            boundary, distance = boundary_for(lon, lat, boundaries)
            uid = (props.get("building_uid") or props.get("building_number") or
                   props.get("osm_id") or props.get("osm_way_id") or "")
            rows.append({
                "boundary_record": f'{boundary["record"]:02d}',
                "boundary_feature_id": boundary["feature_id"],
                "boundary_admin_level": boundary["properties"].get("admin_level", ""),
                "boundary_disputed": boundary["properties"].get("disputed", ""),
                "boundary_maritime": boundary["properties"].get("maritime", ""),
                "boundary_distance_m": round(distance, 2),
                "tile_path": path.relative_to(REPO).as_posix(),
                "tile_z": z, "tile_x": tx, "tile_y": ty,
                "layer_name": str(layer_name), "feature_index": index,
                "building_uid": uid,
                "building_name": (props.get("building_name") or props.get("name") or
                                  props.get("name:en") or props.get("name:tl") or ""),
                "osm_id": (props.get("osm_id") or props.get("osm_way_id") or
                           props.get("osm_wayid") or props.get("way_id") or ""),
                "longitude": round(lon, 8), "latitude": round(lat, 8),
                "geometry_type": (feature.get("geometry") or {}).get("type", ""),
                "properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            })
    return rows


def write_outputs(rows: list[dict[str, Any]], boundaries: list[dict[str, Any]], tile_count: int,
                  errors: list[dict[str, str]]) -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda r: (int(r["boundary_record"]), r["tile_path"], r["layer_name"], int(r["feature_index"])))
    fields = ["boundary_record", "boundary_feature_id", "boundary_admin_level", "boundary_disputed",
              "boundary_maritime", "boundary_distance_m", "tile_path", "tile_z", "tile_x", "tile_y",
              "layer_name", "feature_index", "building_uid", "building_name", "osm_id",
              "longitude", "latitude", "geometry_type", "properties_json"]
    with (OUT_ROOT / "buildings-sorted-by-boundary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    counts = {i: 0 for i in range(1, len(boundaries) + 1)}
    for row in rows:
        counts[int(row["boundary_record"])] += 1
    summary = {
        "status": "completed" if not errors else "completed_with_tile_errors",
        "source_tiles_directory": "Manila/vector-tiles",
        "source_tile_count": tile_count,
        "source_boundary_file": "complete_data/open free tile/layers/boundary.geojsonl",
        "boundary_record_count": len(boundaries),
        "building_features_extracted_from_pbf": len(rows),
        "source_csv_files_used": False,
        "pbf_tiles_modified": False,
        "tile_decode_errors": errors,
        "method": "Each building feature centroid was converted from tile-local coordinates to longitude/latitude, then assigned to the nearest of the 51 line features. This is nearest-line grouping, not a claim that every record forms a closed polygon.",
        "counts_by_boundary_record": [
            {"boundary_record": f"{i:02d}", "feature_id": b["feature_id"],
             "admin_level": b["properties"].get("admin_level", ""), "building_features": counts[i]}
            for i, b in enumerate(boundaries, 1)
        ],
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (OUT_ROOT / "summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["boundary_record", "feature_id", "admin_level", "building_features"])
        writer.writeheader()
        writer.writerows(summary["counts_by_boundary_record"])

    for i in range(1, len(boundaries) + 1):
        group = OUT_ROOT / f"boundary-{i:02d}"
        group.mkdir(parents=True, exist_ok=True)
        with (group / "buildings.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(row for row in rows if int(row["boundary_record"]) == i)

    report = [
        "# فرز مباني PBF حسب سجلات الحدود الـ51", "",
        f"- بلاطات PBF التي تم العثور عليها: {tile_count}",
        f"- سجلات الحدود من الملف المحدد: {len(boundaries)}",
        f"- معالم المباني المستخرجة مباشرة من PBF: {len(rows)}",
        "- لم تُستخدم ملفات CSV كمصدر للمباني.",
        "- لم تُعدّل ملفات PBF الأصلية.",
        "- طريقة الفرز: أقرب خط حدود إلى مركز كل معلم مبنى، والمسافة تقريبية بالمتر.",
        "- يوجد ملف CSV رئيسي وملف مستقل لكل سجل حدود من 01 إلى 51.",
        f"- أخطاء قراءة البلاطات: {len(errors)}", "",
        "| سجل الحد | معرف feature | admin_level | عدد المباني |",
        "|---:|---:|---:|---:|",
    ]
    report.extend(f'| {i:02d} | {b["feature_id"]} | {b["properties"].get("admin_level", "")} | {counts[i]} |'
                  for i, b in enumerate(boundaries, 1))
    (OUT_ROOT / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    boundaries = read_boundaries()
    tiles = sorted(p for p in TILES_ROOT.rglob("*.pbf") if p.is_file())
    if not tiles:
        raise FileNotFoundError(f"No PBF files found under {TILES_ROOT}")
    processed, all_rows = load_progress()
    errors: list[dict[str, str]] = []
    error_file = OUT_ROOT / "tile-errors.json"
    if error_file.exists():
        errors = json.loads(error_file.read_text(encoding="utf-8"))
    print(f"Found {len(tiles)} PBF tiles and {len(boundaries)} boundary records. Resuming {len(processed)} saved tiles.", flush=True)
    pending = 0
    with PROGRESS_PATH.open("a", encoding="utf-8") as progress:
        for i, path in enumerate(tiles, 1):
            rel = path.relative_to(REPO).as_posix()
            if rel in processed:
                continue
            try:
                new_rows = process_tile(path, boundaries)
                for row in new_rows:
                    progress.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                    all_rows.append(row)
                # Marker records even empty tiles, so resumes skip already checked tiles.
                if not new_rows:
                    progress.write(json.dumps({"row_type": "tile_marker", "tile_path": rel}, separators=(",", ":")) + "\n")
                progress.flush()
                processed.add(rel)
                pending += 1
                print(f"[{i}/{len(tiles)}] {rel}: {len(new_rows)} building features; checkpoint {pending}/{CHECKPOINT_EVERY}", flush=True)
                if pending >= CHECKPOINT_EVERY:
                    checkpoint(f"{i}-of-{len(tiles)}-tiles")
                    pending = 0
            except Exception as exc:
                errors.append({"tile_path": rel, "error": str(exc)})
                print(f"ERROR {rel}: {exc}", file=sys.stderr, flush=True)
                progress.write(json.dumps({"row_type": "tile_marker", "tile_path": rel}, separators=(",", ":")) + "\n")
                progress.flush()
                processed.add(rel)
                pending += 1
                if pending >= CHECKPOINT_EVERY:
                    checkpoint(f"{i}-of-{len(tiles)}-tiles")
                    pending = 0
    if pending:
        checkpoint(f"final-tile-batch-{len(processed)}")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "tile-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_outputs(all_rows, boundaries, len(tiles), errors)
    # Remove the working progress file only after final output files have been generated.
    PROGRESS_PATH.unlink(missing_ok=True)
    git("add", "--", str(OUT_ROOT.relative_to(REPO)), str(PROGRESS_PATH.relative_to(REPO)))
    staged = git("diff", "--cached", "--quiet", check=False)
    if staged.returncode:
        git("config", "user.name", USER_NAME)
        git("config", "user.email", USER_EMAIL)
        git("commit", "-m", "Publish PBF buildings sorted by 51 boundary records")
        pushed = git("push", "origin", "HEAD:main", check=False)
        if pushed.returncode:
            print(pushed.stdout, file=sys.stderr, flush=True)
            return 3
    print(json.dumps({"tiles": len(tiles), "boundary_records": len(boundaries),
                      "building_features": len(all_rows), "errors": len(errors)}, ensure_ascii=False), flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
