"""Verifier: recompute run3->run1 alignment independently (Umeyama Sim3 on centres + quaternion-mean rotation), check run3 has no eval images."""
import json, numpy as np, pycolmap
from scipy.spatial.transform import Rotation as Rot
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
r1 = pycolmap.Reconstruction(f"{W}/run1/sparse/0"); r3 = pycolmap.Reconstruction(f"{W}/run3/sparse/0")
def P(r):
    d = {}
    for im in r.images.values():
        T = im.cam_from_world(); R = T.rotation.matrix(); t = np.asarray(T.translation); d[im.name] = (R, -R.T @ t)
    return d
P1, P3 = P(r1), P(r3)
ev3 = [n for n in P3 if n.split("/")[1].startswith("e")]; ev1 = [n for n in P1 if n.split("/")[1].startswith("e")]
print("run1 images", len(P1), "eval in run1", len(ev1), "| run3 images", len(P3), "eval in run3", len(ev3), "points", len(r1.points3D), len(r3.points3D))
com = sorted(set(P1) & set(P3)); print("common", len(com))
C1 = np.array([P1[n][1] for n in com]); C3 = np.array([P3[n][1] for n in com])
# Umeyama sim3 C1 = s R C3 + t
m1, m3 = C1.mean(0), C3.mean(0); X1, X3 = C1 - m1, C3 - m3
U, S, Vt = np.linalg.svd(X1.T @ X3 / len(com)); D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))]); Rs = U @ D @ Vt
s = np.trace(np.diag(S) @ D) / (X3 ** 2).sum(1).mean(); ts = m1 - s * Rs @ m3
# rotation-only from orientations: R_wc1 = Ra R_wc3  -> Ra = R1^T... cam_from_world R: R1 = R3 Ra^T
Q = Rot.from_matrix(np.array([P1[n][0].T @ P3[n][0] for n in com])).mean().as_matrix()
res_rot = [np.degrees(Rot.from_matrix(P1[n][0].T @ P3[n][0] @ Q.T).magnitude()) for n in com]
tq = np.mean(C1 - C3 @ Q.T, 0); res_c = np.linalg.norm(C1 - (C3 @ Q.T + tq), axis=1) * 1000
A = json.load(open(f"{W}/b2_align_run3.json")); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
print("sim3 scale", s, "rot(sim3 vs orient) deg", np.degrees(Rot.from_matrix(Rs @ Q.T).magnitude()))
print("orient-mean vs b2 Ra deg", np.degrees(Rot.from_matrix(Q @ Ra.T).magnitude()), "t diff mm", 1000 * np.linalg.norm(tq - ta))
print("residual centre median %.3f p90 %.3f mm; rot median %.4f p90 %.4f deg" % (np.median(res_c), np.percentile(res_c, 90), np.median(res_rot), np.percentile(res_rot, 90)))
# extent of centres
print("centre extent (m) per axis", np.ptp(C1, 0))
json.dump(dict(Ra=Q.tolist(), ta=tq.tolist(), sim3_scale=s), open("v_align_run3.json", "w"))
