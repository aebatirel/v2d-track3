"""Start geometry at frame 0: our reference pose vs the ground-truth-consistent pose of OUR mesh.
PART A (no GT): for each object at the reference's frame 0: hull-vs-hull overlap with the other object (depth, share),
support on the table (hull points within 1 / 3 mm of the lowest point, COM projection inside the support hull?,
margin, tip angle), up direction in the object frame.
PART B (DIAGNOSTIC WITH GROUND TRUTH, after inference): the pose our mesh would have if our trajectory matched the
mocap exactly (via the kit's mesh registration to the public scan): the same quantities, plus the perception error
of our frame-0 pose (relative pose between the two objects, tilt of each object's up axis).
Usage: geom_audit.py EP [FRAME]"""
import sys, os, json, numpy as np, trimesh, pyarrow.parquet as pq, xml.etree.ElementTree as ET, glob
from scipy.spatial import ConvexHull
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments

ep = int(sys.argv[1]); fr = int(sys.argv[2]) if len(sys.argv) > 2 else 0
d = load_ref(ref_path(ep)); names = d['names']
H = {o: Hulls(hull_path(o)) for o in names}
HV = {o: np.concatenate([h.vertices for h in H[o].H]) for o in names}
HS = {}
for o in names:
    HS[o] = np.concatenate([trimesh.sample.sample_surface(h, max(20, int(6000 * h.area / sum(x.area for x in H[o].H))), seed=k)[0] for k, h in enumerate(H[o].H)])


def com_of(o):
    u = glob.glob(f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{o}_rigid.urdf') or [f'{S}/assets_v3/urdf/{o}_rigid.urdf']
    e = ET.parse(u[0]).getroot().find('link/inertial/origin'); return np.array([float(x) for x in e.get('xyz').split()])


COM = {o: com_of(o) for o in names}


def support(o, p, q, table_z=None):
    W = local_to_world(HV[o], p, q); z0 = W[:, 2].min() if table_z is None else table_z
    c = local_to_world(COM[o][None], p, q)[0]; res = dict(lowest_mm=round(1000 * (W[:, 2].min() - (0.6 if table_z is None else table_z)), 1), com_h_cm=round(100 * (c[2] - z0), 1))
    for tol in (0.001, 0.003, 0.01):
        P = W[W[:, 2] < W[:, 2].min() + tol][:, :2]
        if len(P) >= 3:
            try:
                ch = ConvexHull(P); eq = ch.equations; s = eq[:, :2] @ c[:2] + eq[:, 2]; inside = bool((s <= 0).all()); margin = float(-s.max())
                ext = P.max(0) - P.min(0)
            except Exception:
                inside, margin, ext = False, -np.inf, P.max(0) - P.min(0)
        else:
            inside, margin, ext = False, -np.inf, np.zeros(2)
        res[f'tol{int(tol*1000)}mm'] = dict(n=int(len(P)), patch_cm=[round(100 * float(x), 1) for x in ext], com_inside=inside,
                                           margin_mm=round(1000 * margin, 1) if np.isfinite(margin) else None,
                                           tip_deg=round(float(np.degrees(np.arctan2(margin, c[2] - z0))), 1) if inside else None)
    return res


def overlap(a, pa, qa, b, pb, qb):
    dep, out = H[b].depth(world_to_local(local_to_world(HS[a], pa, qa), pb, qb))
    return dict(max_mm=round(1000 * float(dep.max()), 1), share=round(float((dep > 0.0005).mean()), 3), p95_mm=round(1000 * float(np.percentile(dep[dep > 0], 95)), 1) if (dep > 0).any() else 0.0,
                min_gap_mm=round(1000 * float(out.min()), 1))


out = dict(ep=ep, frame=fr, ours={}, gt_consistent={})
P0 = {o: d['OP'][fr, j] for j, o in enumerate(names)}; Q0 = {o: d['OQ'][fr, j] for j, o in enumerate(names)}
for o in names:
    up = R.from_quat(Q0[o]).inv().apply([0, 0, 1])
    out['ours'][o] = dict(support=support(o, P0[o], Q0[o]), up_in_obj=[round(float(x), 3) for x in up])
    for o2 in names:
        if o2 != o:
            out['ours'][o][f'in_{o2}'] = overlap(o, P0[o], Q0[o], o2, P0[o2], Q0[o2])
# ---- PART B: ground truth (diagnostic only) ----
T3D = f'{S}/loc/t3'; tab = pq.read_table(f'{T3D}/ep{ep}.parquet').to_pandas()
gnames = [str(x['name']) for x in tab['observation.objects'].iloc[0]]


def gt_pose(o, f):
    x = [y for y in tab['observation.objects'].iloc[f] if y['name'] == o][0]; q = np.array(x['pose'], float); return q[:3], np.r_[q[4:7], q[3]]


def scan_path(n):
    q = f'{T3D}/mesh/{n}/{n}.glb'; return q if os.path.exists(q) else f'{T3D}/mesh/{n}/{n}_visual.glb'


IDEAL = {}
for s, o in enumerate(gnames):
    m = trimesh.load(scan_path(o), force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f)
    ca, Rb = T3._register_object_body(budget_mesh(f'{LIB}/{o}.glb', 4096, 4096), (v, f), c, 1_000_003 * ep + 101 * s)
    pg, qg = gt_pose(o, fr); Rg = R.from_quat(qg)
    Ri = Rg * R.from_matrix(Rb)                        # _convert: R_scan = R_ours @ Rb^T  =>  R_ours = R_gt @ Rb
    pi = pg + Rg.apply(c) - Ri.apply(ca)
    IDEAL[o] = (pi, Ri.as_quat())
# GT table height: lowest scan point over resting objects at this frame (assumes mocap z is vertical; checked below)
zt = []
for o in gnames:
    m = trimesh.load(scan_path(o), force='mesh'); pg, qg = gt_pose(o, fr); zt.append((R.from_quat(qg).apply(m.vertices) + pg)[:, 2].min())
table_gt = float(min(zt))
for o in names:
    pi, qi = IDEAL[o]; up = R.from_quat(qi).inv().apply([0, 0, 1]); upo = np.array(out['ours'][o]['up_in_obj'])
    out['gt_consistent'][o] = dict(support=support(o, pi, qi, table_z=table_gt), up_in_obj=[round(float(x), 3) for x in up],
                                   up_tilt_vs_ours_deg=round(float(np.degrees(np.arccos(np.clip(up @ upo, -1, 1)))), 1),
                                   scan_lowest_above_table_mm=round(1000 * (zt[gnames.index(o)] - table_gt), 1))
    for o2 in names:
        if o2 != o:
            out['gt_consistent'][o][f'in_{o2}'] = overlap(o, pi, qi, o2, *IDEAL[o2])
if len(names) == 2:
    a, b = names
    def rel(pa, qa, pb, qb):
        return R.from_quat(qa).inv().apply(pb - pa), R.from_quat(qa).inv() * R.from_quat(qb)
    ro = rel(P0[a], Q0[a], P0[b], Q0[b]); rg = rel(*IDEAL[a], *IDEAL[b])
    out['relative_pose_error'] = dict(of=f'{b} in {a} frame', pos_mm=[round(1000 * float(x), 1) for x in (ro[0] - rg[0])],
                                      pos_norm_mm=round(1000 * float(np.linalg.norm(ro[0] - rg[0])), 1),
                                      rot_deg=round(float(np.degrees((ro[1] * rg[1].inv()).magnitude())), 1))
out['gt_table_z'] = round(table_gt, 4)
json.dump(out, open(f'{W}/out/geom_ep{ep}_f{fr}.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
