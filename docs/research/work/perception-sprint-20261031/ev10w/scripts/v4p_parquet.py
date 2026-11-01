"""Reference (b) of PREREG: the gl10A2 reference parquet with ONLY the two cups' poses replaced by a perception-dir
track (V4p: scratchpad/mask10/eval10/posthoc/V4p/poses.npz; world_T_cam, cam_T_<obj>, 161 frames = the reference's 161),
mapped into the reference world frame by ONE rigid transform G fitted by least squares (Kabsch) on both cups' mesh
points (library_v3 vertices, the file frame both use) over frames FIT_A..FIT_B, where V4p equals the stored track
(before the S12 window). Everything else in the parquet (hands, robot, fps, names) is copied unchanged.
GT-free: our reference + our track only. Reports the fit residual per frame (mm) for both cups over all frames:
for the INPUT track (IN_DIR/poses.npz, same G) the residual over all frames says whether the reference was built from
that track at all; for V4p it shows where V4p moves the cups.
Usage: v4p_parquet.py REF.parquet V4P_DIR IN_DIR FIT_A FIT_B OUT_DIR"""
import sys, os, json
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot
ref, v4p, inp, fa, fb, outd = sys.argv[1:7]; fa, fb = int(fa), int(fb)
t = pq.read_table(ref); row = t.to_pylist()[0]; names = list(row['object_body_names'])
pos = np.array(row['object_body_position'], float); q = np.array(row['object_body_wxyz'], float)
T = len(pos); Oref = np.tile(np.eye(4), (T, len(names), 1, 1))
Oref[..., :3, :3] = Rot.from_quat(q.reshape(-1, 4)[:, [1, 2, 3, 0]]).as_matrix().reshape(T, len(names), 3, 3); Oref[..., :3, 3] = pos


def load(d):
    Z = np.load(os.path.join(d, 'poses.npz')); W = Z['world_T_cam'].astype(float)
    return {n: np.einsum('tij,tjk->tik', W, Z[f'cam_T_{n}'].astype(float)) for n in names}


V, Iin = load(v4p), load(inp)
assert all(len(V[n]) == T for n in names), {n: len(V[n]) for n in names}
pts = {n: np.asarray(trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{n}.glb', force='mesh').vertices)[::7] for n in names}
app = lambda O, X: X @ O[:3, :3].T + O[:3, 3]
A = np.concatenate([app(V[n][f], pts[n]) for f in range(fa, fb + 1) for n in names])
Bp = np.concatenate([app(Oref[f, b], pts[n]) for f in range(fa, fb + 1) for b, n in enumerate(names)])
ca, cb = A.mean(0), Bp.mean(0); Hm = (A - ca).T @ (Bp - cb); U, S, Vt = np.linalg.svd(Hm)
D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); Rg = Vt.T @ D @ U.T; tg = cb - Rg @ ca
G = np.eye(4); G[:3, :3] = Rg; G[:3, 3] = tg


def resid(src):
    out = {}
    for b, n in enumerate(names):
        e = [float(np.median(np.linalg.norm(app(G @ src[n][f], pts[n]) - app(Oref[f, b], pts[n]), axis=1)) * 1e3) for f in range(T)]
        out[n] = np.round(e, 2).tolist()
    return out


rv, ri = resid(V), resid(Iin)
newO = np.stack([np.einsum('ij,tjk->tik', G, V[n]) for n in names], 1)
newpos = newO[..., :3, 3]; newq = Rot.from_matrix(newO[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(T, len(names), 4)[..., [3, 0, 1, 2]]
sub = os.path.relpath(os.path.dirname(ref), os.path.dirname(os.path.dirname(os.path.dirname(ref))))
dst = os.path.join(outd, 'processed', *ref.split(os.sep)[-3:-1]); os.makedirs(dst, exist_ok=True)
for k, v in (('object_body_position', newpos.tolist()), ('object_body_wxyz', newq.tolist())):
    i = t.column_names.index(k); t = t.set_column(i, k, pa.array([v], type=t.schema.field(k).type))
outp = os.path.join(dst, 'ref_v4p.parquet'); pq.write_table(t, outp)
fit_res = np.concatenate([np.array(rv[n][fa:fb + 1]) for n in names])
rep = dict(note='reference (b): gl10A2 parquet with only object_body_position / object_body_wxyz replaced by G @ V4p (DIAGNOSTIC)',
           ref=ref, v4p=v4p, input_track=inp, fit_frames=[fa, fb], G=G.round(6).tolist(),
           G_rot_deg=round(float(np.degrees(Rot.from_matrix(Rg).magnitude())), 2), fit_residual_mm=dict(median=round(float(np.median(fit_res)), 2), max=round(float(fit_res.max()), 2)),
           residual_v4p_vs_ref_mm={n: dict(f0_52_med=round(float(np.median(rv[n][0:53])), 2), f53_99_med=round(float(np.median(rv[n][53:100])), 2),
                                            f100_117_med=round(float(np.median(rv[n][100:118])), 2), f118_160_med=round(float(np.median(rv[n][118:])), 2)) for n in names},
           residual_input_vs_ref_mm={n: dict(f0_52_med=round(float(np.median(ri[n][0:53])), 2), f53_99_med=round(float(np.median(ri[n][53:100])), 2),
                                              f100_117_med=round(float(np.median(ri[n][100:118])), 2), f118_160_med=round(float(np.median(ri[n][118:])), 2),
                                              all_max=round(float(np.max(ri[n])), 2)) for n in names},
           per_frame=dict(v4p=rv, input=ri), out=outp)
json.dump(rep, open(os.path.join(outd, 'v4p_parquet.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'per_frame'}, indent=1))
