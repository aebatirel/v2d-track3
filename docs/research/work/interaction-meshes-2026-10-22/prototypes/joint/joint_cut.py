"""Joint two-object labelling over contested voxels (prototype of the 'joint-optimisation' design; scratch only).

Inference-legal inputs: the two objects' fused grids saved by fuse_save.py (our depth along our tracks), our poses.npz.
No scan or mocap is read here (diagnostics live in eval_*.py).

Model. Variables: one binary label per voxel of each object's independent solid S_o (recon_mesh closing + main part);
the joint step only REMOVES voxels (never adds). Energy
    sum_o sum_v carve_o(v) [v carved]                                  data: what the depth said about v
  + lam_s * sum_{v~v' in S_o} [labels differ]                          Potts smoothness inside each object
  + lam_x * sum_{(a,b) co-located} w_ab [a kept and b kept]            exclusion (rigid in each object's frame, all t)
carve_o(v) = beta + min(ev(v) / med_ev_o, cap), ev = weight * max(0, -tsdf) for observed voxels (0 for never observed,
filled by closing). Pairs (a in S_A, b in S_B) are co-located when a's centre maps into b's voxel (or b's into a's) at
frame t under T_BA = inv(cam_T_B[t]) cam_T_A[t]; w_ab = min(1, frames / n_req), pairs seen in fewer than n_min frames
are dropped (transient contacts, track glitches).
Two objects: flipping B's labels makes every term submodular, so one s-t min cut gives the exact global minimum.
Usage: joint_cut.py A.npz B.npz POSES.npz NAME_A NAME_B OUTDIR [key=value ...]
"""
import sys, os, json, time
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import maxflow

P_DEF = dict(lam_x=50.0, lam_s=0.3, beta=0.1, cap=2.0, n_min=2, n_req=4, stride=2, frames='', mode='joint',
             kit='/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit',
             prior_dir='', prior_w=0.0, halve=0.0, check_scipy=0)


def load_grid(path):
    z = np.load(path, allow_pickle=True)
    g = {k: z[k] for k in z.files}
    for k in ('voxel', 'half', 'trunc', 'auto_thr'):
        g[k] = float(g[k])
    for k in ('min_obs', 'near_vox', 'merge_vox'):
        g[k] = int(g[k])
    g['close'] = str(g['close']); g['obj'] = str(g['obj'])
    g['n'] = n = int(round(2 * g['half'] / g['voxel']))
    g['tsdf'] = g['tsdf'].reshape(n, n, n); g['wgt'] = g['wgt'].reshape(n, n, n)
    return g


def independent_solid(g):
    """recon_mesh.py lines 241-277, verbatim logic: closing (auto/fill/near) then the component nearest the origin."""
    vol, w, n = g['tsdf'], g['wgt'], g['n']
    known = w >= g['min_obs']; inside = known & (vol < 0)
    lab, nl = ndimage.label(~known)
    border = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(),
                             lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
    solid_fill = inside | (~known & ~np.isin(lab, border[border > 0]))
    solid_near = ndimage.binary_fill_holes(inside | (~known & ndimage.binary_dilation(inside, iterations=g['near_vox'])))

    def main_part(sol):
        lb, k = ndimage.label(ndimage.binary_dilation(sol, iterations=max(g['merge_vox'], 1)))
        if k == 0:
            return sol
        c0 = np.array(sol.shape) // 2; sz = ndimage.sum(sol, lb, range(1, k + 1)); cand = np.argsort(-sz)[:5] + 1
        best = cand[int(np.argmin([np.min(np.linalg.norm(np.argwhere(lb == q) - c0, axis=1)) for q in cand]))]
        return sol & (lb == best)
    mf = main_part(solid_fill)
    unk = float((mf & ~inside).sum() / max(mf.sum(), 1))
    mode = g['close'] if g['close'] != 'auto' else ('near' if unk > g['auto_thr'] else 'fill')
    solid = {'fill': solid_fill, 'near': solid_near, 'none': inside}[mode]
    grown = ndimage.binary_dilation(solid, iterations=g['merge_vox']) if g['merge_vox'] > 0 else solid
    lab, nl = ndimage.label(grown)
    sizes = ndimage.sum(grown, lab, range(1, nl + 1)); c = n // 2
    cand = np.argsort(-sizes)[:5] + 1
    dist = [np.min(np.linalg.norm(np.argwhere(lab == k) - c, axis=1)) for k in cand]
    solid = solid & (lab == cand[int(np.argmin(dist))])
    return solid, known, inside, mode


def centres(g, flat):
    n, vx, h = g['n'], g['voxel'], g['half']
    ijk = np.stack(np.unravel_index(flat, (n, n, n)), 1)
    return (ijk + 0.5) * vx - h


def to_index(g, p):
    n, vx, h = g['n'], g['voxel'], g['half']
    ijk = np.floor((p + h) / vx).astype(np.int64)
    ok = np.all((ijk >= 0) & (ijk < n), 1)
    flat = np.full(len(p), -1, np.int64)
    flat[ok] = np.ravel_multi_index(ijk[ok].T, (n, n, n))
    return flat


def mesh_solid(g, solid, out, kit):
    import trimesh
    from skimage.measure import marching_cubes
    field = np.where(solid, -1.0, 1.0).astype(np.float32)
    field = np.pad(ndimage.gaussian_filter(field, 0.8), 1, constant_values=1.0)
    v, f, _, _ = marching_cubes(field, 0.0, spacing=(g['voxel'],) * 3)
    v = v - g['voxel'] - g['half'] + 0.5 * g['voxel']
    m = trimesh.Trimesh(v, f, process=True)
    full = out.replace('.glb', '_full.glb'); m.export(full)
    if os.path.isdir(kit):
        sys.path.insert(0, kit)
        from v2dlb.mesh_budget import budget_mesh
        vb, fb = budget_mesh(full, 4096, 4096); m = trimesh.Trimesh(vb, fb, process=False)
    m.export(out)
    return m


def main():
    A_p, B_p, poses, nA, nB, outdir = sys.argv[1:7]
    prm = dict(P_DEF)
    for kv in sys.argv[7:]:
        k, v = kv.split('=', 1); prm[k] = type(P_DEF[k])(v) if not isinstance(P_DEF[k], str) else v
    os.makedirs(outdir, exist_ok=True); t0 = time.time()
    G = [load_grid(A_p), load_grid(B_p)]
    S, carve, flat, nodeof = [], [], [], []
    stats = dict(params=prm)
    off = 0
    for o, g in enumerate(G):
        solid, known, inside, mode = independent_solid(g)
        fl = np.flatnonzero(solid.ravel())
        ev = (g['wgt'] * np.clip(-g['tsdf'], 0, None)).ravel()[fl] * known.ravel()[fl]
        med = float(np.median(ev[ev > 0])) if (ev > 0).any() else 1.0
        c = prm['beta'] + np.minimum(ev / med, prm['cap'])
        nd = np.full(g['n'] ** 3, -1, np.int64); nd[fl] = off + np.arange(len(fl)); off += len(fl)
        S.append(solid); carve.append(c); flat.append(fl); nodeof.append(nd)
        stats[f'obj{o}'] = dict(name=g['obj'], closing=mode, solid_vox=int(len(fl)), solid_cm3=round(len(fl) * g['voxel'] ** 3 * 1e6, 2),
                               unknown_in_solid=round(float((~known.ravel()[fl]).mean()), 3), med_ev=round(med, 2),
                               obs_inside_cm3=round(float((ev > 0).sum() * g['voxel'] ** 3 * 1e6), 2))
    # co-located pairs over frames
    Pz = np.load(poses); TA = Pz[f'cam_T_{nA}'].astype(np.float64); TB = Pz[f'cam_T_{nB}'].astype(np.float64)
    if prm['frames']:
        a_, b_ = map(int, prm['frames'].split(':')); frames = np.arange(a_, b_, prm['stride'])
    else:
        frames = np.arange(0, len(TA), prm['stride'])
    XA, XB = centres(G[0], flat[0]), centres(G[1], flat[1])
    keys = []
    for t in frames:
        T_BA = np.linalg.inv(TB[t]) @ TA[t]; T_AB = np.linalg.inv(T_BA)
        jb = to_index(G[1], XA @ T_BA[:3, :3].T + T_BA[:3, 3]); ok = jb >= 0
        ib = nodeof[1][jb[ok]]; ia = nodeof[0][flat[0][ok]]; m = ib >= 0
        k1 = ia[m] * off + ib[m]
        ja = to_index(G[0], XB @ T_AB[:3, :3].T + T_AB[:3, 3]); ok = ja >= 0
        ia2 = nodeof[0][ja[ok]]; ib2 = nodeof[1][flat[1][ok]]; m = ia2 >= 0
        k2 = ia2[m] * off + ib2[m]
        keys.append(np.unique(np.r_[k1, k2]))
    allk = np.concatenate(keys) if keys else np.zeros(0, np.int64)
    uk, cnt = np.unique(allk, return_counts=True)
    sel = cnt >= prm['n_min']; uk, cnt = uk[sel], cnt[sel]
    pa, pb = uk // off, uk % off
    wx = prm['lam_x'] * np.minimum(1.0, cnt / prm['n_req'])
    stats['pairs'] = int(len(uk)); stats['frames_used'] = int(len(frames))
    stats['contested_vox'] = [int(len(np.unique(pa))), int(len(np.unique(pb)))]
    # optional tie-break prior (unary bias per object, a function of the voxel's position in its own frame): file
    # prior_dir/<name>.npy with one value per grid voxel, added to the carve cost (positive = harder to carve)
    if prm['prior_dir'] and prm['prior_w'] > 0:
        for o, g in enumerate(G):
            pr = np.load(os.path.join(prm['prior_dir'], g['obj'] + '.npy')).ravel()[flat[o]]
            carve[o] = carve[o] + prm['prior_w'] * pr
    # approach-side ('halving') prior, from our tracks only: each object yields on the side its partner approached
    # from. Contact segments = frames with co-located pairs; at each segment boundary the partner's origin, seen in
    # this object's frame, moves from the contact pose to the pose 5-10 used frames outside the segment; the mean unit
    # vector is the approach direction d_o. Carve cost of a contested voxel v gets - halve * clip(s, -1, 1), s = its
    # position along d_o relative to the contested set's centre, in units of the set's half extent.
    if prm['halve'] > 0 and len(pa):
        ncon = np.array([len(k) for k in keys]); con = ncon > 0
        Tr = [np.array([(np.linalg.inv(TA[t]) @ TB[t])[:3, 3] for t in frames]),     # B origin in A frame
              np.array([(np.linalg.inv(TB[t]) @ TA[t])[:3, 3] for t in frames])]     # A origin in B frame
        bnd = [i for i in range(len(frames)) if con[i] and ((i > 0 and not con[i - 1]) or (i + 1 < len(frames) and not con[i + 1]))]
        stats['approach'] = {}
        segs, i = [], 0
        while i < len(frames):
            if con[i]:
                j = i
                while j + 1 < len(frames) and con[j + 1]:
                    j += 1
                segs.append((i, j)); i = j + 1
            else:
                i += 1
        for o in range(2):
            vs = []
            for i, j in segs:                  # sliding insertion: travel inside the contact segment (>= 2 cm)
                v = Tr[o][i] - Tr[o][j]; nv = np.linalg.norm(v)
                if nv >= 0.02:
                    vs.append(v / nv)
            for i in ([] if vs else bnd):      # otherwise: approach / departure just outside the segment
                for j in (i - 1, i + 1):       # the last used frame before contact / first after it
                    if 0 <= j < len(frames) and not con[j]:
                        v = Tr[o][j] - Tr[o][i]; nv = np.linalg.norm(v)
                        if nv > 0.003:
                            vs.append(v / nv)
            if not vs:
                continue
            d = np.mean(vs, 0); coh = float(np.linalg.norm(d)); d /= max(coh, 1e-9)
            cs = np.unique(pa) if o == 0 else np.unique(pb) - len(flat[0])
            X = XA if o == 0 else XB
            proj = X @ d; pc = proj[cs]; mid = 0.5 * (pc.min() + pc.max()); hw = max(0.5 * (pc.max() - pc.min()), 1e-3)
            s = np.clip((proj - mid) / hw, -1, 1)
            carve[o] = np.maximum(0.02, carve[o] - prm['halve'] * s * np.isin(np.arange(len(X)), cs))
            stats['approach'][G[o]['obj']] = dict(dir=np.round(d, 3).tolist(), coherence=round(coh, 2), n=len(vs),
                                                  extent_cm=round(float(2 * hw * 100), 1))
    # graph
    keepA = np.ones(len(flat[0]), bool); keepB = np.ones(len(flat[1]), bool)
    if prm['mode'] == 'carve_both':                    # naive: every contested voxel leaves both objects
        keepA[np.unique(pa)] = False; keepB[np.unique(pb - len(flat[0]))] = False
    elif prm['mode'] == 'joint':
        gr = maxflow.Graph[float](); gr.add_nodes(off)
        nAn = len(flat[0])
        idx = np.arange(off)
        capS = np.r_[carve[0], np.zeros(len(flat[1]))]; capT = np.r_[np.zeros(nAn), carve[1]]
        gr.add_grid_tedges(idx, capS, capT)
        # exclusion: A kept (source) & B kept (sink) -> edge a->b cut
        if len(pa):
            gr.add_edges(pa.astype(np.int64), pb.astype(np.int64), wx.astype(np.float64), np.zeros(len(pa)))
        # Potts inside each object (6-neighbourhood)
        for o, g in enumerate(G):
            n = g['n']; nd = nodeof[o].reshape(n, n, n)
            for ax in range(3):
                s1 = [slice(None)] * 3; s2 = [slice(None)] * 3; s1[ax] = slice(0, -1); s2[ax] = slice(1, None)
                u, v = nd[tuple(s1)].ravel(), nd[tuple(s2)].ravel(); m = (u >= 0) & (v >= 0)
                if m.any():
                    gr.add_edges(u[m].astype(np.int64), v[m].astype(np.int64), np.full(int(m.sum()), prm['lam_s']),
                                 np.full(int(m.sum()), prm['lam_s']))
        flow = gr.maxflow()
        seg = np.array([gr.get_segment(int(i)) for i in range(off)])
        keepA = seg[:nAn] == 0; keepB = seg[nAn:] == 1
        stats['energy'] = round(float(flow), 2)
        if prm['check_scipy']:
            # licence-clean cross-check (PyMaxflow is GPL): same graph with scipy's Dinic on integer capacities
            from scipy.sparse import coo_matrix
            from scipy.sparse.csgraph import maximum_flow, breadth_first_order
            src, snk = off, off + 1; Q = 1000.0
            r, c_, w = [np.full(off, src), idx], [idx, np.full(off, snk)], [capS, capT]
            r.append(pa); c_.append(pb); w.append(wx)
            for o, g in enumerate(G):
                n = g['n']; nd = nodeof[o].reshape(n, n, n)
                for ax in range(3):
                    s1 = [slice(None)] * 3; s2 = [slice(None)] * 3; s1[ax] = slice(0, -1); s2[ax] = slice(1, None)
                    u, v = nd[tuple(s1)].ravel(), nd[tuple(s2)].ravel(); m = (u >= 0) & (v >= 0)
                    r += [u[m], v[m]]; c_ += [v[m], u[m]]; w += [np.full(int(m.sum()), prm['lam_s'])] * 2
            r, c_, w = np.concatenate(r), np.concatenate(c_), np.round(np.concatenate(w) * Q).astype(np.int64)
            ok = w > 0
            Cm = coo_matrix((w[ok], (r[ok], c_[ok])), shape=(off + 2, off + 2)).tocsr(); Cm.sum_duplicates()
            # scipy needs both directions present: add explicit zero-capacity reverse edges
            Rv = coo_matrix((np.zeros(Cm.nnz, np.int64), (Cm.tocoo().col, Cm.tocoo().row)), shape=Cm.shape).tocsr()
            Cm = (Cm + Rv).tocsr(); Cm.sort_indices()
            res = maximum_flow(Cm.astype(np.int32), src, snk, method='dinic')
            Fl = res.flow.tocsr(); Rs = (Cm - Fl).tocsr(); Rs.data[Rs.data < 0] = 0; Rs.eliminate_zeros()
            reach = breadth_first_order(Rs, src, directed=True, return_predecessors=False)
            S_side = np.zeros(off + 2, bool); S_side[reach] = True
            kA, kB = S_side[:nAn], ~S_side[nAn:off]
            stats['scipy_check'] = dict(flow=round(res.flow_value / Q, 2), agree_A=round(float((kA == keepA).mean()), 5),
                                        agree_B=round(float((kB == keepB).mean()), 5))
    # residual exclusion violations and carve accounting
    viol = keepA[pa] & keepB[pb - len(flat[0])]
    stats['violated_pairs'] = int(viol.sum())
    for o, (keep, c) in enumerate(((keepA, carve[0]), (keepB, carve[1]))):
        g = G[o]; vx3 = g['voxel'] ** 3 * 1e6
        ev_known = c > prm['beta'] + 1e-6
        stats[f'obj{o}'].update(carved_cm3=round(float((~keep).sum() * vx3), 2),
                                carved_observed_inside_cm3=round(float(((~keep) & ev_known).sum() * vx3), 2),
                                carved_mean_cost=round(float(c[~keep].mean()) if (~keep).any() else 0.0, 3))
        stats[f'obj{o}']['carved_obs_share'] = round(stats[f'obj{o}']['carved_observed_inside_cm3'] / max(stats[f'obj{o}']['obs_inside_cm3'], 1e-6), 4)
        stats[f'obj{o}']['contested_share'] = round(len(np.unique(pa if o == 0 else pb)) / max(len(flat[o]), 1), 3)
        sol = np.zeros(g['n'] ** 3, bool); sol[flat[o][keep]] = True; sol = sol.reshape((g['n'],) * 3)
        # keep the component nearest the origin (a carve could split off a sliver)
        lab, nl = ndimage.label(sol)
        if nl > 1:
            sz = ndimage.sum(sol, lab, range(1, nl + 1)); big = int(np.argmax(sz)) + 1
            stats[f'obj{o}']['split_parts'] = int(nl); stats[f'obj{o}']['split_off_cm3'] = round(float((sz.sum() - sz.max()) * vx3), 2)
        m = mesh_solid(g, sol, os.path.join(outdir, f"{g['obj']}.glb"), prm['kit'])
        np.save(os.path.join(outdir, f"{g['obj']}_solid.npy"), sol)
        np.save(os.path.join(outdir, f"{g['obj']}_indep.npy"), S[o])
        stats[f'obj{o}'].update(mesh_faces=int(len(m.faces)), mesh_extents_cm=np.round(m.extents * 100, 2).tolist())
    stats['sec'] = round(time.time() - t0, 1)
    json.dump(stats, open(os.path.join(outdir, 'joint_stats.json'), 'w'), indent=1)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
