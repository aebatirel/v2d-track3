"""ORACLE SCORING (public episodes only), after inference (rts_run.sh post): rts / refine S13 (PREREG.md).
Reads public mocap and the scan registration X*_geom; nothing here feeds inference.
Per input arm (Po = Phase-1 P_o tracks, primary; refineP = 25 Oct tracks, replication) and episode, for the input
track, the control S2 (--steps S2) and the treatment S13 (--steps S2,S13):
  - R = registered ADD-AUC vs mocap through the kit's chain (tools/xstar_fit.py score_track, as heldpose hp_score.py),
    lib = library_v3 at the kit's registration X_kit (leaderboard convention), * = X*_geom;
  - RPE = the kit's rpe_cm on the same converted and scene-aligned arrays (cm; 0 on single-object episodes);
  - per-object AUC; Δ = S13 - S2.
Rule (PREREG §4): PASS iff on Po mean_20 ΔR_lib >= +0.005 and min_ep ΔR_lib >= -0.02; refineP = replication reading;
RPE reported (mean ΔRPE_lib over multi-object episodes, flag ΔRPE_lib > +0.5 cm). INCOMPLETE / INVALID (e) checked here.
Usage: python -I rts_score.py OUT_JSON
"""
import hashlib, json, os, sys, time
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
W = f'{S}/rts/runs'
ARMS = {'Po': f'{S}/leak/t1/in_Po', 'refineP': f'{S}/refine/in'}
PRIMARY = 'Po'
VARIANTS = ('input', 'S2', 'S13')
MEAN_MIN, DROP_MIN, RPE_FLAG = 0.005, -0.02, 0.5
CODE = [f'{REPO}/pipeline/refine.py', f'{REPO}/pipeline/rts.py']


def code_sha():
    return {os.path.basename(p): hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in CODE}


def rpe(names, track, gt, H, REG):
    """The kit's registered RPE (cm) on exactly score_track's converted and aligned arrays."""
    T3 = XF.K['T3']
    N = len(track[names[0]])
    B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    return round(float(T3._registered_pose_metric('rpe_cm', ach, ref, [h['points'] for h in H], axes,
                                                  [h['order'] for h in H])), 4)


def episode(ep):
    XF.kit(KIT)
    t0 = time.time()
    names, gt = XF.mocap(T3D, ep, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    REG = {'lib': [XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)],
           'star': [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]}
    out = dict(names=names, arms={})
    for arm, root in ARMS.items():
        r = {}
        for v in VARIANTS:
            f = f'{root}/ep{ep}/poses_world_vo.npz' if v == 'input' else f'{W}/{arm}/{v}/ep{ep}/poses_world_vo.npz'
            if not os.path.exists(f):
                r[v] = None
                continue
            V = np.load(f)
            N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            g = {n: gt[n][:N] for n in names}
            r[v] = {}
            for c in ('lib', 'star'):
                sc = XF.score_track(names, T, g, H, REG[c])
                sc['RPE'] = rpe(names, T, g, H, REG[c])
                r[v][c] = sc
        if r['S2'] and r['S13']:
            r['delta'] = {c: dict(AUC=round(r['S13'][c]['AUC'] - r['S2'][c]['AUC'], 4),
                                  RPE=round(r['S13'][c]['RPE'] - r['S2'][c]['RPE'], 4),
                                  per_obj_AUC={n: round(r['S13'][c]['per_obj_AUC'][n] - r['S2'][c]['per_obj_AUC'][n], 4)
                                               for n in names}) for c in ('lib', 'star')}
            js = json.load(open(f'{W}/{arm}/S13/ep{ep}/pose_opt.json'))
            r['s13'] = js['steps']['S13']['objects']
            r['s13_T'] = js['T']
        out['arms'][arm] = r
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: ' + ' | '.join(
        f'{arm} S2 lib {r["S2"]["lib"]["AUC"]:.4f} dlib {r["delta"]["lib"]["AUC"]:+.4f} dRPE {r["delta"]["lib"]["RPE"]:+.3f}'
        if 'delta' in r else f'{arm} MISSING' for arm, r in out['arms'].items()) + f' ({out["seconds"]} s)', flush=True)
    return ep, out


def rule(res, arm):
    d = {e: res[str(e)]['arms'][arm].get('delta') for e in XF.PUBLIC}
    if any(x is None or not np.isfinite(x['lib']['AUC']) for x in d.values()):
        return dict(status='INCOMPLETE', missing=[e for e, x in d.items() if x is None])
    dl = {e: x['lib']['AUC'] for e, x in d.items()}
    ds = {e: x['star']['AUC'] for e, x in d.items()}
    multi = [e for e in XF.PUBLIC if len(res[str(e)]['names']) > 1]
    drpe = {e: d[e]['lib']['RPE'] for e in multi}
    mean, mn = float(np.mean(list(dl.values()))), min(dl.values())
    return dict(status='PASS' if (mean >= MEAN_MIN and mn >= DROP_MIN) else 'FAIL',
                mean_dR_lib=round(mean, 5), min_dR_lib=mn, worst_ep=min(dl, key=dl.get),
                better_worse_lib=[sum(x > 0 for x in dl.values()), sum(x < 0 for x in dl.values())],
                mean_dR_star=round(float(np.mean(list(ds.values()))), 5), min_dR_star=min(ds.values()),
                mean_dRPE_lib_multi=round(float(np.mean(list(drpe.values()))), 4), multi_eps=multi,
                rpe_flags=[e for e, x in drpe.items() if x > RPE_FLAG],
                mean_R_lib_S2=round(float(np.mean([res[str(e)]['arms'][arm]['S2']['lib']['AUC'] for e in XF.PUBLIC])), 5),
                mean_R_lib_S13=round(float(np.mean([res[str(e)]['arms'][arm]['S13']['lib']['AUC'] for e in XF.PUBLIC])), 5),
                mean_RPE_lib_S2_multi=round(float(np.mean([res[str(e)]['arms'][arm]['S2']['lib']['RPE'] for e in multi])), 4),
                mean_RPE_lib_S13_multi=round(float(np.mean([res[str(e)]['arms'][arm]['S13']['lib']['RPE'] for e in multi])), 4))


def main():
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit('public episodes only')
    sha0 = code_sha()
    t0 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    print('code sha256 at scoring start', sha0, t0, flush=True)
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for ep, r in ex.map(episode, XF.PUBLIC):
            res[str(ep)] = r
    sha1 = code_sha()
    rp, rr = rule(res, PRIMARY), rule(res, 'refineP')
    if sha0 != sha1:
        verdict = 'INVALID (e): code changed during scoring'
    elif rp['status'] != 'PASS':
        verdict = rp['status']
    else:
        verdict = 'PASS, replicated' if rr['status'] == 'PASS' else (
            'PASS, replication not available' if rr['status'] == 'INCOMPLETE' else 'PASS, not replicated')
    print('Po', json.dumps(rp))
    print('refineP', json.dumps(rr))
    print('VERDICT (bytecheck INVALID (a)/(c) is separate: rts_bytecheck.py):', verdict)
    json.dump(dict(note='ORACLE SCORING (public mocap, X_kit and X*_geom) of rts / refine S13; inference ran before, in '
                        'rts_run.sh post. Rule: PREREG.md §4.', rule=dict(mean_min=MEAN_MIN, drop_min=DROP_MIN,
                        primary=PRIMARY, rpe_flag_cm=RPE_FLAG), code_sha256_start=sha0, code_sha256_end=sha1,
                   started_utc=t0, finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   verdict=verdict, primary=rp, replication=rr, episodes=res), open(sys.argv[1], 'w'), indent=1)
    print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
