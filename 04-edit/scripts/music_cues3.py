"""Tension score cue sheet (raw-video seconds) for v3, modelled on Iman's bed: instant start, hit after the hook,
driving eighth-note pulse, never silent except the half-second before the reveal."""
import json, sys
edl_path = sys.argv[1]
edl = json.load(open(edl_path))
keep = edl["keep"]


def m(x):
    out = 0.0
    for a, b in keep:
        if x <= a:
            return out
        if x < b:
            return out + x - a
        out += b - a
    return out


DB = {"pulse_pedal": -13, "pulse_prog": -14, "drone": -16, "tension_hi": -15, "pads": -14, "ticks": -17}
CUES = [  # stem, t0, t1, fade in, fade out, extra dB
    # hook: thin and eerie from frame 1, no bass, building into the $87 hit
    ("tension_hi", 0.00, 5.74, 0.03, 0.05, 3), ("ticks", 0.00, 5.74, 0.03, 0.05, 4),
    # after the hit: the bass pulse drives under "I owed money to my mom..."
    ("pulse_pedal", 5.76, 14.28, 0.02, 0.05, 0), ("drone", 5.76, 14.28, 0.05, 0.3, 0),
    ("tension_hi", 8.30, 14.28, 2.5, 0.05, -3), ("ticks", 8.30, 14.28, 1.5, 0.05, -1),
    # "Then I changed three simple things": chords lift, pulse follows them
    ("pads", 14.28, 47.40, 0.3, 2.0, 0), ("pulse_prog", 14.28, 47.40, 0.02, 2.0, 0), ("drone", 14.28, 47.40, 1.0, 2.0, -3),
    ("ticks", 20.0, 47.40, 3.0, 2.0, -3),
    # pain section: back to the pedal, tension builds into the $0 hit
    ("pulse_pedal", 47.20, 67.76, 2.0, 0.05, 0), ("drone", 47.20, 67.76, 2.0, 0.05, 0),
    ("tension_hi", 52.0, 67.76, 4.0, 0.05, -2), ("ticks", 50.0, 67.76, 3.0, 0.05, 0),
    ("pads", 67.80, 81.60, 0.05, 1.5, 0), ("pulse_prog", 67.80, 81.60, 0.02, 1.5, -1),
    # "the problem is the platform" -> open loop -> story
    ("pulse_pedal", 81.60, 102.60, 1.0, 0.05, 0), ("drone", 81.60, 102.60, 1.0, 0.05, 0),
    ("tension_hi", 85.0, 102.60, 4.0, 0.05, -1), ("ticks", 84.0, 102.60, 2.0, 0.05, 0),
    # story: emotional pads with a softer pulse
    ("pads", 102.60, 186.60, 0.2, 2.0, 0), ("pulse_prog", 102.60, 186.60, 0.02, 2.0, -4), ("drone", 102.60, 186.60, 1.0, 2.0, -4),
    # "please don't click off" -> build -> half a second of silence -> YouTube Shorts
    ("pulse_pedal", 186.40, 201.62, 1.5, 0.03, 0), ("drone", 186.40, 201.62, 1.5, 0.03, 0),
    ("tension_hi", 188.0, 201.62, 3.0, 0.03, 0), ("ticks", 187.0, 201.62, 2.0, 0.03, 1),
    # proof: full drive
    ("pads", 203.30, 277.25, 0.05, 0.4, 1), ("pulse_prog", 203.30, 277.25, 0.02, 0.4, 1),
    ("drone", 203.30, 277.25, 0.3, 0.4, -3), ("ticks", 203.30, 277.25, 0.3, 0.4, -1),
    # "here's what most people don't understand": tension again, building into 01
    ("pulse_pedal", 277.30, 294.08, 0.05, 0.05, -1), ("drone", 277.30, 294.08, 0.05, 0.05, 0),
    ("tension_hi", 277.30, 294.08, 0.5, 0.05, -1), ("ticks", 277.30, 294.08, 0.5, 0.05, 0),
    # offer
    ("pads", 294.10, 372.30, 0.05, 1.0, 0), ("pulse_prog", 294.10, 372.30, 0.02, 1.0, -1),
    ("drone", 294.10, 372.30, 0.5, 1.0, -4), ("ticks", 300.0, 356.0, 2.0, 2.0, -4),
    ("tension_hi", 356.0, 372.30, 3.0, 1.0, -5),
    # call to action, ringing out on the A drone after the last word
    ("pads", 372.30, 385.30, 0.5, 3.0, 0), ("pulse_prog", 372.30, 383.60, 0.5, 1.5, -1), ("drone", 372.30, 385.30, 0.5, 3.5, -1),
]
HITS = [  # name, raw time, dB, lead (seconds before the time)
    ("riser_hook", 5.74, -9, 5.7), ("braam", 5.74, -2, 0),
    ("riser_3s", 14.28, -14, 3.0), ("hit_soft", 14.30, -7, 0),
    ("riser_3s", 67.76, -12, 3.0), ("braam", 67.78, -4, 0),
    ("reverse_swell", 95.30, -12, 1.8), ("hit_soft", 95.32, -7, 0),
    ("riser_3s", 102.60, -13, 3.0), ("hit_soft", 102.62, -7, 0),
    ("braam", 126.88, -7, 0),
    ("hit_soft", 164.12, -8, 0), ("braam", 166.48, -6, 0),
    ("riser_hook", 201.62, -9, 5.7), ("braam", 202.12, -1, 0),
    ("hit_soft", 277.32, -6, 0), ("riser_3s", 294.08, -13, 3.0), ("hit_soft", 294.10, -8, 0),
    ("hit_soft", 299.92, -10, 0), ("hit_soft", 307.30, -10, 0), ("braam", 318.62, -8, 0),
    ("hit_soft", 360.32, -8, 0), ("riser_3s", 372.38, -14, 3.0), ("hit_soft", 372.40, -9, 0),
]
DB_SHIFT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
edl["music"] = [{"stem": s, "t0": m(a), "t1": m(b), "offset": m(a), "db": DB[s] + x, "fi": fi, "fo": fo}
                for s, a, b, fi, fo, x in CUES]
edl["sfx"] = [s for s in edl["sfx"] if not s.get("_music")] + \
             [{"name": n, "at": m(t), "db": d, "lead": l, "_music": True} for n, t, d, l in HITS]
edl["music_db"] = DB_SHIFT
json.dump(edl, open(edl_path, "w"), indent=1)
print(len(edl["music"]), "music cues,", len(HITS), "hits")
