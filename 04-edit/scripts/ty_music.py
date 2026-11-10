"""Original music bed for Ricky's thank-you video, built to the recipe of AB Nasdaq's thank-you bed
(see THANK-YOU-BREAKDOWN.md, section 7): G minor, 130 BPM, an upright-piano arpeggio of fifths and octaves in
dotted quarters over a soft pad, a high bell layer from ~0:14, a denser middle, a held high note leading into the
script's pivot, and an 808 on G1 on every downbeat from the pivot ("however, on the flip side") to the end.

Piano: VSCO 2 CE Upright Piano (CC0). Pad, held note and 808 are synthesised. Nothing copyrighted.

    python ty_music.py plan.json out.wav
"""
import json, sys
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
BPM = 130
BEAT = 60 / BPM
BAR = 4 * BEAT
STEP = 1.5 * BEAT                                  # dotted quarter: the arpeggio's pulse (0.69 s)
PIANO = "/home/user/sgossner/vsco-2-ce/Keys/Upright Piano"

# one chord per arpeggio cycle (6 notes = 9 beats, so the harmony drifts across the bar line like AB's)
CHORDS = [
    {"arp": [43, 50, 55, 62, 67, 74], "pad": [55, 58, 62], "bell": [79, 86]},       # Gm
    {"arp": [43, 50, 55, 62, 70, 74], "pad": [55, 58, 62, 65], "bell": [82]},       # Gm7
    {"arp": [39, 46, 51, 58, 63, 67], "pad": [51, 55, 58, 62], "bell": [79, 82]},   # Ebmaj7
    {"arp": [38, 45, 50, 57, 62, 66], "pad": [50, 54, 57], "bell": [81]},           # D
]

_samples = {}


def piano(midi, dyn):
    """Nearest VSCO sample (every 4 semitones) repitched by resampling; leading silence trimmed."""
    idx = int(round((midi - 21) / 4)) * 2
    idx = min(max(idx, 0), 44)
    key = (idx, dyn)
    if key not in _samples:
        y, sr = sf.read(f"{PIANO}/Player_dyn{dyn}_rr1_{idx:03d}.wav", dtype="float32")
        y = y if y.ndim == 2 else np.stack([y, y], 1)
        on = np.argmax(np.abs(y).max(1) > np.abs(y).max() * 0.02)
        y = y[max(0, on - 40):]
        y = signal.resample_poly(y, SR, sr, axis=0) if sr != SR else y
        _samples[key] = (y / (np.abs(y).max() + 1e-9)).astype(np.float32)
    y = _samples[key]
    ratio = 2 ** ((midi - (21 + 2 * idx)) / 12)
    if abs(ratio - 1) > 1e-4:                              # pitch shift by resampling (+-2 semitones)
        n = int(len(y) / ratio)
        x = np.linspace(0, len(y) - 1, n)
        y = np.stack([np.interp(x, np.arange(len(y)), y[:, c]) for c in range(2)], 1).astype(np.float32)
    return y


def place(buf, x, t, gain=1.0, pan=0.0, length=None):
    s = int(round(t * SR))
    if s >= len(buf) or s + len(x) <= 0:
        return
    if length is not None:                                 # damp the note after `length` seconds
        n = int(length * SR)
        if n < len(x):
            x = x[: n + int(0.35 * SR)].copy()
            x[n:] *= np.linspace(1, 0, len(x) - n)[:, None] ** 2
    if s < 0:
        x, s = x[-s:], 0
    n = min(len(x), len(buf) - s)
    g = np.array([np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)]) * np.sqrt(2) * gain
    buf[s:s + n] += x[:n] * g


def reverb_ir(rt=2.4, pre=0.02, seed=0):
    rng = np.random.default_rng(seed)
    n = int(rt * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * t / rt)[:, None]
    ir = signal.sosfilt(signal.butter(2, 6000, "low", fs=SR, output="sos"), ir, axis=0)
    ir = np.concatenate([np.zeros((int(pre * SR), 2)), ir])
    return ir / np.sqrt((ir ** 2).sum(0).mean())


def verb(x, wet, rt=2.4):
    ir = reverb_ir(rt)
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet * 0.5) + y * wet


def saw_pad(freqs, dur, sr=SR, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * sr)) / sr
    out = np.zeros((len(t), 2))
    for f in freqs:
        for c, det in enumerate((-0.006, 0.006)):
            for d2 in (0.0, 0.0035):
                ph = rng.random()
                x = 2 * ((t * f * (1 + det + d2) + ph) % 1) - 1
                out[:, c] += x
    sos = signal.butter(2, 900, "low", fs=sr, output="sos")
    out = signal.sosfilt(sos, signal.sosfilt(sos, out, axis=0), axis=0)
    return out / (len(freqs) * 4)


def m2f(m):
    return 440 * 2 ** ((m - 69) / 12)


def main():
    plan = json.load(open(sys.argv[1]))
    out_path = sys.argv[2]
    dur = plan["dur"]
    pivot = plan["music"]["pivot"]
    calm = plan["music"].get("dense", pivot - 50)
    total = dur + 3.0
    n = int(total * SR)
    g0 = pivot - np.ceil(pivot / BAR) * BAR                 # grid origin: a downbeat lands exactly on the pivot
    pno, pad, bell, held, bass = (np.zeros((n, 2)) for _ in range(5))
    rng = np.random.default_rng(7)

    # piano arpeggio + bells + the denser middle line
    k = 0
    t = g0
    while t < total:
        cyc = k // 6
        ch = CHORDS[cyc % len(CHORDS)]
        note = ch["arp"][k % 6]
        tt = t + rng.normal(0, 0.006)
        if tt > -0.5:
            v = 0.95 if k % 6 == 0 else 0.7 + 0.1 * rng.random()
            place(pno, piano(note, 2), tt, v * (0.9 if note > 70 else 1.0), pan=-0.35 if k % 2 else 0.35, length=2.8)
        if k % 6 == 0 and t > 13.5:                         # high bell layer from ~0:14
            for j, b in enumerate(ch["bell"]):
                place(bell, piano(b, 1), t + 0.02 + j * STEP * 2, 0.55, pan=0.5 - j, length=3.0)
        if calm < t < pivot - 0.2 and k % 2 == 1:           # denser middle: answering notes up high
            m = ch["arp"][(k + 3) % 6] + 12
            m = m if m < 84 else m - 12
            place(pno, piano(m, 1), t + BEAT * 0.75, 0.55, pan=0.6 if k % 4 == 1 else -0.6, length=1.6)
        k += 1
        t = g0 + k * STEP

    # pad: one chord per arpeggio cycle, slow swell, crossfaded
    cyc_len = 6 * STEP
    c = 0
    t = g0
    while t < total:
        ch = CHORDS[c % len(CHORDS)]
        seg = saw_pad([m2f(m) for m in ch["pad"]], cyc_len + 1.2, seed=c)
        L = len(seg)
        env = np.minimum(1, np.arange(L) / (1.0 * SR)) * np.minimum(1, (L - np.arange(L)) / (1.2 * SR))
        place(pad, seg * env[:, None], t, 1.0)
        c += 1
        t = g0 + c * cyc_len

    # held high note (D6) building into the pivot, released on it
    a, b = pivot - 9.0, pivot + 0.15
    tt = np.arange(int((b - a) * SR)) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * tt) * np.minimum(1, tt / 2)
    ph = 2 * np.pi * np.cumsum(m2f(86) * vib) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    env = (np.minimum(1, tt / 3.0) * (0.55 + 0.45 * tt / tt[-1])) * np.minimum(1, (tt[-1] - tt) / 0.12)
    place(held, np.stack([tone * env, tone * env], 1) * 0.5, a)

    # 808 on G1, every downbeat from the pivot
    t808 = np.arange(int(1.35 * SR)) / SR
    f = m2f(31) * (1 + 1.2 * np.exp(-t808 / 0.03))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t808 / 0.75) * np.minimum(1, t808 / 0.002)
    body = np.tanh(body * 2.2) / np.tanh(2.2)
    click = np.random.default_rng(1).standard_normal(len(t808)) * np.exp(-t808 / 0.004) * 0.15
    click = signal.sosfilt(signal.butter(2, [1500, 6000], "band", fs=SR, output="sos"), click)
    k808 = (body + click)[:, None].repeat(2, 1)
    t = pivot
    while t < dur + 1.0:
        place(bass, k808, t, 1.0)
        t += BAR

    # bus: reverb on piano/bells/pad, then balance
    pno = pno + 0.4 * signal.sosfilt(signal.butter(1, 3000, "high", fs=SR, output="sos"), pno, axis=0)   # a touch brighter
    pno = verb(pno, 0.32)
    bell = verb(bell, 0.55, rt=3.2)
    pad = verb(pad, 0.4, rt=3.0)
    held = verb(held, 0.5, rt=3.0)
    lvl = lambda x: np.sqrt((x ** 2).mean()) + 1e-12
    pr = lvl(pno[: int(pivot * SR)])
    mix = pno + pad * (pr / lvl(pad) * 10 ** (-9 / 20)) + bell * (pr / (lvl(bell[int(14 * SR):int(pivot * SR)]) + 1e-12) * 10 ** (-12 / 20))
    mix += held * (pr / lvl(held[int((pivot - 4) * SR):int(pivot * SR)]) * 10 ** (-13 / 20))
    pre = lvl(mix[: int(pivot * SR)])
    mix += bass * (pre / lvl(bass[int(pivot * SR):int((pivot + 8) * SR)]) * 10 ** (-5 / 20))   # a soft groove note, not a boom
    mix = mix[: int(dur * SR)]
    fo = int(0.5 * SR)                                      # 0.5 s fade at the very end, like AB
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    mix /= np.abs(mix).max() / 0.9
    sf.write(out_path, mix.astype(np.float32), SR, subtype="FLOAT")
    print(f"music {dur:.1f}s, grid origin {g0:.3f}s, 808 from {pivot:.2f}s, denser from {calm:.1f}s")


if __name__ == "__main__":
    main()
