"""Measure AB Nasdaq's framing: face size over time (Haar face detector at 10 fps), cut points, and whether the
framing changes by cutting (jumps) or by animating (gradual)."""
import subprocess, json
import numpy as np, cv2

W, H, FPS = 960, 540, 10
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "src/abnasdaqvsl.mp4", "-vf", f"fps={FPS},scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
sizes, diffs, prev = [], [], None
while True:
    raw = p.stdout.read(W * H)
    if len(raw) < W * H:
        break
    f = np.frombuffer(raw, np.uint8).reshape(H, W)
    faces = cas.detectMultiScale(f, 1.1, 5, minSize=(60, 60))
    sizes.append(float(max(faces, key=lambda r: r[2])[2]) if len(faces) else np.nan)
    diffs.append(float(np.abs(f.astype(np.int16) - prev).mean()) if prev is not None else 0.0)
    prev = f.astype(np.int16)
json.dump({"size": sizes, "diff": diffs}, open("an/ab_framing.json", "w"))
print(len(sizes), "frames")
