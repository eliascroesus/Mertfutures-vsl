"""Render single frames of the thank-you edit for checking: python ty_stills.py plan.json base.mp4 outdir t1 t2 ..."""
import json, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, "/home/user/work/scripts")
import ty_render as R

plan = json.load(open(sys.argv[1])); base = sys.argv[2]; od = sys.argv[3]
zoom, leaks = R.Zoom(plan["zoom"]), R.Leaks(plan["leaks"])
scenes = [R.Scene(s, plan) for s in plan["scenes"]]
caps = R.Captions(plan["captions"])
for ts in sys.argv[4:]:
    t = float(ts)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", base, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    face = np.frombuffer(raw, np.uint8).reshape(R.H, R.W, 3)
    sc = next((s for s in scenes if s.t0 <= t < s.t1), None)
    if sc is None:
        frame = R.zoomed(face, zoom.at(t)).astype(np.float32)
    else:
        frame = np.empty((R.H, R.W, 3), np.float32); sc.draw(frame, face, t)
    leaks.apply(frame, t); caps.draw(frame, t)
    Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(f"{od}/s_{t:07.2f}.jpg", quality=85)
print("ok")
