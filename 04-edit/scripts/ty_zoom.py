"""Exact zoom curve of a talking-head edit: frame-to-frame similarity transform (ORB + RANSAC) on the whole picture,
chained into a cumulative scale; resets where matching fails (cuts to graphics, flashes).

    python ty_zoom.py video.mp4 out.json
"""
import sys, subprocess, json
import numpy as np, cv2

src, out = sys.argv[1], sys.argv[2]
W, H = 640, 360
p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                      "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
orb = cv2.ORB_create(1500)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
prev, rows, i = None, [], 0
while True:
    raw = p.stdout.read(W * H)
    if len(raw) < W * H:
        break
    g = np.frombuffer(raw, np.uint8).reshape(H, W)
    kp, de = orb.detectAndCompute(g, None)
    row = {"t": round(i * 1001 / 30000, 4), "s": None}
    if prev is not None and de is not None and prev[1] is not None and len(kp) > 50:
        m = bf.match(prev[1], de)
        if len(m) > 40:
            a = np.float32([prev[0][x.queryIdx].pt for x in m]); b = np.float32([kp[x.trainIdx].pt for x in m])
            M, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=2.0)
            if M is not None and inl is not None and inl.sum() > 30:
                s = float(np.hypot(M[0, 0], M[1, 0]))
                row.update(s=s, tx=float(M[0, 2]), ty=float(M[1, 2]), inl=int(inl.sum()))
    rows.append(row)
    prev = (kp, de)
    i += 1
json.dump(rows, open(out, "w"))
print(i, "frames")
