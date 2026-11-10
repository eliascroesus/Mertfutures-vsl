"""Multi-pitch piano roll of the music-only side channel (L-R) of Iman's mix, to see what the strings play.

    python iman_violins.py
"""
import json, numpy as np, librosa

C = np.load("an/iman_side_cqt.npy")            # 216 bins, C2.., 36/oct, hop 256 @ 22050
sr, hop = 22050, 256
fps = sr / hop
semi = C.reshape(72, 3, -1).max(1)              # 72 semitones from C2 (MIDI 36)
P = semi ** 2
# harmonic salience with iterative harmonic subtraction
H = [0, 12, 19, 24, 28, 31]                     # harmonics 1..6 in semitones
roll = np.zeros_like(P)
R = P.copy()
for it in range(4):
    sal = np.zeros_like(R)
    for h, d in enumerate(H):
        sal[:72 - d] += (0.8 ** h) * R[d:]
    k = sal.argmax(0)
    v = sal[k, np.arange(R.shape[1])]
    roll[k, np.arange(R.shape[1])] = np.maximum(roll[k, np.arange(R.shape[1])], v)
    for d in H:
        kk = np.clip(k + d, 0, 71)
        R[kk, np.arange(R.shape[1])] *= 0.1
roll_db = 10 * np.log10(roll + 1e-12)
roll_db -= np.percentile(roll_db[roll > 0], 99)
np.save("an/iman_roll_db.npy", roll_db)
names = [librosa.midi_to_note(36 + k, unicode=False) for k in range(72)]
# per half-second window: strongest notes in low (<C3), mid (C3-B4), high (>=C5)
out = []
for w0 in np.arange(0, C.shape[1] / fps - 0.5, 0.5):
    a, b = int(w0 * fps), int((w0 + 0.5) * fps)
    m = np.where(roll_db[:, a:b] > -30, roll_db[:, a:b] + 30, 0).sum(1)
    reg = lambda lo, hi: [names[k] for k in np.argsort(-m[lo:hi])[:2] + lo if m[k] > 20]
    out.append((w0, reg(0, 12), reg(12, 36), reg(36, 72)))
for w0, lo, mid, hi in out:
    print(f"{w0:5.1f}  low {' '.join(lo):10s} mid {' '.join(mid):10s} high {' '.join(hi)}")
