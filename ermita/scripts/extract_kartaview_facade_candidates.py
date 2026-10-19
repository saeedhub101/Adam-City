#!/usr/bin/env python3
"""Create conservative facade-crop candidates from existing KartaView frames.

Original images are never modified. Every crop is a REVIEW candidate, not an
approved game texture: street frames can contain multiple buildings and people.
"""
from pathlib import Path
import csv, json, math
from PIL import Image, ImageOps, ImageEnhance

ROOT = Path(".")
IMAGE_DIR = ROOT / "kartaview" / "images"
CSV_PATH = ROOT / "kartaview" / "ermita-real-facade-images.csv"
OUT = ROOT / "kartaview" / "facade-crops"
MAX_EDGE = 960
JPEG_QUALITY = 86

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def save_candidate(img, photo_id, candidate, box, row):
    crop = img.crop(box)
    crop = ImageOps.exif_transpose(crop).convert("RGB")
    scale = min(1.0, MAX_EDGE / max(crop.size))
    if scale < 1:
        crop = crop.resize((max(1, round(crop.width*scale)), max(1, round(crop.height*scale))), Image.Resampling.LANCZOS)
    # Keep original camera appearance; do not synthesize missing facade details.
    out_path = OUT / f"{photo_id}_{candidate}.jpg"
    crop.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return {
        "photo_id": str(photo_id), "candidate_id": candidate,
        "source_image": f"kartaview/images/{photo_id}.jpg",
        "crop_path": out_path.as_posix(),
        "building_osm_id": row.get("building_osm_id",""),
        "building_name": row.get("building_name",""),
        "source_latitude": row.get("latitude",""), "source_longitude": row.get("longitude",""),
        "wall_distance_m": row.get("distance_to_building_wall_m",""),
        "heading_difference_deg": row.get("heading_difference_deg",""),
        "source_license": row.get("license","CC BY-SA 4.0"),
        "review_status": "candidate_pending_visual_review",
        "crop_box_px": [int(v) for v in box],
        "crop_note": "Geometric candidate only. Verify target facade, remove people/road/neighbour buildings manually or with reviewed segmentation before game use."
    }

def main():
    if not IMAGE_DIR.exists():
        raise SystemExit(f"Missing existing image directory: {IMAGE_DIR}")
    rows = {}
    if CSV_PATH.exists():
        with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                pid = Path(row.get("local_image","")).stem or str(row.get("photo_id",""))
                if pid:
                    rows[pid] = row
    OUT.mkdir(parents=True, exist_ok=True)
    # Remove only previous generated candidate files, never source photos.
    for p in OUT.glob("*.jpg"):
        p.unlink()
    manifest = []
    errors = []
    images = sorted(IMAGE_DIR.glob("*"))
    images = [p for p in images if p.suffix.lower() in {".jpg",".jpeg",".png",".webp"}]
    for path in images:
        pid = path.stem
        try:
            with Image.open(path) as raw:
                img = ImageOps.exif_transpose(raw).convert("RGB")
                w, h = img.size
                if w < 80 or h < 80:
                    raise ValueError(f"image too small: {w}x{h}")
                # Keep upper facade-bearing portion; avoid treating road foreground as facade.
                y0, y1 = 0, max(1, int(h * 0.78))
                usable_h = y1-y0
                # Overlapping thirds preserve different possible target buildings in a street frame.
                crop_w = min(w, max(1, int(w * 0.48)))
                stride = max(1, int((w-crop_w)/2))
                boxes = [
                    ("left", (0, y0, min(w,crop_w), y1)),
                    ("center", (max(0,(w-crop_w)//2), y0, min(w,(w+crop_w)//2), y1)),
                    ("right", (max(0,w-crop_w), y0, w, y1)),
                ]
                # A wider central overview gives reviewers context when individual crops are ambiguous.
                overview_w = min(w, max(1, int(w*0.68)))
                boxes.append(("overview", (max(0,(w-overview_w)//2), 0, min(w,(w+overview_w)//2), h)))
                row = rows.get(pid, {"photo_id":pid, "local_image":path.as_posix()})
                for label, box in boxes:
                    if box[2] <= box[0] or box[3] <= box[1]:
                        continue
                    manifest.append(save_candidate(img, pid, label, box, row))
        except Exception as exc:
            errors.append({"source_image":path.as_posix(),"error":str(exc)})
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps({
        "title":"KartaView facade crop candidates",
        "status":"REVIEW_REQUIRED_NOT_APPROVED_FOR_GAME",
        "source_images_found":len(images),
        "candidate_crops_created":len(manifest),
        "failed_images":len(errors),
        "method":"Conservative geometric crops from existing repository images; no new image downloads; originals unchanged.",
        "warning":"These are not automatically verified facade extractions. Street-view frames may include adjacent buildings, road, people, vehicles and perspective distortion. Do not apply to game facades until visual review confirms the building and crop boundaries.",
        "attribution":"KartaView / © Grab and KartaView Contributors; check source license metadata (usually CC BY-SA 4.0).",
        "candidates":manifest,
        "errors":errors
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    # Small index makes all candidates searchable without opening the large manifest.
    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["photo_id","candidate_id","source_image","crop_path","building_osm_id","building_name","source_latitude","source_longitude","wall_distance_m","heading_difference_deg","source_license","review_status","crop_box_px","crop_note"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in manifest:
            writer.writerow({**row, "crop_box_px":json.dumps(row["crop_box_px"])})
    print(f"Existing images scanned: {len(images)}")
    print(f"Candidate crops created: {len(manifest)}")
    print(f"Image failures: {len(errors)}")
    print(f"Output: {OUT}")
    if images and not manifest:
        raise SystemExit("No crop candidates were created")

if __name__ == "__main__":
    main()
