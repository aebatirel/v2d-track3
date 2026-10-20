"""DIG 18 C10 (public GT, registration analysis only): the table normal in the GT world from the support planes of
GT-posed objects resting on the table, over all public sessions; leave-session-out (LSO) stability.
Support plane as in B19 (hull facets within 3 deg of the most downward one, area-weighted). Resting = z_min within
2.5 mm of 0.6012 and support area >= 25 cm2 and tilt < 3 deg. Frames: every 20th.
usage: python c10_gt_up.py <out json>"""
import sys, json, numpy as np, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
HULL, rows = {}, []
for ep in EPS:
    e = c11.load_episode(ep)
    for j, n in enumerate(e["names"]):
        if n not in HULL: HULL[n] = trimesh.convex.convex_hull(np.asarray(c11.glb_mesh(n).vertices))
        H = HULL[n]
        for f in range(0, len(e["frame"]), 20):
            q = e["pose"][f, j]
            if not np.isfinite(q).all(): continue
            R = c11.R_of(q[3:]); N = H.face_normals @ R.T; A = H.area_faces
            zmin = (H.vertices @ R.T + q[:3])[:, 2].min(); best = np.argmax(-N[:, 2])
            g = np.degrees(np.arccos(np.clip(N @ N[best], -1, 1))) < 3.0
            nm = (N[g] * A[g, None]).sum(0); nm /= np.linalg.norm(nm)
            tilt = np.degrees(np.arccos(np.clip(-nm[2], -1, 1))); area = A[g].sum() * 1e4
            if abs(zmin - 0.6012) < 0.0025 and area >= 25 and tilt < 3:
                rows.append(dict(ep=ep, f=int(f), obj=n, zmin=float(zmin), area=float(area), lx=float(np.degrees(-nm[0])), ly=float(np.degrees(-nm[1]))))
print(f"resting samples {len(rows)} from {len(set(r['ep'] for r in rows))} sessions")
objs = sorted(set(r["obj"] for r in rows))
print("per object (mean lean x, y deg; sd; n samples; sessions):")
for o in objs:
    L = np.array([[r["lx"], r["ly"]] for r in rows if r["obj"] == o]); S = sorted(set(r["ep"] for r in rows if r["obj"] == o))
    print(f"  {o:18s} ({L[:,0].mean():+.2f}, {L[:,1].mean():+.2f})  sd ({L[:,0].std():.2f}, {L[:,1].std():.2f})  n {len(L):3d}  eps {S}")
# per session: median over that session's samples (objects pooled)
sess = {}
for ep in EPS:
    L = np.array([[r["lx"], r["ly"]] for r in rows if r["ep"] == ep])
    if len(L): sess[ep] = np.median(L, 0)
S = np.array(list(sess.values())); m = S.mean(0)
print("per session median lean:", {k: (round(v[0], 2), round(v[1], 2)) for k, v in sess.items()})
print(f"session mean ({m[0]:+.2f}, {m[1]:+.2f}) |{np.linalg.norm(m):.2f}| deg; session scatter sd ({S[:,0].std(ddof=1):.2f}, {S[:,1].std(ddof=1):.2f}) "
      f"rms dist to mean {np.sqrt(np.mean(np.sum((S-m)**2,1))):.2f} deg")
lso = []
for i, ep in enumerate(sess):
    mo = np.delete(S, i, 0).mean(0); lso.append(np.linalg.norm(S[i] - mo))
print(f"LSO prediction error (held-out session lean vs mean of others): median {np.median(lso):.2f} rms {np.sqrt(np.mean(np.square(lso))):.2f} deg; "
      f"vs predicting 0 (a13 = level table): median {np.median(np.linalg.norm(S,axis=1)):.2f} rms {np.sqrt(np.mean(np.sum(S**2,1))):.2f} deg")
# object-type-balanced estimate (excludes the rack, which dominates) as a mesh-bias check
nr = np.array([[r["lx"], r["ly"]] for r in rows if r["obj"] != "plastic_dish_rack"])
print(f"without the rack: median ({np.median(nr[:,0]):+.2f}, {np.median(nr[:,1]):+.2f}) n {len(nr)}")
json.dump(dict(rows=rows, session={str(k): v.tolist() for k, v in sess.items()}, mean=m.tolist(), lso=lso), open(sys.argv[1], "w"))
