"""Original score for Ricky's VSL, rendered from scratch (no samples, nothing to license).

A minor, 80 BPM. One 24 s cycle (Am(add9) -> Fmaj7 -> Dm9 -> Esus4/E, 6 s each) per stem, rendered as a seamless
loop and tiled to full length. Stems are mixed per section later, so the score can build and drop with the edit.
"""
import sys, os
import numpy as np
from scipy import signal
import soundfile as sf

SR = 48000
BPM = 80
BEAT = 60 / BPM            # 0.75 s
BAR = 4 * BEAT             # 3 s
CHORD_LEN = 2 * BAR        # 6 s
CYCLE = 4 * CHORD_LEN      # 24 s
N = int(CYCLE * SR)
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/music"
CYCLES = int(sys.argv[2]) if len(sys.argv) > 2 else 19   # 19 x 24 s = 7:36
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def hz(note):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    n, o = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)


CHORDS = [  # pad voicings
    ["A3", "C4", "E4", "B4"],
    ["F3", "A3", "C4", "E4"],
    ["D3", "F3", "A3", "E4"],
    ["E3", "A3", "B3", "E4"],   # sus4, resolves to G# halfway
]
ARP = [["A3", "E4", "B4", "C5"], ["F3", "C4", "E4", "A4"], ["D3", "A3", "E4", "F4"], ["E3", "B3", "E4", "G#4"]]
MOTIF = [  # (beat offset inside the chord, note): sparse music-box line
    [(0, "E5"), (3, "C5"), (6, "B4")],
    [(0, "A4"), (3.5, "C5"), (6, "E5")],
    [(0, "F5"), (3, "E5"), (6.5, "D5")],
    [(0, "B4"), (4, "G#4")],
]


def add_wrapped(buf, x, start):
    """Add x into a loop buffer starting at sample `start`, wrapping past the end (seamless loops)."""
    s = start % len(buf)
    i = 0
    while i < len(x):
        n = min(len(x) - i, len(buf) - s)
        buf[s:s + n] += x[i:i + n]
        i += n
        s = 0


def env_adsr(n, a, r, sr=SR):
    e = np.ones(n)
    na, nr = int(a * sr), int(r * sr)
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[n - nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def saw(f, n, phase=0.0, max_h=None, bright=1.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    top = int(min(max_h or 40, 9000 / f))
    for k in range(1, top + 1):
        out += np.sin(2 * np.pi * f * k * t + phase * k) / k * np.exp(-(k - 1) / (6 * bright))
    return out


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low")
    return signal.filtfilt(b, a, x, axis=0)


def loop_filter(fn, x, *a):
    """Filter a looping signal without a seam: filter three copies and keep the middle one."""
    n = len(x)
    return fn(np.concatenate([x, x, x]), *a)[n:2 * n]


def loop_hz(f):
    """Nudge a frequency so it completes a whole number of cycles per loop (no click at the seam)."""
    return round(f * CYCLE) / CYCLE


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.filtfilt(b, a, x, axis=0)


def ir(seconds=3.2, damp=5500, predelay=0.02):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    decay = np.exp(-6.9 * t / seconds)
    l = rng.standard_normal(n) * decay
    r = rng.standard_normal(n) * decay
    l, r = lowpass(l, damp), lowpass(r, damp)
    pad = np.zeros(int(predelay * SR))
    h = np.stack([np.concatenate([pad, l]), np.concatenate([pad, r])], 1)
    return h / np.sqrt((h ** 2).sum() / 2)


IR = ir()


def reverb_loop(x, wet=0.35):
    """Circular convolution so the reverb tail wraps around the loop."""
    out = np.zeros_like(x)
    for c in range(2):
        X = np.fft.rfft(x[:, c], N)
        H = np.fft.rfft(IR[:, c], N) if len(IR) <= N else None
        out[:, c] = np.fft.irfft(X * H, N)
    out *= np.sqrt((x ** 2).mean() / max((out ** 2).mean(), 1e-12))
    return (1 - wet) * x + wet * out


def delay_loop(x, sec, fb=0.35, mix=0.3, pingpong=True):
    d = int(sec * SR)
    y = x.copy()
    tap = x.copy()
    for i in range(1, 6):
        tap = np.roll(tap, d, axis=0) * fb
        if pingpong:
            tap = tap[:, ::-1]
        y += mix * tap
    return y


def stereo(mono, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([mono * l, mono * r], 1)


def norm(x, peak=0.5):
    return x * (peak / max(np.abs(x).max(), 1e-9))


# ---------------------------------------------------------------- stems
def stem_drone():
    t = np.arange(N) / SR
    buf = np.zeros((N, 2))
    sub = np.sin(2 * np.pi * loop_hz(hz("A1")) * t) * (0.8 + 0.2 * np.sin(2 * np.pi * t / CYCLE))
    body = loop_filter(lowpass, saw(loop_hz(hz("A2")), N, max_h=20), 260) * 0.5
    fifth = loop_filter(lowpass, saw(loop_hz(hz("E2")), N, max_h=12), 220) * 0.18
    mono = sub + body + fifth
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / (CYCLE / 2))
    buf += stereo(mono * swell)
    # air: band-limited noise that slowly breathes, wide
    for c, ph in ((0, 0), (1, 1.7)):
        nz = signal.lfilter(*signal.butter(2, [400 / (SR / 2), 3200 / (SR / 2)], "band"), rng.standard_normal(N))
        buf[:, c] += nz * 0.05 * (0.6 + 0.4 * np.sin(2 * np.pi * t / (CYCLE / 3) + ph))
    return norm(reverb_loop(buf, 0.25), 0.5)


def stem_pads():
    buf = np.zeros((N, 2))
    for ci, chord in enumerate(CHORDS):
        start = int(ci * CHORD_LEN * SR)
        n = int((CHORD_LEN + 2.5) * SR)
        for ni, note in enumerate(chord):
            f = hz(note)
            if ci == 3 and note == "A3":       # sus4 -> major third halfway through
                for part, (nn, off, dur) in enumerate((("A3", 0, CHORD_LEN / 2 + 1.0), ("G#3", CHORD_LEN / 2, CHORD_LEN / 2 + 2.5))):
                    m = int(dur * SR)
                    v = sum(saw(hz(nn) * 2 ** (d / 1200), m, phase=rng.uniform(0, 6)) for d in (-7, 0, 7)) / 3
                    v = lowpass(v, 1400) * env_adsr(m, 1.2, 1.4)
                    add_wrapped(buf, stereo(v, -0.3 + 0.2 * ni) * 0.22, start + int(off * SR))
                continue
            for d, pan in ((-8, -0.6), (0, 0.0), (8, 0.6)):
                v = saw(f * 2 ** (d / 1200), n, phase=rng.uniform(0, 6))
                v = lowpass(v, 1300 + 250 * ni) * env_adsr(n, 1.6, 2.4)
                add_wrapped(buf, stereo(v, pan) * 0.22 / 3, start)
    return norm(reverb_loop(buf, 0.45), 0.5)


def pluck(f, dur=2.8, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)          # slight inharmonicity, like a piano or music box
        out += np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.6 + 1.3 * k / bright)) / k ** 1.2
    out *= 1 - np.exp(-t * 400)
    return out


def stem_motif():
    buf = np.zeros((N, 2))
    for ci, notes in enumerate(MOTIF):
        for beat, note in notes:
            x = pluck(hz(note), 3.2) * 0.35
            add_wrapped(buf, stereo(x, rng.uniform(-0.35, 0.35)), int((ci * CHORD_LEN + beat * BEAT) * SR))
    buf = delay_loop(buf, BEAT * 1.5, fb=0.4, mix=0.45)
    return norm(reverb_loop(buf, 0.5), 0.45)


def stem_arp():
    buf = np.zeros((N, 2))
    step = BEAT / 2
    for ci, notes in enumerate(ARP):
        for s in range(int(CHORD_LEN / step)):
            note = notes[s % len(notes)] if (s // 4) % 2 == 0 else notes[::-1][s % len(notes)]
            x = pluck(hz(note) * 2, 0.9, bright=0.7) * (0.5 if s % 2 else 0.7)
            add_wrapped(buf, stereo(x, 0.5 if s % 2 else -0.5), int((ci * CHORD_LEN + s * step) * SR))
    buf = loop_filter(lowpass, buf, 3500)
    buf = delay_loop(buf, BEAT * 0.75, fb=0.3, mix=0.25)
    return norm(reverb_loop(buf, 0.35), 0.4)


def thump(dur=0.45, f0=70, f1=42, click=0.15):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7)
    x[:200] += rng.standard_normal(200) * click * np.linspace(1, 0, 200)
    return x


def stem_heartbeat():
    buf = np.zeros((N, 2))
    for b in range(int(CYCLE / BAR) * 2):          # a heartbeat every half bar (≈ 80 bpm feel)
        t0 = b * BAR / 2
        add_wrapped(buf, stereo(thump(), 0) * 0.9, int(t0 * SR))
        add_wrapped(buf, stereo(thump(f0=60, f1=40), 0) * 0.55, int((t0 + 0.22) * SR))
    return norm(loop_filter(lowpass, buf, 900), 0.6)


def tick(f=3200, dur=0.03):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = signal.lfilter(*signal.butter(2, [f * 0.6 / (SR / 2), min(f * 1.6, 20000) / (SR / 2)], "band"), rng.standard_normal(n))
    return nz * np.exp(-t * 180)


def stem_ticks():
    buf = np.zeros((N, 2))
    for b in range(int(CYCLE / BEAT)):
        add_wrapped(buf, stereo(tick(3600 if b % 2 == 0 else 2700), 0.15 if b % 2 else -0.15) * (0.8 if b % 2 == 0 else 0.6), int(b * BEAT * SR))
    return norm(reverb_loop(buf, 0.2), 0.35)


def stem_hats():
    buf = np.zeros((N, 2))
    for s in range(int(CYCLE / (BEAT / 4))):
        acc = 1.0 if s % 4 == 2 else 0.45
        x = highpass(tick(9000, 0.05), 6000) * acc
        add_wrapped(buf, stereo(x, 0.3), int(s * BEAT / 4 * SR))
    return norm(buf, 0.25)


STEMS = {"drone": stem_drone, "pads": stem_pads, "motif": stem_motif, "arp": stem_arp,
         "heartbeat": stem_heartbeat, "ticks": stem_ticks, "hats": stem_hats}

if __name__ == "__main__":
    for name, fn in STEMS.items():
        loop = fn().astype(np.float32)
        sf.write(f"{OUT}/loop_{name}.wav", loop, SR, subtype="FLOAT")
        sf.write(f"{OUT}/stem_{name}.wav", np.tile(loop, (CYCLES, 1)), SR, subtype="FLOAT")
        print(name, "ok", f"{np.abs(loop).max():.2f}")
