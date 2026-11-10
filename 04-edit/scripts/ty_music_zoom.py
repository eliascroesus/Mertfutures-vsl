"""Close-up piano roll of the side channel (music) for a window, plus the loop length from CQT self-similarity.

    python ty_music_zoom.py mix.wav t0 t1 out.png
"""
import sys
import numpy as np, soundfile as sf, librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

y, sr = sf.read(sys.argv[1]); t0, t1 = float(sys.argv[2]), float(sys.argv[3])
S = (y[:, 0] - y[:, 1]) / 2
x = librosa.resample(S[int(t0 * sr):int(t1 * sr)], orig_sr=sr, target_sr=22050)
hop = 256; fps = 22050 / hop
C = np.abs(librosa.cqt(x, sr=22050, hop_length=hop, fmin=librosa.note_to_hz("C2"), n_bins=60))
D = librosa.amplitude_to_db(C, ref=np.max)
fig, ax = plt.subplots(1, 1, figsize=(24, 9))
ax.imshow(D, origin="lower", aspect="auto", vmin=-50, vmax=0, cmap="magma", extent=[t0, t1, 36 - 0.5, 96 - 0.5])
ax.set_yticks(range(36, 96)); ax.set_yticklabels([librosa.midi_to_note(m) for m in range(36, 96)], fontsize=6)
ax.set_xticks(np.arange(t0, t1, 0.25), minor=True); ax.set_xticks(np.arange(t0, t1 + 0.01, 1.0))
ax.grid(True, which="both", axis="x", alpha=0.25); ax.grid(True, axis="y", alpha=0.1)
plt.tight_layout(); plt.savefig(sys.argv[4], dpi=60)
# loop length: autocorrelation of the (log) CQT over time lag
F = np.log1p(C * 50); F = F - F.mean(1, keepdims=True)
lag_max = int(12 * fps)
ac = np.array([np.sum(F[:, :-l] * F[:, l:]) / (F.shape[1] - l) for l in range(1, lag_max)])
from scipy.signal import find_peaks
pk, _ = find_peaks(ac, distance=int(0.3 * fps))
best = sorted(pk, key=lambda k: -ac[k])[:6]
print("loop-length candidates (s):", [round((k + 1) / fps, 3) for k in sorted(best)])
