"""ORACLE (public): A7 side check. ep11 rest configurations with library_v3 placed by the kit registration X_kit (cup
spin 145 deg for the beige cup) instead of X*_geom (90 deg); otherwise exactly a7prep (table frame, per-object snap)."""
import sys, json, types, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/tools'); sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import leak_tierA as LT
S = sys.argv[1]; W = f'{S}/leak/oracle_tierA'; R = '/home/user/v2d-track3'
a = types.SimpleNamespace(kit=f'{S}/map/scoring/kit/v2d_submission_kit', perc=f'{S}/refine/in', t3=f'{S}/map/scoring/t3', lib=f'{R}/meshes/library_v3',
                          xgeom=f'{R}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json', xtrk=f'{R}/docs/research/work/leak-decomp-20261030/tierA/xstar_trk.json')
ep = 11; D = LT.load(a, ep); P = json.load(open(f'{W}/a7prep.json'))['episodes'][str(ep)]
keep, dropped, z_t = LT.rest_configs(D); assert keep == P['frames']
c = np.mean([D.gt[n][0][:3, 3] for n in D.names], 0); T_tab = np.eye(4); T_tab[:3, 3] = [-c[0], -c[1], LT.MKA['table_z'] - z_t]
for g in ('lib', 'lib_carve'):
    A = P['geoms'][g]['assets']
    Cf = np.stack([np.stack([T_tab @ D.gt[n][t] @ D.Xk[n] for n in D.names]) for t in keep])
    vis = {n: np.asarray(trimesh.load(f'{A}/mesh/{n}/{n}.glb', force='mesh').vertices) for n in D.names}
    h = np.array([(vis[n] @ Cf[0, b, :3, :3].T + Cf[0, b, :3, 3])[:, 2].min() - LT.MKA['table_z'] for b, n in enumerate(D.names)])
    Cf[:, :, 2, 3] += np.where(np.abs(h) <= LT.SNAP_MAX, -h, 0.0)[None]
    f = f'{W}/a7/ep{ep}/{g}_xkit.npz'; np.savez(f, names=np.array(D.names), configs=Cf, frames=np.array(keep), assets=A)
    print(g, f, 'f0 bottoms cm', np.round(h * 100, 2).tolist(), 'X_kit vs X*_geom', {n: LT.XF.compare(D.Xg[n] @ np.linalg.inv(D.Xk[n]), D.H[s]) for s, n in enumerate(D.names)})
