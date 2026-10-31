"""ORACLE SCORING (public episodes only), after inference: mask10 (README §0). Reads public mocap and the scan
registration X*_geom; nothing here feeds inference. For each arm (Po, refineP), episode and variant (input, S2, V1, V1h,
V2, V1d [ep11 only], V3, V3p): registered ADD-AUC vs mocap through the kit's chain (tools/xstar_fit.py score_track):
lib = library_v3 at the kit's registration X_kit (leaderboard convention), * = X*_geom. Δ = variant - S2.
Pre-registered rule (README §0): ep11 Δlib >= +0.05, and |Δlib| <= 0.002 and |Δ*| <= 0.002 on each other episode;
a variant passes when it passes on both arms.
ep11 mechanism readings (* convention, after the kit's frame-0 scene alignment): per-object ADD and blue-cup height
error by the DIAG's phases, beige-minus-blue height at f130 vs mocap.
Usage: python -I m10_score.py OUT_JSON
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
W = f'{S}/mask10/runs'
ARMS = {'Po': f'{S}/leak/t1/in_Po', 'refineP': f'{S}/refine/in'}
VARS = ['input', 'S2', 'V1', 'V1h', 'V2', 'V1d', 'V3', 'V3p']
TOL_OTHER, BAR11 = 0.002, 0.05
PHASES = dict(A=(0, 20), B=(20, 40), C=(40, 60), D=(60, 72), E=(72, 102), F=(102, 137))   # ep11 DIAG §1
THR = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8


def auc_of(e):
    return float(np.mean((e[:, None] < THR[None]).astype(float) @ TW)) if len(e) else float('nan')


def path(arm, v, ep):
    if v == 'input':
        return f'{ARMS[arm]}/ep{ep}/poses_world_vo.npz'
    return f'{W}/{arm}/{v}/ep{ep}/poses_world_vo.npz'


def mech11(names, Tlib, gt, H):
    """* convention per-frame: ADD per object, blue dz (mocap +z), beige - blue height (aligned) vs mocap."""
    T3 = XF.K['T3']
    tr = {n: Tlib[n] @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    N = len(tr[names[0]]); B = len(names)
    ach = np.stack([XF.to7(tr[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ca, Rb = XF.reg_of_X(np.eye(4), H[s]['anchor'])
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], ca, Rb)
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    al = T3._align_registered_scene(ach, ref, [h['axis'] for h in H])
    out = {}
    Z = np.array([0, 0, 1.0])
    add = {}
    for s, n in enumerate(names):
        add[n] = T3._symmetry_point_errors(al[:, :, s], ref[:, :, s], H[s]['points'], H[s]['axis'], H[s]['order'])[:, 0]
    bl, be = names.index('blue_cup'), names.index('beige_cup')
    dz = (al[:, 0, bl, :3] - ref[:, 0, bl, :3]) @ Z
    rel_tr = (al[:, 0, be, :3] - al[:, 0, bl, :3]) @ Z
    rel_gt = (ref[:, 0, be, :3] - ref[:, 0, bl, :3]) @ Z
    for ph, (a, b) in PHASES.items():
        out[ph] = dict(blue_dz_med_cm=round(float(np.median(dz[a:b]) * 100), 2), blue_dz_max_cm=round(float(np.max(dz[a:b]) * 100), 2),
                       blue_auc=round(auc_of(add['blue_cup'][a:b]), 4), beige_auc=round(auc_of(add['beige_cup'][a:b]), 4),
                       blue_add_med_cm=round(float(np.median(add['blue_cup'][a:b]) * 100), 2),
                       beige_add_med_cm=round(float(np.median(add['beige_cup'][a:b]) * 100), 2))
    out['beige_minus_blue_f130_cm'] = dict(track=round(float(rel_tr[130] * 100), 2), mocap=round(float(rel_gt[130] * 100), 2))
    out['beige_minus_blue_F_med_cm'] = dict(track=round(float(np.median(rel_tr[102:137]) * 100), 2),
                                            mocap=round(float(np.median(rel_gt[102:137]) * 100), 2))
    return out


def episode(ep):
    XF.kit(KIT)
    t0 = time.time()
    names, gt = XF.mocap(T3D, ep, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    REG = {'lib': [XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)],
           'star': [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]}
    out = dict(names=names, arms={})
    for arm in ARMS:
        r = {}
        s2md5 = XF.md5(path(arm, 'S2', ep))
        for v in VARS:
            f = path(arm, v, ep)
            if not os.path.exists(f):
                continue
            if v not in ('input', 'S2') and XF.md5(f) == s2md5 and 'S2' in r:   # byte-identical file: same score
                r[v] = dict(r['S2'], identical_to_S2=True)
                continue
            V = np.load(f)
            N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            g = {n: gt[n][:N] for n in names}
            r[v] = {c: XF.score_track(names, T, g, H, REG[c]) for c in ('lib', 'star')}
            if ep == 11:
                r[v]['mech'] = mech11(names, T, g, H)
        r['delta'] = {v: {c: round(r[v][c]['AUC'] - r['S2'][c]['AUC'], 4) for c in ('lib', 'star')} for v in VARS if v in r and v != 'S2'}
        r['delta_per_obj'] = {v: {c: {n: round(r[v][c]['per_obj_AUC'][n] - r['S2'][c]['per_obj_AUC'][n], 4) for n in names}
                                  for c in ('lib', 'star')} for v in VARS if v in r and v != 'S2'}
        out['arms'][arm] = r
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: ' + ' | '.join(f'{arm} S2 lib {r["S2"]["lib"]["AUC"]:.4f} ' + ' '.join(
        f'{v} {r["delta"][v]["lib"]:+.4f}' for v in r['delta'] if v != 'input') for arm, r in out['arms'].items())
        + f' ({out["seconds"]} s)', flush=True)
    return ep, out


def main():
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit('public episodes only')
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for ep, r in ex.map(episode, XF.PUBLIC):
            res[str(ep)] = r
    verdict = {}
    for v in VARS[2:]:
        verdict[v] = {}
        for arm in ARMS:
            e11 = res['11']['arms'][arm]['delta'].get(v)
            others = {e: res[str(e)]['arms'][arm]['delta'].get(v, res[str(e)]['arms'][arm]['delta']['V1'])
                      for e in XF.PUBLIC if e != 11}   # V1d exists on ep11 only; elsewhere it is V1 (no window)
            worst = max(max(abs(d['lib']), abs(d['star'])) for d in others.values())
            verdict[v][arm] = dict(ep11_dlib=e11['lib'], ep11_dstar=e11['star'], others_max_abs_delta=round(worst, 4),
                                   mean_dlib_20=round(float(np.mean([e11['lib']] + [d['lib'] for d in others.values()])), 5),
                                   passed=bool(e11['lib'] >= BAR11 and worst <= TOL_OTHER))
        verdict[v]['passed_both_arms'] = all(verdict[v][arm]['passed'] for arm in ARMS)
        print(v, json.dumps(verdict[v]))
    json.dump(dict(note='ORACLE SCORING (public mocap, X*_geom) of mask10; inference ran before, in m10_run.sh. Rule: README §0.',
                   rule=dict(ep11_dlib_min=BAR11, others_max_abs=TOL_OTHER), verdict=verdict, episodes=res),
              open(sys.argv[1], 'w'), indent=1)
    print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
