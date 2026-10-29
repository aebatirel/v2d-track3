"""DIAGNOSTIC scorer for frame-k object detection on PUBLIC episodes (reads mocap ground truth: never part of inference;
2026-10-23). Scores which SAM2 proposal each object was given (perc2 det_f<k>.npz dumps, or a choice file from
tools/det_replay.py) against reference label maps: the public scans at the mocap pose, rendered into perc2's
rectified-left camera at the dumps' half resolution.

Mocap world -> perception world: one rigid Kabsch fit per episode over all frames and objects (origin + 10 cm axis
points, two 90 % trimmed refits) between mocap and our own tracked poses (perc2 poses.npz: world_T_cam, cam_T_<obj>),
as in the VLM CPU study (scratchpad vlm/cpu-feasibility/scripts/prep.py). Its residual is the reference's error bound;
episodes above --max_resid_cm (default 2) are skipped.
A chosen proposal is a hit for object n when >= 50 % of its pixels carry n's label (purity); "good" also needs it to
cover >= 50 % of n's visible pixels. Hands are not modelled (a hand over an object lowers coverage, not purity).

Usage: det_score.py labels --t3 T3 --perc PERC --eps 2,12,... --frames 0,90 --out LABDIR
       det_score.py score LABDIR DUMPROOT [CHOICES.json]   (DUMPROOT/ep<N>/det_f<k>.npz; without CHOICES the dumps'
                                                           own 'chosen' is scored)
"""
import argparse, json, os, sys
import numpy as np, cv2, trimesh
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot


def T_of(p):  # [x, y, z, qw, qx, qy, qz] -> 4x4
    T = np.eye(4); T[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); T[:3, 3] = p[:3]; return T


def kabsch(A, B):  # G with B ~ G A
    ca, cb = A.mean(0), B.mean(0); U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    d = np.sign(np.linalg.det(Vt.T @ U.T)); R = Vt.T @ np.diag([1, 1, d]) @ U.T
    G = np.eye(4); G[:3, :3] = R; G[:3, 3] = cb - R @ ca; return G


def rect_K(t3):
    """perc2's rectified-left intrinsics (same stereoRectify call) at full resolution 1600 x 1000."""
    C = json.load(open(f'{t3}/calib.json')); cam = C['cameras']
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]; E = np.array(sp['left_to_right'], float)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800),
                                                E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0,
                                                newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    return P1[:3, :3].copy(), (R1, P1, K_('ego_cam_c'), D_('ego_cam_c'))


def raster(objs, K, size):
    """objs: [(label, V_cam, F)]; painter's algorithm (far faces first), pinhole K, no distortion. Label image."""
    W, H = size; lab = np.zeros((H, W), np.int32); L, P, Z = [], [], []
    for li, V, F in objs:
        z = V[:, 2]; ok = z > 0.02; Fk = F[ok[F].all(1)]
        uv = (V @ K.T)[:, :2] / np.maximum(z, 1e-6)[:, None]
        L.append(np.full(len(Fk), li)); P.append(uv[Fk]); Z.append(z[Fk].mean(1))
    L, P, Z = np.concatenate(L), np.concatenate(P), np.concatenate(Z)
    P = np.round(P * 4).astype(np.int64)
    for k in np.argsort(-Z):
        if (np.abs(P[k]) > 4 * 20000).any(): continue
        cv2.fillConvexPoly(lab, P[k].reshape(-1, 1, 2).astype(np.int32), int(L[k]), lineType=cv2.LINE_8, shift=2)
    return lab


def scan(t3, n):
    p = f'{t3}/mesh/{n}/{n}.glb'
    p = p if os.path.exists(p) else f'{t3}/mesh/{n}/{n}_visual.glb'
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, float), np.asarray(m.faces)


def labels(a):
    K, _ = rect_K(a.t3); Kh = K.copy(); Kh[:2] *= 0.5                     # half resolution (800 x 500), as the dumps
    os.makedirs(a.out, exist_ok=True); meta = {}
    for ep in [int(x) for x in a.eps.split(',')]:
        P = np.load(f'{a.perc}/ep{ep}/poses.npz'); W_C = P['world_T_cam'].astype(float); N = len(W_C)
        tab = pq.read_table(f'{a.t3}/ep{ep}.parquet').to_pandas()
        names = [o['name'] for o in tab['observation.objects'].iloc[0]]
        gt = {n: np.stack([T_of(np.array([o for o in row if o['name'] == n][0]['pose'], float))
                           for row in tab['observation.objects'].iloc[:N]]) for n in names}
        A, B = [], []
        for n in names:
            PW = np.einsum('tij,tjk->tik', W_C, P[f'cam_T_{n}'].astype(float))
            for T_m, T_p in zip(gt[n], PW):
                for v in [np.zeros(3), *0.1 * np.eye(3)]:
                    A.append(T_m[:3, :3] @ v + T_m[:3, 3]); B.append(T_p[:3, :3] @ v + T_p[:3, 3])
        A, B = np.array(A), np.array(B); G = kabsch(A, B)
        for _ in range(2):
            r = np.linalg.norm((A @ G[:3, :3].T + G[:3, 3]) - B, axis=1); G = kabsch(A[r <= np.quantile(r, 0.9)], B[r <= np.quantile(r, 0.9)])
        r = np.linalg.norm((A @ G[:3, :3].T + G[:3, 3]) - B, axis=1)
        meta[ep] = dict(names=names, fit_resid_cm_median=round(float(np.median(r) * 100), 2),
                        fit_resid_cm_p90=round(float(np.quantile(r, 0.9) * 100), 2), frames=[])
        meshes = {n: scan(a.t3, n) for n in names}
        for k in [int(x) for x in a.frames.split(',')]:
            k = min(k, N - 1); objs = []
            for li, n in enumerate(names, 1):
                V, F = meshes[n]; T = np.linalg.inv(W_C[k]) @ G @ gt[n][k]
                objs.append((li, V @ T[:3, :3].T + T[:3, 3], F))
            np.save(f'{a.out}/ep{ep}_f{k}_lab.npy', raster(objs, Kh, (800, 500)).astype(np.uint8))
            meta[ep]['frames'].append(k)
        print(ep, meta[ep], flush=True)
    json.dump(meta, open(f'{a.out}/labels_meta.json', 'w'), indent=1)


def unpack(d):
    shp = tuple(d['mask_shape']); return np.unpackbits(d['masks'], axis=-1)[..., :shp[2]].astype(bool)


def score(labdir, dumproot, choices=None, max_resid=2.0, quiet=False):
    meta = json.load(open(f'{labdir}/labels_meta.json')); ch = json.load(open(choices)) if choices else {}
    rows = []
    for ep, m in meta.items():
        if m['fit_resid_cm_median'] > max_resid: continue
        for k in m['frames']:
            f = f'{dumproot}/ep{ep}/det_f{k}.npz'; lf = f'{labdir}/ep{ep}_f{k}_lab.npy'
            if not (os.path.exists(f) and os.path.exists(lf)): continue
            d = np.load(f); lab = np.load(lf); masks = unpack(d); names = [str(x) for x in d['names']]
            chosen = ch.get(f'ep{ep}_f{k}', d['chosen'].tolist())
            for li, n in enumerate(names, 1):
                vis = int((lab == li).sum()); j = int(chosen[li - 1])
                if vis < 50 or j < 0:
                    rows.append(dict(ep=int(ep), frame=k, obj=n, visible=vis, chosen=j, hit=None, good=None)); continue
                pm = masks[j]; inter = int((pm & (lab == li)).sum())
                purity = inter / max(int(pm.sum()), 1); cover = inter / vis
                top = np.bincount(lab[pm], minlength=len(names) + 1); top[0] = 0
                rows.append(dict(ep=int(ep), frame=k, obj=n, visible=vis, chosen=j, purity=round(purity, 3), cover=round(cover, 3),
                                 hit=purity >= 0.5, good=purity >= 0.5 and cover >= 0.5,
                                 on=names[int(top.argmax()) - 1] if top.max() > 0 else 'background'))
    ok = [r for r in rows if r['hit'] is not None]
    summ = dict(instances=len(ok), hits=sum(r['hit'] for r in ok), good=sum(r['good'] for r in ok),
                misses=[f"ep{r['ep']} f{r['frame']} {r['obj']} -> {r['on']} (purity {r['purity']})" for r in ok if not r['hit']])
    if not quiet:
        print(json.dumps(summ, indent=1))
    return summ, rows


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'labels':
        p = argparse.ArgumentParser(); p.add_argument('cmd'); p.add_argument('--t3', required=True); p.add_argument('--perc', required=True)
        p.add_argument('--eps', required=True); p.add_argument('--frames', default='0'); p.add_argument('--out', required=True)
        labels(p.parse_args())
    elif len(sys.argv) > 2 and sys.argv[1] == 'score':
        score(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        sys.exit(__doc__)
