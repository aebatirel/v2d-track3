"""Eval gross-failure audit (PREREG_round3_audit.md, part 2). GT-free: no ground truth exists for eval episodes.
For one eval episode: the PACKED reference's object poses (table frame) are mapped to the camera frame of the perception
run they came from (inv(world_T_cam) . inv(T_table)), rendered with our library_v3 templates, and compared per frame
with our SAM2 video masks and stereo depth. Flags LOST / SWAP / BELOW / FLIP / WRIST spans by the pre-registered
thresholds and writes a JSON summary plus overlay images of the worst frames.
Usage: python -I eval_audit.py EP REF_PARQUET TABLE_FRAME_NPZ PERC_POSES_NPZ DEPTH_NPY VOS_MASKS_NPZ KSRC_NPZ
       MESH_DIR OUT_DIR [--hands HANDS_NPZ] [--video EP_C_MP4 --calib CALIB_JSON]"""
import argparse, json, os, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser()
for k in ('ep', 'ref', 'table', 'perc', 'depth', 'vos', 'ksrc', 'meshes', 'out'):
    p.add_argument(k)
p.add_argument('--hands', default=None)
a = p.parse_args(); EP = int(a.ep); os.makedirs(a.out, exist_ok=True)

t = pq.read_table(a.ref).to_pandas()
names = [str(x) for x in (t['object_name'].iloc[0].split('__') if isinstance(t['object_name'].iloc[0], str) else t['object_name'].iloc[0])]
pos = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_position'].iloc[0]])
qq = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_wxyz'].iloc[0]])
TF = np.load(a.table); iT = np.linalg.inv(TF['T_table_from_world']); n_pl, d_pl = TF['plane_n'], float(TF['plane_d'])
W = np.asarray(np.load(a.perc)['world_T_cam'], float)
K = np.load(a.ksrc)['K'].astype(float)
D = np.load(a.depth, mmap_mode='r'); V = np.load(a.vos)
N = min(len(pos), len(W), len(D))
H4, W4 = 250, 400; sc = D.shape[2] / W4
Kq = K.copy(); Kq[:2] /= sc

def M4(R, t_):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t_; return M

objs = {}
for b, n in enumerate(names):
    m = trimesh.load(f'{a.meshes}/{n}.glb', force='mesh')
    R = Rot.from_quat(np.c_[qq[:N, b, 1:4], qq[:N, b, 0]]).as_matrix()
    Ow = np.einsum('ij,tjk->tik', iT, np.stack([M4(R[i], pos[i, b]) for i in range(N)]))
    Oc = np.einsum('tij,tjk->tik', np.linalg.inv(W[:N]), Ow)
    objs[n] = dict(mesh=m, pts=np.asarray(trimesh.sample.sample_surface(m, 600, seed=0)[0]), Ow=Ow, Oc=Oc,
                   mask=np.unpackbits(V[n], axis=-1)[:, :, :W4].astype(bool) if n in V.files else None)
hand = None
if a.hands and os.path.exists(a.hands):
    Hh = np.load(a.hands); hand = [np.asarray(Hh[k], float) for k in Hh.files if k.startswith('joints_')]

def sil(m, X):
    v = np.asarray(m.vertices) @ X[:3, :3].T + X[:3, 3]; ok = v[:, 2] > 0.05
    uv = v @ Kq.T; uv = uv[:, :2] / np.maximum(uv[:, 2:3], 1e-6)
    img = np.zeros((H4, W4), np.uint8); F = np.asarray(m.faces); F = F[ok[F].all(1)]
    cv2.fillPoly(img, [np.round(uv[f]).astype(np.int32) for f in F], 1); return img > 0

def hand_mask(i):
    hm = np.zeros((H4, W4), np.uint8)
    if hand is None: return hm > 0
    for J in hand:
        if i >= len(J): continue
        Xc = (J[i] - W[i][:3, 3]) @ W[i][:3, :3]              # world -> camera
        for x in Xc:
            if not np.isfinite(x).all() or x[2] <= 0.05: continue
            u, v = (Kq @ x)[:2] / x[2]; cv2.circle(hm, (int(u), int(v)), max(2, int(0.02 * Kq[0, 0] / x[2])), 1, -1)
    return hm > 0

PF = {n: dict(iou=np.full(N, np.nan), other=np.zeros(N), resid=np.full(N, np.nan), low=np.zeros(N), vis=np.zeros(N),
              mpx=np.zeros(N), rotjump=np.zeros(N), wrist=np.full(N, np.inf)) for n in names}
for i in range(N):
    hm = hand_mask(i); dep = np.asarray(D[i]); S_ = {}
    for n, o in objs.items():
        X = o['Oc'][i]; s = sil(o['mesh'], X) & ~hm; S_[n] = s
        mk = o['mask'][i] & ~hm if o['mask'] is not None and i < len(o['mask']) else None
        if mk is not None:
            PF[n]['mpx'][i] = mk.sum(); u = (s | mk).sum()
            PF[n]['iou'][i] = (s & mk).sum() / u if u else np.nan
        Pc = o['pts'] @ X[:3, :3].T + X[:3, 3]
        uv = Pc @ K.T; uv = uv[:, :2] / np.maximum(uv[:, 2:3], 1e-6)
        inb = (uv[:, 0] >= 0) & (uv[:, 0] < D.shape[2]) & (uv[:, 1] >= 0) & (uv[:, 1] < D.shape[1]) & (Pc[:, 2] > 0.05)
        zo = np.zeros(len(Pc)); zo[inb] = dep[uv[inb, 1].astype(int), uv[inb, 0].astype(int)]
        vis = inb & (zo > 0) & (zo > Pc[:, 2] - 0.02)      # not occluded by something nearer than 2 cm
        PF[n]['vis'][i] = vis.mean()
        if vis.sum() >= 20: PF[n]['resid'][i] = float(np.median(np.abs(zo[vis] - Pc[vis, 2]))) * 100
        Pw = o['pts'] @ o['Ow'][i][:3, :3].T + o['Ow'][i][:3, 3]
        PF[n]['low'][i] = float(np.percentile(Pw @ n_pl + d_pl, 2)) * 100
        if i > 0:
            PF[n]['rotjump'][i] = np.degrees(Rot.from_matrix(o['Ow'][max(0, i - 3)][:3, :3].T @ o['Ow'][i][:3, :3]).magnitude())
        if hand is not None:
            ds = [np.linalg.norm(J[i][0] - o['Ow'][i][:3, 3]) for J in hand if i < len(J) and np.isfinite(J[i][0]).all()]
            if ds: PF[n]['wrist'][i] = min(ds) * 100
    for n in names:                                          # swap check: overlap with other objects' masks
        best = 0.0
        for m2 in names:
            if m2 == n or objs[m2]['mask'] is None or i >= len(objs[m2]['mask']): continue
            mk2 = objs[m2]['mask'][i] & ~hm; u = (S_[n] | mk2).sum()
            if u: best = max(best, (S_[n] & mk2).sum() / u)
        PF[n]['other'][i] = best

def spans(flag, minlen=5):
    out, s = [], None
    for i, v in enumerate(np.r_[flag, False]):
        if v and s is None: s = i
        if not v and s is not None:
            if i - s >= minlen: out.append([s, i - 1])
            s = None
    return out

res = dict(episode=EP, objects=names, frames=N, flags={}, stats={})
for n in names:
    f = PF[n]; iou = np.nan_to_num(f['iou'], nan=1.0); res_ = np.nan_to_num(f['resid'], nan=0.0)
    lost = ((iou < 0.2) & (f['mpx'] >= 300)) | (res_ > 3.0)
    swap = (f['other'] > np.nan_to_num(f['iou'], nan=0.0) + 0.3)
    below = f['low'] < -2.0
    flip = (f['rotjump'] > 60) & (iou < 0.5)
    wrist = (f['wrist'] < 2.0) & (iou < 0.2) if n == 'wooden_spoon' else np.zeros(N, bool)
    fl = {k: spans(v) for k, v in dict(LOST=lost, SWAP=swap, BELOW=below, FLIP=flip, WRIST=wrist).items()}
    fl = {k: v for k, v in fl.items() if v}
    res['flags'][n] = fl
    res['stats'][n] = dict(iou_median=round(float(np.nanmedian(f['iou'])), 3) if np.isfinite(f['iou']).any() else None,
                           resid_median_cm=round(float(np.nanmedian(f['resid'])), 2) if np.isfinite(f['resid']).any() else None,
                           low_min_cm=round(float(f['low'].min()), 2), vis_median=round(float(np.median(f['vis'])), 2),
                           flagged_frames=int(sum(e - s + 1 for v in fl.values() for s, e in v)))
res['severity'] = int(sum(s['flagged_frames'] for s in res['stats'].values()))
np.savez_compressed(f'{a.out}/audit_ep{EP}_pf.npz', **{f'{n}_{k}': v for n in names for k, v in PF[n].items()})
json.dump(res, open(f'{a.out}/audit_ep{EP}.json', 'w'), indent=1)
print(EP, 'severity', res['severity'], json.dumps({n: res['stats'][n] for n in names}), json.dumps(res['flags']))
