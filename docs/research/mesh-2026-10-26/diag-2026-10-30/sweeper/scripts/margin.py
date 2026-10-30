# [D] per-seed basin margin: best symmetric-mean-distance among starts that land unflipped vs flipped (C2 about z)
import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import mesh_metric as MM
A = MM.auc
def basins(cand, refm, anchor, seed):
    cv, cf = cand; rv, rf = refm
    cc, cr = A._surface_moments(cv, cf); rc, rr = A._surface_moments(rv, rf)
    cp = (A._sample_mesh_surface(cv, cf, 3000, seed) - cc) * (rr / cr)
    rp = A._sample_mesh_surface(rv, rf, 3000, seed) - rc
    best = {'ok': (math.inf, None), 'flip': (math.inf, None), 'other': (math.inf, None)}
    for st in A._initial_rotations(rp, cp, A._ALIGNMENT_STARTS):
        R, t, d = MM.icp_from(rp, cp, st)
        ang = MM.angle_deg(R)
        k = 'ok' if ang < 30 else ('flip' if ang > 150 else 'other')
        if d < best[k][0]: best[k] = (d, ang)
    return best
if __name__ == '__main__':
    label, path = sys.argv[1], sys.argv[2]
    tf = np.load(sys.argv[3])['T'] if len(sys.argv) > 3 else None
    v, f, _ = MM.load_candidate(path)
    if tf is not None: v = v @ tf[:3,:3].T + tf[:3,3]
    ref = MM.reference('mini_sweeper')
    rows=[]
    for s in [19000057, 30000090, 11, 22, 33, 44]:
        b = basins((v, f), (ref['v'], ref['f']), ref['anchor'], s)
        rows.append(dict(seed=s, ok_mm=round(b['ok'][0]*1e3,3), flip_mm=round(b['flip'][0]*1e3,3), margin_mm=round((b['flip'][0]-b['ok'][0])*1e3,3), other_mm=round(b['other'][0]*1e3,3)))
        print(label, rows[-1])
    json.dump(dict(label=label, rows=rows), open('margins.jsonl','a')); open('margins.jsonl','a').write('\n')
