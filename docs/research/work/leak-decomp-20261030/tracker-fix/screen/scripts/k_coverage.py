"""Which VO keyframe switches of each eval does rule K (S7) actually observe? A switch counts as observed when at least
one roster object is an anchor (eval_screen.ruleK's window rule: no measured hand joint within 3 cm of our mesh, frame 0
or after >= 5 rest frames at < 0.15 cm/frame) on a frame within +-2 of it. Rule K can only read a camera step at an
observed switch; at the others its magnitude is 'not measurable', not zero. GT-free; same inputs as eval_screen.py.
Usage: python -I k_coverage.py OUT_JSON"""
import sys, json, numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
out = {}
for ep in E.EV:
    I = E.inputs(ep, False); det = np.load(I['det'], allow_pickle=True); names = [str(x) for x in det['names']]
    T = E.world(np.load(I['poses'])); N = len(T[names[0]]); kfs = json.load(open(I['vo']))['keyframes']
    hz = np.load(I['hands'], allow_pickle=True)
    J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(np.float64)
    Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
    cand = {}
    for n in names:
        Pp = E.lib_pts(ep, n, False); X = np.einsum('nij,vj->nvi', T[n][:, :3, :3], Pp) + T[n][:, None, :3, 3]
        d = np.array([cKDTree(X[i]).query(J[i][Jv[i]], k=1)[0].min() if Jv[i].any() else np.inf for i in range(N)])
        cen = X.mean(1); spd = np.r_[0, np.linalg.norm(np.diff(cen, axis=0), axis=1)]
        ok = d >= E.D_H; first = int(np.argmax(~ok)) if (~ok).any() else N; st = np.arange(N) < first; run = 0; inside = False
        for i in range(N):
            if not ok[i]:
                inside = False; run = 0; continue
            if inside:
                st[i] = True; continue
            run = run + 1 if spd[i] < E.V_REST else 0
            if run >= E.REST_MIN:
                st[i - E.REST_MIN + 1:i + 1] = True; inside = True
        cand[n] = st
    anyc = np.any([cand[n] for n in names], axis=0)
    sw = [k for k in kfs if k > 0]
    obs = [k for k in sw if anyc[max(0, k - E.KW):min(N, k + E.KW + 1)].any()]
    b = E.burst(kfs)
    bw = [k for k in sw if b[1] is not None and b[1] <= k < b[1] + 25]
    out[str(ep)] = dict(switches=sw, observed=obs, burst=b[0], burst_switches=bw, burst_observed=[k for k in bw if k in obs])
    print(f'ep{ep}: switches {len(sw)}, observed by an anchor {len(obs)} {obs} | burst {b[0]} {bw}, observed {out[str(ep)]["burst_observed"]}')
json.dump(out, open(sys.argv[1], 'w'), indent=1)
