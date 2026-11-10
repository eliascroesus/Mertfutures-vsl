"""Remove a single speaker's voiced harmonics (pYIN f0 comb mask) and high-frequency consonant bursts, leaving the music."""
import sys, numpy as np, librosa, soundfile as sf
y, sr = librosa.load(sys.argv[1], sr=22050, mono=True)
hop, nfft = 256, 8192
f0, voiced, prob = librosa.pyin(y, fmin=70, fmax=300, sr=sr, frame_length=2048, hop_length=hop)
D = librosa.stft(y, n_fft=nfft, hop_length=hop)
freqs = librosa.fft_frequencies(sr=sr, n_fft=nfft)
mask = np.ones(D.shape, np.float32)
n = min(D.shape[1], len(f0))
for t in range(n):
    if voiced[t] and np.isfinite(f0[t]):
        for k in range(1, int(4000 / f0[t]) + 1):
            fk = k * f0[t]
            w = max(6.0, fk * 0.025)                 # ±2.5 % around each harmonic
            mask[np.abs(freqs - fk) < w, t] = 0.03
# speech energy above 2.5 kHz follows the syllables; damp it when the voice is active
active = np.zeros(D.shape[1], bool); active[:n] = voiced[:n]
mask[freqs > 2500][:, active] *= 0.1
music = librosa.istft(D * mask, hop_length=hop, length=len(y))
sf.write(sys.argv[2], music, sr)
print("voiced frames", round(float(np.mean(voiced)) * 100), "%")
