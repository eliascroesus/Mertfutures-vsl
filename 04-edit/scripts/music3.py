"""Tension score modelled on Iman Gadzhi's VSL bed: starts on frame 1 thin and eerie, slams a sub/braam hit after the
hook, then drives on an eighth-note bass pulse at ~115 BPM in A minor, never dropping out.

Loops (A minor, 115 BPM, 4 bars per chord, Am-F-C-G):
  pulse_pedal  eighth-note bass on A (tension sections)      pulse_prog  eighth-note bass following the chords
  drone        A/E open-fifth bed                             tension_hi  high A-Bb-E cluster with 16th tremolo
  pads         Am-F-C-G string pads                           ticks       16th-note muted ticks
One-shots: braam (cinematic hit), riser_hook (5.7 s build into the first hit), hit_soft.
"""
import os, sys
import numpy as np
from scipy import signal
import soundfile as sf

SR = 48000
BPM = 115.0
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORD = 4 * BAR
CYCLE = 4 * CHORD
N = int(round(CYCLE * SR))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/music3"
REPEAT = int(sys.argv[2]) if len(sys.argv) > 2 else 13
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(115)


def hz(n):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    return 440.0 * 2 ** ((names[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def loop_hz(f):
    return round(f * CYCLE) / CYCLE


def lp(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x, axis=0)


def loopf(fn, x, *a):
    n = len(x)
    return fn(np.concatenate([x, x, x]), *a)[n:2 * n]


def add_wrap(buf, x, start):
    s = start % len(buf)
    i = 0
    while i < len(x):
        k = min(len(x) - i, len(buf) - s)
        buf[s:s + k] += x[i:i + k]
        i += k
        s = 0


def env(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr:
        e[n - nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def saw(f, n, top=None, phase=0.0, tilt=6.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, int(min(top or 40, 9000 / f)) + 1):
        out += np.sin(2 * np.pi * f * k * t + phase * k) / k * np.exp(-(k - 1) / tilt)
    return out


def ensemble(f, n, voices=5, cents=10, tilt=5.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for v in range(voices):
        c = (v - (voices - 1) / 2) / max(1, (voices - 1) / 2) * cents
        vib = 1 + 0.0016 * np.sin(2 * np.pi * rng.uniform(4.5, 5.8) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * 2 ** (c / 1200) * vib) / SR + rng.uniform(0, 6)
        for k in range(1, int(min(26, 7500 / f)) + 1):
            out += np.sin(k * ph) / k * np.exp(-(k - 1) / tilt)
    return out / voices


def stereo(m, pan=0.0):
    return np.stack([m * np.cos((pan + 1) * np.pi / 4), m * np.sin((pan + 1) * np.pi / 4)], 1)


def ir(sec=3.4, damp=5200):
    n = int(sec * SR)
    d = np.exp(-6.9 * np.arange(n) / SR / sec)
    h = np.stack([lp(rng.standard_normal(n) * d, damp), lp(rng.standard_normal(n) * d, damp)], 1)
    return h / np.sqrt((h ** 2).sum() / 2)


IR = ir()


def verb_loop(x, wet):
    out = np.zeros_like(x)
    for c in range(2):
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], N) * np.fft.rfft(IR[:, c], N), N)
    out *= np.sqrt((x ** 2).mean() / max((out ** 2).mean(), 1e-12))
    return (1 - wet) * x + wet * out


def verb_one(x, wet, sec=3.0):
    h = IR[: int(sec * SR)]
    y = np.stack([signal.fftconvolve(x[:, c], h[:, c]) for c in range(2)], 1)
    y *= np.sqrt((x ** 2).mean() / max((y ** 2).mean(), 1e-12))
    xx = np.vstack([x, np.zeros((len(y) - len(x), 2))])
    return (1 - wet) * xx + wet * y


def norm(x, peak):
    return x * (peak / max(np.abs(x).max(), 1e-9))


ROOTS = ["A1", "F1", "C2", "G1"]
PADS = [["A2", "E3", "A3", "C4", "E4"], ["F2", "C3", "A3", "C4", "F4"], ["C3", "G3", "C4", "E4", "G4"], ["G2", "D3", "B3", "D4", "G4"]]


def bass_note(f, n, accent):
    """A plucky synth-bass eighth: saw + sub, filter closes fast (the 'driving' pulse)."""
    t = np.arange(n) / SR
    body = saw(f, n, top=24, tilt=4.0)
    bright = lp(body, 1400) * np.exp(-t * 26)
    dark = lp(body, 380) * np.exp(-t * 7)
    sub = np.sin(2 * np.pi * f * t) * np.exp(-t * 6)
    x = (0.55 * dark + 0.35 * bright + 0.6 * sub) * (1 - np.exp(-t * 900))
    return x * accent


def pulse(roots):
    buf = np.zeros((N, 2))
    step = BEAT / 2
    n = int(step * 0.95 * SR)
    for ci, r in enumerate(roots):
        f = hz(r)
        for s in range(int(round(CHORD / step))):
            acc = 1.0 if s % 8 == 0 else 0.82 if s % 2 == 0 else 0.62
            octv = 2.0 if s % 8 in (3, 7) else 1.0
            add_wrap(buf, stereo(bass_note(f * octv, n, acc), 0), int(round((ci * CHORD + s * step) * SR)))
    return norm(loopf(hp, buf, 32), 0.6)


def drone():
    t = np.arange(N) / SR
    m = np.zeros(N)
    for note, g in (("A1", 0.7), ("A2", 0.45), ("E3", 0.3)):
        m += loopf(lp, saw(loop_hz(hz(note)), N, top=20, tilt=5), 420) * g
    sw = 0.7 + 0.3 * np.sin(2 * np.pi * t / CHORD)
    buf = stereo(m * sw)
    for c, ph in ((0, 0.0), (1, 1.9)):
        nz = signal.sosfilt(signal.butter(2, [300, 2400], "band", fs=SR, output="sos"), rng.standard_normal(N))
        buf[:, c] += nz * 0.035 * (0.6 + 0.4 * np.sin(2 * np.pi * t / (CHORD / 2) + ph))
    return norm(verb_loop(buf, 0.3), 0.5)


def tension_hi():
    """Eerie high cluster (A4, Bb4, E5) with 16th-note tremolo: the suspense layer for the hook and builds."""
    t = np.arange(N) / SR
    m = np.zeros((N, 2))
    for note, pan in (("A4", -0.5), ("Bb4", 0.5), ("E5", 0.0)):
        x = ensemble(loop_hz(hz(note)), N, voices=4, cents=9, tilt=3.0)
        m += stereo(loopf(lp, x, 4500), pan)
    trem = 0.55 + 0.45 * (0.5 + 0.5 * np.cos(2 * np.pi * t / (BEAT / 4)))
    m *= trem[:, None]
    return norm(verb_loop(m, 0.45), 0.4)


def pads():
    buf = np.zeros((N, 2))
    for ci, chord in enumerate(PADS):
        n = int((CHORD + 2.5) * SR)
        for ni, note in enumerate(chord):
            x = lp(ensemble(hz(note), n), 1300 + 120 * ni) * env(n, 1.4, 2.4)
            add_wrap(buf, stereo(x, (ni / (len(chord) - 1) - 0.5) * 1.1) * (0.2 if ni else 0.26), int(round(ci * CHORD * SR)))
    return norm(verb_loop(buf, 0.5), 0.5)


def ticks():
    buf = np.zeros((N, 2))
    step = BEAT / 4
    n = int(0.045 * SR)
    t = np.arange(n) / SR
    sos = signal.butter(2, [5000, 11000], "band", fs=SR, output="sos")
    for s in range(int(round(CYCLE / step))):
        acc = 1.0 if s % 4 == 2 else 0.5 if s % 2 == 0 else 0.32
        x = signal.sosfilt(sos, rng.standard_normal(n)) * np.exp(-t * 140) * acc
        add_wrap(buf, stereo(x, 0.25 if s % 2 else -0.25), int(round(s * step * SR)))
    return norm(buf, 0.3)


# ---------------------------------------------------------------- one-shots
def braam():
    """Cinematic hit: detuned low saw stack with a fast opening filter, plus a sub boom and a noise crack."""
    d = 3.2
    n = int(d * SR)
    t = np.arange(n) / SR
    stack = sum(ensemble(hz(nt), n, voices=4, cents=14, tilt=8.0) * g for nt, g in (("A1", 1.0), ("E2", 0.7), ("A2", 0.6)))
    cut = 180 + 2600 * np.exp(-t * 2.2) * (1 - np.exp(-t * 60))
    out = np.zeros(n)
    blk = 1024
    zi = None
    for i in range(0, n, blk):
        sos = signal.butter(2, float(cut[i]), "low", fs=SR, output="sos")
        zi = signal.sosfilt_zi(sos) * 0 if zi is None else zi
        out[i:i + blk], zi = signal.sosfilt(sos, stack[i:i + blk], zi=zi)
    out *= np.exp(-t * 1.1) * (1 - np.exp(-t * 300))
    f = 30 + 55 * np.exp(-t * 7)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) * 1.4
    crack = lp(rng.standard_normal(n), 2500) * np.exp(-t * 22) * 0.5
    return norm(verb_one(stereo(out + boom + crack), 0.3), 0.95)


def hit_soft():
    d = 2.0
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 36 + 40 * np.exp(-t * 8)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4) + lp(rng.standard_normal(n), 1800) * np.exp(-t * 30) * 0.35
    return norm(verb_one(stereo(x), 0.3), 0.8)


def riser(d=5.7):
    """Shepard-style rising tones + a swelling noise sweep, peaking at the end."""
    n = int(d * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for o in range(4):
        f0 = 110 * 2 ** o
        f = f0 * 2 ** (1.0 * t / d)
        w = np.exp(-((np.log2(f / 440)) ** 2) / 2.0)
        out += np.sin(2 * np.pi * np.cumsum(f) / SR) * w
    nz = rng.standard_normal(n)
    sweep = np.zeros(n)
    blk = 1024
    zi = None
    for i in range(0, n, blk):
        fc = 400 + 7000 * (i / n) ** 2
        sos = signal.butter(2, [fc * 0.7, min(fc * 1.4, 20000)], "band", fs=SR, output="sos")
        zi = signal.sosfilt_zi(sos) * 0 if zi is None else zi
        sweep[i:i + blk], zi = signal.sosfilt(sos, nz[i:i + blk], zi=zi)
    x = (out * 0.5 + sweep * 0.9) * (t / d) ** 2.0
    trem = 0.75 + 0.25 * np.cos(2 * np.pi * t / (BEAT / 4))
    return norm(stereo(x * trem), 0.8)


LOOPS = {"pulse_pedal": lambda: pulse(["A1"] * 4), "pulse_prog": lambda: pulse(ROOTS), "drone": drone,
         "tension_hi": tension_hi, "pads": pads, "ticks": ticks}
SHOTS = {"braam": braam, "hit_soft": hit_soft, "riser_hook": lambda: riser(5.7), "riser_3s": lambda: riser(3.0)}

if __name__ == "__main__":
    for name, fn in LOOPS.items():
        loop = fn().astype(np.float32)
        sf.write(f"{OUT}/loop_{name}.wav", loop, SR, subtype="FLOAT")
        sf.write(f"{OUT}/stem_{name}.wav", np.tile(loop, (REPEAT, 1)), SR, subtype="FLOAT")
        print(name, "ok")
    os.makedirs(f"{OUT}/sfx", exist_ok=True)
    for name, fn in SHOTS.items():
        sf.write(f"{OUT}/sfx/{name}.wav", fn().astype(np.float32), SR, subtype="FLOAT")
        print(name, "ok")
