"""Frame compositor for the Iman-style edit.

Reads the base timeline (A-roll cuts) frame by frame, draws the motion-graphics layer (brand plate, cards popping in,
photo stickers beside Ricky, his screen recordings in a glowing frame with number outlines, phone clips in frames)
and pipes the result to ffmpeg, which burns in the ASS text layer (titles, headlines, captions, labels) and encodes.

    python compositor.py elements.json base.mp4 text.ass out_video.mp4 duration
"""
import json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/home/user/work/scripts")
import brand as B

W, H, FPS = 1920, 1080, 30


def clamp(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out_back(x, s=1.4):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3


def blend(dst, src, x, y, opacity=1.0):
    """Alpha-composite an RGBA uint8 array onto an RGB float32 frame at (x, y)."""
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1 or opacity <= 0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = s[..., 3:4] / 255.0 * opacity
    d = dst[y0:y1, x0:x1]
    d *= 1 - a
    d += s[..., :3] * a


def scaled(img, s):
    if abs(s - 1) < 1e-3:
        return img
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.BILINEAR)


class Anim:
    """In/out envelope shared by elements: returns (opacity, scale, dy) for time t."""

    def __init__(self, t0, t1, kind="pop", tin=0.38, tout=0.2):
        self.t0, self.t1, self.kind, self.tin, self.tout = t0, t1, kind, tin, tout

    def at(self, t):
        if self.kind == "overlay":                      # full-frame fades: opacity only, nothing moves or shrinks
            x, y = clamp((t - self.t0) / 0.3), clamp((self.t1 - t) / 0.33)
            return min(x * x * (3 - 2 * x), y * y * (3 - 2 * y)), 1.0, 0
        a = (t - self.t0) / self.tin
        b = (self.t1 - t) / self.tout
        op = min(clamp(a * 2.2), clamp(b))
        if self.kind == "sticker":
            sc = 0.55 + 0.45 * ease_out_back(a, 2.2)
            dy = 0
        elif self.kind == "fade":
            sc, dy = 1.0, 0
        else:
            sc = 0.88 + 0.12 * ease_out_back(a, 1.6)
            dy = 34 * (1 - ease_out_cubic(a))
        if b < 1:
            sc *= 0.96 + 0.04 * clamp(b)
        return op, sc, dy


class Card:
    def __init__(self, e):
        self.e = e
        self.anim = Anim(e["t0"], e["t1"], e.get("anim", "pop"))
        self.img = Image.open(e["img"]).convert("RGBA")
        self.hl = Image.open(e["hl_img"]).convert("RGBA") if e.get("hl_img") else None
        self.cache = {}

    def draw(self, frame, t):
        op, sc, dy = self.anim.at(t)
        if op <= 0:
            return
        src = self.img
        hl_a = 0.0
        if self.hl is not None:
            hl_a = clamp((t - self.e["t0"] - self.e.get("hl_delay", 0.5)) / 0.15)
        key = (round(sc, 3), round(hl_a, 2))
        if key not in self.cache:
            im = src if hl_a <= 0 else (self.hl if hl_a >= 1 else Image.blend(src, self.hl, hl_a))
            arr = np.asarray(scaled(im, sc))
            if len(self.cache) > 64:
                self.cache.clear()
            self.cache[key] = arr
        arr = self.cache[key]
        h, w = arr.shape[:2]
        blend(frame, arr, int(self.e["cx"] - w / 2), int(self.e["cy"] - h / 2 + dy), op)


class FrameBase:
    """The base frame itself (his screen recording), shrunk into a rounded glowing frame on the plate."""

    def __init__(self, e):
        self.e = e
        self.s = e.get("scale", 0.8)
        self.w, self.h = round(W * self.s) // 2 * 2, round(H * self.s) // 2 * 2
        r = 22
        m = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, self.w - 1, self.h - 1), r, fill=255)
        self.mask = (np.asarray(m, np.float32) / 255.0)[..., None]
        pad = 110
        deco = Image.new("RGBA", (self.w + 2 * pad, self.h + 2 * pad), (0, 0, 0, 0))
        g = Image.new("L", deco.size, 0)
        ImageDraw.Draw(g).rounded_rectangle((pad - 6, pad - 6, pad + self.w + 6, pad + self.h + 6), r + 6, fill=190)
        layer = Image.new("RGBA", deco.size, B.PURPLE + (0,))
        layer.putalpha(g.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.7)))
        deco.alpha_composite(layer)
        ImageDraw.Draw(deco).rounded_rectangle((pad, pad, pad + self.w - 1, pad + self.h - 1), r, outline=(255, 255, 255, 50), width=2)
        self.deco, self.pad = np.asarray(deco), pad
        self.cx, self.cy = e.get("cx", 960), e.get("cy", 520)
        self.boxes = []
        for b in e.get("boxes", []):
            x0, y0, x1, y1 = [v * self.s for v in b["box"]]
            bw, bh, m2 = int(x1 - x0) + 40, int(y1 - y0) + 40, 20
            im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            gl = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle((m2, m2, bw - m2, bh - m2), 10, outline=B.PURPLE + (220,), width=10)
            im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(7)))
            ImageDraw.Draw(im).rounded_rectangle((m2, m2, bw - m2, bh - m2), 10, outline=(176, 128, 255, 255), width=4)
            self.boxes.append((b["t0"], b["t1"], int(x0) - m2, int(y0) - m2, np.asarray(im)))

    def draw(self, frame, base, t):
        a = (t - self.e["t0"]) / 0.32
        sc = 0.94 + 0.06 * ease_out_cubic(a) if self.e.get("animate_in", True) else 1.0
        w, h = round(self.w * sc), round(self.h * sc)
        small = np.asarray(Image.fromarray(base).resize((w, h), Image.BILINEAR), np.float32)
        mask = self.mask if (w, h) == (self.w, self.h) else (np.asarray(Image.fromarray((self.mask[..., 0] * 255).astype(np.uint8)).resize((w, h)), np.float32) / 255.0)[..., None]
        x, y = int(self.cx - w / 2), int(self.cy - h / 2)
        deco = self.deco if sc == 1.0 else np.asarray(Image.fromarray(self.deco).resize((w + 2 * self.pad, h + 2 * self.pad)))
        blend(frame, deco, x - self.pad, y - self.pad, 1.0)
        region = frame[y:y + h, x:x + w]
        region *= 1 - mask
        region += small * mask
        for t0, t1, bx, by, im in self.boxes:
            if t0 <= t <= t1:
                op = min(clamp((t - t0) / 0.15), clamp((t1 - t) / 0.15))
                blend(frame, im, x + int(bx * sc), y + int(by * sc), op)


def ease_in_out(x):
    x = clamp(x)
    return 0.5 - 0.5 * np.cos(np.pi * x)


class Split:
    """AB-style split screen: Ricky in a tall panel on the left (cropped around his face), a solid panel on the right
    for a list that the text layer builds line by line. The right panel slides in."""

    def __init__(self, e):
        self.e = e
        self.pw = e.get("panel_w", 840)
        self.cx = e.get("cx", 930)
        self.bg = np.array(e.get("rgb", [8, 8, 10]), np.float32)

    def draw(self, frame, base, t):
        k = min(ease_out_cubic((t - self.e["t0"]) / 0.35), ease_out_cubic((self.e["t1"] - t) / 0.35))
        x0 = int(min(max(self.cx - self.pw / 2, 0), W - self.pw))
        left = int(round(W - (W - self.pw) * k))             # the right panel slides in from the right edge ...
        shift = int(round(x0 * k))                           # ... while the shot slides left into its panel
        frame[:, :left] = base[:, shift:shift + left]
        frame[:, left:] = self.bg


class Behind:
    """AB-style giant text behind Ricky: the text layer is drawn only where he isn't. His outline comes from GrabCut
    on a small copy of each frame, seeded from the previous frame's outline so it stays steady."""

    def __init__(self, e):
        self.e = e
        self.img = np.asarray(Image.open(e["img"]).convert("RGBA"), np.float32)
        self.prev = None

    def person(self, base):
        import cv2
        sw, sh = 480, 270
        bgr = np.ascontiguousarray(cv2.resize(base, (sw, sh), interpolation=cv2.INTER_AREA)[..., ::-1])
        m = np.zeros((sh, sw), np.uint8)
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        if self.prev is None:
            cv2.grabCut(bgr, m, (100, 25, 285, sh - 26), bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
        else:
            m[:] = cv2.GC_PR_BGD
            m[self.prev > 0] = cv2.GC_PR_FGD
            m[cv2.erode(self.prev, np.ones((9, 9), np.uint8)) > 0] = cv2.GC_FGD
            m[cv2.dilate(self.prev, np.ones((21, 21), np.uint8)) == 0] = cv2.GC_BGD
            cv2.grabCut(bgr, m, None, bgd, fgd, 3, cv2.GC_INIT_WITH_MASK)
        fg = (((m == 1) | (m == 3)) * 255).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
        if n > 1:
            fg = ((lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))) * 255).astype(np.uint8)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
        holes = fg.copy()
        cv2.floodFill(holes, None, (0, 0), 255)
        fg = fg | cv2.bitwise_not(holes)                  # fill holes inside him (eyes, collar)
        self.prev = fg
        full = cv2.GaussianBlur(cv2.resize(fg, (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), 1.6)
        return (full.astype(np.float32) / 255.0)[..., None]

    def draw(self, frame, base, t):
        op = min(clamp((t - self.e["t0"]) / 0.12), clamp((self.e["t1"] - t) / 0.2))
        if op <= 0:
            return
        a = self.img[..., 3:4] / 255.0 * op * (1 - self.person(base))
        frame *= 1 - a
        frame += self.img[..., :3] * a


class Zoom:
    """Smooth zooms on Ricky, cropped from the 4K original so the close-up stays sharp.

    Each move is a list of keyframes {"keys": [[t, zoom], ...]} (output time) with an ease-in-out between each pair,
    so it glides in and back out with no jumps. Where the move starts or ends wide, the first and last few frames
    crossfade with the base footage to hide the switch of source. The source is decoded per A-roll piece at 1.2x
    output size (2304x1296), so no zoom up to 1.2 ever upscales.
    """

    S = 1.2
    XF = 0.12    # crossfade with the base at a wide start / end (s)

    def __init__(self, z, keep, src):
        self.keys = [tuple(k) for k in z["keys"]]
        self.z = dict(z, t0=self.keys[0][0], t1=self.keys[-1][0])
        self.src = src
        self.cx, self.cy = z.get("cx", 930), z.get("cy", 590)
        self.pieces, f = [], 0                      # (first output frame, n frames, raw start) per A-roll piece
        i0, i1 = round(self.z["t0"] * FPS), round(self.z["t1"] * FPS)
        for a, b in keep:
            n = round((b - a) * FPS)
            lo, hi = max(i0, f), min(i1, f + n)
            if lo < hi:
                self.pieces.append((lo, hi - lo, a + (lo - f) / FPS))
            f += n
        self.proc, self.cur = None, -1
        self.sw, self.sh = round(W * self.S), round(H * self.S)

    def level(self, t):
        for (ta, za), (tb, zb) in zip(self.keys, self.keys[1:]):
            if ta <= t <= tb:
                return za + (zb - za) * ease_in_out((t - ta) / max(tb - ta, 1e-3))
        return self.keys[-1][1]

    def mix(self, t):
        """How much of the zoomed frame to show (crossfade with the base at a wide start or end)."""
        a = clamp((t - self.z["t0"]) / self.XF) if self.keys[0][1] == 1.0 else 1.0
        b = clamp((self.z["t1"] - t) / self.XF) if self.keys[-1][1] == 1.0 else 1.0
        return min(a, b)

    def frame(self, i, t):
        k = next((j for j, (f0, n, _) in enumerate(self.pieces) if f0 <= i < f0 + n), None)
        if k is None:
            return None
        if k != self.cur:
            self.close()
            f0, n, ss = self.pieces[k]
            ss, n = ss + (i - f0) / FPS, n - (i - f0)          # a render chunk may start partway into a piece
            self.proc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-ss", f"{ss:.4f}", "-i", self.src, "-frames:v", str(n),
                 "-vf", f"fps={FPS},scale={self.sw}:{self.sh}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                stdout=subprocess.PIPE)
            self.cur = k
        raw = self.proc.stdout.read(self.sw * self.sh * 3)
        if len(raw) < self.sw * self.sh * 3:
            return None
        img = Image.frombytes("RGB", (self.sw, self.sh), raw)
        zl = self.level(t)
        cw, ch = self.sw / zl, self.sh / zl
        x0 = min(max(self.cx * self.S - cw / 2, 0), self.sw - cw)
        y0 = min(max(self.cy * self.S - ch / 2, 0), self.sh - ch)
        return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).tobytes()

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc = None


class Clip:
    """A phone clip in a rounded glowing frame (on the plate) or popping in beside Ricky."""

    def __init__(self, e):
        self.e = e
        self.h = e.get("h", 860)
        self.w = round(self.h * 9 / 16) // 2 * 2
        self.anim = Anim(e["t0"], e["t1"], e.get("anim", "pop"))
        fr = Image.new("RGB", (self.w, self.h), (0, 0, 0))
        if e.get("style") == "ab":                            # AB Nasdaq look: clean rounded clip, soft shadow
            import cards_ab
            self.tmpl = cards_ab.shadowed(fr, 28, alpha=90)
        else:
            self.tmpl = B.framed(fr, self.w, self.h, radius=28)   # glow + border + shadow template
        m = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, self.w - 1, self.h - 1), 28, fill=255)
        self.mask = m
        self.proc = None
        self.frame = None

    def _next(self):
        if self.proc is None:
            dur = self.e["t1"] - self.e["t0"] + 0.5
            self.proc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-ss", str(self.e.get("in", 0)), "-t", f"{dur:.3f}", "-i", self.e["file"],
                 "-vf", f"fps={FPS},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        raw = self.proc.stdout.read(self.w * self.h * 3)
        if len(raw) == self.w * self.h * 3:
            self.frame = Image.frombytes("RGB", (self.w, self.h), raw)
        return self.frame

    def draw(self, frame, t):
        fimg = self._next()
        op, sc, dy = self.anim.at(t)
        if fimg is None or op <= 0:
            return
        canvas = self.tmpl.copy()
        pad = (canvas.width - self.w) // 2
        canvas.paste(fimg, (pad, pad), self.mask)
        arr = np.asarray(scaled(canvas, sc))
        h, w = arr.shape[:2]
        blend(frame, arr, int(self.e["cx"] - w / 2), int(self.e["cy"] - h / 2 + dy), op)

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc = None


def main():
    els = json.load(open(sys.argv[1]))
    base_path, ass_path, out_path, total = sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
    start = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0          # optional preview range
    end = float(sys.argv[7]) if len(sys.argv) > 7 else total
    plate = np.asarray(B.plate(), np.float32)
    plates = els.get("plates", [])
    solid = {}
    for p in plates:
        if "rgb" in p and tuple(p["rgb"]) not in solid:
            solid[tuple(p["rgb"])] = np.full((H, W, 3), p["rgb"], np.float32)
    objs = []
    for e in els.get("elements", []):
        cls = {"card": Card, "frame": FrameBase, "clip": Clip, "split": Split, "behind": Behind}[e["type"]]
        objs.append((e["t0"], e["t1"], cls(e)))
    zooms = [Zoom(z, els["keep"], els["zoom_src"]) for z in els.get("zooms", [])]
    n0, n = int(round(start * FPS)), int(round(end * FPS))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-i", base_path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-vf", f"setpts=PTS+{start:.4f}/TB,ass={ass_path},setpts=PTS-STARTPTS,"
                            "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264",
                            # HD colour (BT.709), converted and tagged, so players show the colours as drawn (an untagged
                            # BT.601 encode turns red orange in browsers)
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                            "-preset", "medium", "-crf", "18", "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    fsz = W * H * 3
    last = None
    for i in range(n0, n):
        t = i / FPS
        raw = dec.stdout.read(fsz)
        if len(raw) < fsz:
            raw = last
        last = raw
        for z in zooms:
            if z.z["t0"] <= t < z.z["t1"]:
                zf = z.frame(i, t)
                if zf:
                    a = z.mix(t)
                    if a < 1:
                        zf = (np.frombuffer(zf, np.uint8) * a + np.frombuffer(raw, np.uint8) * (1 - a)).astype(np.uint8).tobytes()
                    raw = zf
            elif t >= z.z["t1"]:
                z.close()
        active = [o for t0, t1, o in objs if t0 <= t < t1]
        pa, pimg = 0.0, plate
        for p in plates:
            if p["t0"] <= t < p["t1"]:
                a = min(clamp((t - p["t0"]) / max(p.get("fade_in", 0.14), 1e-3)), clamp((p["t1"] - t) / max(p.get("fade_out", 0.14), 1e-3)))
                if a > pa:
                    pa, pimg = a, solid.get(tuple(p["rgb"]), plate) if "rgb" in p else plate
        if not active and pa <= 0:
            enc.stdin.write(raw)
            continue
        base = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        frame = base.astype(np.float32)
        for o in active:
            if isinstance(o, Split):
                o.draw(frame, base, t)
        if pa > 0:
            frame = frame * (1 - pa) + pimg * pa
        for o in active:
            if isinstance(o, Split):
                continue
            if isinstance(o, (FrameBase, Behind)):
                o.draw(frame, base, t)
            else:
                o.draw(frame, t)
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        for t0, t1, o in objs:
            if isinstance(o, Clip) and t >= t1:
                o.close()
        if i % 900 == 0:
            print(f"{t:6.1f}s / {total:.1f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.kill()


if __name__ == "__main__":
    main()
