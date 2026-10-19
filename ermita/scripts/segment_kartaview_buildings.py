#!/usr/bin/env python3
"""Generate semantic building masks for existing KartaView photos.

Masks are candidate segmentation only: ADE20K 'building' pixels can include
multiple buildings and are not guaranteed to isolate one facade or remove
occluders. Nothing here auto-assigns a photo to a 3D building.
"""
from pathlib import Path
import csv, json, sys
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(".")
BASE = ROOT / "kartaview"
OUT = BASE / "facade-crops" / "building-segmentation"
MANIFEST = BASE / "facade-crops" / "manifest.csv"
OUT.mkdir(parents=True, exist_ok=True)

def main():
    try:
        import torch
        from transformers import AutoImageProcessor, SegformerForSemanticSegmentation
    except Exception as e:
        raise SystemExit("Install torch and transformers first: " + str(e))
    rows = list(csv.DictReader(MANIFEST.open(newline="", encoding="utf-8-sig")))
    paths = sorted({r.get("source_image", "") for r in rows if r.get("source_image")})
    paths = [Path(p) for p in paths if Path(p).is_file()]
    if not paths:
        raise SystemExit("No existing source images found from manifest.csv")
    model_id = "nvidia/segformer-b0-finetuned-ade-512-512"
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = SegformerForSemanticSegmentation.from_pretrained(model_id)
    model.eval()
    # ADE20K label 1 is building.
    label_id = next((int(k) for k, v in model.config.id2label.items()
                     if str(v).strip().lower() in ("building", "buildings")), 1)
    records = []
    for i, path in enumerate(paths, 1):
        try:
            image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                logits = model(**inputs).logits
                pred = torch.nn.functional.interpolate(
                    logits, size=(image.height, image.width),
                    mode="bilinear", align_corners=False
                ).argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
            mask = (pred == label_id).astype(np.uint8) * 255
            # Save a grayscale binary mask and a transparent candidate extraction.
            stem = path.stem
            mask_path = OUT / f"{stem}-building-mask.png"
            rgba_path = OUT / f"{stem}-building-candidate.png"
            Image.fromarray(mask, mode="L").save(mask_path, optimize=True)
            rgba = image.convert("RGBA")
            rgba.putalpha(Image.fromarray(mask, mode="L"))
            rgba.save(rgba_path, optimize=True)
            coverage = float((mask > 0).mean())
            records.append({
                "source_image": str(path), "mask_path": str(mask_path),
                "candidate_path": str(rgba_path), "building_label_id": label_id,
                "building_pixel_fraction": round(coverage, 5),
                "status": "CANDIDATE_ONLY_NOT_FACADE_VERIFIED",
                "notes": "Semantic building mask; may merge multiple buildings and retain occluders. Do not apply as a single building facade without visual verification."
            })
            if i % 10 == 0:
                print(f"Processed {i}/{len(paths)} images", flush=True)
        except Exception as e:
            records.append({"source_image": str(path), "status": "FAILED", "notes": str(e)[:400]})
            print(f"FAILED {path}: {e}", file=sys.stderr, flush=True)
    fields = ["source_image","mask_path","candidate_path","building_label_id","building_pixel_fraction","status","notes"]
    with (OUT / "segmentation-index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(records)
    (OUT / "README.txt").write_text(
        "Semantic building-mask candidates generated from source images already stored in kartaview/images.\n"
        f"Model: {model_id}\n"
        f"Images found: {len(paths)}; records: {len(records)}; successful: {sum(r.get('status','').startswith('CANDIDATE') for r in records)}\n"
        "IMPORTANT: These masks identify building-class pixels, not an individual facade. They can include multiple buildings, windows/trees/signs occlusion errors, and non-front surfaces. They are not approved textures and must not be automatically mapped to a 3D building. See segmentation-index.csv for each output.\n",
        encoding="utf-8")
    failed = sum(r.get("status") == "FAILED" for r in records)
    print(f"Finished: {len(paths)} images; {failed} failures; outputs in {OUT}")
    if failed == len(paths):
        raise SystemExit("All image segmentations failed")

if __name__ == "__main__":
    main()
