"""V0 (verify_systematics): small bookkeeping checks, no AUC.
  a  capture_time jitter (frames) per public episode
  b  stored rollouts (ep2, 21, 24, 26, 39): step == reference_frame, start_frame, fps, and rollout reference columns vs
     the canonical reference parquet (does any stage after it change the object path?)
  c  box-stored score_registered reference AUC in the canonical results dirs
  d  mocap lowest scan point of each object over frames 0-9 (two objects at rest on the table => is mocap z the
     table normal?)
Usage: python -I v0_adhoc.py OUT.json"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V

out = {'capture_jitter': {}, 'rollouts': {}, 'box_scores': {}, 'mocap_low_first10': {}}
for ep in sorted(CE):
    t = pq.read_table(f'{T3D}/ep{ep}.parquet', columns=['timestamp', 'capture_time']).to_pandas()
    ct = t.capture_time.values - t.capture_time.values[0]; i = np.arange(len(ct)); p = np.polyfit(i, ct, 1)
    r = (ct - np.polyval(p, i)) / p[0]
    out['capture_jitter'][ep] = dict(mean_dt=round(float(p[0]), 5), timestamp_dt=round(float(np.median(np.diff(t.timestamp))), 6),
                                     resid_std_frames=round(float(r.std()), 3), resid_max_frames=round(float(np.abs(r).max()), 3))
    names, gt, _ = mocap(ep)
    lows = {}
    for n in names:
        sv, sf = V.vf(V.scanp(n)); hv = np.asarray(trimesh.Trimesh(sv, sf, process=False).convex_hull.vertices)
        zz = np.einsum('tij,vj->tvi', gt[n][:10, :3, :3], hv)[..., 2].min(1) + gt[n][:10, 2, 3]
        lows[n] = dict(z=round(float(np.median(zz)), 4), xy=np.round(gt[n][0, :2, 3], 3).tolist())
    out['mocap_low_first10'][ep] = lows
for ep in (2, 21, 24, 26, 39):
    e = CE[ep]; fs = sorted(glob.glob(f"{ST}/{e['results_dir']}/r*/episode_*.parquet")); ref = refparq(ref_final(ep)); rows = []
    for f in fs:
        md = {k.decode(): v.decode() for k, v in (pq.read_schema(f).metadata or {}).items()}
        tb = pq.read_table(f).to_pandas(); g = tb[tb.environment_id == tb.environment_id.min()]
        for n, gg in g.groupby('object_body_name', observed=True):
            gg = gg.sort_values('step')
            pp = gg[['reference_position_x', 'reference_position_y', 'reference_position_z']].values
            qq = gg[['reference_quaternion_x', 'reference_quaternion_y', 'reference_quaternion_z', 'reference_quaternion_w']].values
            M = ref[str(n)]
            rows.append(dict(file=f[len(ST) + 1:], obj=str(n), T=len(gg), step_eq_ref_frame=bool((gg.step.values == gg.reference_frame.values).all()),
                             steps_0_to_T=bool((gg.step.values == np.arange(len(gg))).all()), start_frame=md.get('flash_chord.start_frame'),
                             fps=md.get('flash_chord.control_fps'), step_count=md.get('flash_chord.step_count'),
                             ref_cols_vs_canonical_mm=round(float(np.linalg.norm(pp - M[:, :3, 3], axis=1).max() * 1000), 3),
                             ref_cols_vs_canonical_deg=round(float(np.degrees((R.from_quat(qq) * R.from_matrix(M[:, :3, :3]).inv()).magnitude()).max()), 3)))
    if True:
        for j in sorted(glob.glob(f"{ST}/{e['results_dir']}/r*/score_registered_ep{ep}.json")):
            d = json.load(open(j)); out['box_scores'].setdefault(ep, []).append(dict(run=j.split('/')[-2], reference_AUC=d.get('reference', {}).get('AUC'),
                                                                                  sim_AUC=d.get('sim', {}).get('AUC'), meshes=d.get('meshes')))
    out['rollouts'][ep] = rows
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print(json.dumps({k: (v if k != 'rollouts' else {e: (len(r), all(x['step_eq_ref_frame'] and x['steps_0_to_T'] for x in r), max(x['ref_cols_vs_canonical_mm'] for x in r)) for e, r in v.items()}) for k, v in out.items()})[:3000])
