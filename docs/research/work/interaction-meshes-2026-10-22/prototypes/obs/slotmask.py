# DIAGNOSTIC (slot box from the public scan): silhouette free evidence (maskfuse) in the real slot vs real material,
# and over the whole real solid / real empty space of the scan near the board (defects grid is not aligned: use boxes).
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
        f, v = z['NMF'][B], z['NMV'][B]
        out[nm] = dict(NMV_med=float(np.median(v)), NMF_med=float(np.median(f)), ratio_med=round(float(np.median(f / np.maximum(v, 1))), 3),
                       free50=round(float(((f >= 3) & (f >= 0.5 * v)).mean()), 2), free30=round(float(((f >= 3) & (f >= 0.3 * v)).mean()), 2))
    print(g.split('/')[-1], json.dumps(out), 'colour', np.round(z['colour_mu_med'], 1).tolist(), np.round(z['colour_sg_med'], 1).tolist())
