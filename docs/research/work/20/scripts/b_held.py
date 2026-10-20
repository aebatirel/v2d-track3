# Stage B4: spoon markers in HELD frames (whole-image cam a detection, b/c disc-NCC depth sweep along the cam-a ray without a
# table prior, triple picked against the rest triangle 53.0/153.2/194.2 mm +-5). Records per frame: M1..M3 (rect frame),
# image positions, the triangle normal vs the viewing ray (frontalness), and marker image speed (from a[k] vs a[k+2]).
# Usage: b_held.py <ep> <k0> <k1> <step>  -> out/b/held_e<ep>.jsonl (appends; resumable)
import sys, os, json, numpy as np, cv2
ep, k0, k1, st = [int(x) for x in sys.argv[1:5]]
sys.argv = ['x', str(ep), '0']
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b_meas.py').read().split("out = []\nfor k in ks:")[0]
src = src.replace("fa = read_frames(SPL, ep, 'a', [k + 1 for k in ks]); fb = read_frames(SPL, ep, 'b', ks); fc = read_frames(SPL, ep, 'c', ks)", "")
exec(src)
OUTF = f'{OUT}/held_e{ep}.jsonl'
done = set()
if os.path.exists(OUTF): done = {json.loads(l)['k'] for l in open(OUTF)}
ks = [k for k in range(k0, k1, st) if k not in done]
EXP3 = np.array([53.0, 153.2, 194.2])


def sweep_free(cd, rcf, rbf, h=9, z0=0.22, z1=0.90, step=0.0004):
    d = a_ray_r(np.array([cd['uv']]))[0]; ts = np.arange(z0, z1, step) / d[2]
    X = A_centre_r[None] + ts[:, None] * d[None]; xl, yl = proj_rect(X, 0.0, 'c'); xr, yr = proj_rect(X, 0.0, 'b')
    ok = (xl > 20) & (xl < RSZ[0] - 20) & (xr > 20) & (yl > 20) & (yl < RSZ[1] - 20)
    yy_, xx_ = np.mgrid[-h:h + 1, -h:h + 1]; sc = np.full(len(ts), -1.0)
    for i in np.nonzero(ok)[0]:
        p_, q_ = patch(rcf, xl[i], yl[i], h), patch(rbf, xr[i], yr[i], h)
        w = np.exp(-0.5 * (np.maximum(np.hypot(xx_, yy_) - FR * RDISC / X[i, 2], 0) / 1.5) ** 2)
        p_ = p_ - (w * p_).sum() / w.sum(); q_ = q_ - (w * q_).sum() / w.sum()
        sc[i] = (w * p_ * q_).sum() / np.sqrt((w * p_ ** 2).sum() * (w * q_ ** 2).sum() + 1e-9)
    # keep the top 3 separated peaks (ambiguity handled by the triple test)
    peaks = []
    for i in np.argsort(-sc):
        if sc[i] < 0.6 or len(peaks) >= 3: break
        if all(abs(ts[i] - ts[j]) > 0.01 / d[2] for j, _ in peaks): peaks.append((i, sc[i]))
    return [(A_centre_r + ts[i] * d, float(s)) for i, s in peaks]


for k in ks:
    fr = {c: read_frames('evaluation', ep, c, [k])[k] for c in 'bc'}
    fa2 = read_frames('evaluation', ep, 'a', [k + 1, k + 2]); A = fa2[k + 1]
    rc, rb, fdy, dinfo = rect_pair(cv2.cvtColor(fr['c'], cv2.COLOR_BGR2GRAY), cv2.cvtColor(fr['b'], cv2.COLOR_BGR2GRAY))
    rcf, rbf = rc.astype(np.float32), rb.astype(np.float32)
    _, _, cands, _ = detect_a(A, whole=True)
    hyp = []
    for ci, cd in enumerate(cands):
        for X, s in sweep_free(cd, rcf, rbf): hyp.append((ci, X, s))
    best = None
    for a in range(len(hyp)):
        for b in range(len(hyp)):
            for c in range(len(hyp)):
                ia, ib, ic = hyp[a][0], hyp[b][0], hyp[c][0]
                if len({ia, ib, ic}) < 3: continue
                P = [hyp[a][1], hyp[b][1], hyp[c][1]]
                dd = np.array([np.linalg.norm(P[0] - P[1]), np.linalg.norm(P[1] - P[2]), np.linalg.norm(P[0] - P[2])]) * 1e3
                err = np.abs(dd - EXP3).max()
                if err > 6: continue
                cost = np.abs(dd - EXP3).sum() - 10 * (hyp[a][2] + hyp[b][2] + hyp[c][2])
                if best is None or cost < best[0]: best = (cost, a, b, c, dd.tolist())
    rec = dict(k=k, n_cands=len(cands), dy_rms=dinfo['rms'])
    if best:   # wood/skin check along mid(M1,M2)->M3 in cam a (rejects background marker look-alikes)
        hsv = cv2.cvtColor(A, cv2.COLOR_BGR2HSV).astype(int)
        u3 = [np.array(cands[hyp[x][0]]['uv']) for x in best[1:4]]; m12 = 0.5 * (u3[0] + u3[1])
        pts = [m12 + t * (u3[2] - m12) for t in np.linspace(0.08, 0.92, 40)] + [m12]
        wood = [(lambda q: (35 < q[1] < 140) and q[2] > 150 and q[0] < 30)(hsv[int(p_[1]), int(p_[0])]) for p_ in pts
                if 0 <= p_[0] < A.shape[1] and 0 <= p_[1] < A.shape[0]]
        rec['wood_frac'] = float(np.mean(wood)) if wood else 0.0
        if rec['wood_frac'] < 0.4: best = None
    if best:
        _, a, b, c, dd = best; M = np.array([hyp[a][1], hyp[b][1], hyp[c][1]])
        uv = [cands[hyp[x][0]]['uv'] for x in (a, b, c)]; rr = [cands[hyp[x][0]]['r'] for x in (a, b, c)]
        nrm = np.cross(M[1] - M[0], M[2] - M[0]); nrm /= np.linalg.norm(nrm); view = M.mean(0) - A_centre_r; view /= np.linalg.norm(view)
        ax = M[2] - 0.5 * (M[0] + M[1]); ax /= np.linalg.norm(ax)
        # image speed: same detector on a[k+2], nearest candidates
        _, _, c2, _ = detect_a(fa2[k + 2], whole=True)
        sp = [min([np.hypot(q['uv'][0] - u[0], q['uv'][1] - u[1]) for q in c2] or [99]) for u in uv]
        rec.update(M_r=M.tolist(), uv=uv, r=rr, d=dd, ncc=[hyp[x][2] for x in (a, b, c)], tri_n_dot_view=float(abs(nrm @ view)),
                   axis_dot_view=float(abs(ax @ view)), speed_px=sp)
    with open(OUTF, 'a') as f: f.write(json.dumps(rec) + '\n')
    print(k, 'cands', len(cands), ('d ' + ' '.join(f'{x:.1f}' for x in rec['d']) + f" | front {rec['tri_n_dot_view']:.2f} ax.view {rec['axis_dot_view']:.2f} speed " + ' '.join(f'{x:.0f}' for x in rec['speed_px'])) if 'd' in rec else 'no triple', flush=True)
