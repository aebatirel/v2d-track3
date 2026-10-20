# Exact FlashCHORD CoACD call inside a Linux container (cross-platform determinism check). usage: in.npz out.npz
import sys, time, numpy as np
sys.path.insert(0, sys.argv[3]) if len(sys.argv) > 3 else None
import coacd
d = np.load(sys.argv[1]); t = time.time()
parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'], dtype=np.float64), np.ascontiguousarray(d['f'], dtype=np.int64)),
                        threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
np.savez(sys.argv[2], n=len(parts), **{f'v{i}': np.asarray(p[0]) for i, p in enumerate(parts)}, **{f'f{i}': np.asarray(p[1]) for i, p in enumerate(parts)})
print('RESULT', sys.argv[1], 'hulls', len(parts), 'sec %.0f' % (time.time() - t), flush=True)
