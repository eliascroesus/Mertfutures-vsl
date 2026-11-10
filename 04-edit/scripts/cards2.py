"""Iman-style versions of the results cards: same crops and redactions as cards.py, framed with a purple glow and an
optional tilt, plus a copy with the key numbers outlined (crossfaded in by the compositor). Photos can also be made
into 'stickers' that pop up beside Ricky."""
import os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import pillow_heif

sys.path.insert(0, "/home/user/work/scripts")
import brand as B
import cards as C

pillow_heif.register_heif_opener()
OUT = "/home/user/work/gfx/v2"
os.makedirs(OUT, exist_ok=True)


def source(name):
    """Cropped + redacted source image and highlight boxes (fractions of the crop)."""
    fn, crop, blurs, hls, _ = C.SPECS[name]
    im = ImageOps.exif_transpose(Image.open(f"{C.SRC}/{fn}")).convert("RGB")
    Wd, Hd = im.size
    for b in blurs:
        x0, y0, x1, y1 = C.pct_box(b[:4], Wd, Hd)
        radius = b[4] if len(b) > 4 else max(8, (y1 - y0) // 2)
        im.paste(im.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(radius)), (x0, y0))
    cx0, cy0, cx1, cy1 = C.pct_box(crop, Wd, Hd) if crop else (0, 0, Wd, Hd)
    im = im.crop((cx0, cy0, cx1, cy1))
    rel = []
    for b in hls:
        x0, y0, x1, y1 = C.pct_box(b, Wd, Hd)
        rel.append(((x0 - cx0) / im.width, (y0 - cy0) / im.height, (x1 - cx0) / im.width, (y1 - cy0) / im.height))
    return im, rel


def with_highlights(im, rel):
    im = im.convert("RGBA")
    w, h = im.size
    k = max(1.0, w / 900)
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    line = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for x0, y0, x1, y1 in rel:
        box = (x0 * w - 8 * k, y0 * h - 8 * k, x1 * w + 8 * k, y1 * h + 8 * k)
        ImageDraw.Draw(glow).rounded_rectangle(box, int(14 * k), outline=B.PURPLE + (230,), width=int(14 * k))
        ImageDraw.Draw(line).rounded_rectangle(box, int(14 * k), outline=(176, 128, 255, 255), width=int(5 * k))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9 * k)))
    im.alpha_composite(line)
    return im.convert("RGB")


def card(name, max_w=1150, max_h=740, tilt=0.0):
    """Returns (card_path, hl_path or None)."""
    tag = f"{name}_{max_w}x{max_h}_t{tilt:g}"
    p, ph = f"{OUT}/card_{tag}.png", f"{OUT}/cardhl_{tag}.png"
    im, rel = source(name)
    if not os.path.exists(p):
        B.framed(im, max_w, max_h, tilt=tilt).save(p)
    if rel and not os.path.exists(ph):
        B.framed(with_highlights(im, rel), max_w, max_h, tilt=tilt).save(ph)
    return p, (ph if rel else None)


def sticker(name, max_w=520, max_h=560, rot=-3.0):
    tag = f"{name}_{max_w}x{max_h}_r{rot:g}"
    p = f"{OUT}/sticker_{tag}.png"
    if not os.path.exists(p):
        im, _ = source(name)
        B.sticker(im, max_w, max_h, rot=rot).save(p)
    return p
