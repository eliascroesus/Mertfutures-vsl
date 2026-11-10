"""Subtle sound effects built from real recordings (VSCO 2 CE, CC0): a cash-register "cha-ching", a lighter one for
quick repeats, and a phone-notification "ding".

    python sfx2.py OUTDIR
"""
import os, sys
import numpy as np, soundfile as sf
from scipy import signal

SR = 48000
X = "/home/user/sgossner/extra"


def load(name):
    x, sr = sf.read(f"{X}/{name}", always_2d=True)
    x = x.mean(1)
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x)
    return x / (np.abs(x).max() + 1e-9)


def bp(x, lo, hi):
    return signal.sosfiltfilt(signal.butter(4, [lo, hi], "band", fs=SR, output="sos"), x)


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def pitch(x, semis):
    r = 2 ** (semis / 12)
    return np.interp(np.arange(0, len(x) - 1, r), np.arange(len(x)), x)


def onset(x):
    return x[max(0, int(np.argmax(np.abs(x) > 0.05)) - 24):]


def place(buf, x, t, g):
    s = int(t * SR)
    buf[s:s + len(x)] += x[:len(buf) - s] * g


def cash(semis=0.0, light=False):
    n = int(1.3 * SR)
    out = np.zeros(n)
    cha = bp(onset(load("tamb2_1.wav")), 2500, 9000)[: int(0.16 * SR)]
    cha *= env(len(cha), 0.002, 0.05)
    place(out, cha, 0.0, 0.0 if light else 0.45)                 # "cha": the drawer
    jing = bp(onset(load("sleighbell1_hit_quiet.wav")), 3000, 12000)[: int(0.35 * SR)]
    jing *= env(len(jing), 0.002, 0.09)
    place(out, jing, 0.085, 0.22)                                # coins
    bell = pitch(onset(load("glock_medium_C7.wav")), semis)[: int(1.1 * SR)]
    bell *= env(len(bell), 0.001, 0.35)
    tri = pitch(onset(load("triangle1.wav")), semis)[: int(1.1 * SR)]
    tri = bp(tri, 2000, 14000) * env(len(tri), 0.001, 0.3)
    place(out, bell, 0.09, 0.9)                                  # "ching": the bell
    place(out, tri, 0.09, 0.15)
    out = signal.sosfiltfilt(signal.butter(2, 9000, "low", fs=SR, output="sos"), out)
    out = np.stack([out, np.roll(out, int(0.0004 * SR))], 1)     # a hair of width
    return (out / np.abs(out).max() * 0.9).astype(np.float32)


def ding():
    d = onset(load("glock_medium_C7.wav"))[: int(0.9 * SR)] * env(int(0.9 * SR), 0.001, 0.25)[:None]
    d2 = pitch(onset(load("glock_medium_G6.wav")), 0)[: int(0.9 * SR)]
    d2 = d2 * env(len(d2), 0.001, 0.25)
    out = np.zeros(int(1.1 * SR))
    place(out, d2, 0.0, 0.7)
    place(out, d, 0.11, 0.9)
    out = np.stack([out, out], 1)
    return (out / np.abs(out).max() * 0.9).astype(np.float32)


def click(seed):
    """A subtle mouse click: a crisp tick (band-limited noise, ~3 ms) on a tiny plastic body (~3.3 kHz, ~6 ms)."""
    r = np.random.default_rng(seed)
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    tick = bp(r.standard_normal(n), 3500, 11000) * np.exp(-t / 0.0025)
    f = 3300 * (1 + 0.05 * (seed - 1.5))
    body = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006) * 0.3
    x = tick / (np.abs(tick).max() + 1e-9) + body
    x[: int(0.0004 * SR)] *= np.linspace(0, 1, int(0.0004 * SR))
    x = np.stack([x, x], 1)
    return (x / np.abs(x).max() * 0.9).astype(np.float32)


if __name__ == "__main__":
    o = sys.argv[1]
    os.makedirs(o, exist_ok=True)
    sf.write(f"{o}/cash.wav", cash(), SR, subtype="FLOAT")
    for i, s in enumerate((0, 1, 2)):
        sf.write(f"{o}/cash_light{i + 1}.wav", cash(s, light=True), SR, subtype="FLOAT")
    sf.write(f"{o}/ding.wav", ding(), SR, subtype="FLOAT")
    for i in range(4):
        sf.write(f"{o}/click{i + 1}.wav", click(i), SR, subtype="FLOAT")
    print("ok")
