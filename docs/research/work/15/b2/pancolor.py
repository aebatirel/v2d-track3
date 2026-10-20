"""Yellow-green dustpan mask per frame (HSV threshold at 1/4 res): area fraction and border contact.
usage: pancolor.py tag video ; prints summary, saves pan_<tag>.npz"""
import sys, cv2, numpy as np
tag, vid = sys.argv[1:3]; cap = cv2.VideoCapture(vid); A = []; B = []
while True:
    ok, fr = cap.read()
    if not ok: break
    h = cv2.cvtColor(cv2.resize(fr, (507, 380), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV)
    m = cv2.inRange(h, (28, 120, 90), (45, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n_, lab, st, _ = cv2.connectedComponentsWithStats(m); k_ = 1 + np.argmax(st[1:, 4]) if n_ > 1 else 0
    m = (lab == k_) if k_ else np.zeros(m.shape, bool)  # largest blob only (drops hazard-tape stripes)
    A.append(m.mean()); B.append(int(m[:2].sum() + m[-2:].sum() + m[:, :2].sum() + m[:, -2:].sum()))
A = np.array(A); B = np.array(B); np.savez(f'pan_{tag}.npz', area=A, border=B)
med = np.median(A); low = np.where(A < 0.3 * med)[0]; bor = np.where(B > 5)[0]
rng = lambda ix: (f"{len(ix)} f" + (f" in f{ix.min()}-{ix.max()}" if len(ix) else ""))
print(f"{tag} n={len(A)} area_med={med*100:.2f}% area_min={A.min()*100:.2f}% (f{A.argmin()}) "
      f"area<0.3med: {rng(low)}; border-touch: {rng(bor)}")
