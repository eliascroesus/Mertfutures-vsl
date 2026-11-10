"""Render the VSL from an edit decision list (JSON).

    python render.py edl.json out.mp4 [--preview SECONDS]

Layers, bottom to top: base timeline (A-roll cuts + full clips), full-screen inserts, dims and title backgrounds (ASS),
results cards, card highlights, captions and titles (ASS). Audio is mixed in numpy: processed voice, clip audio,
music stems with fades and ducking under the voice, sound effects; then loudness-normalised to -14 LUFS.
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf

FPS = 30
SR = 48000
W, H = 1920, 1080
WORK = "/home/user/work"
PROXY = f"{WORK}/edit/proxy1080.mp4"
VOICE = f"{WORK}/edit/voice_proc.wav"
CARDS = f"{WORK}/gfx/cards"
MUSIC = __import__("os").environ.get("VSL_MUSIC", "/home/user/work/music")
ACCENT_ASS = "&HFF70A9&"           # (169, 112, 255) in ASS BGR
CARD_META = json.load(open(f"{CARDS}/cards.json"))


def fr(t):
    return round(t * FPS) / FPS


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:])
        raise SystemExit(f"command failed: {cmd[:6]}")
    return r


def load_audio(path, ss=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-i", path]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def db(x):
    return 10 ** (x / 20)


# ------------------------------------------------------------------ timeline
def build_timeline(edl):
    """Resolve items to output times. Returns list of dicts with out_t0/out_t1."""
    t = 0.0
    out = []
    for it in edl["items"]:
        it = dict(it)
        it["in"], it["out"] = fr(it["in"]), fr(it["out"])
        d = it["out"] - it["in"]
        it["t0"], it["t1"] = t, t + d
        t += d
        out.append(it)
    return out, t


def render_base(items, path):
    # one input per segment (seeked on input): sharing one input across many trims makes ffmpeg buffer every frame
    inputs, chains, labels = [], [], []
    for i, it in enumerate(items):
        src = PROXY if it["kind"] == "aroll" else it["file"]
        nframes = round((it["out"] - it["in"]) * FPS)
        inputs += ["-ss", f"{it['in']:.4f}", "-i", src]
        chains.append(f"[{i}:v]fps={FPS},trim=end_frame={nframes},setpts=PTS-STARTPTS,"
                      f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,format=yuv420p[s{i}]")
        labels.append(f"[s{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + f"concat=n={len(items)}:v=1:a=0[v]"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[v]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-g", "30", path])


# ------------------------------------------------------------------ ASS
def ass_time(t):
    t = max(0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,-1,0,1,0,3,2,120,120,{capv},1
Style: Title,Inter Display,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-1.5,0,1,0,0,5,160,160,0,1
Style: Small,Inter Display,40,&H00B4B4B4,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,160,160,0,1
Style: Box,Inter,10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: CapL,Inter Display,62,&H00FFFFFF,&H00FFFFFF,&H30000000,&H00000000,-1,0,0,0,100,100,-1,0,3,14,0,1,150,120,{capv},1
Style: Label,Inter Display,58,&H00FFFFFF,&H00FFFFFF,&H38000000,&H00000000,-1,0,0,0,100,100,-0.5,0,3,18,0,8,120,120,64,1
Style: LabelHL,Inter Display,62,&H00FFFFFF,&H00FFFFFF,&H00FF70A9,&H00000000,-1,0,0,0,100,100,-0.5,0,3,20,0,8,120,120,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
RECT = r"{\p1}m 0 0 l 1920 0 1920 1080 0 1080{\p0}"


def caption_text(text, hl):
    words = []
    for w in text.split(" "):
        bare = w.strip(".,!?:;\"'").lower()
        if any(bare == h.lower() or w.lower().startswith(h.lower()) for h in hl):
            words.append("{\\c" + ACCENT_ASS + "}" + w + "{\\c&HFFFFFF&}")
        else:
            words.append(w)
    return " ".join(words)


def write_ass(edl, bg_path, top_path, total):
    bg, top = [ASS_HEAD.format(capv=edl.get("caption_margin", 95))], [ASS_HEAD.format(capv=edl.get("caption_margin", 95))]
    for c in edl.get("cards", []) + [dict(d, at=d["t0"], dur=d["t1"] - d["t0"]) for d in edl.get("dims", [])]:
        a = c.get("dim", 0.55)
        if a <= 0:
            continue
        alpha = format(int(255 * (1 - a)), "02X")
        bg.append(f"Dialogue: 0,{ass_time(c['at'])},{ass_time(c['at'] + c['dur'])},Box,,0,0,0,,"
                  f"{{\\an7\\pos(0,0)\\c&H000000&\\1a&H{alpha}&\\fad(180,180)}}{RECT}")
    for ti in edl.get("titles", []):
        if ti.get("bg", True):
            bg.append(f"Dialogue: 0,{ass_time(ti['t0'])},{ass_time(ti['t1'])},Box,,0,0,0,,"
                      f"{{\\an7\\pos(0,0)\\c&H0A0A0A&\\1a&H{ti.get('bg_alpha', '00')}&\\fad({ti.get('fade_in', 120)},{ti.get('fade_out', 120)})}}{RECT}")
        if not ti["text"]:
            continue
        txt = ti["text"].replace("\n", "\\N")
        for h in ti.get("hl", []):
            txt = txt.replace(h, "{\\c" + ACCENT_ASS + "}" + h + "{\\c&HFFFFFF&}")
        y = ti.get("y", 540)
        size = ti.get("size", 84)
        top.append(f"Dialogue: 2,{ass_time(ti['t0'])},{ass_time(ti['t1'])},Title,,0,0,0,,"
                   f"{{\\pos(960,{y})\\fs{size}\\fsp{-size / 60:.1f}\\fad({ti.get('fade_in', 120) + 80},{ti.get('fade_out', 120)})\\blur0.6"
                   f"\\t(0,350,\\fscx100\\fscy100)\\fscx96\\fscy96}}{txt}")
        if ti.get("sub"):
            top.append(f"Dialogue: 2,{ass_time(ti['t0'] + 0.25)},{ass_time(ti['t1'])},Small,,0,0,0,,"
                       f"{{\\pos(960,{y + int(size * 0.55) + 40})\\fs54\\fad(200,{ti.get('fade_out', 120)})}}{ti['sub']}")
    for c in edl.get("captions", []):
        txt = c["ass"] if "ass" in c else caption_text(c["text"], c.get("hl", []))
        top.append(f"Dialogue: 1,{ass_time(c['t0'])},{ass_time(c['t1'])},{c.get('style', 'Cap')},,0,0,0,,"
                   f"{{\\fad(50,0)\\fscx94\\fscy94\\t(0,90,\\fscx100\\fscy100)}}{txt}")
    for lb in edl.get("labels", []):
        top.append(f"Dialogue: 3,{ass_time(lb['t0'])},{ass_time(lb['t1'])},{lb.get('style', 'Label')},,0,0,0,,"
                   f"{{\\fad(160,160)\\fscx92\\fscy92\\t(0,160,\\fscx100\\fscy100)}}{lb['ass']}")
    for b in edl.get("boxes", []):
        x0, y0, x1, y1 = b["box"]
        r = 12
        path = (f"m {x0 + r} {y0} l {x1 - r} {y0} b {x1} {y0} {x1} {y0} {x1} {y0 + r} l {x1} {y1 - r} b {x1} {y1} {x1} {y1} {x1 - r} {y1} "
                f"l {x0 + r} {y1} b {x0} {y1} {x0} {y1} {x0} {y1 - r} l {x0} {y0 + r} b {x0} {y0} {x0} {y0} {x0 + r} {y0}")
        for lay, extra in ((4, "\\bord9\\blur9\\3a&H60&"), (5, "\\bord4\\blur0.6")):
            top.append(f"Dialogue: {lay},{ass_time(b['t0'])},{ass_time(b['t1'])},Box,,0,0,0,,"
                       f"{{\\an7\\pos(0,0)\\1a&HFF&\\3c{ACCENT_ASS}{extra}\\shad0\\fad(120,150)}}{{\\p1}}{path}{{\\p0}}")
    open(bg_path, "w").write("\n".join(bg) + "\n")
    open(top_path, "w").write("\n".join(top) + "\n")


# ------------------------------------------------------------------ overlays
def render_overlays(edl, base, bg_ass, top_ass, path, total):
    inputs = ["-i", base]
    graph = []
    cur = "[0:v]"
    n = 1
    for k, ins in enumerate(edl.get("inserts", [])):
        inputs += ["-ss", str(ins.get("in", 0)), "-t", str(ins["dur"]), "-i", ins["file"]]
        graph.append(f"[{n}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuva420p,"
                     f"fade=in:st=0:d=0.12:alpha=1,fade=out:st={ins['dur'] - 0.12:.3f}:d=0.12:alpha=1,"
                     f"setpts=PTS-STARTPTS+{ins['at']:.3f}/TB[ins{k}]")
        graph.append(f"{cur}[ins{k}]overlay=0:0:eof_action=pass:enable='between(t,{ins['at']:.3f},{ins['at'] + ins['dur']:.3f})'[i{k}]")
        cur = f"[i{k}]"
        n += 1
    graph.append(f"{cur}ass={bg_ass}[bgl]")
    cur = "[bgl]"
    for k, c in enumerate(edl.get("cards", [])):
        m = CARD_META[c["name"]]
        s = min(1.0, c.get("maxh", 760) / m["card_h"], c.get("maxw", 1500) / m["card_w"])
        w, h = int(m["w"] * s) // 2 * 2, int(m["h"] * s) // 2 * 2
        x = int(c.get("cx", 960) - w / 2)
        y = int(c.get("cy", 470) - h / 2)
        at, dur = c["at"], c["dur"]
        for layer, fname in (("c", f"card_{c['name']}.png"), ("h", f"hl_{c['name']}.png")):
            if layer == "h" and not m["has_highlight"]:
                continue
            delay = 0 if layer == "c" else c.get("hl", 0.45)
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", f"{CARDS}/{fname}"]
            fin = 0.22 if layer == "c" else 0.12
            graph.append(f"[{n}:v]format=rgba,scale={w}:{h},fade=in:st={delay:.3f}:d={fin}:alpha=1,"
                         f"fade=out:st={dur - 0.18:.3f}:d=0.18:alpha=1,setpts=PTS-STARTPTS+{at:.3f}/TB[{layer}{k}]")
            ey = f"{y}+36*pow(max(0,1-(t-{at:.3f})/0.32),2)"
            graph.append(f"{cur}[{layer}{k}]overlay=x={x}:y='{ey}':eof_action=pass:enable='between(t,{at:.3f},{at + dur:.3f})'[o{layer}{k}]")
            cur = f"[o{layer}{k}]"
            n += 1
    graph.append(f"{cur}ass={top_ass},format=yuv420p[v]")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(graph), "-map", "[v]",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", edl.get("preset", "medium"), "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", path])


# ------------------------------------------------------------------ audio
def envelope(x, attack=0.02, release=0.35):
    mono = np.abs(x).mean(1)
    hop = 240
    n = len(mono) // hop
    rms = np.sqrt((mono[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    out = np.zeros(n)
    a, r = np.exp(-hop / (SR * attack)), np.exp(-hop / (SR * release))
    v = 0.0
    for i, e in enumerate(rms):
        v = a * v + (1 - a) * e if e > v else r * v + (1 - r) * e
        out[i] = v
    full = np.repeat(out, hop) if n else np.zeros(0)
    return np.pad(full, (0, max(0, len(x) - len(full))), mode="edge" if len(full) else "constant")[: len(x)]


def place(buf, x, at):
    s = int(round(at * SR))
    if s >= len(buf):
        return
    if s < 0:
        x, s = x[-s:], 0
    n = min(len(x), len(buf) - s)
    buf[s:s + n] += x[:n]


def mix_audio(edl, items, total, path):
    n = int(total * SR) + SR
    voice = np.zeros((n, 2))
    vsrc = load_audio(VOICE)
    fade = int(0.008 * SR)
    for it in items:
        if it["kind"] == "aroll":
            seg = vsrc[int(it["in"] * SR):int(it["out"] * SR)].copy()
            g = db(it.get("voice_db", 0))
        else:
            seg = load_audio(it["file"], it["in"], it["out"] - it["in"])
            g = db(it.get("audio_db", -120))
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade)[:, None]
            seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        place(voice, seg * g, it["t0"])
    for ins in edl.get("inserts", []):
        if ins.get("audio_db") is not None:
            place(voice, load_audio(ins["file"], ins.get("in", 0), ins["dur"]) * db(ins["audio_db"]), ins["at"])
    music = np.zeros((n, 2))
    stems = {}
    for m in edl.get("music", []):
        if m["stem"] not in stems:
            stems[m["stem"]], _ = sf.read(f"{MUSIC}/stem_{m['stem']}.wav", dtype="float32")
        st = stems[m["stem"]]
        off = m.get("offset", m["t0"])                     # where in the stem to start (keeps stems in sync)
        a, b = int(off * SR), int((off + m["t1"] - m["t0"]) * SR)
        seg = st[a:b].astype(np.float64) * db(m.get("db", 0))
        fi, fo = int(m.get("fi", 1.0) * SR), int(m.get("fo", 1.0) * SR)
        if fi:
            seg[:fi] *= (np.linspace(0, 1, fi) ** 2)[:, None]
        if fo:
            seg[-fo:] *= (np.linspace(1, 0, fo) ** 2)[:, None]
        place(music, seg, m["t0"])
    for g in edl.get("music_gaps", []):              # hard drop-outs ("silence hits") before a big line
        a, b = int(g["t0"] * SR), int(g["t1"] * SR)
        ramp = int(0.04 * SR)
        music[a:b] = 0
        music[a - ramp:a] *= np.linspace(1, 0, ramp)[:, None]
        music[b:b + ramp] *= np.linspace(0, 1, ramp)[:, None]
    duck = edl.get("duck_db", 6)
    env = envelope(voice)
    thr = db(-38)
    amount = np.clip((env - thr) / (db(-24) - thr), 0, 1)
    music *= db(-duck * amount)[:, None]
    sfx = np.zeros((n, 2))
    cache = {}
    for s in edl.get("sfx", []):
        if s["name"] not in cache:
            cache[s["name"]], _ = sf.read(f"{MUSIC}/sfx/{s['name']}.wav", dtype="float32")
        place(sfx, cache[s["name"]].astype(np.float64) * db(s.get("db", -10)), s["at"] - s.get("lead", 0))
    mix = voice + music * db(edl.get("music_db", 0)) + sfx * db(edl.get("sfx_db", 0))
    mix = mix[: int(total * SR)]
    sf.write(path + ".pre.wav", mix.astype(np.float32), SR, subtype="FLOAT")
    r = run(["ffmpeg", "-v", "info", "-hide_banner", "-i", path + ".pre.wav", "-af",
             "loudnorm=I=-14:TP=-1.2:LRA=9:print_format=json", "-f", "null", "-"])
    st = json.loads(r.stderr[r.stderr.rindex("{"):])
    run(["ffmpeg", "-y", "-v", "error", "-i", path + ".pre.wav", "-af",
         f"loudnorm=I=-14:TP=-1.2:LRA=9:measured_I={st['input_i']}:measured_TP={st['input_tp']}:"
         f"measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']}:linear=true",
         "-ar", str(SR), "-c:a", "pcm_s24le", path])


def main():
    edl_path, out = sys.argv[1], sys.argv[2]
    edl = json.load(open(edl_path))
    tmp = os.path.splitext(out)[0]
    items, total = build_timeline(edl)
    if "--preview" in sys.argv:
        total = min(total, float(sys.argv[sys.argv.index("--preview") + 1]))
    print(f"timeline {total:.2f}s, {len(items)} items")
    if "--audio-only" not in sys.argv:
        if not ("--reuse-base" in sys.argv and os.path.exists(tmp + "_base.mp4")):
            render_base(items, tmp + "_base.mp4")
        write_ass(edl, tmp + "_bg.ass", tmp + "_top.ass", total)
        render_overlays(edl, tmp + "_base.mp4", tmp + "_bg.ass", tmp + "_top.ass", tmp + "_video.mp4", total)
    mix_audio(edl, items, total, tmp + "_mix.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", tmp + "_video.mp4", "-i", tmp + "_mix.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out])
    print("done", out)


if __name__ == "__main__":
    main()
