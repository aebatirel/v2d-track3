"""Pack 3 -> pack 4: did the REFERENCE (our object path the policy tracks) change in the 7 changed eval episodes?
If it did, dS mixes a policy gain with a target change, and dLB / dS is not a pure 'transfer of an S gain'.
Reads only our own packed eval rollouts (sim + our reference); no ground truth exists or is read for eval episodes.
Also recomputes each packed rollout's S with myscore.sim_vs_ref and compares it with summary.txt."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pyarrow.parquet as pq
import myscore as M

ST = f'{M.SP}/work/verify_mapping/store/runs'
PK = {'p3': '20261025-pack3-3758189', 'p4': '20261026-pack4-f7a49a9'}
SUM = {'p3': '20261025-track3c', 'p4': '20261026-track3d'}


def load(run, e):
    p = f'{ST}/{run}/results/submission/qa/ep{e}/episode_{e:06d}.parquet'
    df = pq.read_table(p).to_pandas()
    names = [str(x) for x in df.drop_duplicates('object_body_id').sort_values('object_body_id').object_body_name]
    fr, sim, ref, md, _ = M.read_rollout(p, names)
    return names, fr, sim, ref, md


out = {}
summ = {k: {int(a): b for a, b in json.loads(re.search(r'\{.*\}', open(f'{M.REPO}/results/submissions/{v}/summary.txt').read()).group(0)).items()}
        for k, v in SUM.items()}
for e in range(1, 40):
    if not os.path.exists(f'{ST}/{PK["p3"]}/results/submission/qa/ep{e}'):
        continue
    n3, f3, s3, r3, m3 = load(PK['p3'], e); n4, f4, s4, r4, m4 = load(PK['p4'], e)
    o = dict(names=n3, frames=[len(f3), len(f4)], S3=M.sim_vs_ref(s3, r3), S4=M.sim_vs_ref(s4, r4),
             S3_summary=summ['p3'][e], S4_summary=summ['p4'][e],
             same_sim=bool(s3.shape == s4.shape and np.allclose(s3, s4)),
             ref_parquet=[m3.get('flash_chord.reference_parquet', '')[-90:], m4.get('flash_chord.reference_parquet', '')[-90:]],
             ck=[m3.get('flash_chord.checkpoint_sha256', '')[:12], m4.get('flash_chord.checkpoint_sha256', '')[:12]])
    if r3.shape == r4.shape:
        d = np.linalg.norm(r3[..., :3] - r4[..., :3], axis=-1)
        ang = np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(r3[..., 3:] * r4[..., 3:], -1)), 0, 1)))
        o.update(ref_identical=bool(np.allclose(r3, r4, atol=1e-6)), ref_dpos_cm_max=round(float(d.max() * 100), 2),
                 ref_dpos_cm_mean=round(float(d.mean() * 100), 2), ref_dang_deg_max=round(float(ang.max()), 1))
        # cross-scores: pack-4 sim against pack-3 reference and vice versa (same yardstick)
        o['S4_vs_ref3'] = M.sim_vs_ref(s4, r3); o['S3_vs_ref4'] = M.sim_vs_ref(s3, r4)
    else:
        o['ref_identical'] = False; o['note'] = f'shape {r3.shape} vs {r4.shape}'
    out[e] = o
    print(e, {k: v for k, v in o.items() if k not in ('ref_parquet',)}, flush=True)
ch = [e for e, o in out.items() if not o['same_sim']]
res = dict(per_episode=out, changed=ch,
           sum_dS_summary=round(sum(out[e]['S4_summary'] - out[e]['S3_summary'] for e in ch), 4),
           sum_dS_own=round(sum(out[e]['S4'] - out[e]['S3'] for e in ch), 4),
           changed_with_new_reference=[e for e in ch if not out[e]['ref_identical']],
           sum_dS_same_yardstick_ref3=round(sum(out[e].get('S4_vs_ref3', np.nan) - out[e]['S3'] for e in ch), 4),
           sum_dS_same_yardstick_ref4=round(sum(out[e]['S4'] - out[e].get('S3_vs_ref4', np.nan) for e in ch), 4))
dlb = 0.81056 - 0.78893
res['dLB'] = round(dlb, 5)
res['transfer_summary'] = round(dlb / (res['sum_dS_summary'] / 20), 4)
res['transfer_same_yardstick_ref3'] = round(dlb / (res['sum_dS_same_yardstick_ref3'] / 20), 4)
res['transfer_same_yardstick_ref4'] = round(dlb / (res['sum_dS_same_yardstick_ref4'] / 20), 4)
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack_refs.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'per_episode'}, indent=1))
