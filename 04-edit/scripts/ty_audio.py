"""Audio breakdown of the AB thank-you reference: music level under the voice, key/tempo/notes of the bed, music
structure over time, and every non-speech transient (SFX candidates) with its band profile.

    python ty_audio.py mix.wav transcript.json outdir
"""
import sys, json
import numpy as np, soundfile as sf, librosa, pyloudnorm as pyln
from scipy import signal
from scipy.signal import find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src, tr, od = sys.argv[1:4]
y, sr = sf.read(src)
L, R = y[:, 0], y[:, 1]
M, S = (L + R) / 2, (L - R) / 2
words = [w for s in json.load(open(tr)) for w in s["words"]]
meter = pyln.Meter(sr)

# speech mask (word spans + 80 ms tail) and music-only gaps
sp = np.zeros(len(M), bool)
for w in words:
    sp[int(w["s"] * sr):int((w["e"] + 0.08) * sr)] = True
gaps = []
i = 0
while i < len(sp):
    if not sp[i]:
        j = i
        while j < len(sp) and not sp[j]:
            j += 1
        if (j - i) / sr >= 0.3:
            gaps.append((i / sr, j / sr))
        i = j
    else:
        i += 1
print("speech-free gaps >= 0.3 s:", len(gaps), [(round(a, 2), round(b - a, 2)) for a, b in gaps][:40])


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


voice_db = rms_db(M[sp])
gap_x = np.concatenate([M[int(a * sr) + 2400:int(b * sr) - 2400] for a, b in gaps if b - a > 0.4]) if gaps else M[:0]
print(f"centre RMS while talking {voice_db:.1f} dB | in pauses {rms_db(gap_x):.1f} dB "
      f"-> music sits about {voice_db - rms_db(gap_x):.1f} dB under the voice (RMS)")
print(f"side RMS while talking {rms_db(S[sp]):.1f} dB | in pauses {rms_db(S[~sp]):.1f} dB")
print(f"integrated {meter.integrated_loudness(y):.1f} LUFS, true-ish peak {20 * np.log10(np.abs(y).max()):.2f} dBFS")

# tone of the bed: side channel band profile + pauses centre
EDGES = [40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 16000]


def bands(x):
    f, P = signal.welch(x, fs=sr, nperseg=8192)
    b = np.array([10 * np.log10(P[(f >= a) & (f < c)].mean() + 1e-20) for a, c in zip(EDGES, EDGES[1:])])
    return b - b.max()


print("bands       " + " ".join(f"{a:>6d}" for a in EDGES[:-1]))
print("side        " + " ".join(f"{v:6.1f}" for v in bands(S)))
print("pause centre" + " ".join(f"{v:6.1f}" for v in bands(gap_x)))
print("voice centre" + " ".join(f"{v:6.1f}" for v in bands(M[sp])))

# key / notes / tempo from the side channel (music-dominated)
y22 = librosa.resample(S, orig_sr=sr, target_sr=22050)
chroma = librosa.feature.chroma_cqt(y=y22, sr=22050, hop_length=512)
names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
prof = chroma.mean(1)
maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
sc = [(np.corrcoef(prof, np.roll(maj, k))[0, 1], names[k] + " major") for k in range(12)] + \
     [(np.corrcoef(prof, np.roll(mnr, k))[0, 1], names[k] + " minor") for k in range(12)]
sc.sort(reverse=True)
print("chroma profile:", " ".join(f"{n}:{v:.2f}" for n, v in zip(names, prof / prof.max())))
print("key guesses:", [(k, round(c, 2)) for c, k in sc[:3]])
oenv = librosa.onset.onset_strength(y=y22, sr=22050, hop_length=512)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=22050, hop_length=512)
bt = librosa.frames_to_time(beats, sr=22050, hop_length=512)
print(f"tempo {float(np.atleast_1d(tempo)[0]):.1f} BPM, beats tracked {len(bt)}, first beats {np.round(bt[:8], 2)}")
ac = librosa.autocorrelate(oenv - oenv.mean(), max_size=int(4 * 22050 / 512))
lags = np.arange(len(ac)) * 512 / 22050
pk, _ = find_peaks(ac[10:], distance=5)
pk = pk + 10
top = sorted(pk, key=lambda k: -ac[k])[:5]
print("onset autocorr peaks (s):", [round(lags[k], 3) for k in sorted(top)])

# chord/bass movement every 2 s window: strongest pitch classes
seg = []
fps = 22050 / 512
for t in np.arange(0, len(y22) / 22050 - 2, 4):
    c = chroma[:, int(t * fps):int((t + 4) * fps)].mean(1)
    o = np.argsort(c)[::-1][:3]
    seg.append(f"{t:.0f}:{'/'.join(names[k] for k in o)}")
print("top pitch classes per 4 s:", " ".join(seg))

# bass notes (40-160 Hz) via CQT on side + centre-in-pauses is unreliable; use side only
Cq = np.abs(librosa.cqt(y22, sr=22050, hop_length=512, fmin=librosa.note_to_hz("C1"), n_bins=84))
Cdb = librosa.amplitude_to_db(Cq, ref=np.max)
bass = Cq[:36]
seq = []
for t in np.arange(0, Cq.shape[1] / fps - 1, 2):
    b = bass[:, int(t * fps):int((t + 2) * fps)].mean(1)
    seq.append(f"{t:.0f}:{librosa.midi_to_note(24 + int(np.argmax(b)))}")
print("bass per 2 s:", " ".join(seq))

# music level over time (side, 1 s) and drop-outs
hop = int(0.05 * sr)
env = np.array([rms_db(S[k:k + hop]) for k in range(0, len(S) - hop, hop)])
sm = np.convolve(env, np.ones(20) / 20, "same")
print("side level per 5 s (dB):", " ".join(f"{k * 5}:{sm[k * 100]:.0f}" for k in range(int(len(sm) / 100))))
ref = np.convolve(env, np.ones(60) / 60, "same")
low = env < ref - 10
drops, k = [], 0
while k < len(low):
    if low[k]:
        j = k
        while j < len(low) and low[j]:
            j += 1
        if j - k >= 3:
            drops.append((round(k * 0.05, 2), round((j - k) * 0.05, 2)))
        k = j
    else:
        k += 1
print("music drop-outs (side 10 dB under its 3 s average, >=0.15 s):", drops)

# transients: onsets in side (SFX are often wide) and in centre during pauses
def band_env(x, lo, hi, win=0.01):
    z = signal.sosfiltfilt(signal.butter(4, [lo, hi], "band", fs=sr, output="sos"), x)
    n = int(win * sr)
    e = np.sqrt(np.convolve(z ** 2, np.ones(n) / n, "same"))[::n]
    return 20 * np.log10(e + 1e-9)


ev = []
for name, x in [("side", S), ("mid", M)]:
    for lo, hi, tag in [(30, 150, "low"), (150, 2000, "midband"), (2500, 12000, "high")]:
        e = band_env(x, lo, hi)
        base = np.convolve(e, np.ones(150) / 150, "same")
        pk, pr = find_peaks(e - base, height=9, distance=25, prominence=9)
        for p_ in pk:
            t = p_ * 0.01
            ev.append((round(t, 2), name, tag, round(float(e[p_] - base[p_]), 1), bool(sp[min(int(t * sr), len(sp) - 1)])))
ev.sort()
json.dump(ev, open(f"{od}/transients.json", "w"))
print("transients (t, channel, band, dB over local, during speech):")
for e_ in ev:
    if e_[1] == "side" or not e_[4]:
        print("  ", e_)

# spectrogram images: side channel and centre, 40 s per row
for name, x in [("side", S), ("mid", M)]:
    fig, axs = plt.subplots(5, 1, figsize=(22, 18))
    for r in range(5):
        a, b = r * 33, min((r + 1) * 33, len(x) / sr)
        seg_ = x[int(a * sr):int(b * sr)]
        f, t, Z = signal.spectrogram(seg_, fs=sr, nperseg=2048, noverlap=1536)
        axs[r].pcolormesh(t + a, f, 10 * np.log10(Z + 1e-14), shading="auto", vmin=-120, vmax=-40, cmap="magma")
        axs[r].set_yscale("symlog", linthresh=200)
        axs[r].set_ylim(30, 16000)
        axs[r].set_xticks(np.arange(int(a), int(b) + 1, 1), minor=True)
        axs[r].set_xticks(np.arange(int(a), int(b) + 1, 2))
        axs[r].grid(True, which="major", axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{od}/spec_{name}.png", dpi=55)
    plt.close()
# CQT piano roll of the side channel
fig, axs = plt.subplots(5, 1, figsize=(22, 18))
for r in range(5):
    a, b = int(r * 33 * fps), int(min((r + 1) * 33, Cq.shape[1] / fps) * fps)
    axs[r].imshow(Cdb[:, a:b], origin="lower", aspect="auto", vmin=-60, vmax=0, cmap="magma",
                  extent=[a / fps, b / fps, 24, 108])
    axs[r].set_yticks(range(24, 109, 12))
    axs[r].set_yticklabels([librosa.midi_to_note(m_) for m_ in range(24, 109, 12)])
    axs[r].set_xticks(np.arange(int(a / fps), int(b / fps) + 1, 2))
    axs[r].grid(True, axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{od}/cqt_side.png", dpi=55)
print("images written")
