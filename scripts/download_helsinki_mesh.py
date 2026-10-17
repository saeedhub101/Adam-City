#!/usr/bin/env python3
"""Download a known urban Helsinki reality-mesh tile and bundle one playable LOD."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "game" / "public" / "models" / "helsinki"
CACHE = ROOT / ".cache" / "helsinki"
BASE = "https://3d.hel.ninja/data/mesh/Helsinki3D-MESH_2017_OBJ_2km-250m_ZIP"
TILES = [
    {
        "name": "Helsinki3D_2017_OBJ_678492x2.zip",
        "url": f"{BASE}/Helsinki3D_2017_OBJ_678492x2.zip",
        "expected_bytes": 2667315142,
    }
]
ALLOWED_EXTENSIONS = {".obj", ".mtl", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}

def safe_extract(archive: zipfile.ZipFile, destination: Path, selected_names: set[str]) -> None:
    base = destination.resolve()
    for member in archive.infolist():
        if member.filename not in selected_names:
            continue
        target = (destination / member.filename).resolve()
        if target != base and base not in target.parents:
            raise RuntimeError(f"Unsafe path in Helsinki archive: {member.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)

def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    cached_manifest = DEST / "manifest.json"
    if cached_manifest.exists():
        try:
            existing = json.loads(cached_manifest.read_text(encoding="utf-8"))
            for tile in TILES:
                cached_tile = next((item for item in existing.get("tiles", []) if item.get("name") == tile["name"]), None)
                if cached_tile and cached_tile.get("objects") and all((ROOT / "game" / "public" / obj["obj"]).exists() for obj in cached_tile["objects"]):
                    compatibility_manifest = ROOT / "game" / "models" / "helsinki" / "manifest.json"
                    compatibility_manifest.parent.mkdir(parents=True, exist_ok=True)
                    compatibility_manifest.write_text(cached_manifest.read_text(encoding="utf-8"), encoding="utf-8")
                    print(f"Using cached extracted Helsinki tile {tile['name']}")
                    return 0
        except Exception:
            pass

    tile_records = []
    for tile in TILES:
        archive_path = CACHE / tile["name"]
        request = urllib.request.Request(tile["url"], headers={"User-Agent": "SaeedOpenWorld/1.0"})
        try:
            if not archive_path.exists() or archive_path.stat().st_size < 1024 * 1024:
                with urllib.request.urlopen(request, timeout=300) as response, archive_path.open("wb") as out:
                    shutil.copyfileobj(response, out)
        except Exception as exc:
            print(f"ERROR: Could not download official Helsinki mesh tile: {exc}", file=sys.stderr)
            return 2
        actual_bytes = archive_path.stat().st_size
        if actual_bytes < 1024:
            print(f"ERROR: Download too small ({actual_bytes} bytes)", file=sys.stderr)
            return 3
        digest = sha256_file(archive_path)
        print(f"Downloaded {tile['name']}: {actual_bytes:,} bytes; sha256={digest}")
        extract_dir = DEST / tile["name"].removesuffix(".zip")
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
            selected_names = {
                n for n in names
                if "_L16_" in PurePosixPath(n).name
                and PurePosixPath(n).suffix.lower() in ALLOWED_EXTENSIONS
            }
            print(f"Archive entries: {len(names)}; selected LOD16 files: {len(selected_names)}")
            safe_extract(archive, extract_dir, selected_names)
        objs = sorted(p for p in extract_dir.rglob("*.obj") if p.is_file())
        mtls = sorted(p for p in extract_dir.rglob("*.mtl") if p.is_file())
        textures = sorted(p for p in extract_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"})
        objects = []
        for path in objs:
            material = next((line.split(None, 1)[1].strip() for line in path.read_text(errors="ignore").splitlines() if line.strip().lower().startswith("mtllib ")), None)
            objects.append({
                "obj": path.relative_to(ROOT / "game" / "public").as_posix(),
                "bytes": path.stat().st_size,
                "mtl": material,
            })
        tile_records.append({
            "name": tile["name"],
            "sourceArchiveName": tile["name"],
            "extractDir": extract_dir.relative_to(ROOT / "game" / "public").as_posix(),
            "archiveBytes": actual_bytes,
            "sha256": digest,
            "objCount": len(objs),
            "mtlCount": len(mtls),
            "textureCount": len(textures),
            "objects": objects,
        })
        print(f"Extracted playable LOD16: {len(objs)} OBJ, {len(mtls)} MTL, {len(textures)} texture images")
        archive_path.unlink(missing_ok=True)

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
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_path = DEST / "manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    compatibility_manifest = ROOT / "game" / "models" / "helsinki" / "manifest.json"
    compatibility_manifest.parent.mkdir(parents=True, exist_ok=True)
    compatibility_manifest.write_text(manifest_text, encoding="utf-8")
    print(f"Manifest: {manifest_path}; selected OBJ={sum(t['objCount'] for t in tile_records)}, textures={sum(t['textureCount'] for t in tile_records)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
