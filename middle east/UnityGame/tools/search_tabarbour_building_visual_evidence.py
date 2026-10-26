#!/usr/bin/env python3
"""No-key, non-API building visual-evidence discovery for Tabarbour.

Indexes every saved OSM building by its own footprint centroid. For named buildings,
queries ordinary Google/Bing HTML search pages (not API endpoints), and records source
pages as candidates only. Every record also gets direct Google Maps/Satellite/Street View
and image-search links so an operator can inspect the actual facade. Never auto-assigns
search-result images as GLB textures.
"""
import gzip, hashlib, html, json, os, pathlib, re, subprocess, time, urllib.parse, urllib.request
from html.parser import HTMLParser

ROOT = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
BASE = ROOT / "middle east/BuildGLB/tabarbour-real/photos"
INPUTS = [
    ROOT / "middle east/BuildGLB/tabarbour-real/source/layers/buildings.geojson.gz",
    ROOT / "middle east/Jordan/layers/buildings.geojson.gz",
]
OUT_GZ = BASE / "building-visual-search-index.jsonl.gz"
REPORT = BASE / "building-visual-search-report.json"
GALLERY = BASE / "building-image-review.html"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_RETRIES = 3

def norm(v):
    return " ".join(re.sub(r"[^\w\s-]", " ", str(v or "").casefold()).split())

def centroid(geometry):
    if not geometry: return None
    typ, coords = geometry.get("type"), geometry.get("coordinates")
    pts = []
    def collect(v, depth=0):
        if not isinstance(v, (list, tuple)): return
        if len(v) >= 2 and isinstance(v[0], (int, float)) and isinstance(v[1], (int, float)):
            pts.append((float(v[0]), float(v[1])))
            return
        for item in v: collect(item, depth + 1)
    collect(coords)
    if not pts: return None
    # A coordinate mean is stable for local building footprints and avoids requiring GIS libraries.
    return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.image_records=[]; self.title=""; self._title=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"):
            self.links.append((a["href"], a.get("aria-label","")))
            if "iusc" in a.get("class","").split() and a.get("m"):
                try:
                    meta=json.loads(html.unescape(a["m"]))
                    if meta.get("murl"):
                        self.image_records.append({"image_url":meta.get("murl"),"thumbnail_url":meta.get("turl"),
                            "source_page":meta.get("purl"),"title":meta.get("t","")})
                except Exception:
                    pass
        if tag=="title": self._title=True
    def handle_endtag(self, tag):
        if tag=="title": self._title=False
    def handle_data(self, data):
        if self._title: self.title += data

def fetch_search(url, engine):
    req=urllib.request.Request(url, headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
    last=None
    for attempt in range(1, MAX_RETRIES+1):
        try:
            with urllib.request.urlopen(req, timeout=18) as r:
                body=r.read(3_000_000).decode("utf-8","replace")
            p=Links(); p.feed(body)
            found=[]
            for href, label in p.links:
                href=html.unescape(href)
                if engine=="google":
                    if href.startswith("/url?"):
                        q=urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("q",[])
                        href=q[0] if q else href
                    if not href.startswith("http") or "google.com" in urllib.parse.urlparse(href).netloc: continue
                elif engine=="bing":
                    if not href.startswith("http") or "bing.com" in urllib.parse.urlparse(href).netloc: continue
                if href not in [x["url"] for x in found]:
                    found.append({"url":href,"anchor":label[:180]})
                if len(found)>=12: break
            return {"status":"ok" if found else "no_results_or_blocked","page_title":p.title[:180],"results":found,"images":p.image_records[:12]}
        except Exception as e:
            last=repr(e)
            if attempt<MAX_RETRIES: time.sleep(attempt*2)
    return {"status":"failed","error":last,"results":[],"images":[]}

def write_outputs(records, report):
    BASE.mkdir(parents=True,exist_ok=True)
    tmp=OUT_GZ.with_suffix(".jsonl.gz.part")
    with gzip.open(tmp,"wt",encoding="utf-8",compresslevel=6) as f:
        for row in records: f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\\n")
    tmp.replace(OUT_GZ)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

def write_gallery(records):
    # Review-only HTML. The game never loads these remote images; nothing is assigned to GLB.
    cards=[]
    for r in records:
        if not r.get("name") or not r.get("candidates"): continue
        imgs=[x for x in r["candidates"] if x.get("image_url","").startswith("http")]
        if not imgs: continue
        links=r.get("search_urls",{})
        block=[f'<article><h3>{html.escape(r.get("name") or r["osm_id"])}</h3>',
               f'<p>OSM {html.escape(r["osm_id"])} · {r.get("latitude")}, {r.get("longitude")}</p>',
               f'<p><a href="{html.escape(links.get("google_maps",""),quote=True)}">Google Maps</a> · '
               f'<a href="{html.escape(links.get("google_street_view",""),quote=True)}">Street View</a> · '
               f'<a href="{html.escape(links.get("google_images",""),quote=True)}">Google Images</a></p>']
        for im in imgs[:6]:
            iu=html.escape(im.get("image_url",""),quote=True)
            sp=html.escape(im.get("source_page") or im.get("image_url",""),quote=True)
            title=html.escape(im.get("title","Unverified image candidate"))
            block.append(f'<a class="photo" href="{sp}" target="_blank" rel="noopener"><img loading="lazy" src="{iu}" alt="{title}"><span>{title}</span></a>')
        block.append('<p class="warning">Candidate only — visually confirm the exact building and image rights before use.</p></article>')
        cards.append("".join(block))
    GALLERY.write_text("""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Tabarbour building image review</title><style>body{font:16px system-ui;margin:1rem;background:#f4f4f4;color:#222}article{background:white;border:1px solid #ddd;border-radius:10px;padding:1rem;margin:1rem 0}article h3{margin:.2rem 0}.photos{display:flex;gap:12px;flex-wrap:wrap}.photo{display:inline-flex;flex-direction:column;width:min(220px,44%);margin:.3rem;text-decoration:none;color:inherit}.photo img{width:100%;height:150px;object-fit:contain;background:#eee}.warning{color:#8a3b00;font-weight:600}</style><h1>Tabarbour — building image review</h1><p>Images are unverified search candidates loaded from their source websites for manual review. This page is not used by the game and does not assign textures automatically.</p>"""+"".join(cards)+"</html>",encoding="utf-8")

def checkpoint():
    rel=[str(OUT_GZ.relative_to(ROOT)),str(REPORT.relative_to(ROOT)),str(GALLERY.relative_to(ROOT))]
    subprocess.run(["git","add","--",*rel],cwd=ROOT,check=True)
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT).returncode==0: return
    subprocess.run(["git","-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com","commit","-m","Checkpoint Tabarbour per-building visual evidence search"],cwd=ROOT,check=True)
    for attempt in range(1,6):
        if subprocess.run(["git","fetch","origin","main"],cwd=ROOT).returncode:
            time.sleep(attempt); continue
        rb=subprocess.run(["git","rebase","origin/main"],cwd=ROOT)
        if rb.returncode:
            subprocess.run(["git","rebase","--abort"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(attempt); continue
        if subprocess.run(["git","push","origin","HEAD:main"],cwd=ROOT).returncode==0:
            print("BUILDING_VISUAL_EVIDENCE_CHECKPOINTED",flush=True); return
        time.sleep(attempt)
    raise RuntimeError("Could not push visual evidence checkpoint to main")

def main():
    source=next((p for p in INPUTS if p.is_file()),None)
    if not source: raise FileNotFoundError("No local buildings.geojson.gz found in Tabarbour or Jordan layers")
    with gzip.open(source,"rt",encoding="utf-8") as f: data=json.load(f)
    features=data.get("features",[])
    old={}
    if REPORT.is_file():
        try: old=json.loads(REPORT.read_text(encoding="utf-8"))
        except Exception: pass
    done=set(old.get("searched_osm_ids",[]))
    records=[]
    if OUT_GZ.is_file():
        try:
            with gzip.open(OUT_GZ,"rt",encoding="utf-8") as f:
                records=[json.loads(line) for line in f if line.strip()]
        except Exception: records=[]
    by_id={r["osm_id"]:r for r in records if r.get("osm_id")}
    named=[]
    for ft in features:
        props=ft.get("properties") or {}
        geom=ft.get("geometry") or {}
        ll=centroid(geom)
        if not ll: continue
        fid=ft.get("id") or props.get("@id") or props.get("osm_id") or props.get("way_id") or props.get("relation_id")
        if fid is None: continue
        fid=str(fid)
        if "/" not in fid: fid=str(props.get("@type") or props.get("type") or "way")+"/"+fid
        lon,lat=ll
        name=next((str(props.get(k)) for k in ("name","name:en","name:ar","official_name","brand") if props.get(k)), "")
        query=" ".join(x for x in [name,"building", "Tabarbour Amman Jordan",f"{lat:.6f} {lon:.6f}"] if x)
        q=urllib.parse.quote(query)
        coord=f"{lat:.7f},{lon:.7f}"
        rec=by_id.get(fid,{
            "osm_id":fid,"name":name or None,"latitude":round(lat,7),"longitude":round(lon,7),
            "geometry_type":geom.get("type"),"source_feature_properties":{k:props.get(k) for k in ("building","height","building:levels","addr:street","addr:housenumber","shop","amenity","brand","name","name:en","name:ar") if props.get(k) is not None},
            "search_urls":{
                "google_web":"https://www.google.com/search?q="+q,
                "google_images":"https://www.google.com/search?tbm=isch&q="+q,
                "google_maps":"https://www.google.com/maps/@"+coord+",20z",
                "google_street_view":"https://www.google.com/maps/@?layer=c&cbll="+coord,
                "bing_images":"https://www.bing.com/images/search?q="+q,
                "wikimedia_commons":"https://commons.wikimedia.org/w/index.php?search="+q+"&title=Special:MediaSearch&type=image",
                "openverse":"https://openverse.org/search/image?q="+q,
                "openstreetmap":"https://www.openstreetmap.org/"+urllib.parse.quote(fid,safe="/")
            },
            "candidates":[],"verification":{"status":"unverified","rule":"Never assign an image to a building based on proximity or search-result title alone."}
        })
        by_id[fid]=rec
        if name and fid not in done: named.append((fid,rec,query))
    # Save the full building-to-coordinate index before slow web discovery.
    records=list(by_id.values())
    report={"area":"Tabarbour, Amman, Jordan","source_file":str(source.relative_to(ROOT)),
            "buildings_indexed":len(records),"named_buildings_total":sum(1 for r in records if r.get("name")),
            "named_buildings_searched":len(done),"search_engines":["Google ordinary HTML search","Bing ordinary HTML image search"],
            "no_api_keys_or_api_endpoints":True,"auto_facade_texture_assignment":False,
            "search_policy":"Coordinates are the centroid of each saved OSM footprint. Search results are candidates only; visually compare facade, address, camera direction and footprint before accepting.",
            "searched_osm_ids":sorted(done),"updated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    write_outputs(records,report); checkpoint()
    # Search named buildings first; all buildings still receive coordinate-specific maps/image-search links.
    for idx,(fid,rec,query) in enumerate(named,1):
        q=urllib.parse.quote(query)
        rec["candidates"]=[]
        rec["web_search"] = fetch_search("https://www.google.com/search?q="+q,"google")
        time.sleep(1.25)
        rec["image_search"] = fetch_search("https://www.bing.com/images/search?q="+q,"bing")
        time.sleep(1.25)
        rec["candidates"]=[
            {"source":"Google Search","url":x["url"],"title":x.get("anchor",""),"status":"unverified_candidate"}
            for x in rec["web_search"].get("results",[])
        ] + [
            {"source":"Bing Images source page","url":x.get("source_page") or x.get("image_url"),"image_url":x.get("image_url"),
             "thumbnail_url":x.get("thumbnail_url"),"title":x.get("title",""),"status":"unverified_candidate"}
            for x in rec["image_search"].get("images",[])
        ] + [
            {"source":"Bing Images result page","url":x["url"],"title":x.get("anchor",""),"status":"unverified_candidate"}
            for x in rec["image_search"].get("results",[])
        ]
        rec["verification"]={"status":"needs_visual_review","verified_building_identity":False,"facade_texture_allowed":False}
        done.add(fid)
        if idx%10==0 or idx==len(named):
            records=list(by_id.values())
            report.update({"buildings_indexed":len(records),"named_buildings_searched":len(done),
                           "searched_osm_ids":sorted(done),"last_checkpoint_osm_id":fid,
                           "updated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
            write_outputs(records,report); write_gallery(records); checkpoint()
            print("BUILDING_SEARCH_PROGRESS",idx,"/",len(named),"indexed",len(records),flush=True)
    report.update({"buildings_indexed":len(by_id),"named_buildings_searched":len(done),
                   "searched_osm_ids":sorted(done),"completed":len(done)==sum(1 for r in by_id.values() if r.get("name")),
                   "updated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
    write_outputs(list(by_id.values()),report); write_gallery(list(by_id.values())); checkpoint()
    print(json.dumps({k:v for k,v in report.items() if k!="searched_osm_ids"},ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__": main()
