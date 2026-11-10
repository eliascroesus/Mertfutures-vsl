"""Single frames of thank-you v2 for checking: python ty_stills2.py plan.json base.mp4 outdir t1 t2 ..."""
import json, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, "/home/user/work/scripts")
import ty_render as R
import ty_render2 as R2

plan = json.load(open(sys.argv[1])); base = sys.argv[2]; od = sys.argv[3]
if plan.get("anchor"):
    R.CX, R.CY = plan["anchor"]
zoom, sweeps = R.Zoom(plan["zoom"]), R2.Sweeps(plan["leaks"])
scenes = [R2.Scene(s) for s in plan["scenes"]]
caps = R.Captions(plan["captions"])
for ts in sys.argv[4:]:
    t = float(ts)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", base, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    face = np.frombuffer(raw, np.uint8).reshape(R.H, R.W, 3)
    frame = R2.compose(face, t, zoom, sweeps, scenes, caps)
    Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(f"{od}/s_{t:07.2f}.jpg", quality=85)
print("ok")
