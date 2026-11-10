"""Song bed for the thank-you video: the boom-free 'Me And The Devil' (song_bed.py's de-boomed stem), played as one
unbroken stretch that ends on the song's real outro at the end of the video (no loop joins), with the same slow
level riding to a steady loudness.

    python ty_songbed.py song_noboom.wav total_seconds out.wav
"""
import sys
import numpy as np, soundfile as sf, pyloudnorm as pyln

SR = 48000


def main():
    h, sr = sf.read(sys.argv[1], always_2d=True)
    total, out = float(sys.argv[2]), sys.argv[3]
    assert sr == SR
    need = total + 1.2
    start = max(0.0, len(h) / SR - need)
    bed = h[int(start * SR):].copy()
    fi = int(0.6 * SR)
    bed[:fi] *= np.linspace(0, 1, fi)[:, None] ** 2
    meter = pyln.Meter(SR, block_size=0.4)
    win, target = int(3 * SR), -28.0
    pts, gains = [], []
    for i in range(0, len(bed) - win, win // 2):
        L = meter.integrated_loudness(bed[i:i + win])
        gains.append(np.clip(target - L, -6, 6) if np.isfinite(L) else 0)
        pts.append(i + win // 2)
    g = np.interp(np.arange(len(bed)), pts, gains)
    g = np.convolve(np.pad(g, (SR, SR), mode="edge"), np.ones(2 * SR) / (2 * SR), "same")[SR:-SR]
    bed = bed * (10 ** (g / 20))[:, None]
    n = int(total * SR)
    bed = bed[:n] if len(bed) >= n else np.concatenate([bed, np.zeros((n - len(bed), 2))])
    fo = int(1.5 * SR)
    bed[-fo:] *= np.linspace(1, 0, fo)[:, None]
    bed = bed / max(np.abs(bed).max() / 0.95, 1.0)
    sf.write(out, bed.astype(np.float32), SR, subtype="FLOAT")
    print(f"song from {start:.1f}s to its end ({len(h) / SR:.1f}s), one unbroken pass, {total:.1f}s")


if __name__ == "__main__":
    main()
