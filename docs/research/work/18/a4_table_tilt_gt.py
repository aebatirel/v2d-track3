"""Table-top tilt in the MOCAP world from public GT rest contacts (analysis only). For every rest segment of note 11
(s8_rest.json), take the scan's lowest vertices (within 1.5 mm of the minimum) at the rest pose: contact xy + z. Fit
z = a x + b y + c_ep (shared slope, per-episode intercept, because x,y are re-centred per episode)."""
import sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
S8 = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/11/s8_rest.json"))
V = {}; rows = []
for name, segs in S8.items():
    if name not in V:
        m = c11.glb_mesh(name); V[name] = np.asarray(m.vertices)
    for s in segs:
        e = c11.load_episode(s["ep"]); j = e["names"].index(name)
        f = (s["f0"] + s["f1"]) // 2
        q = e["pose"][f, j]; P = V[name] @ c11.R_of(q[3:]).T + q[:3]
        lo = P[P[:, 2] < P[:, 2].min() + 0.0015]
        if abs(P[:, 2].min() - 0.6012) < 0.006: rows.append((s["ep"], name, lo[:, 0].mean(), lo[:, 1].mean(), P[:, 2].min()))
eps = sorted(set(r[0] for r in rows)); ix = {e: i for i, e in enumerate(eps)}
A = np.zeros((len(rows), 2 + len(eps))); z = np.zeros(len(rows))
for k, (ep, n, x, y, zz) in enumerate(rows):
    A[k, 0] = x; A[k, 1] = y; A[k, 2 + ix[ep]] = 1; z[k] = zz
sol, *_ = np.linalg.lstsq(A, z, rcond=None); r = z - A @ sol
a, b = sol[:2]; n = np.array([-a, -b, 1.0]); n /= np.linalg.norm(n)
print(f"segments {len(rows)} eps {len(eps)}; slope a={a:+.4f} b={b:+.4f} -> table tilt {np.degrees(np.arccos(n[2])):.2f} deg, "
      f"downhill azimuth {np.degrees(np.arctan2(-b, -a)):.1f} deg; resid rms {np.sqrt(np.mean(r**2))*1000:.2f} mm")
xy = np.array([[r_[2], r_[3]] for r_ in rows]); print("contact xy spread (sd, m):", xy.std(0).round(3))
print("intercepts (table z at episode xy origin):", {e: round(float(sol[2 + ix[e]]), 4) for e in eps})
# bootstrap over episodes
rng = np.random.default_rng(0); T = []
for _ in range(300):
    pick = rng.choice(eps, len(eps)); kk = [k for e in pick for k in range(len(rows)) if rows[k][0] == e]
    s_, *_ = np.linalg.lstsq(A[kk], z[kk], rcond=None); nn = np.array([-s_[0], -s_[1], 1]); T.append(np.degrees(np.arccos(nn[2] / np.linalg.norm(nn))))
print("tilt bootstrap p5-p95:", np.percentile(T, [5, 50, 95]).round(2))
json.dump(dict(a=a, b=b, tilt_deg=float(np.degrees(np.arccos(n[2]))), n=n.tolist(), resid_mm=float(np.sqrt(np.mean(r ** 2)) * 1000),
               nseg=len(rows)), open("a4_table_tilt_gt.json", "w"), indent=1)
