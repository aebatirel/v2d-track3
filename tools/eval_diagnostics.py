"""Usage: eval_diagnostics.py PACK_RUN_DIR OUT.json   (PACK_RUN_DIR = a pulled pack run: results/submission, refs, perc2)
Per-episode diagnostics of the submitted eval rollouts (no ground truth exists for eval episodes).
For every object: where the simulated object leaves our reference (the packed official rollout vs the reference columns
in the same parquet), relative to the grasp-lock hold windows; plus plausibility checks on the reference itself
(perception): unheld motion, sinking below its start height, tilt while unheld, frame-to-frame jumps."""
import glob, json, os, re, sys
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

B = sys.argv[1]
OUT = {}
eps = sorted(int(re.findall(r'episode_(\d+)\.parquet', f)[0]) for f in glob.glob(f'{B}/results/submission/results/episode_*.parquet'))
for ep in eps:
    d = pd.read_parquet(f'{B}/results/submission/results/episode_{ep:06d}.parquet')
    qa = json.load(open(f'{B}/results/submission/qa/ep{ep}/qa_policy.json'))
    gl = glob.glob(f'{B}/refs/glock/ep{ep}/processed/*/*/ref_gl_grasp_lock.json')
    phases = json.load(open(gl[0]))['phases'] if gl else []
    res = json.load(open(f'{B}/perc2/ep{ep}/result.json')) if os.path.exists(f'{B}/perc2/ep{ep}/result.json') else {}
    qref = json.load(open(f'{B}/refs/perc2mck/ep{ep}/qa_ref.json')) if os.path.exists(f'{B}/refs/perc2mck/ep{ep}/qa_ref.json') else {}
    mk = open(f'{B}/refs/perc2mck/ep{ep}/mkref_log.txt').read() if os.path.exists(f'{B}/refs/perc2mck/ep{ep}/mkref_log.txt') else ''
    rc = {}
    try: rc = json.load(open(f'{B}/results/glock_public/ep{ep}/rest_check.json'))
    except Exception: pass
    zs = open(f'{B}/results/glock_public/ep{ep}/zero_score.txt').read() if os.path.exists(f'{B}/results/glock_public/ep{ep}/zero_score.txt') else ''
    evo = []
    for f in sorted(glob.glob(f'{B}/results/glock_public/ep{ep}/evolve/phase*.json')):
        e = json.load(open(f)); g = e['generations']
        evo.append(dict(object=e['object'], side=e['side'], hold=e['hold'], unedited=g[0]['unedited'], best=round(e['best']['fit'], 3),
                        hold_add_cm=e['best'].get('detail', {}).get('hold_add_cm_median')))
    row = dict(ep=ep, sim_vs_ref=qa.get('sim_vs_ref'), floor=qa.get('floor_vs_ref'), det=res.get('det'),
               qa_ref_reasons=qref.get('reasons'), qa_ref_pass=qref.get('pass'),
               support_fallback=('support fallback' in mk), snap=re.findall(r'snap=per_object: z shifts \(cm\) (\{[^}]*\})', mk)[:1],
               zero_action=re.findall(r'zero_action: sim_vs_ref ([0-9.]+)', zs)[:1], rest_check=rc.get('objects'), evolve=evo, objects={})
    for name, g in d[d.get('environment_valid', True) == True].groupby('object_body_name') if 'environment_valid' in d else d.groupby('object_body_name'):
        g = g.sort_values('reference_frame'); fr = g['reference_frame'].values
        A = g[['achieved_position_x', 'achieved_position_y', 'achieved_position_z']].values
        Rf = g[['reference_position_x', 'reference_position_y', 'reference_position_z']].values
        Aq = g[['achieved_quaternion_x', 'achieved_quaternion_y', 'achieved_quaternion_z', 'achieved_quaternion_w']].values
        Rq = g[['reference_quaternion_x', 'reference_quaternion_y', 'reference_quaternion_z', 'reference_quaternion_w']].values
        e = np.linalg.norm(A - Rf, axis=1) * 100
        ang = np.degrees((R.from_quat(Aq) * R.from_quat(Rq).inv()).magnitude())
        obj = name.split('/')[0].replace('track3_', '') if '/' in name else name
        hold = [(p['start'], p['end'], p['hand']) for p in phases if p['object'] == obj]
        held = np.zeros(len(fr), bool)
        for s, e_, _ in hold: held |= (fr >= s) & (fr <= e_)
        lost = int(fr[np.argmax(e > 5)]) if (e > 5).any() else None
        where = None
        if lost is not None:
            if not hold or lost < min(h[0] for h in hold): where = 'before its first hold (start / knocked / unsupported)'
            elif held[np.argmax(e > 5)]: where = 'during a hold (grasp slip / drop / never acquired)'
            else: where = 'after a hold (placement / release / re-grasp gap)'
        # reference plausibility (perception): motion while unheld, sinking, tilt while unheld, jumps
        ref_travel = np.linalg.norm(Rf - Rf[0], axis=1) * 100
        step = np.r_[0, np.linalg.norm(np.diff(Rf, axis=0), axis=1) * 100]
        tilt = np.degrees((R.from_quat(Rq) * R.from_quat(Rq[0]).inv()).magnitude())
        unheld = ~held
        row['objects'][obj] = dict(
            held_frames=int(held.sum()), frames=len(fr), holds=hold,
            in3cm=round(float((e < 3).mean()), 3), mean_err_cm=round(float(e.mean()), 1), max_err_cm=round(float(e.max()), 1),
            final_err_cm=round(float(e[-1]), 1), mean_rot_err_deg=round(float(ang.mean()), 1),
            first_lost5cm_frame=lost, lost_where=where,
            ref_max_travel_cm=round(float(ref_travel.max()), 1),
            ref_unheld_travel_cm=round(float(ref_travel[unheld].max()), 1) if unheld.any() else 0.0,
            ref_min_dz_cm=round(float((Rf[:, 2] - Rf[0, 2]).min() * 100), 1),
            ref_max_tilt_unheld_deg=round(float(tilt[unheld].max()), 0) if unheld.any() else 0.0,
            ref_max_step_cm=round(float(step.max()), 1), ref_steps_over_3cm=int((step > 3).sum()))
    OUT[ep] = row
json.dump(OUT, open(sys.argv[2], 'w'), indent=1, default=str)
for ep, r in OUT.items():
    print(f"\n=== eval {ep}: sim_vs_ref {r['sim_vs_ref']} | det {r['det']} | qa_ref {r['qa_ref_reasons']} | fallback {r['support_fallback']} | zero {r['zero_action']}")
    for o, x in r['objects'].items():
        print(f"  {o:18s} in3cm {x['in3cm']:.2f} mean {x['mean_err_cm']:5.1f}cm final {x['final_err_cm']:5.1f}cm rot {x['mean_rot_err_deg']:5.1f}deg "
              f"held {x['held_frames']}/{x['frames']} lost@{x['first_lost5cm_frame']} [{x['lost_where']}] | REF: travel {x['ref_max_travel_cm']}cm "
              f"unheld-travel {x['ref_unheld_travel_cm']}cm minDz {x['ref_min_dz_cm']}cm unheld-tilt {x['ref_max_tilt_unheld_deg']}deg maxstep {x['ref_max_step_cm']}cm (>3cm x{x['ref_steps_over_3cm']})")
    for e in r['evolve']:
        print(f"  search {e['object']} ({e['side']}) hold {e['hold']}: zero-action {round(e['unedited'],3)} -> {e['best']} (hold ADD median {e['hold_add_cm']} cm)")
