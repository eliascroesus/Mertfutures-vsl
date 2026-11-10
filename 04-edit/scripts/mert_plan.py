"""Edit plan for Mert's VSL: Iman Gadzhi-style motion graphics (black plate with a lime glow, wide caps blurring in
letter by letter as he says each word, a lime handwritten line under headlines) with AB Nasdaq's structure (word
captions, side text in the empty part of the frame, a split screen for the offer, slow push-ins on the heavy lines).

Every element is bound to the words he says (times in the cut video), so nothing is placed by hand.

    python mert_plan.py            # writes /home/user/work/mert/plan.json
"""
import json, re, sys

sys.path.insert(0, "/home/user/work/scripts")
from ty_plan import load_words, mapper, norm

D = "/home/user/work/mert"
LEAD = 0.06

# what Whisper misheard (or his phrasing that reads wrong as a caption) -> what the caption shows
FIX = {"mertz": "Mert", "sp500": "S&P 500", "sp": "S&P", "reached": "reads", "seek": "take", "twitch": "this",
       "mentorships": "mentorship", "evolution": "evaluations", "oneonone": "1-on-1"}


class Edit:
    def __init__(self):
        c = json.load(open(f"{D}/cuts.json"))
        self.keep = [tuple(k) for k in c["keep"]]
        out, self.dur = mapper(self.keep)
        W = load_words(f"{D}/transcript.json")[c["start_word"]:]
        self.words = []
        for i, w in enumerate(W):
            n = norm(w["w"])
            d = re.sub(r"[,.!?;:]", "", w["w"])
            d = FIX.get(n, d)
            self.words.append({"w": d, "raw": w["w"], "s": round(out(w["s"]), 3), "e": round(out(w["e"]), 3), "n": n})
        self.fix_phrase("deep off market", ["Depth", "of", "market"])
        self.fix_phrase("someone check my work", ["someone", "checks", "my", "work"])
        self.fix_phrase("a mistake get catch you", ["a", "mistake", "gets", "caught", "–"])
        self.fix_phrase("i seek trade", ["I", "take", "the trade"])
        self.fix_phrase("because it's almost", ["because", "it", "almost"])
        self.fix_phrase("then i switched sp", ["then", "I", "switched to", "S&P"])
        self.toks = [w["n"] for w in self.words]
        self.scenes, self.leaks, self.off, self.zk, self.hl, self.sfx = [], [], [], [[0.0, 1.0]], [], []

    def fix_phrase(self, phrase, disp):
        i = self.find(phrase)
        for k, d in enumerate(disp):
            self.words[i + k]["w"] = d
        self.toks = [w["n"] for w in self.words]

    # ---------------------------------------------------------------- lookup
    def find(self, phrase, after=0.0):
        p = [norm(x) for x in phrase.split()]
        toks = [w["n"] for w in self.words]
        for i in range(len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p and self.words[i]["s"] >= after - 1e-6:
                return i
        raise ValueError(f"'{phrase}' not found")

    def T(self, phrase, after=0.0):
        return self.words[self.find(phrase, after)]["s"]

    def E(self, phrase, after=0.0):
        i = self.find(phrase, after)
        return self.words[i + len(phrase.split()) - 1]["e"]

    def rows(self, phrase, spec, after=0.0):
        """[(display words, style, size, colour[, extras]), ...]: each display word appears when its spoken word does
        ('_' = a spoken word with nothing shown)."""
        k = self.find(phrase, after)
        n = sum(len(s[0].split()) for s in spec)
        assert n == len(phrase.split()), (phrase, n, len(phrase.split()))
        rows = []
        for sp in spec:
            text, style, size, color = sp[:4]
            ws = []
            for d in text.split():
                ws.append([d.replace("~", " "), self.words[k]["s"]])
                k += 1
            rows.append(dict({"words": ws, "style": style, "size": size, "color": color}, **(sp[4] if len(sp) > 4 else {})))
        return rows

    # ---------------------------------------------------------------- building blocks
    def card(self, kind, t0, t1, captions_off=True, sweep_in=True, sweep_out=True, **kw):
        """A full-screen graphic on the brand plate."""
        self.scenes.append(dict(kind=kind, t0=round(t0, 3), t1=round(t1, 3), full=True, **kw))
        for t, on in ((t0, sweep_in), (t1, sweep_out)):
            if on and not any(abs(l["t"] - t) < 0.05 for l in self.leaks):
                self.leaks.append({"t": round(t, 3), "s": 0.75})
        if sweep_in:
            self.sfx.append(["whoosh", round(t0 - 0.18, 3), 1.0])
        if captions_off:
            self.off.append([t0, t1])
        self.snap(t0)
        if sweep_out:
            self.snap(t1, to=1.0)

    def text(self, phrase, spec, t_out, cy=520, after=0.0, **kw):
        t0 = self.T(phrase, after) - LEAD
        self.card("iman", t0, t_out, rows=self.rows(phrase, spec, after), cy=cy, **kw)
        return t0

    def side(self, phrase, spec, t_out, cy=470, after=0.0, t_in=None):
        """AB's side text in the empty wall left of him, in Iman's type."""
        t0 = (t_in if t_in is not None else self.T(phrase, after)) - 0.25
        self.scenes.append(dict(kind="side", t0=round(t0, 3), t1=round(t_out, 3), rows=self.rows(phrase, spec, after), cy=cy))
        self.off.append([t0, t_out])
        self.sfx.append(["tick", round(self.T(phrase, after), 3), 0.8])

    def headline(self, phrase, spec, t_out, after=0.0):
        """Iman's headline over the talking head: wide caps with a lime handwritten line under it."""
        t0 = self.T(phrase, after) - 0.2
        self.scenes.append(dict(kind="headline", t0=round(t0, 3), t1=round(t_out, 3), rows=self.rows(phrase, spec, after)))
        self.off.append([t0, t_out])
        self.sfx.append(["whoosh_soft", round(t0 - 0.05, 3), 0.7])

    def callout(self, phrase, color="lime", after=0.0):
        """Iman's callout word: the key phrase replaces the subtitle in big caps."""
        i = self.find(phrase, after)
        self.hl.append({"i": i, "n": len(phrase.split()), "color": color})
        self.sfx.append(["whoosh_soft", round(self.words[i]["s"] - 0.12, 3), 0.55])

    def push(self, phrase, z, d=1.7, after=0.0, at=None):
        t = at if at is not None else self.T(phrase, after)
        last = self.zk[-1]
        self.zk.append([round(t, 3), last[1]])
        self.zk.append([round(t + d, 3), z])

    def pull(self, t, d=0.7, z=1.0):
        last = self.zk[-1]
        self.zk.append([round(t, 3), last[1]])
        self.zk.append([round(t + d, 3), z])

    def snap(self, t, to=1.0):
        last = self.zk[-1]
        if last[1] != to:
            self.zk.append([round(t - 0.001, 3), last[1]])
            self.zk.append([round(t, 3), to])

    # ---------------------------------------------------------------- output
    def write(self):
        self.zk.append([round(self.dur, 3), self.zk[-1][1]])
        off = self.off
        hl_at = {}
        for h in self.hl:
            for k in range(h["i"], h["i"] + h["n"]):
                hl_at[k] = h

        def is_off(t):
            return any(a - 0.01 <= t < b for a, b in off)

        caps, cur, W = [], None, self.words
        for k, w in enumerate(W):
            if is_off(w["s"]):
                if cur:
                    caps.append(cur); cur = None
                continue
            h = hl_at.get(k)
            brk = cur is None
            if cur:
                prev_h = hl_at.get(k - 1)
                if h is not prev_h:
                    brk = True
                elif h is None:
                    last = cur["words"][-1]
                    n_ch = sum(len(x[0]) for x in cur["words"]) + len(w["w"])
                    if (re.search(r"[,.!?]$", W[k - 1]["raw"]) or len(cur["words"]) >= 3
                            or (len(cur["words"]) >= 2 and n_ch > 12) or w["s"] - W[k - 1]["e"] > 0.3):
                        brk = True
            if brk:
                if cur:
                    caps.append(cur)
                cur = {"words": [], "hl": h["color"] if h else None}
            cur["words"].append([w["w"].upper() if h else w["w"], w["s"]])
            cur["end"] = w["e"]
        if cur:
            caps.append(cur)
        for c in caps:
            c["t0"] = c["words"][0][1]
        for c, nxt in zip(caps, caps[1:] + [None]):
            c["t1"] = round(min(nxt["t0"] if nxt else self.dur, c["end"] + (0.7 if c["hl"] else 0.5)), 3)
            for a, b in off:
                if c["t0"] < a < c["t1"]:
                    c["t1"] = a
        self.leaks.sort(key=lambda x: x["t"])
        self.zk.sort(key=lambda k: k[0])
        self.scenes.sort(key=lambda s: s["t0"])
        plan = {"keep": [[round(a, 4), round(b, 4)] for a, b in self.keep], "dur": round(self.dur, 3),
                "anchor": [980, 560], "intro_t1": next(s["t1"] for s in self.scenes if s["kind"] == "intro"), "words": self.words, "scenes": self.scenes, "leaks": self.leaks, "zoom": self.zk,
                "captions": caps, "off": off, "sfx": sorted(self.sfx, key=lambda s: s[1])}
        json.dump(plan, open(f"{D}/plan.json", "w"), indent=1)
        pushes = sum(1 for a, b in zip(self.zk, self.zk[1:]) if b[1] > a[1] + 1e-3)
        full = sum(1 for s in self.scenes if s.get("full"))
        print(f"{self.dur:.2f}s: {full} full-screen graphics, {len(self.scenes) - full} overlays, {pushes} push-ins, "
              f"{len(self.hl)} callouts, {len(caps)} caption groups, {len(self.sfx)} sound effects")


def build():
    e = Edit()
    T, E = e.T, e.E

    # 0:00 who he is, on the empty wall beside him
    e.scenes.append(dict(kind="intro", t0=0.0, t1=round(T("in the next four minutes") - LEAD, 3),
                         rows=e.rows("i am mertz i trade sp500 and nasdaq futures and the last two years trading has been my main income",
                                     [("I'M _", "sub", 40, "dim"), ("MERT.", "big", 230, "white", {"ul": True}),
                                      ("_ _ S&P~500 & NASDAQ FUTURES", "sub", 34, "lime"),
                                      ("_ _ _ 2 YEARS — _ _ _ MAIN INCOME", "sub", 34, "white")])))
    e.off.append([0.0, T("in the next four minutes") - LEAD])

    # the promise
    e.text("in the next four minutes i will show you how i stopped the guessing market and started reading real-time auction",
           [("IN THE NEXT 4 MINUTES _ _ _ _ _ _", "sub", 34, "dim"),
            ("STOP _ GUESSING. _", "big", 112, "white"),
            ("_ START READING~THE", "sub", 38, "white"),
            ("REAL-TIME AUCTION.", "big", 96, "lime", {"ul": True})],
           T("if you are watching this") - LEAD, cy=530)
    e.push("if you are watching this", 1.1, 2.4)

    # everything they've tried, crossed out
    e.text("you have watched videos you have tried strategies maybe you have paid a course it still doesn't work",
           [("_ _ WATCHED VIDEOS", "sub", 46, "white", {"strike": True}),
            ("_ _ TRIED STRATEGIES", "sub", 46, "white", {"strike": True}),
            ("_ _ _ PAID A COURSE", "sub", 46, "white", {"strike": True}),
            ("IT STILL DOESN'T WORK.", "big", 92, "red")],
           T("you take a trade") - LEAD, cy=520, sweep_out=False)

    # the trade that stops you out and then runs without you
    e.card("chart", T("you take a trade") - LEAD, T("you have a good week") - LEAD, sweep_in=False, captions_off=False,
           t_entry=T("take a trade"), t_against=T("goes against you"), t_close=T("close it"),
           t_run=T("price moves exactly"), t_run_end=E("where you expected"))
    e.callout("takes it all back", "red")
    e.push("you have a good week", 1.1, 2.5)

    e.text("you finally pass a challenge and account is gone one week later",
           [("_ FINALLY PASSED A CHALLENGE", "sub", 40, "white"),
            ("_ ACCOUNT _ GONE.", "big", 136, "red"),
            ("ONE WEEK LATER.", "sub", 40, "white")],
           T("and you start thinking") - LEAD, plate="red", chart=True, chart_delay=0.9, chart_dur=1.2)
    e.push("maybe trading isn't for you", 1.14, 1.6)

    e.headline("problem is not you it's how you learn to trade",
               [("PROBLEM IS NOT YOU.", "big", 92, "white"),
                ("it's how you learned to trade", "hand", 66, "lime")],
               T("nobody shows you") - 0.1)

    e.text("nobody shows you who is buying and who is selling right now",
           [("NOBODY SHOWS YOU", "sub", 38, "dim"),
            ("WHO IS BUYING", "big", 110, "lime"),
            ("_ WHO IS SELLING", "big", 110, "red"),
            ("RIGHT NOW.", "sub", 38, "white")],
           T("so every trade is just guessing") - LEAD, cy=530)
    e.callout("just guessing", "red")
    e.push("so every trade", 1.12, 1.6)

    e.text("and if your strategy only works because of your win rate that's not so different from roulette",
           [("_ IF YOUR STRATEGY ONLY WORKS", "sub", 38, "white"),
            ("BECAUSE OF YOUR WIN RATE", "big", 80, "white"),
            ("_ NOT SO DIFFERENT FROM", "sub", 38, "dim"),
            ("ROULETTE.", "big", 170, "red", {"ul": True})],
           T("i know because") - LEAD, cy=520)
    e.push("i know because", 1.08, 1.8)
    e.push("quit trading", 1.2, 0.9)
    e.callout("quit trading", "red")

    # the story
    e.pull(T("i will tell you what changed") + 0.2, 1.4)
    e.side("i found trading at 16 in a gaming discord",
           [("_ _ _ AGE", "sub", 32, "dim"), ("16", "big", 230, "lime"), ("_ _ GAMING DISCORD", "sub", 32, "white")],
           T("the older guys") + 1.2, cy=470)
    e.push("about crypto", 1.12, 4.0)
    e.callout("i was hooked", "lime")
    e.pull(T("then i found leverage") - 1.1, 0.7)
    e.side("then i found leverage in 2021 i lost money",
           [("_ _ _ LEVERAGE", "sub", 34, "lime"), ("_ 2021", "big", 170, "white"),
            ("_ LOST MONEY.", "sub", 34, "red", {"strike": False})],
           T("so i moved to forex") - 0.05, cy=470)
    e.text("so i moved to forex ict gold euro dollar i paid for a mentorship i studied economics",
           [("_ _ MOVED TO", "sub", 32, "dim"),
            ("FOREX ICT GOLD EUR/USD _", "big", 84, "white"),
            ("_ PAID FOR A MENTORSHIP.", "sub", 40, "white"),
            ("_ STUDIED ECONOMICS.", "sub", 40, "white")],
           T("and slowly i saw it") - LEAD, cy=520)
    e.push("and slowly i saw it", 1.12, 2.6)
    e.callout("a win rate game", "red")
    e.push("of losing my time", 1.22, 2.6)
    e.callout("my young years", "lime")
    e.pull(T("my family has businesses") + 0.2, 2.5, 1.06)
    e.push("i was close to quitting", 1.18, 1.0)
    e.callout("close to quitting", "red")
    e.headline("then a friend told me learn order flow",
               [("then a friend told me", "hand", 62, "lime"), ("LEARN ORDER FLOW.", "big", 104, "white")],
               T("for the first time") + 0.6)
    e.push("for the first time", 1.26, 2.6)
    e.callout("the real market", "lime")

    # depth of market: who is really buying / selling
    e.card("dom", T("deep off market") - LEAD, T("then i switched sp") - LEAD,
           rows=e.rows("deep off market level two data",
                       [("DEPTH OF MARKET", "sub", 36, "white"), ("LEVEL 2 DATA", "big", 66, "lime", {"ul": True})]),
           t_buy=T("who is really buying"), t_sell=T("who is really selling"))

    e.text("first payout small then two funded accounts paying me",
           [("FIRST PAYOUT. SMALL.", "sub", 38, "dim"), ("_ 2", "big", 260, "lime"),
            ("FUNDED ACCOUNTS PAYING ME.", "sub", 44, "white")],
           T("that's when i saw it") - LEAD, cy=520)
    e.push("that's when i saw it", 1.12, 1.8)
    e.callout("a real job", "lime")
    e.pull(T("so i took a risk") - 0.9, 0.6)
    e.side("so i took a risk and moved to dubai",
           [("_ _ TOOK A RISK", "sub", 34, "lime"), ("_ _ _ DUBAI.", "big", 140, "white")],
           T("but the strategy alone") + 0.3, cy=470)
    e.push("is not what fixed me", 1.15, 2.2)

    # the two things
    e.text("two things", [("2", "big", 300, "lime"), ("THINGS.", "sub", 52, "white")],
           T("first i stopped predicting") - LEAD, cy=500, sweep_out=False)
    e.text("first i stopped predicting", [("01", "big", 150, "lime"), ("_ STOPPED PREDICTING.", "big", 96, "white", {"ul": True})],
           T("every morning before") - LEAD, cy=520, sweep_in=False)
    e.push("every morning before", 1.1, 3.0)
    e.pull(T("i built my own ai") - 1.0, 0.6)
    e.side("i built my own ai tool octomics reached the news and economic data and gives me fundamental bias",
           [("_ _ MY OWN AI TOOL _", "sub", 32, "lime"), ("_ _ NEWS + ECONOMIC DATA", "sub", 32, "white"),
            ("_ _ _ FUNDAMENTAL", "big", 60, "white"), ("BIAS.", "big", 120, "lime")],
           T("then i marked my location") - LEAD, cy=480)
    e.card("steps", T("then i marked my location") - LEAD, T("second someone check") - LEAD,
           t_loc=T("location with volume"), t_flow=T("order flow confirms"), t_rule=T("no confirmation no trade"),
           t_rule2=T("no trade", after=T("no confirmation") + 0.5),
           t_recap=[T("bias location order flow"), T("location order flow", after=T("bias location")),
                    T("order flow", after=T("bias location order"))])
    e.sfx += [["pop", round(T("location with volume"), 3), 0.7], ["pop", round(T("order flow confirms"), 3), 0.7]]

    e.text("second someone check my work that's the part nobody sells you",
           [("02", "big", 150, "lime"), ("SOMEONE CHECKS MY WORK.", "big", 80, "white", {"ul": True}),
            ("_ THE PART NOBODY SELLS YOU.", "sub", 38, "dim")],
           T("and for me it changed") - LEAD, cy=520)
    e.push("and for me it changed", 1.14, 1.6)
    e.callout("changed everything", "lime")
    e.pull(T("let me be honest") + 0.1, 1.2)
    e.push("i am a trader first", 1.2, 0.9)
    e.callout("a trader first", "lime")
    e.pull(T("i opened my instagram") - 0.2, 1.6, 1.04)
    e.push("people kept asking me", 1.16, 2.0)

    e.text("i don't sell signals i never have",
           [("I DON'T SELL", "sub", 46, "white"), ("SIGNALS.", "big", 170, "white", {"strike": True}),
            ("_ NEVER HAVE.", "sub", 40, "dim")],
           T("and i keep it small") - LEAD, cy=520)
    e.sfx.append(["swipe", round(T("signals") + 0.3, 3), 0.8])
    e.push("so i can watch every", 1.15, 2.2)
    e.callout("every student's trade", "lime")

    e.text("it's a one-on-one mentorships", [("_ _ 1-ON-1", "big", 200, "lime"), ("MENTORSHIP.", "big", 92, "white", {"ul": True})],
           T("weeks one to eight") - LEAD, cy=520)

    # the offer: split screen building line by line
    t_w2 = T("weeks nine to 12")
    e.scenes.append(dict(kind="split", t0=round(T("weeks one to eight") - LEAD, 3), t1=round(T("this is for you") - 0.3, 3),
                         t_swap=round(t_w2 - 0.3, 3),
                         a=e.rows("weeks one to eight we will build your process auction market theory volume profile footprint my pre-market analysis and your rules",
                                  [("WEEKS 1–8 _ _", "sub", 32, "lime"), ("_ _ BUILD YOUR PROCESS", "big", 58, "white"),
                                   ("AUCTION MARKET THEORY", "item", 40, "white"), ("VOLUME PROFILE", "item", 40, "white"),
                                   ("FOOTPRINT", "item", 40, "white"), ("_ PRE-MARKET ANALYSIS", "item", 40, "white"),
                                   ("_ YOUR RULES", "item", 40, "white")]),
                         b=e.rows("weeks nine to 12 i follow you you trade live i review it so a mistake get catch you same day not after account is gone and we do pre-market analysis together live",
                                  [("WEEKS 9–12 _ _", "sub", 32, "lime"), ("_ FOLLOW YOU.", "big", 58, "white"),
                                   ("YOU TRADE LIVE", "item", 40, "white"), ("I REVIEW IT", "item", 40, "white"),
                                   ("_ _ MISTAKES CAUGHT _ _ SAME~DAY _ _ _ _ _ _", "item", 40, "white"),
                                   ("_ _ _ PRE-MARKET _ TOGETHER, LIVE", "item", 40, "white")])))
    e.off.append([T("weeks one to eight") - LEAD, T("this is for you") - 0.3])
    e.sfx.append(["whoosh", round(T("weeks one to eight") - 0.25, 3), 0.9])
    e.sfx.append(["whoosh_soft", round(t_w2 - 0.35, 3), 0.7])
    for ph in ["auction market theory", "volume profile footprint", "footprint my", "pre-market analysis and",
               "your rules", "you trade live", "i review it", "mistake get catch", "pre-market analysis together"]:
        e.sfx.append(["tick", round(T(ph, after=180), 3), 0.55])
    e.snap(T("weeks one to eight") - LEAD)

    e.headline("this is for you if you already know strategy and your account doesn't show it yet",
               [("THIS IS FOR YOU.", "big", 92, "white"),
                ("if you already know strategy, but your account doesn't show it yet", "hand", 54, "lime")],
               T("think about what") - 0.1)
    e.push("this is for you", 1.07, 4.5)
    e.push("think about what", 1.17, 2.0)
    e.callout("cost you this year", "red")

    # the call to action
    e.card("cta", T("application is below") - LEAD, T("if it's not") - LEAD,
           rows=e.rows("application is below for a short question if it looks like a fit you book a call with me",
                       [("APPLICATION", "big", 120, "white"), ("_ BELOW.", "big", 120, "lime", {"ul": True}),
                        ("_ _ SHORT QUESTIONS", "sub", 34, "white"),
                        ("_ _ _ _ _ _ _ BOOK A CALL WITH ME.", "sub", 34, "lime")]), cy=430)
    e.push("if it's not", 1.12, 3.0)
    e.callout("see you inside", "lime")
    e.write()


if __name__ == "__main__":
    build()
