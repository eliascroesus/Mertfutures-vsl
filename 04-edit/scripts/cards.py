"""Results cards: each picture cropped/redacted, framed with rounded corners and a soft shadow.

For every card two PNGs of the same size are written: card_<name>.png and hl_<name>.png (a purple outline around
the key number, animated in a beat after the card lands). Positions are percentages of the source image.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
SRC = "/home/user/rickyvsl-clips/02-results-and-b-roll"
OUT = sys.argv[1] if __name__ == "__main__" and len(sys.argv) > 1 else "/home/user/work/gfx/cards"
ACCENT = (169, 112, 255)
PAD = 70                           # room for the shadow

# name: (file, crop %, blur regions %, highlight boxes %, max size (w, h))
SPECS = {
    "yt_sept_91m":   ("IMG_0038.PNG", None, [], [(64.4, 1.5, 78.3, 10.5), (78.5, 23, 94, 33)], (1500, 820)),
    "yt_sept_44m":   ("IMG_0042.PNG", None, [], [(63.9, 12, 78.1, 27)], (1500, 820)),
    "yt_sept_60m":   ("IMG_0043.PNG", None, [], [(63.9, 12, 78.1, 27)], (1500, 820)),
    "yt_48h_11m":    ("IMG_0041.PNG", (0, 12, 100, 100), [], [(29, 34, 71, 47)], (900, 860)),
    "yt_50m":        ("IMG_8168.PNG", (0, 6, 100, 62), [], [(2.5, 19, 31, 28.5)], (900, 860)),
    "yt_first_money": ("IMG_5101.PNG", (0, 6, 100, 91), [], [(6, 28.5, 36, 34.5), (79, 68, 96, 91)], (900, 860)),
    "shop_36k":      ("IMG_0028.HEIC", (47, 24, 97, 53), [], [(54, 34.3, 65, 38.8)], (1100, 860)),
    "shop_11k":      ("IMG_0037.PNG", (0, 30, 100, 100), [], [(13.5, 33, 42.5, 44.5)], (1100, 860)),
    "shop_today_2k": ("IMG_0045.PNG", (0, 6, 100, 44), [], [(2, 18, 23, 24.5)], (1000, 860)),
    "shop_payout":   ("IMG_0039.PNG", (0, 24, 100, 100), [], [(5, 88.5, 34, 97)], (900, 860)),
    "shop_laptop_night": ("IMG_8623.HEIC", None, [(9, 37, 18, 39), (10, 38.4, 57.5, 40.1), (53.3, 40.3, 57.7, 42.1)], [], (900, 860)),
    "night_laptop":  ("IMG_8623.HEIC", None, [(4.5, 35.5, 58, 62.5, 28)], [], (900, 860)),
    "playbuttons_4": ("IMG_3928.HEIC", None, [], [], (900, 860)),
    "playbutton_lv": ("IMG_8301.HEIC", None, [], [], (900, 860)),
    "gwagon":        ("IMG_9974.HEIC", None, [], [], (900, 860)),
    "labels_strip":  ("IMG_3280.HEIC", None, [], [], (900, 860)),
    "labels_stack":  ("IMG_3292.HEIC", None, [], [], (900, 860)),
}


def pct_box(box, w, h):
    x0, y0, x1, y1 = box
    return int(x0 * w / 100), int(y0 * h / 100), int(x1 * w / 100), int(y1 * h / 100)


def build(name, spec):
    fn, crop, blurs, hls, (mw, mh) = spec
    im = ImageOps.exif_transpose(Image.open(f"{SRC}/{fn}")).convert("RGB")
    W, H = im.size
    for b in blurs:                                  # redact before cropping, in source coordinates
        x0, y0, x1, y1 = pct_box(b[:4], W, H)
        radius = b[4] if len(b) > 4 else max(8, (y1 - y0) // 2)
        region = im.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(radius))
        im.paste(region, (x0, y0))
    cx0, cy0, cx1, cy1 = pct_box(crop, W, H) if crop else (0, 0, W, H)
    im = im.crop((cx0, cy0, cx1, cy1))
    # highlight boxes re-expressed relative to the crop
    rel = []
    for b in hls:
        x0, y0, x1, y1 = pct_box(b, W, H)
        rel.append(((x0 - cx0) / im.width, (y0 - cy0) / im.height, (x1 - cx0) / im.width, (y1 - cy0) / im.height))
    s = min(mw / im.width, mh / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    w, h = im.size
    r = max(14, int(min(w, h) * 0.035))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    canvas = Image.new("RGBA", (w + 2 * PAD, h + 2 * PAD), (0, 0, 0, 0))
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((PAD, PAD + 18, PAD + w, PAD + h + 18), r, fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    canvas.paste(Image.new("RGBA", canvas.size, (0, 0, 0, 255)), (0, 0), sh)
    card = im.convert("RGBA")
    card.putalpha(mask)
    canvas.alpha_composite(card, (PAD, PAD))
    ImageDraw.Draw(canvas).rounded_rectangle((PAD, PAD, PAD + w - 1, PAD + h - 1), r, outline=(255, 255, 255, 46), width=2)
    canvas.save(f"{OUT}/card_{name}.png")
    hl = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    if rel:
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        g, d = ImageDraw.Draw(glow), ImageDraw.Draw(hl)
        for (x0, y0, x1, y1) in rel:
            box = (PAD + x0 * w - 6, PAD + y0 * h - 6, PAD + x1 * w + 6, PAD + y1 * h + 6)
            g.rounded_rectangle(box, 14, outline=ACCENT + (200,), width=12)
            d.rounded_rectangle(box, 14, outline=ACCENT + (255,), width=5)
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        glow.alpha_composite(hl)
        hl = glow
    hl.save(f"{OUT}/hl_{name}.png")
    return {"w": canvas.width, "h": canvas.height, "card_w": w, "card_h": h, "has_highlight": bool(rel)}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    meta = {n: build(n, s) for n, s in SPECS.items()}
    json.dump(meta, open(f"{OUT}/cards.json", "w"), indent=1)
    for n, m in meta.items():
        print(n, m)
