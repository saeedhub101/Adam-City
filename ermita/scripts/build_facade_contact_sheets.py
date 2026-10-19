#!/usr/bin/env python3
"""Build visual contact sheets for every existing KartaView source and crop."""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import csv, math

ROOT=Path(".")
BASE=ROOT/"kartaview"/"facade-crops"
OUT=BASE/"contact-sheets"
OUT.mkdir(parents=True, exist_ok=True)
try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except: font=ImageFont.load_default()

def sheets(items, label, cols=4, cell_w=360, cell_h=250, batch=24):
    made=[]
    for start in range(0,len(items),batch):
        chunk=items[start:start+batch]
        rows=math.ceil(len(chunk)/cols)
        canvas=Image.new("RGB",(cols*cell_w,rows*cell_h),(238,241,245))
        draw=ImageDraw.Draw(canvas)
        for k,(path,title) in enumerate(chunk):
            x=(k%cols)*cell_w; y=(k//cols)*cell_h
            try:
                im=Image.open(path); im=ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((cell_w-12,cell_h-42))
                canvas.paste(im,(x+(cell_w-im.width)//2,y+4))
                draw.text((x+6,y+cell_h-32),title[:52],font=font,fill=(15,25,35))
            except Exception as e:
                draw.text((x+6,y+12),"FAILED: "+str(path),font=font,fill=(150,0,0))
        name=f"{label}-{start//batch+1:03d}.jpg"
        canvas.save(OUT/name,"JPEG",quality=82,optimize=True)
        made.append(name)
    return made

def main():
    manifest=BASE/"manifest.csv"
    with manifest.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    originals={}
    crops=[]
    for r in rows:
        originals[r["source_image"]]=r["photo_id"]
        crops.append((r["crop_path"],r["photo_id"]+" / "+r["candidate_id"]))
    src=[(p,Path(p).name) for p in sorted(originals) if Path(p).exists()]
    crop_files=[(p,t) for p,t in crops if Path(p).exists()]
    a=sheets(src,"originals")
    b=sheets(crop_files,"crops")
    (OUT/"README.txt").write_text(
        "Visual review contact sheets generated from existing repository assets.\\n"
        f"Original source images displayed: {len(src)}\\n"
        f"Crop candidates displayed: {len(crop_files)}\\n"
        f"Original contact sheets: {', '.join(a)}\\nCrop contact sheets: {', '.join(b)}\\n"
        "These sheets are for inspection only. No crop is automatically approved as a facade texture.\\n",
        encoding="utf-8")
    print(f"Created {len(a)} original sheets and {len(b)} crop sheets for {len(src)} originals and {len(crop_files)} crops.")
if __name__=="__main__": main()
