"""ORACLE DIAGNOSTIC (public ep31 only): per-frame error of the Phase-1 tracks (P_o, P_o2, P_s) vs mocap, * convention.
Reads ground truth (mocap, public scans) AFTER inference. Nothing here feeds eval inference.
Alignments compared (all on the same per-object kit-registered poses):
  kit   - the scorer's own scene alignment: slot 0 (mini_sweeper, no symmetry axis) full frame-0 pose
  rack0 - diagnostic: the same rule anchored on the rack's frame-0 pose instead
  bw    - one rigid world transform fitted over all frames and both objects (oracle; removes scene-alignment error)
Usage: python -I diag31.py OUT_JSON
"""
import json, os, sys
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

EP = 31
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
RUN = f'{S}/leak/p1/runs/20261030-orcP1b-87fc869/results/leak_p1/ep31'
REF = f'{S}/refine/in/ep31'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT); T3 = XF.K['T3']
THR = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8
FPS = 20.254
Z = np.array([0, 0, 1.0])


def auc_of(e):
    return float(np.mean((e[:, None] < THR[None]).astype(float) @ TW)) if len(e) else float('nan')


def load_tracks():
    names, gt = XF.mocap(T3D, EP, None)
    out = {}
    V = np.load(f'{RUN}/perc2/poses_world_vo.npz'); N = len(V[names[0]])
    out['Po'] = {n: V[n].astype(np.float64) @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    if os.path.exists(f'{RUN}/perc2rep/poses_world_vo.npz'):
        V2 = np.load(f'{RUN}/perc2rep/poses_world_vo.npz')
        out['Po2'] = {n: V2[n].astype(np.float64) @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    Vs = np.load(f'{RUN}/perc2scan/poses_world_vo.npz')
    out['Ps'] = {n: Vs[n].astype(np.float64) for n in names}
    gt = {n: gt[n][:N] for n in names}
    return names, gt, N, out


def to_mats(x7):
    M = np.repeat(np.eye(4)[None], len(x7), 0); M[:, :3, :3] = T3._rotation_matrix(x7[:, 3:]); M[:, :3, 3] = x7[:, :3]; return M


def prep(names, track, gt, H):
    """kit body conversion (identity registration: tracks are in scan frames) -> ach, ref as (N,1,B,7) anchored."""
    N = len(track[names[0]]); B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ca, Rb = XF.reg_of_X(np.eye(4), H[s]['anchor'])
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], ca, Rb)
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    return ach, ref


def apply_world(ach, R, t):
    out = ach.copy(); out[..., :3] = ach[..., :3] @ R.T + t
    out[..., 3:] = T3._quaternion_multiply(Rot.from_matrix(R).as_quat(), ach[..., 3:]); return out


def align_on(ach, ref, s):
    """the kit's rule for a symmetry-free anchor, on slot s"""
    qa = ach[0, 0, s, 3:]; qr = ref[0, 0, s, 3:]
    R = T3._rotation_matrix(T3._quaternion_multiply(qr, qa * [-1, -1, -1, 1]))
    t = ref[0, 0, s, :3] - R @ ach[0, 0, s, :3]
    return R, t


def best_world(ach, ref, H, frames=None):
    """oracle: one rigid transform over the given frames, both objects, matching 60 host points per object"""
    P, Q = [], []
    idx = np.arange(ach.shape[0]) if frames is None else np.asarray(frames)
    for s in range(ach.shape[2]):
        pts = H[s]['points'][::17]
        Ra = T3._rotation_matrix(ach[idx, 0, s, 3:]); Rr = T3._rotation_matrix(ref[idx, 0, s, 3:])
        P.append((np.einsum('nij,vj->nvi', Ra, pts) + ach[idx, 0, s, None, :3]).reshape(-1, 3))
        Q.append((np.einsum('nij,vj->nvi', Rr, pts) + ref[idx, 0, s, None, :3]).reshape(-1, 3))
    P = np.concatenate(P); Q = np.concatenate(Q)
    mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ D @ U.T
    return R, mq - R @ mp


def per_frame(al, ref, H, names):
    res = {}
    for s, n in enumerate(names):
        add = T3._symmetry_point_errors(al[:, :, s], ref[:, :, s], H[s]['points'], H[s]['axis'], H[s]['order'])[:, 0]
        dt = al[:, 0, s, :3] - ref[:, 0, s, :3]
        Ra = T3._rotation_matrix(al[:, 0, s, 3:]); Rr = T3._rotation_matrix(ref[:, 0, s, 3:])
        dR = np.einsum('nij,nkj->nik', Ra, Rr)  # Ra Rr^T (world-frame rotation error)
        rot = np.degrees(Rot.from_matrix(dR).magnitude())
        res[n] = dict(add=add, dt=dt, rot=rot, dRvec=Rot.from_matrix(dR).as_rotvec())
    return res


def main():
    names, gt, N, tr = load_tracks()
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    sw, rk = names.index('mini_sweeper'), names.index('plastic_dish_rack')
    R = {'names': names, 'N': N}
    # ---- mocap phases (oracle labels)
    refpos = {n: gt[n][:, :3, 3] + np.einsum('nij,j->ni', gt[n][:, :3, :3], H[s]['anchor']) for s, n in enumerate(names)}
    ph = {}
    for s, n in enumerate(names):
        p = refpos[n]; v = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * FPS * 100
        Rm = gt[n][:, :3, :3]
        w = np.r_[0, np.degrees(Rot.from_matrix(np.einsum('nij,nkj->nik', Rm[1:], Rm[:-1])).magnitude())] * FPS
        ph[n] = dict(speed=v, wrate=w, disp=np.linalg.norm(p - p[0], axis=1) * 100, z=p[:, 2] * 100,
                     rot_from_f0=np.degrees(Rot.from_matrix(np.einsum('nij,kj->nik', Rm, Rm[0])).magnitude()))
    seg = {}
    for n in names:
        mv = (np.convolve(ph[n]['speed'], np.ones(5) / 5, 'same') > 3) | (np.convolve(ph[n]['wrate'], np.ones(5) / 5, 'same') > 15)
        segs = []; st = 0
        for i in range(1, N + 1):
            if i == N or mv[i] != mv[st]:
                segs.append([int(st), int(i - 1), 'moving' if mv[st] else 'rest']); st = i
        seg[n] = dict(segs=segs, moving=mv)
    R['segments_mocap'] = {n: seg[n]['segs'] for n in names}
    R['mocap_motion'] = {n: dict(max_disp_cm=round(float(ph[n]['disp'].max()), 2), max_rot_deg=round(float(ph[n]['rot_from_f0'].max()), 2)) for n in names}
    # ---- contact / nesting from mocap: sweeper samples vs rack surface (dense samples), and inside the rack's bbox
    import trimesh
    rmesh = trimesh.load(XF.scan_path(T3D, names[rk]), force='mesh'); smesh = trimesh.load(XF.scan_path(T3D, names[sw]), force='mesh')
    rpts = trimesh.sample.sample_surface(rmesh, 120000, seed=3)[0]; spts = trimesh.sample.sample_surface(smesh, 3000, seed=4)[0]
    tree = cKDTree(rpts); lo, hi = np.asarray(rmesh.bounds[0]), np.asarray(rmesh.bounds[1])
    gapcm, inbox = np.zeros(N), np.zeros(N)
    for i in range(N):
        Mrel = np.linalg.inv(gt[names[rk]][i]) @ gt[names[sw]][i]   # sweeper in rack scan frame
        q = spts @ Mrel[:3, :3].T + Mrel[:3, 3]
        gapcm[i] = tree.query(q)[0].min() * 100
        inbox[i] = np.mean(np.all((q > lo) & (q < hi), axis=1))
    R['contact'] = dict(gap_cm=np.round(gapcm, 2).tolist(), frac_sweeper_in_rack_bbox=np.round(inbox, 3).tolist(),
                        rack_bbox_cm=np.round((hi - lo) * 100, 1).tolist())
    # ---- per arm: three alignments
    res = {}
    for arm, T in tr.items():
        ach, ref = prep(names, T, gt, H)
        A = {}
        Rk, tk = align_on(ach, ref, 0); A['kit'] = (Rk, tk)
        A['rack0'] = align_on(ach, ref, rk)
        A['bw'] = best_world(ach, ref, H)
        out = {}
        for k, (Rw, tw) in A.items():
            al = apply_world(ach, Rw, tw)
            if k == 'kit':  # check against the scorer itself
                al2 = T3._align_registered_scene(ach, ref, [h['axis'] for h in H])
                assert np.abs(al2 - al).max() < 1e-6 or np.abs(np.abs(al2[..., 3:]) - np.abs(al[..., 3:])).max() < 1e-6
            out[k] = dict(pf=per_frame(al, ref, H, names), R=Rw, t=tw, al=al)
        res[arm] = dict(out=out, ach=ach, ref=ref)
    # world-alignment difference kit vs bw: the scene rotation the scorer applies because of the sweeper's f0 error
    R['align_diff'] = {}
    for arm in res:
        Rk = res[arm]['out']['kit']['R']; Rb = res[arm]['out']['bw']['R']
        dR = Rk @ Rb.T
        R['align_diff'][arm] = dict(rot_deg=round(float(np.degrees(Rot.from_matrix(dR).magnitude())), 2),
                                    rotvec_deg=np.round(np.degrees(Rot.from_matrix(dR).as_rotvec()), 2).tolist())
    # ---- hands (perception world) -> mocap world via P_s best-world alignment; nearest joint to each object's anchor
    h = np.load(f'{REF}/hands_refined.npz', allow_pickle=True)
    Rb, tb = res['Ps']['out']['bw']['R'], res['Ps']['out']['bw']['t']
    hand = {}
    for n in names:
        hand[n] = {}
    for side in ('left', 'right'):
        J = h[f'joints_{side}'].astype(np.float64); valid = h[f'valid_{side}']
        Jm = J @ Rb.T + tb
        for s, n in enumerate(names):
            # distance to the object's surface (60 host points), not the anchor: the rack is 51 cm long
            P = np.einsum('nij,vj->nvi', gt[n][:, :3, :3], H[s]['points'][::10] + H[s]['anchor']) + gt[n][:, None, :3, 3]
            d = np.array([np.linalg.norm(Jm[i][:, None] - P[i][None], axis=-1).min() for i in range(N)]) * 100
            d[~valid] = np.nan; hand[n][side] = d
    for n in names:
        hand[n]['min'] = np.fmin(hand[n]['left'], hand[n]['right'])
    # ---- summaries
    def st(e, idx):
        idx = np.asarray(idx, int)
        if len(idx) == 0:
            return None
        return dict(n=int(len(idx)), add_med=round(float(np.median(e[idx]) * 100), 2), add_max=round(float(e[idx].max() * 100), 2),
                    auc=round(auc_of(e[idx]), 4))
    summ = {}
    for arm in res:
        summ[arm] = {}
        for k in ('kit', 'rack0', 'bw'):
            pf = res[arm]['out'][k]['pf']
            summ[arm][k] = {n: dict(auc=round(auc_of(pf[n]['add']), 4), add_f0=round(float(pf[n]['add'][0] * 100), 2),
                                    add_med=round(float(np.median(pf[n]['add']) * 100), 2), add_max=round(float(pf[n]['add'].max() * 100), 2),
                                    t_f0=round(float(np.linalg.norm(pf[n]['dt'][0]) * 100), 2), rot_f0=round(float(pf[n]['rot'][0]), 2),
                                    dz_f0=round(float(pf[n]['dt'][0] @ Z * 100), 2),
                                    t_med=round(float(np.median(np.linalg.norm(pf[n]['dt'], axis=1)) * 100), 2), rot_med=round(float(np.median(pf[n]['rot'])), 2))
                            for n in names}
            summ[arm][k]['episode_auc'] = round(float(np.mean([summ[arm][k][n]['auc'] for n in names])), 4)
    R['summary'] = summ
    # official scorer number for each arm (sanity)
    R['official'] = {}
    for arm, T in tr.items():
        REG = [XF.reg_of_X(np.eye(4), H[s]['anchor']) for s in range(len(names))]
        R['official'][arm] = XF.score_track(names, T, gt, H, REG)
    # phases for the sweeper (mocap) and rack; hand-near masks
    mv = seg['mini_sweeper']['moving']
    first_move = int(np.where(mv)[0][0]) if mv.any() else N
    hn_s = np.nan_to_num(hand['mini_sweeper']['min'], nan=99) < 6
    hn_r = np.nan_to_num(hand['plastic_dish_rack']['min'], nan=99) < 6
    near = gapcm < 1.0
    masks = dict(rest_before_first_move=np.arange(N) < first_move, sweeper_moving=mv, sweeper_rest=~mv,
                 sweeper_hand_near=hn_s, sweeper_hand_far=~hn_s, rack_hand_near=hn_r, rack_hand_far=~hn_r,
                 sweeper_touching_rack=near, sweeper_off_rack=~near, sweeper_in_rack_bbox=inbox > 0.3)
    split = {}
    for arm in res:
        split[arm] = {}
        for k in ('kit', 'bw'):
            split[arm][k] = {n: {m: st(res[arm]['out'][k]['pf'][n]['add'], np.where(msk)[0]) for m, msk in masks.items()} for n in names}
    R['split'] = split
    R['first_move_sweeper'] = first_move
    # ---- per-frame rows
    rows = []
    for i in range(N):
        row = dict(f=i, gap_cm=round(float(gapcm[i]), 2), in_bbox=round(float(inbox[i]), 2))
        for n in names:
            row[n] = dict(speed=round(float(ph[n]['speed'][i]), 1), disp=round(float(ph[n]['disp'][i]), 1), z=round(float(ph[n]['z'][i]), 1),
                          moving=bool(seg[n]['moving'][i]),
                          hand=None if np.isnan(hand[n]['min'][i]) else round(float(hand[n]['min'][i]), 1))
            for arm in res:
                for k in ('kit', 'bw'):
                    pf = res[arm]['out'][k]['pf'][n]
                    row[n][f'{arm}_{k}'] = dict(add=round(float(pf['add'][i] * 100), 2), t=round(float(np.linalg.norm(pf['dt'][i]) * 100), 2),
                                                dz=round(float(pf['dt'][i] @ Z * 100), 2), rot=round(float(pf['rot'][i]), 2))
        rows.append(row)
    R['frames'] = rows
    json.dump(R, open(sys.argv[1], 'w'), indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    np.savez(sys.argv[1].replace('.json', '_arrays.npz'),
             **{f'{arm}_{k}_{n}_{q}': res[arm]['out'][k]['pf'][n][q] for arm in res for k in ('kit', 'rack0', 'bw') for n in names for q in ('add', 'dt', 'rot', 'dRvec')},
             **{f'{arm}_{k}_R': res[arm]['out'][k]['R'] for arm in res for k in ('kit', 'rack0', 'bw')},
             **{f'{arm}_{k}_t': res[arm]['out'][k]['t'] for arm in res for k in ('kit', 'rack0', 'bw')},
             gap=gapcm, inbox=inbox, **{f'hand_{n}': hand[n]['min'] for n in names},
             **{f'moving_{n}': seg[n]['moving'] for n in names})
    print(json.dumps(dict(summary=summ, official=R['official'], align_diff=R['align_diff'], segments=R['segments_mocap'],
                          motion=R['mocap_motion'], first_move=first_move), indent=1))


if __name__ == '__main__':
    main()
