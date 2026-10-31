"""PREREG G2 (mesh session M3): settle the beige cup in a carve's pieces from the assembled frames of OUR reference.
Plain MuJoCo (fcvenv, 3.8.1), set up as tools/nest_physics.py --mode inner: the blue cup is a static (mocap) body at its
reference pose, the beige cup a free body (its pieces, inertia.json mass / COM / inertia) started at its reference pose
with zero velocity; gravity world -z; timestep DT (2 ms), SETTLE seconds (2.0), MuJoCo default contact parameters; no
hands, no table. Each frame is settled independently.
Measures, in the blue cup's frame (= world here, the blue does not move), with the beige lathe axis (approach-2 profile
c0, d of the beige file frame):
  dz_mm    displacement of the beige pieces' centre along the blue lathe axis toward the mouth (+ = rises, - = sinks);
  tilt_deg angle between the beige axis before and after;
  pass     |dz| <= 4 mm and tilt <= 5 deg.
Usage: settle_m3.py REF CARVE_DIR BLUE_PROFILE.npz BEIGE_PROFILE.npz FRAMES(a:b:step) OUT.json [--dt 0.002 --settle 2.0]"""
import sys, glob, json, os, time, argparse
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation as Rot
ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('carve'); ap.add_argument('pb'); ap.add_argument('pg')
ap.add_argument('frames'); ap.add_argument('out'); ap.add_argument('--dt', type=float, default=0.002); ap.add_argument('--settle', type=float, default=2.0)
a = ap.parse_args()
import pyarrow.parquet as pq
t = pq.read_table(a.ref); row = t.to_pylist()[0]; names = list(row['object_body_names'])
pos = np.array(row['object_body_position'], float); q = np.array(row['object_body_wxyz'], float)
T = len(pos); ib, ig = names.index('blue_cup'), names.index('beige_cup')
B, G = np.load(a.pb), np.load(a.pg)
db_f = np.asarray(B['d'], float); dg_f = np.asarray(G['d'], float)
import trimesh
cen = {}
assets, bodies = [], []
for c in ('blue_cup', 'beige_cup'):
    pcs = sorted(glob.glob(f'{a.carve}/{c}/piece_*.obj'))
    V = np.concatenate([np.asarray(trimesh.load(p, process=False).vertices) for p in pcs]); cen[c] = (V.min(0) + V.max(0)) / 2
    for k, p in enumerate(pcs):
        assets.append(f'<mesh name="{c}_{k}" file="{os.path.abspath(p)}"/>')
    geoms = ''.join(f'<geom type="mesh" mesh="{c}_{k}"/>' for k in range(len(pcs)))
    if c == 'beige_cup':
        ine = json.load(open(f'{a.carve}/{c}/inertia.json')); I = np.asarray(ine['inertia'], float)
        bodies.append(f'<body name="{c}" pos="0 0 0.5"><freejoint name="{c}_j"/><inertial pos="{" ".join(map(str, ine["com"]))}" '
                      f'mass="{ine["mass"]}" fullinertia="{I[0,0]} {I[1,1]} {I[2,2]} {I[0,1]} {I[0,2]} {I[1,2]}"/>{geoms}</body>')
    else:
        bodies.append(f'<body name="{c}" mocap="true">{geoms}</body>')
xml = (f'<mujoco><compiler angle="radian"/><option timestep="{a.dt}" gravity="0 0 -9.81"/><asset>{"".join(assets)}</asset>'
       f'<worldbody>{"".join(bodies)}</worldbody></mujoco>')
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
bb = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'blue_cup'); bg = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'beige_cup')
ja = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'beige_cup_j')]; mb = model.body_mocapid[bb]
steps = int(round(a.settle / a.dt)); fa, fb, fs = (int(x) for x in a.frames.split(':'))
rows = []; t0 = time.time()
for f in range(fa, fb + 1, fs):
    mujoco.mj_resetData(model, data)
    data.mocap_pos[mb] = pos[f, ib]; data.mocap_quat[mb] = q[f, ib]
    data.qpos[ja:ja + 3] = pos[f, ig]; data.qpos[ja + 3:ja + 7] = q[f, ig]
    mujoco.mj_forward(model, data)
    pen0 = float(min([data.contact[k].dist for k in range(data.ncon)], default=0.0)); n0 = int(data.ncon)
    Rb = Rot.from_quat(q[f, ib][[1, 2, 3, 0]]).as_matrix(); ax_b = Rb @ db_f        # blue lathe axis in world (toward base)
    R0 = Rot.from_quat(q[f, ig][[1, 2, 3, 0]]).as_matrix(); c0w = R0 @ cen['beige_cup'] + pos[f, ig]; a0 = R0 @ dg_f
    peak = 0.0; nan = False
    for k in range(steps):
        mujoco.mj_step(model, data)
        if k % 50 == 49:
            if not np.all(np.isfinite(data.qpos)):
                nan = True; break
            Rk = Rot.from_quat(data.qpos[ja + 3:ja + 7][[1, 2, 3, 0]]).as_matrix(); ck = Rk @ cen['beige_cup'] + data.qpos[ja:ja + 3]
            peak = max(peak, float(np.linalg.norm(ck - c0w)))
    if nan:
        rows.append(dict(frame=f, nan=True, passed=False)); continue
    R1 = Rot.from_quat(data.qpos[ja + 3:ja + 7][[1, 2, 3, 0]]).as_matrix(); c1w = R1 @ cen['beige_cup'] + data.qpos[ja:ja + 3]; a1 = R1 @ dg_f
    dc = c1w - c0w; dz = float(-(dc @ ax_b)) * 1e3                                    # toward the mouth = -axis(base)
    tilt = float(np.degrees(np.arccos(np.clip(a0 @ a1, -1, 1))))
    rows.append(dict(frame=f, dz_mm=round(dz, 2), dlat_mm=round(float(np.linalg.norm(dc + (dz / 1e3) * ax_b)) * 1e3, 2), tilt_deg=round(tilt, 2),
                     peak_disp_mm=round(peak * 1e3, 1), start_min_contact_dist_mm=round(pen0 * 1e3, 2), start_ncon=n0, end_ncon=int(data.ncon),
                     end_speed_mm_s=round(float(np.abs(data.qvel[:3]).max()) * 1e3, 2), passed=bool(abs(dz) <= 4.0 and tilt <= 5.0)))
    print(json.dumps(rows[-1]), flush=True)


def st(x):
    x = np.asarray(x, float)
    return dict(median=round(float(np.median(x)), 2), min=round(float(x.min()), 2), max=round(float(x.max()), 2)) if len(x) else None


summ = {}
for lab, lo, hi in (('f100-117', 100, 117), ('f118-160', 118, 160), ('f100-160', 100, 160)):
    rr = [r for r in rows if lo <= r['frame'] <= hi]
    ok = [r for r in rr if not r.get('nan')]
    summ[lab] = dict(frames=len(rr), passed=int(sum(r['passed'] for r in rr)), nan=int(sum(bool(r.get('nan')) for r in rr)),
                     dz_mm=st([r['dz_mm'] for r in ok]), abs_dz_mm=st([abs(r['dz_mm']) for r in ok]), tilt_deg=st([r['tilt_deg'] for r in ok]),
                     dlat_mm=st([r['dlat_mm'] for r in ok]), start_min_contact_dist_mm=st([r['start_min_contact_dist_mm'] for r in ok]))
out = dict(DIAGNOSTIC='GT-free M3 settle (ev10w/scripts/settle_m3.py)', ref=a.ref, carve=a.carve, frames=a.frames, dt=a.dt, settle_s=a.settle,
           mujoco=mujoco.__version__, ngeom=int(model.ngeom), seconds=round(time.time() - t0, 1), summary=summ, rows=rows)
json.dump(out, open(a.out, 'w'), indent=1)
print(json.dumps(summ))
