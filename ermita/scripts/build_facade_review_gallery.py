#!/usr/bin/env python3
"""Build a browsable human-review gallery and priority queue for facade crops."""
from pathlib import Path
import csv, html, json, math

ROOT = Path(".")
BASE = ROOT / "kartaview" / "facade-crops"
MANIFEST = BASE / "manifest.csv"
OUT_HTML = BASE / "review-gallery.html"
OUT_CSV = BASE / "review-priority.csv"

def number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def priority(row):
    dist = number(row.get("wall_distance_m"))
    heading = number(row.get("heading_difference_deg"))
    # Lower is better. Missing measurements receive conservative penalties.
    score = (dist if dist is not None else 20.0) + 0.18*(heading if heading is not None else 45.0)
    return score

def main():
    if not MANIFEST.exists():
        raise SystemExit("Missing crop manifest; run extract workflow first.")
    with MANIFEST.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # One overview record per original image gives a concise priority queue.
    originals = {}
    for row in rows:
        originals.setdefault(row["photo_id"], row.copy())
    ordered = sorted(originals.values(), key=lambda r: (priority(r), r["photo_id"]))
    for rank, row in enumerate(ordered, 1):
        row["priority_rank"] = rank
        row["priority_score"] = round(priority(row), 3)
        row["visual_facade_verified"] = "NO"
        row["review_status"] = "PENDING_VISUAL_REVIEW"
    fields = list(ordered[0].keys()) if ordered else []
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ordered)

    groups = {}
    for row in rows:
        groups.setdefault(row["photo_id"], []).append(row)
    cards = []
    for rank, row in enumerate(ordered, 1):
        pid = row["photo_id"]
        items = sorted(groups.get(pid, []), key=lambda r: {"overview":0,"center":1,"left":2,"right":3}.get(r["candidate_id"],9))
        title = row.get("building_name") or row.get("building_osm_id") or "Building match unverified"
        meta = f'Priority #{rank} · {title} · wall distance: {row.get("wall_distance_m") or "unknown"} m · heading diff: {row.get("heading_difference_deg") or "unknown"}°'
        thumbs = "".join(
            f'<figure><a href="{html.escape(i["crop_path"])}"><img loading="lazy" src="{html.escape(i["crop_path"])}" alt="{html.escape(pid+" "+i["candidate_id"])}"></a><figcaption>{html.escape(i["candidate_id"])}</figcaption></figure>'
            for i in items
        )
        original = html.escape(row.get("source_image") or f'kartaview/images/{pid}.jpg')
        cards.append(f'<section class="card"><h2>{html.escape(meta)}</h2><p>Photo ID: {html.escape(pid)} · OSM: {html.escape(row.get("building_osm_id",""))} · <a href="{original}">open original frame</a></p><div class="thumbs">{thumbs}</div><p class="warning">NOT APPROVED FOR GAME USE — confirm this is the correct building; crop out road, people, vehicles and neighbouring facades; correct perspective before use.</p></section>')
    doc = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KartaView facade crop review</title><style>
body{font:15px/1.45 system-ui,sans-serif;margin:0;background:#f3f5f8;color:#18212b}header{background:#142338;color:white;padding:18px}header p{max-width:900px}.wrap{max-width:1200px;margin:auto;padding:14px}.card{background:white;border:1px solid #d7dee8;border-radius:10px;padding:12px;margin:14px 0}.card h2{font-size:16px;margin:0 0 5px}.thumbs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}figure{margin:0;min-width:0}img{width:100%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#e8edf3;border:1px solid #ccd5df}figcaption{font-size:12px;text-align:center}a{color:#075eac}.warning{font-weight:600;color:#8c3b13;font-size:13px}@media(max-width:650px){.thumbs{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style></head><body><header><h1>KartaView facade crop review</h1><p>Generated crop candidates from existing repository photos. Sorted by proximity and camera heading as a review aid, not as proof of facade identity. No candidate is approved automatically for the game.</p><p>Attribution: © Grab and KartaView Contributors · check CC BY-SA 4.0 source terms.</p></header><main class="wrap">''' + "".join(cards) + "</main></body></html>"
    OUT_HTML.write_text(doc, encoding="utf-8")
    print(f"Gallery generated: {OUT_HTML}")
    print(f"Priority queue: {OUT_CSV}")
    print(f"Original photos indexed: {len(ordered)}; candidate crops referenced: {len(rows)}")

if __name__ == "__main__":
    main()
