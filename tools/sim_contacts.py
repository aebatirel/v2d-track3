"""Contact targets from a simulated replay (2026-10-30; physics study, "solver into RL" option 2).

FlashCHORD's contact objective rewards the policy for supplying the wrench support of the reference's hand-object
contacts (mano_<side>_object_contact_positions / _normals / _part_ids: world-frame points, unit normals pointing into
the object, 1-indexed object body, 0 = inactive). Ours come from the perceived human hand, which sits near the objects
but does not grip them (docs/research/physics-2026-10-30/README.md). This tool replaces them with the contacts a
simulated replay actually made (e.g. the zero-action replay of a physics-solved reference, tools/physics_solve/), read
with tools/trace_rollout.py CONTACTS=2.

Per frame and hand: every contact between that hand's links and an object body, moved rigidly from the simulated object
pose onto the REFERENCE object pose of that frame (so targets stay attached to where the object should be), normals
oriented hand -> object; at most K per hand (the slot count of the input), strongest normal force first. A frame's hand
targets are replaced only where every object that hand touches is within --max_cm / --max_deg of its reference in the
replay (elsewhere, and on frames where the replay lost the object, the original targets are kept). A hand that touches
nothing while EVERY object is on its reference gets no targets (cleared): the replay shows that hand is not needed
there (e.g. the parked hand of a single-hand carry, whose perceived-hand targets asked it to touch the object). Our reference only;
no ground truth.
Usage: sim_contacts.py REF.parquet TRACE.npz OUT.parquet [--max_cm 3] [--max_deg 20]
"""
import argparse, json, os
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('trace'); ap.add_argument('out')
ap.add_argument('--max_cm', type=float, default=3.0); ap.add_argument('--max_deg', type=float, default=20.0)
a = ap.parse_args()
t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = Rot.from_quat(np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T * B, 4)[:, [1, 2, 3, 0]])
OR = OQ.as_matrix().reshape(T, B, 3, 3)
d = np.load(a.trace); L = [str(x) for x in d['labels']]; q = d['q'].astype(float); fr = np.asarray(d['frame']).astype(int)
if 'cl' not in d.files:
    raise SystemExit('trace has no contact list: record it with CONTACTS=2 tools/trace_rollout.py')
cl = d['cl']
ob = [next(i for i, l in enumerate(L) if l.startswith(f'track3_{n}/')) for n in names]
hand = {s: {i for i, l in enumerate(L) if l.startswith(f'{s}_sharpa_wave/')} for s in ('left', 'right')}
obj_of = {b: j for j, b in enumerate(ob)}

new, stats = {}, {}
for s in ('left', 'right'):
    P = np.array(t.column(f'mano_{s}_object_contact_positions')[0].as_py(), float).reshape(T, -1, 3)
    N = np.array(t.column(f'mano_{s}_object_contact_normals')[0].as_py(), float).reshape(T, -1, 3)
    I = np.array(t.column(f'mano_{s}_object_contact_part_ids')[0].as_py(), float).reshape(T, -1)
    K = P.shape[1]; P2, N2, I2 = P.copy(), N.copy(), I.copy()
    rep = kept_lost = orig_active = sim_active = cleared = 0
    for r in range(len(q)):
        f = fr[r]
        if not 0 <= f < T:
            continue
        rows = cl[cl[:, 0] == r]
        good = {}
        for j, b in enumerate(ob):                                         # replay object vs its reference, this frame
            dp = 100 * np.linalg.norm(q[r, b, :3] - OP[f, j])
            dr = np.degrees((Rot.from_quat(q[r, b, 3:7]) * Rot.from_matrix(OR[f, j]).inv()).magnitude())
            good[j] = dp <= a.max_cm and dr <= a.max_deg
        cand = []
        for row in rows:
            b0, b1 = int(row[1]), int(row[2]); p, n, fn = row[3:6], row[6:9], abs(row[9])
            if b0 in hand[s] and b1 in obj_of:
                j, nn = obj_of[b1], n                                      # shape0 = hand: normal hand -> object
            elif b1 in hand[s] and b0 in obj_of:
                j, nn = obj_of[b0], -n
            else:
                continue
            Rs = Rot.from_quat(q[r, ob[j], 3:7]).as_matrix(); ps = q[r, ob[j], :3]
            loc = Rs.T @ (p - ps); nloc = Rs.T @ nn                         # into the simulated object's frame
            cand.append((fn, j, OR[f, j] @ loc + OP[f, j], OR[f, j] @ nloc))   # onto the reference object pose
        touched = {c[1] for c in cand}
        orig_active += int((I[f] > 0).any()); sim_active += int(bool(cand))
        if not cand:
            if all(good.values()) and (I[f] > 0).any():                  # not needed: every object is on its reference
                P2[f] = 0; N2[f] = 0; I2[f] = 0; cleared += 1
            continue
        if not all(good[j] for j in touched):
            kept_lost += 1; continue
        cand.sort(key=lambda c: -c[0]); cand = cand[:K]
        P2[f] = 0; N2[f] = 0; I2[f] = 0
        for k, (_, j, p, n) in enumerate(cand):
            P2[f, k] = p; N2[f, k] = n / max(np.linalg.norm(n), 1e-9); I2[f, k] = j + 1
        rep += 1
    new[s] = (P2, N2, I2)
    stats[s] = dict(frames=T, replaced=rep, cleared=cleared, kept_object_off_reference=kept_lost, orig_active_frames=orig_active,
                    sim_active_frames=sim_active, slots=K)
    print(s, json.dumps(stats[s]))
for s, (P2, N2, I2) in new.items():
    for k, v in ((f'mano_{s}_object_contact_positions', P2), (f'mano_{s}_object_contact_normals', N2),
                 (f'mano_{s}_object_contact_part_ids', I2)):
        t = t.set_column(t.column_names.index(k), k, pa.array([v.tolist()], type=t.schema.field(k).type))
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
pq.write_table(t, a.out)
json.dump(dict(ref=a.ref, trace=a.trace, **stats), open(a.out.replace('.parquet', '_sim_contacts.json'), 'w'), indent=1)
print('wrote', a.out)
