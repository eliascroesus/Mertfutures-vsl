"""Level a rendered score section by section (LUFS targets per cue), so it sits evenly under Ricky's voice.

    python level_score.py score.wav edl3.json stem_score.wav
"""
import json, sys
import numpy as np, soundfile as sf, pyloudnorm as pyln

SR = 48000
# section (raw time) -> LUFS target
SECS = [(0.0, 5.70, -32), (5.76, 14.28, -27), (14.28, 47.4, -28), (47.4, 67.76, -27.5), (67.8, 81.6, -29),
        (81.6, 102.6, -27.5), (102.6, 114.5, -30), (114.5, 126.88, -29), (126.88, 131.2, -30), (131.2, 150.0, -30),
        (150.0, 164.1, -29.5), (164.1, 166.5, -28), (166.5, 186.6, -28.5), (186.4, 201.62, -27), (203.3, 277.25, -27.5),
        (277.3, 294.08, -29), (294.1, 318.1, -28.5), (318.1, 344.3, -27.5), (344.3, 372.3, -28.5), (372.3, 383.6, -29.5)]


def main():
    x, sr = sf.read(sys.argv[1])
    assert sr == SR
    keep = json.load(open(sys.argv[2]))["keep"]

    def m(t):
        out = 0.0
        for a, b in keep:
            if t <= a:
                return out
            if t < b:
                return out + t - a
            out += b - a
        return out

    meter = pyln.Meter(SR, block_size=0.4)
    g = np.ones(len(x))
    for a, b, tgt in SECS:
        s, t = int(m(a) * SR), int(m(b) * SR)
        L = meter.integrated_loudness(x[s:t])
        gain = 10 ** (np.clip(tgt - L, -15, 10) / 20)
        print(f"{m(a):6.1f}-{m(b):6.1f}s  {L:6.1f} -> {tgt} LUFS  ({20 * np.log10(gain):+.1f} dB)")
        g[s:t] = gain
    k = int(0.6 * SR)                       # glide between sections over 0.6 s
    g = np.convolve(np.pad(g, (k, k), mode="edge"), np.ones(k) / k, "same")[k:-k]
    lv = (x * g[:, None]).astype(np.float32)
    pk = np.abs(lv).max()
    if pk > 0.95:                           # keep the real section levels; only pull down if it would clip
        lv = lv / pk * 0.95
        print(f"pulled down {20 * np.log10(pk / 0.95):.1f} dB to avoid clipping")
    sf.write(sys.argv[3], lv, SR, subtype="FLOAT")


if __name__ == "__main__":
    main()
