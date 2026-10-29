import sys, pandas as pd
d = pd.read_csv(sys.argv[1]); obj = sys.argv[2]; f0, f1, st = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]); side = sys.argv[6]
d = d[(d.obj == obj) & (d.f >= f0) & (d.f <= f1) & (d.f % st == 0)]
cols = ['f', 'ref_lift_cm', 'sim_lift_cm', 'err_cm', 'err_deg', 'sim_disp_mm', 'sim_turn_deg', 'ref_disp_mm', f'{side}_min_mm', f'{side}_palm_mm', f'{side}_ncontact', f'{side}_contacts', f'{side}_ref_min_mm', f'{side}_ref_palm_mm', f'{side}_ref_contacts']
other = 'left' if side == 'right' else 'right'; cols += [f'{other}_min_mm']
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60); pd.set_option('display.max_rows', 500)
print(d[[c for c in cols if c in d.columns]].to_string(index=False))
