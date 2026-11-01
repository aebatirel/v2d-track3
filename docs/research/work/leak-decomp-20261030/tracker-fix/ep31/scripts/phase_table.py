import json, numpy as np
d = np.load('diag31_arrays.npz'); j = json.load(open('diag31.json'))
TH = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8
auc = lambda e: float(np.mean((e[:, None] < TH[None]).astype(float) @ TW))
PH = [('A rest in rack, hands away', 0, 19), ('B rest, hands arrive (L on rack ~f20)', 20, 26), ('C grasp/closing', 27, 44), ('D lift', 45, 61),
      ('E scrub strokes among fins', 62, 184), ('F 2nd lift + carry', 185, 234), ('G put back standing, settle', 235, 245), ('H end rest in rack', 246, 289)]
gap = d['gap']; hs = d['hand_mini_sweeper']; hr = d['hand_plastic_dish_rack']; inb = d['inbox']
rows = []
for name, a, b in PH:
    sl = slice(a, b + 1)
    r = dict(phase=name, frames=f'{a}-{b}', hand_sweeper_cm=round(float(np.nanmedian(hs[sl])), 1), hand_rack_cm=round(float(np.nanmedian(hr[sl])), 1),
             gap_cm=round(float(np.median(gap[sl])), 2), in_rack_bbox=round(float(np.median(inb[sl])), 2))
    for arm in ('Po', 'Po2', 'Ps'):
        for k in ('kit', 'bw'):
            for n, tag in (('mini_sweeper', 'sw'), ('plastic_dish_rack', 'rk')):
                e = d[f'{arm}_{k}_{n}_add'][sl]; rot = d[f'{arm}_{k}_{n}_rot'][sl]
                r[f'{arm}_{k}_{tag}'] = f'{np.median(e)*100:.2f}/{np.median(rot):.1f}/{auc(e):.3f}'
    rows.append(r)
json.dump(rows, open('phase_table.json', 'w'), indent=1)
for r in rows:
    print(r['phase'], r['frames'], 'hand sw/rk', r['hand_sweeper_cm'], r['hand_rack_cm'], 'gap', r['gap_cm'], 'inbox', r['in_rack_bbox'])
    for arm in ('Po', 'Po2', 'Ps'):
        print('   ', arm, 'kit sw', r[f'{arm}_kit_sw'], 'rk', r[f'{arm}_kit_rk'], '| bw sw', r[f'{arm}_bw_sw'], 'rk', r[f'{arm}_bw_rk'])
