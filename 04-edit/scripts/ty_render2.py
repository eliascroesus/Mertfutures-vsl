"""Compositor for thank-you v2: AB's structure and captions with Iman Gadzhi-style motion graphics.

Cards sit on the drifting brand plate (purple, or red for the 'odds are stacked against you' card); text blurs in
letter by letter as Ricky says each word; icons in glass tiles; the application form, the email, the guru
thumbnails and his results in glowing frames; transitions are a clean purple-white light sweep.

    python ty_render2.py plan.json base.mp4 out.mp4 [f0 f1]
"""
import json, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/home/user/work/scripts")
import ty_text as T
import ty_iman as I
import ty_gfx as G
import ty_render as R

W, H, FPS = 1920, 1080, 30
GFX = "/home/user/work/gfx/ty"
clamp, ease_io, ease_out = R.clamp, R.ease_io, R.ease_out


class Sweeps(R.Leaks):
    """Same timing and shape as AB's light leaks, in the brand's purple-to-white light."""
    PAL = np.array([[0.22, 0.08, 0.45], [0.5, 0.28, 0.95], [0.75, 0.58, 1.0], [0.9, 0.84, 1.0], [1.0, 0.98, 1.0]], np.float32)


_cache = {}
# the falling chart line on the red card, routed around the text (left of it, then underneath)
CHART = [(-0.02, 0.04), (0.08, 0.18), (0.05, 0.27), (0.085, 0.64), (0.3, 0.72), (0.27, 0.8), (0.62, 0.86), (0.58, 0.93),
         (1.03, 0.99)]


def chart_mask(p):
    """The falling line drawn on up to fraction p of its length, anti-aliased (drawn 2x, scaled down)."""
    pts = [(x * W * 2, y * H * 2) for x, y in CHART]
    segs = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    left = p * sum(segs)
    draw = [pts[0]]
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if left <= 0:
            break
        f = min(1, left / L)
        draw.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
        left -= L
    m = Image.new("L", (W * 2, H * 2), 0)
    if len(draw) > 1:
        ImageDraw.Draw(m).line(draw, fill=255, width=26, joint="curve")
    return m.resize((W, H), Image.LANCZOS)


def cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def tile(icon, label):
    return cached(("tile", icon, label), lambda: I.glass_tile(Image.open(f"{GFX}/icon_{icon}.png"), label))


def draw_rise(frame, img, cx, cy, t, t_in, rise=40, dur=0.45, blur=12, scale=None):
    """Iman element entrance: rises a little, sharpens and fades in."""
    r = t - t_in
    if r < 0:
        return
    e = ease_out(r / dur)
    bq = int(round(blur * (1 - e) / 2)) * 2
    im = img
    if scale is not None:
        s = scale + (1 - scale) * e
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if bq > 0:
        im = cached(("blur", id(img), bq, im.size), lambda: im.filter(ImageFilter.GaussianBlur(bq)))
    T.blend(frame, np.asarray(im), int(cx - im.width / 2), int(cy - im.height / 2 + rise * (1 - e)), e)


class Scene:
    plates = {}

    def __init__(self, s):
        self.s, self.t0, self.t1 = s, s["t0"], s["t1"]
        pc = s.get("plate", "purple")
        if pc not in Scene.plates:
            Scene.plates[pc] = I.plate(I.RED if pc == "red" else I.PURPLE)
        self.plate = Scene.plates[pc]
        k = s["kind"]
        if k == "iman":
            self.runs, top, bot = I.layout_rows(s["rows"], s.get("cy", 520))
            self.icon = tile(s["icon"], None) if s.get("icon") else None
            self.icon_y = top - 150
        elif k == "tiles":
            self.items = [(tile(i, lab), t) for i, lab, t in s["items"]]
            self.runs = I.layout_rows(s["rows"], s.get("rows_cy", 760))[0] if s.get("rows") else []
        elif k == "app":
            self.imgs = [cached(("app", j), lambda j=j: I.framed(G.application_card(j / 5, blur=0, raw=True), 1180, 660, tilt=-6))
                         for j in range(6)]
        elif k == "email":
            self.imgs = [cached("email", lambda: I.framed(G.email_card(blur=0, raw=True), 1120, 620, tilt=6))]
        elif k == "flicker":
            self.thumbs = [cached(("guru", j), lambda j=j: I.framed(G.guru_thumb(j, raw=True), 1080, 610,
                                                                     tilt=5 if j % 2 else -5)) for j in range(s.get("n", 12))]
        elif k == "pip":
            self.runs, _, _ = I.layout_rows(s["title"], 850)
            self.wall = cached("wall", self.build_wall)
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, W - 1, H - 1), 44, fill=255)
            self.round = m
            g = Image.new("L", (W + 240, H + 240), 0)
            ImageDraw.Draw(g).rounded_rectangle((114, 114, W + 126, H + 126), 52, fill=200)
            gl = Image.new("RGBA", g.size, I.PURPLE + (0,))
            gl.putalpha(g.filter(ImageFilter.GaussianBlur(44)).point(lambda v: int(v * 0.8)))
            self.glow = gl

    def build_wall(self):
        import cards2 as C2
        names = ["shop_36k", "labels_strip", "shop_11k", "shop_payout", "shop_today_2k", "labels_stack", "shop_laptop_night"]
        tiles = []
        for n in names:
            im, _ = C2.source(n)
            tiles.append(I.framed(im, 380, 560))
        cols, colw = 4, 450
        hcol = [0] * cols
        wall = Image.new("RGBA", (W, 3400), (0, 0, 0, 0))
        k = 0
        while min(hcol) < 3100:
            c = int(np.argmin(hcol))
            im = tiles[k % len(tiles)]
            x = int(W / 2 + (c - (cols - 1) / 2) * colw - im.width / 2)
            wall.alpha_composite(im, (x, hcol[c] + (70 if c % 2 else 0)))
            hcol[c] += im.height - 170
            k += 1
        return np.asarray(wall)

    def draw(self, frame, face, t, zprev):
        k, r = self.s["kind"], t - self.t0
        frame[:] = I.plate_at(self.plate, r / max(self.t1 - self.t0, 0.5))
        if k == "iman":
            if self.s.get("chart"):
                p = clamp((r - self.s.get("chart_delay", 0.9)) / self.s.get("chart_dur", 1.3))
                if p > 0:
                    m = chart_mask(ease_io(p))
                    core = np.asarray(m, np.float32)[..., None] / 255.0
                    glow = np.asarray(m.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
                                      .resize((W, H), Image.BILINEAR), np.float32)[..., None] / 255.0
                    col = np.array(I.RED, np.float32)
                    frame += glow * 1.6 * col * 0.5
                    frame *= 1 - core * 0.9
                    frame += core * 0.9 * col
            if self.icon is not None:
                draw_rise(frame, self.icon, W / 2, self.icon_y, t, self.t0 + 0.05)
            I.draw_runs(frame, self.runs, t)
        elif k == "tiles":
            n_vis = [ti for _, ti in self.items]
            for j, (im, ti) in enumerate(self.items):
                if ti > t:
                    continue
                x = W / 2
                for m_ in range(j + 1, len(self.items) + 1):
                    tm = n_vis[m_ - 1]
                    target = W / 2 + (j - (m_ - 1) / 2) * self.s.get("spacing", 420)
                    if m_ == j + 1:
                        x = target
                    elif t >= tm:
                        x = x + (target - x) * ease_io((t - tm) / 0.35)
                draw_rise(frame, im, x, self.s.get("tile_y", 500), t, ti, rise=50)
            I.draw_runs(frame, self.runs, t)
        elif k in ("app", "email"):
            idx = min(5, int(clamp((r - 0.8) / 1.2) * 5)) if k == "app" else 0
            im = self.imgs[idx]
            drift = 1 + 0.035 * ease_io(r / max(self.t1 - self.t0, 0.5))
            j = im.resize((int(im.width * drift), int(im.height * drift)), Image.BICUBIC) if r > 0.45 else im
            if r <= 0.45:
                draw_rise(frame, im, W / 2, 500, t, self.t0 + 0.02, rise=60, dur=0.45, blur=14, scale=0.94)
            else:
                T.blend(frame, np.asarray(j), int(W / 2 - j.width / 2), int(500 - j.height / 2), 1.0)
        elif k == "flicker":
            n = len(self.thumbs)
            i = min(n - 1, int(r / (3 / FPS)))
            im = self.thumbs[i]
            op, out_t = 1.0, self.t1 - t
            if i == n - 1 and out_t < 0.35:
                b = (0.35 - out_t) / 0.35
                im = cached(("gblur", i, int(b * 6)), lambda: im.filter(ImageFilter.GaussianBlur(16 * int(b * 6) / 6)))
                op = 1 - b
            T.blend(frame, np.asarray(im), int(W / 2 - im.width / 2), int(480 - im.height / 2), op)
        elif k == "pip":
            self.draw_pip(frame, face, r, t, zprev)
        if k in ("iman", "tiles"):                         # the captions take the bottom on the other cards
            I.draw_mark(frame, t, self.t0)

    def draw_pip(self, frame, face, r, t, zprev):
        if r > 0.35:
            dy = H + 40 - (330.0 * (r - 0.35) + 260 * (1 - math.exp(-(r - 0.35) / 0.5)))
            T.blend(frame, self.wall, 0, int(dy), 1.0)
        e = ease_io(r / 0.6)
        s = 1 - 0.5 * e
        cy = 540 - 110 * e - 1050 * ease_io((r - 0.95) / 0.8) ** 1.6
        if cy > -H * s / 2:
            src = R.zoomed(face, zprev + (1 - zprev) * e)          # carries on from the held push-in, no jump
            w, h = int(W * s), int(H * s)
            gl = self.glow.resize((int(self.glow.width * s), int(self.glow.height * s)), Image.BILINEAR)
            T.blend(frame, np.asarray(gl), int(W / 2 - gl.width / 2), int(cy - gl.height / 2), clamp(r / 0.15))
            card = Image.fromarray(src).resize((w, h), Image.BILINEAR).convert("RGBA")
            card.putalpha(self.round.resize((w, h), Image.BILINEAR))
            T.blend(frame, np.asarray(card), int(W / 2 - w / 2), int(cy - h / 2), 1.0)
        t_first = self.runs[0]["t"]
        a = clamp((t - (t_first - 0.35)) / 0.35)
        if a > 0:
            pl = I.plate_at(self.plate, r / max(self.t1 - self.t0, 0.5))
            g = np.clip((np.arange(H) - 520) / 240.0, 0, 1)[:, None, None] * a
            frame *= 1 - g
            frame += pl * g
        I.draw_runs(frame, self.runs, t)


def render(plan, base_path, out_path, f0, f1):
    if plan.get("anchor"):                                  # where his face is (zoom centre)
        R.CX, R.CY = plan["anchor"]
    zoom = R.Zoom(plan["zoom"])
    sweeps = Sweeps(plan["leaks"])
    scenes = [Scene(s) for s in plan["scenes"]]
    caps = R.Captions(plan["captions"])
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.4f}", "-i", base_path, "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-color_range", "tv", "-preset", "medium", "-crf", "17", "-movflags", "+faststart", out_path],
                           stdin=subprocess.PIPE)
    fsz, last = W * H * 3, None
    for i in range(f0, f1):
        t = i / FPS
        raw = dec.stdout.read(fsz)
        if len(raw) < fsz:
            raw = last
        last = raw
        face = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        frame = compose(face, t, zoom, sweeps, scenes, caps)
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        if (i - f0) % 300 == 0:
            print(f"{t:7.2f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.kill()


def compose(face, t, zoom, sweeps, scenes, caps):
    sc = next((s for s in scenes if s.t0 <= t < s.t1), None)
    if sc is None:
        frame = R.zoomed(face, zoom.at(t)).astype(np.float32)
    else:
        frame = np.empty((H, W, 3), np.float32)
        sc.draw(frame, face, t, zoom.at(sc.t0 - 0.002))
    sweeps.apply(frame, t)
    caps.draw(frame, t)
    return frame


if __name__ == "__main__":
    plan = json.load(open(sys.argv[1]))
    total = int(round(plan["dur"] * FPS))
    f0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    f1 = int(sys.argv[5]) if len(sys.argv) > 5 else total
    render(plan, sys.argv[2], sys.argv[3], f0, min(f1, total))
