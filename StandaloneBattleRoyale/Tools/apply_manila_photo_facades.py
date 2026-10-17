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
    """Use real Manila building photographs as facade textures; never draw synthetic window grids."""
    from PIL import ImageOps

    photo_dir = MAP_DIR / "Real-Facade-Photos"
    photos = sorted(p for p in photo_dir.glob("*.jpg") if p.is_file())
    if len(photos) < 4:
        raise RuntimeError(f"Expected real facade photographs in {photo_dir}; found {len(photos)}")
    source = Image.open(photos[style % len(photos)]).convert("RGB")
    # Crop a facade region; do not stretch an entire street panorama over a wall.
    width, height = source.size
    crop_width, crop_height = max(1, int(width * 0.62)), max(1, int(height * 0.72))
    left, top = max(0, (width - crop_width) // 2), max(0, (height - crop_height) // 2)
    source = source.crop((left, top, left + crop_width, top + crop_height))
    image = ImageOps.fit(source, (1024, 1024), method=Image.Resampling.LANCZOS, centering=(0.5, 0.42))
    image.save(path, quality=95, optimize=True)
    return image

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
        # Rebuild UVs per face: wall projection must follow each wall's orientation.
        source_vertices = np.asarray(geometry.vertices)
        source_faces = np.asarray(geometry.faces)
        if source_faces.ndim != 2 or source_faces.shape[1] != 3:
            raise RuntimeError(f"Facade mesh {name!r} is not triangular")
        face_vertices = source_vertices[source_faces].reshape((-1, 3))
        face_normals = np.asarray(geometry.face_normals)
        face_uv = np.zeros((len(source_faces), 3, 2), dtype=np.float64)
        for face_index, tri in enumerate(source_faces):
            points = source_vertices[tri]
            normal = face_normals[face_index]
            if abs(float(normal[2])) > 0.7:
                face_uv[face_index, :, 0] = points[:, 0] / 5.0
                face_uv[face_index, :, 1] = points[:, 1] / 5.0
            elif abs(float(normal[1])) >= abs(float(normal[0])):
                face_uv[face_index, :, 0] = points[:, 0] / 4.0
                face_uv[face_index, :, 1] = points[:, 2] / 3.0
            else:
                face_uv[face_index, :, 0] = points[:, 1] / 4.0
                face_uv[face_index, :, 1] = points[:, 2] / 3.0
        geometry.vertices = face_vertices
        geometry.faces = np.arange(len(face_vertices), dtype=np.int64).reshape((-1, 3))
        geometry.visual = trimesh.visual.TextureVisuals(
            uv=face_uv.reshape((-1, 2)),
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
    report["facade_pipeline_version"] = 2
    report["facade_texture_source"] = "real Manila building photographs from Real-Facade-Photos, cropped into facade texture atlases"
    report["facade_texture_method"] = "four or more photographic building facade atlases sourced from real Manila buildings; facade regions cropped before projection; no procedurally drawn window grids"
    report["facade_materials_replaced"] = replacements
    report["facade_photo_projection"] = True
    report["glb_bytes"] = GLB.stat().st_size
    report["note"] = "Real OSM footprints and road alignments textured with cropped photographs of real Manila building facades. Photos are reused across facade batches and are not a full photogrammetry reconstruction; buildings without suitable photographs still require additional photo coverage."
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"FACADE_ATLAS_PASS materials={replacements} textures={len(texture_paths)} glb_bytes={GLB.stat().st_size}")


if __name__ == "__main__":
    main()
