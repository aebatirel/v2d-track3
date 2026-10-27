"""CPU audit, stage 2 (public episodes, ground truth, diagnostics only): object-side facts that matter for the
reference and the scored start:
- frame-0 support of every object: on the table, resting on another object, or unsupported (held in a hand);
- carry segments (object moving: speed > 0.05 m/s or > 30 deg/s, gaps <= 5 frames merged, >= 5 frames long);
- simultaneous carries of two objects (two hands or a hand-over).
Table height 0.6012 m in the mocap frame (note 18). Mesh vertices from the public GLB scans, posed by the parquet pose.
Usage: python gt_objects.py <public data dir> <public mesh dir> <out.json>
"""
import glob, importlib.util, json, os, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
from scipy.signal import savgol_filter

spec = importlib.util.spec_from_file_location("cm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                                                 "carry_model.py"))
cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
TABLE_Z, DT = 0.6012, 1.0 / 20.0
data_dir, mesh_dir, out = sys.argv[1:4]
_mesh = {}


def verts(name):
    if name not in _mesh:
        m = trimesh.load(glob.glob(f"{mesh_dir}/{name}/*.glb")[0], force="mesh")
        v = np.asarray(m.vertices, float)
        if len(v) > 20000:
            v = v[np.random.default_rng(0).choice(len(v), 20000, replace=False)]
        _mesh[name] = v
    return _mesh[name]


def posed(name, p, q):                      # q wxyz
    return verts(name) @ Rot.from_quat([q[1], q[2], q[3], q[0]]).as_matrix().T + p


def segments(mask, gap=5, min_len=5):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    segs, s, e = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - e <= gap:
            e = i
        else:
            segs.append((s, e)); s = e = i
    segs.append((s, e))
    return [(int(a), int(b)) for a, b in segs if b - a + 1 >= min_len]


res = {}
for f in sorted(glob.glob(f"{data_dir}/episode_*.parquet")):
    ep, names, pos, quat = cm.load(f)
    P = {n: cm.fill(pos[:, j]) for j, n in enumerate(names)}
    Q = {n: cm.fill(quat[:, j]) for j, n in enumerate(names)}
    info = {"objects": names, "frames": int(len(pos)), "frame0": {}, "carries": {}}
    V0 = {n: posed(n, P[n][0], Q[n][0]) for n in names}
    for n in names:
        low = V0[n][:, 2].min() - TABLE_Z
        bottom = V0[n][V0[n][:, 2] < V0[n][:, 2].min() + 0.01]
        support, gap_other = "table" if abs(low) < 0.01 else None, None
        if support is None:
            for o in names:
                if o == n:
                    continue
                d, _ = cKDTree(V0[o]).query(bottom)
                if d.min() < 0.015:
                    support, gap_other = f"on {o}", float(d.min())
                    break
        if support is None:
            support = "unsupported (in hand?)" if low > 0 else "below table"
        info["frame0"][n] = {"lowest_above_table_cm": round(100 * low, 1), "support": support}
    moving = {}
    for n in names:
        x = P[n]; q = Q[n]
        v = savgol_filter(x, 9, 2, deriv=1, delta=DT, axis=0)
        w = savgol_filter(cm.ang_vel(q), 9, 2, axis=0)
        mv = (np.linalg.norm(v, axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
        moving[n] = mv
        segs = segments(mv)
        info["carries"][n] = [{"start": a, "end": b, "dur_s": round((b - a + 1) * DT, 2),
                               "lift_cm": round(100 * (P[n][a:b + 1, 2].max() - P[n][a, 2]), 1),
                               "moving_at_frame0": bool(a <= 2)} for a, b in segs]
    both = np.zeros(len(pos), bool)
    if len(names) == 2:
        both = moving[names[0]] & moving[names[1]]
    info["simultaneous_moving_frames"] = int(both.sum())
    res[ep] = info

json.dump(res, open(out, "w"), indent=1)
print("ep | frame-0 support | carry segments (start-end, s, lift cm) | frames with both objects moving")
for ep, info in res.items():
    f0 = "; ".join(f"{n}: {d['support']} ({d['lowest_above_table_cm']:+.1f} cm)" for n, d in info["frame0"].items())
    cs = "; ".join(f"{n}: " + ", ".join(f"{c['start']}-{c['end']} ({c['dur_s']} s, {c['lift_cm']} cm)"
                                        for c in segs) for n, segs in info["carries"].items() if segs)
    print(f"{ep:>2} | {f0} | {cs} | {info['simultaneous_moving_frames']}")
