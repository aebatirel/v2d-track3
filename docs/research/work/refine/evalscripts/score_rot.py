"""SCORER SIDE (reads public mocap; run only after refine has written its outputs).
Runs pipeline/score_registered.py unchanged (runpy, same argv, so the --out json and --per_frame npz are the harness's
own), then reuses its globals (registration REG, host geometry H, mocap gt, trajectory) to compute the per-frame
symmetric orientation error with the kit's own v2dlb.track3_pose._symmetry_orientation_errors after the same
_align_registered_scene. Writes ROT_OUT (.npz: names, rot_deg (T,B)) for gate 3 (flips: > 90 deg on > 5 % of frames).
Usage: python -I score_rot.py ROT_OUT.npz <score_registered.py args...>"""
import runpy, sys
import numpy as np
rot_out = sys.argv[1]
SR = '/home/user/v2d-track3/pipeline/score_registered.py'
sys.argv = [SR] + sys.argv[2:]
g = runpy.run_path(SR, run_name='__main__')
T3, REG, H, gt, B, trajs, names = g['T3'], g['REG'], g['H'], g['gt'], g['B'], g['trajs'], g['names']
ach = trajs['perception'][:, None].copy(); ref = gt[:, None].copy()
for s in range(B):
    ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
    ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]
ach = T3._align_registered_scene(ach, ref, axes)
err = np.degrees(T3._symmetry_orientation_errors(ach, ref, axes, orders))[:, 0]   # (T, B)
pts = [h['points'] for h in H]
auc_u = float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders))       # unrounded (harness rounds to 4 d.p.)
auc_obj_u = [float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1], pts[s:s + 1], axes[s:s + 1],
                                              orders[s:s + 1])) for s in range(B)]
np.savez(rot_out, names=np.array(names), rot_deg=err, auc_unrounded=auc_u, auc_obj_unrounded=np.array(auc_obj_u))
print('ROT', {n: dict(p90=round(float(np.mean(err[:, s] > 90)), 4), med=round(float(np.median(err[:, s])), 2))
              for s, n in enumerate(names)}, file=sys.stderr)
