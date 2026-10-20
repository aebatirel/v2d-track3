"""DIG 18 B13 (public GT analysis only): is the GT world tilted per episode? The dish rack rests flat on the table in
eps 12, 13, 26, 27, 31; world-up expressed in the rack's own frame must then be the same in every episode (up to table
unevenness). Prints the per-episode angle from the mean. (b13_gt_base_tilt.py was a first attempt whose base-plane
detection picked a small vertex cluster; superseded by this test.)"""
import sys, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
ups = {}
for ep in [12, 13, 26, 27, 31]:
    e = c11.load_episode(ep); j = e["names"].index("plastic_dish_rack"); q = e["pose"][0, j]
    ups[ep] = c11.R_of(q[3:]).T @ np.array([0, 0, 1.0])
m = np.mean(list(ups.values()), 0); m /= np.linalg.norm(m)
for ep, u in ups.items(): print(ep, np.round(u, 4), "angle from mean up %.2f deg" % np.degrees(np.arccos(np.clip(u @ m, -1, 1))))
