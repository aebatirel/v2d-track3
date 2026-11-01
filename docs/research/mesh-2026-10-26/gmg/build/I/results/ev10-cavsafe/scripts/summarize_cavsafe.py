"""ev10-cavsafe: one summary JSON + the README numbers table, from the run outputs (evalcheck ep<tag>_frames.json,
contacts_fixed <tag>.json, settle_trace <tag>.json, cavsafe_measure json). Gates as GATES.md.
Usage: python -I summarize_cavsafe.py RUN_DIR OUT.json   (RUN_DIR holds geo_<tag>/, contacts_<tag>.json,
       settle_<tag>.json, measure2.json (packed + v1), measure_v2.json (v2), measure_v3.json (v3), measure_v4.json, measure_v4f.json, measure_v4f_origcav.json (v4), measure_v5.json (v5))"""
import json, os, sys
import numpy as np

run, out = sys.argv[1:3]
TAGS = dict(packed='packed ev10', cand='v1 ev10cs (pre-registered)', cand2='v2 ev10cs2 (post hoc, A2)',
            cand3='v3 ev10cs3 (A3)', cand4='v4 with the 3 mm plate (A4, before F2; not delivered)',
            cand4f='v4 ev10cs4 (A4 with F2: 6 mm plate)', cand5='v5 ev10cs5 (A5: 8 mm plate, standby)')
REST = range(124, 161)
M1 = json.load(open(os.path.join(run, 'measure2.json')))
M2 = json.load(open(os.path.join(run, 'measure_v2.json')))
M3 = json.load(open(os.path.join(run, 'measure_v3.json')))
M4 = json.load(open(os.path.join(run, 'measure_v4.json')))
M4F = json.load(open(os.path.join(run, 'measure_v4f.json')))
M4FO = json.load(open(os.path.join(run, 'measure_v4f_origcav.json')))
M5 = json.load(open(os.path.join(run, 'measure_v5.json')))
res = dict(_note='ev10-cavsafe summary; gates per GATES.md; [M] plain MuJoCo 3.17.0 for contacts', sets={})
for tag, label in TAGS.items():
    fr = json.load(open(os.path.join(run, f'geo_{tag}', f'ep{tag}_frames.json')))
    pair, rows = fr['per_frame']['pair'], fr['per_frame']['rows']
    assert all(rows[f]['H0'] for f in REST)
    vp = np.array([pair[f]['V_packed'] for f in REST]); vf = np.array([pair[f]['V_faithful'] for f in REST])
    allp = np.array([p['V_packed'] for p in pair])
    objs = {o['name']: o for o in fr['summary']['objects']}
    ct = json.load(open(os.path.join(run, f'contacts_{tag}.json')))
    st = json.load(open(os.path.join(run, f'settle_{tag}.json')))
    me = dict(cand2=M2, cand3=M3, cand4=M4, cand4f=M4F, cand5=M5).get(tag, M1)['cand' if tag != 'packed' else 'packed']
    vol = {}
    for n, o in objs.items():
        u, vis, outv = o['packed_union_cm3'], o['vis_cm3'], o['packed_outside_visual_cm3']
        ref = json.load(open(os.path.join(run, 'geo_packed', 'eppacked_frames.json')))['summary']['objects']
        u10 = {x['name']: x['packed_union_cm3'] for x in ref}[n]
        vol[n] = dict(pieces=o['n_pieces'], union_cm3=u, visual_cm3=vis, visual_watertight=o['watertight'],
                      gate4a_union_over_visual=round(u / vis, 3), gate4a_pass=bool(u / vis >= 0.80),
                      r4b_kept_visual=round((u - outv) / vis, 3), r4c_union_over_ev10=round(u / u10, 3))
    g = ct['gate2']
    s = dict(label=label,
             gate1=dict(frames='f124-f160 (37, all H0)', median_cm3=round(float(np.median(vp)), 3),
                        min_cm3=round(float(vp.min()), 3), max_cm3=round(float(vp.max()), 3),
                        argmax_frame=124 + int(vp.argmax()),
                        pass_=bool(np.median(vp) <= 1.0 and vp.max() <= 3.0),
                        faithful_floor_median_cm3=round(float(np.median(vf)), 2), faithful_floor_max_cm3=round(float(vf.max()), 2),
                        all_frames_max_cm3=round(float(allp.max()), 2), all_frames_argmax=int(allp.argmax()),
                        frames_with_overlap_all=int((allp > 0).sum())),
             gate2=dict(g, per_frame=[dict(frame=a['frame'], role=a['role'], max_nefc=a['max_nefc'], max_ncon=a['max_ncon'],
                                           nefc_step0_max=a['nefc0_max'], overflow_copies=a['overflow_copies'],
                                           classes_at_max_nefc=a['classes_at_max_nefc']) for a in ct['frames']]),
             gate3=dict(depth_mm=me['receiver']['cavity_depth_max_mm'],
                        depth_radial_wall_mm=me['receiver']['depth_radial_wall_pieces_max_mm'],
                        intrusion_cm3=me['receiver']['cavity_intrusion_cm3'],
                        pieces_intruding=me['receiver']['pieces_intruding'], pass_=me['receiver']['gate3_pass']),
             gate4=vol, guest=me['guest'],
             settle=[dict(frame=x['frame'], max=x['max'], nefc_step0=x['nefc_step0'],
                          nefc_last_0p5s_median=x['nefc_last_0p5s_median'],
                          guest_rel_disp_end_mm=x['guest_rel_disp_end_mm'],
                          receiver_tilt_end_deg=x['receiver_tilt_end_deg'], guest_table_max=x.get('guest_table_max'),
                          guest_table_steps=x.get('guest_table_steps')) for x in st['frames']],
             drop_check_copies=[dict(frame=a['frame'], copies_with_guest_table_at_max=int(sum(
                 1 for r in a['per_copy'] if (r['classes_at_max_nefc'] or {}).get('guest_table', 0) > 0)))
                 for a in ct['frames']])
    if tag == 'cand4f':
        s['gate3_original_cavity'] = M4FO['cand']['receiver']
    res['sets'][tag] = s
fl = M1['floor']['frames']
R = [x for x in fl if x['frame'] in REST]
res['floor_f124_160_median_cm3'] = {k: round(float(np.median([x[k] for x in R])), 2) for k in
                                    ('V_visual', 'V_visual_in_cavity', 'V_visual_outside_cavity', 'V_design_floor')}
res['floor_f124_160_range_cm3'] = {k: [round(float(min(x[k] for x in R)), 2), round(float(max(x[k] for x in R)), 2)]
                                   for k in ('V_visual', 'V_visual_in_cavity', 'V_visual_outside_cavity', 'V_design_floor')}
json.dump(res, open(out, 'w'), indent=1, default=float)
for tag, s in res['sets'].items():
    print(tag, 'g1', s['gate1']['median_cm3'], s['gate1']['max_cm3'], s['gate1']['pass_'], '| g2', s['gate2']['max_nefc'],
          s['gate2']['max_ncon'], s['gate2']['overflow_copies'], s['gate2']['pass'], '| g3', s['gate3']['depth_mm'],
          s['gate3']['intrusion_cm3'], s['gate3']['pass_'], '| g4a', {n: v['gate4a_union_over_visual'] for n, v in s['gate4'].items()},
          '| 4b', {n: v['r4b_kept_visual'] for n, v in s['gate4'].items()}, '| 4c', {n: v['r4c_union_over_ev10'] for n, v in s['gate4'].items()})
    for a in s['gate2']['per_frame']:
        print('   ', a)
    for x in s['settle']:
        print('    settle', x)
print(res['floor_f124_160_median_cm3'], res['floor_f124_160_range_cm3'])
