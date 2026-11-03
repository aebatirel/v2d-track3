"""SP-SR / MP-SR of stored rollouts against OUR OWN reference (3 Nov 2026, perfect-following lane; coordinator's audit
request). GT-free: the target is our packed reference, never mocap.

Kit logic (metric_code/track_3/MP-SR.py, _registered_pose_metric): per world, position error |p_a - p_r| and the kit's
symmetry-aware orientation error (_symmetry_orientation_errors: cups axial, lid order 2) are averaged over frames per object;
SP-SR: mean over objects of position <= 0.10 m AND of orientation <= 0.5 rad; MP-SR: every object < 0.03 m AND < 30 deg.
Against our own reference no registration / scene alignment is needed (the rollout starts at the reference's frame 0, same
world frame); symmetry axes come from our library meshes with the kit's eigen rule (scorer: the scans').
Inputs: either a Track-3 submission parquet (--submission, rows e/w/f/o) or rollout parquets (--rollout, columns
environment_id / reference_frame / object_id / achieved_*), plus --ref EP=REFERENCE.parquet.
Usage: sr_vs_ref.py --kit KIT --lib LIB (--submission S.parquet | --rollout EP=R.parquet ...) --ref EP=REF.parquet ... --out OUT.json
"""
import argparse, importlib.util, json, os, sys
import numpy as np, pandas as pd, pyarrow.parquet as pq, trimesh

ap = argparse.ArgumentParser(); ap.add_argument('--kit', required=True); ap.add_argument('--lib', required=True)
ap.add_argument('--submission'); ap.add_argument('--rollout', action='append', default=[]); ap.add_argument('--ref', action='append', required=True)
ap.add_argument('--out', required=True); a = ap.parse_args()
spec = importlib.util.spec_from_file_location('mpsr', os.path.join(a.kit, 'metric_code', 'track_3', 'MP-SR.py'))
K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}


def axis_of(name):
    if name not in SYM: return np.zeros(3), 0
    m = trimesh.load(os.path.join(a.lib, f'{name}.glb'), force='mesh'); pts = m.sample(4000, seed=0) if 'seed' in m.sample.__code__.co_varnames else m.sample(4000)
    pts = pts - pts.mean(0); w, U = np.linalg.eigh(np.cov(pts.T))
    if SYM[name] == 'half': return U[:, 0], 2
    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); return U[:, k], 360


def ref_arrays(path):
    t = pq.read_table(path); names = t.column('object_body_names')[0].as_py(); B = len(names)
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
    P = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
    Q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    return names, np.concatenate([P, Q], -1)


def score(ach, ref, names):     # ach / ref: (F, W, B, 7) xyzw
    ax = [axis_of(n) for n in names]; axes = [x[0] for x in ax]; orders = [x[1] for x in ax]
    pos = np.linalg.norm(ach[..., :3] - ref[..., :3], axis=-1).mean(axis=0)              # (W, B)
    ori = K._symmetry_orientation_errors(ach, ref, axes, orders).mean(axis=0)            # (W, B)
    sp = (pos.mean(-1) <= 0.1) & (ori.mean(-1) <= 0.5); mp = np.all((pos < 0.03) & (ori < np.deg2rad(30)), axis=-1)
    return dict(sp_sr=float(sp.mean()), mp_sr=float(mp.mean()), worlds=int(pos.shape[0]),
                sp_pos_mean_cm=round(100 * float(pos.mean(-1).mean()), 2), sp_ori_mean_rad=round(float(ori.mean(-1).mean()), 3),
                objects={n: dict(pos_cm=round(100 * float(pos[:, i].mean()), 2), ori_deg=round(float(np.degrees(ori[:, i].mean())), 1),
                                 mp_pos_margin=round(float(pos[:, i].max() / 0.03), 2), mp_ori_margin=round(float(ori[:, i].max() / np.deg2rad(30)), 2))
                         for i, n in enumerate(names)},
                sp_pos_margin=round(float(pos.mean(-1).max() / 0.1), 2), sp_ori_margin=round(float(ori.mean(-1).max() / 0.5), 2))


refs = {int(k): v for k, v in (x.split('=', 1) for x in a.ref)}; out = {}
if a.submission:
    s = pd.read_parquet(a.submission); k = s.row_id.str.extract(r'^track_3/e(\d+)/w(\d+)/f(\d+)/o(\d+)$').astype(int); k.columns = list('ewfo')
    pose = s[['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']].to_numpy(float)
    for e, rp in sorted(refs.items()):
        names, R = ref_arrays(rp); m = (k.e == e).to_numpy(); kk = k[m]
        W = kk.w.max() + 1; F = sorted(kk.f.unique()); fi = {f: j for j, f in enumerate(F)}
        A = np.full((len(F), W, len(names), 7), np.nan)
        for (w, f, o), p in zip(kk[['w', 'f', 'o']].to_numpy(), pose[m]): A[fi[f], w, o] = p
        Rr = np.repeat(R[F][:, None], W, axis=1)
        if np.isnan(A).any(): out[e] = dict(error='missing rows'); continue
        out[e] = score(A, Rr, names)
for x in a.rollout:
    e, f = x.split('=', 1); e = int(e); names, R = ref_arrays(refs[e]); r = pd.read_parquet(f)
    W = int(r.environment_id.max()) + 1; F = sorted(r.reference_frame.unique()); fi = {v: j for j, v in enumerate(F)}
    A = np.full((len(F), W, len(names), 7), np.nan)
    cols = ['achieved_position_x', 'achieved_position_y', 'achieved_position_z', 'achieved_quaternion_x', 'achieved_quaternion_y', 'achieved_quaternion_z', 'achieved_quaternion_w']
    for (w, fr, o), p in zip(r[['environment_id', 'reference_frame', 'object_id']].to_numpy(), r[cols].to_numpy(float)): A[fi[fr], w, o] = p
    out.setdefault('rollouts', {}).setdefault(e, []).append(dict(file=f, **score(A, np.repeat(R[F][:, None], W, axis=1), names)))
json.dump(out, open(a.out, 'w'), indent=1, default=str)
print(json.dumps({k: (v if k == 'rollouts' else {kk: v.get(kk) for kk in ('sp_sr', 'mp_sr', 'sp_pos_margin', 'sp_ori_margin')}) for k, v in out.items() if k != 'rollouts'}))
