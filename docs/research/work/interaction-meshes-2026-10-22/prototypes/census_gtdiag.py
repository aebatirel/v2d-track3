"""DIAGNOSTIC ONLY (reads mocap ground truth of PUBLIC episodes; never an input to the method).
Same overlap census as census1.py, but OUR meshes are posed with the mocap relative pose (parquet observation.objects
'pose', world_T_object in the scan frame = our mesh frame). Overlap under mocap = error of our MESHES alone; the
difference to census1 (our tracks) = contribution of our TRACKS. Also: relative-pose error of our tracks vs mocap at
the interaction frames (translation of A's origin in B's frame, rotation).
Usage: python census_gtdiag.py EP [EP ...]  -> census/ep<EP>_gtdiag_summary.json, census/ep<EP>_gtdiag_<var>.csv"""
import os, sys, json, csv
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census1 as C


def gt_poses(ep, names):
    tab = pq.read_table(f'{C.S}/loc/t3/ep{ep}.parquet', columns=['observation.objects']).column(0).to_pylist()
    out = {n: np.full((len(tab), 4, 4), np.nan) for n in names}; vis = {n: np.zeros(len(tab), bool) for n in names}
    for t, objs in enumerate(tab):
        for o in objs:
            if o['name'] in out and o['pose'] is not None:
                q = np.array(o['pose'], float); M = np.eye(4)
                M[:3, :3] = Rot.from_quat([q[4], q[5], q[6], q[3]]).as_matrix(); M[:3, 3] = q[:3]
                out[o['name']][t] = M; vis[o['name']][t] = bool(o['visible'])
    return out, vis


def main(ep):
    names = json.load(open(f'{C.S}/loc/perc/ep{ep}/result.json'))['objects']
    G, vis = gt_poses(ep, names)
    P = dict(np.load(f'{C.S}/loc/perc/ep{ep}/poses.npz'))
    T = min(len(P['world_T_cam']), len(G[names[0]]))
    ok = np.isfinite(G[names[0]][:T]).all((1, 2)) & np.isfinite(G[names[1]][:T]).all((1, 2))
    variants = ['v2'] + (['v4'] if names[0].startswith('wooden') else []) + (['v3'] if 'mini_sweeper' in names else [])
    summ = dict(ep=ep, names=names, frames=T, gt_valid_frames=int(ok.sum()), variants={})
    # tracks vs mocap relative pose (A in B frame)
    Ct = {n: P[f'cam_T_{n}'][:T].astype(np.float64) for n in names}
    rel_err_t, rel_err_r = np.full(T, np.nan), np.full(T, np.nan)
    for t in np.flatnonzero(ok):
        Ro = np.linalg.inv(Ct[names[1]][t]) @ Ct[names[0]][t]; Rg = np.linalg.inv(G[names[1]][t]) @ G[names[0]][t]
        rel_err_t[t] = np.linalg.norm(Ro[:3, 3] - Rg[:3, 3]) * 1e3
        rel_err_r[t] = np.degrees(Rot.from_matrix(Ro[:3, :3] @ Rg[:3, :3].T).magnitude())
    for var in variants:
        A, B = C.load_obj(names[0], var), C.load_obj(names[1], var)
        rows = []
        for t in range(T):
            if not ok[t]:
                rows.append(dict(frame=t, valid=0)); continue
            Tab = np.linalg.inv(G[names[1]][t]) @ G[names[0]][t]
            iA, dA, _ = C.inside(A, B, Tab); iB, dB, _ = C.inside(B, A, np.linalg.inv(Tab))
            r = dict(frame=t, valid=1, ov_mean_cm3=0.5 * (len(iA) + len(iB)) * C.H3, ov_AinB_cm3=len(iA) * C.H3, ov_BinA_cm3=len(iB) * C.H3,
                     pen_mm=float(max(dA.max() if len(dA) else 0, dB.max() if len(dB) else 0) * 1e3),
                     surf_dist_mm=C.surf_dist(A, B, Tab) * 1e3, track_rel_err_mm=rel_err_t[t], track_rel_err_deg=rel_err_r[t])
            for tag, idx, O in (('A', iA, A), ('B', iB, B)):
                if len(idx):
                    c = O['pts'][idx]
                    r.update({f'c{tag}_cm': np.round(c.mean(0) * 100, 2).tolist(), f'ext{tag}_cm': np.round(np.ptp(c, 0) * 100, 1).tolist()})
            rows.append(r)
        keys = list(dict.fromkeys(k for r in rows for k in r))
        with open(f'{C.OUT}/ep{ep}_gtdiag_{var}.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, keys, restval=''); w.writeheader(); w.writerows(rows)
        ov = np.array([r.get('ov_mean_cm3', np.nan) for r in rows]); ds = np.array([r.get('surf_dist_mm', np.nan) for r in rows])
        pen = np.array([r.get('pen_mm', np.nan) for r in rows])
        # same frames as the track census's overlap frames
        z = np.load(f'{C.OUT}/ep{ep}_{var}_regions.npz'); ovf = z['overlap_frames']; ovf = ovf[ovf < T]
        k = int(np.nanargmax(ov)) if np.isfinite(ov).any() else 0
        summ['variants'][var] = dict(
            max_overlap_cm3=float(np.nanmax(ov)) if np.isfinite(ov).any() else None, max_overlap_frame=k,
            at_max=rows[k], frames_contact_lt5mm=int(np.nansum(ds < 5)), frames_overlap_gt1cm3=int(np.nansum(ov > 1)),
            max_pen_mm=float(np.nanmax(pen)) if np.isfinite(pen).any() else None,
            on_track_overlap_frames=dict(n=int(len(ovf)), gt_ov_median_cm3=float(np.nanmedian(ov[ovf])) if len(ovf) else None,
                                         gt_pen_median_mm=float(np.nanmedian(pen[ovf])) if len(ovf) else None,
                                         track_ov_median_cm3=float(np.median(z['ov_mean'][ovf])) if len(ovf) else None,
                                         track_rel_err_mm_median=float(np.nanmedian(rel_err_t[ovf])) if len(ovf) else None,
                                         track_rel_err_deg_median=float(np.nanmedian(rel_err_r[ovf])) if len(ovf) else None,
                                         gt_valid=int(ok[ovf].sum()) if len(ovf) else 0))
        print(f'ep{ep} {var} [mocap poses]: max ov {summ["variants"][var]["max_overlap_cm3"]} @f{k}, >1cm3 {int(np.nansum(ov > 1))} f, '
              f'contact<5mm {int(np.nansum(ds < 5))} f, on track-overlap frames: {summ["variants"][var]["on_track_overlap_frames"]}', flush=True)
    summ['track_rel_err_mm_median_all'] = float(np.nanmedian(rel_err_t)); summ['track_rel_err_deg_median_all'] = float(np.nanmedian(rel_err_r))
    json.dump(summ, open(f'{C.OUT}/ep{ep}_gtdiag_summary.json', 'w'), indent=1, default=float)


if __name__ == '__main__':
    for e in sys.argv[1:]:
        main(int(e))
