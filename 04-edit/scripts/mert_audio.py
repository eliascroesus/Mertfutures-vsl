"""Audio for Mert's VSL: his cleaned-up voice cut exactly like the picture, the looped 'Me And The Devil' bed flat
underneath (no ducking, like Iman and AB), and subtle sound effects on the graphics (whooshes into cards and
callouts, soft ticks on side text and list items, pops on the process steps, a swipe on the strike-through), all made
here from scratch. Loudness-normalised to -14 LUFS.

    python mert_audio.py plan.json voice.wav bed.wav out.wav [music_under_db]
"""
import json, subprocess, sys
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
rng = np.random.default_rng(5)


def env(n, attack, decay_tau):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1) ** 2
    d = np.exp(-np.clip(t - attack, 0, None) / decay_tau)
    return a * d


def sweep_noise(dur, f0, f1, q=1.2, peak=0.62):
    """Band-passed noise whose centre sweeps f0 -> f1 (a whoosh), swelling to its peak at `peak` of its length."""
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    out = np.zeros(n)
    blocks = 48
    zi = None
    edges = np.linspace(0, n, blocks + 1).astype(int)
    for b in range(blocks):
        p = b / (blocks - 1)
        fc = f0 * (f1 / f0) ** (p ** 1.3)
        bw = fc / q
        lo, hi = max(fc - bw / 2, 40), min(fc + bw / 2, SR / 2 - 100)
        sos = signal.butter(2, [lo, hi], "band", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[edges[b]:edges[b + 1]], zi = signal.sosfilt(sos, x[edges[b]:edges[b + 1]], zi=zi)
    t = np.linspace(0, 1, n)
    shape = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / (1 - peak) * 4.5))
    return out * shape


def stereo(x, pan_from=-0.6, pan_to=0.6):
    p = np.linspace(pan_from, pan_to, len(x))
    l, r = np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1)


def make(kind):
    if kind == "whoosh":
        x = sweep_noise(0.55, 260, 5200, 1.1, 0.66)
        return stereo(x / np.abs(x).max(), -0.5, 0.5), 0.55
    if kind == "whoosh_soft":
        x = sweep_noise(0.4, 300, 3600, 1.0, 0.7)
        return stereo(x / np.abs(x).max(), 0.3, -0.3), 0.33
    if kind == "tick":
        n = int(0.05 * SR)
        t = np.arange(n) / SR
        x = np.sin(2 * np.pi * 2600 * t) * np.exp(-t / 0.008) + 0.5 * signal.sosfilt(
            signal.butter(2, 4200, "high", fs=SR, output="sos"), rng.normal(0, 1, n)) * np.exp(-t / 0.003)
        return stereo(x / np.abs(x).max(), 0, 0), 0.22
    if kind == "pop":
        n = int(0.16 * SR)
        t = np.arange(n) / SR
        f = 720 * np.exp(-t / 0.03) + 300
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.045)
        return stereo(x / np.abs(x).max(), 0, 0), 0.38
    if kind == "swipe":
        x = sweep_noise(0.28, 1800, 7000, 1.4, 0.4)
        return stereo(x / np.abs(x).max(), -0.7, 0.7), 0.3
    raise ValueError(kind)


def main():
    plan = json.load(open(sys.argv[1]))
    v, vsr = sf.read(sys.argv[2], dtype="float64")
    bed, bsr = sf.read(sys.argv[3], dtype="float64", always_2d=True)
    out = sys.argv[4]
    under = float(sys.argv[5]) if len(sys.argv) > 5 else 18.0
    assert vsr == SR and bsr == SR
    n = int(round(plan["dur"] * SR))
    voice = np.zeros((n, 2))
    pos, fade = 0, int(0.008 * SR)
    for a, b in plan["keep"]:
        seg = v[int(round(a * SR)):int(round(b * SR))].copy()
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]
        seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        m = min(len(seg), n - pos)
        voice[pos:pos + m] += seg[:m]
        pos += len(seg)
    hop = int(0.05 * SR)
    k = n // hop
    e = np.sqrt((voice[:k * hop].mean(1).reshape(k, hop) ** 2).mean(1))
    talk = e[e > np.percentile(e, 60) * 0.5]
    v_rms = np.sqrt((talk ** 2).mean())
    m_rms = np.sqrt((bed ** 2).mean())
    music = np.zeros((n, 2))
    mm = min(n, len(bed))
    music[:mm] = bed[:mm] * (v_rms / m_rms * 10 ** (-under / 20))
    fx = np.zeros((n, 2))
    lib = {}
    for kind, t, g in plan["sfx"]:
        if kind not in lib:
            lib[kind] = make(kind)
        x, lvl = lib[kind]
        i = int(round(t * SR))
        if i < 0:
            x, i = x[-i:], 0
        m = min(len(x), n - i)
        if m > 0:
            fx[i:i + m] += x[:m] * lvl * g * v_rms / 0.25
    mix = voice + music + fx * 0.32
    tmp = out + ".pre.wav"
    sf.write(tmp, mix.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-v", "info", "-hide_banner", "-i", tmp, "-af",
                        "loudnorm=I=-14:TP=-1.2:LRA=9:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    st = json.loads(r.stderr[r.stderr.rindex("{"):])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af",
                    f"loudnorm=I=-14:TP=-1.2:LRA=9:measured_I={st['input_i']}:measured_TP={st['input_tp']}:"
                    f"measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']}:linear=true",
                    "-ar", str(SR), "-c:a", "pcm_s24le", out], check=True)
    print(f"voice in {len(plan['keep'])} pieces, music {under:.0f} dB under the voice, {len(plan['sfx'])} sound effects")


if __name__ == "__main__":
    main()
