"""Share of the lathe cavity (inner profile, floor to mouth) occupied by a mesh's solid. GT-free."""
import sys, json, numpy as np, trimesh
L = '/home/user/v2d-track3/meshes/'
res = {}
for lab, prof, meshes in [('blue_cup', 'out/lathe2/blue_cup_profile.npz', {'library_v3': L + 'library_v3/blue_cup.glb', 'lathe2 body': 'out/lathe2/blue_cup_body.glb'}),
                          ('beige_cup_v3x', 'out/lathe2/beige_cup_v3x_profile.npz', {'library_v3x': L + 'library_v3x/beige_cup.glb', 'lathe2 body': 'out/lathe2/beige_cup_v3x_body.glb'}),
                          ('white_pot', 'out/lathe2/white_pot_profile.npz', {'library_v3': L + 'library_v3/white_pot.glb', 'lathe2 body': 'out/lathe2/white_pot_body.glb'})]:
    z = np.load(prof); c0, d, e1, e2 = z['c0'], z['d'], z['e1'], z['e2']; t = float(z['t'])
    ph, pr = z['prof_h'], z['prof_r']; hb, hm = float(z['hb_plane']), float(z['hm_plane']); sgn = 1 if hm > hb else -1
    hf = hb + sgn * t
    rng = np.random.default_rng(0); n = 40000
    lo, hi = min(hf, hm), max(hf, hm); rmax = pr.max()
    H = rng.uniform(lo, hi, n); X = rng.uniform(-rmax, rmax, (n, 2))
    o = np.argsort(ph); rin = np.interp(H, ph[o], pr[o]) - t
    k = np.linalg.norm(X, axis=1) < rin
    P = c0 + H[k, None] * d + X[k, :1] * e1 + X[k, 1:] * e2
    vol = (hi - lo) * (2 * rmax) ** 2 * k.mean() * 1e6
    out = dict(cavity_cm3=round(vol, 1))
    for ml, mp in meshes.items():
        m = trimesh.load(mp, force='mesh')
        import open3d as o3d
        sc = o3d.t.geometry.RaycastingScene()
        sc.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(m.vertices), o3d.utility.Vector3iVector(m.faces))))
        occ = sc.compute_occupancy(o3d.core.Tensor(P.astype(np.float32))).numpy()
        out[f'{ml}_solid_share'] = round(float(occ.mean()), 3)
    res[lab] = out; print(lab, out)
json.dump(res, open('out/cavity.json', 'w'), indent=1)
