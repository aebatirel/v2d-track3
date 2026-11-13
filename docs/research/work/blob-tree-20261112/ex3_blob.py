"""Descriptive (pre-registered as no-verdict): contact-blob features over exercise 3's flask handover vs physics outcomes.
Args: repo, chord_workshop dir, zero_err.npz, policy_rollout.npz, out_png, out_json"""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
repo, d, zfile, pfile, out_png, out_json = sys.argv[1:7]; MU_ARG = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
sys.path.insert(0, repo + '/pipeline'); sys.path.insert(0, repo + '/tools')
import wrench_gate as wg, blob_features as bf
ref = np.load(f'{d}/assets/reference.npz'); con = np.load(f'{d}/assets/contacts/trajectory_contacts.npz')
q = ref['qpos'].astype(float); T = len(q); P = q[:, 58:61]; Qwxyz = q[:, 61:65]; Q = Qwxyz[:, [1, 2, 3, 0]]
# flask inertial from flask_newton.xml (body obj_4111539686391_object): mass 1.0, COM, principal inertia + quat (wxyz)
qi = np.array([0.6964165633268763, 0.6812763744273828, -0.1612414329989596, 0.15769487073302924])
Ri = Rot.from_quat(qi[[1, 2, 3, 0]]).as_matrix(); I = Ri @ np.diag([0.007631826613944751, 0.007586864902845836, 0.0016285607468969547]) @ Ri.T
ph = dict(mass=1.0, com=np.array([0.0097641097381711, 0.13921871781349182, -0.007940029725432396]), inertia=I)
W, com_w = wg.demand_wrench(P, Q, ph, 20.0); RC, MU = 0.16786547, MU_ARG   # exercise 3 radius; mu: simulator 1.0 (calibration geom_friction), exercise display 0.1
Wn = np.hstack([W[:, :3], W[:, 3:] / RC]); R = Rot.from_quat(Q); up = np.array([0, 0, 1, 0, 0, 0.])
rows = []
for f in range(T):
    pts, nrm, per = [], [], []
    for h in (0, 1):   # 0 left, 1 right (exercise order)
        v = con['valid'][h, f]; per.append(int(v.sum()))
        pts.append(P[f] + R[f].apply(con['points'][h, f, v])); nrm.append(R[f].apply(con['normals'][h, f, v]))
    pts, nrm = np.vstack(pts), np.vstack(nrm); G = wg.generators(pts, nrm, com_w[f], RC, MU); w = Wn[f]
    rows.append(dict(frame=f, left=per[0], right=per[1], score=wg.feasibility(w, G), h_demand=float(bf.support(G, w / np.linalg.norm(w))[0]),
                     h_up=float(bf.support(G, up)[0]), gap=float((bf.support(G, bf.DIRS) <= 1e-12).mean())))
z = np.load(zfile)['err']; p = np.load(pfile)['err']
t = np.arange(T) / 20.0; A = {k: np.array([r[k] for r in rows]) for k in rows[0]}
first = lambda e, th: next((i for i, v in enumerate(e) if v > th), None)  # noqa: E731
summ = dict(frames=T, mu=MU, rc=RC, mass_kg=1.0,
            zero_replay_first_over_2cm=first(z, .02), zero_replay_first_over_10cm=first(z, .10),
            policy_end_frame=int(len(p) - 1), policy_first_over_2cm=first(p, .02),
            share_frames_infeasible=round(float((A['score'] > .5).mean()), 3),
            share_frames_no_contact=round(float(((A['left'] + A['right']) == 0).mean()), 3),
            window_330_352=dict(score_mean=round(float(A['score'][330:353].mean()), 3), gap_mean=round(float(A['gap'][330:353].mean()), 3),
                                left=int(A['left'][330:353].mean()), right=int(A['right'][330:353].mean())))
json.dump(dict(summary=summ, rows=rows), open(out_json, 'w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
ax[0].plot(t, A['left'], label='left hand', color='#3478bd'); ax[0].plot(t, A['right'], label='right hand', color='#da8730')
ax[0].set_ylabel('contacts'); ax[0].legend(loc='upper right', frameon=False)
ax[1].plot(t, A['score'], color='#7a3db8', label='gate score (0 feasible, 1 none)'); ax[1].plot(t, A['gap'], color='#999999', label='blob gap (share of 6-D directions with no push)')
ax[1].set_ylabel('0 to 1'); ax[1].legend(loc='upper right', frameon=False)
ax[2].plot(t, A['h_demand'], color='#2e8b57', label='push along needed wrench'); ax[2].plot(t, A['h_up'], color='#b8860b', label='push straight up')
ax[2].set_ylabel('support h(u)'); ax[2].legend(loc='upper right', frameon=False)
ax[3].plot(t[:len(z)], z * 100, color='#555555', label='no policy (zero residual)'); ax[3].plot(t[:len(p)], p * 100, color='#c0392b', label='trained policy (stops at failure)')
ax[3].axhline(10, ls='--', color='#c0392b', lw=.8); ax[3].set_ylim(0, 40); ax[3].set_ylabel('flask error (cm)'); ax[3].set_xlabel('time (s)')
ax[3].legend(loc='upper right', frameon=False)
for a in ax: a.axvline(len(p) / 20.0, color='#c0392b', lw=.6, alpha=.6); a.spines[['top', 'right']].set_visible(False)
fig.suptitle(f"Exercise 3 flask handover: contact blob (mu {MU}) vs physics (descriptive, one episode)", fontsize=11)
fig.tight_layout(); fig.savefig(out_png, dpi=110)
print(json.dumps(summ, indent=1))
