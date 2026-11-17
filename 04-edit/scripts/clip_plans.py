"""Edit plans for Mert's thank-you video and his five FAQ videos, in exactly the VSL's style (mert_plan.Edit, rendered by
mert_render.py): Iman-style cards on the frosted plate, AB word captions with lime/red callouts, side text, split screen
lists, underlines, slow push-ins. Every element is bound to his words.

    python clip_plans.py [name ...]      # writes /home/user/work/ty_faq/<name>/plan.json
"""
import sys

sys.path.insert(0, "/home/user/work/scripts")
from mert_plan import Edit, LEAD

D = "/home/user/work/ty_faq"
CAPS = {"i": "I", "mert": "Mert", "sms": "SMS", "90": "90%", "i'll": "I'll", "i'm": "I'm", "orderflow": "Order Flow"}


def edit(name, anchor):
    e = Edit(f"{D}/{name}", fixes=[], anchor=anchor)
    for w in e.words:
        w["w"] = CAPS.get(w["n"], w["w"])
    return e


def manual(lines, t):
    """Rows that appear at a fixed time (the FAQ question), one line every 0.12 s."""
    return [{"words": [[txt, round(t + 0.12 * i, 3)]], "style": st, "size": sz, "color": col}
            for i, (txt, st, sz, col) in enumerate(lines)]


def question(lines):
    return manual([(l, "sub", 32, "dim") for l in lines], 0.05)


def split(e, t0, t1, a, b=None, t_swap=None, ticks=()):
    e.scenes.append(dict(kind="split", t0=round(t0, 3), t1=round(t1, 3), t_swap=round(t_swap or t1 + 99, 3), a=a, b=b or []))
    e.off.append([t0, t1])
    e.sfx.append(["whoosh", round(t0 - 0.2, 3), 0.9])
    if t_swap:
        e.sfx.append(["whoosh_soft", round(t_swap - 0.05, 3), 0.7])
    for ph in ticks:
        e.sfx.append(["tick", round(e.T(ph), 3), 0.55])
    e.snap(t0)


# ------------------------------------------------------------------ thank-you
def thankyou():
    e = edit("thankyou", (1074, 500))
    T, E = e.T, e.E
    t1 = T("you have taken action") - LEAD
    e.scenes.append(dict(kind="intro", t0=0.0, t1=round(t1, 3), rows=e.rows(
        "yo what's up mert here i just wanted to thank you for filling out application to the elite mentorship",
        [("YO, WHAT'S UP", "sub", 36, "dim"), ("MERT. _", "big", 230, "white", {"ul": True}),
         ("_ _ _ _ THANK YOU FOR _ _ APPLYING", "sub", 34, "lime"), ("TO THE ELITE MENTORSHIP", "sub", 34, "white")])))
    e.off.append([0.0, t1])
    e.text("you have taken action 90 of traders couldn't do",
           [("YOU _ TOOK ACTION", "sub", 40, "white"), ("90%", "big", 260, "lime", {"ul": True}),
            ("OF TRADERS COULDN'T DO.", "sub", 44, "white")], T("and you are genuinely") - LEAD)
    e.push("and you are genuinely", 1.12, 1.8)
    e.callout("one step closer", "lime")
    e.push("so i want you take", 1.18, 1.2)
    e.callout("extremely seriously", "lime")
    e.text("the opportunity to gain the consistency profitability and that time location and financial freedom",
           [("THE OPPORTUNITY TO GAIN _", "sub", 36, "dim"), ("CONSISTENCY", "big", 104, "white"),
            ("PROFITABILITY _", "big", 104, "lime"), ("_ TIME, LOCATION &", "sub", 40, "white"),
            ("FINANCIAL FREEDOM.", "big", 92, "white", {"ul": True})], T("so what are the next") - LEAD)
    e.text("so what are the next steps", [("_ WHAT ARE THE", "sub", 44, "white"), ("NEXT STEPS?", "big", 150, "lime", {"ul": True})],
           T("well as i speak") - LEAD)
    e.push("well as i speak", 1.1, 2.0)
    e.pull(T("one of my best") - 0.9, 0.6)
    e.side("one of my best students is reviewing your application",
           [("_ _ MY BEST STUDENTS", "sub", 34, "lime"), ("IS REVIEWING", "sub", 34, "white"),
            ("YOUR APPLICATION.", "big", 66, "white")], T("to see if you are good") + 1.2, cy=470)
    e.text("he will reach out to you personally over sms",
           [("_ _ REACH OUT _ _ PERSONALLY", "sub", 40, "white"), ("_ SMS.", "big", 220, "lime", {"ul": True})],
           T("so make sure you have") - LEAD)
    e.push("so make sure you have", 1.14, 1.6)
    e.callout("phone in your hands", "lime")
    e.pull(T("now i know probably") - 0.1, 1.2)
    e.push("a little bit hesitant", 1.15, 1.6)
    e.headline("honestly i totally get it", [("honestly,", "hand", 60, "lime"), ("I TOTALLY GET IT.", "big", 92, "white")],
               T("there is a lot of") - 0.1)
    e.text("a lot of trading gurus trying to sell your dream without actually mentoring you",
           [("A LOT OF TRADING", "sub", 40, "white"), ("GURUS", "big", 230, "red", {"ul": True}),
            ("_ _ SELLING _ DREAMS", "sub", 42, "white"), ("WITHOUT ACTUALLY MENTORING YOU.", "sub", 36, "dim")],
           T("that's exactly why") - LEAD, plate="red", chart=True, chart_delay=1.0, chart_dur=1.2)
    e.text("that's exactly why i built elite mentorship real guidance and the right psychology",
           [("_ EXACTLY WHY I BUILT", "sub", 38, "dim"), ("ELITE MENTORSHIP.", "big", 112, "lime", {"ul": True}),
            ("REAL GUIDANCE & _ RIGHT PSYCHOLOGY", "sub", 40, "white")], T("to bulletproof you") - LEAD)
    e.push("to bulletproof you", 1.15, 1.4)
    e.callout("bulletproof you", "lime")
    e.text("so right now go check your email",
           [("_ _ _ GO CHECK YOUR", "sub", 44, "white"), ("EMAIL.", "big", 230, "lime", {"ul": True})],
           T("and make sure you receive") - LEAD)
    e.push("and make sure you receive", 1.1, 2.4)
    e.callout("accept it", "lime")
    e.callout("locked in your calendar", "lime")
    e.push("on the call we will", 1.16, 2.0)
    e.pull(T("and point you in") + 0.1, 1.4)
    e.headline("becoming profitable sooner rather than later",
               [("_ PROFITABLE", "big", 104, "white"), ("sooner rather than later", "hand", 62, "lime")],
               T("thanks once again") - 0.1)
    e.push("thanks once again", 1.14, 2.2)
    e.callout("see you on the call", "lime")
    e.write()


# ------------------------------------------------------------------ FAQs
def fulltime():
    e = edit("fulltime", (930, 495))
    T = e.T
    e.card("iman", 0.0, T("auction market theory") - LEAD, sweep_in=False, cy=520,
           rows=question(["CAN I DO THIS", "WITH A FULL-TIME JOB?"]) +
           e.rows("yes absolutely", [("YES, ABSOLUTELY.", "big", 130, "lime", {"ul": True})]))
    e.card("iman", T("auction market theory") - LEAD, T("so even if you") - LEAD, sweep_in=False, cy=520,
           rows=manual([("I TEACH", "sub", 36, "dim")], T("auction market theory") - 0.02) +
           e.rows("auction market theory and order flow which you can use any trading session",
                  [("AUCTION MARKET THEORY", "big", 84, "white"), ("_ ORDER FLOW.", "big", 112, "lime", {"ul": True}),
                   ("_ _ _ _ ANY TRADING SESSION.", "sub", 38, "white")]))
    e.callout("full-time job", "lime")
    e.push("you can still learn", 1.14, 1.6)
    e.callout("when it fits your schedule", "lime")
    e.write()


def boughtcourse():
    e = edit("boughtcourse", (1080, 420))
    T = e.T
    e.card("iman", 0.0, T("you will directly") - LEAD, sweep_in=False, cy=520,
           rows=question(["I'VE ALREADY BOUGHT A COURSE.", "WHY IS THIS ONE DIFFERENT?"]) +
           e.rows("because this is not just another video course",
                  [("_ _ _ NOT JUST ANOTHER", "big", 80, "white"), ("VIDEO COURSE.", "big", 120, "lime", {"ul": True})]))
    e.callout("directly work with me", "lime")
    split(e, T("join live trading") - LEAD, T("and guide you through") - LEAD,
          manual([("WITH ME, YOU", "sub", 32, "lime")], T("join live trading") - 0.02) +
          e.rows("join live trading sessions get personal feedback on your trades i will help you fix your mistakes improve your trading psychology",
                 [("JOIN LIVE TRADING SESSIONS", "item", 40, "white"), ("GET PERSONAL FEEDBACK ON YOUR TRADES", "item", 40, "white"),
                  ("_ _ _ _ FIX YOUR MISTAKES", "item", 40, "white"), ("IMPROVE YOUR TRADING PSYCHOLOGY", "item", 40, "white")]),
          ticks=["join live trading", "get personal feedback", "fix your mistakes", "improve your trading"])
    e.text("guide you through your first funded account or your first payout",
           [("_ _ _ YOUR FIRST", "sub", 42, "white"), ("FUNDED ACCOUNT", "big", 112, "lime"),
            ("OR _ FIRST PAYOUT.", "big", 84, "white", {"ul": True})], T("you are not doing this alone") - LEAD)
    e.push("you are not doing", 1.15, 1.4)
    e.callout("not doing this alone", "lime")
    e.write()


def beginners():
    e = edit("beginners", (915, 480))
    T = e.T
    e.card("iman", 0.0, T("it doesn't matter") - LEAD, sweep_in=False, cy=520,
           rows=question(["IS THIS MENTORSHIP", "FOR BEGINNERS?"]) +
           e.rows("yes absolutely", [("YES, ABSOLUTELY.", "big", 130, "lime", {"ul": True})]))
    e.card("iman", T("it doesn't matter") - LEAD, T("we will start from") - LEAD, sweep_in=False, cy=520,
           rows=e.rows("it doesn't matter if you are a beginner or already have trading experience",
                       [("IT DOESN'T MATTER IF _ _", "sub", 38, "dim"), ("_ BEGINNER", "big", 130, "white"),
                        ("OR _ _ _ EXPERIENCED.", "big", 120, "lime", {"ul": True})]))
    e.callout("start from your level", "lime")
    e.push("and improve step", 1.15, 1.2)
    e.callout("step by step", "lime")
    e.write()


def whatsinside():
    e = edit("whatsinside", (1095, 465))
    T = e.T
    e.card("iman", 0.0, T("you will get access") - LEAD, sweep_in=False, cy=520,
           rows=e.rows("inside the orderflow elite mentorship",
                       [("INSIDE THE", "sub", 38, "dim"), ("ORDER~FLOW ELITE", "big", 110, "white"),
                        ("MENTORSHIP.", "big", 120, "lime", {"ul": True})]))
    split(e, T("you will get access") - LEAD, T("the goal is simple") - LEAD,
          manual([("YOU GET ACCESS TO", "sub", 32, "lime")], T("you will get access")) +
          e.rows("my complete video course 8 one-on-one calls with me daily live pre-markets and daily trading sessions weekly trade recaps and our private trading community",
                 [("_ COMPLETE VIDEO COURSE", "item", 40, "white"), ("8 1-ON-1 CALLS WITH ME", "item", 40, "white"),
                  ("DAILY LIVE PRE-MARKETS", "item", 40, "white"), ("_ DAILY TRADING SESSIONS", "item", 40, "white"),
                  ("WEEKLY TRADE RECAPS", "item", 40, "white"), ("_ _ PRIVATE TRADING COMMUNITY", "item", 40, "white")]),
          manual([("YOU ALSO GET", "sub", 32, "lime")], T("you will also get")) +
          e.rows("personal trading plan direct support from me and 4 extra weeks follow-up support",
                 [("PERSONAL TRADING PLAN", "item", 40, "white"), ("DIRECT SUPPORT FROM ME", "item", 40, "white"),
                  ("_ 4 EXTRA WEEKS FOLLOW-UP SUPPORT", "item", 40, "white")]),
          t_swap=T("you will also get") - 0.3,
          ticks=["my complete video", "8 one-on-one", "daily live", "daily trading sessions", "weekly trade",
                 "private trading", "personal trading plan", "direct support", "4 extra weeks"])
    e.text("the goal is simple to help you master auction market theory and order flow",
           [("THE GOAL IS SIMPLE.", "sub", 38, "dim"), ("_ _ _ MASTER", "sub", 42, "white"),
            ("AUCTION MARKET THEORY", "big", 82, "white"), ("_ ORDER FLOW.", "big", 112, "lime", {"ul": True})],
           T("and become a confident") - LEAD)
    e.push("and become a confident", 1.14, 1.6)
    e.callout("confident independent trader", "lime")
    e.write()


def mertorassistant():
    e = edit("mertorassistant", (1080, 465))
    T = e.T
    e.card("iman", 0.0, T("we will have private") - LEAD, sweep_in=False, cy=520,
           rows=question(["WILL I WORK WITH MERT", "OR AN ASSISTANT?"]) +
           e.rows("you will work directly with me", [("_ _ WORK DIRECTLY", "sub", 44, "white"),
                                                     ("WITH ME.", "big", 170, "lime", {"ul": True})]))
    split(e, T("we will have private") - LEAD, T("i will personally guide") - LEAD,
          manual([("1-ON-1 WITH ME", "sub", 32, "lime")], T("we will have private")) +
          e.rows("private one-on-one calls review your trades fix your mistakes and build trading plan for you",
                 [("PRIVATE 1-ON-1 CALLS", "item", 40, "white"), ("REVIEW YOUR TRADES", "item", 40, "white"),
                  ("FIX YOUR MISTAKES", "item", 40, "white"), ("_ BUILD YOUR~TRADING PLAN _ _", "item", 40, "white")]),
          ticks=["private one-on-one", "review your trades", "fix your mistakes", "build trading plan"])
    e.push("i will personally guide", 1.15, 1.4)
    e.callout("personally guide you", "lime")
    e.write()


EDITS = {"thankyou": thankyou, "fulltime": fulltime, "boughtcourse": boughtcourse, "beginners": beginners,
         "whatsinside": whatsinside, "mertorassistant": mertorassistant}

if __name__ == "__main__":
    for n in sys.argv[1:] or EDITS:
        print(n, end=": ")
        EDITS[n]()
