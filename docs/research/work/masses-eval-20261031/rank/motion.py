"""GT-free inputs for the masses eval-retrain ranking (2026-10-31, PLAN.md section 2).
For each stored eval reference (the files the packed policies were trained and evaluated on, as pulled by pack 6's box
runs/20261026-pack6-5203d42/refs; c01s43 / fr3233s43 / evb* copies are byte-identical, fp.py): object names, the URDF
paths the parquet names, md5, mass_arm.traj_fingerprint, and how far OUR perceived reference moves each object
(max displacement from frame 0, lift). Reads only our own reference files; no mocap, no episode `pose` field.
Usage: python -I motion.py <dir holding refs/> <repo>/tools <props_masses_only.json> > motion.json
"""
import glob, json, math, sys
import numpy as np, pyarrow.parquet as pq
sys.path.insert(0, sys.argv[2])
from mass_arm import md5, traj_fingerprint

props = json.load(open(sys.argv[3])); out = {}
for p in sorted(glob.glob(f'{sys.argv[1]}/refs/*/ep*/processed/*/*/*.parquet')):
    rel = 'refs/' + p.split('/refs/', 1)[1]; ep = int(rel.split('/')[2][2:])
    t = pq.read_table(p)
    names = t.column('object_body_names')[0].as_py(); pos = np.array(t.column('object_body_position')[0].as_py())
    objs = {}
    for i, n in enumerate(names):
        d = np.linalg.norm(pos[:, i] - pos[0, i], axis=1); m = props[n]['physics']['mass_kg']
        objs[n] = dict(mass_kg=m, ratio=round(m / 0.3, 3), abs_ln_ratio=round(abs(math.log(m / 0.3)), 2),
                       max_disp_cm=round(float(d.max()) * 100, 1), lift_cm=round(float((pos[:, i, 2] - pos[0, i, 2]).max()) * 100, 1))
    out[ep] = dict(reference=rel, md5=md5(p), traj_fingerprint=traj_fingerprint(t), frames=len(pos),
                   urdf_paths=t.column('object_urdf_paths')[0].as_py(), objects=objs)
print(json.dumps(dict(sorted(out.items())), indent=1))
