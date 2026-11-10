"""Grab a frame from the middle of every title, card, box, insert and label in an edit list and tile them into sheets."""
import json, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont
edl, video, outdir = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
os.makedirs(outdir, exist_ok=True)
pts = []
for t in edl["titles"]:
    if t["text"]: pts.append(((t["t0"] + t["t1"]) / 2, "title " + t["text"][:18].replace("\n", " ")))
for c in edl["cards"]: pts.append((c["at"] + c["dur"] * 0.6, "card " + c["name"]))
for b in edl["boxes"]: pts.append(((b["t0"] + b["t1"]) / 2, "box"))
for i in edl["inserts"]: pts.append((i["at"] + i["dur"] / 2, "insert " + os.path.basename(i["file"])))
for l in edl["labels"]: pts.append(((l["t0"] + l["t1"]) / 2, "label"))
pts.sort()
f = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 18)
tiles = []
for t, name in pts:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=640:360",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    im = Image.frombytes("RGB", (640, 360), raw)
    d = ImageDraw.Draw(im); d.rectangle([0, 0, 640, 24], fill=(0, 0, 0)); d.text((4, 3), f"{int(t // 60)}:{t % 60:04.1f}  {name}", fill=(255, 255, 0), font=f)
    tiles.append(im)
for s in range(0, len(tiles), 12):
    grp = tiles[s:s + 12]; o = Image.new("RGB", (640 * 4, 360 * ((len(grp) + 3) // 4)))
    for i, im in enumerate(grp): o.paste(im, ((i % 4) * 640, (i // 4) * 360))
    o.save(f"{outdir}/qa_{s // 12 + 1:02d}.jpg", quality=85)
print(len(tiles), "frames")
