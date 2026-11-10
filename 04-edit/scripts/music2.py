"""Cinematic fallback score: string-like pads (dark + bright), high shimmer, sub swells, low string pulse.
Am(add9) - Fmaj7 - C(add9) - G6, 80 BPM, 6 s per chord, rendered as seamless 24 s loops and tiled."""
import os, sys
import numpy as np
from scipy import signal
import soundfile as sf

sys.path.insert(0, "/home/user/work/scripts")
import music as M          # helpers: hz, add_wrapped, env_adsr, loop_filter, lowpass, highpass, reverb_loop, stereo, norm

SR, N, CYCLE, CHORD_LEN, BEAT = M.SR, M.N, M.CYCLE, M.CHORD_LEN, M.BEAT
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/music2"
CYCLES = int(sys.argv[2]) if len(sys.argv) > 2 else 19
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(21)

CHORDS = [
    ["A2", "E3", "A3", "C4", "E4", "B4"],
    ["F2", "C3", "A3", "C4", "E4", "A4"],
    ["C3", "G3", "C4", "E4", "G4", "D5"],
    ["G2", "D3", "B3", "D4", "E4", "B4"],
]
ROOTS = ["A1", "F1", "C2", "G1"]


def ensemble(f, n, voices=5, spread=11, bright=1.0):
    """Detuned saw ensemble with slow independent vibrato per voice: the basis of a string pad."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    for v in range(voices):
        cents = (v - (voices - 1) / 2) / ((voices - 1) / 2) * spread
        vib = 1 + 0.0018 * np.sin(2 * np.pi * rng.uniform(4.6, 5.6) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * 2 ** (cents / 1200) * vib) / SR + rng.uniform(0, 6)
        top = int(min(28, 7000 / f))
        for k in range(1, top + 1):
            out += np.sin(k * ph) / k * np.exp(-(k - 1) / (5 * bright))
    return out / voices


def pads(cut, bright, air=False):
    buf = np.zeros((N, 2))
    for ci, chord in enumerate(CHORDS):
        start = int(ci * CHORD_LEN * SR)
        n = int((CHORD_LEN + 3.0) * SR)
        for ni, note in enumerate(chord):
            f = M.hz(note) * (2 if air else 1)
            v = ensemble(f, n, bright=bright)
            v = M.lowpass(v, cut, 2) * M.env_adsr(n, 2.2, 3.0)
            pan = (ni / (len(chord) - 1) - 0.5) * 1.2
            gain = 0.16 if ni > 0 else 0.22
            M.add_wrapped(buf, M.stereo(v, pan) * gain, start)
    if air:
        buf = M.loop_filter(M.highpass, buf, 1800)
    wet = M.reverb_loop(buf, 0.55)
    return M.norm(wet, 0.5)


def sub():
    buf = np.zeros((N, 2))
    t_n = int((CHORD_LEN + 2.0) * SR)
    t = np.arange(t_n) / SR
    for ci, r in enumerate(ROOTS):
        f = M.hz(r)
        x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
        x *= M.env_adsr(t_n, 1.5, 2.0) * (0.75 + 0.25 * np.sin(np.pi * np.clip(t / CHORD_LEN, 0, 1)))
        M.add_wrapped(buf, M.stereo(x, 0) * 0.6, int(ci * CHORD_LEN * SR))
    return M.norm(buf, 0.55)


def pulse():
    """Low string ostinato in eighth notes on the chord root (cinematic 'momentum')."""
    buf = np.zeros((N, 2))
    step = BEAT / 2
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    for ci, r in enumerate(ROOTS):
        f = M.hz(r) * 2
        for s in range(int(CHORD_LEN / step)):
            oct_ = 2 if s % 4 == 2 else 1
            x = ensemble(f * oct_, n, voices=3, spread=7, bright=0.6)
            env = (1 - np.exp(-t * 90)) * np.exp(-t * 7.5)
            acc = 1.0 if s % 2 == 0 else 0.7
            M.add_wrapped(buf, M.stereo(M.lowpass(x * env, 900, 2), 0) * acc * 0.5, int((ci * CHORD_LEN + s * step) * SR))
    return M.norm(M.reverb_loop(buf, 0.3), 0.5)


STEMS = {"pads_dark": lambda: pads(950, 0.8), "pads_bright": lambda: pads(2600, 1.2), "air": lambda: pads(6000, 1.0, air=True),
         "sub": sub, "pulse": pulse}

if __name__ == "__main__":
    for name, fn in STEMS.items():
        loop = fn().astype(np.float32)
        sf.write(f"{OUT}/loop_{name}.wav", loop, SR, subtype="FLOAT")
        sf.write(f"{OUT}/stem_{name}.wav", np.tile(loop, (CYCLES, 1)), SR, subtype="FLOAT")
        print(name, "ok")
