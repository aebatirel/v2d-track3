"""DIG 18 B13 (analysis of public GT only): is the GT world level per episode? For each resting object with a flat
base (rack, pot, cups, pitcher), fit a plane to its scan's lowest vertices (object frame), rotate to the GT world at
frame 0 (and the last frame) and report the base-normal tilt from +z and its azimuth.
usage: python b13_gt_base_tilt.py <eps...>"""
import sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
BASE = {}
def base_normal(name):
    if name in BASE: return BASE[name]
    V = np.asarray(c11.glb_mesh(name).vertices)
    out = None
    for ax in range(3):
        for sg in (1, -1):
            z = sg * V[:, ax]; lo = V[z < z.min() + 0.002]
            if len(lo) < 30: continue
            c = lo.mean(0); _, s, vt = np.linalg.svd(lo - c); n = vt[2] * np.sign(vt[2][ax] * -sg)
            spread = np.sqrt(s[1] / len(lo)); rms = s[2] / np.sqrt(len(lo))
            if out is None or spread > out[1]: out = (n, spread, rms, ax, sg, len(lo))
    BASE[name] = out; return out
for ep in [int(e) for e in sys.argv[1:]]:
    e = c11.load_episode(ep)
    for j, n in enumerate(e["names"]):
        b = base_normal(n)
        if b is None: continue
        res = []
        for f in (0, len(e["frame"]) - 1):
            q = e["pose"][f, j]
            if not np.isfinite(q).all(): continue
            nw = c11.R_of(q[3:]) @ b[0]; tilt = np.degrees(np.arccos(np.clip(-nw[2], -1, 1)))
            res.append(f"f{f}: z {q[2]:.4f} tilt {tilt:.2f} az {np.degrees(np.arctan2(-nw[1], -nw[0])):.0f}")
        print(f"ep {ep:2d} {n:18s} base axis {'xyz'[b[3]]}{'+' if b[4] < 0 else '-'} spread {b[1]*100:.1f} cm rms {b[2]*1000:.2f} mm n {b[5]} | " + " | ".join(res))
