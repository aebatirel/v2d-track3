# Stage C approximate settle test (MuJoCo 3.8.1 CPU, NOT the evaluator's mujoco-warp): public-GT reset states with
# each collider set; how far the pair is pushed apart at reset, how many contacts it creates, and step cost.
# Settings mirror FlashCHORD @8c778f90: dt 0.005 (fps 50 x 4 substeps), implicitfast, Newton solver, pyramidal cone,
# impratio 20, iterations 100, ls_iterations 50, friction 1.0, margin 0, solref (0.02, 1) = newton's default ke 2.5e3 /
# kd 100 via convert_solref, default solimp, maxhullvert 64, hulls of one object never collide with each other.
# Table: box whose top is at the lowest hull vertex of the support object (B) under that collider set (so the
# table itself pushes nothing). Inertia: public URDF diag inertia, 0.3 kg.
# usage: c_settle.py <case> LABEL=hulldir ...     case = ep:frame:A:B  (frame -1 = last)
import sys, os, re, time, numpy as np, pandas as pd
sys.path.append('/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylibmj')
import mujoco
from scipy.spatial.transform import Rotation as Rot
from scipy.spatial import ConvexHull
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls, P as PUB
def inertia(n):
    u = open(f'{PUB}/urdf/{n}_rigid.urdf').read()
    return [float(re.search(f'{k}="([^"]+)"', u).group(1)) for k in ('ixx', 'iyy', 'izz')]
def pose(ep, f, n):
    df = pd.read_parquet(f'{PUB}/data/chunk-000/episode_{ep:06d}.parquet', columns=['observation.objects'])['observation.objects']
    fr = df.iloc[f if f >= 0 else len(df) - 1]; p = [o['pose'] for o in fr if o['name'] == n][0]
    return Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(), np.array(p[:3], float)
def build(objs, ztop):
    assets, bodies = [], []
    for k, (n, R, t, H) in enumerate(objs):
        for i, v in enumerate(H):
            assets.append(f'<mesh name="m{k}_{i}" maxhullvert="64" vertex="{" ".join("%.7f" % x for x in v.ravel())}"/>')
        q = Rot.from_matrix(R).as_quat(); I = inertia(n)
        g = ''.join(f'<geom type="mesh" mesh="m{k}_{i}" contype="{1 << k}" conaffinity="{(1 << 8) | (7 & ~(1 << k))}"/>' for i in range(len(H)))
        bodies.append(f'<body name="b{k}" pos="{t[0]} {t[1]} {t[2]}" quat="{q[3]} {q[0]} {q[1]} {q[2]}"><freejoint/>'
                      f'<inertial pos="0 0 0" mass="0.3" diaginertia="{I[0]} {I[1]} {I[2]}"/>{g}</body>')
    xml = (f'<mujoco><option timestep="0.005" integrator="implicitfast" solver="Newton" cone="pyramidal" impratio="20" '
           f'iterations="100" ls_iterations="50"/><default><geom friction="1 0.005 0.0001" condim="3" margin="0" density="0" '
           f'solref="0.02 1"/></default><asset>{"".join(assets)}</asset><worldbody>'
           f'<geom name="table" type="box" size="1 1 0.05" pos="0 0 {ztop-0.05}" contype="256" conaffinity="7"/>{"".join(bodies)}</worldbody></mujoco>')
    return mujoco.MjModel.from_xml_string(xml)
def rel(d):   # pose of body A in body B's frame
    Ra = d.body('b0').xmat.reshape(3, 3); Rb = d.body('b1').xmat.reshape(3, 3)
    return Rb.T @ Ra, Rb.T @ (d.body('b0').xpos - d.body('b1').xpos)
def main():
    ep, f, A, B = sys.argv[1].split(':'); ep, f = int(ep), int(f)
    for arg in sys.argv[2:]:
        lab, hd = arg.split('=')
        objs = []
        for n in (A, B):
            R, t = pose(ep, f, n); hv = load_hulls(f'{hd}/{n}.npz')
            keep = [v for v in hv if ConvexHull(v).volume > 1e-12]          # drop CoACD debris (C6) so MuJoCo compiles
            if len(keep) < len(hv): print(f'   [{lab}] {n}: dropped {len(hv)-len(keep)} debris hulls (< 1e-12 m3)', flush=True)
            objs.append((n, R, t, keep))
        Rb, tb = objs[1][1], objs[1][2]; ztop = min(((v @ Rb.T) + tb)[:, 2].min() for v in objs[1][3])
        t0 = time.time(); m = build(objs, ztop); tc = time.time() - t0
        d = mujoco.MjData(m); mujoco.mj_forward(m, d); n0 = d.ncon
        R0, p0 = rel(d); xa0, xb0 = d.body('b0').xpos.copy(), d.body('b1').xpos.copy()
        out = []; nmax = n0; ts = time.time(); steps = 0
        for T in (0.005, 0.05, 0.25, 1.0):
            while d.time < T - 1e-9:
                mujoco.mj_step(m, d); steps += 1; nmax = max(nmax, d.ncon)
            R1, p1 = rel(d)
            dr = np.linalg.norm(p1 - p0) * 1e3; ang = np.degrees(Rot.from_matrix(R1 @ R0.T).magnitude())
            da = np.linalg.norm(d.body('b0').xpos - xa0) * 1e3; db = np.linalg.norm(d.body('b1').xpos - xb0) * 1e3
            out.append(f't={T:.3f}s A-rel-B {dr:5.1f} mm {ang:4.1f} deg (|A| {da:5.1f}, |B| {db:5.1f} mm) ncon {d.ncon}')
        wall = (time.time() - ts) / steps * 1e3
        print(f'[{lab:8s}] ep{ep} f{f} {A} on/in {B}: hulls {len(objs[0][3])}+{len(objs[1][3])}, compile {tc:.1f}s, '
              f'ncon(t0) {n0}, ncon max {nmax}, {wall:.1f} ms/step (CPU)', flush=True)
        for o in out: print('     ', o, flush=True)
main()
