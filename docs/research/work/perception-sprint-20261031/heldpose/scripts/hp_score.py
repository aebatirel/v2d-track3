"""ORACLE SCORING (public episodes only), after inference (hp_run.sh): heldpose / refine S10 (README §0).
Reads public mocap and the scan registration X*_geom; nothing here feeds inference.
Per input arm (refineP = 25 Oct tracks, Po = Phase-1 P_o tracks) and episode:
  - registered ADD-AUC vs mocap through the kit's chain (tools/xstar_fit.py score_track), lib = library_v3 at X_kit
    (leaderboard convention) and * = X*_geom, for the input track, S2 (baseline) and S2 + S10 in modes g / r / t;
  - Δ = variant - S2, per episode and per object;
  - diagnostic for [H-HP] (README §0): per-frame symmetry-aware ADD (after the kit's scene alignment, * convention) of
    the tracker (S2 output) and of the prediction P(t) = W(t) G on the S10 hold frames (pose_opt_aux.npz of the S10g
    run: S10_<obj>_side / _P / _vP), with the GT-free visibility v_P of each frame.
Pre-registered rule (README §0): S10g adopted iff on BOTH arms mean Δ lib over episodes {18, 31, 39, 40} >= +0.005 and
no public episode has Δ lib < -0.01.
Usage: python -I hp_score.py OUT_JSON
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
W = f'{S}/heldpose'
ARMS = {'refineP': f'{S}/refine/in', 'Po': f'{S}/leak/t1/in_Po'}
VARIANTS = ('S10g', 'S10r', 'S10t')
PROXY = [18, 31, 39, 40]
MEAN_MIN, DROP_MIN = 0.005, -0.01
CLASS = {'mini_sweeper': 'sweeper', 'mini_dust_pan': 'dust pan', 'blue_cup': 'cups', 'beige_cup': 'cups',
         'white_pot': 'pot/lid', 'white_pot_lid': 'pot/lid', 'water_pitcher': 'pitcher', 'wooden_piece_1': 'boards',
         'wooden_piece_2': 'boards', 'plastic_dish_rack': 'rack'}


def per_frame(names, track, gt, H, REG):
    """Per-frame, per-slot symmetry-aware ADD (m) after the kit's conversion and scene alignment (as score_track)."""
    T3 = XF.K['T3']
    B = len(names)
    N = len(track[names[0]])
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    return [T3._symmetry_point_errors(ach[:, :, s], ref[:, :, s], H[s]['points'], axes[s], H[s]['order'])[:, 0]
            for s in range(B)]


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
        tracks = {}
        for v in ('input', 'S2') + VARIANTS:
            f = f'{root}/ep{ep}/poses_world_vo.npz' if v == 'input' else f'{W}/runs/{arm}/{v}/ep{ep}/poses_world_vo.npz'
            V = np.load(f)
            N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            tracks[v] = T
            g = {n: gt[n][:N] for n in names}
            r[v] = {c: XF.score_track(names, T, g, H, REG[c]) for c in ('lib', 'star')}
        r['delta'] = {v: {c: round(r[v][c]['AUC'] - r['S2'][c]['AUC'], 4) for c in ('lib', 'star')} for v in VARIANTS}
        r['delta_per_obj'] = {v: {c: {n: round(r[v][c]['per_obj_AUC'][n] - r['S2'][c]['per_obj_AUC'][n], 4)
                                      for n in names} for c in ('lib', 'star')} for v in VARIANTS}
        # S10 record (GT-free, written by refine before this script ran)
        js = json.load(open(f'{W}/runs/{arm}/S10g/ep{ep}/pose_opt.json'))
        s10 = js['steps']['S10']
        r['holds'] = {n: [{k: h[k] for k in ('side', 'a', 'b', 'frames_changed', 'change_cm_max', 'w_mean',
                                              'vis_pred_med', 'residual_cm_med', 'residual_deg_med') if k in h}
                          for h in s10['objects'][n]['holds']] for n in names}
        r['refine_sha256'] = js['code']['refine_sha256']
        # diagnostic: tracker vs prediction on hold frames, * convention
        aux = np.load(f'{W}/runs/{arm}/S10g/ep{ep}/pose_opt_aux.npz')
        T2 = tracks['S2']
        N = len(T2[names[0]])
        g = {n: gt[n][:N] for n in names}
        Tp = {n: T2[n].copy() for n in names}
        hold = {}
        for n in names:
            side = aux[f'S10_{n}_side']
            P = aux[f'S10_{n}_P']
            m = (side >= 0) & np.isfinite(P).all(axis=(1, 2))
            m[0] = False
            hold[n] = m
            Tp[n][m] = P[m]
        e_trk = per_frame(names, T2, g, H, REG['star'])
        e_P = per_frame(names, Tp, g, H, REG['star'])
        r['diag'] = {n: dict(cls=CLASS.get(n, n), frames=np.nonzero(hold[n])[0].tolist(),
                             e_trk_cm=np.round(e_trk[s][hold[n]] * 100, 3).tolist(),
                             e_P_cm=np.round(e_P[s][hold[n]] * 100, 3).tolist(),
                             vP=np.round(aux[f'S10_{n}_vP'][hold[n]], 3).tolist(),
                             w_g=np.round(aux[f'S10_{n}_w'][hold[n]], 3).tolist())
                     for s, n in enumerate(names)}
        out['arms'][arm] = r
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: ' + ' | '.join(f'{arm} S2 lib {r["S2"]["lib"]["AUC"]:.4f} Δlib g/r/t '
                                   + '/'.join(f'{r["delta"][v]["lib"]:+.4f}' for v in VARIANTS)
                                   for arm, r in out['arms'].items()) + f' ({out["seconds"]} s)', flush=True)
    return ep, out


def summarise(res):
    verdict = {}
    for arm in ARMS:
        va = {}
        for v in VARIANTS:
            d = {c: {e: res[str(e)]['arms'][arm]['delta'][v][c] for e in XF.PUBLIC} for c in ('lib', 'star')}
            pm = {c: round(float(np.mean([d[c][e] for e in PROXY])), 5) for c in d}
            mn = {c: min(d[c].values()) for c in d}
            worst = {c: min(d[c], key=d[c].get) for c in d}
            cls = {}
            for e in XF.PUBLIC:
                for n, x in res[str(e)]['arms'][arm]['delta_per_obj'][v]['lib'].items():
                    cls.setdefault(CLASS.get(n, n), []).append(x)
            va[v] = dict(proxy_mean=pm, proxy={c: {e: d[c][e] for e in PROXY} for c in d}, min=mn, worst_ep=worst,
                         mean20={c: round(float(np.mean(list(d[c].values()))), 5) for c in d},
                         better_worse={c: [sum(x > 0 for x in d[c].values()), sum(x < 0 for x in d[c].values())] for c in d},
                         per_class_lib_mean={k: [round(float(np.mean(x)), 4), len(x)] for k, x in cls.items()},
                         rule_pass=bool(pm['lib'] >= MEAN_MIN and mn['lib'] >= DROP_MIN))
        verdict[arm] = va
    adopt = all(verdict[arm]['S10g']['rule_pass'] for arm in ARMS)
    # [H-HP] diagnostic, pooled over the thin objects' holds (Po arm primary; refineP beside it)
    diag = {}
    for arm in ARMS:
        dd = {}
        for grp, members in (('thin', ('sweeper', 'dust pan')), ('cups', ('cups',)), ('pot/lid', ('pot/lid',)),
                             ('all', None)):
            et, ep_, vp = [], [], []
            for e in XF.PUBLIC:
                for n, x in res[str(e)]['arms'][arm]['diag'].items():
                    if members is None or x['cls'] in members:
                        et += x['e_trk_cm']; ep_ += x['e_P_cm']; vp += x['vP']
            et, ep_, vp = np.array(et), np.array(ep_), np.array(vp, float)
            bins = {}
            for name, lo, hi in (('v<0.4', -1, 0.4), ('0.4<=v<0.8', 0.4, 0.8), ('v>=0.8', 0.8, 2), ('all', -1, 2)):
                m = (vp >= lo) & (vp < hi)
                bins[name] = dict(n=int(m.sum()),
                                  trk_med_cm=round(float(np.median(et[m])), 3) if m.any() else None,
                                  P_med_cm=round(float(np.median(ep_[m])), 3) if m.any() else None,
                                  P_better_share=round(float((ep_[m] < et[m]).mean()), 3) if m.any() else None)
            dd[grp] = bins
        diag[arm] = dd
    return verdict, adopt, diag


def main():
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit('public episodes only')
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for ep, r in ex.map(episode, XF.PUBLIC):
            res[str(ep)] = r
    verdict, adopt, diag = summarise(res)
    for arm in ARMS:
        for v in VARIANTS:
            x = verdict[arm][v]
            print(arm, v, 'proxy mean', x['proxy_mean'], 'min', x['min'], x['worst_ep'], 'pass', x['rule_pass'])
    print('ADOPT S10g:', adopt)
    print(json.dumps(diag, indent=1))
    json.dump(dict(note='ORACLE SCORING (public mocap, X*_geom) of heldpose / refine S10; inference ran before, in '
                        'hp_run.sh. Rule: README §0.', rule=dict(proxy=PROXY, mean_min=MEAN_MIN, drop_min=DROP_MIN),
                   verdict=verdict, adopt_S10g=adopt, diag=diag, episodes=res), open(sys.argv[1], 'w'))
    print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
