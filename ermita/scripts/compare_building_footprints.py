#!/usr/bin/env python3
"""Compare OSM building polygons with Microsoft's clipped footprint snapshot.

Original source layers are read-only. The script writes a QA table and summary;
it does not merge, overwrite, or promote either source.
"""
import csv
import gzip
import json
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
OSM_PATH = ROOT / "ermita/maps/generated/ermita-building-footprints.geojson"
MS_PATH = ROOT / "ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz"
OUT_DIR = ROOT / "ermita/maps/qa"
CSV_PATH = OUT_DIR / "building-footprint-comparison.csv"
REPORT_PATH = OUT_DIR / "building-footprint-comparison-report.json"
# UTM zone 51N covers Manila; metric measurements are used for area and distance.
PROJECT_CRS = "EPSG:32651"
TRANSFORMER = Transformer.from_crs("EPSG:4326", PROJECT_CRS, always_xy=True)
NEAR_METERS = 8.0


def metric_geometry(feature):
    geom = feature.get("geometry")
    if not geom:
        return None
    try:
        g = transform(TRANSFORMER.transform, shape(geom))
        if g.is_empty or not g.is_valid:
            g = g.buffer(0)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            return None
        return g
    except Exception:
        return None


def load_osm():
    raw = json.loads(OSM_PATH.read_text(encoding="utf-8"))
    rows = []
    for f in raw.get("features", []):
        props = f.get("properties") or {}
        tags = props.get("tags") or {}
        if not (tags.get("building") or tags.get("building:part")):
            continue
        geom = metric_geometry(f)
        if geom is None or geom.area <= 0:
            continue
        rows.append({
            "source_id": props.get("osm_feature_id") or f"osm/{props.get('type','?')}/{props.get('id','?')}",
            "name": tags.get("name", ""),
            "building": tags.get("building", ""),
            "building_part": tags.get("building:part", ""),
            "geometry": geom,
        })
    return rows


def load_microsoft():
    rows = []
    with gzip.open(MS_PATH, "rt", encoding="utf-8") as src:
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            f = json.loads(line)
            props = f.get("properties") or {}
            geom = metric_geometry(f)
            if geom is None or geom.area <= 0:
                continue
            rows.append({
                "source_id": str(f.get("id") or props.get("id") or f"microsoft-line/{line_no}"),
                "geometry": geom,
            })
    return rows


def score(a, b):
    intersection = a.intersection(b).area
    union = a.area + b.area - intersection
    iou = intersection / union if union > 0 else 0.0
    smaller = min(a.area, b.area)
    containment = intersection / smaller if smaller > 0 else 0.0
    return iou, containment, a.distance(b), intersection


def main():
    if not OSM_PATH.exists():
        raise FileNotFoundError(f"Missing OSM source: {OSM_PATH}")
    if not MS_PATH.exists():
        raise FileNotFoundError(f"Missing Microsoft source: {MS_PATH}")
    osm = load_osm()
    ms = load_microsoft()
    if not osm or not ms:
        raise RuntimeError(f"Empty polygon layer: OSM={len(osm)}, Microsoft={len(ms)}")

    tree = STRtree([r["geometry"] for r in ms])
    ms_matched = set()
    counts = Counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "record_type", "classification", "osm_id", "osm_name", "osm_building",
        "osm_building_part", "microsoft_id", "intersection_over_union",
        "intersection_over_smaller_area", "boundary_distance_m",
        "osm_area_m2", "microsoft_area_m2", "intersection_area_m2",
        "area_ratio_osm_to_microsoft", "notes",
    ]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=fields)
        writer.writeheader()
        for o in osm:
            candidate_idx = tree.query(o["geometry"].buffer(NEAR_METERS))
            best = None
            for idx in candidate_idx:
                m = ms[int(idx)]
                iou, containment, distance, intersection = score(o["geometry"], m["geometry"])
                # Rank geometric overlap first, then intersection-over-smaller-area,
                # then distance; keep one best counterpart per OSM polygon.
                rank = (iou, containment, -distance)
                if best is None or rank > best["rank"]:
                    best = {
                        "idx": int(idx), "m": m, "iou": iou,
                        "containment": containment, "distance": distance,
                        "intersection": intersection, "rank": rank,
                    }
            if best is None:
                classification = "osm_only"
                row = {}
                counts[classification] += 1
            else:
                m = best["m"]
                ms_matched.add(best["idx"])
                if best["iou"] >= 0.50:
                    classification = "strong_match_iou_ge_0.50"
                elif best["iou"] >= 0.10 or best["containment"] >= 0.50:
                    classification = "partial_or_conflicting_overlap"
                else:
                    classification = "nearby_no_material_overlap"
                counts[classification] += 1
                row = {
                    "microsoft_id": m["source_id"],
                    "intersection_over_union": round(best["iou"], 5),
                    "intersection_over_smaller_area": round(best["containment"], 5),
                    "boundary_distance_m": round(best["distance"], 2),
                    "microsoft_area_m2": round(m["geometry"].area, 2),
                    "intersection_area_m2": round(best["intersection"], 2),
                    "area_ratio_osm_to_microsoft": round(o["geometry"].area / m["geometry"].area, 5),
                    "notes": "Best candidate among Microsoft polygons intersecting the OSM polygon or its 8 m buffer; not a legal/survey boundary determination.",
                }
            writer.writerow({
                "record_type": "osm_polygon",
                "classification": classification,
                "osm_id": o["source_id"],
                "osm_name": o["name"],
                "osm_building": o["building"],
                "osm_building_part": o["building_part"],
                "osm_area_m2": round(o["geometry"].area, 2),
                **row,
            })

        # Add Microsoft polygons for which no OSM polygon was selected as its best
        # counterpart. This is a candidate list, not proof that OSM is missing a building.
        for i, m in enumerate(ms):
            if i in ms_matched:
                continue
            candidates = tree.query(m["geometry"].buffer(NEAR_METERS))
            best_osm = None
            for oi in STRtree([r["geometry"] for r in osm]).query(m["geometry"].buffer(NEAR_METERS)):
                o = osm[int(oi)]
                iou, containment, distance, intersection = score(o["geometry"], m["geometry"])
                rank = (iou, containment, -distance)
                if best_osm is None or rank > best_osm["rank"]:
                    best_osm = {"o": o, "iou": iou, "containment": containment,
                                "distance": distance, "intersection": intersection, "rank": rank}
            if best_osm and (best_osm["iou"] >= 0.10 or best_osm["containment"] >= 0.50):
                classification = "microsoft_unselected_overlap_candidate"
                note = "Overlaps an OSM polygon but was not selected as that OSM polygon's best counterpart; inspect manually."
            elif best_osm and best_osm["distance"] <= NEAR_METERS:
                classification = "microsoft_near_osm_candidate"
                note = "Within 8 m of OSM geometry; may be a separate building, outline difference, or positional mismatch."
            else:
                classification = "microsoft_only_candidate"
                note = "No OSM polygon within 8 m; validate against current imagery before adding."
            counts[classification] += 1
            writer.writerow({
                "record_type": "microsoft_polygon",
                "classification": classification,
                "osm_id": best_osm["o"]["source_id"] if best_osm else "",
                "osm_name": best_osm["o"]["name"] if best_osm else "",
                "osm_building": best_osm["o"]["building"] if best_osm else "",
                "osm_building_part": best_osm["o"]["building_part"] if best_osm else "",
                "microsoft_id": m["source_id"],
                "intersection_over_union": round(best_osm["iou"], 5) if best_osm else 0,
                "intersection_over_smaller_area": round(best_osm["containment"], 5) if best_osm else 0,
                "boundary_distance_m": round(best_osm["distance"], 2) if best_osm else "",
                "osm_area_m2": round(best_osm["o"]["geometry"].area, 2) if best_osm else "",
                "microsoft_area_m2": round(m["geometry"].area, 2),
                "intersection_area_m2": round(best_osm["intersection"], 2) if best_osm else 0,
                "area_ratio_osm_to_microsoft": round(best_osm["o"]["geometry"].area / m["geometry"].area, 5) if best_osm else "",
                "notes": note,
            })

    report = {
        "status": "success",
        "created_by": "ermita/scripts/compare_building_footprints.py",
        "osm_source": "ermita/maps/generated/ermita-building-footprints.geojson",
        "microsoft_source": "ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz",
        "output_csv": "ermita/maps/qa/building-footprint-comparison.csv",
        "project_crs": PROJECT_CRS,
        "near_candidate_threshold_m": NEAR_METERS,
        "osm_polygon_count": len(osm),
        "microsoft_polygon_count": len(ms),
        "osm_to_best_counterpart_classification_counts": {
            k: v for k, v in counts.items() if k in {
                "strong_match_iou_ge_0.50", "partial_or_conflicting_overlap",
                "nearby_no_material_overlap", "osm_only"
            }
        },
        "microsoft_candidate_classification_counts": {
            k: v for k, v in counts.items() if k.startswith("microsoft_")
        },
        "total_output_rows": sum(counts.values()),
        "limitations": [
            "OSM source export contains points and other features; only polygon/multipolygon features tagged building or building:part are compared.",
            "Microsoft source imagery vintage is 2016–2020; OSM edit dates vary and may be newer.",
            "The AOI is a rectangle and can include neighboring areas.",
            "IoU and distance are screening metrics, not survey accuracy or ground truth.",
            "A Microsoft-only candidate is not automatically a missing or valid building.",
            "Best-counterpart matching is not one-to-one: inspect conflicts and overlapping building parts manually.",
            "Original OSM and Microsoft files are not modified or merged.",
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
