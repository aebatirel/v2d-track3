"""Merge solver windows into a training reference and build the reset-state bank (2026-10-31; solver<->RL loop,
docs/research/physics-2026-10-30/physics-solver.md section 6.1). No ground truth.

Inputs:
  BASE.parquet     the reference the policy trained on (its targets are what the policy's residual is added to);
  --seg S.parquet  one or more tools/physics_solve/solve.py outputs, each solved on BASE from a recorded state
                   (--start_state, --record), with S_solve.npz next to it (offsets, the solver's committed trajectory with
                   full states jq/jqd and contacts cl);
  --trace P.npz    the policy rollout the windows came from (tools/trace_rollout.py policy, STATE=1).
What enters training (written to OUT.parquet and --bank):
  1. targets: in each window [t0, last solved frame] the wrist pose and finger targets are the solver's; after the
     window they return to BASE over --blend frames (the last offset scaled down linearly: position and fingers
     additively, rotation along its rotation vector; fingers kept inside the range of values BASE and the segment
     already use, so FlashCHORD's joint-limit check cannot fail). robot_<side>_frames (the RL hand-tracking target)
     and the object reference stay unchanged;
  2. --contacts: the contact targets of the window frames are replaced by the solver's simulated contacts
     (tools/sim_contacts.py on the segment's trajectory: frames outside the window keep theirs);
  3. reset-state bank (for ops/box/patch_flashchord_states.py): the policy's own states from each window start to
     its failure onset (every --every frames) and the solver's states along the window (every --every frames, only
     where every object is within --bank_cm ADD of its reference: states of a plan that holds, not of one that lost it):
     jq (K, per-world joint_q), jqd (K, per-world joint_qd), frame (K,), src (K,: 0 = policy, 1 = solver), appended
     to --bank_in if given.
Usage: merge_ref.py BASE.parquet OUT.parquet --seg S1.parquet [S2.parquet] [--trace P.npz --windows W.json]
       [--bank B.npz] [--bank_in OLD.npz] [--blend 6] [--every 5] [--contacts]
"""
import argparse, json, os, subprocess, sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

SIDES = ('right', 'left')


def cols(t, s):
    T = len(t.column('robot_left_wrist_position')[0].as_py())
    g = lambda c: np.array(t.column(c)[0].as_py(), float)  # noqa: E731
    return (g(f'robot_{s}_wrist_position').reshape(T, 3), g(f'robot_{s}_wrist_wxyz').reshape(T, 4),
            g(f'robot_{s}_finger_joints').reshape(T, -1))


def main():
    p = argparse.ArgumentParser(); p.add_argument('base'); p.add_argument('out')
    p.add_argument('--seg', nargs='+', required=True); p.add_argument('--trace', default='')
    p.add_argument('--windows', default='', help='failures.py JSON (onsets, for the policy states of the bank)')
    p.add_argument('--bank', default=''); p.add_argument('--bank_in', default='')
    p.add_argument('--blend', type=int, default=6); p.add_argument('--every', type=int, default=5)
    p.add_argument('--contacts', action='store_true'); p.add_argument('--bank_cm', type=float, default=3.0)
    a = p.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import solve as S
    ref = S.Ref(a.base); pts = S.sphere_points(500)
    t = pq.read_table(a.base); T = len(t.column('robot_left_wrist_position')[0].as_py())
    base = {s: cols(t, s) for s in SIDES}; cur = {s: [x.copy() for x in base[s]] for s in SIDES}
    log = dict(base=os.path.abspath(a.base), segments=[])
    bank = dict(jq=[], jqd=[], frame=[], src=[])
    for sp in a.seg:
        st = pq.read_table(sp); seg = {s: cols(st, s) for s in SIDES}
        z = np.load(os.path.splitext(sp)[0] + '_solve.npz'); off = z['offsets']; t0 = int(z['t0'])
        fr = [int(x) for x in z['frame']]; t1 = fr[-1] - 1            # last frame whose targets were committed
        nz = np.where(np.any(off != 0, axis=1))[0]
        row = dict(seg=os.path.abspath(sp), t0=t0, last=t1, edited_frames=int(len(nz)))
        if len(nz):
            w = slice(t0, t1 + 1)
            for s in SIDES:
                P0, Q0, F0 = base[s]; P1, Q1, F1 = seg[s]
                cur[s][0][w], cur[s][1][w], cur[s][2][w] = P1[w], Q1[w], F1[w]
                e = t1                                                  # ramp the last offset out after the window
                dp = P1[e] - P0[e]; df = F1[e] - F0[e]
                dr = (Rot.from_quat(Q0[e][[1, 2, 3, 0]]).inv() * Rot.from_quat(Q1[e][[1, 2, 3, 0]])).as_rotvec()
                lo = np.minimum(F0.min(0), F1.min(0)); hi = np.maximum(F0.max(0), F1.max(0))
                for k in range(a.blend):
                    f = e + 1 + k
                    if f >= T:
                        break
                    c = 1.0 - (k + 1) / (a.blend + 1)
                    cur[s][0][f] = P0[f] + c * dp
                    q = (Rot.from_quat(Q0[f][[1, 2, 3, 0]]) * Rot.from_rotvec(c * dr)).as_quat()
                    q = q if np.dot(q, Q0[f][[1, 2, 3, 0]]) >= 0 else -q
                    cur[s][1][f] = q[[3, 0, 1, 2]]
                    cur[s][2][f] = np.clip(F0[f] + c * df, lo, hi)
            row['window'] = [t0, t1]
        if 'jq' in z.files:                                             # solver states along the window, where it holds
            L = [str(x) for x in z['labels']]; ob = [next(i for i, l in enumerate(L) if l.startswith(f'track3_{nm}/')) for nm in ref.names]
            kept = 0
            for i in range(0, len(fr), a.every):
                if fr[i] < T - 1:
                    add = S.add_dist(z['q'][i][ob].astype(np.float64), ref.OP[fr[i]], ref.OQ[fr[i]], pts)
                    if add.max() <= a.bank_cm / 100:
                        bank['jq'].append(z['jq'][i]); bank['jqd'].append(z['jqd'][i]); bank['frame'].append(fr[i]); bank['src'].append(1); kept += 1
            row['solver_states_banked'] = kept
        log['segments'].append(row)
    if a.trace:                                                         # the policy's states before each failure
        d = np.load(a.trace); fr = [int(x) for x in d['frame']]
        n = next((i for i in range(1, len(fr)) if fr[i] <= fr[i - 1]), len(fr))
        wins = json.load(open(a.windows))['windows'] if a.windows else [dict(start=int(np.load(os.path.splitext(sp)[0] + '_solve.npz')['t0']), onset=None) for sp in a.seg]
        for w in wins:
            on = w.get('onset') or w['start'] + a.every
            for f in range(int(w['start']), int(on) + 1, a.every):
                if f in fr[:n] and 'jq' in d.files:
                    i = fr.index(f); bank['jq'].append(d['jq'][i]); bank['jqd'].append(d['jqd'][i]); bank['frame'].append(f); bank['src'].append(0)
    out = t
    for s in SIDES:
        for c, v in zip((f'robot_{s}_wrist_position', f'robot_{s}_wrist_wxyz', f'robot_{s}_finger_joints'), cur[s]):
            out = out.set_column(out.column_names.index(c), c, pa.array([v.tolist()], type=out.schema.field(c).type))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    pq.write_table(out, a.out)
    if a.contacts:                                                      # solver contacts on the window frames
        for sp in a.seg:
            zp = os.path.splitext(sp)[0] + '_solve.npz'
            if 'cl' in np.load(zp).files:
                r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sim_contacts.py'),
                                    a.out, zp, a.out], capture_output=True, text=True)
                log.setdefault('contacts', []).append(r.stdout.strip().splitlines()[:2] if r.returncode == 0 else 'FAILED: ' + r.stderr[-300:])
    if a.bank:
        if a.bank_in and os.path.exists(a.bank_in):
            old = np.load(a.bank_in)
            for k in bank:
                bank[k] = list(old[k]) + bank[k]
        if bank['jq']:
            np.savez_compressed(a.bank, jq=np.array(bank['jq'], np.float32), jqd=np.array(bank['jqd'], np.float32),
                                frame=np.array(bank['frame'], np.int32), src=np.array(bank['src'], np.int32))
        log['bank'] = dict(path=os.path.abspath(a.bank), states=len(bank['jq']), policy=int(sum(1 for x in bank['src'] if x == 0)),
                           solver=int(sum(1 for x in bank['src'] if x == 1)))
    json.dump(log, open(os.path.splitext(a.out)[0] + '_merge.json', 'w'), indent=1)
    print(json.dumps(log)[:800])


if __name__ == '__main__':
    main()
