import sys, numpy as np, librosa, soundfile as sf
import pyloudnorm as pyln
x, sr = sf.read(sys.argv[1]); y = x.mean(1) if x.ndim > 1 else x
dur = len(y) / sr
meter = pyln.Meter(sr, block_size=0.4)
names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
# chord templates (major/minor triads + sus)
templ = {}
for r in range(12):
    for q, iv in (("", (0, 4, 7)), ("m", (0, 3, 7)), ("sus4", (0, 5, 7)), ("5", (0, 7))):
        v = np.zeros(12); v[[(r + i) % 12 for i in iv]] = 1; templ[names[r] + q] = v / np.linalg.norm(v)
hop = 2048
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
S = np.abs(librosa.stft(y, n_fft=4096, hop_length=hop)); f = librosa.fft_frequencies(sr=sr, n_fft=4096)
cent = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
low = 20 * np.log10(np.sqrt((S[(f < 120)] ** 2).mean(0)) + 1e-9)
mid = 20 * np.log10(np.sqrt((S[(f >= 200) & (f < 2000)] ** 2).mean(0)) + 1e-9)
hi = 20 * np.log10(np.sqrt((S[(f >= 4000)] ** 2).mean(0)) + 1e-9)
fps = sr / hop
step = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
print(f"{'time':>6} {'LUFS':>6} {'low':>6} {'mid':>6} {'high':>6} {'bright':>7}  chord (top chroma)")
for t0 in np.arange(0, dur - 0.5, step):
    a, b = int(t0 * fps), int((t0 + step) * fps)
    seg = x[int(t0 * sr):int((t0 + step) * sr)]
    with np.errstate(all="ignore"):
        L = meter.integrated_loudness(seg) if len(seg) > 0.5 * sr else float("nan")
    c = C[:, a:b].mean(1); c = c / (np.linalg.norm(c) + 1e-9)
    best = max(templ, key=lambda k: templ[k] @ c)
    top = "".join(names[i] + " " for i in np.argsort(c)[::-1][:4])
    print(f"{t0:6.1f} {L:6.1f} {np.median(low[a:b]):6.1f} {np.median(mid[a:b]):6.1f} {np.median(hi[a:b]):6.1f} {np.median(cent[a:b]):7.0f}  {best:6s} ({top.strip()})")
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
tempo = librosa.feature.tempo(onset_envelope=oenv, sr=sr, hop_length=512, aggregate=None)
print("tempo estimates over time (BPM):", np.round(np.percentile(tempo, [10, 50, 90])))
ac = librosa.autocorrelate(oenv - oenv.mean(), max_size=int(4 * sr / 512)); ac /= ac[0]
lags = np.arange(len(ac)) * 512 / sr
pk = [(round(60 / lags[i]), round(ac[i], 2)) for i in range(int(0.25 * sr / 512), len(ac) - 1) if ac[i] > ac[i - 1] and ac[i] > ac[i + 1] and ac[i] > 0.12]
print("pulse peaks (BPM, strength):", pk[:8])
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=512, units="time", backtrack=False)
print(f"onsets: {len(on)} in {dur:.0f}s ({len(on) / dur:.1f}/s)")
