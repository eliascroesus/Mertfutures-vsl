"""AB Nasdaq caption analysis: when captions change (frame differences in the caption area while the rest of the
picture holds still), what sound sits on each change, and the brightness profile behind the captions."""
import subprocess, json
import numpy as np, soundfile as sf
from scipy import signal

W, H, FPS = 640, 360, 30
T0, T1 = 12, 200
p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(T0), "-t", str(T1 - T0), "-i", "src/abnasdaqvsl.mp4",
                    "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(p, np.uint8).reshape(-1, H, W).astype(np.float32)
cap = fr[:, 270:325, 140:500]           # caption band (y 810-975 at 1080p)
top = fr[:, 20:200, :]                  # picture above it
dc = np.abs(np.diff(cap, axis=0)).mean((1, 2))
dt = np.abs(np.diff(top, axis=0)).mean((1, 2))
chg = [i + 1 for i in range(len(dc)) if dc[i] > 4.0 and dt[i] < 3.0 and (i == 0 or dc[i - 1] < 4.0)]
times = [T0 + c / FPS for c in chg]
print("caption changes:", len(times), "median gap", round(float(np.median(np.diff(times))), 2), "s")
# caption animation: how many frames does the caption area keep changing after a change starts?
lens = []
for c in chg:
    k = 0
    while c + k < len(dc) and dc[c - 1 + k] > 1.5:
        k += 1
    lens.append(k)
print("frames of motion per caption change: median", np.median(lens), "| distribution", np.bincount(np.minimum(lens, 10)))
# brightness profile behind captions: mean of each row, face-cam frames only (where no change happens)
prof = fr[:, :, :].mean(axis=(0, 2))
print("row brightness (top->bottom, every 20 px of 360):", " ".join(f"{v:.0f}" for v in prof[::20]))
# left-edge column (window) brightness by height: a dark gradient at the bottom would show here
col = fr[:, :, 0:40].mean(axis=(0, 2))
print("left window strip brightness by height:", " ".join(f"{v:.0f}" for v in col[::20]))
# audio around caption changes
y, sr = sf.read("ab/ab_mix.wav")
mid, side = y.mean(1), (y[:, 0] - y[:, 1]) / 2
def env(x, lo, hi):
    z = signal.sosfiltfilt(signal.butter(4, [lo, hi], "band", fs=sr, output="sos"), x)
    e = np.sqrt(np.convolve(z ** 2, np.ones(int(0.004 * sr)) / int(0.004 * sr), "same"))
    return 20 * np.log10(e + 1e-9)
for name, x in [("mid", mid), ("side", side)]:
    e = env(x, 3000, 9000)
    def burst(t):
        i0, i1 = int((t - 0.06) * sr), int((t + 0.06) * sr)
        ref = np.median(e[int((t - 0.6) * sr):int((t - 0.1) * sr)])
        return e[i0:i1].max() - ref
    at = np.array([burst(t) for t in times])
    rng = np.random.default_rng(0)
    rand = np.array([burst(t) for t in rng.uniform(T0 + 1, T1 - 1, 400)])
    print(f"{name}: high-band burst at caption changes median {np.median(at):.1f} dB vs random moments {np.median(rand):.1f} dB;"
          f" share of changes with a burst >8 dB: {np.mean(at > 8):.2f} (random {np.mean(rand > 8):.2f})")
json.dump({"times": times}, open("an/ab/caption_changes.json", "w"))
