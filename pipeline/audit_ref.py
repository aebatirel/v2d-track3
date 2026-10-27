#!/usr/bin/env python3
"""Physics-feasibility and contact-label audit of one FlashCHORD reference parquet (CPU, note 23 §E lever 2).

Reads only the reference (our inference output, or any FlashCHORD ManoSharpa parquet) and the object meshes it names.
No ground truth. Flags reference problems that can force drops or penalise the grip the carry needs:
  1. frame 0: object lowest point vs the table top (hover / penetration), object-object gaps;
  2. object path: jumps between frames, moving frames (speed > 0.05 m/s or > 30 deg/s on a smoothed path);
  3. contacts: moving frames where no hand has a reference contact on that object (the policy cannot move it without
     touching, and any touch then draws the -10 unintended-contact penalty); contact labels with no hand frame within
     CONTACT_FAR of the object;
  4. hand-object geometry: per moving frame, the nearest robot hand frame to the object surface;
  5. grasp rigidity: wrist pose in the object frame over each contact segment (spread = hand reference sliding on
     the object while it is "held");
  6. wrist demand: per-axis residual (M a + m g z + kd v) / kp along the reference WRIST path while the object moves,
     at the default kp 25 / kd 6 and at kp 100 / kd 12 (clip 0.20 m), as in docs/research/work/23/carry_model.py.

Usage: python audit_ref.py REF.parquet [--table_z 0.60] [--mesh NAME=PATH ...] [--mesh_root DIR] [--out audit.json]
"""
import argparse, glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.signal import savgol_filter
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

M_HAND, M_OBJ, G = 1.243, 0.3, 9.81
CLIP, CONTACT_FAR, JUMP_POS, JUMP_ROT = 0.20, 0.03, 0.10, np.radians(30)


def args():
    p = argparse.ArgumentParser()
    p.add_argument('parquet')
    p.add_argument('--table_z', type=float, default=None, help='support top height (default: lowest object point at frame 0)')
    p.add_argument('--mesh', action='append', default=[], help='NAME=PATH override for an object mesh')
    p.add_argument('--mesh_root', default=None, help='search this directory for <basename of object_mesh_paths>')
    p.add_argument('--out', default=None)
    return p.parse_args()


def load(path):
    r = pq.read_table(path).to_pylist()[0]
    A = lambda k: np.asarray(r[k], float)  # noqa: E731
    ref = dict(fps=float(r['fps']), names=[str(n) for n in r['object_body_names']],
               mesh_paths=[str(m) for m in r['object_mesh_paths']],
               obj_p=A('object_body_position'), obj_q=A('object_body_wxyz'), hands={})
    for s in ('right', 'left'):
        fr = A(f'robot_{s}_frames')
        names = [str(n) for n in r[f'{s}_robot_frame_names']]
        keep = [i for i, n in enumerate(names) if n not in ('universe', 'root_joint')]
        ref['hands'][s] = dict(wrist_p=A(f'robot_{s}_wrist_position'), wrist_q=A(f'robot_{s}_wrist_wxyz'),
                               frames=fr[:, keep, :3], part=np.asarray(r[f'mano_{s}_object_contact_part_ids'], int),
                               task_err=A(f'robot_{s}_frame_task_errors') if f'robot_{s}_frame_task_errors' in r else None)
    return ref


def mesh_points(name, path, a):
    over = dict(m.split('=', 1) for m in a.mesh)
    cand = [over.get(name), path]
    if a.mesh_root:
        cand += glob.glob(os.path.join(a.mesh_root, '**', os.path.basename(path)), recursive=True)
        cand += glob.glob(os.path.join(a.mesh_root, name, '*.glb')) + glob.glob(os.path.join(a.mesh_root, name, '*.obj'))
    for c in cand:
        if c and os.path.exists(c):
            m = trimesh.load(c, force='mesh')
            pts = trimesh.sample.sample_surface(m, 8000, seed=0)[0]
            return np.vstack([pts, np.asarray(m.vertices)[:: max(1, len(m.vertices) // 4000)]])
    sys.exit(f'mesh for {name} not found (tried {cand[:3]}); pass --mesh {name}=PATH or --mesh_root')


def R_of(q):  # wxyz -> matrix
    return Rot.from_quat(np.c_[q[..., 1:], q[..., :1]]).as_matrix()


def ang_vel(q, dt):
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    for i in range(1, len(q)):
        if np.dot(q[i], q[i - 1]) < 0:
            q[i] = -q[i]
    r = Rot.from_quat(np.c_[q[:, 1:], q[:, :1]])
    w = (r[1:] * r[:-1].inv()).as_rotvec() / dt
    return np.vstack([w[:1], w])


def segments(mask, gap=3, min_len=5):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    out, s, e = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - e <= gap:
            e = i
        else:
            out.append((s, e)); s = e = i
    out.append((s, e))
    return [(int(x), int(y)) for x, y in out if y - x + 1 >= min_len]


def main():
    a = args()
    ref = load(a.parquet)
    dt, names = 1.0 / ref['fps'], ref['names']
    T, B = ref['obj_p'].shape[:2]
    pts = [mesh_points(n, p, a) for n, p in zip(names, ref['mesh_paths'])]
    trees = [cKDTree(p) for p in pts]
    R = R_of(ref['obj_q'])                                     # (T,B,3,3)
    world = lambda b, t: pts[b] @ R[t, b].T + ref['obj_p'][t, b]  # noqa: E731
    rep = dict(parquet=a.parquet, fps=ref['fps'], frames=T, objects=names, frame0={}, objects_audit={}, hands={})

    low0 = [world(b, 0)[:, 2].min() for b in range(B)]
    table_z = a.table_z if a.table_z is not None else min(low0)
    rep['table_z'] = table_z
    for b, n in enumerate(names):
        others = {names[o]: round(100 * float(cKDTree(world(o, 0)).query(world(b, 0))[0].min()), 1)
                  for o in range(B) if o != b}
        rep['frame0'][n] = dict(lowest_above_table_cm=round(100 * (low0[b] - table_z), 1), min_gap_to_other_cm=others)

    win = min(9, T - (1 - T % 2)) if T >= 5 else 0
    for b, n in enumerate(names):
        x, q = ref['obj_p'][:, b], ref['obj_q'][:, b]
        dpos = np.r_[0, np.linalg.norm(np.diff(x, axis=0), axis=1)]
        w_raw = ang_vel(q.copy(), dt)
        drot = np.linalg.norm(w_raw, axis=1) * dt
        v = savgol_filter(x, win, 2, deriv=1, delta=dt, axis=0) if win else np.gradient(x, dt, axis=0)
        acc = savgol_filter(x, win, 2, deriv=2, delta=dt, axis=0) if win else np.gradient(v, dt, axis=0)
        w = savgol_filter(w_raw, win, 2, axis=0) if win else w_raw
        mov = (np.linalg.norm(v, axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
        touched = np.zeros(T, bool); near = np.full(T, np.inf); near_side = np.array([''] * T, dtype=object)
        label_far = 0
        for s, h in ref['hands'].items():
            has = (h['part'] == b + 1).any(axis=1)
            touched |= has
            for t in range(T):
                pl = (h['frames'][t] - ref['obj_p'][t, b]) @ R[t, b]          # hand frames in the object frame
                d = trees[b].query(pl)[0].min()
                if d < near[t]:
                    near[t], near_side[t] = d, s
                if has[t] and d > CONTACT_FAR:
                    label_far += 1
        segs = segments(mov)
        seg_rows = []
        for s0, s1 in segs:
            sl = slice(s0, s1 + 1)
            seg_rows.append(dict(start=s0, end=s1, dur_s=round((s1 - s0 + 1) * dt, 2),
                                 lift_cm=round(100 * float(x[sl, 2].max() - x[s0, 2]), 1),
                                 frac_with_contact=round(float(touched[sl].mean()), 2),
                                 nearest_hand_median_cm=round(100 * float(np.median(near[sl])), 1),
                                 nearest_hand_max_cm=round(100 * float(near[sl].max()), 1)))
        # wrist demand along the reference wrist of the hand nearest the object, on moving frames
        demand = {}
        for kp, kd in ((25.0, 6.0), (100.0, 12.0)):
            sat, z95 = 0, []
            for t0, t1 in segs:
                sl = slice(t0, t1 + 1)
                side = max(set(near_side[sl]), key=list(near_side[sl]).count)
                wp = ref['hands'][side]['wrist_p']
                wv = savgol_filter(wp, win, 2, deriv=1, delta=dt, axis=0) if win else np.gradient(wp, dt, axis=0)
                wa = savgol_filter(wp, win, 2, deriv=2, delta=dt, axis=0) if win else np.gradient(wv, dt, axis=0)
                F = (M_HAND + M_OBJ) * wa[sl] + kd * wv[sl]
                F[:, 2] += M_OBJ * G
                r = np.abs(F / kp)
                sat += int((r.max(axis=1) > CLIP).sum()); z95 += list(r[:, 2])
            demand[f'kp{int(kp)}'] = dict(saturated_frames=sat, moving_frames=int(mov.sum()),
                                          z_p95_cm=round(100 * float(np.percentile(z95, 95)), 1) if z95 else 0.0)
        # grasp rigidity: wrist pose in the object frame over contact runs >= 10 frames, per hand
        rig = []
        for s, h in ref['hands'].items():
            has = (h['part'] == b + 1).any(axis=1)
            for c0, c1 in segments(has, gap=2, min_len=10):
                sl = slice(c0, c1 + 1)
                rel_p = np.einsum('tij,ti->tj', R[sl, b], h['wrist_p'][sl] - ref['obj_p'][sl, b])
                rel_R = Rot.from_matrix(np.einsum('tji,tjk->tik', R[sl, b], R_of(h['wrist_q'][sl])))
                ang = (rel_R * rel_R.mean().inv()).magnitude()
                moved = float(np.linalg.norm(x[c1] - x[c0]))
                rig.append(dict(hand=s, start=c0, end=c1, object_moved_cm=round(100 * moved, 1),
                                wrist_slide_cm=round(100 * float(np.linalg.norm(rel_p.std(axis=0))), 1),
                                wrist_turn_deg=round(float(np.degrees(np.median(ang))), 1)))
        rep['objects_audit'][n] = dict(
            jumps=int(((dpos > JUMP_POS) | (drot > JUMP_ROT)).sum()), max_step_cm=round(100 * float(dpos.max()), 1),
            max_step_deg=round(float(np.degrees(drot.max())), 1), moving_frames=int(mov.sum()),
            moving_without_contact=int((mov & ~touched).sum()), contact_labels_far_from_hand=int(label_far),
            peak_speed=round(float(np.linalg.norm(v, axis=1).max()), 2),
            peak_acc=round(float(np.linalg.norm(acc, axis=1).max()), 2),
            moving_segments=seg_rows, wrist_demand=demand, grasp_rigidity=rig)
    for s, h in ref['hands'].items():
        rep['hands'][s] = dict(contact_frames=int((h['part'] > 0).any(axis=1).sum()),
                               ik_task_err_median_cm=(round(100 * float(np.median(h['task_err'])), 2)
                                                      if h['task_err'] is not None else None))
    out = a.out or os.path.splitext(a.parquet)[0] + '_audit.json'
    json.dump(rep, open(out, 'w'), indent=1)
    print(f"{os.path.basename(a.parquet)}: {T} frames at {ref['fps']:g} fps, table_z {table_z:.3f}")
    for n, d in rep['frame0'].items():
        print(f"  frame 0 {n}: lowest point {d['lowest_above_table_cm']:+.1f} cm vs table, gaps {d['min_gap_to_other_cm']}")
    for n, d in rep['objects_audit'].items():
        print(f"  {n}: moving {d['moving_frames']} frames, WITHOUT contact {d['moving_without_contact']}, "
              f"contact labels > {100 * CONTACT_FAR:.0f} cm from hand {d['contact_labels_far_from_hand']}, jumps "
              f"{d['jumps']} (max step {d['max_step_cm']} cm / {d['max_step_deg']} deg), peak {d['peak_speed']} m/s "
              f"{d['peak_acc']} m/s^2")
        for sg in d['moving_segments']:
            print(f"    move {sg['start']}-{sg['end']} ({sg['dur_s']} s, lift {sg['lift_cm']} cm): contact "
                  f"{sg['frac_with_contact']:.0%}, nearest hand frame median {sg['nearest_hand_median_cm']} cm, "
                  f"max {sg['nearest_hand_max_cm']} cm")
        for k, dm in d['wrist_demand'].items():
            print(f"    wrist demand {k}: saturated {dm['saturated_frames']}/{dm['moving_frames']} moving frames, "
                  f"z p95 {dm['z_p95_cm']} cm")
        for g in d['grasp_rigidity']:
            print(f"    contact run {g['hand']} {g['start']}-{g['end']}: object moved {g['object_moved_cm']} cm, wrist "
                  f"slides {g['wrist_slide_cm']} cm / turns {g['wrist_turn_deg']} deg in the object frame")
    for s, d in rep['hands'].items():
        print(f"  {s} hand: contact frames {d['contact_frames']}, IK task error median {d['ik_task_err_median_cm']} cm")
    print(f"  -> {out}")


if __name__ == '__main__':
    main()
