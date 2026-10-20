"""Render-and-compare branch check, PUBLIC ep 11 frame 0, beige cup (the near-3-fold case that failed with 2 markers).
For each candidate spin branch: fit centre shift + small spin to the two front marker blobs, render the TEXTURED scan
(markers are baked into the texture) with the real camera, and compare with the image inside the cup region.
GT used only for the evaluation camera and the starting pose; branch scores are what an automatic verifier would use."""
import numpy as np, sys, cv2, json
from scipy.optimize import least_squares
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); sys.path.insert(0, W12 + '/c')
import real_ep11 as R, mc_spin as mc

im = R.frame(0); G = R.gt(0); rv, tv, _ = R.cam_from_gt(im, G); K, D = R.K, R.D
n = 'beige_cup'; g_, tex = mc.load(n); P, Col, Nrm = mc.sample(g_, tex, 400000, seed=11)
up = np.array(mc.AX[n]['gt_up']); up /= np.linalg.norm(up); R0 = mc.Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix(); c0 = P.mean(0)
Pu = (P - c0) @ R0.T; Mu = (mc.good_markers(n) - c0) @ R0.T
C, th, gt_tilt = R.upright_gauge(n, G[n], (c0, R0))
front = np.array([[1260, 1059], [1479, 986]], float)          # the two detected front blobs (true markers)

def world(Q, phi, d):
    return C + mc.pose_pts(Q, th + phi, d, gt_tilt)

def proj(X):
    return cv2.projectPoints(np.ascontiguousarray(X, float), rv, tv, K, D)[0].reshape(-1, 2)

def fit_branch(phi0):
    def res(q):
        uv = proj(world(Mu, phi0 + q[0], q[1:4])); d = np.linalg.norm(uv[:, None] - front[None], axis=-1)
        return np.r_[d.min(0) / 1.5, q[1:4] / 0.005]
    return least_squares(res, np.zeros(4), loss='soft_l1', f_scale=3).x

def render(phi, d, psize=3):
    X = world(Pu, phi, d); uv = proj(X); Rc = cv2.Rodrigues(rv)[0]; z = (X @ Rc.T + tv.ravel())[:, 2]
    H, W = im.shape[:2]; zb = np.full((H, W), np.inf); img = np.zeros((H, W, 3), np.float32)
    ui, vi = uv[:, 0].astype(int), uv[:, 1].astype(int); cc = Col[:, ::-1]
    offs = [(dx - psize // 2, dy - psize // 2) for dx in range(psize) for dy in range(psize)]
    for dx, dy in offs:
        x, y = np.clip(ui + dx, 0, W - 1), np.clip(vi + dy, 0, H - 1); np.minimum.at(zb, (y, x), z)
    for dx, dy in offs:
        x, y = np.clip(ui + dx, 0, W - 1), np.clip(vi + dy, 0, H - 1); win = z <= zb[y, x] + 1e-6; img[y[win], x[win]] = cc[win]
    return img, np.isfinite(zb)

branches = {}
for phi0 in np.radians([0, -120, 120, -131, 113]):
    q = fit_branch(phi0); phi = phi0 + q[0]
    uvm = proj(world(Mu, phi, q[1:4]))
    branches[round(float(np.degrees(phi0)))] = (phi, q[1:4], uvm)
masks = []; renders = {}
for k, (phi, d, uvm) in branches.items():
    img, m = render(phi, d); renders[k] = img; masks.append(m)
M = np.any(masks, 0); M = cv2.dilate(M.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
obs = im.astype(np.float32) / 255.
def lum(x): return cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)
def hp(x): y = lum(x); y = y - cv2.GaussianBlur(y, (0, 0), 6); return y / (np.sqrt(cv2.GaussianBlur(y * y, (0, 0), 6)) + 0.02)
def gm(x): y = cv2.GaussianBlur(lum(x), (0, 0), 1.5); return np.hypot(cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1))
def nccm(a, b, m):
    a, b = a[m].ravel(), b[m].ravel(); a, b = a - a.mean(), b - b.mean(); return float(a @ b / np.sqrt((a @ a) * (b @ b) + 1e-12))
U = np.zeros(M.shape, np.uint8)
for k, (phi, d, uvm) in branches.items():
    for u in uvm: cv2.circle(U, (int(u[0]), int(u[1])), 24, 1, -1)
U = U > 0
out = {}
for k, img in renders.items():
    phi, d, uvm = branches[k]
    inside = M & (img.sum(-1) > 0)
    ncc = nccm(hp(obs), hp(img), inside); gncc = nccm(gm(obs), gm(img), inside)
    l1 = float(np.abs(obs[inside] - img[inside]).mean())
    uz = U & M     # union of all branches' marker disks: sphere present where predicted, absent where not
    ug, uh = nccm(gm(obs), gm(img), uz), nccm(hp(obs), hp(img), uz)
    print('   union-of-marker-disks: grad NCC %.3f, lum-hp NCC %.3f (%d px)' % (ug, uh, uz.sum()))
    loc = []
    for u in uvm:     # gradient NCC in a 22 px disk around each predicted marker (sphere outline + mount)
        mm = np.zeros(inside.shape, np.uint8); cv2.circle(mm, (int(u[0]), int(u[1])), 22, 1, -1); mm = (mm > 0) & inside
        loc.append(nccm(gm(obs), gm(img), mm) if mm.sum() > 50 else float('nan'))
    out[k] = dict(phi_deg=float(np.degrees(phi)), shift_mm=(np.asarray(d) * 1000).round(1).tolist(), hp_ncc=ncc, grad_ncc=gncc, union_grad_ncc=ug, union_hp_ncc=uh, l1=l1, marker_disk_grad_ncc=loc)
    print('branch %+4d -> spin %+7.1f deg, shift %s mm | lum-hp NCC %.3f | grad NCC %.3f | marker-disk grad NCC %s' % (
        k, np.degrees(phi), np.round(np.asarray(d) * 1000, 1), ncc, gncc, np.round(loc, 3)))
json.dump(out, open(f'{W12}/c/out/rc_branch_ep11_f000.json', 'w'), indent=1)
ys, xs = np.where(M); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
row = [im[y0:y1, x0:x1]] + [(np.clip(renders[k][y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8) for k in renders]
cv2.imwrite(f'{W12}/c/out/rc_branch_ep11_f000.png', np.hstack(row))
