"""ORACLE SCORING (public episodes only), after inference: T1 reference part (tracker-fix PLAN §3 T1).
Reads public mocap and the scan registration X*_geom; nothing here feeds inference. For each input arm (refineP = the
25 Oct tracks, Po = the Phase-1 P_o tracks) and episode:
  - the frozen set of refine S6 (pose_opt.json of the S6,S2 run, written before this script ran) vs the mocap-static
    set (objects whose mocap anchor travels < 1 cm over the episode, the ep11 DIAG definition);
  - registered ADD-AUC vs mocap through the kit's chain (tools/xstar_fit.py score_track): lib = library_v3 at the kit's
    own registration X_kit (leaderboard convention), * = X*_geom; for the input track, refine S2 and refine S6,S2;
  - Δ = (S6,S2) - S2 in lib and *.
Pre-registered rule (PLAN §3 T1, frozen before the run): pass when the frozen set equals the mocap-static set on 20/20
episodes and no episode has Δ < -0.002 in lib or *.
Usage: python -I t1_score.py OUT_JSON
"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

KIT = f'{S}/map/scoring/kit/v2d_submission_kit'
T3D = f'{S}/map/scoring/t3'
LIB = f'{REPO}/meshes/library_v3'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
W = f'{S}/leak/t1'
ARMS = {'refineP': f'{S}/refine/in', 'Po': f'{W}/in_Po'}
STATIC_CM = 1.0     # mocap-static: anchor travel < 1 cm (ep11 DIAG, static_hold_test.py)
TOL = -0.002        # no episode below this Δ (lib or *)


def episode(ep):
    XF.kit(KIT)
    t0 = time.time()
    names, gt = XF.mocap(T3D, ep, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    REG = {'lib': [XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)],
           'star': [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]}
    motion = {}
    for s, n in enumerate(names):
        M = gt[n]
        a = M[:, :3, 3] + np.einsum('nij,j->ni', M[:, :3, :3], H[s]['anchor'])
        motion[n] = round(float(np.linalg.norm(a - a[0], axis=1).max() * 100), 3)
    static = [n for n in names if motion[n] < STATIC_CM]
    out = dict(names=names, mocap_anchor_travel_cm=motion, mocap_static=static, arms={})
    for arm, root in ARMS.items():
        r = {}
        for v in ('input', 'S2', 'S6S2'):
            f = f'{root}/ep{ep}/poses_world_vo.npz' if v == 'input' else f'{W}/runs/{arm}/{v}/ep{ep}/poses_world_vo.npz'
            V = np.load(f)
            N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            g = {n: gt[n][:N] for n in names}
            r[v] = {c: XF.score_track(names, T, g, H, REG[c]) for c in ('lib', 'star')}
        js = json.load(open(f'{W}/runs/{arm}/S6S2/ep{ep}/pose_opt.json'))
        s6 = js['steps']['S6']
        frozen = s6['frozen']
        r['frozen'] = frozen
        r['s6_objects'] = {n: {k: s6['objects'][n][k] for k in ('hmax_cm', 'vmax_cm', 'v_peak_cm', 'v_peak_frame', 'v_end_cm',
                                                               'rmax_deg', 'axisymmetric', 'frozen')} for n in names}
        r['s6_plane_source'] = s6['plane']['source']
        r['refine_sha256'] = js['code']['refine_sha256']
        r['match'] = sorted(frozen) == sorted(static)
        r['delta'] = {c: round(r['S6S2'][c]['AUC'] - r['S2'][c]['AUC'], 4) for c in ('lib', 'star')}
        r['delta_per_obj'] = {c: {n: round(r['S6S2'][c]['per_obj_AUC'][n] - r['S2'][c]['per_obj_AUC'][n], 4) for n in names}
                              for c in ('lib', 'star')}
        out['arms'][arm] = r
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: static {static} | ' + ' | '.join(
        f'{arm} frozen {r["frozen"]} {"OK" if r["match"] else "MISMATCH"} S2 lib {r["S2"]["lib"]["AUC"]:.4f} * '
        f'{r["S2"]["star"]["AUC"]:.4f} Δ lib {r["delta"]["lib"]:+.4f} * {r["delta"]["star"]:+.4f}'
        for arm, r in out['arms'].items()) + f' ({out["seconds"]} s)', flush=True)
    return ep, out


def main():
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit('public episodes only')
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for ep, r in ex.map(episode, XF.PUBLIC):
            res[str(ep)] = r
    verdict = {}
    for arm in ARMS:
        eps = [res[str(e)]['arms'][arm] for e in XF.PUBLIC]
        match = sum(e['match'] for e in eps)
        dmin = {c: min(e['delta'][c] for e in eps) for c in ('lib', 'star')}
        verdict[arm] = dict(frozen_equals_static=f'{match}/20', min_delta=dmin,
                            mean_delta={c: round(float(np.mean([e['delta'][c] for e in eps])), 5) for c in ('lib', 'star')},
                            better_worse={c: [sum(e['delta'][c] > 0 for e in eps), sum(e['delta'][c] < 0 for e in eps)]
                                          for c in ('lib', 'star')},
                            mean_S2={c: round(float(np.mean([e['S2'][c]['AUC'] for e in eps])), 4) for c in ('lib', 'star')},
                            mean_S6S2={c: round(float(np.mean([e['S6S2'][c]['AUC'] for e in eps])), 4) for c in ('lib', 'star')},
                            mean_input={c: round(float(np.mean([e['input'][c]['AUC'] for e in eps])), 4) for c in ('lib', 'star')},
                            passed=bool(match == 20 and min(dmin.values()) >= TOL))
        print(arm, json.dumps(verdict[arm]))
    json.dump(dict(note='ORACLE SCORING (public mocap, X*_geom) of the T1 reference part; inference ran before, in '
                        't1_run.sh. Rule: tracker-fix/PLAN.md §3 T1.', rule=dict(static_cm=STATIC_CM, min_delta=TOL),
                   verdict=verdict, episodes=res), open(sys.argv[1], 'w'), indent=1)
    print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
