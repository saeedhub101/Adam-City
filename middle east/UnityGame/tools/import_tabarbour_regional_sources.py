#!/usr/bin/env python3
"""Keyless regional source packer for Tabarbour: OpenFreeMap vector tiles and NASA GIBS imagery.
No API key/token. Packages tiles into MBTiles to avoid thousands of tiny repository files.
Tiles are source evidence/basemap inputs, not building facade photography.
"""
import datetime, json, math, os, pathlib, sqlite3, subprocess, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
OUT = ROOT / "middle east/BuildGLB/tabarbour-real/source"
BOUNDS = (35.90, 31.96, 35.99, 32.04)  # west,south,east,north
UA = "Adam-City-Tabarbour-source-import/1.0 (keyless open data workflow)"
def xyz(lon, lat, z):
    lat = max(-85.05112878, min(85.05112878, lat))
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return max(0,min(n-1,x)), max(0,min(n-1,y))
def tiles_for_bounds(z):
    w,s,e,n = BOUNDS
    x0,y1 = xyz(w,s,z); x1,y0 = xyz(e,n,z)
    return [(z,x,y) for x in range(min(x0,x1),max(x0,x1)+1) for y in range(min(y0,y1),max(y0,y1)+1)]
def fetch(url, timeout=35):
    req=urllib.request.Request(url, headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type","")
def mbtiles(path, name, fmt, attribution):
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS metadata (name TEXT, value TEXT)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS metadata_name ON metadata(name)")
    db.execute("CREATE TABLE IF NOT EXISTS tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS tile_index ON tiles(zoom_level,tile_column,tile_row)")
    meta={"name":name,"type":"baselayer","version":"1","description":"Tabarbour, Amman regional extract","format":fmt,"bounds":",".join(map(str,BOUNDS)),"attribution":attribution}
    for k,v in meta.items(): db.execute("INSERT OR REPLACE INTO metadata(name,value) VALUES(?,?)",(k,v))
    return db
def checkpoint(paths, message):
    """Commit a durable MBTiles/report checkpoint to main while the workflow is still running."""
    root=ROOT
    try:
        subprocess.run(["git","add","--",*[str(p.relative_to(root)) for p in paths]],cwd=root,check=True)
        if subprocess.run(["git","diff","--cached","--quiet"],cwd=root).returncode==0:
            return True
        subprocess.run(["git","-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com",
                       "commit","-m",message],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for attempt in range(1,6):
            fetch=subprocess.run(["git","fetch","origin","main"],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            if fetch.returncode:
                time.sleep(attempt); continue
            rb=subprocess.run(["git","rebase","origin/main"],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            if rb.returncode:
                subprocess.run(["git","rebase","--abort"],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                time.sleep(attempt); continue
            push=subprocess.run(["git","push","origin","HEAD:main"],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            if push.returncode==0:
                print("SOURCE_CHECKPOINT_PUSHED",message,flush=True); return True
            time.sleep(attempt)
        print("SOURCE_CHECKPOINT_PUSH_FAILED",message,flush=True)
        return False
    except Exception as e:
        print("SOURCE_CHECKPOINT_ERROR",message,repr(e),flush=True)
        return False

def run_tiles(label, path, url_fn, zooms, fmt, attribution, max_tiles=None):
    db=mbtiles(path,label,fmt,attribution); total=ok=0; errors=[]
    try:
        tiles=[t for z in zooms for t in tiles_for_bounds(z)]
        if max_tiles: tiles=tiles[:max_tiles]
        total=len(tiles)
        for i,(z,x,y) in enumerate(tiles,1):
            try:
                data,ctype=fetch(url_fn(z,x,y))
                if len(data)<100 or ("image" not in ctype.lower() and fmt!="pbf"):
                    raise ValueError("unexpected payload/content-type "+ctype+" bytes="+str(len(data)))
                tms_y=(2**z-1)-y
                db.execute("INSERT OR REPLACE INTO tiles VALUES(?,?,?,?)",(z,x,tms_y,data))
            except Exception as e:
                errors.append({"z":z,"x":x,"y":y,"error":repr(e)[:180]})
            if i%50==0:
                db.commit()
                write_report(label,path,total,ok=i-len(errors),errors=errors,complete=False)
                print(label,"checkpoint",i,"/",total,"failed",len(errors),flush=True)
                if i % 250 == 0:
                    checkpoint([path, OUT/"regional-source-import-report.json"],"Checkpoint "+label+" tile batch "+str(i))
        db.commit()
    finally: db.close()
    result={"status":"complete_with_gaps" if errors else "complete","tiles_expected":total,"tiles_saved":total-len(errors),"errors":errors[:100],"error_count":len(errors),"file":str(path.relative_to(ROOT)),"bytes":path.stat().st_size if path.exists() else 0}
    write_report(label,path,total,ok=total-len(errors),errors=errors,complete=True,extra=result)
    checkpoint([path, OUT/"regional-source-import-report.json"],"Save completed "+label+" tile database")
    return result
def write_report(label,path,total,ok,errors,complete,extra=None):
    p=OUT/"regional-source-import-report.json"
    try: report=json.loads(p.read_text(encoding="utf-8"))
    except Exception: report={"area":"Tabarbour, Amman, Jordan","bounds":{"west":BOUNDS[0],"south":BOUNDS[1],"east":BOUNDS[2],"north":BOUNDS[3]},"sources":{}}
    report["sources"][label]={"status":"complete" if complete and not errors else "in_progress" if not complete else "complete_with_gaps","expected_tiles":total,"saved_tiles":ok,"error_count":len(errors),"errors_sample":errors[:20],"file":str(path.relative_to(ROOT))}
    if extra: report["sources"][label].update(extra)
    report["updated_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    tmp=p.with_suffix(".json.part");tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(p)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    results={}
    # Public OpenFreeMap vector tile service. Zoom 12-17, packaged into one MBTiles database.
    results["openfreemap_vector_tiles"]=run_tiles(
      "openfreemap_vector_tiles",OUT/"openfreemap-tabarbour-z12-17.mbtiles",
      lambda z,x,y:f"https://tiles.openfreemap.org/planet/{z}/{x}/{y}.pbf",
      range(12,18),"pbf","© OpenStreetMap contributors; OpenFreeMap / OpenMapTiles")
    # NASA GIBS Sentinel-2 L1C imagery, keyless WMTS tiles. Top-down imagery is useful for
    # land cover/context but is not street-level facade photography. Gaps are explicitly reported.
    day=(datetime.date.today()-datetime.timedelta(days=45)).isoformat()
    results["nasa_gibs_satellite"]=run_tiles(
      "nasa_gibs_satellite",OUT/"nasa-gibs-sentinel2-tabarbour.mbtiles",
      lambda z,x,y:f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Sentinel-2_L1C/default/{day}/GoogleMapsCompatible_Level13/{z}/{y}/{x}.jpg",
      range(10,14),"jpg","NASA GIBS Sentinel-2 L1C imagery; top-down satellite imagery, not facade photos")
    write_report("summary",OUT/"regional-source-import-report.json",0,0,[],True,{"results":results})
    print(json.dumps(results,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__": main()
