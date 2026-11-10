"""Variant B4: B3 after review. The white side fade only ~7 times and softer/narrower (it breaks the video up without
taking over); full-screen pictures in Iman Gadzhi's premium style (dark brand plate, glowing tilted cards with the key
numbers outlined, clips in glowing frames) instead of white; more sound on images (a cash register when a money
screenshot lands, a soft thud on other photos and clips, whooshes); no sound on captions except the highlights, and the
money-loss highlights ($87, $0, $457, $1,500) in red.

B3 notes: Variant B3: B2 after review. Side text with the white fade only on ~13 key moments (the rest back to word captions
and blue emphasis lines), placed a little lower; clean fades (opacity only, nothing shrinks); no click sounds on
any text; no captions over screen shares; zooms only where they mean something (no pulsing in and out).
Fonts: Fellix if its files are installed, otherwise Inter Display.

B2 notes:

Changes from B: word captions 1-2 at a time in AB's size and tight spacing, switched hard on every new word group,
over AB's dark fade along the bottom; AB's side text (stacked regular + heavy caps, key word blue, built as he says it
with a letter-by-letter blur-in, on a white fade from that edge) used for ~30 key lines through the whole video; a
subtle mouse click on every caption and every piece of text instead of pops; "YOUTUBE SHORTS" fully visible.

v1 notes (B):

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
import cards2 as C2
import brand as B

SCREEN = P3.SCREEN
BLUE = "&HFF9A2B&"
RED = "&H3B3BFF&"            # #FF3B3B for money lost           # #2B9AFF electric blue (ASS is BGR)
WHITE_PLATE, GREY_PLATE = [250, 250, 250], [233, 233, 236]
CLIPDIR = P3.CLIPDIR

HEAD_T = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{medium},78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-2.5,0,1,0,0,5,0,0,0,1
Style: Em,{heavy},104,&H00FF9A2B,&H00FF9A2B,&H00FF9A2B,&H00000000,0,0,0,0,100,100,-3,0,1,0,0,5,0,0,0,1
Style: Key,Inter Display Medium,96,&H00141414,&H00141414,&H00000000,&H00000000,0,0,0,0,100,100,-3,0,1,0,0,5,0,0,0,1
Style: Num,Inter Display Bold,240,&H00FF9A2B,&H00FF9A2B,&H00000000,&H00000000,0,0,0,0,100,100,-6,0,1,0,0,5,0,0,0,1
Style: Small,Inter Display Medium,38,&H00909090,&H00909090,&H00000000,&H00000000,0,0,0,0,100,100,9,0,1,0,0,5,0,0,0,1
Style: HookA,Inter Display Medium,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-2.5,0,1,0,0,4,0,0,0,1
Style: HookB,Inter Display Black,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-3,0,1,0,0,4,0,0,0,1
Style: List,Inter Display SemiBold,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-2,0,1,0,0,4,0,0,0,1
Style: Item,Inter Display SemiBold,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-1.5,0,1,0,0,7,0,0,0,1
Style: ItemS,Inter Display Medium,38,&H00A0A0A0,&H00A0A0A0,&H00000000,&H00000000,0,0,0,0,100,100,-0.5,0,1,0,0,7,0,0,0,1
Style: Title,Inter Display Black,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,-1.5,0,1,0,0,5,0,0,0,1
Style: SReg,{medium},74,&H00141414,&H00141414,&H00000000,&H00000000,0,0,0,0,100,100,-2.5,0,1,0,0,4,0,0,0,1
Style: SBold,{heavy},108,&H00141414,&H00141414,&H00000000,&H00000000,0,0,0,0,100,100,-3.5,0,1,0,0,4,0,0,0,1
Style: SNum,{heavy},170,&H00FF9A2B,&H00FF9A2B,&H00000000,&H00000000,0,0,0,0,100,100,-5,0,1,0,0,4,0,0,0,1
Style: Box,Inter,10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# ---- the edit, in raw-video seconds -------------------------------------------------------------------------------
SIDE = [  # AB side text, used sparingly: (side, raw t0, raw t1, [(text, kind, anchor word)])
    ("L", 0.00, 3.55, [("18 million people", "reg", "18"), ("VIEWED MY", "bold", "viewed"), ("PRODUCT", "blue", "product"), ("in one month", "reg", "in")]),
    ("L", 3.55, 8.30, [("and from that", "reg", "and"), ("I ONLY MADE", "bold", "only"), ("$87", "rednum", "$87"), ("in sales", "reg", "in")]),
    ("R", 14.26, 17.00, [("then I changed", "reg", "then"), ("THREE SIMPLE", "bold", "three"), ("THINGS", "blue", "things")]),
    ("L", 102.60, 108.00, [("not that long ago", "reg", "not"), ("I WAS A", "bold", "I"), ("DINING SERVER", "blue", "dining"), ("for $16 an hour", "reg", "for")]),
    ("R", 145.10, 149.70, [("I spent", "reg", "spent"), ("$1,500", "rednum", "$1,500"), ("on a mentor", "reg", "on"), ("WORST ADVICE", "bold", "worst"), ("EVER", "blue", "ever")]),
    ("L", 194.80, 202.00, [("but there was", "reg", "there"), ("ONE PLACE", "bold", "one"), ("I never tried", "reg", "never"), ("every dropshipper said", "reg", "every"), ("STAY AWAY", "blue", "stay")]),
    ("L", 289.50, 293.90, [("what made", "reg", "what"), ("THE DIFFERENCE", "bold", "difference"), ("was three things", "reg", "three")]),
    ("R", 356.00, 360.95, [("if you do the work", "reg", "if"), ("and you're not live", "reg", "and"), ("IN THE NEXT", "bold", "next"), ("60 DAYS", "num", "60")]),
]
EMPH = [  # bottom highlight lines (blue glow caps; a soft whoosh each)
    (12.30, 14.20, "and I was", "THIS CLOSE"),
    (20.30, 23.50, "but I made", "$10,000 IN 3 DAYS"),
    (43.10, 44.70, "one of them is probably", "THE REASON"),
    (74.60, 76.30, "the truth is", "YOU DON'T"),
    (80.20, 81.55, "it's", "NOT YOUR FAULT"),
    (82.10, 84.20, "the problem is", "THE PLATFORM"),
    (120.20, 121.30, "I", "CAN'T DO THIS ANYMORE"),
    (140.25, 142.60, "you're falling for", "THE TIKTOK SCAMS"),
    (184.40, 186.45, "everybody was", "RIGHT ABOUT ME"),
    (188.65, 190.65, "please", "DO NOT CLICK OFF"),
    (221.40, 223.00, "that channel made me", "$300,000"),
    (229.65, 233.20, "I started getting", "SALE AFTER SALE"),
    (261.00, 262.65, "after my first", "$10,000 MONTH"),
    (281.15, 283.70, "is not what made me", "THAT MONEY"),
    (369.50, 370.95, "tired of getting", "ZERO VIEWS"),
    (362.60, 363.95, "I'll work with you", "COMPLETELY FREE"),
    (372.35, 373.95, "the application is", "DOWN BELOW"),
]
ZOOMS = [  # zooms with intent, on the lines that carry weight (eased in and out, never pulsing)
    [(11.60, 1.0), (12.40, 1.15), (13.40, 1.17), (14.25, 1.0)],                        # "I was this close"
    [(74.40, 1.0), (75.15, 1.13), (75.95, 1.15), (76.85, 1.0)],                        # "the truth is, you don't"
    [(92.00, 1.0), (95.30, 1.10), (95.55, 1.10)],                                      # "...the one place" into the card
    [(117.10, 1.0), (120.10, 1.09), (120.85, 1.16), (121.30, 1.17), (122.15, 1.0)],    # "I can't do this anymore"
    [(139.55, 1.0), (140.35, 1.13), (142.35, 1.16), (143.10, 1.0)],                    # "falling for the TikTok scams"
    [(170.90, 1.0), (173.60, 1.12), (174.65, 1.0)],                                    # mom: "I don't think you should..."
    [(183.24, 1.0), (186.30, 1.10), (187.30, 1.06), (189.00, 1.15), (190.55, 1.17), (191.30, 1.0)],  # "right about me", "don't click off"
    [(279.66, 1.0), (283.50, 1.12), (284.35, 1.0)],                                    # "not what made me that money"
    [(321.20, 1.0), (323.60, 1.08), (323.70, 1.08)],                                   # the promise, into the payout card
]
DINER = [(104.60, 107.60), (124.60, 126.60)]     # "dining server": his diner photo / clip, once uploaded
KEYNOTE = [  # white card, black words appearing as he says them; (t0, t1, [line, line], blue words)
    (95.30, 99.30, ["The one place every guru", "was telling me not to post on"], []),
    (126.85, 131.20, ["So I quit,", "with $457 to my name"], ["$457"]),        # money lost: red
    (277.30, 279.50, ["Here's the part that most", "people don't understand"], []),
]
NUMBERS = [  # big blue number on white with a small grey line under it
    (67.74, 69.16, "$0", "AFTER A MILLION VIEWS"),
    (164.10, 165.45, "18,000,000", "VIEWS"),
    (166.45, 167.98, "$87", "IN SALES"),
]
PROOF = [  # full-screen pictures, Iman style: name, t0, t1, max_w, max_h, tilt, sound
    ("shop_11k", 38.45, 42.15, 1150, 720, 6, "cash"),
    ("night_laptop", 61.95, 65.35, 760, 760, -5, "bum"),
    ("shop_payout", 323.60, 326.80, 900, 760, -5, "cash"),
]
PHOTO_PLATE = []
POPS = [  # photos / screenshots beside him in thin white frames: name, t0, t1, cx, cy, sound
    ("shop_11k", 20.35, 22.30, 1470, 430, "cash"),
    ("playbutton_lv", 220.90, 223.55, 1480, 450, "bum"),
    ("shop_36k", 227.60, 230.60, 1470, 440, "cash"),
    ("shop_today_2k", 230.70, 233.60, 1470, 440, None),        # the "sale after sale" cash sounds cover it
    ("gwagon", 267.00, 270.05, 1480, 450, "bum"),
    ("yt_sept_91m", 322.35, 323.55, 1450, 420, "bum"),
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
CASH = [(222.04, "cash", -10.5), (230.30, "cash_light1", -13.5), (231.10, "cash_light2", -12.5),
        (231.78, "cash_light3", -11.5), (261.40, "cash", -10.5)]     # money said aloud with no picture on screen
SOUND_DB = {"cash": -10.5, "bum": -13.0}


def pick_fonts():
    """Fellix (if its files are installed) for captions and side text, otherwise Inter Display."""
    import subprocess
    out = subprocess.run(["fc-list", ":", "family", "style", "file"], capture_output=True, text=True).stdout
    rows = [l for l in out.splitlines() if "fellix" in l.lower()]
    def find(*styles):
        for st in styles:
            for l in rows:
                f, rest = l.split(":", 1)
                if f"style={st}" in rest.replace(" ", "") or f"style={st}," in rest:
                    fam = rest.split("style=")[0].strip().strip(":").split(",")[0]
                    return f"{fam} {st}".replace(" Regular", ""), f.strip()
        return None
    med, heavy = find("Medium", "Regular", "Book"), find("Black", "ExtraBold", "Bold", "SemiBold")
    if med and heavy:
        return {"medium": med[0], "heavy": heavy[0]}, {"medium": med[1], "heavy": heavy[1]}
    inter = "/usr/share/fonts/opentype/inter/"
    return ({"medium": "Inter Display Medium", "heavy": "Inter Display Black"},
            {"medium": inter + "InterDisplay-Medium.otf", "heavy": inter + "InterDisplay-Black.otf"})


FONT_NAMES, FONT_FILES = pick_fonts()
HEAD = HEAD_T.replace("{medium}", FONT_NAMES["medium"]).replace("{heavy}", FONT_NAMES["heavy"])


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

    nclick = [0]

    def pop(at, db=-21):            # B3: no click sounds on text at all (whooshes, cash and the ding stay)
        return

    # ---- AB side text: stacked lines built as he says them, letter-by-letter blur-in, on a white fade from that edge
    from PIL import ImageFont
    FONTS = {"reg": (FONT_FILES["medium"], 68, -2.5), "bold": (FONT_FILES["heavy"], 98, -3.5),
             "blue": (FONT_FILES["heavy"], 98, -3.5), "num": (FONT_FILES["heavy"], 150, -5), "rednum": (FONT_FILES["heavy"], 150, -5)}
    GAP = {"reg": 80, "bold": 96, "blue": 96, "num": 144, "rednum": 144}

    def fit(text, kind, maxw=600):
        f, size, sp = FONTS[kind]
        font = ImageFont.truetype(f, size)
        w = font.getlength(text) + sp * (len(text) - 1)
        return size if w <= maxw else int(size * maxw / w)

    def find(word, after):
        key = re.sub(r"[^a-z0-9$,']", "", word.lower())
        for w in words:
            if w["s"] >= after - 1e-6 and re.sub(r"[^a-z0-9$,']", "", w["w"].lower()).strip(",") == key.strip(","):
                return w["s"]
        return None

    spans = []                                   # one white fade per run of side text on the same side
    for side, a, b, _ in SIDE:
        if spans and spans[-1][0] == side and a - spans[-1][2] < 0.5:
            spans[-1][2] = b
        else:
            spans.append([side, a, b])
    for side, a, b in spans:
        elements.append({"type": "card", "img": A.gradient("left_soft" if side == "L" else "right_soft"), "t0": m(a), "t1": m(b),
                         "cx": 960, "cy": 540, "anim": "overlay"})
    for side, a, b, lines in SIDE:
        t0, t1 = m(a), m(b)
        no_caps.append((a, b))
        span_end = next(m(e) for sd, s0, e in spans if sd == side and s0 <= a < e)
        heights = [GAP[k] * fit(tx, k) / FONTS[k][1] for tx, k, _ in lines]
        y = 545 - sum(heights) / 2 + heights[0] / 2
        cursor = a - 0.6
        for (text, kind, anchor), hgt in zip(lines, heights):
            ts = find(anchor, cursor)
            if ts is None or ts > b:
                ts = cursor + 0.4
            ts = max(ts, a)
            cursor = ts + 0.05
            style = {"reg": "SReg", "bold": "SBold", "blue": "SBold", "num": "SNum", "rednum": "SNum"}[kind]
            col = RED if kind == "rednum" else BLUE if kind in ("blue", "num") else None
            if kind == "rednum":                         # a highlight: money lost, in red, lands with a thud
                sfx.append({"name": "bum", "at": m(ts) + 0.02, "db": -13.0})
            x, an = (110, 4) if side == "L" else (1810, 6)
            size = fit(text, kind)
            body = B.ass_reveal(text, 0, 16, 220, 10, col)
            fade = "\\fad(0,330)" if abs(t1 - span_end) < 0.01 else "\\fad(0,140)"   # with the white fade / quick swap
            events.append(ev(4, m(ts), t1, style, f"{{\\an{an}\\pos({x},{y:.0f})\\fs{size}{fade}}}" + body))
            y += hgt

    # ---- emphasis lines (replace the word captions in their window)
    for a, b, lead, emph in EMPH:
        if lead:
            events += shadowed(4, m(a), m(b), "Cap", (960, 812), lead)
        events += glow(4, m(a), m(b), "Em", (960, 918 if lead else 880), emph, "\\fad(50,0)")
        no_caps.append((a, b))
        whoosh(a, -22, 0.08)

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
                pop(w["s"] if w["s"] >= a else a, -22)
                col = f"\\c{RED}" if tok in blue else "\\c&H141414&"
                parts.append(f"{{\\alpha&HFF&{col}\\t({ms},{ms + 90},\\alpha&H00&)}}{tok}")
            size = "\\fs170\\fsp-6" if n == 1 else ""
            events.append(ev(5, t0, t1, "Key", f"{{\\pos(960,{y:.0f}){size}}}" + " ".join(parts)))
        whoosh(a)
    for a, b, num, sub in NUMBERS:
        t0, t1 = m(a), m(b)
        plates.append({"t0": t0, "t1": t1, "rgb": WHITE_PLATE, "fade_in": 0.0, "fade_out": 0.0})
        no_caps.append((a, b))
        red = num in ("$0", "$87")
        events.append(ev(5, t0, t1, "Num", f"{{\\pos(960,505)\\fscx88\\fscy88\\t(0,180,\\fscx100\\fscy100)" + (f"\\c{RED}" if red else "") + f"}}{num}"))
        if red:
            sfx.append({"name": "bum", "at": t0 + 0.03, "db": -13.0})
        events.append(ev(5, t0, t1, "Small", f"{{\\pos(960,665)\\fad(120,0)}}— {sub} —"))
        whoosh(a); pop(a + 0.04, -19)
    for name, a, b, mw, mh, tilt, snd in PROOF:              # Iman style: dark brand plate, glowing tilted card
        t0, t1 = m(a), m(b)
        p, ph = C2.card(name, mw, mh, tilt)
        plates.append({"t0": t0, "t1": t1})
        elements.append({"type": "card", "img": p, "hl_img": ph, "t0": t0, "t1": t1, "cx": 960, "cy": 520, "hl_delay": 0.55})
        no_caps.append((a, b))
        whoosh(a, -16)
        sfx.append({"name": snd, "at": t0 + 0.06, "db": SOUND_DB[snd]})
    for name, a, b, cx, cy, snd in POPS:
        elements.append({"type": "card", "img": A.photo(name), "t0": m(a), "t1": m(b), "cx": cx, "cy": cy, "anim": "sticker"})
        whoosh(a, -19, 0.1, "whoosh")
        if snd:
            sfx.append({"name": snd, "at": m(a) + 0.06, "db": SOUND_DB[snd]})
    inserts = []
    for fn, a, b, cin, mode, adb in CLIPS:
        t0, t1 = m(a), m(b)
        if mode == "plate":                                 # Iman style: glowing frame on the dark brand plate
            plates.append({"t0": t0, "t1": t1})
            elements.append({"type": "clip", "file": f"{CLIPDIR}/{fn}", "in": cin, "t0": t0, "t1": t1, "h": 860, "cx": 960, "cy": 500})
        else:
            elements.append({"type": "clip", "file": f"{CLIPDIR}/{fn}", "in": cin, "t0": t0, "t1": t1, "h": 620, "cx": 1470, "cy": 470, "anim": "sticker", "style": "ab"})
        sfx.append({"name": "bum", "at": t0 + 0.06, "db": SOUND_DB["bum"]})
        if adb is not None:
            inserts.append({"file": f"{CLIPDIR}/{fn}", "at": t0, "dur": t1 - t0, "in": cin, "audio_db": adb})
        whoosh(a, -16)

    # ---- giant text behind him
    a, b, text = BEHIND
    elements.append({"type": "card", "img": A.behind_text(text, cy=190), "t0": m(a), "t1": m(b), "cx": 960, "cy": 540, "anim": "fade"})
    no_caps.append((a, b))
    whoosh(a, -16); pop(a + 0.03, -19)

    # ---- list in the empty side of the frame, arrow on the current item
    a, b, items, recap = LIST
    t0, t1 = m(a), m(b)
    no_caps.append((a, b))
    elements.append({"type": "card", "img": A.gradient("right_dark"), "t0": t0, "t1": t1, "cx": 960, "cy": 540, "anim": "overlay"})
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
        pop(s, -20)
    pop(recap, -21)

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
        pop(s, -20)
    whoosh(a, -17)
    sfx.append({"name": "ding", "at": m(344.30), "db": -11.5})

    # ---- money sounds
    for at, name, db in CASH:
        sfx.append({"name": name, "at": m(at), "db": db})

    # ---- diner photo / clip on "dining server" (only once it's uploaded to 02-results-and-b-roll as diner.*)
    import glob
    diner = sorted(glob.glob("/home/user/rickyvsl-clips/02-results-and-b-roll/diner*"))
    for a, b in DINER if diner else []:
        f = diner[0]
        if f.lower().endswith((".mov", ".mp4")):
            elements.append({"type": "clip", "file": f, "in": 0.0, "t0": m(a), "t1": m(b), "h": 620, "cx": 1470, "cy": 470,
                             "anim": "sticker", "style": "ab"})
        else:
            elements.append({"type": "card", "img": A.photo_file(f), "t0": m(a), "t1": m(b), "cx": 1470, "cy": 450, "anim": "sticker"})
        whoosh(a, -19, 0.1, "whoosh"); pop(a + 0.06, -19)

    # ---- word captions: AB's, 1-2 words at a time, lowercase, no punctuation, a hard switch and a click on each
    PROPER = {"youtube", "tiktok", "shopify", "ricky", "monday", "friday", "ytd", "shorts", "store", "q&as", "g-wagon"}

    def capword(w):
        t = clean(w)
        if t.lower() in PROPER or t == "I" or t.startswith("I'") or any(c.isupper() for c in t[1:]):
            return t
        return t[:1].lower() + t[1:]

    def hidden(x):
        return (any(a - 0.05 <= x < b for a, b in no_caps) or any(p["t0"] <= m(x) < p["t1"] for p in plates)
                or any(a <= x < b for a, b in SCREEN))

    groups, cur = [], []
    for i, w in enumerate(words):
        if hidden(w["s"]):
            if cur:
                groups.append(cur); cur = []
            continue
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end = (nxt is None or hidden(nxt["s"]) or w["w"][-1] in ".?!," or (nxt["s"] - w["e"]) > 0.2 or len(cur) >= 2
               or len(" ".join(clean(x["w"]) for x in cur)) >= 13
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
        if c1 - c0 < 0.1:
            continue
        text = " ".join(capword(x["w"]) for x in g)
        events += shadowed(2, c0, c1, "Cap", (960, 885), text)
        pop(g[0]["s"], -27)

    # ---- AB's dark fade along the bottom, under the word captions, on every face shot
    covered = sorted([(p["t0"], p["t1"]) for p in plates] + [(m(a), m(b)) for a, b in SCREEN] + [(m(SPLIT[0]), m(SPLIT[1]))])
    stretches, t = [], 0.0
    for a, b in covered:
        if a - t > 0.6:
            stretches.append((t, a))
        t = max(t, b)
    if total - t > 0.6:
        stretches.append((t, total))
    for s0, s1 in stretches:
        elements.insert(0, {"type": "card", "img": A.gradient("bottom"), "t0": s0, "t1": s1, "cx": 960, "cy": 540, "anim": "overlay"})

    # ---- zooms with intent (no pulsing): a push on the lines that carry weight, plus a steady tighter frame for
    #      Ricky's panel in the split screen
    zooms = [{"keys": [(m(t), z) for t, z in K]} for K in ZOOMS] + [{"keys": [(m(SPLIT[0]), 1.15), (m(SPLIT[1]), 1.15)]}]
    side_w = [(m(a), m(b)) for _, a, b, _ in SIDE]
    for z in zooms[:-1]:
        a0, a1 = z["keys"][0][0], z["keys"][-1][0]
        assert not any(a0 < b and a < a1 for a, b in side_w), ("zoom over side text", z)
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
    json.dump(edl, open(f"{outdir}/edlB4.json", "w"), indent=1)
    print("fonts:", FONT_NAMES)
    print(f"{total:.1f}s; plates {len(plates)}, elements {len(elements)}, zoom stretches {len(zooms)}, "
          f"caption groups {len(groups)}, sfx {len(sfx)}")


if __name__ == "__main__":
    main()
