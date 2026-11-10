"""Variant B: Ricky's VSL in AB Nasdaq's style, as close to 1:1 as the material allows (see BREAKDOWN.md).

  * word-group captions: 2-4 words, one line, white, tight Apple-style sans with a soft shadow, no punctuation
  * emphasis: the key phrase drops to its own line in heavy caps, electric blue with a glow
  * the shot is always slowly pushing in or pulling out (AB: 80% of face shots move 15-25% over 5-15 s)
  * white keynote cards with black text appearing word by word as he says it; big blue numbers on white
  * proof on a light-grey keynote plate as clean cards; photos beside him in thin white frames; clips framed on white
  * a list in the empty side of the frame with an arrow on the item he's on; a split screen that builds the offer
  * a whoosh or pop on every graphic (AB: one every ~6 s), plus the cash-register sounds on the money moments

    python plan_ab.py transcript.json silences.txt OUTDIR
"""
import json, os, re, sys

sys.path.insert(0, "/home/user/work/scripts")
import plan as P1
import plan3 as P3
import cards_ab as A

SCREEN = P3.SCREEN
BLUE = "&HFF9A2B&"           # #2B9AFF electric blue (ASS is BGR)
WHITE_PLATE, GREY_PLATE = [250, 250, 250], [233, 233, 236]
CLIPDIR = P3.CLIPDIR

HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display Medium,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-2.5,0,1,0,0,5,0,0,0,1
Style: Em,Inter Display Black,104,&H00FF9A2B,&H00FF9A2B,&H00FF9A2B,&H00000000,0,0,0,0,100,100,-3,0,1,0,0,5,0,0,0,1
Style: Key,Inter Display Medium,96,&H00141414,&H00141414,&H00000000,&H00000000,0,0,0,0,100,100,-3,0,1,0,0,5,0,0,0,1
Style: Num,Inter Display Bold,240,&H00FF9A2B,&H00FF9A2B,&H00000000,&H00000000,0,0,0,0,100,100,-6,0,1,0,0,5,0,0,0,1
Style: Small,Inter Display Medium,38,&H00909090,&H00909090,&H00000000,&H00000000,0,0,0,0,100,100,9,0,1,0,0,5,0,0,0,1
Style: HookA,Inter Display Medium,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-2.5,0,1,0,0,4,0,0,0,1
Style: HookB,Inter Display Black,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-3,0,1,0,0,4,0,0,0,1
Style: List,Inter Display SemiBold,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-2,0,1,0,0,4,0,0,0,1
Style: Item,Inter Display SemiBold,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-1.5,0,1,0,0,7,0,0,0,1
Style: ItemS,Inter Display Medium,38,&H00A0A0A0,&H00A0A0A0,&H00000000,&H00000000,0,0,0,0,100,100,-0.5,0,1,0,0,7,0,0,0,1
Style: Title,Inter Display Black,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-1.5,0,1,0,0,5,0,0,0,1
Style: Box,Inter,10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# ---- the edit, in raw-video seconds -------------------------------------------------------------------------------
HOOK = [  # stacked regular + heavy caps in the empty left side (AB's opening "Every one / OF THESE")
    (0.00, 1.40, "18 million", "PEOPLE"),
    (1.40, 3.55, "viewed my product", "IN ONE MONTH"),
    (3.55, 5.72, "and from that", "I ONLY MADE"),
]
HOOK_NUM = (5.72, 8.30, "$87", "IN SALES")
EMPH = [  # (t0, t1, lead line, emphasis line)
    (12.30, 14.20, "and I was", "THIS CLOSE"),
    (14.26, 16.55, "then I changed", "THREE SIMPLE THINGS"),
    (20.30, 23.50, "but I made", "$10,000 IN 3 DAYS"),
    (74.60, 76.30, "the truth is", "YOU DON'T"),
    (80.20, 81.55, "it's", "NOT YOUR FAULT"),
    (120.20, 121.30, "I", "CAN'T DO THIS ANYMORE"),
    (140.25, 142.60, "you're falling for", "THE TIKTOK SCAMS"),
    (184.40, 186.45, "everybody was", "RIGHT ABOUT ME"),
    (188.65, 190.65, "please", "DO NOT CLICK OFF"),
    (221.40, 223.00, "that channel made me", "$300,000"),
    (229.65, 233.20, "I started getting", "SALE AFTER SALE"),
    (261.00, 262.60, "after my first", "$10,000 MONTH"),
    (281.15, 283.70, "is not what made me", "THAT MONEY"),
    (359.85, 361.40, "in the next", "60 DAYS"),
    (362.60, 363.95, "I'll work with you", "COMPLETELY FREE"),
    (372.35, 373.95, "the application is", "DOWN BELOW"),
]
KEYNOTE = [  # white card, black words appearing as he says them; (t0, t1, [line, line], blue words)
    (95.30, 99.30, ["The one place every guru", "was telling me not to post on"], []),
    (126.85, 131.20, ["So I quit,", "with $457 to my name"], ["$457"]),
    (277.30, 279.50, ["Here's the part that most", "people don't understand"], []),
]
NUMBERS = [  # big blue number on white with a small grey line under it
    (67.74, 69.16, "$0", "AFTER A MILLION VIEWS"),
    (164.10, 165.45, "18,000,000", "VIEWS"),
    (166.45, 167.98, "$87", "IN SALES"),
]
PROOF = [  # screenshots on the light-grey keynote plate: name, t0, t1
    ("shop_11k", 38.45, 42.15),
    ("shop_payout", 323.60, 326.80),
]
PHOTO_PLATE = [("night_laptop", 61.95, 65.35)]     # photo framed on white
POPS = [  # photos / screenshots beside him in thin white frames: name, t0, t1, cx, cy
    ("shop_11k", 20.35, 22.30, 1470, 430),
    ("playbutton_lv", 220.90, 223.55, 1480, 450),
    ("shop_36k", 227.60, 230.60, 1470, 440),
    ("shop_today_2k", 230.70, 233.60, 1470, 440),
    ("gwagon", 267.00, 270.05, 1480, 450),
    ("yt_sept_91m", 322.35, 323.55, 1450, 420),
]
CLIPS = [  # file, t0, t1, in, mode, clip audio dB
    ("IMG_5163.MOV", 204.50, 206.75, 0.0, "plate", None),
    ("IMG_3996.MOV", 263.30, 266.95, 0.0, "pop", None),
    ("IMG_8117.mov", 270.50, 277.00, 3.0, "plate", -16),
]
BEHIND = (202.05, 203.90, "YOUTUBE SHORTS")      # giant text behind his head, like AB's "ONE SETUP"
LIST = (294.00, 318.60, [(294.10, "A proven product"), (300.20, "A channel, not a video"), (307.30, "A brand, not a one-off")], 315.00)
SPLIT = (326.60, 355.50, "WHAT'S INCLUDED", "INSIDE ", "YTD",
         [(326.90, "One weekly 1-on-1 call", "your videos, store and product, every week"),
          (334.40, "Four weekly coaching calls", "product research, competitors, videos, Q&As"),
          (344.30, "My personal phone number", "Monday to Friday, not an assistant")])
CASH = [(20.62, "cash", -10.5), (39.30, "cash", -10.5), (222.04, "cash", -10.5), (230.30, "cash_light1", -13.5),
        (231.10, "cash_light2", -12.5), (231.78, "cash_light3", -11.5), (261.40, "cash", -10.5), (323.60, "cash", -11.0)]


def ass_time(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ev(layer, t0, t1, style, text):
    return f"Dialogue: {layer},{ass_time(t0)},{ass_time(t1)},{style},,0,0,0,,{text}"


def shadowed(layer, t0, t1, style, pos, text, extra="", an=None):
    """AB's soft caption shadow: a blurred dark copy just under the text."""
    a = f"\\an{an}" if an else ""
    x, y = pos
    return [ev(layer, t0, t1, style, f"{{{a}\\pos({x},{y + 4})\\c&H000000&\\alpha&H6A&\\blur9{extra}}}{text}"),
            ev(layer + 1, t0, t1, style, f"{{{a}\\pos({x},{y}){extra}}}{text}")]


def glow(layer, t0, t1, style, pos, text, extra="", an=None):
    a = f"\\an{an}" if an else ""
    x, y = pos
    return [ev(layer, t0, t1, style, f"{{{a}\\pos({x},{y})\\bord7\\3c{BLUE}\\blur16\\alpha&H58&{extra}}}{text}"),
            ev(layer + 1, t0, t1, style, f"{{{a}\\pos({x},{y + 5})\\c&H000000&\\alpha&H7A&\\blur10{extra}}}{text}"),
            ev(layer + 2, t0, t1, style, f"{{{a}\\pos({x},{y}){extra}}}{text}")]


def tokens(words):
    out = []
    for w in words:
        t = w["w"].strip()
        if out and (t.startswith(",") or t.startswith("-")):
            out[-1] = dict(out[-1], w=out[-1]["w"] + t, e=w["e"])
        else:
            out.append(dict(w, w=t))
    return out


def clean(t):
    t = re.sub(r"[.,!?;:]+$", "", t)
    return re.sub(r"^i$", "I", t)


def main():
    transcript, silences, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    words = tokens(P1.load_words(transcript))
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
    no_caps = []                    # raw-time windows without word captions

    def whoosh(at, db=-17, lead=0.12, name="whoosh_soft"):
        sfx.append({"name": name, "at": m(at), "db": db, "lead": lead})

    def pop(at, db=-15):
        sfx.append({"name": "pop", "at": m(at), "db": db})

    # ---- hook: stacked text in the empty left side, then the number
    for a, b, l1, l2 in HOOK:
        events += shadowed(4, m(a), m(b), "HookA", (110, 395), l1, an=4)
        events += shadowed(4, m(a), m(b), "HookB", (106, 490), l2, an=4)
        no_caps.append((a, b))
        pop(a, -19)
    a, b, num, sub = HOOK_NUM
    events += glow(4, m(a), m(b), "Num", (100, 430), num, "\\fs230\\fscx90\\fscy90\\t(0,140,\\fscx100\\fscy100)", an=4)
    events += shadowed(4, m(a) + 0.2, m(b), "HookA", (112, 590), sub, "\\fs52\\fsp7", an=4)
    no_caps.append((a, b))
    pop(a, -13); whoosh(a, -19)

    # ---- emphasis lines (replace the word captions in their window)
    for a, b, lead, emph in EMPH:
        if lead:
            events += shadowed(4, m(a), m(b), "Cap", (960, 812), lead)
        events += glow(4, m(a), m(b), "Em", (960, 918 if lead else 880), emph, "\\fad(50,0)")
        no_caps.append((a, b))
        pop(a, -19)

    # ---- full-screen cards
    for a, b, lines, blue in KEYNOTE:
        t0, t1 = m(a), m(b)
        plates.append({"t0": t0, "t1": t1, "rgb": WHITE_PLATE, "fade_in": 0.0, "fade_out": 0.0})
        no_caps.append((a, b))
        ws = [w for w in words if a - 0.35 <= w["s"] < b]
        k = 0
        n = len(lines)
        for li, line in enumerate(lines):
            y = 540 + (li - (n - 1) / 2) * 118
            parts = []
            for tok in line.split(" "):
                w = ws[min(k, len(ws) - 1)] if ws else {"s": a}
                k += 1
                ms = max(0, int((m(w["s"]) - t0) * 1000))
                col = f"\\c{BLUE}" if tok in blue else "\\c&H141414&"
                parts.append(f"{{\\alpha&HFF&{col}\\t({ms},{ms + 90},\\alpha&H00&)}}{tok}")
            size = "\\fs170\\fsp-6" if n == 1 else ""
            events.append(ev(5, t0, t1, "Key", f"{{\\pos(960,{y:.0f}){size}}}" + " ".join(parts)))
        whoosh(a); pop(a + 0.05, -17)
    for a, b, num, sub in NUMBERS:
        t0, t1 = m(a), m(b)
        plates.append({"t0": t0, "t1": t1, "rgb": WHITE_PLATE, "fade_in": 0.0, "fade_out": 0.0})
        no_caps.append((a, b))
        events.append(ev(5, t0, t1, "Num", f"{{\\pos(960,505)\\fscx88\\fscy88\\t(0,180,\\fscx100\\fscy100)}}{num}"))
        events.append(ev(5, t0, t1, "Small", f"{{\\pos(960,665)\\fad(120,0)}}— {sub} —"))
        whoosh(a); pop(a + 0.04, -14)
    for name, a, b in PROOF:
        t0, t1 = m(a), m(b)
        plates.append({"t0": t0, "t1": t1, "rgb": GREY_PLATE, "fade_in": 0.0, "fade_out": 0.0})
        elements.append({"type": "card", "img": A.proof(name), "t0": t0, "t1": t1, "cx": 960, "cy": 540})
        no_caps.append((a, b))
        whoosh(a, -16)
    for name, a, b in PHOTO_PLATE:
        t0, t1 = m(a), m(b)
        plates.append({"t0": t0, "t1": t1, "rgb": WHITE_PLATE, "fade_in": 0.0, "fade_out": 0.0})
        elements.append({"type": "card", "img": A.proof(name, 1100, 760), "t0": t0, "t1": t1, "cx": 960, "cy": 540})
        whoosh(a, -16)
    for name, a, b, cx, cy in POPS:
        elements.append({"type": "card", "img": A.photo(name), "t0": m(a), "t1": m(b), "cx": cx, "cy": cy, "anim": "sticker"})
        whoosh(a, -19, 0.1, "whoosh"); pop(a + 0.06, -14)
    inserts = []
    for fn, a, b, cin, mode, adb in CLIPS:
        t0, t1 = m(a), m(b)
        if mode == "plate":
            plates.append({"t0": t0, "t1": t1, "rgb": WHITE_PLATE, "fade_in": 0.0, "fade_out": 0.0})
            elements.append({"type": "clip", "file": f"{CLIPDIR}/{fn}", "in": cin, "t0": t0, "t1": t1, "h": 860, "cx": 960, "cy": 540, "style": "ab"})
        else:
            elements.append({"type": "clip", "file": f"{CLIPDIR}/{fn}", "in": cin, "t0": t0, "t1": t1, "h": 620, "cx": 1470, "cy": 470, "anim": "sticker", "style": "ab"})
            pop(a + 0.06, -14)
        if adb is not None:
            inserts.append({"file": f"{CLIPDIR}/{fn}", "at": t0, "dur": t1 - t0, "in": cin, "audio_db": adb})
        whoosh(a, -16)

    # ---- giant text behind him
    a, b, text = BEHIND
    elements.append({"type": "behind", "img": A.behind_text(text, cy=165), "t0": m(a), "t1": m(b)})
    no_caps.append((a, b))
    whoosh(a, -16); pop(a + 0.03, -14)

    # ---- list in the empty side of the frame, arrow on the current item
    a, b, items, recap = LIST
    t0, t1 = m(a), m(b)
    no_caps.append((a, b))
    events.append(ev(3, t0, t1, "Box", "{\\an7\\pos(0,0)\\c&H000000&\\alpha&H70&\\blur60\\fad(250,250)}{\\p1}m 1220 0 l 1920 0 1920 1080 1220 1080{\\p0}"))
    starts = [s for s, _ in items] + [recap]
    for i, (s, text) in enumerate(items):
        y = 430 + i * 110
        for j in range(i, len(items) + 1):          # phases from this item's start on
            p0, p1 = m(starts[j]), (m(starts[j + 1]) if j + 1 < len(starts) else t1)
            current = (j == i)
            bright = current or j == len(items)
            arrow = "  ←" if current else ""
            alpha = "" if bright else "\\alpha&H8C&"
            events += shadowed(4, p0, p1, "List", (1290, y), text + arrow, alpha + ("\\fad(120,0)" if current else ""), an=4)
        pop(s, -16)
    pop(recap, -17)

    # ---- split screen that builds the offer line by line
    a, b, title, lead, brand, items = SPLIT
    t0, t1 = m(a), m(b)
    no_caps.append((a, b))
    elements.append({"type": "split", "t0": t0, "t1": t1, "panel_w": 840, "cx": 930, "rgb": [6, 6, 8]})
    events.append(ev(6, t0 + 0.3, t1 - 0.25, "Title", f"{{\\pos(1380,215)\\fad(150,120)}}{title}"))
    events.append(ev(6, t0 + 0.3, t1 - 0.25, "Title", f"{{\\pos(1380,285)\\fad(150,120)}}{lead}{{\\c{BLUE}}}{brand}"))
    events.append(ev(6, t0 + 0.3, t1 - 0.25, "Title", f"{{\\pos(1380,285)\\bord8\\3c{BLUE}\\blur22\\alpha&HA0&\\fad(150,120)}}{lead}{brand}"))
    events.append(ev(6, t0 + 0.4, t1 - 0.25, "Box", "{\\an7\\pos(0,0)\\c&HFFFFFF&\\alpha&H60&\\fad(150,120)}{\\p1}m 1160 340 l 1600 340 1600 343 1160 343{\\p0}"))
    for i, (s, main_line, sub) in enumerate(items):
        y = 420 + i * 175
        events.append(ev(6, m(s), t1 - 0.25, "Item", f"{{\\pos(960,{y})\\fad(120,120)}}{i + 1}."))
        events.append(ev(6, m(s), t1 - 0.25, "Item", f"{{\\pos(1020,{y})\\fad(120,120)}}{main_line}"))
        events.append(ev(6, m(s) + 0.15, t1 - 0.25, "ItemS", f"{{\\pos(1022,{y + 66})\\fad(150,120)}}{sub}"))
        pop(s, -15)
    whoosh(a, -17)
    sfx.append({"name": "ding", "at": m(344.30), "db": -11.5})

    # ---- money sounds
    for at, name, db in CASH:
        sfx.append({"name": name, "at": m(at), "db": db})

    # ---- word captions: 2-4 words, one line, no punctuation, change about every second
    def hidden(x):
        return any(a - 0.05 <= x < b for a, b in no_caps) or any(p["t0"] <= m(x) < p["t1"] for p in plates)

    groups, cur = [], []
    for i, w in enumerate(words):
        if hidden(w["s"]):
            if cur:
                groups.append(cur); cur = []
            continue
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = " ".join(clean(x["w"]) for x in cur)
        end = (nxt is None or hidden(nxt["s"]) or w["w"][-1] in ".?!," or (nxt["s"] - w["e"]) > 0.25
               or len(cur) >= 4 or (len(txt) >= 16 and len(cur) >= 2)
               or any(a <= nxt["s"] < b for a, b in SCREEN) != any(a <= w["s"] < b for a, b in SCREEN))
        if end:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    for gi, g in enumerate(groups):
        c0 = m(g[0]["s"])
        nxt0 = m(groups[gi + 1][0]["s"]) if gi + 1 < len(groups) else c0 + 3
        c1 = min(nxt0, m(g[-1]["e"]) + 0.3)
        for a, b in no_caps:
            if c0 < m(a) < c1:
                c1 = m(a)
        for p in plates:
            if c0 < p["t0"] < c1:
                c1 = p["t0"]
        if c1 - c0 < 0.12:
            continue
        text = " ".join(clean(x["w"]) for x in g)
        events += shadowed(2, c0, c1, "Cap", (960, 880), text)

    # ---- the slow, never-still zoom (alternating push-in / pull-out), as AB does on every face shot
    covered = sorted([(p["t0"], p["t1"]) for p in plates] + [(m(a), m(b)) for a, b in SCREEN])
    stretches, t = [], 0.0
    for a, b in covered:
        if a - t > 0.6:
            stretches.append((t, a))
        t = max(t, b)
    if total - t > 0.6:
        stretches.append((t, total))
    calm = [(m(0.0), m(8.30)), (m(LIST[0]), m(LIST[1])), (m(BEHIND[0]) - 2.5, m(BEHIND[1]))]   # keep room for text
    gaps = [m(w["e"]) for w, n in zip(words, words[1:]) if n["s"] - w["e"] > 0.12]
    zooms, flip = [], 0
    for s0, s1 in stretches:
        keys, t, up = [(s0, 1.0 if flip % 2 == 0 else 1.18)], s0, flip % 2 == 0
        if s1 - s0 < 3.0:                       # a short shot holds its framing
            keys, t = [(s0, 1.08), (s1, 1.08)], s1
        while t < s1 - 0.5:
            target = t + 7.0
            cand = [g for g in gaps if t + 5.0 <= g <= min(t + 9.5, s1)]
            nt = min(cand, key=lambda g: abs(g - target)) if cand and s1 - t > 9.5 else s1
            lo_hi = (1.0, 1.04) if any(c0 <= t < c1 for c0, c1 in calm) else (1.0, 1.2)
            if any(c0 <= t < c1 for c0, c1 in [(m(SPLIT[0]), m(SPLIT[1]))]):
                lo_hi = (1.12, 1.18)
            keys.append((nt, lo_hi[1] if up else lo_hi[0]))
            up = not up
            t = nt
        for c0, c1 in calm:                     # hold the frame wide wherever text needs the room
            if c1 <= s0 or c0 >= s1:
                continue
            c0, c1 = max(c0, s0), min(c1, s1)
            keys = [k for k in keys if not (c0 <= k[0] <= c1)] + [(c0, 1.03), (c1, 1.03)]
            keys.sort()
            if s1 - c1 < 3.0:                   # too little time left for a calm move: stay put
                keys = [k for k in keys if k[0] <= c1] + ([(s1, 1.03)] if s1 > c1 + 0.05 else [])
            if c0 - s0 < 3.0 and c0 > s0:
                keys = [(s0, 1.03)] + [k for k in keys if k[0] >= c0]
        zooms.append({"keys": keys})
        flip += 1
    for z in zooms:
        a0, a1 = z["keys"][0][0], z["keys"][-1][0]
        assert not any(a0 < m(b) - 0.01 and m(a) + 0.01 < a1 for a, b in SCREEN), z

    os.makedirs(outdir, exist_ok=True)
    events.append(ev(9, total - 0.6, total + 0.1, "Box", "{\\an7\\pos(0,0)\\c&H000000&\\fad(550,0)}{\\p1}m 0 0 l 1920 0 1920 1080 0 1080{\\p0}"))
    open(f"{outdir}/text.ass", "w").write(HEAD + "\n".join(events) + "\n")
    json.dump({"plates": plates, "elements": elements, "zooms": zooms, "keep": keep, "zoom_src": P3.ZOOM_SRC},
              open(f"{outdir}/elements.json", "w"), indent=1)
    edl = {"items": [{"kind": "aroll", "in": a, "out": b} for a, b in keep], "sfx": sorted(sfx, key=lambda s: s["at"]),
           "inserts": inserts, "music": [{"stem": "score", "t0": 0.0, "t1": total, "offset": 0.0, "db": -13.5, "fi": 0.0, "fo": 0.0}],
           "duck_db": 4, "music_db": 0, "total": total, "keep": keep}
    json.dump(edl, open(f"{outdir}/edlB.json", "w"), indent=1)
    print(f"{total:.1f}s; plates {len(plates)}, elements {len(elements)}, zoom stretches {len(zooms)}, "
          f"caption groups {len(groups)}, sfx {len(sfx)}")


if __name__ == "__main__":
    main()
