"""GT-free joint fit: two upright cups on one unknown table plane, from marker blobs only (ep 11 frame 0).
Unknowns (camera frame): plane normal (2), plane offset (1), per cup: base position on plane (2) + spin (1).
GT is read only afterwards, to score the relative pose of the two cups."""
import numpy as np, cv2, json, itertools
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rr
from selfsim import good_markers, axis_for
from meshlib import load, sample, rot
from pnp_check import variant, T_of
import pandas as pd

K, D = variant(False)
def body(n):
    g, tex = load(n); P, _, _ = sample(g, tex, 200000, seed=7); p, a = axis_for(n, P)
    a = a if a[2] > 0 else -a            # +a points from rim to base (cups rest -z up)
    h = (P - p) @ a; base = p + a * h.max()
    mk = good_markers(n)
    return dict(p=p, a=a, base=base, mk=mk)
B = {n: body(n) for n in ['blue_cup', 'beige_cup']}

def basis(a):
    t = np.array([1., 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1., 0])
    e1 = np.cross(a, t); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1); return e1, e2

def cup_pose(n, normal, d, xy, spin):
    """camera_T_cup. normal: unit plane normal pointing up (toward camera side). Base centre on plane."""
    b = B[n]
    # rotation taking body axis a -> -normal, then spin about it
    v = np.cross(b['a'], -normal); s = np.linalg.norm(v); c = b['a'] @ -normal
    R0 = Rr.from_rotvec(v / s * np.arctan2(s, c)).as_matrix() if s > 1e-9 else np.eye(3)
    R = Rr.from_rotvec(-normal * spin).as_matrix() @ R0
    u1, u2 = basis(normal); o = -d * normal               # plane point: n.x + d = 0 -> x = -d n
    base_cam = o + xy[0] * u1 + xy[1] * u2
    t = base_cam - R @ b['base']
    return R, t

def unpack(x):
    th, ph, d = x[:3]
    normal = np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
    return normal, d, x[3:5], x[5], x[6:8], x[8]

def residuals(x, obs):
    normal, d, xy1, s1, xy2, s2 = unpack(x)
    r = []
    for n, xy, s in [('blue_cup', xy1, s1), ('beige_cup', xy2, s2)]:
        R, t = cup_pose(n, normal, d, xy, s)
        X = B[n]['mk'] @ R.T + t
        pr = cv2.projectPoints(X, np.zeros(3), np.zeros(3), K, D)[0].reshape(-1, 2)
        for u in obs[n]:
            dd = np.linalg.norm(pr - u, axis=1); j = dd.argmin(); r += list(pr[j] - u)
    return np.array(r)

def fit(obs, rng):
    best = None
    # rough plane init: camera ~0.5 m from table, looking down ~45 deg; normal mostly toward -y (image up) and -z
    for th0 in [2.0, 2.3, 2.6]:
        for ph0 in [-np.pi / 2, -2.0, -1.2]:
            for s1 in np.radians(np.arange(0, 360, 45)):
                for s2 in np.radians(np.arange(0, 360, 45)):
                    normal = np.array([np.sin(th0) * np.cos(ph0), np.sin(th0) * np.sin(ph0), np.cos(th0)])
                    x0 = np.r_[th0, ph0, 0.45, 0, 0, s1, 0, 0, s2]
                    # init xy from blob means: back-project mean blob ray to plane
                    for k, n in enumerate(['blue_cup', 'beige_cup']):
                        uvm = np.mean(obs[n], 0)
                        ray = cv2.undistortPoints(uvm.reshape(1, 1, 2), K, D).reshape(2); ray = np.r_[ray, 1]
                        lam = -0.45 / (normal @ ray); P = lam * ray
                        u1, u2 = basis(normal); o = -0.45 * normal
                        x0[3 + 3 * k:5 + 3 * k] = [(P - o) @ u1, (P - o) @ u2]
                    try:
                        r = least_squares(residuals, x0, args=(obs,), loss='soft_l1', f_scale=3.0, max_nfev=200)
                    except Exception:
                        continue
                    if best is None or r.cost < best.cost: best = r
    return best

def rel_gt(ep, frame):
    df = pd.read_parquet(f'/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_{ep:06d}.parquet')
    o = {q['name']: T_of(q['pose']) for q in df.iloc[frame]['observation.objects']}
    return np.linalg.inv(o['beige_cup']) @ o['blue_cup']

if __name__ == '__main__':
    import sys
    obs0 = {'blue_cup': np.array([[795, 988], [1044, 1022], [950, 1290]], float),
            'beige_cup': np.array([[1260, 1059], [1479, 984], [1273, 888]], float)}
    G = rel_gt(11, 0)
    rng = np.random.default_rng(0)
    out = []
    for trial, sig in [(0, 0.0)] + [(t, s) for s in (1.0, 2.0, 4.0) for t in range(6)]:
        obs = {n: v + rng.normal(0, sig, v.shape) for n, v in obs0.items()}
        r = fit(obs, rng)
        normal, d, xy1, s1, xy2, s2 = unpack(r.x)
        R1, t1 = cup_pose('blue_cup', normal, d, xy1, s1); R2, t2 = cup_pose('beige_cup', normal, d, xy2, s2)
        T1 = np.eye(4); T1[:3, :3] = R1; T1[:3, 3] = t1; T2 = np.eye(4); T2[:3, :3] = R2; T2[:3, 3] = t2
        E = np.linalg.inv(T2) @ T1
        dpos = np.linalg.norm(E[:3, 3] - G[:3, 3]) * 1000
        drot = np.degrees(Rr.from_matrix(E[:3, :3].T @ G[:3, :3]).magnitude())
        # spin error of beige (anchor) expressed as bearing of blue cup seen from beige frame
        b_est = np.degrees(np.arctan2(E[1, 3], E[0, 3])); b_gt = np.degrees(np.arctan2(G[1, 3], G[0, 3]))
        rms = np.sqrt(np.mean(r.fun ** 2))
        out.append((sig, rms, dpos, drot, (b_est - b_gt + 180) % 360 - 180, d))
        print('noise %.1f px: rms %.2f px | blue-in-beige pos err %.1f mm, rel rot err %.2f deg, bearing err %.2f deg, cam-plane dist %.3f m' % out[-1], flush=True)
    json.dump(out, open('out/joint_fit_ep11.json', 'w'))
