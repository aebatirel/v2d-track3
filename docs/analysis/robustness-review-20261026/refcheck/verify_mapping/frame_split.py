"""Own re-derivation of the mapping check's frame-local numbers (diagnostic; mocap read only here):
prod = mean over frames and objects of g(e_s) * g(e_r) (g = per-frame AUC share, trapezoid weights on 1..9 cm),
T - prod split by object-frames where the TRUE object rests at its frame-0 pose (< 1.5 cm and < 5 deg) or not.
Own-mesh rollouts. Writes frame_split.json."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial.transform import Rotation as Rot
import myscore as M

W = np.full(9, 1 / 8); W[0] = W[-1] = 1 / 16


def g(e):
    return (np.asarray(e)[..., None] < M.THR).astype(float) @ W


def sphere_err(sim, ref):
    r0 = Rot.from_quat(ref[0, 0, 3:]); a0 = Rot.from_quat(sim[0, 0, 3:])
    Rw = (r0 * a0.inv()).as_matrix(); off = ref[0, 0, :3] - Rw @ sim[0, 0, :3]
    P = sim[..., :3] @ Rw.T + off
    Ra = np.einsum('ij,fbjk->fbik', Rw, M._R(sim[..., 3:])); Rr = M._R(ref[..., 3:]); v = M.sphere()
    return np.stack([np.linalg.norm(np.einsum('fij,vj->fvi', Ra[:, b] - Rr[:, b], v) + (P[:, b] - ref[:, b, :3])[:, None],
                                    axis=-1).mean(-1) for b in range(sim.shape[1])], 1)


rows = [json.loads(l) for l in open(f'{M.SP}/work/verify_mapping/all.jsonl')]
rows = [r for r in rows if 'error' not in r and r['lib'] != 'scan']
refc = {}; res = []
for i, r in enumerate(sorted(rows, key=lambda r: (r['ep'], r['lib'], r['ref_digest']))):
    ep = r['ep']; names, fidx, G = M.gt(ep)
    fr, sim, ref, _, _ = M.read_rollout(f"{M.SP}/store/{r['path']}", names)
    k = (ep, r['lib'], r['ref_digest'])
    if k not in refc:
        refc[k] = M.registered(ep, r['lib'], ref, fr, return_err=True)
    er = refc[k]; et = M.registered(ep, r['lib'], sim, fr, return_err=True); es = sphere_err(sim, ref)
    gs, gr, gt = g(es), g(er), g(et)
    q = G[np.searchsorted(fidx, fr)]
    rest = (np.linalg.norm(q[:, :, :3] - q[:1, :, :3], axis=-1) < 0.015) & \
           (np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(q[:, :, 3:] * q[:1, :, 3:], -1)), 0, 1))) < 5.0)
    d = gt - gs * gr; N = d.size
    res.append(dict(ep=ep, S=r['S'], T=r['T'], R=r['R'], T_chk=round(float(gt.mean()), 4), S_chk=round(float(gs.mean()), 4),
                    R_chk=round(float(gr.mean()), 4), prod=float((gs * gr).mean()),
                    rest=float(d[rest].sum() / N), moved=float(d[~rest].sum() / N),
                    obj={n: dict(rest_share=float(rest[:, b].mean()), ex_rest=float(d[rest[:, b], b].sum() / len(d)),
                                 ex_moved=float(d[~rest[:, b], b].sum() / len(d))) for b, n in enumerate(names)}))
    if i % 100 == 0:
        print(i, len(rows), flush=True)
chk = max(max(abs(x['T_chk'] - x['T']), abs(x['S_chk'] - x['S']), abs(x['R_chk'] - x['R'])) for x in res)
out = dict(n=len(res), max_abs_check_vs_T_S_R=round(chk, 4))
for nm, sel in (('all', lambda x: True), ('R<0.95', lambda x: x['R'] < 0.95), ('S>=0.8', lambda x: x['S'] >= 0.8),
                ('S>=0.8,R<0.95', lambda x: x['S'] >= 0.8 and x['R'] < 0.95)):
    q = [x for x in res if sel(x)]
    T = np.array([x['T'] for x in q]); pr = np.array([x['prod'] for x in q]); S = np.array([x['S'] for x in q]); R = np.array([x['R'] for x in q])
    out[nm] = dict(n=len(q), excess_T_minus_prod=round(float(np.mean(T - pr)), 4), from_rest=round(float(np.mean([x['rest'] for x in q])), 4),
                   from_moved=round(float(np.mean([x['moved'] for x in q])), 4),
                   rmse_prod=round(float(np.sqrt(np.mean((T - pr) ** 2))), 4), rmse_SR=round(float(np.sqrt(np.mean((T - S * R) ** 2))), 4))
po = collections.defaultdict(list)
for x in res:
    for n, v in x['obj'].items():
        po[f"ep{x['ep']} {n}"].append(v)
out['per_object'] = {k: dict(n=len(v), rest_share=round(float(np.mean([y['rest_share'] for y in v])), 3),
                             ex_rest=round(float(np.mean([y['ex_rest'] for y in v])), 3),
                             ex_moved=round(float(np.mean([y['ex_moved'] for y in v])), 3)) for k, v in sorted(po.items())}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frame_split.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
