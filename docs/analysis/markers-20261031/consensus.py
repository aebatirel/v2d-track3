"""GT-free marker layout of one object from our own video, pooled over its episodes by constellation registration.

Per episode: body-frame clusters of rest detections (our track's body frame; mklayout.discover on that episode only),
kept when the median 3-D radius is marker-like (>= 4.6 mm), the cluster is seen in >= 20 % of the episode's rest frames
and it is >= 25 mm from a stronger kept cluster. These constellations differ between episodes when our tracker's body
frame differs (e.g. a spin error of a near-symmetric object). Pairs of episode constellations are registered by
RANSAC over matching triplets (pairwise distances within 6 mm; inliers within 6 mm). The medoid episode (most
registered partners, then smallest median rotation to them) defines the consensus frame; every registered episode
gets a constant body-frame offset A_e (consensus -> its track's body frame) and its markers are merged (within 8 mm)
into the consensus layout (markers seen in >= 2 episodes; all markers when the object has one episode).
For the spoon the template layout seeds the per-episode clusters (it is our own video measurement, note 20).
Inputs: scan.py detections and our tracks. No ground truth, no scan.
Usage: python consensus.py OBJ SPLIT EPS(comma) OUT_JSON [--seed-template]
"""
import itertools, json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(__file__))
import mlib, mklayout as L, census as CE

R3_MIN, SHARE_MIN, SEP, MAXK = 0.0046, 0.20, 0.025, 8
TOL_REG, TOL_MERGE = 0.006, 0.008


def episode_constellation(d, seed=None):
    C, share, cnt = L.discover([d['B']], [d['rest']], min_share=0.10)
    rows = []
    for c, sh in zip(C, share):
        r3 = []
        for t, (B, X) in enumerate(d['B']):
            if d['rest'][t] and len(B):
                dd = np.linalg.norm(B - c, axis=1); i = int(np.argmin(dd))
                if dd[i] < 0.012:
                    r3.append(d['dets'][t][i]['r3'])
        rows.append((c, sh, float(np.median(r3)) if r3 else 0.0))
    keep = []
    for c, sh, r3 in sorted(rows, key=lambda r: -r[1]):
        if r3 >= R3_MIN and sh >= SHARE_MIN and all(np.linalg.norm(c - q[0]) >= SEP for q in keep) and len(keep) < MAXK:
            keep.append((c, sh, r3))
    info = [dict(c_mm=(c * 1000).round(1).tolist(), share=round(sh, 3), r3_mm=round(r3 * 1000, 2)) for c, sh, r3 in keep]
    return np.array([k[0] for k in keep]).reshape(-1, 3), info


def register(P, Q):
    """rigid (R, t) with R P + t ~ Q for unlabelled point sets; returns (R, t, inliers, rms) or None."""
    if len(P) < 3 or len(Q) < 3:
        return None
    DP = np.linalg.norm(P[:, None] - P[None], axis=2); DQ = np.linalg.norm(Q[:, None] - Q[None], axis=2)
    best = None
    for a in itertools.combinations(range(len(P)), 3):
        for b in itertools.permutations(range(len(Q)), 3):
            if any(abs(DP[a[i], a[j]] - DQ[b[i], b[j]]) > TOL_REG for i in range(3) for j in range(i + 1, 3)):
                continue
            R, t = L.kabsch(P[list(a)], Q[list(b)])
            Pt = P @ R.T + t; D = np.linalg.norm(Pt[:, None] - Q[None], axis=2)
            pairs = []
            for i, j in sorted(((i, j) for i in range(len(P)) for j in range(len(Q)) if D[i, j] < TOL_REG), key=lambda x: D[x]):
                if i not in [p[0] for p in pairs] and j not in [p[1] for p in pairs]:
                    pairs.append((i, j))
            if len(pairs) < 3:
                continue
            R, t = L.kabsch(P[[p[0] for p in pairs]], Q[[p[1] for p in pairs]])
            rms = float(np.sqrt(np.mean(np.sum((P[[p[0] for p in pairs]] @ R.T + t - Q[[p[1] for p in pairs]]) ** 2, 1))))
            if best is None or len(pairs) > best[2] or (len(pairs) == best[2] and rms < best[3]):
                best = (R, t, len(pairs), rms, pairs)
    return best


def main():
    obj, split, eps, outp = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')], sys.argv[4]
    D = []
    for e in eps:
        d = CE.load(obj, split, e); d['rest'] = L.rest_mask(d['Tw']); d['B'] = L.body_points(d['dets'], d['T']); D.append(d)
    cons = {}
    labelled = '--labelled' in sys.argv
    for d in D:
        if labelled:     # constellation from the labelled sets of a seeded census pass (fix files), per marker median
            F = np.load(f'{mlib.S}/mk/scan/fix_{split}{d["e"]}_{obj}.npz'); labs = json.loads(str(F['labs']))
            k = len(F['layout']); acc = [[] for _ in range(k)]
            for t in range(min(len(labs), d['N'])):
                lab = labs[t]
                if len(lab) == k and d['rest'][t]:
                    B, _ = d['B'][t]
                    for j, i in lab.items():
                        acc[int(j)].append(B[i])
            ok = all(len(a) >= 3 for a in acc)
            P = np.array([np.median(a, 0) for a in acc]) if ok else np.zeros((0, 3))
            info = [dict(c_mm=(p * 1000).round(1).tolist(), n=len(a)) for p, a in zip(P, acc)] if ok else [dict(n=[len(a) for a in acc])]
            cons[d['e']] = (P, info)
            print(obj, d['e'], 'labelled markers', len(P), info, flush=True)
            continue
        P, info = episode_constellation(d)
        cons[d['e']] = (P, info)
        print(obj, d['e'], 'markers', len(P), [r['c_mm'] for r in info], flush=True)
    seed = None
    if '--seed-template' in sys.argv:
        seed = np.array(json.load(open('/home/user/v2d-track3/spoon/params.json'))['markers_canonical_m'])
    # pairwise registration
    reg = {}
    for a, b in itertools.permutations([d['e'] for d in D], 2):
        r = register(cons[a][0], cons[b][0])
        if r is not None:
            reg[(a, b)] = r
    E = [d['e'] for d in D]
    def score(m):
        part = [b for b in E if b != m and (m, b) in reg]
        rot = [np.degrees(Rot.from_matrix(reg[(m, b)][0]).magnitude()) for b in part]
        return (len(part), -float(np.median(rot)) if rot else 0.0)
    if seed is not None:
        # spoon: the template layout is the consensus seed; each episode registers to it
        ref_pts = seed; medoid = 'template'
        A = {}
        for e in E:
            r = register(seed, cons[e][0])
            if r is not None:
                A[e] = r
    else:
        medoid = max(E, key=score) if E else None
        ref_pts = cons[medoid][0] if medoid is not None else np.zeros((0, 3))
        A = {medoid: (np.eye(3), np.zeros(3), len(ref_pts), 0.0, [(i, i) for i in range(len(ref_pts))])}
        for e in E:
            if e != medoid and (medoid, e) in reg:
                A[e] = reg[(medoid, e)]
    # merge into the consensus frame: points of episode e mapped back by A_e^-1
    pts = [[p] for p in ref_pts] if seed is None else [[] for _ in ref_pts]
    src = [[medoid] for _ in ref_pts] if seed is None else [[] for _ in ref_pts]
    extra = []
    for e, (R, t, nin, rms, pairs) in A.items():
        if seed is None and e == medoid:
            continue
        back = (cons[e][0] - t) @ R           # consensus-frame coordinates of e's markers
        for i, p in enumerate(back):
            dd = np.linalg.norm(ref_pts - p, axis=1) if len(ref_pts) else np.array([1.0])
            j = int(np.argmin(dd))
            if dd[j] < TOL_MERGE:
                pts[j].append(p); src[j].append(e)
            else:
                extra.append((e, p))
    need = 1 if len(E) == 1 else 2
    if seed is not None:
        need = 1
    keep = [j for j in range(len(ref_pts)) if len(set(src[j])) >= need]
    layout = np.array([np.median(pts[j], 0) if pts[j] else ref_pts[j] for j in keep]).reshape(-1, 3)
    out = dict(obj=obj, split=split, eps=E, medoid=medoid, n_markers=len(layout), layout_body_m=layout.tolist(),
               marker_support={str(j): sorted(set(map(int, src[j]))) for j in keep},
               episodes={str(e): dict(markers=cons[e][1]) for e in E},
               offsets={str(e): dict(R=A[e][0].tolist(), t=A[e][1].tolist(), inliers=int(A[e][2]), rms_mm=round(A[e][3] * 1000, 2),
                                     rot_deg=round(float(np.degrees(Rot.from_matrix(A[e][0]).magnitude())), 2),
                                     t_mm=round(float(np.linalg.norm(A[e][1]) * 1000), 1)) for e in A},
               unregistered=[e for e in E if e not in A])
    print(obj, 'consensus markers', len(layout), 'medoid', medoid, 'offsets',
          {e: (out['offsets'][str(e)]['rot_deg'], out['offsets'][str(e)]['inliers'], out['offsets'][str(e)]['rms_mm']) for e in A},
          'unregistered', out['unregistered'], flush=True)
    json.dump(out, open(outp, 'w'), indent=1)


if __name__ == '__main__':
    main()
