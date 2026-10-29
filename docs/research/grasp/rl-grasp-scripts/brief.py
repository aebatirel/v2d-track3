import sys, json
for l in sys.stdin:
    r = json.loads(l)
    print(r['win'], 'lift', r['lift_cm'], r['max_lift'], 'low', r['low_mm'], 'ontab', r['frac_on_table'], r['low_region'], 'tilt', r['tilt'], 'turn', r['turn'], 'slide', r['slide_mm'], 'oo', r['oo_min_mm'],
          '| links', r['links'], 'thumb', r['thumb'], 'palm', r['palm'], 'fing', '/'.join(str(v) for v in r['fingers'].values()), 'faces', r['faces'], 'reg', r['regions'])
    print('   top', r['top_links'], 'onlink', r['on_link'])
    print('   palm.plate', r['palm_dot_plate'], 'palm_z', r['palm_normal_z'], 'fd.long', r['fingerdir_dot_long'], 'opp', r['opp_frac'], r['opp_dot_plate'], r['opp_len_cm'], r['opp_palm_nfr'], 'flex', r['flex'], 'thumb', r['thumb_j'])
