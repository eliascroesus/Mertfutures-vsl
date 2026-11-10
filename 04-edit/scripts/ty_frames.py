"""Per-frame stats for the AB thank-you reference: what kind of frame it is (face cam / green card / red card / white
flash), the frame-to-frame change (cuts, light leaks), and the face size (punch-ins).

    python ty_frames.py video.mp4 out.json
"""
import sys, subprocess, json
import numpy as np, cv2

src, out = sys.argv[1], sys.argv[2]
W, H = 640, 360
p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vf", f"scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
rows, prev, i = [], None, 0
while True:
    raw = p.stdout.read(W * H * 3)
    if len(raw) < W * H * 3:
        break
    f = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
    g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
    r, gg, b = (float(f[..., k].astype(np.float32).mean()) for k in range(3))
    sat = hsv[..., 1].astype(np.float32)
    hue = hsv[..., 0][sat > 80]
    green = float(np.mean((hue > 35) & (hue < 85))) if hue.size > 500 else 0.0
    red = float(np.mean((hue < 8) | (hue > 170))) if hue.size > 500 else 0.0
    row = {"t": i * 1001 / 30000, "lum": float(g.mean()), "rgb": [r, gg, b], "satpx": float(np.mean(sat > 80)),
           "green": green, "red": red, "white": float(np.mean(g > 235)),
           "diff": float(np.abs(g.astype(np.int16) - prev).mean()) if prev is not None else 0.0}
    if i % 3 == 0:  # face size at ~10 fps
        faces = cas.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
        if len(faces):
            x, y, w, h = max(faces, key=lambda q: q[2])
            row["face"] = [int(x), int(y), int(w)]
    rows.append(row)
    prev = g.astype(np.int16)
    i += 1
json.dump(rows, open(out, "w"))
print(i, "frames")
