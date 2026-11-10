"""Rebuild the voice and music buses for an edit list and print their levels per section (dB RMS, voice-active frames)."""
import json, sys
import numpy as np
sys.path.insert(0, "/home/user/work/scripts")
import render as R
import soundfile as sf

edl = json.load(open(sys.argv[1]))
items, total = R.build_timeline(edl)
n = int(total * R.SR) + R.SR
voice = np.zeros((n, 2)); vsrc = R.load_audio(R.VOICE)
for it in items:
    R.place(voice, vsrc[int(it["in"] * R.SR):int(it["out"] * R.SR)], it["t0"])
music = np.zeros((n, 2)); stems = {}
for m in edl["music"]:
    if m["stem"] not in stems:
        stems[m["stem"]], _ = sf.read(f"{R.MUSIC}/stem_{m['stem']}.wav", dtype="float32")
    seg = stems[m["stem"]][int(m["offset"] * R.SR):int((m["offset"] + m["t1"] - m["t0"]) * R.SR)].astype(np.float64) * R.db(m["db"])
    R.place(music, seg, m["t0"])
env = R.envelope(voice); thr = R.db(-38)
music *= R.db(-edl.get("duck_db", 6) * np.clip((env - thr) / (R.db(-24) - thr), 0, 1))[:, None]
import pyloudnorm as pyln
_meter = pyln.Meter(R.SR)
def rms(x):
    if len(x) < R.SR // 2:
        return float("nan")
    with np.errstate(all="ignore"):
        v = _meter.integrated_loudness(x)
    return v if np.isfinite(v) else -70.0
hop = R.SR // 10
vact = np.array([20 * np.log10(np.sqrt((voice[i:i + hop] ** 2).mean()) + 1e-12) > -40 for i in range(0, n - hop, hop)])
print("LUFS  window   voice(active)  music(during voice)  music(in gaps)  gap")
for t0 in range(0, int(total), 15):
    a, b = t0 * 10, (t0 + 15) * 10
    idx = np.arange(a, min(b, len(vact)))
    vi = [i for i in idx if vact[i]]; gi = [i for i in idx if not vact[i]]
    cat = lambda x, ii: np.concatenate([x[i * hop:(i + 1) * hop] for i in ii]) if ii else np.zeros((1, 2))
    v, mv, mg = rms(cat(voice, vi)), rms(cat(music, vi)), rms(cat(music, gi))
    print(f"{t0 // 60}:{t0 % 60:02d}    {v:6.1f}         {mv:6.1f}               {mg:6.1f}        {v - mv:5.1f} dB")
