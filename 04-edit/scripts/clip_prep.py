"""Prepare one of Mert's clips (thank-you / FAQ) for the same edit as his VSL: voice clean-up, word-level transcript,
cut list (from just before the first word to just after the last, true silences between words trimmed), and the
graded 30 fps A-roll at 2560x1440 (16:9, cropped centred from whatever the phone recorded, rotation applied).

    python clip_prep.py name src.mov
"""
import json, os, subprocess, sys, wave
import numpy as np
sys.path.insert(0, "/home/user/work/scripts")
from ty_plan import load_words, plan_cuts, mapper

name, src = sys.argv[1], sys.argv[2]
D = f"/home/user/work/ty_faq/{name}"
os.makedirs(f"{D}/base", exist_ok=True)
VC = open("/home/user/work/scripts/voice_chain.txt").read().strip()
GRADE = "eq=contrast=1.05:saturation=1.05"
run = lambda *a: subprocess.run(list(a), check=True)

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                           capture_output=True, text=True).stdout)
if not os.path.exists(f"{D}/voice_proc.wav"):
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", f"{D}/audio16k.wav")
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", "48000", "-af", VC, "-c:a", "pcm_s24le", f"{D}/voice_proc.wav")
if not os.path.exists(f"{D}/transcript.json"):
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", cpu_threads=4)
    wf = wave.open(f"{D}/audio16k.wav")
    a = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
    segs, _ = m.transcribe(a, word_timestamps=True, language="en", beam_size=5)
    out = [{"start": s.start, "end": s.end, "text": s.text,
            "words": [{"w": w.word, "s": w.start, "e": w.end, "p": w.probability} for w in s.words]} for s in segs]
    json.dump(out, open(f"{D}/transcript.json", "w"), indent=1)
W = load_words(f"{D}/transcript.json")
start = max(0.0, round(round((W[0]["s"] - 0.15) * 30) / 30, 4))
stop = min(dur, W[-1]["e"] + 0.6)
keep = [(max(a, start), min(b, stop)) for a, b in plan_cuts(W, f"{D}/voice_proc.wav", dur) if b > start and a < stop]
keep = [(a, b) for a, b in keep if b - a >= 2 / 30]
_, total = mapper(keep)
json.dump({"start_word": 0, "start": start, "keep": keep, "dur": total}, open(f"{D}/cuts.json", "w"), indent=1)
# 16:9 crop: scale to 2560 wide, keep the top of the frame (his head) when the source is taller than 16:9
crop = "scale=2560:-2:flags=lanczos,crop=2560:1440:0:'min(ih-1440,(ih-1440)*0.3)'"
parts = []
for k, (a, b) in enumerate(keep):
    nf = round((b - a) * 30)
    out = f"{D}/base/p{k:03d}.mp4"
    run("ffmpeg", "-y", "-v", "error", "-ss", f"{a:.4f}", "-i", src, "-vf",
        f"fps=30,trim=end_frame={nf},setpts=PTS-STARTPTS,{crop},{GRADE},format=yuv420p", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "13", "-g", "15", out)
    parts.append(out)
open(f"{D}/base/list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{D}/base/list.txt", "-c", "copy", f"{D}/base.mp4")
n = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of",
                        "csv=p=0", f"{D}/base.mp4"], capture_output=True, text=True).stdout)
print(f"{name}: raw {dur:.1f}s -> {total:.2f}s in {len(keep)} pieces, base {n} frames (expected {round(total * 30)})")
for s in json.load(open(f"{D}/transcript.json")):
    print(f"  {s['start']:6.2f} {s['text'].strip()}")
