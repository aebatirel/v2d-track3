"""ORACLE SCORING (public episodes only), after inference: offset experiment (README §0).
Reads public mocap, the scan registration X*_geom and the mocap-fitted trk offsets; nothing here feeds inference.
Per arm (refineP, Po), episode and variant (S2 baseline, V1 mf/whole, V2 f0/whole, V3 f0/prefix):
  - registered ADD-AUC vs mocap through the kit's chain (tools/xstar_fit.py score_track): lib (library_v3 at X_kit,
    decisive) and * (X*_geom); dR = R(variant) - R(S2);
  - the S2 baseline checked byte-identical against T1's S2 outputs;
  - geometric share per corrected object: C_or = inv(X_trk) X*_geom (oracle constant body correction of the arm's input
    track: phase1 xstar_trk_Po.json / tierA xstar_trk.json) vs our C (pose_opt.json S11 C_body), as mean displacement of
    2000 surface samples of our mesh: d0 = |C_or - I|, d1 = |C_or - C|, recovered = 1 - d1/d0.
Usage: python -I off_score.py OUT_JSON   (SPLIT=public; 4 processes)
"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import trimesh

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

KIT = f'{S}/map/scoring/kit/v2d_submission_kit'
T3D = f'{S}/map/scoring/t3'
LIB = f'{REPO}/meshes/library_v3'
LD = f'{REPO}/docs/research/work/leak-decomp-20261030'
XG = json.load(open(f'{LD}/tierA/xstar_geom.json'))['objects']
W = f'{S}/offset/runs'
T1 = f'{S}/leak/t1/runs'
ARMS = {'refineP': f'{LD}/tierA/xstar_trk.json', 'Po': f'{LD}/phase1/scores/xstar_trk_Po.json'}
VARS = ['S2', 'V1', 'V2', 'V3']
TRK = {a: json.load(open(p))['episodes'] for a, p in ARMS.items()}


def samples(n):
    m = trimesh.load(f'{LIB}/{n}.glb', force='mesh')
    return np.asarray(trimesh.sample.sample_surface(m, 2000, seed=5)[0], float)


def disp(A, B, P):
    return float(np.linalg.norm((P @ A[:3, :3].T + A[:3, 3]) - (P @ B[:3, :3].T + B[:3, 3]), axis=1).mean() * 100)


def episode(ep):
    XF.kit(KIT)
    t0 = time.time()
    names, gt = XF.mocap(T3D, ep, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    REG = {'lib': [XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)],
           'star': [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]}
    Ps = {n: samples(n) for n in names}
    out = dict(names=names, arms={})
    for arm in ARMS:
        r = {}
        for v in VARS:
            V = np.load(f'{W}/{arm}/{v}/ep{ep}/poses_world_vo.npz')
            N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            g = {n: gt[n][:N] for n in names}
            r[v] = {c: XF.score_track(names, T, g, H, REG[c]) for c in ('lib', 'star')}
            if v == 'S2':
                V1 = np.load(f'{T1}/{arm}/S2/ep{ep}/poses_world_vo.npz')
                r['S2_identical_to_T1'] = all(V[n].tobytes() == V1[n].tobytes() for n in names)
            else:
                js = json.load(open(f'{W}/{arm}/{v}/ep{ep}/pose_opt.json'))['steps']['S11']
                r[v]['s11'] = {}
                tk = TRK[arm][str(ep)]['objects']
                for n in names:
                    o = js['objects'][n]
                    rec = dict(applied=bool(o['applied']), reason=o.get('reason'), correction=o.get('correction'),
                               consensus=o.get('consensus'), frames_accepted=o.get('frames_accepted'),
                               frames_tried=o.get('frames_tried'))
                    Cor = np.linalg.inv(np.asarray(tk[n]['X_scan_T_lib'])) @ np.asarray(XG[n]['X_scan_T_lib'])
                    C = np.asarray(o['C_body']) if o['applied'] else np.eye(4)
                    d0 = disp(Cor, np.eye(4), Ps[n]); d1 = disp(Cor, C, Ps[n])
                    rec.update(d0_cm=round(d0, 3), d1_cm=round(d1, 3), dC_cm=round(disp(C, np.eye(4), Ps[n]), 3),
                               recovered=round(1 - d1 / d0, 3) if d0 > 1e-6 else None)
                    r[v]['s11'][n] = rec
        for v in VARS[1:]:
            r[v]['d'] = {c: round(r[v][c]['AUC'] - r['S2'][c]['AUC'], 4) for c in ('lib', 'star')}
        sc = TRK[arm][str(ep)]['scores']
        r['input_trk'] = {k: sc[k]['AUC'] for k in ('lib', 'star', 'trk')}
        out['arms'][arm] = r
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: ' + ' | '.join(
        f'{arm} S2 lib {r["S2"]["lib"]["AUC"]:.4f} ' + ' '.join(f'{v} {r[v]["d"]["lib"]:+.4f}/{r[v]["d"]["star"]:+.4f}'
                                                             for v in VARS[1:]) + ('' if r['S2_identical_to_T1'] else ' S2!=T1')
        for arm, r in out['arms'].items()) + f' ({out["seconds"]} s)', flush=True)
    return ep, out


def main():
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit('public episodes only')
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for ep, o in ex.map(episode, XF.PUBLIC):
            res[str(ep)] = o
    json.dump(res, open(sys.argv[1], 'w'), indent=1)
    print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
