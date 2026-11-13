"""ev10-cavsafe, report only (A4 drop check): for each of the 16 jittered copies of the contacts.py pair scene at one frame,
the first step with guest-table contacts, the guest displacement in the receiver frame there, and the deepest beige
base vertex along the blue lathe axis over 2 s (h > the floor top = the beige base went into / through the floor).
Run from the run dir (cfg.json, geo_<tag>/, prof/). Usage: python -I drop_peek.py TAG FRAME FLOOR_TOP_MM"""
import json, sys, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/gmg/build/I/results/collcarve2-evalcheck/scripts')
import contacts as C, mujoco
from scipy.spatial.transform import Rotation as Rot
cfg = json.load(open('cfg.json')); tag = sys.argv[1]; f = int(sys.argv[2])
opt, _ = C.sim_rl(); po = np.load(f'geo_{tag}/ep{tag}_poses.npz'); T = po['T']
fr = json.load(open(f'geo_{tag}/ep{tag}_frames.json')); top = fr['summary']['support']['top_z']
ec = cfg['episodes'][tag]; hr, hg = C.load_hulls(ec['objects']['blue_cup']), C.load_hulls(ec['objects']['beige_cup'])
pr, pg = C.props(hr), C.props(hg)
z = np.load('prof/blue_cup_profile.npz'); c0, d = z['c0'], z['d']
J = C.jitters(); steps = 200
for j, jit in enumerate(J):
    Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(jit[3:]).as_matrix(); Jm[:3, 3] = jit[:3]
    m = mujoco.MjModel.from_xml_string(C.scene(hr, hg, T[f, 0], T[f, 1] @ Jm, top, pr, pg, opt)); dd = mujoco.MjData(m)
    mujoco.mj_forward(m, dd)
    H = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'H'); G = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'G')
    gfirst = int(np.flatnonzero(m.geom_bodyid == G)[0])
    def rel():
        Rh = dd.xmat[H].reshape(3, 3); Rg = dd.xmat[G].reshape(3, 3)
        # beige lowest vertex (all pieces) in the blue lathe frame: h along d
        P = np.vstack([dd.geom_xpos[gfirst + i] + 0 for i in range(len(hg))])
        return Rh.T @ (dd.xpos[G] - dd.xpos[H]), np.degrees(np.arccos(np.clip(Rh[:, 2] @ Rg[:, 2], -1, 1)))
    r0, _ = rel(); first = None; hmax = -1
    for k in range(steps):
        mujoco.mj_step(m, dd)
        cl = C.classes(m, dd)
        # deepest beige vertex along the blue lathe axis (base direction = +h)
        Rh = dd.xmat[H].reshape(3, 3); ph = dd.xpos[H]
        Vg = np.vstack([V @ dd.xmat[G].reshape(3, 3).T + dd.xpos[G] for V in hg[-5:]])   # base pieces
        hb = ((Vg - ph) @ Rh - c0) @ d
        hmax = max(hmax, hb.max())
        if cl['guest_table'] > 0 and first is None:
            r, tilt = rel(); first = (k, cl['guest_table'], np.round((r - r0) * 1e3, 1).tolist(), round(float(tilt), 1), round(float(hb.max() * 1e3), 1))
    print(j, 'first guest-table step/contacts/rel disp mm/axis angle deg/beige base max h mm:', first, '| max beige base h over run %.1f mm (blue floor top %s, lowest blue point 80.0)' % (hmax * 1e3, sys.argv[3]))
