"""DIG 18 C13: express relocaliser outputs computed against map run3 (public-only) in run1 coordinates, which carry the
a13 mocap registration, using b2_align (X_run1 = Ra X_run3 + ta). Pure arithmetic on poses; reads no GT.
After this, every run1-based tool (c2_stats, c9_glitch, c6/c13 export) applies unchanged.
usage: python c13_to_run1.py <align json> <in prefix e.g. r3s5> <out prefix e.g. r3s5r1> [eps...]"""
import sys, json, os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(sys.argv[1])); Ra = np.array(A["Ra"]); ta = np.array(A["ta"]); PI, PO = sys.argv[2], sys.argv[3]
EV = [int(x) for x in sys.argv[4:]] or [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
T31 = np.eye(4); T31[:3, :3] = Ra.T; T31[:3, 3] = -Ra.T @ ta  # run1 coords -> run3 coords
KEYS = ("c_from_world", "a_from_world", "c_only_from_world", "b_from_world")
for e in EV:
    fi = f"{HERE}/c1/{PI}_e{e}.json"
    if not os.path.exists(fi): print(f"e{e}: missing"); continue
    D = json.load(open(fi))
    for r in D["frames"]:
        for k in KEYS:
            if k in r and r[k] is not None:
                T = np.eye(4); T[:3] = np.array(r[k]); r[k] = (T @ T31)[:3].tolist()
    D["frame_of_poses"] = f"run1 (converted from {D.get('model')} with {os.path.basename(sys.argv[1])})"
    json.dump(D, open(f"{HERE}/c1/{PO}_e{e}.json", "w"))
    print(f"e{e}: {len(D['frames'])} frames converted")
