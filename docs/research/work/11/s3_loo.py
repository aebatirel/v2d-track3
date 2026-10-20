"""LOO: value of a task yaw prior for a symmetric slot-0 cup anchor, scored with the official kit functions.
Model: our reference = GT (perfect tracking) except the cup body carries a constant spin error d about its
symmetry axis (body z) in every frame; scorer warps from slot-0 frame-0 as in score()."""
from c11 import *
import json
MODS = {m: load_metric(m) for m in ["AUC", "SP-SR", "MP-SR", "RPE", "MPPE"]}
A = MODS["AUC"]
VERT = {}
def verts(nm):
    if nm not in VERT: VERT[nm] = surface_points(nm, 500, 0)
    return VERT[nm]

def metrics(ach, ref, names):
    a = A._normalise_quaternions(ach[:, None], "s", ValueError); r = A._normalise_quaternions(ref[:, None], "r", ValueError)
    a = A._warp_to_reference_start(a, r); ids = np.arange(ach.shape[1])
    v = np.stack([verts(n) for n in names])
    return dict(AUC=A._add_auc(A._object_add(a, r, v)), SPSR=float(np.mean(MODS["SP-SR"]._spider_success(a, r))),
                MPSR=float(np.mean(MODS["MP-SR"]._maniptrans_success(a, r, ids))),
                RPE=MODS["RPE"]._relative_position_error_cm(a, r), MPPE=MODS["MPPE"]._mean_per_point_error_cm(a, r))

def spin(p, j, deg, axis=(0, 0, 1)):
    o = p.copy(); qz = Rot.from_rotvec(np.radians(deg) * np.array(axis, float)).as_quat()
    o[:, j, 3:] = (Rot.from_quat(p[:, j, 3:]) * Rot.from_quat(qz)).as_quat(); return o

CUPEPS = [11, 12, 13, 21, 22]
E = {ep: load_episode(ep) for ep in CUPEPS}
for e in E.values():
    assert np.isfinite(e['pose']).all()
# truth yaw (abs) and relative yaw of slot0 cup
info = {}
for ep, e in E.items():
    p = e['pose']; nm = e['names']
    ya, _ = yaw_tilt(p[0, 0, 3:], nm[0]); yb, _ = yaw_tilt(p[0, 1, 3:], nm[1])
    info[ep] = dict(abs=float(ya), rel=float(wrap(ya - yb)), task=e['task'])
print(json.dumps(info, indent=0))

def avg(dl):
    return {k: float(np.mean([d[k] for d in dl])) for k in dl[0]}

res = {}
grid = np.arange(-180, 180, 5.0)
for ep, e in E.items():
    p, nm = e['pose'], e['names']
    r = {}
    r['perfect'] = metrics(p, p, nm)
    r['random'] = avg([metrics(spin(p, 0, d), p, nm) for d in grid])
    for d in [3, 5, 10, 15, 20, 30, 45, 90, 180]:
        r[f'spin{d}'] = avg([metrics(spin(p, 0, s * d), p, nm) for s in (-1, 1)])
    twins = [t for t in CUPEPS if t != ep and info[t]['task'] == info[ep]['task']]
    if twins:
        mu_abs = np.degrees(np.angle(np.mean([np.exp(1j * np.radians(info[t]['abs'])) for t in twins])))
        mu_rel = np.degrees(np.angle(np.mean([np.exp(1j * np.radians(info[t]['rel'])) for t in twins])))
        dabs = float(wrap(info[ep]['abs'] - mu_abs)); drel = float(wrap(info[ep]['rel'] - mu_rel))
        # our estimate sets cup yaw = mu (+ W error eps); spin error = estimate - truth
        for epsW in [0, 3, 10]:
            r[f'absprior_W{epsW}'] = avg([metrics(spin(p, 0, -dabs + s * epsW), p, nm) for s in ((-1, 1) if epsW else (1,))])
        r['relprior'] = metrics(spin(p, 0, -drel), p, nm)
        r['_dabs'] = dabs; r['_drel'] = drel
    res[ep] = r
    print(f"\n== ep{ep} {e['task']} slot0={nm[0]}")
    for k, v in r.items():
        if isinstance(v, dict):
            print(f"  {k:14s} " + " ".join(f"{m}={v[m]:.3f}" for m in v))
        else:
            print(f"  {k:14s} {v:.1f}")
json.dump(res, open('s3_loo.json', 'w'), indent=1)
