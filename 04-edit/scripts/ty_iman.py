"""Iman Gadzhi-style motion graphics for the thank-you video (the look of the B5 cards you approved): the near-black
plate with the purple arc glow drifting slowly, wide Unbounded caps that blur in letter by letter as Ricky says each
word, spaced sub lines, purple / red accents with a soft glow, glass icon tiles and glowing tilted frames."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import brand as B
import ty_text as T

W, H = 1920, 1080
PURPLE = B.PURPLE
RED = (255, 34, 34)
COLORS = {"white": (255, 255, 255), "purple": (168, 112, 255), "red": RED, "dim": (205, 200, 220)}
FONTS = {"big": "/root/.local/share/fonts/Unbounded-800.ttf", "sub": "/root/.local/share/fonts/Unbounded-600.ttf",
         "mark": "/root/.local/share/fonts/Unbounded-700.ttf"}
TRACK = {"big": -0.01, "sub": 0.28, "mark": 0.3}


def plate(color=PURPLE, scale=1.06, seed=3):
    """B5's brand plate (near black, a soft glow and a curved band of light from the lower right), any accent colour,
    rendered a little oversize so it can drift."""
    w, h = int(W * scale), int(H * scale)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    x, y = x / scale, y / scale
    img = np.zeros((h, w, 3), np.float32) + np.array([7, 6, 11], np.float32)
    light = tuple(min(255, int(c * 1.25) + 40) for c in color)

    def glow(cx, cy, r, c, s):
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
        return (np.clip(1 - d, 0, 1) ** 2.2 * s)[..., None] * np.array(c, np.float32)

    img += glow(1900, 1250, 1250, color, 0.55)
    img += glow(1500, 1150, 600, light, 0.25)
    img += glow(-100, -150, 900, color, 0.10)
    band = np.exp(-((np.sqrt((x - 2350) ** 2 + (y - 1700) ** 2) - 1250) / 24) ** 2)
    band *= np.clip((x - 900) / 900, 0, 1) * np.clip((1080 - y) / 700 + 0.3, 0, 1)
    img += band[..., None] * np.array([c * 0.8 for c in color], np.float32) * 0.55
    img += np.random.default_rng(seed).normal(0, 2.2, (h, w, 1)).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.float32)


def plate_at(pl, p):
    """Slow After Effects drift: the oversize plate pans a few dozen pixels over the card (p = 0..1)."""
    h, w = pl.shape[:2]
    e = 0.5 - 0.5 * math.cos(math.pi * min(max(p, 0), 1))
    ox, oy = int((w - W) * (1 - e)), int((h - H) * (0.3 + 0.4 * e))
    return pl[oy:oy + H, ox:ox + W]


# ------------------------------------------------------------------ letters
_letters, _blurs = {}, {}


def font(style, size):
    return T.font(size, FONTS[style])


def letter_layout(text, style, size):
    """x offset of every letter (kerning + tracking) and the run's width."""
    f = font(style, size)
    tr = TRACK[style] * size
    xs = [f.getlength(text[:i + 1]) - f.getlength(ch) + tr * i for i, ch in enumerate(text)]
    return xs, (f.getlength(text) + tr * max(len(text) - 1, 0))


def letter_img(ch, style, size, rgb, glow):
    k = (ch, style, size, rgb, glow)
    if k not in _letters:
        f = font(style, size)
        asc, desc = f.getmetrics()
        pad = int(size * 0.45)
        w = int(f.getlength(ch)) + 2 * pad
        m = Image.new("L", (max(w, 1), asc + desc + 2 * pad), 0)
        ImageDraw.Draw(m).text((pad, pad), ch, font=f, fill=255)
        out = Image.new("RGBA", m.size, (0, 0, 0, 0))
        if glow:
            g = Image.new("RGBA", m.size, rgb + (0,))
            g.putalpha(m.filter(ImageFilter.GaussianBlur(size * 0.18)).point(lambda v: int(v * 0.55)))
            out.alpha_composite(g)
        sh = Image.new("RGBA", m.size, (0, 0, 0, 0))
        sh.putalpha(m.filter(ImageFilter.GaussianBlur(size * 0.06)).point(lambda v: int(v * 0.5)))
        out.alpha_composite(sh, (0, int(size * 0.03)))
        fill = Image.new("RGBA", m.size, rgb + (255,))
        fill.putalpha(m)
        out.alpha_composite(fill)
        _letters[k] = (out, pad, asc)
    return _letters[k]


def draw_letters(frame, text, style, size, x0, base, t, t_start, rgb=(255, 255, 255), glow=False, stagger=0.03,
                 dur=0.3, blur=14, alpha=1.0):
    """Iman's per-letter blur-in from the left, starting at t_start."""
    if t < t_start:
        return
    xs, _ = letter_layout(text, style, size)
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        p = (t - t_start - i * stagger) / dur
        if p <= 0:
            continue
        p = min(p, 1.0)
        e = 1 - (1 - p) ** 2
        img, pad, asc = letter_img(ch, style, size, rgb, glow)
        bq = round(blur * (1 - e))
        if bq >= 1:
            k = (ch, style, size, rgb, glow, bq)
            if k not in _blurs:
                if len(_blurs) > 3000:
                    _blurs.clear()
                _blurs[k] = np.asarray(img.filter(ImageFilter.GaussianBlur(bq)))
            arr = _blurs[k]
        else:
            arr = np.asarray(img)
        T.blend(frame, arr, int(round(x0 + xs[i] - pad)), int(round(base - asc - pad)), e * alpha)


# ------------------------------------------------------------------ text rows
def layout_rows(rows, cy, maxw=1640, gap=0.32):
    """rows: [{"words": [[text, t], ...], "style": big|sub, "size": px, "color": name}] -> drawable runs."""
    out, heights = [], []
    for r in rows:
        vis = [(w, t) for w, t in r["words"] if w != "_"]
        text = " ".join(w for w, _ in vis)
        size = r["size"]
        _, lw = letter_layout(text, r["style"], size)
        if lw > maxw:
            size = int(size * maxw / lw)
            _, lw = letter_layout(text, r["style"], size)
        out.append([r, vis, text, size, lw])
        heights.append(size * (0.95 if r["style"] == "big" else 1.0))
    avg = sum(heights) / len(heights)
    gaps = []
    for a, b, ha, hb in zip(out, out[1:], heights, heights[1:]):
        g = gap * avg
        if a[0]["style"] == "sub" and b[0]["style"] == "sub":      # small spaced lines need air between them
            g = max(g, 0.8 * max(ha, hb))
        gaps.append(g)
    total = sum(heights) + sum(gaps)
    y = cy - total / 2
    runs = []
    for i, ((r, vis, text, size, lw), h) in enumerate(zip(out, heights)):
        base = y + h * 0.82
        x0 = (W - lw) / 2
        xs, _ = letter_layout(text, r["style"], size)
        k = 0
        for w, t in vis:                                   # each word starts its letters when he says it
            runs.append({"text": w, "style": r["style"], "size": size, "x": x0 + xs[k], "base": base, "t": t,
                         "rgb": COLORS[r.get("color", "white")], "glow": r.get("color", "white") != "white"})
            k += len(w) + 1
        if r.get("strike") and vis:                        # a red line struck through the row once it's said
            runs.append({"strike": True, "x0": x0 - size * 0.15, "x1": x0 + lw + size * 0.15,
                         "y": base - size * (0.36 if r["style"] == "big" else 0.37), "h": max(4, size * 0.11),
                         "t": vis[-1][1] + 0.3})
        y += h + (gaps[i] if i < len(gaps) else 0)
    return runs, cy - total / 2, cy + total / 2


def draw_strike(frame, r, t, alpha=1.0):
    p = (t - r["t"]) / 0.28
    if p <= 0:
        return
    e = 1 - (1 - min(p, 1)) ** 3
    x1 = r["x0"] + (r["x1"] - r["x0"]) * e
    y0, y1 = int(r["y"] - r["h"] / 2), int(r["y"] + r["h"] / 2)
    xa, xb = int(r["x0"]), int(x1)
    if xb <= xa:
        return
    gl = frame[max(0, y0 - 10):y1 + 10, xa:xb]                 # soft red glow, then the line
    gl *= 0.8
    gl += np.array(RED, np.float32) * 0.2 * alpha
    frame[y0:y1, xa:xb] = frame[y0:y1, xa:xb] * (1 - alpha) + np.array(RED, np.float32) * alpha


def draw_runs(frame, runs, t, alpha=1.0):
    for r in runs:
        if r.get("strike"):
            draw_strike(frame, r, t, alpha)
            continue
        stag = 0.03 if r["style"] == "big" else 0.022
        draw_letters(frame, r["text"], r["style"], r["size"], r["x"], r["base"], t, r["t"], r["rgb"], r["glow"],
                     stagger=stag, dur=0.3, blur=14 if r["style"] == "big" else 10, alpha=alpha)


def draw_mark(frame, t, t0):
    """Small 'YTD' brand mark at the bottom of every card, fading in."""
    a = min(max((t - t0 - 0.2) / 0.3, 0), 1) * 0.45
    if a <= 0:
        return
    _, lw = letter_layout("YTD", "mark", 24)
    draw_letters(frame, "YTD", "mark", 24, (W - lw) / 2, H - 44, t, t0, stagger=0, dur=0.01, blur=0, alpha=a)


# ------------------------------------------------------------------ glass icon tile
def glass_tile(icon_img, label, size=250):
    pad = 90
    S = size + 2 * pad
    out = Image.new("RGBA", (S, S + 90), (0, 0, 0, 0))
    g = Image.new("L", out.size, 0)
    ImageDraw.Draw(g).rounded_rectangle((pad, pad, pad + size, pad + size), 46, fill=170)
    glow = Image.new("RGBA", out.size, PURPLE + (0,))
    glow.putalpha(g.filter(ImageFilter.GaussianBlur(34)).point(lambda v: int(v * 0.6)))
    out.alpha_composite(glow)
    tile = Image.new("RGBA", out.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle((pad, pad, pad + size, pad + size), 46, fill=(22, 18, 34, 235), outline=(255, 255, 255, 46), width=2)
    out.alpha_composite(tile)
    hl = Image.new("L", out.size, 0)                       # glassy highlight on the top edge
    ImageDraw.Draw(hl).rounded_rectangle((pad + 6, pad + 6, pad + size - 6, pad + size * 0.45), 40, fill=26)
    hi = Image.new("RGBA", out.size, (255, 255, 255, 0))
    hi.putalpha(hl.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(hi)
    ic = icon_img.resize((int(size * 0.46), int(size * 0.46)), Image.LANCZOS)
    out.alpha_composite(ic, (pad + (size - ic.width) // 2, pad + (size - ic.height) // 2))
    if label:
        f = font("sub", 30)
        xs, lw = letter_layout(label, "sub", 30)
        for x, ch in zip(xs, label):
            im, lp, la = letter_img(ch, "sub", 30, (255, 255, 255), False)
            out.alpha_composite(im, (int(S / 2 - lw / 2 + x - lp), pad + size + 34 - lp))
    return out


def framed(img, max_w, max_h, tilt=0.0):
    return B.framed(img, max_w, max_h, tilt=tilt)
