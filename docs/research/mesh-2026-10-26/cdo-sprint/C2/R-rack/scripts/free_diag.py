#!/usr/bin/env python
"""C2 track R: GT-free free-space check of a rack mesh against the obs_points vote grids (hits / free per 4 mm voxel).

For every mesh surface sample: the voxel's hit-frames and free-frames (frames that saw through it) of each episode.
A sample is 'seen-empty' in an episode if free >= 3 and hits == 0 there (the obs_points vote: MIN_HITS 3), 'seen' if
hits >= 3, 'unseen' otherwise. Reported per rack region (rack frame from the build record), pooled over episodes.
Reads only obs_points npz files and our own mesh / build record.

Usage: free_diag.py --mesh M.glb --rec joint.json --obs a.npz,... --out OUT.json [--dump D.npz]
"""
import argparse, json, os
import numpy as np
import trimesh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mesh', required=True); ap.add_argument('--rec', required=True)
    ap.add_argument('--obs', required=True); ap.add_argument('--out', required=True); ap.add_argument('--dump', default=None)
    ap.add_argument('--n', type=int, default=200000)
    a = ap.parse_args()
    rec = json.load(open(a.rec))
    fr = {k: np.asarray(v) for k, v in rec['frame'].items()}
    Tm = np.asarray(rec['alignment']['mean_frame_T']) if 'alignment' in rec else np.eye(4)
    m = trimesh.load(a.mesh, force='mesh')
    S, fi = trimesh.sample.sample_surface(m, a.n, seed=0)
    Ti = np.linalg.inv(Tm)
    Q = S @ Ti[:3, :3].T + Ti[:3, 3] - fr['o']
    q = np.c_[Q @ fr['L'], Q @ fr['w'], Q @ fr['up']] * 1e3
    H = np.zeros(len(S), int); Fr = np.zeros(len(S), int); seen = np.zeros(len(S), int); empty = np.zeros(len(S), int)
    for f in a.obs.split(','):
        Z = np.load(f)
        lo = Z['lo']; vox = float(Z['vox']); hits = Z['hits']; free = Z['free']
        ijk = np.floor((S - lo) / vox).astype(int)
        ok = np.all((ijk >= 0) & (ijk < np.array(hits.shape)), axis=1)
        h = np.zeros(len(S), int); fr_ = np.zeros(len(S), int)
        h[ok] = hits[tuple(ijk[ok].T)]; fr_[ok] = free[tuple(ijk[ok].T)]
        H += h; Fr += fr_
        seen += h >= 3
        empty += (fr_ >= 3) & (h == 0)
    x, y, hh = q.T
    reg = np.full(len(q), 'other', dtype=object)
    reg[x < -125] = 'cup'
    reg[(x >= -125) & (y < -50)] = 'front_wall'
    reg[(x >= -125) & (y > 50)] = 'back_wall'
    reg[(x > 255) & (np.abs(y) <= 50)] = 'right_end'
    reg[(x >= -125) & (x <= 255) & (np.abs(y) <= 50) & (hh > 3)] = 'pegs/basin'
    reg[(x >= -125) & (x <= 255) & (np.abs(y) <= 50) & (hh <= 3)] = 'basin_low'
    neps = len(a.obs.split(','))
    out = dict(mesh=a.mesh, n=len(S), regions={})
    for r in ['cup', 'front_wall', 'back_wall', 'right_end', 'pegs/basin', 'basin_low']:
        k = reg == r
        out['regions'][r] = dict(frac_area=round(float(k.mean()), 4),
                                 seen_any=round(float(np.mean(seen[k] > 0)), 4),
                                 empty_any=round(float(np.mean(empty[k] > 0)), 4),
                                 empty_majority=round(float(np.mean(empty[k] > neps / 2)), 4),
                                 unseen_all=round(float(np.mean((seen[k] == 0) & (empty[k] == 0))), 4))
    out['all'] = dict(seen_any=round(float(np.mean(seen > 0)), 4), empty_any=round(float(np.mean(empty > 0)), 4),
                      empty_majority=round(float(np.mean(empty > neps / 2)), 4))
    json.dump(out, open(a.out, 'w'), indent=1)
    if a.dump:
        np.savez_compressed(a.dump, q=(q / 1e3).astype(np.float32), seen=seen.astype(np.int8), empty=empty.astype(np.int8),
                            H=H, F=Fr)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
