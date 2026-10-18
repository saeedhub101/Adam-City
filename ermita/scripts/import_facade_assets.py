#!/usr/bin/env python3
"""Idempotently import compact, photorealistic facade assets and PBR textures."""
import json, os, re, hashlib
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path("ermita/assets")
MODEL_DIR = ROOT / "models"
TEXTURE_DIR = ROOT / "textures"
CATALOG = ROOT / "asset-catalog.json"
UA = "Adam-City-Ermita-Research/1.0 (GitHub Actions)"
MAX_FILE = 80 * 1024 * 1024
API = "https://api.polyhaven.com"

def get_json(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))

def flatten(node, path=""):
    out = []
    if isinstance(node, dict):
        if isinstance(node.get("url"), str):
            out.append({"path": path, **node})
        for key, val in node.items():
            if isinstance(val, (dict, list)):
                out.extend(flatten(val, f"{path}/{key}".strip("/")))
    elif isinstance(node, list):
        for i, val in enumerate(node):
            out.extend(flatten(val, f"{path}/{i}".strip("/")))
    return out

def choose_file(files, kind):
    candidates = []
    for f in files:
        p = f["path"].lower()
        size = int(f.get("size") or 0)
        if size <= 0 or size > MAX_FILE:
            continue
        if kind == "model":
            if ".glb" not in p:
                continue
            # Prefer a self-contained GLB; otherwise choose a compact glTF file.
            score = (0 if "1k" in p else 1, size)
        else:
            if not any(ext in p for ext in (".jpg", ".jpeg", ".png", ".webp")):
                continue
            if not any(term in p for term in ("diff", "albedo", "color", "basecolor", "nor_gl", "normal", "rough")):
                continue
            score = (0 if "2k" in p else 1, size)
        candidates.append((score, f))
    candidates.sort(key=lambda x: x[0])
    if kind == "model":
        return candidates[0][1] if candidates else None
    # Choose one image per material channel; prioritize 2K and JPG/PNG.
    selected = {}
    for _, f in candidates:
        p = f["path"].lower()
        if "nor_gl" in p or "normal" in p: channel = "normal"
        elif "rough" in p: channel = "roughness"
        elif "diff" in p or "albedo" in p or "color" in p or "basecolor" in p: channel = "albedo"
        else: continue
        if channel not in selected:
            selected[channel] = f
    return selected

def download(item, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == int(item.get("size") or -1):
        return {"path": str(target), "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "status": "kept-existing"}
    req = Request(item["url"], headers={"User-Agent": UA})
    with urlopen(req, timeout=120) as response, target.open("wb") as out:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk: break
            total += len(chunk)
            if total > MAX_FILE:
                raise RuntimeError(f"File exceeds size cap: {item['path']}")
            out.write(chunk)
    return {"path": str(target), "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "status": "downloaded"}

def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {"source": "Poly Haven public API", "source_url": "https://polyhaven.com/", "license": "CC0 assets", "assets": [], "notes": [
        "These are high-quality reusable facade modules/materials, not scans of specific Ermita buildings.",
        "Do not replace a location-matched real building with a generic model. Use these assets as a fallback for matching building types while real facade imagery is being aligned.",
        "Files are capped at 80 MiB each; existing files are reused."
    ]}
    tasks = [
        ("model", "modular_urban_apartments_facade", "Urban modular facade model"),
        ("texture", "rectangular_facade_tiles_02", "High-resolution facade tile PBR material"),
    ]
    for kind, slug, label in tasks:
        entry = {"id": slug, "name": label, "type": kind, "source_url": f"https://polyhaven.com/a/{slug}", "files": [], "status": "pending"}
        try:
            tree = get_json(f"{API}/files/{slug}")
            leaves = flatten(tree)
            if kind == "model":
                chosen = choose_file(leaves, "model")
                if not chosen:
                    entry["status"] = "no self-contained GLB model under 80 MiB; skipped"
                else:
                    suffix = ".glb"
                    result = download(chosen, MODEL_DIR / f"{slug}{suffix}")
                    entry["files"].append(result)
                    entry["status"] = "downloaded-or-reused"
            else:
                chosen = choose_file(leaves, "texture")
                if not chosen:
                    entry["status"] = "no compact texture maps found; skipped"
                else:
                    for channel, item in chosen.items():
                        ext = Path(item["path"].split("?")[0]).suffix.lower() or ".jpg"
                        result = download(item, TEXTURE_DIR / f"{slug}_{channel}{ext}")
                        result["channel"] = channel
                        result["resolution_path"] = item["path"]
                        entry["files"].append(result)
                    entry["status"] = "downloaded-or-reused"
        except Exception as exc:
            entry["status"] = f"failed: {type(exc).__name__}: {exc}"
        catalog["assets"].append(entry)
        print(f"{slug}: {entry['status']}")
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    if not any(a["files"] for a in catalog["assets"]):
        raise SystemExit("No assets downloaded or reused; inspect the report and retry another source.")

if __name__ == "__main__":
    main()
