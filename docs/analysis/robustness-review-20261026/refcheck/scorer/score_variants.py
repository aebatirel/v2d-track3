"""Sensitivity of the local registered Track 3 score to our stand-ins for the hidden host geometry.

A re-implementation of pipeline/score_registered.py (commit 9eca613, md5 c2ec4af7...) that calls the same kit functions
(v2dlb.track3_pose, which are AST-identical to metric_code/track_3/*.py) but lets each stand-in vary:
  --anchor   centroid (default; scan surface centroid = what score_registered.py uses) | bbox (bounding-box centre)
             | vmean (vertex mean)
  --points   surface (default; area-uniform surface samples, seed 7+slot) | vertex (scan VERTICES drawn with
             default_rng(0).choice, the kit's documented ADD convention in v2dlb/vertices.py: 500, seed 0)
  --n_points 1000 (default)
  --axis     pca (default; cups: distinct principal axis, lid: thinnest) | z (cups: the scan's +z axis) | fit (cups: the
             direction that makes the scan most rotationally symmetric about the anchor, see fit_axis())
  --reg_seed_offset 0 (default; registration seed is 1_000_003*ep + 101*slot + offset)
  --scan_faces 0 (default: full public scan, ~100k faces) | N: the scan used for REGISTRATION is welded and decimated to
             N faces (as the packer's budget_mesh); anchor, points and axis stay from the full scan. The
             kit decodes the host geometry with a 16 MB limit, so the hidden scans cannot be full-resolution.
  --f0_from_ref 0 (default) | 1: results dirs only: the rollout's frame 0 is replaced by its reference's frame 0, so
             the kit's frame-0 scene alignment no longer sees the simulator's first-step transient.
Several variants run in one process: --variant NAME:key=val,key=val (repeatable). 'base' = all defaults.
Ground truth (public mocap) is read only here, for scoring. CPU only.
Usage: python -I score_variants.py EP SOURCE --meshes DIR --t3 T3 --kit KIT --out OUT.json --variant base
           --variant n4000:n_points=4000 --variant bbox:anchor=bbox ...
"""
import argparse, json, os, sys, time
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('ep', type=int)
p.add_argument('source')
p.add_argument('--meshes', default=None)
p.add_argument('--t3', required=True)
p.add_argument('--kit', required=True)
p.add_argument('--out', required=True)
p.add_argument('--variant', action='append', default=[])
p.add_argument('--trajs', default='', help='comma list of trajectories to score (default all)')
a = p.parse_args()
sys.path.insert(0, a.kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
METRICS = [('AUC', 'add_auc'), ('SP_SR', 'spider_sr'), ('MP_SR', 'maniptrans_sr'), ('MPPE_cm', 'mppe_cm'),
           ('RPE_cm', 'rpe_cm')]
DEFAULT = dict(anchor='centroid', points='surface', n_points=1000, axis='pca', reg_seed_offset=0, scan_faces=0,
               f0_from_ref=0)


def parse_variant(s):
    name, _, rest = s.partition(':')
    cfg = dict(DEFAULT)
    for kv in filter(None, rest.split(',')):
        k, v = kv.split('=')
        cfg[k] = type(DEFAULT[k])(v)
    return name, cfg


VARIANTS = [parse_variant(s) for s in (a.variant or ['base'])]


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


def load_vf(path):
    m = trimesh.load(path, force='mesh')
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def fit_axis(v, f, anchor, a0):
    """Direction (through the anchor) about which the scan is most rotationally symmetric: minimise the summed
    per-height-bin median absolute deviation of the radial distance (robust to marker attachments)."""
    pts = _sample_mesh_surface(v, f, 20000, 12345) - anchor
    a0 = a0 / np.linalg.norm(a0)
    e1 = np.cross(a0, [1.0, 0, 0]); e1 = e1 / np.linalg.norm(e1); e2 = np.cross(a0, e1)

    def cost(ax):
        ax = ax / np.linalg.norm(ax)
        h = pts @ ax; rho = np.linalg.norm(pts - h[:, None] * ax, axis=1)
        bins = np.linspace(h.min(), h.max(), 41); idx = np.digitize(h, bins)
        c = 0.0
        for b in np.unique(idx):
            r = rho[idx == b]
            if len(r) > 20:
                c += len(r) * np.median(np.abs(r - np.median(r)))
        return c / len(pts)
    best = (cost(a0), a0)
    for span, step in ((np.radians(6), np.radians(0.5)), (np.radians(0.6), np.radians(0.05))):
        centre = best[1]
        e1 = np.cross(centre, [1.0, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(centre, e1)
        g = np.arange(-span, span + 1e-12, step)
        for x in g:
            for y in g:
                ax = centre + np.tan(x) * e1 + np.tan(y) * e2
                c = cost(ax)
                if c < best[0]:
                    best = (c, ax / np.linalg.norm(ax))
    return best[1]


def host_geometry(n, slot, cfg):
    v, f = load_vf(scan_path(n))
    c, _ = _surface_moments(v, f)
    if cfg['anchor'] == 'bbox':
        c = (v.min(0) + v.max(0)) / 2
    elif cfg['anchor'] == 'vmean':
        c = v.mean(0)
    if cfg['points'] == 'surface':
        pts = _sample_mesh_surface(v, f, cfg['n_points'], 7 + slot) - c
    else:
        g = np.random.default_rng(0)
        pts = v[g.choice(len(v), size=cfg['n_points'], replace=len(v) < cfg['n_points'])] - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        # the axis is always derived from the default 1000 surface samples about the surface centroid, as in
        # score_registered.py, so that a points/anchor variant does not also change the axis
        c0, _ = _surface_moments(v, f)
        ps = _sample_mesh_surface(v, f, 1000, 7 + slot) - c0
        w, U = np.linalg.eigh(np.cov(ps.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            axis, order = U[:, k], 360
            if cfg['axis'] == 'z':
                axis = np.array([0.0, 0.0, 1.0]) * np.sign(axis[2] or 1)
            elif cfg['axis'] == 'fit':
                axis = fit_axis(v, f, c, axis)
    if cfg['scan_faces']:
        import fast_simplification                                     # weld first, as the kit's budget_mesh does:
        w = trimesh.Trimesh(v, f, process=True)                         # the public scans are unwelded triangle soups,
        v, f = fast_simplification.simplify(np.asarray(w.vertices, np.float64), np.asarray(w.faces, np.int64),
                                            target_count=cfg['scan_faces'])   # and a soup decimates badly (26 Oct: the
        v, f = np.asarray(v, np.float64), np.asarray(f, np.int64)       # first sens2 run did not weld; invalid)
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


def candidate_mesh(n):
    if a.meshes is None:
        return budget_mesh(scan_path(n), 4096, 4096)
    for q in (f'{a.meshes}/episode_{a.ep:06d}/{n}.glb', f'{a.meshes}/{n}.glb', f'{a.meshes}/{n}.obj',
              f'{a.meshes}/{n}.ply'):
        if os.path.exists(q):
            return budget_mesh(q, 4096, 4096)
    raise SystemExit(f'no candidate mesh for {n} under {a.meshes}')


tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
B = len(names)


def gt_xyzw(o):
    q = np.array(o['pose'], float)
    return np.r_[q[:3], q[4:7], q[3]]


trajs = {}
if a.source.endswith('.npz'):
    P = np.load(a.source)
    T = len(P[names[0]])
    trajs['perception'] = np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()]
                                     for n in names] for i in range(T)])
    frames = np.arange(T)
else:
    from v2dlb.submission_parquet import read_trajectory
    tr = read_trajectory(os.path.join(a.source, f'episode_{a.ep:06d}.parquet'))
    w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0])

    def grid(Q):
        G = np.full((len(frames), B, 7), np.nan)
        for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]):
            G[np.searchsorted(frames, fr), s] = q
        return G
    trajs['sim'] = grid(tr.pose_xyzw)
    if tr.reference_xyzw is not None:
        trajs['reference'] = grid(tr.reference_xyzw)
    trajs['static_floor'] = np.repeat(trajs['sim'][:1], len(frames), 0)
if a.trajs:
    trajs = {k: v for k, v in trajs.items() if k in a.trajs.split(',')}
gt = np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]) for n in names]
               for fr in frames])
CAND = [candidate_mesh(n) for n in names]
REG_CACHE = {}


def score(ach, H, REG):
    ach = ach[:, None].copy(); ref = gt[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    out = {k: round(float(T3._registered_pose_metric(m, ach, ref, pts, axes, orders)), 4) for k, m in METRICS}
    out['per_obj_AUC'] = {n: round(float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1],
                                                                   pts[s:s + 1], axes[s:s + 1], orders[s:s + 1])), 4)
                          for s, n in enumerate(names)}
    return out


res = {'episode': a.ep, 'objects': names, 'frames': int(len(frames)), 'meshes': a.meshes or 'public scans',
       'source': a.source, 'variants': {}}
for vname, cfg in VARIANTS:
    t0 = time.time()
    H = [host_geometry(n, s, cfg) for s, n in enumerate(names)]
    REG = []
    for s, n in enumerate(names):
        key = (s, cfg['reg_seed_offset'], tuple(np.round(H[s]['anchor'], 12)), cfg['scan_faces'])
        if key not in REG_CACHE:
            REG_CACHE[key] = T3._register_object_body(CAND[s], H[s]['mesh'], H[s]['anchor'],
                                                      1_000_003 * a.ep + 101 * s + cfg['reg_seed_offset'])
        REG.append(REG_CACHE[key])
    r = {'config': cfg,
         'registration': {n: {'rot_deg': round(float(np.degrees(Rot.from_matrix(REG[s][1]).magnitude())), 3),
                              'anchor_cm': np.round(H[s]['anchor'] * 100, 3).tolist(),
                              'axis': np.round(H[s]['axis'], 4).tolist(), 'order': H[s]['order']}
                          for s, n in enumerate(names)}}
    for k, v in trajs.items():
        if cfg['f0_from_ref'] and k == 'sim' and 'reference' in trajs:
            v = v.copy(); v[0] = trajs['reference'][0]
        r[k] = score(v, H, REG)
    r['seconds'] = round(time.time() - t0, 1)
    res['variants'][vname] = r
    print(vname, {k: r[k]['AUC'] for k in trajs}, r['seconds'], 's', flush=True)
json.dump(res, open(a.out, 'w'), indent=1)
