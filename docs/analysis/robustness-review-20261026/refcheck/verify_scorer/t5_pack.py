"""verify_scorer test 5: independent audit of the uploaded pack-4 file (no ground truth; eval episodes have none).
- every row vs the world-0 achieved pose of the packed rollout (own pyarrow reader, rows matched by step/body id), in
  xyzw and, as a control, in a wrong (wxyz) reading;
- every mesh payload decoded with my own base64 + np.load and compared with budget_mesh(library glb) for library_v3,
  library_v3x, library_v2 (control: must differ);
- frame-0 achieved-vs-reference gaps; the eval-20 cup's early-frame drop vs a semi-implicit free fall.
Usage: python -I t5_pack.py OUT.json"""
import base64, io, json, sys, glob
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np, pandas as pd
from vs_core import *

SUBF = '/home/user/v2d-track3/results/submissions/20261026-track3d/track3_submission.parquet'
RD = f'{STORE}/runs/20261026-pack4-f7a49a9/results/submission/results'
sub = pd.read_parquet(SUBF)
k = sub.row_id.str.extract(r'^track_3/e(\d+)/w(\d+)/f(\d+)/o(\d+)$').astype(int); k.columns = ['e', 'w', 'f', 'o']
sub = pd.concat([sub, k], axis=1)
P = ['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']
out = dict(rows=len(sub), worlds=sorted(sub.w.unique().tolist()), episodes={})
libs = ['library_v3', 'library_v3x', 'library_v2']
for e, g in sub.groupby('e'):
    names, ach, ref, steps, rf, md = load_rollout(f'{RD}/episode_{e:06d}.parquet')
    A = ach[g.f.to_numpy(), g.o.to_numpy()]
    X = g[P].to_numpy()
    wxyz = np.concatenate([A[:, :3], A[:, 6:7], A[:, 3:6]], 1)
    r = dict(names=names, T_rollout=len(steps), T_rows=int(g.f.max() + 1), maxabs_xyzw=float(np.abs(X - A).max()),
             maxabs_if_wxyz=float(np.abs(X - wxyz).max()))
    mesh = {}
    for o, n in enumerate(names):
        pay = g[(g.o == o)].sort_values('f').object_mesh_b64.fillna('')
        npay = int((pay.str.strip() != '').sum())
        with np.load(io.BytesIO(base64.b64decode(pay.iloc[0]))) as z:
            V, F = z['vertices'], z['faces']
        eq = {}
        for L in libs:
            try:
                bv, bf = budget(f'{LIB}/{L}/{n}.glb')
                eq[L] = bool(np.array_equal(V, bv) and np.array_equal(F, bf))
            except Exception as ex:
                eq[L] = f'n/a ({type(ex).__name__})'
        mesh[n] = dict(payloads=npay, first_row_has_payload=bool(pay.iloc[0].strip() != ''), equals=eq)
    r['mesh'] = mesh
    r['frame0_gap'] = {n: dict(pos_mm=round(float(np.linalg.norm(ach[0, s, :3] - ref[0, s, :3]) * 1000), 3),
                               dz_mm=round(float((ach[0, s, 2] - ref[0, s, 2]) * 1000), 3),
                               rot_deg=round(float(np.degrees((Rot.from_quat(ach[0, s, 3:]) * Rot.from_quat(ref[0, s, 3:]).inv()).magnitude())), 3))
                       for s, n in enumerate(names)}
    if e == 20:
        r['cup_dz_mm_frames0to4'] = [round(float((ach[t, 0, 2] - ach[0, 0, 2] + ach[0, 0, 2] - ref[0, 0, 2]) * 1000), 3) for t in range(5)]
        r['cup_ref_dz_mm_frames0to4'] = [round(float((ref[t, 0, 2] - ref[0, 0, 2]) * 1000), 3) for t in range(5)]
        g9, dt = 9.81, 0.01
        r['freefall_pred_mm_after_n_steps'] = [round(g9 * dt * dt * (5 * n) * (5 * n + 1) / 2 * 1000, 3) for n in range(1, 6)]
    out['episodes'][int(e)] = r
    print(e, {kk: r[kk] for kk in ('maxabs_xyzw', 'maxabs_if_wxyz')}, {n: m['equals'] for n, m in mesh.items()}, flush=True)
out['all_rows_equal_xyzw'] = all(r['maxabs_xyzw'] == 0.0 for r in out['episodes'].values())
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print(json.dumps(out['episodes'][20], indent=1))
