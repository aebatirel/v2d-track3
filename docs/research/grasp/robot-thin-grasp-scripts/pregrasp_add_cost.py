"""ADD cost of pre-grasp object motions (tilt about an edge, in-plane yaw, slide) for our flat objects.

Analysis aid for the robot thin-object grasping report (2026-10-24). No ground truth is read: only our own
library_v3 meshes. The per-frame score uses the kit's ADD-AUC rule (thresholds 1..9 cm, trapezoid over 9 points),
so a frame's contribution is f(ADD) and the episode AUC is the mean of f over frames.

usage: python -I pregrasp_add_cost.py <library_dir> <out_json>
"""
import json
import sys

import numpy as np
import trimesh

THR = np.arange(0.01, 0.10, 0.01)
AX = np.linspace(0.0, 1.0, THR.size)


def frame_score(add_m: float) -> float:
    return float(np.trapezoid([(add_m < t) * 1.0 for t in THR], x=AX))


def rot(axis, ang):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * k + (1 - np.cos(ang)) * k @ k


def main():
    lib, out = sys.argv[1], sys.argv[2]
    names = ["wooden_piece_1", "wooden_piece_2", "mini_dust_pan", "mini_sweeper", "white_pot_lid"]
    res = {"rule": "frame score f(ADD) = trapz([ADD < t, t = 1..9 cm], x = linspace(0, 1, 9))",
           "f_of_add_cm": {str(a): frame_score(a / 100) for a in [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 9]}}
    rng = np.random.default_rng(0)
    for n in names:
        m = trimesh.load(f"{lib}/{n}.glb", force="mesh")
        pts, _ = trimesh.sample.sample_surface(m, 6000, seed=0)
        c = pts.mean(0)
        x = pts - c
        w, v = np.linalg.eigh(np.cov(x.T))
        v = v[:, ::-1]  # axis1 long, axis2 mid, axis3 thin (plate normal)
        p = x @ v  # PCA coordinates
        ext = p.max(0) - p.min(0)
        r = {"pca_extent_cm": (ext * 100).round(2).tolist()}
        # lying flat: thin axis = up. Tilt about the long edge (axis1 line at min axis2, bottom face)
        for label, hinge_axis, lever_dim in [("tilt_about_long_edge", 0, 1), ("tilt_about_short_edge", 1, 0)]:
            e = np.zeros(3)
            e[lever_dim] = p[:, lever_dim].min()
            e[2] = p[:, 2].min()
            ax = np.zeros(3)
            ax[hinge_axis] = 1.0
            row = {}
            for deg in [5, 10, 15, 20, 30, 45]:
                R = rot(ax, np.radians(deg))
                q = (p - e) @ R.T + e
                add = np.linalg.norm(q - p, axis=1).mean()
                row[str(deg)] = {"add_cm": round(add * 100, 2), "frame_score": round(frame_score(add), 3)}
            r[label] = row
        row = {}
        for deg in [5, 10, 20, 30, 45, 90]:
            R = rot([0, 0, 1], np.radians(deg))
            q = p @ R.T
            add = np.linalg.norm(q - p, axis=1).mean()
            row[str(deg)] = {"add_cm": round(add * 100, 2), "frame_score": round(frame_score(add), 3)}
        r["yaw_about_centroid"] = row
        res[n] = r
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
