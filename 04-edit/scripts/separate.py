"""Split a mix into voice and background with librosa's REPET-SIM (nearest-neighbour filtering + soft masks)."""
import sys, numpy as np, librosa, soundfile as sf
y, sr = librosa.load(sys.argv[1], sr=44100, mono=False)
y = np.atleast_2d(y)
outs_bg, outs_fg = [], []
for ch in y:
    S, phase = librosa.magphase(librosa.stft(ch, n_fft=4096, hop_length=1024))
    S_filter = librosa.decompose.nn_filter(S, aggregate=np.median, metric="cosine", width=int(librosa.time_to_frames(2.0, sr=sr, hop_length=1024)))
    S_filter = np.minimum(S, S_filter)
    margin_i, margin_v, power = 2, 10, 2
    mask_i = librosa.util.softmask(S_filter, margin_i * (S - S_filter), power=power)
    mask_v = librosa.util.softmask(S - S_filter, margin_v * S_filter, power=power)
    bg = librosa.istft(mask_i * S * phase, hop_length=1024, length=len(ch))
    fg = librosa.istft(mask_v * S * phase, hop_length=1024, length=len(ch))
    outs_bg.append(bg); outs_fg.append(fg)
sf.write(sys.argv[2], np.stack(outs_bg, 1), sr)
sf.write(sys.argv[3], np.stack(outs_fg, 1), sr)
print("ok")
