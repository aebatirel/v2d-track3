"""GT-free candidate fixes of the perception tracks, scored on PUBLIC episodes (31 Oct 2026).

The TRANSFORM (rest_hold) reads only inference-side inputs: our object track (poses_world_vo.npz, library_v3 body
frames, our VO world), our perceived hands (hands_refined.npz, same world), our library_v3 meshes and the object
names / slot order. It never sees mocap or scans. SCORING (after the transform) reads mocap and the public scans
through the kit chain (rdlib, lib convention), exactly as decomp.py's base.

Candidates (parameters fixed in PREREG.md before any score was read):
  K1 rest_hold      every run of >= RUN_MIN frames in which the object is 'free' (no perceived hand joint within
                    HAND_CM of its surface, and not in contact (< SUPPORT_CM) with another object that is not free)
                    is held at the run's robust mean pose (median translation, chordal-mean rotation), provided the
                    track stays within DEV_CM / DEV_DEG of that mean over the run (else the run is left as tracked).
  K2 initial_hold   as K1, but only the run that starts at frame 0 (a multi-frame frame-0 estimate held until the
                    first contact), every other frame as tracked.
Hands: a side that is not valid at frame t uses its last valid joints within CARRY frames, else it is absent.
Cups (axis symmetry, a prior on the object class): deviation is measured as tilt of the cup axis (our mesh's distinct
principal axis); spin is unobservable for them and not scored.
Usage: python -I cand.py RDLIB_DIR SCRATCH INPUTS_TSV OUT_JSON [--episodes ...] [--jobs 4] [--dry]
"""
import argparse, json, os, sys, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HAND_CM, SUPPORT_CM, RUN_MIN, CARRY, DEV_CM, DEV_DEG, NPTS = 4.0, 2.0, 10, 10, 5.0, 25.0, 300
BOX = {13: 'a', 2: 'a', 26: 'a', 44: 'a', 45: 'a', 41: 'a', 0: 'a', 11: 'b', 21: 'b', 31: 'b', 39: 'b', 22: 'b', 42: 'b',
       23: 'b', 12: 'c', 27: 'c', 24: 'c', 18: 'c', 40: 'c', 43: 'c'}
LIB = '/home/user/v2d-track3/meshes/library_v3'
SYM_AXIS = {'beige_cup', 'blue_cup'}


# ---------------- GT-FREE transform (inference-side inputs only)
def chordal_mean(R):
    U, _, Vt = np.linalg.svd(R.mean(0)); D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))]); return U @ D @ Vt


def hand_joints(hands_npz, T):
    """(T, 42, 3) perceived joints (right then left), NaN where a side is absent (after carrying CARRY frames)."""
    V = np.load(hands_npz, allow_pickle=True)
    out = np.full((T, 42, 3), np.nan)
    for k, side in enumerate(('right', 'left')):
        J, ok = V[f'joints_{side}'].astype(np.float64), V[f'valid_{side}'].astype(bool)
        last = -10 ** 9
        for t in range(min(T, len(J))):
            if ok[t]:
                last = t
            if t - last <= CARRY:
                out[t, 21 * k:21 * k + 21] = J[last]
    return out


def free_mask(P4, names, pts, J):
    """(T,B) bool: no perceived hand within HAND_CM of the object surface, and not touching a non-free object."""
    T, B = P4.shape[:2]
    W = [np.einsum('tij,kj->tki', P4[:, s, :3, :3], pts[s]) + P4[:, s, None, :3, 3] for s in range(B)]   # (T,K,3)
    hand_far = np.ones((T, B), bool)
    for s in range(B):
        for t in range(T):
            j = J[t][~np.isnan(J[t, :, 0])]
            if len(j):
                d = np.sqrt(((W[s][t][:, None] - j[None]) ** 2).sum(-1)).min()
                hand_far[t, s] = d * 100 > HAND_CM
    free = hand_far.copy()
    if B > 1:
        for s in range(B):
            for o in range(B):
                if o == s:
                    continue
                for t in range(T):
                    if not hand_far[t, o]:
                        d = np.sqrt(((W[s][t][::3, None] - W[o][t][None, ::3]) ** 2).sum(-1)).min()
                        if d * 100 < SUPPORT_CM:
                            free[t, s] = False
    return free, hand_far


def runs(mask):
    out, t = [], 0
    while t < len(mask):
        if mask[t]:
            u = t
            while u + 1 < len(mask) and mask[u + 1]:
                u += 1
            out.append((t, u)); t = u + 1
        else:
            t += 1
    return out


def rest_hold(P4, names, pts, axes, J, initial_only=False):
    """GT-free: returns the held track (T,B,4,4) and a log of the held runs."""
    free, hand_far = free_mask(P4, names, pts, J)
    out = P4.copy(); log = []
    for s, n in enumerate(names):
        for a, b in runs(free[:, s]):
            if initial_only and a != 0:
                continue
            if b - a + 1 < RUN_MIN:
                continue
            seg = P4[a:b + 1, s]
            tm = np.median(seg[:, :3, 3], 0); Rm = chordal_mean(seg[:, :3, :3])
            dev_cm = float(np.linalg.norm(seg[:, :3, 3] - tm, axis=1).max() * 100)
            if n in SYM_AXIS:
                ax = axes[s]; c = np.clip(np.einsum('tij,j->ti', seg[:, :3, :3], ax) @ (Rm @ ax), -1, 1)
                dev_deg = float(np.degrees(np.arccos(c)).max())
            else:
                cosang = np.clip((np.einsum('tij,ij->t', seg[:, :3, :3], Rm) - 1) / 2, -1, 1)
                dev_deg = float(np.degrees(np.arccos(cosang)).max())
            ok = dev_cm < DEV_CM and dev_deg < DEV_DEG
            log.append(dict(obj=n, frames=[int(a), int(b)], dev_cm=round(dev_cm, 2), dev_deg=round(dev_deg, 1), held=bool(ok)))
            if ok:
                out[a:b + 1, s, :3, 3] = tm; out[a:b + 1, s, :3, :3] = Rm
    return out, log, free


def lib_points_axes(names):
    import trimesh
    pts, axes = [], []
    for n in names:
        m = trimesh.load(f'{LIB}/{n}.glb', force='mesh')
        p = np.asarray(trimesh.sample.sample_surface(m, NPTS, seed=0)[0], np.float64); pts.append(p)
        w, U = np.linalg.eigh(np.cov((p - p.mean(0)).T))
        k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axes.append(U[:, k])
    return pts, axes


# ---------------- scoring (reads GROUND TRUTH, after the transform)
def run(ep, a):
    sys.path.insert(0, a.rdlib)
    import rdlib as L
    L.load_kit(f'{a.scratch}/dl/kit/v2d_submission_kit'); L.guard(ep)
    t0 = time.time(); t3 = f'{a.scratch}/t3'
    names = L.names_of(t3, ep)
    trk = f'{a.scratch}/store/runs/20261030-orcP1{BOX[ep]}-87fc869/results/leak_p1/ep{ep}/perc2/poses_world_vo.npz'
    hands = [l.split('\t') for l in open(a.inputs).read().splitlines()]
    hdir = {int(r[0]): r[6] for r in hands[1:]}[ep]
    P = L.track7(trk, names); P4 = L.to4(P); T = len(P)
    J = hand_joints(f'{a.scratch}/store/{hdir}/hands_refined.npz', T)
    pts, axes = lib_points_axes(names)
    cand = {}
    cand['K1'], log1, free = rest_hold(P4, names, pts, axes, J)
    cand['K2'], log2, _ = rest_hold(P4, names, pts, axes, J, initial_only=True)
    res = dict(ep=ep, names=names, frames=T, free_frac=[round(float(free[:, s].mean()), 3) for s in range(len(names))],
               runs_K1=log1, runs_K2=log2, scores={})
    if a.dry:                                                   # transform only: no ground truth is read
        print(f'ep{ep} {names}: free {res["free_frac"]}  K1 held ' + '; '.join(f'{r["obj"]} {r["frames"]} {r["dev_cm"]}cm {r["dev_deg"]}deg {"H" if r["held"] else "-"}' for r in log1), flush=True)
        return res
    # ---- scoring
    H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
    G = L.ref_anchor(L.mocap7(t3, ep, names, T), H)
    REG = [L.kit_reg(LIB, n, H[s], ep, s) for s, n in enumerate(names)]
    for k, X in [('base', P4)] + list(cand.items()):
        m = L.score(L.convert(L.to7(X), REG), G, H)
        res['scores'][k] = {q: round(m[q], 4) for q in ('AUC', 'MPPE', 'RPE')}
        res['scores'][k]['obj_AUC'] = [round(x, 4) for x in m['obj_AUC']]
    res['seconds'] = round(time.time() - t0, 1)
    s = res['scores']
    print(f'ep{ep} {names}: base {s["base"]["RPE"]:.3f}/{s["base"]["MPPE"]:.3f}/{s["base"]["AUC"]:.4f}  K1 {s["K1"]["RPE"]:.3f}/{s["K1"]["MPPE"]:.3f}/{s["K1"]["AUC"]:.4f}  '
          f'K2 {s["K2"]["RPE"]:.3f}/{s["K2"]["MPPE"]:.3f}/{s["K2"]["AUC"]:.4f}  held K1 {sum(r["held"] for r in log1)}/{len(log1)} runs ({res["seconds"]:.0f} s)', flush=True)
    return res


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rdlib'); p.add_argument('scratch'); p.add_argument('inputs'); p.add_argument('out')
    p.add_argument('--episodes', default='0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45')
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--dry', action='store_true', help='run the GT-free transform only (no scoring, no ground truth)')
    a = p.parse_args()
    eps = [int(e) for e in a.episodes.split(',')]
    res = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for r in ex.map(run, eps, [a] * len(eps)):
            res[str(r['ep'])] = r
    json.dump(dict(kind='rpe-decomp candidates', params=dict(HAND_CM=HAND_CM, SUPPORT_CM=SUPPORT_CM, RUN_MIN=RUN_MIN, CARRY=CARRY,
              DEV_CM=DEV_CM, DEV_DEG=DEV_DEG, NPTS=NPTS), episodes=res), open(a.out, 'w'), indent=1)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
