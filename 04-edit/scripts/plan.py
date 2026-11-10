"""Compile Ricky's VSL edit list from the transcript, the pause map and the cue sheet below (all cues in raw-video time).

    python plan.py transcript.json silences.txt edl.json
"""
import json, re, sys

FPS = 30
RAW_END = 385.3
CLIPS = "/home/user/work/gfx/clips"
ACC = "{\\c&HFF70A9&}"
WHT = "{\\c&HFFFFFF&}"
SCREEN_RANGES = [(24.3, 32.7), (207.43, 220.87), (233.73, 260.6)]   # his own screen recordings (facecam bottom right)
NO_CUT = [(200.5, 203.6)]                                           # keep the natural build into the reveal

# ---------------------------------------------------------------- cue sheet (raw time)
TITLES = [  # t0, t1, text, extra
    (5.72, 8.30, "$87.", dict(hl=["$87."], size=230)),
    (67.74, 69.16, "$0.", dict(hl=["$0."], size=230)),
    (95.30, 99.30, "The one place every guru\ntold me NOT to post on.", dict(hl=["NOT"], bg_alpha="40", size=96)),
    (164.10, 165.45, "18,000,000 views", dict(hl=["18,000,000"], bg_alpha="30", size=130)),
    (166.45, 167.98, "$87.", dict(hl=["$87."], size=230)),
    (201.70, 202.10, "", dict(fade_in=60, fade_out=0)),
    (202.10, 203.36, "YouTube Shorts", dict(fade_in=0, size=150, hl=["Shorts"])),
    (318.10, 320.95, "YTD", dict(sub="my 1-on-1 mentorship", size=220, hl=["YTD"])),
]
CARDS = [  # name, t0, t1, extra
    ("shop_11k", 38.45, 42.15, {}),
    ("night_laptop", 61.95, 65.35, {}),
    ("yt_48h_11m", 213.35, 217.25, {}),
    ("playbutton_lv", 220.90, 223.55, {}),
    ("shop_36k", 227.55, 231.00, {}),
    ("shop_today_2k", 231.00, 233.62, {}),
    ("labels_strip", 239.20, 241.30, {}),
    ("yt_sept_91m", 255.58, 256.85, dict(dim=0, hl=0.3)),
    ("yt_sept_60m", 256.85, 258.05, dict(dim=0, hl=0.3)),
    ("yt_sept_44m", 258.05, 259.25, dict(dim=0, hl=0.3)),
    ("playbuttons_4", 259.25, 260.45, dict(dim=0)),
    ("gwagon", 267.00, 270.05, {}),
    ("shop_payout", 323.60, 326.80, {}),
]
DIMS = [(255.50, 260.50, 0.6)]
INSERTS = [  # file, t0, t1, clip in-point, clip audio dB (None = muted)
    ("fs_classroom.mov", 204.50, 206.75, 0.0, None),
    ("fs_live719k.mov", 217.45, 220.88, 0.3, None),
    ("fs_balcony.mov", 263.30, 266.95, 0.0, None),
    ("fs_sub100k.mov", 270.50, 277.00, 0.0, -16),
]
BOXES = [  # t0, t1, box in 1920x1080 pixels
    (24.60, 27.50, (192, 418, 352, 458)),
    (29.30, 32.60, (192, 418, 352, 458)),
    (208.20, 212.90, (778, 345, 960, 395)),
    (241.35, 242.75, (658, 335, 902, 385)),
    (243.60, 247.85, (674, 335, 882, 385)),
    (248.05, 251.55, (646, 335, 902, 385)),
    (252.30, 255.45, (252, 465, 388, 520)),
]
LABELS = [  # t0, t1, text (ASS), style
    (294.08, 299.85, f"{ACC}1{WHT}   A proven product", "Label"),
    (299.90, 307.20, f"{ACC}2{WHT}   A channel. Not a video. Not an ad.", "Label"),
    (307.28, 315.00, f"{ACC}3{WHT}   A brand. Not a one-off winner.", "Label"),
    (326.92, 334.30, f"{ACC}✓{WHT}   Weekly 1-on-1 call with me", "Label"),
    (334.36, 344.20, f"{ACC}✓{WHT}   4 weekly coaching calls", "Label"),
    (344.28, 355.90, f"{ACC}✓{WHT}   My personal phone number, Mon–Fri", "Label"),
    (356.00, 364.30, f"Not live in 60 days? {ACC}I keep working with you for free.", "Label"),
    (364.40, 368.80, "Small group only", "Label"),
    (372.38, 385.30, "Apply below  ↓", "LabelHL"),
]
STEM_DB = {"drone": -17, "pads": -14, "motif": -14, "arp": -16, "heartbeat": -15, "ticks": -10, "hats": -14}
MUSIC = [  # stem, t0, t1, fade in, fade out
    ("drone", 0.0, 5.62, 0.3, 0.08), ("ticks", 0.0, 5.62, 0.2, 0.08),
    ("drone", 8.30, 47.40, 0.8, 1.0), ("ticks", 8.30, 14.30, 0.3, 0.6),
    ("pads", 14.10, 47.60, 2.0, 1.5), ("motif", 14.30, 47.40, 1.0, 1.5),
    ("drone", 47.20, 67.62, 1.0, 0.06), ("heartbeat", 47.30, 67.62, 1.5, 0.06), ("ticks", 52.0, 67.62, 1.0, 0.06),
    ("drone", 69.16, 102.55, 0.6, 0.05), ("pads", 69.16, 81.60, 1.0, 1.5),
    ("ticks", 81.50, 102.55, 1.0, 0.05), ("heartbeat", 84.30, 102.55, 2.0, 0.05),
    ("drone", 102.60, 194.70, 0.3, 1.0), ("pads", 102.60, 194.70, 1.2, 1.2), ("motif", 104.0, 186.6, 1.5, 2.0),
    ("ticks", 186.60, 201.62, 1.5, 0.05), ("drone", 194.70, 201.62, 0.5, 0.05),
    ("drone", 203.30, 277.25, 0.2, 0.3), ("pads", 203.30, 277.25, 0.4, 0.3), ("heartbeat", 203.30, 277.25, 0.2, 0.3),
    ("arp", 203.30, 277.25, 0.6, 0.3), ("hats", 207.30, 277.25, 2.0, 0.3),
    ("drone", 277.30, 294.05, 0.2, 0.3), ("ticks", 277.30, 294.05, 0.3, 0.3),
    ("drone", 294.05, 385.30, 0.3, 2.5), ("pads", 294.05, 385.30, 0.6, 2.5), ("arp", 294.05, 356.0, 1.0, 2.0),
    ("heartbeat", 356.0, 372.30, 1.5, 0.8), ("motif", 372.30, 385.30, 1.0, 2.5),
]
GAPS = [(5.62, 5.74), (67.62, 67.76), (166.40, 166.47), (201.62, 202.10)]
SFX = [  # name, raw time, dB, lead (s before the time)
    ("boom", 5.75, -4, 0), ("boom", 67.78, -5, 0), ("boom", 166.48, -6, 0), ("boom", 202.12, -2, 0), ("boom", 318.60, -9, 0),
    ("reverse_swell", 95.30, -12, 1.8), ("riser", 102.55, -12, 3.0), ("subdrop", 102.62, -7, 0),
    ("riser", 194.30, -13, 3.0), ("subdrop", 277.32, -8, 0), ("riser", 294.05, -13, 3.0), ("riser", 372.30, -15, 3.0),
    ("whoosh_soft", 164.10, -14, 0.15),
]

HL_WORDS = {"million", "youtube", "shorts", "ytd", "free", "zero"}
WEAK = {"a", "an", "the", "to", "of", "my", "your", "in", "on", "at", "for", "and", "but", "that", "was", "were", "i",
        "is", "it", "me", "with", "from", "this", "every", "so", "you", "i'm", "i've", "we", "will", "be", "are"}


def load_words(path):
    words = []
    for seg in json.load(open(path)):
        for w in seg["words"]:
            tok = w["w"].strip()
            if words and (tok.startswith(",") or tok.startswith("-")) and not tok.startswith("--"):
                words[-1]["w"] += tok
                words[-1]["e"] = w["e"]
            else:
                words.append({"w": tok, "s": w["s"], "e": w["e"]})
    return words


def load_cuts(path):
    lines = open(path).read().splitlines()
    starts = [float(l.split(": ")[1]) for l in lines if l.startswith("silence_start")]
    ends = [float(re.search(r"end: ([0-9.]+)", l).group(1)) for l in lines if l.startswith("silence_end")]
    cuts = []
    for s, e in zip(starts, ends):
        if e - s < 0.35 or any(a <= s <= b for a, b in NO_CUT):
            continue
        a, b = round((s + 0.08) * FPS) / FPS, round((e - 0.07) * FPS) / FPS
        if b - a >= 0.15:
            cuts.append((a, b))
    return cuts


def main():
    words = load_words(sys.argv[1])
    cuts = load_cuts(sys.argv[2])
    keep, t = [], 0.0
    for a, b in cuts:
        keep.append((t, a))
        t = b
    keep.append((t, RAW_END))

    def m(x):
        out = 0.0
        for a, b in keep:
            if x <= a:
                return out
            if x < b:
                return out + x - a
            out += b - a
        return out

    total = m(RAW_END)
    edl = {"items": [{"kind": "aroll", "in": a, "out": b} for a, b in keep], "preset": "medium", "duck_db": 5, "music_db": -2}
    title_spans = [(m(a), m(b)) for a, b, txt, ex in TITLES if not ex.get("bg_alpha") or True]
    edl["titles"] = []
    for a, b, txt, ex in TITLES:
        d = {"t0": m(a), "t1": m(b), "text": txt}
        d.update(ex)
        edl["titles"].append(d)
    edl["cards"] = [dict({"name": n, "at": m(a), "dur": m(b) - m(a)}, **ex) for n, a, b, ex in CARDS]
    edl["dims"] = [{"t0": m(a), "t1": m(b), "dim": d} for a, b, d in DIMS]
    edl["inserts"] = [{"file": f"{CLIPS}/{f}", "at": m(a), "dur": m(b) - m(a), "in": i, "audio_db": adb}
                      for f, a, b, i, adb in INSERTS]
    edl["boxes"] = [{"t0": m(a), "t1": m(b), "box": list(bx)} for a, b, bx in BOXES]
    edl["labels"] = [{"t0": m(a), "t1": m(b), "ass": txt, "style": st} for a, b, txt, st in LABELS]
    edl["music"] = [{"stem": s, "t0": m(a), "t1": m(b), "offset": m(a), "db": STEM_DB[s], "fi": fi, "fo": fo}
                    for s, a, b, fi, fo in MUSIC]
    edl["music_gaps"] = [{"t0": m(a), "t1": m(b)} for a, b in GAPS]
    sfx = [{"name": n, "at": m(t), "db": d, "lead": l} for n, t, d, l in SFX]
    for c in CARDS:                        # a soft whoosh as each card lands, a pop when its highlight lands
        sfx.append({"name": "whoosh", "at": m(c[1]), "db": -15 if c[3].get("dim", 1) else -17, "lead": 0.12})
        sfx.append({"name": "pop", "at": m(c[1]) + c[3].get("hl", 0.45), "db": -19})
    for f, a, b, i, adb in INSERTS:
        sfx.append({"name": "whoosh_soft", "at": m(a), "db": -15, "lead": 0.15})
    for a, b, bx in BOXES:
        sfx.append({"name": "pop", "at": m(a), "db": -18})
    edl["sfx"] = sfx
    # end: fade to black over the last half second
    edl["titles"].append({"t0": total - 0.55, "t1": total + 0.1, "text": "", "fade_in": 500, "fade_out": 0})

    # ---------------- captions: 1-3 word groups, break on punctuation and pauses
    hidden = [(m(a), m(b)) for a, b, txt, ex in TITLES]
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        text_len = sum(len(x["w"]) + 1 for x in cur)
        end_punct = w["w"][-1] in ".,?!:;"
        gap = (nxt["s"] - w["e"]) if nxt else 9
        weak_end = w["w"].lower().strip(".,") in WEAK and len(cur) < 4 and text_len < 20
        if not nxt or end_punct or gap > 0.45 or ((len(cur) >= 3 or text_len > 15) and not weak_end):
            groups.append(cur)
            cur = []
    caps = []
    for gi, g in enumerate(groups):
        t0 = m(g[0]["s"])
        t1 = m(groups[gi + 1][0]["s"]) if gi + 1 < len(groups) else m(g[-1]["e"]) + 0.3
        if t1 - m(g[-1]["e"]) > 0.6:
            t1 = m(g[-1]["e"]) + 0.25
        mid = (t0 + min(t1, m(g[-1]["e"]))) / 2
        if any(a - 0.05 <= mid <= b + 0.05 for a, b in hidden):
            continue
        toks = []
        for w in g:
            tok = w["w"].strip(".,!;:\"")
            if tok.lower() in ("i'm", "i'll", "i've", "i"):
                tok = tok[0].upper() + tok[1:]
            key = tok.lower().strip("'")
            if re.search(r"[0-9$]", tok) or key in HL_WORDS:
                toks.append(ACC + tok + WHT)
            else:
                toks.append(tok)
        raw_mid = g[0]["s"]
        style = "CapL" if any(a <= raw_mid <= b for a, b in SCREEN_RANGES) else "Cap"
        caps.append({"t0": t0, "t1": t1, "ass": " ".join(toks), "style": style})
    for c in caps:                         # don't let a caption run into a title
        for a, b in hidden:
            if c["t0"] < a < c["t1"]:
                c["t1"] = a
    edl["captions"] = caps
    json.dump(edl, open(sys.argv[3], "w"), indent=1, ensure_ascii=False)
    print(f"cuts {len(cuts)} ({sum(b - a for a, b in cuts):.1f}s removed) -> {total:.1f}s; captions {len(caps)}; "
          f"cards {len(CARDS)}; titles {len(TITLES)}; inserts {len(INSERTS)}; boxes {len(BOXES)}; sfx {len(sfx)}")


if __name__ == "__main__":
    main()
