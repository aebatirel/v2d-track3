"""DIG 18 C11: occluded vs unoccluded relocalisation on the same map (run3) and frames. Reads no GT.
usage: python c11_compare.py <eps...>"""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as Rot
def T44(m): x = np.eye(4); x[:3] = np.array(m); return x
def cen(T): return -T[:3, :3].T @ T[:3, 3]
for o in (sys.argv[1].split(",") if "," in sys.argv[1] else ("c50", "c75", "c90", "b67", "l50")):
    inl, inla, dp, dr, dpa, dra, ok, oka, n = [], [], [], [], [], [], 0, 0, 0
    base_inl = []
    for e in [int(x) for x in sys.argv[1:] if "," not in x]:
        B = {r["frame"]: r for r in json.load(open(f"c1/r3s25_e{e}.json"))["frames"]}
        for r in json.load(open(f"c11/{o}_e{e}.json"))["frames"]:
            n += 1; b = B[r["frame"]]; base_inl.append(b["inl_bc"])
            if r["inl_bc"] >= 30:
                ok += 1; inl.append(r["inl_bc"]); M, G = T44(r["c_from_world"]), T44(b["c_from_world"])
                dp.append(np.linalg.norm(cen(M) - cen(G)) * 1000); dr.append(np.degrees(np.linalg.norm(Rot.from_matrix(M[:3, :3] @ G[:3, :3].T).as_rotvec())))
            if r.get("inl_a", 0) >= 30 and "a_from_world" in b:
                oka += 1; inla.append(r["inl_a"]); M, G = T44(r["a_from_world"]), T44(b["a_from_world"])
                dpa.append(np.linalg.norm(cen(M) - cen(G)) * 1000); dra.append(np.degrees(np.linalg.norm(Rot.from_matrix(M[:3, :3] @ G[:3, :3].T).as_rotvec())))
    f = lambda v: f"{np.median(v):.2f}/{np.max(v):.2f}" if v else "-"
    print(f"{o}: n {n} | rig ok {ok/n:.2f} inliers min {min(inl) if inl else 0} median {np.median(inl) if inl else 0:.0f} (unoccluded median {np.median(base_inl):.0f}) "
          f"dpos {f(dp)} mm drot {f(dr)} deg | cam_a ok {oka/n:.2f} inl min {min(inla) if inla else 0} dpos {f(dpa)} mm drot {f(dra)} deg (median/max)")
