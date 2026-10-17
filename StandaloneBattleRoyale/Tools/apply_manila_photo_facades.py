#!/usr/bin/env python3
"""Apply a real CC0 facade photograph to the cached Manila GLB without rebuilding its geometry."""
from __future__ import annotations
import io
import json
import random
from pathlib import Path
import requests
import numpy as np
import trimesh
from PIL import Image, ImageEnhance, ImageOps

MAP_DIR = Path("StandaloneBattleRoyale/Content/Maps")
GLB = MAP_DIR / "Manila-Central-District.glb"
REPORT = MAP_DIR / "Manila-Central-District.json"
SOURCE_URL = "https://commons.wikimedia.org/wiki/Special:Redirect/file/Facade001_4K_Color.jpg"
HEADERS = {"User-Agent": "AdamRoyal-Game-Research/1.0 (facade texture integration)"}

def main() -> None:
    if not GLB.exists() or not REPORT.exists():
        raise FileNotFoundError("Cached Manila GLB and metadata are required; refusing to rebuild geometry.")
    response = requests.get(SOURCE_URL, headers=HEADERS, timeout=60, allow_redirects=True)
    response.raise_for_status()
    source = Image.open(io.BytesIO(response.content)).convert("RGB")
    if source.width < 512 or source.height < 512:
        raise RuntimeError(f"Downloaded facade image is too small: {source.size}")
    # Keep four distinct photographic variants, avoiding one identical color on every building.
    variants = [
        (1.00, 1.00, 1.00),
        (0.88, 0.92, 1.05),
        (1.08, 0.90, 0.88),
        (0.96, 1.08, 0.94),
    ]
    paths = []
    for index, (brightness, contrast, saturation) in enumerate(variants, start=1):
        variant = ImageOps.fit(source, (1024, 1024), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        variant = ImageEnhance.Brightness(variant).enhance(brightness)
        variant = ImageEnhance.Contrast(variant).enhance(contrast)
        variant = ImageEnhance.Color(variant).enhance(saturation)
        path = MAP_DIR / f"Manila-Facade-Texture-{index}.jpg"
        variant.save(path, quality=93, optimize=True)
        paths.append(path)
    scene = trimesh.load(str(GLB), force="scene")
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
    report["facade_texture_source"] = SOURCE_URL
    report["facade_texture_license"] = "CC0 1.0 (verify source metadata at Wikimedia Commons)"
    report["facade_texture_method"] = "one real facade photograph, four color/contrast variants embedded in cached GLB"
    report["facade_materials_replaced"] = replacements
    report["glb_bytes"] = GLB.stat().st_size
    report["note"] = "Real OSM footprints/road alignments; facade uses a real CC0 facade photograph in four variants. It is not geolocated imagery of each specific Manila building; exact facades still need local street-level imagery."
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"PHOTO_FACADE_PASS materials={replacements} image={source.size} glb_bytes={GLB.stat().st_size}")

if __name__ == "__main__":
    main()
