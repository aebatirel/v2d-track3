# DIAGNOSTIC (slot box from the public scan, boards_slot.json): what our fused evidence says inside the real slot
# versus a control box of real material (mirrored y). Grid: obsfuse2 output.
import sys, json, numpy as np
S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
SL = json.load(open(f'{S}/interact/defects/boards_slot.json'))
for g in sys.argv[1:]:
    n = 'wooden_piece_1' if 'piece_1' in g else 'wooden_piece_2'; s = SL[n]
    z = np.load(g); sh = tuple(z['shape']); lo = z['lo']; vx = float(z['voxel'])
    ax = [lo[k] + (np.arange(sh[k]) + 0.5) * vx for k in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing='ij')
    def box(sgn):
        y0, y1 = s['slot_y_range_cm'][0] / 100 + 0.004, s['slot_y_range_cm'][1] / 100 - 0.004
        yy = Y if sgn > 0 else -Y
        return ((X >= s['plate_x_range_cm'][0] / 100) & (X <= s['plate_x_range_cm'][1] / 100) & (yy >= y0) & (yy <= y1) &
                (Z >= s['slot_z_range_cm'][0] / 100 + 0.001) & (Z <= s['slot_z_range_cm'][1] / 100 - 0.001))
    out = {}
    for nm, B in (('slot', box(1)), ('control', box(-1))):
        r = {'vox': int(B.sum())}
        for t in (12, 6, 4):
            W = z[f'W{t}'][B]; m = np.where(W > 0, z[f'S{t}'][B] / np.maximum(W, 1), 0)
            r[f'known{t}'] = round(float((W >= 3).mean()), 2); r[f'inside{t}'] = round(float(((W >= 3) & (m < 0)).mean()), 2)
            r[f'mean{t}_med'] = round(float(np.median(m[W >= 3])), 2) if (W >= 3).any() else None
        r['NF3>=1'] = round(float((z['NF3'][B] >= 1).mean()), 2); r['NF3>=2'] = round(float((z['NF3'][B] >= 2).mean()), 2)
        r['NF3_med'] = float(np.median(z['NF3'][B])); r['NFL3_share'] = round(float(z['NFL3'][B].sum() / max(z['NF3'][B].sum(), 1)), 2)
        r['NV_med'] = float(np.median(z['NV'][B]))
        out[nm] = r
    print(g.split('/')[-1], json.dumps(out))
