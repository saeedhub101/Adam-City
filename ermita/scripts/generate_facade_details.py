#!/usr/bin/env python3
"""Generate procedural facade details for Ermita buildings from original OSM building geometries.

Windows, doors and sign panels are visualization placeholders, not surveyed architecture.
Named sign panels are indexed in a CSV; this script does not invent logos or exact sign text.
"""
import csv, json, math, re, hashlib
from pathlib import Path

import trimesh
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "ermita/maps/generated/ermita-building-details.geojson"
OUT_DIR = ROOT / "ermita/3d/generated"
OUT_GLB = OUT_DIR / "ermita-buildings-facade-details.glb"
OUT_CSV = OUT_DIR / "facade-signage-index.csv"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_LONLAT = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform


def tags_for(feature):
    p = feature.get("properties") or {}
    return p.get("tags") if isinstance(p.get("tags"), dict) else p


def height_for(tags):
    raw = tags.get("height")
    if raw:
        m = re.search(r"\d+(?:\.\d+)?", str(raw).replace(",", "."))
        if m and 1.5 <= float(m.group()) <= 500:
            return float(m.group())
    raw = tags.get("building:levels") or tags.get("levels")
    if raw:
        m = re.search(r"\d+(?:\.\d+)?", str(raw))
        if m and 1 <= float(m.group()) <= 150:
            return float(m.group()) * 3.2
    return 9.6


def box_at(center, extents, angle, color):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 0, 1]))
    mesh.apply_translation(center)
    mesh.visual.face_colors = color
    return mesh


def pbr_material(color, *, metallic=0.0, roughness=0.7, alpha_mode="OPAQUE"):
    return trimesh.visual.material.PBRMaterial(
        name="Facade glass" if alpha_mode == "BLEND" else "Facade painted material",
        baseColorFactor=color,
        metallicFactor=metallic,
        roughnessFactor=roughness,
        alphaMode=alpha_mode,
        doubleSided=True,
    )


def main():
    if not MAP_FILE.exists():
        raise FileNotFoundError(f"Missing {MAP_FILE}; run the OSM building-detail import first")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collection = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    prepared = []
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    maxz = 0.0
    for feature in collection.get("features", []):
        try:
            geom = geom_transform(TO_METERS, shape(feature["geometry"]))
            polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms) if geom.geom_type == "MultiPolygon" else []
            tags = tags_for(feature)
            height = height_for(tags)
            for poly in polys:
                if poly.is_empty or not poly.is_valid or poly.area < 12:
                    continue
                prepared.append((poly, height, tags, feature))
                a,b,c,d = poly.bounds
                minx,miny,maxx,maxy = min(minx,a),min(miny,b),max(maxx,c),max(maxy,d)
                maxz = max(maxz,height)
        except Exception as exc:
            print(f"Skipping invalid building: {exc}")
    if not prepared:
        raise RuntimeError("No valid building polygons available for facade generation")
    center = ((minx+maxx)/2, (miny+maxy)/2, maxz/2)
    wall_meshes = []
    roof_meshes = []
    window_meshes = []
    frame_meshes = []
    sill_meshes = []
    balcony_meshes = []
    door_meshes = []
    sign_meshes = []
    signage = []
    # Real readable OSM-derived storefront names: a shared atlas avoids blank gold panels.
    sign_tile_w, sign_tile_h, sign_cols = 128, 64, 32
    sign_rows = max(1, math.ceil(len(prepared) / sign_cols))
    sign_atlas = Image.new('RGBA', (sign_cols * sign_tile_w, sign_rows * sign_tile_h), (24, 31, 36, 255))
    sign_draw = ImageDraw.Draw(sign_atlas)
    try:
        sign_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
        sign_small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
    except OSError:
        sign_font = ImageFont.load_default()
        sign_small_font = ImageFont.load_default()
    sign_quad_vertices, sign_quad_faces, sign_quad_uv = [], [], []
    sign_slot = 0
    windows_count = doors_count = panels_count = 0

    for poly, height, tags, feature in prepared:
        # Floor count is deliberately estimated where not mapped.
        levels_raw = tags.get("building:levels") or tags.get("levels")
        try:
            levels = max(1, min(100, int(float(levels_raw)))) if levels_raw else max(1, round(height/3.2))
        except (ValueError, TypeError):
            levels = max(1, round(height/3.2))
        floor_h = height / levels
        name = tags.get("name") or tags.get("brand") or tags.get("shop") or tags.get("amenity") or ""
        fid = (feature.get("properties") or {}).get("osm_feature_id", "")
        # Stable per-building variation: avoid a city of identical, repeated blue window blocks.
        seed = int(hashlib.sha256(str(fid or name or len(prepared)).encode()).hexdigest()[:8], 16)
        frame_color = ([218, 211, 195, 255] if seed % 5 in (0, 1) else [76, 72, 66, 255] if seed % 5 in (2, 3) else [156, 151, 139, 255])
        glass_color = ([87, 135, 157, 220] if seed % 4 == 0 else [112, 153, 170, 205] if seed % 4 == 1 else [75, 105, 119, 220] if seed % 4 == 2 else [151, 181, 190, 190])
        # Stable per-building material variants, biased by mapped material/use tags.
        building_type = str(tags.get("building") or tags.get("building:use") or "").lower()
        material_tag = str(tags.get("building:material") or tags.get("building:facade:material") or "").lower()
        palette = ([205, 194, 174, 255], [220, 215, 201, 255], [177, 169, 151, 255])
        if any(k in material_tag for k in ("glass", "curtain", "metal")) or building_type in ("office", "commercial", "hotel"):
            palette = ([143, 163, 169, 255], [164, 178, 180, 255], [124, 145, 151, 255])
        elif any(k in material_tag for k in ("brick", "stone", "concrete")):
            palette = ([173, 143, 119, 255], [194, 171, 146, 255], [157, 151, 139, 255])
        wall_color = palette[seed % len(palette)]
        roof_tag = str(tags.get("roof:material") or tags.get("roof:colour") or "").lower()
        roof_palette = ([104, 108, 105, 255], [127, 119, 105, 255], [145, 139, 126, 255])
        if any(k in roof_tag for k in ("red", "tile", "terracotta")):
            roof_palette = ([137, 77, 57, 255], [157, 91, 66, 255])
        roof_color = roof_palette[seed % len(roof_palette)]
        # Add a thin roof plate at the mapped building height.
        try:
            from shapely.affinity import translate as shift_geometry
            local_poly = shift_geometry(poly, xoff=-center[0], yoff=-center[1])
            roof = trimesh.creation.extrude_polygon(local_poly, height=0.12)
            roof.apply_translation([0, 0, height - center[2] + 0.015])
            roof.visual.face_colors = roof_color
            roof_meshes.append(roof)
        except Exception as exc:
            print(f"Roof skipped for {fid or name or 'unnamed building'}: {exc}")
        # Facade skins add low-relief color/material to all exterior faces.
        ring = list(poly.exterior.coords)
        sign_edge_index = max(range(len(ring)-1), key=lambda i: math.dist(ring[i], ring[i+1])) if len(ring) > 1 else -1
        for edge_index, (a, b) in enumerate(zip(ring[:-1], ring[1:])):
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx,dy)
            if length < 4.5:
                continue
            ux, uy = dx/length, dy/length
            nx, ny = -uy, ux
            angle = math.atan2(dy, dx)
            wall = box_at(((a[0]+b[0])/2-center[0], (a[1]+b[1])/2-center[1], height/2-center[2]), (length, 0.055, height), angle, wall_color)
            wall_meshes.append(wall)
            # Place 1–2 m from corners and avoid excessive tiny windows.
            spacing = 3.0
            count = min(55, max(0, int((length-2.0)/spacing)))
            if count < 1:
                continue
            usable = min(length-1.2, count*spacing)
            start = (length-usable)/2
            for floor in range(levels):
                z = floor*floor_h + min(1.25, floor_h*0.38)
                wh = min(1.35, max(0.55, floor_h*0.42))
                if z + wh > height - 0.15:
                    continue
                for j in range(count):
                    along = start + (j+0.5)*usable/count
                    cx = a[0] + ux*along + nx*0.065 - center[0]
                    cy = a[1] + uy*along + ny*0.065 - center[1]
                    cz = z + wh/2 - center[2]
                    ww = min(1.25, max(0.55, usable/count*0.55))
                    # Slightly larger opaque backing reads as a real frame/reveal around the glass.
                    frame_meshes.append(box_at((cx,cy,cz),(ww+0.16,0.14,wh+0.16),angle,frame_color))
                    window_meshes.append(box_at((cx,cy,cz+0.005),(ww,0.075,wh),angle,glass_color))
                    # Projecting sill catches light and breaks up flat facades.
                    sill_meshes.append(box_at((cx,cy-ny*0.035,cz-wh/2-0.045),(ww+0.22,0.20,0.07),angle,frame_color))
                    windows_count += 1
            # Occasional shallow balconies on taller buildings, using a stable building-specific pattern.
            if height >= 12 and seed % 3 == 0 and floor_h > 2.4 and length >= 9:
                balcony_z = min(height - 1.4, floor_h * (1 + (seed % max(1, levels-1))))
                if balcony_z > 2.8:
                    balcony_meshes.append(box_at((a[0]+ux*length*0.5+nx*0.48-center[0], a[1]+uy*length*0.5+ny*0.48-center[1], balcony_z-center[2]), (min(2.8,length*0.34),0.75,0.12), angle, [174,169,157,255]))
                    balcony_meshes.append(box_at((a[0]+ux*length*0.5+nx*0.82-center[0], a[1]+uy*length*0.5+ny*0.82-center[1], balcony_z+0.48-center[2]), (min(2.8,length*0.34),0.08,0.85), angle, [91,94,91,255]))
            # Ground-floor door and a generic signboard. Real sign text is not fabricated.
            if length >= 7:
                along = length * 0.5
                cx = a[0] + ux*along + nx*0.075 - center[0]
                cy = a[1] + uy*along + ny*0.075 - center[1]
                if height >= 2.4:
                    door_meshes.append(box_at((cx,cy,0.95-center[2]),(0.95,0.12,1.9),angle,[83,65,48,255]))
                    doors_count += 1
                if name and edge_index == sign_edge_index:
                    # Mount an actual textured sign plane; text comes only from the mapped OSM name/brand.
                    sx = a[0] + ux*along + nx*0.13 - center[0]
                    sy = a[1] + uy*along + ny*0.13 - center[1]
                    sign_width = min(3.2, max(1.4, len(str(name))*0.12))
                    slot = sign_slot
                    col, row = slot % sign_cols, slot // sign_cols
                    px, py = col*sign_tile_w, row*sign_tile_h
                    sign_draw.rectangle((px, py, px+sign_tile_w-1, py+sign_tile_h-1), fill=(28, 35, 40, 255))
                    sign_draw.rectangle((px+2, py+2, px+sign_tile_w-3, py+sign_tile_h-3), outline=(206, 174, 104, 255), width=2)
                    label = str(name).strip()
                    if len(label) > 30:
                        label = label[:28] + '…'
                    # Fit the label horizontally rather than producing unreadable clipped fragments.
                    font_size = 13
                    font_use = sign_font
                    while font_size > 7:
                        try:
                            font_use = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
                        except OSError:
                            font_use = sign_font
                            break
                        if sign_draw.textbbox((0,0), label, font=font_use)[2] <= sign_tile_w-12:
                            break
                        font_size -= 1
                    bb = sign_draw.textbbox((0,0), label, font=font_use)
                    sign_draw.text((px+(sign_tile_w-(bb[2]-bb[0]))/2, py+8), label, font=font_use, fill=(248, 245, 235, 255))
                    sublabel = str(tags.get('brand') or tags.get('shop') or tags.get('amenity') or '')
                    if sublabel and sublabel.lower() != label.lower():
                        sign_draw.text((px+5, py+44), sublabel[:22], font=sign_small_font, fill=(223, 190, 120, 255))
                    half = sign_width/2
                    z0, z1 = 2.02-center[2], 2.50-center[2]
                    base = len(sign_quad_vertices)
                    sign_quad_vertices.extend([
                        [sx-ux*half, sy-uy*half, z0], [sx+ux*half, sy+uy*half, z0],
                        [sx+ux*half, sy+uy*half, z1], [sx-ux*half, sy-uy*half, z1]
                    ])
                    sign_quad_faces.extend([[base,base+1,base+2],[base,base+2,base+3]])
                    u0, u1 = px/(sign_cols*sign_tile_w), (px+sign_tile_w)/(sign_cols*sign_tile_w)
                    v0, v1 = py/(sign_rows*sign_tile_h), (py+sign_tile_h)/(sign_rows*sign_tile_h)
                    sign_quad_uv.extend([[u0,1-v1],[u1,1-v1],[u1,1-v0],[u0,1-v0]])
                    sign_slot += 1
                    panels_count += 1
        signage.append({
            "osm_feature_id": fid, "mapped_name_or_use": name,
            "building_height_m": round(height,2), "estimated_floor_count": levels,
            "sign_panel_generated": bool(name),
            "sign_text_or_logo_verified": False,
            "source": "OpenStreetMap contributors; ODbL 1.0",
            "note": "Panel is a generic placeholder; name/use comes from OSM tags when present."
        })
    if not window_meshes and not door_meshes and not sign_meshes:
        raise RuntimeError("No facade details generated; inspect input footprints")

    # Separate geometry groups preserve independent glTF materials for glass and opaque details.
    scene = trimesh.Scene()
    if wall_meshes:
        walls = trimesh.util.concatenate(wall_meshes)
        scene.add_geometry(walls, geom_name="building_facade_skins", node_name="building_facade_skins")
    if roof_meshes:
        roofs = trimesh.util.concatenate(roof_meshes)
        scene.add_geometry(roofs, geom_name="building_roof_surfaces", node_name="building_roof_surfaces")
    if frame_meshes:
        frames = trimesh.util.concatenate(frame_meshes)
        frames.visual = trimesh.visual.TextureVisuals(material=pbr_material([156, 151, 139, 255], metallic=0.0, roughness=0.82))
        scene.add_geometry(frames, geom_name="window_frames", node_name="window_frames")
    if sill_meshes:
        sills = trimesh.util.concatenate(sill_meshes)
        sills.visual = trimesh.visual.TextureVisuals(material=pbr_material([174, 169, 157, 255], metallic=0.0, roughness=0.8))
        scene.add_geometry(sills, geom_name="window_sills", node_name="window_sills")
    if balcony_meshes:
        balconies = trimesh.util.concatenate(balcony_meshes)
        balconies.visual = trimesh.visual.TextureVisuals(material=pbr_material([130, 127, 118, 255], metallic=0.08, roughness=0.7))
        scene.add_geometry(balconies, geom_name="balconies", node_name="balconies")
    if window_meshes:
        glass = trimesh.util.concatenate(window_meshes)
        glass.visual = trimesh.visual.TextureVisuals(
            material=pbr_material([100, 170, 198, 205], metallic=0.25, roughness=0.16, alpha_mode="BLEND")
        )
        scene.add_geometry(glass, geom_name="window_glass", node_name="window_glass")
    if door_meshes:
        doors = trimesh.util.concatenate(door_meshes)
        doors.visual = trimesh.visual.TextureVisuals(
            material=pbr_material([83, 65, 48, 255], metallic=0.0, roughness=0.78)
        )
        scene.add_geometry(doors, geom_name="doors", node_name="doors")
    if sign_quad_vertices:
        signs = trimesh.Trimesh(vertices=sign_quad_vertices, faces=sign_quad_faces, process=False)
        sign_material = trimesh.visual.material.PBRMaterial(
            name="OSM mapped building names and storefront signage",
            baseColorFactor=[255,255,255,255],
            baseColorTexture=sign_atlas,
            metallicFactor=0.02,
            roughnessFactor=0.62,
            doubleSided=True,
        )
        signs.visual = trimesh.visual.TextureVisuals(uv=sign_quad_uv, material=sign_material)
        scene.add_geometry(signs, geom_name="textured_signage", node_name="textured_signage")
    scene.export(OUT_GLB)
    # Store the origin in the same run and from the exact polygons used by this GLB.
    # Never recompute it later from all footprint records, which can be a different set.
    longitude, latitude = TO_LONLAT(center[0], center[1])
    origin = {
        "longitude": longitude,
        "latitude": latitude,
        "anchor_altitude_m": center[2],
        "buildings_used": len(prepared),
        "origin_method": "Generated in the same run as the GLB from the exact prepared polygon bounds and height rules",
        "coordinate_system": "EPSG:3857 local meters, recentered at (longitude, latitude, anchor_altitude_m)"
    }
    (OUT_DIR / "facade-model-origin.json").write_text(
        json.dumps(origin, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(signage[0].keys()))
        writer.writeheader()
        writer.writerows(signage)
    report = {
        "status": "success", "source": "OpenStreetMap contributors",
        "license": "ODbL 1.0; attribution and share-alike obligations apply",
        "output_glb": str(OUT_GLB.relative_to(ROOT)),
        "output_signage_index": str(OUT_CSV.relative_to(ROOT)),
        "building_polygon_parts": len(prepared), "glb_bytes": OUT_GLB.stat().st_size,
        "model_center_epsg3857_m": {"x": center[0], "y": center[1], "z": center[2]},
        "facade_skin_segments": len(wall_meshes), "roof_surfaces": len(roof_meshes), "window_panels": windows_count, "window_frames": len(frame_meshes), "window_sills": len(sill_meshes), "balcony_parts": len(balcony_meshes),
        "door_placeholders": doors_count, "textured_osm_signboards": panels_count,
        "placement": "EPSG:3857 meters; recentered using the same building extent as the extrusion model",
        "limitations": [
            "Facade skins and roof surfaces use tag-based color variants, but are approximations rather than photo-matched finishes. Windows, frames, sills, balconies, doors and signboards remain procedural details, not surveyed architectural features.",
            "Floor counts are estimated if OSM building:levels is absent.",
            "Signboard text is rendered from available OSM name/brand/shop/amenity tags into a shared texture atlas; brand logos and exact photographed sign designs are not reconstructed.",
            "No facade photographs, photogrammetry, or street-level imagery are included."
        ]
    }
    (OUT_DIR / "facade-details-report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
