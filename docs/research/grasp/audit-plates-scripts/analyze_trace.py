"""Per-hold-phase audit of a full-body trace (zero-action replay or policy trace) against our grasp-lock reference.
Usage: analyze_trace.py REF.parquet GRASP_LOCK.json TRACE.npz OUT_PREFIX [--label L] [--every 1]
Writes OUT_PREFIX.json (phase summaries, events) and OUT_PREFIX_frames.csv (per frame and object).
Distances: hand collision samples (URDF hulls) to the object's CoACD pieces (our library_v3 mesh), signed (- inside).
Contact proxy: a link with min distance <= CONTACT_MM. Our reference and simulator traces only (no ground truth)."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial.transform import Rotation as R
from audit_lib import (HullSDF, hand_points, load_ref, load_trace, link_dists, rot_deg, to_obj)

CONTACT_MM = 3.0
p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('gl'); p.add_argument('trace'); p.add_argument('out')
p.add_argument('--label', default=''); p.add_argument('--every', type=int, default=1); p.add_argument('--refcontacts', type=int, default=1)
a = p.parse_args()
ref = load_ref(a.ref); tr = load_trace(a.trace); gl = json.load(open(a.gl)); T = min(ref['T'], tr['T'])
names = ref['names']; hp = {s: hand_points(s) for s in ('left', 'right')}; sdf = {n: HullSDF(n) for n in names}
SHORT = lambda ln: ln.split('_', 1)[1].replace('hand_C_MC', 'palm')  # noqa: E731


def frame_metrics(f, src):
    """src 'sim' or 'ref': per object, per side: link distances."""
    out = {}
    for j, n in enumerate(names):
        op = tr['obj'][n][f] if src == 'sim' else ref['obj'][f, j]
        lp = tr['links'] if src == 'sim' else ref['links']
        lpf = {k: v[f] for k, v in lp.items()}
        out[n] = {s: link_dists(lpf, hp[s], op, sdf[n], side=s) for s in ('left', 'right')}
    return out


rows = []; per = {}
frames = list(range(0, T, a.every))
for f in frames:
    ms = frame_metrics(f, 'sim'); mr = frame_metrics(f, 'ref') if a.refcontacts else None
    for j, n in enumerate(names):
        so = tr['obj'][n][f]; ro = ref['obj'][f, j]; s0 = tr['obj'][n][0]; r0 = ref['obj'][0, j]
        row = dict(f=f, obj=n, ref_lift_cm=100 * (ro[2] - r0[2]), sim_lift_cm=100 * (so[2] - s0[2]),
                   err_cm=100 * np.linalg.norm(so[:3] - ro[:3]), err_deg=rot_deg(so[3:], ro[3:]),
                   sim_disp_mm=1000 * np.linalg.norm(so[:3] - s0[:3]), sim_turn_deg=rot_deg(so[3:], s0[3:]),
                   ref_disp_mm=1000 * np.linalg.norm(ro[:3] - r0[:3]))
        for s in ('left', 'right'):
            d = ms[n][s]; row[f'{s}_min_mm'] = 1000 * min(d.values())
            row[f'{s}_contacts'] = '+'.join(SHORT(k) for k, v in sorted(d.items(), key=lambda kv: kv[1]) if 1000 * v <= CONTACT_MM)
            row[f'{s}_ncontact'] = sum(1 for v in d.values() if 1000 * v <= CONTACT_MM)
            row[f'{s}_palm_mm'] = 1000 * d[f'{s}_hand_C_MC']
            if mr is not None:
                dr = mr[n][s]; row[f'{s}_ref_contacts'] = '+'.join(SHORT(k) for k, v in sorted(dr.items(), key=lambda kv: kv[1]) if 1000 * v <= CONTACT_MM)
                row[f'{s}_ref_ncontact'] = sum(1 for v in dr.values() if 1000 * v <= CONTACT_MM)
                row[f'{s}_ref_min_mm'] = 1000 * min(dr.values())
                row[f'{s}_ref_palm_mm'] = 1000 * dr[f'{s}_hand_C_MC']
        rows.append(row)

import csv
keys = list(rows[0].keys())
with open(a.out + '_frames.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})

# phase summaries
byobj = {n: [r for r in rows if r['obj'] == n] for n in names}
summ = dict(label=a.label, trace=a.trace, phases=[], events={})
for n in names:
    R_ = byobj[n]
    dep = next((r['f'] for r in R_ if r['sim_disp_mm'] > 5 or r['sim_turn_deg'] > 3), None)
    e3 = next((r['f'] for r in R_ if r['err_cm'] > 3), None); e10 = next((r['f'] for r in R_ if r['err_cm'] > 10), None)
    summ['events'][n] = dict(first_departure_from_sim_rest_f=dep, first_err_gt3cm_f=e3, first_err_gt10cm_f=e10,
                             mean_err_cm=round(float(np.mean([r['err_cm'] for r in R_])), 2),
                             frac_within_3cm=round(float(np.mean([r['err_cm'] <= 3 for r in R_])), 3),
                             max_sim_lift_cm=round(float(max(r['sim_lift_cm'] for r in R_)), 1),
                             max_ref_lift_cm=round(float(max(r['ref_lift_cm'] for r in R_)), 1))
    if dep is not None:
        r = next(r for r in R_ if r['f'] == dep)
        summ['events'][n]['at_departure'] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()}
for ph in gl['phases']:
    side, n = ph['hand'], ph['object']; o = 'left' if side == 'left' else 'right'
    h0, s1 = ph['hold_from'], ph['end']; a0 = (ph.get('approach') or {}).get('from_frame', max(0, h0 - 8))
    hc = h0 + gl['args']['close']; mv = ph['move_frame']; R_ = {r['f']: r for r in byobj[n]}
    fr = [f for f in frames if a0 <= f < min(T, s1 + 24)]
    # slip: object pose in the holder's palm (C_MC) frame vs at closure
    pal = tr['links'][f'{side}_hand_C_MC']; ob = tr['obj'][n]

    def rel(f):
        Rp = R.from_quat(pal[f, 3:7]); return Rp.inv().apply(ob[f, :3] - pal[f, :3]), (Rp.inv() * R.from_quat(ob[f, 3:7]))
    pc, rc = rel(min(hc, T - 1))
    slip = {f: (100 * np.linalg.norm(rel(f)[0] - pc), float(np.degrees((rel(f)[1] * rc.inv()).magnitude()))) for f in range(min(hc, T - 1), min(s1, T))}
    carry = [f for f in range(mv, min(s1, T)) if f in R_]
    lifted = [f for f in carry if R_[f]['ref_lift_cm'] > 2]
    best_ref = max(carry, key=lambda f: R_[f]['ref_lift_cm']) if carry else None
    nc = [R_[f][f'{side}_ncontact'] for f in range(hc, min(s1, T)) if f in R_]
    rnc = [R_[f].get(f'{side}_ref_ncontact', 0) for f in range(hc, min(s1, T)) if f in R_]
    from collections import Counter
    cnt = Counter(); rcnt = Counter(); nn = 0
    for f in range(hc, min(s1, T)):
        if f in R_:
            nn += 1
            for c in filter(None, R_[f][f'{side}_contacts'].split('+')):
                cnt[c] += 1
            for c in filter(None, R_[f].get(f'{side}_ref_contacts', '').split('+')):
                rcnt[c] += 1
    s = dict(hand=side, object=n, approach_from=a0, hold_from=h0, closed_at=hc, ref_move=mv, end=s1,
             grasp_frame=ph['grasp_frame'], grasp_type='wrap' if ph.get('wrap') else 'snapped human grasp',
             sim_at_hold_from=dict(err_cm=round(R_[h0]['err_cm'], 1), disp_mm=round(R_[h0]['sim_disp_mm'], 1), turn_deg=round(R_[h0]['sim_turn_deg'], 1)) if h0 in R_ else None,
             sim_at_closed=dict(err_cm=round(R_[hc]['err_cm'], 1), disp_mm=round(R_[hc]['sim_disp_mm'], 1), turn_deg=round(R_[hc]['sim_turn_deg'], 1),
                                contacts=R_[hc][f'{side}_contacts'], palm_mm=round(R_[hc][f'{side}_palm_mm'], 1),
                                ref_contacts=R_[hc].get(f'{side}_ref_contacts'), ref_palm_mm=round(R_[hc].get(f'{side}_ref_palm_mm', np.nan), 1)) if hc in R_ else None,
             ref_peak_lift=dict(frame=best_ref, ref_lift_cm=round(R_[best_ref]['ref_lift_cm'], 1), sim_lift_cm=round(R_[best_ref]['sim_lift_cm'], 1),
                                err_cm=round(R_[best_ref]['err_cm'], 1)) if best_ref is not None else None,
             max_sim_lift_in_phase_cm=round(max((R_[f]['sim_lift_cm'] for f in carry), default=np.nan), 1),
             frames_ref_lifted_gt2cm=len(lifted), frames_sim_lifted_gt2cm=sum(1 for f in lifted if R_[f]['sim_lift_cm'] > 2),
             frac_err_le3cm_in_phase=round(float(np.mean([R_[f]['err_cm'] <= 3 for f in range(h0, min(s1, T)) if f in R_])), 3),
             mean_contacts_while_held=round(float(np.mean(nc)), 2) if nc else None, mean_ref_contacts_while_held=round(float(np.mean(rnc)), 2) if rnc else None,
             contact_share_sim={k: round(v / max(1, nn), 2) for k, v in cnt.most_common(12)},
             contact_share_ref={k: round(v / max(1, nn), 2) for k, v in rcnt.most_common(12)},
             slip_cm_p50_max=[round(float(np.median([v[0] for v in slip.values()])), 1), round(float(max(v[0] for v in slip.values())), 1)] if slip else None,
             slip_deg_p50_max=[round(float(np.median([v[1] for v in slip.values()])), 1), round(float(max(v[1] for v in slip.values())), 1)] if slip else None,
             first_slip_gt2cm_f=next((f for f in sorted(slip) if slip[f][0] > 2), None))
    summ['phases'].append(s)
json.dump(summ, open(a.out + '.json', 'w'), indent=1, default=float)
print(json.dumps(summ, indent=1, default=float))
