"""Text for the AB-style thank-you edit: tight-tracked bold white words with a soft drop shadow, rendered once per
word and cached, plus the grey-to-white rise-in every caption and card word uses."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
SEMI = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
_fonts, _cache = {}, {}


def font(size, path=BOLD):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def width(text, size, track=-0.02, path=BOLD):
    f = font(size, path)
    return f.getlength(text) + track * size * max(len(text) - 1, 0)


def word_img(text, size, track=-0.02, path=BOLD, rgb=(251, 255, 252), shadow=True):
    """RGBA image of one word; the baseline sits `pad + ascent` px from the top. Returns (img, pad, ascent)."""
    k = (text, size, track, path, rgb, shadow)
    if k in _cache:
        return _cache[k]
    f = font(size, path)
    asc, desc = f.getmetrics()
    pad = int(size * 0.25)
    w = int(width(text, size, track, path)) + 2 * pad
    h = asc + desc + 2 * pad
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i, ch in enumerate(text):                       # per-letter placement keeps kerning and adds tracking
        x = pad + f.getlength(text[:i + 1]) - f.getlength(ch) + track * size * i   # kerning with the previous letter
        d.text((x, pad), ch, font=f, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:                                          # soft dark drop shadow, down-right
        s = mask.filter(ImageFilter.GaussianBlur(size * 0.05))
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh.putalpha(s.point(lambda v: int(v * 0.6)))
        out.alpha_composite(sh, (int(size * 0.035), int(size * 0.05)))
    fill = Image.new("RGBA", (w, h), rgb + (255,))
    fill.putalpha(mask)
    out.alpha_composite(fill)
    _cache[k] = (out, pad, asc)
    return _cache[k]


def layout_line(words, size, track=-0.02, path=BOLD, gap=0.24):
    """x offsets (from the line's left edge) of each word and the line width."""
    xs, x, sp = [], 0.0, size * gap
    for w in words:
        xs.append(x)
        x += width(w, size, track, path) + sp
    return xs, x - sp


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def reveal(t, tw, dur=0.12, rise=10, blur=2.5):
    """AB word entrance: appears ~45 % grey, a little low and soft, and rises into place as it turns white.
    Returns (opacity, dy, blur) or None before the word appears."""
    if t < tw:
        return None
    p = ease((t - tw) / dur)
    return 0.45 + 0.55 * p, rise * (1 - p), blur * (1 - p)


_blur_cache = {}


def draw_word(frame, text, size, x, base_y, t, tw, path=BOLD, dur=0.12, rise=10, alpha=1.0, rgb=(251, 255, 252)):
    """Draw one word with its entrance at (x = left edge, base_y = baseline) on a float32 RGB frame."""
    r = reveal(t, tw, dur, rise)
    if r is None:
        return
    op, dy, bl = r
    img, pad, asc = word_img(text, size, path=path, rgb=rgb)
    bq = round(bl * 2) / 2
    if bq > 0:
        k = (text, size, path, rgb, bq)
        if k not in _blur_cache:
            if len(_blur_cache) > 400:
                _blur_cache.clear()
            _blur_cache[k] = img.filter(ImageFilter.GaussianBlur(bq))
        img = _blur_cache[k]
    blend(frame, np.asarray(img), int(round(x - pad)), int(round(base_y - asc - pad + dy)), op * alpha)


def blend(dst, src, x, y, opacity=1.0):
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1 or opacity <= 0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = s[..., 3:4] / 255.0 * opacity
    d = dst[y0:y1, x0:x1]
    d *= 1 - a
    d += s[..., :3] * a
