"""verify_timing: is OUR frame-0 pose an outlier? (27 Oct 2026, CPU, GT-free except to pick objects at rest at the start)
Frame 0 of perc2 is the FoundationPose register() output; frames >= 1 come from track_one(). The kit aligns the scene
on frame 0, so a frame-0 orientation error rotates the whole episode. For every object whose mocap 1 cm onset is
>= 20 (at rest over frames 0-15): deviation of frames 0..4 from the mean pose of frames 5..15.
Usage: python -I vt_frame0.py OUT.json"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
from vt_checks import ang
from vt_shift import chordal_mean
from vt_lag import cross

C = L.canon(); rows = []
for ep in L.PUBLIC:
    if ep == 23:
        continue
    e = C[ep]; names, gt = L.load_mocap(ep); P = L.load_npz(f"{L.STORE}/{e['perception_path']}"); lib = L.lib_of(e, 'perc')
    for n in names:
        Pg = L.point_path(gt[n], L.surf_centroid(L.scan_mesh(n))); dg = np.linalg.norm(Pg - Pg[:5].mean(0), axis=1)
        t1 = cross(dg, 0.01)
        if t1 is not None and t1 < 20:
            continue
        M = P[n]; Po = L.point_path(M, L.surf_centroid(L.our_mesh(lib, n)))
        Rm = chordal_mean(M[5:16, :3, :3]); pm = Po[5:16].mean(0)
        Rgm = chordal_mean(gt[n][5:16, :3, :3])
        rows.append(dict(ep=ep, obj=n, rot_dev_deg=[round(float(ang(M[k, :3, :3], Rm)), 2) for k in range(5)],
                         pos_dev_mm=[round(float(np.linalg.norm(Po[k] - pm) * 1000), 2) for k in range(5)],
                         mocap_rot_dev_deg=[round(float(ang(gt[n][k, :3, :3], Rgm)), 3) for k in range(5)]))
R = np.array([r['rot_dev_deg'] for r in rows]); Pd = np.array([r['pos_dev_mm'] for r in rows]); G = np.array([r['mocap_rot_dev_deg'] for r in rows])
out = dict(n_objects=len(rows), rot_median=np.round(np.median(R, 0), 2).tolist(), rot_mean=np.round(R.mean(0), 2).tolist(),
           pos_median_mm=np.round(np.median(Pd, 0), 2).tolist(), pos_mean_mm=np.round(Pd.mean(0), 2).tolist(),
           mocap_rot_median=np.round(np.median(G, 0), 3).tolist(),
           frac_frame0_largest_rot=round(float(np.mean(R.argmax(1) == 0)), 2), objects=rows)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print({k: v for k, v in out.items() if k != 'objects'})
