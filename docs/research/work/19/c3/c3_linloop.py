# Stage C3: exact FlashCHORD CoACD call on every c3/pt/p*.npz inside one Linux container. usage: indir outdir
import sys, os, glob, time, numpy as np
import coacd
coacd.set_log_level('info')
ind, outd = sys.argv[1], sys.argv[2]; os.makedirs(outd, exist_ok=True)
for fn in sorted(glob.glob(ind + '/p*.npz')):
    d = np.load(fn); t = time.time()
    parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'], dtype=np.float64), np.ascontiguousarray(d['f'], dtype=np.int64)),
                            threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    np.savez(outd + '/' + os.path.basename(fn), n=len(parts), **{f'v{i}': np.asarray(p[0]) for i, p in enumerate(parts)}, **{f'f{i}': np.asarray(p[1]) for i, p in enumerate(parts)})
    print('RESULT', os.path.basename(fn), 'hulls', len(parts), 'sec %.1f' % (time.time() - t), flush=True)
