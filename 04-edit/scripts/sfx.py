"""Sound effects for the edit, rendered from scratch."""
import sys, os
import numpy as np
from scipy import signal
import soundfile as sf

SR = 48000
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/music/sfx"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def t_(d):
    return np.arange(int(d * SR)) / SR


def bandsweep(noise, f_start, f_peak, f_end, q=2.0):
    """Noise through a band-pass whose centre moves start -> peak -> end (processed in short blocks)."""
    n = len(noise)
    out = np.zeros(n)
    blk = 512
    zi = None
    for i in range(0, n, blk):
        p = i / n
        fc = f_start + (f_peak - f_start) * (p / 0.5) if p < 0.5 else f_peak + (f_end - f_peak) * ((p - 0.5) / 0.5)
        bw = fc / q
        lo, hi = max(fc - bw / 2, 40) / (SR / 2), min(fc + bw / 2, 20000) / (SR / 2)
        b, a = signal.butter(2, [lo, hi], "band")
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        seg, zi = signal.lfilter(b, a, noise[i:i + blk], zi=zi)
        out[i:i + blk] = seg
    return out


def ir(seconds=2.2, damp=6000):
    n = int(seconds * SR)
    d = np.exp(-6.9 * np.arange(n) / SR / seconds)
    b, a = signal.butter(2, damp / (SR / 2))
    return np.stack([signal.lfilter(b, a, rng.standard_normal(n) * d) for _ in range(2)], 1)


IR = ir()


def verb(x, wet=0.3):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = np.stack([signal.fftconvolve(x[:, c], IR[:, c])[: len(x) + len(IR) - 1] for c in range(2)], 1)
    y *= np.sqrt((x ** 2).mean() / max((y ** 2).mean(), 1e-12))
    xx = np.vstack([x, np.zeros((len(IR) - 1, 2))])
    return (1 - wet) * xx + wet * y


def fade_tail(x, sec=0.05):
    n = min(int(sec * SR), len(x) // 2)
    x[-n:] *= np.linspace(1, 0, n)[:, None] if x.ndim == 2 else np.linspace(1, 0, n)
    return x


def save(name, x, peak=0.8):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    x = fade_tail(x / max(np.abs(x).max(), 1e-9) * peak)
    sf.write(f"{OUT}/{name}.wav", x.astype(np.float32), SR, subtype="FLOAT")
    print(name, f"{len(x) / SR:.2f}s")


def whoosh(d=0.5, f=(500, 2800, 700), pan=True):
    t = t_(d)
    nz = bandsweep(rng.standard_normal(len(t)), *f, q=1.6)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6
    x = nz * env
    if pan:
        p = np.linspace(-0.7, 0.7, len(t))
        x = np.stack([x * np.cos((p + 1) * np.pi / 4), x * np.sin((p + 1) * np.pi / 4)], 1)
    return verb(x, 0.2)


save("whoosh", whoosh(0.45), 0.7)
save("whoosh_soft", whoosh(0.8, (250, 1400, 400)), 0.6)

# pop: short rounded blip for a number or text landing
t = t_(0.12)
f = 700 + 700 * (1 - np.exp(-t * 60))
x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45)
x[:60] += rng.standard_normal(60) * 0.2 * np.linspace(1, 0, 60)
save("pop", verb(x, 0.15), 0.6)

# boom: cinematic low impact with a long tail
t = t_(2.6)
f = 34 + 46 * np.exp(-t * 9)
body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
b, a = signal.butter(2, 1800 / (SR / 2))
crack = signal.lfilter(b, a, rng.standard_normal(len(t))) * np.exp(-t * 18) * 0.6
save("boom", verb(body + crack, 0.35), 0.9)

# sub drop: falling sine for a transition into a reveal
t = t_(1.2)
f = 30 + 70 * np.exp(-t * 3.5)
save("subdrop", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.5) * np.minimum(t * 40, 1), 0.85)

# riser: noise + rising tone, gets louder, ends abruptly (cut on the next beat)
d = 3.0
t = t_(d)
nz = bandsweep(rng.standard_normal(len(t)), 300, 2500, 7000, q=1.2)
f = 180 * 2 ** (2.2 * t / d)
tone = sum(np.sin(2 * np.pi * np.cumsum(f * k) / SR) / k for k in (1, 2, 3)) * 0.25
env = (t / d) ** 2.2
x = verb((nz + tone) * env, 0.25)[: len(t)]
save("riser", x, 0.75)

# reverse swell: an A-minor bloom played backwards, sucks into a reveal
t = t_(2.5)
chord = sum(np.sin(2 * np.pi * hzv * t) * np.exp(-t * 2.0) for hzv in (220.0, 261.63, 329.63, 493.88))
sw = verb(chord, 0.6)[::-1]
save("reverse_swell", sw[-int(1.8 * SR):], 0.6)

# tick: single clock tick for counters
t = t_(0.04)
b, a = signal.butter(2, [2000 / (SR / 2), 6000 / (SR / 2)], "band")
save("tick", signal.lfilter(b, a, rng.standard_normal(len(t))) * np.exp(-t * 160), 0.5)
