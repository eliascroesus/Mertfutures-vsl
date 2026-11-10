"""Edit plan for Ricky's thank-you video, copied 1:1 from AB Nasdaq's thank-you edit
(rickyvsl-clips/thank-you-vsl-reference/THANK-YOU-BREAKDOWN.md).

Cuts every pause over 0.22 s, then places every card, light leak, zoom and caption on his words.

    python ty_plan.py            # writes edit/ty/plan.json
"""
import json, re
import numpy as np
import soundfile as sf

WORK = "/home/user/work"
RAW = f"{WORK}/thankyou/raw/thankyou_raw.mp4"
FPS = 30
RAW_DUR = 152.81


# ------------------------------------------------------------------ words
def load_words(path=f"{WORK}/thankyou/raw/transcript.json"):
    W = []
    for s in json.load(open(path)):
        for w in s["words"]:
            txt = w["w"].strip()
            if W and (txt.startswith("-") or txt == "%"):           # "one -on -one", "90 %" -> one word
                W[-1]["w"] += txt
                W[-1]["e"] = w["e"]
            else:
                W.append({"w": txt, "s": w["s"], "e": w["e"]})
    return W


def norm(t):
    return re.sub(r"[^a-z0-9%']", "", t.lower())


# ------------------------------------------------------------------ cuts
def plan_cuts(W, voice=f"{WORK}/edit/ty/voice_proc.wav", raw_dur=RAW_DUR):
    y, sr = sf.read(voice)
    m = y.mean(1)
    hop = int(0.01 * sr)
    n = len(m) // hop
    env = 20 * np.log10(np.sqrt((m[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    quiet = np.median(env) - 18                          # room tone / silence, well under speech and breaths

    def q(t):
        return env[min(int(round(t * 100)), n - 1)] < quiet

    cuts = []
    for a, b in zip(W, W[1:]):
        if b["s"] - a["e"] <= 0.18:
            continue
        # the cut has to start and end in real silence (Whisper's word edges can be off by a few hundred ms)
        lo, hi = a["e"] + 0.05, b["s"] - 0.03
        grid = [g / FPS for g in range(int(np.ceil(lo * FPS)), int(np.floor(hi * FPS)) + 1)]
        ok = [g for g in grid if q(g - 0.01) and q(g) and q(g + 0.01)]   # frame-exact points in real silence
        if len(ok) < 2:
            continue
        c0, c1 = ok[0], ok[-1]
        if any(env[int(x * 100)] > np.median(env) - 6 for x in np.arange(c0, c1, 0.01)):
            continue                                          # speech inside: leave it alone
        if c1 - c0 >= 2 / FPS:
            cuts.append((round(c0, 4), round(c1, 4)))
    keep, t = [], 0.0
    for c0, c1 in cuts:
        keep.append((t, c0))
        t = c1
    keep.append((t, np.floor(raw_dur * FPS) / FPS))
    return keep


def mapper(keep):
    starts = np.cumsum([0] + [b - a for a, b in keep])

    def out(t):
        for (a, b), s in zip(keep, starts):
            if t < a:
                return s
            if t <= b:
                return s + t - a
        return starts[-1]
    return out, float(starts[-1])


# ------------------------------------------------------------------ captions
def display(w, prev):
    t = re.sub(r"[,.!?;:]", "", w)
    if norm(t) == "oneonone":
        return "1-on-1"
    if norm(t) == "mentorship" and prev == "1-on-1":
        return "Mentorship"
    return t


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

    def T(phrase, after=0.0):                  # output start time of a phrase
        return words[find(phrase, after)]["s"]

    def E(phrase, after=0.0):                  # output end time of a phrase
        i = find(phrase, after)
        return words[i + len(phrase.split()) - 1]["e"]

    def card_words(phrase, lines, after=0.0):
        """Card lines (display words) bound to the spoken word times, word for word."""
        i = find(phrase, after)
        n = sum(len(l.split()) for l in lines)
        assert n == len(phrase.split()), (phrase, lines)
        out_lines, k = [], i
        for l in lines:
            ws = []
            for d in l.split():
                ws.append([d, words[k]["s"]])
                k += 1
            out_lines.append(ws)
        return out_lines

    scenes, leaks, zk, off = [], [], [[0.0, 1.5]], []
    LEAD = 0.06                                           # the cut sits just before the first word, under the flash

    def card(kind, t0, t1, **kw):
        scenes.append(dict(kind=kind, t0=round(t0, 3), t1=round(t1, 3), **kw))

    def leak(t, strength=1.0):
        leaks.append({"t": round(t, 3), "s": strength})

    def zoom_to(t, z, d=0.7):
        last = zk[-1]
        if t > last[0]:
            zk.append([round(t, 3), last[1]])
        zk.append([round(t + d, 3), z])

    def reset(t):                                         # snap back to wide (under a flash or a card)
        last = zk[-1]
        zk.append([round(t - 0.001, 3), last[1] if t - 0.001 > last[0] else last[1]])
        zk.append([round(t, 3), 1.0])

    def text_card(phrase, lines, t_out, bg="green", sizes=None, icon=None, chart=False, cy=500, after=0.0):
        t0 = T(phrase, after) - LEAD
        card("text", t0, t_out, bg=bg, lines=card_words(phrase, lines, after), sizes=sizes, icon=icon, chart=chart, cy=cy)
        leak(t0); leak(t_out); reset(t0)
        off.append([t0, t_out])
        return t0

    # --- 0:00 open tight on his face, ease out to wide; push on the application line
    zk[:] = [[0.0, 1.5], [1.1, 1.0]]
    zoom_to(T("filling out the application"), 1.2, 0.5)
    zoom_to(T("you've just taken action"), 1.0, 0.6)
    # --- "that 90% of other dropshippers couldn't do"
    t_back = T("and you are genuinely") - LEAD
    text_card("that 90% of other dropshippers couldn't do", ["That 90%", "of other dropshippers couldn't do"], t_back,
              sizes=[150, 74], cy=470)
    # --- staircase push, flash reset on "Therefore"
    zoom_to(T("genuinely"), 1.18, 0.7)
    zoom_to(T("changing your entire life"), 1.38, 0.9)
    tf = T("therefore") - LEAD
    leak(tf); reset(tf)
    zoom_to(T("very seriously"), 1.15, 0.7)
    zoom_to(T("opportunity to get"), 1.0, 0.8)
    # --- "the consistency, the sales" then Time / Location / Freedom circles
    t0 = T("the consistency the sales") - LEAD
    t_circ = T("time location and financial freedom") - 0.04
    t_back = T("and there is countless") - LEAD
    card("text", t0, t_circ, bg="green", lines=card_words("the consistency the sales", ["_ Consistency", "_ Sales"]),
         sizes=[96, 96], cy=500)
    card("circles", t_circ, t_back, bg="green",
         items=[["time", T("time location")], ["location", T("location and financial")], ["freedom", T("freedom you've")]])
    leak(t0); leak(t_back); reset(t0); off.append([t0, t_back])
    # --- "countless other dropshippers in the 1-on-1 mentorship"
    t_back = T("taking advantage of this") - LEAD
    text_card("countless other dropshippers in the one-on-one mentorship",
              ["Countless other dropshippers", "in the 1-on-1 Mentorship"], t_back, sizes=[96, 96])
    zoom_to(T("no reason why"), 1.17, 0.8)
    # --- "what are the next steps to joining the 1-on-1 mentorship?"
    t_back = T("and as i'm speaking") - LEAD
    text_card("what are the next steps to joining the one-on-one mentorship",
              ["What are the", "next steps to joining", "the 1-on-1 Mentorship?"], t_back, sizes=[96, 96, 96], cy=480)
    zoom_to(T("one of my top students"), 1.15, 1.0)
    # --- application card (captions stay on)
    t0 = T("is currently reviewing") - LEAD
    t1 = T("and if you are") - LEAD
    card("app", t0, t1, bg="green"); leak(t0); leak(t1); reset(t0)
    # --- staircases with flash resets: phone in your hand / incredibly important
    zoom_to(T("reach out to you personally"), 1.19, 0.6)
    zoom_to(T("phone is in your hand"), 1.38, 0.8)
    tf = T("because you do not want") - LEAD
    leak(tf); reset(tf)
    zoom_to(T("miss out on this call"), 1.14, 0.7)
    zoom_to(T("incredibly important"), 1.36, 0.7)
    # --- email card: check your email and confirm your call (captions stay on)
    t0 = T("check your email") - LEAD
    t1 = T("seriously you do not") - LEAD
    card("email", t0, t1, bg="green"); leak(t0); leak(t1); reset(t0)
    zoom_to(T("locks in your spot"), 1.15, 0.7)
    zoom_to(T("tells us that you are serious"), 1.32, 0.8)
    zoom_to(T("and it makes sure"), 1.0, 0.9)
    # --- "we only have a limited number of spots"
    t_back = T("and unconfirmed calls") - LEAD
    text_card("we only have a limited number of spots", ["We only have a", "Limited Number of Spots"], t_back,
              sizes=[84, 112], icon="calendar", cy=560)
    zoom_to(T("unconfirmed calls get moved"), 1.15, 0.7)
    zoom_to(T("next person in line"), 1.3, 0.7)
    tf = T("so take 10 seconds") - LEAD
    leak(tf); reset(tf)
    zoom_to(T("open your inbox"), 1.12, 0.6)
    zoom_to(T("hit confirm"), 1.0, 0.6)
    # --- calm stretch, then his doubts as text
    t_back = T("and honestly i totally") - LEAD
    text_card("if this is even something that you can commit to or if it can even really work out and etc",
              ["If this is even something", "that you can commit to,", "or if it can even really work out? _ _"],
              t_back, sizes=[88, 88, 88], cy=500)
    # --- red card: the odds are stacked against you, with the falling chart line
    t0 = T("the odds right now") - LEAD
    t_flick = T("especially from the online") - LEAD
    card("text", t0, t_flick, bg="red", lines=card_words("the odds right now are stacked against you",
                                                         ["The odds right now are", "Stacked Against You"]),
         sizes=[96, 112], cy=500, chart=True)
    leak(t0); reset(t0); off.append([t0, t_flick])
    # --- online gurus: thumbnail flicker (captions on), then "just trying to push a course in front of your face"
    t_txt = T("just trying to push") - LEAD
    card("flicker", t_flick, t_txt, bg="green", n=12)
    leak(t_flick, 0.8)
    t_back = T("or trying to sell you") - LEAD
    card("text", t_txt, t_back, bg="green",
         lines=card_words("just trying to push a course in front of your face",
                          ["Just trying to push a course", "in front of your face"]), sizes=[96, 96], cy=500, fade_in=True)
    off.append([t_txt, t_back]); leak(t_back)
    # --- staircase on "personally mentoring you, holding you accountable", smooth pull-out
    zoom_to(T("personally mentoring you"), 1.2, 0.6)
    zoom_to(T("holding you accountable"), 1.4, 0.6)
    zoom_to(T("or helping you through"), 1.0, 0.8)
    zoom_to(T("exactly why i built"), 1.09, 0.7)
    zoom_to(T("how big of a difference"), 1.0, 0.7)
    zoom_to(T("actually a personal"), 1.11, 0.7)
    # --- bulletproof icon card
    t_back = T("and to be honest") - LEAD
    text_card("to make you bulletproof from the ups and downs of dropshipping",
              ["To Make You Bulletproof", "from the ups and downs of Dropshipping"], t_back, sizes=[104, 80],
              icon="shield", cy=590)
    zoom_to(T("in reality it takes way longer"), 1.12, 1.0)
    zoom_to(T("you probably won't even get"), 1.0, 0.7)
    # --- however, on the flip side (808 enters in the music)
    zoom_to(T("cut down all of the time"), 1.12, 0.7)
    zoom_to(T("thousands of dollars"), 1.25, 0.8)
    t0 = T("and instead you can") - LEAD
    t1 = T("so if you want to join") - LEAD
    card("pip", t0, t1, bg="green", title=card_words("a profitable dropshipper", ["A Profitable", "Dropshipper"]))
    off.append([t0 + 0.3, t1]); leak(t1); reset(t0)
    zoom_to(T("join the one-on-one mentorship and"), 1.13, 0.7)
    zoom_to(T("time location and financial freedom that"), 1.3, 0.7)
    zoom_to(T("financial freedom that"), 1.45, 0.6)
    zoom_to(T("that you've been wanting"), 1.0, 1.0)
    # --- be on the lookout for that call from my team
    t_back = T("thanks again") - LEAD
    text_card("be on the lookout for that call from my team", ["Be on the lookout", "for that call from my team"],
              t_back, sizes=[104, 104], icon="phone", cy=600)
    zk.append([round(dur, 3), 1.0])

    # captions: 1-3 words per phrase, off while a text card or the results wall is up
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
        lim = nxt["t0"] if nxt else dur
        c["t1"] = round(min(lim, c["end"] + 0.5), 3)
        for a, b in off:                                  # never run into a card
            if c["t0"] < a < c["t1"]:
                c["t1"] = a
    leaks.sort(key=lambda x: x["t"])
    zk.sort(key=lambda k: k[0])
    plan = {"keep": [[round(a, 4), round(b, 4)] for a, b in keep], "dur": round(dur, 3), "words": words,
            "scenes": scenes, "leaks": leaks, "zoom": zk, "captions": caps, "off": off,
            "music": {"pivot": T("however on the flip side"), "dense": T("now i know what you're"), "end": dur}}
    json.dump(plan, open(f"{WORK}/edit/ty/plan.json", "w"), indent=1)
    print(f"keep {len(keep)} pieces, {RAW_DUR - dur:.2f}s of pauses cut -> {dur:.2f}s; {len(scenes)} scenes, "
          f"{len(leaks)} light leaks, {len(caps)} caption phrases, {len(zk)} zoom keys; 808 at {plan['music']['pivot']:.2f}s")


if __name__ == "__main__":
    main()
