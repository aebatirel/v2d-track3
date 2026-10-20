"""EVALUATION-ONLY oracle: replace perception's object poses with mocap, keep perception's camera trajectory.

Reads ground truth, so it must never feed an eval-episode submission; it refuses eval episode ids. Purpose: train a
policy on a perfect object reference to separate tracking error from robot/simulation error (STATUS.md, next action 3).
Mocap world -> perception world via one rigid transform fitted on the anchor object (default slot 0) at frame 0, the
same anchor the Track 3 metric warps from. Output has the perc2 poses.npz format: world_T_cam, cam_T_<name>.
Usage: python oracle_poses.py EP PERC_DIR OUT_DIR [--anchor NAME]       (written 2026-10-20, not yet run)
"""
import argparse, json, os, sys, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

EVAL = {1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38}
p = argparse.ArgumentParser()
p.add_argument('ep', type=int); p.add_argument('perc_dir'); p.add_argument('out_dir')
p.add_argument('--anchor', default=None); p.add_argument('--t3', default='/content/t3')
a = p.parse_args()
if a.ep in EVAL:
    sys.exit(f'episode {a.ep} is an eval episode: the oracle reads ground truth and is for public episodes only')

def T_of(pose):  # parquet pose is x, y, z, qw, qx, qy, qz
    T = np.eye(4); T[:3, :3] = Rot.from_quat([pose[4], pose[5], pose[6], pose[3]]).as_matrix(); T[:3, 3] = pose[:3]
    return T

P = np.load(f'{a.perc_dir}/poses.npz')
W_C = P['world_T_cam'].astype(np.float64); N = len(W_C)
tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()
names = [o['name'] for o in tab['observation.objects'].iloc[0]]
gt = {n: np.stack([T_of(np.array([o for o in row if o['name'] == n][0]['pose'], float))
                   for row in tab['observation.objects'].iloc[:N]]) for n in names}
assert all(len(v) == N for v in gt.values()), 'ground truth has fewer frames than the perception output'
anchor = a.anchor or names[0]
G = W_C[0] @ P[f'cam_T_{anchor}'][0] @ np.linalg.inv(gt[anchor][0])      # mocap world -> perception world
out = {'world_T_cam': W_C.astype(np.float32)}
check = {}
for n in names:
    out[f'cam_T_{n}'] = np.stack([np.linalg.inv(W_C[i]) @ G @ gt[n][i] for i in range(N)]).astype(np.float32)
    d = (W_C[0] @ P[f'cam_T_{n}'][0])[:3, 3] - (G @ gt[n][0])[:3, 3]
    check[n] = round(float(np.linalg.norm(d)) * 100, 2)                      # frame-0 perception vs oracle, cm
os.makedirs(a.out_dir, exist_ok=True)
np.savez(f'{a.out_dir}/poses.npz', **out)
for f in ('depths_fs0.5.npy',):                                              # hands/mkref read depth next to poses
    src = os.path.realpath(f'{a.perc_dir}/{f}')
    if os.path.exists(src) and not os.path.exists(f'{a.out_dir}/{f}'): os.symlink(src, f'{a.out_dir}/{f}')
info = {'episode': a.ep, 'anchor': anchor, 'objects': names, 'frames': N, 'frame0_perception_vs_oracle_cm': check,
        'note': 'EVALUATION-ONLY oracle built from mocap; never use for eval-episode inference'}
json.dump(info, open(f'{a.out_dir}/oracle.json', 'w'), indent=1)
print(json.dumps(info, indent=1))
