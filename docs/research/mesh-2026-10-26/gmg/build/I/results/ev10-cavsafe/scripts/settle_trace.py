"""ev10-cavsafe, report only: why the pair-scene maxima rise after step 0. One unjittered copy of the contacts.py pair
scene per frame and piece set; per step nefc, ncon, the guest's displacement in the receiver frame (mm) and the
receiver's tilt (deg); at the max-nefc step the guest-receiver contacts by guest piece group (wall bands 1-3, base; SEG pieces per band
from the guest's lathe_collision.json).
Usage: python -I settle_trace.py CONFIG.json TAG GEO_DIR OUT.json f1,f2,..."""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'collcarve2-evalcheck', 'scripts'))
import contacts as C  # noqa: E402
import mujoco  # noqa: E402
cfg, tag, geo, out, frames = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
opt, _ = C.sim_rl(); steps = int(round(C.SECS / opt['timestep']))
fr = json.load(open(os.path.join(geo, f'ep{tag}_frames.json'))); po = np.load(os.path.join(geo, f'ep{tag}_poses.npz'))
T, ir, ig = po['T'], int(po['ir']), int(po['ig']); names = [str(x) for x in po['names']]
top = fr['summary']['support']['top_z']; ec = cfg['episodes'][tag]
hr, hg = C.load_hulls(ec['objects'][names[ir]]), C.load_hulls(ec['objects'][names[ig]])
pr, pg = C.props(hr), C.props(hg)
SEG = json.load(open(os.path.join(os.path.dirname(ec['objects'][names[ig]]['pieces'][0]), 'lathe_collision.json')))['segments']
res = dict(tag=tag, frames=[])
for f in map(int, frames.split(',')):
    m = mujoco.MjModel.from_xml_string(C.scene(hr, hg, T[f, ir], T[f, ig], top, pr, pg, opt)); d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    H = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'H'); G = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'G')
    def rel():
        Rh = d.xmat[H].reshape(3, 3); return Rh.T @ (d.xpos[G] - d.xpos[H])
    r0 = rel(); z0 = d.xmat[H].reshape(3, 3)[:, 2].copy()
    tr, best = [], (-1, None)
    for k in range(steps):
        mujoco.mj_step(m, d)
        ne, nc = int(d.nefc), int(d.ncon)
        dr = (rel() - r0) * 1e3
        tilt = float(np.degrees(np.arccos(np.clip(d.xmat[H].reshape(3, 3)[:, 2] @ z0, -1, 1))))
        tr.append([k, ne, nc, *np.round(dr, 2).tolist(), round(tilt, 2)])
        if ne > best[0]:
            g1 = np.asarray(d.contact.geom1[:nc]); g2 = np.asarray(d.contact.geom2[:nc])
            gid = [int(a) if m.geom_bodyid[a] == G else int(b) for a, b in zip(g1, g2)
                   if {int(m.geom_bodyid[a]), int(m.geom_bodyid[b])} == {H, G}]
            gfirst = int(np.flatnonzero(m.geom_bodyid == G)[0])
            idx = np.array(gid) - gfirst
            grp = np.bincount(np.minimum(idx // SEG, 3), minlength=4).tolist() if len(idx) else [0, 0, 0, 0]
            best = (ne, dict(step=k, nefc=ne, ncon=nc, guest_receiver_by_guest_group_band1_2_3_base=grp))
    tr = np.array(tr)
    last = tr[-50:]
    rec = dict(frame=f, max=best[1], nefc_step0=int(tr[0, 1]), nefc_last_0p5s_median=float(np.median(last[:, 1])),
               ncon_last_0p5s_median=float(np.median(last[:, 2])),
               guest_rel_disp_end_mm=tr[-1, 3:6].tolist(), receiver_tilt_end_deg=float(tr[-1, 6]),
               trace_every_10=tr[::10].tolist())
    res['frames'].append(rec)
    print(tag, f, json.dumps({k: v for k, v in rec.items() if k != 'trace_every_10'}), flush=True)
json.dump(res, open(out, 'w'), indent=1)
