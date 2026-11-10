"""Pure-music snapshots from the gaps between words (Whisper word timings), analysed over time."""
import json, sys, numpy as np, librosa, soundfile as sf
mix, tr, out = sys.argv[1], sys.argv[2], sys.argv[3]
x, sr = sf.read(mix); y = x.mean(1)
words = [w for s in json.load(open(tr)) for w in s["words"]]
gaps = []
for a, b in zip(words, words[1:]):
    g0, g1 = a["e"] + 0.04, b["s"] - 0.03
    if g1 - g0 >= 0.08: gaps.append((g0, g1))
if words[0]["s"] > 0.15: gaps.insert(0, (0.0, words[0]["s"] - 0.03))
gaps.append((words[-1]["e"] + 0.05, len(y) / sr))
print(f"{len(gaps)} gaps, {sum(b - a for a, b in gaps):.1f}s of pure music")
names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
segs = []
rows = []
for a, b in gaps:
    seg = y[int(a * sr):int(b * sr)]
    if len(seg) < 2048: continue
    segs.append(seg * np.hanning(len(seg)) ** 0.25)
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=1 << 16)); f = np.fft.rfftfreq(1 << 16, 1 / sr)
    pcp = np.zeros(12)
    sel = (f > 55) & (f < 2000)
    midi = 69 + 12 * np.log2(f[sel] / 440)
    np.add.at(pcp, np.round(midi).astype(int) % 12, S[sel] ** 2)
    lvl = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)
    low = 10 * np.log10((S[(f > 20) & (f < 120)] ** 2).sum() / ((S[f > 20] ** 2).sum() + 1e-12) + 1e-12)
    cent = (f * S).sum() / (S.sum() + 1e-9)
    rows.append((a, b, lvl, low, cent, pcp / (pcp.sum() + 1e-12)))
sf.write(out, np.concatenate(segs), sr)
# summary per 10 s
print(f"{'window':>8} {'n':>3} {'level':>6} {'bass%':>6} {'bright':>6}  strongest pitch classes")
for t0 in range(0, int(len(y) / sr) + 1, 10):
    rr = [r for r in rows if t0 <= r[0] < t0 + 10]
    if not rr: continue
    p = np.mean([r[5] for r in rr], 0)
    top = " ".join(f"{names[i]}:{p[i]*100:.0f}" for i in np.argsort(p)[::-1][:5])
    print(f"{t0:5d}-{t0+10:<3d}{len(rr):3d} {np.median([r[2] for r in rr]):6.1f} {np.median([r[3] for r in rr]):6.1f} {np.median([r[4] for r in rr]):6.0f}  {top}")
p = np.mean([r[5] for r in rows], 0)
print("whole video pitch classes:", " ".join(f"{names[i]}:{p[i]*100:.0f}%" for i in np.argsort(p)[::-1][:8]))
