import sys, importlib.util, numpy as np, trimesh
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
names, O, P, Q, fps = I.load_ref(sys.argv[1])
for f in (0, 20, 38, 46, 80, 100, 117, 140, 160):
    print(f, ' '.join(f'{n}: up_in_file {np.round(O[f,b,:3,:3].T @ [0,0,1], 3)}' for b, n in enumerate(names)))
# relative pose beige in blue frame
for f in (0, 46, 60, 90, 100, 105, 110, 117, 120, 140, 160):
    R = np.linalg.inv(O[f, 0]) @ O[f, 1]
    print(f, 'beige origin in blue frame', np.round(R[:3, 3], 4), 'beige z-axis in blue frame', np.round(R[:3, 2], 3))
for n in names:
    m = trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{n}.glb', force='mesh', process=False)
    # radial profile along z
    V = np.asarray(m.vertices); z = V[:, 2]; r = np.linalg.norm(V[:, :2] - V[:, :2].mean(0), axis=1)
    for lo in np.arange(-0.08, 0.09, 0.02):
        k = (z >= lo) & (z < lo + 0.02)
        print(n, f'z {lo:+.2f}', 'n', k.sum(), 'r min/max', np.round([r[k].min() if k.any() else np.nan, r[k].max() if k.any() else np.nan], 4))
