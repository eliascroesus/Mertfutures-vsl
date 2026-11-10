"""Add the cinematic score cues (raw-video seconds) to edl2.json, mapped through the cut list."""
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


DB = {"pads_dark": -13, "pads_bright": -14, "sub": -15, "pulse": -18}
CUES = [  # stem, raw t0, raw t1, fade in, fade out, extra dB
    ("pads_dark", 0.0, 5.62, 1.2, 0.06, -2), ("sub", 0.0, 5.62, 0.8, 0.06, 0),
    ("pads_dark", 8.30, 102.55, 1.5, 0.3, 0), ("sub", 8.30, 67.62, 1.5, 0.06, 0),
    ("pads_bright", 14.20, 47.40, 3.0, 2.5, -3),
    ("pulse", 47.40, 67.62, 3.0, 0.06, -2),
    ("sub", 69.16, 102.55, 0.8, 0.3, 0), ("pulse", 84.30, 102.55, 4.0, 0.3, 0),
    ("pads_dark", 102.60, 166.40, 1.0, 0.08, 0), ("sub", 102.60, 166.40, 1.5, 0.08, -1),
    ("pads_dark", 168.00, 201.62, 0.6, 0.05, 0), ("sub", 168.00, 201.62, 0.6, 0.05, -1),
    ("pulse", 186.60, 201.62, 4.0, 0.05, 0),
    ("pads_bright", 203.30, 277.25, 0.4, 0.4, 1), ("pulse", 203.30, 277.25, 0.3, 0.4, 2), ("sub", 203.30, 277.25, 0.3, 0.4, 0),
    ("pads_dark", 277.30, 294.05, 0.3, 0.6, -2), ("sub", 277.30, 294.05, 0.3, 0.6, 0),
    ("pads_bright", 294.05, 385.30, 1.5, 3.0, 0), ("sub", 294.05, 385.30, 1.5, 3.0, -1),
    ("pulse", 294.05, 356.00, 2.0, 2.5, -2),
]
edl["music"] = [{"stem": s, "t0": m(a), "t1": m(b), "offset": m(a), "db": DB[s] + x, "fi": fi, "fo": fo} for s, a, b, fi, fo, x in CUES]
edl["music_db"] = 0
json.dump(edl, open(edl_path, "w"), indent=1)
print(len(edl["music"]), "music cues")
