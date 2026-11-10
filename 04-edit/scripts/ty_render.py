"""Frame compositor for Ricky's thank-you video in AB Nasdaq's thank-you style.

Layers per frame: Ricky (with the smooth zoom curve) or a full-screen card (green/red gradient with word-by-word
text, icon circles, the application / email card, the guru-thumbnail flicker, the PiP + results wall), then the
light leaks (screen-blended film burn), then the captions. Encodes BT.709.

    python ty_render.py base plan.json base.mp4               # cut + grade the A-roll at 30 fps
    python ty_render.py frames plan.json base.mp4 out.mp4 [f0 f1]
"""
import json, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/home/user/work/scripts")
import ty_text as T

W, H, FPS = 1920, 1080, 30
RAW = "/home/user/work/thankyou/raw/thankyou_raw.mp4"
GFX = "/home/user/work/gfx/ty"
CX, CY = 831, 520                       # zoom anchor: Ricky's face
CAP_SIZE, CAP_BASE = 82, 1026           # captions: size, baseline (text centre ~92.7 % of the height)
GRADE = "eq=contrast=1.05:brightness=0.02:saturation=1.05,unsharp=5:5:0.35"


def clamp(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_io(x):
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_back(x, s=1.7):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


# ------------------------------------------------------------------ base A-roll
def render_base(plan, out):
    inputs, chains, labels = [], [], []
    raw = plan.get("raw", RAW)
    for i, (a, b) in enumerate(plan["keep"]):
        nf = round((b - a) * FPS)
        inputs += ["-ss", f"{a:.4f}", "-i", raw]
        chains.append(f"[{i}:v]fps={FPS},trim=end_frame={nf},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,{GRADE},"
                      f"format=yuv420p[s{i}]")
        labels.append(f"[s{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=1:a=0[v]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[v]", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "12", "-g", "15", out], check=True)


# ------------------------------------------------------------------ zoom curve
class Zoom:
    def __init__(self, keys):
        self.k = keys

    def at(self, t):
        k = self.k
        if t <= k[0][0]:
            return k[0][1]
        for (ta, za), (tb, zb) in zip(k, k[1:]):
            if ta <= t <= tb:
                if tb - ta < 0.01:
                    return zb
                return za + (zb - za) * ease_io((t - ta) / (tb - ta))
        return k[-1][1]


def zoomed(base, z):
    if z <= 1.001:
        return base
    cw, ch = W / z, H / z
    x0 = min(max(CX - cw / 2, 0), W - cw)
    y0 = min(max(CY - ch / 2, 0), H - ch)
    im = Image.fromarray(base).resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    return np.asarray(im)


# ------------------------------------------------------------------ light leaks (procedural film burn)
class Leaks:
    LW, LH = 320, 180
    PAL = np.array([[0.6, 0.12, 0.04], [1.0, 0.42, 0.1], [1.0, 0.7, 0.25], [1.0, 0.86, 0.45], [1.0, 0.95, 0.7]], np.float32)

    def __init__(self, leaks):
        from scipy.ndimage import gaussian_filter
        self.ev = leaks
        yy, xx = np.mgrid[0:self.LH, 0:self.LW]
        self.x, self.y = xx / self.LW, yy / self.LH
        self.noise = []                                 # organic, uneven burn texture per event
        for k in range(len(leaks)):
            n = gaussian_filter(np.random.default_rng(k + 11).random((self.LH, self.LW * 2)), 9, mode="wrap")
            n = (n - n.min()) / (n.max() - n.min())
            self.noise.append(n)

    def color(self, v):
        v = np.clip(v, 0, 1) * (len(self.PAL) - 1)
        i = np.minimum(v.astype(int), len(self.PAL) - 2)
        f = (v - i)[..., None]
        return self.PAL[i] * (1 - f) + self.PAL[i + 1] * f

    def field(self, e, k, r):
        """Light amount (0..1+) for event e at time r relative to its peak."""
        s = e["s"]
        rng = np.random.default_rng(k * 7 + 3)
        d = 1 if k % 2 else -1
        yc = 0.35 + 0.3 * rng.random()
        if r < -0.02:
            inten = ease_io((r + 0.22) / 0.2)
        elif r < 0.03:
            inten = 1.0
        else:
            inten = math.exp(-(r - 0.03) / 0.09)
        p = clamp((r + 0.22) / 0.62)
        cx = 0.5 + d * (0.75 - 1.1 * p)
        band = np.exp(-((self.x - cx) / 0.42) ** 2 - ((self.y - yc) / 0.3) ** 2)
        streak = np.exp(-((self.y - yc - 0.22 * math.sin(k)) / 0.09) ** 2) * np.exp(-((self.x - cx - d * 0.2) / 0.6) ** 2)
        wash = max(0.0, inten - 0.6) / 0.4
        sh = int(r * d * 160) % self.LW
        tex = 0.65 + 0.7 * self.noise[k][:, sh:sh + self.LW]
        v = inten * (0.95 * band + 0.4 * streak) * tex + 0.7 * wash ** 1.5 * (0.75 + 0.25 * band) * (1.05 - 0.45 * self.y)
        if r > 0.03:                                    # leftover glow drifting at one edge
            ex = 0.95 if d > 0 else 0.05
            glow = np.exp(-((self.x - ex) / 0.16) ** 2 - ((self.y - (0.2 + 0.5 * rng.random())) / 0.22) ** 2)
            v = v + glow * 0.55 * math.exp(-(r - 0.03) / 0.22) * (1 - math.exp(-(r - 0.03) / 0.05))
        return v * s

    def apply(self, frame, t):
        for k, e in enumerate(self.ev):
            r = t - e["t"]
            if -0.22 <= r <= 0.45:
                v = self.field(e, k, r)
                col = self.color(v * 0.95) * np.clip(v, 0, 1)[..., None]
                big = np.asarray(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR),
                                 np.float32) / 255.0
                frame[:] = 255.0 - (255.0 - frame) * (1.0 - big)          # screen blend


# ------------------------------------------------------------------ text block (cards)
def layout(lines, sizes, cy, maxw=1640):
    rows = []
    for line, size in zip(lines, sizes):
        vis = [(w, t) for w, t in line if w != "_"]
        ws = [w for w, _ in vis]
        xs, lw = T.layout_line(ws, size)
        if lw > maxw:
            size = int(size * maxw / lw)
            xs, lw = T.layout_line(ws, size)
        rows.append((vis, size, xs, lw))
    hs = [s * 1.08 for _, s, _, _ in rows]
    top = cy - sum(hs) / 2
    out, y = [], top
    for (vis, size, xs, lw), h in zip(rows, hs):
        base = y + size * 0.86
        x0 = (W - lw) / 2
        for (w, t), x in zip(vis, xs):
            out.append((w, t, size, x0 + x, base))
        y += h
    return out, top


class Icon:
    def __init__(self, name, t, cx, cy):
        self.im = Image.open(f"{GFX}/icon_{name}.png")
        self.t, self.cx, self.cy = t, cx, cy
        sh = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        sh.putalpha(self.im.getchannel("A").filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * 0.5)))
        self.sh = sh

    def draw(self, frame, t):
        r = t - self.t
        if r < 0:
            return
        s = 0.3 + 0.7 * ease_back(r / 0.4)
        ang = 5 * math.sin(r * 2.4) * math.exp(-r / 2.5) + 2 * math.sin(r * 1.3)
        op = clamp(r / 0.15)
        for im, dx in ((self.sh, 5), (self.im, 0)):
            j = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC).rotate(ang, Image.BICUBIC, expand=True)
            T.blend(frame, np.asarray(j), int(self.cx - j.width / 2 + dx), int(self.cy - j.height / 2 + dx), op)


CHART = [(-0.02, -0.02), (0.15, 0.17), (0.11, 0.31), (0.47, 0.5), (0.44, 0.68), (0.76, 0.86), (1.03, 0.95)]


def chart_mask(p):
    """The red card's falling zig-zag line, drawn on up to fraction p of its length (half-res mask)."""
    pts = [(x * W / 2, y * H / 2) for x, y in CHART]
    segs = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total, left = sum(segs), p * sum(segs)
    draw = [pts[0]]
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if left <= 0:
            break
        f = min(1, left / L)
        draw.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
        left -= L
    m = Image.new("L", (W // 2, H // 2), 0)
    if len(draw) > 1:
        ImageDraw.Draw(m).line(draw, fill=255, width=9, joint="curve")
    return m.resize((W, H), Image.BILINEAR)


# ------------------------------------------------------------------ scenes
class Scene:
    bgs = {}

    def __init__(self, s, plan):
        self.s = s
        self.t0, self.t1 = s["t0"], s["t1"]
        if s["bg"] not in Scene.bgs:
            Scene.bgs[s["bg"]] = np.load(f"{GFX}/bg_{s['bg']}.npy")
        self.bg = Scene.bgs[s["bg"]]
        k = s["kind"]
        if k == "text":
            sizes = s.get("sizes") or [96] * len(s["lines"])
            cy = s.get("cy", 500)
            self.words, top = layout(s["lines"], sizes, cy)
            self.icon = Icon(s["icon"], self.t0 + 0.08, W / 2, top - 120) if s.get("icon") else None
        elif k == "circles":
            self.items = [(Image.open(f"{GFX}/circle_{n}.png"), t) for n, t in s["items"]]
        elif k == "app":
            self.imgs = [Image.open(f"{GFX}/app_{i}.png") for i in range(6)]
        elif k == "email":
            self.imgs = [Image.open(f"{GFX}/email.png")]
        elif k == "flicker":
            self.thumbs = []
            for i in range(s.get("n", 12)):
                im = Image.open(f"{GFX}/guru_{i:02d}.png")
                im = im.resize((1180, int(im.height * 1180 / im.width)), Image.LANCZOS)
                self.thumbs.append(im)
        elif k == "pip":
            self.title, _ = layout(s["title"], [118, 118], 880)
            self.tiles = [Image.open(f"{GFX}/res_{n}.png") for n in
                          ["shop_36k", "labels_strip", "shop_11k", "shop_payout", "shop_today_2k", "labels_stack",
                           "shop_laptop_night"]]
            self.wall = self.build_wall()
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, W - 1, H - 1), 40, fill=255)
            self.round = m

    def build_wall(self):
        """Masonry wall of result tiles, 4 columns, tall enough to scroll for the whole scene."""
        cols, colw = 4, 470
        hcol = [0] * cols
        wall = Image.new("RGBA", (W, 3200), (0, 0, 0, 0))
        k = 0
        while min(hcol) < 3000:
            c = int(np.argmin(hcol))
            im = self.tiles[k % len(self.tiles)]
            x = int(W / 2 + (c - (cols - 1) / 2) * colw - im.width / 2)
            wall.alpha_composite(im, (x, hcol[c] + (60 if c % 2 else 0)))
            hcol[c] += im.height - 40
            k += 1
        return np.asarray(wall)

    # -- drawing
    def draw(self, frame, face, t):
        k = self.s["kind"]
        r = t - self.t0
        frame[:] = self.bg
        if k == "text":
            if self.s.get("chart"):
                p = clamp((r - 0.9) / 1.3)
                if p > 0:
                    m = np.asarray(chart_mask(ease_io(p)), np.float32)[..., None] / 255.0
                    sh = np.roll(m, (8, 6), (0, 1)) * 0.35
                    frame *= 1 - sh
                    frame *= 1 - m * 0.85
                    frame += m * 0.85 * np.array([118, 0, 24], np.float32)
            if self.icon:
                self.icon.draw(frame, t)
            fade = clamp(r / 0.25) if self.s.get("fade_in") else 1.0
            for w, tw, size, x, base in self.words:
                T.draw_word(frame, w, size, x, base, t, tw, dur=0.2, rise=12, alpha=fade)
        elif k == "circles":
            n = sum(1 for _, ti in self.items if ti <= t)
            for j, (im, ti) in enumerate(self.items):
                if ti > t:
                    continue
                rr = t - ti
                # target x for every count of visible circles; ease between them
                xs = []
                for m_ in range(j + 1, len(self.items) + 1):
                    tm = self.items[m_ - 1][1]
                    xs.append((tm, W / 2 + (j - (m_ - 1) / 2) * 450))
                x = xs[0][1]
                for tm, xt in xs[1:]:
                    if t >= tm:
                        x = x + (xt - x) * ease_io((t - tm) / 0.28)
                if j == 0:
                    s, ang, op, bl = 0.9 + 0.1 * ease_out(rr / 0.3), 0.0, clamp(rr / 0.25), 0
                else:
                    s, ang, op = 0.2 + 0.8 * ease_back(rr / 0.35), -35 * (1 - ease_out(rr / 0.35)), clamp(rr / 0.2)
                    bl = 5 * (1 - clamp(rr / 0.25))
                    x += 170 * (1 - ease_out(rr / 0.4))         # spins in from the outside edge
                j_im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
                if abs(ang) > 0.3:
                    j_im = j_im.rotate(ang, Image.BICUBIC, expand=True)
                if bl > 0.5:
                    j_im = j_im.filter(ImageFilter.GaussianBlur(bl))
                T.blend(frame, np.asarray(j_im), int(x - j_im.width / 2), int(470 - j_im.height / 2), op)
        elif k in ("app", "email"):
            p = ease_out((r - 0.04) / 0.5)
            s = 0.04 + 0.96 * p
            idx = min(5, int(clamp((r - 0.8) / 1.2) * 5)) if k == "app" else 0
            im = self.imgs[idx]
            j = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
            cy = 470 + 50 * (1 - p)
            T.blend(frame, np.asarray(j), int(W / 2 - j.width / 2), int(cy - j.height / 2), clamp(r / 0.1))
        elif k == "flicker":
            step = 3 / FPS
            n = len(self.thumbs)
            i = min(n - 1, int(r / step))
            im = self.thumbs[i]
            out_t = self.t1 - t
            op = 1.0
            if i == n - 1 and out_t < 0.35:
                b = (0.35 - out_t) / 0.35
                im = im.filter(ImageFilter.GaussianBlur(14 * b))
                op = 1 - b
            T.blend(frame, np.asarray(im), int(W / 2 - im.width / 2), int(470 - im.height / 2), op)
        elif k == "pip":
            self.draw_pip(frame, face, r, t)

    def draw_pip(self, frame, face, r, t):
        # wall scrolls up from below, starting while the face shrinks
        if r > 0.35:
            v = 330.0
            dy = H + 40 - (v * (r - 0.35) + 260 * (1 - math.exp(-(r - 0.35) / 0.5)))
            T.blend(frame, self.wall, 0, int(dy), 1.0)
        # Ricky shrinks into a rounded window, then slides up and out
        s = 1 - 0.5 * ease_io(r / 0.6)
        cy = 540 - 110 * ease_io(r / 0.6) - 1050 * ease_io((r - 0.95) / 0.8) ** 1.6
        if cy > -H * s / 2:
            w, h = int(W * s), int(H * s)
            im = Image.fromarray(face).resize((w, h), Image.BILINEAR)
            mask = self.round.resize((w, h), Image.BILINEAR)
            sh = Image.new("RGBA", (w + 120, h + 120), (0, 0, 0, 0))
            sm = Image.new("L", sh.size, 0)
            sm.paste(mask, (60, 72))
            sh.putalpha(sm.filter(ImageFilter.GaussianBlur(26)).point(lambda a: int(a * 0.55)))
            T.blend(frame, np.asarray(sh), int(W / 2 - w / 2 - 60), int(cy - h / 2 - 60), clamp(r / 0.05))
            card = im.convert("RGBA")
            card.putalpha(mask)
            T.blend(frame, np.asarray(card), int(W / 2 - w / 2), int(cy - h / 2), 1.0)
        # title: clean the bottom so it sits on the gradient, then the words rise in
        t_first = self.title[0][1]
        a = clamp((t - (t_first - 0.35)) / 0.35)
        if a > 0:
            g = np.clip((np.arange(H) - 560) / 260.0, 0, 1)[:, None, None] * a
            frame *= 1 - g
            frame += self.bg * g
        for w, tw, size, x, base in self.title:
            T.draw_word(frame, w, size, x, base, t, tw, dur=0.3, rise=40)


# ------------------------------------------------------------------ captions
class Captions:
    def __init__(self, caps):
        self.caps = []
        for c in caps:
            ws = [w for w, _ in c["words"]]
            size = CAP_SIZE
            xs, lw = T.layout_line(ws, size)
            if lw > 1500:
                size = int(size * 1500 / lw)
                xs, lw = T.layout_line(ws, size)
            x0 = (W - lw) / 2
            self.caps.append((c["t0"], c["t1"], [(w, tw, x0 + x) for (w, tw), x in zip(c["words"], xs)], size))

    def draw(self, frame, t):
        for t0, t1, words, size in self.caps:
            if t0 <= t < t1:
                for w, tw, x in words:
                    T.draw_word(frame, w, size, x, CAP_BASE, t, tw, dur=0.12, rise=9)


# ------------------------------------------------------------------ main loop
def render(plan, base_path, out_path, f0, f1):
    zoom = Zoom(plan["zoom"])
    leaks = Leaks(plan["leaks"])
    scenes = [Scene(s, plan) for s in plan["scenes"]]
    caps = Captions(plan["captions"])
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.4f}", "-i", base_path, "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-color_range", "tv", "-preset", "medium", "-crf", "17", "-movflags", "+faststart", out_path],
                           stdin=subprocess.PIPE)
    fsz = W * H * 3
    last = None
    for i in range(f0, f1):
        t = i / FPS
        raw = dec.stdout.read(fsz)
        if len(raw) < fsz:
            raw = last
        last = raw
        face = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        sc = next((s for s in scenes if s.t0 <= t < s.t1), None)
        if sc is None:
            frame = zoomed(face, zoom.at(t)).astype(np.float32)
        else:
            frame = np.empty((H, W, 3), np.float32)
            sc.draw(frame, face, t)
        leaks.apply(frame, t)
        caps.draw(frame, t)
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        if (i - f0) % 300 == 0:
            print(f"{t:7.2f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.kill()


if __name__ == "__main__":
    mode, plan = sys.argv[1], json.load(open(sys.argv[2]))
    if mode == "base":
        render_base(plan, sys.argv[3])
    else:
        total = int(round(plan["dur"] * FPS))
        f0 = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        f1 = int(sys.argv[6]) if len(sys.argv) > 6 else total
        render(plan, sys.argv[3], sys.argv[4], f0, min(f1, total))
