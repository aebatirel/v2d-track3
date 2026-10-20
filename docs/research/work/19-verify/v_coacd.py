# Verifier: exact FlashCHORD CoACD call (mesh.py defaults) on an npz {v,f}; usage: v_coacd.py in.npz out.npz [libdir]
import sys, time, platform, numpy as np
if len(sys.argv) > 3: sys.path.insert(0, sys.argv[3])
import coacd
d = np.load(sys.argv[1]); t = time.time()
parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'], dtype=np.float64), np.ascontiguousarray(d['f'], dtype=np.int64)),
                        threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
np.savez(sys.argv[2], n=len(parts), **{f'v{i}': np.asarray(p[0]) for i, p in enumerate(parts)}, **{f'f{i}': np.asarray(p[1]) for i, p in enumerate(parts)})
print('RESULT', platform.system(), platform.machine(), getattr(coacd, '__file__', ''), sys.argv[1], 'hulls', len(parts), 'sec %.0f' % (time.time() - t), flush=True)
