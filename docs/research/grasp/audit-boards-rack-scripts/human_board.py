"""Human strategy on the boards (ep24) from OUR reference (perceived board poses + our MANO hand joints; no ground truth).
Per frame and hand: each fingertip in the board frame: height above the board's UP face (cm, + = above, - = below the
DOWN face), distance outside the footprint rectangle (cm), nearest edge; contacts (MANO link labels) on the board."""
import sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
d = load_ref(sys.argv[1]); lib = sys.argv[2]; every = int(sys.argv[3]); rng = [int(x) for x in sys.argv[4].split(':')] if len(sys.argv) > 4 else [0, d['T']]
names = d['names']; T = d['T']
SLAB = {'wooden_piece_1': (-0.004, 0.004), 'wooden_piece_2': (-0.004, 0.008)}
TIPS = {'T': 4, 'I': 8, 'M': 12, 'R': 16, 'P': 20}
for j, o in enumerate(names):
    m = trimesh.load(f'{lib}/{o}.glb', force='mesh'); b = m.bounds; hy, hz = b[1][1], b[1][2]; ly, lz = b[0][1], b[0][2]
    print(f'==== {o}  footprint y [{ly*100:.1f},{hy*100:.1f}] z [{lz*100:.1f},{hz*100:.1f}] cm, slab x {SLAB[o]}')
    for t in range(rng[0], rng[1], every):
        r = R.from_quat(d['OQ'][t, j]); p = d['OP'][t, j]
        upx = r.apply([1, 0, 0])[2]; s = 1 if upx > 0 else -1
        tilt = np.degrees(np.arccos(min(1, abs(upx))))
        lowest = (r.apply(m.vertices) + p)[:, 2].min() - 0.600
        line = f'f{t:3d} pos ({p[0]*100:5.1f},{p[1]*100:5.1f}) tilt {tilt:4.1f} low {lowest*100:4.1f} |'
        for hs in ('left', 'right'):
            J = d[f'J_{hs}'][t]; loc = r.inv().apply(J - p)
            c = (np.linalg.norm(d[f'cn_{hs}'][t], axis=-1) > 1e-3) & (d[f'cpid_{hs}'][t] == j + 1)
            if c.sum() == 0 and np.min(np.linalg.norm(loc, axis=1)) > 0.2:
                continue
            up_face = SLAB[o][1] if s > 0 else SLAB[o][0]; dn_face = SLAB[o][0] if s > 0 else SLAB[o][1]
            parts = []
            for k, ji in TIPS.items():
                x, y, zz = loc[ji]
                h = s * (x - up_face) if s * (x - up_face) > 0 else (-(s * (dn_face - x)) if s * (dn_face - x) > 0 else 0.0)
                out = max(y - hy, ly - y, zz - hz, lz - zz, 0)
                edge = ['+y', '-y', '+z', '-z'][int(np.argmax([y - hy, ly - y, zz - hz, lz - zz]))]
                parts.append(f'{k}{h*100:+4.1f}/{out*100:3.1f}{edge if out > 0 else "  "}')
            cl = [d['mano_links'][i].replace('link_', '') for i in np.nonzero(c)[0]]
            line += f' {hs[0].upper()} ' + ' '.join(parts) + f' c={len(cl)}:{",".join(cl)} |'
        print(line)
