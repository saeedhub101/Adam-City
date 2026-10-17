#!/usr/bin/env python3
"""Download license-attributed Wikimedia Commons photos into the game bundle.

The generated catalogue preserves GPS coordinates (when published), author,
license, source page, and a local asset path so the Windows EXE can work offline.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "game/public/data/tabarbour-photo-catalog.json"
OUT = ROOT / "game/public/images/wikimedia"
BUNDLED = ROOT / "game/public/data/bundled-photo-catalog.json"
UA = "SaeedOpenWorld/1.0 (offline game packaging; photo attribution preserved)"
MAX_BYTES = 8 * 1024 * 1024


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                content = response.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError("image exceeds 8 MiB safety limit")
            if not (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"RIFF") or content.startswith(b"GIF8")):
                raise ValueError("response is not a recognized image")
            return content
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def safe_name(index, photo, url):
    title = str(photo.get("title") or f"photo-{index}")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-_")[:60] or f"photo-{index}"
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    return f"{index:03d}-{slug}{suffix}"


def main():
    if not CATALOG.exists():
        raise SystemExit(f"Missing photo catalogue: {CATALOG}")
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    photos = []
    downloaded = 0
    for index, original in enumerate(source.get("photos", []), start=1):
        photo = dict(original)
        url = photo.get("thumbnail") or photo.get("original")
        if url:
            filename = safe_name(index, photo, url)
            target = OUT / filename
            try:
                if not target.exists() or target.stat().st_size == 0:
                    target.write_bytes(fetch(url))
                photo["localFile"] = "/images/wikimedia/" + filename
                photo["bundled"] = True
                downloaded += 1
            except Exception as error:
                photo["bundled"] = False
                photo["bundleError"] = str(error)[:240]
                print(f"WARNING: Could not bundle {photo.get('title', filename)}: {error}")
        else:
            photo["bundled"] = False
        # Do not infer missing GPS coordinates or building matches.
        photo.setdefault("lat", None)
        photo.setdefault("lon", None)
        photo["coordinatesAvailable"] = photo.get("lat") is not None and photo.get("lon") is not None
        photos.append(photo)
        time.sleep(0.15)
    manifest = {
        "area": source.get("area", "Tabarbour, Amman, Jordan"),
        "generatedAt": source.get("generatedAt"),
        "source": "Wikimedia Commons",
        "matchingPolicy": source.get("matchingPolicy", "No building match is inferred."),
        "count": len(photos),
        "bundledCount": downloaded,
        "photos": photos
    }
    BUNDLED.parent.mkdir(parents=True, exist_ok=True)
    BUNDLED.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {downloaded}/{len(photos)} locally bundled Wikimedia photos.")
    if downloaded == 0:
        raise SystemExit("No Wikimedia photos were downloaded; refusing to build an EXE without bundled photos.")


if __name__ == "__main__":
    main()
