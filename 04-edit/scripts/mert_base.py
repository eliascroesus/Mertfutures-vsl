"""Graded A-roll for Mert's VSL: every kept piece cut frame-exact from the 4K60 source, 30 fps, 2560x1440 (so the
push-ins are cropped from real resolution), then joined."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
D = "/home/user/work/mert"
SRC = "/home/user/work/src/Vsl.mov"
GRADE = "eq=contrast=1.07:brightness=0.012:saturation=1.06:gamma=0.98,colorbalance=rs=0.015:bs=-0.01:rh=0.01"
c = json.load(open(f"{D}/cuts.json"))

def piece(k):
    a, b = c["keep"][k]
    nf = round((b - a) * 30)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.4f}", "-i", SRC,
                    "-vf", f"fps=30,trim=end_frame={nf},setpts=PTS-STARTPTS,scale=2560:1440:flags=lanczos,{GRADE},format=yuv420p",
                    "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "13", "-g", "15", f"{D}/base/p{k:03d}.mp4"], check=True)
    return nf

with ThreadPoolExecutor(4) as ex:
    n = list(ex.map(piece, range(len(c["keep"]))))
open(f"{D}/base/list.txt", "w").write("".join(f"file 'p{k:03d}.mp4'\n" for k in range(len(n))))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{D}/base/list.txt", "-c", "copy",
                f"{D}/base.mp4"], check=True)
print("frames", sum(n))
