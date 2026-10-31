"""Two CPU checks on the robot's training plans (public ep2/12/18/24; no ground truth read):
(1) how jittery are the targets the robot is asked to follow (wrist, fingers, object), and how large is the jitter in
    acceleration, which sets the forces a physics-based grip must supply (F = m a);
(2) finger synergies: PCA of the 22 finger joints per hand over all frames; how many coordinated patterns cover the
    grasps, and how many cover the physics solver's own edits (solved - input plan, ep2/ep12).
Usage: refjit_syn.py REFS_DIR OUT.json
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as R

FPS = 20.0


def load(f):
    t = pq.read_table(f).to_pylist()[0]; d = {}
    for s in ('left', 'right'):
        d[f'{s}_wp'] = np.array(t[f'robot_{s}_wrist_position'], float); q = np.array(t[f'robot_{s}_wrist_wxyz'], float)
        d[f'{s}_wq'] = q[:, [1, 2, 3, 0]]; d[f'{s}_fj'] = np.array(t[f'robot_{s}_finger_joints'], float)
    d['obj_p'] = np.array(t['object_body_position'], float)  # (T, B, 3)
    d['names'] = t['object_body_names']; return d


def jitter(x, w=9):  # high-frequency residual RMS and the RMS of the second difference (acceleration)
    lo = savgol_filter(x, w, 2, axis=0); hi = x - lo
    acc = np.diff(x, 2, axis=0) * FPS ** 2; acc_lo = np.diff(lo, 2, axis=0) * FPS ** 2
    return float(np.sqrt((hi ** 2).sum(-1).mean())), float(np.sqrt((acc ** 2).sum(-1).mean())), float(np.sqrt((acc_lo ** 2).sum(-1).mean()))


def rotjit(q):  # wrap-free: angle between each raw orientation and its smoothed version, plus angular acceleration
    for t in range(1, len(q)):
        if np.dot(q[t], q[t - 1]) < 0:
            q[t] = -q[t]
    qs = savgol_filter(q, 9, 2, axis=0); qs /= np.linalg.norm(qs, axis=1, keepdims=True)
    ang = (R.from_quat(qs).inv() * R.from_quat(q)).magnitude() * 180 / np.pi
    w = (R.from_quat(q[:-1]).inv() * R.from_quat(q[1:])).as_rotvec() * FPS  # body angular velocity, rad/s
    ws = (R.from_quat(qs[:-1]).inv() * R.from_quat(qs[1:])).as_rotvec() * FPS
    a = np.linalg.norm(np.diff(w, axis=0) * FPS, axis=1); a_s = np.linalg.norm(np.diff(ws, axis=0) * FPS, axis=1)
    return float(np.sqrt((ang ** 2).mean())), float(np.sqrt((a ** 2).mean())), float(np.sqrt((a_s ** 2).mean()))


refs, outf = sys.argv[1:3]; out = {'jitter': {}, 'synergy': {}}
F_all, edits = [], []
for f in sorted(glob.glob(f'{refs}/*.parquet')):
    k = os.path.basename(f)[:-8]; d = load(f); r = {}
    for s in ('left', 'right'):
        wj, wa, wa_lo = jitter(d[f'{s}_wp'] * 100); rj, ra, ra_lo = rotjit(d[f'{s}_wq'].copy()); fj, fa, fa_lo = jitter(np.rad2deg(d[f'{s}_fj']))
        r[s] = dict(wrist_hf_cm=round(wj, 3), wrist_acc_m_s2=round(wa / 100, 2), wrist_acc_smooth_m_s2=round(wa_lo / 100, 2),
                    wrist_rot_hf_deg=round(rj, 3), wrist_angacc_rad_s2=round(ra, 1), wrist_angacc_smooth_rad_s2=round(ra_lo, 1), finger_hf_deg=round(fj, 3))
        F_all.append(np.rad2deg(d[f'{s}_fj']))
    for b, n in enumerate(d['names']):
        oj, oa, oa_lo = jitter(d['obj_p'][:, b] * 100)
        r[n] = dict(obj_hf_cm=round(oj, 3), obj_acc_m_s2=round(oa / 100, 2), obj_acc_smooth_m_s2=round(oa_lo / 100, 2))
    out['jitter'][k] = r
    if k.startswith('solved_') and os.path.exists(f'{refs}/glilc_{k[7:]}.parquet'):
        d0 = load(f'{refs}/glilc_{k[7:]}.parquet')
        for s in ('left', 'right'):
            e = np.rad2deg(d[f'{s}_fj'] - d0[f'{s}_fj']); m = np.abs(e).max(1) > 0.5  # frames the solver edited
            if m.any():
                edits.append(e[m])


def pca(X, label):
    X = np.concatenate(X); mu = X.mean(0); U, S, Vt = np.linalg.svd(X - mu, full_matrices=False); ev = S ** 2 / (S ** 2).sum(); c = np.cumsum(ev)
    rec = {}
    for kk in (1, 2, 3, 4, 5, 6, 8, 10):
        Xr = (X - mu) @ Vt[:kk].T @ Vt[:kk]; rec[kk] = round(float(np.sqrt(((X - mu - Xr) ** 2).mean())), 3)
    return dict(frames=int(len(X)), k_for_80=int(np.searchsorted(c, 0.80) + 1), k_for_90=int(np.searchsorted(c, 0.90) + 1),
                k_for_95=int(np.searchsorted(c, 0.95) + 1), first5_share=[round(float(v), 3) for v in ev[:5]],
                rms_joint_err_deg_with_k=rec, total_rms_deg=round(float(np.sqrt(((X - mu) ** 2).mean())), 3), _basis=Vt[:8].tolist(), _mean=mu.tolist())


out['synergy']['all_plans'] = pca(F_all, 'all')
if edits:
    out['synergy']['solver_edits'] = pca(edits, 'edits')
json.dump(out, open(outf, 'w'), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if not kk.startswith('_')} for k, v in out['synergy'].items()}, indent=1))
for k, r in out['jitter'].items():
    print(k, {kk: vv for kk, vv in r.items()})
