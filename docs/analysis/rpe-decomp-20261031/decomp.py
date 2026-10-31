"""ORACLE DIAGNOSTIC (public episodes only): what drives RPE / MPPE / AUC of our P_o perception tracks vs mocap, in the
kit's registered convention (lib: library_v3 submitted, kit registration to the public scan), plus ablations by
ground-truth substitution. Reads ground truth (mocap, scans) and the phase-1 X*_trk fits (mocap-fitted). Nothing here
feeds inference.

Substitutions are made in OUR world on the converted host-anchor poses C_s(t), with the truth expressed there by W*,
a robust rigid fit of the whole track onto mocap (rdlib.world_fit; oracle). The kit's own frame-0 alignment then runs
unchanged, so every variant is scored exactly as a submission would be.
  base   P_o as tracked.
  a0     alignment replaced by W* (nothing else changed): the scene-alignment part alone.
  a      the alignment anchors' frame-0 poses replaced by truth (slot 0 full pose; the rotation-anchor object's
         orientation; all-axis episodes: slot 1's position too), our world-frame motion deltas kept.
  a_rot  only the rotation-anchor object's frame-0 orientation (slot 0's for all-axis episodes), deltas kept.
  b      X*_trk: one constant body offset per (episode, object) fitted to mocap (phase-1 fits; AUC upper bound).
  c      objects no hand touches (true travel < 2 cm and true rotation < 5 deg over the episode) held at truth.
  c_rest every object held at truth in the frames where it is still in mocap (+-5 frames: < 0.5 cm, < 2 deg).
  d      every object's frame-0 pose replaced by truth, our world-frame motion deltas kept.
  cd     c, then d on the remaining objects.
  e      the varying remainder = the metric left after b (and after d), reported as values, not deltas.
Usage: python -I decomp.py RDLIB_DIR SCRATCH XTRK_JSON OUT_JSON [--episodes 0,2,...] [--jobs 4]
"""
import argparse, json, os, sys, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor

BOX = {13: 'a', 2: 'a', 26: 'a', 44: 'a', 45: 'a', 41: 'a', 0: 'a', 11: 'b', 21: 'b', 31: 'b', 39: 'b', 22: 'b', 42: 'b',
       23: 'b', 12: 'c', 27: 'c', 24: 'c', 18: 'c', 40: 'c', 43: 'c'}
LIB = '/home/user/v2d-track3/meshes/library_v3'
UNTOUCHED_CM, UNTOUCHED_DEG = 2.0, 5.0


def rnd(m):
    return {k: (round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v]) for k, v in m.items() if not k.startswith('pf_')}


def run(ep, a):
    sys.path.insert(0, a.rdlib)
    import rdlib as L
    from scipy.spatial.transform import Rotation as Rot
    L.load_kit(f'{a.scratch}/dl/kit/v2d_submission_kit'); L.guard(ep)
    t0 = time.time(); t3 = f'{a.scratch}/t3'
    names = L.names_of(t3, ep)
    trk = f'{a.scratch}/store/runs/20261030-orcP1{BOX[ep]}-87fc869/results/leak_p1/ep{ep}/perc2/poses_world_vo.npz'
    P = L.track7(trk, names); T, B = P.shape[:2]
    H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
    G = L.ref_anchor(L.mocap7(t3, ep, names, T), H)                     # GROUND TRUTH
    REG = [L.kit_reg(LIB, n, H[s], ep, s) for s, n in enumerate(names)]
    C = L.convert(P, REG)
    out = dict(ep=ep, names=names, frames=T, track=trk, variants={})
    base = L.score(C, G, H, per_frame=True)
    out['variants']['base'] = rnd(base)

    # ---- oracle world fit and the truth in our world
    W = L.world_fit(C, G, H); Wi = np.linalg.inv(W)
    C4, G4 = L.to4(C), L.to4(G)
    Gw = np.einsum('ij,tsjk->tsik', Wi, G4)                              # truth expressed in our world (T,B,4,4)
    A_W = L.to7(np.einsum('ij,tsjk->tsik', W, C4))
    out['variants']['a0'] = rnd(L.metrics(A_W, G, H))

    tslot, rslot = L.anchor_slots(H)
    def sub_start(slots_full=(), slots_rot=(), slots_pos=()):
        X = C4.copy()
        for s in slots_full:
            X[:, s] = L.retarget_start(C4[:, s], Gw[0, s])
        for s in slots_rot:
            X[:, s] = L.retarget_start(X[:, s], Gw[0, s], rot_only=True)
        for s in slots_pos:
            X[:, s, :3, 3] += Gw[0, s, :3, 3] - X[0, s, :3, 3]
        return L.to7(X)
    if rslot is None:                                                      # all objects have a symmetry axis
        Ca = sub_start(slots_full=[0], slots_pos=[1] if B > 1 else []); Car = sub_start(slots_rot=[0])
    else:
        Ca = sub_start(slots_full=[tslot], slots_rot=[rslot] if rslot != tslot else []); Car = sub_start(slots_rot=[rslot])
    out['variants']['a'] = rnd(L.score(Ca, G, H)); out['variants']['a_rot'] = rnd(L.score(Car, G, H))
    out['anchor'] = dict(translation_slot=tslot, rotation_slot=rslot)

    # ---- b: X*_trk (phase-1 fit to mocap)
    xt = json.load(open(a.xtrk))['episodes'][str(ep)]
    REGt = [L.reg_of_X(np.asarray(xt['objects'][n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
    mb = L.score(L.convert(P, REGt), G, H)
    out['variants']['b'] = rnd(mb); out['phase1_trk_AUC'] = xt['scores']['trk']['AUC']; out['phase1_lib_AUC'] = xt['scores']['lib']['AUC']

    # ---- c: untouched objects held at truth; c_rest: still frames held at truth
    span = L.motion_span(G); still = L.rest_mask(G)
    untouched = [s for s in range(B) if span[s][0] < UNTOUCHED_CM and span[s][1] < UNTOUCHED_DEG]
    Xc = C4.copy()
    for s in untouched:
        Xc[:, s] = Gw[:, s]
    out['variants']['c'] = rnd(L.score(L.to7(Xc), G, H)) if untouched else out['variants']['base']
    Xr = C4.copy(); Xr[still] = Gw[still]
    out['variants']['c_rest'] = rnd(L.score(L.to7(Xr), G, H))
    # ---- d: frame-0 pose per object from truth, our deltas kept; cd: c then d
    Xd = C4.copy()
    for s in range(B):
        Xd[:, s] = L.retarget_start(C4[:, s], Gw[0, s])
    out['variants']['d'] = rnd(L.score(L.to7(Xd), G, H))
    Xcd = Xd.copy()
    for s in untouched:
        Xcd[:, s] = Gw[:, s]
    out['variants']['cd'] = rnd(L.score(L.to7(Xcd), G, H))

    # ---- descriptive diagnostics on base (kit alignment)
    A = L.align(C, G, H)
    Am, Gm = L.to4(A), G4
    obj = []
    for s, h in enumerate(H):
        pos = np.linalg.norm(Am[:, s, :3, 3] - Gm[:, s, :3, 3], axis=1) * 100
        Rerr = np.einsum('tij,tkj->tik', Am[:, s, :3, :3], Gm[:, s, :3, :3])
        if h['order'] == 360:
            aa, ar = Am[:, s, :3, :3] @ h['axis'], Gm[:, s, :3, :3] @ h['axis']
            rot = np.degrees(np.arccos(np.clip((aa * ar).sum(1), -1, 1)))
        else:
            rot = np.degrees(Rot.from_matrix(Rerr).magnitude())
            if h['order'] == 2:
                F = Rot.from_rotvec(np.pi * h['axis']).as_matrix()
                rot = np.minimum(rot, np.degrees(Rot.from_matrix(np.einsum('tij,tkj->tik', Am[:, s, :3, :3], Gm[:, s, :3, :3] @ F)).magnitude()))
        obj.append(dict(name=h['name'], untouched=s in untouched, true_travel_cm=round(span[s][0], 2), true_rot_deg=round(span[s][1], 1),
                        still_frac=round(float(still[:, s].mean()), 3), pos_err_cm_mean=round(float(pos.mean()), 3),
                        rot_err_deg_mean=round(float(rot.mean()), 3), rot_err_deg_f0=round(float(rot[0]), 3),
                        pos_err_cm_f0=round(float(pos[0]), 3), mppe_cm=round(base['obj_MPPE'][s], 4), auc=round(base['obj_AUC'][s], 4),
                        mppe_still_cm=round(float(base['pf_mppe_cm'][still[:, s], s].mean()), 4) if still[:, s].any() else None,
                        mppe_moving_cm=round(float(base['pf_mppe_cm'][~still[:, s], s].mean()), 4) if (~still[:, s]).any() else None))
    out['objects'] = obj
    if B > 1:
        e = base['pf_rpe_cm']; both = still.all(1)
        dr = Gm[:, 1, :3, 3] - Gm[:, 0, :3, 3]
        # lever-arm split in the W*-aligned world: la - lr = Ra^T (da - dr) + (Ra - Rr)^T dr
        AW = L.to4(A_W)
        da = AW[:, 1, :3, 3] - AW[:, 0, :3, 3]
        Ra, Rr = AW[:, 0, :3, :3], Gm[:, 0, :3, :3]
        trans = np.linalg.norm(da - dr, axis=1) * 100
        lever = np.linalg.norm(np.einsum('tji,tj->ti', Ra - Rr, dr), axis=1) * 100
        plain = np.linalg.norm(np.einsum('tji,tj->ti', Ra, da) - np.einsum('tji,tj->ti', Rr, dr), axis=1) * 100
        # same split under the kit's alignment
        dak = Am[:, 1, :3, 3] - Am[:, 0, :3, 3]; Rak = Am[:, 0, :3, :3]
        trans_k = np.linalg.norm(dak - dr, axis=1) * 100
        lever_k = np.linalg.norm(np.einsum('tji,tj->ti', Rak - Rr, dr), axis=1) * 100
        out['rpe'] = dict(kit=round(float(e.mean()), 4), check_vs_kit=round(float(e.mean()) - base['RPE'], 6),
                          frames_both_still=int(both.sum()), rpe_both_still=round(float(e[both].mean()), 4) if both.any() else None,
                          rpe_any_moving=round(float(e[~both].mean()), 4) if (~both).any() else None,
                          share_of_sum_both_still=round(float(e[both].sum() / max(e.sum(), 1e-9)), 3),
                          rpe_f0=round(float(e[0]), 4), true_sep_cm_mean=round(float(np.linalg.norm(dr, axis=1).mean() * 100), 2),
                          plain_rpe_Wstar=round(float(plain.mean()), 4), split_Wstar=dict(rel_translation_cm=round(float(trans.mean()), 4),
                          slot0_rotation_x_lever_cm=round(float(lever.mean()), 4)),
                          split_kit=dict(rel_translation_cm=round(float(trans_k.mean()), 4), slot0_rotation_x_lever_cm=round(float(lever_k.mean()), 4)))
    out['untouched_slots'] = untouched
    out['W_star'] = np.round(W, 6).tolist()
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep} {names}: base AUC {base["AUC"]:.4f} MPPE {base["MPPE"]:.3f} RPE {base["RPE"]:.3f} | '
          + ' '.join(f'{k} {v["RPE"]:.2f}/{v["MPPE"]:.2f}/{v["AUC"]:.3f}' for k, v in out['variants'].items() if k != 'base')
          + f' ({out["seconds"]:.0f} s)', flush=True)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rdlib'); p.add_argument('scratch'); p.add_argument('xtrk'); p.add_argument('out')
    p.add_argument('--episodes', default='0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45')
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args()
    eps = [int(e) for e in a.episodes.split(',')]
    res = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for r in ex.map(run, eps, [a] * len(eps)):
            res[str(r['ep'])] = r
    json.dump(dict(kind='rpe-decomp', note='ORACLE DIAGNOSTIC, public episodes only; reads mocap and scans.', episodes=res),
              open(a.out, 'w'), indent=1)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
