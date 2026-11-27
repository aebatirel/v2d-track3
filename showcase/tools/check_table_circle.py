import sys, json, numpy as np, cv2
S = sys.argv[1]; r = float(sys.argv[2]); cx, cy = [float(v) for v in sys.argv[3].split(',')]; frames = [int(x) for x in sys.argv[4].split(',')]
h = np.load(f'{S}/ep27/ref_vc/hands.npz'); K, D, T_a2rect = h['Ka'], h['Da'], h['T_rect_a'].astype(float)
Tt = np.load(f'{S}/ep27/ref_vc/table_frame.npz')['T_table_from_world']; WC = np.load(f'{S}/ep27/perc2/poses.npz')['world_T_cam'].astype(float)
cap = cv2.VideoCapture('/content/t3/videos/ep27_a.mp4'); imgs = {}; i = 0
while True:
    ok, im = cap.read()
    if not ok: break
    if i in frames: imgs[i] = im
    i += 1
th = np.linspace(0, 2 * np.pi, 400); out = []
for f in frames:
    im = imgs[f].copy()
    for rr, col in ((r, (0, 255, 0)), (0.45, (0, 0, 255))):
        X = np.c_[cx + rr * np.cos(th), cy + rr * np.sin(th), np.full_like(th, 0.60), np.ones_like(th)]
        Xa = (np.linalg.inv(Tt @ WC[f] @ T_a2rect) @ X.T).T[:, :3]; ok = Xa[:, 2] > 0.05
        uv, _ = cv2.projectPoints(Xa[ok].reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K, D)
        cv2.polylines(im, [uv.reshape(-1, 2).astype(np.int32)], False, col, 5)
    out.append(cv2.resize(im, (1014, 760)))
cv2.imwrite(f'{S}/table/circle_check.jpg', np.concatenate(out, 1))
