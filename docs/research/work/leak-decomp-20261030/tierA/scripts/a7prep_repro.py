"""ORACLE (public): recompute A7 rest configurations with the committed leak_tierA code and compare to the stored a7prep npz."""
import sys, json, types, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/tools'); sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import leak_tierA as LT, xstar_fit as XF, frame_xform as FX, trimesh
S = sys.argv[1]; W = f'{S}/leak/oracle_tierA'; T3 = f'{S}/map/scoring/t3'
XF.kit(f'{S}/map/scoring/kit/v2d_submission_kit')
P = json.load(open(f'{W}/a7prep.json'))['episodes']; worst = 0
for ep in XF.PUBLIC:
    names, gt = XF.mocap(T3, ep)
    V = np.load(f'{S}/refine/in/ep{ep}/poses_world_vo.npz'); N = len(V[V.files[0]]); gt = {n: g[:N] for n, g in gt.items()}
    D = types.SimpleNamespace(names=names, N=N, gt=gt, H=[XF.host_geometry(T3, n, s) for s, n in enumerate(names)],
                              Xg=FX.load_xform('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json', ep, names)[0])
    keep, dropped, z_t = LT.rest_configs(D)
    ok = keep == P[str(ep)]['frames'] and dropped == P[str(ep)]['dropped_held']
    c = np.mean([D.gt[n][0][:3, 3] for n in names], 0); T_tab = np.eye(4); T_tab[:3, 3] = [-c[0], -c[1], LT.MKA['table_z'] - z_t]
    for g, d in P[str(ep)]['geoms'].items():
        Z = np.load(d['npz']); A = str(Z['assets'])
        Xr = {n: (np.eye(4) if g == 'scan' else D.Xg[n]) for n in names}
        Cf = np.stack([np.stack([T_tab @ D.gt[n][t] @ Xr[n] for n in names]) for t in keep])
        vis = {n: np.asarray(trimesh.load(f'{A}/mesh/{n}/{n}.glb', force='mesh').vertices) for n in names}
        h = np.array([(vis[n] @ Cf[0, b, :3, :3].T + Cf[0, b, :3, 3])[:, 2].min() - LT.MKA['table_z'] for b, n in enumerate(names)])
        Cf[:, :, 2, 3] += np.where(np.abs(h) <= LT.SNAP_MAX, -h, 0.0)[None]
        dmax = float(np.abs(Cf - Z['configs']).max()) if Cf.shape == Z['configs'].shape else np.inf
        worst = max(worst, dmax); ok &= dmax < 1e-9
    print(f'ep{ep}: frames {keep} dropped {dropped} same {ok}', flush=True)
print('max abs config difference', worst)
