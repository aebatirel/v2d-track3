"""Step 1 of the perfect-following plan (1 Nov 2026): CPU preflight of the 20 packed eval references. No ground truth:
it reads only our references (the packed one and, for grasp-lock episodes, the support-filled one before the lock) and
our library meshes.

Per episode and object:
  holds_pre / holds_ref   hold phases (pipeline/hold_phases.py: MANO contacts + object motion) before the lock and in the
                          packed reference;
  two_hand_pre            frames where BOTH human hands hold the object before the lock (two-hand hold or hand-over
                          overlap) and the hand sequence (e.g. L>R = hand-over);
  robot_reach             over the frames where the object moves (speed > 2 cm/s or 20 deg/s, 3-frame smoothing), the
                          share of frames with no ROBOT fingertip (tip sites of the packed reference) within 3 cm of the
                          posed object surface, per hand the share with >= 2 tips within 3 cm, and the longest such run;
  rest_motion             frames outside every hold of the packed reference (+-3 frames) where the object still moves:
                          translation (cm) and rotation (deg) accumulated there, and for cups the spin about the body z
                          axis (unobservable twist) separately;
  jitter                  p95 / max of the object's and the robot wrists' acceleration (m/s^2) and angular rates.
Usage: python preflight.py STORE_DIR OUT_JSON
"""
import json, os, sys
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(f'{HERE}/../../..')
sys.path.insert(0, f'{REPO}/pipeline')
from hold_phases import hold_phases

CUPS = {'blue_cup', 'beige_cup'}
REACH_M, V_LIN, V_ANG = 0.03, 0.02, 20.0


def col(t, c):
    return t.column(c)[0].as_py()


def load(path):
    t = pq.read_table(path); names = col(t, 'object_body_names'); fps = float(col(t, 'fps'))
    T = len(np.array(col(t, 'robot_left_wrist_position')).reshape(-1, 3))
    OP = np.array(col(t, 'object_body_position'), float).reshape(T, len(names), 3)
    OQ = np.array(col(t, 'object_body_wxyz'), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
    W = {s: np.array(col(t, f'robot_{s}_wrist_position'), float).reshape(T, 3) for s in ('left', 'right')}
    WQ = {s: np.array(col(t, f'robot_{s}_wrist_wxyz'), float).reshape(T, 4)[:, [1, 2, 3, 0]] for s in ('left', 'right')}
    tips = {}
    for s in ('left', 'right'):
        fn = col(t, f'{s}_robot_frame_names'); F = np.array(col(t, f'robot_{s}_frames'), float).reshape(T, len(fn), 7)
        tips[s] = F[:, [i for i, n in enumerate(fn) if n.endswith('tip_site')], :3]
    return dict(t=t, names=names, fps=fps, T=T, OP=OP, OQ=OQ, W=W, WQ=WQ, tips=tips)


def runs(m):
    m = np.concatenate([[0], m.astype(int), [0]]); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def smooth(x, k=3):
    if len(x) < k: return x
    ker = np.ones(k) / k
    return np.stack([np.convolve(x[:, i], ker, mode='same') for i in range(x.shape[1])], 1)


def episode(ep, ref_path, sf_path, mesh_dir):
    R = load(ref_path); T, fps = R['T'], R['fps']
    hp_ref = hold_phases(ref_path)[0]['phases']
    hp_pre = hold_phases(sf_path)[0]['phases'] if sf_path else None
    out = dict(ep=ep, frames=T, fps=fps, objects=R['names'], holds_ref=hp_ref, holds_pre=hp_pre, obj={})
    for j, o in enumerate(R['names']):
        P, Q = R['OP'][:, j], R['OQ'][:, j]
        rot = Rot.from_quat(Q)
        v = np.r_[0, np.linalg.norm(np.diff(smooth(P), axis=0), axis=1) * fps]
        dr = (rot[1:] * rot[:-1].inv()).magnitude()
        w = np.r_[0, np.degrees(dr) * fps]
        w = np.convolve(w, np.ones(3) / 3, mode='same')
        moving = (v > V_LIN) | (w > V_ANG)
        # spin about the body z axis between consecutive frames (twist part of the relative rotation in the body frame)
        rel = (rot[:-1].inv() * rot[1:]).as_quat()                       # body-frame increments, xyzw
        tw = np.r_[0, np.degrees(2 * np.arctan2(rel[:, 2], rel[:, 3]))]
        tw = (tw + 180) % 360 - 180
        # robot reach while moving
        mesh = trimesh.load(f'{mesh_dir}/{o}.glb', force='mesh'); pqm = trimesh.proximity.ProximityQuery(mesh)
        idx = np.arange(T); near = {s: np.zeros(T, int) for s in ('left', 'right')}; dmin = np.full(T, np.inf)
        for f in idx:
            Rinv = rot[f].inv()
            for s in ('left', 'right'):
                loc = Rinv.apply(R['tips'][s][f] - P[f])
                d = np.abs(pqm.signed_distance(loc))
                near[s][f] = int((d < REACH_M).sum()); dmin[f] = min(dmin[f], float(d.min()))
        none = moving & (near['left'] == 0) & (near['right'] == 0)
        nr = runs(none); longest = max([b - a for a, b in nr], default=0)
        # motion outside holds of the packed reference
        held = np.zeros(T, bool)
        for p in hp_ref:
            if p['object'] == o: held[max(0, p['start'] - 3):min(T, p['end'] + 3)] = True
        free = ~held
        trans_free = float(np.linalg.norm(np.diff(P, axis=0), axis=1)[free[1:]].sum() * 100)
        rot_free = float(np.degrees(dr[free[1:]]).sum())
        o_out = dict(moving_frames=int(moving.sum()),
                     no_robot_tip_frames=int(none.sum()), no_robot_tip_longest=int(longest),
                     no_robot_tip_runs=[(int(a), int(b)) for a, b in nr if b - a >= 3],
                     grip_frames={s: int(((near[s] >= 2) & moving).sum()) for s in near},
                     free_frames=int(free.sum()), free_trans_cm=round(trans_free, 1), free_rot_deg=round(rot_free, 1),
                     acc_p95=round(float(np.percentile(np.abs(np.diff(P, 2, axis=0)).max(1) * fps * fps, 95)), 2),
                     angvel_p95_dps=round(float(np.percentile(w, 95)), 1))
        if o in CUPS:
            o_out['twist_free_deg'] = round(float(np.abs(tw[free]).sum()), 1)
            o_out['twist_held_deg'] = round(float(np.abs(tw[~free]).sum()), 1)
            o_out['twist_net_free_deg'] = round(float(tw[free].sum()), 1)
        if hp_pre is not None:
            hands = sorted({p['hand'] for p in hp_pre if p['object'] == o})
            seq = [p['hand'][0].upper() for p in sorted([p for p in hp_pre if p['object'] == o], key=lambda p: p['start'])]
            mask = {s: np.zeros(T, bool) for s in ('left', 'right')}
            for p in hp_pre:
                if p['object'] == o: mask[p['hand']][p['start']:p['end']] = True
            both = mask['left'] & mask['right']
            hands_ref = sorted({p['hand'] for p in hp_ref if p['object'] == o})
            o_out.update(pre_hands=hands, pre_seq='>'.join(seq), ref_hands=hands_ref,
                         pre_two_hand_frames=int(both.sum()),
                         pre_two_hand_runs=[(int(a), int(b)) for a, b in runs(both)],
                         lock_dropped_hand=sorted(set(hands) - set(hands_ref)))
            # does the ROBOT hand of each pre-lock hold phase grip the object (>= 2 tips within 3 cm) in the packed ref?
            o_out['pre_phase_robot_grip'] = [dict(hand=p['hand'], start=p['start'], end=p['end'],
                                                  robot_grip=round(float((near[p['hand']][p['start']:p['end']] >= 2).mean()), 2))
                                             for p in sorted([p for p in hp_pre if p['object'] == o], key=lambda p: p['start'])]
        out['obj'][o] = o_out
    jit = {}
    for s in ('left', 'right'):
        a = np.linalg.norm(np.diff(R['W'][s], 2, axis=0), axis=1) * fps * fps
        r = Rot.from_quat(R['WQ'][s]); wv = np.degrees((r[1:] * r[:-1].inv()).magnitude()) * fps
        jit[s] = dict(acc_p95=round(float(np.percentile(a, 95)), 2), acc_max=round(float(a.max()), 2),
                      angvel_p95_dps=round(float(np.percentile(wv, 95)), 1), angvel_max_dps=round(float(wv.max()), 1))
    out['wrist_jitter'] = jit
    return out


if __name__ == '__main__':
    ST, OUT = sys.argv[1], sys.argv[2]
    P = json.load(open(f'{REPO}/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
    res = {}
    for ep in sorted(P, key=int):
        e = P[ep]; run = e['source_run']
        ref = f'{ST}/runs/{run}/{e["reference"]}'
        if not os.path.exists(ref):                                     # std refs: refs/perc2mcks is a copy of perc2mck
            alt = ref.replace('/refs/perc2mcks/', '/refs/perc2mck/')
            d = os.path.dirname(alt)
            cand = [f for f in os.listdir(d)] if os.path.isdir(d) else []
            ref = os.path.join(d, cand[0]) if len(cand) == 1 else None
        sf = None
        if e['mode'] == 'glock':
            seq = f'sequence_id=t3_ep{int(ep):03d}/robot_name=sharpa_wave'
            c = f'{ST}/runs/{run}/refs/sf/ep{ep}/processed/{seq}/ref_sf.parquet'
            sf = c if os.path.exists(c) else None
        if ref is None:
            print(ep, 'reference missing'); continue
        try:
            res[ep] = episode(int(ep), ref, sf, f'{REPO}/meshes/library_v3')
            res[ep]['ref_path'] = ref.replace(ST + '/', ''); res[ep]['sf_path'] = sf and sf.replace(ST + '/', '')
            res[ep]['mode'] = e['mode']
        except Exception as ex:
            print(ep, 'ERROR', repr(ex)); continue
        print(ep, e['mode'], json.dumps({o: {k: v for k, v in d.items() if k in ('pre_seq', 'ref_hands', 'pre_two_hand_frames',
              'no_robot_tip_frames', 'no_robot_tip_longest', 'free_trans_cm', 'free_rot_deg', 'twist_free_deg', 'pre_phase_robot_grip')}
              for o, d in res[ep]['obj'].items()}), flush=True)
    json.dump(res, open(OUT, 'w'), indent=1, default=int)
