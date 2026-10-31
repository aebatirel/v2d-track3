"""Zero-lag (offline forward-backward / RTS) Kalman smoothing: what is the BEST it can do on the 20 public episodes?
Sweeps observation noise and process noise, with and without the half-frame advance, and reports mean ADD change vs
raw. Tuned on public mocap, so the best cell is an upper bound (diagnostic), not a pre-registered fix.
Usage: rtssweep.py DATA_DIR MESHDIR OUT.json
"""
import glob, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import all20 as A  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import trimesh  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402


def prep(d, meshdir):  # the same fits and gate as all20.episode, returning the raw series per object
    W = np.load(f'{d}/poses_world_vo.npz'); names = list(W.files); Hh = np.load(f'{d}/hands_refined.npz')
    rows = pq.read_table(glob.glob(f'{d}/ep*.parquet')[0], columns=['observation.objects']).column('observation.objects').to_pylist()
    T = min(len(rows), W[names[0]].shape[0]); G = {n: np.zeros((T, 4, 4)) for n in names}
    for t in range(T):
        dd = {str(o['name']): np.asarray(o['pose'], float) for o in rows[t]}
        for n in names:
            q = dd[n]; M = np.eye(4); M[:3, :3] = R.from_quat([q[4], q[5], q[6], q[3]]).as_matrix(); M[:3, 3] = q[:3]; G[n][t] = M
    O = {n: W[n][:T].astype(float) for n in names}
    k4 = np.array([[0, 0, 0], [.05, 0, 0], [0, .05, 0], [0, 0, .05]]); X = {n: np.eye(4) for n in names}
    for _ in range(8):
        src = np.concatenate([np.einsum('tij,kj->tki', (O[n] @ X[n])[:, :3, :3], k4) + (O[n] @ X[n])[:, None, :3, 3] for n in names]).reshape(-1, 3)
        dst = np.concatenate([np.einsum('tij,kj->tki', G[n][:, :3, :3], k4) + G[n][:, None, :3, 3] for n in names]).reshape(-1, 3)
        keep = np.ones(len(src), bool)
        for _ in range(5):
            Rm, tv = A.rigid(src[keep], dst[keep]); e = np.linalg.norm(src @ Rm.T + tv - dst, axis=1); keep = e <= np.quantile(e, 0.8)
        Wf = np.eye(4); Wf[:3, :3] = Rm; Wf[:3, 3] = tv
        for n in names:
            M2 = np.linalg.inv(Wf @ O[n]) @ G[n]; X[n] = np.eye(4); X[n][:3, :3] = R.from_matrix(M2[:, :3, :3]).mean().as_matrix(); X[n][:3, 3] = np.median(M2[:, :3, 3], 0)
    J = [Hh[f'joints_{s}'][:T] for s in ('left', 'right')]; V = [Hh[f'valid_{s}'][:T].astype(bool) for s in ('left', 'right')]
    out = []
    for n in names:
        m = trimesh.load(f'{meshdir}/{n}.glb', force='mesh'); vs = np.asarray(m.vertices)[::max(1, len(m.vertices) // 300)]
        Vw = np.einsum('tij,kj->tki', O[n][:, :3, :3], vs) + O[n][:, None, :3, 3]; held = np.zeros(T, bool)
        for j, v in zip(J, V):
            held |= v & (np.linalg.norm(j[:, :, None, :] - Vw[:, None, :, :], axis=3).min(axis=(1, 2)) < 0.035)
        Am = Wf @ O[n] @ X[n]; out.append(dict(ep=os.path.basename(d), n=n, p=Am[:, :3, 3], q=A.qcont(Am[:, :3, :3]), R0=Am[0, :3, :3], G=G[n], held=held))
    return out


data, meshdir, outf = sys.argv[1:4]
objs = []
for d in sorted(glob.glob(f'{data}/ep*'), key=lambda s: int(s.rsplit('ep', 1)[1])):
    objs += prep(d, meshdir)
raw = np.array([A.add_cm(o['p'], o['q'], o['R0'], o['G']) for o in objs]); adv = {}
res = {'raw_mean': float(raw.mean()), 'n_objects': len(objs), 'cells': []}
for shift in (0.0, A.ADV):
    for sig in (0.0005, 0.001, 0.002, 0.004):
        for qf in (1.0, 4.0, 16.0, 64.0):
            for qs_ratio in (1.0, 1e-2, 1e-4):  # still-object process noise as a fraction of the held one (1.0 = no gating)
                vals = []
                for o in objs:
                    p, q = (o['p'], o['q']) if shift == 0 else (A.advance(o['p'], shift), A.qadvance(o['q'], shift))
                    ps = A.kf(p, o['held'], sig, qf, qf * qs_ratio, smooth=True)
                    qq = A.kf(q, o['held'], sig / 0.1 * np.deg2rad(0.3) / 2, qf * 2.5, qf * 2.5 * qs_ratio, smooth=True)  # rotation noise scaled with sig
                    vals.append(A.add_cm(ps, qq, o['R0'], o['G']))
                v = np.array(vals); dlt = v - raw
                res['cells'].append(dict(shift=shift, sig_m=sig, q_held=qf, still_ratio=qs_ratio, mean=float(v.mean()),
                                         rel_pct=float(100 * (v.mean() / raw.mean() - 1)), better=int((dlt < -0.005).sum()), worse=int((dlt > 0.005).sum())))
        print('shift', shift, 'done', file=sys.stderr, flush=True)
# the shift alone, for reference
sh = np.array([A.add_cm(A.advance(o['p'], A.ADV), A.qadvance(o['q'], A.ADV), o['R0'], o['G']) for o in objs])
res['shift_only'] = dict(mean=float(sh.mean()), rel_pct=float(100 * (sh.mean() / raw.mean() - 1)))
json.dump(res, open(outf, 'w'), indent=1)
best0 = min([c for c in res['cells'] if c['shift'] == 0], key=lambda c: c['mean']); best1 = min([c for c in res['cells'] if c['shift'] > 0], key=lambda c: c['mean'])
print(json.dumps(dict(raw=res['raw_mean'], shift_only=res['shift_only'], best_smoother_no_shift=best0, best_smoother_with_shift=best1), indent=1))
