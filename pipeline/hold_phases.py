"""Hold phases of a reference (2026-10-23, secure grasp-lock reference, docs/research/notes/23): which hand holds which
object from which frame to which, from our own reference only (MANO contact labels + the object trajectory; no ground
truth). A hand holds an object at frame t when it has >= MIN_CONTACTS active contact points on it and the object is
carried (off its rest pose by > MOVE_CM, or within PRE frames before it starts moving / POST after it settles).
Gaps <= BRIDGE (12) frames are bridged (an object being carried cannot hold itself: the labels flicker mid-hold, e.g.
eval ep3 8-10 frame gaps while the spoon stirs); phases shorter than MIN_LEN are dropped.
Usage: hold_phases.py REF.parquet [--json OUT]
"""
import argparse, json

import numpy as np
import pyarrow.parquet as pq

MIN_CONTACTS, MOVE_CM, PRE, POST, BRIDGE, MIN_LEN = 2, 1.5, 8, 4, 12, 6


def runs(mask):
    """[(start, end_exclusive)] of True runs."""
    m = np.concatenate([[0], mask.astype(int), [0]]); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def bridge(mask, gap):
    out = mask.copy(); r = runs(mask)
    for (a0, a1), (b0, _) in zip(r, r[1:]):
        if b0 - a1 <= gap:
            out[a1:b0] = True
    return out


def hold_phases(path):
    t = pq.read_table(path); names = t.column('object_body_names')[0].as_py()
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    phases, counts = [], {}
    for j, o in enumerate(names):
        disp = 100 * np.linalg.norm(OP[:, j] - OP[0, j], axis=1)
        carried = disp > MOVE_CM
        # also the frames just before the object starts moving (the grasp closes) and just after it settles
        grow = carried.copy()
        for a, b in runs(carried):
            grow[max(0, a - PRE):a] = True; grow[b:min(T, b + POST)] = True
        for s in ('left', 'right'):
            n = np.array(t.column(f'mano_{s}_object_contact_normals')[0].as_py(), float).reshape(T, -1, 3)
            pid = np.array(t.column(f'mano_{s}_object_contact_part_ids')[0].as_py()).reshape(T, -1)
            c = ((np.linalg.norm(n, axis=-1) > 1e-3) & (pid == j + 1)).sum(1); counts[(s, o)] = c
            hold = bridge((c >= MIN_CONTACTS) & grow, BRIDGE)
            for a, b in runs(hold):
                if b - a >= MIN_LEN:
                    phases.append(dict(hand=s, object=o, start=int(a), end=int(b), frames=int(b - a),
                                       mean_contacts=round(float(c[a:b].mean()), 1),
                                       object_travel_cm=round(float(disp[a:b].max()), 1)))
    phases.sort(key=lambda p: (p['start'], p['hand']))
    return dict(frames=T, objects=names, phases=phases), counts


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('--json'); a = p.parse_args()
    out, counts = hold_phases(a.ref)
    for ph in out['phases']:
        print(f"{ph['hand']:5s} holds {ph['object']:14s} frames {ph['start']:4d}-{ph['end']:4d} ({ph['frames']:3d}), "
              f"contacts {ph['mean_contacts']}, object travel {ph['object_travel_cm']} cm")
    # overlaps between hands on the same object = hand changes / two-handed holds
    P = out['phases']
    for i, x in enumerate(P):
        for y in P[i + 1:]:
            if x['object'] == y['object'] and x['hand'] != y['hand'] and x['start'] < y['end'] and y['start'] < x['end']:
                print(f"  two-handed on {x['object']}: frames {max(x['start'], y['start'])}-{min(x['end'], y['end'])}")
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)
