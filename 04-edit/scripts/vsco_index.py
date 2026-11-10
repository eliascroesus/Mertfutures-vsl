"""Index VSCO 2 CE samples: parse note names, verify the octave with pitch detection, record length and loudness."""
import json, os, re, sys
import numpy as np, soundfile as sf, librosa
ROOT = "/home/user/sgossner/vsco-2-ce"
FOLDERS = {
    "vln_spic": "Strings/Violin Section/Spic", "vln_sus": "Strings/Violin Section/susVib", "vln_trem": "Strings/Violin Section/Trem",
    "vla_spic": "Strings/Viola Section/spic", "vla_sus": "Strings/Viola Section/susvib", "vla_trem": "Strings/Viola Section/trem",
    "vc_spic": "Strings/Cello Section/spic", "vc_sus": "Strings/Cello Section/susvib", "vc_trem": "Strings/Cello Section/trem",
    "cb_spic": "Strings/Solo Contrabass/Spic", "cb_sus": "Strings/Solo Contrabass/SusVib",
}
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
index = {}
for key, folder in FOLDERS.items():
    rows = []
    for fn in sorted(os.listdir(f"{ROOT}/{folder}")):
        m = re.search(r"_([A-G]#?)(-?\d)_v(\d)", fn)
        if not m:
            continue
        named = NOTE[m.group(1)] + 12 * (int(m.group(2)) + 1)
        x, sr = sf.read(f"{ROOT}/{folder}/{fn}")
        mono = x.mean(1) if x.ndim > 1 else x
        seg = mono[int(0.05 * sr):int(min(len(mono), 1.2 * sr))]
        f0 = librosa.yin(seg, fmin=30, fmax=2000, sr=sr, frame_length=4096)
        det = float(np.median(69 + 12 * np.log2(f0 / 440)))
        rows.append({"file": f"{ROOT}/{folder}/{fn}", "named": named, "detected": det, "dyn": int(m.group(3)),
                     "rr": 2 if re.search(r"rr2|RR2|_2\.wav", fn) else 1, "dur": len(mono) / sr,
                     "peak": float(np.abs(x).max())})
    # octave correction per folder: median difference between detected and named, rounded to 12
    diffs = [r["detected"] - r["named"] for r in rows if np.isfinite(r["detected"])]
    off = int(round(np.median(diffs) / 12)) * 12 if diffs else 0
    for r in rows:
        r["midi"] = r["named"] + off
    index[key] = rows
    durs = [r["dur"] for r in rows]
    lo, hi = min(r["midi"] for r in rows), max(r["midi"] for r in rows)
    print(f"{key:9s} {len(rows):3d} samples  octave fix {off:+d}  range {librosa.midi_to_note(lo)}-{librosa.midi_to_note(hi)}  "
          f"dur {min(durs):.1f}-{max(durs):.1f}s  dyn layers {sorted(set(r['dyn'] for r in rows))}  "
          f"detect err {np.nanmedian([abs(r['detected'] - r['midi']) for r in rows]):.2f} st")
json.dump(index, open("/home/user/work/vsco_index.json", "w"))
