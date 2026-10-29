"""Evaluate reconstructed meshes against the public scans (diagnostic, public episodes only, after inference).

For each <obj>.glb in RECON_DIR: kit CD-O (Sim(3)-registered symmetric Chamfer, cm; v2dlb.object_mesh), the kit
registration of the mesh to the scan (rotation and anchor shift; a large rotation means a flip; symmetry-aware for cups and lid), extents, and a
4-view picture (scan grey, ours red). The registration is repeated with --seeds sampling seeds (seed 0 = the
official one for this episode and slot); flip_rate = share of seeds whose rotation exceeds 30 deg (the hidden scan's
own sampling differs from ours, so a near-tie is a coin toss at Kaggle). Then, if POSES (poses_world_vo.npz) is given, the registered AUC of that
perception trajectory with our meshes vs with the scans (score_registered.py).
Usage: python recon_eval.py EP RECON_DIR [--poses NPZ] [--t3 ..] [--kit ..]
"""
import argparse, json, os, subprocess, sys
import numpy as np, trimesh

p = argparse.ArgumentParser(); p.add_argument('ep', type=int); p.add_argument('recon')
p.add_argument('--poses'); p.add_argument('--t3', default='/content/t3'); p.add_argument('--seeds', type=int, default=8); p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
a = p.parse_args()
sys.path.insert(0, a.kit)
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_budget import budget_mesh
from v2dlb import track3_pose as T3
import importlib.util
spec = importlib.util.spec_from_file_location('cdo', f'{a.kit}/metric_code/track_3/CD-O.py'); CDO = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CDO)


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


import pyarrow.parquet as pq
names = [str(o['name']) for o in pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()['observation.objects'].iloc[0]]
out = {}
objs = sorted(f[:-4] for f in os.listdir(a.recon) if f.endswith('.glb') and not f.endswith('_full.glb'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(len(objs), 4, figsize=(16, 4 * len(objs)), squeeze=False)
for i, n in enumerate(objs):
    ref = budget_mesh(scan_path(n), 4096, 4096); cand = budget_mesh(f'{a.recon}/{n}.glb', 4096, 4096)
    slot = names.index(n) if n in names else 0
    cd = CDO._object_chamfer_cm(ref, cand, 1_000_003 * a.ep + 101 * slot)
    rc, _ = _surface_moments(*ref)
    from scipy.spatial.transform import Rotation as Rot
    # symmetry as scored (README): cups = spin about the central axis is free (error = axis tilt); lid = 180 deg about
    # its normal is free. Axes from the scan's principal directions, as in score_registered.py.
    pts = trimesh.sample.sample_surface(trimesh.Trimesh(*ref, process=False), 4000, seed=0)[0]
    w_, U_ = np.linalg.eigh(np.cov((pts - pts.mean(0)).T))
    def sym_err(R_k):
        if n in ('beige_cup', 'blue_cup'):
            k_ = int(np.argmax([abs(w_[i] - np.mean(np.delete(w_, i))) for i in range(3)])); ax_ = U_[:, k_]
            return float(np.degrees(np.arccos(np.clip(abs(ax_ @ R_k @ ax_), -1, 1))))
        e = float(np.degrees(Rot.from_matrix(R_k).magnitude()))
        if n == 'white_pot_lid':
            e = min(e, float(np.degrees((Rot.from_matrix(R_k) * Rot.from_rotvec(np.pi * U_[:, 0])).magnitude())))
        return e
    rots = []                     # registration over several sampling seeds: a near-tie flips with the samples
    for k in range(a.seeds):
        ca_k, R_k = T3._register_object_body(cand, ref, rc, 1_000_003 * a.ep + 101 * slot + 7919 * k)
        rots.append(sym_err(R_k))
        if k == 0:
            ca, R = ca_k, R_k     # k = 0 is the official seed (episode, slot)
    out[n] = dict(cd_o_cm=round(float(cd), 3), reg_rot_deg=round(rots[0], 2),
                  flip_rate=round(float(np.mean(np.array(rots) > 30)), 2), rot_deg_max=round(max(rots), 1),
                  reg_anchor_shift_cm=round(float(np.linalg.norm(ca - rc) * 100), 2),
                  extents_ours_cm=np.round(np.ptp(cand[0], 0) * 100, 1).tolist(),
                  extents_scan_cm=np.round(np.ptp(ref[0], 0) * 100, 1).tolist())
    rs = trimesh.sample.sample_surface(trimesh.Trimesh(*ref, process=False), 4000, seed=0)[0]
    cs = trimesh.sample.sample_surface(trimesh.Trimesh(*cand, process=False), 4000, seed=0)[0]
    for j, (u, v, lab) in enumerate([(0, 1, 'x-y'), (0, 2, 'x-z'), (1, 2, 'y-z')]):
        ax[i, j].scatter(rs[:, u], rs[:, v], s=0.3, c='0.6'); ax[i, j].scatter(cs[:, u], cs[:, v], s=0.3, c='r')
        ax[i, j].set_aspect('equal'); ax[i, j].set_title(f'{n} {lab}')
    ax[i, 3].axis('off'); ax[i, 3].text(0, 0.5, json.dumps(out[n], indent=1), fontsize=8, family='monospace')
plt.tight_layout(); plt.savefig(f'{a.recon}/recon_vs_scan.png', dpi=60)
if a.poses:
    S = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'score_registered.py')
    for tag, extra in [('scan', []), ('ours', ['--meshes', a.recon])]:
        o = f'{a.recon}/registered_{tag}.json'
        subprocess.run([sys.executable, '-I', S, str(a.ep), a.poses, '--t3', a.t3, '--kit', a.kit, '--out', o, *extra],
                       check=True, stdout=subprocess.DEVNULL)
        r = json.load(open(o))['perception']; out[f'AUC_with_{tag}'] = r['AUC']; out[f'per_obj_with_{tag}'] = r['per_obj_AUC']
json.dump(out, open(f'{a.recon}/recon_eval.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
