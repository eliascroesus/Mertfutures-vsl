"""Compositor for Mert's VSL.

Iman Gadzhi's look: a near-black plate with a lime glow that drifts slowly, wide Unbounded caps that blur in letter by
letter as he says each word, a lime handwritten line under headlines, one accent colour (lime) plus red for losses.
AB Nasdaq's structure: word captions at the bottom, side text in the empty wall beside him, a split screen for the offer,
slow push-ins cropped from the 4K original.

Per frame: either a full-screen graphic (text card, trade chart, order book, process steps, call to action) or Mert
(zoom curve, split-screen shift) with overlays (side text, headline); then the soft lime light sweep on card changes,
then the captions / callouts.

    python mert_render.py plan.json base.mp4 out.mp4 [f0 f1]
"""
import json, math, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/home/user/work/scripts")
import ty_text as T
import ty_iman as I

LIME = (198, 246, 58)
RED = (255, 58, 58)
I.PURPLE = LIME
I.RED = RED
I.COLORS.update({"lime": LIME, "red": RED, "dim": (196, 198, 190), "white": (255, 255, 255)})
I.FONTS.update({"big": "/root/.local/share/fonts/Poppins-800.ttf", "sub": "/root/.local/share/fonts/Poppins-600.ttf", "mark": "/root/.local/share/fonts/Poppins-700.ttf", "hand": "/root/.local/share/fonts/Poppins-500i.ttf", "item": "/root/.local/share/fonts/Poppins-600.ttf"})
I.TRACK.update({"big": -0.015, "hand": 0.0, "item": 0.0, "sub": 0.16})
I.draw_mark = lambda *a, **k: None                       # no brand mark: Mert has no logo yet
import ty_render as R
import ty_render2 as R2

W, H, FPS = 1920, 1080, 30
BW, BH = 2560, 1440                                      # the A-roll is rendered at 1440p so push-ins stay sharp
SEMI = "/root/.local/share/fonts/Poppins-600.ttf"
BOLD = "/root/.local/share/fonts/Poppins-700.ttf"
CAPF = "/root/.local/share/fonts/Poppins-700.ttf"
clamp, ease_io, ease_out = R.clamp, R.ease_io, R.ease_out
CX, CY = 980, 560

# readability: a soft dark fade along the bottom of the talking-head shots (like AB's) for the captions
BOTTOM = (np.clip((np.arange(H) - 640) / 440.0, 0, 1) ** 1.4 * 0.58)[:, None, None].astype(np.float32)
LEFT = (np.clip(1 - np.arange(W) / 980.0, 0, 1) ** 1.7 * 0.55)[None, :, None].astype(np.float32)


def backing(cx, cy, rx, ry, a):
    """A soft dark ellipse behind text that sits over his white t-shirt."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    return (a * np.exp(-((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2))[..., None].astype(np.float32)


CALL_BACK = backing(W / 2, 985, 620, 95, 0.5)


CUR = {"base": None, "blur": None}
_plate_at = I.plate_at


def frosted():
    """His room, heavily blurred and darkened: the glass every card sits on (computed once per frame)."""
    if CUR["blur"] is None:
        b = CUR["base"]
        sm = cv2.resize(b, (160, 90), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), 3.2)
        CUR["blur"] = cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    return CUR["blur"]


def plate_at(pl, p):
    out = _plate_at(pl, p)
    if CUR["base"] is None:
        return out
    return out * 0.9 + frosted() * 0.3


I.plate_at = plate_at
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.38 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.66)) ** 2, 0, 1) ** 1.3)[..., None]
_g = np.random.default_rng(11)
GRAIN = [cv2.GaussianBlur(_g.normal(0, 5.5, (H, W)).astype(np.float32), (0, 0), 0.7)[..., None] for _ in range(6)]
del yy, xx


def scale_about(frame, k, cx=W / 2, cy=H / 2):
    M = cv2.getRotationMatrix2D((cx, cy), 0, k)
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def zoom_blur(frame, amt, n=6):
    acc = frame.copy()
    for k in range(1, n):
        acc += scale_about(frame, 1 + amt * k / (n - 1))
    return acc / n


class Sweeps(R.Leaks):
    """The light sweep on card changes, in the brand's lime-to-white, kept soft."""
    PAL = np.array([[0.2, 0.26, 0.04], [0.5, 0.68, 0.1], [0.74, 0.92, 0.26], [0.9, 0.99, 0.62], [1.0, 1.0, 0.94]], np.float32)


BASE_Z, ZMAX = 1.0, 1.5          # he sits far from the camera: every talking-head shot is framed closer than the raw


def zoomed(base, z, shift=0.0, pan=0.0):
    """1920x1080 view of the 2560x1440 A-roll at zoom z around his face; `shift` moves him left (split screen),
    `pan` moves him right (room for text on the wall)."""
    s = BW / W
    cw, ch = BW / z, BH / z
    x0 = min(max(CX * s - pan * s / z - cw / 2, 0), BW - cw)
    y0 = min(max(CY * s - ch / 2, 0), BH - ch)
    im = Image.fromarray(base).resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    out = np.asarray(im).astype(np.float32)
    if shift > 0.5:
        k = int(round(shift))
        out = np.concatenate([out[:, k:], np.zeros((H, k, 3), np.float32)], 1)
    return out


# ------------------------------------------------------------------ left-aligned text blocks
def left_layout(rows, x, cy=None, top=None, maxw=600, gap=0.34):
    out, heights = [], []
    for r in rows:
        vis = [(w, t) for w, t in r["words"] if w != "_"]
        text = " ".join(w for w, _ in vis)
        size = r["size"]
        _, lw = I.letter_layout(text, r["style"], size)
        if lw > maxw:
            size = int(size * maxw / lw)
        out.append([r, vis, text, size])
        heights.append(size * (0.95 if r["style"] == "big" else 1.0))
    gaps = []
    for (a, _, _, sa), (b, _, _, sb) in zip(out, out[1:]):
        if a["style"] == "item" and b["style"] == "item":
            gaps.append(0.62 * max(sa, sb))
        elif b["style"] == "item":
            gaps.append(0.9 * sb)
        else:
            gaps.append(gap * (sa + sb) / 2 + (0.35 * max(sa, sb) if a["style"] == b["style"] == "sub" else 0))
    total = sum(heights) + sum(gaps)
    y = (cy - total / 2) if top is None else top
    runs = []
    for i, ((r, vis, text, size), h) in enumerate(zip(out, heights)):
        base = y + h * 0.82
        xs, lw = I.letter_layout(text, r["style"], size)
        k = 0
        for w, t in vis:
            runs.append({"text": w, "style": r["style"], "size": size, "x": x + xs[k], "base": base, "t": t,
                         "rgb": I.COLORS[r.get("color", "white")], "glow": r.get("color", "white") != "white"})
            k += len(w) + 1
        if r["style"] == "item" and vis:
            runs.append({"bullet": True, "x": x - size * 0.75, "y": base - size * 0.36, "t": vis[0][1], "r": size * 0.14})
        if r.get("ul") and vis:
            runs.append({"ul": True, "x0": x, "x1": x + lw, "y": base + size * 0.17, "h": max(5, size * 0.055),
                         "t": vis[-1][1] + 0.2, "rgb": I.COLORS["red"] if r.get("color") == "red" else LIME})
        if r.get("strike") and vis:
            runs.append({"strike": True, "x0": x - size * 0.1, "x1": x + lw + size * 0.1,
                         "y": base - size * 0.36, "h": max(4, size * 0.1), "t": vis[-1][1] + 0.3})
        y += h + (gaps[i] if i < len(gaps) else 0)
    return runs


_dots = {}


def dot_img(r, rgb, glow=2.6):
    k = (round(r, 1), rgb, glow)
    if k not in _dots:
        S = int(r * 2 * glow + 8)
        m = Image.new("L", (S * 2, S * 2), 0)
        ImageDraw.Draw(m).ellipse((S - r * 2, S - r * 2, S + r * 2, S + r * 2), fill=255)
        m = m.resize((S, S), Image.LANCZOS)
        g = m.filter(ImageFilter.GaussianBlur(r * 0.9))
        out = Image.new("RGBA", (S, S), rgb + (0,))
        out.putalpha(g.point(lambda v: int(v * 0.7)))
        core = Image.new("RGBA", (S, S), rgb + (255,))
        core.putalpha(m)
        out.alpha_composite(core)
        _dots[k] = np.asarray(out)
    return _dots[k]


def draw_ul(frame, r, t, alpha=1.0):
    """Iman's underline: a lime line that draws in from the left under the key words, with a soft glow."""
    p = (t - r["t"]) / 0.45
    if p <= 0:
        return
    e = ease_io(min(p, 1))
    m = np.zeros((H, W), np.float32)
    y0, y1 = int(r["y"] - r["h"] / 2), int(r["y"] + r["h"] / 2) + 1
    x1 = r["x0"] + (r["x1"] - r["x0"]) * e
    if x1 - r["x0"] < 2 or y1 >= H:
        return
    m[y0:y1, int(r["x0"]):int(x1)] = 1.0
    glow_line(frame, m, r["rgb"], alpha, 0.8)


def draw_runs(frame, runs, t, alpha=1.0):
    plain = [r for r in runs if not r.get("bullet") and not r.get("ul")]
    I.draw_runs(frame, plain, t, alpha)
    for r in runs:
        if r.get("ul"):
            draw_ul(frame, r, t, alpha)
    for r in runs:
        if r.get("bullet") and t >= r["t"]:
            e = ease_out((t - r["t"]) / 0.3)
            d = dot_img(r["r"], LIME)
            T.blend(frame, d, int(r["x"] - d.shape[1] / 2), int(r["y"] - d.shape[0] / 2), e * alpha)


def label(frame, text, x, y, t, t0, size=24, rgb=(235, 236, 230), anchor="l", alpha=1.0, path=SEMI, track=0.06):
    """Small spaced caps (chart/order-book labels), fading up into place."""
    if t < t0:
        return
    e = ease_out((t - t0) / 0.35)
    img, pad, asc = T.word_img(text, size, track, path, rgb, shadow=False)
    w = img.width - 2 * pad
    xx = x if anchor == "l" else x - w if anchor == "r" else x - w / 2
    T.blend(frame, np.asarray(img), int(xx - pad), int(y - asc - pad + 8 * (1 - e)), e * alpha)


def line_mask(pts, p, width, ss=2):
    """Anti-aliased polyline drawn up to fraction p of its length. Returns float32 HxW 0..1 and the pen tip."""
    P = [(x * ss, y * ss) for x, y in pts]
    segs = [math.dist(a, b) for a, b in zip(P, P[1:])]
    left = p * sum(segs)
    draw, tip = [P[0]], P[0]
    for (a, b), L in zip(zip(P, P[1:]), segs):
        if left <= 0:
            break
        f = min(1, left / L)
        tip = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        draw.append(tip)
        left -= L
    xs, ys = [q[0] for q in draw], [q[1] for q in draw]
    pad = width * ss * 2
    bx0, by0 = int(max(min(xs) - pad, 0)), int(max(min(ys) - pad, 0))
    bx1, by1 = int(min(max(xs) + pad, W * ss)), int(min(max(ys) + pad, H * ss))
    m = Image.new("L", (max(bx1 - bx0, 1), max(by1 - by0, 1)), 0)
    if len(draw) > 1:
        ImageDraw.Draw(m).line([(x - bx0, y - by0) for x, y in draw], fill=255, width=int(width * ss), joint="curve")
    m = m.resize((max(1, (bx1 - bx0) // ss), max(1, (by1 - by0) // ss)), Image.LANCZOS)
    full = np.zeros((H, W), np.float32)
    a = np.asarray(m, np.float32) / 255.0
    X0, Y0 = bx0 // ss, by0 // ss
    full[Y0:Y0 + a.shape[0], X0:X0 + a.shape[1]] = a[:H - Y0, :W - X0]
    return full, (tip[0] / ss, tip[1] / ss)


def glow_line(frame, mask, rgb, strength=1.0, glow=0.9):
    small = Image.fromarray((mask * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    g = np.asarray(small.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), np.float32)[..., None] / 255.0
    col = np.array(rgb, np.float32)
    frame += g * glow * col * 0.9 * strength
    m = mask[..., None] * strength
    frame *= 1 - m
    frame += m * col


def dashed(frame, x0, x1, y, rgb, t, t0, alpha=0.55, dash=16, gapl=12, h=2):
    if t < t0:
        return
    e = ease_io((t - t0) / 0.6)
    xe = x0 + (x1 - x0) * e
    col = np.array(rgb, np.float32)
    x = x0
    while x < xe:
        xa, xb = int(x), int(min(x + dash, xe))
        sl = frame[int(y - h / 2):int(y + h / 2) + 1, xa:xb]
        sl *= 1 - alpha
        sl += col * alpha
        x += dash + gapl


# ------------------------------------------------------------------ full-screen graphics
class Plate:
    cache = {}

    def __init__(self, s):
        self.s, self.t0, self.t1 = s, s["t0"], s["t1"]
        pc = s.get("plate", "lime")
        if pc not in Plate.cache:
            Plate.cache[pc] = I.plate(RED if pc == "red" else LIME)
        self.plate = Plate.cache[pc]

    def bg(self, frame, t):
        frame[:] = I.plate_at(self.plate, (t - self.t0) / max(self.t1 - self.t0, 0.5))


class Chart(Plate):
    """A trade: entry, it goes against you, you close it, then price runs to exactly where you expected."""
    X0, X1, Y0, Y1 = 250, 1560, 190, 800
    HIST = [(0, .60), (.03, .55), (.06, .58), (.09, .5), (.12, .54), (.15, .47), (.18, .52), (.21, .45), (.24, .49),
            (.27, .43), (.3, .47)]
    AGAINST = [(.3, .47), (.33, .52), (.36, .49), (.39, .59), (.42, .55), (.46, .7)]
    RUN = [(.46, .7), (.49, .62), (.52, .66), (.57, .49), (.6, .54), (.66, .36), (.69, .41), (.75, .25), (.79, .29),
           (.85, .15), (.92, .12), (1.0, .07)]
    TARGET, STOP = .2, .7

    def px(self, p):
        return (self.X0 + p[0] * (self.X1 - self.X0), self.Y0 + p[1] * (self.Y1 - self.Y0))

    def draw(self, frame, face, t, zprev):
        s = self.s
        self.bg(frame, t)
        r = t - self.t0
        a_grid = clamp(r / 0.5)
        for k in range(6):                                       # faint price grid with levels on the right
            y = int(self.Y0 + k * (self.Y1 - self.Y0) / 5)
            frame[y:y + 1, self.X0:self.X1] = frame[y:y + 1, self.X0:self.X1] * (1 - 0.07 * a_grid) + 255 * 0.07 * a_grid
            label(frame, f"{5891.50 - k * 7.25:,.2f}", self.X1 + 30, y + 8, t, self.t0 + 0.1 + 0.04 * k, 20, (150, 152, 146))
        label(frame, "ES  ·  S&P 500 FUTURES  ·  1 MIN", self.X0, self.Y0 - 46, t, self.t0 + 0.1, 22, (170, 172, 165))
        m, tip = line_mask([self.px(p) for p in self.HIST], ease_io((r - 0.05) / 0.85), 4.5)
        glow_line(frame, m, (235, 236, 232), 1.0, 0.35)
        te = s["t_entry"]
        ex, ey = self.px(self.HIST[-1])
        ty_, sy = self.Y0 + self.TARGET * (self.Y1 - self.Y0), self.Y0 + self.STOP * (self.Y1 - self.Y0)
        dashed(frame, ex, self.X1, ty_, LIME, t, te + 0.1)
        dashed(frame, ex, self.X1, sy, RED, t, te + 0.25)
        label(frame, "YOUR TARGET", self.X1 - 4, ty_ - 14, t, te + 0.4, 22, LIME, "r")
        label(frame, "STOP", self.X1 - 4, sy - 14, t, te + 0.55, 22, RED, "r")
        if t >= s["t_against"]:
            m, tip = line_mask([self.px(p) for p in self.AGAINST], ease_io((t - s["t_against"]) / 0.95), 4.5)
            glow_line(frame, m, RED, 1.0, 0.8)
        if t >= te:                                             # entry dot with a ring
            e = ease_out((t - te) / 0.3)
            d = dot_img(9, LIME)
            T.blend(frame, d, int(ex - d.shape[1] / 2), int(ey - d.shape[0] / 2), e)
            rr = (t - te) / 0.8
            if rr < 1:
                ring(frame, ex, ey, 12 + 50 * ease_out(rr), LIME, (1 - rr) * 0.8)
            label(frame, "ENTRY", ex, ey + 46, t, te, 22, LIME, "c")
        tc = s["t_close"]
        cx, cy = self.px(self.AGAINST[-1])
        if t >= tc:                                             # the close: a red X where you got out
            e = ease_out((t - tc) / 0.25)
            cross(frame, cx, cy, 16 * (0.6 + 0.4 * e), RED, e)
            label(frame, "CLOSED", cx, cy + 50, t, tc, 22, RED, "c")
        tr = s["t_run"]
        if t >= tr:
            p = ease_io((t - tr) / max(s["t_run_end"] - tr + 0.3, 0.6))
            m, tip = line_mask([self.px(q) for q in self.RUN], p, 4.5)
            glow_line(frame, m, LIME, 1.0, 1.0)
            T.blend(frame, dot_img(6, LIME), int(tip[0] - dot_img(6, LIME).shape[1] / 2),
                    int(tip[1] - dot_img(6, LIME).shape[0] / 2), 1.0)
            if tip[1] <= ty_ + 1:                               # crossed the target
                if not hasattr(self, "hit"):
                    self.hit = t
                label(frame, "TARGET HIT", self.X1 - 4, ty_ + 36, t, self.hit, 22, LIME, "r")
                rr = (t - self.hit) / 0.8
                if rr < 1:
                    ring(frame, tip[0], tip[1], 10 + 46 * ease_out(rr), LIME, (1 - rr) * 0.9)


def ring(frame, x, y, rad, rgb, a):
    S = int(rad * 2 + 12)
    m = Image.new("L", (S * 2, S * 2), 0)
    ImageDraw.Draw(m).ellipse((12, 12, S * 2 - 12, S * 2 - 12), outline=255, width=5)
    m = m.resize((S, S), Image.LANCZOS)
    img = Image.new("RGBA", (S, S), rgb + (0,))
    img.putalpha(m)
    T.blend(frame, np.asarray(img), int(x - S / 2), int(y - S / 2), a)


def cross(frame, x, y, r, rgb, a):
    S = int(r * 2 + 30)
    m = Image.new("L", (S * 2, S * 2), 0)
    d = ImageDraw.Draw(m)
    c, k = S, r * 2
    d.line((c - k, c - k, c + k, c + k), fill=255, width=10)
    d.line((c - k, c + k, c + k, c - k), fill=255, width=10)
    m = m.resize((S, S), Image.LANCZOS)
    img = Image.new("RGBA", (S, S), rgb + (0,))
    g = m.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.6))
    img.putalpha(g)
    core = Image.new("RGBA", (S, S), rgb + (255,))
    core.putalpha(m)
    img.alpha_composite(core)
    T.blend(frame, np.asarray(img), int(x - S / 2), int(y - S / 2), a)


class Card(Plate):
    """Iman text card (wide caps blurring in word by word, optional falling red line) via the thank-you renderer."""

    def __init__(self, s):
        super().__init__(s)
        s2 = dict(s)
        s2["plate"] = "red" if s.get("plate") == "red" else "purple"
        R2.Scene.plates.setdefault("purple", I.plate(LIME))
        R2.Scene.plates.setdefault("red", I.plate(RED))
        self.sc = R2.Scene(s2)
        self.ul = []
        if s["kind"] == "iman":
            runs, k = self.sc.runs, 0
            for r in s["rows"]:
                vis = [(w, tt) for w, tt in r["words"] if w != "_"]
                mine = runs[k:k + len(vis)]
                k += len(vis) + (1 if r.get("strike") and vis else 0)
                if r.get("ul") and mine:
                    lw = I.letter_layout(" ".join(w for w, _ in vis), r["style"], mine[0]["size"])[1]
                    self.ul.append({"ul": True, "x0": mine[0]["x"], "x1": mine[0]["x"] + lw,
                                    "y": mine[0]["base"] + mine[0]["size"] * 0.17, "h": max(5, mine[0]["size"] * 0.055),
                                    "t": vis[-1][1] + 0.2, "rgb": RED if r.get("color") == "red" else LIME})

    def draw(self, frame, face, t, zprev):
        self.sc.draw(frame, face, t, zprev)
        for u in self.ul:
            draw_ul(frame, u, t)


class Dom(Plate):
    """Depth of market: a level-2 ladder that builds in, sizes ticking, then the buyers and the sellers light up."""
    N, RH, PW = 15, 38, 640

    def __init__(self, s):
        super().__init__(s)
        self.runs, _, _ = I.layout_rows(s["rows"], 175)
        rng = np.random.default_rng(7)
        self.base = rng.integers(18, 160, (self.N,)).astype(float)
        self.mid = self.N // 2
        self.wall_b, self.wall_a = self.mid + 3, self.mid - 4
        self.base[self.wall_b] = 1240
        self.base[self.wall_a] = 980
        self.panel = self.make_panel()

    def make_panel(self):
        w, h = self.PW, self.N * self.RH + 70
        pad = 80
        im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        g = Image.new("L", im.size, 0)
        ImageDraw.Draw(g).rounded_rectangle((pad, pad, pad + w, pad + h), 26, fill=150)
        gl = Image.new("RGBA", im.size, LIME + (0,))
        gl.putalpha(g.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.35)))
        im.alpha_composite(gl)
        p = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(p)
        d.rounded_rectangle((pad, pad, pad + w, pad + h), 26, fill=(14, 15, 13, 236), outline=(255, 255, 255, 34), width=2)
        im.alpha_composite(p)
        return np.asarray(im), pad

    def draw(self, frame, face, t, zprev):
        s = self.s
        self.bg(frame, t)
        r = t - self.t0
        panel, pad = self.panel
        px0, py0 = W // 2 - self.PW // 2, 300
        T.blend(frame, panel, px0 - pad, py0 - pad, ease_out(r / 0.4))
        cxm = W // 2
        label(frame, "BID", cxm - 255, py0 + 42, t, self.t0 + 0.2, 20, (150, 152, 146), "c")
        label(frame, "PRICE", cxm, py0 + 42, t, self.t0 + 0.2, 20, (150, 152, 146), "c")
        label(frame, "ASK", cxm + 255, py0 + 42, t, self.t0 + 0.2, 20, (150, 152, 146), "c")
        tick = int(t * 6)
        rng = np.random.default_rng(tick)
        jit = rng.integers(-9, 10, self.N)
        buy_on = clamp((t - s["t_buy"]) / 0.35)
        sell_on = clamp((t - s["t_sell"]) / 0.35)
        for i in range(self.N):
            y = py0 + 70 + i * self.RH
            ap = clamp((r - 0.25 - abs(i - self.mid) * 0.04) / 0.3)
            if ap <= 0:
                continue
            price = 5872.25 + (self.mid - i) * 0.25
            is_ask, is_mid = i < self.mid, i == self.mid
            size = max(1, int(self.base[i] + (0 if i in (self.wall_a, self.wall_b) else jit[i])))
            if is_mid:
                band = frame[y + 4:y + self.RH - 4, cxm - self.PW // 2 + 14:cxm + self.PW // 2 - 14]
                band *= 1 - 0.12 * ap
                band += np.array(LIME, np.float32) * 0.12 * ap
            label(frame, f"{price:,.2f}", cxm, y + 27, t, -1, 22, LIME if is_mid else (236, 236, 232), "c", ap,
                  path=BOLD if is_mid else SEMI, track=0.02)
            if is_mid:
                continue
            wall = (i == self.wall_b and buy_on > 0) or (i == self.wall_a and sell_on > 0)
            col = RED if is_ask else LIME
            frac = min(size / 1300, 1.0)
            bar_w = int(118 * frac ** 0.6)
            x_num = cxm + 226 if is_ask else cxm - 226
            bx0 = cxm + 90 if is_ask else cxm - 90 - bar_w
            bar = frame[y + 9:y + self.RH - 9, bx0:bx0 + bar_w]
            k = (0.28 + 0.5 * (buy_on if i == self.wall_b else sell_on if i == self.wall_a else 0)) * ap
            bar *= 1 - k
            bar += np.array(col, np.float32) * k
            label(frame, f"{size:,}", x_num, y + 27, t, -1, 22,
                  col if wall else (200, 202, 196), "r" if not is_ask else "l", ap, path=BOLD if wall else SEMI, track=0.02)
        for on, tt, txt, col, x, anc in ((buy_on, s["t_buy"], "BUYERS", LIME, cxm - self.PW // 2 - 70, "r"),
                                         (sell_on, s["t_sell"], "SELLERS", RED, cxm + self.PW // 2 + 70, "l")):
            if on > 0:
                _, lw = I.letter_layout(txt, "big", 64)
                xx = x - lw if anc == "r" else x
                yy = py0 + 70 + (self.wall_b if txt == "BUYERS" else self.wall_a) * self.RH + 52
                I.draw_letters(frame, txt, "big", 64, xx, yy, t, tt, col, True, stagger=0.03, dur=0.3, blur=14)
                sub = "WHO IS REALLY BUYING?" if txt == "BUYERS" else "WHO IS REALLY SELLING?"
                _, sw = I.letter_layout(sub, "sub", 22)
                I.draw_letters(frame, sub, "sub", 22, (x - sw) if anc == "r" else x, yy + 44, t, tt + 0.15,
                               (220, 222, 216), False, stagger=0.012, dur=0.25, blur=8)
        I.draw_runs(frame, self.runs, t)


class Steps(Plate):
    """His process as three steps joined by a lime line: BIAS -> LOCATION -> ORDER FLOW, then the rule."""
    XS, Y = [430, 960, 1490], 540
    NAMES = ["BIAS", "LOCATION", "ORDER FLOW"]
    SUBS = ["AI · NEWS · ECONOMIC DATA", "VOLUME PROFILE", "CONFIRMATION"]

    def __init__(self, s):
        super().__init__(s)
        self.tn = [self.t0 + 0.15, s["t_loc"], s["t_flow"]]
        self.rule = I.layout_rows([{"words": [["NO", s["t_rule"]], ["CONFIRMATION,", s["t_rule"] + 0.3]],
                                    "style": "sub", "size": 40, "color": "white"},
                                   {"words": [["NO", s["t_rule2"]], ["TRADE.", s["t_rule2"] + 0.25]],
                                    "style": "big", "size": 96, "color": "lime"}], 850)[0]
        self.head = I.layout_rows([{"words": [["MY", self.t0 + 0.05], ["PROCESS", self.t0 + 0.15]], "style": "sub",
                                    "size": 30, "color": "dim"}], 250)[0]

    def draw(self, frame, face, t, zprev):
        self.bg(frame, t)
        I.draw_runs(frame, self.head, t)
        for i in range(2):                                       # connector grows when the next step lands
            if t >= self.tn[i + 1]:
                e = ease_io((t - self.tn[i + 1]) / 0.5)
                x0, x1 = self.XS[i] + 26, self.XS[i] + 26 + (self.XS[i + 1] - self.XS[i] - 52) * e
                m = np.zeros((H, W), np.float32)
                m[self.Y - 2:self.Y + 2, int(x0):int(x1)] = 1.0
                glow_line(frame, m, LIME, 0.95, 0.9)
        for i, (x, tn) in enumerate(zip(self.XS, self.tn)):
            if t < tn:
                continue
            e = ease_out((t - tn) / 0.35)
            pulse = 0.0
            for k, tp in enumerate(self.s["t_recap"]):
                if k == i and 0 <= t - tp < 0.7:
                    pulse = math.sin(math.pi * (t - tp) / 0.7)
            d = dot_img(13 * (1 + 0.35 * pulse), LIME, 2.6 + pulse)
            T.blend(frame, d, int(x - d.shape[1] / 2), int(self.Y - d.shape[0] / 2), e)
            if t - tn < 0.9:
                ring(frame, x, self.Y, 16 + 44 * ease_out((t - tn) / 0.9), LIME, (1 - (t - tn) / 0.9) * 0.8)
            if pulse > 0:
                ring(frame, x, self.Y, 18 + 30 * pulse, LIME, pulse * 0.6)
            nm = self.NAMES[i]
            size = 60
            _, lw = I.letter_layout(nm, "big", size)
            rgb = tuple(int(255 - (255 - c) * pulse) for c in LIME) if pulse > 0 else (255, 255, 255)
            I.draw_letters(frame, nm, "big", size, x - lw / 2, self.Y - 58, t, tn, rgb, pulse > 0.2, stagger=0.03, dur=0.3)
            sb = self.SUBS[i]
            _, sw = I.letter_layout(sb, "sub", 22)
            I.draw_letters(frame, sb, "sub", 22, x - sw / 2, self.Y + 72, t, tn + 0.2, (190, 192, 186), False,
                           stagger=0.012, dur=0.25, blur=8)
        I.draw_runs(frame, self.rule, t)


class Cta(Plate):
    """Application below: the words build, then a lime arrow points down to the button."""

    def __init__(self, s):
        super().__init__(s)
        self.runs, top, self.bot = I.layout_rows(s["rows"], s.get("cy", 430))
        self.t_arrow = s["rows"][1]["words"][-1][1] + 0.15

    def draw(self, frame, face, t, zprev):
        self.bg(frame, t)
        I.draw_runs(frame, self.runs, t)
        if t >= self.t_arrow:
            e = ease_out((t - self.t_arrow) / 0.45)
            bob = 14 * math.sin((t - self.t_arrow) * 2 * math.pi / 1.3)
            y = self.bot + 120 + bob - 30 * (1 - e)
            m = Image.new("L", (W // 2, 240), 0)
            d = ImageDraw.Draw(m)
            cx, cy = W // 4, 60
            d.line((cx - 60, cy, cx, cy + 60, cx + 60, cy), fill=255, width=22, joint="curve")
            m = m.resize((W // 4, 120), Image.LANCZOS)
            full = np.zeros((H, W), np.float32)
            a = np.asarray(m, np.float32) / 255.0
            y0 = int(y - 30)
            if 0 <= y0 < H - 120:
                full[y0:y0 + 120, W // 2 - W // 8:W // 2 + W // 8] = a
                glow_line(frame, full * e, LIME, 1.0, 1.0)


# ------------------------------------------------------------------ overlays on the talking head
class Side:
    def __init__(self, s):
        self.s, self.t0, self.t1 = s, s["t0"], s["t1"]
        self.runs = left_layout(s["rows"], 120, cy=s.get("cy", 470), maxw=540)

    def alpha(self, t):
        return clamp((t - self.t0) / 0.3) * clamp((self.t1 - t) / 0.3)

    def draw(self, frame, t):
        a = self.alpha(t)
        frame *= 1 - LEFT * a
        draw_runs(frame, self.runs, t, clamp((self.t1 - t) / 0.3))


class Intro:
    """The hook: from black into a tight close-up with letterbox bars, his name huge on the wall beside him."""
    BAR = 118

    def __init__(self, s):
        self.s, self.t0, self.t1 = s, s["t0"], s["t1"]
        self.runs = left_layout(s["rows"], 110, cy=505, maxw=520, gap=0.22)

    def draw(self, frame, t):
        frame *= 1 - LEFT * 0.8
        draw_runs(frame, self.runs, t, clamp((self.t1 - t) / 0.25))
        b = int(self.BAR * ease_out(t / 0.5) * (1 - ease_io((t - (self.t1 - 0.45)) / 0.45)))
        if b > 0:
            frame[:b] = 0
            frame[H - b:] = 0


class Headline:
    def __init__(self, s):
        self.s, self.t0, self.t1 = s, s["t0"], s["t1"]
        self.runs, top, bot = I.layout_rows(s["rows"], 875, maxw=1700, gap=0.2)
        xs = [r["x"] for r in self.runs if "x" in r]
        self.back = backing((min(xs) + W - min(xs)) / 2, (top + bot) / 2, (W - 2 * min(xs)) * 0.62, (bot - top) * 1.05, 0.62)

    def draw(self, frame, t):
        a = clamp((t - self.t0) / 0.3) * clamp((self.t1 - t) / 0.3)
        frame *= 1 - BOTTOM * 0.6 * a
        frame *= 1 - self.back * a
        draw_runs(frame, self.runs, t, clamp((self.t1 - t) / 0.3))


class Split:
    """AB's split screen: Mert slides into the left half, the list builds line by line on the plate on the right."""
    SH, PX = 500, 1050

    def __init__(self, s):
        self.s, self.t0, self.t1 = s, s["t0"], s["t1"]
        self.a = left_layout(s["a"], self.PX, top=250, maxw=780)
        self.b = left_layout(s["b"], self.PX, top=250, maxw=780)
        self.plate = I.plate(LIME)
        edge = np.clip(1 - np.arange(80) / 80.0, 0, 1) ** 2 * 0.55
        self.edge = edge[None, :, None].astype(np.float32)

    def progress(self, t):
        return ease_io((t - self.t0) / 0.55) * (1 - ease_io((t - (self.t1 - 0.5)) / 0.5))

    def shift(self, t):
        return self.SH * self.progress(t)

    def draw(self, frame, t):
        e = self.progress(t)
        if e <= 0:
            return
        x0 = int(round(W - 960 * e))
        pl = I.plate_at(self.plate, (t - self.t0) / max(self.t1 - self.t0, 1))
        frame[:, x0:] = pl[:, 960:960 + (W - x0)]
        k = min(80, x0)
        frame[:, x0 - k:x0] *= 1 - self.edge[:, ::-1][:, 80 - k:]
        line = frame[:, x0:x0 + 2]
        line *= 0.6
        line += np.array(LIME, np.float32) * 0.25
        dx = x0 - (W - 960)
        ts = self.s["t_swap"]
        if t < ts + 0.3:
            draw_runs_off(frame, self.a, t, clamp((ts + 0.3 - t) / 0.3) if t > ts else 1.0, dx)
        if t >= ts:
            draw_runs_off(frame, self.b, t, 1.0, dx)


def draw_runs_off(frame, runs, t, alpha, dx):
    if abs(dx) > 0.5:
        runs = [dict(r, x=r["x"] + dx) if "x" in r else dict(r, x0=r["x0"] + dx, x1=r["x1"] + dx) for r in runs]
    draw_runs(frame, runs, t, alpha)


# ------------------------------------------------------------------ captions
class Captions:
    """AB's word captions (white, tight, soft shadow, low on the frame); key phrases as Iman's callout in lime/red caps."""
    SIZE, BASE = 70, 1010

    def __init__(self, caps):
        self.caps = []
        for c in caps:
            ws = [w for w, _ in c["words"]]
            if c.get("hl"):
                text = " ".join(ws)
                size = 72
                _, lw = I.letter_layout(text, "big", size)
                if lw > 1600:
                    size = int(size * 1600 / lw)
                xs, lw = I.letter_layout(text, "big", size)
                x0, k, items = (W - lw) / 2, 0, []
                for w, tw in c["words"]:
                    items.append((w, tw, x0 + xs[k]))
                    k += len(w) + 1
                self.caps.append((c["t0"], c["t1"], items, size, c["hl"]))
            else:
                xs, lw = T.layout_line(ws, self.SIZE, path=CAPF)
                size = self.SIZE
                if lw > 1500:
                    size = int(self.SIZE * 1500 / lw)
                    xs, lw = T.layout_line(ws, size, path=CAPF)
                x0 = (W - lw) / 2
                self.caps.append((c["t0"], c["t1"], [(w, tw, x0 + x) for (w, tw), x in zip(c["words"], xs)], size, None))

    def draw(self, frame, t):
        for t0, t1, words, size, hl in self.caps:
            if t0 <= t < t1:
                if hl:
                    frame *= 1 - CALL_BACK * clamp((t - t0 + 0.1) / 0.2) * clamp((t1 - t) / 0.15)
                    rgb = LIME if hl == "lime" else RED
                    for w, tw, x in words:
                        I.draw_letters(frame, w, "big", size, x, self.BASE - 4, t, tw, rgb, True, stagger=0.025, dur=0.25, blur=12)
                else:
                    for w, tw, x in words:
                        T.draw_word(frame, w, size, x, self.BASE, t, tw, path=CAPF, dur=0.12, rise=9)


# ------------------------------------------------------------------ main loop
FULL = {"iman": Card, "chart": Chart, "dom": Dom, "steps": Steps, "cta": Cta}
OVER = {"side": Side, "headline": Headline, "intro": Intro}


def build(plan):
    global CX, CY
    CX, CY = plan.get("anchor", (CX, CY))
    full, over, split = [], [], []
    for s in plan["scenes"]:
        if s["kind"] in FULL:
            full.append(FULL[s["kind"]](s))
        elif s["kind"] == "split":
            split.append(Split(s))
        else:
            over.append(OVER[s["kind"]](s))
    leaks = [dict(l, s=l["s"] * 0.35) for l in plan["leaks"]]
    edges = []                                              # cuts into / out of full-screen graphics
    fs = sorted(full, key=lambda x: x.t0)
    for i, f in enumerate(fs):
        if i == 0 or abs(fs[i - 1].t1 - f.t0) > 0.02:
            edges.append((f.t0, 1.0))
        else:
            edges.append((f.t0, 0.55))
        if i == len(fs) - 1 or abs(fs[i + 1].t0 - f.t1) > 0.02:
            edges.append((f.t1, 1.0))
    pans = [o for o in over if o.s["kind"] == "side"]
    intro = next((o for o in over if o.s["kind"] == "intro"), None)
    return (R.Zoom(plan["zoom"]), Sweeps(leaks), full, over, split, Captions(plan["captions"]), plan["dur"], edges, pans,
            intro)


def pan_at(t, pans):
    w = 0.0
    for o in pans:
        w = max(w, ease_io((t - (o.t0 - 0.55)) / 0.6) * (1 - ease_io((t - o.t1) / 0.7)))
    return 330 * w


def intro_zoom(t, t1):
    """Punch in from black to a tight shot, settle, then creep in until the first card."""
    if t < 0.5:
        return 1.75 - 0.33 * ease_out(t / 0.5)
    return 1.42 + 0.12 * ease_io((t - 0.5) / max(t1 - 0.5, 1))


def compose(base, t, st):
    zoom, sweeps, full, over, split, caps, dur, edges, pans, intro = st
    CUR["base"], CUR["blur"] = base, None
    sc = next((s for s in full if s.t0 <= t < s.t1), None)
    if sc is not None:
        frame = np.empty((H, W, 3), np.float32)
        sc.draw(frame, base, t, zoom.at(sc.t0 - 0.002))
        frame = scale_about(frame, 1 + 0.035 * ease_io((t - sc.t0) / max(sc.t1 - sc.t0, 0.5)))   # slow camera drift
    else:
        sp = next((s for s in split if s.t0 <= t < s.t1), None)
        if intro is not None and t < intro.t1:
            frame = zoomed(base, 1.0)
        else:
            frame = zoomed(base, min(BASE_Z * zoom.at(t), ZMAX), sp.shift(t) if sp else 0.0)
        frame *= 1 - BOTTOM
        if sp:
            sp.draw(frame, t)
        for o in over:
            if o.t0 <= t < o.t1:
                o.draw(frame, t)
    for b, k in edges:                                      # punch transition: zoom blur + a quick flash of light
        d = abs(t - b)
        if d < 0.2:
            e = (1 - d / 0.2) ** 1.6 * k
            frame = zoom_blur(frame, 0.13 * e)
            frame += (255 - frame) * 0.28 * e ** 2
    if t < 0.4:                                             # the opening: out of black, blur resolving
        frame *= ease_out(t / 0.35)
    sweeps.apply(frame, t)
    frame *= VIGNETTE
    frame += GRAIN[int(t * FPS) % len(GRAIN)]
    caps.draw(frame, t)
    if t > dur - 0.5:
        frame *= clamp((dur - t) / 0.5)
    return frame


def render(plan, base_path, out_path, f0, f1):
    st = build(plan)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.4f}", "-i", base_path, "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-color_range", "tv", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", out_path],
                           stdin=subprocess.PIPE)
    fsz, last = BW * BH * 3, None
    for i in range(f0, f1):
        t = i / FPS
        raw = dec.stdout.read(fsz)
        if len(raw) < fsz:
            raw = last
        last = raw
        base = np.frombuffer(raw, np.uint8).reshape(BH, BW, 3)
        frame = compose(base, t, st)
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        if (i - f0) % 300 == 0:
            print(f"{t:7.2f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.kill()


def stills(plan, base_path, times, out_dir):
    """Single frames for checking (seeks the A-roll per frame)."""
    st = build(plan)
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", base_path, "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        base = np.frombuffer(raw, np.uint8).reshape(BH, BW, 3)
        fr = compose(base, t, st)
        Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).save(f"{out_dir}/f_{t:07.2f}.jpg", quality=90)


if __name__ == "__main__":
    plan = json.load(open(sys.argv[1]))
    if sys.argv[2] == "stills":
        stills(plan, sys.argv[3], [float(x) for x in sys.argv[5].split(",")], sys.argv[4])
    else:
        total = int(round(plan["dur"] * FPS))
        f0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        f1 = int(sys.argv[5]) if len(sys.argv) > 5 else total
        render(plan, sys.argv[2], sys.argv[3], f0, min(f1, total))
