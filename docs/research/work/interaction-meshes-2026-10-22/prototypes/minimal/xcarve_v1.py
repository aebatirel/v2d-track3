"""XCarve prototype (minimal-carve design, scratch, 2026-10-22): evidence-arbitrated mutual exclusion between two
objects' fused TSDF grids, then recon_mesh's own closing + meshing. Inference-legal: our grids, our tracks only.

For every co-located frame t (both tracked), each voxel x of A's closed solid is mapped into B's grid with
T_BA = inv(cam_T_B[t]) @ cam_T_A[t]. B CLAIMS x at t when B's trilinear TSDF there is < 0 over OBSERVED voxels
(weight >= min_obs; closure-filled voxels never claim). Evidence e(x) = w * clip(-tsdf, 0, 1) (0 for closure-filled).
A voxel of A is carved (made known-free) when B claims it in >= K frames AND (e_A(x) == 0 or mean e_B >= R * e_A(x)).
'strong' = both evidences above their own object's median: physically impossible for two well-observed solids, so
its volume is the track-consistency gate. Evidences are those of the fused grids, never updated by carving, so the
result does not depend on the order of the objects (no alternation needed).
Usage: xcarve.py GRID_A GRID_B POSES.npz OUTDIR [--K 5] [--R 2] [--frames a:b] [--stride 2] [--jit_mm 5] [--kit KIT]
"""
import argparse, json, os, sys, time
import numpy as np
from scipy import ndimage


def load_grid(path):
    z = np.load(path, allow_pickle=True)
    G = dict(tsdf=z['tsdf'].astype(np.float32), w=z['wgt'].astype(np.float32), voxel=float(z['voxel']),
             half=float(z['half']), trunc=float(z['trunc']), min_obs=int(z['min_obs']), obj=str(z['obj']))
    if 'args' in z.files:
        a = json.loads(str(z['args']))
    else:
        a = {k: (z[k].item() if z[k].shape == () else z[k]) for k in ('close', 'auto_thr', 'near_vox', 'merge_vox')}
    G.update(close=str(a['close']), auto_thr=float(a['auto_thr']), near_vox=int(a['near_vox']), merge_vox=int(a['merge_vox']))
    n = int(round(2 * G['half'] / G['voxel'])); G['n'] = n
    G['tsdf'] = G['tsdf'].reshape(n, n, n); G['w'] = G['w'].reshape(n, n, n)
    G['known'] = G['w'] >= G['min_obs']
    G['obs_in'] = G['known'] & (G['tsdf'] < 0)
    G['ev'] = np.where(G['obs_in'], G['w'] * np.clip(-G['tsdf'], 0, 1), 0).astype(np.float32)
    return G


def solidify(G, free=None, mode=None):
    """recon_mesh.main lines 241-277 (closing + component nearest the origin), with FREE voxels forced known-outside."""
    known = G['known'].copy(); inside = G['obs_in'].copy()
    if free is not None:
        known |= free; inside &= ~free
    lab, nl = ndimage.label(~known)
    border = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(),
                             lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
    solid_fill = inside | (~known & ~np.isin(lab, border[border > 0]))
    solid_near = ndimage.binary_fill_holes(inside | (~known & ndimage.binary_dilation(inside, iterations=G['near_vox'])))
    if free is not None:
        solid_near &= ~free
    def main_part(sol, mv):
        lb, k = ndimage.label(ndimage.binary_dilation(sol, iterations=max(mv, 1)))
        if k == 0:
            return sol
        c0 = np.array(sol.shape) // 2; sz = ndimage.sum(sol, lb, range(1, k + 1)); cand = np.argsort(-sz)[:5] + 1
        best = cand[int(np.argmin([np.min(np.linalg.norm(np.argwhere(lb == q) - c0, axis=1)) for q in cand]))]
        return sol & (lb == best)
    mf = main_part(solid_fill, G['merge_vox'])
    unk = float((mf & ~inside).sum() / max(mf.sum(), 1))
    if mode is None:
        mode = G['close'] if G['close'] != 'auto' else ('near' if unk > G['auto_thr'] else 'fill')
    solid = {'fill': solid_fill, 'near': solid_near, 'none': inside}[mode]
    solid = main_part(solid, G['merge_vox'])
    return solid, mode, unk


def to_mesh(G, solid, out, kit, keep_open=None):
    """recon_mesh.main lines 278-299; KEEP_OPEN voxels (carved) are kept outside after the Gaussian, so a carved
    1-voxel slot is not closed again by the smoothing (a 1-voxel gap has centre value -0.01 otherwise)."""
    import trimesh
    from skimage.measure import marching_cubes
    field = np.where(solid, -1.0, 1.0).astype(np.float32)
    field = ndimage.gaussian_filter(field, 0.8)
    if keep_open is not None:
        field[keep_open] = np.maximum(field[keep_open], 0.25)
    field = np.pad(field, 1, constant_values=1.0)
    v, f, _, _ = marching_cubes(field, 0.0, spacing=(G['voxel'],) * 3)
    v = v - G['voxel'] - G['half'] + 0.5 * G['voxel']
    m = trimesh.Trimesh(v, f, process=True)
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        big = max(parts, key=lambda q: q.area)
        m = trimesh.util.concatenate([q for q in parts if q.area >= 0.05 * big.area and np.linalg.norm(q.centroid - big.centroid) < 0.15])
    full = out.replace('.glb', '_full.glb'); m.export(full)
    if kit and os.path.isdir(kit):
        sys.path.insert(0, kit)
        from v2dlb.mesh_budget import budget_mesh
        vb, fb = budget_mesh(full, 4096, 4096); m = trimesh.Trimesh(vb, fb, process=False)
    m.export(out)
    return m


def centres(G, idx):
    return (idx + 0.5) * G['voxel'] - G['half']


def claims(A, B, solidA, TA, TB, frames):
    """Per voxel of A's solid: number of frames B claims it, summed B evidence over those frames."""
    idx = np.argwhere(solidA); X = centres(A, idx)
    ncl = np.zeros(len(idx), np.int32); sev = np.zeros(len(idx), np.float32); per_frame = []
    tB = np.where(B['known'], B['tsdf'], 0).astype(np.float32); wB = np.where(B['known'], B['w'], 0).astype(np.float32)
    rA = np.linalg.norm(X, axis=1).max() + A['voxel']; rB = B['half'] * np.sqrt(3)
    for t in frames:
        T = np.linalg.inv(TB[t]) @ TA[t]
        if np.linalg.norm(T[:3, 3]) > rA + rB:
            per_frame.append(0); continue
        P = X @ T[:3, :3].T + T[:3, 3]
        fi = (P + B['half']) / B['voxel'] - 0.5
        ok = np.all((fi >= 0) & (fi <= B['n'] - 1), axis=1)
        if not ok.any():
            per_frame.append(0); continue
        c = fi[ok].T
        ts = ndimage.map_coordinates(tB, c, order=1); ws = ndimage.map_coordinates(wB, c, order=1)
        cl = (ts < 0) & (ws >= B['min_obs'])
        sel = np.flatnonzero(ok)[cl]
        ncl[sel] += 1; sev[sel] += (ws * np.clip(-ts, 0, 1))[cl]
        per_frame.append(int(cl.sum()))
    return idx, ncl, sev, np.array(per_frame)


BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def hand_claims(A, solidA, TA, WC, hands, frames, r):
    """Per voxel of A's solid: frames in which a MediaPipe bone capsule of radius R (world joints, our hands.npz) covers it."""
    H = np.load(hands); idx = np.argwhere(solidA); X = centres(A, idx); cnt = np.zeros(len(idx), np.int32)
    for t in frames:
        TwA = WC[t] @ TA[t]; Ti = np.linalg.inv(TwA); hit = np.zeros(len(idx), bool)
        for side in ('left', 'right'):
            if t >= len(H[f'valid_{side}']) or not H[f'valid_{side}'][t]:
                continue
            J = H[f'joints_{side}'][t].astype(np.float64)
            if not np.all(np.isfinite(J)):
                continue
            J = J @ Ti[:3, :3].T + Ti[:3, 3]
            lo, hi = J.min(0) - r, J.max(0) + r
            near = np.flatnonzero(np.all((X >= lo) & (X <= hi), 1))
            if not len(near):
                continue
            Q = X[near]; hq = np.zeros(len(near), bool)
            for i, j in BONES:
                ab = J[j] - J[i]; ap = Q - J[i]; h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
                hq |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= r
            hit[near] |= hq
        cnt += hit
    return idx, cnt


def rel_jitter(TA, TB, frames, win=9):
    tr = np.array([(np.linalg.inv(TB[t]) @ TA[t])[:3, 3] for t in frames])
    med = ndimage.median_filter(tr, size=(win, 1), mode='nearest')
    return np.linalg.norm(tr - med, axis=1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('ga'); p.add_argument('gb'); p.add_argument('poses'); p.add_argument('outdir')
    p.add_argument('--K', type=int, default=5); p.add_argument('--R', type=float, default=2.0)
    p.add_argument('--stride', type=int, default=2); p.add_argument('--frames', default='')
    p.add_argument('--jit_mm', type=float, default=5.0)
    p.add_argument('--kit', default='/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit')
    p.add_argument('--tag', default='xc')
    p.add_argument('--hands', default='', help='hands.npz: MediaPipe capsules (radius --hand_r) carve CLOSURE-ONLY voxels (evidence 0) in >= K frames')
    p.add_argument('--hand_r', type=float, default=0.007)
    a = p.parse_args(); t0 = time.time(); os.makedirs(a.outdir, exist_ok=True)
    A, B = load_grid(a.ga), load_grid(a.gb)
    P = np.load(a.poses); TA = P[f'cam_T_{A["obj"]}'].astype(np.float64); TB = P[f'cam_T_{B["obj"]}'].astype(np.float64)
    N = min(len(TA), len(TB))
    fr = np.arange(N)[::a.stride]
    if a.frames:
        lo, hi = map(int, a.frames.split(':')); fr = fr[(fr >= lo) & (fr < hi)]
    jit = rel_jitter(TA, TB, fr) * 1000
    good = np.all(np.isfinite(TA[fr].reshape(len(fr), -1)), 1) & np.all(np.isfinite(TB[fr].reshape(len(fr), -1)), 1) & (jit <= a.jit_mm)
    frames = fr[good]
    res = dict(A=A['obj'], B=B['obj'], K=a.K, R=a.R, frames_used=int(len(frames)), frames_dropped_jitter=int((~good).sum()))
    sol0, ev_med, cl = {}, {}, {}
    for nm, G in (('A', A), ('B', B)):
        s, mode, unk = solidify(G); sol0[nm] = (s, mode)
        ev_med[nm] = float(np.median(G['ev'][G['obs_in']]))
        res[f'{nm}_base'] = dict(mode=mode, unknown_share=round(unk, 3), solid_cm3=round(s.sum() * G['voxel'] ** 3 * 1e6, 2),
                                 obs_in_cm3=round(G['obs_in'].sum() * G['voxel'] ** 3 * 1e6, 2), ev_median=round(ev_med[nm], 2))
    # claims both ways, on the pass-1 (uncarved) solids and evidences
    cl['A'] = claims(A, B, sol0['A'][0], TA, TB, frames)
    cl['B'] = claims(B, A, sol0['B'][0], TB, TA, frames)
    carved = {}
    for nm, G, other in (('A', A, 'B'), ('B', B, 'A')):
        idx, ncl, sev, pf = cl[nm]
        evA = G['ev'][tuple(idx.T)]
        mean_eB = np.where(ncl > 0, sev / np.maximum(ncl, 1), 0)
        contested = ncl >= a.K
        lose = contested & ((evA == 0) | (mean_eB >= a.R * evA))
        tie = contested & ~lose & (evA < a.R * mean_eB)
        strong = contested & (evA >= ev_med[nm]) & (mean_eB >= ev_med[other])
        v3 = G['voxel'] ** 3 * 1e6
        free = np.zeros_like(G['known']); free[tuple(idx[lose].T)] = True
        carved[nm] = free
        res[f'{nm}_claims'] = dict(claimed_any_cm3=round(float((ncl > 0).sum() * v3), 2), contested_cm3=round(float(contested.sum() * v3), 2),
                                   carved_cm3=round(float(lose.sum() * v3), 2), carved_closure_only_cm3=round(float((lose & (evA == 0)).sum() * v3), 2),
                                   tie_cm3=round(float(tie.sum() * v3), 2), strong_cm3=round(float(strong.sum() * v3), 2),
                                   kept_contested_cm3=round(float((contested & ~lose).sum() * v3), 2),
                                   frames_with_claims=int((pf > 0).sum()))
    if a.hands:
        WC = P['world_T_cam'].astype(np.float64); hf = np.arange(N)[::a.stride]
        for nm, G, TT in (('A', A, TA), ('B', B, TB)):
            idx, cnt = hand_claims(G, sol0[nm][0], TT, WC, a.hands, hf, a.hand_r)
            evx = G['ev'][tuple(idx.T)]; v3 = G['voxel'] ** 3 * 1e6
            hc = (cnt >= a.K) & (evx == 0); hw = (cnt >= a.K) & (evx > 0)
            res[f'{nm}_hands'] = dict(covered_cm3=round(float((cnt >= a.K).sum() * v3), 2), carved_closure_only_cm3=round(float(hc.sum() * v3), 2),
                                      protected_observed_cm3=round(float(hw.sum() * v3), 2))
            carved[nm][tuple(idx[hc].T)] = True
    for nm, G in (('A', A), ('B', B)):
        s1, mode, unk = solidify(G, free=carved[nm], mode=sol0[nm][1])
        v3 = G['voxel'] ** 3 * 1e6
        res[f'{nm}_after'] = dict(solid_cm3=round(s1.sum() * v3, 2), removed_cm3=round(float((sol0[nm][0] & ~s1).sum() * v3), 2),
                                  added_cm3=round(float((s1 & ~sol0[nm][0]).sum() * v3), 2))
        np.savez_compressed(f'{a.outdir}/{G["obj"]}_{a.tag}_vox.npz', base=sol0[nm][0], after=s1, carved=carved[nm], voxel=G['voxel'], half=G['half'])
        to_mesh(G, sol0[nm][0], f'{a.outdir}/{G["obj"]}_base.glb', a.kit)
        to_mesh(G, s1, f'{a.outdir}/{G["obj"]}_{a.tag}.glb', a.kit, keep_open=carved[nm])
    res['sec'] = round(time.time() - t0, 1)
    json.dump(res, open(f'{a.outdir}/{a.tag}_result.json', 'w'), indent=1); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
