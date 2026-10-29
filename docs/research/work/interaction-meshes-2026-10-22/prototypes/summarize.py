"""Overview table of the census (census/ep*_summary.json) -> census/overview.csv + printed lines."""
import json, glob, csv, os
OUT = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/census'
rows = []
for p in sorted(glob.glob(f'{OUT}/ep*_summary.json'), key=lambda s: int(os.path.basename(s)[2:].split('_')[0])):
    s = json.load(open(p))
    for var, v in s['variants'].items():
        rA, rB = v['region_A'], v['region_B']
        d = v.get('diag_vs_scan', {})
        def ex(tag, k):
            x = d.get(tag, {}).get(k)
            return None if not x else round(x['frac_outside_gt3mm'], 2)
        def far(tag, k):
            x = d.get(tag, {}).get(k)
            return None if not x else round(x['frac_far_gt3mm_any_sign'], 2)
        r = dict(ep=s['ep'], pair='+'.join(s['names']), var=var, frames=s['frames'],
                 moving_A=s['moving_frames'][s['names'][0]], moving_B=s['moving_frames'][s['names'][1]],
                 contact_lt5mm=v['frames_contact_lt5mm'], ov_gt0=v['frames_overlap_gt0'], ov_gt1=v['frames_overlap_gt1cm3'],
                 ov_gt5=v['frames_overlap_gt5cm3'], max_ov=round(v['max_overlap_cm3'], 2), max_ov_f=v['max_overlap_frame'],
                 ov_p50=None if not v['overlap_p50_p90'] else round(v['overlap_p50_p90'][0], 2),
                 max_pen_mm=round(v['max_pen_mm'], 1), pen_p50_mm=None if v['pen_p50_in_overlap_frames_mm'] is None else round(v['pen_p50_in_overlap_frames_mm'], 1),
                 ov_static=v['overlap_frames_both_static'], ov_moving=v['overlap_frames_moving'],
                 jit_all_mm=round(v['rel_jitter_mm_p50_all'], 2),
                 jit_ov_mm=None if v['rel_jitter_mm_p50_overlap'] is None else round(v['rel_jitter_mm_p50_overlap'], 2),
                 relspread_mm=None if not v['rel_pose_spread_in_overlap'] else round(v['rel_pose_spread_in_overlap']['trans_std_mm'], 1),
                 relrot_deg=None if not v['rel_pose_spread_in_overlap'] else round(v['rel_pose_spread_in_overlap']['rot_max_deg'], 1),
                 A_core50=rA.get('core50_cm3'), A_union=rA.get('union_cm3'), A_pers=rA.get('persistence'), A_jac=rA.get('jaccard'),
                 A_cjit_cm=rA.get('centroid_std_cm'), A_core_ext_cm=rA.get('core_extent_cm'), A_core_c_cm=rA.get('core_centroid_cm'),
                 A_core_rel=rA.get('core_rel_pos'),
                 B_core50=rB.get('core50_cm3'), B_union=rB.get('union_cm3'), B_pers=rB.get('persistence'), B_jac=rB.get('jaccard'),
                 B_cjit_cm=rB.get('centroid_std_cm'), B_core_ext_cm=rB.get('core_extent_cm'), B_core_c_cm=rB.get('core_centroid_cm'),
                 B_core_rel=rB.get('core_rel_pos'),
                 diagA_core_out3=ex('A', 'core50'), diagA_core_far3=far('A', 'core50'), diagA_mesh_out3=ex('A', 'whole_mesh'),
                 diagB_core_out3=ex('B', 'core50'), diagB_core_far3=far('B', 'core50'), diagB_mesh_out3=ex('B', 'whole_mesh'),
                 segs=v['overlap_segments'][:8])
        for k, x in list(r.items()):
            if isinstance(x, float):
                r[k] = round(x, 2)
        rows.append(r)
with open(f'{OUT}/overview.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r)
