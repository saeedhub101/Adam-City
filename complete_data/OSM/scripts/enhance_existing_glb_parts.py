#!/usr/bin/env python3
"""Add Roxas-style facade details to the existing four GLB parts without replacing them.

The original GLBs are loaded first and preserved in the exported scene. New facade
geometry is generated from the same committed OSM footprints and the facade-detail
functions in ermita/scripts/generate_roxas_boulevard_buildings.py. Coordinates are
converted to each part's existing EPSG:3857 local frame using its origin sidecar.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import trimesh
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / "complete_data/OSM/data/buildings/parts"
SOURCE = ROOT / "complete_data/OSM/data/buildings/ermita-building-footprints.geojson"
OUT_DIR = PARTS / "enhanced"
GENERATOR = ROOT / "ermita/scripts/generate_roxas_boulevard_buildings.py"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform

spec = importlib.util.spec_from_file_location("roxas_facade_generator", GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load facade generator: {GENERATOR}")
facade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facade)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def feature_tags(feature):
    return facade.tags_of(feature)


def main():
    for path in (SOURCE, GENERATOR):
        if not path.is_file():
            raise FileNotFoundError(f"Required source missing: {path}")
    source = read_json(SOURCE)
    features = source.get("features", [])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overall = {"source": str(SOURCE.relative_to(ROOT)), "output_directory": str(OUT_DIR.relative_to(ROOT)), "parts": []}

    for part_no in range(1, 5):
        part_dir = PARTS / f"part{part_no}"
        original_path = part_dir / f"part{part_no}.glb"
        origin_path = part_dir / f"part{part_no}-origin.json"
        if not original_path.is_file() or original_path.stat().st_size < 1000:
            raise FileNotFoundError(f"Original GLB missing or unexpectedly small: {original_path}")
        origin = read_json(origin_path)
        projected_origin = origin.get("origin_projected_m") or {}
        ox, oy = float(projected_origin["x"]), float(projected_origin["y"])
        bounds = origin.get("bounds_epsg3857_m") or {}
        min_x, max_x = float(bounds["min_x"]), float(bounds["max_x"])
        min_y, max_y = float(bounds["min_y"]), float(bounds["max_y"])

        scene = trimesh.load(original_path, force="scene", process=False)
        if not isinstance(scene, trimesh.Scene):
            raise RuntimeError(f"Failed to load original scene: {original_path}")

        seen = set()
        selected = 0
        window_meshes = 0
        window_boxes = 0
        accent_meshes = 0
        base_meshes = 0
        special_meshes = 0
        skipped = 0

        for feature_index, feature in enumerate(features):
            if not feature.get("geometry"):
                continue
            try:
                projected = geom_transform(TO_METERS, shape(feature["geometry"]))
                tags = feature_tags(feature)
                for poly_index, poly in enumerate(facade.polygon_parts(projected)):
                    if poly.is_empty or not poly.is_valid or poly.area < 8:
                        continue
                    cx, cy = poly.centroid.x, poly.centroid.y
                    # The committed part bounds are in absolute EPSG:3857 metres.
                    # Centroid filtering assigns each source footprint to its spatial part.
                    if not (min_x <= cx <= max_x and min_y <= cy <= max_y):
                        continue
                    key = poly.wkb
                    if key in seen:
                        continue
                    seen.add(key)
                    selected += 1
                    height = facade.height_of(tags)
                    fid = str(tags.get("osm_feature_id") or feature.get("id") or "")
                    node_key = (fid or f"part{part_no}-building{feature_index}") \
                        .replace("/", "_").replace(":", "_").replace(" ", "_")
                    # All detail generators work in the absolute projected frame; translate
                    # only their new geometry into the original GLB's local frame.
                    glazing = facade.facade_window_mesh(poly, height, tags, feature_index)
                    if glazing is not None:
                        glazing.apply_translation([-ox, -oy, 0.0])
                        node = f"{node_key}_glazing_{feature_index}_{poly_index}"
                        scene.add_geometry(glazing, node_name=node, geom_name=node)
                        window_meshes += 1
                        window_boxes += len(glazing.faces) // 12

                    accents = facade.facade_accent_mesh(poly, height, tags, feature_index)
                    if accents is not None:
                        accents.apply_translation([-ox, -oy, 0.0])
                        node = f"{node_key}_facade_accents_{feature_index}_{poly_index}"
                        scene.add_geometry(accents, node_name=node, geom_name=node)
                        accent_meshes += 1

                    base = facade.facade_base_mesh(poly, height, tags, feature_index)
                    if base is not None:
                        base.apply_translation([-ox, -oy, 0.0])
                        node = f"{node_key}_facade_base_{feature_index}_{poly_index}"
                        scene.add_geometry(base, node_name=node, geom_name=node)
                        base_meshes += 1

                    for mesh, suffix in (
                        (facade.facade_podium_mesh(poly, height, tags), "photo_podium"),
                        (facade.facade_upper_band_mesh(poly, height, tags), "photo_upper_bands"),
                        (facade.facade_vertical_fin_mesh(poly, height, tags), "photo_vertical_fins"),
                        (facade.facade_planetarium_dome_mesh(poly, height, tags), "photo_planetarium_dome"),
                        (facade.facade_red_planet_canopy_mesh(poly, height, tags), "photo_red_planet_canopy"),
                    ):
                        if mesh is not None:
                            mesh.apply_translation([-ox, -oy, 0.0])
                            node = f"{node_key}_{suffix}_{feature_index}_{poly_index}"
                            scene.add_geometry(mesh, node_name=node, geom_name=node)
                            special_meshes += 1
            except Exception as exc:
                skipped += 1
                if skipped <= 10:
                    print(f"part{part_no}: skipped source feature {feature_index}: {exc}")

        out_path = OUT_DIR / f"part{part_no}-detailed.glb"
        out_path.write_bytes(scene.export(file_type="glb"))
        # Reopen exported output to validate that it is a readable GLB and contains
        # at least as many scene geometries as the original source scene.
        check = trimesh.load(out_path, force="scene", process=False)
        if not isinstance(check, trimesh.Scene) or out_path.stat().st_size <= original_path.stat().st_size:
            raise RuntimeError(f"Enhanced GLB validation failed: {out_path}")
        report = {
            "original_glb": str(original_path.relative_to(ROOT)),
            "output_glb": str(out_path.relative_to(ROOT)),
            "original_bytes": original_path.stat().st_size,
            "output_bytes": out_path.stat().st_size,
            "source_feature_count": len(features),
            "footprint_parts_selected_by_part_bounds": selected,
            "facade_window_meshes": window_meshes,
            "facade_window_boxes_estimate": window_boxes,
            "facade_accent_meshes": accent_meshes,
            "facade_base_meshes": base_meshes,
            "photo_specific_detail_meshes": special_meshes,
            "skipped_source_features": skipped,
            "origin_projected_m": {"x": ox, "y": oy},
            "coordinate_policy": "Preserve original GLB scene and use the existing part origin; add only new facade/detail meshes in the same local coordinate frame.",
            "limitations": [
                "The original building meshes and their materials are retained; added details are procedural overlays from the Roxas Boulevard facade generator.",
                "Photo-specific details are generated only for source footprints with matching identities/tags. This is not a photogrammetric reconstruction of every facade."
            ]
        }
        (OUT_DIR / f"part{part_no}-detailed-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        overall["parts"].append(report)
        print(json.dumps(report, indent=2))

    (OUT_DIR / "enhancement-report.json").write_text(json.dumps(overall, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
