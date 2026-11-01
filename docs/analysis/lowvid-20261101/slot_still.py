"""Still: each eval-25 board, visual mesh (library_v3) vs the simulator's carved collision pieces (meshes/carve/ev25),
seen face-on (looking along the board's thin axis) so the carved slot shows as a gap. Usage: slot_still.py OUT.jpg"""
import glob, sys, numpy as np, trimesh, cv2
L, C = '/home/user/v2d-track3/meshes/library_v3', '/home/user/v2d-track3/meshes/carve/ev25'
W = H = 520; light = np.array([0.3, -0.4, 0.85]); light /= np.linalg.norm(light)
def render(parts, view, title, base):
    img = np.full((H, W, 3), (40, 34, 30), np.uint8); allv = np.concatenate([v for v, f in parts])
    c = allv.mean(0); ext = np.ptp(allv, 0).max(); s = 0.8 * W / ext
    Rv = view; prims = []
    for i, (v, f) in enumerate(parts):
        X = (v - c) @ Rv.T; uv = np.c_[X[:, 0] * s + W / 2, -X[:, 1] * s + H / 2]; T = X[f]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        sh = (0.35 + 0.65 * np.abs(n @ light)) * (0.7 + 0.3 * ((i * 0.618) % 1.0) if len(parts) > 1 else 1.0)
        for k in range(len(f)):
            prims.append((X[f[k], 2].mean(), uv[f[k]].astype(np.int32), tuple(int(x) for x in np.array(base) * sh[k])))
    for _, p, col in sorted(prims, key=lambda r: r[0]):
        cv2.fillConvexPoly(img, p, col, cv2.LINE_AA)
    cv2.putText(img, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1, cv2.LINE_AA); return img
def rot(thin):  # look along the thin axis (the board's thickness), slightly oblique
    z = np.eye(3)[thin]; up = np.eye(3)[2] if thin != 2 else np.eye(3)[1]
    R0 = np.stack([np.cross(up, z), up, z]); a = np.radians(25)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]]); return Ry @ R0
rows = []
for n, col in (('wooden_piece_1', (60, 170, 255)), ('wooden_piece_2', (220, 120, 40))):
    vm = trimesh.load(f'{L}/{n}.glb', force='mesh'); thin = int(np.argmin(np.ptp(vm.vertices, 0))); Rv = rot(thin)
    P = [trimesh.load(fp, force='mesh') for fp in sorted(glob.glob(f'{C}/{n}/*.obj'))]
    rows.append(np.hstack([render([(np.asarray(vm.vertices), np.asarray(vm.faces))], Rv, f'{n}: visual mesh we submit (no slot)', col),
                           render([(np.asarray(p.vertices), np.asarray(p.faces)) for p in P], Rv, f'{n}: simulator collision pieces ({len(P)})', col)]))
cv2.imwrite(sys.argv[1], np.vstack(rows)); print('wrote', sys.argv[1])
