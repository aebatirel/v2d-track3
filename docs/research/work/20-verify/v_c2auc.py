"""Verifier (DIG 20 C2): official kit AUC internals (AUC.py loaded as-is) on public GT with only the slot-0 frame-0
anchor replaced by a window mean, on top of several base-error models. Own vertex sampling, own seeds."""
import sys, json, importlib.util, numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
from v_c12 import load, karcher, ROOT, PUB
KIT = f'{ROOT}/kit/v2d_submission_kit/metric_code/track_3/AUC.py'
spec = importlib.util.spec_from_file_location('AUC', KIT); AUC = importlib.util.module_from_spec(spec); spec.loader.exec_module(AUC)
_V = {}
def verts(name, n=1000):
    if name not in _V:
        import os
        p = f'{ROOT}/data/track_3/public/mesh/{name}/{name}.glb'
        if not os.path.exists(p): p = f'{ROOT}/data/track_3/public/mesh/{name}/{name}_visual.glb'
        m = trimesh.util.concatenate(list(trimesh.load(p, force='scene').dump()))
        _V[name] = np.asarray(trimesh.sample.sample_surface(m, n, seed=7)[0], float)
    return _V[name]
def auc(ach, ref, names):
    a = AUC._normalise_quaternions(ach[:, None], 's', ValueError); r = AUC._normalise_quaternions(ref[:, None], 's', ValueError)
    a = AUC._warp_to_reference_start(a, r)
    V = np.stack([verts(n) for n in names]); add = AUC._object_add(a, r, V)
    return AUC._add_auc(add), add
def base(ref, model, sigma, rng):
    T, B = ref.shape[:2]; ach = ref.copy()
    if sigma <= 0: return ach
    def rdir(*s):
        v = rng.normal(size=s + (3,)); return v / np.linalg.norm(v, axis=-1, keepdims=True)
    if model == 'iid':
        ach[..., :3] += rdir(T, B) * np.abs(rng.normal(0, sigma, (T, B, 1)))
    elif model == 'const':   # constant per-object offset (systematic) + 3 mm iid jitter
        ach[..., :3] += rdir(1, B) * np.abs(rng.normal(0, sigma, (1, B, 1))) + rdir(T, B) * np.abs(rng.normal(0, 0.003, (T, B, 1)))
    elif model == 'rw':      # slowly drifting error (random walk scaled to rms ~ sigma at the end)
        steps = rng.normal(0, sigma / np.sqrt(T), (T, B, 3)); ach[..., :3] += np.cumsum(steps, 0)
    ach[0, 0] = ref[0, 0]
    return ach
if __name__ == '__main__':
    gt = {r['ep']: r for r in json.load(open(f'{ROOT}/work/20-verify/v_c12.json'))}
    models = [('iid', 0.0), ('iid', 0.01), ('iid', 0.02), ('iid', 0.03), ('const', 0.01), ('const', 0.02), ('rw', 0.02)]
    res = {}
    for ep in PUB:
        names, P = load(ep); g = gt[ep]
        wins = dict(det=g['end'], orc=g['pert'] - 1, orr=g['pert_r'] - 1, cm1=g['on'] - 1, f15=14, last=('last', g['on'] - 1))
        maxadd = {}
        for (mdl, sg) in models:
            out = {k: [] for k in ['f0'] + list(wins)}
            for sd in range(4):
                rng = np.random.default_rng(99991 * ep + 17 * sd + 5); ach0 = base(P, mdl, sg, rng)
                for k in out:
                    ach = ach0.copy()
                    if k != 'f0':
                        w = wins[k]
                        if isinstance(w, tuple):  # anchor = the single last pre-onset frame
                            ach[0, 0] = P[w[1], 0]
                        elif w >= 1:
                            W = P[:w + 1, 0]; ach[0, 0, :3] = W[:, :3].mean(0); ach[0, 0, 3:] = karcher(W[:, 3:]).as_quat()
                    s, add = auc(ach, P, names); out[k].append(s)
                    if sg == 0 and sd == 0: maxadd[k] = float(add.max())
                if sg == 0: break
            res.setdefault(f'{mdl}{sg}', {})[ep] = {k: float(np.mean(v)) for k, v in out.items()}
        print(f'p{ep:2d} max ADD (m) with exact tracker:', {k: round(v, 4) for k, v in maxadd.items()},
              '| AUC exact:', {k: round(v, 4) for k, v in res['iid0.0'][ep].items()}, flush=True)
    for key, d in res.items():
        base_m = np.mean([d[e]['f0'] for e in d])
        line = f'{key:9s} base AUC {base_m:.4f} |'
        for k in ['det', 'orc', 'orr', 'cm1', 'f15', 'last']:
            dd = np.array([d[e][k] - d[e]['f0'] for e in d]); line += f' {k} {dd.mean():+.4f} (min {dd.min():+.4f})'
        print(line)
    json.dump(res, open(f'{ROOT}/work/20-verify/v_c2auc.json', 'w'), indent=0)
