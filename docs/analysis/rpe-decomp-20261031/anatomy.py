"""ORACLE DIAGNOSTIC (public episodes only): anatomy of the kit's RPE for our P_o tracks (lib convention, kit world).
Per frame, with the kit's own symmetry-aware formula (_symmetry_relative_position_cm, pair 0-1):
  full    as scored;
  trans   slot 0's achieved rotation replaced by the true one: only the relative-translation error is left;
  lever   the achieved slot-1-minus-slot-0 vector replaced by the true one: only slot 0's rotation error times the
          true separation is left (cups: tilt only, as the kit ignores their spin; lid: min over its flip).
Phases from mocap (still = +-5 frames < 0.5 cm, < 2 deg). Reads ground truth.
Usage: python -I anatomy.py RDLIB_DIR SCRATCH OUT_JSON
"""
import json, sys
import numpy as np
sys.path.insert(0, sys.argv[1])
import rdlib as L

BOX = {13: 'a', 2: 'a', 26: 'a', 0: 'a', 11: 'b', 21: 'b', 31: 'b', 22: 'b', 23: 'b', 12: 'c', 27: 'c', 24: 'c', 18: 'c'}
LIB = '/home/user/v2d-track3/meshes/library_v3'


def kit_pair_err(Ra, pa0, pa1, Rr, pr0, pr1, H):
    la = np.einsum('tji,tj->ti', Ra, pa1 - pa0); lr = np.einsum('tji,tj->ti', Rr, pr1 - pr0)
    ax, o = H[0]['axis'], H[0]['order']
    if o == 2:
        alt = lr @ L.M._axial_rotations(ax, 2)[1]
        return np.minimum(np.linalg.norm(la - lr, axis=-1), np.linalg.norm(la - alt, axis=-1)) * 100
    if np.any(ax):
        ha, hr = la @ ax, lr @ ax
        pa = np.linalg.norm(la - ha[:, None] * ax, axis=-1); pr = np.linalg.norm(lr - hr[:, None] * ax, axis=-1)
        return np.hypot(ha - hr, pa - pr) * 100
    return np.linalg.norm(la - lr, axis=-1) * 100


def main():
    scratch, out = sys.argv[2], sys.argv[3]
    L.load_kit(f'{scratch}/dl/kit/v2d_submission_kit'); t3 = f'{scratch}/t3'; res = {}
    for ep in sorted(BOX):
        L.guard(ep)
        names = L.names_of(t3, ep)
        P = L.track7(f'{scratch}/store/runs/20261030-orcP1{BOX[ep]}-87fc869/results/leak_p1/ep{ep}/perc2/poses_world_vo.npz', names)
        H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
        G = L.ref_anchor(L.mocap7(t3, ep, names, len(P)), H)
        REG = [L.kit_reg(LIB, n, H[s], ep, s) for s, n in enumerate(names)]
        A = L.align(L.convert(P, REG), G, H)
        Ra, Rr = L.M._rotation_matrix(A[:, 0, 3:]), L.M._rotation_matrix(G[:, 0, 3:])
        full = kit_pair_err(Ra, A[:, 0, :3], A[:, 1, :3], Rr, G[:, 0, :3], G[:, 1, :3], H)
        trans = kit_pair_err(Rr, A[:, 0, :3], A[:, 1, :3], Rr, G[:, 0, :3], G[:, 1, :3], H)
        lever = kit_pair_err(Ra, G[:, 0, :3], G[:, 1, :3], Rr, G[:, 0, :3], G[:, 1, :3], H)
        still = L.rest_mask(G)
        ph = {'both_still': still.all(1), 'slot0_moving': ~still[:, 0], 'only_slot1_moving': still[:, 0] & ~still[:, 1]}
        r = dict(names=names, rpe=round(float(full.mean()), 4), trans_only=round(float(trans.mean()), 4), lever_only=round(float(lever.mean()), 4),
                 sep_cm=round(float(np.linalg.norm(G[:, 1, :3] - G[:, 0, :3], axis=1).mean() * 100), 2), phases={})
        for k, m in ph.items():
            r['phases'][k] = dict(frac=round(float(m.mean()), 3), rpe=round(float(full[m].mean()), 3) if m.any() else None,
                                  share=round(float(full[m].sum() / full.sum()), 3),
                                  trans=round(float(trans[m].mean()), 3) if m.any() else None, lever=round(float(lever[m].mean()), 3) if m.any() else None)
        res[str(ep)] = r
        print(ep, names, r['rpe'], 'trans', r['trans_only'], 'lever', r['lever_only'], {k: (v['frac'], v['rpe'], v['share']) for k, v in r['phases'].items()}, flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
