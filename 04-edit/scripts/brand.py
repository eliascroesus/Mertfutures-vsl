"""Iman-style brand system for Ricky's VSL: the glowing purple plate, per-letter blur-in text (ASS), headline over
A-roll with a handwritten sub-line, underlines, and framed cards with a tilt and glow."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
PURPLE = (150, 92, 255)
PURPLE_ASS = "&HFF5C96&"          # BGR of PURPLE
PURPLE_SOFT_ASS = "&HFF9BC4&"


def plate(seed=3):
    """Near-black background with a soft purple glow sweeping in from the lower right (like Iman's lime cards)."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32) + np.array([7, 6, 11], np.float32)

    def glow(cx, cy, r, color, strength):
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 2.2 * strength
        return a[..., None] * np.array(color, np.float32)

    img += glow(1900, 1250, 1250, PURPLE, 0.55)
    img += glow(1500, 1150, 600, (190, 140, 255), 0.25)
    img += glow(-100, -150, 900, PURPLE, 0.10)
    # a curved band of light, like the glowing edge in Iman's cards
    band = np.exp(-((np.sqrt((x - 2350) ** 2 + (y - 1700) ** 2) - 1250) / 24) ** 2)
    band *= np.clip((x - 900) / 900, 0, 1) * np.clip((1080 - y) / 700 + 0.3, 0, 1)
    img += band[..., None] * np.array([120, 70, 230], np.float32) * 0.55
    rng = np.random.default_rng(seed)
    img += rng.normal(0, 2.2, (H, W, 1)).astype(np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def ass_reveal(text, start_ms=0, stagger=28, dur=300, blur=14, color=None, extra=""):
    """Per-letter blur-in from the left, as in Iman's text cards. Returns ASS text."""
    out = []
    i = 0
    for ch in text:
        if ch == "\n":
            out.append("\\N")
            continue
        if ch == " ":
            out.append(" ")
            i += 1
            continue
        t0 = start_ms + i * stagger
        c = f"\\c{color}" if color else ""
        out.append(f"{{\\alpha&HFF&\\blur{blur}{c}{extra}\\t({t0},{t0 + dur},\\alpha&H00&\\blur0.6)}}{ch}")
        i += 1
    return "".join(out)


def ass_rich_reveal(parts, start_ms=0, stagger=28, dur=300, blur=14):
    """parts: list of (text, color or None). Keeps one stagger clock across the parts."""
    out, i = [], 0
    for text, color in parts:
        for ch in text:
            if ch == "\n":
                out.append("\\N")
                continue
            if ch == " ":
                out.append(" ")
                i += 1
                continue
            t0 = start_ms + i * stagger
            c = f"\\c{color}" if color else "\\c&HFFFFFF&"
            out.append(f"{{\\alpha&HFF&\\blur{blur}{c}\\t({t0},{t0 + dur},\\alpha&H00&\\blur0.6)}}{ch}")
            i += 1
    return "".join(out), i


def ass_underline(x0, x1, y, t_ms, dur_ms=350, thick=7, color=PURPLE_ASS):
    """A line that draws itself left to right (scale-x from 0 on a left-anchored drawing)."""
    w = x1 - x0
    return (f"{{\\an7\\pos({x0},{y})\\c{color}\\bord0\\shad0\\blur1.5\\fscx0\\t({t_ms},{t_ms + dur_ms},0.6,\\fscx100)}}"
            f"{{\\p1}}m 0 0 l {w} 0 {w} {thick} 0 {thick}{{\\p0}}")


def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width - 1, img.height - 1), r, fill=255)
    out = img.convert("RGBA")
    a = np.array(out.split()[3]) * (np.array(m) / 255.0)
    out.putalpha(Image.fromarray(a.astype(np.uint8)))
    return out


def framed(img, max_w, max_h, radius=26, glow=True, border=(255, 255, 255, 40), tilt=0.0):
    """A card: rounded corners, thin border, purple glow and soft shadow, optional perspective tilt (degrees)."""
    s = min(max_w / img.width, max_h / img.height)
    img = img.convert("RGB").resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    card = rounded(img, radius)
    ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius, outline=border, width=2)
    pad = 110
    cw, ch = card.width + 2 * pad, card.height + 2 * pad
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    if glow:
        g = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(g).rounded_rectangle((pad - 6, pad - 6, pad + card.width + 6, pad + card.height + 6), radius + 6, fill=200)
        g = g.filter(ImageFilter.GaussianBlur(38))
        layer = Image.new("RGBA", (cw, ch), PURPLE + (0,))
        layer.putalpha(g.point(lambda v: int(v * 0.75)))
        canvas.alpha_composite(layer)
    sh = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 24, pad + card.width, pad + card.height + 24), radius, fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(30))
    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    shadow.putalpha(sh)
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(card, (pad, pad))
    if tilt:
        canvas = perspective_tilt(canvas, tilt)
    return canvas


def perspective_tilt(img, deg):
    """Rotate around the vertical axis by `deg` (positive: right side recedes)."""
    w, h = img.size
    k = math.tan(math.radians(abs(deg))) * 0.5
    shrink = h * k * 0.5
    if deg > 0:
        dst = [(0, 0), (w, shrink), (w, h - shrink), (0, h)]
    else:
        dst = [(0, shrink), (w, 0), (w, h), (0, h - shrink)]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = _persp_coeffs(dst, src)
    return img.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def _persp_coeffs(pa, pb):
    A = []
    for (x, y), (u, v) in zip(pa, pb):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(A, float)
    B = np.array([c for p in pb for c in p], float)
    return np.linalg.solve(A, B).tolist()


def sticker(img, max_w, max_h, rot=-3.0, border=10, radius=18):
    """A photo 'popping up' beside Ricky: white border, rounded, slight rotation, shadow."""
    s = min(max_w / img.width, max_h / img.height)
    img = img.convert("RGB").resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    framed_img = Image.new("RGB", (img.width + 2 * border, img.height + 2 * border), (250, 250, 252))
    framed_img.paste(img, (border, border))
    card = rounded(framed_img, radius)
    pad = 60
    canvas = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 16, pad + card.width, pad + card.height + 16), radius, fill=160)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(22)))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(card, (pad, pad))
    return canvas.rotate(rot, resample=Image.BICUBIC, expand=True)
