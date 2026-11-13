"""Rest-averaged anchor orientation in a reference (2 Nov 2026, perfect-following lane; docs/research/work/
pf-anchor-20261102/PREREG.md). GT-free: our reference + the raw tracker (perc2 poses.npz) + our mesh.

The kit aligns the whole achieved scene on the anchor's frame-0 orientation (docs/research/spoon-2026-10-25/README.md);
the rollout's frame 0 is the reference's frame 0. This replaces the anchor object's orientation over its initial rest
with the raw tracker's rest-averaged orientation, the estimator (b) of tools/anchor_f0_test.py:
  onset = first frame whose anchor position is > 1 cm from frame 0 (reference); rest = frames < min(onset, REST_MAX) with
  a finite raw pose; Rraw_t = world_T_cam_t @ cam_T_<obj>_t; W = chordal mean over frames t >= onset + 10 of
  Rref_t Rraw_t^-1 (the raw -> reference rotation); Rnew = W * chordal_mean(Rraw_rest).
Frames < onset: orientation := Rnew; position z shifted so the mesh's lowest point keeps its old height (per frame;
x, y unchanged). Frames onset .. onset + RAMP - 1: the frame-(onset-1) correction C = Rnew Rref_{onset-1}^-1 (and its dz)
fades linearly to identity (R'_t = slerp(I, C, w) Rref_t). Every other column and object is byte-unchanged.
Usage: anchor_rest.py REF.parquet POSES.npz MESH OUT.parquet --obj wooden_spoon [--ramp 10] [--rest_max 30] [--json J]
"""
import argparse, json
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot, Slerp

ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('poses'); ap.add_argument('mesh'); ap.add_argument('out')
ap.add_argument('--obj', required=True); ap.add_argument('--ramp', type=int, default=10); ap.add_argument('--rest_max', type=int, default=30)
ap.add_argument('--json'); a = ap.parse_args()
t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py(); B = len(names); k = names.index(a.obj)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
P = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
Q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)
Rref = Rot.from_quat(Q[:, k][:, [1, 2, 3, 0]])
Z = np.load(a.poses); raw = np.einsum('tij,tjk->tik', Z['world_T_cam'], Z[f'cam_T_{a.obj}'])
n = min(T, len(raw)); ok = np.isfinite(raw[:n]).all((1, 2))
mv = np.nonzero(np.linalg.norm(P[:, k] - P[0, k], axis=1) > 0.01)[0]; on = int(mv[0]) if len(mv) else T
rest = [i for i in range(min(on, a.rest_max)) if ok[i]]; after = [i for i in range(on + 10, n) if ok[i]]
assert len(rest) >= 3 and len(after) >= 10, (len(rest), len(after))
Rraw = {i: Rot.from_matrix(raw[i, :3, :3]) for i in rest + after}
Wi = Rot.concatenate([Rref[i] * Rraw[i].inv() for i in after]); W = Wi.mean()
resid = np.degrees((W.inv() * Wi).magnitude())                     # consistency of raw -> reference over the motion
Rnew = W * Rot.concatenate([Rraw[i] for i in rest]).mean()
V = np.asarray(trimesh.load(a.mesh, force='mesh').vertices, float)
lowz = lambda R, p: float((R.apply(V) + p)[:, 2].min())
P2, R2 = P.copy(), [Rref[i] for i in range(T)]
for i in range(on):
    P2[i, k, 2] += lowz(Rref[i], P[i, k]) - lowz(Rnew, P[i, k]); R2[i] = Rnew
if on > 0:
    C = Rnew * Rref[on - 1].inv(); dz = P2[on - 1, k, 2] - P[on - 1, k, 2]
    S = Slerp([0, 1], Rot.concatenate([Rot.identity(), C]))
    for j in range(a.ramp):
        i = on + j
        if i >= T: break
        w = 1 - (j + 1) / (a.ramp + 1); R2[i] = S([w])[0] * Rref[i]; P2[i, k, 2] += w * dz
q2 = Rot.concatenate(R2).as_quat()[:, [3, 0, 1, 2]]
q2 *= np.sign((q2 * Q[:, k]).sum(1))[:, None] + (np.sign((q2 * Q[:, k]).sum(1))[:, None] == 0)   # keep the stored sign
Q2 = Q.copy(); E = min(T, on + a.ramp); Q2[:E, k] = q2[:E]                    # frames after the ramp: byte-unchanged
for c, v in (('object_body_position', P2), ('object_body_wxyz', Q2)):
    sh = np.array(t.column(c)[0].as_py(), float).shape
    t = t.set_column(t.column_names.index(c), c, pa.array([v.reshape(sh).tolist()], type=t.schema.field(c).type))
pq.write_table(t, a.out)
d0 = (Rref[0].inv() * Rnew)
info = dict(obj=a.obj, frames=T, onset=on, rest_frames=len(rest), ramp=a.ramp,
            ref_f0_to_new_deg=round(float(np.degrees(d0.magnitude())), 2), ref_f0_to_new_rotvec_deg=np.degrees(d0.as_rotvec()).round(2).tolist(),
            dz_f0_mm=round(1000 * float(P2[0, k, 2] - P[0, k, 2]), 2), raw_to_ref_resid_deg=dict(median=round(float(np.median(resid)), 2), p90=round(float(np.percentile(resid, 90)), 2)),
            rest_jitter_deg=round(float(np.degrees(np.median([(Rnew.inv() * W * Rraw[i]).magnitude() for i in rest]))), 2))
print(json.dumps(info))
if a.json: json.dump(info, open(a.json, 'w'), indent=1)
