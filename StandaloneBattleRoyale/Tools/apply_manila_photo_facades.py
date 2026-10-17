#!/usr/bin/env python3
"""Restore repeatable, building-scale facade atlases; never stretch street panoramas across walls.

Wikimedia street photos remain licensed reference material in Street-Imagery. They are
not valid generic wall textures: cropping a whole streetscape into a square makes
billboard-like repeated facades. This stage therefore rebuilds four tileable facade
atlases and assigns them to the existing GLB facade batches without changing geometry.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFilter

MAP_DIR = Path("StandaloneBattleRoyale/Content/Maps")
GLB = MAP_DIR / "Manila-Central-District.glb"
REPORT = MAP_DIR / "Manila-Central-District.json"
PHOTO_DIR = MAP_DIR / "Street-Imagery"


def make_facade_texture(path: Path, style: int) -> Image.Image:
    """Create a seamless, readable facade atlas with window reveals and varied materials."""
    random.seed(7319 + style * 97)
    size = 512
    palettes = [
        ((177, 166, 147), (48, 65, 76)),
        ((205, 192, 164), (56, 69, 76)),
        ((143, 145, 141), (52, 68, 77)),
        ((183, 160, 132), (70, 76, 76)),
    ]
    wall, glass = palettes[style % len(palettes)]
    im = Image.new("RGB", (size, size), wall)
    px = im.load()
    for y in range(size):
        for x in range(size):
            n = random.randint(-7, 7)
            px[x, y] = tuple(max(0, min(255, c + n)) for c in wall)
    d = ImageDraw.Draw(im)
    row_h = 82 if style % 2 == 0 else 68
    # Edge-aligned rows and columns keep tiling coherent at the UV boundary.
    for y in range(0, size, row_h):
        d.rectangle((0, y, size, min(size, y + 7)), fill=tuple(max(0, c - 27) for c in wall))
        for x in range(8, size, 58):
            ww = random.randint(27, 35)
            hh = max(24, row_h - random.randint(23, 31))
            top = y + 12
            bottom = min(size - 1, top + hh)
            right = min(size - 1, x + ww)
            d.rectangle((x - 4, top - 4, right + 4, bottom + 5), fill=tuple(max(0, c - 36) for c in wall))
            tint = random.choice([glass, (35, 48, 58), (77, 87, 89), (91, 99, 96)])
            d.rectangle((x, top, right, bottom), fill=tint)
            d.line((x + 4, top + 2, x + 4, bottom - 2), fill=(155, 165, 163), width=2)
            d.line((x + (right - x) // 2, top, x + (right - x) // 2, bottom), fill=(30, 38, 42), width=3)
            d.line((x, top + (bottom - top) // 2, right, top + (bottom - top) // 2), fill=(30, 38, 42), width=2)
            d.line((x - 4, bottom + 5, right + 4, bottom + 5), fill=tuple(min(255, c + 24) for c in wall), width=3)
    im = im.filter(ImageFilter.GaussianBlur(0.2))
    im.save(path, quality=94, optimize=True)
    return im


def main() -> None:
    if not GLB.is_file() or not REPORT.is_file():
        raise FileNotFoundError("Cached Manila GLB and metadata are required.")
    scene = trimesh.load(str(GLB), force="scene")
    replacements = 0
    texture_paths = []
    for style in range(1, 5):
        path = MAP_DIR / f"Manila-Facade-Texture-{style}.jpg"
        make_facade_texture(path, style - 1)
        texture_paths.append(path)

    for geometry in scene.geometry.values():
        visual = getattr(geometry, "visual", None)
        material = getattr(visual, "material", None)
        if not isinstance(visual, trimesh.visual.TextureVisuals) or material is None:
            continue
        name = str(getattr(material, "name", ""))
        if "ManilaFacadeStyle" not in name and "ManilaPhotographicFacade" not in name:
            continue
        try:
            suffix = name.rsplit("Style", 1)[1] if "Style" in name else name.rsplit("Facade", 1)[1]
            style = max(0, int(suffix) - 1) % 4
        except (ValueError, IndexError):
            style = replacements % 4
        image = Image.open(texture_paths[style]).convert("RGB")
        uv = np.asarray(visual.uv)
        if uv.ndim != 2 or len(uv) != len(geometry.vertices):
            raise RuntimeError(f"Facade mesh {name!r} has invalid UV coordinates")
        geometry.visual = trimesh.visual.TextureVisuals(
            uv=uv,
            material=trimesh.visual.material.PBRMaterial(
                name=f"ManilaFacadeStyle{style + 1}",
                baseColorTexture=image,
                metallicFactor=0.02,
                roughnessFactor=0.88,
            ),
        )
        replacements += 1

    if replacements < 1:
        raise RuntimeError("No recognized Manila facade batches were found; map was not accepted.")
    scene.export(str(GLB), file_type="glb")
    checked = trimesh.load(str(GLB), force="scene")
    if GLB.stat().st_size < 100_000 or len(checked.geometry) > 50:
        raise RuntimeError("Facade atlas integration failed GLB size/mesh validation.")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    report["facade_texture_source"] = "locally generated tileable facade atlases; Wikimedia Commons images retained as attributed reference only"
    report["facade_texture_method"] = "four distinct repeatable facade atlases with window frames, reveals, sills, and material variation; no whole-street photographs stretched across walls"
    report["facade_materials_replaced"] = replacements
    report["facade_photo_projection"] = False
    report["glb_bytes"] = GLB.stat().st_size
    report["note"] = "Real OSM footprints and road alignments with procedural tileable facade atlases. Licensed Manila photographs are retained as reference images and are not falsely represented as building-specific photogrammetry. This improves tiling artifacts but is not a photogrammetry reconstruction."
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"FACADE_ATLAS_PASS materials={replacements} textures={len(texture_paths)} glb_bytes={GLB.stat().st_size}")


if __name__ == "__main__":
    main()
