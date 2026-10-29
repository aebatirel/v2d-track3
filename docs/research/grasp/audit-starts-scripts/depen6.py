"""Frame-0 pose candidates for a GUEST object resting on/in a HOST object (start-overlap fix class).
(a) GT-FREE minimal 6-DoF depenetration: smallest rigid motion of the guest (translation <= 4 cm, rotation <= 15 deg)
    that takes its hull-surface samples out of the host's hulls (FlashCHORD's own CoACD hulls) and above the table,
    cost = sum(depth^2) * 1e6 + |dt|^2 / (1 cm)^2 + |drot|^2 / (5 deg)^2; random restarts + Powell.
(b) DIAGNOSTIC WITH GROUND TRUTH (only to separate perception error from hull inflation): the guest placed at its
    mocap-consistent pose RELATIVE to the host (host kept at our reference pose); its remaining overlap.
Prints both as 'x y z qx qy qz qw' (world, our sim frame) with the overlap before/after.
Usage: depen6.py EP GUEST HOST"""
import sys, os, json, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.optimize import minimize
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments

ep, g, h = int(sys.argv[1]), sys.argv[2], sys.argv[3]
d = load_ref(ref_path(ep)); n = d['names']; gi, hi = n.index(g), n.index(h)
Hg, Hh = Hulls(hull_path(g)), Hulls(hull_path(h))
GS = np.concatenate([trimesh.sample.sample_surface(x, max(30, int(3000 * x.area / sum(y.area for y in Hg.H))), seed=k)[0] for k, x in enumerate(Hg.H)] + [x.vertices for x in Hg.H])
pg, qg, ph, qh = d['OP'][0, gi], d['OQ'][0, gi], d['OP'][0, hi], d['OQ'][0, hi]
# speed: keep only guest samples and host hulls within 5 cm of each other (motions are <= 4 cm), plus the guest's
# lowest samples for the table term
_Lh = world_to_local(local_to_world(GS, pg, qg), ph, qh)
_keep_h = [k for k, x in enumerate(Hh.H) if np.all(_Lh.min(0) - 0.05 <= x.bounds[1]) and np.all(_Lh.max(0) + 0.05 >= x.bounds[0])]
_near = np.zeros(len(GS), bool)
for k in _keep_h:
    lo, hi_ = Hh.H[k].bounds; _near |= np.all((_Lh >= lo - 0.05) & (_Lh <= hi_ + 0.05), 1)
_zw = local_to_world(GS, pg, qg)[:, 2]; _near |= _zw < _zw.min() + 0.02
GS = GS[_near]; Hh.eq = [Hh.eq[k] for k in _keep_h]; Hh.H = [Hh.H[k] for k in _keep_h]
print('kept', len(GS), 'guest samples,', len(_keep_h), 'host hulls', flush=True)


def pen(p, q):
    W_ = local_to_world(GS, p, q); dep, _ = Hh.depth(world_to_local(W_, ph, qh)); tab = np.maximum(0, 0.6 - W_[:, 2])
    return dep, tab


def apply(x):
    return pg + x[:3] / 100, (R.from_rotvec(np.radians(x[3:])) * R.from_quat(qg)).as_quat()


def cost(x):
    p, q = apply(x); dep, tab = pen(p, q)
    return 1e6 * (np.sum(dep ** 2) + np.sum(tab ** 2)) + np.sum(x[:3] ** 2) + np.sum((x[3:] / 5) ** 2) + 1e3 * max(0, np.linalg.norm(x[:3]) - 4) ** 2 + 1e3 * max(0, np.linalg.norm(x[3:]) - 15) ** 2


d0, t0 = pen(pg, qg)
res = dict(ep=ep, guest=g, host=h, before=dict(max_mm=round(1000 * float(d0.max()), 1), share=round(float((d0 > 0.0005).mean()), 3)))
best = None; rng = np.random.default_rng(0)
for k in range(0 if os.environ.get('SKIP_MIN') else 4):
    x0 = np.zeros(6) if k == 0 else np.r_[rng.normal(0, 1.0, 3), rng.normal(0, 3, 3)]
    r = minimize(cost, x0, method='Powell', options=dict(maxiter=1500, xtol=1e-2, ftol=1e-5))
    if best is None or r.fun < best.fun:
        best = r
if best is not None:
    p1, q1 = apply(best.x); d1, t1 = pen(p1, q1)
    res['minimal'] = dict(dt_mm=(10 * best.x[:3]).round(1).tolist(), drot_deg=best.x[3:].round(2).tolist(), dt_norm_mm=round(10 * float(np.linalg.norm(best.x[:3])), 1),
                          drot_norm_deg=round(float(np.linalg.norm(best.x[3:])), 2), after_max_mm=round(1000 * float(d1.max()), 2), after_share=round(float((d1 > 0.0005).mean()), 4),
                          table_pen_mm=round(1000 * float(t1.max()), 2), pose=np.r_[p1, q1].round(6).tolist())
# (b) GT-consistent relative pose (diagnostic)
T3D = f'{S}/loc/t3'; tab_ = pq.read_table(f'{T3D}/ep{ep}.parquet').to_pandas(); gn = [str(x['name']) for x in tab_['observation.objects'].iloc[0]]


def ideal(o):
    s = gn.index(o); q = f'{T3D}/mesh/{o}/{o}.glb'; q = q if os.path.exists(q) else f'{T3D}/mesh/{o}/{o}_visual.glb'
    m = trimesh.load(q, force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64); c, _ = _surface_moments(v, f)
    ca, Rb = T3._register_object_body(budget_mesh(f'{LIB}/{o}.glb', 4096, 4096), (v, f), c, 1_000_003 * ep + 101 * s)
    x = [y for y in tab_['observation.objects'].iloc[0] if y['name'] == o][0]; qq = np.array(x['pose'], float)
    Rg = R.from_quat(np.r_[qq[4:7], qq[3]]); Ri = Rg * R.from_matrix(Rb); return qq[:3] + Rg.apply(c) - Ri.apply(ca), Ri


pgI, RgI = ideal(g); phI, RhI = ideal(h)
rel_p = RhI.inv().apply(pgI - phI); rel_R = RhI.inv() * RgI
p2 = ph + R.from_quat(qh).apply(rel_p); q2 = (R.from_quat(qh) * rel_R).as_quat(); d2, t2 = pen(p2, q2)
res['gt_relative'] = dict(dt_mm=(1000 * (p2 - pg)).round(1).tolist(), drot_deg=round(float(rot_deg(q2, qg)), 2), after_max_mm=round(1000 * float(d2.max()), 2),
                          after_share=round(float((d2 > 0.0005).mean()), 4), table_pen_mm=round(1000 * float(t2.max()), 2), pose=np.r_[p2, q2].round(6).tolist())
json.dump(res, open(f'{W}/out/depen6_ep{ep}_{g}.json', 'w'), indent=1); print(json.dumps(res, indent=1))
