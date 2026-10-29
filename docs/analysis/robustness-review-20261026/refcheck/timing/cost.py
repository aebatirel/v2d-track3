"""refcheck/timing, cost: what our timing errors cost in the kit's registered AUC (public episodes; diagnostics only).

In-process kit scoring (refcheck/systematics kit_prepare + the kit's own _align_registered_scene /
_symmetry_point_errors / ADD thresholds; checked against pipeline/score_registered.py on ep39 and ep21, shifted paths,
identical to 4 decimals). Sources: perc (all 20 episodes) and ref (the 10 with a canonical reference).
Variants of our object path:
  base         as stored
  shift_pool   ours'(t) = ours(t + L) with ONE constant L = the pooled median sub-frame onset lag of the
               perception (all public objects; inference-legal: a constant chosen on public data)
  shift_ep     the same with this episode's own median onset lag (oracle: needs mocap per episode)
  shift_obj    oracle: each object shifted by its own onset lag (median of its 1 / 2 cm and 10 deg crossing lags,
               only if abs(lag) <= 3; other objects unshifted)
  rest_hold    oracle: ours held at its frame-0 pose until the TRUE physical onset (all frames for an object that
               is static in mocap), and at its own median end-rest pose after the TRUE physical offset (removes creep / jitter / early or late settling outside the true
               moving window; frame 0, which sets the kit's scene alignment, is unchanged)
  (A first version also had a piecewise-linear onset+offset warp; on ep2 ref it scored 0.9402 vs base 0.9798,
   because offset crossings are shifted by spatial settling errors, not by time. Dropped; see README.)
Per-frame breakdown (base): per object and frame the kit ADD and the frame's share of the ADD-AUC (trapezoid over the
kit thresholds, AUC = mean of the shares), grouped by phase: rest (mocap not moving), moving + human hand within 2 cm
with that hand measured, moving + hand near but not measured (tracker-filled or invalid: occlusion proxy), moving with
no hand near, and track-guard re-acquired / held frames (guard arm = canonical perception for ep0 / ep23).
Usage: python -I cost.py TIMING.json OUT.json
"""
import glob, json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401,F403
import timing as TM                                                        # noqa: E402
from v2dlb import track3_pose as T3                                        # noqa: E402
from v2dlb.object_pose import _ADD_THRESHOLDS_M, _add_auc                  # noqa: E402

MAX_WARP, ONSET_KEYS = 40, ('on_p1_f', 'on_p2_f', 'on_r_f')
AX = np.linspace(0.0, 1.0, _ADD_THRESHOLDS_M.size)
TRAP = getattr(np, 'trapezoid', None) or np.trapz


def perframe(ep, names, ours7, gt, H, REG):
    ach, ref = S.kit_prepare(ep, names, ours7, gt, H, REG)
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]
    al = T3._align_registered_scene(ach, ref, axes)
    vals = np.stack([T3._symmetry_point_errors(al[:, :, i], ref[:, :, i], H[i]['points'], axes[i], orders[i])[:, 0]
                     for i in range(len(names))], 1)                              # (T, B) metres
    share = TRAP((vals[..., None] < _ADD_THRESHOLDS_M).astype(float), x=AX, axis=-1)   # (T, B)
    auc = float(_add_auc(vals[:, None, :]))
    return vals, share, auc


def warp_path(A7, kg, ko):
    T = len(A7)
    kg, ko = np.asarray(kg, float), np.asarray(ko, float)
    keep = [0]
    for i in range(1, len(kg)):                                                  # strictly increasing knots
        if kg[i] > kg[keep[-1]] + 0.5 and ko[i] > ko[keep[-1]] + 0.5:
            keep.append(i)
    tq = np.clip(np.interp(np.arange(T), kg[keep], ko[keep]), 0, T - 1)
    pos = np.stack([np.interp(tq, np.arange(T), A7[:, k]) for k in range(3)], 1)
    rot = Slerp(np.arange(T), Rot.from_quat(A7[:, 3:]))(tq).as_quat()
    return np.concatenate([pos, rot], 1)


def ev_pair(evg, evo, kind):
    for k in ((f'{kind}_p1_f', f'{kind}_r_f')):
        if evg.get(k) is not None and evo.get(k) is not None and abs(evo[k] - evg[k]) <= MAX_WARP:
            return evg[k], evo[k]
    return None


def pooled_lag(TJ, src='perc'):
    v = []
    for ep, R in TJ.items():
        if ep == '23':
            continue
        for n, o in R['obj'].items():
            if o['static']:
                continue
            for k in ONSET_KEYS:
                x = o['lags'].get(src, {}).get(k)
                if x is not None and abs(x) <= 3:
                    v.append(x)
    return float(np.median(v)), len(v)


def main():
    TJ = json.load(open(sys.argv[1])); out_path = sys.argv[2]
    Lpool, nl = pooled_lag(TJ, 'perc')
    print('pooled perception onset lag', Lpool, 'from', nl, 'crossings', flush=True)
    C = canon(); res = dict(pooled_onset_lag_frames=round(Lpool, 3), pooled_from_crossings=nl, episodes={})
    if os.path.exists(out_path):                                                  # resume: keep finished episodes
        old = json.load(open(out_path))
        if old.get('pooled_onset_lag_frames') == res['pooled_onset_lag_frames']:
            res['episodes'] = {int(k): v for k, v in old['episodes'].items()}
            print('resuming; done:', sorted(res['episodes']), flush=True)
    for ep, e in sorted(C.items()):
        if ep in res['episodes']:
            continue
        R = TJ[str(ep)]; names, gt = load_gt(ep); T = len(gt[names[0]])
        H = [S.host_geometry(n, s) for s, n in enumerate(names)]
        src = {k: v for k, v in sources(ep, e, with_sim=False, with_stale=False).items() if k in ('perc', 'ref')}
        er = {}
        # phase masks (mocap moving, human hand near / measured), from the reference with hands (pre or stale)
        fin, pre, _ = ref_files(e)
        hp = pre or fin
        if hp is None:
            sf = sorted(glob.glob(f"{STORE}/{STALE.format(ep)}/processed/*/*/*.parquet")); hp = sf[0] if sf else None
            hlib = 'scan'
        else:
            hlib = REF_LIB[ep]
        near, near_meas = {}, {}
        if hp:
            hn, obj, Hh = TM.load_hands(hp)
            import pyarrow.parquet as pq
            raw = pq.read_table(hp, columns=['raw_motion_file']).column(0)[0].as_py()
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(hp)))) if '/processed/' in hp else os.path.dirname(hp)
            hf = os.path.join(base_dir, os.path.basename(raw.split('|')[-1]))
            Hn = np.load(hf) if os.path.exists(hf) else None
            for s, n in enumerate(hn):
                tree = TM.surface_tree(mesh_for(hlib, n))
                dd = {sd: TM.hand_dist(Hh[sd]['human'], obj[n], tree) for sd in ('right', 'left')}
                near[n] = (dd['right'] < 2.0) | (dd['left'] < 2.0)
                if Hn is not None:
                    near_meas[n] = ((dd['right'] < 2.0) & Hn['measured_right'].astype(bool)) | ((dd['left'] < 2.0) & Hn['measured_left'].astype(bool))
        guard = R.get('guard', {}) if e['perception_path'].startswith('runs/20261025-guard-fe3f407') else {}
        for k, v in src.items():
            lib = v['lib']
            REG = [S.registration(ep, s, n, our_mesh_path(lib, n)) for s, n in enumerate(names)]
            b7 = {n: S.to7(v['poses'][n]) for n in names}
            vals, share, auc = perframe(ep, names, b7, gt, H, REG)
            row = dict(base=round(auc, 4), per_obj_base={n: round(float(share[:, i].mean()), 4) for i, n in enumerate(names)})
            # shifts
            for tag, L in (('shift_pool', Lpool),):
                _, _, a2 = perframe(ep, names, {n: S.shift_path(b7[n], L) for n in names}, gt, H, REG)
                row[tag] = round(a2, 4); row[tag + '_L'] = round(L, 3)
            lv = [x for n in names if not R['obj'][n]['static'] for kk, x in R['obj'][n]['lags'].get(k, {}).items()
                  if kk in ONSET_KEYS and abs(x) <= 3]
            if lv:
                Le = float(np.median(lv))
                _, _, a3 = perframe(ep, names, {n: S.shift_path(b7[n], Le) for n in names}, gt, H, REG)
                row['shift_ep'] = round(a3, 4); row['shift_ep_L'] = round(Le, 3)
            # oracle: each object shifted by its own onset lag
            so, Lo = {}, {}
            for n in names:
                lo = [x for kk, x in R['obj'][n]['lags'].get(k, {}).items() if kk in ONSET_KEYS and abs(x) <= 3]
                Lo[n] = round(float(np.median(lo)), 3) if (lo and not R['obj'][n]['static']) else 0.0
                so[n] = S.shift_path(b7[n], Lo[n]) if Lo[n] else b7[n]
            _, _, a5 = perframe(ep, names, so, gt, H, REG)
            row['shift_obj'] = round(a5, 4); row['shift_obj_L'] = Lo
            # oracle: hold our rest poses outside the true moving window
            rh = {}
            for n in names:
                evg = R['obj'][n]['mocap']; A = b7[n].copy()
                if R['obj'][n]['static']:                              # truly static: hold frame 0 throughout
                    A[1:] = A[0]
                elif evg.get('on_phys') is not None:
                    on, off = evg['on_phys'], evg['off_phys']
                    if on > 1:
                        A[1:on] = A[0]
                    if off < T - 2:
                        idx = np.arange(off + 1, T)
                        A[idx, :3] = np.median(A[idx, :3], 0); A[idx, 3:] = Rot.from_quat(A[idx, 3:]).mean().as_quat()
                rh[n] = A
            _, sh4, a4 = perframe(ep, names, rh, gt, H, REG)
            row['rest_hold'] = round(a4, 4)
            row['per_obj_rest_hold'] = {n: round(float(sh4[:, i].mean()), 4) for i, n in enumerate(names)}
            # per-frame phase breakdown (base)
            grp = {}
            for i, n in enumerate(names):
                mv = np.zeros(T, bool)
                evg = R['obj'][n]['mocap']
                if evg.get('on_phys') is not None:
                    for b0, b1 in evg['bouts']:
                        mv[b0:b1 + 1] = True
                nr = near.get(n, np.zeros(T, bool)); nm = near_meas.get(n, nr)
                masks = dict(rest=~mv, moving_hand_measured=mv & nm, moving_hand_unmeasured=mv & nr & ~nm,
                             moving_no_hand=mv & ~nr)
                if k == 'perc' and n in guard:
                    gm = np.zeros(T, bool)
                    for t in guard[n]['reacquired_frames'] + guard[n]['held_frames']:
                        gm[t] = True
                    masks['guard_reacquired_or_held'] = gm
                for gk, m in masks.items():
                    if m.sum() == 0:
                        continue
                    g = grp.setdefault(gk, dict(frames=0, add_cm=[], share=[]))
                    g['frames'] += int(m.sum()); g['add_cm'] += (vals[m, i] * 100).tolist(); g['share'] += share[m, i].tolist()
                    row.setdefault('per_obj_groups', {}).setdefault(n, {})[gk] = dict(
                        frames=int(m.sum()), add_cm_median=round(float(np.median(vals[m, i]) * 100), 2),
                        share_mean=round(float(share[m, i].mean()), 3),
                        auc_loss_contrib=round(float((1 - share[m, i]).sum() / T / len(names)), 4))
            row['groups'] = {gk: dict(frames=g['frames'], add_cm_median=round(float(np.median(g['add_cm'])), 2),
                                      add_cm_p90=round(float(np.percentile(g['add_cm'], 90)), 2),
                                      share_mean=round(float(np.mean(g['share'])), 3)) for gk, g in grp.items()}
            er[k] = row
            print(ep, k, {kk: row[kk] for kk in ('base', 'shift_pool', 'shift_ep', 'shift_obj', 'rest_hold') if kk in row}, flush=True)
        res['episodes'][ep] = er
        json.dump(res, open(out_path, 'w'), indent=1)
    # pooled
    summ = {}
    for k in ('perc', 'ref'):
        rows = [v[k] for ep, v in res['episodes'].items() if k in v]
        rows_x = [v[k] for ep, v in res['episodes'].items() if k in v and ep != 23]
        s = {}
        for var in ('base', 'shift_pool', 'shift_ep', 'shift_obj', 'rest_hold'):
            xs = [r[var] for r in rows_x if var in r]
            s[var] = round(float(np.mean(xs)), 4) if xs else None
            s[var + '_minus_base_mean'] = round(float(np.mean([r[var] - r['base'] for r in rows_x if var in r])), 4) if xs else None
            s[var + '_improved'] = int(sum(r[var] > r['base'] for r in rows_x if var in r))
        s['episodes_excl_ep23'] = len(rows_x)
        summ[k] = s
    res['summary'] = summ
    print(json.dumps(summ, indent=1))
    json.dump(res, open(out_path, 'w'), indent=1)


if __name__ == '__main__':
    main()
