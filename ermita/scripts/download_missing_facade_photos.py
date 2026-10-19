#!/usr/bin/env python3
"""Download missing, already-matched KartaView facade candidates into the repo.

This is an incremental asset step only: it does not add KartaView points to the map,
does not claim automatic visual identification, and never overwrites existing images.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
MATCH_CSV = ROOT / "ermita/3d/facade-photo-review.csv"
MASTER_CSV = ROOT / "kartaview/ermita-real-facade-images.csv"
IMAGE_DIR = ROOT / "kartaview/images"
REPORT = ROOT / "kartaview/ermita-facade-image-download-report.json"
USER_AGENT = "Adam-City facade research; image source attribution retained"
MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024
MAX_EDGE = 2400
TIMEOUT = (15, 90)


def read_csv(path: Path):
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_image(data: bytes) -> bytes:
    """Keep the source photograph but resize/re-encode huge originals for repo use."""
    with Image.open(io.BytesIO(data)) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True, progressive=True)
        return output.getvalue()


def main():
    matched, matched_fields = read_csv(MATCH_CSV)
    master, master_fields = read_csv(MASTER_CSV)
    if not matched:
        raise SystemExit(f"Missing/empty matched photo list: {MATCH_CSV}")
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    downloaded, skipped, failed = [], [], []

    master_by_id = {str(r.get("photo_id", "")).strip(): r for r in master}
    for row in matched:
        pid = str(row.get("photo_id", "")).strip()
        url = (row.get("image_url") or "").strip()
        local = (row.get("local_image") or "").strip() or f"kartaview/images/{pid}.jpg"
        if not pid or not url or urlparse(url).scheme != "https":
            if pid:
                failed.append({"photo_id": pid, "reason": "missing photo ID or HTTPS image URL"})
            continue
        destination = ROOT / local
        if destination.is_file() and destination.stat().st_size > 0:
            skipped.append(pid)
            row["local_image"] = local
            if pid in master_by_id:
                master_by_id[pid]["local_image"] = local
                master_by_id[pid]["download_status"] = "downloaded"
            continue
        try:
            response = session.get(url, timeout=TIMEOUT, stream=True)
            response.raise_for_status()
            chunks, total = [], 0
            for chunk in response.iter_content(1024 * 256):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ValueError(f"source image exceeds {MAX_DOWNLOAD_BYTES} byte safety cap")
                chunks.append(chunk)
            raw = b"".join(chunks)
            encoded = normalize_image(raw)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(encoded)
            digest = hashlib.sha256(encoded).hexdigest()
            row["local_image"] = local
            row["download_status"] = "downloaded" if "download_status" in row else row.get("download_status", "")
            if pid in master_by_id:
                master_by_id[pid]["local_image"] = local
                master_by_id[pid]["download_status"] = "downloaded"
            downloaded.append({"photo_id": pid, "path": local, "source_bytes": len(raw), "stored_bytes": len(encoded), "sha256": digest})
        except Exception as exc:
            failed.append({"photo_id": pid, "reason": str(exc)[:300]})
        time.sleep(0.15)

    # Keep review rows and master catalog in sync without changing match/verification status.
    write_csv(MATCH_CSV, matched, matched_fields)
    if master_fields:
        write_csv(MASTER_CSV, list(master_by_id.values()), master_fields)

    report = {
        "status": "success" if not failed else ("partial" if downloaded or skipped else "failed"),
        "area": "Ermita, Manila, Philippines",
        "source": "KartaView public street-level imagery",
        "source_terms": "https://kartaview.org/terms",
        "image_license": "CC BY-SA 4.0",
        "attribution_required": "© Grab and KartaView Contributors",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "matched_rows_checked": len(matched),
        "new_images_downloaded": len(downloaded),
        "existing_images_skipped": len(skipped),
        "failures": failed,
        "new_image_details": downloaded,
        "outputs": ["kartaview/images/", "kartaview/ermita-real-facade-images.csv", "ermita/3d/facade-photo-review.csv"],
        "important_limitations": [
            "These are geolocation/heading-based facade candidates, not visually confirmed building identities.",
            "No KartaView layer or photo points are added to the map.",
            "Photos are not automatically projected onto 3D building walls; use only after visual identity verification.",
            "Images are resized to a maximum 2400 px edge and optimized to keep repository size manageable.",
            "Attribution and CC BY-SA 4.0 licensing information are retained in the catalog."
        ]
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "new_image_details"}, ensure_ascii=False, indent=2))
    if failed and not downloaded and not skipped:
        raise SystemExit("No images downloaded or already available; see report for failures.")


if __name__ == "__main__":
    main()
