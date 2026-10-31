"""Frame mask for obs_points.py output (GT-free): keep only the points of frames chosen from frame_census.py.
lathe_obs.py has no frame option; it reads only 'pts' and 'cam', so filtering the npz is equivalent to a frame mask.
Rules: sep   = near_blue_frac < 0.5 (beige cup not nested in the blue cup along our tracks)
       sephf = sep and nearest hand joint >= 30 mm from the beige surface (obs_points hand_r)
Usage: mask_obs.py OBS.npz CENSUS.json RULE OUT.npz
"""
import json, sys
import numpy as np

obs, census, rule, out = sys.argv[1:5]
rows = json.load(open(census))
keep = []
for r in rows:
    sep = r['near_blue_frac'] < 0.5
    hf = r['hand_mm'] is None or r['hand_mm'] >= 30.0
    if (rule == 'sep' and sep) or (rule == 'sephf' and sep and hf) or rule == 'all':
        keep.append(r['t'])
keep = np.array(sorted(keep))
Z = np.load(obs)
m = np.isin(Z['frame'], keep)
d = {k: Z[k] for k in Z.files}
d['pts'], d['cam'], d['frame'] = Z['pts'][m], Z['cam'][m], Z['frame'][m]
d['mask'] = json.dumps(dict(rule=rule, frames=keep.tolist(), census=census, src=obs))
np.savez_compressed(out, **d)
print(json.dumps(dict(rule=rule, n_frames_kept=int(len(keep)), frames=f'{keep.min()}..{keep.max()}',
                      pts_in=int(len(Z['pts'])), pts_out=int(m.sum()))))
