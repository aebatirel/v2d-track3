"""Task 1: per-episode statistics of the public Track 3 mocap trajectories."""
import json
import numpy as np
from common import *

V_LIN, V_ANG = 0.03, np.radians(15)  # moving if smoothed speed > 3 cm/s or > 15 deg/s


def smooth(x, k=5):
    if len(x) < k:
        return x
    ker = np.ones(k) / k
    return np.convolve(np.pad(x, (k//2, k//2), mode="edge"), ker, mode="valid")


def segments(mask):
    segs, start = [], None
    for i, m in enumerate(mask):
        if m and start is None: start = i
        if not m and start is not None: segs.append((start, i)); start = None
    if start is not None: segs.append((start, len(mask)))
    return segs


rows = []
for e in all_episodes():
    p, vis = e["pose"], e["vis"]; T, N, _ = p.shape
    dt = np.median(np.diff(e["ts"]))
    gaps = [len(segments(~vis[:, j])) for j in range(N)]
    held = [int(np.sum(np.all(np.diff(p[:, j], axis=0) == 0, axis=1))) for j in range(N)]
    objs = []
    for j in range(N):
        x, q = p[:, j, :3], p[:, j, 3:]
        disp = np.linalg.norm(x - x[0], axis=1)
        rot = np.degrees(qangle(q, q[0]))
        v = np.r_[0, np.linalg.norm(np.diff(x, axis=0), axis=1)] / dt
        w = np.r_[0, qangle(q[1:], q[:-1])] / dt
        jumps = int(np.sum((v > 1.5) | (w > np.radians(360))))
        mv = (smooth(v) > V_LIN) | (smooth(w) > V_ANG)
        segs = [s for s in segments(mv) if s[1] - s[0] >= 3]
        onset = next((i for i in range(T) if disp[i] > 0.03 or rot[i] > 10), None)
        objs.append(dict(name=e["names"][j], slot=j, max_disp_cm=disp.max()*100, end_disp_cm=disp[-1]*100,
                         path_cm=np.sum(np.linalg.norm(np.diff(x, axis=0), axis=1))*100,
                         ext_cm=list(np.round(np.ptp(x, axis=0)*100, 1)), max_rot_deg=rot.max(), end_rot_deg=rot[-1],
                         peak_v_cms=np.percentile(v, 99)*100, peak_w_dps=np.degrees(np.percentile(w, 99)),
                         moving_pct=mv.mean()*100, n_move_segs=len(segs), onset_frame=onset,
                         jumps=jumps, held_frames=held[j], gaps=gaps[j], z0=x[0, 2]))
    d0 = [np.linalg.norm(p[:, j, :3] - p[0, 0, :3], axis=1) for j in range(N)]
    rows.append(dict(ep=e["ep"], task=TASKS[e["ep"]], T=T, dur_s=T*dt, objs=objs,
                     lever_from_slot0_start_cm=[float(np.mean(d)*100) for d in d0],
                     lever_max_cm=[float(np.max(d)*100) for d in d0]))

json.dump(rows, open("stats.json", "w"), indent=1, default=float)
print(f"{'ep':>3} {'task':18s} {'T':>4} {'s':>5}  slot:name  maxdisp/end cm  path cm  maxrot/end deg  mov%  segs onset  lever(mean/max from slot0 start)")
for r in rows:
    for o in r["objs"]:
        print(f"{r['ep']:>3} {r['task']:18s} {r['T']:>4} {r['dur_s']:5.1f}  {o['slot']}:{o['name']:17s} {o['max_disp_cm']:5.1f}/{o['end_disp_cm']:5.1f} {o['path_cm']:6.1f}  "
              f"{o['max_rot_deg']:5.1f}/{o['end_rot_deg']:5.1f}  {o['moving_pct']:4.0f} {o['n_move_segs']:3d} {str(o['onset_frame']):>5}  "
              f"{r['lever_from_slot0_start_cm'][o['slot']]:5.1f}/{r['lever_max_cm'][o['slot']]:5.1f}  vpk {o['peak_v_cms']:4.0f}cm/s wpk {o['peak_w_dps']:4.0f}d/s jumps {o['jumps']} held {o['held_frames']} gaps {o['gaps']}")
