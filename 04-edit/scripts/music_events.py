"""How often does the music change? Texture changes (novelty peaks) and short drop-outs in a music-only signal.

    python music_events.py file.wav [side|mid] [t0 t1]
"""
import sys
import numpy as np, soundfile as sf, librosa
from scipy.signal import find_peaks


def analyse(path, which="side", t0=0, t1=None):
    y, sr = sf.read(path)
    y = (y[:, 0] - y[:, 1]) / 2 if which == "side" else y.mean(1)
    y = y[int(t0 * sr): int(t1 * sr) if t1 else None]
    y = librosa.resample(y, orig_sr=sr, target_sr=22050); sr = 22050
    hop = 512; fps = sr / hop
    C = librosa.amplitude_to_db(np.abs(librosa.cqt(y, sr=sr, hop_length=hop, fmin=librosa.note_to_hz("C2"), n_bins=72)), ref=np.max)
    # beat-free texture features averaged over 0.5 s, novelty from a checkerboard kernel over +-4 s
    w = int(0.5 * fps)
    F = np.stack([C[:, i:i + w].mean(1) for i in range(0, C.shape[1] - w, w)], 1)
    F = (F - F.mean(1, keepdims=True)) / (F.std(1, keepdims=True) + 1e-6)
    Fn = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-9)
    Sm = Fn.T @ Fn
    k = 8
    g = np.outer(np.r_[-np.ones(k), np.ones(k)], np.r_[-np.ones(k), np.ones(k)])
    nov = np.array([np.sum(Sm[i - k:i + k, i - k:i + k] * g) if k <= i < len(Sm) - k else 0 for i in range(len(Sm))])
    nov = np.maximum(nov, 0) / (nov.max() + 1e-9)
    pk, _ = find_peaks(nov, height=0.25, distance=6)
    ch = (pk * 0.5 + t0).round(1)
    # drop-outs: broadband level falls 10+ dB below the surrounding 3 s for 0.15-1.5 s
    rms = 20 * np.log10(librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0] + 1e-9)
    ref = np.convolve(rms, np.ones(int(3 * fps)) / int(3 * fps), "same")
    low = rms < ref - 10
    drops, i = [], 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if 0.15 <= (j - i) / fps <= 1.5:
                drops.append((round(i / fps + t0, 1), round((j - i) / fps, 2)))
            i = j
        else:
            i += 1
    dur = len(y) / sr
    return ch, drops, dur


if __name__ == "__main__":
    which = sys.argv[2] if len(sys.argv) > 2 else "side"
    t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    t1 = float(sys.argv[4]) if len(sys.argv) > 4 else None
    ch, drops, dur = analyse(sys.argv[1], which, t0, t1)
    gaps = np.diff(ch) if len(ch) > 1 else []
    print(f"{sys.argv[1].split('/')[-1]} ({dur:.0f}s): {len(ch)} texture changes = one every {dur / max(len(ch), 1):.1f}s"
          f" (median gap {np.median(gaps) if len(gaps) else 0:.1f}s)")
    print("   at:", " ".join(map(str, ch[:40])))
    print(f"   drop-outs: {len(drops)}", drops[:25])
