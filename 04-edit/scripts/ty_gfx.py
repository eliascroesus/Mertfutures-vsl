"""Still graphics for the AB-style thank-you edit: card gradients, white line icons, dashed icon circles, the mock
application form and confirm-your-call email, the 'online guru' thumbnails and the results tiles.

    python ty_gfx.py        # (re)builds everything into gfx/ty/
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/home/user/work/scripts")
import ty_text as T

OUT = "/home/user/work/gfx/ty"
W, H = 1920, 1080
GREEN = [(0.0, (31, 146, 51)), (0.25, (23, 112, 38)), (0.5, (16, 74, 24)), (0.75, (7, 39, 13)), (1.0, (1, 3, 0))]
RED = [(0.0, (218, 0, 50)), (0.25, (165, 0, 37)), (0.5, (111, 0, 24)), (0.75, (55, 0, 13)), (1.0, (3, 1, 1))]


def gradient(stops):
    """Vertical linear gradient, flat across the width (AB's card background)."""
    y = np.linspace(0, 1, H)
    col = np.zeros((H, 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(y, [s for s, _ in stops], [v[c] for _, v in stops])
    return np.repeat(col[:, None, :], W, axis=1)


# ------------------------------------------------------------------ line icons (white, round caps)
def icon(name, size=150, stroke=0.055):
    S = 4                                              # supersample
    n = size * S
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    lw = max(2, int(n * stroke))

    def P(x, y):
        return (x * n, y * n)

    def line(pts, closed=False):
        pts = [P(*p) for p in pts]
        if closed:
            pts = pts + [pts[0]]
        d.line(pts, fill=255, width=lw, joint="curve")
        for p in (pts[0], pts[-1]):
            d.ellipse((p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2), fill=255)

    def arc(box, a0, a1):
        d.arc([v * n for v in box], a0, a1, fill=255, width=lw)

    if name == "hourglass":
        line([(0.28, 0.12), (0.72, 0.12)]); line([(0.28, 0.88), (0.72, 0.88)])
        line([(0.33, 0.12), (0.33, 0.24), (0.5, 0.5), (0.33, 0.76), (0.33, 0.88)])
        line([(0.67, 0.12), (0.67, 0.24), (0.5, 0.5), (0.67, 0.76), (0.67, 0.88)])
        d.polygon([P(0.4, 0.83), P(0.6, 0.83), P(0.5, 0.68)], fill=255)
    elif name == "pin":
        arc((0.27, 0.08, 0.73, 0.54), 150, 390)
        line([(0.29, 0.39), (0.5, 0.72), (0.71, 0.39)])
        d.ellipse([v * n for v in (0.42, 0.23, 0.58, 0.39)], outline=255, width=lw)
        d.ellipse([v * n for v in (0.18, 0.74, 0.82, 0.94)], outline=255, width=lw)
    elif name == "diamond":
        line([(0.2, 0.36), (0.33, 0.18), (0.67, 0.18), (0.8, 0.36), (0.5, 0.84)], closed=True)
        line([(0.2, 0.36), (0.8, 0.36)])
        line([(0.4, 0.18), (0.36, 0.36), (0.5, 0.84), (0.64, 0.36), (0.6, 0.18)])
    elif name == "mail":
        line([(0.12, 0.24), (0.88, 0.24), (0.88, 0.76), (0.12, 0.76)], closed=True)
        line([(0.12, 0.26), (0.5, 0.56), (0.88, 0.26)])
    elif name == "calendar":
        line([(0.14, 0.2), (0.86, 0.2), (0.86, 0.86), (0.14, 0.86)], closed=True)
        line([(0.14, 0.38), (0.86, 0.38)])
        line([(0.32, 0.1), (0.32, 0.28)]); line([(0.68, 0.1), (0.68, 0.28)])
        for cx, cy in [(0.32, 0.52), (0.5, 0.52), (0.68, 0.52), (0.32, 0.7), (0.5, 0.7)]:
            d.ellipse([(cx - 0.035) * n, (cy - 0.035) * n, (cx + 0.035) * n, (cy + 0.035) * n], fill=255)
        line([(0.6, 0.66), (0.66, 0.73), (0.77, 0.6)])
    elif name == "shield":
        line([(0.5, 0.08), (0.84, 0.2), (0.82, 0.5), (0.5, 0.92), (0.18, 0.5), (0.16, 0.2)], closed=True)
        line([(0.35, 0.5), (0.46, 0.62), (0.66, 0.38)])
    elif name == "phone":
        line([(0.3, 0.08), (0.7, 0.08), (0.7, 0.92), (0.3, 0.92)], closed=True)
        line([(0.44, 0.82), (0.56, 0.82)])
        arc((0.4, 0.3, 0.6, 0.5), 300, 60); arc((0.46, 0.22, 0.74, 0.58), 300, 60)
        d.ellipse([v * n for v in (0.41, 0.36, 0.49, 0.44)], fill=255)
    elif name == "note":                                  # music note (short-form apps)
        d.ellipse([v * n for v in (0.18, 0.62, 0.42, 0.84)], outline=255, width=lw)
        line([(0.42, 0.73), (0.42, 0.14), (0.78, 0.26)])
    elif name == "camera":
        line([(0.12, 0.3), (0.34, 0.3), (0.4, 0.2), (0.6, 0.2), (0.66, 0.3), (0.88, 0.3), (0.88, 0.8), (0.12, 0.8)], closed=True)
        d.ellipse([v * n for v in (0.36, 0.4, 0.64, 0.68)], outline=255, width=lw)
    elif name == "play":
        line([(0.12, 0.22), (0.88, 0.22), (0.88, 0.78), (0.12, 0.78)], closed=True)
        d.polygon([P(0.43, 0.37), P(0.43, 0.63), P(0.63, 0.5)], fill=255)
    elif name == "box":
        line([(0.5, 0.12), (0.86, 0.3), (0.86, 0.72), (0.5, 0.9), (0.14, 0.72), (0.14, 0.3)], closed=True)
        line([(0.14, 0.3), (0.5, 0.48), (0.86, 0.3)]); line([(0.5, 0.48), (0.5, 0.9)])
    elif name == "bag":
        line([(0.18, 0.34), (0.82, 0.34), (0.86, 0.88), (0.14, 0.88)], closed=True)
        arc((0.34, 0.12, 0.66, 0.52), 180, 360)
    elif name == "chat":                                  # speech bubble with a question mark
        line([(0.12, 0.18), (0.88, 0.18), (0.88, 0.7), (0.42, 0.7), (0.24, 0.86), (0.26, 0.7), (0.12, 0.7)], closed=True)
        arc((0.4, 0.27, 0.6, 0.47), 200, 400)
        line([(0.56, 0.44), (0.5, 0.5), (0.5, 0.54)])
        d.ellipse([v * n for v in (0.475, 0.59, 0.525, 0.64)], fill=255)
    elif name == "user":
        d.ellipse([v * n for v in (0.34, 0.12, 0.66, 0.44)], outline=255, width=lw)
        arc((0.16, 0.54, 0.84, 1.22), 180, 360)
    im = im.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    out.putalpha(im)
    return out


def dashed_circle(d_px, label, icon_name):
    """AB's icon circle: dashed white ring, line icon, label under it."""
    S = 3
    n = d_px * S
    im = Image.new("L", (n, n), 0)
    dr = ImageDraw.Draw(im)
    r, lw = n / 2 - 6 * S, int(5.5 * S)
    dashes = 30
    for k in range(dashes):
        a0 = k * 360 / dashes
        dr.arc((n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r), a0, a0 + 360 / dashes * 0.55, fill=255, width=lw)
    im = im.resize((d_px, d_px), Image.LANCZOS)
    out = Image.new("RGBA", (d_px, d_px), (255, 255, 255, 0))
    out.putalpha(im)
    ic = icon(icon_name, int(d_px * 0.3))
    out.alpha_composite(ic, ((d_px - ic.width) // 2, int(d_px * 0.2)))
    size = int(d_px * 0.13)
    img, pad, asc = T.word_img(label, size)
    out.alpha_composite(img, (int((d_px - img.width) / 2), int(d_px * 0.55) - pad))
    return out


def soft_shadow(card, radius, blur=30, alpha=110, dy=16, pad=80):
    out = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + dy, pad + card.width, pad + card.height + dy), radius, fill=alpha)
    out.putalpha(sh.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(card, (pad, pad))
    return out


def rounded(im, radius):
    im = im.convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius, fill=255)
    im.putalpha(m)
    return im


# ------------------------------------------------------------------ mock application form + email
def application_card(filled=0.0, blur=2.6, raw=False):
    """White rounded card with the 1-on-1 Mentorship application, softly blurred like AB's screen recording.
    `filled` (0..1) types a name into the first field."""
    w, h = 1300, 700
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    title, s = "1-on-1 Mentorship Application", 64
    tw = T.width(title, s, path=T.SEMI)
    timg, pad, asc = T.word_img(title, s, path=T.SEMI, rgb=(70, 70, 74), shadow=False)
    im.paste(timg, (int((w - tw) / 2) - pad, 46 - pad), timg)
    y = 190
    for k, lab in enumerate(["Full name", "Email", "Phone number"]):
        limg, lp, la = T.word_img(lab, 26, path=T.SEMI, rgb=(150, 150, 156), shadow=False)
        im.paste(limg, (70 - lp, y - lp), limg)
        d.rounded_rectangle((64, y + 40, w - 64, y + 100), 12, outline=(222, 222, 228), width=3)
        if k == 0 and filled > 0:
            d.rounded_rectangle((84, y + 54, 84 + int(330 * filled), y + 86), 6, fill=(40, 40, 44))
        y += 130
    d.rounded_rectangle((64, y + 20, w - 64, y + 100), 16, fill=(245, 205, 78))
    bimg, bp, ba = T.word_img("Submit Application", 34, path=T.SEMI, rgb=(60, 50, 20), shadow=False)
    im.paste(bimg, (int((w - T.width("Submit Application", 34, path=T.SEMI)) / 2) - bp, y + 40 - bp), bimg)
    im = im.filter(ImageFilter.GaussianBlur(blur)) if blur else im
    return im if raw else soft_shadow(rounded(im, 34), 34)


def email_card(blur=1.2, raw=False):
    """Inbox mock: 'Confirm your 1-on-1 call' email with a big confirm button."""
    w, h = 1240, 640
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((60, 52, 150, 142), fill=(31, 146, 51))
    a, ap, aa = T.word_img("R", 54, rgb=(255, 255, 255), shadow=False)
    im.paste(a, (105 - int(T.width("R", 54)) // 2 - ap, 66 - ap), a)
    n, npd, na = T.word_img("Ricky's Team", 38, path=T.SEMI, rgb=(40, 40, 44), shadow=False)
    im.paste(n, (180 - npd, 58 - npd), n)
    m, mp, ma = T.word_img("to me", 28, path=T.SEMI, rgb=(150, 150, 156), shadow=False)
    im.paste(m, (180 - mp, 106 - mp), m)
    s, sp, sa = T.word_img("Confirm your 1-on-1 call", 60, rgb=(30, 30, 34), shadow=False)
    im.paste(s, (60 - sp, 196 - sp), s)
    for k, ww in enumerate([0.86, 0.78, 0.62]):
        d.rounded_rectangle((60, 300 + k * 46, 60 + int((w - 120) * ww), 322 + k * 46), 11, fill=(232, 232, 236))
    bx0, by0, bx1, by1 = 60, 470, 560, 568
    d.rounded_rectangle((bx0, by0, bx1, by1), 18, fill=(31, 146, 51))
    b, bp, ba = T.word_img("Confirm my call", 40, rgb=(255, 255, 255), shadow=False)
    im.paste(b, (int((bx0 + bx1 - T.width("Confirm my call", 40)) / 2) - bp, by0 + 26 - bp), b)
    im = im.filter(ImageFilter.GaussianBlur(blur)) if blur else im
    return im if raw else soft_shadow(rounded(im, 34), 34)


# ------------------------------------------------------------------ "online guru" thumbnails (no real people)
GURU = [
    ("$30K/MONTH", "DROPSHIPPING", (255, 196, 0), (20, 20, 24), "up"),
    ("QUIT YOUR", "9-5 TODAY", (255, 60, 60), (250, 250, 250), "x"),
    ("$0 → $100K", "IN 30 DAYS", (40, 220, 120), (12, 18, 30), "up"),
    ("1 PRODUCT", "= $1,000,000", (255, 255, 255), (230, 40, 40), "box"),
    ("PASSIVE", "INCOME SECRET", (255, 230, 60), (60, 20, 120), "up"),
    ("AI STORE", "IN 10 MINUTES", (90, 200, 255), (8, 10, 22), "box"),
    ("WINNING", "PRODUCT FOUND", (255, 120, 0), (250, 250, 250), "up"),
    ("MY $997", "COURSE (90% OFF)", (255, 255, 255), (20, 120, 60), "x"),
    ("EASY", "$1,000/DAY", (40, 230, 90), (20, 20, 24), "up"),
    ("DON'T START", "WITHOUT THIS", (255, 220, 0), (200, 20, 30), "x"),
    ("SECRET", "STRATEGY", (255, 255, 255), (12, 60, 160), "up"),
    ("$9,412", "IN ONE WEEK", (60, 240, 120), (14, 14, 18), "box"),
]


def guru_thumb(i, w=1200, h=675, raw=False):
    a, b, fg, bg, deco = GURU[i]
    rng = np.random.default_rng(i)
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    g = Image.new("L", (w, h), 0)                       # bright radial glow behind the deco
    ImageDraw.Draw(g).ellipse((w * 0.5, -h * 0.2, w * 1.3, h * 1.1), fill=110)
    glow = Image.new("RGB", (w, h), tuple(min(255, c + 90) for c in bg))
    im.paste(glow, (0, 0), g.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(im)
    if deco == "up":                                    # rising chart + arrow
        pts, x, y = [], w * 0.55, h * 0.8
        for k in range(9):
            pts.append((x, y))
            x += w * 0.045
            y -= h * (0.05 + 0.06 * rng.random()) * (1 if k % 3 else -0.4)
        d.line(pts, fill=(40, 230, 90), width=14, joint="curve")
        x1, y1 = pts[-1]
        d.polygon([(x1 + 34, y1 - 34), (x1 - 30, y1 - 22), (x1 + 20, y1 + 30)], fill=(40, 230, 90))
    elif deco == "box":                                 # product box
        d.rounded_rectangle((w * 0.62, h * 0.3, w * 0.92, h * 0.85), 18, fill=(196, 150, 96))
        d.line([(w * 0.62, h * 0.45), (w * 0.92, h * 0.45)], fill=(150, 108, 64), width=10)
        d.rectangle((w * 0.74, h * 0.3, w * 0.8, h * 0.85), fill=(222, 190, 140))
    else:                                               # red X
        d.line([(w * 0.66, h * 0.3), (w * 0.9, h * 0.78)], fill=(255, 40, 40), width=34)
        d.line([(w * 0.9, h * 0.3), (w * 0.66, h * 0.78)], fill=(255, 40, 40), width=34)
    for k, (txt, sz, y) in enumerate([(a, 118, 120), (b, 84, 300)]):
        f = T.font(sz, "/usr/share/fonts/opentype/inter/Inter-Black.otf")
        stroke = 10
        d.text((56, y), txt, font=f, fill=fg, stroke_width=stroke, stroke_fill=(0, 0, 0))
    d.rounded_rectangle((w - 150, h - 76, w - 22, h - 22), 10, fill=(0, 0, 0))
    f = T.font(34, T.SEMI)
    d.text((w - 136, h - 70), f"{rng.integers(8, 59)}:{rng.integers(10, 59)}", font=f, fill=(255, 255, 255))
    return im if raw else rounded(im, 28)


# ------------------------------------------------------------------ results tiles (Ricky's own Shopify proof)
RESULTS = ["shop_36k", "shop_11k", "shop_today_2k", "shop_payout", "shop_laptop_night", "labels_strip", "labels_stack"]


def result_tile(name, w=420):
    import cards2 as C2
    im, _ = C2.source(name)
    im = im.convert("RGB")
    h = int(im.height * w / im.width)
    h = min(h, int(w * 1.45))
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS).crop((0, 0, w, h))
    return soft_shadow(rounded(im, 18), 18, blur=18, alpha=140, dy=10, pad=40)


def main():
    os.makedirs(OUT, exist_ok=True)
    for nm, st in [("green", GREEN), ("red", RED)]:
        np.save(f"{OUT}/bg_{nm}.npy", gradient(st).astype(np.float32))
    for nm, lab, ic in [("time", "Time", "hourglass"), ("location", "Location", "pin"), ("freedom", "Freedom", "diamond")]:
        dashed_circle(392, lab, ic).save(f"{OUT}/circle_{nm}.png")
    for ic in ["mail", "calendar", "shield", "phone", "hourglass", "pin", "diamond", "note", "camera", "play", "box", "bag", "user", "chat"]:
        icon(ic, 170).save(f"{OUT}/icon_{ic}.png")
    for k in range(6):
        application_card(k / 5).save(f"{OUT}/app_{k}.png")
    email_card().save(f"{OUT}/email.png")
    for i in range(len(GURU)):
        guru_thumb(i).save(f"{OUT}/guru_{i:02d}.png")
    for nm in RESULTS:
        result_tile(nm).save(f"{OUT}/res_{nm}.png")
    print("ok", OUT)


if __name__ == "__main__":
    main()
