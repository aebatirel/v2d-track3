"""ORACLE DIAGNOSTIC (public ep0 only): per-frame errors of P_s (scan templates), P_o (library_v3) and the refine-input
P (25 Oct guard run, library_v2) vs mocap, in the * convention (lib tracks taken to scan frames by X*_geom), two ways:
  kit   the scorer's own frame-0 scene alignment (_align_registered_scene; slot 0 = white_pot is the anchor)
  G     one world transform perception -> mocap fitted (soft-L1) on the P_o pot over all frames; the same G for every
        arm (they share world_T_cam), so each object's error is independent of the other's frame-0 pose.
Plus mocap phases (speed), lid-on-pot relation, and hand proximity (refine/in hands vs mocap mapped by G^-1).
Reads mocap: diagnostics only."""
import sys, json, os
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
REPO = '/home/user/v2d-track3'
sys.path.insert(0, REPO + '/tools')
import xstar_fit as XF
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
KIT = S + '/map/scoring/kit/v2d_submission_kit'; T3D = S + '/map/scoring/t3'
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 0
OUT = S + f'/leak/diag_ep{EP}/out'
os.makedirs(OUT, exist_ok=True)
XF.kit(KIT); T3 = XF.K['T3']
FPS = 20.25411910142744
names, gt = XF.mocap(T3D, EP)
N = len(gt[names[0]])
H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
XG = json.load(open(REPO + '/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
X = {n: np.array(XG[n]['X_scan_T_lib']) for n in names}
R = S + '/leak/p1/oracle_roots'
def load(path, lib):
    V = np.load(path); out = {}
    for n in names:
        T = V[n].astype(np.float64)[:N]
        out[n] = T @ np.linalg.inv(X[n]) if lib else T
    return out
arms = {'Ps': load(f'{R}/Ps_scan/ep{EP}/poses_world_vo.npz', False),
        'Po': load(f'{R}/Po/ep{EP}/poses_world_vo.npz', True),
        'Pr': load(f'{S}/refine/in/ep{EP}/poses_world_vo.npz', True)}
if os.path.exists(f'{R}/Po2/ep{EP}/poses_world_vo.npz'):
    arms['Po2'] = load(f'{R}/Po2/ep{EP}/poses_world_vo.npz', True)
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
TW = None

def kit_aligned(track):
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(len(names)):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], H[s]['anchor'], np.eye(3))
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    ach = T3._align_registered_scene(ach, ref, axes)
    add = np.stack([T3._symmetry_point_errors(ach[:, :, s], ref[:, :, s], pts[s], axes[s], orders[s])[:, 0] for s in range(len(names))], 1)
    te = np.linalg.norm(ach[:, 0, :, :3] - ref[:, 0, :, :3], axis=-1)
    re = T3._symmetry_orientation_errors(ach, ref, axes, orders)[:, 0]
    auc = {n: float(T3._registered_pose_metric('add_auc', ach[:, :, s:s+1], ref[:, :, s:s+1], pts[s:s+1], axes[s:s+1], orders[s:s+1])) for s, n in enumerate(names)}
    return add * 100, te * 100, np.degrees(re), auc, ach, ref

def share(add_cm):  # per-frame share of the ADD-AUC (trapezoid over 1..9 cm), AUC = mean over frames
    thr = np.arange(1, 10); w = np.r_[0.5, np.ones(7), 0.5] / 8
    return ((add_cm[..., None] < thr) * w).sum(-1)

# --- world transform G (perception world -> mocap world), fitted on P_o's white_pot (no symmetry) over all frames
pot = names.index('white_pot') if 'white_pot' in names else 0
p0 = H[pot]['points'][::10] + H[pot]['anchor']
Tp = arms['Po'][names[pot]]; Tg = gt[names[pot]]
def G_of(x):
    M = np.eye(4); M[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix(); M[:3, 3] = x[3:]; return M
def res(x):
    G = G_of(x); A = np.einsum('ij,njk->nik', G, Tp)
    a = np.einsum('nij,pj->npi', A[:, :3, :3], p0) + A[:, None, :3, 3]
    b = np.einsum('nij,pj->npi', Tg[:, :3, :3], p0) + Tg[:, None, :3, 3]
    return (a - b).ravel()
# init from frame 0
G0 = Tg[0] @ np.linalg.inv(Tp[0])
x0 = np.r_[Rot.from_matrix(G0[:3, :3]).as_rotvec(), G0[:3, 3]]
sol = least_squares(res, x0, loss='soft_l1', f_scale=0.02)
G = G_of(sol.x)
rr = res(sol.x).reshape(N, -1, 3); fit_med_cm = float(np.median(np.linalg.norm(rr, axis=-1).mean(1)) * 100)

def indep(track):
    out = {}
    for s, n in enumerate(names):
        A = np.einsum('ij,njk->nik', G, track[n]); B = gt[n]
        c = H[s]['anchor']; pa = A[:, :3, :3] @ c + A[:, :3, 3]; pb = B[:, :3, :3] @ c + B[:, :3, 3]
        te = np.linalg.norm(pa - pb, axis=1) * 100
        Rrel = np.einsum('nji,njk->nik', B[:, :3, :3], A[:, :3, :3])        # body-frame error B^T A
        rot = np.degrees(Rot.from_matrix(Rrel).magnitude())
        P = H[s]['points'] + c
        qa = np.einsum('nij,pj->npi', A[:, :3, :3], P) + A[:, None, :3, 3]
        best = np.full(N, np.inf); rot_sym = rot.copy()
        for Sm in XF.sym_group(H[s], 360 if H[s]['order'] == 360 else 2):
            Bs = np.einsum('nij,jk->nik', B, Sm)
            qb = np.einsum('nij,pj->npi', Bs[:, :3, :3], P) + Bs[:, None, :3, 3]
            best = np.minimum(best, np.linalg.norm(qa - qb, axis=-1).mean(1))
            if H[s]['order'] == 2:
                rot_sym = np.minimum(rot_sym, np.degrees(Rot.from_matrix(np.einsum('nji,njk->nik', Bs[:, :3, :3], A[:, :3, :3])).magnitude()))
        d = dict(t_cm=te, rot_deg=rot, add_cm=best * 100)
        if H[s]['order']:
            ax = H[s]['axis']; aa = A[:, :3, :3] @ ax; ab = B[:, :3, :3] @ ax
            d['axis_tilt_deg'] = np.degrees(np.arccos(np.clip((aa * ab).sum(1), -1, 1)))
            if H[s]['order'] == 2:
                d['rot_sym_deg'] = rot_sym
        out[n] = d
    return out

# --- mocap phases
def speeds(T, c):
    p = T[:, :3, :3] @ c + T[:, :3, 3]
    v = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * 100 * FPS
    w = np.r_[0, np.degrees(Rot.from_matrix(np.einsum('nji,njk->nik', T[:-1, :3, :3], T[1:, :3, :3])).magnitude())] * FPS
    k = np.ones(5) / 5
    return np.convolve(v, k, 'same'), np.convolve(w, k, 'same'), p
ph = {}
for s, n in enumerate(names):
    v, w, p = speeds(gt[n], H[s]['anchor'])
    ph[n] = dict(speed_cms=v, angvel_dps=w, moving=(v > 3) | (w > 15), pos=p)
rel = None
if 'white_pot' in names and 'white_pot_lid' in names:
    Tpot, Tlid = gt['white_pot'], gt['white_pot_lid']
    Lr = np.einsum('nji,njk->nik', Tpot, Tlid)  # inv(pot) @ lid for rigid (approx: use proper inverse)
    Lr = np.stack([np.linalg.inv(Tpot[i]) @ Tlid[i] for i in range(N)])
    cl = H[names.index('white_pot_lid')]['anchor']
    q = Lr[:, :3, :3] @ cl + Lr[:, :3, 3]
    rel = dict(d_from_f0_cm=np.linalg.norm(q - q[0], axis=1) * 100,
               rot_from_f0_deg=np.degrees(Rot.from_matrix(np.einsum('nji,njk->nik', Lr[[0] * N, :3, :3], Lr[:, :3, :3])).magnitude()))
# --- hands (perception world, refine inputs) vs mocap objects mapped to perception world by G^-1
hd = {}
hf = f'{S}/refine/in/ep{EP}/hands_refined.npz'
if os.path.exists(hf):
    Hn = np.load(hf); Gi = np.linalg.inv(G)
    for s, n in enumerate(names):
        P = H[s]['points'][::5] + H[s]['anchor']
        A = np.einsum('ij,njk->nik', Gi, gt[n]); q = np.einsum('nij,pj->npi', A[:, :3, :3], P) + A[:, None, :3, 3]
        dmin = np.full(N, np.inf)
        for side in ('left', 'right'):
            J = Hn[f'joints_{side}'][:N].astype(np.float64); ok = Hn[f'valid_{side}'][:N]
            d = np.linalg.norm(J[:, :, None] - q[:, None], axis=-1).min((1, 2)) * 100
            dmin = np.where(ok, np.minimum(dmin, d), dmin)
        hd[n] = dmin

res_all = {'ep': EP, 'names': names, 'N': N, 'G_fit_median_cm_pot_Po': round(fit_med_cm, 3)}
per = {}
for a, T in arms.items():
    add, te, re, auc, ach, ref = kit_aligned(T)
    ind = indep(T)
    per[a] = dict(kit=dict(add=add, t=te, r=re), auc=auc, ind=ind)
    res_all[a] = dict(auc_kit={k: round(v, 4) for k, v in auc.items()}, auc_scene=round(float(np.mean(list(auc.values()))), 4))
np.savez(f'{OUT}/perframe.npz', **{f'{a}_{k}_{n}': (per[a]['kit'][k][:, s]) for a in per for k in ('add', 't', 'r') for s, n in enumerate(names)},
         **{f'{a}_ind_{k}_{n}': v for a in per for n in names for k, v in per[a]['ind'][n].items()},
         **{f'mocap_speed_{n}': ph[n]['speed_cms'] for n in names}, **{f'mocap_angvel_{n}': ph[n]['angvel_dps'] for n in names},
         **({f'hand_{n}': hd[n] for n in hd}), **({'lid_rel_d': rel['d_from_f0_cm'], 'lid_rel_rot': rel['rot_from_f0_deg']} if rel else {}),
         G=G)
json.dump(res_all, open(f'{OUT}/summary.json', 'w'), indent=1)
print(json.dumps(res_all, indent=1))
