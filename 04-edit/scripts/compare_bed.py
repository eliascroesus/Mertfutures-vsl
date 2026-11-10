"""Compare a score against Iman's bed on the measures that matter: width, tone, articulation, ticking.

    python compare_bed.py score.wav [t0 t1 ...]
"""
import sys, json
import numpy as np, soundfile as sf, librosa
from scipy import signal
from scipy.signal import find_peaks

EDGES = [40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 16000]


def bands(x, sr):
    f, P = signal.welch(x, fs=sr, nperseg=8192)
    b = np.array([10 * np.log10(P[(f >= a) & (f < c)].mean() + 1e-20) for a, c in zip(EDGES, EDGES[1:])])
    return b - b[3]          # relative to the 315-630 Hz band


def depth(y, sr, a, b, midis):
    C = np.abs(librosa.cqt(librosa.resample(y[int(a * sr):int(b * sr)], orig_sr=sr, target_sr=22050), sr=22050,
                           hop_length=256, fmin=librosa.note_to_hz('C2'), n_bins=216, bins_per_octave=36))
    db = 20 * np.log10(C.reshape(72, 3, -1).max(1) + 1e-9); fps = 22050 / 256
    out = []
    for mm in midis:
        x = np.convolve(db[mm - 36], np.ones(2) / 2, 'same')
        pk, _ = find_peaks(x, distance=int(0.1 * fps)); tr, _ = find_peaks(-x, distance=int(0.1 * fps))
        out.append(round(float(np.median(x[pk]) - np.median(x[tr])), 1) if len(pk) > 3 and len(tr) > 3 else None)
    return out


def tickband(y, sr, a, b):
    hb = signal.sosfiltfilt(signal.butter(4, [4500, 11000], 'band', fs=sr, output='sos'), y[int(a * sr):int(b * sr)])
    env = librosa.feature.rms(y=hb, frame_length=1024, hop_length=256)[0]; fps = sr / 256
    edb = np.convolve(20 * np.log10(env + 1e-9), np.ones(2) / 2, 'same')
    pk, pr = find_peaks(edb, prominence=3, distance=int(0.09 * fps))
    return round(float(np.median(np.diff(pk)) / fps), 3), round(float(np.median(pr['prominences'])), 1)


def report(name, y2, sr, wins, music_mask=None):
    L, R = y2[:, 0], y2[:, 1]
    M, S = (L + R) / 2, (L - R) / 2
    mm = M[music_mask] if music_mask is not None else M
    ss = S[music_mask] if music_mask is not None else S
    print(f"{name}: side vs centre {10 * np.log10((ss ** 2).mean() / (mm ** 2).mean()):.1f} dB")
    print(f"   side tone  " + " ".join(f"{v:6.1f}" for v in bands(S, sr)))
    print(f"   centre tone" + " ".join(f"{v:6.1f}" for v in bands(mm, sr)))
    for a, b in wins:
        print(f"   {a}-{b}s  string gaps E4/A4/E5/A5 {depth(S, sr, a, b, [64, 69, 76, 81])}   tick IOI/depth {tickband(S, sr, a, b)}")


if __name__ == "__main__":
    print("bands      " + " ".join(f"{a:>6d}" for a in EDGES[:-1]) + "   (dB vs 315-630 Hz)")
    y, sr = sf.read("/home/user/work/iman/iman_mix.wav")
    words = [w for s in json.load(open("/home/user/work/iman/iman_transcript.json")) for w in s["words"]]
    mask = np.ones(len(y), bool)
    for w in words:
        mask[int(w["s"] * sr):int((w["e"] + 0.08) * sr)] = False
    report("Iman (centre from his pauses)", y, sr, [(8, 14), (22, 28), (73, 79)], mask)
    x, sr2 = sf.read(sys.argv[1])
    w = [tuple(map(float, sys.argv[i:i + 2])) for i in range(2, len(sys.argv), 2)] or [(8, 14), (22, 28), (205, 211)]
    report("ours", x, sr2, w)
