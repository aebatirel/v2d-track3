"""Shaded multi-view renders of a mesh (CPU, numpy z-buffer splatting of dense surface samples, Lambert shading).
Views: three orthographic directions along the mesh's PCA axes (largest-spread axis vertical) plus one oblique.
Usage: render_views.py MESH.glb OUT.png [title]"""
import sys, numpy as np, trimesh, cv2
m = trimesh.load(sys.argv[1], force='mesh'); title = sys.argv[3] if len(sys.argv) > 3 else ''
P, fi = trimesh.sample.sample_surface(m, 400000, seed=0); N = m.face_normals[fi]
c = P.mean(0); X = P - c; w, V = np.linalg.eigh(np.cov(X.T)); V = V[:, ::-1]
X = X @ V; N = N @ V                                          # PCA frame: x = largest spread
def rot(ax, deg):
    t = np.radians(deg); c_, s_ = np.cos(t), np.sin(t)
    return {'x': np.array([[1, 0, 0], [0, c_, -s_], [0, s_, c_]]), 'y': np.array([[c_, 0, s_], [0, 1, 0], [-s_, 0, c_]]),
            'z': np.array([[c_, -s_, 0], [s_, c_, 0], [0, 0, 1]])}[ax]
base = rot('z', 90)                                           # largest spread vertical
views = [('front', base), ('side', rot('y', 90) @ base), ('top', rot('x', 90) @ base), ('oblique', rot('x', 30) @ rot('y', 35) @ base)]
S = 360; scale = 0.9 * S / (2 * np.abs(X).max()); tiles = []
light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
for name, Rv in views:
    Q = X @ Rv.T; Nq = N @ Rv.T
    u = (S / 2 + Q[:, 0] * scale).astype(int); v = (S / 2 - Q[:, 1] * scale).astype(int); z = Q[:, 2]
    ok = (u >= 0) & (u < S) & (v >= 0) & (v < S)
    zb = np.full(S * S, -np.inf); col = np.zeros(S * S)
    lin = v[ok] * S + u[ok]; zz = z[ok]; sh = 0.25 + 0.75 * np.abs(Nq[ok] @ light)   # two-sided shading
    order = np.argsort(zz); lin, zz, sh = lin[order], zz[order], sh[order]
    zb[lin] = zz; col[lin] = sh                                   # nearest (largest z) written last wins
    img = np.full((S, S, 3), 245, np.uint8); hit = np.isfinite(zb).reshape(S, S)
    g = (col.reshape(S, S) * 255).astype(np.uint8)
    img[hit] = np.stack([g[hit] * 0.75, g[hit] * 0.82, g[hit]], 1).astype(np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cv2.putText(img, name, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1)
    tiles.append(img)
out = np.hstack(tiles)
if title:
    bar = np.full((26, out.shape[1], 3), 255, np.uint8); cv2.putText(bar, title, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    out = np.vstack([bar, out])
cv2.imwrite(sys.argv[2], out)
