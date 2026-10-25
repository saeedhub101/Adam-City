#!/usr/bin/env python3
"""Discover public LiDAR holdings intersecting Jordan and Palestine and import directly downloadable files.

CMR metadata is inventoried separately; only explicitly public direct-download assets are downloaded.
GitHub's 100 MB per-file limit is respected, and files that cannot be stored are recorded in the report.
"""
import json, os, re
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path("complete_data/LiDAR")
RAW = ROOT / "downloads"
META = ROOT / "catalog"
REPORT = ROOT / "LIDAR_IMPORT_REPORT.md"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Adam-City-LiDAR-import/1.0 (public geodata research)"})
MAX_FILE = 95 * 1024 * 1024
MAX_TOTAL = 2_000 * 1024 * 1024
TOTAL = 0
BBOX = "34.1,29.1,39.4,33.4"
ROOT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)
records, downloaded, notes = [], [], []

def get_json(url, params=None):
    r = SESSION.get(url, params=params, timeout=90)
    r.raise_for_status()
    return r.json()

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:150]

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def download(url, label):
    global TOTAL
    if not url.startswith("https://"):
        return "skipped: non-HTTPS link"
    if TOTAL >= MAX_TOTAL:
        return "skipped: workflow download budget reached (2 GB/run)"
    name = safe_name(label or os.path.basename(urlparse(url).path) or "asset")
    if not Path(name).suffix:
        name += ".bin"
    target = RAW / name
    if target.exists() and target.stat().st_size:
        return f"already present ({target.stat().st_size} bytes)"
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with SESSION.get(url, stream=True, timeout=(30, 180), allow_redirects=True) as r:
            if r.status_code != 200:
                return f"not directly downloadable (HTTP {r.status_code})"
            length = int(r.headers.get("content-length", "0") or 0)
            if length > MAX_FILE:
                return f"not committed: file advertises {length} bytes (GitHub per-file limit)"
            read = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    read += len(chunk)
                    if read > MAX_FILE or TOTAL + read > MAX_TOTAL:
                        tmp.unlink(missing_ok=True)
                        return "stopped at repository/run storage safety limit"
                    f.write(chunk)
        if read == 0:
            tmp.unlink(missing_ok=True)
            return "empty response"
        tmp.replace(target)
        TOTAL += read
        downloaded.append({"file": str(target), "url": url, "bytes": read})
        return f"downloaded {read} bytes to {target}"
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return f"download failed: {type(e).__name__}: {e}"

# Public AWS Open LiDAR registry. Coverage is not assumed to be global.
try:
    listing = SESSION.get("https://open-lidar-data.s3.eu-central-1.amazonaws.com/?list-type=2", timeout=90)
    listing.raise_for_status()
    (META / "open-lidar-data-s3-listing.xml").write_bytes(listing.content)
    import xml.etree.ElementTree as ET
    xmlroot = ET.fromstring(listing.content)
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    keys = [el.text for el in xmlroot.findall(".//s3:Contents/s3:Key", ns) if el.text]
    matches = [k for k in keys if re.search(r"(jordan|palestin|west.?bank|gaza|israel|levant)", k, re.I)]
    save_json(META / "open-lidar-data-matching-objects.json",
              {"bucket": "open-lidar-data", "listed_keys": len(keys), "regional_name_matches": matches})
    for key in matches:
        url = "https://open-lidar-data.s3.eu-central-1.amazonaws.com/" + requests.utils.quote(key, safe="/")
        status = download(url, key.replace("/", "__"))
        records.append({"source": "AWS Open LiDAR Data", "asset": key, "url": url, "status": status})
    notes.append(f"AWS Open LiDAR registry: {len(keys)} keys in first public listing page; {len(matches)} regional filename matches. Filename matching does not prove geographic coverage.")
except Exception as e:
    notes.append(f"AWS Open LiDAR registry query failed: {type(e).__name__}: {e}")

# NASA CMR catalogs for satellite laser altimetry. Tracks are not dense city scans.
collections = [
    ("GEDI L2A elevation/height footprints", "C2142771958-LPCLOUD"),
    ("GEDI L2B canopy metrics footprints", "C2142771963-LPCLOUD"),
    ("ICESat-2 ATL03 photon data", "C1200391745-NSIDC_CPRD"),
    ("ICESat-2 ATL08 land/vegetation segments", "C2144428006-NSIDC_ECS"),
]
for label, concept in collections:
    try:
        payload = get_json("https://cmr.earthdata.nasa.gov/search/granules.json",
                           {"collection_concept_id": concept, "bounding_box": BBOX,
                            "page_size": 200, "sort_key": "-start_date"})
        items = payload.get("feed", {}).get("entry", [])
        save_json(META / (safe_name(concept) + ".json"),
                  {"collection": label, "concept_id": concept, "bounding_box_wgs84": BBOX, "granules": items})
        records.append({"source": "NASA CMR", "asset": label, "granules_found": len(items), "status": "metadata inventoried"})
        count = 0
        for item in items:
            title = item.get("title", "granule")
            for link in item.get("links", []):
                href, rel = link.get("href", ""), link.get("rel", "")
                if not href.startswith("https://") or "data#" not in rel:
                    continue
                if not re.search(r"\.(h5|hdf5|nc|laz|las|tif|tiff)(\?|$)", href, re.I):
                    continue
                status = download(href, safe_name(title) + "_" + os.path.basename(urlparse(href).path))
                records.append({"source": "NASA CMR", "asset": title, "url": href, "status": status})
                count += 1
                if count >= 20 or TOTAL >= MAX_TOTAL:
                    break
            if count >= 20 or TOTAL >= MAX_TOTAL:
                break
        notes.append(f"{label}: {len(items)} intersecting granule records; attempted at most 20 direct data links. Satellite tracks are not wall-to-wall coverage.")
    except Exception as e:
        notes.append(f"{label}: query failed: {type(e).__name__}: {e}")

save_json(META / "import-log.json", {"bbox_wgs84": BBOX, "records": records,
          "downloaded": downloaded, "bytes_downloaded_this_run": TOTAL, "notes": notes})
lines = [
    "# Jordan-Palestine LiDAR import report", "",
    "Generated by .github/workflows/import-jordan-palestine-lidar.yml.", "",
    "## Scope and limitations", "",
    "- This workflow inventories public catalog records intersecting Jordan / West Bank / Gaza.",
    "- GEDI and ICESat-2 are satellite laser observations with sparse tracks/footprints, not dense airborne LiDAR or complete 3D city models.",
    "- Only assets reachable without credentials are downloaded; cap is 95 MiB per file and 2 GiB per run.",
    "- Earthdata-authenticated, oversized, or non-direct assets are recorded/skipped rather than falsely reported as imported.",
    "- Catalog results do not prove complete national LiDAR coverage.", "",
    "## Run results", "", f"- Bytes downloaded this run: {TOTAL}",
    f"- Files downloaded this run: {len(downloaded)}", "", "## Catalog results", ""
]
lines += [f"- {n}" for n in notes]
lines += ["", "## Asset status", ""]
lines += [f"- {r.get('source')}: {r.get('asset')} — {r.get('status', str(r.get('granules_found', '')) + ' granules')}" for r in records]
lines += ["", "## Stored files", "", "- catalog/: metadata and inventories",
          "- downloads/: directly downloadable data assets",
          "- catalog/import-log.json: machine-readable import log", ""]
REPORT.write_text("\n".join(lines), encoding="utf-8")
print(f"LiDAR import complete: {len(downloaded)} files, {TOTAL} bytes. See {REPORT}")
