"""verify_timing: robot-hand arrival vs the TRUE (mocap) onset, own code (27 Oct 2026, CPU).
Contact = any of the 15 mkref probe sites (either hand) or the palm centre (mean of 5 palm frames) within THR of OUR
mesh surface posed by the SAME reference parquet. Runs: gaps <= 2 frames bridged, runs >= 3 frames kept.
True moving window from mocap: physical onset/offset (speed >= 1 cm/s or rate >= 10 deg/s), my own rule (vt_checks).
Usage: python -I vt_hand.py OUT.json EP:OBJ:SRC [...]   (SRC = pre | ref)
"""
import sys, os, json
import numpy as np, pyarrow.parquet as pq, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
from vt_checks import phys_onset, phys_offset, speed, rrate
from vt_lag import cross

PROBE = ['thumb_tip_site', 'index_tip_site', 'middle_tip_site', 'ring_tip_site', 'pinky_tip_site',
         'thumb_DP_site', 'index_DP_site', 'middle_DP_site', 'ring_DP_site', 'pinky_DP_site',
         'thumb_MCP_VL_site', 'index_MP_site', 'middle_MP_site', 'ring_MP_site', 'pinky_MP_site']
PALM = ['hand_C_MC', 'index_MCP_VL_site', 'middle_MCP_VL_site', 'ring_MCP_VL_site', 'pinky_MC_site']


def runs(mask, gap=2, minlen=3):
    m = mask.copy(); idx = np.nonzero(m)[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= gap + 1:
            m[a:b] = True
    out, t = [], 0
    while t < len(m):
        if m[t]:
            s = t
            while t < len(m) and m[t]:
                t += 1
            if t - s >= minlen:
                out.append((s, t - 1))
        else:
            t += 1
    return out


def main():
    res = {}
    C = L.canon()
    for spec in sys.argv[2:]:
        ep, obj, src = spec.split(':'); ep = int(ep)
        e = C[ep]; fin, pre = L.ref_paths(e); path = fin if src == 'ref' else pre
        lib = L.lib_of(e, 'ref')
        P = L.load_refpq(path)
        cols = ['right_robot_frame_names', 'robot_right_frames', 'left_robot_frame_names', 'robot_left_frames']
        t = pq.read_table(path, columns=cols)
        pts = []
        for side in ('right', 'left'):
            names = t.column(f'{side}_robot_frame_names')[0].as_py()
            F = np.asarray(t.column(f'robot_{side}_frames')[0].as_py(), float)[:, :, :3]
            ix = {n: i for i, n in enumerate(names)}
            pts += [F[:, ix[f'{side}_{s}']] for s in PROBE]
            pts.append(np.mean([F[:, ix[f'{side}_{s}']] for s in PALM], 0))
        X = np.stack(pts, 1)                                   # T x 32 x 3 (table frame)
        mesh = trimesh.load(L.our_mesh(lib, obj), force='mesh')
        M = P[obj]; T = len(M)
        Xb = np.einsum('tji,tkj->tki', M[:, :3, :3], X - M[:, None, :3, 3])   # into the object body frame
        _, dist, _ = trimesh.proximity.closest_point(mesh, Xb.reshape(-1, 3))
        dmin = dist.reshape(T, -1).min(1)
        names, gt = L.load_mocap(ep)
        cg = L.surf_centroid(L.scan_mesh(obj)); Pg = L.point_path(gt[obj], cg)
        dg = np.linalg.norm(Pg - Pg[:5].mean(0), axis=1)
        on = phys_onset(Pg, gt[obj][:, :3, :3], cross(dg, 0.01)); off = phys_offset(Pg, gt[obj][:, :3, :3])
        row = dict(true_on=on, true_off=off)
        for thr in (0.02, 0.01):
            R = runs(dmin < thr)
            cov = [r for r in R if r[0] <= on <= r[1] + 0]
            arr = cov[0][0] if cov else next((r[0] for r in R if r[0] > on), None)
            moving = np.zeros(T, bool); moving[on:off + 1] = True
            vg, wg = speed(Pg), rrate(gt[obj][:, :3, :3]); movmask = (vg >= 1.0) | (wg >= 10.0)
            held = np.zeros(T, bool)
            for a, b in R:
                held[a:b + 1] = True
            row[f'{int(thr*100)}cm'] = dict(arrival=arr, lead=None if arr is None else on - arr,
                                           unheld_true_moving=int((moving & ~held).sum()), true_moving=int(moving.sum()),
                                           unheld_moving_frames=int((movmask & ~held).sum()), moving_frames=int(movmask.sum()),
                                           runs=R[:6])
        row['dmin_cm_around_onset'] = {int(k): round(float(dmin[k] * 100), 1) for k in range(max(0, on - 10), min(T, on + 40), 3)}
        res[spec] = row
        print(spec, json.dumps({k: v for k, v in row.items() if k != 'dmin_cm_around_onset'}))
        print('   dmin around onset', row['dmin_cm_around_onset'])
    json.dump(res, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
