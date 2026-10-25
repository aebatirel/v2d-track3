"""Interaction-infeasibility census over eval references (GT-free): approach-1 study, 2026-10-25.

For each two-object eval episode: the simulator meshes of the packed reference (refs/sf/epN/assets, i.e. library_v3 plus
support fills) posed by the reference the policy was trained to follow (ref_sf.parquet). Per frame (stride STRIDE):
mesh-mesh overlap volume (mean of both directions) and the deepest penetration. Reports frame-0 values (the simulator
starts there exactly: a start jolt), the maximum, frames above 1 cm3, the longest run above 1 cm3 (persistent contact),
and the overlap while both objects are still (relative motion < 2 mm / frame) after frame 0. Mesh overlap is a lower
bound on what the simulator sees (CoACD hulls add volume; eval 25: hulls 13.7 vs mesh 10.3 cm3).
Usage: python eval_census.py ROOT OUT.json   (ROOT/<run>/refs/sf/epN/...)"""
import glob, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pair_overlap as po  # noqa: E402

STRIDE = 2
root, out = sys.argv[1:3]
res = {}
for ref in sorted(glob.glob(f'{root}/**/ref_sf.parquet', recursive=True)):
    import pyarrow.parquet as pq
    row = pq.read_table(ref, columns=['object_body_names']).to_pylist()[0]
    names = list(row['object_body_names'])
    ep = ref.split('/refs/sf/')[1].split('/')[0]; run = ref.split('/runs/')[1].split('/')[0]
    if len(names) != 2:
        continue
    base = ref.split('/processed/')[0]
    meshes = [f'{base}/assets/mesh/{n}/{n}.glb' for n in names]
    if not all(os.path.exists(m) for m in meshes):
        print(ep, 'missing mesh', flush=True); continue
    mA, mB = po.load_mesh(meshes[0]), po.load_mesh(meshes[1]); sA, sB = po.SD(mA), po.SD(mB)
    SA, _ = po.solid(mA, sA); SB, _ = po.solid(mB, sB); v = po.PITCH ** 3 * 1e6
    TA, TB = po.load_poses(ref, *names)
    F = list(range(0, len(TA), STRIDE)); ov, pen, rel = [], [], []
    for t in F:
        T = np.linalg.inv(TB[t]) @ TA[t]; Ti = np.linalg.inv(T); rel.append(Ti[:3, 3])
        dA = sB(SA @ T[:3, :3].T + T[:3, 3]); dB = sA(SB @ Ti[:3, :3].T + Ti[:3, 3])
        ov.append(((dA < 0).sum() + (dB < 0).sum()) / 2 * v)
        pen.append(float(-min(dA.min(), dB.min(), 0.0)) * 1e3)
    ov, pen, rel = np.array(ov), np.array(pen), np.array(rel)
    still = np.r_[False, np.linalg.norm(np.diff(rel, axis=0), axis=1) * 1e3 / STRIDE < 2.0]
    above = ov > 1.0; runs, cur = [], 0
    for a in above:
        cur = cur + 1 if a else 0; runs.append(cur)
    key = f'{ep} ({run.split("-")[1]})'
    res[key] = dict(objects=names, frames=len(TA), f0_overlap_cm3=round(float(ov[0]), 2), f0_pen_mm=round(float(pen[0]), 1),
                    max_overlap_cm3=round(float(ov.max()), 2), max_at_frame=int(F[int(ov.argmax())]), max_pen_mm=round(float(pen.max()), 1),
                    frames_gt1cm3=int(above.sum() * STRIDE), longest_run_frames=int(max(runs) * STRIDE),
                    still_overlap_median_cm3=round(float(np.median(ov[still & above])), 2) if (still & above).any() else 0.0,
                    still_frames_gt1cm3=int((still & above).sum() * STRIDE), solids_cm3=[round(len(SA) * v, 1), round(len(SB) * v, 1)])
    print(key, res[key], flush=True)
json.dump(res, open(out, 'w'), indent=1)
