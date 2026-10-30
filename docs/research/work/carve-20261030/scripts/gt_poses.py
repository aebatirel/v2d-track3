"""PUBLIC TWINS ONLY, diagnostics after inference: mocap ground-truth poses of OUR meshes (scratch, 2026-10-29).
The public parquet gives world_T_scan (scanned mesh frame). Our mesh is registered to the public scan with the kit's
own _register_object_body (as pipeline/score_registered.py does), giving the candidate anchor ca and rotation Rr with
  R_ours = R_scan Rr,  p_ours = p_scan + R_scan c_scan - R_ours ca      (c_scan = the scan's surface centroid).
Writes OUT.npz with T [F, B, 4, 4] in the reference's object order, plus the per-frame position / angle error of the
reference against it. Never used by inference; only by overlap / settle diagnostics on public twins.
Usage: gt_poses.py EP REF.parquet OURMESHDIR PUBLIC_DIR KIT_DIR OUT.npz"""
import json, sys

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

ep, ref, md, pub, kit, out = int(sys.argv[1]), *sys.argv[2:7]
sys.path.insert(0, kit)
from v2dlb import track3_pose as T3  # noqa: E402
from v2dlb.object_mesh import _surface_moments  # noqa: E402

row = pq.read_table(ref).to_pylist()[0]; names = list(row['object_body_names'])
tab = pq.read_table(f'{pub}/data/chunk-000/episode_{ep:06d}.parquet', columns=['observation.objects']).column(0).to_pylist()


def vf(p):
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)


nF = len(tab); T = np.tile(np.eye(4), (nF, len(names), 1, 1)); reg = {}
for s, n in enumerate(names):
    import os; scan = vf(next(x for x in (f'{pub}/mesh/{n}/{n}.glb', f'{pub}/mesh/{n}/{n}_visual.glb') if os.path.exists(x))); ours = vf(f'{md}/{n}/{n}.glb' if not md.endswith('.glb') else md)
    c_scan, _ = _surface_moments(*scan)
    ca, Rr = T3._register_object_body(ours, scan, c_scan, 1_000_003 * ep + 101 * s)
    reg[n] = dict(ca_cm=np.round(np.asarray(ca) * 100, 2).tolist(), rot_deg=round(float(R.from_matrix(Rr).magnitude() * 180 / np.pi), 2))
    for f in range(nF):
        o = [x for x in tab[f] if x['name'] == n][0]; q = np.array(o['pose'], float)
        Rs = R.from_quat(np.r_[q[4:7], q[3]]).as_matrix(); Ro = Rs @ Rr
        T[f, s, :3, :3] = Ro; T[f, s, :3, 3] = q[:3] + Rs @ c_scan - Ro @ ca
pos = np.array(row['object_body_position'], float); qq = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
F = min(nF, len(pos)); Tr = np.tile(np.eye(4), (F, len(names), 1, 1))
Tr[..., :3, :3] = R.from_quat(qq[:F].reshape(-1, 4)).as_matrix().reshape(F, len(names), 3, 3); Tr[..., :3, 3] = pos[:F]
# world frames differ (the kit aligns the scene once at frame 0), so compare the RELATIVE pose (object 1 in object 0)
rr = np.linalg.inv(Tr[:, 0]) @ Tr[:, 1]; rg = np.linalg.inv(T[:F, 0]) @ T[:F, 1]
err = {'rel': dict(pos_cm=np.round(np.linalg.norm(rr[:, :3, 3] - rg[:, :3, 3], axis=1) * 100, 2).tolist(),
                   deg=np.round(np.degrees(R.from_matrix(np.einsum('fij,fkj->fik', rr[:, :3, :3], rg[:, :3, :3])).magnitude()), 1).tolist())}
np.savez(out, T=T, names=np.array(names))
json.dump(dict(ep=ep, ref=ref, names=names, gt_frames=nF, ref_frames=len(pos), registration=reg, ref_vs_gt=err),
          open(out.replace('.npz', '.json'), 'w'))
print(json.dumps(dict(ep=ep, names=names, gt_frames=nF, ref_frames=len(pos), registration=reg,
                      ref_vs_gt_median={n: [float(np.median(e['pos_cm'])), float(np.median(e['deg']))] for n, e in err.items()})))
