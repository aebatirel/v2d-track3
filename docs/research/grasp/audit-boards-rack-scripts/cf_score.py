"""DIAGNOSTIC WITH GROUND TRUTH (after inference): official-style registered scoring (kit v2dlb.track3_pose, as
pipeline/score_registered.py; public scans as the hidden geometry) of rollouts and COUNTERFACTUALS where parts of the
simulated trajectory are replaced by our reference: tells how much of the loss sits in which object / phase.
Usage: cf_score.py KIT T3 EP MESHDIR SPECS_JSON ROLLOUT_DIR...  SPECS = {"label": [[slot, f_from, f_to], ...], ...}"""
import sys, os, json, numpy as np, trimesh, pyarrow.parquet as pq
kit, t3, ep, meshdir, specs = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], json.loads(sys.argv[5]); rolls = sys.argv[6:]
sys.path.insert(0, kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
from v2dlb.submission_parquet import read_trajectory
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
def scan_path(n):
    q = f'{t3}/mesh/{n}/{n}.glb'; return q if os.path.exists(q) else f'{t3}/mesh/{n}/{n}_visual.glb'
def load_vf(p):
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
tab = pq.read_table(f'{t3}/ep{ep}.parquet').to_pandas(); names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]; B = len(names)
H = []
for s, n in enumerate(names):
    v, f = load_vf(scan_path(n)); c, _ = _surface_moments(v, f); pts = _sample_mesh_surface(v, f, 1000, 7 + s) - c
    H.append(dict(mesh=(v, f), anchor=c, points=pts, axis=np.zeros(3), order=0))
REG = [T3._register_object_body(budget_mesh(f'{meshdir}/{n}.glb', 4096, 4096), H[s]['mesh'], H[s]['anchor'], 1_000_003 * ep + 101 * s) for s, n in enumerate(names)]
def gt_xyzw(o):
    q = np.array(o['pose'], float); return np.r_[q[:3], q[4:7], q[3]]
def score(ach, gt):
    ach = ach[:, None].copy(); ref = gt[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    tot = float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders))
    per = [float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1], pts[s:s + 1], axes[s:s + 1], orders[s:s + 1])) for s in range(B)]
    return tot, per
allres = {}
for rd in rolls:
    tr = read_trajectory(os.path.join(rd, f'episode_{ep:06d}.parquet')); w0 = tr.world_index == tr.world_index.min(); frames = np.unique(tr.frame_index[w0])
    def grid(Q):
        G = np.full((len(frames), B, 7), np.nan)
        for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]): G[np.searchsorted(frames, fr), s] = q
        return G
    sim, ref = grid(tr.pose_xyzw), grid(tr.reference_xyzw)
    gt = np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]) for n in names] for fr in frames])
    res = {}
    for lab, reps in [('sim', []), ('reference', 'REF'), ('floor', 'FLOOR')] + list(specs.items()):
        if reps == 'REF': a = ref.copy()
        elif reps == 'FLOOR': a = np.repeat(sim[:1], len(frames), 0)
        else:
            a = sim.copy()
            for s, f0, f1 in reps: a[f0:f1, s] = ref[f0:f1, s]
        tot, per = score(a, gt); res[lab] = dict(AUC=round(tot, 4), per={n: round(p, 4) for n, p in zip(names, per)})
    allres[os.path.basename(rd.rstrip('/'))] = res
    print(os.path.basename(rd.rstrip('/')), json.dumps(res))
json.dump(allres, open(sys.argv[0].replace('.py', f'_ep{ep}.json').replace('scripts/', 'out/'), 'w'), indent=1)
