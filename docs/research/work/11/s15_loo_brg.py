"""LOO (twin -> held-out) of the world-free bearing prior vs rel/abs priors for symmetric slot-0 cups (eps 12,13,21,22),
and for 2-fold slot-0 anchors (margin to the 180-deg flip). Official kit metric functions; perfect tracking otherwise.
Research only."""
from c11 import *
import json
MODS = {m: load_metric(m) for m in ["AUC", "SP-SR", "MP-SR", "RPE", "MPPE"]}; A = MODS["AUC"]
V = {}
def verts(n):
    if n not in V: V[n] = surface_points(n, 500, 0)
    return V[n]
def metrics(ach, ref, names):
    a = A._normalise_quaternions(ach[:, None], "s", ValueError); r = A._normalise_quaternions(ref[:, None], "r", ValueError)
    a = A._warp_to_reference_start(a, r); ids = np.arange(ach.shape[1]); v = np.stack([verts(n) for n in names])
    return dict(AUC=round(A._add_auc(A._object_add(a, r, v)), 3), SP=round(float(np.mean(MODS["SP-SR"]._spider_success(a, r))), 2),
                MP=round(float(np.mean(MODS["MP-SR"]._maniptrans_success(a, r, ids))), 2), MPPE=round(MODS["MPPE"]._mean_per_point_error_cm(a, r), 2))
def spin(p, j, deg):
    o = p.copy(); q = Rot.from_rotvec(np.radians(deg) * np.array([0, 0, 1.0])).as_quat()
    o[:, j, 3:] = (Rot.from_quat(p[:, j, 3:]) * Rot.from_quat(q)).as_quat(); return o
def q(e):
    p = e['pose'][0]; nm = e['names']; ya, _ = yaw_tilt(p[0, 3:], nm[0]); yb, _ = yaw_tilt(p[1, 3:], nm[1]); d = p[1, :2] - p[0, :2]
    return dict(abs=float(ya), rel=float(wrap(ya - yb)), brg=float(wrap(ya - np.degrees(np.arctan2(d[1], d[0])))))
out = {}
for pair in ([12, 13], [21, 22]):
    E = {ep: load_episode(ep) for ep in pair}
    for ep in pair:
        tw = [t for t in pair if t != ep][0]; qe, qt = q(E[ep]), q(E[tw]); p, nm = E[ep]['pose'], E[ep]['names']
        r = {}
        for k in ('abs', 'rel', 'brg'):
            d = float(wrap(qe[k] - qt[k])); r[k] = dict(err=round(d, 1), **metrics(spin(p, 0, -d), p, nm))
        dc = float(np.degrees(np.angle(np.exp(1j * np.radians(wrap(qe['rel'] - qt['rel']))) + np.exp(1j * np.radians(wrap(qe['brg'] - qt['brg']))))))
        r['rel+brg'] = dict(err=round(dc, 1), **metrics(spin(p, 0, -dc), p, nm))
        out[ep] = r; print(ep, E[ep]['task'], r)
json.dump(out, open('s15_loo_brg.json', 'w'), indent=1)
