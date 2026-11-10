"""Thank-you edit v2 (after review): AB's structure and captions, but every card in the Iman Gadzhi style (dark brand
plate, wide caps blurring in letter by letter as Ricky says them), only slow intentional push-ins that hold until
the next card (never a visible zoom out), and the 'Me And The Devil' song bed.

    python ty_plan2.py            # writes edit/ty2/plan.json
"""
import json, os, re, sys

sys.path.insert(0, "/home/user/work/scripts")
from ty_plan import WORK, load_words, plan_cuts, mapper, norm, display

OUT = f"{WORK}/edit/ty2"


def main():
    W = load_words()
    keep = plan_cuts(W)
    out, dur = mapper(keep)
    words, prev = [], ""
    for w in W:
        d = display(w["w"], prev)
        words.append({"w": d, "raw": w["w"], "s": round(out(w["s"]), 3), "e": round(out(w["e"]), 3), "n": norm(w["w"])})
        prev = d
    toks = [w["n"] for w in words]

    def find(phrase, after=0.0):
        p = [norm(x) for x in phrase.split()]
        for i in range(len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p and words[i]["s"] >= after - 1e-6:
                return i
        raise ValueError(phrase)

    def T(phrase, after=0.0):
        return words[find(phrase, after)]["s"]

    def rows(phrase, spec):
        """spec: [(display words, style, size, colour), ...] bound word for word to the spoken phrase."""
        i = find(phrase)
        n = sum(len(s[0].split()) for s in spec)
        assert n == len(phrase.split()), (phrase, spec)
        out_rows, k = [], i
        for text, style, size, color in spec:
            ws = []
            for d in text.split():
                ws.append([d, words[k]["s"]])
                k += 1
            out_rows.append({"words": ws, "style": style, "size": size, "color": color})
        return out_rows

    scenes, leaks, zk, off = [], [], [[0.0, 1.0]], []
    LEAD = 0.06

    def card(kind, t0, t1, captions_off=True, leak_in=True, leak_out=True, **kw):
        scenes.append(dict(kind=kind, t0=round(t0, 3), t1=round(t1, 3), **kw))
        if leak_in:
            leaks.append({"t": round(t0, 3), "s": 1.0})
        if leak_out:
            leaks.append({"t": round(t1, 3), "s": 1.0})
        if captions_off:
            off.append([t0, t1])
        snap(t0)

    def push(t, z, d=1.6):
        """A slow eased push-in that then holds (only ever inward; the card cut after it resets to wide)."""
        last = zk[-1]
        zk.append([round(t, 3), last[1]])
        zk.append([round(t + d, 3), z])

    def snap(t):
        last = zk[-1]
        if last[1] != 1.0:
            zk.append([round(t - 0.001, 3), last[1]])
            zk.append([round(t, 3), 1.0])

    def text(phrase, spec, t_out, cy=520, **kw):
        t0 = T(phrase) - LEAD
        card("iman", t0, t_out, rows=rows(phrase, spec), cy=cy, **kw)

    # 0:00-0:06 wide, still
    text("that 90% of other dropshippers couldn't do",
         [("_ 90%", "big", 250, "purple"), ("OF OTHER DROPSHIPPERS COULDN'T DO.", "sub", 46, "white")],
         T("and you are genuinely") - LEAD, cy=500)
    push(T("one step away"), 1.12, 1.8)
    t0 = T("the consistency the sales") - LEAD
    t_tiles = T("time location and financial freedom") - 0.04
    card("iman", t0, t_tiles, leak_out=False, cy=500,
         rows=rows("the consistency the sales", [("_ CONSISTENCY.", "big", 130, "white"), ("_ SALES.", "big", 130, "purple")]))
    card("tiles", t_tiles, T("and there is countless") - LEAD, leak_in=False,
         items=[["hourglass", "TIME", T("time location")], ["pin", "LOCATION", T("location and financial")],
                ["diamond", "FREEDOM", T("freedom you've")]])
    text("countless other dropshippers in the one-on-one mentorship",
         [("COUNTLESS OTHER DROPSHIPPERS", "big", 92, "white"), ("IN THE 1-ON-1 MENTORSHIP.", "sub", 44, "purple")],
         T("taking advantage of this") - LEAD)
    push(T("no reason why"), 1.1, 1.6)
    text("what are the next steps to joining the one-on-one mentorship",
         [("WHAT ARE THE", "sub", 44, "white"), ("NEXT STEPS", "big", 160, "purple"),
          ("TO JOINING THE 1-ON-1 MENTORSHIP?", "sub", 44, "white")], T("and as i'm speaking") - LEAD)
    card("app", T("is currently reviewing") - LEAD, T("and if you are") - LEAD, captions_off=False)
    push(T("phone is in your hand"), 1.13, 1.6)
    card("email", T("check your email") - LEAD, T("seriously you do not") - LEAD, captions_off=False)
    push(T("locks in your spot"), 1.1, 1.8)
    text("we only have a limited number of spots",
         [("WE ONLY HAVE A", "sub", 44, "white"), ("LIMITED NUMBER", "big", 120, "white"), ("OF SPOTS.", "big", 120, "purple")],
         T("and unconfirmed calls") - LEAD, icon="calendar", cy=560)
    # 1:09-1:19 calm and wide on purpose (scarcity line, then the empathetic part)
    text("if this is even something that you can commit to or if it can even really work out and etc",
         [("IF THIS IS EVEN SOMETHING", "big", 74, "white"), ("THAT YOU CAN COMMIT TO,", "big", 74, "white"),
          ("OR IF IT CAN EVEN REALLY WORK OUT? _ _", "big", 74, "purple")], T("and honestly i totally") - LEAD)
    t_flick = T("especially from the online") - LEAD
    text("the odds right now are stacked against you",
         [("THE ODDS RIGHT NOW ARE", "sub", 46, "white"), ("STACKED AGAINST YOU.", "big", 84, "red")],
         t_flick, chart=True, plate="red", leak_out=False)
    card("flicker", t_flick, T("just trying to push") - LEAD, captions_off=False, leak_out=False, n=12)
    text("just trying to push a course in front of your face",
         [("JUST TRYING TO PUSH A COURSE", "big", 86, "white"), ("IN FRONT OF YOUR FACE.", "sub", 46, "purple")],
         T("or trying to sell you") - LEAD, leak_in=False)
    push(T("personally mentoring you"), 1.08, 2.0)
    push(T("exactly why i built"), 1.16, 1.8)
    text("to make you bulletproof from the ups and downs of dropshipping",
         [("TO MAKE YOU", "sub", 46, "white"), ("BULLETPROOF", "big", 150, "purple"),
          ("FROM THE UPS AND DOWNS OF DROPSHIPPING.", "sub", 40, "white")], T("and to be honest") - LEAD,
         icon="shield", cy=590)
    push(T("however on the flip side"), 1.12, 1.8)
    t0 = T("and instead you can") - LEAD
    card("pip", t0, T("so if you want to join") - LEAD, leak_in=False,
         title=rows("a profitable dropshipper", [("A PROFITABLE", "sub", 50, "white"), ("DROPSHIPPER.", "big", 130, "purple")]))
    off[-1][0] = t0 + 0.3                                  # his words stay captioned while the window shrinks
    push(T("time location and financial freedom that"), 1.12, 1.6)
    text("be on the lookout for that call from my team",
         [("BE ON THE LOOKOUT", "big", 104, "white"), ("FOR THAT CALL FROM MY TEAM.", "sub", 46, "purple")],
         T("thanks again") - LEAD, icon="phone", cy=600)
    zk.append([round(dur, 3), zk[-1][1]])

    # captions (AB's): 1-3 words, off while a text card / the results wall is up
    def is_off(t):
        return any(a - 0.01 <= t < b for a, b in off)

    caps, cur = [], None
    for k, w in enumerate(words):
        if is_off(w["s"]):
            if cur:
                caps.append(cur); cur = None
            continue
        brk = cur is None
        if cur:
            last = cur["words"][-1]
            n_ch = sum(len(x[0]) for x in cur["words"]) + len(w["w"])
            glued = last[0] == "1-on-1" and w["w"] == "Mentorship"
            if not glued and (re.search(r"[,.!?]$", words[k - 1]["raw"]) or len(cur["words"]) >= 3
                              or (len(cur["words"]) >= 2 and n_ch > 11) or w["s"] - words[k - 1]["e"] > 0.3):
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
        c["t1"] = round(min(nxt["t0"] if nxt else dur, c["end"] + 0.5), 3)
        for a, b in off:
            if c["t0"] < a < c["t1"]:
                c["t1"] = a
    leaks.sort(key=lambda x: x["t"])
    zk.sort(key=lambda k: k[0])
    os.makedirs(OUT, exist_ok=True)
    plan = {"keep": [[round(a, 4), round(b, 4)] for a, b in keep], "dur": round(dur, 3), "words": words,
            "scenes": scenes, "leaks": leaks, "zoom": zk, "captions": caps, "off": off,
            "music": {"pivot": T("however on the flip side"), "end": dur}}
    json.dump(plan, open(f"{OUT}/plan.json", "w"), indent=1)
    pushes = sum(1 for a, b in zip(zk, zk[1:]) if b[1] > a[1])
    print(f"{dur:.2f}s; {len(scenes)} cards, {len(leaks)} light sweeps, {pushes} push-ins, {len(caps)} caption phrases")


if __name__ == "__main__":
    main()
