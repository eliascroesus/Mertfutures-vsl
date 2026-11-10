"""Orchestral tension cue for Ricky's VSL, played with real string and timpani recordings (VSCO 2 CE, CC0).

A minor, 115 BPM (the tempo of the pulse in Iman Gadzhi's bed). Cellos + bass drive an eighth-note ostinato, violas
tick in sixteenths, violins hold long swelling notes and shimmer in tremolo for the hook; timpani rolls build into
hits of timpani + bass drum + a low-string stab. Sections follow the edit (cue times in raw-video seconds, mapped
through the cut list).

    python strings_score.py edl3.json out.wav
"""
import json, sys
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
BPM = 115.0
BEAT = 60 / BPM
E8, E16, BAR = BEAT / 2, BEAT / 4, 4 * BEAT
VS = "/home/user/sgossner/vsco-2-ce/Percussion"
IDX = json.load(open("/home/user/work/vsco_index.json"))
rng = np.random.default_rng(7)
_cache = {}


def load(path):
    if path not in _cache:
        x, sr = sf.read(path, dtype="float32", always_2d=True)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, 1)
        if sr != SR:
            n = int(round(len(x) * SR / sr))
            x = np.stack([np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x[:, c]) for c in range(2)], 1).astype(np.float32)
        _cache[path] = x
    return _cache[path]


def repitch(x, semis):
    if abs(semis) < 1e-3:
        return x
    r = 2 ** (semis / 12)
    n = int(len(x) / r)
    pos = np.arange(n) * r
    return np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1).astype(np.float32)


_rr = {}


def pick(art, midi, vel):
    rows = IDX[art]
    best = min(abs(r["midi"] - midi) for r in rows)
    cands = [r for r in rows if abs(r["midi"] - midi) == best]
    dyns = sorted(set(r["dyn"] for r in cands))
    dyn = dyns[0] if vel < 0.55 or len(dyns) == 1 else dyns[-1]
    cands = [r for r in cands if r["dyn"] == dyn]
    k = (art, midi)
    _rr[k] = _rr.get(k, -1) + 1
    return cands[_rr[k] % len(cands)]


_pcache = {}


def note(buf, art, midi, t, dur=None, vel=0.7, attack=0.0, release=0.35, swell=None, gain=1.0):
    """Place one sampled note. dur=None plays the whole (short) sample. swell=(v0, v1) ramps loudness across the note."""
    r = pick(art, midi, vel)
    key = (r["file"], midi)
    if key not in _pcache:
        _pcache[key] = repitch(load(r["file"]), midi - r["midi"])
    x = _pcache[key]
    if dur is not None:
        n = min(len(x), int((dur + release) * SR))
        x = x[:n].copy()
        if release:
            nr = min(n, int(release * SR))
            x[n - nr:] *= np.linspace(1, 0, nr)[:, None] ** 1.5
    else:
        x = x.copy()
    if attack:
        na = min(len(x), int(attack * SR))
        x[:na] *= np.linspace(0, 1, na)[:, None] ** 2
    g = vel * gain
    if swell:
        e = np.linspace(swell[0], swell[1], len(x)) ** 1.6
        x *= e[:, None]
    s = int(round((t + rng.normal(0, 0.004)) * SR))
    if s < 0:
        x, s = x[-s:], 0
    e2 = min(len(buf), s + len(x))
    if e2 > s:
        buf[s:e2] += x[:e2 - s] * g * rng.uniform(0.93, 1.05)


def perc(buf, path, t, gain=1.0, semis=0.0, fade_in=0.0, length=None):
    x = repitch(load(path), semis).copy()
    if length:
        x = x[:int(length * SR)]
        nr = min(len(x), int(0.25 * SR))
        x[-nr:] *= np.linspace(1, 0, nr)[:, None]
    if fade_in:
        e = np.linspace(0, 1, len(x)) ** 3 if fade_in == "cresc" else np.ones(len(x))
        x *= e[:, None]
    s = int(round(t * SR))
    if s < 0:
        x, s = x[-s:], 0
    e2 = min(len(buf), s + len(x))
    if e2 > s:
        buf[s:e2] += x[:e2 - s] * gain


A = {"A": 45, "F": 41, "C": 48, "G": 43}           # chord roots (cello register, A2 = 45)
CHORDS = ["A", "F", "C", "G"]
MELODY_TENSION = [69, 72, 71, 68]                     # A4 C5 B4 G#4 (harmonic minor pull)
MELODY_LIFT = {"A": 76, "F": 77, "C": 76, "G": 74}    # E5 F5 E5 D5 over Am F C G
MELODY_HIGH = {"A": 81, "F": 81, "C": 79, "G": 79}    # A5 A5 G5 G5 for the proof section
VIOLA_TICK = {"A": (64, 69), "F": (65, 69), "C": (64, 67), "G": (62, 67)}


def grid(t0, t1, step):
    k = int(np.ceil(t0 / step - 1e-6))
    out = []
    while k * step < t1 - 1e-6:
        out.append(k * step)
        k += 1
    return out


def chord_at(t, t_start, bars_per_chord=2):
    i = int((t - t_start + 1e-6) // (bars_per_chord * BAR))
    return CHORDS[i % 4]


def ostinato(buf, t0, t1, root_fn, vel=0.75, bass=True):
    for t in grid(t0, t1, E8):
        i = int(round(t / E8)) % 8
        r = root_fn(t)
        m = r + (12 if i == 7 else 7 if i == 6 and (int(t / BAR) % 2) else 0)
        acc = vel * (1.0 if i in (0, 4) else 0.78)
        note(buf, "vc_spic", m, t, vel=acc, gain=0.9)
        if bass and i % 2 == 0:
            note(buf, "cb_spic", r - 12, t, vel=acc * 0.95, gain=1.0)


def ticks(buf, t0, t1, notes_fn, vel=0.45):
    for t in grid(t0, t1, E16):
        i = int(round(t / E16)) % 4
        a, b = notes_fn(t)
        note(buf, "vla_spic", a if i % 2 == 0 else b, t, vel=vel * (1.0 if i == 0 else 0.7), gain=0.55)


def long_notes(buf, art, t0, t1, seq, bars_each=2, vel=(0.35, 0.8), gain=0.8, octave_double=False):
    starts = grid(t0, t1, bars_each * BAR)
    if not starts or starts[0] > t0 + 0.05:
        starts = [t0] + starts
    for j, s in enumerate(starts):
        e = min(t1, s + bars_each * BAR) if j + 1 >= len(starts) else starts[j + 1]
        m = seq(s, j)
        note(buf, art, m, s, dur=e - s, vel=vel[1], attack=0.25, release=0.6, swell=vel, gain=gain)
        if octave_double:
            note(buf, art, m - 12, s, dur=e - s, vel=vel[1], attack=0.3, release=0.6, swell=vel, gain=gain * 0.6)


TIMP_HIT = [f"{VS}/Timpani/Timpani4_Hit_v4_rr1_Sum.wav", f"{VS}/Timpani/Timpani4_Hit_v4_rr2_Sum.wav"]
TIMP_ROLL = f"{VS}/Timpani/Rolls/Timpani4_Roll_v5_rr1_Sum.wav"
BDRUM = [f"{VS}/BDrumNewhit_v7_rr1_Sum.wav", f"{VS}/BDrumNewhit_v7_rr2_Sum.wav", f"{VS}/BDrumNewhit_v5_rr1_Sum.wav"]
_h = [0]


def hit(buf, t, big=1.0):
    _h[0] += 1
    perc(buf, TIMP_HIT[_h[0] % 2], t, gain=2.2 * big)
    perc(buf, BDRUM[_h[0] % 3 if big >= 1 else 2], t, gain=2.6 * big)
    note(buf, "cb_sus", 33, t, dur=1.6, vel=0.95, release=1.2, gain=1.3 * big)       # A1 stab
    note(buf, "vc_sus", 45, t, dur=1.6, vel=0.95, release=1.2, gain=1.0 * big)       # A2


def roll(buf, t_end, length=3.0, gain=1.6):
    perc(buf, TIMP_ROLL, t_end - length, gain=gain, fade_in="cresc", length=length + 0.02)


def build(edl):
    keep = edl["keep"]

    def m(x):
        out = 0.0
        for a, b in keep:
            if x <= a:
                return out
            if x < b:
                return out + x - a
            out += b - a
        return out

    total = m(385.3)
    buf = np.zeros((int((total + 8) * SR), 2), np.float32)
    S = lambda a, b: (m(a), m(b))
    pedal = lambda t: A["A"]

    # 0 - 5.74 hook: shimmering violin tremolo (A5 + E5) swelling, violas ticking softly, no bass; roll into the hit
    t0, t1 = S(0.0, 5.74)
    for mm, g in ((81, 0.55), (76, 0.5)):
        note(buf, "vln_trem", mm, t0, dur=t1 - t0, vel=0.9, attack=0.05, release=0.08, swell=(0.35, 1.0), gain=g)
    ticks(buf, t0 + 0.0, t1, lambda t: (64, 69), vel=0.38)
    roll(buf, t1, 3.2, 1.5)
    hit(buf, t1, 1.0)
    # 5.76 - 14.28 drive under "I owed money to my mom...": the ostinato kicks in on the hit
    t0, t1 = S(5.76, 14.28)
    ostinato(buf, t0, t1, pedal, vel=0.85)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_TENSION[j % 4], vel=(0.3, 0.75), gain=0.7)
    ticks(buf, m(8.3), t1, lambda t: (64, 69), vel=0.32)
    roll(buf, t1, 2.2, 0.9)
    hit(buf, t1, 0.55)
    # 14.28 - 47.4 lift: Am F C G, pulse follows the chords
    t0, t1 = S(14.28, 47.40)
    cs = t0
    ostinato(buf, t0, t1, lambda t: A[chord_at(t, cs)], vel=0.75)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_LIFT[CHORDS[j % 4]], vel=(0.4, 0.75), gain=0.65)
    long_notes(buf, "vla_sus", t0, t1, lambda s, j: MELODY_LIFT[CHORDS[j % 4]] - 7 if CHORDS[j % 4] != "F" else 69, vel=(0.35, 0.6), gain=0.45)
    ticks(buf, m(20.0), t1, lambda t: VIOLA_TICK[chord_at(t, cs)], vel=0.28)
    # 47.4 - 67.76 pain: pedal A, harmonic-minor melody, roll into $0
    t0, t1 = S(47.40, 67.76)
    ostinato(buf, t0, t1, pedal, vel=0.8)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_TENSION[j % 4], vel=(0.35, 0.85), gain=0.7)
    ticks(buf, t0, t1, lambda t: (64, 69), vel=0.35)
    note(buf, "vln_trem", 81, m(58.0), dur=t1 - m(58.0), vel=0.8, attack=0.5, swell=(0.2, 0.9), gain=0.4)
    roll(buf, t1, 3.0, 1.5)
    hit(buf, t1, 0.95)
    # 67.8 - 81.6 softer lift
    t0, t1 = S(67.80, 81.60)
    cs = t0
    ostinato(buf, t0, t1, lambda t: A[chord_at(t, cs)], vel=0.6, bass=False)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_LIFT[CHORDS[j % 4]], vel=(0.3, 0.6), gain=0.6)
    long_notes(buf, "vc_sus", t0, t1, lambda s, j: A[CHORDS[j % 4]] - 12 + 12, vel=(0.3, 0.55), gain=0.5)
    # 81.6 - 102.6 the platform / open loop: tension builds, small hit on the title, roll into the story
    t0, t1 = S(81.60, 102.60)
    ostinato(buf, t0, t1, pedal, vel=0.78)
    ticks(buf, t0, t1, lambda t: (64, 69), vel=0.36)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_TENSION[j % 4], vel=(0.35, 0.8), gain=0.65)
    note(buf, "vln_trem", 81, m(86.0), dur=t1 - m(86.0), vel=0.8, attack=0.8, swell=(0.2, 0.9), gain=0.38)
    roll(buf, m(95.30), 2.0, 0.9)
    hit(buf, m(95.30), 0.5)
    roll(buf, t1, 3.0, 1.2)
    hit(buf, t1, 0.6)
    # 102.6 - 186.6 story: emotional, softer pulse, cellos and violins sing
    t0, t1 = S(102.60, 186.60)
    cs = t0
    ostinato(buf, t0, t1, lambda t: A[chord_at(t, cs, 4)], vel=0.5, bass=False)
    long_notes(buf, "vc_sus", t0, t1, lambda s, j: A[CHORDS[j % 4]], bars_each=4, vel=(0.3, 0.6), gain=0.55)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: [72, 71, 69, 67][j % 4], bars_each=4, vel=(0.3, 0.65), gain=0.6)
    long_notes(buf, "vla_sus", t0, t1, lambda s, j: [64, 65, 64, 62][j % 4], bars_each=4, vel=(0.25, 0.5), gain=0.4)
    hit(buf, m(126.88), 0.6)
    hit(buf, m(164.12), 0.4)
    hit(buf, m(166.48), 0.75)
    # 186.4 - 201.62 build into the reveal: pedal, ticks, tremolo, long roll; then half a second of silence
    t0, t1 = S(186.40, 201.62)
    ostinato(buf, t0, t1, pedal, vel=0.85)
    ticks(buf, t0, t1, lambda t: (64, 69), vel=0.42)
    note(buf, "vln_trem", 81, t0, dur=t1 - t0, vel=0.9, attack=1.0, release=0.05, swell=(0.25, 1.0), gain=0.5)
    note(buf, "vln_trem", 76, t0, dur=t1 - t0, vel=0.9, attack=1.0, release=0.05, swell=(0.25, 1.0), gain=0.45)
    roll(buf, t1, 4.0, 1.8)
    hit(buf, m(202.12), 1.15)
    # 203.3 - 277.25 proof: full drive, violins high
    t0, t1 = S(203.30, 277.25)
    cs = t0
    ostinato(buf, t0, t1, lambda t: A[chord_at(t, cs)], vel=0.85)
    ticks(buf, t0, t1, lambda t: VIOLA_TICK[chord_at(t, cs)], vel=0.36)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_HIGH[CHORDS[j % 4]], vel=(0.45, 0.8), gain=0.62, octave_double=True)
    long_notes(buf, "vla_sus", t0, t1, lambda s, j: VIOLA_TICK[CHORDS[j % 4]][1], vel=(0.35, 0.6), gain=0.4)
    for tb in grid(t0, t1, 4 * BAR):
        perc(buf, TIMP_HIT[int(tb) % 2], tb, gain=0.9)
    # 277.3 - 294.08 "what most people don't understand": strip back to tremolo + ticks, roll into 01
    t0, t1 = S(277.30, 294.08)
    hit(buf, t0, 0.5)
    ticks(buf, t0, t1, lambda t: (64, 69), vel=0.38)
    note(buf, "vln_trem", 81, t0, dur=t1 - t0, vel=0.8, attack=0.4, release=0.05, swell=(0.3, 0.9), gain=0.45)
    note(buf, "cb_sus", 33, t0, dur=t1 - t0, vel=0.6, attack=1.0, release=0.1, swell=(0.3, 0.7), gain=0.6)
    roll(buf, t1, 3.0, 1.3)
    hit(buf, t1, 0.65)
    # 294.1 - 372.3 offer: steady lift, hits on the cards
    t0, t1 = S(294.10, 372.30)
    cs = t0
    ostinato(buf, t0, t1, lambda t: A[chord_at(t, cs)], vel=0.7)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_LIFT[CHORDS[j % 4]], vel=(0.4, 0.7), gain=0.6)
    long_notes(buf, "vla_sus", t0, t1, lambda s, j: VIOLA_TICK[CHORDS[j % 4]][0], vel=(0.3, 0.55), gain=0.4)
    ticks(buf, m(300.0), m(356.0), lambda t: VIOLA_TICK[chord_at(t, cs)], vel=0.25)
    for x in (299.92, 307.30):
        hit(buf, m(x), 0.45)
    hit(buf, m(318.62), 0.7)
    hit(buf, m(360.32), 0.6)
    # 372.3 - end: call to action, ring out on an open A-E chord after the last word
    t0, t1 = S(372.30, 383.60)
    cs = t0
    ostinato(buf, t0, t1, lambda t: A[chord_at(t, cs)], vel=0.6, bass=False)
    long_notes(buf, "vln_sus", t0, t1, lambda s, j: MELODY_LIFT[CHORDS[j % 4]], vel=(0.4, 0.65), gain=0.55)
    te = m(383.60)
    for art, mm, g in (("cb_sus", 33, 0.8), ("vc_sus", 45, 0.7), ("vla_sus", 64, 0.5), ("vln_sus", 69, 0.55), ("vln_sus", 76, 0.45)):
        note(buf, art, mm, te, dur=4.0, vel=0.6, attack=0.3, release=2.5, swell=(0.8, 0.4), gain=g)

    # hall reverb + gentle glue
    n = int(2.6 * SR)
    d = np.exp(-6.9 * np.arange(n) / SR / 2.6)
    sos = signal.butter(2, 5500, "low", fs=SR, output="sos")
    ir = np.stack([signal.sosfilt(sos, rng.standard_normal(n) * d), signal.sosfilt(sos, rng.standard_normal(n) * d)], 1)
    ir[: int(0.018 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum() / 2)
    wet = np.stack([signal.fftconvolve(buf[:, c], ir[:, c])[: len(buf)] for c in range(2)], 1)
    wet *= np.sqrt((buf ** 2).mean() / max((wet ** 2).mean(), 1e-12))
    mix = 0.78 * buf + 0.32 * wet
    mix = signal.sosfiltfilt(signal.butter(2, 32, "high", fs=SR, output="sos"), mix, axis=0)
    mix = mix[: int(total * SR) + int(3 * SR)]
    return (mix / max(np.abs(mix).max(), 1e-9) * 0.9).astype(np.float32), total


if __name__ == "__main__":
    edl = json.load(open(sys.argv[1]))
    out, total = build(edl)
    sf.write(sys.argv[2], out, SR, subtype="FLOAT")
    print(f"score {len(out) / SR:.1f}s for a {total:.1f}s video")
