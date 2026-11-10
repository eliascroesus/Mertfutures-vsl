"""Version 4 of the strings cue: v3's sound (matched to Iman Gadzhi's bed), no booms, and more movement for retention.

Changes from v3, after comparing with Iman's and AB Nasdaq's beds:
  * no drums, timpani, rolls or sub hits at all ("drop booms" removed); transitions are carried by the strings
  * the violins switch pattern every 4 bars: Iman-style re-bowed pairs, then AB-style broken chords (single notes
    walking through the chord), so the top keeps changing without changing the mood
  * every 4-bar phrase breathes: the violins swell a little through the phrase and reset
  * the melody walks to the next chord through passing notes instead of holding one note per chord
  * no dead air before "YouTube Shorts": the proof music starts on the title card

v3 notes:

What changed after measuring his music against ours (music-only side channel and his pauses; see IMAN-AUDIO.md):
  * tempo: his runs at about 101-103 BPM (beat 0.58-0.59 s, ticks every 0.145 s). v2 ran at 115 and felt rushed.
  * articulation: his high strings are crisp, with deep gaps between notes (14-18 dB on A5); ours smeared (8-10 dB).
    The short notes are now cut to fit their 16th and get far less reverb than the long notes.
  * a ticking layer: his top end (4.5-11 kHz) is a 16th-note shaker/hat tick with 17-25 dB gaps, evenly accented.
    Here: a real tambourine (VSCO 2 CE, 12 different hits), band-passed so only the jingle "tick" is left, a
    different hit in each ear so it sits wide like his.
  * width: his music is focused (side 15-20 dB under the centre); ours was very wide (5 dB) and washy. Now narrowed.
  * tone: his is much brighter above 5 kHz and has sub weight on the hits; ours was dark. Brighter strings, sub
    under the hits (the bass drum pitched down).
Composition (progressions, sections, cues) is the same as v2: chords every 2 beats over the falling A-G-F-E bass in
the tense parts, every bar in the calm ones, a melody moving with each chord, a rising staircase into the reveal.

    python strings_score3.py edl3.json out.wav
"""
import glob, json, sys
import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, "/home/user/work/scripts")
import strings_score as S0

SR = 48000
BPM = 102.0
BEAT = 60 / BPM
E8, E16, BAR = BEAT / 2, BEAT / 4, 4 * BEAT
for k, v in dict(BPM=BPM, BEAT=BEAT, E8=E8, E16=E16, BAR=BAR).items():
    setattr(S0, k, v)                       # the shared helpers (grid, ...) follow the new tempo
grid = S0.grid
rng = np.random.default_rng(11)
TAMB = sorted(glob.glob("/home/user/sgossner/extra/tamb3_*.wav")) + sorted(glob.glob("/home/user/sgossner/extra/tamb2_[234].wav"))
VS = S0.VS

# chord: bass (cello register), pad tones (violas/cellos), violin pair (lower, upper)
CH = {
    "Am": dict(bass=45, pad=(57, 60, 64), ost=(76, 81)),
    "G": dict(bass=43, pad=(55, 59, 62), ost=(74, 79)),
    "F": dict(bass=41, pad=(57, 60, 65), ost=(77, 81)),
    "E": dict(bass=40, pad=(56, 59, 64), ost=(76, 80)),
    "C": dict(bass=48, pad=(55, 60, 64), ost=(76, 79)),
}
LAMENT = (["Am", "G", "F", "E"], [72, 71, 69, 68])
LAMENT_HI = [76, 74, 72, 71]
LIFT = (["Am", "F", "C", "G"], [72, 69, 67, 71])
ROCK = (["Am", "E"], [72, 71])


class Bus:
    def __init__(self, n):
        self.x = np.zeros((n, 2), np.float32)


def place(bus, x, t, gain):
    s = int(round((t + rng.normal(0, 0.003)) * SR))
    if s < 0:
        x, s = x[-s:], 0
    e = min(len(bus.x), s + len(x))
    if e > s:
        bus.x[s:e] += x[:e - s] * gain * rng.uniform(0.93, 1.05)


_pc = {}


def sample(art, midi, vel):
    r = S0.pick(art, midi, vel)
    k = (r["file"], midi)
    if k not in _pc:
        _pc[k] = S0.repitch(S0.load(r["file"]), midi - r["midi"])
    return _pc[k]


def short(bus, art, midi, t, length, vel=0.6, gain=1.0):
    """A short bowed note cut to fit its slot (crisp, with a real gap after it)."""
    x = sample(art, midi, vel)[: int(length * SR)].copy()
    nr = min(len(x), int(0.035 * SR))
    x[-nr:] *= np.linspace(1, 0, nr)[:, None] ** 2
    place(bus, x, t, vel * gain)


def long(bus, art, midi, t, dur, vel=0.7, attack=0.1, release=0.5, swell=None, gain=1.0):
    x = sample(art, midi, vel)
    n = min(len(x), int((dur + release) * SR))
    x = x[:n].copy()
    nr = min(n, int(release * SR))
    x[n - nr:] *= np.linspace(1, 0, nr)[:, None] ** 1.5
    na = min(n, int(attack * SR))
    x[:na] *= np.linspace(0, 1, na)[:, None] ** 2
    if swell:
        x *= (np.linspace(swell[0], swell[1], n) ** 1.6)[:, None]
    place(bus, x, t, vel * gain)


_tamb = None


def tick_samples():
    global _tamb
    if _tamb is None:
        sos = signal.butter(4, [6500, 11000], "band", fs=SR, output="sos")
        _tamb = []
        for f in TAMB:
            x = S0.load(f)
            x = signal.sosfiltfilt(sos, x, axis=0).astype(np.float32)
            on = int(np.argmax(np.abs(x).max(1) > 0.05 * np.abs(x).max()))     # trim to the attack
            x = x[max(0, on - 48): on + int(0.07 * SR)].copy()
            x[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))[:, None] ** 2
            _tamb.append(x / np.abs(x).max())
    return _tamb


def ticks(bus, t0, t1, vel=0.5, rate=None, cresc=None):
    """The shaker/hat-style tick in 16ths: evenly accented, a little louder on the beat, never the same hit twice."""
    rate = rate or E16
    ts = grid(t0, t1, rate)
    smp = tick_samples()
    for n, t in enumerate(ts):
        i = int(round(t / rate)) % (4 if rate == E16 else 2)
        v = vel * (1.0 if i == 0 else 0.78) * rng.uniform(0.85, 1.1)
        if cresc:
            v *= cresc[0] + (cresc[1] - cresc[0]) * n / max(len(ts) - 1, 1)
        a, b = rng.choice(len(smp), 2, replace=False)        # a different hit in each ear: wide like his, centre
        ln = min(len(smp[a]), len(smp[b]))                    # stays clear for the voice, still there in mono
        g = (1.0, 0.7) if n % 2 else (0.7, 1.0)
        x = np.stack([smp[a][:ln, 0] * g[0], smp[b][:ln, 1] * g[1]], 1)
        place(bus, x, t, v)


class Prog:
    def __init__(self, prog, t0, beats):
        self.seq, self.mel = prog
        self.t0, self.L = t0, beats * BEAT

    def idx(self, t):
        return int((t - self.t0 + 1e-6) // self.L)

    def chord(self, t):
        return CH[self.seq[self.idx(t) % len(self.seq)]]

    def starts(self, t0, t1):
        out, k = [t0], self.idx(t0) + 1
        while self.t0 + k * self.L < t1 - 0.05:
            out.append(self.t0 + k * self.L)
            k += 1
        return out


def bass_drive(sh, t0, t1, P, vel=0.8, bass=True):
    """Cellos (and basses) in eighths on the chord root, octave/fifth flicks at the end of the bar."""
    for t in grid(t0, t1, E8):
        i = int(round(t / E8)) % 8
        r = P.chord(t)["bass"]
        m = r + (12 if i == 7 else 7 if i == 6 and int(t / BAR) % 2 else 0)
        acc = vel * (1.0 if i in (0, 4) else 0.78)
        short(sh, "vc_spic", m, t, E8 * 0.7, vel=acc, gain=0.9)
        if bass and i % 2 == 0:
            short(sh, "cb_spic", r - 12, t, E8 * 1.6, vel=acc * 0.95, gain=1.0)


def pad(lg, t0, t1, P, vel=(0.35, 0.6), gain=0.45):
    st = P.starts(t0, t1)
    for j, s in enumerate(st):
        e = st[j + 1] if j + 1 < len(st) else t1
        lo, mid, hi = P.chord(s)["pad"]
        long(lg, "vc_sus", lo, s, e - s, vel=vel[1], attack=0.12, release=0.45, swell=vel, gain=gain)
        long(lg, "vla_sus", mid, s, e - s, vel=vel[1], attack=0.12, release=0.45, swell=vel, gain=gain * 0.8)
        long(lg, "vla_sus", hi, s, e - s, vel=vel[1], attack=0.12, release=0.45, swell=vel, gain=gain * 0.7)


SCALE = [57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81]     # A natural minor, A3..A5


def steps_between(a, b, n):
    """Up to n notes leading from a into b: the scale notes in between, or (for a step) b's neighbour from the
    other side, so the line always moves into the next chord."""
    sc = sorted(set(SCALE + [b]))
    ia = min(range(len(sc)), key=lambda k: abs(sc[k] - a)); ib = sc.index(b)
    d = 1 if ib > ia else -1
    between = [sc[k] for k in range(ia + d, ib, d)][:n]
    if between:
        return between
    k = ib + d                                   # approach from beyond the target
    return [sc[k]] if 0 <= k < len(sc) else []


def melody(lg, t0, t1, P, line=None, vel=(0.4, 0.75), gain=0.6):
    """One melody note per chord; on chords a bar long it walks to the next chord's note in the last 2 beats."""
    st = P.starts(t0, t1)
    mel = line or P.mel
    for j, s in enumerate(st):
        e = st[j + 1] if j + 1 < len(st) else t1
        m = mel[P.idx(s) % len(mel)]
        nxt = mel[(P.idx(s) + 1) % len(mel)]
        walk = steps_between(m, nxt, 2) if (e - s) > 3.5 * BEAT and j + 1 < len(st) else []
        if walk:
            hold = e - s - len(walk) * BEAT
            long(lg, "vln_sus", m, s, hold, vel=vel[1], attack=0.1, release=0.25, swell=vel, gain=gain)
            for k, w in enumerate(walk):
                long(lg, "vln_sus", w, s + hold + k * BEAT, BEAT, vel=vel[1] * 0.9, attack=0.06, release=0.2, gain=gain * 0.9)
        else:
            long(lg, "vln_sus", m, s, e - s, vel=vel[1], attack=0.1, release=0.5, swell=vel, gain=gain)


ARP = {   # broken-chord shapes for the AB-style bars: top, middle, low, middle
    "Am": (81, 76, 72, 76), "G": (79, 74, 71, 74), "F": (81, 77, 72, 77), "E": (80, 76, 71, 76), "C": (79, 76, 72, 76),
}


def chord_name(P, t):
    return P.seq[P.idx(t) % len(P.seq)]


def vln_tick(sh, t0, t1, P, rate=None, vel=0.5, gain=0.5, cresc=None, upper=None, vary=True):
    """Violins on every 16th (or 8th). Every 4 bars they switch between re-bowing a pair of chord tones together
    (Iman) and walking through the chord one note at a time (AB). Each 4-bar phrase swells a little and resets."""
    rate = rate or E16
    ts = grid(t0, t1, rate)
    acc = (1.0, 0.72, 0.85, 0.72) if rate == E16 else (1.0, 0.75)
    for n, t in enumerate(ts):
        i = int(round(t / rate)) % len(acc)
        lo, hi = P.chord(t)["ost"]
        if upper:
            hi = upper(t)
        phrase = int((t - t0 + 1e-6) // (4 * BAR))
        x = ((t - t0) % (4 * BAR)) / (4 * BAR)
        v = vel * acc[i] * (0.8 + 0.25 * x)                       # phrase swell
        if cresc:
            v *= cresc[0] + (cresc[1] - cresc[0]) * n / max(len(ts) - 1, 1)
        if vary and not upper and phrase % 2 == 1:
            shape = ARP[chord_name(P, t)]
            m = shape[int(round(t / rate)) % 4]
            short(sh, "vln_spic", m, t, rate * 0.6, vel=v, gain=gain * 0.85)
        else:
            short(sh, "vln_spic", hi, t, rate * 0.55, vel=v, gain=gain * 0.62)
            short(sh, "vln_spic", lo, t, rate * 0.55, vel=v, gain=gain * 0.5)


def pedal_tick(sh, t0, t1, midi=64, vel=0.42, gain=0.5):
    for t in grid(t0, t1, E8):
        i = int(round(t / E8)) % 2
        short(sh, "vla_spic", midi, t, E8 * 0.45, vel=vel * (1.0 if i == 0 else 0.75), gain=gain)


def trem(lg, t0, t1, midi=81, vel=(0.2, 0.9), gain=0.4, attack=0.6):
    long(lg, "vln_trem", midi, t0, t1 - t0, vel=0.85, attack=attack, release=0.08, swell=vel, gain=gain)


def gliss(lg, art, midi, t, dur, drop=14.0, gain=0.5, vel=0.85):
    x = sample(art, midi, vel)
    u = np.arange(int(dur * SR)) / SR
    pos = np.cumsum(2 ** (-drop * (u / dur) ** 1.4 / 12))
    pos = pos[pos < len(x) - 1]
    y = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    env = np.minimum(1, np.minimum(np.arange(len(y)) / (0.25 * SR), (len(y) - np.arange(len(y))) / (0.9 * SR)))
    place(lg, (y * env[:, None]).astype(np.float32), t, vel * gain)


TIMP_HIT, TIMP_ROLL, BDRUM = S0.TIMP_HIT, S0.TIMP_ROLL, S0.BDRUM
_sub = []


def sub_boom():
    if not _sub:
        x = S0.repitch(S0.load(BDRUM[0]), -8)
        x = signal.sosfiltfilt(signal.butter(4, 110, "low", fs=SR, output="sos"), x, axis=0)
        x = x[: int(2.2 * SR)].copy()
        x[-int(0.6 * SR):] *= np.linspace(1, 0, int(0.6 * SR))[:, None]
        _sub.append((x / np.abs(x).max()).astype(np.float32))
    return _sub[0]


_h = [0]


def hit(lg, sub, t, big=1.0):
    _h[0] += 1
    S0.perc(lg.x, TIMP_HIT[_h[0] % 2], t, gain=2.2 * big)
    S0.perc(lg.x, BDRUM[_h[0] % 3 if big >= 1 else 2], t, gain=2.6 * big)
    long(lg, "cb_sus", 33, t, 1.6, vel=0.95, release=1.2, gain=1.3 * big, attack=0.005)
    long(lg, "vc_sus", 45, t, 1.6, vel=0.95, release=1.2, gain=1.0 * big, attack=0.005)
    place(sub, sub_boom(), t, 0.45 * big)


def roll(lg, t_end, length=3.0, gain=1.6):
    S0.perc(lg.x, TIMP_ROLL, t_end - length, gain=gain, fade_in="cresc", length=length + 0.02)


def reverb(x, rt, corr=0.65, lp=8000):
    """Hall-ish reverb; `corr` ties left and right tails together so it doesn't smear wide."""
    n = int(rt * SR)
    r2 = np.random.default_rng(7)
    d = np.exp(-6.9 * np.arange(n) / SR / rt)
    sos = signal.butter(2, lp, "low", fs=SR, output="sos")
    a, b = r2.standard_normal(n), r2.standard_normal(n)
    ir = np.stack([signal.sosfilt(sos, a * d), signal.sosfilt(sos, (corr * a + (1 - corr) * b) * d)], 1)
    ir[: int(0.018 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum() / 2)
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return wet * np.sqrt((x ** 2).mean() / max((wet ** 2).mean(), 1e-12))


def narrow(x, side_gain):
    m, s = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2 * side_gain
    return np.stack([m + s, m - s], 1)


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
    n = int((total + 8) * SR)
    SH, LG, TK, SUB = Bus(n), Bus(n), Bus(n), Bus(n)        # short strings, long strings + hits, ticks, sub
    S = lambda a, b: (m(a), m(b))

    # 0 - 5.74 hook: an airy held E, violins ticking on E/A swelling, the tick enters halfway, roll into the hit
    t0, t1 = S(0.0, 5.74)
    for mm, g in ((76, 0.5), (64, 0.42)):
        long(LG, "vln_trem", mm, t0, t1 - t0, vel=0.9, attack=0.05, release=0.08, swell=(0.35, 1.0), gain=g)
    P = Prog((["Am"], [76]), t0, 4)
    vln_tick(SH, t0 + 1.0, t1, P, vel=0.55, gain=0.45, cresc=(0.35, 1.0))
    ticks(TK, t0 + 2.9, t1, vel=0.5, cresc=(0.3, 1.0))
    # 5.76 - 14.28 "I owed money to my mom...": lament, a chord every 2 beats
    t0, t1 = S(5.76, 14.28)
    P = Prog(LAMENT, t0, 2)
    bass_drive(SH, t0, t1, P, vel=0.85)
    pad(LG, t0, t1, P)
    melody(LG, t0, t1, P)
    vln_tick(SH, t0, t1, P, vel=0.5)
    pedal_tick(SH, m(8.3), t1)
    ticks(TK, t0, t1, vel=0.55)
    # 14.28 - 47.4 "Then I changed three simple things": lift, a chord every bar
    t0, t1 = S(14.28, 47.40)
    P = Prog(LIFT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.75)
    pad(LG, t0, t1, P, vel=(0.35, 0.55))
    melody(LG, t0, t1, P, vel=(0.4, 0.7))
    vln_tick(SH, t0, t1, P, vel=0.45)
    pedal_tick(SH, m(20.0), t1, vel=0.32)
    ticks(TK, t0, t1, vel=0.5)
    # 47.4 - 67.76 the pain: lament every 2 beats, tremolo rising on top, roll into $0
    t0, t1 = S(47.40, 67.76)
    P = Prog(LAMENT, t0, 2)
    bass_drive(SH, t0, t1, P, vel=0.8)
    pad(LG, t0, t1, P)
    melody(LG, t0, t1, P, vel=(0.4, 0.8))
    vln_tick(SH, t0, t1, P, vel=0.5)
    pedal_tick(SH, t0, t1, vel=0.36)
    ticks(TK, t0, t1, vel=0.55)
    trem(LG, m(58.0), t1, 81, gain=0.36)
    # 67.8 - 81.6 softer lift: no basses, violins and tick in 8ths
    t0, t1 = S(67.80, 81.60)
    P = Prog(LIFT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.6, bass=False)
    pad(LG, t0, t1, P, vel=(0.3, 0.5))
    melody(LG, t0, t1, P, vel=(0.35, 0.6))
    vln_tick(SH, t0, t1, P, rate=E8, vel=0.42)
    ticks(TK, t0, t1, vel=0.45, rate=E8)
    # 81.6 - 102.6 the open loop: lament, ticking, tremolo build, small hit on the title, roll into the story
    t0, t1 = S(81.60, 102.60)
    P = Prog(LAMENT, t0, 2)
    bass_drive(SH, t0, t1, P, vel=0.78)
    pad(LG, t0, t1, P)
    melody(LG, t0, t1, P, line=LAMENT_HI, vel=(0.4, 0.75))
    vln_tick(SH, t0, t1, P, vel=0.48)
    pedal_tick(SH, t0, t1, vel=0.36)
    ticks(TK, t0, t1, vel=0.55)
    trem(LG, m(86.0), m(95.3), 81, gain=0.34, attack=0.8)
    # 102.6 - 114.5 the story opens: slower lament (a chord a bar), E pedal and the tick in 8ths, melody sings
    t0, t1 = S(102.60, 114.50)
    P = Prog(LAMENT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.5, bass=False)
    pad(LG, t0, t1, P, vel=(0.3, 0.55))
    melody(LG, t0, t1, P, vel=(0.35, 0.7))
    pedal_tick(SH, t0, t1, vel=0.38)
    ticks(TK, t0, t1, vel=0.4, rate=E8)
    # 114.5 - 126.88 threatened at work / "I can't do this anymore": chords every 2 beats, 16ths creep in, into I QUIT
    t0, t1 = S(114.50, 126.88)
    P = Prog(LAMENT, t0, 2)
    bass_drive(SH, t0, t1, P, vel=0.7)
    pad(LG, t0, t1, P)
    melody(LG, t0, t1, P, line=LAMENT_HI, vel=(0.4, 0.78))
    vln_tick(SH, t0, t1, P, vel=0.5, cresc=(0.5, 1.0))
    pedal_tick(SH, t0, t1, vel=0.36)
    ticks(TK, t0, t1, vel=0.55, cresc=(0.6, 1.0))
    trem(LG, m(120.2), t1, 81, gain=0.36, attack=0.5)
    # 126.88 - 131.2 "I QUIT." card: a breath, low A and a high E ringing
    t0, t1 = S(126.88, 131.20)
    long(LG, "cb_sus", 33, t0, t1 - t0, vel=0.6, attack=0.4, release=0.4, swell=(0.6, 0.4), gain=0.6)
    trem(LG, t0, t1 + 0.3, 76, vel=(0.5, 0.3), gain=0.3, attack=0.3)
    # 131.2 - 150 rocking A minor / E: 8ths, then 16ths from "you're falling for the TikTok scams"
    t0, t1 = S(131.20, 150.00)
    P = Prog(ROCK, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.55, bass=False)
    pad(LG, t0, t1, P, vel=(0.3, 0.55))
    melody(LG, t0, t1, P, vel=(0.35, 0.7))
    pedal_tick(SH, t0, m(139.75), vel=0.38)
    ticks(TK, t0, m(139.75), vel=0.4, rate=E8)
    vln_tick(SH, m(139.75), t1, P, vel=0.45, cresc=(0.6, 1.0))
    ticks(TK, m(139.75), t1, vel=0.5)
    # 150 - 166.5 lament a bar per chord, ticking
    t0, t1 = S(150.00, 166.50)          # runs on under the 18,000,000 and $87 cards
    P = Prog(LAMENT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.6)
    pad(LG, t0, t1, P)
    melody(LG, t0, t1, P, vel=(0.4, 0.72))
    vln_tick(SH, t0, t1, P, vel=0.45)
    ticks(TK, t0, t1, vel=0.5)
    # 166.5 - 186.6 mom / "everybody was right about me": lament every 2 beats, high melody, building
    t0, t1 = S(166.50, 186.60)
    P = Prog(LAMENT, t0, 2)
    bass_drive(SH, t0, t1, P, vel=0.72)
    pad(LG, t0, t1, P)
    melody(LG, t0, t1, P, line=LAMENT_HI, vel=(0.4, 0.82))
    vln_tick(SH, t0, t1, P, vel=0.5, cresc=(0.7, 1.0))
    pedal_tick(SH, t0, t1, vel=0.36)
    ticks(TK, t0, t1, vel=0.55, cresc=(0.75, 1.0))
    # 186.4 - 201.62 build into the reveal: pedal A, the violins' top note climbs a semitone every bar, long roll,
    # then half a second of silence before "YouTube Shorts"
    t0, t1 = S(186.40, 201.62)
    P = Prog((["Am"], [72]), t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.85)
    vln_tick(SH, t0, t1, P, vel=0.55, cresc=(0.6, 1.0), upper=lambda t: 81 + min(int((t - t0) // BAR), 7))
    pedal_tick(SH, t0, t1, vel=0.42)
    ticks(TK, t0, t1, vel=0.55, cresc=(0.6, 1.1))
    trem(LG, t0, t1, 76, vel=(0.25, 1.0), gain=0.42, attack=1.0)
    long(LG, "vc_sus", 45, t0, t1 - t0, vel=0.7, attack=1.0, release=0.05, swell=(0.3, 0.8), gain=0.5)
    # 202.12 - 277.25 proof: starts on the "YouTube Shorts" card, full drive, a chord a bar; 8ths for contrast in the middle
    t0, t1 = S(202.12, 277.25)
    P = Prog(LIFT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.85)
    pad(LG, t0, t1, P, vel=(0.4, 0.6))
    melody(LG, t0, t1, P, vel=(0.45, 0.78))
    mid0, mid1 = m(233.73), m(252.5)
    vln_tick(SH, t0, mid0, P, vel=0.5)
    vln_tick(SH, mid0, mid1, P, rate=E8, vel=0.48)
    vln_tick(SH, mid1, t1 - 3.0, P, vel=0.52)
    pedal_tick(SH, t0, t1 - 3.0, vel=0.34)
    ticks(TK, t0, t1 - 3.0, vel=0.55)
    gliss(LG, "vln_sus", 81, t1 - 3.4, 3.6, drop=14, gain=0.55)
    gliss(LG, "vln_sus", 76, t1 - 3.4, 3.6, drop=14, gain=0.45)
    # 277.3 - 294.08 "what most people don't understand": strip back, slow chords, tick in 8ths, roll into 01
    t0, t1 = S(277.30, 294.08)
    P = Prog(LAMENT, t0, 4)
    pad(LG, t0, t1, P, vel=(0.3, 0.5), gain=0.4)
    pedal_tick(SH, t0, t1, vel=0.38)
    ticks(TK, t0 + 1.0, t1, vel=0.42, rate=E8)
    trem(LG, t0, t1, 81, vel=(0.3, 0.85), gain=0.4, attack=0.4)
    long(LG, "cb_sus", 33, t0, t1 - t0, vel=0.6, attack=1.0, release=0.1, swell=(0.3, 0.7), gain=0.6)
    # 294.1 - 372.3 offer: steady lift, ticking 16ths, a little stronger from the phone number on, hits on the cards
    t0, t1 = S(294.10, 372.30)
    P = Prog(LIFT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.7)
    pad(LG, t0, t1, P, vel=(0.35, 0.55))
    melody(LG, t0, t1, P, vel=(0.4, 0.7))
    vln_tick(SH, t0, m(344.3), P, vel=0.4)
    vln_tick(SH, m(344.3), t1, P, vel=0.46)
    pedal_tick(SH, m(300.0), m(356.0), vel=0.3)
    ticks(TK, t0, t1, vel=0.5)
    # 372.3 - end: call to action, ring out on an open A-E chord after the last word
    t0, t1 = S(372.30, 383.60)
    P = Prog(LIFT, t0, 4)
    bass_drive(SH, t0, t1, P, vel=0.6, bass=False)
    pad(LG, t0, t1, P, vel=(0.35, 0.5))
    melody(LG, t0, t1, P, vel=(0.4, 0.65))
    vln_tick(SH, t0, t1, P, rate=E8, vel=0.4)
    ticks(TK, t0, t1, vel=0.4, rate=E8)
    te = m(383.60)
    for art, mm, g in (("cb_sus", 33, 0.8), ("vc_sus", 45, 0.7), ("vla_sus", 64, 0.5), ("vln_sus", 69, 0.55), ("vln_sus", 76, 0.45)):
        long(LG, art, mm, te, 4.0, vel=0.6, attack=0.3, release=2.5, swell=(0.8, 0.4), gain=g)

    # mix: short strings fairly dry, long strings + hits in the hall, ticks nearly dry; everything narrowed
    shelf = signal.butter(2, 4500, "high", fs=SR, output="sos")
    def bright(x, db):
        return x + signal.sosfilt(shelf, x, axis=0) * (10 ** (db / 20) - 1)
    sh = bright(SH.x.astype(np.float64), 2)
    lg = LG.x.astype(np.float64)
    sh = 0.9 * sh + 0.1 * reverb(sh, 1.6)
    lg = 0.74 * lg + 0.34 * reverb(lg, 2.4)
    tk = 0.92 * TK.x + 0.12 * reverb(TK.x.astype(np.float64), 1.2, corr=0.4, lp=12000)
    mix = narrow(sh, 0.38) + narrow(lg, 0.42) + tk * 0.17 + SUB.x
    mix = signal.sosfiltfilt(signal.butter(2, 28, "high", fs=SR, output="sos"), mix, axis=0)
    mix = mix[: int(total * SR) + int(3 * SR)]
    return (mix / max(np.abs(mix).max(), 1e-9) * 0.9).astype(np.float32), total


if __name__ == "__main__":
    edl = json.load(open(sys.argv[1]))
    out, total = build(edl)
    sf.write(sys.argv[2], out, SR, subtype="FLOAT")
    print(f"score {len(out) / SR:.1f}s for a {total:.1f}s video")
