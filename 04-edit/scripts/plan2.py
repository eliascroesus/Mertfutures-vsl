"""Version 2 of Ricky's VSL edit: Iman-style title cards, headlines over A-roll, results popping in on the brand plate,
screen recordings in glowing frames, photo stickers beside Ricky. All cue times are raw-video seconds.

    python plan2.py transcript.json silences.txt OUTDIR
writes OUTDIR/edl2.json (audio + timeline), OUTDIR/elements.json (compositor), OUTDIR/text.ass (all text).
"""
import json, os, re, sys
from fontTools.ttLib import TTFont
from PIL import ImageFont

sys.path.insert(0, "/home/user/work/scripts")
import brand as B
import cards2 as C2
import plan as P1                      # pause cutting, word loading, caption grouping rules

CLIPDIR = "/home/user/rickyvsl-clips/02-results-and-b-roll"
FONTS = os.path.expanduser("~/.local/share/fonts")
PU = B.PURPLE_ASS
PS = B.PURPLE_SOFT_ASS

# ---------------------------------------------------------------- cue sheet (raw seconds)
# Title cards on the plate. (t0, t1, lines, sub, script)  lines: list of [(text, color), ...] per line, with size
TITLES = [
    dict(t0=5.72, t1=8.30, lines=[[("$87.", PU)]], size=250, sub="IN SALES.", boom=True),
    dict(t0=67.74, t1=69.16, lines=[[("$0.", PU)]], size=250, sub="AFTER A MILLION VIEWS.", boom=True),
    dict(t0=95.30, t1=99.30, lines=[[("THE ONE PLACE EVERY GURU", None)], [("TOLD ME ", None), ("NOT", PU), (" TO POST ON.", None)]],
         size=96, underline="NOT", swell=True),
    dict(t0=126.85, t1=131.20, lines=[[("I QUIT.", None)]], size=220, script="with $457 to my name", boom=True),
    dict(t0=164.10, t1=165.45, lines=[[("18,000,000", PU)]], size=170, sub="VIEWS."),
    dict(t0=166.45, t1=167.98, lines=[[("$87.", PU)]], size=250, sub="IN SALES.", boom=True),
    dict(t0=201.70, t1=202.10, lines=[], size=10),
    dict(t0=202.10, t1=203.36, lines=[[("YOUTUBE", None)], [("SHORTS.", PU)]], size=190, boom=True, fade_in=0),
    dict(t0=277.30, t1=279.50, lines=[[("WHAT MOST PEOPLE", None)], [("DON'T ", PU), ("UNDERSTAND.", None)]], size=86, underline="DON'T"),
    dict(t0=294.08, t1=296.40, lines=[[("01", PU)]], size=200, sub="A PROVEN PRODUCT."),
    dict(t0=299.90, t1=302.20, lines=[[("02", PU)]], size=200, sub="A CHANNEL. NOT A VIDEO."),
    dict(t0=307.28, t1=309.70, lines=[[("03", PU)]], size=200, sub="A BRAND. NOT A ONE-OFF WINNER."),
    dict(t0=318.10, t1=320.95, lines=[[("YTD", PU)]], size=260, sub="MY 1-ON-1 MENTORSHIP.", boom=True),
    dict(t0=326.92, t1=329.30, lines=[[("WEEKLY", None)], [("1-ON-1 CALL", PU)]], size=120, sub="WITH ME. EVERY WEEK."),
    dict(t0=334.36, t1=336.70, lines=[[("4 WEEKLY", None)], [("COACHING CALLS", PU)]], size=110),
    dict(t0=344.28, t1=347.60, lines=[[("MY PERSONAL", None)], [("PHONE NUMBER", PU)]], size=110, sub="MON-FRI. NOT AN ASSISTANT."),
    dict(t0=360.30, t1=364.15, lines=[[("60 DAYS", PU)]], size=210, sub="OR I KEEP WORKING WITH YOU FOR FREE."),
]
STEPS = (315.00, 318.10, ["PRODUCT", "CHANNEL", "BRAND"])
# Headlines over A-roll (lower third) with an optional handwritten sub-line; captions hide while they show.
HEADS = [
    (0.30, 3.58, "18 MILLION VIEWS", "in one month", None),
    (14.40, 19.30, "3 SIMPLE THINGS", "same products. no ads.", None),
    (20.30, 24.00, "$10,000 IN 3 DAYS", None, "$10,000"),
    (74.60, 76.30, "THE TRUTH? YOU DON'T.", "you don't need ads", "YOU DON'T."),
    (80.15, 81.58, "IT'S NOT YOUR FAULT.", None, None),
    (81.62, 84.10, "THE PROBLEM IS THE PLATFORM.", None, "PLATFORM."),
    (105.90, 108.00, "$16 / HOUR", "dining server", "$16"),
    (120.20, 121.58, "I CAN'T DO THIS ANYMORE.", None, None),
    (140.20, 142.95, "“BRO, YOU'RE FALLING\nFOR THE TIKTOK SCAMS.”", "my friends", None),
    (145.20, 149.95, "$1,500 MENTOR.", "worst advice ever", "$1,500"),
    (157.20, 162.20, "40 PRODUCTS.", "a couple hundred bucks", "40"),
    (171.10, 173.60, "“RICKY, I DON'T THINK YOU\nSHOULD BE DOING THIS.”", "my mom", None),
    (182.00, 183.25, "AND I DID.", None, None),
    (188.60, 194.30, "DON'T CLICK OFF.", "what happened next is why I made this video", None),
    (224.50, 227.35, "YOUTUBE STORE.", "where you can tag your products", "YOUTUBE STORE."),
    (366.10, 368.70, "SMALL GROUP ONLY.", None, None),
    (372.38, 376.20, "APPLY BELOW ↓", "the application is down below", "APPLY BELOW ↓"),
]
# Results on the plate: (name, t0, t1, max_w, max_h, tilt)
PLATE_CARDS = [
    ("shop_11k", 38.45, 42.15, 1150, 720, 6),
    ("night_laptop", 61.95, 65.35, 760, 760, -5),
    ("yt_48h_11m", 213.35, 217.25, 900, 760, 5),
    ("shop_36k", 227.55, 231.00, 1150, 740, -5),
    ("shop_today_2k", 231.00, 233.62, 1050, 740, 5),
    ("yt_sept_91m", 255.58, 256.85, 1300, 720, 0),
    ("yt_sept_60m", 256.85, 258.05, 1400, 600, 0),
    ("yt_sept_44m", 258.05, 259.25, 1400, 600, 0),
    ("playbuttons_4", 259.25, 260.45, 700, 760, 4),
    ("shop_payout", 323.60, 326.80, 900, 760, -5),
]
# Photos popping up beside Ricky: (name, t0, t1, cx, cy, rotation)
STICKERS = [
    ("playbutton_lv", 220.90, 223.55, 1470, 470, -4),
    ("labels_strip", 239.20, 241.30, 1480, 500, 4),
    ("gwagon", 267.00, 270.05, 1470, 470, 3),
]
# Phone clips: (file, t0, t1, in, mode, audio dB)
CLIPS = [
    ("IMG_5163.MOV", 204.50, 206.75, 0.0, "plate", None),
    ("copy_6653ECDF-BC6B-47EA-9EEE-A6560D228956.mov", 217.45, 220.88, 0.3, "plate", None),
    ("IMG_3996.MOV", 263.30, 266.95, 0.0, "pop", None),
    ("IMG_8117.mov", 270.50, 277.00, 3.0, "plate", -16),
]
# His screen recordings shown in a glowing frame on the plate, with number outlines (box coords in the raw frame)
FRAMES = [
    (24.30, 32.70, [(24.60, 27.50, (192, 418, 352, 458)), (29.30, 32.60, (192, 418, 352, 458))]),
    (207.43, 213.35, [(208.20, 212.90, (778, 345, 960, 395))]),
    (233.73, 255.58, [(241.35, 242.75, (658, 335, 902, 385)), (243.60, 247.85, (674, 335, 882, 385)),
                      (248.05, 251.55, (646, 335, 902, 385)), (252.30, 255.45, (252, 465, 388, 520))]),
]
LABELS = [  # small top labels that stay after each quick card
    (296.40, 299.85, "01  A PROVEN PRODUCT"),
    (302.20, 307.20, "02  A CHANNEL. NOT A VIDEO."),
    (309.70, 315.00, "03  A BRAND. NOT A ONE-OFF WINNER."),
    (329.30, 334.30, "WEEKLY 1-ON-1 CALL WITH ME"),
    (336.70, 344.20, "4 WEEKLY COACHING CALLS"),
    (347.60, 355.90, "MY PERSONAL PHONE NUMBER"),
    (376.20, 385.30, "APPLY BELOW ↓"),
]


# ---------------------------------------------------------------- text measurement (to place underlines)
class Measure:
    def __init__(self):
        self.fonts = {}

    def width(self, text, family_file, ass_size, spacing=0):
        f = TTFont(family_file)
        k = f["head"].unitsPerEm / (f["OS/2"].usWinAscent + f["OS/2"].usWinDescent)   # libass sizes fonts by win metrics
        key = (family_file, ass_size)
        if key not in self.fonts:
            self.fonts[key] = ImageFont.truetype(family_file, max(1, round(ass_size * k)))
        return self.fonts[key].getlength(text) + spacing * max(0, len(text) - 1)


M = Measure()
UNB_XB = f"{FONTS}/Unbounded-800.ttf"
UNB_SB = f"{FONTS}/Unbounded-600.ttf"

STYLES = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,-0.5,0,1,0,3,2,140,140,70,1
Style: Big,Unbounded ExtraBold,200,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Sub,Unbounded SemiBold,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,7,0,1,0,0,5,0,0,0,1
Style: Head,Unbounded ExtraBold,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,0,0,0,100,100,1,0,1,0,5,5,0,0,0,1
Style: Script,Caveat,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,0,3,5,0,0,0,1
Style: Mark,Unbounded Bold,24,&H70FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,6,0,1,0,0,2,0,0,44,1
Style: Label,Unbounded SemiBold,30,&H00FFFFFF,&H00FFFFFF,&H50000000,&H00000000,0,0,0,0,100,100,3,0,3,16,0,8,120,120,56,1
Style: Box,Inter,10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def at(t):
    return P1_ass_time(t)


def P1_ass_time(t):
    t = max(0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ev(layer, t0, t1, style, text):
    return f"Dialogue: {layer},{at(t0)},{at(t1)},{style},,0,0,0,,{text}"


def main():
    transcript, silences, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    words = P1.load_words(transcript)
    cuts = P1.load_cuts(silences)
    keep, t = [], 0.0
    for a, b in cuts:
        keep.append((t, a))
        t = b
    keep.append((t, P1.RAW_END))

    def m(x):
        out = 0.0
        for a, b in keep:
            if x <= a:
                return out
            if x < b:
                return out + x - a
            out += b - a
        return out

    total = m(P1.RAW_END)
    events, plates, elements, sfx = [], [], [], []

    # ---- title cards on the plate
    hide = []                                           # spans where captions are hidden
    for T in TITLES:
        t0, t1 = m(T["t0"]), m(T["t1"])
        plates.append({"t0": t0, "t1": t1, "fade_in": 0.0 if T.get("fade_in") == 0 else 0.12, "fade_out": 0.12})
        hide.append((t0, t1))
        if not T["lines"]:
            continue
        size = T["size"]
        n = len(T["lines"])
        lh = size * 1.08
        extra = (60 if T.get("sub") else 0) + (70 if T.get("script") else 0)
        y0 = 540 - (n * lh + extra) / 2 + lh / 2 - 10
        clock = 0
        for li, parts in enumerate(T["lines"]):
            y = y0 + li * lh
            txt, nchar = B.ass_rich_reveal(parts, start_ms=clock, stagger=max(18, 60 - len("".join(p for p, _ in parts)) * 2), dur=320, blur=16)
            events.append(ev(3, t0, t1, "Big", f"{{\\pos(960,{y:.0f})\\fs{size}\\fad(0,120)}}{txt}"))
            if T.get("underline"):
                full = "".join(p for p, _ in parts)
                if T["underline"] in full:
                    pre = full[:full.index(T["underline"])]
                    wfull = M.width(full, UNB_XB, size)
                    x_start = 960 - wfull / 2 + M.width(pre, UNB_XB, size)
                    x_end = x_start + M.width(T["underline"].strip(), UNB_XB, size)
                    events.append(ev(3, t0, t1, "Box", B.ass_underline(int(x_start), int(x_end), int(y + size * 0.42), 650)))
            clock += 220
        ybot = y0 + (n - 1) * lh + size * 0.55
        if T.get("sub"):
            events.append(ev(3, t0, t1, "Sub", f"{{\\pos(960,{ybot + 48:.0f})\\fad(0,120)}}" + B.ass_reveal(T["sub"], clock + 150, 22, 280, 10)))
        if T.get("script"):
            events.append(ev(3, t0, t1, "Script", f"{{\\pos(960,{ybot + 60:.0f})\\c{PS}\\fad(0,120)}}" + B.ass_reveal(T["script"], clock + 200, 16, 260, 8)))
        events.append(ev(3, t0, t1, "Mark", "{\\fad(200,120)}YTD"))
        sfx.append({"name": "whoosh_soft", "at": t0, "db": -16, "lead": 0.2})
        if T.get("boom"):
            sfx.append({"name": "boom", "at": t0 + 0.02, "db": -5})

    # ---- steps recap
    s0, s1, names = STEPS
    t0, t1 = m(s0), m(s1)
    plates.append({"t0": t0, "t1": t1})
    hide.append((t0, t1))
    xs = [460, 960, 1460]
    for i, (x, name) in enumerate(zip(xs, names)):
        d = 150 + i * 420
        events.append(ev(3, t0, t1, "Big", f"{{\\pos({x},470)\\fs120\\fad(0,120)}}" + B.ass_reveal(f"0{i + 1}", d, 60, 300, 14, PU)))
        events.append(ev(3, t0, t1, "Sub", f"{{\\pos({x},590)\\fs40\\fad(0,120)}}" + B.ass_reveal(name, d + 160, 30, 280, 10)))
        if i < 2:
            events.append(ev(3, t0, t1, "Box", B.ass_underline(x + 110, x + 390, 468, d + 260, 380, 4)))
    events.append(ev(3, t0, t1, "Mark", "{\\fad(200,120)}YTD"))
    sfx.append({"name": "whoosh_soft", "at": t0, "db": -16, "lead": 0.2})

    # ---- headlines over A-roll
    for h0, h1, text, script, accent in HEADS:
        t0, t1 = m(h0), m(h1)
        hide.append((t0, t1))
        lines = text.split("\n")
        size = 84 if max(len(l) for l in lines) <= 18 else 70
        ybase = 840 if len(lines) == 1 else 790
        clock = 0
        for li, line in enumerate(lines):
            parts = [(line, None)]
            if accent and accent in line:
                i = line.index(accent)
                parts = [(line[:i], None), (accent, PU), (line[i + len(accent):], None)]
            txt, nchar = B.ass_rich_reveal([p for p in parts if p[0]], start_ms=clock, stagger=26, dur=300, blur=14)
            events.append(ev(4, t0, t1, "Head", f"{{\\pos(960,{ybase + li * size * 1.12:.0f})\\fs{size}\\fad(0,150)}}{txt}"))
            clock += nchar * 26
        if script:
            y = ybase + (len(lines) - 1) * size * 1.12 + 84
            events.append(ev(4, t0, t1, "Script", f"{{\\pos(960,{y:.0f})\\c{PS}\\fad(0,150)}}" + B.ass_reveal(script, clock + 120, 14, 260, 8)))
        sfx.append({"name": "whoosh_soft", "at": t0, "db": -20, "lead": 0.15})

    # ---- results on the plate
    for name, a, b, mw, mh, tilt in PLATE_CARDS:
        t0, t1 = m(a), m(b)
        p, ph = C2.card(name, mw, mh, tilt)
        plates.append({"t0": t0, "t1": t1})
        elements.append({"type": "card", "img": p, "hl_img": ph, "t0": t0, "t1": t1, "cx": 960, "cy": 500, "hl_delay": 0.55})
        sfx.append({"name": "whoosh", "at": t0, "db": -15, "lead": 0.12})
        if ph:
            sfx.append({"name": "pop", "at": t0 + 0.55, "db": -18})
    for name, a, b, cx, cy, rot in STICKERS:
        t0, t1 = m(a), m(b)
        elements.append({"type": "card", "img": C2.sticker(name, 520, 560, rot), "t0": t0, "t1": t1, "cx": cx, "cy": cy, "anim": "sticker"})
        sfx.append({"name": "pop", "at": t0 + 0.05, "db": -14})
        sfx.append({"name": "whoosh", "at": t0, "db": -18, "lead": 0.1})
    audio_inserts = []
    for fn, a, b, cin, mode, adb in CLIPS:
        t0, t1 = m(a), m(b)
        if mode == "plate":
            plates.append({"t0": t0, "t1": t1})
            elements.append({"type": "clip", "file": f"{CLIPDIR}/{fn}", "in": cin, "t0": t0, "t1": t1, "h": 860, "cx": 960, "cy": 500})
        else:
            elements.append({"type": "clip", "file": f"{CLIPDIR}/{fn}", "in": cin, "t0": t0, "t1": t1, "h": 620, "cx": 1470, "cy": 470, "anim": "sticker"})
        if adb is not None:
            audio_inserts.append({"file": f"{CLIPDIR}/{fn}", "at": t0, "dur": t1 - t0, "in": cin, "audio_db": adb})
        sfx.append({"name": "whoosh", "at": t0, "db": -15, "lead": 0.12})
    for a, b, boxes in FRAMES:
        t0, t1 = m(a), m(b)
        plates.append({"t0": t0, "t1": t1})
        elements.append({"type": "frame", "t0": t0, "t1": t1, "scale": 0.8, "cx": 960, "cy": 488,
                         "boxes": [{"t0": m(x), "t1": m(y), "box": list(bx)} for x, y, bx in boxes]})
        sfx.append({"name": "whoosh_soft", "at": t0, "db": -17, "lead": 0.15})
        for x, y, bx in boxes:
            sfx.append({"name": "pop", "at": m(x), "db": -18})
    for a, b, text in LABELS:
        events.append(ev(2, m(a), m(b), "Label", "{\\fad(160,160)}" + text.replace("↓", "{\\fnInter Display}↓{\\fnUnbounded SemiBold}")))

    # ---- captions (2-4 word groups), hidden under titles and headlines
    caps = []
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        text_len = sum(len(x["w"]) + 1 for x in cur)
        end_punct = w["w"][-1] in ".,?!:;"
        gap = (nxt["s"] - w["e"]) if nxt else 9
        weak_end = w["w"].lower().strip(".,") in P1.WEAK and len(cur) < 4 and text_len < 20
        if not nxt or end_punct or gap > 0.45 or ((len(cur) >= 3 or text_len > 15) and not weak_end):
            groups.append(cur)
            cur = []
    for gi, g in enumerate(groups):
        c0 = m(g[0]["s"])
        c1 = m(groups[gi + 1][0]["s"]) if gi + 1 < len(groups) else m(g[-1]["e"]) + 0.3
        if c1 - m(g[-1]["e"]) > 0.6:
            c1 = m(g[-1]["e"]) + 0.25
        mid = (c0 + min(c1, m(g[-1]["e"]))) / 2
        if any(a - 0.05 <= mid <= b + 0.05 for a, b in hide):
            continue
        for a, b in hide:
            if c0 < a < c1:
                c1 = a
        toks = []
        for w in g:
            tok = w["w"].strip(".,!;:\"")
            if tok.lower() in ("i'm", "i'll", "i've", "i"):
                tok = tok[0].upper() + tok[1:]
            if re.search(r"[0-9$]", tok) or tok.lower().strip("'") in P1.HL_WORDS:
                toks.append(f"{{\\c{PS}}}{tok}{{\\c&HFFFFFF&}}")
            else:
                toks.append(tok)
        caps.append(ev(1, c0, c1, "Cap", "{\\fad(40,0)\\fscx95\\fscy95\\t(0,80,\\fscx100\\fscy100)}" + " ".join(toks)))
    events += caps
    events.append(ev(9, total - 0.6, total + 0.1, "Box", f"{{\\an7\\pos(0,0)\\c&H000000&\\fad(550,0)}}{{\\p1}}m 0 0 l 1920 0 1920 1080 0 1080{{\\p0}}"))

    # ---- extra sound design for the big beats
    sfx += [
        {"name": "reverse_swell", "at": m(95.30), "db": -12, "lead": 1.8},
        {"name": "riser", "at": m(102.55), "db": -13, "lead": 3.0},
        {"name": "riser", "at": m(194.30), "db": -12, "lead": 3.0},
        {"name": "riser", "at": m(201.70), "db": -12, "lead": 3.0},
        {"name": "subdrop", "at": m(277.32), "db": -9},
        {"name": "riser", "at": m(372.30), "db": -15, "lead": 3.0},
    ]
    os.makedirs(outdir, exist_ok=True)
    open(f"{outdir}/text.ass", "w").write(STYLES + "\n".join(events) + "\n")
    json.dump({"plates": plates, "elements": elements}, open(f"{outdir}/elements.json", "w"), indent=1)
    edl = {"items": [{"kind": "aroll", "in": a, "out": b} for a, b in keep], "sfx": sfx, "inserts": audio_inserts,
           "music": [], "duck_db": 5, "total": total, "keep": keep}
    json.dump(edl, open(f"{outdir}/edl2.json", "w"), indent=1)
    print(f"{total:.1f}s; titles {len(TITLES)}, heads {len(HEADS)}, plate cards {len(PLATE_CARDS)}, stickers {len(STICKERS)}, "
          f"clips {len(CLIPS)}, frames {len(FRAMES)}, captions {len(caps)}, sfx {len(sfx)}, plates {len(plates)}")


if __name__ == "__main__":
    main()
