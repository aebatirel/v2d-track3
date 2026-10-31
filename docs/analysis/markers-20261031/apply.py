"""Apply the marker correction layer (GT-free) to every listed object of one episode and write the variants.

Variants: base (our track as is), noconst (primary without the pooled layout's constant episode offset A_e),
primary (correct.py defaults: gate, outlier rejection, 9-frame smoothing, carry,
static vote with abstain), novote, nocarry (fix frames only, no interpolation; static vote kept), fused (no vote,
no carry). Objects without a census fix file (not eligible) stay as tracked in every variant.
Output npz: world-frame poses per variant: <variant>/<obj> (T,4,4) = world_T_cam @ cam_T_obj, plus stats JSON.
No ground truth, no scan.
Usage: python apply.py SPLIT EP OBJS(comma) OUT_NPZ [--eligible OBJ1,OBJ2]  (default: all OBJS eligible)
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import mlib, correct

VARIANTS = dict(primary={}, novote=dict(vote=False), nocarry=dict(carry=False), fused=dict(vote=False, carry=False),
                noconst=dict(const=False))


def main():
    split, ep, objs, out = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(','), sys.argv[4]
    elig = sys.argv[sys.argv.index('--eligible') + 1].split(',') if '--eligible' in sys.argv else objs
    P = np.load(mlib.poses_path(split, ep)); W = P['world_T_cam'].astype(np.float64)
    res, stats = {}, {}
    for o in objs:
        T = P[f'cam_T_{o}'].astype(np.float64)
        res[f'base/{o}'] = W @ T
        f = f'{mlib.S}/mk/scan/fix_{split}{ep}_{o}.npz'
        if not os.path.exists(f) or o not in elig:
            for v in VARIANTS:
                res[f'{v}/{o}'] = W @ T
            stats[o] = 'not eligible'; continue
        F = np.load(f); n = len(F['n'])
        for v, opt in VARIANTS.items():
            Tc, C, info = correct.correct(T[:n], F['n'], F['fix'], F['rest'], opt, A=F['A'] if 'A' in F.files else None)
            Tfull = T.copy(); Tfull[:n] = Tc
            res[f'{v}/{o}'] = W @ Tfull
            if v == 'primary':
                from scipy.spatial.transform import Rotation as Rot
                info['corr_t_mm_med'] = round(float(np.median(np.linalg.norm(C[:, :3, 3], axis=1)) * 1000), 2)
                info['corr_r_deg_med'] = round(float(np.median(np.degrees(Rot.from_matrix(C[:, :3, :3]).magnitude()))), 2)
                info['f0_t_mm'] = round(float(np.linalg.norm(C[0, :3, 3]) * 1000), 2)
                info['f0_r_deg'] = round(float(np.degrees(Rot.from_matrix(C[0, :3, :3]).magnitude())), 2)
                stats[o] = info
    np.savez_compressed(out, **res)
    json.dump(stats, open(out.replace('.npz', '.json'), 'w'), indent=1)
    print(ep, json.dumps({o: (s if isinstance(s, str) else {k: s[k] for k in ('fix3', 'accepted', 'corr_t_mm_med', 'corr_r_deg_med', 'f0_t_mm', 'f0_r_deg')}) for o, s in stats.items()}))


if __name__ == '__main__':
    main()
