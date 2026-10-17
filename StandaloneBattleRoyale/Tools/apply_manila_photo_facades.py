#!/usr/bin/env python3
"""Apply a real CC0 facade photograph to the cached Manila GLB without rebuilding its geometry."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageEnhance, ImageOps

MAP_DIR = Path("StandaloneBattleRoyale/Content/Maps")
GLB = MAP_DIR / "Manila-Central-District.glb"
REPORT = MAP_DIR / "Manila-Central-District.json"
PHOTO_DIR = MAP_DIR / "Street-Imagery"
PHOTO_FILES = [
    "commons_manila_019_First_United_Building_Escolta_Binondo_Manila_2014-10-04_jpg.jpg",
    "commons_manila_018_Escolta_Street_in_Manila_looking_west_from_the_Burke_Street_intersecti.jpg",
    "commons_manila_016_Escolta_Street_Binondo_Manila_04-07-2023_jpg.jpg",
    "commons_manila_002_Escolta_Street_buildings_drone_Binondo_Manila_09-06-2025_jpg.jpg",
]

def main() -> None:
    if not GLB.exists() or not REPORT.exists():
        raise FileNotFoundError("Cached Manila GLB and metadata are required; refusing to rebuild geometry.")
    scene = trimesh.load(str(GLB), force="scene")
    texture_materials = []
    photo_materials = []
    for geometry in scene.geometry.values():
        visual = getattr(geometry, "visual", None)
        material = getattr(visual, "material", None)
        if not isinstance(visual, trimesh.visual.TextureVisuals) or material is None:
            continue
        name = str(getattr(material, "name", ""))
        if "ManilaFacadeStyle" in name:
            texture_materials.append(geometry)
        elif "ManilaPhotographicFacade" in name:
            photo_materials.append(geometry)

    if not texture_materials:
        if not photo_materials:
            raise RuntimeError("No known Manila facade materials found; refusing to save an untextured map.")
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        report["facade_texture_source"] = "Wikimedia Commons Manila street photographs; see Street-Imagery and attribution manifest"
        report["facade_texture_method"] = "four distinct real Manila/Escolta street photographs used as facade image textures"
        report["facade_materials_replaced"] = len(photo_materials)
        report["glb_bytes"] = GLB.stat().st_size
        report["note"] = "Real OSM footprints and road alignments; facade materials use four different actual Manila/Escolta street photographs. These are photographic surface references, not a georeferenced photogrammetry model of every individual building; attribution is documented in Street-Imagery/manifest.json."
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"PHOTO_FACADE_PASS materials={len(photo_materials)} already_applied=true glb_bytes={GLB.stat().st_size}")
        return

    source_images = []
    for filename in PHOTO_FILES:
        image_path = PHOTO_DIR / filename
        if not image_path.is_file():
            raise FileNotFoundError(f"Required real Manila street photograph is missing: {image_path}")
        image = Image.open(image_path).convert("RGB")
        if image.width < 512 or image.height < 256:
            raise RuntimeError(f"Manila reference photo is too small: {image_path} {image.size}")
        source_images.append((filename, image))

    # Use four different, locally cached photographs of actual Escolta/Binondo streets,
    # rather than one generic non-Manila facade image tinted four times.
    paths = []
    for index, (filename, source) in enumerate(source_images, start=1):
        variant = ImageOps.fit(source, (1024, 1024), method=Image.Resampling.LANCZOS, centering=(0.5, 0.42))
        variant = ImageEnhance.Contrast(variant).enhance(1.06)
        variant = ImageEnhance.Color(variant).enhance(0.96)
        texture_path = MAP_DIR / f"Manila-Facade-Texture-{index}.jpg"
        variant.save(texture_path, quality=93, optimize=True)
        paths.append(texture_path)
        print(f"MANILA_PHOTO_TEXTURE={texture_path.name} source={filename} source_size={source.size}")

    replacements = 0
    for geometry in scene.geometry.values():
        visual = getattr(geometry, "visual", None)
        material = getattr(visual, "material", None)
        if not isinstance(visual, trimesh.visual.TextureVisuals) or material is None:
            continue
        name = str(getattr(material, "name", ""))
        if "ManilaFacadeStyle" not in name:
            continue
        try:
            style = int(name.rsplit("Style", 1)[1]) - 1
        except (ValueError, IndexError):
            style = replacements % 4
        image = Image.open(paths[style % 4]).convert("RGB")
        geometry.visual = trimesh.visual.TextureVisuals(
            uv=np.asarray(visual.uv),
            material=trimesh.visual.material.PBRMaterial(
                name=f"ManilaPhotographicFacade{style + 1}",
                baseColorTexture=image,
                metallicFactor=0.02,
                roughnessFactor=0.86,
            ),
        )
        replacements += 1
    if replacements < 1:
        raise RuntimeError("No Manila facade materials matched; refusing to save a map without applied photo textures.")
    scene.export(str(GLB), file_type="glb")
    check = trimesh.load(str(GLB), force="scene")
    if GLB.stat().st_size < 100_000 or len(check.geometry) > 50:
        raise RuntimeError("Photographic facade GLB failed size/mesh validation.")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    report["facade_texture_source"] = "Wikimedia Commons Manila street photographs; see Street-Imagery and attribution manifest"
    report["facade_texture_method"] = "four distinct real Manila/Escolta street photographs used as facade image textures"
    report["facade_materials_replaced"] = replacements
    report["glb_bytes"] = GLB.stat().st_size
    report["note"] = "Real OSM footprints and road alignments; facade materials use four different actual Manila/Escolta street photographs. These are photographic surface references, not a georeferenced photogrammetry model of every individual building; attribution is documented in Street-Imagery/manifest.json."
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"PHOTO_FACADE_PASS materials={replacements} image={source.size} glb_bytes={GLB.stat().st_size}")

if __name__ == "__main__":
    main()
