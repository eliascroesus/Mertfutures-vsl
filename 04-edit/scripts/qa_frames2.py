"""Stills from the middle of every title, headline, card, sticker, clip and frame in a v2 plan."""
import json, re, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont
els, ass, video, outdir = json.load(open(sys.argv[1])), open(sys.argv[2]).read(), sys.argv[3], sys.argv[4]
lim = float(sys.argv[5]) if len(sys.argv) > 5 else 1e9
os.makedirs(outdir, exist_ok=True)
def secs(s):
    h, m, x = s.split(":"); return int(h) * 3600 + int(m) * 60 + float(x)
pts = []
for e in els["elements"]:
    pts.append(((e["t0"] + e["t1"]) / 2, e["type"] + " " + os.path.basename(e.get("img", e.get("file", "")))[:28]))
seen = set()
for line in ass.splitlines():
    mm = re.match(r"Dialogue: (\d+),([^,]+),([^,]+),(Big|Head),", line)
    if mm and mm.group(2) not in seen:
        seen.add(mm.group(2)); a, b = secs(mm.group(2)), secs(mm.group(3))
        pts.append((a + min(1.2, (b - a) * 0.7), mm.group(4).lower()))
pts = sorted(p for p in pts if p[0] < lim)
f = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 18)
tiles = []
for t, name in pts:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=640:360", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    if len(raw) < 640 * 360 * 3: continue
    im = Image.frombytes("RGB", (640, 360), raw); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 640, 24], fill=(0, 0, 0)); d.text((4, 3), f"{int(t // 60)}:{t % 60:04.1f} {name}", fill=(255, 255, 0), font=f)
    tiles.append(im)
for s in range(0, len(tiles), 16):
    g = tiles[s:s + 16]; o = Image.new("RGB", (2560, 360 * ((len(g) + 3) // 4)))
    for i, im in enumerate(g): o.paste(im, ((i % 4) * 640, (i // 4) * 360))
    o.save(f"{outdir}/qa_{s // 16 + 1:02d}.jpg", quality=82)
print(len(tiles), "frames")
