"""Version 2 of the strings cue, rewritten after studying how the strings move in Iman Gadzhi's bed.

What his music does (measured on the music-only side channel, L-R, of his mix; see IMAN-AUDIO.md):
  * the chords change every 2 beats (about every 1.1 s), over a bass that walks down A-G-F-E (the "lament" line, with
    E major's G# pulling back to A minor) or rocks between A and E. Something moves every second.
  * the violins never hold one note for long: the same high notes (A5 and E5 together) are re-bowed on every 16th
    (attacks every 0.14-0.19 s), with a repeated E4 eighth-note pedal underneath, like a clock ticking.
  * a slow line (C5-B4-A4-G#4) moves one step per chord, under the ticking.
  * at an important instruction the strings slide down for 3-4 s (a downward glissando) before the music changes.

So this version: chords every 2 beats in the tense parts and every bar in the calmer ones; violins re-bow a pair of
chord tones together on every 16th; violas tick an E pedal; cellos + basses keep the eighth-note drive; a stepwise melody
moves with each chord; a rising staircase in the build to the reveal; a downward slide into "what most people don't
understand". Section times and hits follow the same cue sheet as v1 (raw-video seconds, mapped through the cut list).

    python strings_score2.py edl3.json out.wav
"""
import json, sys
import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, "/home/user/work/scripts")
import strings_score as S0
from strings_score import note, perc, hit, roll, grid, BEAT, E8, E16, BAR, SR, TIMP_HIT

# chord: bass (cello register), pad tones (violas/cellos), violin ostinato pair (lower, upper)
CH = {
    "Am": dict(bass=45, pad=(57, 60, 64), ost=(76, 81)),   # A2 | A3 C4 E4 | E5 A5
    "G": dict(bass=43, pad=(55, 59, 62), ost=(74, 79)),    # G2 | G3 B3 D4 | D5 G5
    "F": dict(bass=41, pad=(57, 60, 65), ost=(77, 81)),    # F2 | A3 C4 F4 | F5 A5
    "E": dict(bass=40, pad=(56, 59, 64), ost=(76, 80)),    # E2 | G#3 B3 E4 | E5 G#5
    "C": dict(bass=48, pad=(55, 60, 64), ost=(76, 79)),    # C3 | G3 C4 E4 | E5 G5
}
LAMENT = (["Am", "G", "F", "E"], [72, 71, 69, 68])        # melody C5 B4 A4 G#4
LAMENT_HI = (["Am", "G", "F", "E"], [76, 74, 72, 71])     # E5 D5 C5 B4
LIFT = (["Am", "F", "C", "G"], [72, 69, 67, 71])          # C5 A4 G4 B4
ROCK = (["Am", "E"], [72, 71])                            # C5 B4


class Prog:
    def __init__(self, prog, t0, beats):
        self.seq, self.mel = prog
        self.t0, self.L = t0, beats * BEAT

    def idx(self, t):
        return int((t - self.t0 + 1e-6) // self.L)

    def chord(self, t):
        return CH[self.seq[self.idx(t) % len(self.seq)]]

    def starts(self, t0, t1):
        k0 = self.idx(t0)
        out = [t0]
        k = k0 + 1
        while self.t0 + k * self.L < t1 - 0.05:
            out.append(self.t0 + k * self.L)
            k += 1
        return out


def bass_drive(buf, t0, t1, P, vel=0.8, bass=True):
    S0.ostinato(buf, t0, t1, lambda t: P.chord(t)["bass"], vel=vel, bass=bass)


def pad(buf, t0, t1, P, vel=(0.35, 0.6), gain=0.45):
    st = P.starts(t0, t1)
    for j, s in enumerate(st):
        e = st[j + 1] if j + 1 < len(st) else t1
        c = P.chord(s)
        lo, mid, hi = c["pad"]
        note(buf, "vc_sus", lo, s, dur=e - s, vel=vel[1], attack=0.12, release=0.45, swell=vel, gain=gain)
        note(buf, "vla_sus", mid, s, dur=e - s, vel=vel[1], attack=0.12, release=0.45, swell=vel, gain=gain * 0.8)
        note(buf, "vla_sus", hi, s, dur=e - s, vel=vel[1], attack=0.12, release=0.45, swell=vel, gain=gain * 0.7)


def melody(buf, t0, t1, P, line=None, vel=(0.4, 0.75), gain=0.6, octave=0):
    st = P.starts(t0, t1)
    mel = line or P.mel
    for j, s in enumerate(st):
        e = st[j + 1] if j + 1 < len(st) else t1
        m = mel[P.idx(s) % len(mel)] + octave
        note(buf, "vln_sus", m, s, dur=e - s, vel=vel[1], attack=0.1, release=0.5, swell=vel, gain=gain)


def vln_tick(buf, t0, t1, P, rate=E16, vel=0.5, gain=0.5, cresc=None, upper=None):
    """Violins (divisi) re-bowing a pair of chord tones together on every 16th (or 8th), accented on the beat."""
    ts = grid(t0, t1, rate)
    acc = (1.0, 0.72, 0.85, 0.72) if rate == E16 else (1.0, 0.75)
    for n, t in enumerate(ts):
        i = int(round(t / rate)) % len(acc)
        lo, hi = P.chord(t)["ost"]
        if upper:
            hi = upper(t)
        v = vel * acc[i]
        if cresc:
            v *= cresc[0] + (cresc[1] - cresc[0]) * n / max(len(ts) - 1, 1)
        note(buf, "vln_spic", hi, t, vel=v, gain=gain * 0.62)
        note(buf, "vln_spic", lo, t, vel=v, gain=gain * 0.5)


def pedal_tick(buf, t0, t1, midi=64, vel=0.42, gain=0.5):
    """The repeated E eighth-note pedal (violas), the clock under everything."""
    for t in grid(t0, t1, E8):
        i = int(round(t / E8)) % 2
        note(buf, "vla_spic", midi, t, vel=vel * (1.0 if i == 0 else 0.75), gain=gain)


def trem(buf, t0, t1, midi=81, vel=(0.2, 0.9), gain=0.4, attack=0.6):
    note(buf, "vln_trem", midi, t0, dur=t1 - t0, vel=0.85, attack=attack, release=0.08, swell=vel, gain=gain)


def gliss(buf, art, midi, t, dur, drop=14.0, gain=0.5, vel=0.85):
    """A string note sliding down `drop` semitones over `dur` seconds (Iman's slide before a change)."""
    r = S0.pick(art, midi, vel)
    x = S0.repitch(S0.load(r["file"]), midi - r["midi"])
    u = np.arange(int(dur * SR)) / SR
    pos = np.cumsum(2 ** (-drop * (u / dur) ** 1.4 / 12))
    pos = pos[pos < len(x) - 1]
    y = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    env = np.minimum(1, np.minimum(np.arange(len(y)) / (0.25 * SR), (len(y) - np.arange(len(y))) / (0.9 * SR)))
    y *= env[:, None] * vel * gain
    s = int(t * SR)
    buf[s:s + len(y)] += y[:len(buf) - s]


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

    # 0 - 5.74 hook: an airy held E (Iman opens on a held E too), 16ths ticking on E/A swelling, roll into the hit
    t0, t1 = S(0.0, 5.74)
    for mm, g in ((76, 0.5), (64, 0.42)):
        note(buf, "vln_trem", mm, t0, dur=t1 - t0, vel=0.9, attack=0.05, release=0.08, swell=(0.35, 1.0), gain=g)
    P = Prog(([("Am")], [76]), t0, 4)
    vln_tick(buf, t0 + 1.0, t1, P, vel=0.55, gain=0.45, cresc=(0.35, 1.0))
    roll(buf, t1, 3.2, 1.5)
    hit(buf, t1, 1.0)
    # 5.76 - 14.28 "I owed money to my mom...": lament, a chord every 2 beats, violins ticking 16ths
    t0, t1 = S(5.76, 14.28)
    P = Prog(LAMENT, t0, 2)
    bass_drive(buf, t0, t1, P, vel=0.85)
    pad(buf, t0, t1, P)
    melody(buf, t0, t1, P)
    vln_tick(buf, t0, t1, P, vel=0.5)
    pedal_tick(buf, m(8.3), t1)
    roll(buf, t1, 2.2, 0.9)
    hit(buf, t1, 0.55)
    # 14.28 - 47.4 "Then I changed three simple things": lift, a chord every bar
    t0, t1 = S(14.28, 47.40)
    P = Prog(LIFT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.75)
    pad(buf, t0, t1, P, vel=(0.35, 0.55))
    melody(buf, t0, t1, P, vel=(0.4, 0.7))
    vln_tick(buf, t0, t1, P, vel=0.45)
    pedal_tick(buf, m(20.0), t1, vel=0.32)
    # 47.4 - 67.76 the pain: lament every 2 beats, tremolo rising on top, roll into $0
    t0, t1 = S(47.40, 67.76)
    P = Prog(LAMENT, t0, 2)
    bass_drive(buf, t0, t1, P, vel=0.8)
    pad(buf, t0, t1, P)
    melody(buf, t0, t1, P, vel=(0.4, 0.8))
    vln_tick(buf, t0, t1, P, vel=0.5)
    pedal_tick(buf, t0, t1, vel=0.36)
    trem(buf, m(58.0), t1, 81, gain=0.36)
    roll(buf, t1, 3.0, 1.5)
    hit(buf, t1, 0.95)
    # 67.8 - 81.6 softer lift: no basses, violins in 8ths
    t0, t1 = S(67.80, 81.60)
    P = Prog(LIFT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.6, bass=False)
    pad(buf, t0, t1, P, vel=(0.3, 0.5))
    melody(buf, t0, t1, P, vel=(0.35, 0.6))
    vln_tick(buf, t0, t1, P, rate=E8, vel=0.42)
    # 81.6 - 102.6 the open loop: lament, ticking, tremolo build, small hit on the title, roll into the story
    t0, t1 = S(81.60, 102.60)
    P = Prog(LAMENT, t0, 2)
    bass_drive(buf, t0, t1, P, vel=0.78)
    pad(buf, t0, t1, P)
    melody(buf, t0, t1, P, line=LAMENT_HI[1], vel=(0.4, 0.75))
    vln_tick(buf, t0, t1, P, vel=0.48)
    pedal_tick(buf, t0, t1, vel=0.36)
    trem(buf, m(86.0), m(95.3), 81, gain=0.34, attack=0.8)
    roll(buf, m(95.30), 2.0, 0.9)
    hit(buf, m(95.30), 0.5)
    roll(buf, t1, 3.0, 1.2)
    hit(buf, t1, 0.6)
    # 102.6 - 114.5 the story opens: slower lament (a chord a bar), only the E pedal ticking, melody sings
    t0, t1 = S(102.60, 114.50)
    P = Prog(LAMENT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.5, bass=False)
    pad(buf, t0, t1, P, vel=(0.3, 0.55))
    melody(buf, t0, t1, P, vel=(0.35, 0.7))
    pedal_tick(buf, t0, t1, vel=0.38)
    # 114.5 - 126.88 threatened at work / "I can't do this anymore": chords every 2 beats, 16ths creep in, into I QUIT
    t0, t1 = S(114.50, 126.88)
    P = Prog(LAMENT, t0, 2)
    bass_drive(buf, t0, t1, P, vel=0.7)
    pad(buf, t0, t1, P)
    melody(buf, t0, t1, P, line=LAMENT_HI[1], vel=(0.4, 0.78))
    vln_tick(buf, t0, t1, P, vel=0.5, cresc=(0.5, 1.0))
    pedal_tick(buf, t0, t1, vel=0.36)
    trem(buf, m(120.2), t1, 81, gain=0.36, attack=0.5)
    roll(buf, t1, 2.6, 1.1)
    hit(buf, m(126.88), 0.75)
    # 126.88 - 131.2 "I QUIT." card: a breath, low A and a high E ringing
    t0, t1 = S(126.88, 131.20)
    note(buf, "cb_sus", 33, t0, dur=t1 - t0, vel=0.6, attack=0.4, release=0.4, swell=(0.6, 0.4), gain=0.6)
    trem(buf, t0, t1 + 0.3, 76, vel=(0.5, 0.3), gain=0.3, attack=0.3)
    # 131.2 - 150 rocking A minor / E: 8ths, then 16ths from "you're falling for the TikTok scams"
    t0, t1 = S(131.20, 150.00)
    P = Prog(ROCK, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.55, bass=False)
    pad(buf, t0, t1, P, vel=(0.3, 0.55))
    melody(buf, t0, t1, P, vel=(0.35, 0.7))
    pedal_tick(buf, t0, m(139.75), vel=0.38)
    vln_tick(buf, m(139.75), t1, P, vel=0.45, cresc=(0.6, 1.0))
    # 150 - 164.1 lament a bar per chord, ticking
    t0, t1 = S(150.00, 164.10)
    P = Prog(LAMENT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.6)
    pad(buf, t0, t1, P)
    melody(buf, t0, t1, P, vel=(0.4, 0.72))
    vln_tick(buf, t0, t1, P, vel=0.45)
    hit(buf, m(164.12), 0.4)
    hit(buf, m(166.48), 0.75)
    # 166.5 - 186.6 mom / "everybody was right about me": lament every 2 beats, high melody, building
    t0, t1 = S(166.50, 186.60)
    P = Prog(LAMENT, t0, 2)
    bass_drive(buf, t0, t1, P, vel=0.72)
    pad(buf, t0, t1, P)
    melody(buf, t0, t1, P, line=LAMENT_HI[1], vel=(0.4, 0.82))
    vln_tick(buf, t0, t1, P, vel=0.5, cresc=(0.7, 1.0))
    pedal_tick(buf, t0, t1, vel=0.36)
    # 186.4 - 201.62 build into the reveal: pedal A, the violins' top note climbs a semitone every bar, long roll,
    # then half a second of silence before "YouTube Shorts"
    t0, t1 = S(186.40, 201.62)
    P = Prog((["Am"], [72]), t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.85)
    vln_tick(buf, t0, t1, P, vel=0.55, cresc=(0.6, 1.0), upper=lambda t: 81 + min(int((t - t0) // BAR), 7))
    pedal_tick(buf, t0, t1, vel=0.42)
    trem(buf, t0, t1, 76, vel=(0.25, 1.0), gain=0.42, attack=1.0)
    note(buf, "vc_sus", 45, t0, dur=t1 - t0, vel=0.7, attack=1.0, release=0.05, swell=(0.3, 0.8), gain=0.5)
    roll(buf, t1, 4.0, 1.8)
    hit(buf, m(202.12), 1.15)
    # 203.3 - 277.25 proof: full drive, a chord a bar, 16ths, timpani every 4 bars; 8ths for contrast in the middle
    t0, t1 = S(203.30, 277.25)
    P = Prog(LIFT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.85)
    pad(buf, t0, t1, P, vel=(0.4, 0.6))
    melody(buf, t0, t1, P, vel=(0.45, 0.78))
    mid0, mid1 = m(233.73), m(252.5)
    vln_tick(buf, t0, mid0, P, vel=0.5)
    vln_tick(buf, mid0, mid1, P, rate=E8, vel=0.48)
    vln_tick(buf, mid1, t1 - 3.0, P, vel=0.52)
    pedal_tick(buf, t0, t1 - 3.0, vel=0.34)
    for tb in grid(t0, t1, 4 * BAR):
        perc(buf, TIMP_HIT[int(tb) % 2], tb, gain=0.9)
    gliss(buf, "vln_sus", 81, t1 - 3.4, 3.6, drop=14, gain=0.55)     # slide down into the next part
    gliss(buf, "vln_sus", 76, t1 - 3.4, 3.6, drop=14, gain=0.45)
    # 277.3 - 294.08 "what most people don't understand": strip back, only slow chords + ticking, roll into 01
    t0, t1 = S(277.30, 294.08)
    hit(buf, t0, 0.5)
    P = Prog(LAMENT, t0, 4)
    pad(buf, t0, t1, P, vel=(0.3, 0.5), gain=0.4)
    pedal_tick(buf, t0, t1, vel=0.38)
    trem(buf, t0, t1, 81, vel=(0.3, 0.85), gain=0.4, attack=0.4)
    note(buf, "cb_sus", 33, t0, dur=t1 - t0, vel=0.6, attack=1.0, release=0.1, swell=(0.3, 0.7), gain=0.6)
    roll(buf, t1, 3.0, 1.3)
    hit(buf, t1, 0.65)
    # 294.1 - 372.3 offer: steady lift, ticking 16ths, a little stronger from the phone number on, hits on the cards
    t0, t1 = S(294.10, 372.30)
    P = Prog(LIFT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.7)
    pad(buf, t0, t1, P, vel=(0.35, 0.55))
    melody(buf, t0, t1, P, vel=(0.4, 0.7))
    vln_tick(buf, t0, m(344.3), P, vel=0.4)
    vln_tick(buf, m(344.3), t1, P, vel=0.46)
    pedal_tick(buf, m(300.0), m(356.0), vel=0.3)
    for x in (299.92, 307.30):
        hit(buf, m(x), 0.45)
    hit(buf, m(318.62), 0.7)
    hit(buf, m(360.32), 0.6)
    # 372.3 - end: call to action, ring out on an open A-E chord after the last word
    t0, t1 = S(372.30, 383.60)
    P = Prog(LIFT, t0, 4)
    bass_drive(buf, t0, t1, P, vel=0.6, bass=False)
    pad(buf, t0, t1, P, vel=(0.35, 0.5))
    melody(buf, t0, t1, P, vel=(0.4, 0.65))
    vln_tick(buf, t0, t1, P, rate=E8, vel=0.4)
    te = m(383.60)
    for art, mm, g in (("cb_sus", 33, 0.8), ("vc_sus", 45, 0.7), ("vla_sus", 64, 0.5), ("vln_sus", 69, 0.55), ("vln_sus", 76, 0.45)):
        note(buf, art, mm, te, dur=4.0, vel=0.6, attack=0.3, release=2.5, swell=(0.8, 0.4), gain=g)

    # hall reverb + gentle glue (same as v1)
    n = int(2.6 * SR)
    rng = np.random.default_rng(7)
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
