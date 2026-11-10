"""Music bed for Mert's VSL: 'Me And The Devil' (instrumental), the full song, looped once.

The song is 3:03 and the video longer, so it plays from the top, jumps back exactly 20 bars (keeps bar and phrase
position) at the beat where the harmony before and after the jump matches best (short equal-power crossfade), and then
plays through to its real outro, which lands on the last frame. A gentle low shelf keeps the 808 from muddying the voice,
and a slow level ride keeps the tension even.

    python mert_songbed.py song.wav total_seconds out.wav
"""
import json, sys
import numpy as np, soundfile as sf, librosa, pyloudnorm as pyln
from scipy import signal

SR = 48000
BEAT, B0 = 0.67338, 0.232          # measured beat period and first beat


def main():
    src, total, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    y, sr = sf.read(src, always_2d=True)
    assert sr == SR
    end = len(y) / SR
    jump = 80 * BEAT                                            # 20 bars of 4
    grid = np.arange(B0, end, BEAT)
    m = librosa.resample(y.mean(1), orig_sr=SR, target_sr=22050)
    C = librosa.feature.chroma_stft(y=m, sr=22050, hop_length=512)
    fps = 22050 / 512

    def ctx(t, a, b):
        seg = C[:, int((t + a) * fps):int((t + b) * fps)]
        v = seg.mean(1)
        return v / (np.linalg.norm(v) + 1e-9)

    best = None
    for t in grid:
        if t < 60 or t > end - 25:
            continue
        b = t - jump
        s = ctx(t, -4 * BEAT, 0) @ ctx(b, -4 * BEAT, 0) + ctx(t, 0, 4 * BEAT) @ ctx(b, 0, 4 * BEAT)
        if best is None or s > best[0]:
            best = (s, t, b)
    s, a1, b = best
    xf = int(0.12 * SR)
    head = y[:int(a1 * SR) + xf // 2].copy()
    tail = y[int(b * SR) - xf // 2:].copy()
    r = np.linspace(0, 1, xf)[:, None]
    bed = np.concatenate([head[:-xf], head[-xf:] * np.sqrt(1 - r) + tail[:xf] * np.sqrt(r), tail[xf:]])
    need = total + 0.4
    skip = max(0.0, len(bed) / SR - need)
    skip = round(skip / (4 * BEAT)) * 4 * BEAT if skip > 2 * BEAT else 0.0     # start on a bar so the groove sits
    bed = bed[int(skip * SR):]
    sos = signal.butter(2, 28, "high", fs=SR, output="sos")
    bed = signal.sosfiltfilt(sos, bed, axis=0)
    b_, a_ = shelf(110, -4.5)
    bed = signal.filtfilt(b_, a_, bed, axis=0)
    meter = pyln.Meter(SR, block_size=0.4)
    win, target = int(4 * SR), -24.0
    pts, gains = [], []
    for i in range(0, len(bed) - win, win // 2):
        L = meter.integrated_loudness(bed[i:i + win])
        gains.append(np.clip(target - L, -4, 4) if np.isfinite(L) else 0)
        pts.append(i + win // 2)
    g = np.interp(np.arange(len(bed)), pts, gains)
    g = np.convolve(np.pad(g, (2 * SR, 2 * SR), mode="edge"), np.ones(4 * SR) / (4 * SR), "same")[2 * SR:-2 * SR]
    bed = bed * (10 ** (g / 20))[:, None]
    n = int(total * SR)
    bed = bed[:n] if len(bed) >= n else np.concatenate([bed, np.zeros((n - len(bed), 2))])
    fi, fo = int(0.25 * SR), int(1.2 * SR)
    bed[:fi] *= np.linspace(0, 1, fi)[:, None]
    bed[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    bed = bed / max(np.abs(bed).max() / 0.95, 1.0)
    sf.write(out, bed.astype(np.float32), SR, subtype="FLOAT")
    json.dump({"jump_from": round(a1, 3), "jump_to": round(b, 3), "match": round(float(s) / 2, 3), "start_offset": round(skip, 3)},
              open(out.replace(".wav", "_loop.json"), "w"))
    print(f"song plays from {skip:.1f}s, jumps back at {a1:.2f}s to {b:.2f}s (match {s / 2:.3f}), ends on its outro")


def shelf(f0, gain_db, q=0.707):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    c = np.cos(w)
    b = [A * ((A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al)]
    a = [(A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al]
    return np.array(b) / a[0], np.array(a) / a[0]


if __name__ == "__main__":
    main()
