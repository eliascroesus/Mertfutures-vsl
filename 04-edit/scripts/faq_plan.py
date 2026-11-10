"""Edit plans for Ricky's FAQ videos, in the thank-you v2 style without music: AB's word captions, Iman Gadzhi-style
cards on the brand plate (wide caps blurring in as he says each word), glass icon tiles, purple light sweeps, and only
slow push-ins on key lines that hold until the next card.

    python faq_plan.py [name ...]        # writes edit/faq/<name>/plan.json
"""
import json, os, re, subprocess, sys

sys.path.insert(0, "/home/user/work/scripts")
from ty_plan import WORK, load_words, plan_cuts, mapper, norm, display

RAW = f"{WORK}/faq/raw"
OUT = f"{WORK}/edit/faq"
VOICE_CHAIN = open("/home/user/rickyvsl-clips/04-edit/scripts/voice_chain.txt").read().strip()
LEAD = 0.06


class Edit:
    def __init__(self, name, anchor):
        self.name, self.anchor = name, anchor
        self.raw = f"{RAW}/{name}.mp4"
        os.makedirs(f"{OUT}/{name}", exist_ok=True)
        self.voice = f"{OUT}/{name}/voice_proc.wav"
        if not os.path.exists(self.voice):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", self.raw, "-vn", "-ac", "2", "-ar", "48000", "-af",
                            VOICE_CHAIN, "-c:a", "pcm_s24le", self.voice], check=True)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    self.raw], capture_output=True, text=True).stdout)
        W = load_words(f"{RAW}/{name}.json")
        self.keep = plan_cuts(W, self.voice, dur)
        out, self.dur = mapper(self.keep)
        self.words, prev = [], ""
        for w in W:
            d = display(w["w"], prev)
            self.words.append({"w": d, "raw": w["w"], "s": round(out(w["s"]), 3), "e": round(out(w["e"]), 3),
                               "n": norm(w["w"])})
            prev = d
        self.toks = [w["n"] for w in self.words]
        self.scenes, self.leaks, self.off, self.zk = [], [], [], [[0.0, 1.0]]

    # -- lookup
    def find(self, phrase):
        p = [norm(x) for x in phrase.split()]
        for i in range(len(self.toks) - len(p) + 1):
            if self.toks[i:i + len(p)] == p:
                return i
        raise ValueError(f"{self.name}: '{phrase}' not found")

    def T(self, phrase):
        return self.words[self.find(phrase)]["s"]

    def rows(self, phrase, spec):
        """[(display words, style, size, colour[, extras]), ...] bound word for word to the spoken phrase."""
        k = self.find(phrase)
        n = sum(len(s[0].split()) for s in spec)
        assert n == len(phrase.split()), (self.name, phrase, n, len(phrase.split()))
        rows = []
        for sp in spec:
            text, style, size, color = sp[:4]
            ws = []
            for d in text.split():
                ws.append([d, self.words[k]["s"]])
                k += 1
            rows.append(dict({"words": ws, "style": style, "size": size, "color": color}, **(sp[4] if len(sp) > 4 else {})))
        return rows

    # -- building blocks
    def card(self, kind, t0, t1, captions_off=True, leak_in=True, leak_out=True, **kw):
        self.scenes.append(dict(kind=kind, t0=round(t0, 3), t1=round(t1, 3), **kw))
        for t, on in ((t0, leak_in), (t1, leak_out)):
            if on and not any(abs(l["t"] - t) < 0.05 for l in self.leaks):
                self.leaks.append({"t": round(t, 3), "s": 1.0})
        if captions_off:
            self.off.append([t0, t1])
        self.snap(t0)

    def text(self, phrase, spec, t_out, cy=520, **kw):
        t0 = self.T(phrase) - LEAD
        self.card("iman", t0, t_out, rows=self.rows(phrase, spec), cy=cy, **kw)
        return t0

    def push(self, phrase, z, d=1.7):
        t = self.T(phrase)
        last = self.zk[-1]
        self.zk.append([round(t, 3), last[1]])
        self.zk.append([round(t + d, 3), z])

    def snap(self, t):
        last = self.zk[-1]
        if last[1] != 1.0:
            self.zk.append([round(t - 0.001, 3), last[1]])
            self.zk.append([round(t, 3), 1.0])

    # -- output
    def write(self):
        self.zk.append([round(self.dur, 3), self.zk[-1][1]])
        off = self.off

        def is_off(t):
            return any(a - 0.01 <= t < b for a, b in off)

        caps, cur, W = [], None, self.words
        for k, w in enumerate(W):
            if is_off(w["s"]):
                if cur:
                    caps.append(cur); cur = None
                continue
            brk = cur is None
            if cur:
                last = cur["words"][-1]
                n_ch = sum(len(x[0]) for x in cur["words"]) + len(w["w"])
                glued = last[0] == "1-on-1" and w["w"] == "Mentorship"
                if not glued and (re.search(r"[,.!?]$", W[k - 1]["raw"]) or len(cur["words"]) >= 3
                                  or (len(cur["words"]) >= 2 and n_ch > 11) or w["s"] - W[k - 1]["e"] > 0.3):
                    brk = True
            if brk:
                if cur:
                    caps.append(cur)
                cur = {"words": []}
            cur["words"].append([w["w"], w["s"]])
            cur["end"] = w["e"]
        if cur:
            caps.append(cur)
        for c in caps:
            c["t0"] = c["words"][0][1]
        for c, nxt in zip(caps, caps[1:] + [None]):
            c["t1"] = round(min(nxt["t0"] if nxt else self.dur, c["end"] + 0.5), 3)
            for a, b in off:
                if c["t0"] < a < c["t1"]:
                    c["t1"] = a
        self.leaks.sort(key=lambda x: x["t"])
        self.zk.sort(key=lambda k: k[0])
        plan = {"raw": self.raw, "voice": self.voice, "anchor": self.anchor, "keep": [[round(a, 4), round(b, 4)] for a, b in self.keep],
                "dur": round(self.dur, 3), "words": self.words, "scenes": self.scenes, "leaks": self.leaks,
                "zoom": self.zk, "captions": caps, "off": off}
        json.dump(plan, open(f"{OUT}/{self.name}/plan.json", "w"), indent=1)
        pushes = sum(1 for a, b in zip(self.zk, self.zk[1:]) if b[1] > a[1])
        print(f"{self.name}: {self.dur:.2f}s, {len(self.scenes)} cards, {len(self.leaks)} sweeps, {pushes} push-ins, "
              f"{len(caps)} caption phrases")


# ------------------------------------------------------------------ the four videos
def howmuchtime():
    e = Edit("howmuchtime", [889, 585])
    e.push("while i was in school", 1.1, 2.0)
    t_swap = e.T("six different products") - 0.04
    e.text("two to three hours a day and i was still able to make dropshipping work and run",
           [("2 – 3 HOURS", "big", 200, "purple"), ("A DAY.", "sub", 50, "white"),
            ("_ _ _ STILL ABLE TO MAKE DROPSHIPPING WORK. _ _", "sub", 40, "white")], t_swap, cy=500, leak_out=False)
    e.card("iman", t_swap, e.T("so no matter what") - LEAD, leak_in=False, cy=500,
           rows=e.rows("six different products every single month",
                       [("6 _ PRODUCTS", "big", 190, "purple"), ("EVERY SINGLE MONTH.", "sub", 50, "white")]))
    e.push("no matter what your position", 1.12, 1.8)
    e.write()


def issaturated():
    e = Edit("issaturated", [890, 588])
    e.push("2024 method", 1.1, 1.6)
    e.text("honestly doesn't work anymore",
           [("HONESTLY", "sub", 46, "white"), ("DOESN'T WORK", "big", 140, "red"), ("ANYMORE.", "big", 140, "red")],
           e.T("running a saturated") - LEAD, plate="red", chart=True, chart_delay=0.15, chart_dur=1.1)
    e.card("tiles", e.T("tiktok and instagram") - LEAD, e.T("but when you run") - LEAD, tile_y=400, spacing=420,
           items=[["note", "TIKTOK", e.T("tiktok and")], ["camera", "INSTAGRAM", e.T("instagram makes")]],
           rows=e.rows("makes it incredibly difficult to get views and sales",
                       [("_ _ INCREDIBLY DIFFICULT", "big", 84, "red"), ("TO GET VIEWS AND SALES.", "sub", 44, "white")]),
           rows_cy=760)
    e.text("strictly on youtube you are able to capitalize so much on the youtube audience",
           [("STRICTLY ON", "sub", 46, "white"), ("YOUTUBE.", "big", 180, "purple"),
            ("_ _ _ _ CAPITALIZE _ _ ON THE YOUTUBE AUDIENCE.", "sub", 40, "white")],
           e.T("and as well as that") - LEAD, icon="play", cy=600)
    e.push("run saturated products that", 1.12, 1.8)
    e.write()


def whoworkwith():
    e = Edit("whoworkwith", [900, 588])
    e.text("with me personally not some other assistant not some other coach",
           [("WITH ME", "sub", 46, "white"), ("PERSONALLY.", "big", 150, "purple"),
            ("NOT SOME OTHER ASSISTANT,", "sub", 42, "white", {"strike": True}),
            ("NOT SOME OTHER COACH.", "sub", 42, "white", {"strike": True})], e.T("you're actually going") - LEAD)
    e.push("hold your hand", 1.1, 1.7)
    e.card("tiles", e.T("picking a product") - LEAD, e.T("and i can help") - LEAD, tile_y=440, spacing=420,
           items=[["box", "PRODUCT", e.T("product making")], ["play", "VIDEOS", e.T("videos and")],
                  ["bag", "STORE", e.T("store so")]],
           rows=e.rows("so you don't have to do anything yourself",
                       [("SO YOU DON'T HAVE TO DO", "sub", 42, "white"), ("ANYTHING YOURSELF.", "big", 92, "purple")]),
           rows_cy=780)
    e.push("help you through the entire", 1.12, 1.6)
    e.write()


def whatsinside():
    e = Edit("Whatsinside", [914, 596])
    e.push("you will get access to seven", 1.08, 1.4)
    e.text("seven different things", [("7", "big", 320, "purple"), ("DIFFERENT THINGS.", "sub", 50, "white")],
           e.T("number one is") - LEAD, cy=500)
    e.text("number one is the full six-hour video course on youtube dropshipping",
           [("_ 01 _ _", "big", 150, "purple"), ("FULL 6-HOUR VIDEO COURSE", "big", 84, "white"),
            ("ON YOUTUBE DROPSHIPPING.", "sub", 44, "white")], e.T("number two is") - LEAD)
    e.text("number two is inner circle community access",
           [("_ 02 _", "big", 150, "purple"), ("INNER CIRCLE", "big", 104, "white"), ("COMMUNITY ACCESS.", "sub", 46, "white")],
           e.T("you will get access to the community") - LEAD)
    e.push("making money in the dropshipping", 1.1, 1.8)
    e.text("number three is weekly one-on-one calls with me",
           [("_ 03 _", "big", 150, "purple"), ("WEEKLY 1-ON-1 CALLS", "big", 92, "white"), ("WITH ME.", "sub", 46, "white")],
           e.T("personally you can ask") - LEAD)
    e.push("never stuck for the next", 1.1, 1.6)
    t_tiles = e.T("product research competitor") - LEAD
    e.text("number four is four weekly group coaching calls",
           [("_ 04 _", "big", 150, "purple"), ("4 WEEKLY GROUP", "big", 96, "white"), ("COACHING CALLS.", "sub", 46, "white")],
           t_tiles, leak_out=False)
    e.card("tiles", t_tiles, e.T("so you're never stuck at all") - LEAD, leak_in=False, tile_y=500, spacing=375,
           items=[["box", "PRODUCTS", e.T("product research competitor")], ["user", "COMPETITORS", e.T("competitor research")],
                  ["play", "VIDEOS", e.T("videos stores")], ["bag", "STORES", e.T("stores and questions")],
                  ["chat", "Q&A", e.T("questions and answers")]])
    e.push("always have your questions", 1.1, 1.6)
    e.text("number five is direct access to my personal phone number not an assistant",
           [("_ 05 _", "big", 150, "purple"), ("DIRECT ACCESS", "big", 104, "white"),
            ("TO MY PERSONAL PHONE NUMBER.", "sub", 44, "white"), ("NOT AN ASSISTANT.", "sub", 40, "white", {"strike": True})],
           e.T("so you can ask me") - LEAD)
    e.push("never stuck trying", 1.1, 1.6)
    e.text("number six is product sign off",
           [("_ 06 _", "big", 150, "purple"), ("PRODUCT SIGN-OFF. _", "big", 104, "white")], e.T("so before you ever") - LEAD)
    e.push("ask me personally if", 1.08, 1.6)
    e.push("never wasting time", 1.16, 1.6)
    e.text("number seven branded store builder",
           [("_ 07", "big", 150, "purple"), ("BRANDED STORE BUILDER.", "big", 92, "white")], e.T("me and you will build") - LEAD)
    e.push("look perfect", 1.1, 1.6)
    t0 = e.T("and that is what's inside") - LEAD
    items = ["VIDEO COURSE", "INNER CIRCLE", "WEEKLY 1-ON-1 CALLS", "GROUP COACHING", "MY PHONE NUMBER",
             "PRODUCT SIGN-OFF", "BRANDED STORE BUILDER"]
    recap = []
    for i, it in enumerate(items):                           # the seven, one line each, landing in quick succession
        recap.append({"words": [[f"{i + 1:02d}  {it}", t0 + 0.12 + 0.24 * i]], "style": "sub", "size": 40,
                      "color": "white"})
    e.card("iman", t0, e.T("and that is everything") - LEAD, rows=recap, cy=520)
    e.push("everything that you will get", 1.12, 1.8)
    e.write()


EDITS = {"howmuchtime": howmuchtime, "issaturated": issaturated, "whoworkwith": whoworkwith, "Whatsinside": whatsinside}

if __name__ == "__main__":
    for n in sys.argv[1:] or EDITS:
        EDITS[n]()
