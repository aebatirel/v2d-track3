"""Guided second detection pass (GT-free): look for each marker where the current pose predicts it.

Pose per frame = the census fix when >= 2 markers were labelled (then the window is small, 12 mm, because the missing
marker can only move by the unobserved rotation), else our perc2 track (window 30 mm). Inside each window detect.stereo
runs with relaxed appearance thresholds (support 0.30, interior sd 20, black-base contrast 10); new stereo detections
(> 3 mm from existing ones) are appended to the frame's detection list. census.py then re-labels with the layout
distances, so a relaxed false detection only counts if it is layout-consistent.
Inputs: videos, calibration, perc2 track, census fix file. No ground truth, no scan.
Usage: python guided.py SPLIT EP OBJ   (reads scan/<split><ep>_<obj>.json, writes scan/<split><ep>_<obj>_g.json)
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import mlib, detect


def main():
    split, ep, obj = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    t0 = time.time(); S = mlib.S
    J = json.load(open(f'{S}/mk/scan/{split}{ep}_{obj}.json'))
    F = np.load(f'{S}/mk/scan/fix_{split}{ep}_{obj}.npz'); Lb = F['layout']
    rig = mlib.Rig(); rc, rb = mlib.rectified(rig, split, ep)
    T = np.load(mlib.poses_path(split, ep))[f'cam_T_{obj}'].astype(np.float64)
    N = min(J['N'], len(F['n'])); added = 0
    for t in range(N):
        fixed = F['n'][t] >= 2 and np.all(np.isfinite(F['fix'][t]))
        P = F['fix'][t] if fixed else T[t]
        X = Lb @ P[:3, :3].T + P[:3, 3]
        if np.any(X[:, 2] < 0.15):
            continue
        uL, _ = rig.proj(X); have = np.array([d['X'] for d in J['dets'][t]]) if J['dets'][t] else np.zeros((0, 3))
        for j in range(len(Lb)):
            if len(have) and np.linalg.norm(have - X[j], axis=1).min() < 0.004:
                continue
            w = rig.FR * (0.012 if fixed else 0.03) / X[j, 2]
            rect = (int(uL[j, 0] - w), int(uL[j, 1] - w), int(uL[j, 0] + w), int(uL[j, 1] + w))
            if rect[0] < 0 or rect[1] < 0 or rect[2] > 1599 or rect[3] > 999:
                continue
            dz = 0.02 if fixed else 0.05
            for d in detect.stereo(rig, rc[t], rb[t], rect, (X[j, 2] - dz, X[j, 2] + dz), J['dv0'], 1.5, k=6,
                                   min_sup=0.30, max_isd=20.0, min_dark=10.0):
                Xd = np.array(d['X'])
                if len(have) and np.linalg.norm(have - Xd, axis=1).min() < 0.003:
                    continue
                d['guided'] = 1; J['dets'][t].append(d); have = np.vstack([have, Xd[None]]); added += 1
    J['guided'] = dict(added=added, seconds=round(time.time() - t0, 1))
    json.dump(J, open(f'{S}/mk/scan/{split}{ep}_{obj}_g.json', 'w'))
    print(f'{split} ep{ep} {obj}: guided pass added {added} detections ({time.time() - t0:.0f} s)', flush=True)


if __name__ == '__main__':
    main()
