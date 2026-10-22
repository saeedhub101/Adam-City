#!/usr/bin/env python3
"""Export every Ermita OSM building footprint into six complete GLB parts.

No corridor filter is used. Each source feature and every polygon component is exported;
invalid polygon rings are repaired, and any unexportable feature fails the build instead
of being silently dropped. Per-part origin metadata preserves geographic placement.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import trimesh
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "complete_data/OSM/data/buildings/ermita-building-footprints.geojson"
OUT_DIR = ROOT / "complete_data/OSM/data/buildings/ermita-glb-parts"
PART_COUNT = 6
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_METERS = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
sys.path.insert(0, str(ROOT / "ermita/scripts"))
from generate_roxas_boulevard_buildings import height_of, pbr_for, tags_of, positive_number


def polygon_parts(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if isinstance(g, GeometryCollection):
        return [p for child in g.geoms for p in polygon_parts(child)]
    return []


def stable_id(feature, index):
    props = feature.get("properties") or {}
    tags = tags_of(feature)
    return str(tags.get("osm_feature_id") or tags.get("id") or props.get("id") or f"source-feature-{index:07d}")


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Required source GeoJSON missing: {SOURCE}")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise RuntimeError("Source GeoJSON has no features; refusing to generate empty GLBs.")

    prepared = []
    invalid_repaired = 0
    for index, feature in enumerate(features):
        geom_json = feature.get("geometry")
        if not geom_json:
            raise RuntimeError(f"Source feature {index} has no geometry; refusing to omit it.")
        geom = geom_transform(TO_METERS, shape(geom_json))
        if not geom.is_valid:
            geom = geom.buffer(0)
            invalid_repaired += 1
        parts = polygon_parts(geom)
        if geom.is_empty or not parts:
            raise RuntimeError(f"Source feature {index} ({stable_id(feature,index)}) has no usable polygon after repair.")
        parts = [p for p in parts if not p.is_empty and p.area > 0]
        if not parts:
            raise RuntimeError(f"Source feature {index} ({stable_id(feature,index)}) has no positive-area polygon.")
        tags = tags_of(feature)
        centroids = [p.centroid for p in parts]
        total_area = sum(p.area for p in parts)
        cx = sum(p.area*c.x for p,c in zip(parts, centroids)) / total_area
        cy = sum(p.area*c.y for p,c in zip(parts, centroids)) / total_area
        prepared.append({
            "index": index, "id": stable_id(feature,index), "tags": tags,
            "parts": parts, "cx": cx, "cy": cy,
            "properties": feature.get("properties") or {},
        })

    prepared.sort(key=lambda item: (item["cx"], item["cy"], item["id"]))
    chunks = [prepared[i*len(prepared)//PART_COUNT:(i+1)*len(prepared)//PART_COUNT]
              for i in range(PART_COUNT)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = []
    part_reports = []
    total_polygon_parts = 0
    total_meshes = 0

    for part_no, chunk in enumerate(chunks, 1):
        if not chunk:
            raise RuntimeError(f"Part {part_no} would be empty; refusing to create an incomplete set.")
        area_sum = sum(sum(p.area for p in item["parts"]) for item in chunk)
        ox = sum(sum(p.area*p.centroid.x for p in item["parts"]) for item in chunk) / area_sum
        oy = sum(sum(p.area*p.centroid.y for p in item["parts"]) for item in chunk) / area_sum
        scene = trimesh.Scene()
        part_inventory = []
        meshes_here = 0
        for item in chunk:
            tags = item["tags"]
            height = float(height_of(tags))
            base = positive_number(tags.get("min_height") or tags.get("building:min_level"), 0, 500) or 0.0
            if base >= height:
                raise RuntimeError(f"Invalid base/height for {item['id']}: base={base}, height={height}")
            label, rgba, metallic, roughness = pbr_for(tags, item["index"])
            material = trimesh.visual.material.PBRMaterial(
                name=str(label).replace(" ", "_")[:64],
                baseColorFactor=[max(0,min(255,int(round(float(c)*255)))) for c in rgba[:3]] + [255],
                metallicFactor=float(metallic), roughnessFactor=float(roughness),
                alphaMode="OPAQUE", doubleSided=True,
            )
            for poly_no, poly in enumerate(item["parts"], 1):
                local_poly = geom_transform(lambda x,y,z=None: (x-ox,y-oy), poly)
                try:
                    mesh = trimesh.creation.extrude_polygon(local_poly, height-base, engine="earcut")
                except Exception as exc:
                    raise RuntimeError(f"Failed to extrude {item['id']} polygon part {poly_no}: {exc}") from exc
                mesh.apply_translation([0,0,base])
                mesh.visual = trimesh.visual.TextureVisuals(material=material)
                mesh.metadata.update({
                    "osm_feature_id": item["id"],
                    "source_feature_index": item["index"],
                    "polygon_component": poly_no,
                    "height_m": height,
                    "base_height_m": base,
                })
                name = f"{item['id'].replace('/','_')}_component_{poly_no:03d}"
                scene.add_geometry(mesh, geom_name=name, node_name=name,
                                   metadata={"osm_feature_id": item["id"],
                                             "source_feature_index": item["index"],
                                             "polygon_component": poly_no})
                meshes_here += 1
            part_inventory.append({
                "osm_feature_id": item["id"],
                "source_feature_index": item["index"],
                "polygon_components_exported": len(item["parts"]),
                "height_m": height,
                "base_height_m": base,
                "properties": item["properties"],
            })
        filename = f"ermita-buildings-part-{part_no:02d}-of-{PART_COUNT:02d}.glb"
        out = OUT_DIR / filename
        scene.export(out, file_type="glb")
        if not out.is_file() or out.stat().st_size < 1000:
            raise RuntimeError(f"GLB export failed or is unexpectedly small: {out}")
        lon, lat = FROM_METERS(ox, oy)
        origin = {
            "file": filename, "part": part_no, "part_count": PART_COUNT,
            "crs": "EPSG:3857", "origin_projected_m": {"x": ox, "y": oy},
            "origin_wgs84": {"longitude": lon, "latitude": lat},
            "source_geojson": str(SOURCE.relative_to(ROOT)),
            "source_feature_count": len(chunk),
            "polygon_components_exported": sum(len(x["parts"]) for x in chunk),
            "mesh_count": meshes_here,
        }
        (OUT_DIR / filename.replace(".glb", "-origin.json")).write_text(
            json.dumps(origin, ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT_DIR / filename.replace(".glb", "-inventory.json")).write_text(
            json.dumps({"part": part_no, "features": part_inventory}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        inventory.extend([{"part": part_no, "source_feature_index": x["source_feature_index"],
                           "osm_feature_id": x["osm_feature_id"],
                           "polygon_components_exported": x["polygon_components_exported"]}
                          for x in part_inventory])
        polygon_count = origin["polygon_components_exported"]
        total_polygon_parts += polygon_count
        total_meshes += meshes_here
        part_reports.append({
            "part": part_no, "file": filename, "bytes": out.stat().st_size,
            "feature_count": len(chunk), "polygon_components": polygon_count,
            "mesh_count": meshes_here, "origin": origin["origin_wgs84"],
        })
        print(f"Part {part_no}/{PART_COUNT}: {len(chunk)} source features, {polygon_count} polygon components, {meshes_here} meshes, {out.stat().st_size} bytes")

    exported_indices = [x["source_feature_index"] for x in inventory]
    if len(exported_indices) != len(features) or sorted(exported_indices) != list(range(len(features))):
        raise RuntimeError(f"Coverage validation failed: source={len(features)}, exported entries={len(exported_indices)}")
    report = {
        "status": "validated",
        "source_geojson": str(SOURCE.relative_to(ROOT)),
        "source_feature_count": len(features),
        "exported_source_feature_count": len(exported_indices),
        "unique_source_feature_indices": len(set(exported_indices)),
        "part_count": PART_COUNT,
        "polygon_components_exported": total_polygon_parts,
        "mesh_count": total_meshes,
        "invalid_geometries_repaired": invalid_repaired,
        "omitted_source_features": [],
        "clipping_or_corridor_filter": False,
        "height_source": "OSM height/building:levels tags with existing project landmark corrections and documented fallback",
        "parts": part_reports,
    }
    (OUT_DIR / "ermita-buildings-parts-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "README.md").write_text(
        "# Ermita buildings — split GLB exports\n\n"
        "Six GLB files generated from the complete ermita-building-footprints.geojson source. "
        "Every source feature is assigned to exactly one part; every polygon component is exported, "
        "without corridor filtering or minimum-area filtering. Each GLB has an -origin.json placement "
        "sidecar and an -inventory.json listing source properties and IDs. "
        "The report records source/export counts and fails generation if coverage is incomplete.\n\n"
        "Use the part-specific origin metadata when positioning each GLB; the six files use different "
        "local origins to maintain mesh precision.\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
