#!/usr/bin/env python3
"""Download a small official Helsinki 3D reality-mesh tile for the game build.

The full-city archive is split into many very large ZIP tiles (some exceed 3 GB).
We intentionally start with the previously identified 10.9 MB tile, verify it,
and keep its textures/materials together. Expand the tile list only after runtime
memory and coordinate placement have been validated.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "game" / "public" / "models" / "helsinki"
BASE = "https://3d.hel.ninja/data/mesh/Helsinki3D-MESH_2017_OBJ_2km-250m_ZIP"
TILES = [
    {
        "name": "Helsinki3D_2017_OBJ_666492x2.zip",
        "url": f"{BASE}/Helsinki3D_2017_OBJ_666492x2.zip",
        "expected_bytes": 10895783,
    }
]

def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    base = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if target != base and base not in target.parents:
            raise RuntimeError(f"Unsafe path in Helsinki archive: {member.filename}")
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    tile_records = []
    for tile in TILES:
        archive_path = DEST / tile["name"]
        request = urllib.request.Request(tile["url"], headers={"User-Agent": "SaeedOpenWorld/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response, archive_path.open("wb") as out:
                shutil.copyfileobj(response, out)
        except Exception as exc:
            print(f"ERROR: Could not download official Helsinki mesh tile: {exc}", file=sys.stderr)
            return 2
        actual_bytes = archive_path.stat().st_size
        if actual_bytes < 1024:
            print(f"ERROR: Download too small ({actual_bytes} bytes)", file=sys.stderr)
            return 3
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        print(f"Downloaded {tile['name']}: {actual_bytes:,} bytes; sha256={digest}")
        extract_dir = DEST / tile["name"].removesuffix(".zip")
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            safe_extract(archive, extract_dir)
            names = [n for n in archive.namelist() if not n.endswith("/")]
            print(f"Archive entries: {len(names)}; sample: {names[:24]}")
        objs = sorted(p for p in extract_dir.rglob("*.obj") if p.is_file())
        mtls = sorted(p for p in extract_dir.rglob("*.mtl") if p.is_file())
        textures = sorted(p for p in extract_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"})
        tile_records.append({
            "name": tile["name"],
            "archive": archive_path.relative_to(ROOT / "game" / "public").as_posix(),
            "extractDir": extract_dir.relative_to(ROOT / "game" / "public").as_posix(),
            "archiveBytes": actual_bytes,
            "sha256": digest,
            "objCount": len(objs),
            "mtlCount": len(mtls),
            "textureCount": len(textures),
            "objects": [
                {
                    "obj": p.relative_to(ROOT / "game" / "public").as_posix(),
                    "bytes": p.stat().st_size,
                    "mtl": next((line.split(None, 1)[1].strip() for line in p.read_text(errors="ignore").splitlines() if line.strip().lower().startswith("mtllib ")), None),
                }
                for p in objs
            ],
        })
        print(f"Extracted: {len(objs)} OBJ, {len(mtls)} MTL, {len(textures)} texture images")
    manifest = {
        "title": "Helsinki 3D reality mesh",
        "source": "City of Helsinki",
        "sourceUrl": "https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/helsinki-3d",
        "viewerUrl": "https://kartta.hel.fi/3d/mesh",
        "license": "CC BY 4.0",
        "imageryYear": 2017,
        "downloadedTileCount": len(tile_records),
        "tiles": tile_records,
    }
    manifest_path = DEST / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path}; total OBJ={sum(t['objCount'] for t in tile_records)}, textures={sum(t['textureCount'] for t in tile_records)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
