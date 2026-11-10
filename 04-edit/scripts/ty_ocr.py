"""OCR every on-screen text in a video at a fixed rate (captions + card text), with box and text brightness.

    python ty_ocr.py video.mp4 fps out.jsonl [t0 t1]
"""
import sys, subprocess, json
import numpy as np
from rapidocr_onnxruntime import RapidOCR

src, fps, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0
t1 = float(sys.argv[5]) if len(sys.argv) > 5 else None
W, H = 1280, 720
cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(t0)] + (["-to", str(t1)] if t1 else []) + \
      ["-i", src, "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
eng = RapidOCR()
fo = open(out, "w")
k = 0
while True:
    raw = p.stdout.read(W * H * 3)
    if len(raw) < W * H * 3:
        break
    f = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
    res, _ = eng(f[:, :, ::-1].copy())
    items = []
    for box, txt, conf in res or []:
        b = np.array(box)
        x0, y0, x1, y1 = int(b[:, 0].min()), int(b[:, 1].min()), int(b[:, 0].max()), int(b[:, 1].max())
        crop = f[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3).astype(int)
        lum = crop.mean(1)
        top = np.sort(lum)[-max(1, len(lum) // 10):].mean() if len(lum) else 0
        items.append({"txt": txt, "conf": round(float(conf), 2), "box": [x0, y0, x1, y1], "bright": round(float(top), 1)})
    fo.write(json.dumps({"t": round(t0 + k / fps, 3), "items": items}) + "\n")
    fo.flush()
    k += 1
print("frames", k)
