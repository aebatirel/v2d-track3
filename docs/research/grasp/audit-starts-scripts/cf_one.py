"""DIAGNOSTIC WITH GROUND TRUTH (mocap + public scans; after inference, reporting only): official-style registered
ADD-AUC (kit v2dlb.track3_pose, as pipeline/score_registered.py: our library meshes registered to the public scans,
scene aligned once at frame 0, cup axis / lid half-turn symmetries) of the policy rollouts, split EXACTLY into frame
windows (the AUC per object is the mean over frames of a per-frame score g(ADD), so the loss is additive over frames),
plus counterfactuals where windows of the simulated trajectory are replaced by our reference.
Usage: cf_one.py EP ROLLOUT_PARQUET...   (zero: also score the zero-action traces zero.npz / zero_r1.npz)"""
import sys, os, glob, json, numpy as np, trimesh, pyarrow.parquet as pq
from pathlib import Path
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.object_pose import _ADD_THRESHOLDS_M
from v2dlb.mesh_common import _sample_mesh_surface
from v2dlb.submission_parquet import read_trajectory

ep = int(sys.argv[1]); T3D = f'{S}/loc/t3'
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
tab = pq.read_table(f'{T3D}/ep{ep}.parquet').to_pandas(); names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]; B = len(names)


def scan_path(n):
    q = f'{T3D}/mesh/{n}/{n}.glb'; return q if os.path.exists(q) else f'{T3D}/mesh/{n}/{n}_visual.glb'


def host(n, slot):
    m = trimesh.load(scan_path(n), force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f); pts = _sample_mesh_surface(v, f, 1000, 7 + slot) - c; axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


H = [host(n, s) for s, n in enumerate(names)]
REG = [T3._register_object_body(budget_mesh(f'{LIB}/{n}.glb', 4096, 4096), H[s]['mesh'], H[s]['anchor'], 1_000_003 * ep + 101 * s) for s, n in enumerate(names)]
gl = json.load(open(glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/processed/*/*/ref_gl_grasp_lock.json')[0]))
h0 = {n: min([p['hold_from'] for p in gl['phases'] if p['object'] == n], default=None) for n in names}
first_any = min(v for v in h0.values() if v is not None)


def gt_xyzw(o):
    q = np.array(o['pose'], float); return np.r_[q[:3], q[4:7], q[3]]


def g_of(add):  # per-frame AUC contribution (trapezoid over the kit's thresholds), so AUC = mean over frames
    x = np.linspace(0, 1, _ADD_THRESHOLDS_M.size); ind = (add[:, None] < _ADD_THRESHOLDS_M[None]).astype(float)
    return np.trapezoid(ind, x=x, axis=1) if hasattr(np, 'trapezoid') else np.trapz(ind, x=x, axis=1)


def per_frame(ach, gt):
    a = ach[:, None].copy(); r = gt[:, None].copy()
    for s in range(B):
        a[:, :, s] = T3._convert_object_body(a[:, :, s], *REG[s])
        r[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(r[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]
    a = T3._align_registered_scene(a, r, axes)
    add = np.stack([T3._symmetry_point_errors(a[:, :, s], r[:, :, s], H[s]['points'], axes[s], orders[s])[:, 0] for s in range(B)], 1)
    tot = float(T3._registered_pose_metric('add_auc', a, r, [h['points'] for h in H], axes, orders))
    return add, tot


def analyse(label, sim, ref, gt, frames):
    T = len(frames); out = dict(label=label)
    add, tot = per_frame(sim, gt); g = np.stack([g_of(add[:, s]) for s in range(B)], 1)
    out['AUC'] = round(tot, 4); out['AUC_check'] = round(float(g.mean()), 4)
    out['per_obj'] = {}
    for s, n in enumerate(names):
        a = h0[n] if h0[n] is not None else T
        w = dict(pre=(0, a), hold_on=(a, T))
        lo = {k: round(float((1 - g[b:e, s]).sum() / T), 4) for k, (b, e) in w.items()}
        out['per_obj'][n] = dict(AUC=round(float(g[:, s].mean()), 4), loss=lo, first_hold=a,
                                 add_cm_pre=round(100 * float(add[:a, s].mean()), 2) if a > 0 else None,
                                 add_cm_hold=round(100 * float(add[a:, s].mean()), 2) if a < T else None)
    # counterfactuals (replace windows of the simulated trajectory with our reference)
    cfs = {'reference': [(s, 0, T) for s in range(B)], 'f0_only': [(s, 0, 1) for s in range(B)],
           'pre_first_hold_all': [(s, 0, first_any) for s in range(B)],
           'pre_own_hold': [(s, 0, h0[n] if h0[n] is not None else T) for s, n in enumerate(names)],
           'hold_on_all': [(s, h0[n], T) for s, n in enumerate(names) if h0[n] is not None]}
    for s, n in enumerate(names):
        cfs[f'{n}_all'] = [(s, 0, T)]
        if h0[n] is not None:
            cfs[f'{n}_pre'] = [(s, 0, h0[n])]; cfs[f'{n}_hold_on'] = [(s, h0[n], T)]
    out['cf'] = {}
    for k, reps in cfs.items():
        x = sim.copy()
        for s, b, e in reps:
            x[b:e, s] = ref[b:e, s]
        out['cf'][k] = round(per_frame(x, gt)[1], 4)
    out['cf']['floor'] = round(per_frame(np.repeat(sim[:1], T, 0), gt)[1], 4)
    return out


def gt_for(frames):
    return np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[min(fr, len(tab) - 1)] if o['name'] == n][0]) for n in names] for fr in frames])


res = []
for rp in sys.argv[2:]:
    tr = read_trajectory(Path(rp)); w0 = tr.world_index == tr.world_index.min(); frames = np.unique(tr.frame_index[w0])
    def grid(Q):
        G = np.full((len(frames), B, 7), np.nan)
        for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]):
            G[np.searchsorted(frames, fr), s] = q
        return G
    sim, ref = grid(tr.pose_xyzw), grid(tr.reference_xyzw); gt = gt_for(frames)
    add, tot = per_frame(sim, gt); g = np.stack([g_of(add[:, s]) for s in range(B)], 1)
    a2, t2 = per_frame(ref, gt); g2 = np.stack([g_of(a2[:, s]) for s in range(B)], 1)
    print(rp.split('/')[-2], 'AUC %.4f' % tot, {n: round(float(g[:, s].mean()), 4) for s, n in enumerate(names)}, '| reference AUC %.4f' % t2, {n: round(float(g2[:, s].mean()), 4) for s, n in enumerate(names)}, flush=True)
