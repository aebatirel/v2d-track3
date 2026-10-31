import sys, glob, time, importlib.util, numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
src = open(sys.argv[1]).read(); exec(src[src.index('def push_dir'):src.index('Z = np.load(out)')])
names, O, P, Q, fps = I.load_ref(sys.argv[2]); Oi = I.inv_pose(O); sim = sys.argv[3]
U = {n: I.Union(sorted(glob.glob(f'{sim}/{n}/piece_*.obj'))) for n in names}; S = {n: U[n].lattice(0.002) for n in names}
for f in map(int, sys.argv[4:]):
    for t, p in ((0, 1), (1, 0)):
        R = Oi[f, t] @ O[f, p]; X = S[names[p]] @ R[:3, :3].T + R[:3, 3]; t0 = time.time()
        s, u = push_dir(U[names[t]], X)
        sb = -u if t == 0 else R[:3, :3].T @ u; up = O[f, 0, :3, :3].T @ np.array([0, 0, 1.0])
        print(f, names[p], 'in', names[t], f'push {s*1e3:.1f} mm, blue-shift up-cos {sb @ up:+.2f}, dir(blue frame) {np.round(sb, 2)}, {time.time()-t0:.1f}s', flush=True)
