"""Music bed for Mert's VSL: 'Me And The Devil' (instrumental) exactly as uploaded, no EQ, no level changes.

The beat-only intro (first 5.5 s) is skipped: the video opens right where the symphony comes in (5.54 s into the song),
plays to the song's natural end (~3:02), then goes back to that same point, as many times as the video needs; the last
second fades out.

    python mert_songbed.py song.wav total_seconds out.wav
"""
import json, sys
import numpy as np, soundfile as sf

SR = 48000


def main():
    src, total, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    y, sr = sf.read(src, always_2d=True)
    assert sr == SR
    m = y.mean(1)
    hop = int(0.05 * SR)
    k = len(m) // hop
    db = 20 * np.log10(np.sqrt((m[:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-9)
    end = (np.nonzero(db > -45)[0][-1] + 1) * hop / SR              # where the song's own tail has died away
    start = 5.54                                                     # where the strings/melody enter
    one = y[int(start * SR):int(end * SR)].copy()
    f = int(0.01 * SR)
    one[:f] *= np.linspace(0, 1, f)[:, None]
    n = int(total * SR)
    reps = int(np.ceil(n / len(one))) + 1
    bed = np.concatenate([one] * reps)[:n].copy()
    fo = int(1.0 * SR)
    bed[-fo:] *= np.linspace(1, 0, fo)[:, None]
    sf.write(out, bed.astype(np.float32), SR, subtype="FLOAT")
    json.dump({"song_from": start, "song_to": round(end, 3), "restarts_at": [round((end - start) * i, 3) for i in range(1, reps) if (end - start) * i < total]},
              open(out.replace(".wav", "_loop.json"), "w"))
    print(f"song from {start}s (symphony) to {end:.1f}s; restarts at video time", [round((end - start) * i, 1) for i in range(1, reps) if (end - start) * i < total])


if __name__ == "__main__":
    main()
