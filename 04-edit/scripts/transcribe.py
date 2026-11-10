import json, subprocess, sys, time
import numpy as np
from faster_whisper import WhisperModel
src, out = sys.argv[1], sys.argv[2]
t = time.time()
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
audio = np.frombuffer(raw, np.float32).copy()
m = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8", cpu_threads=4,
                 download_root="/home/user/work/models")
segs, info = m.transcribe(audio, language="en", beam_size=5, word_timestamps=True, vad_filter=False,
                          condition_on_previous_text=True)
data = []
for s in segs:
    data.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                 "words": [{"w": w.word, "s": w.start, "e": w.end, "p": round(w.probability, 3)} for w in s.words]})
    print(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text.strip()}", flush=True)
json.dump(data, open(out, "w"), indent=1)
print(f"done in {time.time() - t:.0f}s", file=sys.stderr)
