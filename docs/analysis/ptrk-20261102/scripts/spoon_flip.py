"""PREREG_spoonflip.md: per frame, the packed reference spoon pose vs its 180-degree ROLL (about the long axis) and YAW
(about the face normal) alternatives, scored on the SAM2 spoon mask (IoU) and stereo depth (median residual).
GT-free (eval). Usage: python -I spoon_flip.py EP REF TABLE POSES DEPTH VOS KSRC MESH_DIR OUT_DIR [--hands H]"""
import argparse, json, os, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser()
for k in ('ep', 'ref', 'table', 'perc', 'depth', 'vos', 'ksrc', 'meshes', 'out'):
    p.add_argument(k)
p.add_argument('--hands', default=None)
a = p.parse_args(); EP = int(a.ep); os.makedirs(a.out, exist_ok=True)
t = pq.read_table(a.ref).to_pandas(); on = t['object_name'].iloc[0]; names = on.split('__') if isinstance(on, str) else list(on)
b = names.index('wooden_spoon')
pos = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_position'].iloc[0]])[:, b]
qq = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_wxyz'].iloc[0]])[:, b]
iT = np.linalg.inv(np.load(a.table)['T_table_from_world']); W = np.asarray(np.load(a.perc)['world_T_cam'], float)
K = np.load(a.ksrc)['K'].astype(float); D = np.load(a.depth, mmap_mode='r'); V = np.load(a.vos)
N = min(len(pos), len(W), len(D)); H4, W4 = 250, 400; sc = D.shape[2] / W4; Kq = K.copy(); Kq[:2] /= sc
m = trimesh.load(f'{a.meshes}/wooden_spoon.glb', force='mesh'); pts = np.asarray(trimesh.sample.sample_surface(m, 800, seed=0)[0])
c = m.bounds.mean(0); w, U = np.linalg.eigh(np.cov(np.asarray(m.vertices).T)); L, Nn = U[:, 2], U[:, 0]

def flip(axis):
    R = Rot.from_rotvec(np.pi * axis).as_matrix(); M = np.eye(4); M[:3, :3] = R; M[:3, 3] = c - R @ c; return M
ALT = {'REF': np.eye(4), 'ROLL': flip(L), 'YAW': flip(Nn)}
mask = np.unpackbits(V['wooden_spoon'], axis=-1)[:, :, :W4].astype(bool)
hand = None
if a.hands and os.path.exists(a.hands):
    Hh = np.load(a.hands); hand = [np.asarray(Hh[k], float) for k in Hh.files if k.startswith('joints_')]

def hmask(i):
    hm = np.zeros((H4, W4), np.uint8)
    for J in (hand or []):
        if i >= len(J): continue
        Xc = (J[i] - W[i][:3, 3]) @ W[i][:3, :3]
        for x in Xc:
            if np.isfinite(x).all() and x[2] > 0.05:
                u, v = (Kq @ x)[:2] / x[2]; cv2.circle(hm, (int(u), int(v)), max(2, int(0.02 * Kq[0, 0] / x[2])), 1, -1)
    return hm > 0

def sil(X):
    v = np.asarray(m.vertices) @ X[:3, :3].T + X[:3, 3]; ok = v[:, 2] > 0.05
    uv = v @ Kq.T; uv = uv[:, :2] / np.maximum(uv[:, 2:3], 1e-6)
    img = np.zeros((H4, W4), np.uint8); F = np.asarray(m.faces); F = F[ok[F].all(1)]
    cv2.fillPoly(img, [np.round(uv[f]).astype(np.int32) for f in F], 1); return img > 0

S = {k: dict(iou=np.full(N, np.nan), res=np.full(N, np.nan)) for k in ALT}
for i in range(N):
    hm = hmask(i); mk = mask[i] & ~hm if i < len(mask) else None
    if mk is None or mk.sum() < 150: continue
    M = np.eye(4); M[:3, :3] = Rot.from_quat(np.r_[qq[i, 1:4], qq[i, 0]]).as_matrix(); M[:3, 3] = pos[i]
    X0 = np.linalg.inv(W[i]) @ iT @ M; dep = np.asarray(D[i])
    for k, F_ in ALT.items():
        X = X0 @ F_; s = sil(X) & ~hm; u = (s | mk).sum(); S[k]['iou'][i] = (s & mk).sum() / u if u else np.nan
        Pc = pts @ X[:3, :3].T + X[:3, 3]; uv = Pc @ K.T; uv = uv[:, :2] / np.maximum(uv[:, 2:3], 1e-6)
        inb = (uv[:, 0] >= 0) & (uv[:, 0] < D.shape[2]) & (uv[:, 1] >= 0) & (uv[:, 1] < D.shape[1]) & (Pc[:, 2] > 0.05)
        zo = np.zeros(len(Pc)); zo[inb] = dep[uv[inb, 1].astype(int), uv[inb, 0].astype(int)]
        vis = inb & (zo > 0) & (zo > Pc[:, 2] - 0.02)
        if vis.sum() >= 20: S[k]['res'][i] = float(np.median(np.abs(zo[vis] - Pc[vis, 2]))) * 100
out = dict(episode=EP, frames=N, scored=int(np.isfinite(S['REF']['iou']).sum()), spans={}, stats={})
for k in ('ROLL', 'YAW'):
    ir, ia, rr, ra = S['REF']['iou'], S[k]['iou'], S['REF']['res'], S[k]['res']
    with np.errstate(invalid='ignore'):
        win = ((ia >= ir + 0.10) & (ra <= rr + 0.3)) | ((ra <= rr - 0.5) & (ia >= ir - 0.05))
    win = np.nan_to_num(win, nan=0).astype(bool)
    idx = np.nonzero(win)[0]; spans = []
    if len(idx):
        s0 = p0 = idx[0]
        for j in idx[1:]:
            if j - p0 <= 3: p0 = j; continue
            if p0 - s0 + 1 >= 5: spans.append([int(s0), int(p0)])
            s0 = p0 = j
        if p0 - s0 + 1 >= 5: spans.append([int(s0), int(p0)])
    out['spans'][k] = spans
    out['stats'][k] = dict(win_frames=int(win.sum()), median_dIoU=round(float(np.nanmedian(ia - ir)), 3) if np.isfinite(ia - ir).any() else None,
                           median_dRes=round(float(np.nanmedian(ra - rr)), 3) if np.isfinite(ra - rr).any() else None)
out['stats']['REF'] = dict(iou_median=round(float(np.nanmedian(S['REF']['iou'])), 3) if np.isfinite(S['REF']['iou']).any() else None,
                           res_median=round(float(np.nanmedian(S['REF']['res'])), 2) if np.isfinite(S['REF']['res']).any() else None)
np.savez_compressed(f'{a.out}/spoonflip_ep{EP}.npz', **{f'{k}_{q}': S[k][q] for k in S for q in S[k]})
json.dump(out, open(f'{a.out}/spoonflip_ep{EP}.json', 'w'), indent=1)
print(EP, json.dumps(out))
