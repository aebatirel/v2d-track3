"""ORACLE reading (public), after inference: does S11's GT-free correction C move each object toward the oracle constant
body offset C_or = inv(X_trk) X*_geom of its input track (phase1 xstar_trk_Po.json / tierA xstar_trk.json, mocap-fitted)?
Distances are mean displacements (cm) of points of our mesh: 2000 surface samples, or for the cups (spin free in the
scorer and in the trk fit) 3 points on our mesh's symmetry axis (centroid +- RMS radius), as the trk fit does.
d0 = |C_or - I|, dC = |C - I|, d1 = |C_or - C|, recovered = 1 - d1/d0. [H-OFF] falsified for a variant if the median
recovered over the objects with d0 >= 0.5 cm that it corrected is <= 0 (README §0).
Usage: python -I geo_share.py RUNS_DIR OUT_JSON"""
import json, sys
import numpy as np, trimesh
REPO = '/home/user/v2d-track3'; LD = f'{REPO}/docs/research/work/leak-decomp-20261030'
W = sys.argv[1]
XG = json.load(open(f'{LD}/tierA/xstar_geom.json'))['objects']
TRK = {'refineP': json.load(open(f'{LD}/tierA/xstar_trk.json'))['episodes'],
       'Po': json.load(open(f'{LD}/phase1/scores/xstar_trk_Po.json'))['episodes']}
CUPS = {'blue_cup', 'beige_cup'}
PTS = {}


def pts(n):
    if n not in PTS:
        m = trimesh.load(f'{REPO}/meshes/library_v3/{n}.glb', force='mesh')
        P = np.asarray(trimesh.sample.sample_surface(m, 20000, seed=5)[0], float)
        if n in CUPS:
            c = P.mean(0); w, U = np.linalg.eigh(np.cov((P - c).T))
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            r = float(np.sqrt(((P - c) ** 2).sum(1).mean()))
            PTS[n] = c + np.outer([-1.0, 0.0, 1.0], U[:, k]) * r
        else:
            PTS[n] = P[::10]
    return PTS[n]


def disp(A, B, P):
    return float(np.linalg.norm((P @ A[:3, :3].T + A[:3, 3]) - (P @ B[:3, :3].T + B[:3, 3]), axis=1).mean() * 100)


out = {}; summ = {}
for arm in ('Po', 'refineP'):
    for v in ('V1', 'V2', 'V3'):
        rows = []
        for ep, e in sorted(TRK[arm].items(), key=lambda x: int(x[0])):
            s = json.load(open(f'{W}/{arm}/{v}/ep{ep}/pose_opt.json'))['steps']['S11']['objects']
            for n, o in e['objects'].items():
                Cor = np.linalg.inv(np.asarray(o['X_scan_T_lib'])) @ np.asarray(XG[n]['X_scan_T_lib'])
                C = np.asarray(s[n]['C_body']) if s[n]['applied'] else np.eye(4)
                d0, d1, dc = disp(Cor, np.eye(4), pts(n)), disp(Cor, C, pts(n)), disp(C, np.eye(4), pts(n))
                rows.append(dict(ep=int(ep), obj=n, applied=bool(s[n]['applied']), d0=round(d0, 3), dC=round(dc, 3),
                                 d1=round(d1, 3), recovered=round(1 - d1 / d0, 3) if d0 > 1e-6 else None))
        g = np.array([r['recovered'] for r in rows if r['applied'] and r['d0'] >= 0.5])
        summ[f'{arm}_{v}'] = dict(n=int(len(g)), median_recovered=round(float(np.median(g)), 3) if len(g) else None,
                                  share_closer=round(float((g > 0).mean()), 3) if len(g) else None,
                                  mean_d0=round(float(np.mean([r['d0'] for r in rows if r['applied'] and r['d0'] >= 0.5])), 3) if len(g) else None,
                                  mean_d1=round(float(np.mean([r['d1'] for r in rows if r['applied'] and r['d0'] >= 0.5])), 3) if len(g) else None,
                                  falsified=bool(len(g) and np.median(g) <= 0))
        out[f'{arm}_{v}'] = rows
        print(arm, v, summ[f'{arm}_{v}'])
json.dump(dict(summary=summ, rows=out), open(sys.argv[2], 'w'), indent=1)
