"""Turn a song into a boom-free, looped tension bed for the whole VSL.

1. Keep only the tonal part (harmonic/percussive separation drops kicks, 808 hits, snares, claps, hats) and cut
   everything under the bass range, so no boom is left.
2. Loop it on its own 2-beat grid, choosing the jump points where the music before the jump matches the music before
   the landing point (so the joins are seamless), ending on the song's real outro at the end of the video.
3. Even the level out (slow gain riding to a steady loudness) so the tension holds the whole way.

    python song_bed.py song.wav total_seconds out_dir
"""
import json, sys
import numpy as np, soundfile as sf, librosa, pyloudnorm as pyln
from scipy import signal

SR = 48000


def deboom(y):
    out = []
    for c in range(y.shape[1]):
        D = librosa.stft(y[:, c], n_fft=4096, hop_length=1024)
        Hm, Pm = librosa.decompose.hpss(D, margin=(1.0, 2.0))          # strict on percussion
        out.append(librosa.istft(Hm, hop_length=1024, length=len(y)))
    h = np.stack(out, 1)
    h = signal.sosfiltfilt(signal.butter(6, 160, "high", fs=SR, output="sos"), h, axis=0)   # no sub, no 808
    return h


def grid_chroma(m, grid):
    C = librosa.feature.chroma_cqt(y=librosa.resample(m, orig_sr=SR, target_sr=22050), sr=22050, hop_length=512)
    fps = 22050 / 512
    rows = []
    for a, b in zip(grid, grid[1:]):
        rows.append(C[:, int(a * fps):max(int(b * fps), int(a * fps) + 1)].mean(1))
    R = np.array(rows)
    return R / (np.linalg.norm(R, axis=1, keepdims=True) + 1e-9)


def main():
    src, total, outdir = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    y, sr = sf.read(src, always_2d=True)
    assert sr == SR
    h = deboom(y)
    sf.write(f"{outdir}/song_noboom.wav", h.astype(np.float32), SR, subtype="FLOAT")
    # 2-beat grid from the song's own boom pulse (measured: every 1.3483 s from 5.57 s)
    P, g0 = 1.3483, 5.57
    grid = np.arange(g0, len(h) / SR - 0.5, P)
    R = grid_chroma(h.mean(1), grid)
    ctx = 4
    def sim(i, j):        # similarity of the 4 grid cells before grid point i and before grid point j
        return float(np.mean([R[i - k] @ R[j - k] for k in range(1, ctx + 1)]))
    gi = lambda t: int(np.argmin(np.abs(grid - t)))
    end_song = len(h) / SR
    need = total + 2.0
    best = None
    if need < end_song - g0:                        # shorter than the song: one seamless skip, ending on the real outro
        skip = int(round((end_song - g0 - need) / P))
        for a1 in range(gi(30), gi(end_song - 30) - skip):
            score = 2 * sim(a1, a1 + skip)
            if best is None or score > best[0]:
                best = (score, a1, a1 + skip, None, None)
    for a1 in range(gi(160), gi(176) + 1) if best is None else []:   # leave pass 1 here ...
        for b in range(gi(10), gi(60) + 1):         # ... and jump back to here
            if sim(a1, b) < 0.85:
                continue
            for b2 in range(gi(118), gi(150) + 1):  # final pass from here to the real ending
                rest = need - (grid[a1] - g0) - (end_song - grid[b2])
                a2 = gi(grid[b] + rest)
                if not (gi(100) <= a2 <= gi(176)):
                    continue
                score = sim(a1, b) + sim(a2, b2)
                if best is None or score > best[0]:
                    best = (score, a1, b, a2, b2)
    score, a1, b, a2, b2 = best
    if a2 is None:
        plan = [(g0, grid[a1]), (grid[b], end_song)]
    else:
        plan = [(g0, grid[a1]), (grid[b], grid[a2]), (grid[b2], end_song)]
    xf = int(0.25 * SR)
    bed = np.zeros((0, 2))
    for s, e in plan:
        seg = h[int(s * SR):int(e * SR)].copy()
        if len(bed):
            r = np.linspace(0, 1, xf)[:, None]
            bed[-xf:] = bed[-xf:] * np.sqrt(1 - r) + seg[:xf] * np.sqrt(r)
            seg = seg[xf:]
        bed = np.concatenate([bed, seg])
    # level riding: 3 s loudness windows pulled toward a steady target, gain moves slowly
    meter = pyln.Meter(SR, block_size=0.4)
    win = int(3 * SR)
    target = -28.0
    pts, gains = [], []
    for i in range(0, len(bed) - win, win // 2):
        L = meter.integrated_loudness(bed[i:i + win])
        g = np.clip(target - L, -6, 6) if np.isfinite(L) else 0
        pts.append(i + win // 2); gains.append(g)
    gcurve = np.interp(np.arange(len(bed)), pts, gains)
    gcurve = np.convolve(np.pad(gcurve, (SR, SR), mode="edge"), np.ones(2 * SR) / (2 * SR), "same")[SR:-SR]
    bed = bed * (10 ** (gcurve / 20))[:, None]
    n_end = int((total + 1.2) * SR)                                   # ring a little past the last frame
    if len(bed) < n_end:
        bed = np.concatenate([bed, np.zeros((n_end - len(bed), 2))])
    bed = bed[:n_end]
    fo = int(2.0 * SR)
    bed[n_end - fo:] *= np.linspace(1, 0, fo)[:, None]
    pk = np.abs(bed).max()
    if pk > 0.95:
        bed = bed / pk * 0.95
    sf.write(f"{outdir}/stem_score.wav", bed.astype(np.float32), SR, subtype="FLOAT")
    json.dump({"passes": [[round(s, 3), round(e, 3)] for s, e in plan], "join_similarity": round(score / 2, 3)},
              open(f"{outdir}/loop_plan.json", "w"), indent=1)
    print("passes (song seconds):", [(round(s, 1), round(e, 1)) for s, e in plan], "join similarity", round(score / 2, 3),
          "length", round(len(bed) / SR, 1))


if __name__ == "__main__":
    main()
